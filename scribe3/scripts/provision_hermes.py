"""可复现地把 scribe3 拥有的 Hermes 网关配置叠加进 ~/.hermes(部署到任何地方都一致)。

背景/设计见 scribe3/deploy/hermes/README.md。一句话:三个 profile 的网关配置此前全靠手动
配在部署机上、一行不在 git;本脚本把 scribe3【拥有】的那部分(platform_toolsets 安全不变量 /
mcp_servers 工具白名单 / 端口 / 主编身份)纳入 git,幂等叠加进 ~/.hermes,密钥与 Dashboard
管的键原样保留。

关键性质:
- **叠加(深合并),不整文件覆写**:overlay 里只有 scribe3 拥有的键 → 深合并只动这些键,
  providers/secrets/model/skills/cron 等(密钥 + Dashboard 管)天然不被触碰。
- **幂等**:现状已合模板 → dry-run 显示零变更;可反复跑。
- **机器路径参数化**:mcp_servers.command 的 {{RUN_MCP}} 按 --repo 替换成绝对路径。
- **默认 dry-run**:只打印将改什么;--commit 才真写,且先备份 .bak.<ms>。
- **安全不变量强制**:写库前断言默认 profile 零工具面 + 任何 include 无 *_reveal;不满足则
  拒绝写入(fail-closed)。

用法:
  python -m scribe3.scripts.provision_hermes                 # dry-run(缺省 ~/.hermes + 自动探测 repo)
  python -m scribe3.scripts.provision_hermes --commit        # 真写全部受管 profile
  python -m scribe3.scripts.provision_hermes --profile scribe3_deduce_preview --skip-crons --commit
  HERMES_HOME=/tmp/h python -m scribe3.scripts.provision_hermes --repo /path/to/repo --commit
"""
from __future__ import annotations

import argparse
import ast
import copy
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

# 安全不变量常量(与 mcp.py / app._summarize_hermes_runtime 的门禁同源语义)
REVEAL_SUFFIX = "_reveal"

_DEPLOY_DIR = Path(__file__).resolve().parent.parent / "deploy" / "hermes"
# profile → (overlay 文件, 目标 config 相对 HERMES_HOME 的路径, 是否注入共享 mcp_servers, SOUL 模板)
_PROFILES = {
    "default": ("overlay.default.yaml", "config.yaml", False, None),
    "scribe3": ("overlay.scribe3.yaml", "profiles/scribe3/config.yaml", True, "SOUL.scribe3.md"),
    "scribe3_write": ("overlay.scribe3_write.yaml", "profiles/scribe3_write/config.yaml", True,
                      "SOUL.scribe3_write.md"),
    "scribe3_deduce": ("overlay.scribe3_deduce.yaml", "profiles/scribe3_deduce/config.yaml", True,
                       "SOUL.scribe3_write.md"),
    "scribe3_deduce_preview": ("overlay.scribe3_deduce_preview.yaml",
                                "profiles/scribe3_deduce_preview/config.yaml", True,
                                "SOUL.scribe3.md"),
    # 大纲/节拍脚手架：与 run_stage_policy outline|beats|plan → scribe3_plan 对齐
    "scribe3_plan": ("overlay.scribe3_plan.yaml",
                     "profiles/scribe3_plan/config.yaml", True,
                     "SOUL.scribe3_write.md"),
    "scribe3_draft": ("overlay.scribe3_draft.yaml",
                      "profiles/scribe3_draft/config.yaml", True,
                      "SOUL.scribe3_write.md"),
}

# Hermes 会注册 profile config 中的全部 MCP server；platform_toolsets 只是请求标签，
# 不是服务器级过滤器。因此每个阶段 profile 必须物理只声明自己能使用的最小工具面。
_PROFILE_MCP_SERVERS = {
    "scribe3": ("scribe3_read",),
    "scribe3_write": ("scribe3_read", "scribe3_write"),
    "scribe3_deduce": ("scribe3_deduce_read", "scribe3_deduce_write"),
    "scribe3_deduce_preview": ("scribe3_deduce_read",),
    "scribe3_plan": ("scribe3_plan_read", "scribe3_plan_write"),
    "scribe3_draft": ("scribe3_draft_read", "scribe3_draft_write"),
}


# TokenPlan/Qwen 会按 Hermes 文档输出 XML 工具调用；Hermes 0.18.2 的会话循环尚未
# 将其还原为 OpenAI 兼容的 ``assistant_message.tool_calls``。该标记用于受管、幂等地
# 安装最小桥接，不匹配上游锚点时必须失败，避免静默失效。
_XML_TOOL_CALL_BRIDGE_MARKER = "# scribe3-managed: xml-tool-call-bridge v1"
_XML_TOOL_CALL_LOOP_ANCHOR = (
    "            # Check for tool calls\n"
    "            if assistant_message.tool_calls:"
)


# Hermes 0.18.2 已有 session-expired 重连+单次重放，但只检查 ``str(exc)``。
# AnyIO ``ClosedResourceError()`` 的消息为空，因此首次 stdio 写调用会绕过恢复路径。
# 这个受管补丁只扩展异常分类，不改工具权限、elicitation 或重放次数。
_MCP_CLOSED_RESOURCE_RECOVERY_MARKER = (
    "# scribe3-managed: empty ClosedResourceError recovery v1"
)
_MCP_CLOSED_RESOURCE_LEGACY_BLOCK = '''    msg = str(exc).lower()
    if not msg:
        return False
    return any(marker in msg for marker in _SESSION_EXPIRED_MARKERS)'''
_MCP_CLOSED_RESOURCE_FIXED_BLOCK = f'''    {_MCP_CLOSED_RESOURCE_RECOVERY_MARKER}
    # AnyIO transport exceptions such as ``ClosedResourceError()`` commonly
    # carry no message at all. Include the exception type so an empty stale
    # transport error still reaches the existing reconnect-and-retry path.
    detail = f"{{type(exc).__name__}}: {{exc}}".lower()
    return any(marker in detail for marker in _SESSION_EXPIRED_MARKERS)'''


# macOS 上长寿命进程与新启动 watchdog 可能因 psutil/boot_time 采样基准变化，
# 对同一 PID 得到相差整 1 秒的 create_time。Hermes 0.18.2 用 float 严格不等
# 判 PID 复用，会误杀仍由原 gateway 持有的 MCP child。PPID 不同仍是第一硬闸；
# create_time 只保留为第二重 PID 复用保护，并允许已实测到的小幅测量漂移。
_MCP_WATCHDOG_PARENT_IDENTITY_MARKER = (
    "# scribe3-managed: stable MCP watchdog parent identity v1"
)
_MCP_WATCHDOG_CREATE_TIME_TOLERANCE_S = 2.0
_MCP_WATCHDOG_CONSTANT_ANCHOR = "_TERM_GRACE_S = 3.0\n"
_MCP_WATCHDOG_TOLERANCE_BLOCK = f'''{_MCP_WATCHDOG_CONSTANT_ANCHOR.rstrip()}
{_MCP_WATCHDOG_PARENT_IDENTITY_MARKER}
_PARENT_CREATE_TIME_TOLERANCE_S = {_MCP_WATCHDOG_CREATE_TIME_TOLERANCE_S:.1f}
'''
_MCP_WATCHDOG_LEGACY_RETURN = (
    "        return psutil.Process(original_ppid).create_time() != parent_create_time"
)
_MCP_WATCHDOG_FIXED_RETURN = '''        actual_create_time = psutil.Process(original_ppid).create_time()
        return abs(actual_create_time - parent_create_time) > _PARENT_CREATE_TIME_TOLERANCE_S'''


def _atomic_write_text(path: Path, text: str) -> None:
    """同目录临时文件 + fsync + replace，避免上游源码出现半写状态。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            tmp.chmod(path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _function_body_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef):
    """遍历一个函数自身的语法树，不把嵌套作用域误算进当前函数。"""
    stack = list(reversed(function.body))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Lambda)):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _named_module_function(tree: ast.Module, name: str):
    all_named = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == name]
    module_named = [node for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == name]
    if len(all_named) != 1 or len(module_named) != 1:
        raise RuntimeError(
            f"Hermes mcp_tool.py 的 {name} 模块级锚点必须全文唯一；拒绝盲目补丁"
        )
    return module_named[0]


def _assigned_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
    elif isinstance(node, ast.AnnAssign):
        target = node.target
    else:
        return None
    return target.id if isinstance(target, ast.Name) else None


def _call_name(node: ast.Call) -> str | None:
    return node.func.id if isinstance(node.func, ast.Name) else None


def _directly_terminates(statements: list[ast.stmt]) -> bool:
    return len(statements) == 1 and isinstance(statements[0], (ast.Return, ast.Raise))


def _classifier_control_flow_guard(
        handler: ast.FunctionDef | ast.AsyncFunctionDef,
        classifier_call: ast.Call) -> ast.If | None:
    """找出能在 classifier=False 时直接终止 handler 的顶层 guard。"""
    for statement in handler.body:
        if not isinstance(statement, ast.If):
            continue
        test = statement.test
        if (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
                and test.operand is classifier_call
                and _directly_terminates(statement.body)):
            return statement
        if test is classifier_call and _directly_terminates(statement.orelse):
            return statement
        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Eq, ast.Is))
                and len(test.comparators) == 1):
            left_false = (isinstance(test.left, ast.Constant)
                          and test.left.value is False)
            right = test.comparators[0]
            right_false = isinstance(right, ast.Constant) and right.value is False
            if ((test.left is classifier_call and right_false)
                    or (left_false and right is classifier_call)):
                if _directly_terminates(statement.body):
                    return statement
    return None


def _validate_mcp_closed_resource_source(source: str) -> str:
    """验证 Hermes 0.18.2 的分类器与既有单次重连边界，返回 legacy/fixed。"""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise RuntimeError(
            "Hermes mcp_tool.py 语法结构无法解析；拒绝盲目补丁"
        ) from exc

    classifier = _named_module_function(tree, "_is_session_expired_error")
    handler = _named_module_function(tree, "_handle_session_expired_and_retry")

    marker_assignments = [
        node for node in tree.body
        if _assigned_name(node) == "_SESSION_EXPIRED_MARKERS"
    ]
    all_marker_assignments = [
        node for node in ast.walk(tree)
        if _assigned_name(node) == "_SESSION_EXPIRED_MARKERS"
    ]
    if len(marker_assignments) != 1 or len(all_marker_assignments) != 1:
        raise RuntimeError(
            "Hermes mcp_tool.py 的 _SESSION_EXPIRED_MARKERS 模块级锚点必须全文唯一"
        )
    marker_node = marker_assignments[0]
    try:
        marker_values = ast.literal_eval(marker_node.value)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "Hermes mcp_tool.py 的 _SESSION_EXPIRED_MARKERS 必须是字面量"
        ) from exc
    if (not isinstance(marker_values, (tuple, list, set))
            or "closedresourceerror" not in marker_values):
        raise RuntimeError(
            "Hermes mcp_tool.py 的 _SESSION_EXPIRED_MARKERS 缺少 closedresourceerror"
        )

    marker_count = source.count(_MCP_CLOSED_RESOURCE_RECOVERY_MARKER)
    if marker_count > 1:
        raise RuntimeError("MCP ClosedResource recovery 受管标记必须全文唯一")
    if marker_count:
        marker_line = source[:source.index(
            _MCP_CLOSED_RESOURCE_RECOVERY_MARKER
        )].count("\n") + 1
        if not classifier.lineno <= marker_line <= classifier.end_lineno:
            raise RuntimeError("MCP ClosedResource recovery 标记位置错误，疑似半补丁")

    legacy_count = source.count(_MCP_CLOSED_RESOURCE_LEGACY_BLOCK)
    if legacy_count > 1:
        raise RuntimeError("Hermes ClosedResourceError legacy 锚点出现多处，必须唯一")
    if legacy_count:
        legacy_line = source[:source.index(
            _MCP_CLOSED_RESOURCE_LEGACY_BLOCK
        )].count("\n") + 1
        if not classifier.lineno <= legacy_line <= classifier.end_lineno:
            raise RuntimeError("Hermes ClosedResourceError legacy 锚点位置错误")

    expected_detail = ast.parse(
        'detail = f"{type(exc).__name__}: {exc}".lower()'
    ).body[0].value
    expected_return = ast.parse(
        "return any(marker in detail for marker in _SESSION_EXPIRED_MARKERS)"
    ).body[0].value
    detail_nodes = [
        node for node in ast.walk(tree)
        if _assigned_name(node) == "detail"
        and ast.dump(node.value, include_attributes=False)
        == ast.dump(expected_detail, include_attributes=False)
    ]
    return_nodes = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Return) and node.value is not None
        and ast.dump(node.value, include_attributes=False)
        == ast.dump(expected_return, include_attributes=False)
    ]
    classifier_nodes = set(_function_body_nodes(classifier))
    detail_in_classifier = [node for node in detail_nodes if node in classifier_nodes]
    return_in_classifier = [node for node in return_nodes if node in classifier_nodes]
    fixed = (len(detail_nodes) == len(detail_in_classifier) == 1
             and len(return_nodes) == len(return_in_classifier) == 1)
    legacy = legacy_count == 1 and not detail_nodes and not return_nodes
    if marker_count and not fixed:
        raise RuntimeError("MCP ClosedResource recovery 受管标记对应半补丁结构")
    if not legacy and not fixed:
        raise RuntimeError(
            "Hermes mcp_tool.py 缺少唯一 ClosedResourceError 分类锚点，或存在半补丁结构"
        )

    handler_nodes = list(_function_body_nodes(handler))
    classifier_calls = [
        node for node in handler_nodes if isinstance(node, ast.Call)
        and _call_name(node) == "_is_session_expired_error"
    ]
    reconnect_calls = [
        node for node in handler_nodes if isinstance(node, ast.Call)
        and _call_name(node) == "_signal_reconnect_and_wait"
    ]
    retry_calls = [
        node for node in handler_nodes if isinstance(node, ast.Call)
        and _call_name(node) == "retry_call"
    ]
    classifier_call = classifier_calls[0] if len(classifier_calls) == 1 else None
    if (classifier_call is None or len(classifier_call.args) != 1
            or not isinstance(classifier_call.args[0], ast.Name)
            or classifier_call.args[0].id != "exc" or classifier_call.keywords):
        raise RuntimeError("Hermes 恢复 handler 必须恰好判定一次 session-expired 异常")
    classifier_guard = _classifier_control_flow_guard(handler, classifier_call)
    if classifier_guard is None:
        raise RuntimeError(
            "Hermes 恢复 handler 的 classifier 必须作为明确控制流 guard；"
            "false 分支须直接 return/raise"
        )
    retry_call = retry_calls[0] if len(retry_calls) == 1 else None
    if (len(reconnect_calls) != 1 or retry_call is None
            or retry_call.args or retry_call.keywords):
        raise RuntimeError("Hermes 恢复 handler 必须保留恰好一次重连和单次重放")
    reconnect_pos = (reconnect_calls[0].lineno, reconnect_calls[0].col_offset)
    retry_pos = (retry_calls[0].lineno, retry_calls[0].col_offset)
    guard_pos = (classifier_guard.lineno, classifier_guard.col_offset)
    if guard_pos >= reconnect_pos:
        raise RuntimeError("Hermes 恢复 handler 的 classifier guard 必须位于重连之前")
    if reconnect_pos >= retry_pos:
        raise RuntimeError("Hermes 恢复 handler 的重连必须发生在单次重放之前")
    return "fixed" if fixed else "legacy"


def _sync_mcp_closed_resource_recovery(hermes_home: Path, *, commit: bool) -> int:
    """安装 Hermes stdio 空消息关闭资源恢复补丁，返回变更数。"""
    target = hermes_home / "hermes-agent" / "tools" / "mcp_tool.py"
    if not target.is_file():
        raise RuntimeError(f"找不到已安装 Hermes MCP 客户端: {target}")

    before = target.read_text(encoding="utf-8")
    state = _validate_mcp_closed_resource_source(before)
    # 兼容当前运行机已应用的等价最小修复（无受管标记），但只接受完整语义结构。
    if state == "fixed":
        print("  ✅ [MCP ClosedResource recovery] 已同步(幂等)")
        return 0

    after = before.replace(
        _MCP_CLOSED_RESOURCE_LEGACY_BLOCK,
        _MCP_CLOSED_RESOURCE_FIXED_BLOCK,
        1,
    )
    if _validate_mcp_closed_resource_source(after) != "fixed":
        raise RuntimeError("Hermes ClosedResourceError 补丁后结构验证失败")
    print("  · [MCP ClosedResource recovery] 1 处将同步"
          + ("" if commit else " (dry-run)"))
    if not commit:
        return 1

    backup = target.with_name(
        target.name + f".bak.scribe3-closed-resource-{int(time.time() * 1000)}"
    )
    shutil.copy2(target, backup)
    target.write_text(after, encoding="utf-8")
    print(f"    MCP 客户端备份 → {backup.name}")
    return 1


def _validate_mcp_watchdog_parent_identity_source(source: str) -> str:
    """严格识别 Hermes 0.18.2 watchdog 的 legacy/fixed 父进程身份闸。"""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise RuntimeError(
            "Hermes mcp_stdio_watchdog.py 语法结构无法解析；拒绝盲目补丁"
        ) from exc

    identity = _named_module_function(tree, "_is_orphaned")
    arg_names = [arg.arg for arg in identity.args.args]
    if arg_names != ["original_ppid", "parent_create_time", "getppid"]:
        raise RuntimeError("Hermes watchdog _is_orphaned 参数结构漂移")

    expected_ppid_guard = ast.parse(
        "if getppid() != original_ppid:\n    return True"
    ).body[0]
    expected_psutil_guard = ast.parse(
        "if psutil is None:\n    return False"
    ).body[0]
    expected_pid_guard = ast.parse(
        "if not psutil.pid_exists(original_ppid):\n    return True"
    ).body[0]
    expected_handler = ast.parse(
        "try:\n    pass\nexcept psutil.Error:\n    return True"
    ).body[0].handlers[0]

    # 上游实现在 psutil fallback 分支中含解释性注释。用 AST
    # 核对严格控制流，避免把注释/空白的非语义变化误报成源码漂移。
    identity_body = list(identity.body)
    if (identity_body and isinstance(identity_body[0], ast.Expr)
            and isinstance(identity_body[0].value, ast.Constant)
            and isinstance(identity_body[0].value.value, str)):
        identity_body = identity_body[1:]
    same_ast = lambda left, right: (  # noqa: E731
        ast.dump(left, include_attributes=False)
        == ast.dump(right, include_attributes=False)
    )
    if (len(identity_body) != 3
            or not same_ast(identity_body[0], expected_ppid_guard)
            or not same_ast(identity_body[1], expected_psutil_guard)
            or not isinstance(identity_body[2], ast.Try)):
        raise RuntimeError("Hermes watchdog PPID/psutil 守卫控制流结构漂移")
    identity_try = identity_body[2]
    if (len(identity_try.body) not in (2, 3)
            or not same_ast(identity_try.body[0], expected_pid_guard)
            or len(identity_try.handlers) != 1
            or not same_ast(identity_try.handlers[0], expected_handler)
            or identity_try.orelse or identity_try.finalbody):
        raise RuntimeError("Hermes watchdog PID 存活/异常保护结构漂移")

    function_source = ast.get_source_segment(source, identity) or ""

    marker_count = source.count(_MCP_WATCHDOG_PARENT_IDENTITY_MARKER)
    legacy_count = source.count(_MCP_WATCHDOG_LEGACY_RETURN)
    fixed_count = source.count(_MCP_WATCHDOG_FIXED_RETURN)
    anchor_count = source.count(_MCP_WATCHDOG_CONSTANT_ANCHOR)
    tolerance_block_count = source.count(_MCP_WATCHDOG_TOLERANCE_BLOCK)
    if marker_count > 1 or legacy_count > 1 or fixed_count > 1:
        raise RuntimeError("Hermes watchdog 父进程身份锚点必须全文唯一")

    tolerance_assignments = [
        node for node in tree.body
        if _assigned_name(node) == "_PARENT_CREATE_TIME_TOLERANCE_S"
    ]
    all_tolerance_assignments = [
        node for node in ast.walk(tree)
        if _assigned_name(node) == "_PARENT_CREATE_TIME_TOLERANCE_S"
    ]
    fixed_assignment = False
    if len(tolerance_assignments) == len(all_tolerance_assignments) == 1:
        try:
            fixed_assignment = (
                float(ast.literal_eval(tolerance_assignments[0].value))
                == _MCP_WATCHDOG_CREATE_TIME_TOLERANCE_S
            )
        except (TypeError, ValueError):
            fixed_assignment = False

    legacy = (
        marker_count == 0
        and legacy_count == 1
        and fixed_count == 0
        and anchor_count == 1
        and not all_tolerance_assignments
        and _MCP_WATCHDOG_LEGACY_RETURN in function_source
    )
    fixed = (
        marker_count == 1
        and legacy_count == 0
        and fixed_count == 1
        and anchor_count == 1
        and tolerance_block_count == 1
        and fixed_assignment
        and _MCP_WATCHDOG_FIXED_RETURN in function_source
    )
    if not legacy and not fixed:
        raise RuntimeError(
            "Hermes mcp_stdio_watchdog.py 父进程身份结构未知或存在半补丁；拒绝写入"
        )
    return "fixed" if fixed else "legacy"


def _sync_mcp_watchdog_parent_identity(hermes_home: Path, *, commit: bool) -> int:
    """修复 macOS create_time 小漂移导致的 watchdog 活父误杀，返回变更数。"""
    target = hermes_home / "hermes-agent" / "tools" / "mcp_stdio_watchdog.py"
    if not target.is_file():
        raise RuntimeError(f"找不到已安装 Hermes MCP watchdog: {target}")

    before = target.read_text(encoding="utf-8")
    state = _validate_mcp_watchdog_parent_identity_source(before)
    if state == "fixed":
        print("  ✅ [MCP watchdog parent identity] 已同步(幂等)")
        return 0

    after = before.replace(
        _MCP_WATCHDOG_CONSTANT_ANCHOR,
        _MCP_WATCHDOG_TOLERANCE_BLOCK,
        1,
    ).replace(
        _MCP_WATCHDOG_LEGACY_RETURN,
        _MCP_WATCHDOG_FIXED_RETURN,
        1,
    )
    if _validate_mcp_watchdog_parent_identity_source(after) != "fixed":
        raise RuntimeError("Hermes MCP watchdog 父进程身份补丁后结构验证失败")
    print("  · [MCP watchdog parent identity] 1 处将同步"
          + ("" if commit else " (dry-run)"))
    if not commit:
        return 1

    backup = target.with_name(
        target.name + f".bak.scribe3-parent-identity-{int(time.time() * 1000)}"
    )
    shutil.copy2(target, backup)
    _atomic_write_text(target, after)
    print(f"    MCP watchdog 备份 → {backup.name}")
    return 1


def _sync_xml_tool_call_bridge(hermes_home: Path, repo: Path, *, commit: bool) -> int:
    """同步 TokenPlan/Qwen XML 调用桥接到已安装的 Hermes，返回变更数量。

    只接受仓内严格解析器产出的、当前 Hermes 已注册的函数名；随后仍由 Hermes 原有的
    参数校验、MCP 调度与作者审批处理。上游会话循环若变动则 fail-loud，绝不假称已部署。
    """
    source = repo / "scribe3" / "hermes_xml_tool_calls.py"
    agent_dir = hermes_home / "hermes-agent" / "agent"
    target_parser = agent_dir / "scribe3_xml_tool_calls.py"
    target_loop = agent_dir / "conversation_loop.py"
    if not source.is_file():
        raise RuntimeError(f"XML 工具调用解析器不存在: {source}")
    if not target_loop.is_file():
        raise RuntimeError(f"找不到已安装 Hermes 会话循环: {target_loop}")

    source_text = source.read_text(encoding="utf-8")
    parser_before = target_parser.read_text(encoding="utf-8") if target_parser.exists() else ""
    loop_before = target_loop.read_text(encoding="utf-8")
    if _XML_TOOL_CALL_BRIDGE_MARKER in loop_before:
        loop_after = loop_before
    else:
        if _XML_TOOL_CALL_LOOP_ANCHOR not in loop_before:
            raise RuntimeError(
                "Hermes 会话循环缺少 XML 工具调用桥接锚点；上游实现可能已变化，拒绝盲目补丁"
            )
        bridge = '''            # scribe3-managed: xml-tool-call-bridge v1
            # TokenPlan/Qwen 的 XML 调用先严格还原；未通过白名单的文本保持可见且不可执行。
            if not assistant_message.tool_calls:
                from agent.scribe3_xml_tool_calls import extract_xml_tool_calls
                _scribe3_xml_calls, _scribe3_visible_text = extract_xml_tool_calls(
                    getattr(assistant_message, "content", None),
                    allowed_names=agent.valid_tool_names,
                )
                if _scribe3_xml_calls:
                    assistant_message.tool_calls = _scribe3_xml_calls
                    assistant_message.content = _scribe3_visible_text

'''
        loop_after = loop_before.replace(_XML_TOOL_CALL_LOOP_ANCHOR,
                                         bridge + _XML_TOOL_CALL_LOOP_ANCHOR, 1)

    changes = int(parser_before != source_text) + int(loop_before != loop_after)
    if not changes:
        print("  ✅ [TokenPlan XML bridge] 已同步(幂等)")
        return 0
    print(f"  · [TokenPlan XML bridge] {changes} 处将同步" + ("" if commit else " (dry-run)"))
    if not commit:
        return changes

    agent_dir.mkdir(parents=True, exist_ok=True)
    if parser_before != source_text:
        if target_parser.exists():
            backup = target_parser.with_name(target_parser.name + f".bak.scribe3-xml-{int(time.time() * 1000)}")
            shutil.copy2(target_parser, backup)
            print(f"    解析器备份 → {backup.name}")
        target_parser.write_text(source_text, encoding="utf-8")
    if loop_before != loop_after:
        backup = target_loop.with_name(target_loop.name + f".bak.scribe3-xml-{int(time.time() * 1000)}")
        shutil.copy2(target_loop, backup)
        target_loop.write_text(loop_after, encoding="utf-8")
        print(f"    会话循环备份 → {backup.name}")
    return changes


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """把 overlay 深合并进 base 的副本:dict 递归合并,其它类型(含 list)直接被 overlay 覆盖。
    list 覆盖而非追加是刻意的——工具白名单 / platform_toolsets 要精确强制(删掉的工具要真消失)。"""
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _run_mcp_path(repo: Path) -> str:
    return str(repo / "scribe3" / "run_mcp.sh")


def _build_overlay(profile: str, repo: Path) -> dict:
    overlay_file, _, inject_mcp, _ = _PROFILES[profile]
    overlay = _load_yaml(_DEPLOY_DIR / overlay_file)
    if inject_mcp:
        mcp = _load_yaml(_DEPLOY_DIR / "mcp_servers.yaml")
        allowed = _PROFILE_MCP_SERVERS[profile]
        mcp = {name: mcp[name] for name in allowed}
        run_mcp = _run_mcp_path(repo)
        for server in mcp.values():
            if isinstance(server, dict) and server.get("command") == "{{RUN_MCP}}":
                server["command"] = run_mcp
        overlay["mcp_servers"] = mcp
    return overlay


def _assert_invariants(profile: str, merged: dict) -> list[str]:
    """返回违规列表(空=通过)。这些是【写库前】的硬门,不满足则拒绝写(fail-closed)。"""
    violations = []
    if profile == "default":
        api = ((merged.get("platform_toolsets") or {}).get("api_server")) or []
        if api:
            violations.append(f"默认 profile 的 api_server 工具面非空({api})——速答不得挂任何工具(U-006)")
    elif profile in _PROFILE_MCP_SERVERS:
        api = ((merged.get("platform_toolsets") or {}).get("api_server")) or []
        expected = list(_PROFILE_MCP_SERVERS[profile])
        configured_servers = set((merged.get("mcp_servers") or {}).keys())
        if list(api) != expected or any(name not in configured_servers for name in api):
            violations.append(
                f"{profile}.platform_toolsets.api_server 必须引用当前 mcp_servers 裸键"
                f"({expected})，实际为 {api}；禁止使用 mcp-* 兼容别名"
            )
    # 任何 profile:mcp server 的 include 里绝无 *_reveal(U-003)
    for sname, server in (merged.get("mcp_servers") or {}).items():
        if not isinstance(server, dict):
            continue
        include = (((server.get("tools") or {}) if isinstance(server.get("tools"), dict) else {})
                   .get("include")) or []
        reveal = [t for t in include if str(t).endswith(REVEAL_SUFFIX)]
        if reveal:
            violations.append(f"{sname}.include 含 *_reveal 全知工具({reveal})——挂网关即泄密(U-003)")
    return violations


def _diff_keys(before: dict, after: dict, prefix="") -> list[str]:
    """只报 scribe3 关心的键的变化(平铺路径),不刷屏整份 config。"""
    changes = []
    owned = ("platform_toolsets", "platforms", "mcp_servers", "mcp_discovery_timeout",
             "fallback_providers", "agent")
    keys = owned if prefix == "" else sorted(set(before) | set(after))
    for k in keys:
        b, a = before.get(k), after.get(k)
        if b == a:
            continue
        path = f"{prefix}{k}"
        if isinstance(b, dict) and isinstance(a, dict):
            changes.extend(_diff_keys(b, a, path + "."))
        elif isinstance(b, list) and isinstance(a, list):
            added = [x for x in a if x not in b]
            removed = [x for x in b if x not in a]
            parts = []
            if added:
                parts.append("+" + ", ".join(map(str, added)))
            if removed:
                parts.append("-" + ", ".join(map(str, removed)))
            changes.append(f"  {path}: {'; '.join(parts) if parts else f'{b!r} → {a!r}'}")
        else:
            changes.append(f"  {path}: {b!r} → {a!r}")
    return changes


def _sync_profile_api_port_env(hermes_home: Path, profile: str, overlay: dict, *, commit: bool) -> bool:
    """将 Hermes 优先级更高的 ``API_SERVER_PORT`` 与受管 YAML 端口对齐。

    只替换这一枚非秘密基础设施键；providers/API key/其它用户环境变量字节保持原样。
    """
    if profile == "default":
        return False
    port = (((overlay.get("platforms") or {}).get("api_server") or {}).get("port"))
    if not isinstance(port, int) or port <= 0:
        return False
    path = hermes_home / "profiles" / profile / ".env"
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    line = f"API_SERVER_PORT={port}"
    if re.search(r"(?m)^API_SERVER_PORT=.*$", before):
        after = re.sub(r"(?m)^API_SERVER_PORT=.*$", line, before)
    else:
        after = before + ("" if not before or before.endswith("\n") else "\n") + line + "\n"
    if after == before:
        return False
    print(f"    API_SERVER_PORT: 已同步为 {port}" + ("" if commit else " (dry-run)"))
    if commit:
        if path.exists():
            backup = path.with_name(path.name + f".bak.{int(time.time() * 1000)}")
            shutil.copy2(path, backup)
            print(f"    .env 备份 → {backup.name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after, encoding="utf-8")
    return True


def provision(hermes_home: Path, repo: Path, *, commit: bool,
              profiles: tuple[str, ...] | None = None,
              sync_crons: bool = True,
              install_xml_tool_call_bridge: bool = False,
              install_mcp_closed_resource_recovery: bool = False,
              install_mcp_watchdog_parent_identity: bool = False) -> dict:
    """将声明式 overlay 叠加到指定 profile。

    ``profiles=None`` 保持全量同步兼容；增量部署必须显式给出 profile，并可关闭
    cron 同步，避免一个阶段网关上线顺带改变无关运维状态。
    """
    if not _DEPLOY_DIR.exists():
        raise SystemExit(f"模板目录不存在: {_DEPLOY_DIR}")
    selected_profiles = tuple(profiles) if profiles is not None else tuple(_PROFILES)
    if not selected_profiles:
        raise ValueError("至少指定一个 Hermes profile")
    unknown_profiles = sorted(set(selected_profiles) - set(_PROFILES))
    if unknown_profiles:
        raise ValueError(f"未知 Hermes profile: {', '.join(unknown_profiles)}")
    # 先验证/应用 Hermes 上游补丁；否则不开始修改 profile 配置，避免 TOCTOU。
    total_changes = 0
    if install_xml_tool_call_bridge:
        _sync_xml_tool_call_bridge(hermes_home, repo, commit=False)
    if install_mcp_closed_resource_recovery:
        total_changes += _sync_mcp_closed_resource_recovery(
            hermes_home, commit=commit
        )
    if install_mcp_watchdog_parent_identity:
        total_changes += _sync_mcp_watchdog_parent_identity(
            hermes_home, commit=commit
        )
    run_mcp = Path(_run_mcp_path(repo))
    print(f"  HERMES_HOME: {hermes_home}")
    print(f"  repo:        {repo}")
    print(f"  run_mcp.sh:  {run_mcp}  {'✅存在' if run_mcp.exists() else '⚠不存在(路径对不对?)'}")
    print(f"  模式:        {'COMMIT(真写)' if commit else 'DRY-RUN(只看不写)'}")
    print("  " + "=" * 60)

    all_ok = True
    for profile in selected_profiles:
        _, rel, _, soul_tpl = _PROFILES[profile]
        target = hermes_home / rel
        before = _load_yaml(target)
        overlay = _build_overlay(profile, repo)
        after = _deep_merge(before, overlay)
        # mcp_servers 是 Scribe 拥有的完整权限清单；深合并会保留旧 server，
        # 而 Hermes 会把它们全部注册，故这里必须以阶段白名单整体替换。
        if profile in _PROFILE_MCP_SERVERS:
            after["mcp_servers"] = copy.deepcopy(overlay["mcp_servers"])

        violations = _assert_invariants(profile, after)
        if violations:
            all_ok = False
            print(f"  ❌ [{profile}] 安全不变量违规,拒绝写入:")
            for v in violations:
                print(f"       {v}")
            continue

        changes = _diff_keys(before, after)
        soul_change = _soul_status(hermes_home, rel, soul_tpl)
        if not changes and not soul_change:
            print(f"  ✅ [{profile}] 已合模板,无变更(幂等)")
            if _sync_profile_api_port_env(hermes_home, profile, overlay, commit=commit):
                total_changes += 1
            continue
        total_changes += len(changes)
        print(f"  · [{profile}] {target}")
        for c in changes:
            print(c)
        if soul_change:
            print(f"    {soul_change}")

        if commit:
            if before:   # 已存在才备份(空=新建无可备)
                bak = target.with_suffix(target.suffix + f".bak.{int(time.time() * 1000)}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, bak)
                print(f"    备份 → {bak.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(yaml.safe_dump(after, allow_unicode=True, sort_keys=False),
                              encoding="utf-8")
            _write_soul_if_missing(hermes_home, rel, soul_tpl)
            print("    ✅ 已写入")
        if _sync_profile_api_port_env(hermes_home, profile, overlay, commit=commit):
            total_changes += 1

    if sync_crons:
        _sync_crons(hermes_home, commit=commit)

    print("  " + "=" * 60)
    if not all_ok:
        print("  ⛔ 存在安全不变量违规,未全部写入。修模板后重跑。")
        return {"ok": False}
    if install_xml_tool_call_bridge:
        total_changes += _sync_xml_tool_call_bridge(hermes_home, repo, commit=commit)
    if commit:
        print("  ✅ provision 完成。")
    else:
        print(f"  DRY-RUN:共 {total_changes} 处将变更。加 --commit 真写。")
    return {"ok": True, "changes": total_changes}


def _sync_crons(hermes_home: Path, *, commit: bool) -> None:
    """P2:cron 任务声明式同步(deploy/hermes/crons.yaml + scripts/)。

    幂等纪律:按 name 匹配——`hermes cron list` 里已存在的任务绝不动(可能有用户手工调优);
    只创建缺失的。脚本拷到 ~/.hermes/scripts/(--no-agent 哨兵:空 stdout=静默,失败才响)。
    dry-run 零副作用(不 subprocess、不写文件),测试可安全跑。"""
    cfg = _load_yaml(_DEPLOY_DIR / "crons.yaml")
    jobs = (cfg or {}).get("jobs") or []
    if not jobs:
        return
    scripts_src = _DEPLOY_DIR / "scripts"
    if not commit:
        for j in jobs:
            print(f"  · [cron] 计划(dry-run):{j['name']} @ {j['schedule']} script={j['script']}")
        return
    # 1) 脚本落位(内容一致即跳过)
    sdir = hermes_home / "scripts"
    for f in sorted(scripts_src.glob("*.sh")):
        tgt = sdir / f.name
        if tgt.exists() and tgt.read_text(encoding="utf-8") == f.read_text(encoding="utf-8"):
            print(f"  ✅ [cron脚本] {f.name} 已同步")
            continue
        sdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, tgt)
        tgt.chmod(0o755)
        print(f"  ✅ [cron脚本] {f.name} 已写入")
    # 2) 任务注册(name 幂等;list 失败如实报,不静默跳过)
    try:
        existing = subprocess.run(["hermes", "cron", "list"], capture_output=True,
                                  text=True, timeout=30).stdout
    except Exception as e:
        print(f"  ❌ hermes cron list 失败({e})——脚本已就位,任务需手动 create(命令见 crons.yaml)")
        return
    for j in jobs:
        name = j["name"]
        if name in existing:
            print(f"  ✅ [cron] {name} 已存在(幂等跳过,不覆盖)")
            continue
        cmd = ["hermes", "cron", "create", j["schedule"], "--name", name,
               "--script", j["script"], "--deliver", j.get("deliver", "local")]
        if j.get("no_agent", True):
            cmd.append("--no-agent")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            print(f"  ❌ [cron] {name} 创建失败:{(r.stderr or r.stdout).strip()[:200]}")
        else:
            print(f"  ✅ [cron] {name} 已创建({j['schedule']})")


def _soul_dir(hermes_home: Path, rel: str) -> Path:
    return (hermes_home / rel).parent


def _soul_status(hermes_home: Path, rel: str, soul_tpl: str | None) -> str:
    if not soul_tpl:
        return ""
    dst = _soul_dir(hermes_home, rel) / "SOUL.md"
    if dst.exists():
        return ""   # 不覆盖既有身份(可能有你的调优)
    return f"SOUL.md 缺失 → 将写入主编身份模板({soul_tpl})"


def _write_soul_if_missing(hermes_home: Path, rel: str, soul_tpl: str | None) -> None:
    if not soul_tpl:
        return
    dst = _soul_dir(hermes_home, rel) / "SOUL.md"
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_DEPLOY_DIR / soul_tpl, dst)


def _detect_repo() -> Path:
    # 本文件在 <repo>/scribe3/scripts/provision_hermes.py
    return Path(__file__).resolve().parent.parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser(description="叠加 scribe3 Hermes 网关配置(可复现部署)")
    ap.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
    ap.add_argument("--repo", default=None, help="scribe3 repo 根(缺省自动探测)")
    ap.add_argument("--commit", action="store_true", help="真写(缺省 dry-run)")
    ap.add_argument("--profile", action="append", choices=sorted(_PROFILES),
                    help="仅同步此 profile；可重复指定。缺省同步全部受管 profile")
    ap.add_argument("--skip-crons", action="store_true",
                    help="不处理 cron；阶段 profile 的最小增量部署使用此项")
    ap.add_argument("--install-xml-tool-call-bridge", action="store_true",
                    help="为 TokenPlan/Qwen 安装受管 XML→Hermes tool_calls 兼容桥")
    ap.add_argument("--install-mcp-closed-resource-recovery", action="store_true",
                    help="为 Hermes 0.18.2 安装受管 stdio 关闭资源重连补丁")
    ap.add_argument("--install-mcp-watchdog-parent-identity", action="store_true",
                    help="为 Hermes 0.18.2 安装受管 MCP watchdog 父进程身份补丁")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _detect_repo()
    res = provision(Path(args.hermes_home).expanduser(), repo, commit=args.commit,
                    profiles=tuple(args.profile) if args.profile else None,
                    sync_crons=not args.skip_crons,
                    install_xml_tool_call_bridge=args.install_xml_tool_call_bridge,
                    install_mcp_closed_resource_recovery=(
                        args.install_mcp_closed_resource_recovery
                    ),
                    install_mcp_watchdog_parent_identity=(
                        args.install_mcp_watchdog_parent_identity
                    ))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
