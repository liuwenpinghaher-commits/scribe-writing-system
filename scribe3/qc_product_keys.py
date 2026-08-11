"""产品 QC 计数 SSOT（章卡 / outline / post_check / scorecard 合计面）。

与 ``quality_flags`` 返回的 list 类键对齐；**排除** rhythm/adverb（dict|None 形态）。
扩维后须同步 ``QUALITY_CACHE_REVISION``（见 store.core_preamble）。
"""
from __future__ import annotations

from typing import Any, Mapping

# 章卡合计与 breakdown 产品键（顺序稳定 · UI 可依赖）
PRODUCT_QC_LIST_KEYS: tuple[str, ...] = (
    "repetition",
    "structural",
    "purple",
    "ai_tics",
    "oversaturation",
    "god_view",
    "degeneration",
    "filler",
    "rule_of_three",  # 用户决议：计入章卡合计
)

# 历史五类（兼容旧测试 / 文档对照，勿再用于新产品合计）
LEGACY_QC_FIVE_KEYS: tuple[str, ...] = (
    "repetition",
    "structural",
    "purple",
    "ai_tics",
    "oversaturation",
)


def product_qc_breakdown_from_flags(qf: Mapping[str, Any] | None) -> dict[str, int]:
    """从 quality_flags 结果取产品 breakdown（仅 list 键 · 长度）。"""
    src = qf or {}
    out: dict[str, int] = {}
    for k in PRODUCT_QC_LIST_KEYS:
        v = src.get(k)
        if isinstance(v, list):
            out[k] = len(v)
        else:
            out[k] = 0
    return out


def product_qc_total(breakdown: Mapping[str, Any] | None) -> int:
    """产品合计 = PRODUCT_QC_LIST_KEYS 之和（忽略未知键）。"""
    bd = breakdown or {}
    return int(sum(int(bd.get(k) or 0) for k in PRODUCT_QC_LIST_KEYS))


def project_product_qc_breakdown(raw: Mapping[str, Any] | None) -> dict[str, int]:
    """读路径投影：保证全键存在；未知旧键忽略。"""
    raw = raw or {}
    return {k: int(raw.get(k) or 0) for k in PRODUCT_QC_LIST_KEYS}
