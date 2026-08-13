"""Pipeline Trace 步骤目录：稳定 step_key + 中文名 + 层 + 父子规则。零 I/O。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from scribe3.injection_registry import SEGMENT_REGISTRY

SCHEMA_VER = "pipeline_trace.v1"

SEG_TITLES: dict[str, str] = {
    "identity": "身份",
    "write_protocol": "写协议",
    "prefix": "身份前缀",
    "revision": "改稿",
    "structure_diversity": "结构多样性",
    "continue_snapshot": "续写快照",
    "secret_guard": "密语守卫",
    "focalizer": "限知视角",
    "narrative_contract": "场面合同",
    "story_ember": "上章余烬",
    "story_recall": "世界此刻",
    "story_causal": "前因后果",
    "event_drive": "事件驱动",
    "event_drive_hook": "事件钩",
    "drama_contract": "戏剧合同",
    "drama_vacuum": "戏剧真空",
    "outline": "大纲",
    "envelope": "信封",
    "codex": "正典",
    "seed_words": "种子词",
    "craft": "工艺",
    "phase_role": "阶段角色",
    "avoid": "避忌",
    "revelation_discipline": "揭示纪律",
    "sincerity": "诚意",
    "purpose": "本章目的",
    "volume_intro": "卷首",
    "brief_must": "必须发生",
    "pressure_drive": "压力驱动",
    "author_prefs": "作者偏好",
    "voice_anchor": "声口锚",
    "reference_craft": "参考工艺",
    "storyline_polish": "故事线打磨",
    "discourse_soft": "话语讲法",
    "story_move": "招式",
    "deduction_final": "终稿推演",
    "material_recall": "素材召回",
    "final_reminder": "收束提醒",
    "scene_truth_proj": "场面真相",
    "request_constraint": "本轮约束",
    "tool_scope": "工具范围",
    "craft_skills_index": "技法索引",
    "benchmark_advisory": "标杆提示",
}

SEG_SOURCE: dict[str, str] = {
    "identity": "_editor_identity_block()",
    "write_protocol": "_protocol_raw − final_reminder echo",
    "prefix": "anti_slop + 章号",
    "revision": "改稿判定 + 原文",
    "structure_diversity": "structure_diversity flag",
    "continue_snapshot": "重读 ack / 章快照",
    "secret_guard": "_secret_guard_block (T0 facts_at)",
    "focalizer": "request.focalizer",
    "narrative_contract": "load_chapter_story_inputs.contract",
    "story_ember": "chapter[n-1].narrative_drive.end_hook",
    "story_recall": "限知投影后的世界",
    "story_causal": "上章存在性",
    "event_drive": "叙事引擎 + 无场面",
    "event_drive_hook": "叙事引擎 + 有场面",
    "drama_contract": "章 beats",
    "drama_vacuum": "should_inject_drama_vacuum",
    "outline": "synopsis / beats",
    "envelope": "ContextAssembler.assemble",
    "codex": "_codex_block(for_generation=True)",
    "seed_words": "章 seed_words",
    "craft": "list_craft_rules",
    "phase_role": "phase",
    "avoid": "现网默认 omit",
    "revelation_discipline": "焦点者",
    "sincerity": "已并入 prefix",
    "purpose": "章 purpose",
    "volume_intro": "旗 + 章 volume",
    "brief_must": "章 brief",
    "pressure_drive": "章 pressure",
    "author_prefs": "章 prefs",
    "voice_anchor": "voice / 章锚",
    "reference_craft": "draft/final + briefs",
    "storyline_polish": "旗 + storyline meta",
    "discourse_soft": "旗 + discourse",
    "story_move": "旗 + approved plan",
    "deduction_final": "draft/final + deduction",
    "material_recall": "draft/final + materials",
    "final_reminder": "恒有",
    "scene_truth_proj": "phase==deduce",
    "request_constraint": "extra_instructions",
    "tool_scope": "with_tools",
    "craft_skills_index": "with_tools",
    "benchmark_advisory": "draft/final + 旗",
}

SEG_FN: dict[str, str] = {
    "identity": "_editor_identity_block",
    "write_protocol": "subtract_codex_canonical_echoes",
    "prefix": "anti_slop_floor_block",
    "revision": "is_revision_request",
    "structure_diversity": "structure_diversity_block",
    "continue_snapshot": "continue_block_text",
    "secret_guard": "prompt_blocks._secret_guard_block",
    "focalizer": "writing_limited_banner",
    "narrative_contract": "format_story_contract_head",
    "story_ember": "collect_story_fuel_segments",
    "story_recall": "collect_story_fuel_segments",
    "story_causal": "collect_story_fuel_segments",
    "event_drive": "_event_drive_block",
    "event_drive_hook": "_event_drive_block",
    "drama_contract": "_drama_block",
    "drama_vacuum": "should_inject_drama_vacuum",
    "outline": "_outline_block",
    "envelope": "ContextAssembler.assemble",
    "codex": "cap_codex_text",
    "seed_words": "seed_words_push",
    "craft": "list_craft_rules",
    "phase_role": "_phase_role_block",
    "avoid": "default_omit",
    "revelation_discipline": "_revelation_discipline_block",
    "sincerity": "merged_into_prefix",
    "purpose": "_purpose_and_lessons_write_block",
    "volume_intro": "_volume_intro_block",
    "brief_must": "_brief_must_sections_write_block",
    "pressure_drive": "_pressure_drive_write_block",
    "author_prefs": "_author_prefs_block_safe",
    "voice_anchor": "_voice_anchor_block",
    "reference_craft": "reference_craft",
    "storyline_polish": "storyline_inject_polish",
    "discourse_soft": "discourse_soft",
    "story_move": "validate_story_move_plan",
    "deduction_final": "_deduction_context_segments",
    "material_recall": "_material_recall_block",
    "final_reminder": "_final_reminder",
    "scene_truth_proj": "scene_truth_proj",
    "request_constraint": "extra_instructions",
    "tool_scope": "_s3_work_scope_block",
    "craft_skills_index": "skills_index_block",
    "benchmark_advisory": "benchmark_inject_enabled",
}

PRECOMPUTE_SEG = frozenset({
    "identity", "write_protocol", "prefix", "revision", "structure_diversity",
    "continue_snapshot", "secret_guard", "focalizer", "tool_scope",
    "craft_skills_index",
})
FUEL_SEG = frozenset({"story_ember", "story_recall", "story_causal"})
LOAD_SEG = frozenset({"narrative_contract"})

FIXED_STEPS: tuple[tuple[str, str, str, str | None], ...] = (
    ("handler.reread_gate", "续写重读门", "guard", None),
    ("handler.context_enforce", "上下文绑定门", "guard", None),
    ("assemble.precompute", "编译前预计算", "assemble", None),
    ("assemble.load_story_inputs", "加载章故事输入", "assemble", "compile.engine"),
    ("assemble.collect_fuel", "收集三燃料", "assemble", "compile.engine"),
    ("assemble.freeze_expected", "冻结期望事实", "assemble", "compile.engine"),
    ("budget.l2", "L2 补充裁剪", "budget", "compile.engine"),
    ("budget.o1", "O1 全域硬顶", "budget", "compile.engine"),
    ("compile.envelope", "组装信封", "compile", "compile.engine"),
    ("compile.manifest", "落 Manifest", "compile", "compile.engine"),
    ("compile.engine", "编译引擎", "compile", None),
    ("guard.epistemic", "限知出口守卫", "guard", None),
    ("llm.generate", "模型生成", "llm", None),
    ("persist.outcome", "落 Outcome", "persist", "llm.generate"),
    ("persist.turn_bind", "落 TurnBind", "persist", None),
    ("persist.chapter", "落章正文", "persist", None),
    ("save.loop_busy", "loop 互斥", "save", None),
    ("save.pilot_busy", "pilot 互斥", "save", None),
    ("save.craft_gate", "工艺门", "save", None),
    ("save.finalize_gate", "定稿门", "save", None),
    ("save.strict_scene", "严格戏格", "save", None),
    ("claim.reader_claim", "宣称可读", "claim", None),
    ("claim.scaffold_gate_b", "脚手架 GATE-B", "claim", None),
)


@dataclass(frozen=True)
class StepDef:
    step_key: str
    step_title: str
    layer: str
    parent_key: str | None
    name: str | None = None
    tier: str | None = None
    zone: str | None = None
    source: str | None = None
    compute_fn: str | None = None


def _reg_meta() -> dict[str, tuple[str, str]]:
    return {m.name: (m.tier, m.zone) for m in SEGMENT_REGISTRY}


def _seg_key(name: str) -> str:
    return f"assemble.seg.{name}"


def parent_of(step_key: str) -> str | None:
    if step_key.startswith("tool."):
        return "llm.generate"
    if step_key == "persist.outcome":
        return "llm.generate"
    if step_key.startswith("assemble.seg."):
        name = step_key[len("assemble.seg."):]
        if name in PRECOMPUTE_SEG:
            return "assemble.precompute"
        if name in FUEL_SEG:
            return "assemble.collect_fuel"
        if name in LOAD_SEG:
            return "assemble.load_story_inputs"
        return "compile.engine"
    for key, _title, _layer, parent in FIXED_STEPS:
        if key == step_key:
            return parent
    return None


def _build_catalog() -> dict[str, StepDef]:
    meta = _reg_meta()
    out: dict[str, StepDef] = {}
    names = [m.name for m in SEGMENT_REGISTRY]
    for extra in SEG_TITLES:
        if extra not in names:
            names.append(extra)
    for name in names:
        tier, zone = meta.get(name, ("extra", None))
        key = _seg_key(name)
        out[key] = StepDef(
            step_key=key,
            step_title=SEG_TITLES.get(name, f"未登记·{name}"),
            layer="assemble" if name != "envelope" else "compile",
            parent_key=parent_of(key),
            name=name,
            tier=tier,
            zone=zone,
            source=SEG_SOURCE.get(name),
            compute_fn=SEG_FN.get(name),
        )
    # envelope 既是段也是 compile.envelope；段键保留，compile.envelope 另登记
    for key, title, layer, parent in FIXED_STEPS:
        out[key] = StepDef(
            step_key=key,
            step_title=title,
            layer=layer,
            parent_key=parent,
            compute_fn=key.replace(".", "_"),
        )
    return out


_CATALOG = _build_catalog()


def lookup(step_key: str) -> StepDef:
    hit = _CATALOG.get(step_key)
    if hit:
        return hit
    if step_key.startswith("tool."):
        raw = step_key[5:]
        return StepDef(
            step_key=step_key,
            step_title=f"工具 · {raw}",
            layer="tool",
            parent_key="llm.generate",
            compute_fn="tool_hop",
        )
    if step_key.startswith("assemble.seg."):
        name = step_key[len("assemble.seg."):]
        return StepDef(
            step_key=step_key,
            step_title=f"未登记·{name}",
            layer="assemble",
            parent_key=parent_of(step_key),
            name=name,
            tier="extra",
            source="unregistered",
            compute_fn="unregistered",
        )
    return StepDef(
        step_key=step_key,
        step_title=step_key,
        layer="assemble",
        parent_key=parent_of(step_key),
    )


def all_step_keys() -> list[str]:
    return list(_CATALOG.keys())


_TOOL_SAFE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def tool_step_key(name: str | None) -> str:
    raw = _TOOL_SAFE.sub("", str(name or "")).strip("._")[:64]
    return f"tool.{raw}" if raw else "tool.unknown"


def layer_title(layer: str) -> str:
    return {
        "assemble": "装段",
        "budget": "预算裁剪",
        "compile": "编译",
        "guard": "门闩",
        "llm": "模型",
        "tool": "工具跳",
        "persist": "落库",
        "save": "存稿门",
        "claim": "宣称门",
    }.get(layer, layer)
