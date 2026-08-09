"""世界真相 / 命题树投影辅助（Must · PR-UX1）。

引擎表名仍为 proposition；作者可见「世界真相」。
bridge 只认 source==codex_bridge，禁止 attribute 启发式。
见 docs/plans/2026-08-09-proposition-author-ux-v2-optimization.md · KD-17。
"""
from __future__ import annotations

from typing import Any

# ingest 合成的噪音属性（Must 树默认隐藏）
NOISE_ATTRS: frozenset[str] = frozenset({"获知", "行动", "from_knowledge"})

BRIDGE_SOURCE = "codex_bridge"

# 作者可见分类名
WORLD_TRUTH_LABEL = "世界真相"
WORLD_TRUTH_HINT = "全库时态账本 · 日常请打开角色卡"


def tree_hide_must(
    attribute: str,
    source: str | None = None,
    *,
    show_engine: bool = False,
) -> bool:
    """Must 树投影隐藏谓词。True = 应从默认树中隐藏。

    - bridge 只认 source==codex_bridge（禁止 attribute 猜测）
    - 属性噪音：获知 / 行动 / from_knowledge
    """
    if show_engine:
        return False
    src = (source or "").strip() or None
    if src == BRIDGE_SOURCE:
        return True
    return (attribute or "").strip() in NOISE_ATTRS


def format_fact_as_codex_title(
    entity_id: str,
    attribute: str,
    value: str | None = None,
    *,
    secret: bool = False,
    max_value: int = 24,
) -> str:
    """设定树叶标题：实体本地名 · 属性（可选截断值；私密不露值）。"""
    ent = (entity_id or "").split(":", 1)[-1] or "—"
    attr = (attribute or "").strip() or "—"
    if secret:
        return f"{ent}·{attr}"
    val = (value or "").strip()
    if not val:
        return f"{ent}·{attr}"
    if len(val) > max_value:
        val = val[: max_value - 1] + "…"
    return f"{ent}·{attr} = {val}"


def row_source(row: Any) -> str | None:
    if isinstance(row, dict):
        s = row.get("source")
    else:
        s = getattr(row, "source", None)
    if s is None:
        return None
    t = str(s).strip()
    return t or None
