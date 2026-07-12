"""scribe3 后端 API(FastAPI,端口 3321)· 多书(一书一 DB)。

每端点按 ?work=<slug> 路由到对应书的 DB(NS=scribe3 / db=slug),store 按书缓存。
/works 列表/新建。读端点直查;写作走主编对话(/chat/write),不经 /render 直渲。生成走 Hermes。
与 scribe2 后端 3320 隔离(3321)。

写授权契约(P02):
- REST 写端点 = 作者可信通道(全权,含 secret)。作者直编,不经待批。
- MCP 写工具 = agent 受限通道(经 elicitation 待批,commit_if_approved)。
- 新增写端点必须显式登记在 _check_write_paths 白名单,测试守护不漂移。
"""
from __future__ import annotations

import json
import hashlib
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque

import httpx
from fastapi import (
    BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from scribe3.context_models import NavigationIntent, StaleContextError
from scribe3.context_service import (
    ContextService, ContextServiceError, ContextWorkMismatch,
)
from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.live import live_stream
from scribe3.ontology import Entity, Fact
from scribe3.store import (
    MATERIAL_KINDS, OVERDUE_SLACK, SurrealStore, _overdue_flag, create_work,
    delete_work, list_works, rename_work,
)
from scribe3.verify import causal_complete

from scribe3 import settings as _settings
_settings.apply_restart_overrides()   # restart 类 DB 覆盖灌 env,必须在 CORS/token 读取前

app = FastAPI(title="scribe3")
_CORS = os.environ.get("SCRIBE3_CORS_ORIGINS", "http://127.0.0.1:3311,http://localhost:3311")

# P3-e1 Fix 1 / 批C D-3+H-1:overdue 阈值单源——常量定义在 store.py(OVERDUE_SLACK),
# app / health cron / timeline 均从 store 导入同一份,杜绝口径漂移(前端从 /quality 消费,不重算)。
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _CORS.split(",") if o.strip()],
                   allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])

# P01: 可选 bearer token 认证(本地不设 env=放行;暴露=设 SCRIBE3_API_TOKEN 强制)
_API_TOKEN = os.environ.get("SCRIBE3_API_TOKEN")


@app.middleware("http")
async def _auth_middleware(request, call_next):
    if _API_TOKEN and not request.url.path.startswith("/health"):
        auth = request.headers.get("authorization", "")
        import hmac
        if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:].strip(), _API_TOKEN):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "invalid token"})
    return await call_next(request)

_STORE_CACHE_MAX = 8
_stores: OrderedDict[str, SurrealStore] = OrderedDict()
_complete_fn = None

# P0-1: 同章 ingest 去重——(work,seq) 在途集合。防"存为正文"双触发
# (save-chapter 排一个 + checkpoint(final) 又排一个)对同章并发 purge→抽取→写,
# 造成 knows/reader_knows/char_state/motif_instance/promise_touch 双份或互删。
# 排队前查此集合:同 (work,seq) 已在途/在排则跳过第二次;标记在 _bg_ingest 完成时清除。
# ⚠ 单 worker 依赖:此为模块级进程内 set,仅在单 worker 部署下有效(自动 _bg_ingest 与
#   手动 /ingest 同进程共享此集合去重)。上多 worker(多进程/多机)前必须改为跨进程去重
#   (如 SurrealDB 上的在途锁行 / Redis SETNX),否则同章 ingest 会跨进程交错。
_pending_ingest: set[tuple[str, int]] = set()
_pending_ingest_lock = threading.Lock()
# P0门审查 P1-3:loop 同章互斥(并发两次 POST /loop/chapter 同章 → 双生成/双落库/双 ingest)
_loop_inflight: set[tuple[str, int]] = set()
_loop_inflight_lock = threading.Lock()

# 遗留处置 1-A:S1 熔断(三重防误杀之三)——最近 10 次 loop 中由 S1(findings_schema)
# 触发 blocking 的比例 >30%(样本≥5)→ 暂停共振升格并在响应标注(宁可漏不可磨;
# 检测器错杀由盲评池人工裁决后再调共振表)。进程内状态,重启清零(熔断是保护不是账本)。
_s1_recent: dict[str, deque] = {}


def _s1_circuit_open(work: str) -> bool:
    d = _s1_recent.get(work)
    return bool(d) and len(d) >= 5 and (sum(d) / len(d)) > 0.3


def _s1_record(work: str, s1_triggered: bool) -> None:
    _s1_recent.setdefault(work, deque(maxlen=10)).append(bool(s1_triggered))

# P28 限流三件套裁决(审计 P1-12,方案原文"接线或删除二选一"):
# 日调用帽下沉到 llm.py 单点接线(所有 LLM 出口:complete/stream/responses);
# _sema 并发闸(asyncio,与同步 httpx 调用形态不符)与 CircuitBreaker(持续故障
# 熔断,0.18 网关自身有重试/排队)删除——见台账 D-029。


def set_store(store, work: str = "main") -> None:
    """测试注入某书的 store。"""
    _stores[work] = store


def set_complete_fn(fn) -> None:
    global _complete_fn
    _complete_fn = fn


def _store_for(work: str) -> SurrealStore:
    if work not in _stores:
        st = SurrealStore(ns="scribe3", db=work)
        st.apply_schema()
        _stores[work] = st
        while len(_stores) > _STORE_CACHE_MAX:
            _, old = _stores.popitem(last=False)
            old.close()
    else:
        _stores.move_to_end(work)
    return _stores[work]


_OBJECT_PREFIX = {"role": "role", "fact": "fact"}


def _normalize_lifecycle_id(object_type: str, object_id: str) -> str:
    if object_type == "material":
        return object_id
    prefix = _OBJECT_PREFIX.get(object_type)
    if not prefix:
        raise HTTPException(status_code=404, detail=f"unsupported object type '{object_type}'")
    return object_id if object_id.startswith(prefix + ":") else f"{prefix}:{object_id}"


def _impact_token(work: str, object_type: str, object_id: str, references: list[dict]) -> str:
    raw = json.dumps(
        {"work": work, "type": object_type, "id": object_id, "references": references},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _object_impact(st: SurrealStore, object_type: str, object_id: str, work: str) -> dict:
    normalized = _normalize_lifecycle_id(object_type, object_id)
    if object_type == "material":
        raw = st.material_lifecycle_impact(normalized)
    else:
        raw = st.record_lifecycle_impact(normalized)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"{object_type} '{object_id}' 不存在")
    references = [
        {"kind": kind, "count": count}
        for kind, count in sorted((raw.get("counts") or {}).items())
        if count
    ]
    payload = {
        "object": {
            "type": object_type,
            "id": normalized,
            "label": raw["object"].get("label") or normalized,
        },
        "references": references,
        "recommended_action": "archive" if references else "hard_delete_allowed",
    }
    payload["confirm_impact_token"] = _impact_token(work, object_type, normalized, references)
    return payload


def _delete_object_with_lifecycle(st: SurrealStore, object_type: str, object_id: str,
                                  work: str, confirm_impact_token: str | None):
    impact = _object_impact(st, object_type, object_id, work)
    has_refs = any((r.get("count") or 0) > 0 for r in impact["references"])
    if has_refs and confirm_impact_token != impact["confirm_impact_token"]:
        return JSONResponse(status_code=409, content=impact)
    normalized = impact["object"]["id"]
    if object_type == "material":
        ok = st.delete_material(normalized, cleanup_refs=True)
    else:
        ok = st.delete_record(normalized, cleanup_refs=True)
    if not ok:
        raise HTTPException(status_code=404, detail=f"{object_type} '{object_id}' 不存在")
    return {"ok": True, "impact": impact}


def _archive_object_with_lifecycle(st: SurrealStore, object_type: str, object_id: str, work: str):
    impact = _object_impact(st, object_type, object_id, work)
    normalized = impact["object"]["id"]
    if object_type == "material":
        ok = st.update_material(normalized, {"archived": True})
    else:
        if st.exists(normalized):
            st.update_record(normalized, {"archived": True})
            ok = True
        else:
            ok = False
    if not ok:
        raise HTTPException(status_code=404, detail=f"{object_type} '{object_id}' 不存在")
    return {"ok": True, "object": impact["object"], "impact": impact}


def _work_has_tools(work: str) -> bool:
    """当前请求是否可挂 s3_ MCP 工具。

    H-01 后 mcp.py 的所有 s3_ 工具都支持显式 work 参数,同一 MCP 进程按书缓存
    SurrealStore。故不再用 SCRIBE3_WORK 禁掉非默认书;防串库责任转为提示层硬约束:
    所有 s3_ 调用必须传当前 work。"""
    return True


def _normalize_work(work: str | None) -> str:
    return (work or os.environ.get("SCRIBE3_WORK", "main")).strip() or "main"


def _s3_work_scope_block(work: str | None) -> str:
    w = _normalize_work(work)
    return (
        f"\n\n【s3_ 工具作用域·硬约束】当前作品 slug: work={w}。"
        f"调用任何 s3_ 工具时必须显式传 `work` 参数,值固定为 \"{w}\";"
        "只读工具和写入待批工具都一样。不得省略 work,不得改成 SCRIBE3_WORK/default/main,"
        "避免跨书读取或写入。"
    )


def _hermes_session_key(work: str, thread_id: str, chapter: int | None = None) -> str:
    """稳定 session key 只含 work + thread —— 导航切章不换 Hermes session,主编历史连续(Task 11)。

    为什么删 chapter:章/阶段/焦点只存 ContextEnvelope.focus,不再用 session key 切断主编历史。
    LRU 100 掉链是常态,掉链后由 Scribe 侧 thread messages + working summary 重建,不依赖
    Hermes 端无限续接。chapter 形参保留只为语义显式(调用点可传当前章),函数内丢弃不参与拼 key。
    格式经 scribe3_session_key 单一源拼串(Minor #6 防漂移)。"""
    del chapter
    from scribe3.hermes_runtime import scribe3_session_key
    return scribe3_session_key(work, thread_id=thread_id)


def _editor_turn_context(work: str, actor_id: str = "author"):
    """组装本轮主编 turn 的会话连续上下文(Task 11 产出 HermesTurnContext)。

    thread_id 取本 work 的稳定主编线程(get_or_create_editorial_thread,一 work 一连续线程);
    conversation/previous_response 从线程行取(Hermes 会话续接锚,LRU 100 掉链常态);
    context_* 属动态 envelope 层(默认关),此处留空,开启后由 assembler 填。
    fail-soft:线程取数异常则退化为 work 兜底线程名,仍给出稳定 session key,不阻断对话。"""
    from scribe3.hermes_runtime import HermesTurnContext
    w = _normalize_work(work)
    try:
        thread = _store_for(w).get_or_create_editorial_thread(w, actor_id)
        return HermesTurnContext(
            work=w,
            thread_id=thread["thread_id"],
            conversation_id=thread.get("hermes_conversation_id") or None,
            previous_response_id=thread.get("previous_response_id") or None,
        )
    except Exception:
        logging.getLogger("scribe3").warning(
            "editorial thread 取数失败,退化为 work 兜底线程", exc_info=True)
        return HermesTurnContext(work=w, thread_id=w)


def _listish(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, tuple):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value]
    return []


def _hermes_profile_config_summary(profile: str, home=None) -> dict:
    """Return non-secret profile tool-surface facts for runtime diagnostics."""
    from pathlib import Path

    root = Path(home) if home is not None else Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
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
    summary["api_server_mcp_tool_count"] = sum(
        summary["mcp_toolsets"][name]["tool_count"]
        for name in api_server
        if name in summary["mcp_toolsets"]
    )
    summary["api_server_native_toolsets"] = [
        name for name in api_server
        if name not in summary["mcp_toolsets"] and not name.startswith("mcp-")
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
    if "scribe3_write" in (read_cfg.get("api_server_toolsets") or []):
        issues.append(_issue("error", "read_gateway_has_write_tools", "只读网关误启用了写工具面"))
    if read_cfg.get("api_server_native_toolsets"):
        issues.append(_issue("warning", "read_native_toolsets_enabled", "只读网关启用了非 scribe3 原生工具面"))
    if write_cfg.get("api_server_native_toolsets"):
        issues.append(_issue("warning", "write_native_toolsets_enabled", "写网关启用了非 scribe3 原生工具面"))
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


def _flag_enabled(name: str) -> bool:
    """Task 16-B 统一开关判定门面(委托 context_cache.flag_enabled,单一真值来源)。
    每次读 env,默认关 → 系统行为与开关引入前【字节等价】。"""
    from scribe3 import context_cache
    return context_cache.flag_enabled(name)


def _context_memory_metrics(work: str = "main") -> dict:
    """Task 16-B runtime-status 指标块。绝不含原始 prompt / 秘密值——只有计数、
    分位数与布尔/短标识。诚实区分【当前有真实值】与【采集骨架待 16-C 接线】:

    真实值:cross_work_rejections(16-A)、memory_events_pending/failed(store 计数)、
      context_sessions_active(store 计数)、spectron_shadow(detect)、hermes_memory_provider。
    采集骨架(接线后自动填,当前 0/None):retrieval_p50/p95、context_tokens_p95、
      stale_rejections——依赖 16-C 把检索/组装接进生产读路径与 stale 拒绝路径。"""
    from scribe3 import context_cache
    metrics = dict(context_cache.metrics_snapshot())   # 检索/组装侧(当前多为 0/None)
    # 安全指标(16-A 只读快照,不复算)
    metrics["cross_work_rejections"] = get_security_metrics().get("cross_work_rejections", 0)
    # 记忆捕获管线水位(per work,与既有 memory_capture.failed_events 同库口径)
    pending = failed = 0
    sessions = 0
    try:
        st = _store_for(work)
        try:
            pending = st.count_memory_events(status="pending")
        except Exception:
            pending = 0
        try:
            failed = st.count_failed_memory_events()
        except Exception:
            failed = 0
        try:
            sessions = st.count_active_context_sessions()
        except Exception:
            sessions = 0
    except Exception:
        pass
    metrics["memory_events_pending"] = pending
    metrics["memory_events_failed"] = failed
    metrics["context_sessions_active"] = sessions
    # Spectron 影子:只上报开关 + 可用性 + 原因(全无秘密);包未发布时 available=False 是正确态
    try:
        from scribe3.spectron_adapter import detect_spectron
        det = detect_spectron()
        metrics["spectron_shadow"] = {
            "flag": _flag_enabled("SCRIBE3_SPECTRON_SHADOW"),
            "available": bool(det.enabled),
            "reason": det.reason,
        }
    except Exception:
        metrics["spectron_shadow"] = {"flag": _flag_enabled("SCRIBE3_SPECTRON_SHADOW"),
                                      "available": False, "reason": "detect_failed"}
    # 生产记忆提供方:自建多通道检索恒为生产提供方(Spectron 仅影子,永不接管生产读,Task 15)。
    metrics["hermes_memory_provider"] = "scribe3_builtin"
    return metrics


def _hermes_runtime_status() -> dict:
    from scribe3.hermes_runtime import HermesRuntime
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
    ]
    profile_configs = {
        HERMES_RESPONSES_PROFILE: _hermes_profile_config_summary(HERMES_RESPONSES_PROFILE),
        HERMES_RUNS_PROFILE: _hermes_profile_config_summary(HERMES_RUNS_PROFILE),
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


def _hermes_runs_runtime():
    from scribe3.hermes_runtime import HermesRuntime
    from scribe3.llm import HERMES_RUNS, HERMES_RUNS_PROFILE
    return HermesRuntime(api_base=HERMES_RUNS, profile=HERMES_RUNS_PROFILE)


def _run_session_key(work: str) -> str:
    # Runs(写 profile 长任务)与主编讨论线程隔离:稳定 key = work|runs(不随章/线程漂)。
    # 不复用 _hermes_session_key(后者 Task 11 起专指 work+thread 讨论线程),但共用
    # scribe3_session_key 单一格式源(Minor #6 防漂移)。
    from scribe3.hermes_runtime import scribe3_session_key
    return scribe3_session_key(_normalize_work(work), scope="runs")


def _record_ai_run_trace(work: str, run_id: str | None, **fields) -> None:
    if not run_id:
        return
    try:
        _store_for(work).upsert_ai_run_trace(run_id, **fields)
    except Exception:
        logging.getLogger("scribe3").warning("ai_run_trace 落库失败(忽略)", exc_info=True)


def _capture_turn_memory(store, *, work: str, thread_id: str, turn_id: str,
                         text: str, chapter: int | None = None) -> None:
    """Task 9:把本轮作者意图幂等捕获成经验记忆(同步 drain)。

    best-effort:任何失败只告警,绝不阻断写作主链路(与 chat_message 落库同纪律 D-004)。
    幂等:event_id = turn:<turn_id>(同轮重放不重复记)。分类/正典红线/linked_ids 领域反查
    在 MemoryCapture 内;known_from=chapter 在此传入(限知门对捕获记忆生效,防知情倒灌)。

    Task 16-C 对称门控:SCRIBE3_MEMORY_FABRIC_V1【关】(默认)→ 最前零成本短路,不捕获、
    不 embed、不写 memory_event/memory_item —— 与检索侧(_get_write_retriever 返 None)
    同开同关,"记忆织物"关时写作路径【字节等价】,根治"捕获恒开只写不读半空转"。"""
    if not _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1"):
        return
    if not (text or "").strip() or not turn_id:
        return
    try:
        from scribe3.memory_capture import MemoryCapture, turn_event
        MemoryCapture(store).capture_event(turn_event(
            text=text, event_id=f"turn:{turn_id}", work=store.db_name,
            thread_id=thread_id, known_from=chapter))
    except Exception:
        logging.getLogger("scribe3").warning("记忆捕获失败(忽略,不阻断写作)", exc_info=True)


def _record_ai_run_event(work: str, run_id: str, app_ev: dict, *, source: str | None = None) -> None:
    try:
        payload = dict(app_ev or {})
        if source:
            payload["source"] = source
        _store_for(work).append_ai_run_trace_event(run_id, payload)
    except Exception:
        logging.getLogger("scribe3").warning("ai_run_trace event 落库失败(忽略)", exc_info=True)


SCRIBE3_READ_MCP_LABEL = os.environ.get("SCRIBE3_READ_MCP_LABEL", "scribe3_read")


def _response_events_iter(fn, message, instructions: str, **kwargs):
    """Call real Hermes with full runtime kwargs while preserving old test stubs."""
    if _responses_events is None:
        return fn(message, instructions, **kwargs)
    safe = {k: v for k, v in kwargs.items() if k in {"model", "with_tools"}}
    return fn(message, instructions, **safe)


def _fact_item(f, reveal_secret: bool = False) -> dict:
    """命题序列化(单条,列表/单条端点共用)。
    批E-A1 无损化:回全字段 valid_from/valid_to/leak_markers,让前端能整行安全编辑
    (此前只回 value,现有命题只能 supersede/删除)。私密门控:secret 且未解锁时,
    value 与 leak_markers 一并屏蔽——leak_markers 是私密的"破绽词",本身即敏感,
    与 value 同级隐藏。"""
    hide = f.secret and not reveal_secret
    return {
        "id": f.id,
        "entity": f.entity_id,
        "attribute": f.attribute,
        "is_secret": f.secret,
        "value": None if hide else f.value,   # 私密 value 屏蔽,前端只知"此处有私密"
        "valid_from": f.valid_from,
        "valid_to": f.valid_to,
        "leak_markers": [] if hide else list(f.leak_markers or []),
    }


def _facts(fs, reveal_secret: bool = False):
    return [_fact_item(f, reveal_secret) for f in fs]


# 私密字段掩码占位符(唯一真相源):GET 打码用此值,写路径收到此值即视为"未改"(不落库)。
# 前端 F4 防线硬编码同值 '🔒 私密';二者必须一致。
_SECRET_MASK = "🔒 私密"


def _mask_field(row: dict, field: str, secret_field: str, reveal: bool) -> dict:
    """若 row[secret_field] 为 True 且未解锁,将 row[field] 替换为锁占位符。"""
    if row.get(secret_field) and not reveal:
        row = {**row, field: _SECRET_MASK}
    return row


# ===== 书 =====
@app.get("/health")
def health():
    # 审计 #80:真探测——ping 默认书连接(此前纯桩,DB 挂了照样报 ok 假绿)。
    try:
        _store_for("main")._query("RETURN 1")
        return {"ok": True, "ns": "scribe3", "db": "ok"}
    except Exception as e:
        return {"ok": False, "ns": "scribe3", "db": f"down: {str(e)[:80]}"}


@app.get("/ready")
def ready():
    """就绪探针:DB 可达 200,否则 503(部署/看门狗用)。"""
    try:
        _store_for("main")._query("RETURN 1")
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db not ready: {str(e)[:80]}")


@app.get("/ai/runtime-status")
def ai_runtime_status():
    return _hermes_runtime_status()


@app.get("/capabilities")
def capabilities():
    """Task 16-B 灰度能力下发:只读各 feature flag 的 env 状态(不下发任何秘密)。

    前端能力以后端 capabilities 为准——不允许只靠 localStorage 开启未就绪的服务端能力。
    默认全关时各 flag 均 False,系统行为与开关引入前字节等价(capabilities 只上报、不改行为)。
    回滚顺序:inspector → memory retrieval → editorial thread → context snapshot;数据表保留不删。"""
    from scribe3 import context_cache, embed
    return {
        "flags": {
            "snapshot_v1": _flag_enabled("SCRIBE3_CONTEXT_SNAPSHOT_V1"),
            "editorial_thread_v1": _flag_enabled("SCRIBE3_EDITORIAL_THREAD_V1"),
            "memory_fabric_v1": _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1"),
            "context_inspector_v1": _flag_enabled("SCRIBE3_CONTEXT_INSPECTOR_V1"),
            "spectron_shadow": _flag_enabled("SCRIBE3_SPECTRON_SHADOW"),
            # Task 7 既有开关,一并上报(不改语义)
            "assembler_v1": _flag_enabled("SCRIBE3_CONTEXT_ASSEMBLER_V1"),
        },
        "versions": {
            "retrieval_policy": context_cache.RETRIEVAL_POLICY_VERSION,
            "embedding_model": embed.model_version(),
        },
    }


# ── 统一设置中心(spec: docs/superpowers/specs/2026-07-12-settings-center-design.md)──
class SettingPutReq(BaseModel):
    value: object = None


@app.get("/settings")
def settings_all():
    """全量设置:值(secret 掩码)+来源+默认+元数据+pending_restart。只读。"""
    from scribe3 import settings as S
    return {"settings": S.settings_snapshot(),
            "categories": ["connection", "llm", "craft", "flags", "gateway"]}


@app.get("/settings/audit")
def settings_audit(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    # 双侧夹紧在校验层:SQLite 里 LIMIT -1 = 不限量(全表),负数必须 422 而非透传
    from scribe3 import settings_store
    return {"rows": settings_store.audit_rows(limit=limit, offset=offset)}


@app.put("/settings/{key}")
def settings_put(key: str, req: SettingPutReq):
    from scribe3 import settings as S
    try:
        return S.put_setting(key, req.value)
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))


@app.post("/settings/{key}/reset")
def settings_reset(key: str):
    from scribe3 import settings as S
    try:
        S.reset_setting(key)
    except KeyError:
        raise HTTPException(404, f"未登记的设置项: {key}")
    return {"key": key, "status": "reset"}


@app.get("/ai/usage")
def ai_usage(work: str = "main", days: int = 7):
    """H-10 全系统预算面板:日帽(跨进程共享台账)+ token 真实用量(trace 聚合)。

    - cap:计"发起的 LLM 调用笔数"。scope=shared 表示 app 与 MCP 进程同记一本
      SQLite 台账(SCRIBE3_LLM_LEDGER);=process 表示台账故障已回退进程内计数。
    - tokens:Hermes 各响应体回传的真实 usage,按天聚合(Responses/Runs 分列)。
      fail-soft:聚合挂了回空列表带 error,帽信息照常返回。
    """
    from scribe3 import usage as usage_mod
    from scribe3 import llm as llm_mod
    used, scope = usage_mod.used_today()
    try:
        tokens = _store_for(work).usage_summary(days=days)
    except Exception as e:
        tokens = {"days": [], "error": str(e)}
    return {
        "work": work,
        "cap": {"cap": llm_mod._cap(), "used_today": used,
                "remaining": llm_mod.daily_remaining(), "scope": scope},
        "tokens": tokens,
    }


# ---------------------------------------------------------------------------
# Task 13:Runs 审批前重校验"发起时上下文快照"的判据
# ---------------------------------------------------------------------------

def _run_focus_target(focus) -> tuple[str, str] | None:
    """把焦点归一到可比较的写目标 (kind, key):
    - 章/场景 → ('chapter', <章号>)(id 兼容 '9' / 'chapter:9' / 'scene:9:2');
    - entry/view 等中性视图 → None(无具体写目标,不与任何 run 的写目标相交);
    - 其它具名对象(角色/伏笔/事实…) → ('entity', <id>)。
    MVP 判据,可精化:目前按 focus.type/id 粗匹配,足够拦"旧 run 写当前章/条目"。"""
    if not isinstance(focus, dict):
        return None
    ftype = focus.get("type")
    fid = str(focus.get("id") or "").strip()
    if ftype in ("chapter", "scene"):
        # 场景 id 形如 'scene:9:2' / 章 id 形如 'chapter:9' 或裸 '9' → 取章号维度
        parts = [p for p in fid.replace("chapter:", "").replace("scene:", "").split(":") if p]
        return ("chapter", parts[0]) if parts else None
    if ftype in ("entry", "view") or not fid:
        return None
    return ("entity", fid)


def _run_focus_affects(origin_focus, current_focus) -> bool:
    """写目标是否影响当前焦点:同章/同条目 → 影响(True);任一为中性视图或不同目标 → False。
    影响=原审批作废(409 run_context_changed);不影响=可经 approve_stale 二次确认放行。

    I-2 残留风险(如实记账,MVP 判据):只按 (kind,key) 相等判影响,未纳入"下游爆炸半径"——
    过期 run 写其原目标、而作者已导航到相邻/下游章并 approve_stale 放行时,写入可能与作者
    刚写的当前章矛盾(如 origin=promise:7 的伏笔回收会牵动其所属章,但焦点若停在别处则判无关)。
    有 approve_stale 二次确认(作者主动"忽略过期")兜底,故为 Important 非 Critical。
    未把写目标所属章/伏笔归属章纳入判定,是为不过度收紧到"切个章就作废"伤体验;收紧留后续。"""
    o = _run_focus_target(origin_focus)
    c = _run_focus_target(current_focus)
    if o is None or c is None:
        return False
    return o == c


class RunContextChanged(HTTPException):
    """审批重校验失败:发起时快照与当前快照不一致。code 区分两态:
    - run_context_changed:影响当前章/条目 → 原审批作废,须新建 run 重新联查;
    - run_context_stale:无关的过期 run → 前端展示两卡,用户带 approve_stale=true 才执行。"""

    def __init__(self, code: str, *, origin, current, run_id: str):
        super().__init__(status_code=409, detail={
            "code": code,
            "run_id": run_id,
            "origin_context_revision": origin.get("revision"),
            "origin_focus": origin.get("focus"),
            "current_context_revision": current.get("revision"),
            "current_focus": current.get("focus"),
        })


def _recheck_run_origin_context(store, run_id: str, trace: dict, req: "AIRunApprovalReq",
                                choice: str) -> int | None:
    """审批写入前的上下文闸门。返回本次执行绑定的"当前 revision"(供记 completion);
    无 origin 绑定 / deny 时返回 None(跳过校验,现有行为零回归)。

    三结果(计划 Step 4):
    - 未变(origin revision == 当前 session revision,且 session 一致)→ 放行;
    - 已变且影响当前章/条目 → RunContextChanged('run_context_changed');
    - 已变但写目标与当前焦点无关 → 需 approve_stale=true,否则 RunContextChanged('run_context_stale')。

    I-3 fail-closed:origin 已绑定但【核实不了当前快照】(session 缺失/被删/读不到)时,
    绝不回退用审批请求自报的 revision 放行——/ai/runs* 是后端公开面,"核实不了就保守作废"。
    """
    origin_rev = trace.get("origin_context_revision")
    origin_session = trace.get("context_session_id")
    origin_focus = trace.get("focus")
    # deny 永远安全(不写入);无 origin 绑定的存量 run 不做重校验。
    if choice == "deny" or origin_rev is None:
        return None
    origin_snap = {"revision": origin_rev, "focus": origin_focus}
    # I-3:能核实才放行,核实不了(无 session / live 读不到)一律作废,不信任自报值。
    live = store.get_context_snapshot(origin_session) if origin_session else None
    if live is None:
        raise RunContextChanged("run_context_changed", origin=origin_snap,
                                current={"revision": None, "focus": None}, run_id=run_id)
    current_rev = live.get("revision")
    current_focus = live.get("focus")
    # 声明的 session 与发起时不一致 → 按"已变"处理(裁决:对不上按已变,保守作废)。
    session_mismatch = bool(req.context_session_id) and req.context_session_id != origin_session
    if not (session_mismatch or current_rev != origin_rev):
        return current_rev   # 未变
    current_snap = {"revision": current_rev, "focus": current_focus}
    # 换了 session 无法确证写目标相交 → 保守按"影响"作废(写入安全不打折)。
    if session_mismatch or _run_focus_affects(origin_focus, current_focus):
        raise RunContextChanged("run_context_changed", origin=origin_snap,
                                current=current_snap, run_id=run_id)
    if not req.approve_stale:
        raise RunContextChanged("run_context_stale", origin=origin_snap,
                                current=current_snap, run_id=run_id)
    return current_rev


class AIRunCreateReq(BaseModel):
    input: str
    instructions: str = ""
    session_id: str | None = None
    conversation_history: list[dict] | None = None
    previous_response_id: str | None = None
    # Task 13:发起时的上下文绑定(可选)——供审批前重校验"旧 run 拿着过期焦点写入当前章"。
    # 缺省(存量/旧前端)→ 不记 origin binding,审批不被重校验拦截(现有行为零回归)。
    context_session_id: str | None = None
    context_revision: int | None = Field(default=None, ge=0)


class AIRunApprovalReq(BaseModel):
    approval_id: str | None = None
    choice: str | None = None
    decision: str | None = None
    message: str | None = None
    approved: bool | None = None
    # Task 13:审批当刻声明的上下文(前端从当前快照带上);approve_stale=用户看过"发起时/
    # 当前焦点"两卡后仍决定放行"无关的过期 run"的二次确认令牌。
    context_session_id: str | None = None
    context_revision: int | None = Field(default=None, ge=0)
    approve_stale: bool = False


def _hermes_approval_choice(req: AIRunApprovalReq) -> str:
    raw = (req.choice or req.decision or "").strip().lower()
    if not raw and req.approved is not None:
        raw = "approve" if req.approved else "deny"
    aliases = {
        "approve": "once",
        "approved": "once",
        "allow": "once",
        "yes": "once",
        "true": "once",
        "deny": "deny",
        "denied": "deny",
        "reject": "deny",
        "rejected": "deny",
        "no": "deny",
        "false": "deny",
    }
    choice = aliases.get(raw, raw)
    if choice not in {"once", "session", "always", "deny"}:
        raise HTTPException(
            status_code=400,
            detail="invalid approval decision; expected approve/deny or once/session/always/deny",
        )
    return choice


@app.post("/ai/runs")
def ai_run_create(req: AIRunCreateReq, work: str = "main"):
    """创建 Hermes Run。用于需要人类审批/可恢复事件流的 agentic 长任务。"""
    ins = (req.instructions or "").strip()
    ins = (ins + _s3_work_scope_block(work)) if ins else _s3_work_scope_block(work).lstrip()
    session_key = _run_session_key(work)
    result = _hermes_runs_runtime().create_run(
        req.input,
        instructions=ins,
        session_id=req.session_id,
        conversation_history=req.conversation_history,
        previous_response_id=req.previous_response_id,
        session_key=session_key,
    )
    run_id = result.get("run_id") or result.get("id")
    _record_ai_run_trace(
        work,
        run_id,
        status=result.get("status") or "created",
        session_key=session_key,
        input_text=req.input,
        instructions=ins,
        response=result,
    )
    # Task 13:把 run 链回作品级主编线程,并快照"发起时的上下文"(session/revision/hash/focus)。
    # best-effort:绑定失败只告警,绝不阻断 run 创建(与 trace 留痕同纪律)。
    _bind_run_origin_context(work, run_id, req)
    return result


def _bind_run_origin_context(work: str, run_id: str | None, req: AIRunCreateReq) -> None:
    """记 parent_thread_id(作品级主编线程)+ 发起时上下文快照。

    thread 优先取发起时快照落库的 thread_id(与该会话严格一致),取不到再退化到
    _editor_turn_context(work) 的稳定主编线程;origin_context_revision/hash/focus 从
    快照读——审批时以此为准判"是否过期",不信任审批请求自报的值。"""
    if not run_id:
        return
    try:
        store = _store_for(work)
        parent_thread_id = _editor_turn_context(work).thread_id
        origin_session = req.context_session_id
        origin_rev = req.context_revision
        origin_hash = None
        origin_focus = None
        if origin_session:
            snap = (store.get_context_snapshot(origin_session, revision=origin_rev)
                    if origin_rev is not None else None) \
                or store.get_context_snapshot(origin_session)
            if snap:
                # Minor:origin revision/hash/focus 一律以【库内实际读到的快照】为准,不用请求自报值——
                # 与"不信任自报"一致;自报一个库里不存在的 revision 时,回退当前快照后三者仍是一致对。
                origin_rev = snap.get("revision")
                origin_hash = snap.get("context_hash")
                origin_focus = snap.get("focus")
                parent_thread_id = snap.get("thread_id") or parent_thread_id
        store.update_ai_run_context(
            run_id,
            parent_thread_id=parent_thread_id,
            context_session_id=origin_session,
            origin_context_revision=origin_rev,
            origin_context_hash=origin_hash,
            focus=origin_focus,
        )
    except Exception:
        logging.getLogger("scribe3").warning("run origin context 绑定失败(忽略)", exc_info=True)


@app.get("/ai/runs/{run_id}")
def ai_run_status(run_id: str, work: str = "main"):
    result = _hermes_runs_runtime().run_status(run_id, session_key=_run_session_key(work))
    _record_ai_run_trace(work, run_id, status=result.get("status") or result.get("state"), response=result)
    return result


@app.get("/ai/runs/{run_id}/trace")
def ai_run_trace(run_id: str, work: str = "main"):
    store = _store_for(work)
    trace = store.get_ai_run_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail="ai_run_trace not found")
    # Task 16-A 纵深(spec 审):对齐其他 surface 的 work 绑定。ai_run_trace.work 存的是
    # 物理库名(db_name)——生产 db-per-work 下 _store_for(work)→db=work,恒成立故为 tautology
    # (跨 work 早在 get_ai_run_trace 读不到→404);仅在 store 与请求同库时校验,测试注入
    # (set_store 使 db_name≠work)下跳过避免误报。真正的逻辑-work 绑定待 Task 13 把逻辑 work
    # 落进 ai_run_trace(现存 db_name)后随多 work 并库一并加固。
    if store.db_name == work:
        _assert_work_binding(trace.get("work"), work,
                             kind="ai_run_trace", ident=run_id)
    return trace


@app.get("/ai/runs/{run_id}/events")
def ai_run_events(run_id: str, work: str = "main"):
    from scribe3.hermes_runtime import HermesEventAdapter

    adapter = HermesEventAdapter()
    _record_ai_run_trace(work, run_id, status="streaming")

    def gen():
        try:
            for ev in _hermes_runs_runtime().run_events(run_id, session_key=_run_session_key(work)):
                app_ev = adapter.adapt(ev)
                kind = app_ev.get("kind")
                _record_ai_run_event(work, run_id, app_ev)
                if kind == "text.delta":
                    yield f"data: {json.dumps({'delta': app_ev.get('delta', '')}, ensure_ascii=False)}\n\n"
                elif kind == "tool.started":
                    yield f"data: {json.dumps({'tool': app_ev.get('name', ''), 'tool_args': app_ev.get('arguments', '')}, ensure_ascii=False)}\n\n"
                elif kind == "tool.output":
                    yield f"data: {json.dumps({'tool_output': app_ev.get('output', ''), 'tool_call_id': app_ev.get('call_id')}, ensure_ascii=False)}\n\n"
                elif kind == "approval.requested":
                    yield f"data: {json.dumps({'approval': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'message')}}, ensure_ascii=False)}\n\n"
                elif kind == "approval.resolved":
                    yield f"data: {json.dumps({'approval_resolved': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'decision')}}, ensure_ascii=False)}\n\n"
                elif kind == "run.completed":
                    yield f"data: {json.dumps({'run': {'run_id': app_ev.get('run_id'), 'status': 'completed', 'usage': app_ev.get('usage')}}, ensure_ascii=False)}\n\n"
                elif kind == "run.failed":
                    yield f"data: {json.dumps({'error': app_ev.get('error') or 'run failed'}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'raw': app_ev}, ensure_ascii=False)}\n\n"
        except Exception as e:
            _record_ai_run_trace(work, run_id, status="failed", error=str(e)[:160])
            yield f"data: {json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/ai/runs/{run_id}/approval")
def ai_run_approval(run_id: str, req: AIRunApprovalReq, work: str = "main"):
    payload = req.model_dump(exclude_none=True)
    choice = _hermes_approval_choice(req)
    # Task 13:写入前重校验发起时上下文快照(限知写入安全闸)。校验通过后原 approve 流程一字不改;
    # RunContextChanged(409)在此前抛出,绝不进 Hermes approve——旧 run 的过期写入被物理拦下。
    store = _store_for(work)
    trace = store.get_ai_run_trace(run_id) or {}
    completion_rev = _recheck_run_origin_context(store, run_id, trace, req, choice)
    hermes_payload = {"choice": choice}
    try:
        result = _hermes_runs_runtime().approve_run(
            run_id,
            hermes_payload,
            session_key=_run_session_key(work),
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        _record_ai_run_trace(work, run_id, status="approval_failed", error=detail)
        raise HTTPException(status_code=502, detail=f"Hermes approval failed: {detail}") from exc
    _record_ai_run_event(work, run_id, {
        "kind": "approval.resolved",
        "run_id": run_id,
        "approval_id": payload.get("approval_id"),
        "decision": payload.get("decision"),
        "choice": choice,
    }, source="user")
    _record_ai_run_trace(work, run_id, status=result.get("status") or "approval_submitted", response=result)
    # Task 13:记完成时上下文 revision + write_effects 台账(仅 approve 类且有 origin 绑定时)。
    # Minor:同一审批重放时按 (approval_id, revision, kind) 去重,不叠重复台账
    # (读改写非 CAS,能挡幂等重放;真并发双批准极罕见,同 approval_id 亦会命中去重)。
    if choice != "deny" and completion_rev is not None:
        try:
            effects = list(trace.get("write_effects") or [])
            new_effect = {
                "kind": "approval",
                "approval_id": payload.get("approval_id"),
                "choice": choice,
                "stale_confirmed": bool(req.approve_stale),
                "context_revision": completion_rev,
            }
            key = (new_effect["approval_id"], new_effect["context_revision"], new_effect["kind"])
            if not any((e.get("approval_id"), e.get("context_revision"), e.get("kind")) == key
                       for e in effects):
                effects.append(new_effect)
            store.update_ai_run_context(
                run_id,
                completion_context_revision=completion_rev,
                write_effects=effects,
            )
        except Exception:
            logging.getLogger("scribe3").warning("run completion context 记账失败(忽略)", exc_info=True)
    return result


@app.post("/ai/runs/{run_id}/stop")
def ai_run_stop(run_id: str, work: str = "main"):
    result = _hermes_runs_runtime().stop_run(run_id, session_key=_run_session_key(work))
    _record_ai_run_trace(work, run_id, status=result.get("status") or "stopped", response=result)
    return result


# ---------------------------------------------------------------------------
# 统一上下文与记忆系统 · Task 4:Context API(会话/导航/快照)
# work 约定:?work= 只用于定位 store(全仓约定);校验以 session 落库的 work
# 为准(Task 16 的 work 绑定校验语义,现在就按此做)——不符 409 context_work_mismatch。
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Task 16-A(安全隔离子集):统一 work 绑定校验 + 安全指标。
# 单机单用户无 claim 体系——?work= 只是前端【声明】,权威 work 以记录落库值为准。
# 每个 surface(context/thread/memory/trace/run)取记录落库 work 与请求 ?work= 比对,
# 不符 → 409 context_work_mismatch。隔离底座仍是 per-work db:记录不在本 work 库 → 404。
# cross_work_rejections 是内存安全指标,供 Task 16-B 的 /ai/runtime-status 消费(不含
# 任何 prompt / 秘密值)。
# ---------------------------------------------------------------------------
_security_metrics = {"cross_work_rejections": 0}


def get_security_metrics() -> dict:
    """安全指标只读快照(Task 16-B runtime-status 用)。绝不含原始 prompt / 秘密值。"""
    return dict(_security_metrics)


def _bump_cross_work_rejection() -> None:
    _security_metrics["cross_work_rejections"] += 1


def _thread_work(thread_id: str | None) -> str | None:
    """从 ethread:<work>:<uuid> 解出落库 work(work 是无冒号 slug,uuid hex 无冒号)。
    无法解析(非 ethread 命名/旧格式)→ None:交由端点 not-found 分支给 404,不误判 409。"""
    if not isinstance(thread_id, str) or not thread_id.startswith("ethread:"):
        return None
    work, sep, _tail = thread_id[len("ethread:"):].rpartition(":")
    return work if (sep and work) else None


def _assert_work_binding(record_work: str | None, requested_work: str,
                         *, kind: str, ident: str) -> None:
    """统一 work 绑定校验:记录落库 work ≠ 请求声明 work → 409 context_work_mismatch。

    record_work=None(无法判定归属 work)→ 不在此拦,由端点 not-found 分支给 404
    (计划 Task 16 ① 的 409/404 协调:存在但越权→409;不存在/不可判→404)。"""
    if record_work is not None and record_work != requested_work:
        _bump_cross_work_rejection()
        raise HTTPException(status_code=409, detail={
            "code": "context_work_mismatch",
            "message": f"{kind} '{ident}' 属于 work '{record_work}',"
                       f"请求 work '{requested_work}' 不符",
            "expected": requested_work, "actual": record_work})


def _context_http_error(e: Exception) -> HTTPException:
    """context 语义异常 → HTTPException(detail 恒带稳定 code,前端读 error.body.detail.code)。"""
    if isinstance(e, StaleContextError):
        return HTTPException(status_code=409, detail={
            "code": e.code, "expected": e.expected, "actual": e.actual, "latest": e.latest})
    status = {
        "context_binding_required": 400,
        "context_session_not_found": 404,
        "context_snapshot_not_found": 404,
        "context_session_ended": 409,
        "context_work_mismatch": 409,
    }.get(getattr(e, "code", ""), 500)
    detail = {"code": getattr(e, "code", "context_error"), "message": str(e)}
    if isinstance(e, ContextWorkMismatch):
        detail |= {"expected": e.expected, "actual": e.actual}
        # ContextService 路径的跨 work 越权也计入统一安全指标(与 _assert_work_binding 同源)。
        _bump_cross_work_rejection()
    return HTTPException(status_code=status, detail=detail)


class ContextSessionCreateReq(BaseModel):
    actor_id: str = "author"
    device_id: str = ""
    # work 可放 body(优先)或 ?work= query;创建后固化进 session 记录
    work: str | None = None


@app.post("/context/sessions")
def context_session_create(req: ContextSessionCreateReq, work: str = "main"):
    """开上下文会话:落 revision=0 初始快照并返回(session 与快照同事务,无中间态)。"""
    w = (req.work or work).strip() or "main"
    return _store_for(w).create_context_session(w, req.actor_id, req.device_id)


@app.get("/context/sessions/{session_id}")
def context_session_get(session_id: str, work: str = "main"):
    """读会话当前快照(含 revision/context_hash,前端绑定 LLM 调用的三件套来源)。"""
    try:
        return ContextService(_store_for(work)).get(session_id, work)
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e


@app.post("/context/sessions/{session_id}/navigate")
def context_session_navigate(session_id: str, intent: NavigationIntent, work: str = "main"):
    """CAS 推进上下文(body 为 NavigationIntent 形状)。失配 409 stale_context
    (带 latest 供前端直接对齐);同 navigation_id 幂等重放(store 合同)。"""
    try:
        return ContextService(_store_for(work)).navigate(
            session_id, work, intent.model_dump(mode="json"))
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e


@app.get("/context/sessions/{session_id}/snapshots/{revision}")
def context_snapshot_get(session_id: str, revision: int, work: str = "main"):
    """读历史版快照(回放/审计);该 revision 不存在 → 404 context_snapshot_not_found。"""
    try:
        return ContextService(_store_for(work)).get(session_id, work, revision=revision)
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e


@app.get("/context/sessions/{session_id}/trace/{revision}")
def context_trace_get(session_id: str, revision: int, work: str = "main"):
    """读某快照版本的记忆溯源 trace(Task 14 上下文检查器数据源):主编到底看到了
    什么、为什么选这条记忆、为什么弃那条。

    限知红线:私密事实的 value 在服务端【权威屏蔽】后才返回(前端不可信,Task 7 教训)——
    store.get_memory_trace_for_snapshot 落库时已屏蔽,此处再过一遍 mask_memory_trace 兜底。

    诚实边界:真实 trace 数据待 Task 16 检索接进生产 prompt 后填充;在此之前该版本
    多无溯源 → 404 memory_trace_not_found(前端据此显"未检索到证据",不显"没有相关事实")。"""
    from scribe3.store import mask_memory_trace
    trace = _store_for(work).get_memory_trace_for_snapshot(session_id, int(revision))
    if not trace:
        raise HTTPException(status_code=404, detail={
            "code": "memory_trace_not_found",
            "message": "该快照版本暂无记忆溯源(检索生产接线待 Task 16)"})
    # Task 16-A:memory_trace 落库 work 与请求 ?work= 比对(空 work=旧数据→不判,走 mask)。
    _assert_work_binding(trace.get("work") or None, work,
                         kind="memory_trace", ident=session_id)
    return mask_memory_trace(trace)


# ---------------------------------------------------------------------------
# 统一上下文与记忆系统 · Task 6:主编线程(一 work 一连续线程 + 每轮焦点标签)
# GET  /chat/threads               本 work 线程列表(含分支)
# GET  /chat/threads/{id}/messages 该线程全部消息(store.list_thread_messages)
# POST /chat/threads/{id}/fork     显式分支(写 parent_thread_id 建新线程)
# 导航路径绝不调 fork——fork 只在作者显式"另起支线"时触发。
# ---------------------------------------------------------------------------

class ForkThreadReq(BaseModel):
    title: str | None = None


@app.get("/chat/threads")
def chat_threads(work: str = "main", actor_id: str = "author"):
    """本 work 线程列表;顺带保证默认线程存在(首次访问即建,幂等)。"""
    store = _store_for(work)
    store.get_or_create_editorial_thread(work, actor_id)
    return {"threads": store.list_editorial_threads(work)}


@app.get("/chat/threads/{thread_id}/messages")
def chat_thread_messages(thread_id: str, work: str = "main", limit: int = 500):
    """该线程全部消息(ts 升序)。Task 16-A:thread_id 内嵌 work(ethread:<work>:<uuid>)——
    落库 work 与请求 ?work= 不符 → 409(否则空 [] 会把越权伪装成"无消息")。"""
    _assert_work_binding(_thread_work(thread_id), work,
                         kind="editorial_thread", ident=thread_id)
    return _store_for(work).list_thread_messages(thread_id, limit=limit)


@app.post("/chat/threads/{thread_id}/fork")
def chat_thread_fork(thread_id: str, req: ForkThreadReq, work: str = "main"):
    """显式分支:以 thread_id 为父建新线程(写 parent_thread_id)。父不存在 404。
    Task 16-A:先校验父线程落库 work 与请求 ?work= 一致(防跨 work fork 出他书子线程)。"""
    _assert_work_binding(_thread_work(thread_id), work,
                         kind="editorial_thread", ident=thread_id)
    try:
        return _store_for(work).fork_editorial_thread(thread_id, title=req.title)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={
            "code": "thread_not_found", "message": str(e)}) from e


# ---------------------------------------------------------------------------
# 统一上下文与记忆系统 · Task 12:/memory/* REST(可选 scribe3-memory Hermes provider 消费)
#
# 把 Task 8/9 的内部检索/捕获/固化能力暴露成 HTTP,仅供【直接用 Hermes 会话】(非 Scribe Web
# 主路)读写 Scribe 记忆。Scribe Web 的 chat/write 主路【完全不经】这些端点——它在 app 内直调
# ContextAssembler / MemoryRetriever / MemoryCapture,与本段解耦;关闭 provider(不设
# SCRIBE3_API_BASE)对主路零影响。
#
# work-scoped 硬红线(复用 16-A):?work= 定位 per-work db(物理隔离,跨 work 检索不到彼此);
# thread_id 内嵌 work(ethread:<work>:<uuid>)时再过 _assert_work_binding,跨 work 声明→409。
# best-effort:捕获/固化失败只告警不 5xx(与主链路捕获同纪律,不阻断上游会话)。
# ---------------------------------------------------------------------------
class MemoryPrefetchReq(BaseModel):
    thread_id: str | None = None
    query: str = ""
    k: int = Field(default=24, ge=1, le=200)


@app.post("/memory/prefetch")
def memory_prefetch(req: MemoryPrefetchReq, work: str = "main"):
    """检索本 work 记忆,返回组装好的记忆块文本(供直连 Hermes 会话注入 prompt)。

    讨论模式组装(无章 → 限知门 fail-open,作者全知视角):canonical 命题 + 经验记忆,
    work 隔离 / 秘密屏蔽在检索·组装链内生效。组装异常降级空块(绝不 5xx 拖垮上游会话)。"""
    w = _normalize_work(work)
    _assert_work_binding(_thread_work(req.thread_id), w,
                         kind="editorial_thread", ident=req.thread_id or "")
    store = _store_for(w)
    from scribe3.context_assembler import ContextAssembler, render_envelope_text
    from scribe3.memory_retrieval import MemoryRetriever
    try:
        snap = _write_snapshot(store, chapter=None, focalizer=None, phase=None, work=w)
        envelope = ContextAssembler(store, MemoryRetriever(store)).assemble(
            snap, req.query or "", "discussion")
        context = render_envelope_text(envelope)
    except Exception:
        logging.getLogger("scribe3").warning(
            "/memory/prefetch 组装失败(降级空块)", exc_info=True)
        context = ""
    return {"context": context, "work": w}


class MemoryCaptureTurnReq(BaseModel):
    thread_id: str | None = None
    event_id: str | None = None
    user: str = ""
    assistant: str = ""
    messages: list = Field(default_factory=list)


@app.post("/memory/capture-turn")
def memory_capture_turn(req: MemoryCaptureTurnReq, work: str = "main"):
    """幂等捕获一轮对话为经验记忆(同步 drain)。event_id 幂等键:同 event_id 二次→idempotent。

    捕获作者意图文本(user 优先,空则退 assistant);分类/正典红线/linked_ids 领域反查在
    MemoryCapture 内。best-effort:失败只告警,返回 capture_failed 而非 5xx。"""
    w = _normalize_work(work)
    _assert_work_binding(_thread_work(req.thread_id), w,
                         kind="editorial_thread", ident=req.thread_id or "")
    store = _store_for(w)
    from scribe3.memory_capture import MemoryCapture, turn_event
    text = (req.user or "").strip() or (req.assistant or "").strip()
    if not text:
        return {"status": "skipped", "work": w}
    ev_id = (req.event_id or "").strip() or None
    try:
        result = MemoryCapture(store).capture_event(turn_event(
            text=text, event_id=ev_id, work=w, thread_id=req.thread_id))
    except Exception:
        logging.getLogger("scribe3").warning(
            "/memory/capture-turn 捕获失败(忽略,不阻断上游会话)", exc_info=True)
        return {"status": "capture_failed", "work": w}
    return {"status": result.get("status"),
            "idempotent": bool(result.get("idempotent")),
            "event_id": ev_id, "work": w}


class MemoryFlushReq(BaseModel):
    thread_id: str | None = None
    reason: str = "manual"


@app.post("/memory/flush")
def memory_flush(req: MemoryFlushReq, work: str = "main"):
    """固化线程工作摘要 + drain 掉线残留(Hermes on_pre_compress / on_session_end 触发)。
    幂等:working_summary 按 (work,thread) 唯一 UPSERT。best-effort:失败降级 through_turn=0。"""
    w = _normalize_work(work)
    _assert_work_binding(_thread_work(req.thread_id), w,
                         kind="editorial_thread", ident=req.thread_id or "")
    store = _store_for(w)
    from scribe3.memory_capture import MemoryCapture
    try:
        result = MemoryCapture(store).consolidate_thread(req.thread_id, work=w)
    except Exception:
        logging.getLogger("scribe3").warning(
            "/memory/flush 固化失败(忽略)", exc_info=True)
        result = {"through_turn": 0}
    return {"status": "flushed", "reason": req.reason, "work": w,
            "through_turn": result.get("through_turn", 0)}


@app.get("/works")
def works():
    out = []
    for w in list_works():
        try:
            store = _store_for(w["slug"])
            st = store.stats()
            intent = store.get_intent()
            # 携带 total_word_goal 供书卡进度条使用;None 时前端回退 100000
            if intent.get("total_word_goal") is not None:
                st["total_word_goal"] = intent["total_word_goal"]
        except Exception:
            st = {"chapter_count": 0, "word_count": 0}
        out.append({**w, **st})
    return out


@app.get("/objects/{object_type}/{object_id}/impact")
def object_impact_ep(object_type: str, object_id: str, work: str = "main"):
    return _object_impact(_store_for(work), object_type, object_id, work)


@app.delete("/objects/{object_type}/{object_id}")
def object_delete_ep(object_type: str, object_id: str,
                     confirm_impact_token: str | None = None,
                     work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), object_type, object_id, work, confirm_impact_token)


@app.post("/objects/{object_type}/{object_id}/archive")
def object_archive_ep(object_type: str, object_id: str, work: str = "main"):
    return _archive_object_with_lifecycle(_store_for(work), object_type, object_id, work)


class WorkIn(BaseModel):
    title: str


@app.post("/works")
def make_work(w: WorkIn):
    return create_work(w.title)


@app.patch("/works/{slug}")
def rename(slug: str, w: WorkIn):
    rename_work(slug, w.title)
    return {"ok": True}


@app.delete("/works/{slug}")
def remove_work(slug: str):
    delete_work(slug)
    _stores.pop(slug, None)
    return {"ok": True}


# ===== 读(按书)=====
@app.get("/entities")
def entities(work: str = "main", reveal_secret: bool = False):
    def _entity_dict(e):
        t = e.traits or {}
        row = {
            "id": e.id, "kind": e.kind, "name": e.name,
            "backstory": t.get("backstory"),
            "backstory_secret": t.get("backstory_secret", False),
            "importance": t.get("importance"),
            "appearance": t.get("appearance"),
            "personality_tags": t.get("personality_tags"),
            "aliases": t.get("aliases") or [],
            "personality_detail": t.get("personality_detail"),
            "abilities": t.get("abilities"),
            "weaknesses": t.get("weaknesses"),
            "first_appearance": t.get("first_appearance"),
            "surface_goal": t.get("surface_goal"),
            "deep_need": t.get("deep_need"),
            "internal_conflict": t.get("internal_conflict"),
            "fear": t.get("fear"),
        }
        if e.kind == "character":
            row = _mask_field(row, "backstory", "backstory_secret", reveal_secret)
        return row
    return [_entity_dict(e) for e in _store_for(work).all_entities()]


@app.get("/facts")
def facts(chapter: int = Query(ge=1), work: str = "main", reveal_secret: bool = False):
    """本章有效命题。批E-A1:加 reveal_secret(默认 False 仍屏蔽私密 value/leak_markers);
    每条回全字段(valid_from/valid_to/leak_markers)供前端整行编辑。"""
    return _facts(_store_for(work).facts_at(chapter), reveal_secret=reveal_secret)


@app.get("/facts/{local}")
def get_fact(local: str, work: str = "main", reveal_secret: bool = False):
    """单条命题全字段读回(批E-A1②)。含 valid_from/valid_to/leak_markers/is_secret,
    让在库 leak_markers 等私密字段可安全编辑(reveal_secret=true 解锁真 value/leak_markers)。
    不存在 → 404。"""
    f = _store_for(work).fact(f"fact:{local}")
    if f is None:
        raise HTTPException(status_code=404, detail=f"命题 fact:{local} 不存在")
    return _fact_item(f, reveal_secret=reveal_secret)


@app.get("/events")
def events(chapter: int = Query(ge=1), work: str = "main"):
    return [{"id": ev.id, "type": ev.type, "chapter": ev.story_time, "goal": ev.motivated_by_goal}
            for ev in _store_for(work).events_at(chapter)]


class NarrativeIn(BaseModel):
    narrative_position: int | None = None


@app.patch("/events/{eid}/narrative")
def patch_event_narrative(eid: str, body: NarrativeIn, work: str = "main"):
    """更新已有事件的叙事位(narrative_position)。
    body.narrative_position=null → 清除,回退 story_chapter(线性叙事默认)。
    body.narrative_position=N  → 设为叙事位 N(倒叙/闪回)。
    eid 为事件的本体 oid(如 'ev:xxx')或裸 local id(如 'xxx',自动补前缀)。"""
    st = _store_for(work)
    # 容忍裸 local id 或带前缀的 oid
    event_oid = eid if eid.startswith("ev:") else f"ev:{eid}"
    if not st.exists(event_oid):
        raise HTTPException(status_code=404, detail=f"事件 {event_oid} 不存在")
    st.update_event_narrative(event_oid, body.narrative_position)
    return {"ok": True, "event": event_oid, "narrative_position": body.narrative_position}


@app.get("/timeline")
def timeline(ch_from: int = Query(default=1, ge=1),
             ch_to: int | None = Query(default=None, ge=1),
             axis: str = Query(default="story"),
             limit: int = Query(default=500, ge=1, le=5000),
             work: str = "main"):
    """时间线工艺视图(F-02):返回 [ch_from, ch_to] 区间内按章排序的事件条目。
    作者全知视图,无限知门控。四类泳道:events / promise / arc / relation。
    完整期双轴(spec §3.1):axis='story'(默认,故事编年)| 'narrative'(叙事顺序,
    事件按 narrative_position ?? story_chapter 横铺,倒叙/闪回落叙事位)。
    axis 非法值回退 'story'(向后兼容)。

    Phase0-BE1(千万字基座):新增 total items 上限 limit(默认 500,防全书一次返上万条)。
    items 被截断时返回 truncated=true,前端可据此提示缩小区间;结构其余不变。"""
    if axis not in ("story", "narrative"):
        axis = "story"
    st = _store_for(work)
    # 多取一条探测是否溢出 limit,以便回报 truncated
    items = st.timeline(ch_from, ch_to, axis=axis, limit=limit + 1)
    truncated = len(items) > limit
    if truncated:
        items = items[:limit]
    max_ch = st.max_chapter()
    return {
        "from": ch_from,
        "to": ch_to if ch_to is not None else max_ch,
        "max_chapter": max_ch,
        "axis": axis,
        "limit": limit,
        "truncated": truncated,
        "items": items,
    }


@app.get("/frame")
def frame(focalizer: str, chapter: int = Query(ge=1), work: str = "main"):
    return _facts(project_frame(_store_for(work), focalizer, chapter).facts)


@app.get("/irony")
def irony(focalizer: str, chapter: int = Query(ge=1), work: str = "main"):
    return _facts(dramatic_irony(_store_for(work), focalizer, chapter))


@app.get("/causal")
def causal(chapter: int = Query(ge=1), work: str = "main"):
    """本章事件图的因果完整性校验。
    批D P1-5 假绿止血:返回对象 {no_event_data, violations} 而非裸 violations 列表——
    event 表对该章为空时 no_event_data=True(区分'因果完整=violations 空'与
    '根本没有事件数据可校验'),防空表恒返 [] 被前端读作'因果完整✅'的假信号。"""
    st = _store_for(work)
    violations = [{"event": v.event_id, "reason": v.reason} for v in causal_complete(st, chapter)]
    return {"no_event_data": not st.events_at(chapter), "violations": violations}


@app.get("/recall")
def recall(q: str, k: int = Query(default=5, ge=1, le=50), work: str = "main"):
    return _facts(_store_for(work).semantic_recall(q, k))


def _search_excerpt(text: str, q: str, limit: int = 96) -> str:
    text = text or ""
    q = q or ""
    if not text:
        return ""
    idx = text.lower().find(q.lower()) if q else -1
    if idx < 0:
        return text[:limit]
    start = max(0, idx - 24)
    end = min(len(text), idx + len(q) + 48)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def _search_hit(q: str, *parts: str | None) -> bool:
    needle = (q or "").strip().lower()
    if not needle:
        return False
    return any(needle in str(p or "").lower() for p in parts)


@app.get("/search")
def global_search(q: str, limit: int = Query(default=30, ge=1, le=100), work: str = "main"):
    """全局搜索:正文/设定/素材/伏笔/母题的 typed target 聚合,供四栏钻取。"""
    query = (q or "").strip()
    if not query:
        return {"query": query, "results": []}
    st = _store_for(work)
    results = []

    def add(item):
        if len(results) < limit * 3:
            results.append(item)

    for c in st.list_chapters():
        ch = st.get_chapter(int(c["seq"])) or c
        text = "\n".join(str(ch.get(k) or "") for k in ("title", "synopsis", "prose", "scene_truth"))
        if _search_hit(query, text):
            seq = int(ch["seq"])
            title = ch.get("title") or f"第{seq}章"
            add({
                "id": f"search:chapter:{seq}",
                "type": "chapter",
                "label": title,
                "excerpt": _search_excerpt(text, query),
                "source": "正文",
                "chapter": seq,
                "score": 1.0 if _search_hit(query, title) else 0.75,
                "target_node": {"id": f"ch:{seq}", "type": "chapter", "ref": seq, "label": f"{seq} {title}".strip()},
            })

    for ev in st._all_events_bulk():
        text = "\n".join([
            ev.id or "",
            ev.type or "",
            ev.motivated_by_goal or "",
            ev.location or "",
            " ".join(ev.preconditions or []),
            " ".join(ev.participants.values() or []),
        ])
        if _search_hit(query, text):
            seq = int(ev.story_time or 0)
            label = ev.type or ev.id
            add({
                "id": f"search:event:{ev.id}",
                "type": "event",
                "label": label,
                "excerpt": _search_excerpt(text, query),
                "source": "事件",
                "chapter": seq or None,
                "score": 0.78 if _search_hit(query, label) else 0.62,
                "target_node": {"id": ev.id, "type": "event", "chapter": seq, "label": label},
            })

    for m in st.list_materials():
        if m.get("archived"):
            continue
        text = "\n".join([m.get("title") or "", m.get("body") or "", " ".join(m.get("tags") or [])])
        if _search_hit(query, text):
            mid = str(m["id"])
            add({
                "id": f"search:material:{mid}",
                "type": "material",
                "label": m.get("title") or mid,
                "excerpt": _search_excerpt(text, query),
                "source": "素材",
                "score": 0.9 if _search_hit(query, m.get("title")) else 0.65,
                "target_node": {"id": f"material:{mid}", "type": "material", "ref": mid, "label": m.get("title") or mid,
                                "meta": {"kind": m.get("kind")}},
            })

    for e in st.all_entities():
        text = "\n".join([e.name or "", str((e.traits or {}).get("backstory") or ""), " ".join((e.traits or {}).get("aliases") or [])])
        if _search_hit(query, text):
            local = e.id.split(":", 1)[-1]
            add({
                "id": f"search:entity:{e.id}",
                "type": e.kind,
                "label": e.name,
                "excerpt": _search_excerpt(text, query),
                "source": "设定",
                "score": 0.8,
                "target_node": {"id": f"{e.kind}:{local}", "type": e.kind, "ref": local, "label": e.name},
            })

    max_ch = max(1, st.max_chapter())
    for f in st.facts_at(max_ch):
        text = "\n".join([f.entity_id or "", f.attribute or "", f.value or ""])
        if _search_hit(query, text):
            local = f.id.split(":", 1)[-1]
            add({
                "id": f"search:fact:{local}",
                "type": "proposition",
                "label": f.value or f.attribute or local,
                "excerpt": _search_excerpt(text, query),
                "source": "设定",
                "score": 0.7,
                "target_node": {"id": f"proposition:{local}", "type": "proposition", "ref": local, "label": f.value or local},
            })

    for p in st.list_promises():
        text = "\n".join(str(p.get(k) or "") for k in ("text", "status", "kind"))
        if _search_hit(query, text):
            pid = str(p.get("id") or p.get("text"))
            add({
                "id": f"search:promise:{pid}",
                "type": "promise",
                "label": p.get("text") or pid,
                "excerpt": _search_excerpt(text, query),
                "source": "伏笔",
                "chapter": p.get("setup_chapter"),
                "score": 0.6,
                "target_node": {"id": f"promise:{pid}", "type": "promise_view", "ref": "open", "label": p.get("text") or pid},
            })

    for m in st.list_motifs():
        text = "\n".join(str(m.get(k) or "") for k in ("name", "theme", "echoes", "unfolding"))
        if _search_hit(query, text):
            mid = str(m.get("id") or m.get("name"))
            add({
                "id": f"search:motif:{mid}",
                "type": "motif",
                "label": m.get("name") or mid,
                "excerpt": _search_excerpt(text, query),
                "source": "母题",
                "score": 0.6,
                "target_node": {"id": f"motif:{mid}", "type": "motif", "ref": mid, "label": m.get("name") or mid},
            })

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"query": query, "results": results[:limit]}


@app.get("/promises")
def promises(work: str = "main"):
    """P3-e1 Fix 1: 每条 promise 携带 overdue 字段(backend 单源,前端直读)。"""
    st = _store_for(work)
    proms = st.list_promises()
    mc = st.max_chapter()
    intent = st.get_intent()
    # 经 list_promises 补算窗口后 legacy slack 分支仅数据异常行可达,threshold 近似废弃,留防御
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    for p in proms:
        p["overdue"] = _overdue_flag(p, mc, slack)
    return proms


@app.get("/promises/ledger")
def promises_ledger(work: str = "main"):
    """作者工具 F-03 伏笔台账(单源):三栏(open/closed/red_herring)+ 每条
    setup/payoff/overdue/跨度 + open/close bracket 完整性审计。
    overdue 阈值同 /promises、/quality(_overdue_flag 单源)。"""
    st = _store_for(work)
    intent = st.get_intent()
    # 经 list_promises 补算窗口后 legacy slack 分支仅数据异常行可达,threshold 近似废弃,留防御
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    return st.promise_ledger(slack)


@app.get("/motifs")
def motifs(work: str = "main"):
    return _store_for(work).list_motifs()


@app.get("/motif-instances")
def motif_instances(chapter: int = Query(ge=1), work: str = "main"):
    """本章触及的母题:[{motif_id, name, evidence}]。ingest 抽取落库,未反哺的章返回空。"""
    return _store_for(work).list_motif_instances(chapter)


@app.get("/chapter-pulse")
def chapter_pulse_ep(seq: int = Query(ge=1), work: str = "main"):
    """主编主动化 T1:六维脉搏(promise/arc/relation/tension/causal/quality)。
    只读聚合,零新检测器;decision 级=时机引擎开口依据(全部源自确定性信号);
    宪法:无总分,分维 severity。"""
    from scribe3.pulse import chapter_pulse
    return chapter_pulse(_store_for(work), seq)


@app.get("/chapter-brief")
def chapter_brief(seq: int = Query(ge=1), focalizer: str = "", work: str = "main"):
    """Task7 章前创作简报(只读):弧光指令 + 伏笔窗口分流 + 开环账本 + 待激活角色。
    与 _editor_write_system 的注入同源(assemble_chapter_brief 单源)。"""
    from scribe3.brief import assemble_chapter_brief
    return assemble_chapter_brief(_store_for(work), seq, focalizer=focalizer)


# ===== 角色弧光:静态锚(五要素)+ arc_plan 里程碑(migration 054)=====
@app.get("/char-anchors")
def get_char_anchors(character_id: str, work: str = "main"):
    """单角色的弧光锚(七键)+ 里程碑计划(按 target_chapter 有序)。"""
    st = _store_for(work)
    return {"anchors": st.char_anchors(character_id),
            "arc_plan": st.list_arc_plan(character_id)}


@app.patch("/char-anchors")
def patch_char_anchors(req: dict, work: str = "main"):
    """局部更新弧光锚:只写传入的键,未传字段不动(store 层 _ANCHOR_KEYS 白名单)。
    Task5-C④:角色不存在回 404,不再静默 200。
    Task7-C①:存在但非 character(如 place)同样 404,防误挂锚。"""
    st = _store_for(work)
    cid = req["character_id"]
    ent = st.entity(cid)
    if ent is None or ent.kind != "character":
        raise HTTPException(status_code=404, detail=f"角色 '{cid}' 不存在")
    st.set_char_anchors(cid, req.get("anchors") or {})
    return {"status": "updated"}


@app.post("/arc-beats")
def post_arc_beat(req: dict, work: str = "main"):
    # Task5-C⑤:lie_belief_target 非 None 时须 0-100 数值,否则 422(应用层闸;DB 级 ASSERT 不做)
    lbt = req.get("lie_belief_target")
    if lbt is not None and (isinstance(lbt, bool)
                            or not isinstance(lbt, (int, float))
                            or not (0 <= lbt <= 100)):
        raise HTTPException(status_code=422,
                            detail="lie_belief_target 须为 0-100 的数值或不传")
    _store_for(work).add_arc_beat(
        req["character_id"], req["beat_name"], int(req["target_chapter"]),
        lbt, req.get("trigger_event") or "")
    return {"status": "created"}


@app.delete("/arc-beats/{beat_id}")
def del_arc_beat(beat_id: str, work: str = "main"):
    _store_for(work).delete_arc_beat(beat_id)
    return {"status": "deleted"}


# ===== 设定库 增删改(作者直编,不经 elicitation;非世界状态级别的 agent 写)=====
class CharIn(BaseModel):
    name: str
    backstory: str | None = None
    backstory_secret: bool = False
    importance: str | None = None
    appearance: str | None = None
    personality_detail: str | None = None
    personality_tags: list[str] = []
    aliases: list[str] = []
    abilities: str | None = None
    weaknesses: list = []
    surface_goal: str | None = None
    deep_need: str | None = None
    internal_conflict: str | None = None
    fear: str | None = None
    first_appearance: int | None = None


@app.post("/characters")
def add_char(c: CharIn, work: str = "main"):
    # 掩码写哨兵:backstory 收到掩码占位符 → 视为未提供(不落库为字面掩码值)。
    backstory = None if c.backstory == _SECRET_MASK else c.backstory
    _store_for(work).add_entity(Entity(
        f"role:{c.name}", "character", c.name,
        traits={"backstory": backstory, "backstory_secret": c.backstory_secret,
                "personality_tags": c.personality_tags, "aliases": c.aliases}))
    return {"ok": True, "oid": f"role:{c.name}"}


@app.patch("/characters/{local}")
def edit_char(local: str, c: CharIn, work: str = "main"):
    st = _store_for(work)
    # 掩码写哨兵:backstory 收到掩码占位符 → 置 None(下方 None 过滤剔除)= 视为未改,不覆盖库中真值。
    backstory = None if c.backstory == _SECRET_MASK else c.backstory
    fields = {"name": c.name, "backstory": backstory, "backstory_secret": c.backstory_secret,
              "importance": c.importance,
              "appearance": c.appearance, "personality_detail": c.personality_detail,
              "personality_tags": c.personality_tags, "aliases": c.aliases,
              "abilities": c.abilities, "weaknesses": c.weaknesses,
              "surface_goal": c.surface_goal, "deep_need": c.deep_need,
              "internal_conflict": c.internal_conflict, "fear": c.fear,
              "first_appearance": c.first_appearance}
    st.update_record(f"role:{local}", {k: v for k, v in fields.items() if v is not None})
    return {"ok": True}


@app.delete("/characters/{local}")
def del_char(local: str, confirm_impact_token: str | None = None, work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), "role", local, work, confirm_impact_token)


class FactIn(BaseModel):
    entity: str
    attribute: str
    value: str
    valid_from: int = 1
    valid_to: int | None = None
    secret: bool = False
    leak_markers: list[str] = []


@app.post("/facts")
def add_fact_ep(f: FactIn, work: str = "main"):
    import uuid
    oid = f"fact:{uuid.uuid4().hex[:8]}"
    _store_for(work).add_fact(Fact(oid, f.entity, f.attribute, f.value, f.valid_from,
                                   valid_to=f.valid_to, secret=f.secret,
                                   leak_markers=f.leak_markers))
    return {"ok": True, "oid": oid}


@app.patch("/facts/{local}")
def edit_fact(local: str, f: FactIn, work: str = "main"):
    st = _store_for(work)
    st.update_record(f"fact:{local}", {
        "entity_id": f.entity,
        "attribute": f.attribute,
        "value": f.value,
        "valid_from": f.valid_from,
        "valid_to": f.valid_to,
        "secret": f.secret,
        "leak_markers": f.leak_markers,
    })
    # value 变更后重建 embedding,保持语义召回向量与当前值对齐
    try:
        st.semantic_index(f"fact:{local}", f.value)
    except Exception as _e:
        logging.getLogger("scribe3.app").warning(
            "edit_fact: 重建 embedding 失败,命题 fact:%s 将指向旧向量: %s", local, _e)
    return {"ok": True}


@app.delete("/facts/{local}")
def del_fact(local: str, confirm_impact_token: str | None = None, work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), "fact", local, work, confirm_impact_token)


class SupersedeIn(BaseModel):
    entity_id: str
    attribute: str
    value: str
    since_chapter: int
    secret: bool = False


@app.post("/facts/supersede")
def supersede_fact_ep(s: SupersedeIn, work: str = "main"):
    new_oid = _store_for(work).supersede_fact(
        s.entity_id, s.attribute, s.value, s.since_chapter, secret=s.secret)
    return {"ok": True, "oid": new_oid}


class ForgetIn(BaseModel):
    knower_id: str
    proposition_id: str
    until_chapter: int


@app.post("/knowledge/forget")
def forget_knowledge_ep(f: ForgetIn, work: str = "main"):
    _store_for(work).forget_knowledge(f.knower_id, f.proposition_id, f.until_chapter)
    return {"ok": True}


class PromIn(BaseModel):
    text: str
    setup_chapter: int = 1
    promise_kind: str = "promise"
    # tier 三档兑现窗口:chapter(近场 +1..+3)/arc(卷级 +5..+15)/book(书级 payoff_max=None 永不超期)。
    # 可选:add 时缺省即 chapter;edit 时缺省即保留既有 tier(不发送则 update_promise 不动窗口/层级)。
    tier: str | None = None
    # 悬念存档答案(方案B任务21,rules/story-narrative.md:20):"悬念必须有文档记录的
    # 真实答案"。仅 tier∈{book,arc} 的长期悬念强制(见 add_prom 校验);chapter 级短期
    # 悬念本章内起落即兑现,不强制,向后兼容不传此字段的既有调用方。
    resolution: str | None = None


@app.post("/promises-new")
def add_prom(p: PromIn, work: str = "main"):
    tier = p.tier or "chapter"
    # 悬念存档答案强制(方案B任务21):book/arc 长期悬念必须在建伏笔时就写下真实答案,
    # 不能含糊留白;chapter 级短期悬念(本章内起落即兑现)豁免,向后兼容。
    if tier in ("book", "arc") and not (p.resolution and p.resolution.strip()):
        raise HTTPException(
            status_code=422,
            detail="悬念必须有文档记录的真实答案+预计回收章(tier=chapter 短期悬念豁免)")
    # B21 收尾清理批:plant_promise 已支持 resolution 落库,此处把已校验的字段透传;
    # 未传/空串时 or "" 保持向后兼容(store 层默认值不变)。
    try:
        _store_for(work).plant_promise(p.text, p.setup_chapter, kind=p.promise_kind, tier=tier,
                                        resolution=p.resolution or "")
    except ValueError as e:  # 非法 tier → store 层 raise
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.patch("/promises/{pid}")
def edit_prom(pid: str, p: PromIn, work: str = "main"):
    # P1-3:exclude_unset——只 SET 客户端真正提交的字段,未传字段保留库中旧值
    # (此前 promise_kind/setup_chapter 的默认值会静默把 red_herring 重置为 promise、setup 重置为 1)。
    sent = p.model_dump(exclude_unset=True)
    st = _store_for(work)
    fields: dict = {}
    if "text" in sent:
        fields["text"] = sent["text"]
    if "setup_chapter" in sent:
        fields["setup_chapter"] = sent["setup_chapter"]
    if "promise_kind" in sent:  # 端点入参名 promise_kind ↔ store 字段名 kind
        fields["kind"] = sent["promise_kind"]
    if sent.get("tier") is not None:  # 仅显式改 tier 时透传(缺省保留既有层级,由 update_promise 重算窗口)
        fields["tier"] = sent["tier"]
    if sent.get("resolution") is not None:  # B21 收尾清理批:PATCH 也可补写悬念真实答案
        fields["resolution"] = sent["resolution"]
    # B21 收尾清理批(审查发现的绕过口):把 tier 改成 book/arc 等于把短期悬念升格成
    # 长期悬念,须与 /promises-new 同约束——显式传入 tier∈{book,arc} 且改后无 resolution
    # (请求里没带、库里也没有)→ 422。pid 不存在时不在此拦(交给下面 404,语义更准)。
    if sent.get("tier") in ("book", "arc") and not (sent.get("resolution") or "").strip():
        row = next((x for x in st.list_promises() if x["id"] == pid), None)
        if row is not None and not (row.get("resolution") or "").strip():
            raise HTTPException(
                status_code=422,
                detail="悬念必须有文档记录的真实答案+预计回收章(tier=chapter 短期悬念豁免)")
    try:
        found = st.update_promise(pid, fields)
    except ValueError as e:  # 非法 tier → store 层 raise
        raise HTTPException(status_code=422, detail=str(e))
    if not found:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return {"ok": True}


@app.delete("/promises/{pid}")
def del_prom(pid: str, work: str = "main"):
    found = _store_for(work).delete_promise(pid)
    if not found:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return {"ok": True}


class AdvanceIn(BaseModel):
    payoff_chapter: int


@app.post("/promises/{pid}/advance")
def advance_prom(pid: str, body: AdvanceIn, work: str = "main"):
    """回收伏笔(作者直编):标 closed + payoff_chapter。payoff≥setup 校验。"""
    try:
        _store_for(work).advance_promise(pid, body.payoff_chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.post("/promises/{pid}/mark-herring")
def mark_herring(pid: str, work: str = "main"):
    """将伏笔标记为障眼法(red_herring)。伏笔不存在→404。"""
    try:
        found = _store_for(work).mark_promise_herring(pid)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not found:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return {"ok": True}


class ClueIn(BaseModel):
    note: str
    chapter: int


@app.post("/promises/{pid}/clues")
def add_promise_clue(pid: str, body: ClueIn, work: str = "main"):
    """追加草蛇灰线中途线索到某条伏笔。body:{note, chapter}。
    R2.4: chapter 必须 >= setup_chapter;若 payoff 已设则也须 <= payoff_chapter。
    """
    st = _store_for(work)
    # R2.4: 先取 promise 的 setup/payoff 章号做范围校验
    proms = st.list_promises()
    prom = next((p for p in proms if p["id"] == pid), None)
    if prom is None:
        raise HTTPException(status_code=422, detail=f"promise '{pid}' 不存在")
    setup = prom.get("setup_chapter", 1)
    payoff = prom.get("payoff_chapter")
    if body.chapter < setup:
        raise HTTPException(
            status_code=422,
            detail=f"clue.chapter({body.chapter}) < setup_chapter({setup}):线索不能早于埋设章"
        )
    if payoff is not None and body.chapter > payoff:
        raise HTTPException(
            status_code=422,
            detail=f"clue.chapter({body.chapter}) > payoff_chapter({payoff}):线索不能晚于回收章"
        )
    try:
        st.add_promise_clue(pid, body.note, body.chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.delete("/promises/{pid}/clues/{idx}")
def remove_promise_clue(pid: str, idx: int, work: str = "main"):
    """按下标(0-based)删除某条伏笔的线索。"""
    try:
        _store_for(work).remove_promise_clue(pid, idx)
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


# ===== 世界规则 + 势力(设定完整性)=====
class RuleIn(BaseModel):
    name: str
    category: str = "magic"
    source: str | None = None
    capabilities: list = []
    cost: str | None = None
    limitations: list = []
    exceptions: list = []
    scope: str = "global"
    established_chapter: int | None = None
    note: str | None = None


@app.get("/world-rules")
def list_rules(category: str | None = None, work: str = "main"):
    return _store_for(work).list_world_rules(category)


# P1-8:world_rule.scope 合法枚举(对齐 migration 027 的 DB ASSERT);应用层提前 422,
# 不再让非法值走到落库层 ASSERT 才 500。
_WORLD_RULE_SCOPES = {"global", "regional", "faction_specific"}


@app.post("/world-rules")
def add_rule(r: RuleIn, work: str = "main"):
    if r.scope not in _WORLD_RULE_SCOPES:
        raise HTTPException(status_code=422,
                            detail=f"非法 scope='{r.scope}'(合法: {sorted(_WORLD_RULE_SCOPES)})")
    _store_for(work).add_world_rule(r.name, r.category, r.source, r.capabilities, r.cost,
                                     r.limitations, r.exceptions, r.scope,
                                     r.established_chapter, r.note)
    return {"ok": True}


@app.delete("/world-rules")
def del_rule(name: str, work: str = "main"):
    _store_for(work).delete_world_rule(name)
    return {"ok": True}


class FactionIn(BaseModel):
    name: str
    status: str = "active"
    ideology: str | None = None
    leader: str | None = None
    known_members: list = []
    public_face: str | None = None
    private_operation: str | None = None
    private_operation_secret: bool = False
    first_mention_chapter: int | None = None


@app.get("/factions")
def list_factions(work: str = "main", reveal_secret: bool = False):
    rows = _store_for(work).list_factions()
    return [_mask_field(dict(r), "private_operation", "private_operation_secret", reveal_secret)
            for r in rows]


@app.post("/factions")
def add_faction_ep(fc: FactionIn, work: str = "main"):
    """势力 upsert:真 merge 语义(端点层)。

    store.add_faction 是 DELETE+CREATE 整行覆盖——对字段省略脆弱(缺任一字段即销毁),
    不止 private_operation(public_face/ideology/leader 同理)。此处根治:
    - 只取客户端「真正提交」的字段(exclude_unset),未提交字段一律保留库中旧值;
    - 掩码写哨兵:private_operation 收到掩码占位符 → 视为未改(丢弃,保旧真值),
      覆盖前端 F4 未拦截的 curl/MCP 直传掩码路径。
    这样编辑任一字段都不销毁未传/掩码字段。store.add_faction 保持覆盖语义供其它调用方。
    """
    st = _store_for(work)
    sent = fc.model_dump(exclude_unset=True)          # 仅客户端显式提交的字段
    if sent.get("private_operation") == _SECRET_MASK:  # 掩码哨兵:显式回传掩码=未改
        sent.pop("private_operation", None)
    old = next((f for f in st.list_factions() if f.get("name") == fc.name), {})

    def pick(k, default):
        # 客户端提交了该字段 → 用提交值(含显式清空 None);否则保留旧值,再退默认。
        return sent[k] if k in sent else old.get(k, default)

    st.add_faction(
        fc.name,
        ideology=pick("ideology", None),
        status=pick("status", "active"),
        leader=pick("leader", None),
        known_members=pick("known_members", []),
        public_face=pick("public_face", None),
        private_operation=pick("private_operation", None),
        first_mention_chapter=pick("first_mention_chapter", None),
        private_operation_secret=pick("private_operation_secret", False),
    )
    return {"ok": True}


@app.delete("/factions")
def del_faction(name: str, work: str = "main"):
    _store_for(work).delete_faction(name)
    return {"ok": True}


@app.get("/setting-completeness")
def setting_completeness(work: str = "main"):
    return _store_for(work).setting_completeness()


# ===== 物品/道具 + 术语(设置完整性)=====
@app.get("/items")
def list_items_endpoint(state: str | None = None, work: str = "main"):
    return _store_for(work).list_items(state)


@app.post("/items")
def add_item_endpoint(req: dict, work: str = "main"):
    """物品 upsert:PATCH/merge 语义(端点层,参照 /factions)。

    P1-9:store.add_item 是 DELETE+CREATE 整行覆盖(state_history 硬置 []);编辑物品任一
    字段(如描述)都会清空状态流转史。此处根治:客户端「真正提交」的键才更新,未提交字段
    (含 state_history)一律读回旧值保留。这样编辑其它字段不再清 state_history;状态流转走
    专用 POST /items/{name}/state(update_item_state 追加史)。"""
    st = _store_for(work)
    name = req.get("name", "")
    old = next((i for i in st.list_items() if i.get("name") == name), {})

    def pick(k, default):
        # 客户端提交了该字段 → 用提交值;否则保留旧值,再退默认。
        return req[k] if k in req else old.get(k, default)

    st.add_item(name,
                category=pick("category", None),
                description=pick("description", None),
                current_owner=pick("current_owner", None),
                symbolic_state=pick("symbolic_state", "active"),
                special_properties=pick("special_properties", None),
                first_chapter=pick("first_chapter", None),
                state_history=pick("state_history", old.get("state_history", [])))
    return {"ok": True}


@app.post("/items/{name}/state")
def update_item_state_endpoint(name: str, req: dict, work: str = "main"):
    """记录物品符号状态流转(P1-9:暴露 store.update_item_state,此前无可达调用方)。
    body: {"state": "lost"|"destroyed"|"active"|"unknown", "chapter": int, "note": str?}
    追加一条 state_history(如「镇煞钉 lost@第3章」),不清空既有史。"""
    new_state = req.get("state") or req.get("symbolic_state")
    chapter = req.get("chapter")
    if not new_state or chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: state/chapter")
    # 批E-A3:chapter 畸形(非数字串如 'abc')→ int() ValueError,返 422 而非 500 未处理异常
    try:
        chapter_int = int(chapter)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail=f"chapter 须为整数,收到: {chapter!r}")
    _store_for(work).update_item_state(name, new_state, chapter_int, note=req.get("note", ""))
    return {"ok": True}


@app.delete("/items")
def delete_item_endpoint(name: str, work: str = "main"):
    _store_for(work).delete_item(name)
    return {"ok": True}


@app.get("/terms")
def list_terms_endpoint(work: str = "main"):
    return _store_for(work).list_terms()


@app.post("/terms")
def add_term_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_term(req.get("name",""), category=req.get("category"),
                definition=req.get("definition"), aliases=req.get("aliases"),
                first_mention_chapter=req.get("first_mention_chapter"))
    return {"ok": True}


@app.delete("/terms")
def delete_term_endpoint(name: str, work: str = "main"):
    _store_for(work).delete_term(name)
    return {"ok": True}


@app.get("/character-relations")
def character_relations(chapter: int | None = None, work: str = "main"):
    st = _store_for(work)
    if chapter:
        return st.relations_at(chapter)
    return st.relations_at(9999)


@app.post("/character-relations")
def add_character_relation_endpoint(req: dict, work: str = "main"):
    # R2.1: 缺字段返回 422;ValueError(实体不存在)→422
    src = req.get("src")
    dst = req.get("dst")
    relation = req.get("relation")
    since_chapter = req.get("since_chapter")
    if not src or not dst or not relation or since_chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: src/dst/relation/since_chapter")
    st = _store_for(work)
    try:
        st.add_character_relation(src, dst, relation, since_chapter, req.get("note"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.post("/character-relations/evolve")
def evolve_relation_endpoint(req: dict, work: str = "main"):
    # R2.1: 缺字段返回 422;ValueError(实体不存在)→422
    src = req.get("src")
    dst = req.get("dst")
    relation = req.get("relation")
    since_chapter = req.get("since_chapter")
    if not src or not dst or not relation or since_chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: src/dst/relation/since_chapter")
    st = _store_for(work)
    try:
        st.evolve_relation(src, dst, relation, since_chapter, req.get("note"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.post("/character-relations/end")
def end_relation_endpoint(req: dict, work: str = "main"):
    # R2.1: 缺字段返回 422;ValueError(实体不存在)→422
    src = req.get("src")
    dst = req.get("dst")
    until_chapter = req.get("until_chapter")
    if not src or not dst or until_chapter is None:
        raise HTTPException(status_code=422, detail="缺少必填字段: src/dst/until_chapter")
    st = _store_for(work)
    try:
        st.end_relation(src, dst, until_chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.get("/char-states")
def char_states(character_id: str, work: str = "main"):
    return _store_for(work).list_char_states(character_id)


@app.post("/char-states")
def add_char_state_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_char_state(req["character_id"], req["chapter"], req["change_type"],
                      req["summary"],
                      before_state=req.get("before_state"),
                      after_state=req.get("after_state"),
                      trigger_event=req.get("trigger_event"),
                      arc_phase=req.get("arc_phase"),
                      affects_voice=req.get("affects_voice"),
                      confidence=req.get("confidence", "confirmed"))
    return {"ok": True}


@app.get("/char-state-at")
def char_state_at(character_id: str, chapter: int, work: str = "main"):
    """查询角色在某章时刻的完整状态快照(时点查询,设计文档 §3.6)。
    返回该章时刻的能力/关系/性格/弧光阶段。"""
    return _store_for(work).char_state_at(character_id, chapter)


@app.get("/voice-profile")
def get_voice_profile_endpoint(character_id: str, work: str = "main"):
    """获取角色声线指纹(9节 voice_profile,设计文档 §3.1.2)。
    批D P1-11 后端跟进:此前 store.get_voice_profile 无 REST 暴露 → 前端声线指纹只在
    fold 响应里一次性展示、刷新不回显。补此 GET(镜像 /char-states)让指纹常驻回显。
    角色无指纹时返回 null(不 500),前端据此隐藏声音区或提示尚未建立。"""
    return _store_for(work).get_voice_profile(character_id)



class MotifIn(BaseModel):
    name: str
    theme: str = ""
    echoes: str = ""
    unfolding: str = ""


@app.post("/motifs-new")
def add_motif_ep(m: MotifIn, work: str = "main"):
    _store_for(work).add_motif(m.name, m.theme, m.echoes, m.unfolding)
    return {"ok": True}


@app.patch("/motifs/{mid}")
def edit_motif(mid: str, m: MotifIn, work: str = "main"):
    _store_for(work).update_motif(mid, {"name": m.name, "theme": m.theme, "echoes": m.echoes,
                                        "unfolding": m.unfolding})
    return {"ok": True}


@app.delete("/motifs/{mid}")
def del_motif(mid: str, work: str = "main"):
    _store_for(work).delete_motif(mid)
    return {"ok": True}


# ===== 素材库 material(非正典写作材料;镜像 motif/promise CRUD 形态)=====
# 与设定库(codex=正典)严格分开:不进知识图谱、不被 ingest、不参与限知/伏笔/QC/时间线。

def _check_material_kind(kind: str | None) -> None:
    if kind is not None and kind not in MATERIAL_KINDS:
        raise HTTPException(status_code=422,
                            detail=f"非法素材分类 kind='{kind}'(合法: {list(MATERIAL_KINDS)})")


class MaterialIn(BaseModel):
    title: str
    body: str | None = None
    kind: str = "note"
    tags: list[str] = []
    source: str | None = None


class MaterialPatch(BaseModel):
    title: str | None = None
    body: str | None = None
    kind: str | None = None
    tags: list[str] | None = None
    source: str | None = None


@app.get("/materials")
def list_materials_ep(kind: str | None = None, limit: int | None = Query(default=None, ge=1, le=500),
                      cursor: int = Query(default=0, ge=0), q: str = "", view: str = "all",
                      work: str = "main"):
    _check_material_kind(kind)
    rows = _store_for(work).list_materials(kind, archived=True if view == "archived" else False)
    needle = (q or "").strip().lower()
    if needle:
        rows = [m for m in rows if needle in "\n".join([
            str(m.get("title") or ""), str(m.get("body") or ""),
            " ".join(m.get("tags") or []), " ".join(m.get("ref_tags") or []),
        ]).lower()]
    if view == "pinned":
        rows = [m for m in rows if m.get("pinned")]
    elif view == "referenced":
        rows = [m for m in rows if (m.get("recall_count") or 0) > 0]
    elif view == "untagged":
        rows = [m for m in rows if not (m.get("tags") or m.get("ref_tags"))]
    if limit is None:
        return rows
    start = int(cursor or 0)
    items = rows[start:start + limit]
    next_cursor = start + limit if start + limit < len(rows) else None
    return {"items": items, "next_cursor": next_cursor, "total": len(rows)}


@app.post("/materials")
def add_material_ep(m: MaterialIn, work: str = "main"):
    _check_material_kind(m.kind)
    mid = _store_for(work).add_material(m.title, m.body, m.kind, m.tags, m.source)
    return {"ok": True, "id": mid}


@app.patch("/materials/{mid}")
def edit_material_ep(mid: str, m: MaterialPatch, work: str = "main"):
    _check_material_kind(m.kind)
    fields = {k: v for k, v in m.model_dump().items() if v is not None}
    found = _store_for(work).update_material(mid, fields)
    if not found:
        raise HTTPException(status_code=404, detail=f"material '{mid}' 不存在")
    return {"ok": True}


@app.delete("/materials/{mid}")
def del_material_ep(mid: str, confirm_impact_token: str | None = None, work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), "material", mid, work, confirm_impact_token)


# ===== 素材导入(多格式 → AI 切分打标摘要 → 预览确认 → 落库)=====
_import_jobs: dict = {}   # job_id → {stage, done, total, items, error, work}


class ImportCommitReq(BaseModel):
    items: list[dict]


def _run_import(job_id: str, markdown: str, source: str | None) -> None:
    """后台流水线:AI 切分打标摘要 → 结果存 job 待预览(不直接落库)。fail-soft。"""
    from scribe3.llm import hermes_complete
    from scribe3.material_import import split_and_tag
    job = _import_jobs.get(job_id)
    if job is None:
        return
    try:
        job["stage"] = "AI 切分打标中"
        job["items"] = split_and_tag(
            markdown, lambda p: hermes_complete(p, max_tokens=4000), source)
        job["total"] = len(job["items"])
        job["stage"] = "待预览确认"
    except Exception as e:
        job["stage"], job["error"] = "error", str(e)[:200]
    finally:
        job["done"] = True


@app.post("/materials/import")
async def material_import_ep(background: BackgroundTasks, text: str = Form(None),
                            url: str = Form(None), source: str = Form(None),
                            file: UploadFile = File(None), work: str = "main"):
    """导入入口:file(markitdown 解析)/url(httpx 抓)/text → 后台 AI 切分打标 → 返回 job_id。"""
    import uuid
    markdown = ""
    if file is not None:
        import os
        import tempfile
        from scribe3.material_import import parse_to_markdown
        content = await file.read()
        suffix = os.path.splitext(file.filename or "")[1] or ".txt"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(content)
            tmp.close()
            markdown = parse_to_markdown(tmp.name)
        finally:
            os.unlink(tmp.name)
        source = source or file.filename
    elif url:
        import httpx
        markdown = httpx.get(url, timeout=30, follow_redirects=True).text
        source = source or url
    elif text:
        markdown = text
    if not (markdown or "").strip():
        raise HTTPException(status_code=422, detail="无内容可导入(text/url/file 至少一个非空)")
    job_id = uuid.uuid4().hex[:12]
    _import_jobs[job_id] = {"stage": "解析完成", "done": False, "total": 0,
                            "items": [], "error": "", "work": work}
    background.add_task(_run_import, job_id, markdown, source)
    return {"job_id": job_id}


@app.get("/materials/import/{job_id}/progress")
async def material_import_progress_ep(job_id: str):
    """SSE 进度推送:解析→切分打标→待预览/完成/错误(0.5s 轮询,上限 5 分钟防挂)。"""
    import asyncio
    import json as _j

    async def gen():
        for _ in range(600):
            job = _import_jobs.get(job_id)
            if job is None:
                yield "data: " + _j.dumps({"stage": "not_found", "done": True}) + "\n\n"
                return
            yield ("data: " + _j.dumps({"stage": job["stage"], "done": job["done"],
                                        "total": job["total"], "error": job["error"]}) + "\n\n")
            if job["done"]:
                return
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/materials/import/{job_id}/preview")
def material_import_preview_ep(job_id: str):
    """预览 AI 切分结果(作者编辑/删条/合并前)。"""
    job = _import_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"导入任务 '{job_id}' 不存在或已清理")
    return {"stage": job["stage"], "done": job["done"], "error": job["error"],
            "items": job["items"]}


@app.post("/materials/import/{job_id}/commit")
def material_import_commit_ep(job_id: str, req: ImportCommitReq, work: str = "main"):
    """作者确认(可编辑后)→ 批量落库 + 建联想边。单条 fail-soft。返回落库数。"""
    st = _store_for(work)
    ids = []
    failed = []
    warnings = []
    for idx, it in enumerate(req.items):
        title = (it.get("title") or "").strip()
        if not title:
            failed.append({"index": idx, "title": "", "reason": "标题为空"})
            continue
        try:
            mid = st.add_material(title, it.get("body"), it.get("kind") or "note",
                                  it.get("tags"), it.get("source"), ref_tags=it.get("ref_tags"))
            ids.append(mid)
            try:
                st.build_material_edges(mid)
            except Exception as e:
                warnings.append({
                    "index": idx,
                    "title": title,
                    "stage": "build_edges",
                    "reason": str(e),
                })
        except Exception as e:
            failed.append({"index": idx, "title": title, "reason": str(e)})
    _import_jobs.pop(job_id, None)
    return {"created": len(ids), "ids": ids, "failed": failed, "warnings": warnings}


@app.get("/materials/recall")
def material_recall_ep(q: str, chapter: int | None = None, k: int = 5, work: str = "main"):
    """素材三通道召回(前端搜索:关键词+语义+图);纯检索排序,不烧 LLM 重排。"""
    return _store_for(work).material_recall(q, chapter, k)


@app.get("/materials/graph")
def material_graph_ep(focus: str | None = None, limit: int = Query(default=200, ge=1, le=2000),
                      hop: int = Query(default=1, ge=1, le=3), work: str = "main"):
    """素材记忆网络:节点(素材)+ relates 联想边,供前端 sigma 可视化。"""
    return _store_for(work).material_graph(focus=focus, limit=limit, hop=hop)


@app.get("/materials/refs-by-chapter")
def material_refs_by_chapter_ep(chapter: int, work: str = "main"):
    """反向溯源:本章参考了哪些素材(+ reason/dimension)。"""
    st = _store_for(work)
    rows = st.material_refs_by_chapter(chapter)
    out = []
    for r in rows:
        m = st.get_material(str(r.get("material_id"))) or {}
        out.append({**r, "title": m.get("title"), "kind": m.get("kind"), "source": m.get("source")})
    return out


@app.get("/materials/{mid}/refs")
def material_refs_ep(mid: str, work: str = "main"):
    """正向溯源:这条素材用在了哪些章。"""
    return _store_for(work).material_refs_by_material(mid)


@app.get("/voice-flags")
def voice_flags(work: str = "main"):
    return _store_for(work).list_voice_flags("open")


@app.post("/voice-flags/{fid}/resolve")
def resolve_voice_flag_endpoint(fid: str, work: str = "main"):
    """关闭声音演变 flag(status: open → done)。flag 不存在→404。"""
    found = _store_for(work).resolve_voice_flag(fid)
    if not found:
        raise HTTPException(status_code=404, detail=f"voice_evolution_flag '{fid}' 不存在")
    return {"ok": True}


@app.post("/voice-flags/fold")
def fold_voice_flags_endpoint(body: dict, work: str = "main"):
    """半自动声音演变折叠:把角色的 open voice_evolution_flag 折叠进 voice_profile(LLM 演变)。
    body: {"character_id": "role:xxx"}
    返回: {"folded": n, "profile": {...}} 或 {"folded": 0, "degraded": true}
    """
    character_id = body.get("character_id", "")
    if not character_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="character_id 必填")
    from scribe3.llm import hermes_complete
    return _store_for(work).fold_voice_flags(character_id, hermes_complete)


@app.get("/graph")
def graph(chapter: int | None = None, focus: str | None = None,
          limit: int = Query(default=300, ge=1, le=2000), hop: int = Query(default=1, ge=1, le=3),
          work: str = "main"):
    """知识图谱:角色/命题节点 + knows/关系 边(Atlas 视图)。
    Phase0-BE1(千万字基座):默认不再无上限全图返回。
    - focus 给定 → 该实体 ego 子图(focus + hop 跳邻居 + 它们之间的边)。
    - focus 为 None → top-limit 重要度子集(secret 优先),节点总数硬上限 limit。
    - chapter 时间门保留(截至该章;省略=全书)。"""
    return _store_for(work).graph(chapter=chapter, focus=focus, limit=limit, hop=hop)


@app.get("/quality")
def quality(work: str = "main"):
    """质量仪表盘聚合:每章 字数/双层QC问题/因果违规 + 伏笔状态。
    P3-e1 Fix 1: 使用 OVERDUE_SLACK 模块常量(唯一真源),支持 intent.overdue_threshold 覆盖;
    foreshadow.promises 含每条 promise 的 overdue 字段,前端直读,不重算。

    Phase0-BE1(千万字基座):**改读 outline() 章级缓存列**(qc_word_count/qc_issues/qc_causal/
    qc_breakdown),不再逐章 get_chapter 全文 + quality_flags 重算 + 逐章查因果图(数千章=分钟级)。
    缓存由 save_chapter 写时落库;返回字段(seq/title/word_count/qc_issues/qc_breakdown/causal)口径不变。"""
    st = _store_for(work)
    out = st.outline()
    per = []
    for c in out["chapters"]:
        per.append({
            "seq": c["seq"], "title": c.get("title", ""),
            "word_count": c.get("word_count") or 0,
            "qc_issues": c.get("qc_issues") or 0,
            "qc_breakdown": c.get("qc_breakdown") or {
                "repetition": 0, "structural": 0, "purple": 0,
                "ai_tics": 0, "oversaturation": 0},
            "causal": c.get("qc_causal") or 0,
        })
    # 缓存稳定章序按 seq 升序返回(与旧 list_chapters ORDER BY seq 口径一致)
    per.sort(key=lambda x: x["seq"])
    proms = st.list_promises()
    mc = st.max_chapter()
    # 单源阈值:intent 可覆盖 OVERDUE_SLACK(per-work 配置)
    # 经 list_promises 补算窗口后 legacy slack 分支仅数据异常行可达,threshold 近似废弃,留防御
    intent = st.get_intent()
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    prom_list = []
    for p in proms:
        is_overdue = _overdue_flag(p, mc, slack)
        prom_list.append({
            "id": p.get("id"), "text": p.get("text", ""),
            "setup_chapter": p.get("setup_chapter"), "status": p["status"],
            "kind": p.get("kind"), "overdue": is_overdue,
        })
    fore = {
        "open": sum(1 for p in proms if p["status"] == "open"),
        "closed": sum(1 for p in proms if p["status"] == "closed"),
        "overdue": sum(1 for p in prom_list if p["overdue"]),
        "promises": prom_list,
    }
    return {"chapters": per, "foreshadow": fore, "total_words": sum(c["word_count"] for c in per)}


@app.get("/intent")
def get_intent(work: str = "main"):
    return _store_for(work).get_intent()


class IntentIn(BaseModel):
    reader_feeling: str = ""
    emotional_arc: str = ""
    red_lines: str = ""
    overdue_threshold: int | None = None
    total_word_goal: int | None = None   # 整稿目标字数;None → 前端回退默认 100000
    daily_word_goal: int | None = None   # 每日目标字数;None → 不显示每日进度


@app.put("/intent")
def put_intent(i: IntentIn, work: str = "main"):
    _store_for(work).set_intent(i.model_dump())
    return {"ok": True}


@app.get("/progress")
def get_progress(work: str = "main", window: str = "all"):
    """日字数序列 + 累计曲线 + streak + 目标完成度(只读,数据源 daily_progress 表)。
    window: '30' | '90' | 'all'(默认 all)——仅影响图表区间,streak/heatmap 始终全量。"""
    return _store_for(work).progress(window=window)


def _codex_block(st, reveal: bool = True) -> str:
    """注入当前书的「设定圣经」(codex:角色前史/势力/物件/术语/世界规则/母题)。
    关键:经 codex 表(非命题)建的书,_editor_system 的 facts_at 注入为空 → 主编看不到设定;
    此块直接从当前 store 的 codex 表读,确保主编(讨论/写作)看到的是**这本书**的设定,
    不依赖 MCP(MCP 网关连固定库,会串到别的书)。

    reveal=False(限知模式,focalizer 非空):对 backstory_secret 角色隐去 backstory,
    防 POV 倒灌(F-3——限知章设定圣经明文注入私密前史);reveal=True(全知)保留。"""
    def _safe(fn):
        try:
            return fn() or []
        except Exception:
            return []
    parts = []
    chars = _safe(st.characters)
    if chars:
        cl = []
        for c in chars[:14]:
            traits = (c.traits or {}) if hasattr(c, 'traits') else {}
            bs = traits.get('backstory') or ''
            if bs and not reveal and traits.get('backstory_secret'):
                bs = ''   # 限知模式:私密前史对帧外隐去(F-3)
            cl.append(f"- {c.name}:{bs[:48]}" if bs else f"- {c.name}")
        parts.append("〔角色〕\n" + "\n".join(cl))
    facs = _safe(st.list_factions) if hasattr(st, 'list_factions') else []
    if facs:
        parts.append("〔势力〕" + "；".join(f"{f.get('name')}（{(f.get('ideology') or '')[:18]}）" for f in facs[:10]))
    items = _safe(st.list_items) if hasattr(st, 'list_items') else []
    if items:
        parts.append("〔物件〕" + "；".join(f"{i.get('name')}" for i in items[:14]))
    terms = _safe(st.list_terms) if hasattr(st, 'list_terms') else []
    if terms:
        parts.append("〔术语〕" + "；".join(f"{t.get('name')}:{(t.get('definition') or '')[:16]}" for t in terms[:14]))
    rules = _safe(st.list_world_rules) if hasattr(st, 'list_world_rules') else []
    if rules:
        parts.append("〔世界规则〕" + "；".join(f"{r.get('name')}（代价:{(r.get('cost') or '—')[:14]}）" for r in rules[:10]))
    motifs = _safe(st.list_motifs) if hasattr(st, 'list_motifs') else []
    if motifs:
        parts.append("〔母题〕" + "；".join(m.get('name') for m in motifs[:10]))
    return "\n".join(parts)


def _editor_system(st, focalizer: str = "", chapter: int = None) -> str:
    """主编对话的系统提示:注入本书北极星 + 角色 + 已确立设定。

    focalizer 非空(限知章):设定块只注入焦点者帧内可见事实,secret 明文屏蔽;
    focalizer 空(作者全知视角):M6 设定三态注入(opt-in)——本书未配 injection_mode 时
      等同旧 facts_at(99999)[:28] 全量(含私密标记,行为一字不变);一旦有 fact 显式配了
      injection_mode 则启用门控(None/always→恒注入,detected 挂真实实体→须本章草料提及,
      never→不注入,世界级命题→恒注入)+ 字符预算裁剪。
    """
    intent = st.get_intent()
    chars = st.characters()
    ctx_chars = "、".join(c.name for c in chars[:14]) or "(尚无角色)"

    if focalizer:
        # 限知模式:只注入焦点者帧内可见事实,secret value 物理屏蔽
        try:
            from scribe3.knowledge import project_frame
            ch = chapter if chapter is not None else 1
            frame = project_frame(st, focalizer, ch)
            masked = _facts(frame.facts, reveal_secret=False)
            visible = [d for d in masked if d.get("value") is not None]
            lines = [
                f"- {d.get('entity', '')} · {d.get('attribute', '')}:{d.get('value', '')}"
                for d in visible[:28]
            ]
        except Exception:
            lines = []
        ctx_set = "\n".join(lines) or "(焦点者帧内暂无可见设定)"
        set_label = f"【焦点者({focalizer})帧内可见设定(限知基座,帧外私密已屏蔽)】"
    else:
        # 作者全知视角:M6 设定三态注入(opt-in,migration 056)。
        # 真·向后兼容:本书从未配 injection_mode → assemble_injection 回 fallback=True,
        #   此处直接走旧 facts[:28] 全量,旧书行为一字不变(未点名实体/世界级命题/secret 均不丢)。
        # 一旦作者显式配了 ≥1 条 injection_mode → 启用门控:None/always/世界级 恒注入,
        #   detected 挂真实实体须本章草料(synopsis/beats/scene_truth)提及,never 不注入。
        def _line(f):
            return (f"- {f.entity_id} · {f.attribute}:{f.value}"
                    + ("(私密/伏线)" if f.secret else ""))
        try:
            from scribe3.brief import assemble_injection
            inj = assemble_injection(st, chapter)
            if inj["fallback"]:
                lines = [_line(f) for f in inj["facts"][:28]]
            else:
                lines = [f"- {i['text']}" for i in inj["chosen"]]
        except Exception:
            lines = [_line(f) for f in st.facts_at(99999)[:28]]
        ctx_set = "\n".join(lines) or "(尚无设定)"
        set_label = "【已确立设定(你全知,含私密伏线)】"

    # 开着的伏笔:预注入强提醒(易忘项;母题/事件等详情留主编按需调工具查)
    promises = st.open_promises() if hasattr(st, "open_promises") else []
    rem = ""
    if promises:
        items = "；".join(
            f"第{p.get('setup_chapter')}章埋:{(p.get('text') or '')[:30]}" for p in promises[:6])
        rem = f"\n【⚠ 开着的承诺线·勿忘(适时推进/回收,别让它凭空消失)】{items}"
    # 素材记忆能力提示(非空库时引导主编按需经 s3_material_recall 唤起参考素材;借鉴非事实)
    mat_hint = ""
    try:
        if st.list_materials():
            mat_hint = ("\n【素材记忆库】作者备有素材记忆(研究/风格/桥段等参考),讨论或构思时"
                        "可经 s3_material_recall(query) 按当前话题唤起相关素材借鉴(借鉴非照搬),"
                        "并向作者说明为什么参考。")
    except Exception:
        pass
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        f"【北极星·作品意图】读者感受:{intent['reader_feeling'] or '—'};"
        f"情感弧:{intent['emotional_arc'] or '—'};绝不背叛的红线:{intent['red_lines'] or '—'}\n"
        f"【主要角色】{ctx_chars}\n{set_label}\n{ctx_set}\n\n"
        f"【本书设定圣经(以下即这本书的全部设定,务必只据此写,绝不串入别的书/别的世界)】\n{_codex_block(st, reveal=not focalizer) or '(尚无设定)'}\n\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣上面的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    ) + rem + mat_hint


def _pulse_digest(st, seq: int | None) -> str:
    """主编主动化 T3(时机C):讨论模式注入的脉搏速览段(≤400 字)。
    decision 级全文(主编该主动带出的话头)+ nudge 级只计数(防唠叨);
    写作模式已有完整简报,不注入此段(防双重施压)。fail-soft:挂了返回空段。"""
    if seq is None:
        return ""
    try:
        from scribe3.pulse import chapter_pulse
        p = chapter_pulse(st, int(seq))
        decisions, nudges = [], 0
        for d in p["dimensions"]:
            for it in d["items"]:
                if it["severity"] == "decision":
                    decisions.append(it["message"])
                elif it["severity"] == "nudge":
                    nudges += 1
        if not decisions and not nudges:
            return ""
        lines = [f"\n\n## 本章脉搏速览(第{seq}章,系统确定性信号——讨论时自然带出相关项,勿逐条播报)"]
        lines += [f"- 【需决策】{m}" for m in decisions[:4]]
        if nudges:
            lines.append(f"- 另有 {nudges} 项建议级提示(作者问到再展开)")
        out, total = [], 0
        for ln in lines:
            if total + len(ln) > 600:   # 按行裁剪,不截半句(审查 P2-10)
                break
            out.append(ln)
            total += len(ln)
        return "\n".join(out)
    except Exception as e:
        logging.getLogger("scribe3").warning("pulse digest 失败(忽略): %s", e)
        return ""


# S-001:纯讨论(hermes_complete_stream 单遍无续接)对开放式提问,doubao 易回"让我查查"
# 之类思考开场白然后单轮结束。给纯讨论 sysmsg 加通用作答引导,让开放问题也直接给完整方案,
# 不必逼作者每次都写"别说让我查查"。只作用于 chat_stream(纯讨论);写作/agentic 路径不受影响。
_DISCUSSION_DIRECTIVE = (
    "\n\n【作答方式(纯讨论)】直接、完整、可操作地回答,一次说透。"
    "不要用『让我查查/让我想想/让我先看看』这类拖延开场——你此刻在纯讨论对话中,"
    "没有实时查询工具,请直接凭你的编辑学识与上方已有设定作答。"
    "作者要方案时,当场给出完整选项(含各自代价),不要只起个头就停。")


@app.get("/chat/stream")
def chat_stream(msg: str, work: str = "main", seq: int | None = None):
    """主编对话(SSE 流式)。注入本书设定上下文,经 Hermes 逐字回流。
    seq(时机C):当前讨论章号,注入脉搏速览——主编讨论时能主动带出超期伏笔等信号。"""
    from scribe3.llm import hermes_complete_stream
    sysmsg = _editor_system(_store_for(work)) + _pulse_digest(_store_for(work), seq) + _DISCUSSION_DIRECTIVE

    def gen():
        try:
            for delta in hermes_complete_stream(msg, system=sysmsg):
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:  # 失败如实回流,不静默
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


_responses_events = None  # 测试可 monkeypatch


@app.get("/chat/agentic-stream")
def chat_agentic_stream(msg: str, work: str = "main", seq: int | None = None):
    """主编 agentic 对话(SSE):经 scribe3 网关 /v1/responses,主编自调 s3_ 工具查 SurrealDB 真实数据。
    事件:tool(工具调用提示)/delta(回复片段)/done。"""
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.llm import hermes_responses_events
    fn = _responses_events or hermes_responses_events
    adapter = HermesEventAdapter()
    # H-01:工具 work-scoped,所有作品都可挂工具;提示必须钉死当前 work,防跨书读写。
    with_tools = _work_has_tools(work)
    instructions = _editor_system(_store_for(work)) + _pulse_digest(_store_for(work), seq)
    if with_tools:
        instructions += _s3_work_scope_block(work) + (
            "\n\n你能调用 s3_ 工具实时查询/操作这部书的 SurrealDB(知识帧 s3_project_frame、反讽 s3_dramatic_irony、"
            "伏笔 s3_list_promises、母题 s3_list_motifs、章节 s3_get_chapter、确定性QC s3_qc_chapter、纪律判官 "
            "s3_discipline_check、语义召回 s3_semantic_recall、因果 s3_causal_complete 等)。"
            "回答前先用只读工具核实真实数据,不臆测;引用数据时说明来自哪个工具。"
            "写操作(加角色/事实/伏笔等)会进入待批,不会立即生效。"
        )

    # Task 11:稳定 session key = work+thread(切章不换 Hermes session,主编历史连续);
    # 会话续接锚 conversation/previous_response 从线程行取(掉链常态,由 Scribe 侧重建兜底)。
    turn = _editor_turn_context(work)

    def gen():
        resp_id = None
        try:
            events = _response_events_iter(
                fn,
                msg,
                instructions,
                with_tools=with_tools,
                session_key=turn.session_key,
                conversation=turn.conversation_id,
                previous_response_id=turn.previous_response_id,
                store=True,
                server_label=SCRIBE3_READ_MCP_LABEL,
            )
            for ev in events:
                app_ev = adapter.adapt(ev)
                if app_ev["kind"] == "text.delta":
                    d = app_ev.get("delta", "")
                    if d:
                        yield f"data: {json.dumps({'delta': d}, ensure_ascii=False)}\n\n"
                elif app_ev["kind"] == "tool.started":
                    yield f"data: {json.dumps({'tool': app_ev.get('name', ''), 'tool_args': app_ev.get('arguments', '')}, ensure_ascii=False)}\n\n"
                elif app_ev["kind"] == "tool.output":
                    yield f"data: {json.dumps({'tool_output': app_ev.get('output', ''), 'tool_call_id': app_ev.get('call_id')}, ensure_ascii=False)}\n\n"
                elif app_ev["kind"] == "approval.requested":
                    yield f"data: {json.dumps({'approval': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'message')}}, ensure_ascii=False)}\n\n"
                elif app_ev["kind"] == "approval.resolved":
                    yield f"data: {json.dumps({'approval_resolved': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'decision')}}, ensure_ascii=False)}\n\n"
                elif app_ev["kind"] == "run.completed":
                    # 记新 response id,turn 结束后回写线程,供下一轮 previous_response_id 续接。
                    resp_id = app_ev.get("response_id") or resp_id
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        if resp_id:
            try:
                # 竞态记账(#5):同一线程若并发两 turn,后完成者覆盖 previous_response_id。
                # 现状不显现——前端 ChiefDock 默认 agentic:false(本路未启用)且 UI busy 期
                # 串行化发送;重新启用 agentic 或引入并发发送时需加"仅当更晚 turn 才覆盖"的护栏。
                _store_for(work).update_thread_response_id(turn.thread_id, resp_id)
            except Exception:
                logging.getLogger("scribe3").warning("thread response_id 回写失败(忽略)", exc_info=True)
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


def _editor_identity_block() -> str:
    """主编身份 + 硬协议(纯身份,零数据注入)。I1:v1 上下文段由 envelope 独占,故 v1
    只取本块作身份,避免 _editor_system 的设定/角色/伏笔注入与 envelope 的 canonical/global
    重复(facts 出现 2 次、promises 最多 3 次的注意力稀释病灶,B-3 同型)。
    与 _editor_system 共享措辞但独立成函数:_editor_system 保持原样(旧路径字节一致),
    本块把"上面的世界观与北极星"改指"下方提供的"——v1 里数据段在身份之后由 envelope 给出。"""
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣下方提供的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    )


def _secret_guard_block(st, chapter: int | None = None) -> str:
    """S-002:知情主角限知泄露修复。project_frame 只屏蔽【焦点者不知道】的帧外私密,
    但焦点者是知情主角时,他自己知道的核心悬念秘密(真名/前史/印记)在帧内、且 backstory
    里也写了 → 写他视角就把该留到揭示章的秘密提前泄露给读者(知情 POV 倒灌)。
    修复:对本书 secret 命题的破绽词(leak_markers),即便视角人物知情,也硬性约束本章
    藏匿、禁明写。默认所有 secret 都藏;作者要在某章揭示时,写作指令里明说'本章揭示X'覆盖。
    无 secret 命题 → 空串(默认行为字节不变,旧书/无私密书零变化)。"""
    try:
        facts = st.facts_at(chapter or 99999)
    except Exception:
        return ""
    markers: list[str] = []
    for f in facts:
        if getattr(f, "secret", False):
            markers.extend(getattr(f, "leak_markers", None) or [])
    markers = list(dict.fromkeys(m for m in markers if m and str(m).strip()))
    if not markers:
        return ""
    banned = "、".join(markers[:40])
    return (
        "\n\n【核心悬念·限知纪律(本章须藏·硬约束)】本书有读者尚不该知道的核心伏线。"
        "即便视角人物自己知情,本章也**绝不明写**这些秘密——只可用身体反应、回避、物件、"
        "欲言又止来暗示,把重量压住、留到揭示章引爆。**严禁在正文出现以下破绽词**(含其明显变体):"
        f"{banned}。剧情若逼近,以『藏着不说/一闪而过/避而不答』处理,绝不点破。")


def _write_protocol_block() -> str:
    """写作硬协议(讨论 vs 动稿)+ 文风基准(纯静态,零数据)。原 _editor_write_system 内联串
    原样抽出,供旧 _editor_write_system 与 v1 共用——不改一字,保旧路径字节一致。"""
    return (
        "\n\n你是这部小说的主编,以**作者视角**帮作者写/改这本书的手稿——作者在写一本书,"
        "不是从某个角色的受限视角做渲染。\n\n"
        "## 核心判断:讨论 vs 动稿\n"
        "- 若作者只是讨论/提问/点评/分析/给意见 → **纯文字回复,绝对禁止输出 ⟦PROPOSAL⟧ 围栏**。\n"
        "- **仅当**作者明确使用「写/改/续写/帮我写/重写/把这段…/本章这样展开」等写作动词,\n"
        "  或作者提供了角色演绎草稿请求成文时 → 先简短说一句你的处理思路,"
        "然后把**书的本章正文**放进围栏:\n"
        "  (scope 取 chapter=整章 / selection=改选中段 / append=续写接在后面)\n"
        "  ⟦PROPOSAL scope=chapter⟧\n  （书的正文，作者笔调，纯散文，不要解说）\n  ⟦/PROPOSAL⟧\n"
        "- **多候选**:当作者对某段改写要求「2-3 个候选/几个版本/不同侧重」时,**连续输出 2-3 个独立的**\n"
        "  ⟦PROPOSAL scope=selection⟧…⟦/PROPOSAL⟧ 围栏,每个是对同一段的不同改法(如:一个收紧、"
        "一个加潜台词、一个换感官切入),围栏之间可不写解说。其余情况只出一个围栏。\n\n"
        "## 写作规则\n"
        "- 若作者给了某角色的「演绎草稿」(那角色这一场的限知体验)作为素材,把它**织进**书的叙事。\n"
        "- 尊重已确立设定/伏笔/北极星意图。默认作者视角(可全知);仅当作者明确指定本章跟某焦点者的"
        "限知走时,叙事才贴该视角、不写他不知道的私密。\n\n"
        "## 文风基准:贴《乱世铜炉》(志怪笔记体)——两条硬要求\n"
        "1. **古白话语体**:句子要带旧白话的筋骨与风物实词,少用现代抽象/翻译腔。多用'端的、岂料、怎禁得、"
        "却原来、一径、约莫'这类词;状物用具体名物(花脚毛驴、青骡子、喜糕、水酒)而非笼统形容。"
        "**禁**'像散了一地的骨头''张牙舞爪'这类用力过猛的现代文学比喻——冷笔、素描,信物自身说话。\n"
        "2. **世界密度(乱世铜炉的命门)**:每章须织入与主线无关、却让世界活起来的市井风物侧笔——"
        "婚丧社戏的张罗、乡邻帮衬、打更人讨水酒、行当忌讳、节庆吃食。别一上来直奔情节;让村镇先有烟火气,"
        "妖异方有依附。范例语感(仅供体感,勿照抄字句):\n"
        "  「" + _LUANSHI_EXEMPLAR + "」\n"
        "  ——注意它如何用一整段写婚宴的杀猪宰羊、姑嫂蒸糕、打更人讨酒,世界先活,事件才落地。"
    )


def _write_revision_block() -> str:
    """M8 修订纪律(恒注入)。原 _editor_write_system 内联串原样抽出,旧/ v1 共用。"""
    return (
        "\n\n## 修订纪律\n"
        "- 改稿默认 **span 级定向**:只重写被指出的最小片段,其余一字不动;"
        "除非作者明确要求整章重写。\n"
        "- 禁止开放式整章自评重写(critique 放在大纲/节拍层;正文层只做表达增强)——"
        "自评重写会同质化、越改越平。\n"
        "- 高潮章作者要多候选时,按已有多候选围栏规则出 2-3 个独立版本。")


def _editor_write_system(st, focalizer: str = "", chapter: int = None) -> str:
    # 旧路径字节一致:_editor_system(身份+设定数据) + _write_protocol_block(静态硬协议/文风)
    base = (_editor_system(st, focalizer=focalizer, chapter=chapter)
            + _write_protocol_block() + _secret_guard_block(st, chapter))
    # Task7:章前简报注入(chapter 已知才组装;fail-safe——组装异常只 warning 不阻断写作)
    brief_txt = ""
    if chapter is not None:
        try:
            from scribe3.brief import assemble_chapter_brief
            _brief = assemble_chapter_brief(st, chapter, focalizer=focalizer)
            sec = _brief.get("sections") or {}
            _pd = sec.get("promises") or {}
            # 空简报判 sections 各桶(text 恒含标题行,不能判 text)
            if (sec.get("arcs") or _pd.get("reminders") or _pd.get("directives")
                    or _pd.get("decisions") or (sec.get("loops") or {}).get("weighted")
                    or sec.get("heartbeat")):
                brief_txt = _brief.get("text") or ""
        except Exception as _bf_e:
            import logging
            logging.getLogger("scribe3").warning("章前简报组装失败(non-fatal): %s", _bf_e)
    # Task7:M8 修订纪律(恒注入,与是否有简报无关)
    revision = _write_revision_block()
    return base + revision + (("\n\n" + brief_txt) if brief_txt else "")


_LUANSHI_EXEMPLAR = (
    "看着贺客如潮，满日不绝，韩诤喜不自禁，顾不得年迈体衰，趁着兴头，频频把盏敬客，岂料同村几个毛头小伙"
    "喝发了兴，见主人尽欢，也都意气风发起来，一再持酒相劝。眼看着月儿西移，打更的刘时喜在门口来回好几遭了，"
    "讨了好几杯水酒喝。"
)


_WRITE_VERB_RE = re.compile(
    r"写|改|续写|帮我写|重写|把这段|本章|展开|写出来|写一段|续到"
)

_FALLBACK_MIN_CHARS = 120  # 兜底散文最短字数阈值(更短的视为讨论)

# P2-a Fix6: 兜底剥离——主编开场白标志词(出现即截断,保留后续散文主体)
_PREAMBLE_SIGNALS = re.compile(
    r"(?:^|\n)(?:好的[,,,。]?\s*|我的处理思路\s*[:：]|处理思路\s*[:：]|思路\s*[:：]|建议\s*[:：]|我来|我将|我会)[^\n]*\n",
    re.MULTILINE,
)
_PREAMBLE_SPLIT = re.compile(
    r"(?:我的处理思路|处理思路|思路\s*[:：]|建议\s*[:：])[^\n]*\n"
)


def _strip_preamble(text: str) -> str:
    """剥离兜底 proposal 中模型的开场解说段(对话话术),只保留散文主体。
    策略:找首个双换行分隔符(\n\n)或⟦标志前的解说段,若首段含"思路/建议/处理"等关键词则丢弃首段。
    保守:若判断不确定则保留全文(宁多勿少)。"""
    stripped = text.strip()
    # 首选:按 \n\n 段落切分,若第一段含开场标志词则丢弃
    paras = stripped.split("\n\n", 1)
    if len(paras) == 2:
        first, rest = paras
        SIGNALS = ("我的处理思路", "处理思路", "思路：", "思路:", "建议：", "建议:", "我来", "我将", "我会")
        if any(sig in first for sig in SIGNALS) and len(rest.strip()) >= _FALLBACK_MIN_CHARS:
            return rest.strip()
    # 退路:若首行含明确标志词,尝试从第二行起
    lines = stripped.splitlines()
    if lines:
        SIGNALS = ("我的处理思路", "处理思路", "思路：", "思路:", "建议：", "建议:")
        if any(sig in lines[0] for sig in SIGNALS) and len(lines) > 1:
            return "\n".join(lines[1:]).strip()
    return stripped


def _is_write_intent(msg) -> bool:
    """检测用户消息是否含写作动词(镜像 _editor_write_system 的围栏触发规则)。
    msg 可以是 str 或 list(含图片的 content 块)。"""
    if isinstance(msg, str):
        text = msg
    elif isinstance(msg, list):
        text = " ".join(
            block.get("text", "") if isinstance(block, dict) else ""
            for block in msg
        )
    else:
        text = str(msg)
    return bool(_WRITE_VERB_RE.search(text))


def _stream_write(message, instructions: str, expect_proposal: bool = False,
                  with_tools: bool = True, on_complete=None,
                  mcp_server_label: str = SCRIBE3_READ_MCP_LABEL):
    """共用的写作 SSE 流生成器(GET/POST 复用,P20 DRY)。
    message: str(纯文本) 或 list(含图片附件)。
    expect_proposal: 若为 True 且模型未输出围栏但散文足够长,在流末尾追加兜底 proposal 事件。
    with_tools:H-01 work-scoped MCP 开关;为 True 时 instructions 必须已钉死当前 work。
    on_complete:北极星任务1——流尽后以 assistant 落库文本回调一次(围栏外散文+提案标记,
    不含提案正文,台账 D-003);回调异常吞掉(best-effort,D-004),绝不影响 SSE 收尾。"""
    import json as _j
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.llm import hermes_responses_events
    from scribe3.proposal import ProposalParser
    fn = _responses_events or hermes_responses_events
    adapter = HermesEventAdapter()
    parser = ProposalParser()
    prop = {"scope": None, "prose": []}
    prop_marks: list[str] = []   # 本轮出过的提案标记(scope+字数),落库口径 D-003

    # 兜底追踪状态
    saw_proposal = False
    delta_acc: list[str] = []   # 累积全部 delta 文本,用于兜底长散文
    trace = {"status": "streaming", "tool_calls": [], "tool_outputs": [],
             "response_id": None, "usage": None}

    def drain(events):
        nonlocal saw_proposal
        for kind, val in events:
            if kind == "delta":
                delta_acc.append(val)
                yield f"data: {_j.dumps({'delta': val}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_open":
                saw_proposal = True
                prop["scope"] = val
                yield f"data: {_j.dumps({'proposal_start': {'scope': val}}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_delta":
                prop["prose"].append(val)
                yield f"data: {_j.dumps({'proposal_chunk': {'text': val}}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_close":
                yield f"data: {_j.dumps({'proposal': {'scope': prop['scope'], 'prose': ''.join(prop['prose'])}}, ensure_ascii=False)}\n\n"
                prop_marks.append(f"⟦提案 scope={prop['scope']}·{len(''.join(prop['prose']))}字⟧")
                prop["scope"] = None
                prop["prose"] = []

    try:
        for ev in _response_events_iter(fn, message, instructions, with_tools=with_tools, store=True,
                                        server_label=mcp_server_label):
            app_ev = adapter.adapt(ev)
            if app_ev["kind"] == "text.delta":
                yield from drain(parser.feed(app_ev.get("delta", "")))
            elif app_ev["kind"] == "tool.started":
                trace["tool_calls"].append({
                    "name": app_ev.get("name", ""),
                    "arguments": app_ev.get("arguments", ""),
                    "call_id": app_ev.get("call_id"),
                })
                yield f"data: {_j.dumps({'tool': app_ev.get('name', '')}, ensure_ascii=False)}\n\n"
            elif app_ev["kind"] == "tool.output":
                trace["tool_outputs"].append({
                    "call_id": app_ev.get("call_id"),
                    "output": app_ev.get("output", ""),
                })
                yield f"data: {_j.dumps({'tool_output': app_ev.get('output', ''), 'tool_call_id': app_ev.get('call_id')}, ensure_ascii=False)}\n\n"
            elif app_ev["kind"] == "approval.requested":
                trace.setdefault("approvals", []).append({
                    "run_id": app_ev.get("run_id"),
                    "approval_id": app_ev.get("approval_id"),
                    "message": app_ev.get("message", ""),
                    "status": "requested",
                })
                yield f"data: {_j.dumps({'approval': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'message')}}, ensure_ascii=False)}\n\n"
            elif app_ev["kind"] == "approval.resolved":
                trace.setdefault("approvals", []).append({
                    "run_id": app_ev.get("run_id"),
                    "approval_id": app_ev.get("approval_id"),
                    "decision": app_ev.get("decision"),
                    "status": "resolved",
                })
                yield f"data: {_j.dumps({'approval_resolved': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'decision')}}, ensure_ascii=False)}\n\n"
            elif app_ev["kind"] == "run.completed":
                trace["status"] = "completed"
                trace["response_id"] = app_ev.get("response_id")
                trace["usage"] = app_ev.get("usage")
            elif app_ev["kind"] == "run.failed":
                trace["status"] = "failed"
                trace["response_id"] = app_ev.get("response_id")
                trace["error"] = app_ev.get("error")
        yield from drain(parser.flush())
        if trace["status"] == "streaming":
            trace["status"] = "completed"
        # 兜底:模型忘写围栏 → 把累积散文包成 chapter 提案末尾推送
        # P2-a Fix6: 剥离首段主编开场白("我的处理思路"/"思路:"/"建议:"等解说),
        # 只把散文主体包进 proposal,避免对话话术混入手稿。
        if expect_proposal and not saw_proposal:
            accumulated = "".join(delta_acc)
            prose_body = _strip_preamble(accumulated)
            if len(prose_body.strip()) >= _FALLBACK_MIN_CHARS:
                prop_marks.append(f"⟦提案 scope=chapter·{len(prose_body)}字·兜底⟧")
                yield (
                    f"data: {_j.dumps({'proposal': {'scope': 'chapter', 'prose': prose_body, 'fallback': True}}, ensure_ascii=False)}\n\n"
                )
        yield 'data: {"done": true}\n\n'
    except Exception as e:
        trace["status"] = "failed"
        trace["error"] = str(e)[:160]
        yield f"data: {_j.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'
    finally:
        # 北极星任务1 + P0门审查 P1-6:落库必须在 finally——客户端断流时 Starlette
        # 在 yield 点抛 GeneratorExit(BaseException,except Exception 接不住),
        # 半截对话也要留痕;本块纯副作用不 yield,GeneratorExit 语义安全(D-004)。
        if on_complete is not None:
            try:
                txt = "".join(delta_acc).strip()
                if prop_marks:
                    txt = (txt + "\n" if txt else "") + " ".join(prop_marks)
                if txt:
                    try:
                        on_complete(txt, trace)
                    except TypeError:
                        on_complete(txt)
            except Exception:
                logging.getLogger("scribe3").warning("chat_message assistant 落库失败(忽略)", exc_info=True)


def _avoid_directive(st, chapter: int, lookback: int = 8, top: int = 40) -> str:
    """前 lookback 章独特措辞 → '本章避免逐字复用'系统指令(服务端确定性防跨章复读)。

    根因:单遍长程生成的"复读病"——模型跨章逐字复用自己偏爱的措辞/动作句(实测 10 章共 106 处
    跨章逐字搬运,逐章 QC 全查不到)。把前文招式喂进【系统指令】,生成时就避开,而非事后删。

    lookback=8 覆盖到全书绝大多数前文(此前 =3 时第 7-10 章看不到前段招式→复读回升);
    刻意母题/专名(奈何谷/镇煞钉/大元炼真经…)经 motif_terms 白名单排除,不进 avoid——
    它们本应复现,逼模型回避反而伤质感(乱世铜炉正以母题手法见长)。
    """
    try:
        from scribe3.critique import distinctive_phrases
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        avoid, seen = [], set()
        for c in st.recent_proses(chapter, k=lookback):
            for ph in distinctive_phrases(c.get("prose", ""), n=8, top=40, allow=allow):
                if ph not in seen and not ph.startswith("#"):
                    seen.add(ph)
                    avoid.append(ph)
        if not avoid:
            return ""
        return ("\n\n【防跨章复读·硬约束】前文已用过下列 ≥8 字措辞/动作句,本章**严禁逐字复用**——"
                "同一个意思换感官/换喻体/换节奏另写(专有名词与刻意母题可保留,忌的是动作描写与句式的偷懒重打):\n"
                + "、".join(f"「{a}」" for a in avoid[:top]))
    except Exception:
        return ""


def _arc_state_block(st, focalizer: str, chapter: int) -> str:
    """构建焦点者弧光状态块:将角色在当前章节的能力/关系/性格/阶段快照注入续写 prompt。"""
    if not focalizer:
        return ""
    snap = st.char_state_at(focalizer, chapter)
    if not snap:
        return ""
    parts = []
    abilities = snap.get("abilities") or {}
    if abilities:
        parts.append("能力:" + "、".join(f"{k}={v}" for k, v in abilities.items()))
    relations = snap.get("relations") or {}
    if relations:
        parts.append("关系:" + "、".join(f"{k}={v}" for k, v in relations.items()))
    personality = snap.get("personality") or ""
    if personality:
        parts.append("性格:" + str(personality))
    phases = snap.get("arc_phases") or []
    if phases:
        parts.append("当前阶段:" + str(phases[-1].get("phase", "")))
    if not parts:
        return ""
    return (f"\n\n## 本章焦点者弧光状态(写作须贴合)\n"
            f"{focalizer}:" + ";".join(parts))


def _voice_anchor_block(st, focalizer: str = "") -> str:
    """构建声音锚注入块:焦点者完整 voice_profile(含3节死字段) + 所有角色对白声音速记。
    用于 /chat/write 的 instructions 末尾,让生成时已在声而非事后 check_ooc。"""
    parts = []

    # 焦点者声音锚(叙述/内心独白贴这个声音)
    if focalizer:
        vp = st.get_voice_profile(focalizer)
        if vp and vp.get("style_summary"):
            line = (f"\n\n## 本章焦点者声音锚\n"
                    f"叙述与内心独白贴「{focalizer}」的声音:{vp['style_summary']}")
            cp = vp.get("catchphrases")
            if cp and isinstance(cp, list):
                line += f" 口头禅:{'、'.join(str(x) for x in cp if x)}。"
            tr = vp.get("tone_rules")
            if tr and isinstance(tr, list):
                line += f" 语气规则:{'；'.join(str(x) for x in tr if x)}。"
            # P3-d: 注入3个此前未用的声音节点
            im = vp.get("internal_monologue_style")
            if im:
                line += f" 内心独白风格:{im}。"
            sp = vp.get("sentence_patterns")
            if sp and isinstance(sp, dict):
                sp_str = "、".join(f"{k}={v}" for k, v in sp.items() if v)
                if sp_str:
                    line += f" 句式:{sp_str}。"
            voc = vp.get("vocabulary_profile")
            if voc and isinstance(voc, dict):
                voc_str = "、".join(str(v) for v in voc.values() if v)
                if voc_str:
                    line += f" 词汇倾向:{voc_str}。"
            rl = vp.get("reference_lines")
            # P3-e1 Fix 2: reference_lines schema 是 object 但消费时须兼容 dict/list 两种形状
            if rl:
                if isinstance(rl, dict):
                    rl_items = list(rl.values())[:2]
                elif isinstance(rl, list):
                    rl_items = rl[:2]
                else:
                    rl_items = []
                if rl_items:
                    line += f" 参考语感:{'｜'.join(str(x) for x in rl_items if x)}"
            # 声音待演变提示:该角色有 open voice_evolution_flag 时附加
            try:
                flags = st.list_voice_flags("open") or []
                focal_flags = [f for f in flags if f.get("character") == focalizer]
                if focal_flags:
                    reasons = "、".join(
                        str(f.get("reason") or f.get("trigger_chapter") or "")
                        for f in focal_flags if f.get("reason") or f.get("trigger_chapter")
                    )
                    if reasons:
                        line += (f"\n\n## 声音待演变提示\n"
                                 f"{focalizer} 因下列情节声音正在转变,行文可体现这种变化:{reasons}")
            except Exception:
                pass
            parts.append(line)

    # 对白声音速记——所有有 profile 的角色,各自对白在声,别串味
    profiles = st.list_voice_profiles() or []
    digests = []
    for p in profiles[:6]:
        cid = p.get("character_id") or ""
        ss = (p.get("style_summary") or "").strip()
        if cid and ss:
            digests.append(f"{cid}—{ss[:30]}")
    if digests:
        parts.append("\n\n## 登场角色对白声音(各自在声,别串味)\n" + "；".join(digests))

    return "".join(parts)


def _motif_block(st) -> str:
    """构建母题注入块:列出贯穿母题(name/theme/echoes),供生成时主动编织。
    空母题表 → 返回空串。上限 5 条,保持 prompt 紧凑。"""
    motifs = st.list_motifs() or []
    if not motifs:
        return ""
    lines = ["## 贯穿母题(可主动编织)"]
    for m in motifs[:5]:
        name = m.get("name") or ""
        theme = m.get("theme") or ""
        echoes = m.get("echoes") or ""
        if not name:
            continue
        entry = name
        if theme:
            entry += f":{theme}"
        if echoes:
            entry += f"（回声:{echoes}）"
        lines.append(entry)
    if len(lines) <= 1:
        return ""
    return "\n\n" + "\n".join(lines)


def _frame_block(st, focalizer: str, chapter: int) -> str:
    """限知帧注入块:将 focalizer 截至本章确知的事实喂进 prompt(私密 value 屏蔽)。
    物理隔断:帧外的事情物理上进不了这段 prompt,生成时无从写他不知道的内容。"""
    if not focalizer:
        return ""
    try:
        from scribe3.knowledge import project_frame
        frame = project_frame(st, focalizer, chapter)
        masked = _facts(frame.facts, reveal_secret=False)   # secret value → None
        # 仅保留 value 不为 None 的条目(secret=True 且未解锁的被屏蔽掉)
        visible = [f for f in masked if f.get("value") is not None]
        if not visible:
            return ""
        lines = [
            f"- {f.get('entity') or ''}|{f.get('attribute', '')}|{f.get('value', '')}"
            for f in visible[:40]
        ]
        return (
            f"\n\n## 本章焦点者【此刻确知】的事实(限知硬边界)\n"
            f"以下是 {focalizer} 截至第 {chapter} 章所知的全部。"
            "**只能据这些写他的所见所想,严禁写他不知道的事**:\n"
            + "\n".join(lines)
        )
    except Exception:
        return ""


def _recap_block(st, chapter: int) -> str:
    """前情注入块:上一章结尾文字 + 关键事件摘要,让主编接着写时不失忆。"""
    if chapter <= 1:
        return ""
    try:
        parts = []
        prev = st.recent_proses(chapter, k=1)   # seq < chapter 最近1章
        if prev:
            tail = (prev[0].get("prose") or "")[-300:]
            if tail:
                parts.append("上一章结尾:\n" + tail)
        evs = st.events_at(chapter - 1) or []
        if evs:
            ev_summ = "；".join(
                str(e.type or e.motivated_by_goal or "")
                for e in evs[:6] if e
            )
            if ev_summ:
                parts.append("上一章关键事件:" + ev_summ)
        if not parts:
            return ""
        return "\n\n## 前情(接着往下写,别重复已发生的)\n" + "\n\n".join(parts)
    except Exception:
        return ""


def _current_tail_block(st, chapter: int) -> str:
    """续写衔接块:当前章已写部分的末段(~400字),让 append 续写自然接上,不另起炉灶。
    若当前章无 prose(全新章)则返回空串,不干扰全新章的生成。"""
    try:
        ch = st.get_chapter(chapter)
        if not ch:
            return ""
        prose = ch.get("prose") or ""
        tail = prose[-400:].strip()
        if not tail:
            return ""
        return (
            "\n\n## 本章已写到这里(若续写,从此处自然接上,别另起炉灶/别重复)\n" + tail
        )
    except Exception:
        return ""


@app.get("/chat/write")
def chat_write(msg: str, chapter: int = 1, focalizer: str = "", phase: str = "",
               work: str = "main", short_mode: bool = False):
    """对话驱动写作(SSE):主编自判讨论 vs 动稿;动稿用 ⟦PROPOSAL⟧ 围栏回传新散文。
    事件:delta(对话,进右轨)/ tool(工具调用)/ proposal(草稿,进中区)/ done。
    P0门对抗审查 P2-1:改调 _assemble_write_instructions 单源——此前 GET 自带一套
    内联组装且已漂移(缺 _revelation_discipline_block 限知揭示纪律),旧注入点教训
    (每新开一个注入点都泄露过一次)对 GET 同样成立;现与 POST/loop 物理同源。
    不落库(台账 D-005,无生产调用方的兼容端点)。"""
    st = _store_for(work)
    _wt = _work_has_tools(work)   # H-01:工具已 work-scoped,组装链提示必须同频钉 work
    instructions = _assemble_write_instructions(
        st, chapter=chapter, focalizer=focalizer, phase=phase,
        seed_words=[], short_mode=short_mode, with_tools=_wt, work=work)
    return StreamingResponse(
        _stream_write(msg, instructions, expect_proposal=_is_write_intent(msg),
                      with_tools=_wt),
        media_type="text/event-stream",
    )


_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGES = 6
_MAX_IMG_BYTES = 5 * 1024 * 1024


class ImageModel(BaseModel):
    data: str
    type: str

    @field_validator("type")
    @classmethod
    def _mime_ok(cls, v: str) -> str:
        if v not in _ALLOWED_MIME:
            raise ValueError(f"unsupported mime: {v}")
        return v

    @field_validator("data")
    @classmethod
    def _size_ok(cls, v: str) -> str:
        import base64
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("invalid base64")
        if len(raw) > _MAX_IMG_BYTES:
            raise ValueError("image too large")
        return v


class ChatWriteReq(BaseModel):
    msg: str
    chapter: int = 1
    focalizer: str = ""
    images: list[ImageModel] = []
    seed_words: list[str] = []   # 浸泡产出的情绪种子词(由前端可选传入),注入写作 prompt
    phase: str = ""              # 阶段角色(Phase0-BE2):plan|draft|final;空=现状不变
    short_mode: bool = False     # 方案B任务16:短篇模式——跳过 build_craft_block 的
                                  # ENGINES["restraint"](留白/克制)注入
    # Task 4:上下文绑定字段一律 optional——契约不硬断存量调用方(1270 项测试/旧前端/
    # loop/pilot)。强制校验挂 SCRIBE3_CONTEXT_SNAPSHOT_V1:开关开 + 字段缺失/过期 → 4xx;
    # 开关关(默认)→ 完全忽略,行为不变。见 context_service.ContextService.enforce。
    context_session_id: str | None = None
    context_revision: int | None = Field(default=None, ge=0)
    context_hash: str | None = Field(default=None, min_length=64, max_length=64)
    thread_id: str | None = None   # Task 6:主编线程归属(一 work 一连续线程)
    focus: dict | None = None      # Task 6:本轮焦点标签(切焦点不切线程,焦点只作每轮标签)

    @field_validator("images")
    @classmethod
    def _count_ok(cls, v: list) -> list:
        if len(v) > _MAX_IMAGES:
            raise ValueError(f"too many images (max {_MAX_IMAGES})")
        return v


def _soak_block(seed_words: list[str]) -> str:
    """浸泡种子词注入块:仅当 seed_words 非空时注入,否则返回空串(不发 LLM,pure-cheap)。
    soak() 需要 LLM 调用,不在写作热路径中自动触发;前端可预先调用 soak 后把 seed_words 传进来。"""
    if not seed_words:
        return ""
    return "\n\n## 情绪种子词(浸泡得出,贴此情绪写)\n" + "、".join(str(w) for w in seed_words)


def _revelation_discipline_block(focalizer: str | None) -> str:
    """限知揭示纪律注入块(M1-①):
    focalizer 为空/None → 返回空串(作者全知章不加);
    focalizer 非空 → 返回信息揭示节制纪律块,对抗配角批发真相病。"""
    if not focalizer:
        return ""
    return (
        f"\n\n## 限知揭示纪律(本章 {focalizer} 限知视角,务必遵守)\n"
        "- 焦点者的「未知」靠现象、误判、半懂、留白逐步透出:让他看见反常的「果」却猜不到「因」,先存疑,真相延后。\n"
        "- 在场的知情者**不得**整段向焦点者陈述背景、来历、数字、门派渊源、因果真相——那是「读设定卡」,不是叙事。"
        "配角要藏话、要欲言又止、要话只说三分。\n"
        "- 凡涉及焦点者本不知的隐情,宁露冰山一角(一个眼神/一件反常的物/一句没说完的话),不可借旁人之口一次说穿。\n"
        "- 数字、年份、人数等设定细节除非剧情必须且自然,否则不写进对话。\n"
        "- **被追问/逼问时绝不倒豆子**:知情者被焦点者(或读者)逼问真相时,连续的设定性陈述**不得超过2-3句**,"
        "之后必须以回避、岔开、反问、沉默、半句没说完、或让对方误判来收住;真相按「半句+留白」一点点漏,"
        "横跨数章慢慢拼,绝不在一场戏里整段独白讲完世界观/来历/机制/操作步骤。\n"
        "- **禁止「临死/摊牌前长篇身世独白」**:身世、动机、二十年前的因果要靠前文物象暗示分散打碎,"
        "高潮场只留动作与一两句点睛,不要插叙整段往事。\n"
        "- **禁止排比抒情回环**:不可用「想起A、想起B、想起C」「至少…至少…」这类同句式排比或同一串意象的回环来堆砌、复述情绪;"
        "情绪靠一个动作、一件物象点到即止。"
    )


def _focalizer_sincerity_block() -> str:
    """方案B任务13b:叙述者真诚视角硬约束(与 focalizer 限知引擎同向,是防
    "知情POV倒灌"的又一道文字层约束)——不管本章是否标注了反转/是否限知,
    叙述者的措辞都不得带上只有事后才成立的"知情腔",否则等于提前剧透。
    始终附带,不因参数为空而跳过(与 _final_reminder 同类,恒定注入)。"""
    return (
        "\n\n【叙述者真诚视角】叙述者必须真诚相信自己当前视角的认知,"
        "不得写出暗示后文反转的知情语气(如提前埋「果然」「殊不知」「万万没想到」式的"
        "预告腔,或用只有揭示之后才成立的措辞去描述当下场景)。"
    )


def _phase_role_block(phase: str) -> str:
    """阶段角色提示块(Phase0-BE2 四阶段):按写作阶段微调主编侧重。
    phase 空 → 返回空串(默认行为不变)。plan/draft/final 各加一句角色提示,挂 instructions 末尾。"""
    p = (phase or "").strip().lower()
    roles = {
        "plan": "## 阶段角色(规划期)\n你此刻是规划者:重事件因果与结构骨架——先把这章要发生什么、"
                "推动哪条线、落哪些伏笔/弧光说清,暂不雕字句。",
        "draft": "## 阶段角色(草稿期)\n你此刻是写手:重限知帧——严格贴焦点者所知所感铺陈,"
                 "先把场景与节拍落成连贯草稿,允许糙,但不得越界写焦点者不知之事。",
        "final": "## 阶段角色(正文期)\n你此刻是编审:重 QC——逐句收紧文风、清复读与 AI 腔、"
                 "查情感直说与限知泄露,把草稿打磨成定稿。",
    }
    block = roles.get(p)
    return f"\n\n{block}" if block else ""


_OUTLINE_BUDGET = 1200   # 大纲/节拍注入字符上限(与 M6 事实注入 1200 预算同量级)


def _clip(s: str, n: int) -> str:
    """超 n 字截断加省略号(防超长 synopsis/beats 撑爆 prompt)。"""
    return s if len(s) <= n else s[:n] + "…"


def _outline_block(st, chapter: int, focalizer: str = "") -> str:
    """B-3 根治:把本章五阶段的「大纲(synopsis)+ 节拍(beats)」注入写作 prompt。
    此前 synopsis/beats 从不注入 → 模型被指令"据大纲/节拍写"却从未收到内容。
    仿 _deduction_block:空(无 synopsis 且无 beats)→ 返回空串(默认行为不变)。
    Task8审查必修2:限知章(focalizer 非空)补一句限知免责——大纲是作者视角,
      帧外私密不得由焦点者知晓或道破(对齐 _deduction_block 的全知/限知分离)。
    方案B任务10:情节点字数预算契约(oh-story artifact-protocols.md 移植)——
      本函数是 chat_write(GET/POST)唯一共用的组装点,前端"大纲/节拍" tab 与
      "草稿" tab 都映射到同一 phase 经此函数注入(节拍无独立生成端点,由
      前端/主编对话驱动),故契约段落点选在此处而非另开端点:
      · 生成/调整节拍时的密度+预算标注规范(始终附带,覆盖节拍生成时刻);
      · 写草稿时"按预算分配笔墨"的执行要求(仅当已有节拍内容时附带)。
      确定性校验见 brief.validate_beat_budgets(后续可接进节拍保存端点)。
    自带前导 \\n\\n(与 _motif_block/_recap_block 同约定,caller 直接 += 即可)。"""
    if chapter is None:
        return ""
    try:
        ch = st.get_chapter(chapter) or {}
    except Exception:
        return ""
    synopsis = (ch.get("synopsis") or "").strip()
    beat_texts = []
    for b in ch.get("beats") or []:
        t = ((b.get("text") if isinstance(b, dict) else str(b)) or "").strip()
        if t:
            beat_texts.append(t)
    if not synopsis and not beat_texts:
        return ""
    parts = ["## 本章大纲/节拍(据此展开正文,勿另起炉灶)"]
    if synopsis:
        parts.append("〔大纲〕" + _clip(synopsis, _OUTLINE_BUDGET))
    if beat_texts:
        parts.append("〔节拍〕" + _clip(" ".join(f"{i}.{t}" for i, t in enumerate(beat_texts, 1)),
                                       _OUTLINE_BUDGET))
        parts.append("写作要求:严格按各情节点字数预算分配笔墨,预算内欠账的密点优先补足,不得均匀注水。")
    if focalizer:
        parts.append("(以上为作者视角大纲,写限知视角时只呈现焦点者可感知的部分;"
                     "帧外私密留作伏笔,不得由焦点者知晓或道破。)")
    parts.append(
        "情节点字数预算契约:生成/调整节拍时,每个情节点须标注「密度:密|疏」与"
        "「字数预算:N字」(密≥250字,慢镜头爽点400-600字,疏≈40字过场);"
        "全部情节点预算求和必须落在[章目标字数, ×1.1]区间;"
        "节拍列表末尾输出一行「预算合计:X字」。"
    )
    # 方案B任务11:章节定位六型 + 卷级张弛基线(oh-story outline-structure-theory.md:282-289 移植)——
    # 大纲/节拍标注补充"这一章在全书张弛节奏里的定位",供 brief.find_tension_monotony 卷级检测消费。
    parts.append(
        "章节定位标注:生成/调整大纲或节拍时,每章须标注「压力级:1-5」与"
        "「chapter_role:高压|推进|修炼|关系回收|低压|信息整理」;"
        "低压/关系回收章允许无显性爽点,但须保留追读拉力(未解悬念或未了结的关系张力仍须推进);"
        "均衡基线非硬配额,严肃志怪基调整体取克制档,但同一 chapter_role 不得连排超过 2-3 章。"
    )
    # 方案B任务13b:反转标注规范(oh-story reversal-toolkit.md 7类反转)——
    # 若本章含反转,节拍须显式标注 reversal_type/setup_clues/reveal_position_pct 三字段,
    # 供 critique.build_reversal_rubric_prompt 机检(铺垫是否≥3处/揭示是否<300字/
    # 有无凭空新信息/揭示位置是否落在50-85%最佳区间)。
    parts.append(
        "反转标注规范:若本章含反转,节拍须标注「reversal_type:七类之一(身份反转/"
        "动机反转/因果反转/立场反转/信息差反转/时间线反转/道德反转)」+「setup_clues」"
        "(≥3 处铺垫,须引用前文对应片段)+「reveal_position_pct」(建议落在 50-85 区间)。"
    )
    return "\n\n" + "\n".join(parts)


def _deduction_block(st, seq: int) -> str:
    """草稿期把本章「场景真相 + 各角色限知投影」注入 instructions。
    空(无真相且无投影)→ 返回空串(默认行为不变)。"""
    ch = st.get_chapter(seq) or {}
    truth = (ch.get("scene_truth") or "").strip()
    deds = ch.get("deductions") or []
    if not truth and not deds:
        return ""
    parts = ["## 本章演绎(据此以作者视角写限知初稿)"]
    if truth:
        parts.append(f"〔场景真相·全知〕{truth}")
    for d in deds:
        nm = d.get("character_name") or d.get("character_id") or "?"
        pr = (d.get("prose") or "").strip()
        if pr:
            parts.append(f"〔{nm}·限知投影〕{pr}")
    parts.append("要求:以场景真相为事实骨架;焦点者投影当 POV、他人投影约束其言行并埋反讽;不写角色不知道的私密。")
    return "\n".join(parts)


def _final_reminder() -> str:
    """末尾强化提醒(recency 效应):把三条非谈判性约束放在 instructions 最后,
    对抗多块拼接后关键规则被稀释的注意力漂移。不含新信息,仅复述最高优先级约束。"""
    return (
        "\n\n（再次强调:① 动稿必须用 ⟦PROPOSAL scope=...⟧ 围栏包正文;"
        "② 文风贴乱世铜炉志怪笔记体——古白话、冷笔、世界密度,忌现代翻译腔与用力比喻;"
        "③ 情感不可直说——禁止用概念词直陈情绪(他感到害怕/她心里很疼/他不是个坏人/这一夜永远熬不到天亮);"
        "只写动作、生理反应、物象细节,让情绪自现(show, don't tell);"
        "④ **焦点者不自悟真相**:限知视角的焦点者绝不可'忽然明白/原来…/如今他懂了'地参透他本不知道的机关/真相,"
        "只能疑惧、误判、半懂、存疑——真相留给读者从现象里自己拼,别借主角之口替读者解题;"
        "⑤ **意象不即时翻译**:写了物象/声音/动作就让它自己说话,绝不紧跟一句解释它'象征/对应/意味着'什么"
        "(写了蛐蛐叫就别补'像在数阳寿');同一意象/动作(如某物自行微动)整章至多出现 2-3 次,每次换细节,杜绝节拍器式复读;"
        "⑥ **禁止诗化分行**:不可把单字/短句独立成行来抒情造气氛(如'等谁。/ 等什么。/ 还剩多少。'),"
        "用连贯的古白话长句白描,文体前后一致；"
        "⑦ **知情焦点者不交底**:若焦点者本就知情,其叙述/内心绝不可把自己的真身、目的、结局或秘局全貌交代给读者"
        "——这些一律留作伏笔,只用动作、欲言又止、缩回的手势暗示;**禁止'焦点者碰巧偷听到反派/知情者把底牌全亮'"
        "的廉价巧合**(偷听至多留半句不祥即被打断/走远,其余靠读者拼)。知情不等于全交底,藏比说更难也更对;"
        "⑧ **单一焦点者视角不漂移**:若本章限定了焦点者(某人的限知视角),则全章严格只写此人视角与内心,"
        "绝不中途切换到他人(包括另一POV主角)的视角/想法/独白(head-hopping);别人只能作为焦点者眼中所见的对象出现,"
        "其内心一概不可直接进入。一章一个脑袋,从头到尾;"
        "⑨ **禁拟声词/单字短句煞尾**:章节结尾绝不可停在孤立的拟声词(如'咔——''笃——')或单字短句上空响,"
        "同一拟声词整章至多 1-2 次、绝不连用三遍;恐怖/悬念的收口要把劲压在**人物的身体反应或一个实物动作**上落地"
        "(如他终于没点着那火折子、手抖得捏湿了纸),用实写比喻砸下,而非靠拟声悬停。"
        "⑩ **时间/称谓连续**:更次(一更→五更)须单调递增不可倒退(开篇四更则后文只能五更/天明,不可又回三更);"
        "引号务必成对开闭,人名/称谓前后一致;"
        "⑪ **知情者之间不互相交底(禁 as-you-know-Bob)**:当两个都知情的角色对话时,绝不可为喂读者而让他们"
        "互相把彼此早已心知的机关/图谋/真相逐条讲全(典型反派交底:'有了X再配上Y他就能Z');他们只说行话、黑话、"
        "半截话、威胁与试探(彼此心知故不必说全),解释性台词一律删去——话越省读者越急,真相留在场外让读者和不知情者一样够不着。"
        "——通篇紧贴《乱世铜炉》志怪笔记体:实得密、诡得克、半懂着往下沉。）"
    )


def _purpose_workflow_block(st, chapter: int, with_tools: bool = False,
                            work: str | None = None) -> str:
    """北极星任务6:目的合同工序提示(底座对表 Q5 裁决:prompt 内嵌是唯一确定性
    生效通道,工序长在对话流程里——skill 自选加载纪律必失守)。已登记合同 → 简报段
    (单源)已带必达清单,只提醒验收;未登记 → 提示聊定目的后列草单走待批。
    with_tools:H-01 work-scoped MCP;启用工具时必须提醒模型所有 s3_ 调用带当前 work。
    空合同照常可写(渐进采纳,不设硬门槛)。fail-soft。"""
    try:
        from scribe3.purpose import parse_deltas
        ds = parse_deltas((st.get_chapter(chapter) or {}).get("deltas"))
    except Exception:
        ds = []
    if ds:
        return ("\n\n【目的合同工序】本章已登记 delta 合同(见简报「必达清单」):写作时逐条兑现;"
                "验收验的是「状态变化发生没发生」,不是好不好。")
    w = _normalize_work(work)
    register_hint = (f"有 s3_register_purpose 工具就调用它走待批登记;调用时必须传 work=\"{w}\"。"
                     if with_tools else "请作者在章面板登记(本对话未挂联查工具)。")
    return ("\n\n【目的合同工序】本章尚未登记目的合同:与作者聊定本章目的后,自动列出 "
            "delta 草单(四类:认知/承诺/事实/关系增量,≤7 条,每条一个可验收的状态变化),"
            + register_hint + "空合同也可正常写作,此工序不阻塞。")


def _material_recall_block(st, chapter: int, phase: str, focalizer: str = "", llm=None) -> str:
    """写作总闸素材注入(全生成相位共用):聚焦 query → material_recall(三通道)→ LLM 重排理由 →
    render 参考段 + 写溯源(反哺强度)。门控:无草料/空库/无命中 → 空串(零开销,不调 LLM)。
    参考语义:素材是借鉴非事实,注入段自带反照搬边界。限知不约束素材(元层面创作参考,非故事内知识)。
    全 try/except fail-soft:素材召回任何异常都不阻断写作主链。"""
    try:
        from scribe3.brief import chapter_draft_text, detect_mentions
        from scribe3.material_recall import (extract_focus_query, gate,
                                             render_material_block, rerank_materials)
        draft = chapter_draft_text(st.get_chapter(chapter) or {})
        if not (draft or "").strip():
            return ""
        entities = [{"id": e.id, "name": e.name,
                     "aliases": (getattr(e, "traits", None) or {}).get("aliases") or []}
                    for e in st.all_entities()]
        mentioned = detect_mentions(draft, entities)
        query = extract_focus_query({"beats": [draft[:200]], "mentioned": list(mentioned)})
        if not query:
            return ""
        cands = gate(st.material_recall(query, chapter, k=5, mentioned_entities=mentioned))
        if not cands:
            return ""   # 门控:空库/无命中 → 不调 LLM 重排
        if llm is None:
            from scribe3.llm import hermes_complete
            def llm(p):
                return hermes_complete(p, max_tokens=500)
        ranked = rerank_materials(cands, query, llm, k=3)
        block = render_material_block(ranked)
        if block:
            for c in ranked:   # 溯源反哺(recall_count++/last_recalled_at)
                try:
                    st.add_material_reference(
                        c["material_id"], chapter,
                        dimension=(c.get("ref_tags") or [None])[0],
                        reason=c.get("reason"), via=f"phase:{phase}")
                except Exception:
                    pass
        return "\n\n" + block if block else ""
    except Exception:
        logging.getLogger("scribe3").debug("素材召回块失败(不阻断写作)", exc_info=True)
        return ""


# M1:v1 组装失败回退旧链的累计次数(金丝雀读它判断真机是否真走了 v1,防静默降级)。
_context_assembler_fallbacks = 0


def _context_assembler_enabled() -> bool:
    """Task 7:SCRIBE3_CONTEXT_ASSEMBLER_V1 是否开启(每次调用读,默认关)。
    关 → _assemble_write_instructions 走旧散点组装链,行为一字不变(1270+ 后端测试
      与真机写作路径零影响,控制器裁决)。开 → 走 ContextAssembler 组装的 envelope。
    Task 17 的"写作质量金丝雀门"真机验证通过后才允许默认开启。
    统一走 _flag_enabled(设置中心 DB 覆盖→env→默认,热生效),与 /capabilities
    上报同一判定路径,消除双路径分裂。"""
    return _flag_enabled("SCRIBE3_CONTEXT_ASSEMBLER_V1")


# ContextSnapshot.phase 的合法枚举(context_models.PhaseName);写作端点的 phase
# 串("plan"/"draft"/"final"/...)不在此集合的一律降 None,防合成快照校验失败。
_ASSEMBLER_PHASES = {"outline", "beats", "deduce", "draft", "final"}


def _write_snapshot(st, *, chapter, focalizer, phase, work):
    """为写作组装合成一份最小 ContextSnapshot(v1 路径喂给 ContextAssembler)。
    写作端点不像导航那样带完整快照,这里用确定性占位补齐 session/thread/nav——
    它只作 assembler 的取数坐标(work/chapter/focalizer/phase),不入 CAS 存储。"""
    from datetime import datetime, timezone
    from scribe3.context_models import ContextFocus, ContextSnapshot
    w = _normalize_work(work)
    ph = (phase or "").strip().lower()
    ph = ph if ph in _ASSEMBLER_PHASES else None
    has_ch = chapter is not None
    snap = ContextSnapshot(
        session_id="write", work=w, revision=0, thread_id=f"write:{w}",
        entry="chapter", directory_path=(),
        focus=ContextFocus(type="chapter" if has_ch else "view",
                           id=str(chapter) if has_ch else w,
                           label=focalizer or ""),
        detail_route=f"chapter:{chapter}" if has_ch else "view:book",
        chapter=chapter, phase=ph, focalizer=focalizer or None,
        previous_revision=None, navigation_id=f"write:{w}:{chapter}",
        captured_at=datetime.now(timezone.utc), context_hash="")
    return snap.with_hash()


def _get_write_retriever(st):
    """Task 8 MemoryRetriever 注入点(对称门控,Task 16-C)。

    SCRIBE3_MEMORY_FABRIC_V1【关】(默认)→ None:assembler 走 store 直查降级(canonical
      仍有真数据),与 16-C 前【字节等价】——写作 prompt 不读经验记忆、零检索成本。
    【开】→ MemoryRetriever(st):四通道检索 / RRF / 限知门 / 正典压制接进写作 envelope
      (剧透门 known_from、秘密屏蔽 C1、work 隔离全在检索/组装链内生效)。
    注:检索真进 prompt 还需 SCRIBE3_CONTEXT_ASSEMBLER_V1 同开(v1 组装路径消费本 retriever);
    任一关 = 当前生产行为。捕获侧 _capture_turn_memory 由同一 flag 对称门控(同开同关)。
    M4 记账:门控不完全对称——读路径需 MEMORY_FABRIC + ASSEMBLER_V1【同开】(assembler 是 envelope
      注入点),写(捕获)只需 MEMORY_FABRIC。Task 17 金丝雀门须【同开两旗】才真验读路径。"""
    if not _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1"):
        return None
    from scribe3.memory_retrieval import MemoryRetriever
    return MemoryRetriever(st)


def _build_write_retrieval_query(st, *, chapter, seed_words) -> str:
    """I1(Task 16-C):为写作检索拼一个有意义的 query,靶向本章相关经验记忆。

    源优先级(选 seed_words 为主的理由:它是作者给本章的种子词/意象,签名已带、最贴"此刻在写什么",
    是最自然的检索靶向;章纲作退路补全):
      ① seed_words —— 本章种子词(_soak_block 同源),空白项剔除后拼接;
      ② 无种子词 → 章纲 synopsis(get_chapter)截断 200 字,给一个"本章要写什么"的兜底靶向。
    作者 msg 未透传到本组装函数(_assemble_write_instructions 链只带 seed_words),不为它改签名/注入点
    (文档1 教训:每新开一个注入点泄露过一次限知);seed_words+章纲已足够靶向,故不硬塞 msg。
    仅在检索器接上(MEMORY_FABRIC 开)时被调用;返回空串则退化为"只出 canonical"的保守行为(不崩)。"""
    parts = [w.strip() for w in (seed_words or []) if isinstance(w, str) and w.strip()]
    if parts:
        return " ".join(parts)[:200]
    try:
        ch = st.get_chapter(chapter) or {}
        syn = (ch.get("synopsis") or "").strip()
        if syn:
            return syn[:200]
    except Exception:
        pass
    return ""


def _write_context_binding(req, headers=None) -> dict:
    """从 chat/write 请求解析【前端真实上下文会话绑定】(供落 memory_trace 给 ContextInspector)。

    三件套 + thread 优先取 body 字段,缺失回退等价请求头 X-Scribe-Context-*(与
    ContextService.enforce 同源同形,I-1 双通道)。返回 dict(值可为 None);
    调用侧只在检索发生【且 session_id/revision 齐备】时消费——即前端确实带了会话绑定
    (WriteChat.runContextBind 发 context_session_id + context_revision)。不带绑定的
    调用方(loop / 存量)→ session_id 缺 → 不落 trace(Inspector 诚实 404)。"""
    from scribe3.context_service import HEADER_HASH, HEADER_REVISION, HEADER_SESSION
    headers = headers if headers is not None else {}
    session_id = getattr(req, "context_session_id", None) or headers.get(HEADER_SESSION)
    context_hash = getattr(req, "context_hash", None) or headers.get(HEADER_HASH)
    revision = getattr(req, "context_revision", None)
    if revision is None:
        raw = headers.get(HEADER_REVISION)
        try:
            revision = int(raw) if raw not in (None, "") else None
        except (TypeError, ValueError):
            revision = None
    return {
        "context_session_id": session_id,
        "context_revision": revision,
        "context_hash": context_hash,
        "thread_id": getattr(req, "thread_id", None),
    }


def _save_write_memory_trace(st, *, snap, envelope, result, query, work, ctx) -> str:
    """Task 16 最后一厘米:一次写作检索的 RetrievalResult → memory_trace(ContextInspector 数据源)。

    键对齐(命门):context_session_id/snapshot_revision 取【前端真实会话绑定】(ctx,来自
    chat/write 的 req/请求头)——前端 ContextInspector 正是用同一 snapshot.session_id/revision
    查 GET /context/sessions/{id}/trace/{rev},键天然对齐,检索发生即显真数据。snapshot_hash/
    thread_id 前端未必带(WriteChat 只发 session_id+revision)→ 回退写作合成快照 snap。

    幂等:trace_id 用 (work,session,thread,revision) 确定性 hash;同一快照版本反复写只留最新
    一条(save_memory_trace 先删后建)。

    秘密屏蔽(限知红线):build_memory_trace(store=st) 叠加 _secret_fact_ids 权威判定,
    save_memory_trace 落库前再 mask_memory_trace 兜底 → DB at-rest 绝无秘密 value。

    调用方 best-effort try/except 兜底:本函数任何异常都不得阻断写作主链路。"""
    import hashlib

    from scribe3.store import build_memory_trace
    session_id = str(ctx.get("context_session_id"))
    revision = int(ctx.get("context_revision"))
    snap_hash = str(ctx.get("context_hash") or getattr(snap, "context_hash", "") or "")
    thread_id = str(ctx.get("thread_id") or getattr(snap, "thread_id", "") or "")
    env_hash = str(getattr(envelope, "envelope_hash", "") or "")
    block_tokens = {b.name: b.token_estimate
                    for b in (getattr(envelope, "blocks", None) or [])}
    # channels:每条选入候选实际命中的通道计数(审计观测;Inspector 主看 block_tokens/证据)。
    channels: dict = {}
    for c in (getattr(result, "selected", None) or []):
        for ch in (getattr(c, "channels", None) or ()):
            channels[str(ch)] = channels.get(str(ch), 0) + 1
    key = f"{work or ''}|{session_id}|{thread_id}|{revision}"
    trace_id = "mt:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    trace = build_memory_trace(
        trace_id=trace_id, work=str(work or ""), thread_id=thread_id,
        context_session_id=session_id, snapshot_revision=revision,
        result=result, query=query or "", snapshot_hash=snap_hash,
        envelope_hash=env_hash, channels=channels, block_tokens=block_tokens,
        store=st)
    st.save_memory_trace(trace)
    return trace_id


def _assemble_write_instructions_v1(st, *, chapter, focalizer, phase, seed_words,
                                    short_mode, with_tools=False, work=None,
                                    envelope_trace=None, memory_trace_ctx=None):
    """SCRIBE3_CONTEXT_ASSEMBLER_V1【开】路径:身份/硬协议保持内嵌,上下文段由
    ContextAssembler 统一组装(可预算/可溯源/正典优先/限知屏蔽);强制纪律仍逐条内嵌
    (_final_reminder/_revelation_discipline_block/_focalizer_sincerity_block 等是
    "每请求硬协议",不进 envelope——计划全局约束的稳定层分工)。旧块函数
    (_frame_block/_recap_block/_material_recall_block)不删不改,其取数语义由 assembler
    的 store 降级路径承接(source adapter)。⚠ Task 17 金丝雀门真机验证前默认不启用。"""
    from scribe3.context_assembler import (
        ContextAssembler, envelope_trace_manifest, render_envelope_text)
    from scribe3.craft import build_craft_block
    # I1:身份用【纯身份块】而非 _editor_write_system——后者经 _editor_system 注入设定/角色/
    # 伏笔 + 章前简报,会与下方 envelope 的 canonical/global 重复(facts 2×/promises 3×)。
    # v1 让 envelope 独占 facts/promises/角色/北极星的数据注入,身份层只留身份+硬协议+文风。
    instructions = (_editor_identity_block() + _write_protocol_block()
                    + _write_revision_block() + _secret_guard_block(st, chapter))
    instructions += f"\n当前第 {chapter} 章。"
    if with_tools:
        instructions += _s3_work_scope_block(work)
    if focalizer:
        instructions += (f"作者指定本章跟随焦点者 {focalizer} 的限知视角:"
                         "贴该角色所知所感写,别写他不知道的私密。")
    else:
        instructions += "本章未指定限知焦点者 → 作者视角(可全知)。"
    # 统一上下文段(替代旧 avoid/voice/arc/motif/frame/recap/tail/outline/material 散点拼装)
    snap = _write_snapshot(st, chapter=chapter, focalizer=focalizer,
                           phase=phase, work=work)
    mode = "write" if (phase or "").strip().lower() in ("draft", "final") else "plan"
    # I1(Task 16-C 核心修复):写作路径必须给 assemble 一个【有意义 query】,否则
    #   store.memory_bm25/vector 对空串硬返 [](graph 种子亦空)→ episodic/working 三条经验
    #   通道全归零,只剩 structured/canonical(与 query 无关,retriever=None 降级即可得),
    #   捕获→memory_item→检索的经验回路在生产仍是"只写不读"。故 fabric 开(retriever 非 None)时
    #   用本章种子词/章纲作 query 靶向经验记忆;fabric 关(retriever=None)时 query 仍空——
    #   envelope 与接线前逐字不变(默认关字节等价,连 focus 块"作者此刻问"都不出现)。
    #   剧透门不受影响:known_from 门在 store SQL/Python 侧恒生效,有意义 query 也挡不掉未来揭示。
    retriever = _get_write_retriever(st)
    retrieval_query = (_build_write_retrieval_query(st, chapter=chapter, seed_words=seed_words)
                       if retriever is not None else "")
    # Task 16 最后一厘米:检索发生(retriever 非 None = MEMORY_FABRIC 开)时收集本次完整
    # RetrievalResult,组装后落 memory_trace 给 ContextInspector 真数据。retriever=None
    # (MEMORY_FABRIC 关)→ 收集器 None → assemble 走协议 retrieve() → 与接线前【字节等价】。
    _retrieval_out = {} if retriever is not None else None
    envelope = ContextAssembler(st, retriever).assemble(
        snap, retrieval_query, mode, retrieval_out=_retrieval_out)
    # M3 记账 + 指标接入:采样本次组装 envelope 的 token 估算(context_tokens_p95 由 0 变真实)。
    # 纯观测副作用,不改 instructions 字节;仅 v1 路径(ASSEMBLER_V1 开)才走到这里——即 MEMORY_FABRIC
    # 关而 ASSEMBLER_V1 开时仍会采样(内存 deque,无秘密、字节无害),这是刻意的观测下限,非泄露。
    try:
        from scribe3 import context_cache as _cc
        _cc.record_context_tokens(envelope.total_token_estimate)
    except Exception:
        pass
    # Caveat 1(Task 17 Step 5b):把 envelope 的【安全块清单】回填 envelope_trace,供
    # chat/write 落 chat_message.trace.context 审计"主编这轮看到了哪些上下文块"(Task 14
    # ContextInspector 数据源)。复用 envelope_trace_manifest —— 它本就"给 trace.context 用"
    # (计划 Step 5):每块只记 name/token/source id/被屏蔽 source id + omitted 原因,
    # 【绝不含】块正文与秘密 value(限知红线,test_trace_manifest_excludes_secret_values 锁死)。
    # 纯观测副作用:envelope_trace 缺省 None(仅 chat_write_post 传入)→ 其余调用方字节等价;
    # 摘要计算异常绝不影响写作主链路。
    if envelope_trace is not None:
        try:
            envelope_trace["context"] = envelope_trace_manifest(envelope)
        except Exception:
            pass
    # Task 16 最后一厘米:检索真发生(retriever 非 None)且前端带了会话绑定
    # (memory_trace_ctx 有 session_id + revision)时,落 memory_trace 给 ContextInspector。
    # 键用前端真实会话(前端 Inspector 查同一 session/revision,天然对齐);无绑定的调用方
    # (loop / 存量)→ 不落(诚实 404)。best-effort:落库失败只告警,绝不阻断写作主链路
    # (与 chat_message 同纪律);秘密屏蔽复用 _save_write_memory_trace 内 build/save 双重 mask。
    _mtc = memory_trace_ctx or {}
    if (_retrieval_out is not None and _mtc.get("context_session_id")
            and _mtc.get("context_revision") is not None):
        _result = _retrieval_out.get("result")
        if _result is not None:
            try:
                _save_write_memory_trace(
                    st, snap=snap, envelope=envelope, result=_result,
                    query=retrieval_query, work=work, ctx=_mtc)
            except Exception:
                logging.getLogger("scribe3").warning(
                    "memory_trace 落库失败(忽略,不阻断写作)", exc_info=True)
    env_text = render_envelope_text(envelope)
    if env_text:
        instructions += "\n\n" + env_text
    # 生成模式/情绪种子/工艺块(叠加,非上下文事实)
    instructions += _soak_block(seed_words)
    craft = build_craft_block(st.list_craft_rules() or None, short_mode=short_mode)
    if craft:
        instructions += "\n\n" + craft
    instructions += _phase_role_block(phase)
    # 每请求硬协议(强制纪律,恒内嵌 prompt,不进 envelope)
    # S-007:跨章避免复用是【确定性禁令】(distinctive_phrases→"别逐字复用前文这些措辞"),
    #   不是上下文信息——envelope 只聚合"前文写了什么",给不出"禁止复用"的禁令。按本函数
    #   自己的分工原则(强制纪律逐条内嵌、不进 envelope),它本就该内嵌,此前随"替代旧散点"
    #   一起漏掉,导致 assembler_v1 放量后跨章复读防线失效(实证:某章 cross_repetition=25)。
    instructions += _avoid_directive(st, chapter)
    instructions += _revelation_discipline_block(focalizer)
    instructions += _focalizer_sincerity_block()
    instructions += _purpose_workflow_block(st, chapter, with_tools, work)
    instructions += _final_reminder()
    return instructions


def _assemble_write_instructions(st, *, chapter: int, focalizer: str, phase: str,
                                 seed_words: list, short_mode: bool,
                                 with_tools: bool = False,
                                 work: str | None = None,
                                 envelope_trace: dict | None = None,
                                 memory_trace_ctx: dict | None = None) -> str:
    """chat_write 完整组装链单源(北极星任务4 提炼,原 chat_write_post 内联段)。
    POST /chat/write 与 POST /loop/chapter 共用**同一个函数**——宪法条款
    "regenerate 复用完整组装链"的物理保证:loop 回炉不存在第二套注入点
    (文档1 发现3 教训:历史上每新开一个注入点都泄露过一次)。
    with_tools:透传给工序提示段;启用时所有 s3_ 调用必须带 work。
    envelope_trace(Caveat 1):可选可变收集器;仅 v1 路径成功组装时被回填
      {"context": <安全块清单>}(仅 chat_write_post 传入,供落 chat_message.trace.context)。
      缺省 None → 全部其余调用方与旧路径字节等价。
    memory_trace_ctx(Task 16 最后一厘米):可选前端会话绑定
      {context_session_id/context_revision/context_hash/thread_id};仅 v1 路径且检索发生
      (MEMORY_FABRIC 开)+ 绑定齐备时,把 RetrievalResult 落 memory_trace 给 ContextInspector。
      缺省 None → 不落 trace,其余调用方(loop/存量)行为不变。

    Task 7:SCRIBE3_CONTEXT_ASSEMBLER_V1【开】→ 委托 _assemble_write_instructions_v1
      (ContextAssembler 统一组装);组装异常 → 回退下方旧链(fail-safe)。
      【关】(默认)→ 直接执行下方旧链,行为一字不变(控制器裁决的硬性验收条件)。"""
    if _context_assembler_enabled():
        try:
            return _assemble_write_instructions_v1(
                st, chapter=chapter, focalizer=focalizer, phase=phase,
                seed_words=seed_words, short_mode=short_mode,
                with_tools=with_tools, work=work, envelope_trace=envelope_trace,
                memory_trace_ctx=memory_trace_ctx)
        except Exception:
            # M1:回退是【结构化信号】,不能静默——否则 Task 17 金丝雀门会被蒙蔽(v1
            # 其实全程降级到旧链却以为在测 v1)。累计计数器 + 带阶段/章/书的 warning,
            # 供金丝雀读 app._context_assembler_fallbacks 判断"这次真机是否真走了 v1"。
            global _context_assembler_fallbacks
            _context_assembler_fallbacks += 1
            logging.getLogger("scribe3").warning(
                "ContextAssembler v1 组装失败,回退旧组装链(fail-safe) "
                "stage=assemble_write_instructions chapter=%s focalizer=%s work=%s "
                "fallbacks=%d",
                chapter, focalizer, work, _context_assembler_fallbacks, exc_info=True)
    from scribe3.craft import build_craft_block
    instructions = _editor_write_system(st, focalizer=focalizer, chapter=chapter)
    instructions += f"\n当前第 {chapter} 章。"
    if with_tools:
        instructions += _s3_work_scope_block(work)
    if focalizer:
        instructions += f"作者指定本章跟随焦点者 {focalizer} 的限知视角:贴该角色所知所感写,别写他不知道的私密。"
    else:
        instructions += "本章未指定限知焦点者 → 作者视角(可全知)。"
    instructions += _avoid_directive(st, chapter)
    instructions += _voice_anchor_block(st, focalizer)
    instructions += _arc_state_block(st, focalizer, chapter)
    instructions += _motif_block(st)
    instructions += _frame_block(st, focalizer, chapter)
    instructions += _revelation_discipline_block(focalizer)
    instructions += _recap_block(st, chapter)
    instructions += _current_tail_block(st, chapter)
    instructions += _soak_block(seed_words)
    craft = build_craft_block(st.list_craft_rules() or None, short_mode=short_mode)
    if craft:
        instructions += "\n\n" + craft
    instructions += _phase_role_block(phase)
    instructions += _outline_block(st, chapter, focalizer)   # B-3:五阶段 synopsis/beats 注入(限知护栏随 focalizer)
    instructions += _material_recall_block(st, chapter, phase, focalizer)  # 素材联想记忆(借鉴参考,覆盖全生成相位)
    instructions += _focalizer_sincerity_block()   # 方案B任务13b:叙述者真诚视角硬约束
    _ph_lower = (phase or "").strip().lower()
    if _ph_lower in ("draft", "final"):
        # F-1 修复(B-3 同型第四次):正文相位——draft(四阶段草稿)与 final(loop/pilot/
        # 选择环一步到正文的默认相位)——都必须注入演绎块。此前只 draft 注入,而 loop/pilot/
        # 选择环全走 final → deduce 步烧的 1+N 发 LLM 产物(场景真相+限知投影)物理漏在
        # prompt 外,驱动语"按简报与演绎写"沦为空指令。演绎字段空→_deduction_block 返空串→
        # 不注入(默认行为不变)。回归钉:test_gapfix.test_deduce_phase_injects_scene_truth。
        ded = _deduction_block(st, chapter)
        if ded:
            instructions += "\n\n" + ded
            logging.getLogger("scribe3").debug(
                "chat/write 组装 phase=%s chapter=%s → 注入演绎块 %s 字(命中 _deduction_block)",
                _ph_lower, chapter, len(ded))
    elif _ph_lower == "deduce":
        # 断头修复(演绎多棱镜 #5):投影必须从同一场景真相物理派生——此前指令说
        # "据场景真相"但真相从不进 prompt(B-3 同型坑:被指令据 X 却没收到 X),
        # "多投影天然一致"沦为对模型的口头要求。真相非空即注入;生成真相本身时
        # 它可作重写参照,无害。
        try:
            _truth = ((st.get_chapter(chapter) or {}).get("scene_truth") or "").strip()
        except Exception:
            _truth = ""
        if _truth:
            instructions += ("\n\n## 本场「场景真相」(全知,各角色投影派生的唯一事实源)\n"
                             + _truth
                             + "\n\n生成角色限知投影时:只从上述真相中该角色能感知/推知的"
                               "部分派生;真相里没有的事不得出现在任何投影里。")
    instructions += _purpose_workflow_block(st, chapter, with_tools, work)   # 北极星任务6:目的合同工序
    instructions += _final_reminder()
    return instructions


@app.post("/chat/write")
def chat_write_post(req: ChatWriteReq, request: Request, work: str = "main"):
    """POST 版写作对话(支持图片附件):前端用 fetch 流式读取。"""
    st = _store_for(work)
    # Task 4:context 绑定强校验(SCRIBE3_CONTEXT_SNAPSHOT_V1 门控,默认关=零变化)。
    # 必须在 user 落库与 StreamingResponse 之前完成——流一旦开始,4xx 会退化成流中错误。
    # 双通道(I-1):body 三件套缺失时逐字段回退请求头 X-Scribe-Context-*
    # (api.js contextHeaders 产出),两通道都缺才 400。
    try:
        ContextService(st).enforce(req, work, headers=request.headers)
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e
    _wt = _work_has_tools(work)   # H-01:工具已 work-scoped,组装链提示必须同频钉 work
    # Caveat 1:v1 组装路径把 envelope 安全块清单回填这里,随 assistant 落 trace.context;
    # flag 关/回退旧链时保持空 → trace 不含 context 键(字节等价,零回归)。
    _envelope_trace: dict = {}
    # Task 16 最后一厘米:前端真实会话绑定(供 v1 检索路径落 memory_trace 给 ContextInspector);
    # 三件套优先 body,缺失回退请求头 X-Scribe-Context-*。仅 v1 + MEMORY_FABRIC 开 + 绑定齐备时
    # 被消费落 trace——flag 关/无绑定时不影响写作字节(纯落库副作用,与 chat_message 同 best-effort)。
    _memory_trace_ctx = _write_context_binding(req, request.headers)
    instructions = _assemble_write_instructions(
        st, chapter=req.chapter, focalizer=req.focalizer, phase=req.phase,
        seed_words=req.seed_words, short_mode=req.short_mode, with_tools=_wt, work=work,
        envelope_trace=_envelope_trace, memory_trace_ctx=_memory_trace_ctx)

    if req.images:
        content = [{"type": "input_text", "text": req.msg}]
        for img in req.images:
            content.append({"type": "input_image", "image_url": f"data:{img.type};base64,{img.data}"})
        message = [{"role": "user", "content": content}]
    else:
        message = req.msg

    # 北极星任务1:会话落库(蓝图 §4-② 第1级)——user 受理即写,assistant 流尽回调写;
    # 均 best-effort(D-004),落库失败只告警,绝不影响写作主链路。
    # turn id(P2-6):串起本轮 user/assistant,防并发会话交错污染蒸馏配对。
    import uuid
    turn_id = uuid.uuid4().hex[:12]
    user_text = req.msg + (f"\n[附图{len(req.images)}张]" if req.images else "")
    # Task 6:线程归属 + 本轮 context 绑定/焦点标签随消息落库(切焦点不切线程);
    # 全 optional,存量调用方(不传 thread_id)仍走 backfill 的默认线程回看。
    _bind = dict(thread_id=req.thread_id, context_session_id=req.context_session_id,
                 context_revision=req.context_revision, context_hash=req.context_hash,
                 focus=req.focus)
    try:
        st.add_chat_message(chapter=req.chapter, stage=req.phase, role="user",
                            text=user_text, turn=turn_id, **_bind)
    except Exception:
        logging.getLogger("scribe3").warning("chat_message user 落库失败(忽略)", exc_info=True)

    def _persist_assistant(text: str, trace: dict | None = None) -> None:
        # assistant 侧 response_id 取自 Hermes trace(便于按响应回溯本轮)。
        trace = dict(trace or {})
        # Caveat 1:v1 组装路径(ASSEMBLER_V1 开且成功)才有 envelope 块清单 →
        # 并入 trace.context 供审计"主编这轮看到了哪些上下文块"。manifest 每块仅记
        # name/token/source id/被屏蔽 source id,绝无块正文与秘密 value(限知红线)。
        # flag 关或回退旧链时 _envelope_trace 为空 → 不加 context 键(字节等价)。
        _ctx = _envelope_trace.get("context")
        if _ctx:
            trace["context"] = _ctx
        resp_id = trace.get("response_id")
        st.add_chat_message(chapter=req.chapter, stage=req.phase, role="assistant",
                            text=text, turn=turn_id, trace=trace,
                            response_id=resp_id, **_bind)
        # Task 9:本轮作者意图捕获成经验记忆(幂等 + 同步 drain;每 8 轮/会话末 consolidate)。
        # 捕获作者原话(决策/偏好/不确定的真源),不碰正文生成与 prompt 组装(写作路径零改动)。
        _capture_turn_memory(st, work=work, thread_id=(req.thread_id or f"write:{work}"),
                             turn_id=turn_id, text=user_text, chapter=req.chapter)

    return StreamingResponse(
        _stream_write(message, instructions, expect_proposal=_is_write_intent(req.msg),
                      with_tools=_wt,
                      on_complete=_persist_assistant),
        media_type="text/event-stream",
    )


@app.get("/chat/messages")
def chat_messages(chapter: int | None = None, limit: int = 500, work: str = "main"):
    """会话留痕回看(北极星任务1):按章拉 chat_message,ts 升序。
    复盘蒸馏(任务8)与「当初为什么这么定」的翻账都从这里读。
    GET /chat/write(兼容端点,无生产调用方)不落库——台账 D-005。"""
    return _store_for(work).list_chat_messages(chapter=chapter, limit=limit)


def _collect_write(message, instructions: str, with_tools: bool = True):
    """同步(非 SSE)写作收集器,loop 编排(北极星任务4)用。与 _stream_write 同一事件源
    (_responses_events 可 monkeypatch)与同一 ProposalParser 语义,只是不产 SSE 帧。
    返回 (围栏外散文, proposals=[{scope, prose}, ...]);LLM 异常向上抛(journal 的
    in_progress 会停在 generate stage,resume/审计可见,不吞错)。"""
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.llm import hermes_responses_events
    from scribe3.proposal import ProposalParser
    fn = _responses_events or hermes_responses_events
    adapter = HermesEventAdapter()
    parser = ProposalParser()
    outside: list[str] = []
    proposals: list[dict] = []
    cur = {"scope": None, "prose": []}

    def drain(events):
        for kind, val in events:
            if kind == "delta":
                outside.append(val)
            elif kind == "proposal_open":
                cur["scope"] = val
                cur["prose"] = []
            elif kind == "proposal_delta":
                cur["prose"].append(val)
            elif kind == "proposal_close":
                proposals.append({"scope": cur["scope"], "prose": "".join(cur["prose"])})
                cur["scope"] = None
                cur["prose"] = []

    for ev in _response_events_iter(fn, message, instructions, with_tools=with_tools, store=True,
                                    server_label=SCRIBE3_READ_MCP_LABEL):
        app_ev = adapter.adapt(ev)
        if app_ev["kind"] == "text.delta":
            drain(parser.feed(app_ev.get("delta", "")))
    drain(parser.flush())
    return "".join(outside), proposals


def _loop_journal_path(work: str, chapter: int):
    """loop 编排 journal 路径(北极星任务4,台账 D-012)。与 _import_journal_path 的
    临时目录语义**刻意不同**:loop journal 兼任秘密审计(任务13)的抽查数据源
    ("哪章被自动回炉了几轮、为什么"),须持久——默认 ~/.scribe3-loop-journals/{work}/,
    SCRIBE3_LOOP_JOURNAL_DIR 可覆盖(测试指 tmp_path)。每次调用新开带纳秒时间戳的
    文件:重复 loop 同章不串账(journal 的 should_skip 语义只在单次运行内成立)。"""
    import time
    from pathlib import Path
    base = os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR") or os.path.expanduser("~/.scribe3-loop-journals")
    d = Path(base) / work
    d.mkdir(parents=True, exist_ok=True)
    return d / f"loop_ch{chapter}_{time.time_ns()}.json"


class LoopChapterReq(BaseModel):
    chapter: int
    focalizer: str = ""
    msg: str = ""            # 可选驱动语;默认"按简报写第N章正文"
    phase: str = "final"
    short_mode: bool = False


@app.post("/loop/chapter")
def loop_chapter(req: LoopChapterReq, work: str = "main"):
    """北极星任务4:修复环编排端点(蓝图 §3-①)。同步长请求(D-009:单用户本地工具
    形态;响应带 journal_path 留 202 演进位)。编排纯逻辑在 scribe3/loop.py(依赖注入),
    本端点只绑真实现:
    - generate 复用 chat_write 完整组装链(_assemble_write_instructions 同一函数,
      宪法:regenerate 绝不另起简化 prompt);负面约束段追加在 instructions 尾部;
    - post_check 直接调用 /post-check 端点函数(判据零漂移);
    - blocking→自动回炉≤2轮 / advisory→清单待批不重写 / pass→落库+final版+同步 ingest;
    - loop 自动轮不写 chat_message(D-010,journal 已留痕)。"""
    from scribe3.ingest import ingest_chapter
    from scribe3.loop import run_chapter_loop
    from scribe3.pipeline_journal import PipelineJournal
    st = _store_for(work)
    # P0门审查 P1-3:同章 loop 互斥——在途拒 409,防双生成/双落库/双 ingest。
    _lkey = (work, req.chapter)
    with _loop_inflight_lock:
        if _lkey in _loop_inflight:
            raise HTTPException(status_code=409,
                                detail=f"chapter {req.chapter} 已有 loop 在途(同章互斥)")
        _loop_inflight.add(_lkey)
    # P2门审查 P2-1(loop 侧同修):journal 构造若抛异常须释放互斥,否则该章永久 409。
    try:
        jp = _loop_journal_path(work, req.chapter)
        journal = PipelineJournal(jp)
    except Exception:
        with _loop_inflight_lock:
            _loop_inflight.discard(_lkey)
        raise

    def _generate(attempt: int, constraints: str) -> str:
        instructions = _assemble_write_instructions(
            st, chapter=req.chapter, focalizer=req.focalizer, phase=req.phase,
            seed_words=[], short_mode=req.short_mode,
            with_tools=_work_has_tools(work), work=work)
        if constraints:
            instructions += "\n\n" + constraints
        msg = req.msg or (f"按本章简报、大纲与全部纪律写第 {req.chapter} 章完整正文,"
                          f"用 ⟦PROPOSAL scope=chapter⟧ 围栏交稿。")
        text, proposals = _collect_write(msg, instructions, with_tools=_work_has_tools(work))
        # P0门审查 P1-7:只认 scope=chapter 围栏(scene/selection 片段不能当整章);
        # 无合格围栏时兜底散文必须过长度门——否则一段短聊天语可能四判据全绿直通
        # pass,把既有整章正文静默覆盖掉。
        chapter_props = [p for p in proposals if p.get("scope") == "chapter"]
        if chapter_props:
            return chapter_props[-1]["prose"]
        body = _strip_preamble(text)
        if len(body.strip()) >= _FALLBACK_MIN_CHARS:
            return body
        raise HTTPException(status_code=422, detail=(
            f"第 {attempt} 轮未产出合格章稿(无 scope=chapter 围栏且散文不足 "
            f"{_FALLBACK_MIN_CHARS} 字)——请检查驱动语是否要求用围栏交稿"))

    _last_post: dict = {}   # 北极星任务6:finalize 结算要用最后一轮 fulfillment 结果

    def _post_check(prose: str) -> dict:
        resp = post_check(PostCheckReq(prose=prose, focalizer=req.focalizer,
                                       short_mode=req.short_mode),
                          seq=req.chapter, work=work)
        _last_post.clear()
        _last_post.update(resp)
        return resp

    def _persist_version(prose: str, attempt: int, verdict: str) -> str:
        return st.add_chapter_version(
            req.chapter, prose, label=f"loop第{attempt}稿·{verdict}",
            kind="checkpoint", stage="draft", stats=_prose_stats(prose))

    def _finalize(prose: str) -> dict:
        title = (st.get_chapter(req.chapter) or {}).get("title") or ""
        st.save_chapter(req.chapter, prose, title=title, focalizer=req.focalizer or None)
        try:
            st.add_chapter_version(req.chapter, prose, label="loop过审", kind="final",
                                   stage="final", stats=_prose_stats(prose))
        except Exception as e:
            logging.getLogger("scribe3").warning("loop final 留版失败(不阻断): %s", e)
        # P0门审查 P1-3:loop 的同步 ingest 也走 _pending_ingest 在途护栏——与 /ingest、
        # _bg_ingest 共用同一 (work,seq) 集合,防 loop 长请求期间用户手点反哺/存稿触发的
        # ingest 与本次交错(knows/char_state/motif_instance 双份或互删)。
        ikey = (work, req.chapter)
        with _pending_ingest_lock:
            if ikey in _pending_ingest:
                return {"ok": False,
                        "error": "同章 ingest 在途(_pending_ingest 护栏),本次跳过;正文已落库,稍后可手动 /ingest"}
            _pending_ingest.add(ikey)
        try:
            from scribe3.llm import hermes_complete
            r = ingest_chapter(st, req.chapter, hermes_complete)
            # 北极星任务6 + P1门审查 P0-1:结算必须在 ingest **之后**——promise_touch/
            # relation_touch/获知 fact 正是 ingest 抽取落库的,先结算必然把已兑现的
            # delta 误判 not_achieved 错误滚入下章(错账向后污染,brief 会催 LLM 重做
            # 已做过的回收)。结构类此刻现场重算;认知类沿用最后一轮 post-check 的
            # LLM verdicts 合并(此前的时序错误正是把真机 ch7 的 promise 误记 carried)。
            try:
                from scribe3.purpose import (check_fulfillment_structural,
                                             parse_deltas, settle_purpose)
                _ds = parse_deltas((st.get_chapter(req.chapter) or {}).get("deltas"))
                if _ds:
                    _struct = check_fulfillment_structural(st, req.chapter, _ds)
                    _kn = {(i.get("kind"), i.get("predicate")): i
                           for i in ((_last_post.get("fulfillment") or {}).get("items") or [])
                           if i.get("kind") == "knowledge"}
                    _merged = []
                    for _it in _struct:
                        if _it["kind"] == "knowledge" and _it["verdict"] == "not_checkable":
                            _j = _kn.get((_it["kind"], _it["predicate"]))
                            if _j and _j.get("verdict"):
                                _it = {**_it, "verdict": _j["verdict"]}
                        _merged.append(_it)
                    settle_purpose(st, req.chapter, _merged)
            except Exception as se:
                logging.getLogger("scribe3").warning("loop 目的合同结算失败(忽略): %s", se)
            # 北极星任务8:loop 章 ingest 后复盘蒸馏(loop 自动轮不写 chat_message,
            # 该章无人工对话时蒸馏自动 no_messages 跳过;有过讨论则照常沉淀)。
            # P1门审查 P2-5:与 /ingest 一致认 _complete_fn(测试可注入)。
            try:
                from scribe3.lesson import distill_chapter
                _dfn2 = _complete_fn
                if _dfn2 is None:
                    _dfn2 = hermes_complete
                distill_chapter(st, req.chapter, _dfn2)
            except Exception as de:
                logging.getLogger("scribe3").warning("loop 复盘蒸馏失败(忽略): %s", de)
            # ingest 后刷新 scorecard(P2-3 单源;在 settle 之后——fulfillment 读结算态)。
            _refresh_scorecard_after_ingest(st, req.chapter)
            return {"ok": True, "parse_failed": bool(r.get("parse_failed"))}
        except Exception as e:
            logging.getLogger("scribe3").warning("loop ingest 失败(正文已落库,如实上报): %s", e)
            return {"ok": False, "error": str(e)[:160]}
        finally:
            with _pending_ingest_lock:
                _pending_ingest.discard(ikey)

    try:
        result = run_chapter_loop(chapter=req.chapter, generate=_generate,
                                  post_check=_post_check, persist_version=_persist_version,
                                  finalize=_finalize, journal=journal)
    finally:
        with _loop_inflight_lock:
            _loop_inflight.discard(_lkey)
    # 遗留处置 1-A:熔断数据源。审查 P2-1:记"S1 是某轮唯一 blocking 来源"而非"S1 出现
    # 过"——与泄密/退化同场时章确有硬伤,S1 非决定性,计入会污染误杀率分子、熔断偏易开。
    def _s1_sole_blocking(rounds):
        for r0 in rounds:
            bl = r0.get("blocking") or []
            if bl and all(b.get("detector") == "findings_schema" for b in bl):
                return True
        return False
    _s1_record(work, _s1_sole_blocking(result.get("rounds", [])))
    # 遗留处置 1-C(#2):rounds 明细(含 blocking 原因)落 journal 旁,复用选择环
    # .result.json 模式——审计与盲评池的"为什么"单文件可查,不再只活在 HTTP 响应里。
    try:
        with open(str(jp) + ".result.json", "w", encoding="utf-8") as _f:
            json.dump(result, _f, ensure_ascii=False, indent=1)
    except Exception as e:
        logging.getLogger("scribe3").warning("loop 结果落盘失败(忽略): %s", e)
    result["journal_path"] = str(jp)
    return result


@app.get("/chapters")
def chapters(work: str = "main"):
    return _store_for(work).list_chapters()


@app.get("/chapters/archived")
def archived_chapters(work: str = "main"):
    """归档箱:列出已归档但尚未永久删除的章节。"""
    return _store_for(work).archived_chapters()


class ChapterCreateReq(BaseModel):
    title: str | None = None
    volume: str | None = None


@app.post("/chapters")
def create_chapter(req: ChapterCreateReq, work: str = "main"):
    """新建空章:seq 使用历史最大章号+1,不复用归档章。"""
    try:
        ch = _store_for(work).create_chapter(req.title or "", req.volume)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"status": "created", **ch}


class ChapterArchiveReq(BaseModel):
    reason: str | None = None


@app.post("/chapters/{seq}/archive")
def archive_chapter(seq: int, req: ChapterArchiveReq | None = None, work: str = "main"):
    """归档章节:默认删除动作,隐藏但保留正文、版本和关联。"""
    ok = _store_for(work).archive_chapter(seq, (req.reason if req else "") or "")
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "archived", "seq": seq}


@app.post("/chapters/{seq}/restore")
def restore_chapter(seq: int, work: str = "main"):
    ok = _store_for(work).restore_chapter(seq)
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "restored", "seq": seq}


@app.get("/chapters/{seq}/impact")
def chapter_impact(seq: int, work: str = "main"):
    impact = _store_for(work).chapter_lifecycle_impact(seq)
    if impact is None:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return impact


@app.delete("/chapters/{seq}")
def delete_chapter(seq: int, confirm_impact_token: str | None = None, work: str = "main"):
    """永久删除章节。必须先读取 impact 并带回 confirm_impact_token。"""
    st = _store_for(work)
    impact = st.chapter_lifecycle_impact(seq)
    if impact is None:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    if confirm_impact_token != impact["confirm_impact_token"]:
        return JSONResponse(status_code=409, content=impact)
    ok = st.delete_chapter_permanent(seq)
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "deleted", "seq": seq, "impact": impact}


# ===== 大纲/卷章树(手稿支数据层,作者工具 F-01 后端)=====

@app.get("/outline")
def get_outline(work: str = "main"):
    """聚合大纲:卷 + 章(梗概/字数/QC/视角/sort_order/label + 场景数)。
    章按 sort_order 升序;sort_order=NONE 时回退 seq。不回正文全文。"""
    return _store_for(work).outline()


@app.get("/project-tree")
def get_project_tree(work: str = "main"):
    """混合 Binder 项目树(作者工具 F-06):手稿支(卷→章→场景)+ 素材支(分类→条目)
    + 横切视图清单。只读统一投影,只回身份+角标,详情按 ref 懒加载。"""
    return _store_for(work).project_tree()


class ReorderReq(BaseModel):
    volume: str | None = None   # 目标卷裸 id;None = 未分卷区
    order: list[int]            # 该卷内章 seq 的新顺序(全量)


@app.post("/chapters/reorder")
def reorder_chapters(req: ReorderReq, work: str = "main"):
    """拖拽重排:改 sort_order(及 volume),绝不动 seq(故事时间轴主键)。
    R2.5: 目标 volume 不存在→422。
    """
    try:
        count = _store_for(work).reorder_chapters(req.volume, req.order)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"status": "reordered", "volume": req.volume, "count": count}


class ChapterMetaReq(BaseModel):
    synopsis: str | None = None
    volume: str | None = None   # 卷裸 id 或 None(置未分卷)
    label: str | None = None
    title: str | None = None
    beats: list | None = None   # 节拍:[{text, done?}, ...](Phase0-BE2 四阶段)
    scene_truth: str | None = None          # 场景真相(全知)
    involved_characters: list | None = None # 涉及角色 id
    deductions: list | None = None          # [{character_id, character_name, prose}]
    purpose_text: str | None = None         # 北极星任务6:一句话章节目的
    deltas: list | None = None              # 北极星任务6:delta 清单(登记时校验+预演)


@app.patch("/chapters/{seq}")
def patch_chapter(seq: int, req: ChapterMetaReq, work: str = "main"):
    """改章梗概/卷归属/标签/标题,不碰正文/embedding/qc。
    R2.3: 用 exclude_unset=True(区分"没传"与"传了 null"),让 volume=None 能清空卷归属。
    R2.5: 目标 volume 不存在→422。
    """
    fields = req.model_dump(exclude_unset=True)
    # 北极星任务6:目的合同登记校验——strict 解析(P1-5:非法条目 422 指明第几条,
    # 绝不静默丢弃后整体覆盖=静默数据销毁)+ 条数量控 + 认知类写前预演
    # (不可实现 → 422 带原因;预演降级放行时响应带旗,P2-2)。
    _rehearse_degraded = False
    if "purpose_text" in fields and fields["purpose_text"]:
        fields["purpose_text"] = str(fields["purpose_text"])[:200]
    if "deltas" in fields and fields["deltas"] is not None:
        from scribe3.purpose import (parse_deltas_strict, rehearse_delta_ex,
                                     validate_deltas)
        _ds, _errs = parse_deltas_strict(fields["deltas"])
        if _errs:
            raise HTTPException(status_code=422,
                                detail="deltas 有非法条目,未写入:" + ";".join(_errs))
        _err = validate_deltas(_ds)
        if _err:
            raise HTTPException(status_code=422, detail=_err)
        _foc = (_store_for(work).get_chapter(seq) or {}).get("focalizer")
        for _d in _ds:
            _rerr, _rdeg = rehearse_delta_ex(_store_for(work), seq, _d, _foc)
            _rehearse_degraded = _rehearse_degraded or _rdeg
            if _rerr:
                raise HTTPException(status_code=422, detail=_rerr)
        fields["deltas"] = _ds   # 存规范化后的清单
    try:
        ok = _store_for(work).update_chapter_meta(seq, fields)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    _resp = {"status": "updated", "seq": seq}
    if _rehearse_degraded:
        _resp["rehearse_degraded"] = True   # P2-2:预演故障放行须对调用方可见
    return _resp


# == 卷 CRUD ==

class VolumeReq(BaseModel):
    title: str = ""
    sort_order: int = 0
    intro: str | None = None
    color: str | None = None


@app.get("/volumes")
def list_volumes(work: str = "main"):
    return _store_for(work).list_volumes()


@app.post("/volumes")
def add_volume(req: VolumeReq, work: str = "main"):
    vid = _store_for(work).add_volume(
        title=req.title, sort_order=req.sort_order,
        intro=req.intro, color=req.color)
    return {"status": "created", "id": vid}


class VolumePatchReq(BaseModel):
    title: str | None = None
    sort_order: int | None = None
    intro: str | None = None
    color: str | None = None


@app.patch("/volumes/{vid}")
def update_volume(vid: str, req: VolumePatchReq, work: str = "main"):
    fields = req.model_dump(exclude_none=True)
    found = _store_for(work).update_volume(vid, fields)
    if not found:
        raise HTTPException(status_code=404, detail=f"volume '{vid}' 不存在")
    return {"status": "updated", "id": vid}


@app.delete("/volumes/{vid}")
def delete_volume(vid: str, work: str = "main"):
    """删卷:该卷下的章 volume 置 NONE(章不删),再删卷记录。卷不存在→404。"""
    found = _store_for(work).delete_volume(vid)
    if not found:
        raise HTTPException(status_code=404, detail=f"volume '{vid}' 不存在")
    return {"status": "deleted", "id": vid}


@app.get("/chapter")
def get_chapter(seq: int, work: str = "main"):
    return _store_for(work).get_chapter(seq) or {}


@app.get("/qc")
def qc(seq: int, work: str = "main"):
    """本章正文确定性体检(读已存正文,即算即返;全为确定性扫描,不打 LLM)。

    在原 quality_flags 五项(repetition/structural/purple/ai_tics/oversaturation)之外,
    补全 /save-chapter 同款的单章检测器:cross_repetition(跨章逐字复读)、
    duplicate_lines(整句重复)、emotion_telling(情感直说)。每项各自 fail-soft。

    返回每项为命中列表(前端取 length 显数、可点开看命中短语);另附
    cross_repetition_phrases 供高亮定位。cross_consistency 属全书聚合(非单章),
    留在 /post-check,不在此触发以免面板加载时跑全书查询。"""
    from scribe3.critique import (quality_flags, find_cross_chapter_repetitions,
                                  find_duplicate_lines, find_emotion_telling)
    import logging
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {}
    prose = ch["prose"]
    out = dict(quality_flags(prose))   # 五项:各为命中列表
    # 跨章复读(比对前文最近 8 章逐字 ≥8 字重叠,母题白名单放行)
    cross_rep: list[dict] = []
    try:
        priors = [c["prose"] for c in st.recent_proses(seq, k=8) if c.get("prose")]
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        cross_rep = find_cross_chapter_repetitions(prose, priors, n=8, allow=allow)
    except Exception as e:
        logging.getLogger("scribe3").warning("qc cross_repetition 失败 work=%s seq=%s: %s", work, seq, e)
    out["cross_repetition"] = cross_rep
    out["cross_repetition_phrases"] = [h.get("phrase") for h in cross_rep[:12]]
    # 整行复读
    try:
        out["duplicate_lines"] = find_duplicate_lines(prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("qc duplicate_lines 失败 work=%s seq=%s: %s", work, seq, e)
        out["duplicate_lines"] = []
    # 情感直说
    try:
        out["emotion_telling"] = find_emotion_telling(prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("qc emotion_telling 失败 work=%s seq=%s: %s", work, seq, e)
        out["emotion_telling"] = []
    return out


_QC_ISSUE_LABELS = {
    "repetition": "复读(章内)",
    "cross_repetition": "跨章复读",
    "duplicate_lines": "整句重复",
    "structural": "排比句式",
    "emotion_telling": "情感直说",
    "purple": "辞藻升华",
    "ai_tics": "AI 腔",
    "oversaturation": "过饱和",
}


def _issue_hit_text(hit) -> str:
    if isinstance(hit, str):
        return hit
    if isinstance(hit, dict):
        for k in ("phrase", "line", "span", "text", "detail", "reason"):
            if hit.get(k):
                return str(hit[k])
    return str(hit)


def _issue_hit_range(hit) -> list[int]:
    if isinstance(hit, dict):
        span = hit.get("range") or hit.get("loc")
        if isinstance(span, (list, tuple)) and len(span) == 2:
            return [int(span[0] or 0), int(span[1] or 0)]
        if hit.get("start") is not None or hit.get("end") is not None:
            return [int(hit.get("start") or 0), int(hit.get("end") or 0)]
    return [0, 0]


@app.get("/issues")
def issue_ledger(chapter: int | None = Query(default=None, ge=1), work: str = "main"):
    """校验台账:把 QC/因果等现有确定性结果归一化为可钻取 issue。"""
    st = _store_for(work)
    seqs = [chapter] if chapter is not None else [int(c["seq"]) for c in st.list_chapters()]
    issues = []
    degraded_sources = []
    for seq in seqs:
      try:
        q = qc(seq, work)
      except Exception as e:
        degraded_sources.append({"source": "qc", "chapter": seq, "reason": str(e)})
        q = {}
      for source_key, label in _QC_ISSUE_LABELS.items():
        hits = q.get(source_key) or []
        if isinstance(hits, int):
            hits = [{} for _ in range(hits)]
        if not isinstance(hits, list):
            continue
        for idx, hit in enumerate(hits):
            reason = _issue_hit_text(hit)
            severity = "error" if source_key in {"duplicate_lines", "cross_repetition"} else "warning"
            issues.append({
                "id": f"issue:qc:{seq}:{source_key}:{idx}",
                "source": "qc",
                "kind": source_key,
                "severity": severity,
                "title": label,
                "reason": reason,
                "chapter": seq,
                "range": _issue_hit_range(hit),
                "status": "open",
                "suggested_action": "定位到正文后改写或删减重复表达。",
                "target_node": {"id": f"ch:{seq}", "type": "chapter", "ref": seq, "label": f"第 {seq} 章"},
            })
      try:
        causal_result = causal(seq, work)
        for idx, v in enumerate(causal_result.get("violations") or []):
            issues.append({
                "id": f"issue:causal:{seq}:{idx}",
                "source": "causal",
                "kind": "causal",
                "severity": "warning",
                "title": "因果链缺口",
                "reason": v.get("reason") or str(v),
                "chapter": seq,
                "range": [0, 0],
                "status": "open",
                "suggested_action": "补上前因、目标或结果承接。",
                "target_node": {"id": f"ch:{seq}", "type": "chapter", "ref": seq, "label": f"第 {seq} 章"},
            })
      except Exception as e:
        degraded_sources.append({"source": "causal", "chapter": seq, "reason": str(e)})
    return {"issues": issues, "degraded_sources": degraded_sources}


@app.get("/discipline")
def discipline(seq: int, brief: str = "", work: str = "main"):
    from scribe3.critique import discipline_truncate
    from scribe3.llm import hermes_complete
    ch = _store_for(work).get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"ok": True, "violations": []}
    return discipline_truncate(ch["prose"], brief, hermes_complete)


@app.post("/tension-check")
def tension_check(seq: int, work: str = "main"):
    """M2a 叙事张力检查:确定性3项(伏笔进展/开环账本/信息差盘点)+ LLM rubric 5项
    (戏剧问题/结局语法/价值反转/微张力荒漠/续读钩子,单次合并盲评)。读已存正文,不落库,
    登记为 read-only POST(见 KNOWN_REST_WRITE_ROUTES)。no_prose 早退;rubric 失败(坏 JSON /
    LLM 异常)→ rubric_failed=True,确定性项照常返回,不崩。"""
    from scribe3.brief import tension_deterministic
    from scribe3.critique import build_tension_rubric_prompt, parse_tension_report
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"items": [], "error": "no_prose"}
    items = tension_deterministic(st, seq)
    raw = None
    try:
        from scribe3.llm import hermes_complete
        raw = hermes_complete(build_tension_rubric_prompt(ch["prose"]))
    except Exception as e:
        logging.getLogger("scribe3").warning("tension_check rubric LLM 失败 work=%s seq=%s: %s", work, seq, e)
    rep = parse_tension_report(raw)
    if rep is None:
        return {"items": items, "rubric": None, "rubric_failed": True}
    # Minor1(T9):rep 是合法 JSON 但值型可能错(如 outcomes 是字符串列表而非 dict 列表)。
    # o.get()/"、".join() 会抛 AttributeError/TypeError——整段组装纳入 try,失败降级
    # rubric_failed=True(与坏 JSON 同口径),确定性项照常返回,端点不 500。
    try:
        outs = rep.get("outcomes") or []
        yes_leak = [o for o in outs if o.get("type") == "yes"]
        deserts = (rep.get("micro_tension") or {}).get("deserts") or []
        items += [
            {"item": "dramatic_question", "pass": bool((rep.get("dramatic_question") or {}).get("present")),
             "detail": (rep.get("dramatic_question") or {}).get("note") or "",
             "fix": "给本章立一个悬着的小问题,章末回答并升级"},
            {"item": "outcome_grammar", "pass": not yes_leak,
             "detail": f"{len(yes_leak)} 场顺利达成(泄气)",
             "fix": "把顺利达成改为 yes-but(达成+新并发症)或 no-and(失败+更糟)"},
            {"item": "value_shift", "pass": bool((rep.get("value_shift") or {}).get("present")),
             "detail": (rep.get("value_shift") or {}).get("note") or "",
             "fix": "至少让一场戏的核心价值发生极性反转"},
            {"item": "micro_tension", "pass": not deserts,
             # Minor2(T9):运算符优先级——原 "荒漠段:"+join or "无" 因加法先算,"无"永不触发,
             # 空 deserts 时显示尾冒号。改为整体三元:空 → "无"。
             "detail": ("荒漠段:" + "、".join(deserts)) if deserts else "无",
             "fix": "在荒漠段给 POV 角色写情绪对立/念头交战(对话与内心相悖/动作带矛盾情绪)"},
            {"item": "hook", "pass": bool((rep.get("hook") or {}).get("present")),
             "detail": f"{(rep.get('hook') or {}).get('type')}/{(rep.get('hook') or {}).get('strength')}",
             "fix": "章末以危险临近/信息截断/悬置选择收尾"},
        ]
    except (AttributeError, TypeError) as e:
        logging.getLogger("scribe3").warning(
            "tension_check rubric 值型错(合法 JSON 但结构不符)work=%s seq=%s: %s", work, seq, e)
        return {"items": items, "rubric": None, "rubric_failed": True}
    return {"items": items, "rubric": rep}


# ===== 写 =====
class SaveChapterReq(BaseModel):
    seq: int
    prose: str
    title: str = ""
    focalizer: str | None = None


class CheckpointReq(BaseModel):
    prose: str
    label: str = ""
    kind: str = "checkpoint"   # checkpoint | final
    qc: dict = {}


class CheckReq(BaseModel):
    prose: str
    focalizer: str = ""
    short_mode: bool = False  # 方案B任务16:短篇模式——透传给 aggregate_ai_grade,
                              # 直写情绪不计入 psych_ratio/Gate C


def _refresh_scorecard_after_ingest(st, seq: int) -> None:
    """ingest 后刷新章 scorecard(P0门审查 P2-3,单源供 /ingest、_bg_ingest、loop 共用):
    存稿时快照没有本章事件,qc_causal 停在 -1 哨兵;反哺落库后重算出真值。
    fail-soft:刷新失败只告警,不影响 ingest 结果。"""
    try:
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
        if prose.strip():
            st._upsert_scorecard(st._compute_scorecard(seq, prose, ch.get("focalizer")))
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning(
            "ingest 后 scorecard 刷新失败(忽略) seq=%s: %s", seq, e)


def _bg_ingest(work: str, seq: int) -> None:
    """后台客观回写:开**独立** store 连接跑 ingest_chapter(P2-3:不复用 _store_for 的共享 ws,
    避免多后台任务跨线程交错同一连接)。异常只记日志,不影响存稿(non-fatal)。
    schema 已由端点侧 _store_for(work) 建好,此处不重复 apply。完成时(finally)清在途标记。"""
    import logging
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    # 审计 P1-6:ingest 结果状态落 chapter(ingest_status/ingest_error)——此前失败只写
    # 服务端日志,前端零感知,知识账本悄悄落后,后续章简报/限知帧全吃陈旧数据。
    def _mark(st0, status, err=""):
        try:
            st0._execute_write(
                "UPDATE type::record('chapter',$seq) SET ingest_status=$st, ingest_error=$er",
                {"seq": seq, "st": status, "er": (err or "")[:200]})
        except Exception as me:
            logging.getLogger("scribe3").warning("ingest 状态落库失败(忽略): %s", me)

    st = None
    try:
        st = SurrealStore(ns="scribe3", db=work)
        r = ingest_chapter(st, seq, hermes_complete)
        if r.get("parse_failed"):
            logging.getLogger("scribe3").warning(
                "后台 ingest %s 第%s章: LLM 回复解析失败,既有知识已保留(未 purge)", work, seq)
            _mark(st, "parse_failed", "LLM 回复解析失败,知识账本未更新")
        else:
            _refresh_scorecard_after_ingest(st, seq)   # P2-3:主链路 ingest 后哨兵转真值
            _mark(st, "ok")
        # 北极星任务8:后台 ingest 完成后同样触发复盘蒸馏(fail-soft)。
        try:
            from scribe3.lesson import distill_chapter
            distill_chapter(st, seq, hermes_complete)
        except Exception as e:
            logging.getLogger("scribe3").warning("后台 ingest 复盘蒸馏失败(忽略) %s 第%s章: %s",
                                                 work, seq, e)
    except Exception as e:
        logging.getLogger("scribe3").warning("后台 ingest %s 第%s章失败: %s", work, seq, e)
        if st is not None:
            _mark(st, "failed", str(e))
    finally:
        with _pending_ingest_lock:
            _pending_ingest.discard((work, seq))
        if st is not None:
            try:
                st.close()
            except Exception as ce:
                logging.getLogger("scribe3").warning(
                    "后台 ingest 独立连接关闭失败 %s 第%s章: %s", work, seq, ce)


def _enqueue_ingest(background: BackgroundTasks, work: str, seq: int) -> bool:
    """排后台 ingest,同章去重(P0-1 竞态根治):同 (work,seq) 已在途/在排 → 跳过第二次排队。
    谁先排谁负责,第二个跳过——这样"存为正文"的 save-chapter + checkpoint(final) 双触发
    只会真正跑一次 ingest。返回是否真正排入(在途标记随 _bg_ingest 完成时清除)。"""
    key = (work, seq)
    with _pending_ingest_lock:
        if key in _pending_ingest:
            return False
        _pending_ingest.add(key)
    background.add_task(_bg_ingest, work, seq)
    return True


@app.post("/save-chapter")
def save_chapter(req: SaveChapterReq, background: BackgroundTasks, work: str = "main"):
    # 遗留处置 1-B:同章生成在途(loop/选择环)时拒绝手动存稿——数分钟长请求期间
    # 手改再存会与自动落库互踩静默覆盖。409 不丢编辑(正文仍在前端编辑器里)。
    with _loop_inflight_lock:
        if (work, req.seq) in _loop_inflight:
            raise HTTPException(status_code=409, detail=(
                f"第 {req.seq} 章生成在途(loop/选择环),完成后再存——"
                "你的编辑不会丢,可先复制正文"))
    _guard_pilot_busy(work, req.seq)   # R2-3:pilot 非 loop 步在途/连写中也拦(防挂旧稿)
    st = _store_for(work)
    st.save_chapter(req.seq, req.prose, title=req.title, focalizer=req.focalizer)
    # 四阶段(Phase0-BE2):存正文自动留 final 版(快照存稿瞬间)。fail-soft:留版失败不阻断存稿。
    # 审计 P2-1:内容与最新 final 版相同则不重复落版(自动存稿风暴刷屏版本史)。
    try:
        if st.latest_version_prose(req.seq, "final") != req.prose:
            st.add_chapter_version(req.seq, req.prose, label="", kind="final",
                                   stage="final", stats=_prose_stats(req.prose))
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning(
            "save-chapter 自动留 final 版失败(存稿不受影响) work=%s seq=%s: %s", work, req.seq, e)
    # 软校验(确定性、快、不打 LLM):QC + 限知泄露。回写走独立 /ingest(前端接受后再调)。
    from scribe3.critique import quality_flags, find_cross_chapter_repetitions, find_duplicate_lines, find_emotion_telling
    qf = quality_flags(req.prose)
    # 跨章复读:逐章 QC 查不到的"单遍长程生成典型病"(模型跨章复用偏爱措辞)。
    # 比对前文最近 5 章逐字 ≥8 字重叠——把"重复"从'事后逐章删'升级为'跨章可度量'。
    cross_rep: list[dict] = []
    try:
        priors = [c["prose"] for c in st.recent_proses(req.seq, k=8) if c.get("prose")]
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        cross_rep = find_cross_chapter_repetitions(req.prose, priors, n=8, allow=allow)
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning("cross_repetition 失败 work=%s seq=%s: %s", work, req.seq, e)
    # M2-①: 整行复读 + 情感直说计数(fail-soft)
    dup_lines_count = 0
    try:
        dup_lines_count = len(find_duplicate_lines(req.prose))
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning("find_duplicate_lines 失败 work=%s seq=%s: %s", work, req.seq, e)
    emotion_telling_count = 0
    try:
        emotion_telling_count = len(find_emotion_telling(req.prose))
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning("find_emotion_telling 失败 work=%s seq=%s: %s", work, req.seq, e)
    leaks, leak_error = None, None
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            leaks = len(find_leaks(req.prose, st, req.focalizer, req.seq))
        except Exception as e:
            import logging
            logging.getLogger("scribe3").warning("find_leaks 失败 work=%s seq=%s: %s", work, req.seq, e)
            leak_error = str(e)[:160]
    _enqueue_ingest(background, work, req.seq)
    return {"status": "saved", "seq": req.seq,
            "qc": {"repetition": len(qf["repetition"]), "structural": len(qf["structural"]),
                   "purple": len(qf["purple"]), "cross_repetition": len(cross_rep),
                   "duplicate_lines": dup_lines_count, "emotion_telling": emotion_telling_count},
            "cross_repetition_phrases": [h["phrase"] for h in cross_rep[:12]],
            "leaks": leaks, "leak_error": leak_error, "ingesting": True}


@app.post("/dedup-chapter")
def dedup_chapter(seq: int, background: BackgroundTasks, work: str = "main"):
    """确定性事后跨章改写(QC 的'治'层):定位本章含跨章逐字复读的句子→定向 LLM 改写→存回。

    比'prompt 预防'可靠(实测最严重章跨章复读 30→8,↓73%),契合本系统'确定性扫描+定向改'的纪律。
    幂等:无复读则原样返回、不调 LLM(不落版、不排 ingest)。

    C-1(正文覆写三路对称):真改写正文后,与 /save-chapter 对称——落 final 版本(补版本历史断链)
    + 排后台 ingest(内容变了理应重抽知识账本;经 _enqueue_ingest 与 P0-1 同章去重护栏协同,
    若该章已有 ingest 在途则跳过,不产生双份)。"""
    # 批次一审查 P1-2:与 /save-chapter 同款在途护栏——loop/选择环期间 dedup 改写落库
    # 会与自动落库互踩(1-B 堵了手动存稿这个门,这里是同一风险的另一个门)。
    with _loop_inflight_lock:
        if (work, seq) in _loop_inflight:
            raise HTTPException(status_code=409, detail=(
                f"第 {seq} 章生成在途(loop/选择环),完成后再去重"))
    _guard_pilot_busy(work, seq)   # R2-3:pilot 非 loop 步在途/连写中也拦
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        raise HTTPException(status_code=404, detail="chapter not found")
    from scribe3.critique import rewrite_cross_repetitions
    from scribe3.llm import hermes_complete
    priors = [c["prose"] for c in st.recent_proses(seq, k=8) if c.get("prose")]
    allow = st.motif_terms() if hasattr(st, "motif_terms") else None
    res = rewrite_cross_repetitions(ch["prose"], priors, hermes_complete, n=8, allow=allow)
    if res["rewritten"] > 0:
        st.save_chapter(seq, res["prose"], title=ch.get("title", ""), focalizer=ch.get("focalizer"))
        # 落 final 版(与 /save-chapter 对称;fail-soft:留版失败不阻断改写落库)
        try:
            st.add_chapter_version(seq, res["prose"], label="", kind="final",
                                   stage="final", stats=_prose_stats(res["prose"]))
        except Exception as e:
            import logging
            logging.getLogger("scribe3").warning(
                "dedup-chapter 自动留 final 版失败(改写已落库) work=%s seq=%s: %s", work, seq, e)
        # 内容变了 → 排 ingest(去重护栏防与自动 ingest 撞双份)
        _enqueue_ingest(background, work, seq)
    return {"seq": seq, "rewritten": res["rewritten"],
            "cross_repetition_before": res["before"], "cross_repetition_after": res["after"]}


@app.post("/polish-chapter")
def polish_chapter(seq: int, background: BackgroundTasks, work: str = "main"):
    """章内精修(QC 治层·章内维度):定位本章内 repetition/duplicate_lines/排比 → 定向改写 → 存回。

    与 /dedup-chapter(跨章逐字复读)对称互补:分幕长章在章内自我复读、堆排比,跨章 dedup 完全
    治不到。同源哲学'确定性扫描+定向改写'——不靠 prompt 记住禁令,只精准改犯规句,改写器强约束
    保限知(绝不点破未揭示悬念)。幂等:无章内硬伤则原样返回、不调 LLM(不落版、不排 ingest)。
    三路对称(落 final 版 + 排后台 ingest)与 /save-chapter、/dedup-chapter 一致。"""
    with _loop_inflight_lock:
        if (work, seq) in _loop_inflight:
            raise HTTPException(status_code=409, detail=(
                f"第 {seq} 章生成在途(loop/选择环),完成后再精修"))
    _guard_pilot_busy(work, seq)
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        raise HTTPException(status_code=404, detail="chapter not found")
    from scribe3.critique import rewrite_intra_chapter_issues
    from scribe3.llm import hermes_complete
    allow = st.motif_terms() if hasattr(st, "motif_terms") else None
    res = rewrite_intra_chapter_issues(ch["prose"], hermes_complete, allow=allow)
    leak_guard = None
    if res["rewritten"] > 0:
        # 限知二次门:改写单句无全局 context,可能把原文刻意模糊的表述"具体化点破"未揭示悬念。
        # 落库前复跑 find_leaks(与 /save-chapter、/check 同一泄露门),泄露增加则整体回退不落库。
        foc = ch.get("focalizer")
        if foc:
            try:
                from scribe3.verify import find_leaks
                before_leaks = len(find_leaks(ch["prose"], st, foc, seq))
                after_leaks = len(find_leaks(res["prose"], st, foc, seq))
                if after_leaks > before_leaks:
                    leak_guard = {"before": before_leaks, "after": after_leaks, "action": "rolled_back"}
                    res = {"rewritten": 0, "before": res["before"], "after": res["before"],
                           "prose": ch["prose"]}
            except Exception as e:
                import logging
                logging.getLogger("scribe3").warning(
                    "polish-chapter find_leaks 二次门异常(保守起见回退不落库) work=%s seq=%s: %s",
                    work, seq, e)
                leak_guard = {"error": str(e), "action": "rolled_back"}
                res = {"rewritten": 0, "before": res["before"], "after": res["before"],
                       "prose": ch["prose"]}
    if res["rewritten"] > 0:
        st.save_chapter(seq, res["prose"], title=ch.get("title", ""), focalizer=ch.get("focalizer"))
        try:
            st.add_chapter_version(seq, res["prose"], label="", kind="final",
                                   stage="final", stats=_prose_stats(res["prose"]))
        except Exception as e:
            import logging
            logging.getLogger("scribe3").warning(
                "polish-chapter 自动留 final 版失败(改写已落库) work=%s seq=%s: %s", work, seq, e)
        _enqueue_ingest(background, work, seq)
    resp = {"seq": seq, "rewritten": res["rewritten"],
            "intra_issues_before": res["before"], "intra_issues_after": res["after"]}
    if leak_guard:
        resp["leak_guard"] = leak_guard
    return resp


@app.post("/check")
def check_prose(req: CheckReq, seq: int, work: str = "main"):
    """护栏轻检查:QC + 限知泄露,不落库(改造③ 停笔静默刷新用)。
    F-05: 新增顶层 issues 列表(带 range),兼容旧 qc/leaks 计数字段。"""
    st = _store_for(work)
    from scribe3.critique import quality_flags, quality_issues
    # 方案B任务14:本书 craft 豁免——extra(升华正则加法)+ allow_words/allow_patterns
    # (前置 skip 判定,减法),fail-soft(取不到就退回 None,不影响本次检查)。
    import logging
    extra = allow_words = allow_pats = None
    try:
        extra = st.purple_patterns() if hasattr(st, "purple_patterns") else None
        allow_words = set(st.allow_words()) if hasattr(st, "allow_words") else None
        allow_pats = st.allow_patterns() if hasattr(st, "allow_patterns") else None
    except Exception as e:
        logging.getLogger("scribe3").warning("check 取 craft 豁免失败: %s", e)
    qf = quality_flags(req.prose, extra, allow_words, allow_pats)
    leaks = []
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            leaks = [{"fact_id": lk.fact_id, "marker": lk.marker, "subject": lk.subject,
                      "range": list(lk.range) if lk.range else None}
                     for lk in find_leaks(req.prose, st, req.focalizer, seq)]
        except Exception as e:
            logging.getLogger("scribe3").warning("check find_leaks 失败: %s", e)

    # F-05: 组装带 range 的 issues(白送类 QC + leaks)
    issues: list[dict] = []
    try:
        issues = quality_issues(req.prose, extra, allow_words, allow_pats)
    except Exception as e:
        logging.getLogger("scribe3").warning("check quality_issues 失败: %s", e)
    # 追加 leak issues
    for lk in leaks:
        issues.append({
            "type": "leak",
            "message": f"限知泄露:视角角色不该知道「{lk['marker']}」",
            "text": lk["marker"],
            "range": lk["range"],
            "meta": {"fact_id": lk["fact_id"], "subject": lk["subject"]},
        })

    resp = {"qc": {"repetition": len(qf["repetition"]),
                   "structural": len(qf["structural"]),
                   "purple": len(qf["purple"]),
                   "ai_tics": len(qf["ai_tics"]),
                   "oversaturation": len(qf["oversaturation"])},
            "leaks": leaks,
            "issues": issues}
    # 方案A任务8:整章 AI 味定档聚合,fail-soft(异常时不给该字段,不 500)。
    try:
        from scribe3.critique import aggregate_ai_grade
        resp["ai_grade"] = aggregate_ai_grade(qf, req.prose, short_mode=req.short_mode)
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning("check aggregate_ai_grade 失败: %s", e)
    return resp


class PostCheckReq(BaseModel):
    prose: str
    focalizer: str = ""
    brief: str = ""
    short_mode: bool = False  # 方案B任务16:短篇模式——直写情绪+审判金句合法,
                              # 透传给 find_emotion_telling/aggregate_ai_grade,
                              # emotion_telling 检出归零、psych_ratio/Gate C 不触发


@app.post("/post-check")
def post_check(req: PostCheckReq, seq: int, work: str = "main"):
    """生成后全量体检:五类确定性 QC + 限知泄露 + LLM 语义纪律判(fail-open)。
    不落库。注册为 read-only POST(见 KNOWN_REST_WRITE_ROUTES)。
    F-05: 新增顶层 issues 列表(带 range),兼容旧 quality/leaks 字段。
    M2-②: 新增 duplicate_lines/emotion_telling(B/C 检测器)+ cross_consistency(跨章矛盾)。"""
    import logging
    from scribe3.critique import (quality_flags, quality_issues, discipline_truncate,
                                  find_duplicate_lines, find_emotion_telling,
                                  find_parallelism, find_poetic_fragments,
                                  find_unbalanced_quotes, find_watch_regression)
    st = _store_for(work)

    # 方案B任务14:本书 craft 豁免——extra(升华正则加法)+ allow_words/allow_patterns
    # (前置 skip 判定,减法),fail-soft(取不到就退回 None,不影响本次体检)。
    extra = allow_words = allow_pats = None
    try:
        extra = st.purple_patterns() if hasattr(st, "purple_patterns") else None
        allow_words = set(st.allow_words()) if hasattr(st, "allow_words") else None
        allow_pats = st.allow_patterns() if hasattr(st, "allow_patterns") else None
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check 取 craft 豁免失败: %s", e)

    # 方案B任务19:跨批开放伏笔账本注入 reviewer(scribe3 DB 优势区)——同一处取
    # craft 豁免的上下文里,顺手筛"预计回收章≤本章"的 open promise 作"继承的
    # 开放项",供下面 LLM 纪律判读作背景(未处理的坑要在 findings 里指出)。
    # fail-soft:取不到不影响本次体检其余字段。
    from scribe3.brief import inherited_open_block
    inherited_open_promises: list[dict] = []
    inherited_text = ""
    try:
        inherited = inherited_open_block(st.promises_with_lifecycle(max_chapter=seq), chapter=seq)
        inherited_open_promises = inherited["items"]
        inherited_text = inherited["text"]
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check inherited_open_block 失败: %s", e)

    # 1. 确定性五类 QC
    qf = quality_flags(req.prose, extra, allow_words, allow_pats)
    qc_breakdown = {
        "repetition": len(qf["repetition"]),
        "structural": len(qf["structural"]),
        "purple": len(qf["purple"]),
        "ai_tics": len(qf["ai_tics"]),
        "oversaturation": len(qf["oversaturation"]),
    }
    qc_total = sum(qc_breakdown.values())

    # 2. 限知泄露(有 focalizer 才跑)
    leaks: list[dict] = []
    leaks_degraded = False
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            leaks = [{"fact_id": lk.fact_id, "marker": lk.marker, "subject": lk.subject,
                      "range": list(lk.range) if lk.range else None}
                     for lk in find_leaks(req.prose, st, req.focalizer, seq)]
        except Exception as e:
            logging.getLogger("scribe3").warning("post_check find_leaks 失败: %s", e)
            leaks_degraded = True

    # 3. LLM 语义纪律判(fail-open)
    discipline: dict = {}
    degraded = False
    degraded_stages: list[str] = []
    try:
        # 优先用测试注入的 _complete_fn,否则走真实 hermes_complete
        complete_fn = _complete_fn
        if complete_fn is None:
            from scribe3.llm import hermes_complete
            complete_fn = hermes_complete
        # 任务19:有到期继承开放项时拼进 brief——若调用方未传 brief,先补回
        # build_discipline_prompt 的默认纪律文案(DEFAULT_DISCIPLINE_BRIEF 单一来源,
        # 收尾清理批 Minor:消除手写字面量副本的漂移风险),再拼继承项,
        # 避免"继承开放项非空"顶掉默认纪律要求(两者都该在场)。
        brief_for_discipline = req.brief
        if inherited_text:
            from scribe3.critique import DEFAULT_DISCIPLINE_BRIEF
            base_brief = req.brief or DEFAULT_DISCIPLINE_BRIEF
            brief_for_discipline = base_brief + "\n\n" + inherited_text
        discipline = discipline_truncate(req.prose, brief_for_discipline, complete_fn)
        # 审计 E-2/#58:LLM 回复解析失败 → fail-open 放行但计 degraded(没查≠没病;
        # 不入 _PASS_CRITICAL_STAGES——纪律判是 S1 来源,不是 pass 门关键检测)。
        if discipline.get("parse_failed"):
            degraded = True
            degraded_stages.append("discipline_parse")
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check discipline 失败: %s", e)
        degraded = True
        degraded_stages.append("discipline")
    if leaks_degraded:
        degraded = True
        degraded_stages.append("find_leaks")

    # 4. 设定校验:物品状态/OOC/世界规则/命名一致性(fail-soft)
    setting: list[dict] = []
    try:
        setting = st.validate_setting(seq, req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check validate_setting 失败: %s", e)
        degraded = True
        degraded_stages.append("validate_setting")

    # F-05: 组装带 range 的顶层 issues(白送类 QC + leaks + discipline.cut_after)
    issues: list[dict] = []
    try:
        issues = quality_issues(req.prose, extra, allow_words, allow_pats)
    except Exception as e:
        # P0门审查 P1-4:issues 喂 loop 的 blocking 判据②(degeneration)与待批清单,
        # 该 stage 挂掉必须记 degraded——否则"没查被当没病",loop 会假绿宣 pass。
        logging.getLogger("scribe3").warning("post_check quality_issues 失败: %s", e)
        degraded = True
        degraded_stages.append("quality_issues")
    # leak issues
    for lk in leaks:
        issues.append({
            "type": "leak",
            "message": f"限知泄露:视角角色不该知道「{lk['marker']}」",
            "text": lk["marker"],
            "range": lk["range"],
            "meta": {"fact_id": lk["fact_id"], "subject": lk["subject"]},
        })
    # 纪律违规 issue(遗留处置 1-A)。violations 即报——此前 cut_after 为空时违规被
    # 静默吞;cut_after 只负责定位。severity 三重防误杀:单次 LLM 判默认 S2(advisory);
    # 仅确定性信号同向命中(共振表,≤5 条硬编码)才升 S1 → triage blocking 判据④;
    # 熔断开(近 10 次 loop S1 触发率>30%)时升格暂停。共振表(自定口径,待盲评池校准):
    #   knowledge_leak ↔ find_leaks 命中 或 god_view(kind=god_spoiler,叙述层知识泄露形态)
    #   god_view       ↔ god_view(kind∈{god_spoiler,explain_causality};批次一审查 P1-1:
    #                    summarize 的"此刻,他"/sublimation 是好稿常见句式或纯风格,
    #                    与全知违规同向性不足,拿来共振=为无关违规背书,故收窄强全知两类)
    #   exposition_dump↔ oversaturation>0
    #   double_climax / voice_collapse 无确定性对应物 → 恒 S2
    if discipline.get("violations") or discipline.get("cut_after"):
        cut = discipline.get("cut_after") or ""
        idx = req.prose.find(cut) if cut else -1
        rng = [idx, idx + len(cut)] if (cut and idx >= 0) else None
        _viol = set(discipline.get("violations") or [])
        _god_kinds = {(i.get("meta") or {}).get("kind")
                      for i in issues if i.get("type") == "god_view"}
        _resonance = (
            ("knowledge_leak" in _viol and (bool(leaks) or "god_spoiler" in _god_kinds))
            or ("god_view" in _viol
                and bool(_god_kinds & {"god_spoiler", "explain_causality"}))
            or ("exposition_dump" in _viol
                and (qc_breakdown.get("oversaturation") or 0) > 0)
        )
        _sev = "S1" if (_resonance and not _s1_circuit_open(work)) else "S2"
        issues.append({
            "type": "discipline",
            "message": f"纪律违规:{'、'.join(discipline.get('violations', []))}",
            "text": cut,
            "range": rng,
            "meta": {"violations": discipline.get("violations", []),
                     "extra": discipline.get("extra") or [],   # LLM 自由文本观察(D-024,不参与升格)
                     "severity": _sev, "resonance": _resonance},
        })
    # setting issues
    for hint in setting:
        evidence = hint.get("evidence") or ""
        idx = req.prose.find(evidence) if evidence else -1
        rng = [idx, idx + len(evidence)] if idx >= 0 and evidence else None
        issues.append({
            "type": "setting",
            "message": hint.get("description", "设定校验问题"),
            "text": evidence,
            "range": rng,
            "meta": {"entity": hint.get("entity"), "severity": hint.get("severity")},
        })

    # 方案A任务7:同义词循环(elegant_variation)——需要角色名单,纯函数层拿不到,
    # 不进 quality_flags;这里用 store 上下文取角色名单再调用,fail-soft(取不到角色/
    # store 异常时直接跳过,不影响 /post-check 整体 200)。
    try:
        from scribe3.critique import find_elegant_variation
        names = [c.name for c in st.characters()]
        for hit in find_elegant_variation(req.prose, names):
            issues.append({
                "type": "elegant_variation",
                "message": f"同义词循环:「{hit['name']}」被泛称({'、'.join(hit['aliases'])})反复替换指代,疑似刻意避重复过犹不及",
                "text": hit["name"],
                "range": hit["range"],
                "meta": {"aliases": hit["aliases"]},
            })
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_elegant_variation 失败: %s", e)

    # M2-②: 接线 B/C 检测器 + 跨章矛盾(fail-soft;异常不阻断,记 degraded_stages)
    dup_lines: list[dict] = []
    try:
        dup_lines = find_duplicate_lines(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_duplicate_lines 失败: %s", e)
        degraded = True
        degraded_stages.append("find_duplicate_lines")

    emotion_telling: list[dict] = []
    try:
        # B14 审查(收尾清理批):allow_pats 已在本函数上文从 st.allow_patterns() 取出
        # (供 quality_flags/quality_issues 用),此前未传给 find_emotion_telling——
        # 题材豁免正则对直写情绪检测器不生效,这里补上,与其余检测器同一豁免机制。
        emotion_telling = find_emotion_telling(req.prose, allow_pats, short_mode=req.short_mode)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_emotion_telling 失败: %s", e)
        degraded = True
        degraded_stages.append("find_emotion_telling")

    cross_consistency: list[dict] = []
    try:
        cross_consistency = st.validate_cross_chapter_consistency()
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check validate_cross_chapter_consistency 失败: %s", e)
        degraded = True
        degraded_stages.append("validate_cross_chapter_consistency")

    # 方案B任务11:卷级张弛基线——接线落点说明:仓内无独立"全书体检/审计"端点
    # (/qc 显式注明 cross_consistency 属全书聚合但"留在 /post-check,不在此触发,以免
    # 面板加载时跑全书查询";/post-check 是仓内唯一已把"全书聚合"字段(cross_consistency/
    # orphan_edges)混入单章体检响应的端点),故本检测器同样落点于此,带 work 全章上下文
    # (遍历 st.list_chapters() 逐章解析 role/pressure,而非只看当前 seq)。fail-soft:
    # 书级扫描异常不阻断本次单章体检的其余字段。
    tension_monotony: list[dict] = []
    try:
        from scribe3.brief import find_tension_monotony, parse_chapter_meta, chapter_draft_text
        chapters_meta: list[dict] = []
        # R2-16:窄查(chapters_lite 只拉草料字段,不逐章 get_chapter 全行含 prose)——
        # 与 north_star_book 同一 tension 聚合的 2-D#5 先例对齐;chapter_draft_text 仅用
        # synopsis/beats/scene_truth,chapters_lite 全覆盖,行为等价、去掉全书 prose 拉取。
        for c in st.chapters_lite():
            meta = parse_chapter_meta(chapter_draft_text(c))
            if meta:
                chapters_meta.append({"seq": c["seq"], **meta})
        tension_monotony = find_tension_monotony(chapters_meta)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_tension_monotony 失败 work=%s: %s", work, e)
        degraded = True
        degraded_stages.append("find_tension_monotony")

    # 批E-B(P2-15):orphan_knowledge_edges 审计器接线——此前仅测试、零生产接线。
    # 真实孤儿路径:DELETE /facts 删命题时 knows 图边级联消失,但 reader_knows(独立表,
    # CREATE 非 RELATE)不级联 → 留悬挂边。全书聚合(非单章),同 cross_consistency 留在
    # /post-check;fail-soft。注:内部按边逐条 existence 查(N+1),仅在此按需体检跑,非热路径。
    orphan_edges: list[dict] = []
    try:
        orphan_edges = st.orphan_knowledge_edges()
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check orphan_knowledge_edges 失败: %s", e)
        degraded = True
        degraded_stages.append("orphan_knowledge_edges")

    # P1-10 彻查:4 个既有确定性检测器接线(此前已实现但全仓零生产接线)。
    # 排比/诗化分行/引号失配/更次倒退——均对单章成文,不需跨章上下文
    # (find_watch_regression 检测的是本章内更次序列的非单调,非跨章连续性);各自 fail-soft。
    parallelism: list[dict] = []
    try:
        parallelism = find_parallelism(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_parallelism 失败: %s", e)
        degraded = True
        degraded_stages.append("find_parallelism")

    poetic_fragments: list[dict] = []
    try:
        poetic_fragments = find_poetic_fragments(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_poetic_fragments 失败: %s", e)
        degraded = True
        degraded_stages.append("find_poetic_fragments")

    unbalanced_quotes: list[dict] = []
    try:
        unbalanced_quotes = find_unbalanced_quotes(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_unbalanced_quotes 失败: %s", e)
        degraded = True
        degraded_stages.append("find_unbalanced_quotes")

    watch_regression: list[dict] = []
    try:
        watch_regression = find_watch_regression(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_watch_regression 失败: %s", e)
        degraded = True
        degraded_stages.append("find_watch_regression")

    # 方案A任务8:整章 AI 味定档聚合,fail-soft(异常时不给该字段,记 degraded,不 500)。
    # 计划A尾巾(A8-Important):dup_lines/emotion_telling/parallelism/poetic_fragments
    # 上面已经算过一遍,precomputed 传进去复用,避免 aggregate_ai_grade 内部对同一份
    # req.prose 重新跑一遍这四个检测器。
    ai_grade = None
    try:
        from scribe3.critique import aggregate_ai_grade
        # P0门审查 P1-5:降级的输入检测器不得以空列表冒充结果喂 precomputed——
        # 假零会让 Gate 判不出 heavy(blocking 判据③被掏空)。缺谁让 aggregate 自己
        # 重算谁;重算仍挂会落本 except 记 aggregate_ai_grade 降级(pass 门关键 stage)。
        _pre: dict = {}
        if "find_duplicate_lines" not in degraded_stages:
            _pre["duplicate_lines"] = dup_lines
        if "find_emotion_telling" not in degraded_stages:
            _pre["emotion_telling"] = emotion_telling
        if "find_parallelism" not in degraded_stages:
            _pre["parallelism"] = parallelism
        if "find_poetic_fragments" not in degraded_stages:
            _pre["poetic_fragments"] = poetic_fragments
        ai_grade = aggregate_ai_grade(qf, req.prose, precomputed=_pre,
                                      short_mode=req.short_mode)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check aggregate_ai_grade 失败: %s", e)
        degraded = True
        degraded_stages.append("aggregate_ai_grade")

    # 方案A任务9(计划A最后一项):标点归一建议(report-only,不改写正文),fail-soft。
    punct_suggestions: list[dict] = []
    try:
        from scribe3.critique import normalize_punctuation_suggestions
        punct_suggestions = normalize_punctuation_suggestions(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check normalize_punctuation_suggestions 失败: %s", e)
        degraded = True
        degraded_stages.append("normalize_punctuation_suggestions")

    # 批次三:时间线第一刀(季节冲突/时辰倒流/同章同主体双地),report-only——
    # 只进 advisory 通道(不设 meta.severity),永不 blocking;fail-soft 且不记
    # degraded(不在 _PASS_CRITICAL_STAGES,时间线没查成不动摇 pass 门)。
    try:
        from scribe3.critique import find_intra_chapter_time_conflicts
        for tc in find_intra_chapter_time_conflicts(req.prose):
            issues.append({"type": "timeline", "message": tc["note"], "text": tc["phrase"],
                           "range": tc["range"], "meta": {"kind": tc["kind"]}})
        for hint in st.validate_event_colocation(seq):
            issues.append({"type": "timeline", "message": hint["note"], "text": "",
                           "range": None, "meta": {"kind": "event_colocation",
                                                   "subject": hint["subject"]}})
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check timeline 检测失败(忽略): %s", e)

    # 方案B任务20:finding-merge 纪律——同位置"机械替换"(punct_suggestions)让位
    # "按功能改写"(issues),并给 degeneration issue 绑定 fix_action=regenerate
    # (回炉重打,不是改写)。fail-soft:异常时保留合并前的原始值,记 degraded_stages。
    try:
        from scribe3.critique import merge_findings
        issues, punct_suggestions = merge_findings(issues, punct_suggestions)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check merge_findings 失败: %s", e)
        degraded = True
        degraded_stages.append("merge_findings")

    # 北极星任务6:目的合同写后验收段(蓝图 §3-④)——结构类查库零噪声;认知类
    # LLM 三值判定(FABLES:supported 须逐字引文),只进面板与 advisory,永不进
    # blocking(宪法)。/post-check 是 read-only:此处只验收不落库,结算(settle)
    # 挂 loop pass finalize 与 /ingest 成功路径。fail-soft。
    fulfillment: dict = {"status": "not_available", "items": []}
    try:
        from scribe3.purpose import (check_fulfillment_structural,
                                     judge_knowledge_delta, parse_deltas)
        _pc_ds = parse_deltas((st.get_chapter(seq) or {}).get("deltas"))
        if _pc_ds:
            _items = check_fulfillment_structural(st, seq, _pc_ds)
            _kn_fn = _complete_fn
            if _kn_fn is None:
                from scribe3.llm import hermes_complete as _kn_fn
            for _it in _items:
                if (_it["kind"] == "knowledge" and _it["verdict"] == "not_checkable"
                        and _it.get("status") not in ("achieved", "waived")):
                    _j = judge_knowledge_delta(req.prose, _it, _kn_fn)
                    _it["verdict"] = _j["verdict"]
                    if _j.get("evidence"):
                        _it["evidence"] = _j["evidence"]
            fulfillment = {"status": "active", "items": _items,
                           "achieved": sum(1 for i in _items
                                           if i["verdict"] in ("achieved", "supported")),
                           "total": len(_items)}
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check fulfillment 失败(fail-soft): %s", e)
        degraded = True
        degraded_stages.append("fulfillment")

    from scribe3.critique import _degen_visible_length
    _visible_chars = _degen_visible_length(req.prose or "")
    resp = {
        "quality": {**qc_breakdown, "total": qc_total},
        "leaks": leaks,
        "leaks_degraded": leaks_degraded,
        "fulfillment": fulfillment,
        "s1_circuit_open": _s1_circuit_open(work),   # 1-A 熔断状态对调用方可见
        "visible_chars": _visible_chars,   # 2-B:A5 口径可见字数,triage 短文本降档判据源
        "discipline": discipline,
        "degraded": degraded,
        "degraded_stages": degraded_stages,
        "inherited_open_promises": inherited_open_promises,
        "setting": setting,
        "issues": issues,
        "duplicate_lines": dup_lines,
        "emotion_telling": emotion_telling,
        "cross_consistency": cross_consistency,
        "tension_monotony": tension_monotony,
        "orphan_edges": orphan_edges,
        "parallelism": parallelism,
        "poetic_fragments": poetic_fragments,
        "unbalanced_quotes": unbalanced_quotes,
        "watch_regression": watch_regression,
        "punct_suggestions": punct_suggestions,
    }
    if ai_grade is not None:
        resp["ai_grade"] = ai_grade
    return resp


class DraftCheckReq(BaseModel):
    prose: str
    focalizer: str = ""


@app.post("/draft-check")
def draft_check(req: DraftCheckReq, seq: int = 0, work: str = "main"):
    """块四b(§5.4):草稿阶段轻量确定性分析。对**任意草稿文本**跑确定性检测器
    (quality_flags 五类 + 整行复读 + 排比 + 情感直说)+ 限知泄露预览(可选,只读)。
    与 /post-check 共用同一批确定性聚合,但入参是草稿文本、**不读章、不写库**:
    绝不跑 LLM ingest、绝不写 proposition/knows/台账/任何库——纯计算 + 只读预览。
    注册为 read-only POST(见 KNOWN_REST_WRITE_ROUTES)。各检测器 fail-soft。"""
    import logging
    from scribe3.critique import (quality_flags, find_duplicate_lines,
                                  find_parallelism, find_emotion_telling)
    degraded_stages: list[str] = []

    # Minor:quality_flags 也 fail-soft(与其余检测器一致)——抛错时降级归零而非整个端点 500。
    try:
        qf = quality_flags(req.prose)
        quality = {
            "repetition": len(qf["repetition"]),
            "structural": len(qf["structural"]),
            "purple": len(qf["purple"]),
            "ai_tics": len(qf["ai_tics"]),
            "oversaturation": len(qf["oversaturation"]),
        }
        quality["total"] = sum(quality.values())
    except Exception as e:
        logging.getLogger("scribe3").warning("draft_check quality_flags 失败: %s", e)
        degraded_stages.append("quality_flags")
        quality = {"repetition": 0, "structural": 0, "purple": 0,
                   "ai_tics": 0, "oversaturation": 0, "total": 0}

    dup_lines: list[dict] = []
    try:
        dup_lines = find_duplicate_lines(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("draft_check find_duplicate_lines 失败: %s", e)
        degraded_stages.append("find_duplicate_lines")

    parallelism: list[dict] = []
    try:
        parallelism = find_parallelism(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("draft_check find_parallelism 失败: %s", e)
        degraded_stages.append("find_parallelism")

    emotion_telling: list[dict] = []
    try:
        emotion_telling = find_emotion_telling(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("draft_check find_emotion_telling 失败: %s", e)
        degraded_stages.append("find_emotion_telling")

    # 限知泄露预览:仅当给了 focalizer 才碰 store,且只 READ(find_leaks 只读 load_knowledge,
    # 不写任何边/命题)。无 focalizer → 完全不接触 store,零库交互。fail-soft。
    leaks: list[dict] = []
    leaks_degraded = False
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            st = _store_for(work)
            leaks = [{"fact_id": lk.fact_id, "marker": lk.marker, "subject": lk.subject,
                      "range": list(lk.range) if lk.range else None}
                     for lk in find_leaks(req.prose, st, req.focalizer, seq)]
        except Exception as e:
            logging.getLogger("scribe3").warning("draft_check find_leaks 失败: %s", e)
            leaks_degraded = True
            degraded_stages.append("find_leaks")

    return {
        "quality": quality,
        "duplicate_lines": dup_lines,
        "parallelism": parallelism,
        "emotion_telling": emotion_telling,
        "leaks": leaks,
        "leaks_degraded": leaks_degraded,
        "degraded_stages": degraded_stages,
    }


@app.post("/checkpoint")
def checkpoint(req: CheckpointReq, seq: int, background: BackgroundTasks, work: str = "main"):
    st = _store_for(work)
    vid = st.add_chapter_version(seq, req.prose, label=req.label,
                                 kind=req.kind, qc=req.qc)
    # kind=final → 这是正式定稿,知识图谱应同步更新(非 final 的草稿快照不 ingest)。
    # P0-1:走去重排队——"存为正文"里 save-chapter 已排的同章 ingest 仍在途时,这里跳过,
    # 不重复排(checkpoint 的职责是落 final 版本;ingest 由 save-chapter 负责)。
    # checkpoint 单独触达(无前置 save-chapter)时仍会正常排入,不丢 ingest。
    if req.kind == "final":
        _enqueue_ingest(background, work, seq)
    return {"status": "saved", "id": vid, "seq": seq, "kind": req.kind}


def _prose_stats(prose: str) -> dict:
    """轻量正文统计:{words, avg_sentence, dialog_count}。纯确定性,不打 LLM。
    - words:去空白字符数(同 save_chapter 的字数口径)。
    - avg_sentence:按句末标点切句的平均句长(字符)。
    - dialog_count:含引号的行/句计为对白(粗略,够前端展示)。"""
    import re
    words = len("".join((prose or "").split()))
    sentences = [s for s in re.split(r"[。！？!?…]+", prose or "") if s.strip()]
    avg_sentence = round(words / len(sentences), 1) if sentences else 0
    dialog_count = len(re.findall(r"[“「『][^”」』]*[”」』]", prose or ""))
    return {"words": words, "avg_sentence": avg_sentence, "dialog_count": dialog_count}


class SaveDraftReq(BaseModel):
    prose: str
    summary: str = ""


@app.post("/save-draft")
def save_draft(req: SaveDraftReq, seq: int, work: str = "main"):
    """存草稿(四阶段·写手期):写 chapter.draft + 追加 chapter_version(stage='draft')。
    刷新恢复读最新 draft(chapter.draft 是最新草稿;版本是历史采用点)。返回新版本 id。"""
    st = _store_for(work)
    st.save_chapter_draft(seq, req.prose)
    stats = _prose_stats(req.prose)
    # kind 限于 ['checkpoint','final'](038 枚举校验);草稿/正文语义走新轴 stage,kind 保持 checkpoint。
    vid = st.add_chapter_version(seq, req.prose, label="", kind="checkpoint",
                                 stage="draft", summary=req.summary, stats=stats)
    return {"status": "saved", "id": vid, "seq": seq, "stage": "draft", "stats": stats}


@app.get("/latest-draft")
def latest_draft(seq: int, work: str = "main"):
    """取该章最新 draft 版(prose+stats),供刷新恢复。无 draft 版返回空对象 {}。"""
    v = _store_for(work).latest_draft_version(seq)
    if not v:
        return {}
    import json
    raw = v.get("stats")
    try:
        v["stats"] = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        v["stats"] = {}
    return v


@app.get("/chapter-versions")
def chapter_versions(seq: int, work: str = "main"):
    return _store_for(work).list_chapter_versions(seq)


@app.get("/chapter-version/{vid}")
def chapter_version(vid: str, work: str = "main"):
    v = _store_for(work).get_chapter_version(vid)
    if not v:
        raise HTTPException(status_code=404, detail="version not found")
    return v


@app.post("/ingest")
def ingest(seq: int, work: str = "main"):
    """手动反哺设定库(前端"反哺设定库"按钮),同步跑 ingest_chapter。
    P0-1 收尾:纳入 _pending_ingest 去重护栏——与后台 _bg_ingest/_enqueue_ingest
    共用同一 (work,seq) 在途集合。同章已有 ingest 在途(后台自动或另一次手点)时拒 409,
    防手点反哺撞自动 ingest 交错造成 knows/reader_knows/char_state/motif_instance/
    promise_touch 双份或互删。自身执行期间也占位在途,故并发 _enqueue_ingest 同章会被跳过;
    完成/异常均在 finally 清标记(避免该章永久锁死)。"""
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    key = (work, seq)
    with _pending_ingest_lock:
        if key in _pending_ingest:
            raise HTTPException(status_code=409, detail="该章正在反哺中,请稍候再试")
        _pending_ingest.add(key)
    try:
        st = _store_for(work)
        r = ingest_chapter(st, seq, hermes_complete)
        if not r.get("parse_failed"):
            # 北极星任务6:手动链路结构类结算(认知类留面板人工;loop 链有完整结算)。
            # settle 在 scorecard 刷新之前——刷新要读结算后的 deltas 状态。
            try:
                from scribe3.purpose import (check_fulfillment_structural,
                                             parse_deltas, settle_purpose)
                _ds = parse_deltas((st.get_chapter(seq) or {}).get("deltas"))
                if _ds:
                    settle_purpose(st, seq, check_fulfillment_structural(st, seq, _ds))
            except Exception as e:
                logging.getLogger("scribe3").warning("/ingest 目的合同结算失败(忽略): %s", e)
            _refresh_scorecard_after_ingest(st, seq)   # P2-3:主链路 ingest 后哨兵转真值
        # 北极星任务8:章后复盘蒸馏(事件驱动挂 ingest 路径,蓝图定死不走 cron)——
        # 与知识抽取成败无关(对话的方法教训独立于 parse_failed);fail-soft 绝不拖垮 ingest。
        try:
            from scribe3.lesson import distill_chapter
            _dfn = _complete_fn
            if _dfn is None:
                from scribe3.llm import hermes_complete as _dfn
            distill_chapter(st, seq, _dfn)
        except Exception as e:
            logging.getLogger("scribe3").warning("/ingest 复盘蒸馏失败(忽略): %s", e)
        return r
    finally:
        with _pending_ingest_lock:
            _pending_ingest.discard(key)


class ImportChapterItem(BaseModel):
    seq: int
    prose: str


class ImportReq(BaseModel):
    chapters: list[ImportChapterItem]


def _import_journal_path(work: str):
    """story-import 断点续跑 journal 文件路径(方案B任务24)。
    取舍记录:scribe3 一书一 DB(SurrealDB),没有天然的"该书的磁盘目录"可挂 journal——
    另起一套按书的文件系统目录纯为 journal 服务不值当。journal 的语义本就是"短生命周期的
    崩溃恢复提示"(见 pipeline_journal.py docstring),故落在系统临时目录、按 work 名隔离
    即可;可用 SCRIBE3_IMPORT_JOURNAL_DIR 环境变量覆盖(测试用它指到 tmp_path,避免与其他
    测试/其他 work 撞车)。"""
    import tempfile
    from pathlib import Path
    base = Path(os.environ.get("SCRIBE3_IMPORT_JOURNAL_DIR") or tempfile.gettempdir())
    return base / f"scribe3_import_{work}.json"


@app.post("/import")
def story_import(req: ImportReq, work: str = "main"):
    """story-import 逆向导入(方案B任务24,P3 战略):作者贴已发布章节 → 逐章复用现有单章
    逆向内核 ingest_chapter 反推知识账本(角色关系/伏笔触及/弧光/事件),免人工重建 bible
    即可从下一章无缝续写。

    ①逐章按 seq 升序存正文(save_chapter)+ 走 ingest_chapter(grep-back 自检已内置在
      ingest_chapter 里,自动生效,这里不重复做)。
    ②用 PipelineJournal(见 pipeline_journal.py)包裹每章:stage=f"import_ch{seq}",
      journal 文件路径见 _import_journal_path;should_skip 使已完成章在进程崩溃重启/
      重复调用本端点时被跳过,故本端点整体幂等可重入。
    ③crash-safe 取舍:某章 ingest 失败(抛异常或 parse_failed)不会"跳过继续下一章"——
      按 journal 协议,一个 Stage 中途失败视为整体没跑通,不 complete_stage,立即中止
      循环。响应选 200 + error 字段而非 4xx:失败时已完成的 imported/skipped/resume_from
      仍是调用方需要的有效进度信息,4xx 容易被调用方整体丢弃响应体,丢失这份进度。
    ④五锚逆向(build_reverse_anchor_prompt/parse_reverse_anchors,ingest.py)刻意不在这里
      接线——对每个主要角色同步串行调一次 LLM 会显著拖慢本端点,留作 import 完成后的
      可选异步步骤(TODO:后续任务按 delta 里出现过的角色排队后台调用)。
    ⑤Minor(收尾清理批):正文 save_chapter 先于知识抽取(ingest_chapter)落库,
      失败重跑会覆写该章正文(幂等覆盖)——journal 保护的是"跳过已完成章",
      不是"正文不被重写"。
    """
    from scribe3.ingest import ingest_chapter
    from scribe3.pipeline_journal import PipelineJournal

    st = _store_for(work)
    complete_fn = _complete_fn
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete

    journal = PipelineJournal(_import_journal_path(work))
    chapters = sorted(req.chapters, key=lambda c: c.seq)

    def _open_promises():
        return [p for p in st.promises_with_lifecycle() if p["status"] == "open"]

    imported = 0
    skipped = 0
    annotated_total = 0
    max_seq = 0
    for item in chapters:
        stage = f"import_ch{item.seq}"
        if journal.should_skip(stage):
            skipped += 1
            max_seq = max(max_seq, item.seq)
            continue
        journal.start_stage(stage)
        st.save_chapter(item.seq, item.prose)
        try:
            result = ingest_chapter(st, item.seq, complete_fn)
        except Exception as e:
            # 中途崩溃:journal 保持 in_progress=stage,不 complete——下次重跑本端点会
            # 从这一章重新整章跑(should_skip 对未 complete 的 stage 恒返回 False)。
            return {"imported": imported, "skipped": skipped, "resume_from": item.seq,
                    "open_promises": _open_promises(), "annotated_total": annotated_total,
                    "error": f"第 {item.seq} 章 ingest 抛异常,已中止:{e}"}
        if result.get("parse_failed"):
            return {"imported": imported, "skipped": skipped, "resume_from": item.seq,
                    "open_promises": _open_promises(), "annotated_total": annotated_total,
                    "error": f"第 {item.seq} 章知识抽取解析失败(parse_failed),已中止"}
        journal.complete_stage(stage)
        imported += 1
        annotated_total += len(result.get("annotated") or [])
        max_seq = max(max_seq, item.seq)

    return {"imported": imported, "skipped": skipped, "resume_from": max_seq + 1,
            "open_promises": _open_promises(), "annotated_total": annotated_total}


@app.get("/ingest-unverified")
def ingest_unverified(status: str = "pending", work: str = "main"):
    return _store_for(work).list_unverified(status)


@app.post("/ingest-unverified/{uid}/accept")
def accept_unverified_ep(uid: str, work: str = "main"):
    from scribe3.llm import hermes_complete
    return _store_for(work).accept_unverified(uid, complete_fn=hermes_complete)


@app.post("/ingest-unverified/{uid}/ignore")
def ignore_unverified_ep(uid: str, work: str = "main"):
    _store_for(work).ignore_unverified(uid)
    return {"ok": True}


@app.post("/ingest-unverified/ignore-all")
def ignore_all_unverified_ep(status: str = "pending", work: str = "main"):
    """R2-12:批量忽略——unverified 死水(产生速率≫消化)一键清账,防账本失信号价值。
    只清指定 status(默认 pending);accepted/ignored 的决策存活是设计。"""
    st = _store_for(work)
    n = 0
    for r in st.list_unverified(status):
        try:
            st.ignore_unverified(r.get("id"))
            n += 1
        except Exception:
            pass
    return {"ignored": n}


@app.get("/north-star/chapter/{seq}")
def north_star_chapter(seq: int, work: str = "main"):
    """章级北极星 scorecard(北极星任务3,蓝图 §3-③):constraints(硬约束偏离)/
    advisory_scores(软参考)/fulfillment(正向达成,任务6 前占位)三分栏。
    不合成总分(宪法条款);loop 编排(任务4)只读 constraints。
    缓存缺失时 store 侧 lazy 现算回填;章不存在/无正文 → 404。"""
    sc = _store_for(work).get_chapter_scorecard(seq)
    if sc is None:
        raise HTTPException(status_code=404, detail=f"chapter {seq} 不存在或无正文")
    return sc


@app.get("/audit/blind-pack")
def audit_blind_pack(work: str = "main", sample_n: int = 2, seed: int = 0,
                     per_volume: int | None = None):
    """盲评包导出(北极星任务13,秘密审计制度——防 Goodhart 的流程性防护):
    池A=被自动 regenerate 的章(loop journal 含 *_verdict_blocking,附第0稿并排、
    随机左右序,审「重写后真的更好吗」);池B=随机抽样章(seed 可复现)。
    sample_n 是**全书总抽样数**(P2门审查 P2-4:旧名 per_volume 语义失实,制度 doc
    的"每卷 2-3 章"由作者按卷分次导出或 sample_n=卷数×2 执行;旧参名兼容保留)。
    样本用盲号(不含章号;池A样本带双稿形态,天然暴露"回炉过"池别——制度 doc 已
    明示此偏离)。key 补 regen_rounds(回炉轮数,journal 计)。结论只供人读,
    **永不接入任何自动收敛判据**(宪法级);read-only 端点。"""
    if per_volume is not None:
        sample_n = per_volume
    import glob as _glob
    import json as _json
    import random
    import re as _re_mod
    _re_audit = _re_mod.compile(r"_a(\d+)_")
    st = _store_for(work)
    base = (os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR")
            or os.path.expanduser("~/.scribe3-loop-journals"))
    pool_a: set[int] = set()
    pool_a2: set[int] = set()   # 2-A:needs_human 章(三稿全拦)——检测器假阳性富矿
    regen_rounds: dict[int, int] = {}   # P2门审查 P2-4:key 补回炉轮数(制度 doc 承诺)
    blocking_dist: dict[int, dict] = {}   # 2-A:拦截原因分布(detector 计数,来自 .result.json)
    for fp in _glob.glob(os.path.join(base, work, "loop_ch*.json")):
        try:
            with open(fp, encoding="utf-8") as _fh:
                data = _json.loads(_fh.read())
            stages = data.get("stages_completed") or []
            seq_a = int(os.path.basename(fp).split("_")[1][2:])
            if any("_needs_human" in s for s in stages):
                pool_a2.add(seq_a)
            elif any("_verdict_blocking" in s for s in stages):
                pool_a.add(seq_a)
            else:
                continue
            attempts = [int(m.group(1)) for s in stages
                        for m in [_re_audit.search(s)] if m]
            regen_rounds[seq_a] = max(regen_rounds.get(seq_a, 0), max(attempts, default=0))
            try:   # 1-C#2 的旁文件有则读 detector 分布(旧 journal 没有,None 即如实)
                with open(fp + ".result.json", encoding="utf-8") as _fh2:
                    rj = _json.loads(_fh2.read())
                _cnt: dict[str, int] = {}
                for _r0 in rj.get("rounds") or []:
                    for _b in _r0.get("blocking") or []:
                        _d = str(_b.get("detector") or "?")
                        _cnt[_d] = _cnt.get(_d, 0) + 1
                if _cnt:
                    blocking_dist[seq_a] = _cnt
            except Exception:
                pass
        except Exception:
            continue
    pool_a -= pool_a2   # 同章多 journal 时 needs_human 语义优先(A 的"重写后过审"对照不成立)
    chapters = [c["seq"] for c in st.list_chapters()]
    rng = random.Random(seed)
    rest = [c for c in chapters if c not in pool_a and c not in pool_a2]
    pool_b = sorted(rng.sample(rest, min(sample_n, len(rest)))) if rest else []
    # 池A2 不要求章已落库正文(needs_human 章 prose 不落库,三稿在版本库)
    picked = ([("A", s) for s in sorted(pool_a) if s in chapters]
              + [("A2", s) for s in sorted(pool_a2)]
              + [("B", s) for s in pool_b])
    rng.shuffle(picked)
    samples, key = [], {}
    for i, (pool, seq) in enumerate(picked):
        blind_id = f"S{seed}-{i + 1:02d}"
        ch = st.get_chapter(seq) or {}
        item = {"blind_id": blind_id, "prose": ch.get("prose") or "",
                "questions": ["张力:想继续读下一章吗(1-5)?",
                              "声音:遮住人名还认得出这本书吗(1-5)?",
                              "记忆点:24 小时后还记得哪个画面?",
                              "违和:有没有机器味/被打磨过头的段落(引原文)?"]}
        if pool == "A":
            vers = [v for v in (st.list_chapter_versions(seq) or [])
                    if "loop第0稿" in (v.get("label") or "")]
            if vers:
                raw = (st.get_chapter_version(vers[0]["id"]) or {}).get("prose") or ""
                pair = [item["prose"], raw]
                rng.shuffle(pair)   # 随机左右序防位置偏置(Arena 先例)
                item["pair"] = [{"tag": f"稿{'甲乙'[k]}", "prose": p}
                                for k, p in enumerate(pair)]
                item["pair_question"] = "两稿哪份更好?自动重写是否磨掉了好东西?"
                item.pop("prose")
        elif pool == "A2":
            # 2-A:needs_human 章三稿并排(正文未落库,稿全在版本库 loop第N稿)。
            # 按轮次序不随机——A2 审的是「检测器拦得对不对」,轮次演进本身是证据
            # (自定口径,记 D-025);位置偏置防护留给池A的优劣对比场景。
            # 版本库可能存多轮 loop 的稿(label 无 run id);list_chapter_versions 新→旧,
            # 顺扫遇到重复 attempt 号即越过组边界——只取最新一组(needs_human 那次)。
            _re_draft_n = _re_mod.compile(r"loop第(\d+)稿")
            _cand, _seen_n = [], set()
            for v in (st.list_chapter_versions(seq) or []):
                _m = _re_draft_n.search(v.get("label") or "")
                if not _m:
                    continue
                _n = int(_m.group(1))
                if _n in _seen_n:
                    break
                _seen_n.add(_n)
                _cand.append((_n, v))
            _cand.sort(key=lambda t: t[0])
            item["triple"] = [
                {"tag": f"第{n}稿",
                 "prose": (st.get_chapter_version(v["id"]) or {}).get("prose") or ""}
                for n, v in _cand]
            item["triple_question"] = ("这几稿真的都不行吗?有可用稿即说明检测器过严,"
                                       "引原文说明哪一稿哪一段其实成立。")
            item.pop("prose")   # needs_human 正文未落库,不出空 prose 误导评审
        samples.append(item)
        try:
            sc = st.get_chapter_scorecard(seq) or {}
        except Exception:
            sc = {}
        key[blind_id] = {"chapter": seq, "pool": pool,
                         "regen_rounds": regen_rounds.get(seq),
                         "blocking_dist": blocking_dist.get(seq),   # 2-A:拦截原因分布
                         "ai_grade": ((sc.get("advisory_scores") or {}).get("ai_grade")
                                      or {}).get("grade"),
                         "constraints": sc.get("constraints")}
    return {"samples": samples, "key": key,
            "note": "评审时勿看 key;结论写人工文档,永不接入任何自动收敛判据(宪法)"}


class SelectChapterReq(BaseModel):
    chapter: int
    force: bool = False       # 非关键章硬要出候选(作者主权;默认拦,N 倍成本只花刀刃)
    msg: str = ""             # 可选驱动语补充


@app.post("/select/chapter")
def select_chapter(req: SelectChapterReq, work: str = "main"):
    """选择环(北极星任务11,蓝图 §4-①):关键章同一合同出 3 个策略多样候选 →
    确定性过滤(triage blocking 杀)→ rubric 全循环赛只排序(无共识则不排)→
    候选留版本,响应供对比页,终选走 /select/finalize(人)。
    关键章判定:chapter_role∈{高压,关系回收} 或含 reversal_type(节拍标注,
    parse_chapter_meta);非关键章 422(force=true 可越过)。同章互斥 409。"""
    from scribe3.brief import chapter_draft_text, parse_chapter_meta
    from scribe3.pipeline_journal import PipelineJournal
    from scribe3.qd import chapter_style_profile
    from scribe3.selection import STRATEGIES, is_key_chapter, run_selection
    st = _store_for(work)
    ch = st.get_chapter(req.chapter)
    if not ch:
        raise HTTPException(status_code=404, detail=f"chapter {req.chapter} 不存在")
    _draft_txt = chapter_draft_text(ch)
    meta = parse_chapter_meta(_draft_txt) or {}
    # reversal_type 不在 parse_chapter_meta 输出里(它只抓压力级/role)——
    # 关键章判定的反转分支从草料文本直接正则(方案B任务13b 的标注规范同源)。
    import re as _re
    _rev = _re.search(r"reversal_type\s*[::]\s*(\S+)", _draft_txt)
    if _rev:
        meta["reversal_type"] = _rev.group(1)
    if not is_key_chapter(meta) and not req.force:
        raise HTTPException(status_code=422, detail=(
            "非关键章不触发选择环(N 倍成本只花刀刃):节拍标注 chapter_role 为 高压/关系回收 "
            "或标注 reversal_type 后再试;确要出候选传 force=true"))
    _guard_pilot_busy(work, req.chapter)   # D1:pilot 非 loop 步在途/连写中不出候选(防互踩,同终选 R2-3)
    # B4:选择环单次 ~10 发 LLM,启动前预检剩余日帽——撞帽半途炸不如提前如实拦
    from scribe3.llm import daily_remaining
    _sel_est = 10
    if daily_remaining() < _sel_est:
        raise HTTPException(status_code=429, detail=(
            f"LLM 日帽剩余不足:选择环约需 {_sel_est} 发,当前剩 {daily_remaining()} 发。"
            f"次日 0 点重置,或调大 SCRIBE3_DAILY_CALL_CAP"))
    _skey = (work, req.chapter)
    with _loop_inflight_lock:   # 与修复环共用同章互斥(同章不得同时 loop 与选择)
        if _skey in _loop_inflight:
            raise HTTPException(status_code=409, detail=f"chapter {req.chapter} 已有生成在途")
        _loop_inflight.add(_skey)
    # P2门审查 P2-1:journal 构造放锁后 try 内(构造抛异常曾致锁永不释放、该章全 409);
    # 且只替换**文件名**(str.replace 全路径会把含 loop_ch 的目录段也改写)。
    try:
        jp = _loop_journal_path(work, req.chapter)
        jp = jp.with_name(jp.name.replace("loop_ch", "select_ch", 1))
        journal = PipelineJournal(jp)
    except Exception:
        with _loop_inflight_lock:
            _loop_inflight.discard(_skey)
        raise

    def _generate(strategy: dict) -> str:
        instructions = _assemble_write_instructions(
            st, chapter=req.chapter, focalizer=ch.get("focalizer") or "", phase="final",
            seed_words=[], short_mode=False, with_tools=False, work=work)   # 候选生成不挂工具(纯写作)
        instructions += "\n\n【选择环候选策略(本候选必须执行)】" + strategy["directive"]
        msg = ((req.msg + "\n") if req.msg else "") + (
            f"写第 {req.chapter} 章完整正文,严格执行上面的候选策略,"
            f"用 ⟦PROPOSAL scope=chapter⟧ 围栏交稿。")
        text, proposals = _collect_write(msg, instructions, with_tools=False)
        chapter_props = [p for p in proposals if p.get("scope") == "chapter"]
        if chapter_props:
            return chapter_props[-1]["prose"]
        body = _strip_preamble(text)
        if len(body.strip()) >= _FALLBACK_MIN_CHARS:
            return body
        # B2:业务层不抛 HTTPException(HTTP 语义应留给端点层)——抛普通异常,由 run_selection
        # 的 B1 容错捕获成"该候选生成失败"跳过,不污染 HTTP 语义、不拖垮其余候选。
        raise RuntimeError(f"策略 {strategy['key']} 未产出合格章稿(无围栏且散文不足)")

    def _post_check(prose: str) -> dict:
        return post_check(PostCheckReq(prose=prose, focalizer=ch.get("focalizer") or ""),
                          seq=req.chapter, work=work)

    def _persist(prose: str, strategy_key: str) -> str:
        # kind 枚举 DB 级 ASSERT 仅 checkpoint/final(migration 先例)——候选语义由
        # label 前缀「选择环候选·」承载,免改已有表 schema(免影子库演练,D-019 附注)。
        # C1(彻查 D-10):候选用独立 stage="candidate",不用 "draft"——否则
        # latest_draft_version(按 stage='draft' 取最新)会把选择环候选当"最新草稿",
        # 污染作者草稿 tab 的「刷新恢复」。version_id 不变,CandidateCard 展开全文不受影响。
        return st.add_chapter_version(req.chapter, prose, kind="checkpoint", stage="candidate",
                                      label=f"选择环候选·{strategy_key}",
                                      stats=_prose_stats(prose))

    def _judge(a: str, b: str) -> str:
        """成对比较(rubric 初筛员,只排序)。LLM 失败 → **恒返回 "A"(先手)**:
        位置对换下同对两方向都判先手 = w1≠w2 矛盾 → round_robin 判 inconsistent →
        consensus=False 交人。P2门审查 P1-1:此前的"交替返回"推理是反的——交替
        ("A","B") 在位置对换下恰好等于两方向一致判先手胜,产出零矛盾的确定性
        **假共识**(已复现);恒定先手才是被双向对换必然识破的降级形态。"""
        prompt = ("两份同一章级合同下的候选章稿,只判哪份更好(贴合同/张力/文风三维综合),"
                  '只输出一个字母 A 或 B。\n'
                  f"【A】\n{a[:2800]}\n【B】\n{b[:2800]}")
        try:
            fn = _complete_fn
            if fn is None:
                from scribe3.llm import hermes_complete as fn
            raw = str(fn(prompt)).strip().upper()
            # P2门审查 P3:取独立的 A/B token(防 "ANSWER" 里的 A 误判)
            import re as _re2
            m = _re2.search(r"(?<![A-Z0-9])([AB])(?![A-Z0-9])", raw)
            if m:
                return m.group(1)
        except Exception as e:
            logging.getLogger("scribe3").warning("selection judge 失败(降级为无共识): %s", e)
        return "A"

    def _save_result(res: dict) -> None:
        """P2门审查 P2-3:结果元数据落 journal 旁文件——同步长请求断连/切章后,
        候选的 filtered/rank/profile 不再只活在一次 HTTP 响应里(prose 本就在版本库)。"""
        import json as _j2
        try:
            with open(str(jp) + ".result.json", "w", encoding="utf-8") as f:
                _j2.dump(res, f, ensure_ascii=False)
        except Exception as e:
            logging.getLogger("scribe3").warning("selection 结果落盘失败(忽略): %s", e)

    try:
        result = run_selection(chapter=req.chapter, generate=_generate,
                               post_check=_post_check, persist_candidate=_persist,
                               profile_fn=chapter_style_profile, judge_fn=_judge,
                               journal=journal, save_result=_save_result)
    finally:
        with _loop_inflight_lock:
            _loop_inflight.discard(_skey)
    result["journal_path"] = str(jp)
    result["key_chapter"] = is_key_chapter(meta)
    return result


class SelectFinalizeReq(BaseModel):
    chapter: int
    version_id: str
    reason_axis: str = "其他"
    reason_text: str


@app.post("/select/finalize")
def select_finalize(req: SelectFinalizeReq, background: BackgroundTasks, work: str = "main"):
    """选择环终选(人):选中候选落正文 + 留 final 版 + **终选理由入 lesson 流**
    (蓝图:理由是沉淀环最贵的输入;强制一句,轴+自由文本双格式)。"""
    if not (req.reason_text or "").strip():
        raise HTTPException(status_code=422, detail="终选必须留一句理由(入 lesson 流)")
    # P2门审查 P1-3:同章 loop/选择在途时禁止终选——否则 loop pass 的 save+ingest
    # 与终选落库互踩(正文与知识表错位)。检查即可,不持锁。
    with _loop_inflight_lock:
        if (work, req.chapter) in _loop_inflight:
            raise HTTPException(status_code=409,
                                detail=f"chapter {req.chapter} 有生成在途,完成后再终选")
    _guard_pilot_busy(work, req.chapter)   # R2-3:pilot 非 loop 步在途/连写中也拦
    st = _store_for(work)
    ver = st.get_chapter_version(req.version_id)
    if not ver or ver.get("seq") != req.chapter:
        raise HTTPException(status_code=404, detail="候选版本不存在或不属于该章")
    prose = ver.get("prose") or ""
    title = (st.get_chapter(req.chapter) or {}).get("title") or ""
    foc = (st.get_chapter(req.chapter) or {}).get("focalizer")
    st.save_chapter(req.chapter, prose, title=title, focalizer=foc)
    _enqueue_ingest(background, work, req.chapter)   # C3(D-13):终选定稿反哺知识账本(去重后台),不再停在旧稿
    try:
        st.add_chapter_version(req.chapter, prose, label=f"终选定稿·{ver.get('label') or ''}",
                               kind="final", stage="final", stats=_prose_stats(prose))
    except Exception as e:
        logging.getLogger("scribe3").warning("终选留 final 版失败(正文已落库): %s", e)
    try:
        st.add_lesson(req.chapter, "decision",
                      f"第{req.chapter}章关键章终选胜在{(req.reason_axis or '其他')[:12]}:"
                      f"{req.reason_text.strip()[:160]}",
                      condition="关键章多候选终选")
    except Exception as e:
        logging.getLogger("scribe3").warning("终选理由入 lesson 失败(定稿不受影响): %s", e)
    return {"status": "finalized", "chapter": req.chapter, "version_id": req.version_id,
            "note": "正文已落库;已排后台反哺(ingest)更新知识账本"}


# ═══════════ Chapter Pilot(主编主动化 T6/T7/T10):章生命周期驱动器 ═══════════
# 作者=创意总监,主编=执行主编。状态机在 scribe3/pilot.py(纯核可测);此处只做
# executor 绑定(全部复用既有链,禁止新写生成逻辑)+ HTTP 面 + 连写循环。

def _pilot_llm_gen(st, work: str, seq: int, phase: str, ask: str, focalizer: str = "",
                   max_tokens: int | None = 1600) -> str:
    """pilot 生成通道:同一 _assemble_write_instructions 组装链(宪法:不另起简化 prompt)。"""
    from scribe3.llm import hermes_complete
    ins = _assemble_write_instructions(
        st, chapter=seq, focalizer=focalizer, phase=phase,
        with_tools=False, seed_words=[], short_mode=False, work=work)
    return (hermes_complete(ask, system=ins, max_tokens=max_tokens) or "").strip()


def _pilot_steer(st, seq: int) -> str:
    rows = st._query("SELECT pilot_steer FROM type::record('chapter',$seq)", {"seq": seq})
    return ((rows[0] if rows else {}).get("pilot_steer") or "").strip()


def _pilot_journal(work: str, seq: int):
    """审查 P1-5:pilot 审计留痕(每章一份 pilot_ch{n}.json,stage=pilot_ch{n}_{action})。
    fail-soft:journal 建不起来不阻塞编排。"""
    try:
        from scribe3.pipeline_journal import PipelineJournal
        base = (os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR")
                or os.path.expanduser("~/.scribe3-loop-journals"))
        d = os.path.join(base, work)
        os.makedirs(d, exist_ok=True)
        return PipelineJournal(os.path.join(d, f"pilot_ch{seq}.json"))
    except Exception as e:
        logging.getLogger("scribe3").warning("pilot journal 建立失败(忽略): %s", e)
        return None


def _pilot_executor(work: str) -> dict:
    """action → callable(st, seq)。全部落库走 update_chapter_meta 白名单/既有端点函数。"""
    def propose_outline(st, seq):
        ch0 = st.get_chapter(seq) or {}
        if (ch0.get("synopsis") or "").strip():
            # 审查 P1-2:字段已有内容(可能人工编辑)——跳步推进,绝不覆盖;
            # 想重新提案:清空大纲或走未来 revise 通道。
            return {"skipped": "大纲已有内容,按既有推进(不覆盖)"}
        steer = _pilot_steer(st, seq)
        out = _pilot_llm_gen(st, work, seq, "plan",
                             f"给第{seq}章出大纲提案:3-5句,写清这章发生什么、压力级(1-5)、"
                             f"章末钩子。只输出大纲正文。"
                             + (f"\n作者意图(最高优先):{steer}" if steer else ""))
        st.update_chapter_meta(seq, {"synopsis": out})
        return {"synopsis": out}

    def expand_beats(st, seq):
        ch = st.get_chapter(seq) or {}
        if ch.get("beats"):
            return {"skipped": "节拍已有内容,按既有推进(不覆盖)"}
        out = _pilot_llm_gen(st, work, seq, "plan",
                             f"据本章大纲展开节拍:4-7条,每条一行一个动作/转折,"
                             f"不写成正文。只输出节拍行,每行一条。\n大纲:{ch.get('synopsis') or ''}")
        import re as _re_b
        beats = [{"text": _re_b.sub(r"^\s*(?:[-·•]|\d{1,2}[.、])\s*", "", ln).strip()}
                 for ln in out.splitlines() if ln.strip()]
        beats = [b for b in beats if b["text"]][:8]
        st.update_chapter_meta(seq, {"beats": beats})
        return {"beats": beats}

    def deduce(st, seq):
        ch = st.get_chapter(seq) or {}
        have_truth = bool((ch.get("scene_truth") or "").strip())
        have_deds = bool(ch.get("deductions"))
        if have_truth and have_deds:
            return {"skipped": "演绎已有内容,按既有推进(不覆盖)"}
        involved = ch.get("involved_characters") or []
        if not involved:   # 后端版智能预填(同 DeduceTree 前端逻辑):名字出现在大纲/节拍
            text = (ch.get("synopsis") or "") + " " + " ".join(
                (b.get("text") if isinstance(b, dict) else str(b)) or "" for b in ch.get("beats") or [])
            involved = [c.id for c in st.characters() if c.name and c.name in text][:4]
            if involved:
                st.update_chapter_meta(seq, {"involved_characters": involved})
        # R1-2 修复:字段级跳步。旧代码合取守卫(truth AND deductions)在"半有"态判 False →
        # 整体重生成覆盖作者手写;而 scene_truth/deductions 无版本化=覆盖即不可恢复,且作者
        # 手写常是核心创意。故:真相已有则复用不覆盖;投影逐 character_id merge 只补缺失角色。
        if have_truth:
            truth = (ch.get("scene_truth") or "").strip()
        else:
            truth = _pilot_llm_gen(st, work, seq, "deduce",
                                   f"写第{seq}章这一场的「场景真相」:全知冷叙,客观上真正发生了什么,"
                                   f"含角色们察觉不到的隐藏机制。只输出真相正文。")
            st.update_chapter_meta(seq, {"scene_truth": truth})
        existing = {str(d.get("character_id")): d for d in (ch.get("deductions") or [])
                    if isinstance(d, dict) and d.get("character_id")}
        deds = list(ch.get("deductions") or [])
        made = 0
        for cid in involved:
            if str(cid) in existing:
                continue   # 该角色投影已有(可能作者手编)——不覆盖
            name = str(cid).split(":")[-1]
            prose = _pilot_llm_gen(
                st, work, seq, "deduce",
                f"以「{name}」截至第{seq}章的限知,写他这一场的限知投影,分五个小标题:"
                f"看到/听到、知道、以为(误读)、做了/说了、没察觉的;每个小标题用 ### 起行。"
                f"只含他所知所感。", focalizer=str(cid))
            deds.append({"character_id": str(cid), "character_name": name, "prose": prose})
            made += 1
        if made or not have_deds:
            st.update_chapter_meta(seq, {"deductions": deds})
        return {"scene_truth_chars": len(truth), "deductions": len(deds)}

    def draft_loop(st, seq):
        ch = st.get_chapter(seq) or {}
        if (ch.get("prose") or "").strip():
            # 正文已在(pass 落库/作者手动采纳 advisory 稿)→ 跳过生成直接体检
            return {"skipped": "正文已在,跳过生成(advisory 稿手动采纳后走此路)"}
        steer = _pilot_steer(st, seq)
        req = LoopChapterReq(chapter=seq, focalizer=ch.get("focalizer") or "",
                             msg=(f"按简报与演绎写第{seq}章正文。"
                                  + (f"作者意图:{steer}" if steer else "")))
        return loop_chapter(req, work=work)   # 端点函数直调:互斥/journal/回炉/落库全复用

    def full_check(st, seq):
        ch = st.get_chapter(seq) or {}
        prose = (ch.get("prose") or "").strip()
        if not prose:
            return {"pilot_park": "正文为空,无从体检(上游未交稿——若在等 advisory 裁决请先处理)"}
        resp = post_check(PostCheckReq(prose=prose, focalizer=ch.get("focalizer") or ""),
                          seq=seq, work=work)
        # 审查 P1-7:体检结果必须被消费——blocking 停靠,不再"烧一遍然后扔"
        from scribe3.loop import triage
        t = triage(resp)
        if t["verdict"] == "blocking":
            dets = "、".join(sorted({b.get("detector") or "?" for b in t["blocking"]}))
            return {"pilot_park": f"全量体检 blocking({dets}),请处理后继续", "post_check": resp}
        resp["_triage_verdict"] = t["verdict"]
        return resp

    def deliver(st, seq):
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
        if not prose.strip():
            return {"pilot_park": "空正文不可交付(审查 P0-1 独立防御)"}
        # 交付卡:低置信段=主编自审(置信度校准,调研:主动暴露不确定处)
        low_conf = ""
        try:
            low_conf = _pilot_llm_gen(
                st, work, seq, "final",
                f"你刚交付第{seq}章。列出你拿不准的地方(≤3处,每处引原文短语+一句为什么拿不准);"
                f"没有就回「无」。只输出清单。\n正文:\n{prose[:3000]}", max_tokens=400)
        except Exception as e:
            low_conf = f"(自审未跑成:{str(e)[:60]})"
        try:
            st.add_chapter_version(seq, prose, label=f"pilot交付", kind="checkpoint",
                                   stage="final", stats=_prose_stats(prose))
        except Exception as e:
            logging.getLogger("scribe3").warning("pilot 交付留版失败(忽略): %s", e)
        _qrows = st._query("SELECT qc_issues FROM type::record('chapter',$seq)", {"seq": seq})
        _qc = (_qrows[0] if _qrows else {}).get("qc_issues")
        _qn = len(_qc) if isinstance(_qc, list) else (_qc or 0)
        _prom = []
        try:
            for pr in st.promises_with_lifecycle(max_chapter=seq):
                if pr.get("setup_chapter") == seq:
                    _prom.append(f"埋「{(pr.get('text') or '')[:20]}」")
                if pr.get("payoff_chapter") == seq:
                    _prom.append(f"收「{(pr.get('text') or '')[:20]}」")
        except Exception:
            pass
        card = {"seq": seq, "words": len("".join(prose.split())),
                "qc": _qn, "promises": _prom, "low_confidence": low_conf}
        st._execute_write("UPDATE type::record('chapter',$seq) SET pilot_card=$c",
                          {"seq": seq, "c": json.dumps(card, ensure_ascii=False)})
        return {"card": card}

    def finalize(st, seq):
        ch = st.get_chapter(seq) or {}
        prose = ch.get("prose") or ""
        if st.latest_version_prose(seq, "final") != prose:
            st.add_chapter_version(seq, prose, label="pilot终选", kind="final",
                                   stage="final", stats=_prose_stats(prose))
        return {"finalized": True}

    return {"propose_outline": propose_outline, "expand_beats": expand_beats,
            "deduce": deduce, "draft_loop": draft_loop, "full_check": full_check,
            "deliver": deliver, "finalize": finalize}


# pilot 自身并发互斥(独立于 _loop_inflight:draft_loop 直调 loop 端点函数,
# loop 自己会登记 _loop_inflight——pilot 若预登记会撞自己 409)。
_pilot_inflight: set[tuple[str, int]] = set()
_pilot_inflight_lock = threading.Lock()


def _guard_pilot_busy(work: str, seq: int) -> None:
    """R2-3:pilot 非 loop 步在途 / 连写运行中 → 拦 save/dedup/select(防 full_check/deliver
    期间改正文致体检、交付挂旧稿,防双写)。draft_loop 期已由 _loop_inflight 拦(loop 自登记)。"""
    with _pilot_inflight_lock:
        if (work, seq) in _pilot_inflight:
            raise HTTPException(status_code=409, detail=f"第 {seq} 章 pilot 正在推进,请稍候再改")
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中——请先 /pilot/pause 再改本章")


class PilotStepReq(BaseModel):
    seq: int
    mode: str = "manual"     # manual | run(run 由 /pilot/run 循环使用)
    steer: str = ""          # 追加/更新作者意图(写入 pilot_steer)


@app.post("/pilot/step")
def pilot_step(req: PilotStepReq, work: str = "main"):
    """推进一步。approve 级动作(finalize)不在此执行——必须走 /pilot/approve(宪法)。"""
    from scribe3.pilot import NEXT, read_state, step
    st = _store_for(work)
    if not st.get_chapter(req.seq):
        raise HTTPException(status_code=404, detail=f"第 {req.seq} 章不存在(先建章或用 /pilot/run 自动建)")
    if req.steer.strip():
        # P2-8:与 /ideas 一致改追加(覆盖会清掉 Inbox 攒的想法),帽 2000
        _prev_s = _pilot_steer(st, req.seq)
        _merged = ((_prev_s + "\n") if _prev_s else "") + req.steer.strip()
        st._execute_write("UPDATE type::record('chapter',$seq) SET pilot_steer=$s",
                          {"seq": req.seq, "s": _merged[-2000:]})
    cur = read_state(st, req.seq)["state"]
    nxt = NEXT.get(cur)
    if nxt and nxt[0] == "finalize":
        raise HTTPException(status_code=409, detail="终选是宪法级动作:请走 /pilot/approve(作者背书)")
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中(/pilot/pause 先停),防并发双跑")
    _k = (work, req.seq)
    with _pilot_inflight_lock:
        if _k in _pilot_inflight:
            raise HTTPException(status_code=409, detail=f"第 {req.seq} 章 pilot 已在推进")
        _pilot_inflight.add(_k)
    try:
        # R2-9:手动步也传 journal(此前只 approve/run 传,手动步零留痕——生产实锤)
        return step(st, req.seq, _pilot_executor(work), mode=req.mode,
                    journal=_pilot_journal(work, req.seq))
    finally:
        with _pilot_inflight_lock:
            _pilot_inflight.discard(_k)


class IdeaIn(BaseModel):
    text: str


_IDEA_ROUTE_PROMPT = """你是写作系统的想法路由器。作者丢来一句想法,判断它该落到哪:
- outline:关于某未来/当前章"写什么"(剧情走向/场景/事件)→ 给该章定向
- steer:对某章的写法要求(语气/节奏/禁忌,如"别煽情")
- setting:动人物长期设定/世界观(如"老范其实识字""改成三兄妹")
- revise:要改已写好的章的具体内容
- unclear:信息不足,需要问一个澄清问题
只输出 JSON:{"kind":"outline|steer|setting|revise|unclear","target_seq":章号或null,
"note":"一句话复述你的理解","question":"仅 unclear 时给一个澄清问题"}
当前书最新章:{max_ch};作者想法:{text}"""


@app.post("/ideas")
def add_idea(req: IdeaIn, work: str = "main"):
    """想法收件箱(主编主动化 T8):作者唯一的输入负担——丢一句话,主编路由落位。
    宪法:setting 类永不自动动圣经(pending_approval 进决策收件箱);
    outline/steer 落该章 pilot_steer(propose_outline/draft 时最高优先吃它);
    revise 生成定向修订提案进收件箱;unclear 只问一个澄清问题。"""
    import json as _json
    st = _store_for(work)
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="想法不能为空")
    complete_fn = _complete_fn
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    route = {"kind": "unclear", "target_seq": None, "note": "", "question": "能再说具体点吗?"}
    try:
        raw = complete_fn(_IDEA_ROUTE_PROMPT.replace("{max_ch}", str(st.max_chapter()))
                          .replace("{text}", text[:500]))
        import re as _re
        m = _re.search(r"\{.*\}", raw or "", _re.S)
        if m:
            d = _json.loads(m.group(0))
            if d.get("kind") in ("outline", "steer", "setting", "revise", "unclear"):
                route = {"kind": d["kind"],
                         "target_seq": d.get("target_seq"),
                         "note": str(d.get("note") or "")[:200],
                         "question": str(d.get("question") or "")[:200]}
    except Exception as e:
        logging.getLogger("scribe3").warning("idea 路由失败(落 unclear): %s", e)
    kind = route["kind"]
    # 审查 P1-3:target_seq 脏值(LLM 返回"第3章"/越界/负数)一律降级,绝不 500 丢想法
    tseq = None
    try:
        tseq = int(route.get("target_seq"))
    except (TypeError, ValueError):
        tseq = None
    if kind in ("outline", "steer") and (tseq is None or not st.get_chapter(tseq)):
        kind, route["note"] = "unclear", (route.get("note") or "")
        route["question"] = f"这想法该落到第几章?(路由到的章 {route.get('target_seq')!r} 不存在)"
    status = "routed"
    if kind in ("outline", "steer"):
        # 追加进该章 pilot_steer(想法可累积,帽 2000 字防膨胀;pilot 提案/草稿最高优先注入)
        prev = _pilot_steer(st, tseq)
        merged = ((prev + "\n") if prev else "") + text
        st._execute_write("UPDATE type::record('chapter',$seq) SET pilot_steer=$s",
                          {"seq": tseq, "s": merged[-2000:]})
        status = "done"
    elif kind in ("setting", "revise"):
        status = "pending_approval"   # 宪法:动圣经/改旧章永远等人
    elif kind == "unclear":
        status = "unclear"
    # 想法本体先落库(任何后续失败不丢想法)
    st._execute_write(
        "CREATE idea SET text=$t, route_kind=$k, target_seq=$sq, note=$n, status=$st_, created_at=time::now()",
        {"t": text, "k": kind, "sq": tseq, "n": route["note"], "st_": status})
    q = (route.get("question") or "").strip() or "能再说具体点吗?"
    return {"kind": kind, "target_seq": tseq, "status": status,
            "note": route["note"], "question": q if kind == "unclear" else None}


class IdeaResolveReq(BaseModel):
    id: str


@app.post("/ideas/resolve")
def resolve_idea(req: IdeaResolveReq, work: str = "main"):
    """审查 P1-4:想法处理完毕出收件箱(status→done)——决策收件箱不积压噪声。"""
    _store_for(work)._execute_write(
        "UPDATE type::record('idea',$id) SET status='done'", {"id": req.id})
    return {"ok": True}


class PilotDismissReq(BaseModel):
    seq: int


@app.post("/pilot/dismiss")
def pilot_dismiss(req: PilotDismissReq, work: str = "main"):
    """审查 P1-6:pilot 僵尸态出口——作者绕开 pilot 手写的章,一键退出编排
    (清 pilot_state,不动任何正文/草料;想再用 pilot 从头 step 即可)。"""
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中——请先 /pilot/pause 再退出 pilot")
    # R2-13:一并清 pilot_steer——否则陈旧作者意图重启 pilot 时以「最高优先」静默复活(不可见的行为漂移)
    _store_for(work)._execute_write(
        "UPDATE type::record('chapter',$seq) SET pilot_state=NONE, pilot_state_at=NONE, "
        "pilot_parked=NONE, pilot_card=NONE, pilot_steer=NONE", {"seq": req.seq})
    return {"seq": req.seq, "pilot_state": None}


@app.get("/pilot/status")
def pilot_status(seq: int, work: str = "main"):
    from scribe3.pilot import status
    return status(_store_for(work), seq)


class PilotApproveReq(BaseModel):
    seq: int
    expect_state: str = ""   # 审查 P1-1:知情背书——前端携带条目状态,错位 409 防误触终选


@app.post("/pilot/approve")
def pilot_approve(req: PilotApproveReq, work: str = "main"):
    """作者背书放行当前停靠动作(propose 停靠=继续推进;delivered→finalize=终选)。"""
    from scribe3.pilot import read_state, step
    st = _store_for(work)
    cur = read_state(st, req.seq)["state"]
    if req.expect_state and cur != req.expect_state:
        raise HTTPException(status_code=409, detail=(
            f"状态已变({req.expect_state} → {cur}),为防误背书请刷新收件箱再操作"))
    if cur == "finalized":
        return {"seq": req.seq, "state": cur, "note": "已定稿"}
    # R2-3:连写运行中不许 approve(防 stale 放行与 run 并发双跑同章)
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中(/pilot/pause 先停),防并发双跑")
    _k = (work, req.seq)
    with _pilot_inflight_lock:
        if _k in _pilot_inflight:
            raise HTTPException(status_code=409, detail=f"第 {req.seq} 章pilot 已在推进")
        _pilot_inflight.add(_k)
    try:
        return step(st, req.seq, _pilot_executor(work), mode="manual",
                    journal=_pilot_journal(work, req.seq))
    finally:
        with _pilot_inflight_lock:
            _pilot_inflight.discard(_k)


class PilotRunReq(BaseModel):
    start_seq: int
    until_seq: int


# 连写运行态(进程内;pause 在 step 边界生效,不打断在途 loop)
_pilot_run_state: dict[str, dict] = {}


def _pilot_run_bg(work: str, start: int, until: int) -> None:
    """T10 连写:逐章推进到 delivered(交付卡照发),finalize(宪法锚)永远留人——
    连写不等终选:loop pass 已同步 ingest,下一章简报吃得到本章知识;终选是作者背书,
    攒在收件箱。停靠条件:pause / parked(needs_human·执行失败·日帽)/ until 达成。"""
    from scribe3.pilot import read_state, step
    state = _pilot_run_state.setdefault(work, {})
    state.update({"running": True, "cur_seq": start, "until": until, "stopped": ""})
    try:
        st = _store_for(work)   # 与 sync 端点同模型(executor 内 loop/post-check 也走它)
        ex = _pilot_executor(work)
        existing_seqs = set(st.chapter_seqs_in_range(start, until))
        for seq in range(start, until + 1):
            state["cur_seq"] = seq
            if seq not in existing_seqs:
                st.save_chapter(seq, "", title=f"第{seq}章")
                existing_seqs.add(seq)
            while True:
                if not state.get("running"):
                    state["stopped"] = "作者暂停"
                    return
                cur = read_state(st, seq)["state"]
                if cur in ("delivered", "finalized"):
                    break   # 本章交付,下一章(终选留人)
                _k = (work, seq)
                with _pilot_inflight_lock:
                    _pilot_inflight.add(_k)
                try:
                    r = step(st, seq, ex, mode="run", journal=_pilot_journal(work, seq))
                finally:
                    with _pilot_inflight_lock:
                        _pilot_inflight.discard(_k)
                if r["gate"] == "parked":
                    state["stopped"] = f"第{seq}章停靠:{r.get('reason') or ''}"
                    # R2-7:parked artifact 若含 prose_unsaved(留版失败的唯一副本)→ 落兜底文件,绝不静默丢
                    _unsaved = (r.get("artifact") or {}).get("prose_unsaved")
                    if _unsaved:
                        try:
                            _bj = (os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR")
                                   or os.path.expanduser("~/.scribe3-loop-journals"))
                            _bd = os.path.join(_bj, work)
                            os.makedirs(_bd, exist_ok=True)
                            with open(os.path.join(_bd, f"pilot_unsaved_ch{seq}.txt"), "w", encoding="utf-8") as _fh:
                                _fh.write(_unsaved)
                            state["stopped"] += "(草稿留版失败,已存兜底 pilot_unsaved 文件)"
                        except Exception:
                            pass
                    return
                if r["state"] == "delivered":
                    break
        state["stopped"] = f"连写完成:第{start}-{until}章已交付(终选在收件箱等你)"
    except Exception as e:
        logging.getLogger("scribe3").warning("pilot run %s 异常停靠: %s", work, e)
        state["stopped"] = f"异常停靠:{str(e)[:120]}"
        # R2-8:体外异常也写库(否则只活进程内存,重启失忆、收件箱无承载)
        try:
            _cur = state.get("cur_seq")
            if _cur is not None:
                _store_for(work)._execute_write(
                    "UPDATE type::record('chapter',$seq) SET pilot_parked=$p",
                    {"seq": _cur, "p": f"连写异常停靠:{str(e)[:100]}"})
        except Exception:
            pass
    finally:
        state["running"] = False


@app.post("/pilot/run")
def pilot_run(req: PilotRunReq, background: BackgroundTasks, work: str = "main"):
    if req.until_seq < req.start_seq:
        raise HTTPException(status_code=422, detail="until_seq 须 ≥ start_seq")
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="该书连写已在进行(/pilot/pause 可停)")
    # R2-3:有手动 pilot 步在途也不启动连写(防同章同 action 并发双跑)
    with _pilot_inflight_lock:
        if any(w == work for (w, _s) in _pilot_inflight):
            raise HTTPException(status_code=409, detail="有 pilot 步在途,请稍候再启动连写")
    background.add_task(_pilot_run_bg, work, req.start_seq, req.until_seq)
    return {"running": True, "start": req.start_seq, "until": req.until_seq,
            "note": "逐章推进到交付;终选(宪法)在收件箱等你;/pilot/pause 随时停"}


@app.post("/pilot/pause")
def pilot_pause(work: str = "main"):
    state = _pilot_run_state.get(work)
    if state:
        state["running"] = False
    return {"paused": True}


@app.get("/pilot/run-status")
def pilot_run_status(work: str = "main"):
    return _pilot_run_state.get(work) or {"running": False, "stopped": ""}


@app.post("/pilot/reset-step")
def pilot_reset(req: PilotApproveReq, work: str = "main"):
    """stalled/parked 解卡:清 parked 标记(状态不回退——版本库无损,重跑当前步即可)。"""
    from scribe3.pilot import read_state, write_state
    st = _store_for(work)
    s = read_state(st, req.seq)
    write_state(st, req.seq, s["state"], parked="")
    return {"seq": req.seq, "state": s["state"], "parked": ""}


@app.get("/inbox")
def decision_inbox(work: str = "main", seq: int | None = None):
    """主编主动化 T4:决策收件箱——所有「等作者」的事项一处集中(替代散落各面板)。
    三源聚合:①needs_human 章(loop 三稿全拦,journal 扫描)②升格候选 lesson(≥阈,
    宪法:永不自动升格)③当前章 pulse decision 级。只读聚合,零新状态。"""
    import glob as _glob
    import json as _json
    st = _store_for(work)
    items: list[dict] = []
    degraded: list[str] = []   # R2-18:失败源如实标记(对齐 pulse degraded,防部分失败被当完整清单假绿)
    # ① needs_human 章
    base = (os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR")
            or os.path.expanduser("~/.scribe3-loop-journals"))
    # 审查 P1-7:同章取时间戳最新的 journal(文件名含 time_ns 可排序)——旧 needs_human
    # 之后重跑过审的章不再滞留收件箱。
    latest: dict[int, tuple[int, str]] = {}
    for fp in _glob.glob(os.path.join(base, work, "loop_ch*.json")):
        try:
            bn = os.path.basename(fp)
            s_ = int(bn.split("_")[1][2:])
            ns_ = int(bn.rsplit("_", 1)[1].split(".")[0])
            if s_ not in latest or ns_ > latest[s_][0]:
                latest[s_] = (ns_, fp)
        except Exception:
            continue
    seen_nh: set[int] = set()
    # P2-9:pilot parked 的章由⑤源承载(带更准 reason),journal 源跳过防同章双挂
    _pilot_parked_seqs: set[int] = set()
    try:
        for rr in st._query("SELECT seq, pilot_parked FROM chapter:.. WHERE pilot_parked != NONE"):
            if (rr.get("pilot_parked") or "").strip():
                _pilot_parked_seqs.add(rr.get("seq"))
    except Exception:
        pass
    for s_, (_ns, fp) in latest.items():
        if s_ in _pilot_parked_seqs:
            continue
        try:
            with open(fp, encoding="utf-8") as _fh:
                stages = (_json.loads(_fh.read()) or {}).get("stages_completed") or []
            if any("_needs_human" in x for x in stages):
                seen_nh.add(s_)
        except Exception:
            continue
    for s in sorted(seen_nh):
        items.append({"kind": "needs_human", "seq": s,
                      "message": f"第 {s} 章 loop 三稿全被拦(needs_human):三稿在版本库,请裁决——真不行还是检测器过严?",
                      "action": {"kind": "chat",
                                 "payload": f"第 {s} 章三稿全被拦(needs_human),帮我并排评估版本库三稿:哪稿其实成立?检测器是不是过严?给裁决建议"}})
    # ② 升格候选
    try:
        for r in st.list_lessons():
            if (r.get("importance") or 0) >= 4 and not r.get("invalid_at"):
                items.append({"kind": "promotable_lesson", "id": r.get("id"),
                              "message": f"教训已达升格阈(重要性 {r.get('importance')}):「{(r.get('text') or '')[:60]}」——认可则在主编对话让其走待批升格",
                              "action": {"kind": "chat", "payload": f"这条教训「{(r.get('text') or '')[:40]}」我认可,想升格为长期工艺规则——请到章内写作对话(主编在那挂 s3_craft_rule_add)走待批升格"}})
    except Exception as e:
        logging.getLogger("scribe3").warning("inbox lessons 失败(忽略): %s", e)
        degraded.append("lessons")
    # ⑤ pilot 停靠项(T11):propose 级(大纲提案/交付卡)+ parked(needs_human/失败)
    try:
        rows = st._query(
            "SELECT seq, pilot_state, pilot_parked, pilot_card, synopsis FROM chapter:.. "
            "WHERE pilot_state != NONE ORDER BY seq")
        for r in rows:
            ps, seq_p = r.get("pilot_state"), r.get("seq")
            if r.get("pilot_parked"):
                items.append({"kind": "pilot_parked", "seq": seq_p,
                              "message": f"第 {seq_p} 章 pilot 停靠:{r['pilot_parked']}",
                              "action": {"kind": "chat",
                                         "payload": f"第 {seq_p} 章 pilot 停在「{r['pilot_parked'][:60]}」,帮我分析怎么解"}})
            elif ps == "outline_proposed":
                items.append({"kind": "pilot_outline", "seq": seq_p,
                              "message": f"第 {seq_p} 章大纲提案待放行:{(r.get('synopsis') or '')[:80]}",
                              # R1-3:approve 带 expect_state(知情背书,防 stale 收件箱误触下一动作)
                              "action": {"kind": "pilot_approve", "payload": seq_p,
                                         "expect_state": "outline_proposed"}})
            elif ps == "delivered":
                card = {}
                try:
                    card = _json.loads(r.get("pilot_card") or "{}")
                except Exception:
                    pass
                lc = (card.get("low_confidence") or "").strip()
                items.append({"kind": "pilot_delivered", "seq": seq_p,
                              "message": f"第 {seq_p} 章已交付({card.get('words', '?')} 字)"
                                         + (f";主编拿不准:{lc[:100]}" if lc and lc != "无" else ";主编自评无拿不准处"),
                              # R2-4:附结构化交付卡(promises/qc/完整 low_conf)——此前 promises/qc 写而无读(死数据)
                              "card": card or None,
                              # R1-3:delivered→finalize 是宪法级终选背书,expect_state 防 stale 误触
                              "action": {"kind": "pilot_approve", "payload": seq_p,
                                         "expect_state": "delivered"}})
    except Exception as e:
        logging.getLogger("scribe3").warning("inbox pilot 失败(忽略): %s", e)
        degraded.append("pilot")
    # ④ 想法待批(T8:setting=动圣经/revise=改旧章——宪法与品味决策,永远等人)
    try:
        for r in st._query("SELECT meta::id(id) AS id, text, route_kind, note "
                           "FROM idea WHERE status = 'pending_approval'"):
            lbl = "动设定" if r.get("route_kind") == "setting" else "修旧章"
            items.append({"kind": f"idea_{r.get('route_kind')}", "id": r.get("id"),
                          "message": f"想法待批({lbl}):「{(r.get('text') or '')[:60]}」"
                                     f"——主编理解:{r.get('note') or '(无)'}",
                          "action": {"kind": "chat",
                                     "payload": f"我这个想法:「{(r.get('text') or '')[:80]}」——"
                                                f"帮我评估影响面和落法,先别动手"},
                          "resolve": {"kind": "idea_resolve", "payload": r.get("id")}})
    except Exception as e:
        logging.getLogger("scribe3").warning("inbox ideas 失败(忽略): %s", e)
        degraded.append("ideas")
    # ③ 当前章 pulse decision
    if seq is not None:
        try:
            from scribe3.pulse import chapter_pulse
            for d in chapter_pulse(st, int(seq))["dimensions"]:
                for it in d["items"]:
                    if it["severity"] == "decision":
                        items.append({"kind": "pulse_decision", "dimension": d["dimension"],
                                      "seq": int(seq), "message": it["message"],
                                      "action": it.get("action")})
        except Exception as e:
            logging.getLogger("scribe3").warning("inbox pulse 失败(忽略): %s", e)
            degraded.append("pulse")
    return {"items": items, "count": len(items), "degraded_sources": degraded}


@app.get("/lessons/promotable")
def lessons_promotable(work: str = "main", threshold: int = 4):
    """升格候选队列(北极星任务8):importance ≥ threshold 的有效 lesson。
    只列候选——升格动作必须由作者在主编对话让其调用 s3_craft_rule_add
    (elicitation 待批);蒸馏产物升格永不自动生效(宪法条款,防自评自改变体)。"""
    rows = [r for r in _store_for(work).list_lessons()
            if (r.get("importance") or 0) >= threshold]
    for r in rows:
        r["note"] = ("已达升格阈:如认可,请在主编对话中让其调用 s3_craft_rule_add"
                     "(elicitation 待批)升格为 craft_rule;系统绝不自动升格")
    return rows


@app.get("/north-star/book")
def north_star_book(work: str = "main"):
    """书级北极星 scorecard(北极星任务7,蓝图 §3-③ 后半):四维面板——张弛分布/
    伏笔回收率/跨章矛盾密度/目的达成率 + 因果欠账存量(§3-② 溢出承载)。
    绝不合成加权总分(宪法):北极星语义=所有 setpoint 在区间内 + 各维无恶化趋势,
    面板全绿只证明机器没失职,"是不是好小说"的裁决留给人。
    按需现算不建缓存表(D-016:底座对表 Q2 裁决弃 DB EVENT 聚合;章级变更已走
    /live 推送,前端因章变而重取书级)。各维独立 fail-soft,空书 no_data 不假绿。"""
    st = _store_for(work)
    out: dict = {}
    try:   # ① 张弛分布(find_tension_monotony,与 /post-check 同源组装)
        from scribe3.brief import chapter_draft_text, find_tension_monotony, parse_chapter_meta
        metas: list[dict] = []
        # 2-D(#5):窄查询一次拉草料字段(chapter_draft_text 只吃 synopsis/beats/
        # scene_truth),不再逐章 get_chapter 拉 prose/embedding 全行
        for c in st.chapters_lite():
            m = parse_chapter_meta(chapter_draft_text(c))
            if m:
                metas.append({"seq": c["seq"], **m})
        out["tension"] = {"no_data": not metas, "chapters_with_meta": len(metas),
                          "findings": find_tension_monotony(metas) if metas else []}
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book tension 失败: %s", e)
        out["tension"] = {"no_data": True, "degraded": True}
    try:   # ② 伏笔回收率 = payoff/(open+payoff),另列超期数(蓝图公式)
        rows = st.promises_with_lifecycle()
        payoff = sum(1 for p in rows if p.get("payoff_chapter"))
        open_ = sum(1 for p in rows if p.get("status") == "open")
        overdue = sum(1 for p in rows if (p.get("window") or {}).get("state") == "overdue")
        denom = payoff + open_
        out["promise_recovery"] = ({"no_data": True} if not rows else
                                   {"no_data": False, "payoff": payoff, "open": open_,
                                    "overdue": overdue,
                                    "rate": (payoff / denom) if denom else None})
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book promise 失败: %s", e)
        out["promise_recovery"] = {"no_data": True, "degraded": True}
    try:   # ③ 跨章矛盾密度(CED 口径归一"错误/万字";仅自比趋势)
        cc = st.validate_cross_chapter_consistency() or []
        total_wc = st.total_word_count()
        out["contradiction_density"] = {
            "no_data": total_wc == 0, "issues": len(cc), "total_chars": total_wc,
            "per_10k": (len(cc) / total_wc * 10000) if total_wc else None,
            "self_compare_only": True,
            "note": "口径同 ConStory CED、检测器不同,数字不可对标外部基准(蓝图 v2 口径警示)"}
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book contradiction 失败: %s", e)
        out["contradiction_density"] = {"no_data": True, "degraded": True,
                                        "self_compare_only": True}
    try:   # ④ 目的达成率(任务6 deltas 聚合;waived 出分母)
        # P1门审查 P1-4:按 (kind,predicate) 链尾状态去重——carried 滚动副本会把
        # 还清的债永久挂账、分母每滚一次膨胀(一条最终达成的 delta 被计成 50%)。
        from scribe3.purpose import parse_deltas
        tail: dict = {}   # (kind, predicate) -> (seq, status)
        for c in st.chapters_lite():   # 2-D(#5):deltas 从窄查询取,不拉全行
            for d in parse_deltas(c.get("deltas")):
                key = (d["kind"], d["predicate"])
                prev = tail.get(key)
                if prev is None or c["seq"] >= prev[0]:
                    tail[key] = (c["seq"], d["status"])
        statuses = [s for _, s in tail.values()]
        tot = len(statuses)
        ach = statuses.count("achieved")
        carried = statuses.count("carried")
        waived = statuses.count("waived")
        denom = tot - waived
        out["fulfillment"] = ({"no_data": True} if tot == 0 else
                              {"no_data": False, "achieved": ach, "total": tot,
                               "carried_backlog": carried, "waived": waived,
                               "rate": (ach / denom) if denom else None,
                               "note": "按目的链尾状态去重统计(滚动副本不重复计账)"})
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book fulfillment 失败: %s", e)
        out["fulfillment"] = {"no_data": True, "degraded": True}
    try:   # 附加信息位:因果欠账存量(非四维,§3-② brief top-5 溢出的面板承载)
        out["causal_debt_total"] = st.causal_debt_total()
    except Exception:
        out["causal_debt_total"] = None
    try:   # ⑤ QD 文体多样性档案(北极星任务9):分布单调告警,只进面板不进任何门禁
        from scribe3.qd import CV_FLAT_RUN, style_drift_alerts
        profs = st.list_style_profiles()
        out["style_diversity"] = {"no_data": not profs, "profiles_n": len(profs),
                                  "alerts": style_drift_alerts(profs),
                                  # P2-3:窗口不足≠无漂移——前端不得把空 alerts 当绿灯
                                  "insufficient_window": len(profs) < CV_FLAT_RUN + 3,
                                  "latest": (profs[-1] if profs else None)}
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book style_diversity 失败: %s", e)
        out["style_diversity"] = {"no_data": True, "degraded": True, "alerts": []}
    return out


# chapter_scorecard:北极星任务3——scorecard 缓存表入 /live SSE(蓝图附录 A.2,前端面板不轮询)
_LIVE_TABLES = ["character", "place", "proposition", "event", "knows", "reader_knows",
                "promise", "motif", "chapter", "material", "chapter_scorecard",
                "idea", "lesson"]   # R2-5:#想法待批/升格候选的表变更也推送,收件箱 badge 实时刷新
                                    # (此前前端过滤集含 lesson=死过滤、缺 idea=badge 不动)


_LIVE_MAX = int(os.environ.get("SCRIBE3_LIVE_MAX", "5"))
_live_count: dict[str, int] = {}


@app.get("/live")
async def live(work: str = "main"):
    if _live_count.get(work, 0) >= _LIVE_MAX:
        raise HTTPException(status_code=429, detail=f"too many live connections for {work}")
    _live_count[work] = _live_count.get(work, 0) + 1
    url = os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")
    try:
        return StreamingResponse(live_stream(url, "scribe3", work, _LIVE_TABLES),
                                 media_type="text/event-stream")
    finally:
        _live_count[work] = max(0, _live_count.get(work, 0) - 1)


def main() -> None:
    import uvicorn
    list_works()   # 确保 main 已登记
    uvicorn.run(app, host="127.0.0.1", port=3321)


if __name__ == "__main__":
    main()
