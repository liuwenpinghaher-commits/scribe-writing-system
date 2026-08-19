"""Service helpers extracted from app_impl (architecture split Phase B).

Runtime: ``app_impl._rebind_services()`` rebinds each public function into
``app_impl`` globals (monkeypatch / router rebind).  Do not call these for
side-effectful paths without going through ``scribe3.app`` / ``app_impl``.
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
from typing import Any, Optional


def _visible_usage(usage):
    from scribe3.llm_visible import visible_usage
    return visible_usage(usage) if isinstance(usage, dict) else usage


# Note: function bodies resolve free names via rebound globals on app_impl.
def _work_has_tools(work: str) -> bool:
    """当前请求是否可挂 s3_ MCP 工具。

    H-01 后 mcp.py 的所有 s3_ 工具都支持显式 work 参数,同一 MCP 进程按书缓存
    SurrealStore。故不再用 SCRIBE3_WORK 禁掉非默认书;防串库责任转为提示层硬约束:
    所有 s3_ 调用必须传当前 work。"""
    return True


def _write_phase_allows_tools(phase: str) -> bool:
    """纯生成相位已有完整事实输入，不能让代理式联查抢占输出回合。"""
    return (phase or "").strip().lower() not in {"final", "deduce"}


_WRITE_VERB_RE = re.compile(
    r"写|改|续写|帮我写|重写|把这段|本章|展开|写出来|写一段|续到"
)


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
                  with_tools: bool = True, on_complete=None, on_terminal=None,
                  # U-003:这是限知章续写路径,mcp_server_label 恒 READ,不接受调用方
                  # 覆盖成别的 label——即便将来 *_reveal 全知孪生工具真挂上了某个网关,
                  # 这里也绝不能是那个 label(它们能解锁任意 secret 明文写进续写 prompt,
                  # 台账 U-003 的洞本身)。全仓两个调用点(GET /chat/write、POST
                  # /chat/write)都不传自定义 label,恒用此默认值;门禁见
                  # tests/test_reveal_isolation.py。
                  mcp_server_label: str | None = None,
                  max_tokens: int | None = None):
    if mcp_server_label is None:
        from scribe3.api import app_impl as _core
        mcp_server_label = _core.SCRIBE3_READ_MCP_LABEL
    """共用的写作 SSE 流生成器(GET/POST 复用,P20 DRY)。
    message: str(纯文本) 或 list(含图片附件)。
    expect_proposal: 若为 True 且模型未输出围栏但散文足够长,在流末尾追加兜底 proposal 事件。
    with_tools:H-01 work-scoped MCP 开关;为 True 时 instructions 必须已钉死当前 work。
    on_terminal:任何终态都硬回调一次 ``(trace)``，用于 Outcome；失败必须上抛。
    on_complete:Outcome 成功后的 best-effort UI/chat 回调 ``(ui_text, trace)``；
    一参旧回调继续兼容。"""
    import json as _j
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.llm import hermes_responses_events, official_deepseek_provider_identity
    from scribe3.proposal import ProposalParser
    try:
        bind = getattr(on_terminal, "__self__", None)
        if bind is not None:
            from scribe3.pipeline_trace_hooks import start_llm
            _mt = getattr(bind, "manifest_trace", None)
            _st = getattr(bind, "_store", None)
            from scribe3.pipeline_trace_store import buffer_for
            _buf = buffer_for(str((_mt or {}).get("request_id") or ""))
            start_llm(
                _st, _mt,
                work=getattr(_buf, "work", None) or "main",
                chapter=int(getattr(_buf, "chapter", 0) or 0),
            )
    except Exception:
        logging.getLogger("scribe3").warning("start_llm fail-soft", exc_info=True)
    fn = _responses_events or hermes_responses_events
    # GAP-11：写路径必须 filter_tools=False（默认已关）；显式 phase=write 不 enforce
    adapter = HermesEventAdapter(phase=None, filter_tools=False)
    parser = ProposalParser()
    prop = {"scope": None, "prose": []}
    prop_marks: list[str] = []   # 本轮出过的提案标记(scope+字数),落库口径 D-003
    terminal_seen = False
    terminal_callback_started = False

    # 兜底追踪状态
    saw_proposal = False
    delta_acc: list[str] = []   # UI/对话摘要口径：围栏外文本
    raw_delta_acc: list[str] = []  # 供应商原始 delta：只用于 output_hash，不持久正文
    initial_provider = (
        {"provider": "hermes_gateway", "official": False, "transport": "hermes"}
        if with_tools else official_deepseek_provider_identity()
    )
    trace = {"status": "streaming", "tool_calls": [], "tool_outputs": [],
             "response_id": None, "usage": None, "provider": initial_provider}

    def run_terminal_callbacks() -> None:
        """固定先写硬 Outcome，再做既有 best-effort chat 留痕；全程只执行一次。"""
        nonlocal terminal_callback_started
        if terminal_callback_started:
            return
        terminal_callback_started = True
        trace["output_hash"] = hashlib.sha256(
            "".join(raw_delta_acc).encode("utf-8")
        ).hexdigest()
        try:
            from scribe3.pipeline_trace_hooks import note_llm_output
            _out = "".join(prop.get("prose") or [])
            if not _out.strip():
                _out = "".join(delta_acc)
            note_llm_output(_out)
        except Exception:
            logging.getLogger("scribe3").warning("note_llm_output fail-soft", exc_info=True)
        txt = "".join(delta_acc).strip()
        if prop_marks:
            txt = (txt + "\n" if txt else "") + " ".join(prop_marks)
        if on_terminal is not None:
            on_terminal(trace)
        if on_complete is None:
            return
        try:
            import inspect
            try:
                signature = inspect.signature(on_complete)
                signature.bind(txt, trace)
            except (TypeError, ValueError):
                on_complete(txt)
            else:
                # 先 bind 再调用，避免把回调内部 TypeError 误判为旧签名而重放。
                on_complete(txt, trace)
        except Exception:
            logging.getLogger("scribe3").warning("写作完成回调失败(忽略)", exc_info=True)

    def provider_trace_for_persistence(event: dict) -> dict:
        """只持久安全已知的 provider identity，不信任供应商事件的任意 trace。"""
        if with_tools:
            return {
                "provider": "hermes_gateway",
                "official": False,
                "transport": "hermes",
            }
        raw = event.get("trace")
        if not isinstance(raw, dict):
            return {}
        safe: dict = {}
        for key in ("provider", "api_base", "model", "transport"):
            if isinstance(raw.get(key), str):
                safe[key] = raw[key]
        if isinstance(raw.get("official"), bool):
            safe["official"] = raw["official"]
        return safe

    def observe_provider_metadata(event) -> None:
        """从每个原始事件累积安全元数据，不能等到终态才第一次看。"""
        if not isinstance(event, dict):
            return
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        response_id = event.get("response_id") or response.get("id")
        if isinstance(response_id, str) and response_id:
            trace["response_id"] = response_id
        model = event.get("model") or response.get("model")
        if isinstance(model, str) and model:
            trace["model"] = model
        usage = event.get("usage")
        if not isinstance(usage, dict):
            usage = response.get("usage")
        if isinstance(usage, dict):
            trace["usage"] = _visible_usage(usage)
        provider = provider_trace_for_persistence(event)
        if not with_tools and provider:
            trace["provider"].update(provider)
        raw_trace = event.get("trace")
        if with_tools and isinstance(raw_trace, dict):
            reasoning: dict = {}
            for key in ("provider", "model", "provider_request_id", "response_id"):
                if isinstance(raw_trace.get(key), str) and raw_trace[key]:
                    reasoning[key] = raw_trace[key]
            # Hermes 自身只是网关；只有下游推理供应商证据才进 reasoning 层。
            if reasoning.get("provider") not in (None, "hermes", "hermes_gateway"):
                trace["reasoning_provider"] = reasoning

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
        _stream_kwargs = dict(with_tools=with_tools, store=True, server_label=mcp_server_label)
        if max_tokens is not None:
            _stream_kwargs["max_tokens"] = max_tokens
        for ev in _response_events_iter(fn, message, instructions, **_stream_kwargs):
            if terminal_seen:
                # 第一个 provider 终态是不可变事实；继续排空迭代器，但忽略迟到事件。
                continue
            observe_provider_metadata(ev)
            source_type = (
                ev.get("type") or ev.get("event")
                if isinstance(ev, dict) else None
            )
            if source_type in {"response.incomplete", "response.cancelled"}:
                # Hermes/OpenAI Responses 会显式发送非成功终态；旧 adapter
                # 尚未映射这两类，在 Outcome 咽喉点直接提取真实元数据。
                terminal_seen = True
                response = ev.get("response") if isinstance(ev.get("response"), dict) else {}
                trace["status"] = (
                    "incomplete_stream"
                    if source_type == "response.incomplete"
                    else "cancelled"
                )
                trace["error"] = (
                    response.get("incomplete_details")
                    or response.get("error")
                    or ev.get("error")
                )
                continue
            app_ev = adapter.adapt(ev)
            if app_ev["kind"] == "text.delta":
                from scribe3.llm_visible import strip_thinking_markup
                raw_delta = app_ev.get("delta", "")
                if not isinstance(raw_delta, str):
                    raw_delta = str(raw_delta)
                raw_delta = strip_thinking_markup(raw_delta)
                if not raw_delta:
                    continue
                raw_delta_acc.append(raw_delta)
                yield from drain(parser.feed(raw_delta))
            elif app_ev["kind"] == "tool.started":
                trace["tool_calls"].append({
                    "name": app_ev.get("name", ""),
                    "arguments": app_ev.get("arguments", ""),
                    "call_id": app_ev.get("call_id"),
                })
                try:
                    bind = getattr(on_terminal, "__self__", None)
                    if bind is not None:
                        from scribe3.pipeline_trace_hooks import start_tool
                        from scribe3.pipeline_trace_store import buffer_for
                        _mt = getattr(bind, "manifest_trace", None)
                        _buf = buffer_for(str((_mt or {}).get("request_id") or ""))
                        _sid = start_tool(
                            getattr(bind, "_store", None), _mt, app_ev.get("name", ""),
                            work=getattr(_buf, "work", None) or "main",
                            chapter=int(getattr(_buf, "chapter", 0) or 0),
                        )
                        trace.setdefault("_pt_tools", {})[str(app_ev.get("call_id") or app_ev.get("name"))] = _sid
                except Exception:
                    pass
                yield f"data: {_j.dumps({'tool': app_ev.get('name', '')}, ensure_ascii=False)}\n\n"
            elif app_ev["kind"] == "tool.output":
                trace["tool_outputs"].append({
                    "call_id": app_ev.get("call_id"),
                    "output": app_ev.get("output", ""),
                })
                try:
                    bind = getattr(on_terminal, "__self__", None)
                    _sid = (trace.get("_pt_tools") or {}).get(str(app_ev.get("call_id") or ""))
                    if bind is not None and _sid:
                        from scribe3.pipeline_trace_hooks import end_tool
                        end_tool(getattr(bind, "_store", None), _sid, ok=True)
                except Exception:
                    pass
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
                terminal_seen = True
                if trace["status"] != "failed":
                    trace["status"] = "completed"
                if isinstance(app_ev.get("response_id"), str) and app_ev["response_id"]:
                    trace["response_id"] = app_ev["response_id"]
                if isinstance(app_ev.get("usage"), dict):
                    trace["usage"] = _visible_usage(app_ev["usage"])
                response = ev.get("response") if isinstance(ev, dict) else None
                if isinstance(response, dict) and isinstance(response.get("model"), str):
                    trace["model"] = response["model"]
            elif app_ev["kind"] == "run.failed":
                terminal_seen = True
                trace["status"] = "failed"
                if isinstance(app_ev.get("response_id"), str) and app_ev["response_id"]:
                    trace["response_id"] = app_ev["response_id"]
                trace["error"] = app_ev.get("error")
                response = ev.get("response") if isinstance(ev, dict) else None
                if isinstance(response, dict):
                    trace["usage"] = _visible_usage(response.get("usage"))
                    if isinstance(response.get("model"), str):
                        trace["model"] = response["model"]
        yield from drain(parser.flush())
        if not terminal_seen:
            trace["status"] = "incomplete_stream"
        # 兜底:模型忘写围栏 → 把累积散文包成 chapter 提案末尾推送
        # P2-a Fix6: 剥离首段主编开场白("我的处理思路"/"思路:"/"建议:"等解说),
        # 只把散文主体包进 proposal,避免对话话术混入手稿。
        if trace["status"] == "completed" and expect_proposal and not saw_proposal:
            accumulated = "".join(delta_acc)
            prose_body = _strip_preamble(accumulated)
            if len(prose_body.strip()) >= _FALLBACK_MIN_CHARS:
                prop_marks.append(f"⟦提案 scope=chapter·{len(prose_body)}字·兜底⟧")
                yield (
                    f"data: {_j.dumps({'proposal': {'scope': 'chapter', 'prose': prose_body, 'fallback': True}}, ensure_ascii=False)}\n\n"
                )
        # 正常路径必须在 done 对客户端可见之前先形成不可变 Outcome。
        run_terminal_callbacks()
        if trace["status"] == "failed":
            yield f"data: {_j.dumps({'error': '写作流失败，请重试'}, ensure_ascii=False)}\n\n"
        elif trace["status"] != "completed":
            yield f"data: {_j.dumps({'error': '写作流未完整结束，请重试'}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'
    except GeneratorExit:
        # 只有供应商终态尚未到达时，客户端断开才是 cancelled。
        # response.completed/failed 已到达后在 SSE done 帧处 close，不得
        # 反向篡改已确定的供应商真实终态。
        if not terminal_seen:
            trace["status"] = "cancelled"
        raise
    except Exception as e:
        # 硬 Outcome 回调失败不得被转写成一条普通 SSE error 后吞掉。
        if terminal_callback_started:
            raise
        # provider 明确终态是权威；终态后的 transport/迭代器异常只能告警，
        # 不得反向改写 status/id/usage。随后仍按既定终态形成 Outcome 与 done。
        if terminal_seen:
            logging.getLogger("scribe3").warning(
                "provider 终态后的流异常已忽略: %s", str(e)[:120],
            )
            run_terminal_callbacks()
            if trace["status"] == "failed":
                yield f"data: {_j.dumps({'error': '写作流失败，请重试'}, ensure_ascii=False)}\n\n"
            elif trace["status"] != "completed":
                yield f"data: {_j.dumps({'error': '写作流未完整结束，请重试'}, ensure_ascii=False)}\n\n"
            yield 'data: {"done": true}\n\n'
            return
        # Qwen 官方服务客户端在未见 done 时以带 status 的异常
        # fail-loud；不能因为 Python 出口是 exception 就把真实终态改写为 failed。
        trace["status"] = (
            "incomplete_stream"
            if getattr(e, "status", None) == "incomplete_stream"
            else "failed"
        )
        response_id = getattr(e, "response_id", None)
        if isinstance(response_id, str) and response_id:
            trace["response_id"] = response_id
        usage = getattr(e, "usage", None)
        if isinstance(usage, dict):
            trace["usage"] = _visible_usage(usage)
        if isinstance(getattr(e, "model", None), str):
            trace["model"] = e.model
        identity = getattr(e, "identity", None)
        if identity is not None:
            try:
                from dataclasses import asdict
                trace["provider"] = asdict(identity)
            except (TypeError, ValueError):
                pass
        trace["error"] = str(e)[:160]
        run_terminal_callbacks()
        yield f"data: {_j.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'
    finally:
        # 北极星任务1 + P0门审查 P1-6:落库必须在 finally——客户端断流时 Starlette
        # 在 yield 点抛 GeneratorExit(BaseException,except Exception 接不住),
        # 半截对话也要留痕;本块纯副作用不 yield,GeneratorExit 语义安全(D-004)。
        if not terminal_callback_started:
            run_terminal_callbacks()


def _write_snapshot(st, *, chapter, focalizer, phase, work, memory_trace_ctx=None):
    """为写作/讨论组装 ContextSnapshot。

    B∪C：若请求带真实 context_session_id + revision，注入导航可查键，使
    TurnBind/检查器与 UI 对齐；否则合成 write 占位（synthetic，仅取数坐标）。
    """
    from datetime import datetime, timezone
    from scribe3.context_models import ContextFocus, ContextSnapshot
    try:
        w = _normalize_work(work)  # type: ignore[name-defined]
        phases = _ASSEMBLER_PHASES  # type: ignore[name-defined]
    except NameError:
        from scribe3.api import app_impl as _core
        w = _core._normalize_work(work)
        phases = getattr(_core, "_ASSEMBLER_PHASES", frozenset({
            "outline", "beats", "deduce", "draft", "final", "plan",
        }))
    ph = (phase or "").strip().lower()
    ph = ph if ph in phases else None
    has_ch = chapter is not None
    ctx = memory_trace_ctx or {}
    real_sid = str(ctx.get("context_session_id") or "").strip()
    real_rev = ctx.get("context_revision")
    real_hash = str(ctx.get("context_hash") or "").strip()
    real_thread = str(ctx.get("thread_id") or "").strip()
    synthetic = not (real_sid and real_rev is not None)
    if synthetic:
        session_id, revision, thread_id = "write", 0, f"write:{w}"
        nav_id = f"write:{w}:{chapter}"
        ctx_hash = ""
    else:
        session_id = real_sid
        revision = int(real_rev)
        thread_id = real_thread or f"write:{w}"
        nav_id = f"nav:{real_sid}:{revision}"
        ctx_hash = real_hash
    snap = ContextSnapshot(
        session_id=session_id, work=w, revision=revision, thread_id=thread_id,
        entry="chapter", directory_path=(),
        focus=ContextFocus(type="chapter" if has_ch else "view",
                           id=str(chapter) if has_ch else w,
                           label=focalizer or ""),
        detail_route=f"chapter:{chapter}" if has_ch else "view:book",
        chapter=chapter, phase=ph, focalizer=focalizer or None,
        previous_revision=None, navigation_id=nav_id,
        captured_at=datetime.now(timezone.utc), context_hash=ctx_hash)
    snap = snap.with_hash()
    # 标记供 TurnBind（ContextSnapshot 无该字段时挂到对象旁路 dict 由调用方读 ctx）
    return snap


def _get_write_retriever(st):
    """生产写路径 MemoryRetriever 注入点。

    产品默认 MEMORY_FABRIC 开 → 恒挂 MemoryRetriever(四通道 / RRF / 限知门 / 正典压制)。
    仅显式关(测试隔离)→ None,assembler 降级 store 直查 canonical(非产品 fallback 叙事)。
    捕获侧 _capture_turn_memory 与本注入点同 flag 对称。"""
    try:
        enabled = _flag_enabled("SCRIBE3_MEMORY_FABRIC_V1")  # type: ignore[name-defined]
    except NameError:
        from scribe3.api import app_impl as _core
        enabled = _core._flag_enabled("SCRIBE3_MEMORY_FABRIC_V1")
    if not enabled:
        return None
    from scribe3.memory_retrieval import MemoryRetriever
    return MemoryRetriever(st)


def _build_write_retrieval_query(st, *, chapter, seed_words, request_text: str = "") -> str:
    """I1(Task 16-C):为写作检索拼一个有意义的 query,靶向本章相关经验记忆。

    源优先级(种子词最短、最凝练；作者本轮请求覆盖空章真实写作；章纲只作最后退路):
      ① seed_words —— 本章种子词(_soak_block 同源),空白项剔除后拼接;
      ② 无种子词 → 作者本轮 request_text 截断 200 字；它只参与检索，绝不作为正典或
         事实块注入；
      ③ 无请求 → 章纲 synopsis(get_chapter)截断 200 字,给一个"本章要写什么"的兜底靶向。
    仅在检索器接上(MEMORY_FABRIC 开)时被调用;返回空串则退化为"只出 canonical"的保守行为(不崩)。"""
    parts = [w.strip() for w in (seed_words or []) if isinstance(w, str) and w.strip()]
    if parts:
        return " ".join(parts)[:200]
    request_query = (request_text or "").strip()
    if request_query:
        return request_query[:200]
    try:
        ch = st.get_chapter(chapter) or {}
        syn = (ch.get("synopsis") or "").strip()
        if syn:
            return syn[:200]
    except Exception as e:
        from scribe3.soft_fail import soft_fail
        soft_fail("write_retrieval_query_synopsis", e, logger="scribe3", chapter=chapter)
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


def _save_context_turn_bind(st, *, snap, envelope, work, ctx,
                            task_kind: str = "draft", path: str = "write",
                            manifest_id=None, request_id=None,
                            actual_input_hash=None, policy_version=None,
                            selected=None, rejected=None, query: str = "",
                            usage_digest=None) -> str:
    """B∪C：编译成功后落 TurnBind（检查器主键），best-effort 由调用方 try。"""
    from scribe3.context_turn_view import build_turn_view
    from scribe3.store import build_memory_trace  # noqa: F401 — 仅文档对称

    session_id = str(ctx.get("context_session_id") or "")
    revision = int(ctx.get("context_revision"))
    synthetic = str(getattr(snap, "session_id", "") or "") in ("", "write")
    # selected/rejected：若传入检索结果则映射，否则空
    sel, rej = list(selected or []), list(rejected or [])
    view = build_turn_view(
        session_id=session_id,
        revision=revision,
        work=str(work or ""),
        task_kind=task_kind,
        path=path,
        envelope=envelope,
        manifest_id=manifest_id,
        request_id=request_id,
        actual_input_hash=actual_input_hash,
        policy_version=policy_version,
        envelope_hash=str(getattr(envelope, "envelope_hash", "") or ""),
        selected=sel,
        rejected=rej,
        usage_digest=usage_digest or {},
        query=query or "",
        synthetic_snapshot=synthetic,
    )
    return st.save_context_turn_bind(view)


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


def _save_write_context_outcome(st, envelope_trace: dict, trace: dict):
    """将写作供应商终态绑定到已持久化 Manifest，不保存输出正文。"""
    from scribe3.context_outcome import ContextOutcomeTrace
    from scribe3.context_store import ContextStore

    required = ("request_id", "manifest_id", "actual_input_hash")
    missing = [key for key in required if not envelope_trace.get(key)]
    if missing:
        raise ValueError(f"Outcome 缺少 Manifest 绑定: {', '.join(missing)}")

    raw_status = trace.get("status")
    status = {
        "completed": "succeeded",
        "failed": "failed",
        "incomplete_stream": "incomplete_stream",
        "cancelled": "cancelled",
    }.get(raw_status)
    if status is None:
        raise ValueError(f"未知写作终态: {raw_status!r}")

    provider_identity = trace.get("provider")
    if isinstance(provider_identity, dict):
        provider = provider_identity.get("provider")
        model = trace.get("model") or provider_identity.get("model")
    else:
        provider = provider_identity if isinstance(provider_identity, str) else None
        model = trace.get("model")
    error = trace.get("error")
    raw_usage = trace.get("usage")
    usage = None
    if isinstance(raw_usage, dict):
        # ContextOutcomeTrace 是窄合同：保留供应商顶层数值计量，
        # 不把不定形的嵌套明细整包灌入审计表。
        usage = {
            str(key): value for key, value in raw_usage.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }

    request_id = str(envelope_trace["request_id"])
    manifest_id = str(envelope_trace["manifest_id"])
    actual_input_hash = str(envelope_trace["actual_input_hash"])
    identity = f"{request_id}\0{manifest_id}\0{actual_input_hash}"
    if provider == "hermes_gateway":
        transport_provider = "hermes_gateway"
        reasoning_identity = trace.get("reasoning_provider")
    else:
        transport_provider = (
            provider_identity.get("transport")
            if isinstance(provider_identity, dict) else None
        )
        reasoning_identity = provider_identity
    if isinstance(reasoning_identity, dict):
        reasoning_provider = reasoning_identity.get("provider")
        reasoning_model = reasoning_identity.get("model") or model
        reasoning_request_id = (
            reasoning_identity.get("provider_request_id")
            or reasoning_identity.get("response_id")
        )
    else:
        reasoning_provider = None
        reasoning_model = None
        reasoning_request_id = None
    if provider != "hermes_gateway":
        reasoning_request_id = reasoning_request_id or trace.get("response_id")
    outcome = ContextOutcomeTrace(
        outcome_id=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
        request_id=request_id,
        manifest_id=manifest_id,
        actual_input_hash=actual_input_hash,
        status=status,
        provider=provider,
        model=model if isinstance(model, str) else None,
        provider_request_id=(str(trace["response_id"])
                             if trace.get("response_id") is not None else None),
        transport_provider=(str(transport_provider) if transport_provider else None),
        transport_request_id=(str(trace["response_id"])
                              if trace.get("response_id") is not None else None),
        reasoning_provider=(str(reasoning_provider) if reasoning_provider else None),
        reasoning_model=(str(reasoning_model) if reasoning_model else None),
        reasoning_request_id=(str(reasoning_request_id) if reasoning_request_id else None),
        usage=usage,
        output_hash=trace.get("output_hash"),
        error=error,
    )
    return ContextStore(st).save_outcome(outcome)


def bind_pilot_trace(outcome_binding, st, work: str, seq: int, phase: str) -> bool:
    """入口只看 current_trace_buffer。已绑定=nested：抄 defer_finish，不开链。"""
    from scribe3.pipeline_trace import current_trace_buffer
    from scribe3.pipeline_trace_hooks import open_write_chain

    buf = current_trace_buffer()
    if buf is not None:
        outcome_binding.manifest_trace["request_id"] = getattr(buf, "trace_id", "") or ""
        outcome_binding.manifest_trace["defer_finish"] = True
        return True
    open_write_chain(
        st, outcome_binding.manifest_trace,
        work=work, chapter=int(seq or 1), kind="write", phase=phase or "draft",
    )
    return False


class _WriteOutcomeBinding:
    """一次生成请求的 Manifest 绑定；Outcome 失败属于主链错误，禁止吞掉。"""

    def __init__(self, st):
        self._store = st
        self.manifest_trace: dict = {}

    def persist(self, trace: dict) -> None:
        try:
            outcome = _save_write_context_outcome(self._store, self.manifest_trace, trace)
        except Exception:
            logging.getLogger("scribe3").error(
                "Context Outcome 落库失败，终止本次生成", exc_info=True,
            )
            try:
                from scribe3.pipeline_trace_hooks import finish_failed
                finish_failed(self._store, self.manifest_trace)
            except Exception:
                pass
            raise
        try:
            from scribe3.run_card_store import attach_outcome_to_run_card
            rid = ""
            if isinstance(self.manifest_trace, dict):
                rid = str(self.manifest_trace.get("request_id") or "")
            oid = getattr(outcome, "outcome_id", None) if outcome is not None else None
            status = getattr(outcome, "status", None) if outcome is not None else None
            usage = getattr(outcome, "usage", None) if outcome is not None else None
            if isinstance(outcome, dict):
                oid = outcome.get("outcome_id")
                status = outcome.get("status")
                usage = outcome.get("usage")
            attach_outcome_to_run_card(
                self._store,
                request_id=rid,
                outcome_id=oid,
                status=status,
                usage=usage if isinstance(usage, dict) else None,
            )
        except Exception:
            logging.getLogger("scribe3").warning(
                "attach_outcome_to_run_card fail-soft", exc_info=True,
            )
        try:
            from scribe3.pipeline_trace_hooks import finish_ok
            finish_ok(self._store, self.manifest_trace, outcome=outcome)
        except Exception:
            logging.getLogger("scribe3").warning(
                "pipeline finish_ok fail-soft", exc_info=True,
            )


def _collect_write(message, instructions: str, with_tools: bool = True,
                   on_terminal=None, text_mode: bool = False,
                   max_tokens: int | None = None):
    """同步(非 SSE)写作收集器,loop 编排(北极星任务4)用。与 _stream_write 同一事件源
    (_responses_events 可 monkeypatch)与同一 ProposalParser 语义,只是不产 SSE 帧。
    返回 (围栏外散文, proposals=[{scope, prose}, ...])；text_mode=True 时返回
    供应商完整文本。任何 completed/failed/incomplete/异常均先硬写 Outcome，再返回或抛。"""
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.llm import hermes_responses_events, official_deepseek_provider_identity
    from scribe3.proposal import ProposalParser
    try:
        bind = getattr(on_terminal, "__self__", None)
        if bind is not None:
            from scribe3.pipeline_trace_hooks import start_llm
            from scribe3.pipeline_trace_store import buffer_for
            _mt = getattr(bind, "manifest_trace", None)
            _buf = buffer_for(str((_mt or {}).get("request_id") or ""))
            start_llm(
                getattr(bind, "_store", None), _mt,
                work=getattr(_buf, "work", None) or "main",
                chapter=int(getattr(_buf, "chapter", 0) or 0),
            )
    except Exception:
        logging.getLogger("scribe3").warning("start_llm collect fail-soft", exc_info=True)
    fn = _responses_events or hermes_responses_events
    # GAP-11：写路径必须 filter_tools=False（默认已关）；显式 phase=write 不 enforce
    adapter = HermesEventAdapter(phase=None, filter_tools=False)
    parser = ProposalParser()
    outside: list[str] = []
    raw_delta_acc: list[str] = []
    proposals: list[dict] = []
    cur = {"scope": None, "prose": []}
    initial_provider = (
        {"provider": "hermes_gateway", "official": False, "transport": "hermes"}
        if with_tools else official_deepseek_provider_identity()
    )
    trace = {"status": "streaming", "response_id": None, "usage": None,
             "provider": initial_provider}
    terminal_seen = False
    stream_error: Exception | None = None

    def apply_terminal_metadata(ev: dict, status: str) -> None:
        nonlocal terminal_seen
        terminal_seen = True
        trace["status"] = status
        response = ev.get("response") if isinstance(ev.get("response"), dict) else {}
        if status != "completed":
            trace["error"] = (
                response.get("incomplete_details")
                or response.get("error")
                or ev.get("error")
            )

    def observe_provider_metadata(ev) -> None:
        if not isinstance(ev, dict):
            return
        response = ev.get("response") if isinstance(ev.get("response"), dict) else {}
        response_id = ev.get("response_id") or response.get("id")
        if isinstance(response_id, str) and response_id:
            trace["response_id"] = response_id
        model = ev.get("model") or response.get("model")
        if isinstance(model, str) and model:
            trace["model"] = model
        usage = ev.get("usage")
        if not isinstance(usage, dict):
            usage = response.get("usage")
        if isinstance(usage, dict):
            trace["usage"] = _visible_usage(usage)
        if not with_tools and isinstance(ev.get("trace"), dict):
            for key in ("provider", "api_base", "model", "transport", "official"):
                value = ev["trace"].get(key)
                if isinstance(value, str) or (key == "official" and isinstance(value, bool)):
                    trace["provider"][key] = value
        if with_tools and isinstance(ev.get("trace"), dict):
            raw_trace = ev["trace"]
            reasoning = {
                key: raw_trace[key]
                for key in ("provider", "model", "provider_request_id", "response_id")
                if isinstance(raw_trace.get(key), str) and raw_trace[key]
            }
            if reasoning.get("provider") not in (None, "hermes", "hermes_gateway"):
                trace["reasoning_provider"] = reasoning

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

    # U-003 修复:server_label 硬编码 SCRIBE3_READ_MCP_LABEL,不接受参数、不可被调用方
    # 覆盖——收集式写作(loop 编排/select 环)与 _stream_write 同规矩,绝不能挂
    # s3_*_reveal 全知孪生工具面(否则模型能自己解锁任意 secret 明文写进续写文本)。
    response_kwargs = {
        "with_tools": with_tools,
        "store": True,
        "server_label": SCRIBE3_READ_MCP_LABEL,
    }
    if max_tokens is not None:
        response_kwargs["max_tokens"] = max_tokens
    try:
        for ev in _response_events_iter(fn, message, instructions, **response_kwargs):
            if terminal_seen:
                continue
            observe_provider_metadata(ev)
            source_type = (
                ev.get("type") or ev.get("event")
                if isinstance(ev, dict) else None
            )
            if source_type == "response.incomplete":
                apply_terminal_metadata(ev, "incomplete_stream")
                continue
            if source_type == "response.cancelled":
                apply_terminal_metadata(ev, "cancelled")
                continue
            app_ev = adapter.adapt(ev)
            if app_ev["kind"] == "text.delta":
                from scribe3.llm_visible import strip_thinking_markup
                raw_delta = app_ev.get("delta", "")
                if not isinstance(raw_delta, str):
                    raw_delta = str(raw_delta)
                raw_delta = strip_thinking_markup(raw_delta)
                if not raw_delta:
                    continue
                raw_delta_acc.append(raw_delta)
                drain(parser.feed(raw_delta))
            elif app_ev["kind"] == "run.failed":
                apply_terminal_metadata(ev, "failed")
            elif app_ev["kind"] == "run.completed" and trace["status"] != "failed":
                apply_terminal_metadata(ev, "completed")
    except Exception as error:
        if terminal_seen:
            logging.getLogger("scribe3").warning(
                "provider 终态后的收集异常已忽略: %s", str(error)[:120],
            )
        else:
            stream_error = error
            trace["status"] = (
                "incomplete_stream"
                if getattr(error, "status", None) == "incomplete_stream"
                else "failed"
            )
            response_id = getattr(error, "response_id", None)
            if isinstance(response_id, str) and response_id:
                trace["response_id"] = response_id
            usage = getattr(error, "usage", None)
            if isinstance(usage, dict):
                trace["usage"] = _visible_usage(usage)
            if isinstance(getattr(error, "model", None), str):
                trace["model"] = error.model
            identity = getattr(error, "identity", None)
            if identity is not None:
                try:
                    from dataclasses import asdict
                    trace["provider"] = asdict(identity)
                except (TypeError, ValueError):
                    pass
            trace["error"] = str(error)[:160]
    drain(parser.flush())
    if not terminal_seen and stream_error is None:
        trace["status"] = "incomplete_stream"
        trace["error"] = "LLM 写作流未完整结束"
    trace["output_hash"] = hashlib.sha256(
        "".join(raw_delta_acc).encode("utf-8")
    ).hexdigest()
    try:
        from scribe3.pipeline_trace_hooks import note_llm_output
        _out = ""
        for p in proposals:
            if isinstance(p, dict) and p.get("prose"):
                _out += str(p.get("prose") or "")
        note_llm_output(_out)
    except Exception:
        logging.getLogger("scribe3").warning("note_llm_output collect fail-soft", exc_info=True)
    if on_terminal is not None:
        on_terminal(trace)
    if stream_error is not None:
        raise RuntimeError("LLM 写作流异常，未生成完整候选稿") from None
    if trace["status"] == "failed":
        raise RuntimeError("LLM 写作流失败，未生成完整候选稿")
    if trace["status"] != "completed":
        raise RuntimeError("LLM 写作流未完整结束，未生成完整候选稿")
    if text_mode:
        return "".join(raw_delta_acc).strip()
    return "".join(outside), proposals

