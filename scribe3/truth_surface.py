"""世界真相 / 命题树与读路径投影（PR-UX1 + PR-4）。

引擎表名仍为 proposition；作者可见「世界真相」。
bucket 分类与树过滤同一真相源（rev.3 classify_bucket）。
见 docs/plans/2026-08-09-proposition-full-chain-optimization.md · PR-4。
"""
from __future__ import annotations

from typing import Any

# ingest 合成的噪音属性（仅 source 为空时启发式进 ingest_noise）
NOISE_ATTRS: frozenset[str] = frozenset({"获知", "行动", "from_knowledge"})

# 状态槽 → bucket=state
STATE_ATTRS: frozenset[str] = frozenset({
    "state", "condition", "status", "外观状态", "状态",
})

BRIDGE_SOURCE = "codex_bridge"
INGEST_SOURCE = "ingest"

# 树/高级浏览器默认隐藏的 bucket
TREE_HIDE_BUCKETS: frozenset[str] = frozenset({"bridge", "ingest_noise"})

# 作者可见分类名
WORLD_TRUTH_LABEL = "世界真相"
WORLD_TRUTH_HINT = "全库时态账本 · 日常请打开角色卡"


def classify_bucket(
    source: str | None,
    attribute: str,
    *,
    is_secret: bool = False,
) -> str:
    """命题展示分桶（单一真相源 · PR-4）。is_secret 不抢 bucket，UI 另读角标。

    | source | attribute | bucket |
    | codex_bridge | * | bridge |
    | ingest | * | ingest_noise |
    | null + 获知/行动/from_knowledge | ingest_noise |
    | author/canon/其它非空 | 获知 | author（不藏） |
    | null + state 槽 | state |
    | 其余 | author |
    """
    del is_secret  # 角标另读，不参与分桶
    src = (source or "").strip() or None
    attr = (attribute or "").strip()
    if src == BRIDGE_SOURCE:
        return "bridge"
    if src == INGEST_SOURCE:
        return "ingest_noise"
    # 兼容旧行：仅 source 为空时用 attribute 启发式
    if src is None and attr in NOISE_ATTRS:
        return "ingest_noise"
    if src == "canon":
        return "author"
    if attr in STATE_ATTRS:
        return "state"
    return "author"


def tree_hide_must(
    attribute: str,
    source: str | None = None,
    *,
    show_engine: bool = False,
) -> bool:
    """树投影隐藏谓词（PR-UX1b 起走 classify_bucket）。

    True = 应从默认树中隐藏。bridge 只认 source==codex_bridge。
    手写 source=author 且 attribute=获知 → **不**藏（与 Must 属性滤粗路径不同）。
    """
    if show_engine:
        return False
    return classify_bucket(source, attribute) in TREE_HIDE_BUCKETS


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
