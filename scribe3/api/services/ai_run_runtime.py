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

from fastapi import (
    APIRouter, BackgroundTasks, File, Form, HTTPException, Query, Request,
    UploadFile, Body, Header, Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator


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

