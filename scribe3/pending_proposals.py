"""DIR-01 / N-06：execute=false 的提案落到可按 id 取回的持久层。

真源是 pending_proposal 表（migration 162）。不向 store 注入隐藏属性。
进程内 dict 只做短暂快路径。
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

_log = logging.getLogger("scribe3.pending_proposals")
_FAST_SEC = 2.0
_FAST: dict[str, tuple[float, dict[str, Any]]] = {}


def _fast_put(rec: dict[str, Any]) -> None:
    _FAST[str(rec.get("id") or "")] = (time.time(), dict(rec))


def _fast_get(pid: str) -> dict[str, Any] | None:
    hit = _FAST.get(str(pid))
    if not hit:
        return None
    ts, rec = hit
    if time.time() - ts > _FAST_SEC:
        return None
    return dict(rec)


def save_pending_proposal(store: Any, proposal: dict | None) -> dict[str, Any]:
    if store is None:
        raise TypeError("save_pending_proposal 需要 store，execute=false 也必须能按 id 取回")
    rec = dict(proposal or {})
    pid = str(rec.get("id") or uuid.uuid4().hex[:16])
    rec["id"] = pid
    rec["status"] = rec.get("status") or "pending"
    writer = getattr(store, "save_pending_proposal", None)
    if callable(writer):
        writer(pid, rec)
        _fast_put(rec)
        return rec
    exec_w = getattr(store, "_execute_write", None)
    if callable(exec_w):
        exec_w(
            "UPSERT pending_proposal SET pid=$pid, status=$st, payload=$p, "
            "updated_at=time::now()",
            {"pid": pid, "st": rec.get("status"), "p": json.dumps(rec, ensure_ascii=False)},
        )
        _fast_put(rec)
        return rec
    _fast_put(rec)
    _log.warning("pending_proposal 无 DB 写入路径，仅快路径 pid=%s", pid)
    return rec


def get_pending_proposal(store: Any, pid: str) -> dict[str, Any] | None:
    pid = str(pid or "").strip()
    if not pid:
        return None
    cached = _fast_get(pid)
    if cached:
        return cached
    if store is None:
        return None
    getter = getattr(store, "get_pending_proposal", None)
    if callable(getter):
        row = getter(pid)
        if row:
            return row
    q = getattr(store, "_query", None)
    if callable(q):
        try:
            rows = q(
                "SELECT payload, status FROM pending_proposal WHERE pid=$pid LIMIT 1",
                {"pid": pid},
            ) or []
        except Exception as e:
            _log.warning("pending_proposal read fail %s: %s", pid, e)
            rows = []
        if rows:
            raw = rows[0].get("payload") if isinstance(rows[0], dict) else None
            if isinstance(raw, str):
                try:
                    rec = json.loads(raw)
                    if isinstance(rec, dict):
                        _fast_put(rec)
                        return rec
                except Exception:
                    return None
            if isinstance(raw, dict):
                _fast_put(raw)
                return raw
    hit = _FAST.get(pid)
    if hit:
        return dict(hit[1])
    return None


def list_pending_proposals(store: Any) -> list[dict[str, Any]]:
    if store is None:
        return []
    lister = getattr(store, "list_pending_proposals", None)
    if callable(lister):
        try:
            rows = lister() or []
            return [r for r in rows if isinstance(r, dict)]
        except Exception:
            pass
    q = getattr(store, "_query", None)
    if not callable(q):
        return [dict(rec) for _, rec in list(_FAST.values()) if rec.get("status") == "pending"]
    try:
        rows = q(
            "SELECT payload, status FROM pending_proposal WHERE status='pending'"
        ) or []
    except Exception:
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = row.get("payload")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                continue
        if isinstance(raw, dict):
            out.append(raw)
    return out
