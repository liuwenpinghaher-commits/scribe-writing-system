"""scribe3 后端 API(FastAPI,端口 3321)· 多书(一书一 DB)。

每端点按 ?work=<slug> 路由到对应书的 DB(NS=scribe3 / db=slug),store 按书缓存。
/works 列表/新建。读端点直查;写作走主编对话(/chat/write),不经 /render 直渲。生成走 Hermes。
与 scribe2 后端 3320 隔离(3321)。

架构入口: docs/CURRENT_ARCHITECTURE.md · 拆分路线: docs/ARCHITECTURE_SPLIT_ROADMAP.md
边界决策: AGENTIC_BOUNDARY_DECISION.md

写授权契约(P02) · 2026-07-22 现状(未强制关闭 REST):
- MCP 写工具 = agent 通道(elicitation 待批 + commit_if_approved;失败须 status=error 不假绿)。
- REST 写端点 = 仍注册并可供测试/兼容/部分 UI;产品意图以对话驱动+审批为主(见边界决策)。
- 前端 WIP: Codex/北极星等已有记录倾向只读,写入种子交给主编工具。
- 新增写端点必须显式登记在 _check_write_paths 白名单,测试守护不漂移。

# ----- 文件分区地图(Phase0 基线;搬迁时按此切 api/*)-----
# A. 引导/中间件/依赖: app 创建 · CORS · auth · store 缓存 · 并发锁 (~1-850)
# B. 运行时与设置: /health /ready /settings /gateway /ai/* (~850-1700)
# C. 上下文与会话: /context/* /chat/threads* (~1700-2700)
# D. 写作与章节: chapters · loop · ingest · QC/repair
# E. Codex 世界状态: characters · factions · facts · relations · materials
# F. 伏笔/意图/质量: promises · intent · quality routers(已 include)
# G. 作品与管理: /works · lifecycle · admin
# 具体行号随演进漂移;以路由装饰器与本图语义岛为准。
"""
from __future__ import annotations

import json
import hashlib
import logging
import os
import re
import threading
import time
from contextlib import asynccontextmanager
from functools import wraps
from collections import OrderedDict, deque
from queue import Empty, Full, Queue

import httpx
from fastapi import (
    BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator
from surrealdb.errors import ServerError as _SurrealServerError

from scribe3.codex_schema import (
    ENTITY_RELATION_TYPES,
    all_storage_keys as codex_all_storage_keys,
    chief_only_keys as codex_chief_only_keys,
    fields_for as codex_fields_for,
    prompt_keys as codex_prompt_keys,
    schema_for as codex_schema_for,
    secret_capable_keys as codex_secret_capable_keys,
    secret_flag_key as codex_secret_flag_key,
)
from scribe3.codex_secret_bridge import sync_faction_secrets
from scribe3.codex_validate import validate_faction_consistency
from scribe3.context_models import NavigationIntent, StaleContextError
from scribe3.context_service import (
    ContextService, ContextServiceError, ContextWorkMismatch,
)
from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.live import live_stream
from scribe3.ontology import Entity, Fact
from scribe3.store import (
    MATERIAL_KINDS, OVERDUE_SLACK, QUALITY_CACHE_REVISION, SurrealStore, _overdue_flag, archive_work,
    archived_works, create_work, delete_work, list_works, rename_work,
    restore_work,
)
from scribe3.verify import causal_complete

from scribe3 import settings as _settings
_settings.apply_restart_overrides()   # restart 类 DB 覆盖灌 env,必须在 CORS/token 读取前


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    """统一承载启动安全守卫与退出连接回收，替代已弃用的 on_event。"""
    _startup_gateway_guard()
    try:
        yield
    finally:
        _close_cached_stores()


app = FastAPI(title="scribe3", lifespan=_app_lifespan)
_CORS = os.environ.get("SCRIBE3_CORS_ORIGINS", "http://127.0.0.1:3311,http://localhost:3311")

# P3-e1 Fix 1 / 批C D-3+H-1:overdue 阈值单源——常量定义在 store.py(OVERDUE_SLACK),
# app / health cron / timeline 均从 store 导入同一份,杜绝口径漂移(前端从 /quality 消费,不重算)。
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _CORS.split(",") if o.strip()],
                   allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])

from scribe3.quality.api import quality_router, quality_eval_router
app.include_router(quality_router)
app.include_router(quality_eval_router)

# P01: 可选 bearer token 认证(本地不设 env=放行;暴露=设 SCRIBE3_API_TOKEN 强制)
# L1 会话门禁(SCRIBE3_AUTH_ENABLED)由 scribe3.auth.middleware 接管;此处跳过以免
# Cookie 会话仍被共享 token 闸误杀。机器 Bearer 在 L1 中间件中作为次要身份。
_API_TOKEN = os.environ.get("SCRIBE3_API_TOKEN")


def _l1_session_auth_enabled() -> bool:
    return (os.environ.get("SCRIBE3_AUTH_ENABLED") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


@app.middleware("http")
async def _auth_middleware(request, call_next):
    if _l1_session_auth_enabled():
        return await call_next(request)
    if _API_TOKEN and not request.url.path.startswith("/health"):
        auth = request.headers.get("authorization", "")
        import hmac
        if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:].strip(), _API_TOKEN):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "invalid token"})
    return await call_next(request)


# 世界状态 REST 写路径前缀(精确相等或 prefix + "/…"；避免 /charactersX 误伤)。
# 放行:全部 GET；/health /settings /gateway /ai/ /chat/ /context/ /memory/ /quality/
# /works /live /capabilities；正文存盘 /save-chapter 等手稿路径不在此清单。
_REST_WORLD_WRITE_PREFIXES = (
    "/characters",
    "/facts",
    "/knowledge",
    "/promises",
    "/promises-new",
    "/world-rules",
    "/factions",
    "/items",
    "/terms",
    "/character-relations",
    "/entity-relations",
    "/char-states",
    "/char-anchors",
    "/motifs-new",
    "/motifs",
    "/intent",
    "/volumes",
    "/chapters",
    "/arc-beats",
    "/events",
    "/objects",
)
_REST_WORLD_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


# 工程配额写:字数目标/逾期阈值,非叙事北极星;允许在 emergency 关时表单 PUT。
# 须挂在 /intent 前缀下以外路径,否则 _is_rest_world_write_path("/intent") 子路径会一并 403。
_INTENT_ENGINEERING_PATH = "/intent-goals"
_INTENT_ENGINEERING_KEYS = frozenset({
    "total_word_goal", "daily_word_goal", "overdue_threshold",
})


def _is_rest_world_write_path(path: str) -> bool:
    """path 命中世界写前缀:精确相等,或以 prefix + '/' 开头。"""
    # 工程配额例外(非正典叙事)
    if path == _INTENT_ENGINEERING_PATH or path.startswith(_INTENT_ENGINEERING_PATH + "/"):
        return False
    # 素材库是作者直管的非正典参考记忆，整个 /materials 路由不在世界写闸内。
    # 章节软生命周期 + 版本恢复是作者手稿台一等操作,与 /save-chapter 同级闸外。
    # 永久删除仍走 /chapters/{seq} DELETE + impact token,保持在世界写闸内。
    # 形态: /chapters/{seq}/archive|restore|restore-version
    if path.startswith("/chapters/"):
        rest = path[len("/chapters/"):]
        parts = [p for p in rest.split("/") if p]
        if len(parts) == 2 and parts[0].isdigit() and parts[1] in (
                "archive", "restore", "restore-version"):
            return False
    for p in _REST_WORLD_WRITE_PREFIXES:
        if path == p or path.startswith(p + "/"):
            return True
    return False


# 作者私人非正典摘录：不在世界写闸内(路径本身不在 _REST_WORLD_WRITE_PREFIXES)。
# 见 POST /author/session-clips —— 作者剪藏 ≠ AI/表单写正典。
_SESSION_CLIP_KINDS = frozenset({"snippet", "note"})


@app.middleware("http")
async def _emergency_rest_write_middleware(request, call_next):
    """SCRIBE3_EMERGENCY_REST_WRITE 默认关:拦截世界状态 REST 写,逼走对话+MCP 审批。

    仅自动化测试/紧急运维显式开启;conftest autouse 钉 '1' 保存量写测不炸。
    不拦 /author/session-clips(作者私人素材剪藏,非正典)。
    """
    if request.method in _REST_WORLD_WRITE_METHODS and _is_rest_world_write_path(request.url.path):
        if not _flag_enabled("SCRIBE3_EMERGENCY_REST_WRITE"):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "REST world write disabled; use dialogue + MCP approval"},
            )
    return await call_next(request)

_STORE_CACHE_MAX = 8
_stores: OrderedDict[str, SurrealStore] = OrderedDict()
_stores_lock = threading.RLock()
_complete_fn = None

# P0-1: 同章 ingest 去重——(work,seq) 在途集合。防"存为正文"双触发
# (save-chapter 排一个 + checkpoint(final) 又排一个)对同章并发 purge→抽取→写,
# 造成 knows/reader_knows/char_state/motif_instance/promise_touch 双份或互删。
# 排队前查此集合:同 (work,seq) 已在途/在排则跳过第二次;标记在 _bg_ingest 完成时清除。
# 路径合同:
#   · 自动:save-chapter / checkpoint(final) / 若干终选路径 → _enqueue_ingest → _bg_ingest
#   · 手动:POST /ingest(作者「反哺设定库」) → 同步 ingest_chapter,共用同一在途集合
#   · 手动撞自动 → 409「该章正在反哺中」;自动撞在途 → _enqueue 返回 False 跳过
# ⚠ 单 worker 依赖:此为模块级进程内 set,仅在单 worker 部署下有效。
#   多 worker(多进程/多机)前必须改为跨进程去重(Surreal 在途锁行 / Redis SETNX),
#   否则同章 ingest 会跨进程交错。生产默认单 uvicorn worker。
_pending_ingest: set[tuple[str, int]] = set()
_pending_ingest_lock = threading.Lock()
# P0门审查 P1-3:loop 同章互斥(并发两次 POST /loop/chapter 同章 → 双生成/双落库/双 ingest)
_loop_inflight: set[tuple[str, int]] = set()
_loop_inflight_lock = threading.Lock()
# 精修与跨章去重都会读取整章、调用模型、再覆写正文；若同章并发，后完成者会把先完成者
# 的修复覆盖掉。和 loop 一样以 (work, seq) 为粒度互斥，客户端可明确收到 409 后重试。
_chapter_repair_inflight: set[tuple[str, int]] = set()
_chapter_repair_lock = threading.Lock()


def _acquire_chapter_repair(work: str, seq: int) -> None:
    key = (work, seq)
    with _chapter_repair_lock:
        if key in _chapter_repair_inflight:
            raise HTTPException(status_code=409, detail=(
                f"第 {seq} 章正在执行质量修复，完成后请重新检查再操作"))
        _chapter_repair_inflight.add(key)


def _release_chapter_repair(work: str, seq: int) -> None:
    with _chapter_repair_lock:
        _chapter_repair_inflight.discard((work, seq))


def _exclusive_chapter_repair(handler):
    """为整章读-改-写端点加 finally 释放的同章互斥，不依赖客户端连接是否仍在。"""
    @wraps(handler)
    def wrapped(*args, **kwargs):
        seq = kwargs.get("seq", args[0] if args else None)
        work = kwargs.get("work", "main")
        _acquire_chapter_repair(work, int(seq))
        try:
            return handler(*args, **kwargs)
        finally:
            _release_chapter_repair(work, int(seq))
    return wrapped

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
    with _stores_lock:
        _stores[work] = store


def set_complete_fn(fn) -> None:
    global _complete_fn
    _complete_fn = fn


def _store_for(work: str) -> SurrealStore:
    # Surreal 同步客户端每次建连都会启动 recv_events/keepalive 线程。
    # 首次并发访问同一 work 时，必须把“检查→建连→迁移→入缓存”作为一个原子区，
    # 否则被后写缓存覆盖的客户端没有所有者关闭，最终耗尽线程和套接字。
    with _stores_lock:
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


def _close_cached_stores() -> None:
    """关闭进程级 work→SurrealStore 缓存，供正常服务退出释放 WebSocket/keepalive。"""
    with _stores_lock:
        cached = list(_stores.values())
        _stores.clear()
    for store in cached:
        try:
            store.close()
        except Exception:
            logging.getLogger("scribe3").warning("服务退出时关闭 SurrealStore 失败", exc_info=True)


# 参考/质量路由是独立模块，但必须复用主应用的一书一库解析器，而不是持有
# 一个隐式默认 store。赋值放在定义之后，以便路由实际执行时总能得到同一缓存。
app.state.store_for = _store_for


_OBJECT_PREFIX = {"role": "role", "fact": "fact"}
















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


def _resolve_thread_or_raise(work: str, thread: str | None):
    """P0a 零降级:thread 传了必须有效——不存在 404 / 已归档 409 / 跨 work 409。
    绝不静默回落 active(回落=串台掩盖器,作者定案「不要降级逻辑」)。
    返回线程行;未传返回 None(调用方走 active 默认,文档化参数默认非降级)。"""
    if not thread:
        return None
    _assert_work_binding(_thread_work(thread), work,
                         kind="editorial_thread", ident=thread)
    row = _store_for(work)._get_editorial_thread(thread)
    if row is None:
        raise HTTPException(status_code=404, detail={
            "code": "thread_not_found", "message": f"线程 '{thread}' 不存在"})
    if row.get("status") == "archived":
        raise HTTPException(status_code=409, detail={
            "code": "thread_archived",
            "message": "会话已归档,恢复(PATCH status=active)后再用"})
    return row


def _editor_turn_context(work: str, actor_id: str = "author",
                         thread_row: dict | None = None):
    """组装本轮主编 turn 的会话连续上下文(Task 11 产出 HermesTurnContext)。

    thread_id 取本 work 的稳定主编线程(get_or_create_editorial_thread,一 work 一连续线程);
    P0a:thread_row 给定(作者在下拉选了会话)时用该线程,跳过 get_or_create。
    conversation/previous_response 从线程行取(Hermes 会话续接锚,LRU 100 掉链常态);
    context_* 属动态 envelope 层(默认关),此处留空,开启后由 assembler 填。
    U-011:线程取数异常直接抛(fail-loud)——退化线程会让留痕落错处+历史读不到=静默失忆。"""
    from scribe3.hermes_runtime import HermesTurnContext
    w = _normalize_work(work)
    try:
        thread = thread_row or _store_for(w).get_or_create_editorial_thread(w, actor_id)
        return HermesTurnContext(
            work=w,
            thread_id=thread["thread_id"],
            conversation_id=thread.get("hermes_conversation_id") or None,
            previous_response_id=thread.get("previous_response_id") or None,
        )
    except Exception:
        # U-011(作者要 fail-loud):删"退化为 work 兜底线程"——退化后留痕落错线程、历史读不到,
        # 主编静默失忆且对话记录漂移。线程取数失败直接抛(端点 500/SSE error,前端报错)。
        logging.getLogger("scribe3").error("editorial thread 取数失败", exc_info=True)
        raise


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


def _flag_enabled(name: str) -> bool:
    """统一开关判定门面(委托 context_cache.flag_enabled,单一真值来源)。
    上下文产品三件套默认开(见 settings);显式 env/DB 覆盖可关。"""
    from scribe3 import context_cache
    return context_cache.flag_enabled(name)


def _context_memory_metrics(work: str = "main") -> dict:
    """Task 16-B runtime-status 指标块。绝不含原始 prompt / 秘密值——只有计数、
    分位数与布尔/短标识。诚实区分【当前有真实值】与【采集骨架待 16-C 接线】:

    真实值:cross_work_rejections(16-A)、memory_events_pending/failed(store 计数)、
      context_sessions_active(store 计数)、hermes_memory_provider。
    采样指标:retrieval_p50/p95、context_tokens_p95、stale_rejections；相关事件尚无
      样本时如实为 0/None，不表示统一内核或采集接线关闭。"""
    from scribe3 import context_cache
    metrics = dict(context_cache.metrics_snapshot())   # 检索/组装侧(当前多为 0/None)
    # 安全指标(16-A 只读快照,不复算)
    metrics["cross_work_rejections"] = get_security_metrics().get("cross_work_rejections", 0)
    # 记忆捕获管线水位(per work,与既有 memory_capture.failed_events 同库口径)。
    # U-011(作者要 fail-loud):删掉"查询失败伪装成 0"——那是把"查询挂了"喂成"0个失败事件"
    # 塞进运维仪表盘(最迷惑的假绿,恰恰发生在用来发现问题的诊断路径上)。查询失败在指标块
    # 标 memory_metrics_error(仪表盘显"查询失败"而非假0),但不 500 整个 runtime-status
    # (否则连诊断面板都没了)。
    try:
        st = _store_for(work)
        metrics["memory_events_pending"] = st.count_memory_events(status="pending")
        metrics["memory_events_failed"] = st.count_failed_memory_events()
        metrics["context_sessions_active"] = st.count_active_context_sessions()
    except Exception as e:
        logging.getLogger("scribe3").error("_context_memory_metrics 查询失败", exc_info=True)
        metrics["memory_metrics_error"] = str(e)[:120]
    # 生产记忆提供方：SurrealDB 内的自建多通道检索是唯一运行时实现。
    metrics["hermes_memory_provider"] = "scribe3_builtin"
    return metrics


def _hermes_runtime_status() -> dict:
    from scribe3.hermes_runtime import HermesRuntime
    from scribe3.llm import (
        HERMES,
        HERMES_DEDUCE_PREVIEW_RUNS,
        HERMES_DEDUCE_RUNS,
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
    ]
    profile_configs = {
        "default": _hermes_profile_config_summary("default"),   # U-006:速答网关工具面自检需要
        HERMES_RESPONSES_PROFILE: _hermes_profile_config_summary(HERMES_RESPONSES_PROFILE),
        HERMES_RUNS_PROFILE: _hermes_profile_config_summary(HERMES_RUNS_PROFILE),
        "scribe3_deduce": _hermes_profile_config_summary("scribe3_deduce"),
        "scribe3_deduce_preview": _hermes_profile_config_summary("scribe3_deduce_preview"),
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
    from scribe3.llm import (HERMES_DEDUCE_PREVIEW_RUNS, HERMES_DEDUCE_RUNS,
                             HERMES_RUNS, HERMES_RUNS_PROFILE)
    if policy is not None:
        api_base_by_env = {
            "HERMES_DEDUCE_RUNS_API": HERMES_DEDUCE_RUNS,
            "HERMES_DEDUCE_PREVIEW_RUNS_API": HERMES_DEDUCE_PREVIEW_RUNS,
        }
        try:
            api_base = api_base_by_env[policy.api_env]
        except KeyError as exc:
            raise RuntimeError(f"unconfigured run stage policy: {policy.phase}") from exc
        return HermesRuntime(api_base=api_base, profile=policy.profile)
    return HermesRuntime(api_base=HERMES_RUNS, profile=HERMES_RUNS_PROFILE)


def _run_session_key(work: str, scope: str = "runs") -> str:
    # Run 需与讨论线程隔离；同一章节阶段可续接，不同阶段绝不共享工具轨迹，
    # 以免演绎任务继承正文/设定任务的长上下文后工具游走。
    from scribe3.hermes_runtime import scribe3_session_key
    return scribe3_session_key(_normalize_work(work), scope=scope or "runs")


_ai_run_trace_write_lock = threading.RLock()
# 同一待审批 Run 可能同时出现在原页面与刷新恢复的页面。Hermes 的 elicitation
# 只能消费一次，故这里按 (work, run) 做条带串行化：首个作者决定落审计后，后到的
# 同决定重放直接幂等返回，不得把正常竞态误报成 approval_failed。
_AI_RUN_APPROVAL_LOCK_STRIPES = tuple(threading.RLock() for _ in range(64))


def _serialize_ai_run_approval(fn):
    @wraps(fn)
    def wrapped(run_id: str, *args, **kwargs):
        work = kwargs.get("work", "main")
        lock = _AI_RUN_APPROVAL_LOCK_STRIPES[hash((str(work), str(run_id))) % len(_AI_RUN_APPROVAL_LOCK_STRIPES)]
        with lock:
            return fn(run_id, *args, **kwargs)
    return wrapped


def _record_ai_run_trace(work: str, run_id: str | None, **fields) -> None:
    if not run_id:
        return
    try:
        with _ai_run_trace_write_lock:
            _store_for(work).upsert_ai_run_trace(run_id, **fields)
    except Exception:
        logging.getLogger("scribe3").warning("ai_run_trace 落库失败(忽略)", exc_info=True)


def _capture_turn_memory(store, *, work: str, thread_id: str, turn_id: str,
                         text: str, chapter: int | None = None) -> None:
    """Task 9:把本轮作者意图幂等捕获成经验记忆(同步 drain)。

    best-effort:任何失败只告警,绝不阻断写作主链路(与 chat_message 落库同纪律 D-004)。
    幂等:event_id = turn:<turn_id>(同轮重放不重复记)。分类/正典红线/linked_ids 领域反查
    在 MemoryCapture 内;known_from=chapter 在此传入(限知门对捕获记忆生效,防知情倒灌)。

    产品默认 MEMORY_FABRIC 开:写路径同步捕获经验记忆。
    仅显式关(env/DB=0)时短路——测试/运维隔离,不是产品 fallback。
    捕获异常只告警不阻断写作主链路(与 chat_message 同纪律);HTTP /memory/capture-turn 则 fail-loud。"""
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
        with _ai_run_trace_write_lock:
            _store_for(work).append_ai_run_trace_event(run_id, payload)
    except Exception:
        logging.getLogger("scribe3").warning("ai_run_trace event 落库失败(忽略)", exc_info=True)


def _runtime_for_traced_run(work: str, run_id: str):
    """Run 的后续请求沿创建时的 profile 与 session，绝不退回作品级全写面。"""
    from scribe3.run_stage_policy import (
        policy_from_trace_snapshot,
        tool_contract_from_trace_snapshot,
    )

    trace = _store_for(work).get_ai_run_trace(run_id)
    if not trace:
        # run_id 不是跨作品能力令牌。若请求 work 下没有创建时 trace，不能退回
        # 默认 write profile/session 去碰 Hermes 中同名 Run；状态、事件、审批、停止
        # 四条后续路径都必须在此统一 fail-closed。
        raise HTTPException(status_code=404, detail="ai_run_trace not found")
    try:
        policy = policy_from_trace_snapshot(trace.get("stage_policy"))
        tool_contract = tool_contract_from_trace_snapshot(trace.get("tool_contract"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return (
        _hermes_runs_runtime(policy) if policy is not None else _hermes_runs_runtime(),
        trace.get("session_key") or _run_session_key(work),
        policy,
        tool_contract,
        trace,
    )


SCRIBE3_READ_MCP_LABEL = os.environ.get("SCRIBE3_READ_MCP_LABEL", "scribe3_read")
# U-003 真机实测推翻的旧方案(勿重加):曾想引入 SCRIBE3_CHIEF_MCP_LABEL 给主编
# agentic 联查挂 s3_*_reveal 全知孪生工具面,与写作路径"隔离"。真机实测证明
# server_label 根本不是选择器——Hermes 网关把 platform_toolsets.api_server 里
# 所有 MCP server 的工具一律暴露给每个走该网关的请求,label 只是个标签,不做过滤。
# 主编对话(chat_agentic_stream)与限知续写(_stream_write/_collect_write)物理上
# 共用同一个网关进程(:8643),给前者挂 reveal 工具就等于给了后者。故只留这一个
# label;6 把 *_reveal 工具(mcp.py)目前不挂在任何网关 profile 上(见
# _summarize_hermes_runtime 的 gateway_exposes_reveal_tools 自检)。


def _response_events_iter(fn, message, instructions: str, **kwargs):
    """Call real Hermes with full runtime kwargs while preserving old test stubs."""
    if _responses_events is None:
        return fn(message, instructions, **kwargs)
    safe = {
        k: v for k, v in kwargs.items()
        if k in {"model", "with_tools", "max_tokens"}
        and (k != "max_tokens" or v is not None)
    }
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


# ===== 书 =====








# ── 统一设置中心(spec: docs/superpowers/specs/2026-07-12-settings-center-design.md)──
class SettingPutReq(BaseModel):
    value: object = None












class GatewayFilePutReq(BaseModel):
    id: str
    content: str
    base_sha256: str






class GatewayRestartReq(BaseModel):
    profile: str












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
    # 章级阶段运行的会话隔离键。旧客户端缺省时保持作品级 runs 兼容行为。
    run_scope: str | None = Field(default=None, pattern=r"^[A-Za-z0-9:_-]{1,120}$")
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


def _already_resolved_approval(trace: dict, approval_id: str | None, choice: str) -> bool:
    """只将已持久化的同一作者决定识别为审批重放，绝不吞掉未知写入。"""
    if not approval_id:
        return False
    approved = {"approve", "approved", "once", "session", "always", True}
    denied = {"deny", "denied", "decline", "declined", "reject", "rejected", False}
    expected = denied if choice == "deny" else approved
    for item in reversed(list(trace.get("approvals") or [])):
        if item.get("approval_id") != approval_id:
            continue
        decision = item.get("choice", item.get("decision"))
        if decision in expected and str(item.get("status") or "").lower() in {
            "resolved", "approved", "denied", "declined",
        }:
            return True
    return False




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


def _pending_approval_from_trace(trace: dict) -> dict | None:
    """从持久审计链找出尚未决的审批；只返回作者恢复审批卡所需的最小字段。"""
    status = str(trace.get("status") or "").lower()
    error = str(trace.get("error") or "")
    # 审批卡不仅要在本地 trace 中未决，还必须仍可由 Hermes 接受。Run 已有终态，
    # 或网关已明确返回 approval_not_active 时，旧的 approval.requested 只是审计历史；
    # 刷新后重新展示会诱导作者点击一个必定失败的“批准”按钮。其他 transport 失败
    # 仍保留请求，允许作者在 Hermes 仍等待时重试。
    if (
        status in _AI_RUN_TERMINAL_STATUSES
        or status == "remote_completed_pending_audit"
        or status == "approval_expired"
        or (status == "approval_failed" and "approval_not_active" in error)
    ):
        return None
    approvals = [row for row in (trace.get("approvals") or []) if isinstance(row, dict)]
    resolved_ids = {
        str(row.get("approval_id"))
        for row in approvals
        if row.get("approval_id") and (
            row.get("decision") is not None
            or str(row.get("status") or "").lower() in {"resolved", "approved", "denied", "declined"}
        )
    }
    for row in reversed(approvals):
        approval_id = row.get("approval_id")
        if not approval_id or str(approval_id) in resolved_ids:
            continue
        if str(row.get("status") or "requested").lower() not in {"requested", "pending"}:
            continue
        return {
            "run_id": trace.get("run_id"),
            "approval_id": approval_id,
            "message": row.get("message") or "需要你确认后才会写入章节演绎。",
        }
    return None








def _iter_persisted_ai_run_events(work: str, run_id: str, runtime, session_key: str,
                                  policy, tool_contract):
    """消费 Hermes Run 事件并先持久化，再交给 SSE 或审批收尾使用。

    浏览器刷新会取消 EventSource；审批后的 MCP 完成事件不能只依赖那个易断的
    浏览器连接，否则 Hermes 清理 completed Run 后审计链将永久缺尾。
    """
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.run_stage_policy import validate_tool_trace

    adapter = HermesEventAdapter()
    for ev in runtime.run_events(run_id, session_key=session_key):
        app_ev = adapter.adapt(ev)
        kind = app_ev.get("kind")
        _record_ai_run_event(work, run_id, app_ev)
        # Hermes Runs 的 run.completed 原生带最终回答；append_ai_run_trace_event
        # 只负责生命周期/工具链，需在此显式写入 response，才能让质量复核和
        # 刷新后的作者界面读取与本次工具证据同源的解释文本。
        if kind == "run.completed":
            # 终态事件是 Run 的权威 usage/model 载体。此前只在有 output 时覆盖 response，
            # 且覆盖时漏掉 model；作者审批后的回收会把创建响应中的模型身份抹掉，导致
            # 已真实执行的 TokenPlan/Qwen Run 无法被审计。终态无输出也必须留这份身份。
            terminal_response = {
                "run_id": app_ev.get("run_id") or run_id,
                "status": "completed",
                "usage": app_ev.get("usage"),
            }
            if app_ev.get("output") is not None:
                terminal_response["output"] = app_ev.get("output")
            if isinstance(app_ev.get("model"), str) and app_ev["model"]:
                terminal_response["model"] = app_ev["model"]
            _record_ai_run_trace(work, run_id, response=terminal_response)
        policy_violations = None
        trace_policy = policy or tool_contract
        if kind == "run.completed" and trace_policy is not None:
            trace = _store_for(work).get_ai_run_trace(run_id) or {}
            policy_violations = validate_tool_trace(
                trace_policy,
                list(trace.get("tool_calls") or []),
                list(trace.get("tool_outputs") or []),
            )
            if policy_violations:
                _store_for(work).update_ai_run_context(
                    run_id, policy_violations=policy_violations)
                _record_ai_run_trace(
                    work, run_id, status="failed",
                    error="stage tool policy violation",
                )
        yield app_ev, policy_violations
        if policy_violations:
            return


_ai_run_collector_lock = threading.RLock()
_ai_run_collectors: set[tuple[str, str]] = set()
_ai_run_event_subscribers: dict[tuple[str, str], list[Queue]] = {}
_AI_RUN_TERMINAL_STATUSES = {
    "completed", "completed_unverified", "failed", "stopped", "cancelled", "canceled",
}


def _ai_run_collector_key(work: str, run_id: str) -> tuple[str, str]:
    return (_normalize_work(work), str(run_id))


def _remote_terminal_after_pruned_events(runtime, run_id: str, session_key: str,
                                         exc: Exception) -> dict | None:
    """Hermes 回收 events 前先以状态端点确认真实终态。

    不能把 events=404 一概当作写入失败：真实网关会在 Run 已 completed 后清理
    事件端点。也不能把它升格为完整成功，因为 tool.completed 审计尾部已丢失；调用方
    要以 ``completed_unverified`` 明示必须回读正典完成复核。
    """
    if not isinstance(exc, httpx.HTTPStatusError):
        return None
    response = exc.response
    if response is None or response.status_code != 404:
        return None
    try:
        remote = runtime.run_status(run_id, session_key=session_key)
    except Exception:
        return None
    if not isinstance(remote, dict) or str(remote.get("status") or "").lower() != "completed":
        return None
    # 只持久化稳定、无请求内容的状态字段，避免把网关响应意外变成新的 secret 通道。
    return {
        key: remote[key]
        for key in ("run_id", "status", "last_event", "created_at", "updated_at", "model", "usage")
        if key in remote
    }


def _mark_run_completed_unverified(work: str, run_id: str, response: dict) -> str:
    """记录可证明远端终态、但无法证明工具审计尾部的状态。"""
    error = "Hermes 已报告 Run 完成，但 events 审计尾部不可获得；必须回读正典复核写入结果"
    _record_ai_run_trace(
        work, run_id, status="completed_unverified", error=error, response=response,
    )
    return error


def _publish_ai_run_event(key: tuple[str, str], app_ev: dict,
                          policy_violations: list[dict] | None = None) -> None:
    """把已落库事件分发给当前浏览器订阅者；慢客户端不得反压审计收集器。"""
    payload = {"event": app_ev, "policy_violations": policy_violations or []}
    with _ai_run_collector_lock:
        subscribers = list(_ai_run_event_subscribers.get(key) or [])
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(payload)
        except Full:
            # 浏览器只负责展示；完整事件已在 trace，不能为了它阻断唯一的 Hermes 消费者。
            continue


def _ensure_ai_run_event_collector(work: str, run_id: str) -> None:
    """为每个 Run 启动唯一的服务端 Hermes 事件消费者。

    浏览器 SSE 只是该消费者的订阅者。这样作者在等待审批时刷新、关页或网络抖动，
    都不会中断 MCP 的 tool.completed/run.completed 审计收尾。
    """
    trace = _store_for(work).get_ai_run_trace(run_id) or {}
    if trace.get("status") in _AI_RUN_TERMINAL_STATUSES:
        return
    key = _ai_run_collector_key(work, run_id)
    with _ai_run_collector_lock:
        if key in _ai_run_collectors:
            return
        _ai_run_collectors.add(key)

    def collect() -> None:
        try:
            runtime, session_key, policy, tool_contract, _trace = _runtime_for_traced_run(work, run_id)
            _record_ai_run_trace(work, run_id, status="streaming")
            terminal_event_seen = False
            for app_ev, policy_violations in _iter_persisted_ai_run_events(
                work, run_id, runtime, session_key, policy, tool_contract,
            ):
                _publish_ai_run_event(key, app_ev, policy_violations)
                if app_ev.get("kind") in {"run.completed", "run.failed"}:
                    terminal_event_seen = True
                if policy_violations:
                    return
            if not terminal_event_seen:
                try:
                    remote = runtime.run_status(run_id, session_key=session_key)
                except Exception:
                    remote = None
                if isinstance(remote, dict) and str(remote.get("status") or "").lower() == "completed":
                    safe_remote = {
                        name: remote[name]
                        for name in ("run_id", "status", "last_event", "created_at", "updated_at", "model", "usage")
                        if name in remote
                    }
                    error = _mark_run_completed_unverified(work, run_id, safe_remote)
                    _publish_ai_run_event(key, {
                        "kind": "run.reconciliation_required", "run_id": run_id,
                        "error": error, "remote_status": "completed",
                    })
        except Exception as exc:
            reconciled = _remote_terminal_after_pruned_events(
                runtime, run_id, session_key, exc,
            )
            if reconciled is not None:
                error = _mark_run_completed_unverified(work, run_id, reconciled)
                _publish_ai_run_event(key, {
                    "kind": "run.reconciliation_required", "run_id": run_id,
                    "error": error, "remote_status": "completed",
                })
            else:
                _record_ai_run_trace(work, run_id, status="failed", error=str(exc)[:160])
                _publish_ai_run_event(key, {"kind": "run.failed", "run_id": run_id,
                                            "error": str(exc)[:160]})
        finally:
            _publish_ai_run_event(key, {"kind": "run.done", "run_id": run_id})
            with _ai_run_collector_lock:
                _ai_run_collectors.discard(key)

    threading.Thread(target=collect, name=f"scribe3-run-{str(run_id)[:12]}", daemon=True).start()








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
    # P0a:显式绑定某会话线程(切会话=重建 session 绑新线程);缺省=active 默认线程
    thread_id: str | None = None












# ---------------------------------------------------------------------------
# 统一上下文与记忆系统 · Task 6:主编线程(一 work 一连续线程 + 每轮焦点标签)
# GET  /chat/threads               本 work 线程列表(含分支)
# GET  /chat/threads/{id}/messages 该线程全部消息(store.list_thread_messages)
# POST /chat/threads/{id}/fork     显式分支(写 parent_thread_id 建新线程)
# 导航路径绝不调 fork——fork 只在作者显式"另起支线"时触发。
# ---------------------------------------------------------------------------

class ForkThreadReq(BaseModel):
    title: str | None = None








def _maybe_summarize_thread(work: str, thread_id: str, threshold: int = 40) -> dict:
    """P0b L2:线程增量摘要(补 _thread_history_for_prompt 挂账的 L2)。

    未摘要消息(ts > summarized_upto_ts)≥ threshold 才压缩:旧 summary + 新增轮次
    → 新 summary(≤1500 字;优先保留:①未决决策 ②作者偏好/否决表态 ③伏笔/设定承诺)。
    成功:set_thread_summary(+游标,清 summary_error);失败:log.error + summary_error
    (前端摘要卡红字——失败不许只躺日志,零降级可见性);旧 summary 保留,下轮重试。
    每轮流结束后由 BackgroundTasks 触发(阈值内秒退,零 LLM 成本);/maintenance 夜间兜底。
    整体防线:store 读失败也走 error 路径(log.error + summary_error 尽力标红)——摘要是
    后台增强,绝不允许它把刚结束的对话请求崩掉(BackgroundTasks 异常会炸给 TestClient/日志)。"""
    try:
        return _summarize_thread_inner(work, thread_id, threshold)
    except Exception as e:
        logging.getLogger("scribe3").error("线程摘要失败(store 层)thread=%s", thread_id,
                                           exc_info=True)
        try:
            _store_for(work).set_thread_summary_error(thread_id, str(e)[:200])
        except Exception:
            logging.getLogger("scribe3").error("summary_error 落库也失败 thread=%s", thread_id,
                                               exc_info=True)
        return {"status": "error", "error": str(e)[:200]}


def _summarize_thread_inner(work: str, thread_id: str, threshold: int) -> dict:
    st = _store_for(work)
    row = st._get_editorial_thread(thread_id)
    if row is None:
        return {"status": "missing"}
    upto = str(row.get("summarized_upto_ts") or "")
    msgs = st.list_thread_messages(thread_id, limit=1000)
    fresh = [m for m in msgs
             if m.get("role") in ("user", "assistant")
             and (m.get("text") or "").strip()
             and str(m.get("ts") or "") > upto]
    if len(fresh) < max(2, int(threshold)):
        return {"status": "skipped", "new_count": len(fresh)}
    lines, total = [], 0
    for m in fresh:
        t = (m.get("text") or "").strip().replace("\n", " ")[:300]
        line = f"{'作者' if m['role'] == 'user' else '主编'}:{t}"
        if total + len(line) > 9000:
            break
        lines.append(line)
        total += len(line)
    prev = (row.get("summary") or "").strip()
    prompt = (
        "你是写作系统的会话压缩器。把主编与作者的讨论增量压缩为持续摘要,供后续对话作早期记忆。\n"
        "硬要求:≤1200字;优先保留三类信息:①未决决策(选项与倾向)②作者的偏好/否决表态"
        "③伏笔/设定承诺;去客套与过程性废话;第三人称陈述;绝不虚构未出现的内容。\n"
        f"【既有摘要(为空则忽略,否则融合)】\n{prev or '(无)'}\n\n"
        "【新增讨论】\n" + "\n".join(lines) + "\n\n只输出新摘要正文,不加任何前后缀。")
    complete_fn = _complete_fn
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    last_ts = str(fresh[-1].get("ts") or "")
    try:
        out = (complete_fn(prompt) or "").strip()
        if not out:
            raise RuntimeError("摘要输出为空")
        st.set_thread_summary(thread_id, out[:1500], last_ts)
        return {"status": "summarized", "new_count": len(fresh)}
    except Exception as e:
        logging.getLogger("scribe3").error("线程摘要失败 thread=%s", thread_id, exc_info=True)
        st.set_thread_summary_error(thread_id, str(e)[:200])
        return {"status": "error", "error": str(e)[:200]}








class ThreadCreateReq(BaseModel):
    title: str | None = None


class ThreadPatchReq(BaseModel):
    title: str | None = None
    status: str | None = None






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


def _require_memory_fabric():
    """仅当显式关闭 MEMORY_FABRIC 时拒绝 /memory/*(测试隔离/运维关闸)。
    产品默认开 → 不 403。"""
    if not _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1"):
        raise HTTPException(
            status_code=403,
            detail="MEMORY_FABRIC disabled; set SCRIBE3_MEMORY_FABRIC_V1=1 (or remove override) for experience memory",
        )




class MemoryCaptureTurnReq(BaseModel):
    thread_id: str | None = None
    event_id: str | None = None
    user: str = ""
    assistant: str = ""
    messages: list = Field(default_factory=list)




class MemoryFlushReq(BaseModel):
    thread_id: str | None = None
    reason: str = "manual"






class PendingClaimResolveReq(BaseModel):
    decision: str   # approve | reject
    valid_from: int = 1
    secret: bool = False












class WorkIn(BaseModel):
    title: str


class WorkPurgeReq(BaseModel):
    confirm_title: str














# ===== 读(按书)=====








class NarrativeIn(BaseModel):
    narrative_position: int | None = None


class CausalRootIn(BaseModel):
    reason: str


class CausalLinkIn(BaseModel):
    source_event: str
    ctype: str = "enables"




















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























# ===== 角色弧光:静态锚(五要素)+ arc_plan 里程碑(migration 054)=====








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










class FactIn(BaseModel):
    entity: str
    attribute: str
    value: str
    valid_from: int = 1
    valid_to: int | None = None
    secret: bool = False
    leak_markers: list[str] = []








class SupersedeIn(BaseModel):
    entity_id: str
    attribute: str
    value: str
    since_chapter: int
    secret: bool = False




class ForgetIn(BaseModel):
    knower_id: str
    proposition_id: str
    until_chapter: int




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








class AdvanceIn(BaseModel):
    payoff_chapter: int










class ClueIn(BaseModel):
    note: str
    chapter: int






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






# P1-8:world_rule.scope 合法枚举(对齐 migration 027 的 DB ASSERT);应用层提前 422,
# 不再让非法值走到落库层 ASSERT 才 500。
_WORLD_RULE_SCOPES = {"global", "regional", "faction_specific"}







# CX-Task 3:FactionIn 由 codex_schema 注册表动态生成(create_model),字段清单的唯一权威源
# 是 codex_schema.FACTION_FIELDS——不在这里手写第二份字段清单,避免两处漂移(见
# test_faction_in_fields_match_registry_storage_keys 钉住 "字段集 == all_storage_keys")。
# extra="allow":未登记字段原样透传进 model_dump(exclude_unset=True),交给
# store.add_faction 的白名单去拒(ValueError→422,见 add_faction_ep),而不是被 pydantic
# 静默吞掉——否则前端字段名笔误,查不出为什么没生效。
_FACTION_TYPE_MAP: dict[str, type] = {
    "text": str, "textarea": str, "enum": str, "int": int, "bool": bool,
    "array<string>": list, "array<object>": list, "object": dict,
}


def _build_faction_in() -> type[BaseModel]:
    field_defs: dict[str, tuple] = {}
    for f in codex_fields_for("faction"):
        if f.key == "name":
            field_defs["name"] = (str, ...)
            continue
        py_type = _FACTION_TYPE_MAP.get(f.type, str)
        field_defs[f.key] = (py_type | None, None)
        if f.secret_capable:
            field_defs[codex_secret_flag_key(f.key)] = (bool | None, None)
    return create_model("FactionIn", __config__=ConfigDict(extra="allow"), **field_defs)


FactionIn = _build_faction_in()


_FACTION_STORAGE_KEYS = frozenset(codex_all_storage_keys("faction"))


def _field_violations(fields, value: dict, prefix: str = "") -> list[str]:
    """按 codex_schema 字段定义校验取值合法性(enum 取值 + 数组元素类型),数据驱动、
    不硬编码字段名——注册表新增字段自动获得校验,无需在此加分支。返回违规描述列表,
    空即合法。app 层是唯一防线,漏掉的畸形值会一路走到 DB 炸成裸 500:

    - enum:顶层 + array<object>/object 内一层子字段(SurrealDB 对 FLEXIBLE 子字段不做
      取值校验,尽力而为:只探一层,不递归更深);
    - array<object> 的元素必须是对象:migration 083 把这些字段的 `.*` 定义为
      `TYPE object FLEXIBLE`,传字符串元素会 coercion 失败(Expected `object`);
    - array<string> 的元素必须是字符串:DB 类型是 `array<string>`,传 dict/int 同样
      coercion 失败。
    这两类元素类型错误 pydantic 拦不住——FactionIn 里它们只是裸 `list`,元素不带类型。
    """
    errors: list[str] = []
    for f in fields:
        if f.key not in value or value[f.key] is None:
            continue
        v = value[f.key]
        path = f"{prefix}{f.key}"
        if f.type == "enum" and f.enum is not None:
            if v not in f.enum:
                errors.append(f"{path}={v!r} 非法(合法值: {list(f.enum)})")
        elif f.type == "array<object>" and isinstance(v, list):
            for i, item in enumerate(v):
                if not isinstance(item, dict):
                    errors.append(
                        f"{path}[{i}] 应为对象,实际是 {type(item).__name__}: {item!r}")
                elif f.item_schema:
                    errors.extend(_field_violations(f.item_schema, item, prefix=f"{path}[{i}]."))
        elif f.type == "array<string>" and isinstance(v, list):
            for i, item in enumerate(v):
                if not isinstance(item, str):
                    errors.append(
                        f"{path}[{i}] 应为字符串,实际是 {type(item).__name__}: {item!r}")
        elif f.type == "object" and f.item_schema and isinstance(v, dict):
            errors.extend(_field_violations(f.item_schema, v, prefix=f"{path}."))
    return errors




















# ===== 物品/道具 + 术语(设置完整性)=====


























# ===== CX-Task 5:通用实体关系表(双向认知 + 主编独知 truth + 时态)=====
# 与上面 /character-relations(锁死 character↔character)是两套独立端点,互不影响。
# entity_relation 的 a/b 是不锁类型的自由字符串实体引用,不走 codex_schema 注册表驱动
# (那是给「一个实体类型的一整份字段表单」用的;本表字段少且固定,直接手写字段清单
# 更直接,与 /character-relations 走 dict body 的既有风格一致)。















class MotifIn(BaseModel):
    name: str
    theme: str = ""
    echoes: str = ""
    unfolding: str = ""
    echo_terms: list[str] | None = None
    phase: str | None = None
    tier: str | None = None
    scope: str | None = None








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
    ref_tags: list[str] = []
    summary: str | None = None
    pinned: bool = False
    origin: str | None = None  # 兼容旧请求；作者 REST 创建由服务端强制为 manual


class MaterialPatch(BaseModel):
    title: str | None = None
    body: str | None = None
    kind: str | None = None
    tags: list[str] | None = None
    source: str | None = None
    ref_tags: list[str] | None = None
    summary: str | None = None
    pinned: bool | None = None
    archived: bool | None = None








class SessionClipIn(BaseModel):
    """作者选区/会话摘录。仅 snippet|note；source 可空(服务端补会话来源)。"""
    body: str
    title: str | None = None
    kind: str = "snippet"
    source: str | None = None
    scope_label: str | None = None
    chapter_seq: int | None = None
    origin_label: str | None = None
    summary: str | None = None
    ref_tags: list[str] | None = None








# ===== 素材导入(多格式 → AI 切分打标摘要 → 预览确认 → 落库)=====
# 内存热缓存 + Surreal 持久化(一书一 DB);进程重启后仍可从 store 恢复。
_import_jobs: dict = {}   # job_id → {stage, done, total, items, error, work}


class ImportCommitReq(BaseModel):
    items: list[dict]


def _import_job_get(job_id: str, work: str | None = None) -> dict | None:
    job = _import_jobs.get(job_id)
    if job is not None:
        return job
    # 持久层回源
    try:
        st = _store_for(work or "main")
        row = st.get_import_job(job_id)
        if not row:
            return None
        job = {
            "stage": row.get("stage") or "",
            "done": bool(row.get("done")),
            "total": int(row.get("total") or 0),
            "items": list(row.get("items") or []),
            "error": row.get("error") or "",
            "work": row.get("work") or work or "main",
            "source": row.get("source"),
        }
        _import_jobs[job_id] = job
        return job
    except Exception:
        return None


def _import_job_save(job_id: str, job: dict) -> None:
    _import_jobs[job_id] = job
    try:
        st = _store_for(job.get("work") or "main")
        st.save_import_job(job_id, job)
    except Exception:
        logging.getLogger("scribe3").warning(
            "import job persist failed job=%s", job_id, exc_info=True)


def _run_import(job_id: str, markdown: str, source: str | None, work: str = "main") -> None:
    """后台流水线:AI 切分打标摘要 → 结果存 job 待预览(不直接落库)。fail-soft。"""
    from scribe3.llm import hermes_complete
    from scribe3.material_import import split_and_tag
    job = _import_job_get(job_id, work) or {
        "stage": "", "done": False, "total": 0, "items": [], "error": "", "work": work}
    try:
        job["stage"] = "AI 切分打标中"
        job["work"] = work
        _import_job_save(job_id, job)
        job["items"] = split_and_tag(
            markdown, lambda p: hermes_complete(p, max_tokens=4000), source)
        job["total"] = len(job["items"])
        job["stage"] = "待预览确认"
    except Exception as e:
        job["stage"], job["error"] = "error", str(e)[:200]
    finally:
        job["done"] = True
        _import_job_save(job_id, job)

















class MaterialReferenceIn(BaseModel):
    chapter: int = Field(ge=1)
    dimension: str | None = None
    reason: str | None = None






















class IntentIn(BaseModel):
    reader_feeling: str = ""
    emotional_arc: str = ""
    red_lines: str = ""
    overdue_threshold: int | None = None
    total_word_goal: int | None = None   # 整稿目标字数;None → 前端回退默认 100000
    daily_word_goal: int | None = None   # 每日目标字数;None → 不显示每日进度




class IntentGoalsIn(BaseModel):
    """工程配额-only:整稿/每日字数目标、逾期阈值。禁止叙事北极星字段。"""
    total_word_goal: int | None = None
    daily_word_goal: int | None = None
    overdue_threshold: int | None = None






_FACTION_PROMPT_CHAR_CAP = 400   # 单势力注入上限(字),超出截断(spec §4 长度预算)


def _faction_known_fact_ids(st, focalizer: str, chapter: int) -> set:
    """focalizer 在 chapter 时刻的知情投影(knowledge.project_frame)里的 fact id 集合。

    focalizer 为空 → 直接返回空集,不发 project_frame 查询——这就是 fail-closed 的
    落点:没有可验证身份时,一律当作"什么都不知道",宁可少给也不能泄密。"""
    if not focalizer:
        return set()
    frame = project_frame(st, focalizer, chapter)
    return {f.id for f in frame.facts}


def _faction_bridge_fact_index(st, chapter: int) -> dict:
    """{(entity_id, attribute): fact_id} 索引,供势力 secret 字段定位自己的桥接命题。
    直接复用 st.facts_at(与 _secret_guard_block 同款查询),不另立一套查询语义。"""
    try:
        return {(f.entity_id, f.attribute): f.id for f in st.facts_at(chapter)}
    except Exception:
        return {}


def _codex_value_repr(field, value) -> str:
    """按 CodexField.type 把值转成注入 prompt 的紧凑文本表示。"""
    if field.type == "array<object>" and isinstance(value, list):
        items = []
        for item in value:
            if not isinstance(item, dict):
                continue
            sub = [f"{sf.label}={item[sf.key]}" for sf in (field.item_schema or ())
                   if item.get(sf.key) not in (None, "", [], {})]
            if sub:
                items.append("/".join(sub))
        return "、".join(items)
    if field.type == "object" and isinstance(value, dict):
        sub = [f"{sf.label}={value[sf.key]}" for sf in (field.item_schema or ())
               if value.get(sf.key) not in (None, "", [], {})]
        return "/".join(sub)
    if field.type == "array<string>" and isinstance(value, list):
        return "、".join(str(v) for v in value)
    return str(value)


def _faction_relation_summary(st, name: str, chapter: int, *, for_generation: bool) -> str:
    """该势力的实体关系摘要:perception_a/b(双方各自认知)两档都注入。

    truth(主编独知的真相)是三档可见性的第三档:`for_generation=True`(限知续写/生成
    路径)永不注入——truth 不是给生成模型看的;`for_generation=False`(作者/主编对话)
    才注入,与 codex_schema.chief_only 字段(如 secret_agenda)同级——"仅主编可见"
    的字面意思就是主编在对话里看得见,只是不能流进读者最终看到的限知正文。
    2026-07-15 修订:此前 truth 无论哪种场合都不注入,是"太钝"的旧实现,把主编自己
    也挡在外面。"""
    entity_id = f"faction:{name}"
    try:
        rows = (st.entity_relations_at(chapter, entity_id) if chapter is not None
                else st.list_entity_relations(entity_id))
    except Exception:
        raise   # U-011 fail-loud: _faction_relation_summary 关系摘要
    segs = []
    for r in rows or []:
        a, b, rt = r.get("a"), r.get("b"), r.get("relation_type")
        seg = f"{a}↔{b}[{rt}]"
        pa, pb = r.get("perception_a"), r.get("perception_b")
        if pa:
            seg += f"({a}认知:{pa})"
        if pb:
            seg += f"({b}认知:{pb})"
        if not for_generation:
            truth = r.get("truth")
            if truth:
                seg += f"(真相[仅主编可见]:{truth})"
        segs.append(seg)
    return "；".join(segs)








def _author_prefs_block_safe() -> str:
    """P3:跨书作者偏好注入(单点——_editor_system 被讨论/agentic/写作全路径复用)。
    语义在 scribe3.author_prefs:文件不存在=空(合法初始态);存在但读失败=抛(fail-loud)。"""
    from scribe3.author_prefs import author_prefs_block
    return author_prefs_block()


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
# “没有实时查询工具”是【真话】,由机制保障:U-006 起默认 profile
# platform_toolsets.api_server=[](速答网关零工具面),自检门禁 default_gateway_has_tools
# 盯着它别漂回去。此前默认 profile 继承全部 toolsets(含 hermes-cli 终端),这句是谎——
# 主编速答借此真的执行过跨仓库 git 提交/push。对模型断言的每件事都必须机制上为真。
_DISCUSSION_DIRECTIVE = (
    "\n\n【作答方式(纯讨论)】直接、完整、可操作地回答,一次说透。"
    "不要用『让我查查/让我想想/让我先看看』这类拖延开场——你此刻在纯讨论对话中,"
    "没有实时查询工具,请直接凭你的编辑学识与上方已有设定作答。"
    "作者要方案时,当场给出完整选项(含各自代价),不要只起个头就停。")


class _ChatTurnLog:
    """主编【讨论 / agentic】对话留痕的统一咽喉点(北极星任务1 沉淀环第1级;U-005 补齐)。

    背景(2026-07-15 真机实证):三条 SSE 对话路径此前只有 POST /chat/write(动稿)留痕;
    chat_stream(速答讨论)与 chat_agentic_stream(agentic 联查/审批)**从不落库**——作者
    与主编讨论设定、推敲情节、拍板决策的全过程凭空消失(《印迹》一条讨论都没留下,尽管
    当时批准写入了 15 世界规则 + 6 势力)。此类补齐,两条路共用同一个咽喉点,行为一致:

    - `__enter__`(开流前)即落 user:哪怕流中途崩,你的问话已留痕(与 chat_write 同序)。
    - `.feed(delta)` 累积 assistant 文本;`.set_response_id(rid)` 记本轮响应 id。
    - `__exit__`(正常 done / 异常 / 客户端断开触发的 GeneratorExit 都会调)落 assistant 全文;
      流断则落已累积的部分(有一个字也比凭空消失强);完全空则不落(user 已足证"问过")。

    全程 best-effort(D-004):任何一步落库失败只告警,绝不影响对话主链路(SSE 已在飞)。
    留痕存的是【主编回作者的话】——作者对话语境(主编对作者全知),不引入新泄密面,故
    **不做 for_generation 门控**(那是喂正文生成 prompt 的事,与回看历史无关)。也**不做**
    chat_write 的意图捕获(_capture_turn_memory 只该挂动稿路径:讨论不是写作意图)。
    """

    def __init__(self, st, *, user_text: str, chapter: int, stage: str,
                 thread_id: str | None, focus: dict | None = None):
        import uuid
        self._st = st
        self._user_text = user_text
        self._chapter = chapter
        self._stage = stage
        self._thread_id = thread_id
        self._focus = focus
        self.turn_id = uuid.uuid4().hex[:12]   # 串本轮 user/assistant,防并发交错污染蒸馏
        self._buf: list[str] = []
        self._response_id = None
        self._log = logging.getLogger("scribe3")

    def feed(self, delta: str) -> None:
        if delta:
            self._buf.append(delta)

    def set_response_id(self, rid) -> None:
        if rid:
            self._response_id = rid

    def _persist_user(self) -> None:
        try:
            self._st.add_chat_message(
                chapter=self._chapter, stage=self._stage, role="user",
                text=self._user_text, turn=self.turn_id,
                thread_id=self._thread_id, focus=self._focus)
        except Exception:
            self._log.warning("chat_message user 落库失败(忽略)", exc_info=True)

    def _persist_assistant(self) -> None:
        text = "".join(self._buf)
        if not text.strip():
            return   # 完全空(流开头即崩)→ 不落噪声;user 已足证"问过"
        try:
            self._st.add_chat_message(
                chapter=self._chapter, stage=self._stage, role="assistant",
                text=text, turn=self.turn_id, thread_id=self._thread_id,
                focus=self._focus, response_id=self._response_id)
        except Exception:
            self._log.warning("chat_message assistant 落库失败(忽略)", exc_info=True)

    def __enter__(self):
        self._persist_user()
        # P0a:首条 user 消息给默认标题的线程自动命名(store 侧幂等判默认标题;
        # 纯库内小查询,失败上抛不静默——同 U-011 纪律,留痕 best-effort 豁免不适用于它)。
        if self._thread_id:
            self._st.maybe_autotitle_thread(self._thread_id, self._user_text)
        return self

    def __exit__(self, exc_type, exc, tb):
        self._persist_assistant()
        return False   # 不吞异常


def _thread_history_for_prompt(st, thread_id: str | None, *, max_msgs: int = 12,
                               max_chars_each: int = 600,
                               last_assistant_chars: int = 2400,
                               max_total_chars: int = 8000) -> list[dict]:
    """U-009:主编速答的对话记忆——把本线程最近几轮 user/assistant 留痕变成 chat messages。

    根因:hermes_complete_stream 此前每轮只发 [system, 当前一句],模型从未见过自己
    上一轮说了什么(S-001 注释自认"单遍无续接")——作者选了主编自己给的"方向C",
    主编反问"方向C是什么"。U-005 已把讨论留痕进 editorial thread,这里让**同一份留痕**
    成为模型的上下文(单一事实源:界面显示的历史 = 模型看到的历史;前端零改动)。

    预算(业界 L1 近窗原文层;字符≈token 的中文近似,刻意不引 tokenizer):
    - 普通消息截头部 max_chars_each 字(线程里有《印迹》回填的整篇世界观全案,不截撑爆 prompt);
    - **最后一条 assistant 拿大预算 last_assistant_chars,且超长时头尾各留**(P1 修正:
      作者短回复"选C"的指代对象几乎总在上一条主编消息里,而"方向C:…"这类选项/结论
      惯常在消息**尾部**——砍尾留头恰好丢掉被指代的那段,失忆复发);
    - 总预算 max_total_chars,超了从最旧开始丢。
    **必须在落本轮 user 留痕之前调用**,否则当前这句会在 history 里出现第二遍。
    U-011:取历史失败直接抛(fail-loud),不再静默回 []——那等于失忆降级悄悄复发。
    P0b:L2 已补——线程 summary(增量压缩的更早轮次)作为首条 assistant 记忆块注入,
    近窗(L1)之外的早期讨论不再彻底失忆;summary 由 _maybe_summarize_thread 后台增量生成。"""
    if not thread_id:
        return []
    try:
        thread_row = st._get_editorial_thread(thread_id) or {}
        rows = st.list_thread_messages(thread_id, limit=max_msgs)
        kept = [(r.get("role"), (r.get("text") or "").strip()) for r in rows
                if r.get("role") in ("user", "assistant") and (r.get("text") or "").strip()]
        # 会话延续(作者定义纠正 2026-07-17):新建会话是为了**界面清洁/分类,不是失忆**。
        # 有 parent 的会话(新建默认=fork 延续)在本会话消息不足近窗时,用直接父会话的
        # 尾部原文补齐——主编无缝记得上一会话聊到哪(零 LLM、无损;fork 已拷父 summary 兜早期)。
        # 全新会话(无 parent,手动"不带历史"通道)不回溯;只回溯一层,父的父由父 summary 承载。
        parent_id = (thread_row.get("parent_thread_id") or "").strip()
        if parent_id and len(kept) < max_msgs:
            prows = st.list_thread_messages(parent_id, limit=max_msgs - len(kept))
            pkept = [(r.get("role"), (r.get("text") or "").strip()) for r in prows
                     if r.get("role") in ("user", "assistant") and (r.get("text") or "").strip()]
            kept = pkept + kept
        last_asst = max((i for i, (role, _) in enumerate(kept) if role == "assistant"),
                        default=None)
        out = []
        for i, (role, text) in enumerate(kept):
            if i == last_asst and len(text) > last_assistant_chars:
                head = text[: last_assistant_chars * 2 // 3]
                tail = text[-(last_assistant_chars // 3):]
                text = head + "\n…(中段截断)…\n" + tail
            elif i != last_asst and len(text) > max_chars_each:
                text = text[:max_chars_each] + "…(后文截断)"
            out.append({"role": role, "content": text})
        while out and sum(len(m["content"]) for m in out) > max_total_chars:
            out.pop(0)   # 从最旧开始丢,近轮优先
        # P0b L2:早期摘要块置顶(不参与近窗预算裁剪——它本身就是预算的解法)
        summ = (thread_row.get("summary") or "").strip()
        if summ:
            out.insert(0, {"role": "assistant",
                           "content": "【主编讨论早期摘要(系统压缩,更早轮次的要点)】\n" + summ[:1600]})
        return out
    except Exception:
        # U-011(作者要 fail-loud):此前"取历史失败→本轮无记忆"是静默失忆(恰是 U-009 作者
        # 投诉的症状,由降级悄悄复发)。改抛→SSE error 帧→前端内联报错,作者当场看见。
        logging.getLogger("scribe3").error("载入主编讨论历史失败", exc_info=True)
        raise




_responses_events = None  # 测试可 monkeypatch






def _secret_guard_block(st, chapter: int | None = None) -> str:
    """S-002:知情主角限知泄露修复。project_frame 只屏蔽【焦点者不知道】的帧外私密,
    但焦点者是知情主角时,他自己知道的核心悬念秘密(真名/前史/印记)在帧内、且 backstory
    里也写了 → 写他视角就把该留到揭示章的秘密提前泄露给读者(知情 POV 倒灌)。
    修复:对本书 secret 命题的破绽词(leak_markers),即便视角人物知情,也硬性约束本章
    藏匿、禁明写。默认所有 secret 都藏;作者要在某章揭示时,写作指令里明说'本章揭示X'覆盖。
    无 secret 命题 → 空串(默认行为字节不变,旧书/无私密书零变化)。

    U-011(2026-07-15,作者要 fail-loud):删掉了"facts_at 异常即返空串"——那是把反剧透
    护栏悄悄整体撤除(fail-open),稿子照写、无人知道核心悬念已失防。现在查询失败直接【抛】,
    崩到 SSE error 帧让作者看见,而不是静默拆防线。"""
    facts = st.facts_at(chapter or 99999)
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








_LUANSHI_EXEMPLAR = (
    "看着贺客如潮，满日不绝，韩诤喜不自禁，顾不得年迈体衰，趁着兴头，频频把盏敬客，岂料同村几个毛头小伙"
    "喝发了兴，见主人尽欢，也都意气风发起来，一再持酒相劝。眼看着月儿西移，打更的刘时喜在门口来回好几遭了，"
    "讨了好几杯水酒喝。"
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
        raise   # U-011: fail-loud,取块失败上抛(_avoid_directive 防复读)


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




def _motif_block(st, chapter: int | None = None) -> str:
    """构建母题注入块(兼容 bt_render / 旧测)。

    写作主路径真源: `_codex_block(..., for_generation=True)` 的 heat 调度块
    (与 assemble_chapter_brief 同源 motif_craft)。本函数:有 chapter 时走 schedule。
    """
    motifs = st.list_motifs() or []
    if not motifs:
        return ""
    if chapter is not None and hasattr(st, "motif_touch_map"):
        from scribe3.motif_craft import motif_schedule_directives, generation_motif_block
        d = motif_schedule_directives(motifs, st.motif_touch_map(), int(chapter))
        block = generation_motif_block(d)
        return ("\n\n" + block) if block else ""
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
        raise   # U-011: fail-loud(_frame_block 限知帧)


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
        raise   # U-011: fail-loud(_recap_block 前情)


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
        raise   # U-011: fail-loud(_current_tail_block 续写衔接)




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






def _deduction_block(st, seq: int) -> str:
    """草稿期把本章「场景真相 + 各角色限知投影」注入 instructions。
    空(无真相且无投影)→ 返回空串(默认行为不变)。"""
    return "".join(text for _, _, text in _deduction_context_segments(st, seq))


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
    """兼容旧名:生产写路径目的合同 + 教训内联注入。"""
    return _purpose_and_lessons_write_block(st, chapter, with_tools, work)






# 已废弃的历史观测字段；统一内核不再回退，因此必须恒为 0。
_context_assembler_fallbacks = 0


def _context_assembler_enabled() -> bool:
    """兼容旧调用方：统一内核已启用；这不是用户设置。"""
    return True


# ContextSnapshot.phase 的合法枚举(context_models.PhaseName);写作端点的 phase
# 串("plan"/"draft"/"final"/...)不在此集合的一律降 None,防合成快照校验失败。
_ASSEMBLER_PHASES = {"outline", "beats", "deduce", "draft", "final"}



























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








class ChapterCreateReq(BaseModel):
    title: str | None = None
    volume: str | None = None




class ChapterArchiveReq(BaseModel):
    reason: str | None = None






class RestoreVersionReq(BaseModel):
    """从 chapter_version 恢复正文,或直接用 prose 覆盖(前端已取过版本全文时)。"""
    version_id: str | None = None
    prose: str | None = None
    label: str = "从存档恢复"
    # 恢复历史稿默认仍重抽知识(与当前正文对齐);仅运维逃生可关。
    reingest: bool = True








# ===== 大纲/卷章树(手稿支数据层,作者工具 F-01 后端)=====





class ReorderReq(BaseModel):
    volume: str | None = None   # 目标卷裸 id;None = 未分卷区
    order: list[int]            # 该卷内章 seq 的新顺序(全量)




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

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value):
        if value is None:
            return value
        allowed = {"draft", "revise", "done", "idea", "beat"}
        if value not in allowed:
            raise ValueError("label 必须是 draft、revise、done、idea 或 beat")
        return value


class DeductionGroundingReq(BaseModel):
    candidate: str
    character_id: str = ""


from scribe3.deduce_helpers import DEDUCTION_HEADINGS as _DEDUCTION_HEADINGS
_DEDUCTION_BLANK = "未能从场景真相确认。"


def _verbatim_deduction_fallback(source: str, character_id: str) -> str:
    """把角色在场景真相中被明确提及的句子编排成可机械验真的五栏投影。

    这是自由生成两次未通过事实门时的安全兜底：不伪造角色限知，也不让失败稿
    留在编辑器里诱导误存。来源不足时明确留白，不能拿全知叙述补齐。
    """
    import re

    name = (character_id or "").split(":", 1)[-1].strip()
    sentences = [s.strip() for s in re.findall(r"[^。！？]+[。！？]?", source or "") if s.strip()]
    def subject_tail(sentence: str) -> str:
        pos = sentence.find(name)
        return sentence[pos + len(name):pos + len(name) + 48] if pos >= 0 else ""

    # 仅接受角色自身紧随其名的感知/认知/行动，不能因句子在谈论该角色就把
    # 旁白或他者的认知搬进限知栏(如“黑盐纹认得……季棠”)。
    owned = [(idx, s) for idx, s in enumerate(sentences) if name and s.find(name) >= 0]
    if not owned:
        return ""
    def with_continuation(idx: int, sentence: str) -> str:
        # “季棠……。她……”是同一角色连续表述时，合并为一个仍可逐字定位的来源片段。
        if idx + 1 < len(sentences) and sentences[idx + 1].startswith("她"):
            return sentence + sentences[idx + 1]
        return sentence

    seen = next((s for _idx, s in owned if any(k in subject_tail(s) for k in ("看", "听", "照", "触"))), owned[0][1])
    known = next((with_continuation(idx, s) for idx, s in owned if "不知道" not in subject_tail(s)
                  and any(k in subject_tail(s) for k in ("知道", "看出", "认得", "明白"))), seen)
    action = next((s for _idx, s in owned if any(k in subject_tail(s) for k in ("用", "拿", "照", "说", "做"))), seen)
    sections = (seen, known, _DEDUCTION_BLANK, action, _DEDUCTION_BLANK)
    return "\n\n".join(f"### {heading}\n{content}" for heading, content in zip(_DEDUCTION_HEADINGS, sections))








# == 卷 CRUD ==

class VolumeReq(BaseModel):
    title: str = ""
    sort_order: int = 0
    intro: str | None = None
    color: str | None = None






class VolumePatchReq(BaseModel):
    title: str | None = None
    sort_order: int | None = None
    intro: str | None = None
    color: str | None = None










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








# ===== 写 =====
class SaveChapterReq(BaseModel):
    seq: int
    prose: str
    title: str = ""
    focalizer: str | None = None
    # 工艺门闩逃生:工具/测试/明确跳过;默认受 SCRIBE3_CRAFT_GATE 约束
    skip_craft_gate: bool = False


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
















class PostCheckReq(BaseModel):
    prose: str
    focalizer: str = ""
    brief: str = ""
    short_mode: bool = False  # 方案B任务16:短篇模式——直写情绪+审判金句合法,
                              # 透传给 find_emotion_telling/aggregate_ai_grade,
                              # emotion_telling 检出归零、psych_ratio/Gate C 不触发








class DraftCheckReq(BaseModel):
    prose: str
    focalizer: str = ""








class SaveDraftReq(BaseModel):
    prose: str
    summary: str = ""












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
















class SelectChapterReq(BaseModel):
    chapter: int
    force: bool = False       # 非关键章硬要出候选(作者主权;默认拦,N 倍成本只花刀刃)
    msg: str = ""             # 可选驱动语补充




class SelectFinalizeReq(BaseModel):
    chapter: int
    version_id: str
    reason_axis: str = "其他"
    reason_text: str


def _is_selection_candidate_version(ver: dict) -> bool:
    """终选只接受选择环候选留版:stage=candidate 或 label 前缀「选择环候选·」。
    击杀稿 label 含 ·filtered,不得定稿。"""
    label = str(ver.get("label") or "")
    if "·filtered" in label or label.endswith("filtered"):
        return False
    stage = ver.get("stage") or ""
    if stage == "candidate":
        return True
    # 兼容早期 stage=draft 但 label 已钉「选择环候选·」的留版
    return label.startswith("选择环候选·") or label.startswith("选择环候选")






# ─── 选择环 L1 轻路径:2 条策略短变体 → 人点选 → 草稿种子(非三整章) ───

class SelectLightReq(BaseModel):
    chapter: int
    msg: str = ""


class SelectLightPickReq(BaseModel):
    chapter: int
    version_id: str | None = None
    strategy: str | None = None


def _select_l1_result_path(work: str, chapter: int):
    """L1 结果旁路文件:与 L2 select_ch 分离,避免覆盖重环元数据。"""
    jp = _loop_journal_path(work, chapter)
    return jp.with_name(jp.name.replace("loop_ch", "select_l1_ch", 1))








# ═══════════ Chapter Pilot(主编主动化 T6/T7/T10):章生命周期驱动器 ═══════════
# 作者=创意总监,主编=执行主编。状态机在 scribe3/pilot.py(纯核可测);此处只做
# executor 绑定(全部复用既有链,禁止新写生成逻辑)+ HTTP 面 + 连写循环。

def _pilot_llm_gen(st, work: str, seq: int, phase: str, ask: str, focalizer: str = "",
                   max_tokens: int | None = 1600) -> str:
    """pilot 生成通道:同一 _assemble_write_instructions 组装链(宪法:不另起简化 prompt)。"""
    outcome_binding = _WriteOutcomeBinding(st)
    ins = _assemble_write_instructions(
        st, chapter=seq, focalizer=focalizer, phase=phase,
        with_tools=False, seed_words=[], short_mode=False, work=work,
        envelope_trace=outcome_binding.manifest_trace, request_text=ask)
    return _collect_write(
        ask, ins, with_tools=False, on_terminal=outcome_binding.persist,
        text_mode=True, max_tokens=max_tokens,
    )




def _grounding_llm(st, work: str, chapter: int, prompt: str) -> str:
    """事实对齐审查经统一上下文引擎走 Qwen 官方服务，并持久化 Outcome。"""
    return _contextual_review_complete(
        st, work, chapter, "grounding", prompt,
        max_tokens=4096, official_api=True, thinking="disabled",
    )




def _pilot_steer(st, seq: int) -> str:
    rows = st._query("SELECT pilot_steer FROM type::thing('chapter',$seq)", {"seq": seq})
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




class IdeaResolveReq(BaseModel):
    id: str




class PilotDismissReq(BaseModel):
    seq: int






class PilotApproveReq(BaseModel):
    seq: int
    expect_state: str = ""   # 审查 P1-1:知情背书——前端携带条目状态,错位 409 防误触终选




class PilotRunReq(BaseModel):
    start_seq: int
    until_seq: int


# 连写运行态(进程内;pause 在 step 边界生效,不打断在途 loop)
_pilot_run_state: dict[str, dict] = {}


















# chapter_scorecard:北极星任务3——scorecard 缓存表入 /live SSE(蓝图附录 A.2,前端面板不轮询)
# U-002(2026-07-13):faction/item/term/world_rule 四张【设定库分类表】此前漏出清单——
# 主编经审批写入 15 条世界规则+6 个势力后,前端项目树收不到 live 事件、不重拉,
# 设定库看着还是空的(数据其实已落库),作者误以为写入失败。铁律:**设定库树里有的分类,
# 其表必须在此清单里**(门禁 test_live.test_codex_tables_all_in_live_tables 钉死)。
_LIVE_TABLES = ["character", "place", "proposition", "event", "knows", "reader_knows",
                "promise", "motif", "chapter", "material", "chapter_scorecard",
                "idea", "lesson",   # R2-5:#想法待批/升格候选的表变更也推送,收件箱 badge 实时刷新
                                    # (此前前端过滤集含 lesson=死过滤、缺 idea=badge 不动)
                "faction", "item", "term", "world_rule"]   # U-002:设定库四类,写入即刷新


_LIVE_MAX = int(os.environ.get("SCRIBE3_LIVE_MAX", "5"))
_live_count: dict[str, int] = {}




def main() -> None:
    import uvicorn
    list_works()   # 确保 main 已登记
    uvicorn.run(app, host="127.0.0.1", port=3321)


if __name__ == "__main__":
    main()

__all__ = [n for n in list(globals()) if not (n.startswith("__") and n.endswith("__"))]


# ----- AUTO_EXTRACTED_ROUTERS (do not register routes here; app.py includes routers) -----
# Handlers re-exported via routers._bind_and_register onto this module for monkeypatch.


# ----- service rebind (architecture split Phase B) -----
def _rebind_services() -> None:
    """Bind service helpers into this module globals for monkeypatch identity."""
    import types
    from scribe3.api.services import (
        write_stream as _svc_write_stream,
        write_assemble as _svc_write_assemble,
        ingest_bg as _svc_ingest_bg,
        pilot_runtime as _svc_pilot_runtime,
        lifecycle as _svc_lifecycle,
    )
    g = globals()
    for mod, names in (
        (_svc_write_stream, ['_work_has_tools', '_write_phase_allows_tools', '_WRITE_VERB_RE', '_is_write_intent', '_stream_write', '_write_snapshot', '_get_write_retriever', '_build_write_retrieval_query', '_write_context_binding', '_save_write_memory_trace', '_save_write_context_outcome', '_WriteOutcomeBinding', '_collect_write']),
        (_svc_write_assemble, ['_faction_prompt_block', '_codex_block', '_editor_system', '_editor_identity_block', '_write_protocol_block', '_write_revision_block', '_editor_write_system', '_voice_anchor_block', '_outline_block', '_deduction_context_segments', '_purpose_and_lessons_write_block', '_brief_must_sections_write_block', '_material_recall_block', '_assemble_write_instructions_v1', '_assemble_write_instructions']),
        (_svc_ingest_bg, ['_refresh_scorecard_after_ingest', '_bg_ingest', '_enqueue_ingest', '_semantic_repair_violations', '_prose_stats']),
        (_svc_pilot_runtime, ['_contextual_review_complete', '_grounding_review', '_pilot_executor', '_pilot_run_bg']),
        (_svc_lifecycle, ['_normalize_lifecycle_id', '_impact_token', '_object_impact', '_delete_object_with_lifecycle', '_archive_object_with_lifecycle']),
    ):
        for name in names:
            fn = getattr(mod, name)
            if isinstance(fn, type):
                g[name] = fn
                continue
            if not callable(fn):
                g[name] = fn
                continue
            reb = types.FunctionType(
                fn.__code__, g, name, fn.__defaults__, fn.__closure__)
            if getattr(fn, "__annotations__", None):
                reb.__annotations__ = dict(fn.__annotations__)
            if getattr(fn, "__kwdefaults__", None):
                reb.__kwdefaults__ = dict(fn.__kwdefaults__)
            if getattr(fn, "__doc__", None):
                reb.__doc__ = fn.__doc__
            g[name] = reb


_rebind_services()
