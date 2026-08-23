"""DIR-08/09/11 / N-05：收件箱项可标已处理。

真源是 inbox_dismissed 表。进程内 set 只服务本请求快路径，请求结束即丢。
"""
from __future__ import annotations

import contextvars
import logging
from typing import Any

_log = logging.getLogger("scribe3.inbox_dismiss")
_req: contextvars.ContextVar[set[str] | None] = contextvars.ContextVar(
    "s3_inbox_dismissed", default=None,
)


def _bag() -> set[str]:
    s = _req.get()
    if s is None:
        s = set()
        _req.set(s)
    return s


def _db_dismiss(store: Any, iid: str) -> None:
    fn = getattr(store, "dismiss_inbox_item", None)
    if callable(fn):
        try:
            fn(iid)
            return
        except Exception as e:
            _log.warning("store.dismiss_inbox_item fail %s: %s", iid, e)
    writer = getattr(store, "_execute_write", None)
    if callable(writer):
        try:
            writer(
                "UPSERT type::record('inbox_dismissed', $id) SET "
                "item_id=$id, dismissed=true, updated_at=time::now()",
                {"id": iid},
            )
        except Exception as e:
            _log.warning("inbox_dismissed write fail %s: %s", iid, e)


def _db_is_dismissed(store: Any, iid: str) -> bool:
    fn = getattr(store, "inbox_item_dismissed", None)
    if callable(fn):
        try:
            return bool(fn(iid))
        except Exception:
            return False
    getter = getattr(store, "_query", None)
    if not callable(getter):
        return False
    try:
        rows = getter(
            "SELECT item_id FROM type::record('inbox_dismissed', $id) "
            "WHERE dismissed=true LIMIT 1",
            {"id": iid},
        ) or []
        if rows:
            return True
        rows = getter(
            "SELECT item_id FROM inbox_dismissed WHERE item_id=$id LIMIT 1",
            {"id": iid},
        ) or []
        return bool(rows)
    except Exception:
        return False


def _db_dismissed_set(store: Any) -> set[str]:
    getter = getattr(store, "_query", None)
    if not callable(getter):
        return set()
    try:
        rows = getter("SELECT item_id FROM inbox_dismissed") or []
    except Exception:
        return set()
    out: set[str] = set()
    for r in rows:
        if isinstance(r, dict) and r.get("item_id"):
            out.add(str(r["item_id"]))
        elif isinstance(r, str):
            out.add(r)
    return out


def dismiss_inbox_item(store: Any, item_id: str) -> dict[str, Any]:
    iid = str(item_id or "").strip()
    if not iid:
        return {"ok": False, "code": "missing_id"}
    _bag().add(iid)
    if store is not None:
        _db_dismiss(store, iid)
    return {"ok": True, "id": iid, "dismissed": True}


def is_dismissed(store: Any, item_id: str) -> bool:
    iid = str(item_id or "").strip()
    if not iid:
        return False
    if iid in _bag():
        return True
    if store is None:
        return False
    return _db_is_dismissed(store, iid)


def filter_inbox(store: Any, items: list[dict] | None) -> list[dict]:
    dismissed = set(_bag())
    if store is not None:
        dismissed |= _db_dismissed_set(store)
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if str(it.get("id") or "") in dismissed:
            continue
        if is_dismissed(store, str(it.get("id") or "")):
            continue
        out.append(it)
    return out
