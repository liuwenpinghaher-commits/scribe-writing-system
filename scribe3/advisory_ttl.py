"""DED-11 / B-01：advisory 72 小时内可一键收下正文。

真源是 advisory_pending 表（migration 164）。进程内 dict 只做 1 秒快路径，
多 Worker 之间以库为准，重启后仍能确认已生成的稿。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

ADVISORY_TTL_HOURS = 72
_CACHE_SEC = 1.0
# 1 秒快路径；不是多 Worker 共享真源
_CACHE: dict[int, tuple[float, dict[str, Any]]] = {}
_log = logging.getLogger("scribe3.advisory_ttl")


def _now() -> float:
    return time.time()


def _rec(
    seq: int,
    prose: str,
    items: list | None,
    *,
    ttl_hours: int = ADVISORY_TTL_HOURS,
    status: str = "pending",
) -> dict[str, Any]:
    now = _now()
    return {
        "seq": int(seq),
        "advisory_id": str(int(seq)),
        "prose": prose or "",
        "items": list(items or []),
        "status": status,
        "marked_at": now,
        "expires_at": now + int(ttl_hours) * 3600,
    }


def _cache_put(rec: dict[str, Any]) -> None:
    _CACHE[int(rec["seq"])] = (_now(), dict(rec))


def _cache_get(seq: int) -> dict[str, Any] | None:
    hit = _CACHE.get(int(seq))
    if not hit:
        return None
    ts, rec = hit
    if _now() - ts > _CACHE_SEC:
        return None
    return dict(rec)


def _row_to_rec(row: dict[str, Any]) -> dict[str, Any]:
    items = row.get("items")
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            items = []
    if not isinstance(items, list):
        items = []
    return {
        "seq": int(row.get("seq") or 0),
        "advisory_id": str(row.get("advisory_id") or row.get("seq") or ""),
        "prose": row.get("prose") or "",
        "items": items,
        "status": row.get("status") or "pending",
        "marked_at": float(row.get("marked_at") or 0),
        "expires_at": float(row.get("expires_at") or 0),
    }


def _db_write(store: Any, rec: dict[str, Any]) -> None:
    writer = getattr(store, "_execute_write", None)
    if not callable(writer):
        return
    writer(
        "UPSERT type::record('advisory_pending', $seq) SET "
        "seq=$seq, advisory_id=$aid, prose=$prose, items=$items, status=$st, "
        "marked_at=$ma, expires_at=$ex, updated_at=time::now()",
        {
            "seq": int(rec["seq"]),
            "aid": str(rec.get("advisory_id") or rec["seq"]),
            "prose": rec.get("prose") or "",
            "items": json.dumps(rec.get("items") or [], ensure_ascii=False),
            "st": rec.get("status") or "pending",
            "ma": float(rec.get("marked_at") or 0),
            "ex": float(rec.get("expires_at") or 0),
        },
    )


def _db_read(store: Any, seq: int) -> dict[str, Any] | None:
    getter = getattr(store, "_query", None)
    if not callable(getter):
        return None
    try:
        rows = getter(
            "SELECT seq, advisory_id, prose, items, status, marked_at, expires_at "
            "FROM type::record('advisory_pending', $seq) LIMIT 1",
            {"seq": int(seq)},
        ) or []
    except Exception as e:
        _log.warning("advisory_pending read fail seq=%s: %s", seq, e)
        return None
    if not rows:
        try:
            rows = getter(
                "SELECT seq, advisory_id, prose, items, status, marked_at, expires_at "
                "FROM advisory_pending WHERE seq=$seq LIMIT 1",
                {"seq": int(seq)},
            ) or []
        except Exception:
            rows = []
    if not rows:
        return None
    return _row_to_rec(rows[0] if isinstance(rows[0], dict) else {})


def mark_advisory_pending(
    seq: int,
    prose: str,
    items: list | None = None,
    *,
    ttl_hours: int = ADVISORY_TTL_HOURS,
    store: Any = None,
    advisory_id: str | None = None,
) -> dict[str, Any]:
    rec = _rec(seq, prose, items, ttl_hours=ttl_hours)
    if advisory_id:
        rec["advisory_id"] = str(advisory_id)
    if store is not None:
        _db_write(store, rec)
    _cache_put(rec)
    return dict(rec)


def get_advisory_pending(seq: int, store: Any = None) -> dict[str, Any] | None:
    cached = _cache_get(int(seq))
    if cached:
        return cached
    if store is not None:
        rec = _db_read(store, seq)
        if rec:
            _cache_put(rec)
            return rec
    hit = _CACHE.get(int(seq))
    if hit:
        return dict(hit[1])
    return None


def check_advisory_pending(seq: int, advisory_id: str | None = None, store: Any = None) -> dict[str, Any] | None:
    rec = get_advisory_pending(seq, store=store)
    if not rec:
        return None
    if advisory_id and str(rec.get("advisory_id") or "") not in ("", str(advisory_id)):
        return None
    if float(rec.get("expires_at") or 0) < _now():
        rec = dict(rec)
        rec["status"] = "expired"
        return rec
    if rec.get("status") != "pending":
        return rec
    return rec


def accept_advisory(store: Any, seq: int) -> dict[str, Any]:
    rec = get_advisory_pending(seq, store=store)
    if not rec:
        return {"ok": False, "code": "not_found", "message": "没有待确认的稿"}
    if rec.get("status") != "pending":
        return {"ok": False, "code": rec.get("status") or "gone", "message": "这条已经处理过"}
    if float(rec.get("expires_at") or 0) < _now():
        rec["status"] = "expired"
        _cache_put(rec)
        if store is not None:
            rec2 = dict(rec)
            _db_write(store, rec2)
        return {"ok": False, "code": "expired", "message": "超过 72 小时，这条待确认过期了"}
    saver = getattr(store, "save_chapter", None)
    if callable(saver):
        saver(int(seq), rec.get("prose") or "")
    rec = dict(rec)
    rec["status"] = "accepted"
    _cache_put(rec)
    if store is not None:
        deleter = getattr(store, "_execute_write", None)
        if callable(deleter):
            try:
                deleter(
                    "DELETE type::record('advisory_pending', $seq)",
                    {"seq": int(seq)},
                )
            except Exception:
                rec["status"] = "accepted"
                _db_write(store, rec)
        else:
            _db_write(store, rec)
    return {"ok": True, "seq": int(seq), "status": "accepted"}
