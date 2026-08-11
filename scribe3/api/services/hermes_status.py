"""Service helpers extracted from app_impl (architecture split).

Rebound into ``app_impl`` globals via ``_rebind_services()`` for monkeypatch.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from functools import wraps
from queue import Empty, Full, Queue
from typing import Any, Optional


def _listish(value) -> list[str]:
    """Normalize platform_toolsets / tools.include to a flat list of strings.

    Local copy of app_impl._listish so this module works both rebound and
    imported directly (HERMES_HOME mount makes config parse reachable).
    """
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    s = str(value).strip()
    return [s] if s else []


def _hermes_profile_config_summary(profile: str, home=None) -> dict:
    """Return non-secret profile tool-surface facts for runtime diagnostics."""
    from pathlib import Path

    root = Path(home) if home is not None else Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
    # default profile 的 config 是【根】 config.yaml,不在 profiles/default/ 下(Hermes 约定:
    # 根 = 默认 profile,profiles/<name>/ = 具名 profile)。不回落的话 default 恒 ok=False
    # →U-006 的 default_gateway_has_tools 门禁会变成永不触发的假门(2026-07-15 实测踩到)。
    if profile == "default":
        config_path = root / "config.yaml"
    else:
        config_path = root / "profiles" / profile / "config.yaml"
    summary = {
        "profile": profile,
        "config_path": str(config_path),
        "ok": False,
        "api_server_toolsets": [],
        "api_server_mcp_tool_count": 0,
        "api_server_native_toolsets": [],
        "mcp_toolsets": {},
    }
    if not config_path.exists():
        summary["error"] = "profile config not found"
        return summary
    try:
        import yaml
    except Exception as exc:
        summary["error"] = f"yaml unavailable: {type(exc).__name__}"
        return summary
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        summary["error"] = f"config parse failed: {str(exc)[:120]}"
        return summary

    mcp_servers = cfg.get("mcp_servers") or {}
    if isinstance(mcp_servers, dict):
        for name, server in mcp_servers.items():
            if not isinstance(server, dict):
                continue
            tools = server.get("tools") if isinstance(server.get("tools"), dict) else {}
            include = _listish((tools or {}).get("include"))
            summary["mcp_toolsets"][str(name)] = {
                "enabled": bool(server.get("enabled", True)),
                "tool_count": len(include),
                "tools": include,
            }

    platform_toolsets = cfg.get("platform_toolsets") or {}
    api_server = []
    if isinstance(platform_toolsets, dict):
        api_server = _listish(platform_toolsets.get("api_server"))
    summary["api_server_toolsets"] = api_server
    # Hermes 既兼容 ``mcp-<name>`` 运行时别名，也接受直接引用
    # ``mcp_servers.<name>`` 裸键。诊断必须同时识别两种形态，否则写网关
    # 实际已调用 MCP，这里却会误报“0 工具 + 原生工具面”。
    def _mcp_server_name(toolset: str) -> str | None:
        if toolset in summary["mcp_toolsets"]:
            return toolset
        return toolset.removeprefix("mcp-") if toolset.startswith("mcp-") else None

    summary["api_server_mcp_tool_count"] = sum(
        summary["mcp_toolsets"][server_name]["tool_count"]
        for name in api_server
        if (server_name := _mcp_server_name(name)) in summary["mcp_toolsets"]
    )
    summary["api_server_native_toolsets"] = [
        name for name in api_server
        if _mcp_server_name(name) not in summary["mcp_toolsets"]
    ]
    summary["ok"] = True
    return summary


def _hermes_cron_status(profile: str = "scribe3", *, timeout: float = 3.0) -> dict:
    """Best-effort ops snapshot. Failure must not make runtime status unusable."""
    import subprocess

    status = {
        "checked": False,
        "profile": profile,
        "gateway_running": False,
        "active_jobs": None,
        "scribe3_qc": {"present": False, "active": False, "last_status": None},
    }
    try:
        stat = subprocess.run(
            ["hermes", "-p", profile, "cron", "status"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        listing = subprocess.run(
            ["hermes", "-p", profile, "cron", "list"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        status["error"] = str(exc)[:160]
        return status

    status["checked"] = True
    status_text = (stat.stdout or "") + "\n" + (stat.stderr or "")
    list_text = (listing.stdout or "") + "\n" + (listing.stderr or "")
    status["gateway_running"] = "Gateway is running" in status_text
    m = re.search(r"(\d+)\s+active job", status_text)
    if m:
        status["active_jobs"] = int(m.group(1))
    if "scribe3-体检" in list_text:
        status["scribe3_qc"]["present"] = True
        # The job id line carries [active] immediately before the Name line in Hermes list output.
        idx = list_text.find("scribe3-体检")
        nearby = list_text[max(0, idx - 160): idx + 240]
        status["scribe3_qc"]["active"] = "[active]" in nearby
        job_tail = list_text[idx:]
        last = re.search(r"Last run:\s+.*?\s+([A-Za-z_ -]+)\s*(?:\n|$)", job_tail)
        if last:
            status["scribe3_qc"]["last_status"] = last.group(1).strip()
    return status


def _profile_by_name(profiles: list[dict], name: str, fallback_index: int | None = None) -> dict:
    for profile in profiles:
        if profile.get("profile") == name:
            return profile
    if fallback_index is not None and len(profiles) > fallback_index:
        return profiles[fallback_index]
    return {}


def _profile_has_skill(profile: dict, skill_name: str) -> bool:
    return any((skill or {}).get("name") == skill_name for skill in (profile.get("skills") or []))


def _issue(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def _summarize_hermes_runtime(profiles: list[dict], *, profile_configs: dict | None = None,
                              cron: dict | None = None) -> dict:
    configs = profile_configs or {}
    default = _profile_by_name(profiles, "default", 0)
    read = _profile_by_name(profiles, "scribe3", 1)
    write = _profile_by_name(profiles, "scribe3_write", 2)
    read_profile = read.get("profile") or "scribe3"
    write_profile = write.get("profile") or "scribe3_write"
    read_cfg = configs.get(read_profile) or {}
    write_cfg = configs.get(write_profile) or {}

    default_features = default.get("features") or {}
    read_features = read.get("features") or {}
    write_features = write.get("features") or {}
    chat_available = bool(default.get("ok") and default_features.get("chat_completions"))
    read_available = bool(read.get("ok") and read_features.get("responses_api"))
    write_available = bool(
        write.get("ok")
        and write_features.get("run_submission")
        and write_features.get("run_approval_response")
    )
    read_skill_loaded = _profile_has_skill(read, "scribe-novel-v2")
    write_skill_loaded = _profile_has_skill(write, "scribe-novel-v2")
    issues = []
    if not chat_available:
        issues.append(_issue("error", "default_gateway_unavailable", "默认 Hermes 补全网关不可用"))
    if not read_available:
        issues.append(_issue("error", "read_gateway_unavailable", "scribe3 只读 Responses 网关不可用"))
    if not write_available:
        issues.append(_issue("error", "write_gateway_unavailable", "scribe3_write Runs/Approval 写网关不可用"))
    if read_cfg.get("api_server_mcp_tool_count") == 0:
        issues.append(_issue("error", "read_mcp_tools_missing", "只读网关没有启用 scribe3_read MCP 工具面"))
    if write_cfg.get("api_server_mcp_tool_count") == 0:
        issues.append(_issue("error", "write_mcp_tools_missing", "写网关没有启用 scribe3 MCP 工具面"))
    if "mcp-scribe3_write" in (read_cfg.get("api_server_toolsets") or []):
        issues.append(_issue("error", "read_gateway_has_write_tools", "只读网关误启用了写工具面"))
    # U-003 修复(v2,真机实测推翻"CHIEF label 隔离"的上一版方案):Hermes 的
    # server_label 不做过滤——网关把某 profile 挂载的所有 MCP server 工具一律
    # 暴露给每个经该网关的请求,不管请求自称哪个 label。真正的不变量因此不是
    # "某 profile 的顶层 api_server_toolsets 是否等于某个标签",而是:**不管挂在
    # 哪个 profile、哪个 mcp server,只要 include 白名单里出现一把 s3_*_reveal
    # 全知孪生工具(mcp.py,能解锁 secret 明文),这个 profile 服务的任何请求——
    # 包括共用同一网关进程的写作/续写路径——就物理够得着它**。逐 profile、逐
    # mcp server 扫 tools.include(_hermes_profile_config_summary 已读出该列表),
    # 不再比较 label 字符串。
    _reveal_tool_hits = [
        f"{_profile_name}/{_server_name}/{_tool}"
        for _profile_name, _cfg in configs.items()
        for _server_name, _toolset in ((_cfg or {}).get("mcp_toolsets") or {}).items()
        for _tool in (_toolset or {}).get("tools") or []
        if str(_tool).endswith("_reveal")
    ]
    if _reveal_tool_hits:
        issues.append(_issue(
            "error", "gateway_exposes_reveal_tools",
            "网关 include 白名单挂了 *_reveal 全知孪生工具(" + "; ".join(_reveal_tool_hits[:5])
            + ("…" if len(_reveal_tool_hits) > 5 else "")
            + ")——server_label 不做过滤,挂上即等于交给写作/续写路径"))
    if read_cfg.get("api_server_native_toolsets"):
        issues.append(_issue("warning", "read_native_toolsets_enabled", "只读网关启用了非 scribe3 原生工具面"))
    if write_cfg.get("api_server_native_toolsets"):
        issues.append(_issue("warning", "write_native_toolsets_enabled", "写网关启用了非 scribe3 原生工具面"))
    # U-006(2026-07-15):速答/渲染/判官全打默认网关的 /v1/chat/completions。默认 profile
    # 若不显式 platform_toolsets.api_server: [] 就继承全部 toolsets(含 hermes-cli 终端)——
    # 主编速答借此执行了跨仓库 git 提交/push。速答该是纯补全:api_server 工具面必须为空。
    # (Dashboard/CLI 等其他 platform 不经此网关,不受影响。)与上面 native/reveal 门禁同层,
    # 防配置漂回去。default_cfg 缺失/未加载时不误报(装载探测失败已由 default_gateway_unavailable 覆盖)。
    default_profile = default.get("profile") or "default"
    default_cfg = configs.get(default_profile) or {}
    if default_cfg.get("ok") and (default_cfg.get("api_server_toolsets") or []):
        issues.append(_issue(
            "error", "default_gateway_has_tools",
            "速答网关(默认 profile)暴露了工具面(" + "; ".join(
                str(t) for t in (default_cfg.get("api_server_toolsets") or [])[:5])
            + ")——速答应是纯补全;主编可借此执行终端/git 等系统外动作(U-006)"))
    if not (read_skill_loaded or write_skill_loaded):
        issues.append(_issue("warning", "scribe_skill_missing", "scribe-novel-v2 skill 未加载"))
    if cron and cron.get("checked") and not (cron.get("scribe3_qc") or {}).get("present"):
        issues.append(_issue("warning", "scribe3_cron_missing", "scribe3-体检 cron 未注册"))

    return {
        "chat": {
            "profile": default.get("profile") or "default",
            "available": chat_available,
            "version": (default.get("health") or {}).get("version"),
        },
        "read": {
            "profile": read_profile,
            "available": read_available,
            "version": (read.get("health") or {}).get("version"),
            "mcp_toolsets": read_cfg.get("api_server_toolsets") or [],
            "mcp_tool_count": read_cfg.get("api_server_mcp_tool_count") or 0,
            "native_toolsets": read_cfg.get("api_server_native_toolsets") or [],
            "scribe_skill_loaded": read_skill_loaded,
        },
        "write": {
            "profile": write_profile,
            "available": write_available,
            "version": (write.get("health") or {}).get("version"),
            "mcp_toolsets": write_cfg.get("api_server_toolsets") or [],
            "mcp_tool_count": write_cfg.get("api_server_mcp_tool_count") or 0,
            "native_toolsets": write_cfg.get("api_server_native_toolsets") or [],
            "scribe_skill_loaded": write_skill_loaded,
        },
        "cron": cron or {"checked": False},
        "degraded": {
            "chat": not chat_available,
            "read_tools": not read_available,
            "write_runs": not write_available,
        },
        "issues": issues,
    }


def _hermes_runtime_status() -> dict:
    from scribe3.hermes_runtime import HermesRuntime
    from scribe3.hermes_runs_env import (
        HERMES_DEDUCE_PREVIEW_RUNS,
        HERMES_DEDUCE_RUNS,
        HERMES_DRAFT_RUNS,
        HERMES_PLAN_RUNS,
    )
    from scribe3.llm import (
        HERMES,
        HERMES_RESPONSES,
        HERMES_RESPONSES_PROFILE,
        HERMES_RUNS,
        HERMES_RUNS_PROFILE,
    )

    profiles = [
        HermesRuntime(api_base=HERMES, profile="default").probe(),
        HermesRuntime(api_base=HERMES_RESPONSES, profile=HERMES_RESPONSES_PROFILE).probe(),
        HermesRuntime(api_base=HERMES_RUNS, profile=HERMES_RUNS_PROFILE).probe(),
        HermesRuntime(api_base=HERMES_DEDUCE_RUNS, profile="scribe3_deduce").probe(),
        HermesRuntime(api_base=HERMES_DEDUCE_PREVIEW_RUNS, profile="scribe3_deduce_preview").probe(),
        HermesRuntime(api_base=HERMES_PLAN_RUNS, profile="scribe3_plan").probe(),
        HermesRuntime(api_base=HERMES_DRAFT_RUNS, profile="scribe3_draft").probe(),
    ]
    profile_configs = {
        "default": _hermes_profile_config_summary("default"),   # U-006:速答网关工具面自检需要
        HERMES_RESPONSES_PROFILE: _hermes_profile_config_summary(HERMES_RESPONSES_PROFILE),
        HERMES_RUNS_PROFILE: _hermes_profile_config_summary(HERMES_RUNS_PROFILE),
        "scribe3_deduce": _hermes_profile_config_summary("scribe3_deduce"),
        "scribe3_deduce_preview": _hermes_profile_config_summary("scribe3_deduce_preview"),
        "scribe3_plan": _hermes_profile_config_summary("scribe3_plan"),
        "scribe3_draft": _hermes_profile_config_summary("scribe3_draft"),
    }
    cron = _hermes_cron_status(HERMES_RESPONSES_PROFILE)
    summary = _summarize_hermes_runtime(profiles, profile_configs=profile_configs, cron=cron)
    has_error = any(issue.get("severity") == "error" for issue in summary["issues"])
    # Task 9:捕获管线工作者失败不阻断对话,但对 runtime-status 可见(留 outbox failed 计数)。
    mem_capture = {"failed_events": 0}
    try:
        mem_capture["failed_events"] = _store_for("main").count_failed_memory_events()
    except Exception:
        mem_capture["error"] = "count_failed_memory_events 不可用"
    # Task 16-B:统一上下文/记忆运行指标块(真实值 + 待接线骨架,绝不含 prompt/秘密)。
    try:
        context_memory = _context_memory_metrics()
    except Exception:
        context_memory = {"error": "context_memory 指标不可用"}
    return {
        "ok": all(p.get("ok") for p in profiles) and not has_error,
        "profiles": profiles,
        "profile_configs": profile_configs,
        "cron": cron,
        "summary": summary,
        "memory_capture": mem_capture,
        "context_memory": context_memory,
    }


def _hermes_runs_runtime(policy=None):
    """按受控阶段策略选择 Runs gateway；调用方不能指定 profile 或 URL。"""
    from scribe3.hermes_runtime import HermesRuntime
    from scribe3.hermes_runs_env import hermes_runs_api_base_for_env
    from scribe3.llm import HERMES_RUNS, HERMES_RUNS_PROFILE
    if policy is not None:
        try:
            api_base = hermes_runs_api_base_for_env(policy.api_env)
        except KeyError as exc:
            raise RuntimeError(f"unconfigured run stage policy: {policy.phase}") from exc
        return HermesRuntime(api_base=api_base, profile=policy.profile)
    return HermesRuntime(api_base=HERMES_RUNS, profile=HERMES_RUNS_PROFILE)


def _run_session_key(work: str, scope: str = "runs") -> str:
    # Run 需与讨论线程隔离；同一章节阶段可续接，不同阶段绝不共享工具轨迹，
    # 以免演绎任务继承正文/设定任务的长上下文后工具游走。
    from scribe3.hermes_runtime import scribe3_session_key
    return scribe3_session_key(_normalize_work(work), scope=scope or "runs")


def _gateway_security_violations(home=None) -> list[str]:
    """启动守卫的判据:纯读 Hermes profile config 文件(不走网络),检查安全不变量。

    与 _summarize_hermes_runtime 的运行时门禁同源,但轻量(无探针)、可在启动早期跑:
      ① 默认 profile(:8642 速答/渲染/判官)api_server 工具面必须为空(U-006)。
      ② 任何 profile 的任何 mcp server include 里绝无 *_reveal 全知工具(U-003)。
    config 读不到(如全新机器还没 provision)→ 不报 violation(交给部署流程/运行时门禁),
    这里只对【确凿能读到且确实违规】的配置发声,避免 dev/test 环境误伤。
    """
    violations = []
    default_cfg = _hermes_profile_config_summary("default", home=home)
    if default_cfg.get("ok") and (default_cfg.get("api_server_toolsets") or []):
        violations.append(
            "默认网关(:8642 速答)暴露了工具面 "
            f"{default_cfg.get('api_server_toolsets')} —— 主编速答可借此执行终端/git 等系统外动作"
            "(U-006)。跑 `python -m scribe3.scripts.provision_hermes --commit` 修复。")
    for prof in ("default", "scribe3", "scribe3_write"):
        cfg = _hermes_profile_config_summary(prof, home=home)
        if not cfg.get("ok"):
            continue
        for sname, toolset in (cfg.get("mcp_toolsets") or {}).items():
            reveal = [t for t in (toolset or {}).get("tools") or [] if str(t).endswith("_reveal")]
            if reveal:
                violations.append(
                    f"{prof}/{sname} 挂了 *_reveal 全知工具 {reveal} —— server_label 不过滤,"
                    "挂网关即等于交给写作/续写路径(U-003)。")
    return violations


def _startup_gateway_guard():
    """部署到任何地方的最后一道防线:即便有人跳过 provision 或配置漂了,后端一启动就发现。
    只在真 uvicorn 启动时触发(不在 import/测试时)。默认响亮 CRITICAL 日志;
    生产可设 SCRIBE3_STRICT_GATEWAY_GUARD=1 让配置违规直接 fail-fast(拒绝起服务)。"""
    try:
        violations = _gateway_security_violations()
    except Exception:
        logging.getLogger("scribe3").warning("网关安全守卫自检异常(忽略,不阻断启动)", exc_info=True)
        return
    if not violations:
        return
    log = logging.getLogger("scribe3")
    for v in violations:
        log.critical("🚨 网关安全不变量违规:%s", v)
    strict = os.environ.get("SCRIBE3_STRICT_GATEWAY_GUARD", "").strip().lower() in ("1", "true", "yes", "on")
    if strict:
        raise RuntimeError(
            "SCRIBE3_STRICT_GATEWAY_GUARD=1 且网关安全不变量违规,拒绝启动。违规:\n- "
            + "\n- ".join(violations))

