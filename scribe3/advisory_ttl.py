"""DED-11：advisory 72 小时内可一键收下正文。"""
from __future__ import annotations

import time
from typing import Any

ADVISORY_TTL_HOURS = 72
_PENDING: dict[int, dict[str, Any]] = {}


def mark_advisory_pending(
    seq: int,
    prose: str,
    items: list | None = None,
    *,
    ttl_hours: int = ADVISORY_TTL_HOURS,
) -> dict[str, Any]:
    now = time.time()
    rec = {
        "seq": int(seq),
        "prose": prose or "",
        "items": list(items or []),
        "status": "pending",
        "marked_at": now,
        "expires_at": now + int(ttl_hours) * 3600,
    }
    _PENDING[int(seq)] = rec
    return dict(rec)


def get_advisory_pending(seq: int) -> dict[str, Any] | None:
    rec = _PENDING.get(int(seq))
    return dict(rec) if rec else None


def accept_advisory(store: Any, seq: int) -> dict[str, Any]:
    rec = _PENDING.get(int(seq))
    if not rec:
        return {"ok": False, "code": "not_found", "message": "没有待确认的稿"}
    if rec.get("status") != "pending":
        return {"ok": False, "code": rec.get("status") or "gone", "message": "这条已经处理过"}
    if float(rec.get("expires_at") or 0) < time.time():
        rec["status"] = "expired"
        return {"ok": False, "code": "expired", "message": "超过 72 小时，这条待确认过期了"}
    saver = getattr(store, "save_chapter", None)
    if callable(saver):
        saver(int(seq), rec.get("prose") or "")
    rec["status"] = "accepted"
    return {"ok": True, "seq": int(seq), "status": "accepted"}
