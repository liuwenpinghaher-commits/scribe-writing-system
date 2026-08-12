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
    """off | shadow | active。默认 active（质量优先参与 join）。"""
    raw = (os.environ.get("SCRIBE3_INJECTION_REGISTRY")
           if "SCRIBE3_INJECTION_REGISTRY" in os.environ
           else "active").strip().lower()
    if raw in ("1", "true", "yes", "on", "active"):
        return "active"
    if raw in ("0", "false", "off", "no"):
        return "off"
    if raw == "shadow":
        return "shadow"
    if raw == "":
        return "active"
    dens = (os.environ.get("SCRIBE3_DENSITY_TRACE") or "1").strip().lower()
    if dens in ("0", "false", "off", "no"):
        return "off"
    return "active"


@dataclass(frozen=True)
class SegmentMeta:
    name: str
    tier: str  # L0|L1|L2|L3
    zone: str  # head|mid|tail
    epistemic: str  # redline|frame|world|craft|audit


# 与 generation_physical_order_names 对齐的声明表
# outline → SEGMENT_L1，默认物理序在 drama_vacuum 后、envelope 前（U4）
SEGMENT_REGISTRY: tuple[SegmentMeta, ...] = (
    SegmentMeta("prefix", "L0", "head", "redline"),
    SegmentMeta("structure_diversity", "L0", "head", "redline"),
    SegmentMeta("event_drive", "L0", "head", "redline"),
    SegmentMeta("drama_contract", "L0", "head", "redline"),
    SegmentMeta("drama_vacuum", "L0", "head", "redline"),
    SegmentMeta("outline", "L1", "head", "frame"),  # SEGMENT_L1 · 高注意力
    SegmentMeta("envelope", "L1", "mid", "frame"),
    SegmentMeta("codex", "L2", "mid", "world"),
    SegmentMeta("seed_words", "L3", "mid", "craft"),
    SegmentMeta("craft", "L3", "mid", "craft"),
    SegmentMeta("phase_role", "L3", "mid", "craft"),
    SegmentMeta("avoid", "L3", "mid", "craft"),
    SegmentMeta("revelation_discipline", "L0", "mid", "redline"),
    SegmentMeta("sincerity", "L0", "mid", "redline"),
    SegmentMeta("purpose", "L2", "mid", "frame"),
    SegmentMeta("volume_intro", "L3", "mid", "world"),
    SegmentMeta("brief_must", "L2", "mid", "frame"),
    SegmentMeta("pressure_drive", "L2", "mid", "frame"),
    SegmentMeta("author_prefs", "L3", "mid", "craft"),
    SegmentMeta("voice_anchor", "L2", "mid", "frame"),
    SegmentMeta("reference_craft", "L3", "mid", "craft"),
    SegmentMeta("storyline_polish", "L3", "mid", "craft"),  # SL2 · 故事线 polish
    SegmentMeta("deduction_final", "L0", "mid", "redline"),
    SegmentMeta("material_recall", "L3", "mid", "craft"),
    SegmentMeta("final_reminder", "L0", "tail", "redline"),
    SegmentMeta("scene_truth_proj", "L0", "mid", "redline"),
    SegmentMeta("request_constraint", "L3", "tail", "craft"),
)

# 次杠杆：审计/元数据段（不含 envelope 整包）
META_SEGMENT_NAMES: frozenset[str] = frozenset({
    "phase_role", "avoid", "material_recall", "seed_words", "volume_intro",
})
DRAMA_CORE_NAMES: frozenset[str] = frozenset({
    "event_drive", "drama_contract", "drama_vacuum", "outline", "brief_must",
})


def density_trace_for_segments(
    domain_lengths: dict[str, int] | None = None,
    order_indices: dict[str, int] | None = None,
    *,
    envelope_block_lengths: dict[str, int] | None = None,
    provenance_trace_items: int | None = None,
    provenance_in_prompt_chars: int | None = None,
) -> dict[str, Any]:
    """密度报告：G1(a) provenance_in_prompt_tokens 硬字段 + G1(b) audit_meta_share。

    - ``provenance_in_prompt_chars``：最终进生成 joined 的溯源字符；Assembler omit 后必须为 0。
    - ``envelope_block_lengths``：八块各自渲染长度（含改前溯源，供相对基线）；omit 后
      provenance 键应为 0。
    - ``provenance_trace_items``：trace/manifest 条数，可与 in_prompt 解耦。
    """
    lengths = dict(domain_lengths or {})
    env = dict(envelope_block_lengths or {})
    by_tier: dict[str, int] = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
    meta_reg = {s.name: s for s in SEGMENT_REGISTRY}
    for name, n in lengths.items():
        tier = meta_reg[name].tier if name in meta_reg else "L3"
        by_tier[tier] = by_tier.get(tier, 0) + int(n)
    total = sum(lengths.values()) or 1
    # G1(a)：进 prompt 的溯源；默认取 env/lengths 中 provenance，显式参数优先
    if provenance_in_prompt_chars is not None:
        prov_in = max(0, int(provenance_in_prompt_chars))
    else:
        prov_in = int(
            env.get("provenance", 0)
            or lengths.get("provenance", 0)
            or 0
        )
    meta_seg = sum(int(lengths.get(n, 0) or 0) for n in META_SEGMENT_NAMES)
    meta_total = meta_seg + prov_in
    drama_core = sum(int(lengths.get(n, 0) or 0) for n in DRAMA_CORE_NAMES)
    env_canon = int(env.get("canonical", 0) or 0)
    env_recent = int(env.get("recent", 0) or 0)
    audit_meta_share = round(meta_total / total, 4)
    return {
        "mode": registry_mode(),
        "by_tier": by_tier,
        "tier_share": {k: round(v / total, 4) for k, v in by_tier.items()},
        "order_indices": dict(order_indices or {}),
        "segment_count": len(lengths),
        "registry_names": [s.name for s in SEGMENT_REGISTRY],
        # G1(a) 硬验收
        "provenance_in_prompt": prov_in > 0,
        "provenance_in_prompt_tokens": prov_in,
        "provenance_trace_items": (
            int(provenance_trace_items)
            if provenance_trace_items is not None
            else 0
        ),
        # G1(b)
        "audit_meta_share": audit_meta_share,
        "audit_share": audit_meta_share,  # 别名
        "meta_segments_share": round(meta_seg / total, 4),
        "drama_core_share": round(drama_core / total, 4),
        "envelope_canon_share": round(env_canon / total, 4),
        "envelope_recent_share": round(env_recent / total, 4),
        "drama_plus_canon_recent_share": round(
            (drama_core + env_canon + env_recent) / total, 4
        ),
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
    }


def registry_physical_order_names(*, v2: bool = True) -> list[str]:
    """注册表声明序；active 时作为 ordered_generation_segments 的 order_names。

    优先与 ``generation_physical_order_names`` 对齐（含 outline-after-drama 旗），
    再补上注册表独有段名。
    """
    try:
        from scribe3.context_budget import generation_physical_order_names
        base = generation_physical_order_names(v2=v2)
    except Exception:
        base = [s.name for s in SEGMENT_REGISTRY]
        if not v2:
            base = [n for n in base if n != "codex"]
        return base
    reg = [s.name for s in SEGMENT_REGISTRY]
    if not v2:
        reg = [n for n in reg if n != "codex"]
        base = [n for n in base if n != "codex"]
    seen = set(base)
    extra = [n for n in reg if n not in seen]
    return list(base) + extra


def registry_l3_names() -> frozenset[str]:
    """L3 段名：active 时 join 标 supplemental 优先裁。"""
    return frozenset(s.name for s in SEGMENT_REGISTRY if s.tier == "L3")


def active_registry_orders_join() -> bool:
    """active 时 join 用注册表序 + L3 预算策略（非 no-op）。"""
    return registry_mode() == "active"
