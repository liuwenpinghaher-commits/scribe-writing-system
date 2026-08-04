"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import types
from typing import Any, Optional, List, Dict, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Body,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

router = APIRouter(tags=['context_sessions'])


# Import app_impl constants/models used as signature defaults (late-safe for helpers).
def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith('__'):
            continue
        if k not in g:
            g[k] = v
try:
    _import_core_defaults()
except Exception:
    pass  # core may be partially init during first import cycle


def context_session_create(req: ContextSessionCreateReq, work: str = "main"):
    """开上下文会话:落 revision=0 初始快照并返回(session 与快照同事务,无中间态)。
    P0a:body 带 thread_id 时快照绑该会话线程(零降级:无效 404 / 归档 409,不回落)。"""
    w = (req.work or work).strip() or "main"
    _resolve_thread_or_raise(w, req.thread_id)
    return _store_for(w).create_context_session(w, req.actor_id, req.device_id,
                                                thread_id=req.thread_id)

def context_session_get(session_id: str, work: str = "main"):
    """读会话当前快照(含 revision/context_hash,前端绑定 LLM 调用的三件套来源)。"""
    try:
        return ContextService(_store_for(work)).get(session_id, work)
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e

def context_session_navigate(session_id: str, intent: NavigationIntent, work: str = "main"):
    """CAS 推进上下文(body 为 NavigationIntent 形状)。失配 409 stale_context
    (带 latest 供前端直接对齐);同 navigation_id 幂等重放(store 合同)。"""
    try:
        return ContextService(_store_for(work)).navigate(
            session_id, work, intent.model_dump(mode="json"))
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e

def context_snapshot_get(session_id: str, revision: int, work: str = "main"):
    """读历史版快照(回放/审计);该 revision 不存在 → 404 context_snapshot_not_found。"""
    try:
        return ContextService(_store_for(work)).get(session_id, work, revision=revision)
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e

def context_trace_get(session_id: str, revision: int, work: str = "main"):
    """读某快照版本的记忆溯源 trace(Task 14 上下文检查器数据源):主编到底看到了
    什么、为什么选这条记忆、为什么弃那条。

    限知红线:私密事实的 value 在服务端【权威屏蔽】后才返回(前端不可信,Task 7 教训)——
    store.get_memory_trace_for_snapshot 落库时已屏蔽,此处再过一遍 mask_memory_trace 兜底。

    诚实边界:新会话/新快照在首次检索前本来就没有 trace。这是可预期的资源状态，
    不是网络错误：返回 ``available=false``，让自动加载的 ContextInspector 不制造
    浏览器 404 噪声，也不把“尚未检索”伪装成“没有相关事实”。

    但 session/revision 必须先由 ContextService 按 work 验证；不存在或跨书的快照
    仍按既有安全语义返回 404/409，绝不因空 trace 放松隔离。"""
    from scribe3.store import mask_memory_trace
    store = _store_for(work)
    trace = store.get_memory_trace_for_snapshot(session_id, int(revision))
    if not trace:
        # 只有“没有 trace”时才需要确认它确实是一个现存快照的正常空态。
        # 已持久化 trace 的回放/历史迁移数据可独立于 context_session 存在；先强制
        # ContextService 会错误地让这些可审计证据变成 404，破坏既有 API 合同。
        try:
            ContextService(store).get(session_id, work, revision=int(revision))
        except (ContextServiceError, StaleContextError) as e:
            raise _context_http_error(e) from e
        return {
            "available": False,
            "session_id": session_id,
            "snapshot_revision": int(revision),
            "reason": "not_retrieved_yet",
        }
    # Task 16-A:memory_trace 落库 work 与请求 ?work= 比对(空 work=旧数据→不判,走 mask)。
    _assert_work_binding(trace.get("work") or None, work,
                         kind="memory_trace", ident=session_id)
    return mask_memory_trace(trace)



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['context_session_create']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'context_session_create', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'context_session_create', _re)
    g['context_session_create'] = _re
    router.add_api_route('/context/sessions', _re, methods=['POST'], name='context_session_create')

    _fn = g['context_session_get']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'context_session_get', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'context_session_get', _re)
    g['context_session_get'] = _re
    router.add_api_route('/context/sessions/{session_id}', _re, methods=['GET'], name='context_session_get')

    _fn = g['context_session_navigate']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'context_session_navigate', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'context_session_navigate', _re)
    g['context_session_navigate'] = _re
    router.add_api_route('/context/sessions/{session_id}/navigate', _re, methods=['POST'], name='context_session_navigate')

    _fn = g['context_snapshot_get']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'context_snapshot_get', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'context_snapshot_get', _re)
    g['context_snapshot_get'] = _re
    router.add_api_route('/context/sessions/{session_id}/snapshots/{revision}', _re, methods=['GET'], name='context_snapshot_get')

    _fn = g['context_trace_get']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'context_trace_get', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'context_trace_get', _re)
    g['context_trace_get'] = _re
    router.add_api_route('/context/sessions/{session_id}/trace/{revision}', _re, methods=['GET'], name='context_trace_get')

_bind_and_register()
