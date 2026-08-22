"""DED-06：章纲为空时禁止无约束生成责任卡。"""
from __future__ import annotations

from typing import Any


def refuse_empty_synopsis(
    ctx: dict[str, Any] | None,
    store: Any = None,
    seq: int | None = None,
) -> dict[str, Any] | None:
    """synopsis 空则返回 {ok:False}；有章纲返回 None（放行）。"""
    data = ctx if isinstance(ctx, dict) else {}
    syn = str(data.get("synopsis") or "").strip()
    if not syn and store is not None:
        n = seq if seq is not None else data.get("seq")
        getter = getattr(store, "get_chapter", None)
        if callable(getter) and n is not None:
            try:
                ch = getter(int(n)) or {}
            except Exception:
                ch = {}
            if isinstance(ch, dict):
                syn = str(ch.get("synopsis") or "").strip()
    if syn:
        return None
    return {
        "ok": False,
        "code": "empty_synopsis",
        "message": "本章还没有章纲，不能无约束生成",
    }
