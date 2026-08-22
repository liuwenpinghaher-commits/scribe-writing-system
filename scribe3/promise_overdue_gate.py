"""PRM-01：超期伏笔达到阈值时硬闸，阻止写新章 / 存定稿 / 对话写。"""
from __future__ import annotations

from typing import Any

OVERDUE_HARD_THRESHOLD = 3


def count_open_overdue(
    promises: list[dict] | None,
    max_chapter: int,
    slack: int | None = None,
) -> int:
    from scribe3.store.core_preamble import OVERDUE_SLACK, _overdue_flag

    n_slack = OVERDUE_SLACK if slack is None else int(slack)
    n = 0
    for p in promises or []:
        if not isinstance(p, dict):
            continue
        if _overdue_flag(p, int(max_chapter or 0), n_slack):
            n += 1
    return n


def overdue_hard_block(
    overdue_count: int,
    threshold: int = OVERDUE_HARD_THRESHOLD,
) -> dict[str, Any] | None:
    """count>=threshold 返回阻断 dict；否则 None。"""
    n = int(overdue_count or 0)
    t = int(threshold)
    if n < t:
        return None
    return {
        "allowed": False,
        "ok": False,
        "code": "promise_overdue",
        "blocking": True,
        "overdue_count": n,
        "threshold": t,
        "detail": f"超期伏笔 {n} 条（≥{t}），先兑现再写新章",
        "message": f"超期伏笔 {n} 条（≥{t}），先兑现再写新章",
    }


def check_overdue_hard(store: Any, *, threshold: int = OVERDUE_HARD_THRESHOLD) -> dict[str, Any] | None:
    """读 store 的 open 伏笔；查询失败 fail-open（不砖写作）。"""
    if store is None:
        return None
    try:
        lister = getattr(store, "open_promises", None) or getattr(store, "list_promises", None)
        rows = lister() if callable(lister) else []
        max_ch = 0
        mx = getattr(store, "max_chapter", None)
        if callable(mx):
            max_ch = int(mx() or 0)
        slack = None
        getter = getattr(store, "get_intent", None)
        if callable(getter):
            intent = getter() or {}
            if isinstance(intent, dict) and intent.get("overdue_threshold") is not None:
                slack = int(intent["overdue_threshold"])
        n = count_open_overdue(rows, max_ch, slack)
        return overdue_hard_block(n, threshold)
    except Exception:
        return None
