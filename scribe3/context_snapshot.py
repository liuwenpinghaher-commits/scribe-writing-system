"""DED-07：同一请求里 playbook / 写路径共用一份上下文快照。"""
from __future__ import annotations

import contextvars
from typing import Any, Callable

_cache: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "s3_ctx_snapshot", default=None,
)


def snapshot_get_or_set(key: str, factory: Callable[[], Any]) -> Any:
    bag = _cache.get()
    if bag is None:
        bag = {}
        _cache.set(bag)
    if key not in bag:
        bag[key] = factory()
    return bag[key]


def snapshot_clear() -> None:
    _cache.set({})
