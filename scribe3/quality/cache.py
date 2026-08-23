"""质量仪表盘进程内短 TTL 缓存。store 与 router 共用，禁止互相 import。"""
from __future__ import annotations

import time
from typing import Any

_QUALITY_TTL: dict[tuple, tuple[float, dict]] = {}
_QUALITY_TTL_SEC = 2.0


def invalidate_quality_cache(work: str | None = None) -> None:
    """save_chapter 成功后清本 Worker 质量仪表盘缓存，避免立刻读到旧值。"""
    if work is None:
        _QUALITY_TTL.clear()
        return
    for key in list(_QUALITY_TTL):
        if key[0] == work:
            _QUALITY_TTL.pop(key, None)


def quality_cache_get(stamp: tuple) -> dict | None:
    hit = _QUALITY_TTL.get(stamp)
    if not hit:
        return None
    ts, payload = hit
    if time.monotonic() - ts >= _QUALITY_TTL_SEC:
        return None
    return payload


def quality_cache_put(stamp: tuple, payload: dict[str, Any]) -> None:
    _QUALITY_TTL[stamp] = (time.monotonic(), payload)
