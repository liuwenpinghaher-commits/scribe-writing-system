"""经验压力状态 · RAM 缓存 + settings SQLite 持久化(按 work)。

键: experience_pressure:{work} → JSON blob
字段: mode, letter_items, scene_grids, strict_scene, require_reread,
      reread_ack (list[int]), seeds, feedback

clear_ram() 仅清内存以测「重启」; clear_work/clear_all 默认同清磁盘。
"""
from __future__ import annotations

import json
import threading
from copy import deepcopy
from typing import Any

_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _settings_key(work: str) -> str:
    return f"experience_pressure:{work or 'main'}"


def _empty_blob() -> dict[str, Any]:
    return {
        "mode": "full",
        "letter_items": {},
        "scene_grids": {},  # str(seq) -> grid
        "strict_scene": False,
        "require_reread": False,
        "reread_ack": [],
        "seeds": [],
        "feedback": [],
    }


def _load_disk(work: str) -> dict[str, Any]:
    try:
        from scribe3 import settings_store
        raw = settings_store.get_override(_settings_key(work))
        if not raw:
            return _empty_blob()
        data = json.loads(raw)
        if not isinstance(data, dict):
            return _empty_blob()
        base = _empty_blob()
        base.update(data)
        # normalize types
        if not isinstance(base.get("letter_items"), dict):
            base["letter_items"] = {}
        if not isinstance(base.get("scene_grids"), dict):
            base["scene_grids"] = {}
        if not isinstance(base.get("reread_ack"), list):
            base["reread_ack"] = []
        if not isinstance(base.get("seeds"), list):
            base["seeds"] = []
        if not isinstance(base.get("feedback"), list):
            base["feedback"] = []
        return base
    except Exception:
        return _empty_blob()


def _save_disk(work: str, blob: dict[str, Any]) -> None:
    from scribe3 import settings_store
    settings_store.set_override(
        _settings_key(work),
        json.dumps(blob, ensure_ascii=False),
    )


def _blob(work: str) -> dict[str, Any]:
    w = work or "main"
    if w not in _cache:
        _cache[w] = _load_disk(w)
    return _cache[w]


def _touch(work: str) -> dict[str, Any]:
    """返回可写 blob 并在调用方改完后 _commit。"""
    return _blob(work or "main")


def _commit(work: str) -> None:
    w = work or "main"
    if w in _cache:
        _save_disk(w, _cache[w])


def clear_ram() -> None:
    """仅清 RAM(模拟进程重启);磁盘保留。"""
    with _lock:
        _cache.clear()


def clear_work(work: str = "main", *, disk: bool = True) -> None:
    w = work or "main"
    with _lock:
        _cache.pop(w, None)
        if disk:
            try:
                from scribe3 import settings_store
                settings_store.delete_override(_settings_key(w))
            except Exception:
                pass


def clear_all(*, disk: bool = True) -> None:
    with _lock:
        works = list(_cache.keys())
        _cache.clear()
        if disk:
            try:
                from scribe3 import settings_store
                for w in works:
                    try:
                        settings_store.delete_override(_settings_key(w))
                    except Exception:
                        pass
            except Exception:
                pass


def get_revision_mode(work: str = "main") -> str:
    from scribe3.experience.modes import normalize_revision_mode
    with _lock:
        return normalize_revision_mode(_blob(work).get("mode"))


def set_revision_mode(work: str, mode: str) -> str:
    from scribe3.experience.modes import normalize_revision_mode
    m = normalize_revision_mode(mode)
    with _lock:
        b = _touch(work)
        b["mode"] = m
        _commit(work)
    return m


def get_letter_overlay(work: str = "main") -> dict[str, dict[str, Any]]:
    with _lock:
        return deepcopy(_blob(work).get("letter_items") or {})


def set_letter_item(work: str, item_id: str, *, status: str,
                    author_note: str = "") -> dict[str, Any]:
    w = work or "main"
    with _lock:
        b = _touch(w)
        bucket = b.setdefault("letter_items", {})
        prev = dict(bucket.get(item_id) or {})
        prev["status"] = status
        if author_note is not None:
            prev["author_note"] = (author_note or "")[:500]
        hist = list(prev.get("history") or [])
        hist.append({"status": status, "note": prev.get("author_note") or ""})
        prev["history"] = hist[-20:]
        bucket[item_id] = prev
        _commit(w)
        return deepcopy(prev)


def get_scene_grid(work: str, seq: int) -> dict[str, Any] | None:
    with _lock:
        g = (_blob(work).get("scene_grids") or {}).get(str(int(seq)))
        return deepcopy(g) if g else None


def set_scene_grid(work: str, seq: int, grid: dict[str, Any]) -> dict[str, Any]:
    w = work or "main"
    with _lock:
        b = _touch(w)
        grids = b.setdefault("scene_grids", {})
        grids[str(int(seq))] = dict(grid)
        _commit(w)
        return deepcopy(grids[str(int(seq))])


def get_strict_scene(work: str = "main") -> bool:
    with _lock:
        return bool(_blob(work).get("strict_scene", False))


def set_strict_scene(work: str, on: bool) -> bool:
    with _lock:
        b = _touch(work)
        b["strict_scene"] = bool(on)
        _commit(work)
        return bool(on)


def get_require_reread(work: str = "main") -> bool:
    with _lock:
        return bool(_blob(work).get("require_reread", False))


def set_require_reread(work: str, on: bool) -> bool:
    with _lock:
        b = _touch(work)
        b["require_reread"] = bool(on)
        _commit(work)
        return bool(on)


def ack_reread(work: str, seq: int) -> None:
    with _lock:
        b = _touch(work)
        ack = set(int(x) for x in (b.get("reread_ack") or []))
        ack.add(int(seq))
        b["reread_ack"] = sorted(ack)
        _commit(work)


def has_reread_ack(work: str, seq: int) -> bool:
    with _lock:
        return int(seq) in set(int(x) for x in (_blob(work).get("reread_ack") or []))


def clear_reread_ack(work: str, seq: int) -> None:
    with _lock:
        b = _touch(work)
        ack = set(int(x) for x in (b.get("reread_ack") or []))
        ack.discard(int(seq))
        b["reread_ack"] = sorted(ack)
        _commit(work)


def set_seeds(work: str, seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with _lock:
        b = _touch(work)
        b["seeds"] = list(seeds)
        _commit(work)
        return deepcopy(b["seeds"])


def get_seeds(work: str = "main") -> list[dict[str, Any]]:
    with _lock:
        return deepcopy(_blob(work).get("seeds") or [])


def mark_seed_promoted(work: str, seed_id: str) -> dict[str, Any] | None:
    with _lock:
        b = _touch(work)
        rows = b.get("seeds") or []
        for r in rows:
            if r.get("id") == seed_id:
                r["promoted"] = True
                _commit(work)
                return deepcopy(r)
    return None


def append_feedback(work: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with _lock:
        b = _touch(work)
        bucket = b.setdefault("feedback", [])
        bucket.extend(items)
        _commit(work)
        return deepcopy(bucket)


def get_feedback(work: str = "main") -> list[dict[str, Any]]:
    with _lock:
        return deepcopy(_blob(work).get("feedback") or [])
