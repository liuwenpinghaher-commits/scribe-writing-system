"""阶段化 Hermes Run 的真实工具边界契约。"""

import pytest


def test_deduce_scope_uses_dedicated_profile_and_exact_allowlist():
    """演绎不是靠提示词约束：必须由独立 profile 物理收窄工具面。"""
    from scribe3.run_stage_policy import resolve_run_stage_policy

    policy = resolve_run_stage_policy("chapter:1:deduce")

    assert policy.profile == "scribe3_deduce"
    assert policy.api_env == "HERMES_DEDUCE_RUNS_API"
    assert policy.allowed_tools == frozenset({
        "s3_get_chapter",
        "s3_project_frame",
        "s3_character_state",
        "s3_list_entity_relations",
        "s3_list_world_rules",
        "s3_list_promises",
        "s3_patch_chapter_plan",
    })
    assert policy.max_tool_calls == 12


def test_deduce_preview_scope_is_physically_read_only_and_requires_chapter_evidence():
    from scribe3.run_stage_policy import resolve_run_stage_policy, validate_stage_tool_trace

    policy = resolve_run_stage_policy("chapter:1:deduce_preview")

    assert policy.profile == "scribe3_deduce_preview"
    assert policy.allowed_tools == frozenset({
        "s3_get_chapter", "s3_project_frame", "s3_character_state",
        "s3_list_entity_relations", "s3_list_world_rules", "s3_list_promises",
    })
    # 预览不能只输出一段“我已经核对过”的文本；至少必须读取当前章，
    # 否则作者无法把预览当作正典上下文的真实分析证据。
    assert policy.required_tools == frozenset({"s3_get_chapter"})
    assert validate_stage_tool_trace(policy, [], []) == [
        {"code": "required_tool_missing", "tool": "s3_get_chapter"},
    ]


def test_regular_runs_remain_on_full_write_profile_for_compatibility():
    from scribe3.run_stage_policy import resolve_run_stage_policy

    assert resolve_run_stage_policy(None) is None
    assert resolve_run_stage_policy("runs") is None


def test_explicit_write_contract_follows_tool_search_then_call_protocol():
    """Tool Search 已接管 MCP schema 时，模型必须继续到 tool_call，不能止于搜索。"""
    from scribe3.run_stage_policy import RunToolContract, native_tool_call_guidance

    text = native_tool_call_guidance(RunToolContract(
        source="explicit_tool_request", required_tools=frozenset({"s3_add_chapter"}),
    ))

    assert "mcp__scribe3_write__s3_add_chapter" in text
    assert "tool_search" in text and "tool_describe" in text
    assert "tool_call(name=" in text
    assert "搜索或描述后不得结束 Run" in text
    # XML 只是模型输出的普通文本，不能作为原生工具调用的降级通道。
    assert "不得输出 <tool_call> XML" in text
    assert "严格 XML" not in text
    assert '"name"' not in text and '"arguments"' not in text
    assert "不得输出 <tool_call>" in text


@pytest.mark.parametrize("scope", [
    "chapter:0:deduce",
    "chapter:1:invent",
    "chapter:one:deduce",
    "chapter:1:deduce:extra",
])
def test_invalid_or_unknown_chapter_scope_is_rejected_fail_closed(scope):
    from scribe3.run_stage_policy import resolve_run_stage_policy

    with pytest.raises(ValueError, match="unsupported chapter run phase"):
        resolve_run_stage_policy(scope)
