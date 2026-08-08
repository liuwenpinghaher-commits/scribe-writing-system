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

router = APIRouter(tags=['memory'])


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


def memory_prefetch(req: MemoryPrefetchReq, work: str = "main"):
    """检索本 work 记忆,返回组装好的记忆块文本(供直连 Hermes 会话注入 prompt)。

    讨论模式组装(无章 → 限知门 fail-open,作者全知视角):canonical 命题 + 经验记忆,
    work 隔离 / 秘密屏蔽在检索·组装链内生效。
    组装失败 fail-loud(500),不得用空串冒充「没有记忆」。
    产品默认 fabric 开;仅显式关 → 403。"""
    _require_memory_fabric()
    w = _normalize_work(work)
    _assert_work_binding(_thread_work(req.thread_id), w,
                         kind="editorial_thread", ident=req.thread_id or "")
    store = _store_for(w)
    from scribe3.context_assembler import ContextAssembler, render_envelope_text
    from scribe3.memory_retrieval import MemoryRetriever
    try:
        snap = _write_snapshot(store, chapter=None, focalizer=None, phase=None, work=w)
        # 可选 chapter/focalizer：写预览用（req 上若有则带上）
        ch = getattr(req, "chapter", None)
        foc = getattr(req, "focalizer", None) or ""
        if ch is not None or foc:
            try:
                snap = _write_snapshot(
                    store, chapter=ch, focalizer=foc or None, phase="draft", work=w)
            except Exception:
                pass
        envelope = ContextAssembler(store, MemoryRetriever(store)).assemble(
            snap, req.query or "", "discussion" if not foc else "write")
        context = render_envelope_text(envelope)
        from scribe3.context_assembler import envelope_trace_manifest
        manifest = envelope_trace_manifest(envelope)
        usage = manifest.get("usage_digest") or {}
    except Exception as e:
        logging.getLogger("scribe3").error(
            "/memory/prefetch 组装失败(fail-loud)", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"memory prefetch assemble failed: {e}",
        ) from e
    return {
        "context": context or "",
        "work": w,
        "empty": not bool((context or "").strip()),
        # D7：作者可见「本轮会用到哪些记忆」摘要（无秘密 value）
        "usage_digest": usage,
    }


def memory_usage_preview(req: MemoryPrefetchReq, work: str = "main"):
    """D7：只返回 usage_digest（本轮记忆/正典来源人话摘要），不返回整段 context。

    供前端轻量展示「记忆在扛什么」；组装失败 fail-loud。
    """
    _require_memory_fabric()
    w = _normalize_work(work)
    _assert_work_binding(_thread_work(req.thread_id), w,
                         kind="editorial_thread", ident=req.thread_id or "")
    store = _store_for(w)
    from scribe3.context_assembler import ContextAssembler, envelope_trace_manifest
    from scribe3.memory_retrieval import MemoryRetriever
    try:
        ch = getattr(req, "chapter", None)
        foc = getattr(req, "focalizer", None) or None
        snap = _write_snapshot(
            store, chapter=ch, focalizer=foc, phase="draft" if ch else None, work=w)
        mode = "write" if (ch or foc) else "discussion"
        envelope = ContextAssembler(store, MemoryRetriever(store)).assemble(
            snap, req.query or "", mode)
        digest = envelope_trace_manifest(envelope).get("usage_digest") or {}
    except Exception as e:
        logging.getLogger("scribe3").error(
            "/memory/usage-preview 组装失败(fail-loud)", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"memory usage preview failed: {e}",
        ) from e
    return {"work": w, "usage_digest": digest}

def memory_capture_turn(req: MemoryCaptureTurnReq, work: str = "main"):
    """幂等捕获一轮对话为经验记忆(同步 drain)。event_id 幂等键:同 event_id 二次→idempotent。

    捕获作者意图文本(user 优先,空则退 assistant);分类/正典红线/linked_ids 领域反查在
    MemoryCapture 内。捕获失败 fail-loud(500),不得用 capture_failed 假绿。
    产品默认 fabric 开;仅显式关 → 403。"""
    _require_memory_fabric()
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
    except Exception as e:
        logging.getLogger("scribe3").error(
            "/memory/capture-turn 捕获失败(fail-loud)", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"memory capture failed: {e}",
        ) from e
    return {"status": result.get("status"),
            "idempotent": bool(result.get("idempotent")),
            "event_id": ev_id, "work": w}

def memory_flush(req: MemoryFlushReq, work: str = "main"):
    """固化线程工作摘要 + drain 掉线残留(Hermes on_pre_compress / on_session_end 触发)。
    幂等:working_summary 按 (work,thread) 唯一 UPSERT。
    U-011(作者要 fail-loud):删"失败降级 through_turn=0 却仍返 status=flushed"——那是响应体
    主动撒谎(Hermes 钩子据此以为摘要已安全落库,实际可能丢)。固化失败直接抛(500),诚实。
    MEMORY_FABRIC 关 → 403。"""
    _require_memory_fabric()
    w = _normalize_work(work)
    _assert_work_binding(_thread_work(req.thread_id), w,
                         kind="editorial_thread", ident=req.thread_id or "")
    store = _store_for(w)
    from scribe3.memory_capture import MemoryCapture
    result = MemoryCapture(store).consolidate_thread(req.thread_id, work=w)
    return {"status": "flushed", "reason": req.reason, "work": w,
            "through_turn": result.get("through_turn", 0)}

def memory_list_pending_claims(work: str = "main", status: str = "pending"):
    """列待审正典揭示(默认 pending)。不写经验记忆,但属 fabric 产品面 → 同 flag。"""
    _require_memory_fabric()
    w = _normalize_work(work)
    return {"claims": _store_for(w).list_pending_authority_claims(work=w, status=status or None),
            "work": w}

def memory_resolve_pending_claim(claim_id: str, req: PendingClaimResolveReq,
                                 work: str = "main"):
    """关闭待审:approve 写入 proposition 正典;reject 仅改 status。
    MEMORY_FABRIC 关 → 403。approve 走 store.add_fact 正典路径。"""
    _require_memory_fabric()
    w = _normalize_work(work)
    st = _store_for(w)
    try:
        out = st.resolve_pending_authority_claim(
            claim_id, req.decision,
            valid_from=req.valid_from, secret=req.secret)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    out["work"] = w
    return out



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['memory_prefetch']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'memory_prefetch', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'memory_prefetch', _re)
    g['memory_prefetch'] = _re
    router.add_api_route('/memory/prefetch', _re, methods=['POST'], name='memory_prefetch')

    _fn = g['memory_usage_preview']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'memory_usage_preview', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'memory_usage_preview', _re)
    g['memory_usage_preview'] = _re
    router.add_api_route('/memory/usage-preview', _re, methods=['POST'], name='memory_usage_preview')

    _fn = g['memory_capture_turn']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'memory_capture_turn', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'memory_capture_turn', _re)
    g['memory_capture_turn'] = _re
    router.add_api_route('/memory/capture-turn', _re, methods=['POST'], name='memory_capture_turn')

    _fn = g['memory_flush']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'memory_flush', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'memory_flush', _re)
    g['memory_flush'] = _re
    router.add_api_route('/memory/flush', _re, methods=['POST'], name='memory_flush')

    _fn = g['memory_list_pending_claims']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'memory_list_pending_claims', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'memory_list_pending_claims', _re)
    g['memory_list_pending_claims'] = _re
    router.add_api_route('/memory/pending-claims', _re, methods=['GET'], name='memory_list_pending_claims')

    _fn = g['memory_resolve_pending_claim']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'memory_resolve_pending_claim', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'memory_resolve_pending_claim', _re)
    g['memory_resolve_pending_claim'] = _re
    router.add_api_route('/memory/pending-claims/{claim_id}/resolve', _re, methods=['POST'], name='memory_resolve_pending_claim')

_bind_and_register()
