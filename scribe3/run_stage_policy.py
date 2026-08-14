"""Hermes Run 的阶段能力边界。

Hermes Runs API 没有请求级 MCP 工具过滤；阶段安全不能依赖提示词或
``server_label``。本模块把章节阶段映射到独立 gateway profile，使 profile
的 ``mcp_servers.*.tools.include`` 成为实际能力边界。
"""
from __future__ import annotations

from dataclasses import dataclass
import re


_CHAPTER_SCOPE = re.compile(r"^chapter:([1-9][0-9]*):([a-z][a-z0-9_-]{0,31})$")
_EXPLICIT_TOOL_CALL = re.compile(
    r"(?:请|必须|需要|要求|务必|立即|立刻|现在)?\s*"
    r"(?:调用|使用|执行|call|invoke|use)\s*`?"
    r"(s3_[a-z][a-z0-9_]*)\b", re.IGNORECASE,
)


@dataclass(frozen=True)
class RunStagePolicy:
    """一个受限阶段 Run 的不可变能力合同。"""

    phase: str
    profile: str
    api_env: str
    allowed_tools: frozenset[str]
    max_tool_calls: int
    required_tools: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RunToolContract:
    """普通书级 Run 的最小工具审计合同。

    它不改变 Hermes profile 的能力面（书级主编仍走既有完整写 profile），只把作者
    明确点名的 ``s3_*`` 调用转化为可回读的终态证据要求。这样模型用文字声称调用
    工具而没有工具事件时，不会被 ``run.completed`` 假绿。
    """

    source: str
    required_tools: frozenset[str]


DEDUCE_ALLOWED_TOOLS = frozenset({
    "s3_get_chapter",
    "s3_project_frame",
    "s3_character_state",
    "s3_list_entity_relations",
    "s3_list_world_rules",
    "s3_list_promises",
    "s3_patch_chapter_plan",
    "s3_generate_stage",
})

DEDUCE_PREVIEW_ALLOWED_TOOLS = DEDUCE_ALLOWED_TOOLS - {"s3_patch_chapter_plan"}

# 大纲/节拍脚手架：可读章 + plan 写；物理排除 save/ingest（novel-first O-5）
PLAN_SCAFFOLD_ALLOWED_TOOLS = frozenset({
    "s3_get_chapter",
    "s3_list_chapters",
    "s3_get_intent",
    "s3_list_promises",
    "s3_list_volumes",
    "s3_patch_chapter_plan",
    "s3_patch_chapter_meta",
    "s3_generate_stage",
})

# 明确禁止出现在脚手架 allowlist
PLAN_SCAFFOLD_FORBIDDEN = frozenset({
    "s3_save_chapter",
    "s3_ingest_chapter",
})
assert not (PLAN_SCAFFOLD_ALLOWED_TOOLS & PLAN_SCAFFOLD_FORBIDDEN)


_POLICIES = {
    "deduce": RunStagePolicy(
        phase="deduce",
        profile="scribe3_deduce",
        api_env="HERMES_DEDUCE_RUNS_API",
        allowed_tools=DEDUCE_ALLOWED_TOOLS,
        # 演绎至多需读取当前章+角色/规则/关系/伏笔，再提交一次计划；12 次后说明游走。
        max_tool_calls=12,
        required_tools=frozenset({"s3_patch_chapter_plan"}),
    ),
    # 预览是质量审查的输入，必须物理上没有任何写工具；它绝不能靠 prompt “不写”。
    "deduce_preview": RunStagePolicy(
        phase="deduce_preview",
        profile="scribe3_deduce_preview",
        api_env="HERMES_DEDUCE_PREVIEW_RUNS_API",
        allowed_tools=DEDUCE_PREVIEW_ALLOWED_TOOLS,
        max_tool_calls=11,
        # 预览必须先读取当前章，不能以一段未联查的文字冒充基于正典的分析。
        required_tools=frozenset({"s3_get_chapter"}),
    ),
    "outline": RunStagePolicy(
        phase="outline",
        profile="scribe3_plan",
        api_env="HERMES_PLAN_RUNS_API",
        allowed_tools=PLAN_SCAFFOLD_ALLOWED_TOOLS,
        max_tool_calls=12,
        required_tools=frozenset({"s3_patch_chapter_plan"}),
    ),
    "beats": RunStagePolicy(
        phase="beats",
        profile="scribe3_plan",
        api_env="HERMES_PLAN_RUNS_API",
        allowed_tools=PLAN_SCAFFOLD_ALLOWED_TOOLS,
        max_tool_calls=12,
        required_tools=frozenset({"s3_patch_chapter_plan"}),
    ),
    # 与 outline/beats 共用受限 plan profile
    "plan": RunStagePolicy(
        phase="plan",
        profile="scribe3_plan",
        api_env="HERMES_PLAN_RUNS_API",
        allowed_tools=PLAN_SCAFFOLD_ALLOWED_TOOLS,
        max_tool_calls=12,
        required_tools=frozenset({"s3_patch_chapter_plan"}),
    ),
    # 草稿：允许 save，禁止 ingest / 世界设定写
    "draft": RunStagePolicy(
        phase="draft",
        profile="scribe3_draft",
        api_env="HERMES_DRAFT_RUNS_API",
        allowed_tools=frozenset({
            "s3_get_chapter",
            "s3_list_chapters",
            "s3_project_frame",
            "s3_character_state",
            "s3_list_promises",
            "s3_list_entity_relations",
            "s3_list_world_rules",
            "s3_save_chapter",
            "s3_save_chapter_draft",
            "s3_patch_chapter_plan",
            "s3_generate_stage",
        }),
        max_tool_calls=20,
        required_tools=frozenset(),
    ),
    "final": RunStagePolicy(
        phase="final",
        profile="scribe3_draft",
        api_env="HERMES_DRAFT_RUNS_API",
        allowed_tools=frozenset({
            "s3_get_chapter",
            "s3_list_chapters",
            "s3_project_frame",
            "s3_character_state",
            "s3_list_promises",
            "s3_list_entity_relations",
            "s3_list_world_rules",
            "s3_save_chapter",
            "s3_save_chapter_draft",
            "s3_patch_chapter_plan",
            "s3_generate_stage",
        }),
        max_tool_calls=20,
        required_tools=frozenset(),
    ),
}


def scaffold_tools_exclude_save(policy: RunStagePolicy | None) -> bool:
    """脚手架策略不得包含 save/ingest。"""
    if policy is None:
        return False
    tools = policy.allowed_tools or frozenset()
    return not (tools & PLAN_SCAFFOLD_FORBIDDEN)


# 脚手架阶段：即使「世界写」启发式命中，也必须带 chapter:N:<phase> run_scope，
# 走 scribe3_plan / deduce 受限 profile，禁止静默落到全写（含 save/ingest）。
SCAFFOLD_PHASES = frozenset({
    "outline", "beats", "plan", "deduce", "deduce_preview", "draft", "final",
})


def normalize_scaffold_phase(phase: str | None) -> str | None:
    """UI/编排 phase → 可解析的 run_stage phase；非脚手架返回 None。"""
    p = (phase or "").strip().lower()
    if p in SCAFFOLD_PHASES:
        return p
    return None


def scaffold_run_scope(chapter: int | None, phase: str | None) -> str | None:
    """脚手架强制 run_scope；缺章或非脚手架 → None。

    调用方（主编坞 world-write 路径）必须在 outline|beats|plan|deduce 时使用本函数
    结果，**不得**因 useWorldWriteRun 清空 phase。
    """
    p = normalize_scaffold_phase(phase)
    if p is None or chapter is None:
        return None
    try:
        ch = int(chapter)
    except (TypeError, ValueError):
        return None
    if ch < 1:
        return None
    return f"chapter:{ch}:{p}"


def scaffold_forces_stage_profile(phase: str | None, *, world_write: bool = False) -> bool:
    """world_write 启发式为真时，脚手架 phase 仍须走阶段 profile。"""
    del world_write  # 显式：world_write 不得覆盖脚手架
    return normalize_scaffold_phase(phase) is not None


def resolve_run_stage_policy(run_scope: str | None) -> RunStagePolicy | None:
    """解析章节阶段 scope；普通 Runs 保持兼容，章节未知 phase 一律拒绝。"""
    scope = (run_scope or "").strip()
    if not scope or scope == "runs":
        return None
    match = _CHAPTER_SCOPE.fullmatch(scope)
    if not match:
        raise ValueError("unsupported chapter run phase")
    phase = match.group(2)
    try:
        return _POLICIES[phase]
    except KeyError as exc:
        raise ValueError("unsupported chapter run phase") from exc


def explicit_book_tool_contract(input_text: str, instructions: str = "") -> RunToolContract | None:
    """提取作者明确要求执行的 ``s3_*`` 工具，忽略一般性提及。"""
    requested = {
        match.group(1).lower()
        for match in _EXPLICIT_TOOL_CALL.finditer(f"{input_text or ''}\n{instructions or ''}")
    }
    if not requested:
        return None
    return RunToolContract(
        source="explicit_tool_request",
        required_tools=frozenset(requested),
    )


def tool_contract_snapshot(contract: RunToolContract) -> dict:
    return {
        "source": contract.source,
        "required_tools": sorted(contract.required_tools),
    }


def _native_tool_names(required_tools: frozenset[str]) -> list[str]:
    """把领域工具名转换成当前 Hermes 看见的原生 MCP 函数名。"""
    from scribe3.mcp import requires_approval

    return [
        f"mcp__{'scribe3_write' if requires_approval(tool) else 'scribe3_read'}__{tool}"
        for tool in sorted(required_tools)
    ]


def _native_tool_call_guidance(required_tools: frozenset[str]) -> str:
    """要求模型把工具需求落实为可审计的原生 MCP 调用。

    领域工具在产品话术中是 ``s3_*``，Hermes 的 OpenAI tool schema 中则带 server
    前缀。模型若把前者写成 XML/普通文本，网关不会执行任何工具；这里明确要求调用
    完整原生函数名。当前 Hermes 会在 MCP schema
    较多时启用官方 Tool Search：模型先搜索和描述，再必须经 ``tool_call`` 桥调用实际
    函数。XML 只是模型输出文本，绝不能视作调用或后备执行路径。
    """
    native_names = _native_tool_names(required_tools)
    return (
        "【原生 MCP 工具调用·必须执行】本轮的完成条件是实际产生以下函数调用事件："
        + "、".join(native_names)
        + "。若当前可见 `tool_search`、`tool_describe`、`tool_call` 三个桥接工具，"
        "必须先用 tool_search 找到上列函数名、用 tool_describe 读取参数 schema，随后必须调用"
        "tool_call(name=上列完整函数名, arguments=按 schema 填写的对象)；搜索或描述后不得结束 Run。"
        "若完整函数已直接可见，则直接原生调用。不得输出 <tool_call> XML、Markdown、普通 JSON 文本、"
        "“正在调用”的说明或省略参数来冒充调用；"
        "若工具调用接口不可用，明确报告失败并停止，不能把 Run 说成完成。"
    )


def native_tool_call_guidance(contract: RunToolContract) -> str:
    """生成作者明确点名工具的原生 MCP 调用指引。"""
    return _native_tool_call_guidance(contract.required_tools)


def native_stage_tool_guidance(policy: RunStagePolicy) -> str:
    """生成章节阶段 required_tools 的原生 MCP 调用指引。"""
    return _native_tool_call_guidance(policy.required_tools)


def tool_contract_from_trace_snapshot(snapshot: object) -> RunToolContract | None:
    """恢复书级合同；审计记录被污染时宁可拒绝继续消费。"""
    if snapshot is None:
        return None
    if not isinstance(snapshot, dict) or set(snapshot) != {"source", "required_tools"}:
        raise ValueError("invalid run tool contract trace")
    required = snapshot.get("required_tools")
    if snapshot.get("source") != "explicit_tool_request" or not isinstance(required, list):
        raise ValueError("invalid run tool contract trace")
    names = frozenset(str(name) for name in required)
    if not names or any(not re.fullmatch(r"s3_[a-z][a-z0-9_]*", name) for name in names):
        raise ValueError("invalid run tool contract trace")
    if sorted(names) != required:
        raise ValueError("invalid run tool contract trace")
    return RunToolContract(source="explicit_tool_request", required_tools=names)


def policy_from_trace_snapshot(snapshot: object) -> RunStagePolicy | None:
    """从服务端创建时留下的快照恢复 policy，并拒绝被污染的审计记录。"""
    if snapshot is None:
        return None
    if not isinstance(snapshot, dict):
        raise ValueError("invalid run stage policy trace")
    phase = snapshot.get("phase")
    policy = _POLICIES.get(phase)
    if policy is None:
        raise ValueError("invalid run stage policy trace")
    expected = {
        "phase": policy.phase,
        "profile": policy.profile,
        "allowed_tools": sorted(policy.allowed_tools),
        "max_tool_calls": policy.max_tool_calls,
        "required_tools": sorted(policy.required_tools),
    }
    if snapshot != expected:
        raise ValueError("invalid run stage policy trace")
    return policy


def validate_tool_trace(policy: RunStagePolicy | RunToolContract, tool_calls: list[dict],
                        tool_outputs: list[dict]) -> list[dict]:
    """对已落库的工具审计链做 fail-closed 校验。"""
    violations: list[dict] = []
    if isinstance(policy, RunStagePolicy):
        for call in tool_calls:
            tool = str(call.get("name") or "")
            sequence = call.get("sequence")
            if tool not in policy.allowed_tools:
                violations.append({"code": "tool_not_allowed", "tool": tool, "sequence": sequence})
        if len(tool_calls) > policy.max_tool_calls:
            violations.append({
                "code": "tool_call_limit_exceeded",
                "actual": len(tool_calls),
                "max": policy.max_tool_calls,
            })
    output_ids = {str(out.get("call_id")) for out in tool_outputs if out.get("call_id")}
    for call in tool_calls:
        call_id = call.get("call_id")
        if not call_id or str(call_id) not in output_ids:
            violations.append({
                "code": "tool_output_missing",
                "tool": str(call.get("name") or ""),
                "sequence": call.get("sequence"),
            })
    called_tools = {str(call.get("name") or "") for call in tool_calls}
    for tool in sorted(policy.required_tools):
        if tool not in called_tools:
            violations.append({"code": "required_tool_missing", "tool": tool})
    return violations


# 兼容既有章节阶段调用方；新书级合同使用更中性的 validate_tool_trace。
validate_stage_tool_trace = validate_tool_trace
