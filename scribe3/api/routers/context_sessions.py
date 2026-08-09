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
    """读某快照版本的 ContextTurnView(B∪C 检查器数据源)。

    优先 context_turn_bind；再用 memory_trace 补检索明细。无绑定时
    available=false / availability=not_compiled_yet（不画假 0 块）。

    限知红线:secret value 服务端 mask 后才返回。
    session/revision 不存在仍 404/409，不因空态放松隔离。
    """
    from scribe3.store import mask_memory_trace
    from scribe3.context_turn_view import (
        not_compiled_view, view_from_bind_row, merge_memory_trace_into_view,
    )
    store = _store_for(work)
    bind = None
    try:
        bind = store.get_context_turn_bind(session_id, int(revision))
    except Exception:
        bind = None
    trace = store.get_memory_trace_for_snapshot(session_id, int(revision))
    if not bind and not trace:
        try:
            ContextService(store).get(session_id, work, revision=int(revision))
        except (ContextServiceError, StaleContextError) as e:
            raise _context_http_error(e) from e
        return not_compiled_view(session_id=session_id, revision=int(revision))
    if bind:
        _assert_work_binding(bind.get("work") or None, work,
                             kind="context_turn_bind", ident=session_id)
        view = view_from_bind_row(bind, session_id=session_id, revision=int(revision))
        if trace:
            _assert_work_binding(trace.get("work") or None, work,
                                 kind="memory_trace", ident=session_id)
            view = merge_memory_trace_into_view(view, mask_memory_trace(trace))
        return view
    # 仅有旧 memory_trace（无 TurnBind）：升格为兼容 View
    _assert_work_binding(trace.get("work") or None, work,
                         kind="memory_trace", ident=session_id)
    t = mask_memory_trace(trace)
    blocks = []
    bt = t.get("block_tokens") or {}
    for name, tok in (bt.items() if isinstance(bt, dict) else []):
        blocks.append({
            "name": name,
            "token_estimate": int(tok or 0),
            "source_ids": [],
            "source_count": 0,
        })
    return {
        "available": True,
        "availability": "ready",
        "view_version": "context-turn-view.v1",
        "work": t.get("work") or "",
        "context_session_id": t.get("context_session_id") or session_id,
        "session_id": t.get("context_session_id") or session_id,
        "snapshot_revision": int(t.get("snapshot_revision") or revision),
        "task_kind": "draft",
        "path": "write",
        "block_tokens": bt,
        "blocks": blocks,
        "selected": t.get("selected") or [],
        "rejected": t.get("rejected") or [],
        "query": t.get("query") or "",
        "envelope_hash": t.get("envelope_hash") or "",
        "channels": t.get("channels") or {},
    }



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
