"""注入段注册表（影子 / active）— novel-first。

默认 shadow：只产出 density 观测，不改渲染路径。
``SCRIBE3_INJECTION_REGISTRY=1`` 时 write_assemble 仍以
``join_generation_segments`` 为 SSOT；本模块提供声明式元数据与 trace。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def registry_mode() -> str:
    """off | shadow | active。默认 shadow 当 DENSITY_TRACE 开，否则 off。"""
    raw = (os.environ.get("SCRIBE3_INJECTION_REGISTRY") or "").strip().lower()
    if raw in ("1", "true", "yes", "on", "active"):
        return "active"
    if raw in ("0", "false", "off", "no"):
        return "off"
    if raw == "shadow":
        return "shadow"
    # 默认：观测开则 shadow
    dens = (os.environ.get("SCRIBE3_DENSITY_TRACE") or "1").strip().lower()
    if dens in ("0", "false", "off", "no"):
        return "off"
    return "shadow"


@dataclass(frozen=True)
class SegmentMeta:
    name: str
    tier: str  # L0|L1|L2|L3
    zone: str  # head|mid|tail
    epistemic: str  # redline|frame|world|craft|audit


# 与 generation_physical_order_names 对齐的声明表
SEGMENT_REGISTRY: tuple[SegmentMeta, ...] = (
    SegmentMeta("prefix", "L0", "head", "redline"),
    SegmentMeta("event_drive", "L0", "head", "redline"),
    SegmentMeta("drama_contract", "L0", "head", "redline"),
    SegmentMeta("drama_vacuum", "L0", "head", "redline"),
    SegmentMeta("envelope", "L1", "mid", "frame"),
    SegmentMeta("codex", "L2", "mid", "world"),
    SegmentMeta("seed_words", "L3", "mid", "craft"),
    SegmentMeta("craft", "L3", "mid", "craft"),
    SegmentMeta("phase_role", "L3", "mid", "craft"),
    SegmentMeta("avoid", "L3", "mid", "craft"),
    SegmentMeta("revelation_discipline", "L0", "mid", "redline"),
    SegmentMeta("sincerity", "L0", "mid", "redline"),
    SegmentMeta("purpose", "L2", "mid", "frame"),
    SegmentMeta("outline", "L2", "mid", "frame"),
    SegmentMeta("volume_intro", "L3", "mid", "world"),
    SegmentMeta("brief_must", "L2", "mid", "frame"),
    SegmentMeta("pressure_drive", "L2", "mid", "frame"),
    SegmentMeta("author_prefs", "L3", "mid", "craft"),
    SegmentMeta("voice_anchor", "L2", "mid", "frame"),
    SegmentMeta("reference_craft", "L3", "mid", "craft"),
    SegmentMeta("deduction_final", "L0", "mid", "redline"),
    SegmentMeta("material_recall", "L3", "mid", "craft"),
    SegmentMeta("final_reminder", "L0", "tail", "redline"),
    SegmentMeta("scene_truth_proj", "L0", "mid", "redline"),
    SegmentMeta("request_constraint", "L3", "tail", "craft"),
)


def density_trace_for_segments(
    domain_lengths: dict[str, int] | None = None,
    order_indices: dict[str, int] | None = None,
) -> dict[str, Any]:
    """影子密度报告（可挂 envelope_trace）。"""
    lengths = dict(domain_lengths or {})
    by_tier: dict[str, int] = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
    meta = {s.name: s for s in SEGMENT_REGISTRY}
    for name, n in lengths.items():
        tier = meta[name].tier if name in meta else "L3"
        by_tier[tier] = by_tier.get(tier, 0) + int(n)
    total = sum(by_tier.values()) or 1
    return {
        "mode": registry_mode(),
        "by_tier": by_tier,
        "tier_share": {k: round(v / total, 4) for k, v in by_tier.items()},
        "order_indices": dict(order_indices or {}),
        "segment_count": len(lengths),
        "registry_names": [s.name for s in SEGMENT_REGISTRY],
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
    }


def registry_physical_order_names(*, v2: bool = True) -> list[str]:
    """注册表声明序；active 模式可与 context_budget.generation_physical_order_names 对齐校验。"""
    names = [s.name for s in SEGMENT_REGISTRY]
    if not v2:
        return [n for n in names if n != "codex"]
    return list(names)


def active_registry_orders_join() -> bool:
    """active 时 join 前按注册表重排段名（仍走 join_generation_segments SSOT）。"""
    return registry_mode() == "active"
