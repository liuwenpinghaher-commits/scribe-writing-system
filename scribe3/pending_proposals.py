"""DIR-01：execute=false 的提案落到可按 id 取回的持久层。

真源是 store（方法或 pending_proposal 表 / store._pending_proposals），
不是进程内备忘。"""
from __future__ import annotations

import json
import uuid
from typing import Any


def _bucket(store: Any) -> dict[str, dict[str, Any]]:
    bucket = getattr(store, "_pending_proposals", None)
    if not isinstance(bucket, dict):
        bucket = {}
        try:
            store._pending_proposals = bucket
        except Exception:
            pass
    return bucket if isinstance(getattr(store, "_pending_proposals", None), dict) else bucket


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
        return rec
    if hasattr(store, "_execute_write"):
        store._execute_write(
            "UPSERT pending_proposal SET pid=$pid, status=$st, payload=$p, "
            "updated_at=time::now()",
            {"pid": pid, "st": rec.get("status"), "p": json.dumps(rec, ensure_ascii=False)},
        )
        _bucket(store)[pid] = rec
        return rec
    _bucket(store)[pid] = rec
    return rec


def get_pending_proposal(store: Any, pid: str) -> dict[str, Any] | None:
    pid = str(pid or "").strip()
    if not pid:
        return None
    if store is None:
        return None
    getter = getattr(store, "get_pending_proposal", None)
    if callable(getter):
        row = getter(pid)
        if row:
            return row
    bucket = getattr(store, "_pending_proposals", None)
    if isinstance(bucket, dict) and pid in bucket:
        return dict(bucket[pid])
    if hasattr(store, "_query"):
        rows = store._query(
            "SELECT payload, status FROM pending_proposal WHERE pid=$pid LIMIT 1",
            {"pid": pid}) or []
        if rows:
            raw = rows[0].get("payload")
            if isinstance(raw, str):
                return json.loads(raw)
            if isinstance(raw, dict):
                return raw
    return None
