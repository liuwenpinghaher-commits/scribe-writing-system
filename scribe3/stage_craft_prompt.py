"""R8 W10: assemble 只注入 StageSpec 短核；完整生成合同在 stage_generate。"""
from __future__ import annotations

from scribe3.stage_generate import normalize_stage, stage_craft_kernel

# draft/final 不灌写法圣经（R8）；只给 outline/beats/deduce 短核。
_ASSEMBLE_STAGES = frozenset({"outline", "plan", "beats", "deduce"})


def stage_craft_block(phase: str) -> str:
    p = normalize_stage(phase)
    if p not in _ASSEMBLE_STAGES and (phase or "").strip().lower() not in _ASSEMBLE_STAGES:
        return ""
    return stage_craft_kernel(phase)[:400]
