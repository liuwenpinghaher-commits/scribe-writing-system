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

router = APIRouter(tags=['chat_threads'])


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


def chat_threads(work: str = "main", actor_id: str = "author"):
    """本 work 线程列表;顺带保证默认线程存在(首次访问即建,幂等)。"""
    store = _store_for(work)
    store.get_or_create_editorial_thread(work, actor_id)
    return {"threads": store.list_editorial_threads(work)}

def chat_thread_messages(thread_id: str, work: str = "main", limit: int = 500,
                         before_ts: str | None = None):
    """该线程消息(ts 升序)。P0b:before_ts 给定=只取更早(「载入更早」分页游标)。
    Task 16-A:thread_id 内嵌 work(ethread:<work>:<uuid>)——
    落库 work 与请求 ?work= 不符 → 409(否则空 [] 会把越权伪装成"无消息")。"""
    _assert_work_binding(_thread_work(thread_id), work,
                         kind="editorial_thread", ident=thread_id)
    return _store_for(work).list_thread_messages(thread_id, limit=limit,
                                                 before_ts=before_ts)

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

def maintenance_summarize_threads(work: str = "main", threshold: int = 40):
    """P0b/P2:摘要兜底(夜间 cron 调;幂等——阈值内的线程秒过)。逐 active 线程跑
    _maybe_summarize_thread,失败线程如实列在 errors(收件箱/调用方可见,不静默)。"""
    st = _store_for(work)
    results: dict[str, dict] = {}
    for t in st.list_editorial_threads(work):
        if t.get("status") != "active":
            continue
        results[t["thread_id"]] = _maybe_summarize_thread(work, t["thread_id"],
                                                          threshold=threshold)
    return {"threads": len(results),
            "summarized": sum(1 for v in results.values() if v.get("status") == "summarized"),
            "errors": {k: v for k, v in results.items() if v.get("status") == "error"}}

def maintenance_daily_digest(work: str = "main"):
    """P2:每日创作摘报(cron 晨间调)——昨日字数 vs 目标 / 待批积压 / 伏笔健康,
    写 chief_digest 一天一行,决策收件箱消费。零降级:任何一源失败如实进 error 字段
    (收件箱红字),绝不产出"看着完整其实缺项"的假摘报。"""
    from datetime import date
    st = _store_for(work)
    lines: list[str] = []
    errs: list[str] = []
    try:
        p = st.progress(window="30") or {}
        tw, goal = p.get("today_words"), p.get("daily_word_goal")
        streak = p.get("current_streak")
        lines.append(f"字数:今日 {tw if tw is not None else '?'}"
                     + (f" / 目标 {goal}" if goal else "")
                     + (f";连续 {streak} 天" if streak else ""))
    except Exception as e:
        errs.append(f"progress: {str(e)[:80]}")
    try:
        inbox = decision_inbox(work)
        lines.append(f"等你决策:{inbox['count']} 项"
                     + (f"(来源失败:{'/'.join(inbox['degraded_sources'])})" if inbox.get("degraded_sources") else ""))
    except Exception as e:
        errs.append(f"inbox: {str(e)[:80]}")
    try:
        led = promises_ledger(work)
        open_rows = led.get("open") or []
        overdue = sum(1 for r in open_rows if r.get("overdue"))
        lines.append(f"伏笔:未收 {len(open_rows)} 条" + (f",超期 {overdue} 条" if overdue else ""))
    except Exception as e:
        errs.append(f"promises: {str(e)[:80]}")
    body = ";".join(lines) if lines else "(全部来源失败,无可汇总)"
    err = " | ".join(errs) or None
    day = date.today().isoformat()
    st.upsert_chief_digest(day, body, err)
    return {"day": day, "body": body, "error": err}

def chat_thread_export(thread_id: str, format: str = "md", work: str = "main"):
    """P0b:会话导出(借鉴 hermes sessions export 范式)。只含 role/text/ts
    (spec 审核修正#9:不带工具输出,泄密面最小)。"""
    from fastapi.responses import PlainTextResponse
    if format not in ("md", "jsonl"):
        raise HTTPException(status_code=422, detail=f"format 只支持 md|jsonl,收到 {format!r}")
    _assert_work_binding(_thread_work(thread_id), work,
                         kind="editorial_thread", ident=thread_id)
    st = _store_for(work)
    row = st._get_editorial_thread(thread_id)
    if row is None:
        raise HTTPException(status_code=404, detail={
            "code": "thread_not_found", "message": f"线程 '{thread_id}' 不存在"})
    msgs = st.list_thread_messages(thread_id, limit=2000)
    kept = [(m.get("role"), (m.get("text") or "").strip(), str(m.get("ts") or ""))
            for m in msgs if m.get("role") in ("user", "assistant") and (m.get("text") or "").strip()]
    if format == "jsonl":
        body = "\n".join(json.dumps({"role": r, "text": t, "ts": ts}, ensure_ascii=False)
                         for r, t, ts in kept)
        media, ext = "application/jsonl", "jsonl"
    else:
        parts = [f"# {row.get('title') or '主编讨论'}\n"]
        if (row.get("summary") or "").strip():
            parts.append(f"> 早期摘要:{row['summary'].strip()}\n")
        for r, t, ts in kept:
            parts.append(f"**{'作者' if r == 'user' else '主编'}** · {ts}\n\n{t}\n\n---\n")
        body = "\n".join(parts)
        media, ext = "text/markdown", "md"
    fname = f"thread_{thread_id.rsplit(':', 1)[-1][:8]}.{ext}"
    return PlainTextResponse(body, media_type=f"{media}; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{fname}"'})

def chat_thread_create(req: ThreadCreateReq, work: str = "main", actor_id: str = "author"):
    """P0a:显式新建会话(与 GET /chat/threads 的幂等取默认不同,每次都建新线程)。"""
    if req.title is not None and len(req.title) > 60:
        raise HTTPException(status_code=422, detail="标题过长(≤60 字)")
    return _store_for(work).create_editorial_thread(work, actor_id, title=req.title)

def chat_thread_patch(thread_id: str, req: ThreadPatchReq, work: str = "main"):
    """P0a:改名/归档。零降级:线程不存在 404、跨 work 409、非法 status 422。"""
    if req.status is not None and req.status not in ("active", "archived"):
        raise HTTPException(status_code=422,
                            detail=f"非法 status={req.status!r}(active|archived)")
    if req.title is not None and len(req.title) > 60:
        raise HTTPException(status_code=422, detail="标题过长(≤60 字)")
    _assert_work_binding(_thread_work(thread_id), work,
                         kind="editorial_thread", ident=thread_id)
    st = _store_for(work)
    if st._get_editorial_thread(thread_id) is None:
        raise HTTPException(status_code=404, detail={
            "code": "thread_not_found", "message": f"线程 '{thread_id}' 不存在"})
    st.update_editorial_thread_meta(thread_id, title=req.title, status=req.status)
    return st._get_editorial_thread(thread_id)



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['chat_threads']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_threads', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_threads', _re)
    g['chat_threads'] = _re
    router.add_api_route('/chat/threads', _re, methods=['GET'], name='chat_threads')

    _fn = g['chat_thread_messages']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_thread_messages', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_thread_messages', _re)
    g['chat_thread_messages'] = _re
    router.add_api_route('/chat/threads/{thread_id}/messages', _re, methods=['GET'], name='chat_thread_messages')

    _fn = g['chat_thread_fork']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_thread_fork', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_thread_fork', _re)
    g['chat_thread_fork'] = _re
    router.add_api_route('/chat/threads/{thread_id}/fork', _re, methods=['POST'], name='chat_thread_fork')

    _fn = g['maintenance_summarize_threads']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'maintenance_summarize_threads', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'maintenance_summarize_threads', _re)
    g['maintenance_summarize_threads'] = _re
    router.add_api_route('/maintenance/summarize-threads', _re, methods=['POST'], name='maintenance_summarize_threads')

    _fn = g['maintenance_daily_digest']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'maintenance_daily_digest', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'maintenance_daily_digest', _re)
    g['maintenance_daily_digest'] = _re
    router.add_api_route('/maintenance/daily-digest', _re, methods=['POST'], name='maintenance_daily_digest')

    _fn = g['chat_thread_export']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_thread_export', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_thread_export', _re)
    g['chat_thread_export'] = _re
    router.add_api_route('/chat/threads/{thread_id}/export', _re, methods=['GET'], name='chat_thread_export')

    _fn = g['chat_thread_create']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_thread_create', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_thread_create', _re)
    g['chat_thread_create'] = _re
    router.add_api_route('/chat/threads', _re, methods=['POST'], name='chat_thread_create')

    _fn = g['chat_thread_patch']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_thread_patch', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_thread_patch', _re)
    g['chat_thread_patch'] = _re
    router.add_api_route('/chat/threads/{thread_id}', _re, methods=['PATCH'], name='chat_thread_patch')

_bind_and_register()
