"""DIR-08/09/11：收件箱项可标已处理，不再堆着。"""
from __future__ import annotations

from typing import Any

_MEM: set[str] = set()


def dismiss_inbox_item(store: Any, item_id: str) -> dict[str, Any]:
    iid = str(item_id or "").strip()
    if not iid:
        return {"ok": False, "code": "missing_id"}
    _MEM.add(iid)
    fn = getattr(store, "dismiss_inbox_item", None)
    if callable(fn):
        try:
            fn(iid)
        except Exception:
            pass
    return {"ok": True, "id": iid, "dismissed": True}


def is_dismissed(store: Any, item_id: str) -> bool:
    iid = str(item_id or "").strip()
    if iid in _MEM:
        return True
    fn = getattr(store, "inbox_item_dismissed", None)
    if callable(fn):
        try:
            return bool(fn(iid))
        except Exception:
            return False
    return False


def filter_inbox(store: Any, items: list[dict] | None) -> list[dict]:
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if is_dismissed(store, str(it.get("id") or "")):
            continue
        out.append(it)
    return out
