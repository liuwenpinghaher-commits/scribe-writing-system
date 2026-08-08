"""Work ownership helpers (registry metadata + enforcement)."""
from __future__ import annotations

import os
from typing import Any


def legacy_owner() -> str:
    return (os.environ.get("SCRIBE3_LEGACY_OWNER") or "admin").strip() or "admin"


def effective_owner(work_row: dict[str, Any] | None) -> str | None:
    """Resolve owner for a registry row (legacy books → SCRIBE3_LEGACY_OWNER)."""
    if not work_row:
        return None
    raw = work_row.get("owner_user_id")
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    return legacy_owner()


def user_owns_work(username: str | None, work_row: dict[str, Any] | None) -> bool:
    if not username or not work_row:
        return False
    # 管理员可访问任意作品（管理台 + 业务路径）
    try:
        from scribe3.auth.users import is_admin
        if is_admin(username):
            return True
    except Exception:
        pass
    owner = effective_owner(work_row)
    return owner == str(username).strip()


def filter_works_for_user(
    rows: list[dict[str, Any]], username: str | None
) -> list[dict[str, Any]]:
    if username is None:
        return list(rows)
    uid = str(username).strip()
    try:
        from scribe3.auth.users import is_admin
        if is_admin(uid):
            return list(rows)
    except Exception:
        pass
    out = []
    for r in rows:
        if effective_owner(r) == uid:
            out.append(r)
    return out


def get_work_row(slug: str, url: str | None = None) -> dict[str, Any] | None:
    """Fetch a single work registry row (active or archived).

    Prefer ``WHERE slug = $s`` over record-id constructors: on SurrealDB
    2.1.x ``type::record('work', $s)`` InternalError on some deployments,
    which turned every work-scoped API into HTTP 500 after L1 auth was enabled.
    """
    if not slug or not all(c.isalnum() or c == "_" for c in slug):
        return None
    from scribe3.store.core_preamble import _reg_conn

    db = _reg_conn(url)
    try:
        # Match list_works style (table scan by slug field) — reliable on _reg.
        rows = db.query("SELECT * FROM work WHERE slug = $s", {"s": slug})
        if not rows:
            # Fallback: record id == slug (create_work uses work:<slug>)
            try:
                rows = db.query(
                    "SELECT * FROM work WHERE id = type::thing('work', $s)",
                    {"s": slug},
                )
            except Exception:
                rows = None
        if not rows:
            return None
        r = rows[0]
        return {
            "slug": r.get("slug") or slug,
            "title": r.get("title"),
            "owner_user_id": r.get("owner_user_id"),
            "archived": r.get("archived"),
        }
    except Exception:
        # Never bubble Surreal driver errors as uncaught 500 through middleware;
        # treat as missing so callers get 404 rather than blank UI.
        return None
    finally:
        db.close()


def assert_user_may_access_work(username: str | None, slug: str, url: str | None = None) -> None:
    """Raise PermissionError if user may not access slug; KeyError if missing."""
    row = get_work_row(slug, url=url)
    if row is None:
        raise KeyError(slug)
    if not user_owns_work(username, row):
        raise PermissionError(slug)
