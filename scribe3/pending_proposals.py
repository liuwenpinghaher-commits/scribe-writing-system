"""DIR-01：execute=false 的提案落到可按 id 取回的持久层。"""
from __future__ import annotations

import json
import uuid
from typing import Any

_MEM: dict[str, dict[str, Any]] = {}


def save_pending_proposal(store: Any, proposal: dict | None) -> dict[str, Any]:
    rec = dict(proposal or {})
    pid = str(rec.get("id") or uuid.uuid4().hex[:16])
    rec["id"] = pid
    rec["status"] = rec.get("status") or "pending"
    _MEM[pid] = rec
    writer = getattr(store, "save_pending_proposal", None)
    if callable(writer):
        try:
            writer(pid, rec)
        except Exception:
            pass
    elif store is not None and hasattr(store, "_execute_write"):
        try:
            store._execute_write(
                "CREATE pending_proposal SET pid=$pid, status=$st, payload=$p, "
                "updated_at=time::now()",
                {"pid": pid, "st": rec.get("status"), "p": json.dumps(rec, ensure_ascii=False)},
            )
        except Exception:
            pass
    return rec


def get_pending_proposal(store: Any, pid: str) -> dict[str, Any] | None:
    pid = str(pid or "").strip()
    if not pid:
        return None
    if pid in _MEM:
        return dict(_MEM[pid])
    getter = getattr(store, "get_pending_proposal", None)
    if callable(getter):
        try:
            row = getter(pid)
            if row:
                return row
        except Exception:
            return None
    if store is not None and hasattr(store, "_query"):
        try:
            rows = store._query(
                "SELECT payload, status FROM pending_proposal WHERE pid=$pid LIMIT 1",
                {"pid": pid}) or []
            if rows:
                raw = rows[0].get("payload")
                if isinstance(raw, str):
                    return json.loads(raw)
                if isinstance(raw, dict):
                    return raw
        except Exception:
            return None
    return None
