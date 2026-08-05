"""进程内经验压力状态(按 work 分桶)。

避免 Surreal 迁移阻塞目标;FakeStore 测试与单进程 demo 足够。
API 与纯函数经此读写 letter 状态/模式/grid/续写确认。
"""
from __future__ import annotations

import threading
from copy import deepcopy
from typing import Any

_lock = threading.Lock()

# work -> revision_mode
_modes: dict[str, str] = {}
# work -> item_id -> {status, author_note}
_letter_items: dict[str, dict[str, dict[str, Any]]] = {}
# work -> seq -> scene_grid dict
_scene_grids: dict[str, dict[int, dict[str, Any]]] = {}
# work -> strict_scene_grid bool
_strict_scene: dict[str, bool] = {}
# work -> require_reread bool
_require_reread: dict[str, bool] = {}
# work -> set of seq that acked reread
_reread_ack: dict[str, set[int]] = {}
# work -> list of seed suggestion dicts
_seeds: dict[str, list[dict[str, Any]]] = {}
# work -> list of external feedback items attached
_feedback: dict[str, list[dict[str, Any]]] = {}


def clear_work(work: str = "main") -> None:
    """测试夹具:清空一书状态。"""
    w = work or "main"
    with _lock:
        _modes.pop(w, None)
        _letter_items.pop(w, None)
        _scene_grids.pop(w, None)
        _strict_scene.pop(w, None)
        _require_reread.pop(w, None)
        _reread_ack.pop(w, None)
        _seeds.pop(w, None)
        _feedback.pop(w, None)


def clear_all() -> None:
    with _lock:
        _modes.clear()
        _letter_items.clear()
        _scene_grids.clear()
        _strict_scene.clear()
        _require_reread.clear()
        _reread_ack.clear()
        _seeds.clear()
        _feedback.clear()


def get_revision_mode(work: str = "main") -> str:
    from scribe3.experience.modes import normalize_revision_mode
    with _lock:
        return normalize_revision_mode(_modes.get(work or "main"))


def set_revision_mode(work: str, mode: str) -> str:
    from scribe3.experience.modes import normalize_revision_mode
    m = normalize_revision_mode(mode)
    with _lock:
        _modes[work or "main"] = m
    return m


def get_letter_overlay(work: str = "main") -> dict[str, dict[str, Any]]:
    with _lock:
        return deepcopy(_letter_items.get(work or "main") or {})


def set_letter_item(work: str, item_id: str, *, status: str,
                    author_note: str = "") -> dict[str, Any]:
    w = work or "main"
    with _lock:
        bucket = _letter_items.setdefault(w, {})
        prev = dict(bucket.get(item_id) or {})
        prev["status"] = status
        if author_note is not None:
            prev["author_note"] = (author_note or "")[:500]
        # 审计:保留历史不删
        hist = list(prev.get("history") or [])
        hist.append({"status": status, "note": prev.get("author_note") or ""})
        prev["history"] = hist[-20:]
        bucket[item_id] = prev
        return deepcopy(prev)


def get_scene_grid(work: str, seq: int) -> dict[str, Any] | None:
    with _lock:
        g = (_scene_grids.get(work or "main") or {}).get(int(seq))
        return deepcopy(g) if g else None


def set_scene_grid(work: str, seq: int, grid: dict[str, Any]) -> dict[str, Any]:
    w = work or "main"
    with _lock:
        bucket = _scene_grids.setdefault(w, {})
        bucket[int(seq)] = dict(grid)
        return deepcopy(bucket[int(seq)])


def get_strict_scene(work: str = "main") -> bool:
    with _lock:
        return bool(_strict_scene.get(work or "main", False))


def set_strict_scene(work: str, on: bool) -> bool:
    with _lock:
        _strict_scene[work or "main"] = bool(on)
        return bool(on)


def get_require_reread(work: str = "main") -> bool:
    with _lock:
        return bool(_require_reread.get(work or "main", False))


def set_require_reread(work: str, on: bool) -> bool:
    with _lock:
        _require_reread[work or "main"] = bool(on)
        return bool(on)


def ack_reread(work: str, seq: int) -> None:
    with _lock:
        _reread_ack.setdefault(work or "main", set()).add(int(seq))


def has_reread_ack(work: str, seq: int) -> bool:
    with _lock:
        return int(seq) in (_reread_ack.get(work or "main") or set())


def clear_reread_ack(work: str, seq: int) -> None:
    with _lock:
        s = _reread_ack.get(work or "main")
        if s:
            s.discard(int(seq))


def set_seeds(work: str, seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with _lock:
        _seeds[work or "main"] = list(seeds)
        return deepcopy(_seeds[work or "main"])


def get_seeds(work: str = "main") -> list[dict[str, Any]]:
    with _lock:
        return deepcopy(_seeds.get(work or "main") or [])


def mark_seed_promoted(work: str, seed_id: str) -> dict[str, Any] | None:
    with _lock:
        rows = _seeds.get(work or "main") or []
        for r in rows:
            if r.get("id") == seed_id:
                r["promoted"] = True
                return deepcopy(r)
    return None


def append_feedback(work: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with _lock:
        bucket = _feedback.setdefault(work or "main", [])
        bucket.extend(items)
        return deepcopy(bucket)


def get_feedback(work: str = "main") -> list[dict[str, Any]]:
    with _lock:
        return deepcopy(_feedback.get(work or "main") or [])
