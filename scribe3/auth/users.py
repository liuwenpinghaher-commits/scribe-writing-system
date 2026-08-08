"""SQLite user store for L1 auth + admin console (roles, status, audit)."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from scribe3.auth.passwords import hash_password, verify_password

_lock = threading.Lock()

ROLES = frozenset({"admin", "author"})
STATUSES = frozenset({"active", "disabled"})


def _db_path() -> Path:
    override = os.environ.get("SCRIBE3_AUTH_DB")
    if override:
        return Path(override)
    settings = os.environ.get("SCRIBE3_SETTINGS_DB")
    if settings:
        return Path(settings).expanduser().resolve().parent / "scribe3_auth.sqlite3"
    return Path.home() / ".scribe2-surreal" / "scribe3_auth.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "username TEXT PRIMARY KEY NOT NULL,"
        "password_hash TEXT NOT NULL,"
        "created_at REAL NOT NULL"
        ")"
    )
    # 增量列（老库兼容）
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    alters = [
        ("role", "TEXT NOT NULL DEFAULT 'author'"),
        ("display_name", "TEXT"),
        ("status", "TEXT NOT NULL DEFAULT 'active'"),
        ("note", "TEXT"),
        ("updated_at", "REAL"),
        ("last_login_at", "REAL"),
        ("password_changed_at", "REAL"),
        ("session_version", "INTEGER NOT NULL DEFAULT 0"),
    ]
    for name, decl in alters:
        if name not in cols:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {decl}")
            except sqlite3.OperationalError:
                pass
    conn.execute(
        "CREATE TABLE IF NOT EXISTS auth_audit ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "ts REAL NOT NULL,"
        "actor TEXT NOT NULL,"
        "action TEXT NOT NULL,"
        "target_type TEXT,"
        "target_id TEXT,"
        "detail TEXT"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_audit_ts ON auth_audit(ts DESC)"
    )
    conn.commit()
    return conn


def _row_public(row: sqlite3.Row | dict) -> dict[str, Any]:
    d = dict(row) if not isinstance(row, dict) else row
    return {
        "username": d.get("username"),
        "role": (d.get("role") or "author").strip() or "author",
        "display_name": d.get("display_name") or "",
        "status": (d.get("status") or "active").strip() or "active",
        "note": d.get("note") or "",
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
        "last_login_at": d.get("last_login_at"),
        "password_changed_at": d.get("password_changed_at"),
        "session_version": int(d.get("session_version") or 0),
    }


def _bootstrap_admin_names() -> set[str]:
    """Users that should be admin on first seed / SCRIBE3_ADMIN_USERS."""
    raw = (os.environ.get("SCRIBE3_ADMIN_USERS") or "admin").strip()
    names = {p.strip() for p in raw.split(",") if p.strip()}
    # bootstrap list first token often admin
    boot = (os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "").strip()
    if boot:
        first = boot.split(",")[0].strip()
        if ":" in first:
            names.add(first.split(":", 1)[0].strip())
    return names or {"admin"}


def ensure_bootstrap_users() -> list[str]:
    """Seed SCRIBE3_BOOTSTRAP_USERS when the table is empty. Returns created usernames."""
    raw = (os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "").strip()
    if not raw:
        _ensure_at_least_one_admin()
        return []
    created: list[str] = []
    admins = _bootstrap_admin_names()
    with _lock:
        conn = _connect()
        try:
            n = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            if n > 0:
                _promote_env_admins(conn)
                conn.commit()
                return []
            now = time.time()
            for part in raw.split(","):
                part = part.strip()
                if not part or ":" not in part:
                    continue
                user, pw = part.split(":", 1)
                user = user.strip()
                pw = pw.strip()
                if not user or not pw:
                    continue
                role = "admin" if user in admins else "author"
                conn.execute(
                    "INSERT INTO users(username, password_hash, created_at, role, status, "
                    "updated_at, password_changed_at, session_version) "
                    "VALUES(?,?,?,?,?,?,?,0)",
                    (user, hash_password(pw), now, role, "active", now, now),
                )
                created.append(user)
            # 若 bootstrap 无人落 admin，把第一个人提为 admin
            if created and not any(
                conn.execute(
                    "SELECT 1 FROM users WHERE role='admin' LIMIT 1"
                ).fetchone()
            ):
                conn.execute(
                    "UPDATE users SET role='admin' WHERE username=?",
                    (created[0],),
                )
            conn.commit()
        finally:
            conn.close()
    return created


def _promote_env_admins(conn: sqlite3.Connection) -> None:
    for name in _bootstrap_admin_names():
        conn.execute(
            "UPDATE users SET role='admin' WHERE username=? AND (role IS NULL OR role='' OR role='author')",
            (name,),
        )
        # only promote if still author — actually always set admin for listed names
        conn.execute(
            "UPDATE users SET role='admin' WHERE username=?",
            (name,),
        )


def _ensure_at_least_one_admin() -> None:
    with _lock:
        conn = _connect()
        try:
            n = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role='admin' AND status='active'"
            ).fetchone()["c"]
            if n == 0:
                row = conn.execute(
                    "SELECT username FROM users ORDER BY created_at ASC LIMIT 1"
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE users SET role='admin' WHERE username=?",
                        (row["username"],),
                    )
                    conn.commit()
        finally:
            conn.close()


def create_user(
    username: str,
    password: str,
    *,
    role: str = "author",
    display_name: str = "",
    note: str = "",
    status: str = "active",
) -> dict[str, Any]:
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("username and password required")
    if len(username) > 64 or not all(
        c.isalnum() or c in "._-" for c in username
    ):
        raise ValueError("username must be 1-64 chars: letters, digits, . _ -")
    role = (role or "author").strip()
    if role not in ROLES:
        raise ValueError(f"role must be one of {sorted(ROLES)}")
    status = (status or "active").strip()
    if status not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    now = time.time()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO users(username, password_hash, created_at, role, display_name, "
                "status, note, updated_at, password_changed_at, session_version) "
                "VALUES(?,?,?,?,?,?,?,?,?,0)",
                (
                    username,
                    hash_password(password),
                    now,
                    role,
                    (display_name or "").strip() or None,
                    status,
                    (note or "").strip() or None,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()
            return _row_public(row)
        except sqlite3.IntegrityError as e:
            raise ValueError(f"user exists: {username}") from e
        finally:
            conn.close()


def get_user(username: str) -> dict[str, Any] | None:
    username = (username or "").strip()
    if not username:
        return None
    ensure_bootstrap_users()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()
        finally:
            conn.close()
    return _row_public(row) if row else None


def list_users(
    *,
    q: str | None = None,
    role: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    ensure_bootstrap_users()
    offset = max(0, int(offset))
    limit = max(1, min(200, int(limit)))
    clauses: list[str] = []
    params: list[Any] = []
    if q and q.strip():
        clauses.append(
            "(username LIKE ? OR IFNULL(display_name,'') LIKE ? OR IFNULL(note,'') LIKE ?)"
        )
        like = f"%{q.strip()}%"
        params.extend([like, like, like])
    if role and role.strip() in ROLES:
        clauses.append("role = ?")
        params.append(role.strip())
    if status and status.strip() in STATUSES:
        clauses.append("status = ?")
        params.append(status.strip())
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with _lock:
        conn = _connect()
        try:
            total = conn.execute(
                f"SELECT COUNT(*) AS c FROM users{where}", params
            ).fetchone()["c"]
            rows = conn.execute(
                f"SELECT * FROM users{where} ORDER BY created_at ASC "
                f"LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        finally:
            conn.close()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_row_public(r) for r in rows],
    }


def update_user(
    username: str,
    *,
    display_name: str | None = None,
    role: str | None = None,
    status: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    username = (username or "").strip()
    cur = get_user(username)
    if not cur:
        raise KeyError(username)
    fields: list[str] = []
    params: list[Any] = []
    if display_name is not None:
        fields.append("display_name = ?")
        params.append(display_name.strip() or None)
    if role is not None:
        role = role.strip()
        if role not in ROLES:
            raise ValueError(f"role must be one of {sorted(ROLES)}")
        if cur["role"] == "admin" and role != "admin":
            _assert_not_last_active_admin(username)
        fields.append("role = ?")
        params.append(role)
    if status is not None:
        status = status.strip()
        if status not in STATUSES:
            raise ValueError(f"status must be one of {sorted(STATUSES)}")
        if cur["role"] == "admin" and status == "disabled":
            _assert_not_last_active_admin(username)
        fields.append("status = ?")
        params.append(status)
    if note is not None:
        fields.append("note = ?")
        params.append(note.strip() or None)
    if not fields:
        return cur
    fields.append("updated_at = ?")
    params.append(time.time())
    params.append(username)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE username = ?",
                params,
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()
        finally:
            conn.close()
    return _row_public(row)


def set_password(username: str, password: str, *, bump_session: bool = True) -> None:
    username = (username or "").strip()
    if not get_user(username):
        raise KeyError(username)
    if len(password or "") < 6:
        raise ValueError("password must be at least 6 characters")
    now = time.time()
    with _lock:
        conn = _connect()
        try:
            if bump_session:
                conn.execute(
                    "UPDATE users SET password_hash=?, password_changed_at=?, "
                    "updated_at=?, session_version=IFNULL(session_version,0)+1 "
                    "WHERE username=?",
                    (hash_password(password), now, now, username),
                )
            else:
                conn.execute(
                    "UPDATE users SET password_hash=?, password_changed_at=?, "
                    "updated_at=? WHERE username=?",
                    (hash_password(password), now, now, username),
                )
            conn.commit()
        finally:
            conn.close()


def delete_user(username: str) -> None:
    username = (username or "").strip()
    cur = get_user(username)
    if not cur:
        raise KeyError(username)
    if cur["role"] == "admin":
        _assert_not_last_active_admin(username)
    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM users WHERE username=?", (username,))
            conn.commit()
        finally:
            conn.close()


def force_logout(username: str) -> int:
    """Bump session_version so existing cookies stop validating."""
    username = (username or "").strip()
    if not get_user(username):
        raise KeyError(username)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET session_version=IFNULL(session_version,0)+1, "
                "updated_at=? WHERE username=?",
                (time.time(), username),
            )
            conn.commit()
            row = conn.execute(
                "SELECT session_version FROM users WHERE username=?",
                (username,),
            ).fetchone()
            return int(row["session_version"] or 0)
        finally:
            conn.close()


def get_session_version(username: str) -> int:
    u = get_user(username)
    return int((u or {}).get("session_version") or 0)


def _assert_not_last_active_admin(username: str) -> None:
    with _lock:
        conn = _connect()
        try:
            n = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role='admin' AND status='active' "
                "AND username != ?",
                (username,),
            ).fetchone()["c"]
        finally:
            conn.close()
    if n < 1:
        raise ValueError("cannot remove or demote the last active admin")


def count_active_admins() -> int:
    ensure_bootstrap_users()
    with _lock:
        conn = _connect()
        try:
            return int(
                conn.execute(
                    "SELECT COUNT(*) AS c FROM users WHERE role='admin' AND status='active'"
                ).fetchone()["c"]
            )
        finally:
            conn.close()


def is_admin(username: str | None) -> bool:
    if not username:
        return False
    # env force-list always admin if account exists and active
    if username.strip() in _bootstrap_admin_names():
        u = get_user(username)
        return bool(u and u.get("status") == "active")
    u = get_user(username)
    return bool(u and u.get("role") == "admin" and u.get("status") == "active")


def authenticate(username: str, password: str) -> bool:
    username = (username or "").strip()
    if not username or not password:
        return False
    ensure_bootstrap_users()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT password_hash, status FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        finally:
            conn.close()
    if not row:
        verify_password(password, hash_password("dummy-timing"))
        return False
    if (row["status"] or "active") == "disabled":
        verify_password(password, hash_password("dummy-timing"))
        return False
    ok = verify_password(password, row["password_hash"])
    if ok:
        touch_login(username)
    return ok


def touch_login(username: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET last_login_at=? WHERE username=?",
                (time.time(), username),
            )
            conn.commit()
        finally:
            conn.close()


def user_exists(username: str) -> bool:
    return get_user(username) is not None


def write_audit(
    actor: str,
    action: str,
    *,
    target_type: str = "",
    target_id: str = "",
    detail: dict | list | str | None = None,
) -> None:
    detail_s = ""
    if detail is not None:
        if isinstance(detail, (dict, list)):
            detail_s = json.dumps(detail, ensure_ascii=False)[:4000]
        else:
            detail_s = str(detail)[:4000]
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO auth_audit(ts, actor, action, target_type, target_id, detail) "
                "VALUES(?,?,?,?,?,?)",
                (
                    time.time(),
                    (actor or "").strip() or "?",
                    (action or "").strip() or "unknown",
                    target_type or "",
                    target_id or "",
                    detail_s,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def list_audit(
    *,
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    offset = max(0, int(offset))
    limit = max(1, min(200, int(limit)))
    clauses: list[str] = []
    params: list[Any] = []
    if actor and actor.strip():
        clauses.append("actor = ?")
        params.append(actor.strip())
    if action and action.strip():
        clauses.append("action = ?")
        params.append(action.strip())
    if target_type and target_type.strip():
        clauses.append("target_type = ?")
        params.append(target_type.strip())
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with _lock:
        conn = _connect()
        try:
            total = conn.execute(
                f"SELECT COUNT(*) AS c FROM auth_audit{where}", params
            ).fetchone()["c"]
            rows = conn.execute(
                f"SELECT id, ts, actor, action, target_type, target_id, detail "
                f"FROM auth_audit{where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        finally:
            conn.close()
    items = []
    for r in rows:
        d = dict(r)
        try:
            d["detail"] = json.loads(d["detail"]) if d.get("detail") else None
        except Exception:
            pass
        items.append(d)
    return {"total": total, "offset": offset, "limit": limit, "items": items}


def summary_counts() -> dict[str, Any]:
    ensure_bootstrap_users()
    with _lock:
        conn = _connect()
        try:
            total = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            active = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE status='active'"
            ).fetchone()["c"]
            disabled = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE status='disabled'"
            ).fetchone()["c"]
            admins = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role='admin' AND status='active'"
            ).fetchone()["c"]
            authors = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role='author'"
            ).fetchone()["c"]
        finally:
            conn.close()
    return {
        "users_total": total,
        "users_active": active,
        "users_disabled": disabled,
        "admins_active": admins,
        "authors": authors,
    }
