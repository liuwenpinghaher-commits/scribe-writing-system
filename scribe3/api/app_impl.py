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

from scribe3.feature_flags import get_flag
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
        from scribe3.ingest_integrity import maybe_heal_ingest_on_connect
        with _stores_lock:
            cached = list(_stores.values())
        for st in cached:
            maybe_heal_ingest_on_connect(st)
    except Exception as e:
        logging.getLogger("scribe3").warning("ingest heal on startup skipped: %s", e)
    # S-2: Changefeed 缓存消费者（flag 关则 no-op）+ A3 factory 双写
    try:
        from scribe3.changefeed_consumer import ChangefeedCacheWorker, changefeed_cache_enabled
        from scribe3.context_cache import set_cache_watch_store_factory

        def _store_factory():
            # GAP-2：changefeed 必须用独立 WS 连接，禁止复用请求路径 _stores 缓存。
            # 共享同一 Surreal WS 会在后台线程与请求线程交叉 query 时卡死 /ready。
            from scribe3.feature_flags import get_flag
            work = (get_flag("SCRIBE3_DEFAULT_WORK") or "main").strip() or "main"
            return SurrealStore(ns="scribe3", db=work)

        if changefeed_cache_enabled():
            set_cache_watch_store_factory(_store_factory)
            _app.state.changefeed_worker = ChangefeedCacheWorker(_store_factory)
            _app.state.changefeed_worker.start()
            logging.getLogger("scribe3").warning("changefeed cache worker started")
    except Exception as e:
        logging.getLogger("scribe3").warning("changefeed worker not started: %s", e)
    try:
        yield
    finally:
        try:
            from scribe3.context_cache import set_cache_watch_store_factory
            set_cache_watch_store_factory(None)
        except Exception:
            pass
        try:
            w = getattr(_app.state, "changefeed_worker", None)
            if w is not None:
                w.stop()
        except Exception:
            pass
        _close_cached_stores()


app = FastAPI(title="scribe3", lifespan=_app_lifespan)


@app.exception_handler(HTTPException)
async def _unify_http_errors(_request: Request, exc: HTTPException):
    from scribe3.feature_flags import flag_truthy
    from scribe3.http_errors import http_error_response
    if not flag_truthy("SCRIBE3_HTTP_ERRORS_UNIFIED"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    return http_error_response(exc.status_code, exc.detail)


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
    "arc_tracking",
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
        # SSOT：chapter_gcd_rest.is_emergency_bypass_chapter_path
        try:
            from scribe3.chapter_gcd_rest import is_emergency_bypass_chapter_path
            if is_emergency_bypass_chapter_path(path):
                return False
        except Exception:
            rest = path[len("/chapters/"):]
            parts = [p for p in rest.split("/") if p]
            if len(parts) == 2 and parts[0].isdigit() and parts[1] in (
                    "archive", "restore", "restore-version",
                    "gcd-fields", "beats-fields", "story-move-plan"):
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
#   · 手动:POST /ingest(作者「反哺设定库」) → 同步 ingest_chapter
#   · 互斥唯一路径 = chapter_lock(op=ingest|loop|…)（见 _acquire_op_mutex）
#   · 多 worker：依赖 DB distributed lock / chapter_lock store 后端
# GAP-1：已移除进程内 _loop_inflight / _chapter_repair_inflight / _pending_ingest 集合。


def _db_lock_on() -> bool:
    try:
        from scribe3.surreal_flags import db_inflight_lock
        return db_inflight_lock()
    except Exception:
        return False


def _chapter_op_busy(work: str, seq: int, op: str = "loop") -> bool:
    """只读忙检：chapter_lock / concurrency_lock 快照（GAP-1 单一真相源）。"""
    try:
        from scribe3.novel_first_surface import is_chapter_op_busy
        return bool(is_chapter_op_busy(op, work, int(seq)))
    except Exception:
        return False


def _acquire_op_mutex(work: str, seq: int, op: str, *, detail: str) -> None:
    """GAP-1：章节操作互斥仅经 chapter_lock（可注入 store → distributed）。"""
    st = None
    try:
        st = _store_for(work)
    except Exception:
        st = None
    from scribe3.chapter_lock import (
        acquire_chapter_lock,
        chapter_lock_busy_http_detail,
    )
    clr = acquire_chapter_lock(op, work, int(seq), store=st)
    if not clr.ok:
        raise HTTPException(
            status_code=409,
            detail=detail or chapter_lock_busy_http_detail(clr),
        )


def _release_op_mutex(work: str, seq: int, op: str) -> None:
    st = None
    try:
        st = _store_for(work)
    except Exception:
        st = None
    try:
        from scribe3.chapter_lock import release_chapter_lock
        release_chapter_lock(op, work, int(seq), store=st)
    except Exception:
        pass


def _acquire_chapter_repair(work: str, seq: int) -> None:
    _acquire_op_mutex(
        work, int(seq), "repair",
        detail=f"第 {seq} 章正在执行质量修复，完成后请重新检查再操作",
    )


def _release_chapter_repair(work: str, seq: int) -> None:
    _release_op_mutex(work, int(seq), "repair")


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
        newborn = False
        if work not in _stores:
            st = SurrealStore(ns="scribe3", db=work)
            st.apply_schema()
            _stores[work] = st
            newborn = True
            while len(_stores) > _STORE_CACHE_MAX:
                _, old = _stores.popitem(last=False)
                old.close()
        else:
            _stores.move_to_end(work)
        st = _stores[work]
    if newborn:
        try:
            from scribe3.ingest_integrity import maybe_heal_ingest_on_connect
            maybe_heal_ingest_on_connect(st)
        except Exception:
            pass
    try:
        from scribe3.pipeline_trace_store import maybe_purge_pipeline_traces
        maybe_purge_pipeline_traces(st, work=work)
    except Exception:
        pass
    try:
        from scribe3.run_card_store import maybe_purge_run_cards
        maybe_purge_run_cards(st, work=work)
    except Exception:
        pass
    return st


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






def _listish(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, tuple):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value]
    return []














def _flag_enabled(name: str) -> bool:
    """统一开关判定门面(委托 context_cache.flag_enabled,单一真值来源)。
    上下文产品三件套默认开(见 settings);显式 env/DB 覆盖可关。"""
    from scribe3 import context_cache
    return context_cache.flag_enabled(name)










_ai_run_trace_write_lock = threading.RLock()
# 同一待审批 Run 可能同时出现在原页面与刷新恢复的页面。Hermes 的 elicitation
# 只能消费一次，故这里按 (work, run) 做条带串行化：首个作者决定落审计后，后到的
# 同决定重放直接幂等返回，不得把正常竞态误报成 approval_failed。
_AI_RUN_APPROVAL_LOCK_STRIPES = tuple(threading.RLock() for _ in range(64))












SCRIBE3_READ_MCP_LABEL = os.environ.get("SCRIBE3_READ_MCP_LABEL", "scribe3_read")
# U-003 真机实测推翻的旧方案(勿重加):曾想引入 SCRIBE3_CHIEF_MCP_LABEL 给主编
# agentic 联查挂 s3_*_reveal 全知孪生工具面,与写作路径"隔离"。真机实测证明
# server_label 根本不是选择器——Hermes 网关把 platform_toolsets.api_server 里
# 所有 MCP server 的工具一律暴露给每个走该网关的请求,label 只是个标签,不做过滤。
# 主编对话(chat_agentic_stream)与限知续写(_stream_write/_collect_write)物理上
# 共用同一个网关进程(:8643),给前者挂 reveal 工具就等于给了后者。故只留这一个
# label;6 把 *_reveal 工具(mcp.py)目前不挂在任何网关 profile 上(见
# _summarize_hermes_runtime 的 gateway_exposes_reveal_tools 自检)。








# 私密字段掩码占位符(唯一真相源):GET 打码用此值,写路径收到此值即视为"未改"(不落库)。
# 前端 F4 防线硬编码同值 '🔒 私密';二者必须一致。
_SECRET_MASK = "🔒 私密"








# ===== 书 =====








# ── 统一设置中心(spec: docs/superpowers/specs/2026-07-12-settings-center-design.md)──






























# ---------------------------------------------------------------------------
# Task 13:Runs 审批前重校验"发起时上下文快照"的判据
# ---------------------------------------------------------------------------































_ai_run_collector_lock = threading.RLock()
_ai_run_collectors: set[tuple[str, str]] = set()
_ai_run_event_subscribers: dict[tuple[str, str], list[Queue]] = {}
_AI_RUN_TERMINAL_STATUSES = {
    "completed", "completed_unverified", "failed", "stopped", "cancelled", "canceled",
}


















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














# ---------------------------------------------------------------------------
# 统一上下文与记忆系统 · Task 6:主编线程(一 work 一连续线程 + 每轮焦点标签)
# GET  /chat/threads               本 work 线程列表(含分支)
# GET  /chat/threads/{id}/messages 该线程全部消息(store.list_thread_messages)
# POST /chat/threads/{id}/fork     显式分支(写 parent_thread_id 建新线程)
# 导航路径绝不调 fork——fork 只在作者显式"另起支线"时触发。
# ---------------------------------------------------------------------------



























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


def _require_memory_fabric():
    """仅当显式关闭 MEMORY_FABRIC 时拒绝 /memory/*(测试隔离/运维关闸)。
    产品默认开 → 不 403。"""
    if not _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1"):
        raise HTTPException(
            status_code=403,
            detail="MEMORY_FABRIC disabled; set SCRIBE3_MEMORY_FABRIC_V1=1 (or remove override) for experience memory",
        )










































# ===== 读(按书)=====


































def _search_hit(q: str, *parts: str | None) -> bool:
    needle = (q or "").strip().lower()
    if not needle:
        return False
    return any(needle in str(p or "").lower() for p in parts)























# ===== 角色弧光:静态锚(五要素)+ arc_plan 里程碑(migration 054)=====








# ===== 设定库 增删改(作者直编,不经 elicitation;非世界状态级别的 agent 写)=====


















































# ===== 世界规则 + 势力(设定完整性)=====






# P1-8:world_rule.scope 合法枚举(对齐 migration 027 的 DB ASSERT);应用层提前 422,
# 不再让非法值走到落库层 ASSERT 才 500。
_WORLD_RULE_SCOPES = {"global", "regional", "faction_specific"}







# CX-Task 3:FactionIn 由 codex_schema 动态生成——见 services.misc_helpers._build_faction_in。
# 在 _rebind_services() 之后赋值 FactionIn / _FACTION_STORAGE_KEYS（见文件末尾）。






















# ===== 物品/道具 + 术语(设置完整性)=====


























# ===== CX-Task 5:通用实体关系表(双向认知 + 主编独知 truth + 时态)=====
# 与上面 /character-relations(锁死 character↔character)是两套独立端点,互不影响。
# entity_relation 的 a/b 是不锁类型的自由字符串实体引用,不走 codex_schema 注册表驱动
# (那是给「一个实体类型的一整份字段表单」用的;本表字段少且固定,直接手写字段清单
# 更直接,与 /character-relations 走 dict body 的既有风格一致)。























# ===== 素材库 material(非正典写作材料;镜像 motif/promise CRUD 形态)=====
# 与设定库(codex=正典)严格分开:不进知识图谱、不被 ingest、不参与限知/伏笔/QC/时间线。

def _check_material_kind(kind: str | None) -> None:
    if kind is not None and kind not in MATERIAL_KINDS:
        raise HTTPException(status_code=422,
                            detail=f"非法素材分类 kind='{kind}'(合法: {list(MATERIAL_KINDS)})")




















# ===== 素材导入(多格式 → AI 切分打标摘要 → 预览确认 → 落库)=====
# 内存热缓存 + Surreal 持久化(一书一 DB);进程重启后仍可从 store 恢复。
_import_jobs: dict = {}   # job_id → {stage, done, total, items, error, work}






def _import_job_save(job_id: str, job: dict) -> None:
    _import_jobs[job_id] = job
    try:
        st = _store_for(job.get("work") or "main")
        st.save_import_job(job_id, job)
    except Exception:
        logging.getLogger("scribe3").warning(
            "import job persist failed job=%s", job_id, exc_info=True)



















































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












def _author_prefs_block_safe() -> str:
    """P3:跨书作者偏好注入(单点——_editor_system 被讨论/agentic/写作全路径复用)。
    语义在 scribe3.author_prefs:文件不存在=空(合法初始态);存在但读失败=抛(fail-loud)。"""
    from scribe3.author_prefs import author_prefs_block
    return author_prefs_block()




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

_DISCUSSION_LOOKUP_DIRECTIVE = (
    "\n\n【作答方式(查阅)】先翻这本书再下判断。不要说『让我查查』然后空停。"
    "信息不够就用只读工具核实；最多查四轮。不要输出写作围栏，不要改库。")








_responses_events = None  # 测试可 monkeypatch

















_FALLBACK_MIN_CHARS = 120  # 兜底散文最短字数阈值(更短的视为讨论)

# P2-a Fix6: 兜底剥离——主编开场白标志词(出现即截断,保留后续散文主体)
_PREAMBLE_SIGNALS = re.compile(
    r"(?:^|\n)(?:好的[,,,。]?\s*|我的处理思路\s*[:：]|处理思路\s*[:：]|思路\s*[:：]|建议\s*[:：]|我来|我将|我会)[^\n]*\n",
    re.MULTILINE,
)
_PREAMBLE_SPLIT = re.compile(
    r"(?:我的处理思路|处理思路|思路\s*[:：]|建议\s*[:：])[^\n]*\n"
)
























_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGES = 6
_MAX_IMG_BYTES = 5 * 1024 * 1024






def _soak_block(seed_words: list[str]) -> str:
    """浸泡种子词注入块:仅当 seed_words 非空时注入,否则返回空串(不发 LLM,pure-cheap)。
    soak() 需要 LLM 调用,不在写作热路径中自动触发;前端可预先调用 soak 后把 seed_words 传进来。"""
    if not seed_words:
        return ""
    return "\n\n## 情绪种子词(浸泡得出,贴此情绪写)\n" + "、".join(str(w) for w in seed_words)








_OUTLINE_BUDGET = 1200   # 大纲/节拍注入字符上限(与 M6 事实注入 1200 预算同量级)
_VOLUME_INTRO_BUDGET = 400  # 卷纲摘要注入字符上限(write_assemble rebind 需在 app_impl 可见)


def _clip(s: str, n: int) -> str:
    """超 n 字截断加省略号(防超长 synopsis/beats 撑爆 prompt)。"""
    return s if len(s) <= n else s[:n] + "…"






def _deduction_block(st, seq: int, *, focalizer: str = "") -> str:
    """草稿期把本章「场景真相 + 各角色限知投影」注入 instructions。
    空(无真相且无投影)→ 返回空串(默认行为不变)。"""
    return "".join(
        text for _, _, text in _deduction_context_segments(
            st, seq, focalizer=focalizer,
        )
    )






def _purpose_workflow_block(st, chapter: int, with_tools: bool = False,
                            work: str | None = None, global_text: str = "") -> str:
    """兼容旧名:生产写路径目的合同 + 教训内联注入。"""
    return _purpose_and_lessons_write_block(
        st, chapter, with_tools, work, global_text=global_text,
    )






# 已废弃的历史观测字段；统一内核不再回退，因此必须恒为 0。
_context_assembler_fallbacks = 0


def _context_assembler_enabled() -> bool:
    """兼容旧调用方：统一内核已启用；这不是用户设置。"""
    return True


# ContextSnapshot.phase 的合法枚举(context_models.PhaseName);写作端点的 phase
# 串("plan"/"draft"/"final"/...)不在此集合的一律降 None,防合成快照校验失败。
_ASSEMBLER_PHASES = {"outline", "beats", "deduce", "draft", "final"}























































# ===== 大纲/卷章树(手稿支数据层,作者工具 F-01 后端)=====













from scribe3.deduce_helpers import DEDUCTION_HEADINGS as _DEDUCTION_HEADINGS
_DEDUCTION_BLANK = "未能从场景真相确认。"










# == 卷 CRUD ==

















# Prefer review.schema.QC_ISSUE_LABELS (god_view/degeneration included)
try:
    from scribe3.review.schema import QC_ISSUE_LABELS as _QC_ISSUE_LABELS
except Exception:  # pragma: no cover
    _QC_ISSUE_LABELS = {
        "repetition": "复读(章内)",
        "cross_repetition": "跨章复读",
        "duplicate_lines": "整句重复",
        "structural": "排比句式",
        "emotion_telling": "情感直说",
        "purple": "辞藻升华",
        "ai_tics": "AI 腔",
        "oversaturation": "过饱和",
        "god_view": "全知/解释口吻",
        "degeneration": "模型退化指纹",
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




                              # 直写情绪不计入 psych_ratio/Gate C
















                              # 透传给 find_emotion_telling/aggregate_ai_grade,
                              # emotion_telling 检出归零、psych_ratio/Gate C 不触发




























































# ─── 选择环 L1 轻路径:2 条策略短变体 → 人点选 → 草稿种子(非三整章) ───





def _select_l1_result_path(work: str, chapter: int):
    """L1 结果旁路文件:与 L2 select_ch 分离,避免覆盖重环元数据。"""
    jp = _loop_journal_path(work, chapter)
    return jp.with_name(jp.name.replace("loop_ch", "select_l1_ch", 1))








# ═══════════ Chapter Pilot(主编主动化 T6/T7/T10):章生命周期驱动器 ═══════════
# 作者=创意总监,主编=执行主编。状态机在 scribe3/pilot.py(纯核可测);此处只做
# executor 绑定(全部复用既有链,禁止新写生成逻辑)+ HTTP 面 + 连写循环。





def _grounding_llm(st, work: str, chapter: int, prompt: str) -> str:
    """事实对齐审查经统一上下文引擎走 Qwen 官方服务，并持久化 Outcome。"""
    return _contextual_review_complete(
        st, work, chapter, "grounding", prompt,
        max_tokens=4096, official_api=True, thinking="disabled",
    )




def _pilot_steer(st, seq: int) -> str:
    raw = (st.get_pilot_steer(seq) if hasattr(st, "get_pilot_steer") else "") or ""
    # D5 质量验收：SCRIBE3_MEMORY_STEER_MODE=minimal 时不把库内长 steer 当设定灌输，
    # 只保留极简冲突句，迫使模型依赖记忆/正典注入（见 memory_must_link）。
    try:
        from scribe3.memory_must_link import is_minimal_steer, minimal_chapter_steer
        if is_minimal_steer():
            ch = st.get_chapter(seq) or {}
            title = (ch.get("title") or f"第{seq}章").strip()
            foc = (ch.get("focalizer") or "").replace("role:", "") or "主角"
            syn = (ch.get("synopsis") or raw or "")[:80]
            return minimal_chapter_steer(seq, title, foc, syn)
    except Exception:
        pass
    return raw






# pilot 自身并发互斥经 chapter_lock(op=pilot)；loop 走 op=loop，不交叉抢同一 key。
_pilot_inflight: set[tuple[str, int]] = set()
_pilot_inflight_lock = threading.Lock()


def _guard_pilot_busy(work: str, seq: int) -> None:
    """R2-3:pilot 非 loop 步在途 / 连写运行中 → 拦 save/dedup/select(防 full_check/deliver
    期间改正文致体检、交付挂旧稿,防双写)。draft_loop 期由 chapter_lock(op=loop) 互斥。"""
    with _pilot_inflight_lock:
        if (work, seq) in _pilot_inflight:
            raise HTTPException(status_code=409, detail=f"第 {seq} 章 pilot 正在推进,请稍候再改")
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中——请先 /pilot/pause 再改本章")








_IDEA_ROUTE_PROMPT = """你是写作系统的想法路由器。作者丢来一句想法,判断它该落到哪:
- outline:关于某未来/当前章"写什么"(剧情走向/场景/事件)→ 给该章定向
- steer:对某章的写法要求(语气/节奏/禁忌,如"别煽情")
- setting:动人物长期设定/世界观(如"老范其实识字""改成三兄妹")
- revise:要改已写好的章的具体内容
- unclear:信息不足,需要问一个澄清问题
只输出 JSON:{"kind":"outline|steer|setting|revise|unclear","target_seq":章号或null,
"note":"一句话复述你的理解","question":"仅 unclear 时给一个澄清问题"}
当前书最新章:{max_ch};作者想法:{text}"""




















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


_LIVE_MAX = int(get_flag("SCRIBE3_LIVE_MAX"))
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






# Request/response models (stable names on this module)
from scribe3.api.models import *  # noqa: F403


def _rebind_services() -> None:
    """Bind service helpers into this module globals for monkeypatch identity."""
    import types
    from scribe3.api.services import (
        ai_run_runtime as _svc_ai_run_runtime,
        hermes_status as _svc_hermes_status,
        ingest_bg as _svc_ingest_bg,
        lifecycle as _svc_lifecycle,
        misc_helpers as _svc_misc_helpers,
        pilot_runtime as _svc_pilot_runtime,
        prompt_blocks as _svc_prompt_blocks,
        thread_helpers as _svc_thread_helpers,
        write_assemble as _svc_write_assemble,
        write_stream as _svc_write_stream,
    )
    g = globals()
    for mod, names in (
        (_svc_ai_run_runtime, ['_serialize_ai_run_approval', '_record_ai_run_trace', '_record_ai_run_event', '_runtime_for_traced_run', '_response_events_iter', '_run_focus_target', '_run_focus_affects', 'RunContextChanged', '_recheck_run_origin_context', '_hermes_approval_choice', '_already_resolved_approval', '_bind_run_origin_context', '_pending_approval_from_trace', '_iter_persisted_ai_run_events', '_ai_run_collector_key', '_remote_terminal_after_pruned_events', '_mark_run_completed_unverified', '_publish_ai_run_event', '_ensure_ai_run_event_collector']),
        (_svc_hermes_status, ['_hermes_profile_config_summary', '_hermes_cron_status', '_profile_by_name', '_profile_has_skill', '_issue', '_summarize_hermes_runtime', '_hermes_runtime_status', '_hermes_runs_runtime', '_run_session_key', '_gateway_security_violations', '_startup_gateway_guard']),
        (_svc_ingest_bg, ['mark_chapter_ingest_status', '_refresh_scorecard_after_ingest', '_bg_ingest', '_enqueue_ingest', '_enqueue_ingest_raw', 'schedule_ingest', '_semantic_repair_violations', '_prose_stats']),
        (_svc_lifecycle, ['_normalize_lifecycle_id', '_impact_token', '_object_impact', '_delete_object_with_lifecycle', '_archive_object_with_lifecycle']),
        (_svc_misc_helpers, ['_FACTION_TYPE_MAP', '_fact_item', '_facts', '_mask_field', '_search_excerpt', '_build_faction_in', '_field_violations', '_import_job_get', '_run_import', '_current_tail_block', '_focalizer_sincerity_block', '_phase_role_block', '_loop_journal_path', '_import_journal_path', '_is_selection_candidate_version', '_PLAYBOOK_PILOT_PHASES', '_CODEX_PILOT_PHASES', '_pilot_uses_official_complete', '_pilot_official_complete', '_pilot_llm_gen', '_pilot_journal']),
        # expand_beats 嵌套在 _pilot_executor 内，rebind 后 __globals__=app_impl，
        # 须把节拍 v2 解析/接地/门闩助手一并注入，否则 NameError: parse_beats_v2_output。
        (_svc_pilot_runtime, [
            '_contextual_review_complete', '_grounding_review',
            '_pilot_executor', '_pilot_run_bg',
            'parse_beats_v2_output', 'parse_beats_v1_lines',
            'grounding_candidate_from_beats', '_beats_from_synopsis_segments',
            '_compose_beats_meta', '_drama_gate_park_if_needed',
        ]),
        (_svc_prompt_blocks, ['_codex_value_repr', '_faction_relation_summary', '_pulse_digest', '_thread_history_for_prompt', '_secret_guard_block', '_load_reveal_secret_ids', '_fact_secret_keys', '_strip_preamble', '_avoid_directive', '_arc_state_block', '_motif_block', '_frame_block', '_recap_block', '_revelation_discipline_block', '_final_reminder', '_final_reminder_full', '_verbatim_deduction_fallback']),
        # is_revision_request is imported by write_assemble_v1; rebind needs it in app_impl globals
        (_svc_thread_helpers, ['_resolve_thread_or_raise', '_editor_turn_context', '_context_memory_metrics', '_capture_turn_memory', '_maybe_summarize_thread', '_summarize_thread_inner', '_ChatTurnLog']),
        # inject_floor_env_enabled + _anti_slop_floor_block：写路径 v1 组装在
        # _assemble_write_instructions_v1 内调用；漏绑会在 rebind 后 NameError，
        # 阻断 reference craft 注入与 craft_use 审计（见 test_assembler_v1_parity）。
        # _pressure_drive_write_block：v1 _render_final_input 在 rebind 后经 LOAD_GLOBAL
        # 解析；漏绑则写组装 NameError（flag 开/关均会调到该 helper）。
        # write_assemble 白名单 SSOT：scribe3.api.services.write_assemble.WRITE_ASSEMBLE_REBIND_NAMES
        (_svc_write_assemble, list(
            getattr(
                _svc_write_assemble,
                "WRITE_ASSEMBLE_REBIND_NAMES",
                (
                    "_assemble_write_instructions_v1",
                    "_assemble_write_instructions",
                    "generation_forbidden_source_kinds",
                    "_record_write_soft_fail",
                ),
            )
        )),
        (_svc_write_stream, ['_visible_usage', '_work_has_tools', '_write_phase_allows_tools', '_WRITE_VERB_RE', '_is_write_intent', '_stream_write', '_write_snapshot', '_get_write_retriever', '_build_write_retrieval_query', '_write_context_binding', '_save_write_memory_trace', '_save_context_turn_bind', '_save_write_context_outcome', '_WriteOutcomeBinding', '_collect_write']),
    ):
        for name in names:
            fn = getattr(mod, name)
            if isinstance(fn, type) or not callable(fn):
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
    # 补 rebound 漏掉的模块私有助手：保持原函数 __globals__，避免
    # FunctionType 改写后找不到同模块邻居（如 _load_reveal_secret_ids）。
    from scribe3.api.services import write_assemble_context as _wac
    from scribe3.api.services import write_assemble_blocks as _wab
    from scribe3.api.services import prompt_blocks as _pb2
    for _mod in (_wac, _wab, _pb2):
        for _name in dir(_mod):
            if not _name.startswith("_") or _name.startswith("__"):
                continue
            if _name in g:
                continue
            _fn = getattr(_mod, _name)
            if callable(_fn):
                g[_name] = _fn


_rebind_services()


def assert_write_path_rebind_ready() -> list[str]:
    """启动/测试用：检查写路径 rebind 后必需符号是否齐全。"""
    from scribe3.api.services.write_assemble import assert_write_assemble_rebind_ready
    return assert_write_assemble_rebind_ready(globals())

# FactionIn 依赖 _build_faction_in（services 重绑之后）
FactionIn = _build_faction_in()
_FACTION_STORAGE_KEYS = frozenset(codex_all_storage_keys("faction"))
