"""GAP-11：Per-run 工具后验拦截（Hermes 无请求级 filter 时的等价替代）。

在 agent 返回 tool_calls 后，用 stage policy 白名单过滤非法调用。
"""
from __future__ import annotations

from typing import Any, Iterable


# 讨论/agentic 只读默认白名单（写工具默认拦）
_DISCUSS_READ_ALLOW: frozenset[str] = frozenset({
    "s3_project_frame", "s3_skill_read", "s3_find_leaks", "s3_causal_complete",
    "s3_semantic_recall", "s3_hybrid_recall", "s3_chapter_recall", "s3_graph_recall",
    "s3_material_recall", "s3_setting_completeness", "s3_list_world_rules",
    "s3_list_factions", "s3_character_state", "s3_character_timeline",
    "s3_relations_at", "s3_list_entity_relations", "s3_get_voice_profile",
    "s3_check_ooc", "s3_list_items", "s3_list_terms", "s3_resolve_entities",
    "s3_validate_setting", "s3_dramatic_irony", "s3_list_promises", "s3_list_motifs",
    "s3_list_chapters", "s3_list_volumes", "s3_get_chapter", "s3_qc_chapter",
    "s3_recent_phrases", "s3_cross_repetition", "s3_dedup_cross",
    "s3_emotion_palette", "s3_craft_rule_list", "s3_discipline_check",
    "s3_list_voice_flags", "s3_get_intent",
})


def allowed_tools_for_phase(phase: str | None) -> frozenset[str] | None:
    """返回允许的 s3_* 工具名集合；None 表示不拦截。"""
    p = (phase or "").strip().lower()
    if not p:
        return None
    try:
        from scribe3.run_stage_policy import stage_policy_for
        pol = stage_policy_for(p)
        if pol is None:
            # discuss / agentic 默认只读
            if p in ("discuss", "discussion", "agentic", "chat"):
                return _DISCUSS_READ_ALLOW
            return None
        for attr in ("allowed_tools", "tools", "tool_allowlist"):
            v = getattr(pol, attr, None)
            if v:
                return frozenset(str(x) for x in v)
    except Exception:
        if p in ("discuss", "discussion", "agentic", "chat"):
            return _DISCUSS_READ_ALLOW
    if "deduce" in p:
        return frozenset({
            "s3_list_chapters", "s3_get_chapter", "s3_semantic_recall",
            "s3_hybrid_recall", "s3_graph_recall", "s3_project_frame",
            "s3_list_promises", "s3_character_state",
        })
    if p in ("discuss", "discussion", "agentic", "chat"):
        return _DISCUSS_READ_ALLOW
    return None


def filter_tool_calls(
    tool_calls: Iterable[dict[str, Any]] | None,
    *,
    phase: str | None = None,
    allow: frozenset[str] | None = None,
) -> dict[str, Any]:
    """过滤 tool_calls；返回 kept / blocked / allowed_set。"""
    allow_set = allow if allow is not None else allowed_tools_for_phase(phase)
    calls = list(tool_calls or [])
    if allow_set is None:
        return {
            "kept": calls,
            "blocked": [],
            "allowed": None,
            "enforced": False,
        }
    kept: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for c in calls:
        if not isinstance(c, dict):
            blocked.append({"raw": c, "reason": "not_dict"})
            continue
        name = (
            c.get("name")
            or c.get("tool")
            or (c.get("function") or {}).get("name")
            or ""
        )
        name = str(name)
        # 剥离 mcp__server__ 前缀
        if "__" in name:
            name = name.split("__")[-1]
        if name in allow_set or name.startswith("s3_") and name in allow_set:
            kept.append(c)
        elif name in allow_set:
            kept.append(c)
        else:
            blocked.append({**c, "blocked_name": name, "reason": "not_in_allowlist"})
    return {
        "kept": kept,
        "blocked": blocked,
        "allowed": sorted(allow_set),
        "enforced": True,
    }
