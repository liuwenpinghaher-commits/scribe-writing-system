"""MAN-01：章版本保留策略（纯函数，store 负责真正 DELETE）。"""
from __future__ import annotations

from typing import Any, Iterable

KEEP_KINDS = frozenset({"milestone", "published", "referenced"})
DEFAULT_KEEP_RECENT = 20


def select_versions_to_drop(
    rows: Iterable[dict[str, Any]] | None,
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
    keep_kinds: frozenset[str] = KEEP_KINDS,
) -> list[dict[str, Any]]:
    """rows 按 created_at 新→旧。保留最近 N 条 + 里程碑/引用；其余可删。"""
    items = [r for r in (rows or []) if isinstance(r, dict) and r.get("id")]
    keep_ids: set[Any] = set()
    n = max(0, int(keep_recent))
    for i, r in enumerate(items):
        if i < n:
            keep_ids.add(r["id"])
            continue
        kind = str(r.get("kind") or "")
        if kind in keep_kinds:
            keep_ids.add(r["id"])
    return [r for r in items if r["id"] not in keep_ids]
