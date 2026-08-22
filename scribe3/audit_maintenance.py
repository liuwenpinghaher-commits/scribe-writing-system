"""GAP-3：audit_event TTL 清理 + 查询。"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import logging
import os
from typing import Any

_log = logging.getLogger("scribe3.audit_maintenance")


def audit_ttl_days() -> int:
    try:
        from scribe3.settings import get_setting
        v = get_setting("SCRIBE3_AUDIT_TTL_DAYS")
        return max(1, int(v))
    except Exception:
        pass
    raw = (get_flag("SCRIBE3_AUDIT_TTL_DAYS") or "30").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 30


def purge_audit_events(store: Any, *, days: int | None = None) -> dict[str, Any]:
    """删除超过 TTL 的审计行。best-effort。"""
    d = audit_ttl_days() if days is None else max(1, int(days))
    try:
        store.purge_audit_events_older_than(d)
        return {"ok": True, "ttl_days": d, "action": "deleted_older_than"}
    except Exception as e:
        _log.warning("purge_audit_events failed: %s", e)
        return {"ok": False, "ttl_days": d, "error": str(e)[:160]}


def query_audit_log(
    store: Any,
    *,
    table: str | None = None,
    kind: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """读取审计日志（最近 N 条）。"""
    lim = max(1, min(500, int(limit or 50)))
    try:
        return store.query_audit_events(table=table, kind=kind, limit=lim)
    except Exception as e:
        _log.debug("query_audit_log: %s", e)
        return []
