"""SQLite user store for L1 auth (alongside settings ledger)."""
from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

from scribe3.auth.passwords import hash_password, verify_password

_lock = threading.Lock()


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
    conn.commit()
    return conn


def ensure_bootstrap_users() -> list[str]:
    """Seed SCRIBE3_BOOTSTRAP_USERS when the table is empty. Returns created usernames."""
    raw = (os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "").strip()
    if not raw:
        return []
    created: list[str] = []
    with _lock:
        conn = _connect()
        try:
            n = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            if n > 0:
                return []
            import time

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
                conn.execute(
                    "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
                    (user, hash_password(pw), now),
                )
                created.append(user)
            conn.commit()
        finally:
            conn.close()
    return created


def create_user(username: str, password: str) -> None:
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("username and password required")
    import time

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
                (username, hash_password(password), time.time()),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError(f"user exists: {username}") from e
        finally:
            conn.close()


def authenticate(username: str, password: str) -> bool:
    username = (username or "").strip()
    if not username or not password:
        return False
    ensure_bootstrap_users()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username,)
            ).fetchone()
        finally:
            conn.close()
    if not row:
        # Dummy verify to reduce timing oracle on missing users
        verify_password(password, hash_password("dummy-timing"))
        return False
    return verify_password(password, row["password_hash"])


def user_exists(username: str) -> bool:
    username = (username or "").strip()
    if not username:
        return False
    ensure_bootstrap_users()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)
            ).fetchone()
        finally:
            conn.close()
    return row is not None
