"""WorkPackage 持久化 · settings_store 按 work 隔离。"""
from __future__ import annotations

import json
import threading
from copy import deepcopy
from typing import Any

_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _key(work: str) -> str:
    return f"orch_work_package:{(work or 'main')}"


def _load(work: str) -> dict[str, Any]:
    w = work or "main"
    if w in _cache:
        return _cache[w]
    blob: dict[str, Any] = {"active": None, "queue": []}
    try:
        from scribe3 import settings_store
        raw = settings_store.get_override(_key(w))
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict):
                blob.update(data)
    except Exception:
        pass
    _cache[w] = blob
    return blob


def _save(work: str) -> None:
    w = work or "main"
    blob = _cache.get(w) or {"active": None, "queue": []}
    try:
        from scribe3 import settings_store
        settings_store.set_override(_key(w), json.dumps(blob, ensure_ascii=False))
    except Exception:
        pass


def get_active(work: str = "main") -> dict[str, Any] | None:
    with _lock:
        a = _load(work).get("active")
        return deepcopy(a) if a else None


def set_active(work: str, package: dict[str, Any] | None) -> dict[str, Any] | None:
    with _lock:
        blob = _load(work)
        blob["active"] = deepcopy(package) if package else None
        _save(work)
        return deepcopy(blob["active"])


def clear_ram() -> None:
    with _lock:
        _cache.clear()


def clear_work(work: str = "main", *, disk: bool = True) -> None:
    w = work or "main"
    with _lock:
        _cache.pop(w, None)
        if disk:
            try:
                from scribe3 import settings_store
                settings_store.delete_override(_key(w))
            except Exception:
                pass
