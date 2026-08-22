"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import types
from typing import Any, Optional, List, Dict, Literal

from scribe3.feature_flags import get_flag

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

router = APIRouter(tags=['misc_routes'])


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


def get_progress(work: str = "main", window: str = "all"):
    """日字数序列 + 累计曲线 + streak + 目标完成度(只读,数据源 daily_progress 表)。
    window: '30' | '90' | 'all'(默认 all)——仅影响图表区间,streak/heatmap 始终全量。"""
    return _store_for(work).progress(window=window)

def chat_stream(msg: str, background: BackgroundTasks, work: str = "main",
                seq: int | None = None, thread: str | None = None,
                context_session_id: str | None = None,
                context_revision: int | None = None,
                context_hash: str | None = None):
    """主编对话(SSE 流式)。B∪C：系统上下文经 discussion 单编译；可选 session 绑定落 TurnBind。
    seq(时机C):当前讨论章号,注入脉搏速览。
    U-005:讨论留痕；U-009:history 续接。"""
    from scribe3.llm import hermes_complete_stream
    from scribe3.api.services.write_assemble import assemble_discussion_system
    from scribe3.llm_path_guard import assert_llm_path_ok
    # GAP-12：讨论路径必须走 Hermes；旁路可观测并 soft-block
    _path_chk = assert_llm_path_ok(hermes_complete_stream, path="discuss")
    if _path_chk.get("bypass"):
        logging.getLogger("scribe3").error(
            "GAP-12 discuss LLM bypass blocked fn=%s", _path_chk.get("fn"),
        )
        from scribe3.api.sse import sse_response

        def _deny():
            yield f"data: {json.dumps({'error': 'LLM path must be Hermes (GAP-12)', 'bypass': True}, ensure_ascii=False)}\n\n"
            yield 'data: {"done": true}\n\n'
        return sse_response(_deny())
    st = _store_for(work)
    thread_id = _editor_turn_context(
        work, thread_row=_resolve_thread_or_raise(work, thread)).thread_id
    background.add_task(_maybe_summarize_thread, work, thread_id)
    _ctx = {
        "context_session_id": context_session_id,
        "context_revision": context_revision,
        "context_hash": context_hash,
        "thread_id": thread_id,
    }

    def gen():
        try:
            import time as _time
            _t0 = _time.perf_counter()
            pulse = _pulse_digest(st, seq)
            history = _thread_history_for_prompt(st, thread_id)
            sysmsg = assemble_discussion_system(
                st, work=work, chapter=seq, user_msg=msg,
                memory_trace_ctx=_ctx if _ctx.get("context_session_id") else None,
                pulse_text=pulse,
                directive_text=_DISCUSSION_DIRECTIVE,
                history=history,
            )
            try:
                from scribe3.context_cache import record_discuss_assembly
                record_discuss_assembly(
                    (_time.perf_counter() - _t0) * 1000.0,
                    len(sysmsg or ""),
                    chapter=seq,
                    work=work,
                    thread_id=thread_id,
                )
            except Exception:
                pass
        except Exception as e:
            logging.getLogger("scribe3").error("chat_stream 上下文组装失败", exc_info=True)
            yield f"data: {json.dumps({'error': f'上下文组装失败:{type(e).__name__}: {str(e)[:200]}'}, ensure_ascii=False)}\n\n"
            yield 'data: {"done": true}\n\n'
            return
        from scribe3.pipeline_trace_hooks import (
            begin_discuss_trace, end_discuss_trace, note_discuss_step,
        )
        dtrace = begin_discuss_trace(st, work=work, chapter=seq)
        note_discuss_step(
            "discuss.assemble", name="discuss.assemble.in",
            body=sysmsg or "", summary=f"前置 {len(sysmsg or '')} 字",
            kind="prompt",
        )
        with _ChatTurnLog(st, user_text=msg, chapter=seq or 0, stage="discuss",
                          thread_id=thread_id) as clog:
            try:
                for delta in hermes_complete_stream(msg, system=sysmsg, history=history):
                    clog.feed(delta)
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                end_discuss_trace(st, dtrace, ok=False, err=e)
                yield 'data: {"done": true}\n\n'
                return
        note_discuss_step(
            "discuss.answer", name="discuss.answer",
            body=clog.collected_text(), summary=f"回答 {len(clog.collected_text())} 字",
        )
        end_discuss_trace(st, dtrace, ok=True)
        yield 'data: {"done": true}\n\n'

    from scribe3.api.sse import sse_response
    return sse_response(gen())

def chat_agentic_stream(msg: str, background: BackgroundTasks, work: str = "main",
                        seq: int | None = None, thread: str | None = None,
                        context_session_id: str | None = None,
                        context_revision: int | None = None,
                        context_hash: str | None = None):
    """主编讨论查阅(SSE):零 MCP Responses + Scribe 进程内闭集只读工具。
    事件:tool(查阅中)/delta/done。失败不改打 /chat/stream。"""
    from scribe3.discuss_lookup_loop import discuss_lookup_events
    from scribe3.llm import HERMES_DISCUSS, hermes_responses_events
    from scribe3.llm_path_guard import assert_llm_path_ok
    fn = _responses_events or hermes_responses_events
    _ag_chk = assert_llm_path_ok(fn, path="agentic")
    if _ag_chk.get("bypass"):
        logging.getLogger("scribe3").error(
            "GAP-12 agentic LLM bypass blocked fn=%s", _ag_chk.get("fn"),
        )
        from scribe3.api.sse import sse_response

        def _deny_ag():
            yield f"data: {json.dumps({'error': 'LLM path must be Hermes (GAP-12)', 'bypass': True}, ensure_ascii=False)}\n\n"
            yield 'data: {"done": true}\n\n'
        return sse_response(_deny_ag())

    turn = _editor_turn_context(work, thread_row=_resolve_thread_or_raise(work, thread))
    st = _store_for(work)
    background.add_task(_maybe_summarize_thread, work, turn.thread_id)
    _ctx = {
        "context_session_id": context_session_id,
        "context_revision": context_revision,
        "context_hash": context_hash,
        "thread_id": turn.thread_id,
    }

    def _build_instructions() -> str:
        import time as _time
        from scribe3.api.services.write_assemble import assemble_discussion_system
        _t0 = _time.perf_counter()
        history = _thread_history_for_prompt(st, turn.thread_id)
        tools_hint = (
            _s3_work_scope_block(work) + (
                "\n\n你能调用只读工具翻当前打开的这本书"
                "（s3_setting_completeness / s3_list_promises / s3_resolve_entities / "
                "s3_character_state / s3_get_chapter / s3_semantic_recall / "
                "s3_chapter_recall / s3_list_chapters）。"
                "先核实再下判断。工具由服务钉死当前书，传错书名也会被丢掉。"
                "不要调用写/生成/揭密工具。"
            )
        )
        ins = assemble_discussion_system(
            st, work=work, chapter=seq, user_msg=msg,
            memory_trace_ctx=_ctx if _ctx.get("context_session_id") else None,
            pulse_text=_pulse_digest(st, seq),
            directive_text=_DISCUSSION_LOOKUP_DIRECTIVE,
            with_tools_hint=tools_hint,
            history=history,
        )
        if not turn.previous_response_id and history:
            lines = ["【近窗对话】"]
            for m in history:
                role = "作者" if m.get("role") == "user" else "主编"
                lines.append(f"{role}：{(m.get('content') or '')[:800]}")
            ins = ins + "\n\n" + "\n".join(lines)
        try:
            from scribe3.context_cache import record_discuss_assembly
            record_discuss_assembly(
                (_time.perf_counter() - _t0) * 1000.0,
                len(ins or ""),
                chapter=seq,
                work=work,
                thread_id=turn.thread_id,
                path="agentic",
            )
        except Exception:
            pass
        return ins

    def gen():
        resp_id = None
        try:
            instructions = _build_instructions()
        except Exception as e:
            logging.getLogger("scribe3").error("chat_agentic_stream 上下文组装失败", exc_info=True)
            yield f"data: {json.dumps({'error': f'上下文组装失败:{type(e).__name__}: {str(e)[:200]}'}, ensure_ascii=False)}\n\n"
            yield 'data: {"done": true}\n\n'
            return
        from scribe3.pipeline_trace_hooks import (
            begin_discuss_trace, end_discuss_trace, note_discuss_step,
        )
        dtrace = begin_discuss_trace(st, work=work, chapter=seq)
        note_discuss_step(
            "discuss.assemble", name="discuss.assemble.in",
            body=instructions or "", summary=f"前置 {len(instructions or '')} 字",
            kind="prompt",
        )
        with _ChatTurnLog(st, user_text=msg, chapter=seq or 0, stage="discuss",
                          thread_id=turn.thread_id) as clog:
            try:
                events = discuss_lookup_events(
                    msg,
                    instructions,
                    work=work,
                    api_base=HERMES_DISCUSS,
                    session_key=turn.session_key,
                    conversation=turn.conversation_id,
                    previous_response_id=turn.previous_response_id,
                    store=True,
                    context_revision=context_revision,
                    context_hash=context_hash,
                )
                for app_ev in events:
                    kind = app_ev.get("kind")
                    if kind == "text.delta":
                        d = app_ev.get("delta", "")
                        if d:
                            clog.feed(d)
                            yield f"data: {json.dumps({'delta': d}, ensure_ascii=False)}\n\n"
                    elif kind == "tool.blocked":
                        yield f"data: {json.dumps({'tool_blocked': app_ev.get('name', ''), 'reason': app_ev.get('reason'), 'phase': app_ev.get('phase')}, ensure_ascii=False)}\n\n"
                    elif kind == "looking_up":
                        yield f"data: {json.dumps({'looking_up': True}, ensure_ascii=False)}\n\n"
                    elif kind == "tool.started":
                        yield f"data: {json.dumps({'tool': app_ev.get('name', ''), 'tool_args': app_ev.get('arguments', '')}, ensure_ascii=False)}\n\n"
                    elif kind == "tool.output":
                        out = str(app_ev.get("output") or "")
                        nm = str(app_ev.get("name") or "tool")
                        note_discuss_step(
                            "discuss.lookup", name=f"discuss.lookup.{nm}",
                            body=out[:800], summary=nm,
                        )
                        yield f"data: {json.dumps({'tool_output': app_ev.get('output', ''), 'tool_call_id': app_ev.get('call_id')}, ensure_ascii=False)}\n\n"
                    elif kind == "approval.requested":
                        yield f"data: {json.dumps({'approval': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'message')}}, ensure_ascii=False)}\n\n"
                    elif kind == "approval.resolved":
                        yield f"data: {json.dumps({'approval_resolved': {k: app_ev.get(k) for k in ('run_id', 'approval_id', 'decision')}}, ensure_ascii=False)}\n\n"
                    elif kind in ("run.completed", "lookup.done"):
                        resp_id = app_ev.get("response_id") or resp_id
                        if resp_id:
                            clog.set_response_id(resp_id)
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
                end_discuss_trace(st, dtrace, ok=False, err=e)
                if resp_id:
                    try:
                        _store_for(work).update_thread_response_id(turn.thread_id, resp_id)
                    except Exception:
                        logging.getLogger("scribe3").warning("thread response_id 回写失败(忽略)", exc_info=True)
                yield 'data: {"done": true}\n\n'
                return
        note_discuss_step(
            "discuss.answer", name="discuss.answer",
            body=clog.collected_text(), summary=f"回答 {len(clog.collected_text())} 字",
        )
        end_discuss_trace(st, dtrace, ok=True)
        if resp_id:
            try:
                # UI busy 互斥；仅回写本 turn 拿到的 response id。
                _store_for(work).update_thread_response_id(turn.thread_id, resp_id)
            except Exception:
                logging.getLogger("scribe3").warning("thread response_id 回写失败(忽略)", exc_info=True)
        yield 'data: {"done": true}\n\n'

    from scribe3.api.sse import sse_response
    return sse_response(gen())

def chat_messages(chapter: int | None = None, limit: int = 500, work: str = "main"):
    """会话留痕回看(北极星任务1):按章拉 chat_message,ts 升序。
    复盘蒸馏(任务8)与「当初为什么这么定」的翻账都从这里读。
    GET /chat/write(兼容端点,无生产调用方)不落 chat_message，但会落 Manifest/Outcome。"""
    return _store_for(work).list_chat_messages(chapter=chapter, limit=limit)

def get_project_tree(work: str = "main"):
    """混合 Binder 项目树(作者工具 F-06):手稿支(卷→章→场景)+ 素材支(分类→条目)
    + 横切视图清单。只读统一投影,只回身份+角标,详情按 ref 懒加载。"""
    return _store_for(work).project_tree()

def issue_ledger(chapter: int | None = Query(default=None, ge=1), work: str = "main"):
    """校验台账 Phase A/B：Track D 多源 + coverage；永不在本路径同步 LLM。

    Phase A：qc（全可映射键含 god_view/degeneration）+ leaks + causal + secret_without_markers。
    Phase B：若 chapter_review 旁表 prose_fp 匹配，合并 L 轨 findings。
    """
    from scribe3.review.ledger import build_phase_a_ledger, build_work_scope_faction_ledger
    from scribe3.review.normalize import normalize_issues
    from scribe3.review.snapshot import load_chapter_review

    st = _store_for(work)
    seqs = [chapter] if chapter is not None else [int(c["seq"]) for c in st.list_chapters()]
    # 全书扫描限制在合理范围，避免超大响应
    if chapter is None and len(seqs) > 80:
        seqs = seqs[-80:]

    all_issues = []
    all_degraded = []
    coverages = []

    def _qc(seq: int):
        return qc(seq, work)

    def _causal(seq: int):
        return causal(seq, work)

    # 全书 scope：势力一致性只扫一次（不按章重复、不用 chapter=0）
    if chapter is None:
        try:
            fac = build_work_scope_faction_ledger(st)
            all_issues.extend(fac.get("issues") or [])
        except Exception as e:
            all_degraded.append({"source": "faction", "reason": str(e)[:200]})

    for seq in seqs:
        led = build_phase_a_ledger(store=st, seq=seq, qc_fn=_qc, causal_fn=_causal)
        issues = list(led.get("issues") or [])
        degraded = list(led.get("degraded_sources") or [])
        coverage = dict(led.get("coverage") or {})

        # Phase B: merge L snapshot when fp matches
        try:
            ch = st.get_chapter(seq)
            prose = (ch or {}).get("prose") or ""
            snap = load_chapter_review(st, work=work, seq=seq, current_prose=prose)
            if snap and snap.get("fp_match"):
                l_issues = normalize_issues(snap.get("issues") or [], chapter=seq)
                issues.extend(l_issues)
                coverage["mode"] = (snap.get("mode") or "full")
                coverage["tracks"] = ["D", "L"]
                coverage["snapshot"] = {
                    "prose_fp": snap.get("prose_fp"),
                    "fp_match": True,
                    "mode": snap.get("mode"),
                }
                coverage["note"] = "含深检快照（L 轨）；打开左栏不触发新 LLM"
                for d in snap.get("degraded") or []:
                    if isinstance(d, dict):
                        degraded.append(d)
            elif snap is None and coverage.get("mode") == "deterministic_only":
                pass
        except Exception as e:
            degraded.append({"source": "snapshot", "chapter": seq, "reason": str(e)[:200]})

        # A3: read-only quality_dim from completed evaluation (no LLM; left-bar safe)
        try:
            from scribe3.quality.dim_scores import load_chapter_dim_scores
            from scribe3.review.m5_projection import project_quality_dim_advisory

            skipped = list(coverage.get("sources_skipped") or [])
            run = list(coverage.get("sources_run") or [])
            scores = load_chapter_dim_scores(st, work, seq)
            if scores:
                existing = {
                    (i.get("kind") or i.get("id"))
                    for i in issues
                    if i.get("source") == "quality_dim" or i.get("type") == "quality_dim"
                }
                for qi in project_quality_dim_advisory(scores, chapter=seq):
                    key = qi.get("kind") or qi.get("id")
                    if key in existing:
                        continue
                    issues.append(qi)
                    existing.add(key)
                if "quality_dim" in skipped:
                    skipped = [s for s in skipped if s != "quality_dim"]
                if "quality_dim" not in run:
                    run.append("quality_dim")
                tracks = list(coverage.get("tracks") or ["D"])
                if "L" not in tracks:
                    tracks.append("L")
                coverage["tracks"] = tracks
                note = (coverage.get("note") or "").strip()
                addon = "含十维弱维 advisory（只读已有评价）"
                if addon not in note:
                    coverage["note"] = f"{note}；{addon}".strip("；") if note else addon
            coverage["sources_skipped"] = skipped
            coverage["sources_run"] = run
        except Exception as e:
            degraded.append({"source": "quality_dim", "chapter": seq, "reason": str(e)[:200]})

        all_issues.extend(issues)
        all_degraded.extend(degraded)
        coverages.append({"chapter": seq, **coverage})

    # Single-chapter response flattens coverage; multi keeps list
    if chapter is not None and coverages:
        coverage_out = coverages[0]
    else:
        coverage_out = {
            "mode": "deterministic_only",
            "chapters": coverages,
            "note": "多章台账默认确定性；语义深检见各章 snapshot",
        }

    return {
        "issues": all_issues,
        "degraded_sources": all_degraded,
        "coverage": coverage_out,
    }

def discipline(seq: int, brief: str = "", work: str = "main"):
    from scribe3.critique import discipline_truncate
    from scribe3.llm import hermes_complete
    ch = _store_for(work).get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"ok": True, "violations": []}
    return discipline_truncate(ch["prose"], brief, hermes_complete)

def tension_check(seq: int, work: str = "main"):
    """M2a 叙事张力检查:确定性3项(伏笔进展/开环账本/信息差盘点)+ LLM rubric 5项
    (戏剧问题/结局语法/价值反转/微张力荒漠/续读钩子,单次合并盲评)。读已存正文,不落库,
    登记为 read-only POST(见 KNOWN_REST_WRITE_ROUTES)。no_prose 早退;rubric 失败(坏 JSON /
    LLM 异常)→ rubric_failed=True,确定性项照常返回,不崩。

    rubric 经章后缓存复用（同正文指纹免二调）。"""
    from scribe3.brief import tension_deterministic
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"items": [], "error": "no_prose"}
    items = tension_deterministic(st, seq)
    rep = None
    rubric_failed = False
    cache_hit = False
    try:
        from scribe3.chapter_analysis import run_tension_rubric_with_cache
        from scribe3.llm import hermes_complete
        tr = run_tension_rubric_with_cache(
            work=work, seq=seq, prose=ch["prose"],
            complete_fn=hermes_complete, st=st, force=False,
        )
        rep = tr.get("rubric")
        rubric_failed = bool(tr.get("rubric_failed"))
        cache_hit = bool(tr.get("cache_hit"))
    except Exception as e:
        logging.getLogger("scribe3").warning("tension_check rubric LLM 失败 work=%s seq=%s: %s", work, seq, e)
        rubric_failed = True
    if rep is None:
        return {"items": items, "rubric": None, "rubric_failed": True, "cache_hit": cache_hit}
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
        return {"items": items, "rubric": None, "rubric_failed": True, "cache_hit": cache_hit}
    return {"items": items, "rubric": rep, "cache_hit": cache_hit}

def save_chapter(req: SaveChapterReq, background: BackgroundTasks, work: str = "main"):
    import uuid as _uuid
    _rc_id = _uuid.uuid4().hex
    _rc_rows: list[dict] = []
    _rc_emitted = False
    st = None
    try:
        st = _store_for(work)
    except Exception:
        st = None
    # R1：存章前剥提案帧 / fallback / 导演提纲腔 / 替换符
    _san_reasons: list[str] = []
    try:
        from scribe3.prose_sanitize import sanitize_for_persist, fill_placeholder_title
        _san = sanitize_for_persist(req.prose or "")
        _san_reasons = list(_san.get("reasons") or [])
        if _san.get("prose") != (req.prose or ""):
            req.prose = _san["prose"]
        try:
            _syn = ""
            if st is not None:
                _syn = str((st.get_chapter(int(req.seq)) or {}).get("synopsis") or "")
            req.title = fill_placeholder_title(req.title or "", _syn, int(req.seq))
        except Exception:
            pass
    except Exception:
        pass

    def _rc_emit(ok: bool, latch: dict | None = None):
        nonlocal _rc_emitted
        if _rc_emitted:
            return
        _rc_emitted = True
        try:
            from scribe3.run_card import build_gate_run_card, run_card_enabled
            from scribe3.run_card_store import emit_write_run_card
            if not run_card_enabled():
                from scribe3.pipeline_trace_hooks import emit_gate_spans
                emit_gate_spans(
                    st, work=work, chapter=int(req.seq), kind="save",
                    trace_id=_rc_id, rows=list(_rc_rows), ok=ok, card=None,
                )
                return
            card = build_gate_run_card(
                work=work, chapter=int(req.seq), kind="save", request_id=_rc_id,
                gate_rows=list(_rc_rows), assemble_ok=ok,
                quality={"latch": latch or {"count": 0, "kinds": []}},
            )
            emit_write_run_card(
                st=st, work=work, chapter=int(req.seq), kind="save",
                assemble_ok=ok, card=card,
            )
            from scribe3.pipeline_trace_hooks import emit_gate_spans
            emit_gate_spans(
                st, work=work, chapter=int(req.seq), kind="save",
                trace_id=_rc_id, rows=list(_rc_rows), ok=ok, card=card,
            )
        except Exception:
            import logging as _lg
            _lg.getLogger("scribe3.run_card").warning("save run_card fail-soft", exc_info=True)

    # 遗留处置 1-B:同章生成在途时拒绝手动存稿（_chapter_op_busy → chapter_lock 快照）
    if _chapter_op_busy(work, req.seq, "loop"):
        _rc_rows.append({"name": "loop_busy", "expected": True, "actual": "failed", "actual_reason": "loop_busy"})
        _rc_emit(False)
        raise HTTPException(status_code=409, detail=(
            f"第 {req.seq} 章生成在途(loop/选择环),完成后再存——"
            "你的编辑不会丢,可先复制正文"))
    _rc_rows.append({"name": "loop_busy", "expected": True, "actual": "present", "actual_reason": "idle"})
    try:
        _guard_pilot_busy(work, req.seq)   # R2-3:pilot 非 loop 步在途/连写中也拦(防挂旧稿)
        _rc_rows.append({"name": "pilot_busy", "expected": True, "actual": "present", "actual_reason": "idle"})
    except HTTPException:
        _rc_rows.append({"name": "pilot_busy", "expected": True, "actual": "failed", "actual_reason": "pilot_busy"})
        _rc_emit(False)
        raise
    if st is None:
        st = _store_for(work)
    # 存正文只走定稿门 check_finalize_for_save（旧 craft GATE-A/B 已废）
    # 门A/KR1:定稿门闩单源 check_finalize_for_save(与 MCP/dedup/polish/终选共用)
    fg_decision = None
    try:
        from scribe3.finalize_gate import check_finalize_for_save
        fg_decision = check_finalize_for_save(
            st, req.seq, req.prose,
            focalizer=req.focalizer or None,
            danger_draft=bool(req.danger_draft),
            skip=bool(req.skip_finalize_gate),
        )
        if not fg_decision.get("allowed"):
            _rc_rows.append({"name": "finalize_gate", "expected": True, "actual": "failed", "actual_reason": str(fg_decision.get("code") or "finalize_gate")})
            _rc_emit(False, {"count": len(fg_decision.get("advisory_items") or []), "kinds": ["finalize_gate"]})
            raise HTTPException(status_code=409, detail={
                "code": fg_decision.get("code") or "finalize_gate",
                "message": fg_decision.get("detail") or "定稿门闩未通过",
                "verdict": fg_decision.get("verdict"),
                "blocking": fg_decision.get("blocking") or [],
                "advisory_items": fg_decision.get("advisory_items") or [],
                "danger_draft_hint": "显式传 danger_draft=true 可旁路(危险,仅草稿)",
            })
        if bool(req.skip_finalize_gate):
            # 跳过 ≠ 过门。actual 不得 present，否则对照假绿。
            _rc_rows.append({
                "name": "finalize_gate",
                "expected": True,
                "actual": "empty",
                "actual_reason": "skipped_by_flag",
            })
        else:
            _rc_rows.append({
                "name": "finalize_gate",
                "expected": True,
                "actual": "present",
                "actual_reason": "allowed",
            })
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("scribe3").error(
            "finalize gate 评估失败(阻断存稿) work=%s seq=%s: %s", work, req.seq, e,
            exc_info=True)
        raise HTTPException(status_code=503, detail={
            "code": "finalize_gate_error",
            "message": f"定稿门闩评估失败,已阻断存稿: {e}",
        }) from e
    # 经验压力 E2:严格戏格 opt-in(默认不拦空 grid)
    try:
        from scribe3.experience import exp_state
        from scribe3.experience.scene_grid import evaluate_strict_scene_gate
        if exp_state.get_strict_scene(work) and not req.danger_draft:
            _sg = exp_state.get_scene_grid(work, req.seq)
            _ss = evaluate_strict_scene_gate(
                _sg, strict=True, prose=req.prose)
            if not _ss.get("allowed"):
                _rc_rows.append({"name": "strict_scene", "expected": True, "actual": "failed", "actual_reason": "strict_scene"})
                _rc_emit(False)
                raise HTTPException(status_code=409, detail={
                    "code": _ss.get("code") or "strict_scene",
                    "message": _ss.get("detail") or "严格戏格未通过",
                    "issues": _ss.get("issues") or [],
                })
            _rc_rows.append({"name": "strict_scene", "expected": True, "actual": "present", "actual_reason": "allowed"})
        else:
            _rc_rows.append({"name": "strict_scene", "expected": False, "actual": "absent", "actual_reason": "flag_off"})
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning(
            "strict scene 评估失败(忽略,不拦) work=%s: %s", work, e)
    st.save_chapter(req.seq, req.prose, title=req.title, focalizer=req.focalizer)
    _rc_rows.append({"name": "persist_chapter", "expected": True, "actual": "present", "actual_reason": "saved"})
    _rc_emit(True)
    craft_compliance_out = None
    # G4：kind=final 须 craft hard（explore soft-save 可落 prose，不可半齐套 stamp final）
    # 单源 try_stamp_kind_final；失败不阻断 draft 存稿，响应带 final_stamp。
    final_stamp = None
    try:
        from scribe3.finalize_gate import try_stamp_kind_final
        final_stamp = try_stamp_kind_final(
            st, req.seq, req.prose,
            label="", stage="final", stats=_prose_stats(req.prose),
            skip_craft=bool(req.skip_craft_gate),
        )
        if not final_stamp.get("stamped") and final_stamp.get("code") == "craft_finalize":
            import logging
            logging.getLogger("scribe3").info(
                "save-chapter skip kind=final (craft incomplete) work=%s seq=%s blocking=%s",
                work, req.seq, final_stamp.get("blocking"),
            )
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning(
            "save-chapter try_stamp_kind_final 失败(存稿不受影响) work=%s seq=%s: %s",
            work, req.seq, e)
        final_stamp = {
            "stamped": False, "allowed": False, "code": "stamp_error",
            "detail": str(e)[:200],
        }
    # 软校验(确定性、快、不打 LLM):QC + 限知泄露。回写走独立 /ingest(前端接受后再调)。
    from scribe3.critique import quality_flags, find_cross_chapter_repetitions, find_duplicate_lines, find_emotion_telling
    qf = quality_flags(req.prose)
    # 跨章复读:逐章 QC 查不到的"单遍长程生成典型病"(模型跨章复用偏爱措辞)。
    # 比对前文最近 5 章逐字 ≥8 字重叠——把"重复"从'事后逐章删'升级为'跨章可度量'。
    # U-011(作者要 fail-loud):检测器失败此前静默归 0/[],与"真没问题"无区别=存稿后质控假绿。
    # 改成记进 qc_errors(照抄同函数已有的 leak_error 范式),前端红字"检测器故障·本次未检"。
    # 这里【不 raise】——存稿已成功落库,检测是存后软校验,不该因检测器炸 500 掉一次成功存稿。
    import logging as _lg
    qc_errs: dict[str, str] = {}
    cross_rep: list[dict] = []
    try:
        priors = [c["prose"] for c in st.recent_proses(req.seq, k=8) if c.get("prose")]
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        cross_rep = find_cross_chapter_repetitions(req.prose, priors, n=12, allow=allow)
    except Exception as e:
        _lg.getLogger("scribe3").error("cross_repetition 失败 work=%s seq=%s", work, req.seq, exc_info=True)
        qc_errs["cross_repetition"] = str(e)[:120]
    # M2-①: 整行复读 + 情感直说计数
    dup_lines_count = 0
    try:
        dup_lines_count = len(find_duplicate_lines(req.prose))
    except Exception as e:
        _lg.getLogger("scribe3").error("find_duplicate_lines 失败 work=%s seq=%s", work, req.seq, exc_info=True)
        qc_errs["duplicate_lines"] = str(e)[:120]
    emotion_telling_count = 0
    try:
        emotion_telling_count = len(find_emotion_telling(req.prose))
    except Exception as e:
        _lg.getLogger("scribe3").error("find_emotion_telling 失败 work=%s seq=%s", work, req.seq, exc_info=True)
        qc_errs["emotion_telling"] = str(e)[:120]
    leaks, leak_error = None, None
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks_for_chapter as find_leaks
            leaks = len(find_leaks(req.prose, st, req.focalizer, req.seq))
        except Exception as e:
            _lg.getLogger("scribe3").error("find_leaks 失败 work=%s seq=%s", work, req.seq, exc_info=True)
            leak_error = str(e)[:160]
    # Writeback 单入口：IngestPolicy + hold supersedes checkpoint 第二跳
    from scribe3.ingest_policy import GateSnapshot
    from scribe3.api.services.ingest_bg import schedule_ingest
    _verdict = "pass"
    if fg_decision is not None:
        _verdict = str(fg_decision.get("verdict") or "pass").lower()
        if fg_decision.get("code") == "advisory" or (
            fg_decision.get("advisory_items") and not fg_decision.get("blocking")
        ):
            # check_finalize may return allowed+advisory
            v0 = str(fg_decision.get("verdict") or "").lower()
            if v0 in ("advisory", "warn", "warning"):
                _verdict = "advisory"
            elif fg_decision.get("advisory_items") and v0 in ("", "pass", "ok"):
                # 有 advisory 项且允许落库 → 策略 hold
                _verdict = "advisory"
    _ai = None
    try:
        _ai = (fg_decision or {}).get("ai_grade")
    except Exception:
        _ai = None
    _gate = GateSnapshot(
        path="save",
        craft_allowed=True,
        finalize_verdict=_verdict,
        danger_draft=bool(req.danger_draft),
        ai_grade=_ai,
        create_mode=getattr(req, "create_mode", None),
    )
    _ing = schedule_ingest(
        st, work, req.seq,
        background=background,
        prose=req.prose,
        gate=_gate,
        source="save",
        mode="bg",
    )
    enqueued = bool(_ing.get("enqueued"))
    out = {"status": "saved", "seq": req.seq,
            "qc": {"repetition": len(qf["repetition"]), "structural": len(qf["structural"]),
                   "purple": len(qf["purple"]), "cross_repetition": len(cross_rep),
                   "duplicate_lines": dup_lines_count, "emotion_telling": emotion_telling_count},
            "cross_repetition_phrases": [h["phrase"] for h in cross_rep[:12]],
            "leaks": leaks, "leak_error": leak_error,
            "qc_errors": qc_errs or None, "ingesting": bool(enqueued),
            "ingest_enqueued": bool(enqueued),
            "craft_compliance": craft_compliance_out,
            "final_stamp": final_stamp,
            "final_version_stamped": bool((final_stamp or {}).get("stamped")),
            "ingest": {
                "action": _ing.get("action"),
                "reason": _ing.get("reason"),
                "held": bool(_ing.get("held")),
                "confirm_token": _ing.get("confirm_token"),
                "hold_reason": _ing.get("hold_reason"),
                "prose_fp": _ing.get("prose_fp"),
            }}
    if fg_decision is not None:
        out["finalize_gate"] = {
            "code": fg_decision.get("code"),
            "verdict": fg_decision.get("verdict"),
            "danger_draft": bool(req.danger_draft),
            "advisory_count": len(fg_decision.get("advisory_items") or []),
            "blocking_count": len(fg_decision.get("blocking") or []),
        }
    # dual-lamp: 存稿响应透出 anti_meta / reader_ready（soft；不改变 200）
    try:
        from scribe3.reader_ready import build_reader_ready
        _beats = None
        try:
            _beats = (st.get_chapter(req.seq) or {}).get("beats")
        except Exception:
            _beats = None
        _sc_ok = None
        rr = build_reader_ready(
            req.prose or "",
            st=st,
            work=work,
            seq=int(req.seq),
            beats=_beats,
            load_ack=True,
            require_scene_cover=bool(_beats),
            scaffold_ok=_sc_ok,
        )
        out["anti_meta"] = rr.get("anti_meta")
        out["reader_ready"] = rr
        out["lamps"] = rr.get("lamps")
        out["claims"] = rr.get("claims")
        _readable = bool((rr.get("claims") or {}).get("may_claim_readable"))
        if _readable:
            out["author_copy"] = "已存草稿"
            out["status_label"] = "已存草稿"
        else:
            out["author_copy"] = "已存草稿（不可宣称可读）"
            out["status_label"] = "已存草稿（不可宣称可读）"
        if bool(req.skip_finalize_gate):
            out["author_copy"] = "已存草稿（定稿门跳过 · 不可宣称可读）"
            out["status_label"] = out["author_copy"]
        if "restaged_scene" in _san_reasons:
            out["author_copy"] = (out.get("author_copy") or "已存草稿") + " · 疑似场面重演"
            out["status_label"] = out["author_copy"]
        if "replacement_char" in _san_reasons:
            out["sanitize_reasons"] = _san_reasons
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning(
            "save_chapter reader_ready attach fail-soft work=%s: %s", work, e)
        out.setdefault("author_copy", "已存草稿（不可宣称可读）")
        out.setdefault("status_label", "已存草稿（不可宣称可读）")
    if "author_copy" not in out:
        out["author_copy"] = "已存草稿（不可宣称可读）"
        out["status_label"] = out["author_copy"]
    return out

def dedup_chapter(seq: int, background: BackgroundTasks, work: str = "main"):
    """确定性事后跨章改写(QC 的'治'层):定位本章含跨章逐字复读的句子→定向 LLM 改写→存回。

    比'prompt 预防'可靠(实测最严重章跨章复读 30→8,↓73%),契合本系统'确定性扫描+定向改'的纪律。
    幂等:无复读则原样返回、不调 LLM(不落版、不排 ingest)。

    C-1(正文覆写三路对称):真改写正文后,与 /save-chapter 对称——落 final 版本(补版本历史断链)
    + 排后台 ingest(内容变了理应重抽知识账本;经 _enqueue_ingest 与 P0-1 同章去重护栏协同,
    若该章已有 ingest 在途则跳过,不产生双份)。"""
    # 批次一审查 P1-2:与 /save-chapter 同款在途护栏（chapter_lock 只读）
    if _chapter_op_busy(work, seq, "loop"):
        raise HTTPException(status_code=409, detail=(
            f"第 {seq} 章生成在途(loop/选择环),完成后再去重"))
    _guard_pilot_busy(work, seq)   # R2-3:pilot 非 loop 步在途/连写中也拦
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        raise HTTPException(status_code=404, detail="chapter not found")
    from scribe3.critique import rewrite_cross_repetitions
    from scribe3.llm import default_timeout, hermes_complete
    priors = [c["prose"] for c in st.recent_proses(seq, k=8) if c.get("prose")]
    allow = st.motif_terms() if hasattr(st, "motif_terms") else None
    # dedup 同样会按句调用模型；必须沿用精修的短超时、单次尝试边界，避免一个坏响应
    # 把整章请求放大为生成级的多轮长阻塞。
    def _dedup_complete(prompt: str, system: str) -> str:
        return hermes_complete(prompt, system, timeout=min(float(default_timeout()), 30.0),
                               max_tokens=360, retries_override=1)

    # 与章内精修同样分批：一次最多处理六句，避免高命中章节把一次 HTTP 请求放大为
    # 无界的串行模型调用；下一次调用会从最新正文继续收敛。
    res = rewrite_cross_repetitions(ch["prose"], priors, _dedup_complete,
                                    n=12, allow=allow, max_targets=6)
    if res["rewritten"] > 0:
        # KR1+G4: craft hard + 质控（check_persist_gates）；再 try_stamp_kind_final
        from scribe3.finalize_gate import check_persist_gates, try_stamp_kind_final
        _fg = check_persist_gates(
            st, seq, res["prose"], focalizer=ch.get("focalizer") or None)
        if not _fg.get("allowed"):
            raise HTTPException(status_code=409, detail={
                "code": _fg.get("code") or "finalize_gate",
                "message": _fg.get("detail") or "去重改写结果未过定稿门闩,未落库",
                "blocking": _fg.get("blocking") or [],
                "craft": _fg.get("craft"),
                "rewritten_unsaved": res["rewritten"],
            })
        st.save_chapter(seq, res["prose"], title=ch.get("title", ""), focalizer=ch.get("focalizer"))
        _stamp = try_stamp_kind_final(
            st, seq, res["prose"], label="", stage="final",
            stats=_prose_stats(res["prose"]),
        )
        if not _stamp.get("stamped") and _stamp.get("code") == "craft_finalize":
            raise HTTPException(status_code=409, detail={
                "code": "craft_finalize",
                "message": "去重已过质控但 craft 未齐套，拒绝 kind=final",
                "blocking": _stamp.get("blocking") or [],
                "rewritten_unsaved": res["rewritten"],
            })
        # 内容变了 → 单入口策略(缺 snapshot 安全 hold; active hold supersede)
        from scribe3.ingest_policy import GateSnapshot
        from scribe3.api.services.ingest_bg import schedule_ingest
        schedule_ingest(
            st, work, seq, background=background, prose=res["prose"],
            gate=GateSnapshot(path="dedup", finalize_verdict=None),
            source="dedup", mode="bg",
        )
    return {"seq": seq, "rewritten": res["rewritten"],
            "cross_repetition_before": res["before"], "cross_repetition_after": res["after"]}

def polish_chapter(seq: int, background: BackgroundTasks, work: str = "main"):
    """章内精修(QC 治层·章内维度):定位本章内 repetition/duplicate_lines/排比 → 定向改写 → 存回。

    与 /dedup-chapter(跨章逐字复读)对称互补:分幕长章在章内自我复读、堆排比,跨章 dedup 完全
    治不到。同源哲学'确定性扫描+定向改写'——不靠 prompt 记住禁令,只精准改犯规句,改写器强约束
    保限知(绝不点破未揭示悬念)。幂等:无章内硬伤则原样返回、不调 LLM(不落版、不排 ingest)。
    三路对称(落 final 版 + 排后台 ingest)与 /save-chapter、/dedup-chapter 一致。"""
    if _chapter_op_busy(work, seq, "loop"):
        raise HTTPException(status_code=409, detail=(
            f"第 {seq} 章生成在途(loop/选择环),完成后再精修"))
    _guard_pilot_busy(work, seq)
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        raise HTTPException(status_code=404, detail="chapter not found")
    from scribe3.critique import repair_nested_dialogue_opens, rewrite_intra_chapter_issues
    from scribe3.llm import default_timeout, hermes_complete
    allow = st.motif_terms() if hasattr(st, "motif_terms") else None
    # 章内 AI 词精修同样尊重作者白名单：motif_terms 用于复读豁免，allow_words
    # 用于 find_ai_tics 的禁词豁免；合并后沿用 rewrite_intra 的单一 allow 入参。
    try:
        allow = set(allow or ()) | set(st.allow_words() if hasattr(st, "allow_words") else ())
    except Exception:
        allow = set(allow or ()) or None
    quote_fixed = repair_nested_dialogue_opens(ch["prose"])
    quote_repairs = max(0, quote_fixed.count("”") - ch["prose"].count("”"))
    # 精修一轮可能有数十句；不能让单句沿用生成级 600s 超时而拖死整章。超时会被
    # rewrite_intra 的逐句 fail-soft 保留原句，最后仍须通过净减少门才会落库。
    def _polish_complete(prompt: str, system: str) -> str:
        return hermes_complete(prompt, system, timeout=min(float(default_timeout()), 30.0),
                               max_tokens=360, retries_override=1)

    # 一次至多改六个目标，调用方可安全重复请求续跑；避免高问题密度章把同步端点拖成
    # 数十分钟的串行任务。每批仍走净减少回滚门，绝不为赶进度写坏稿。
    res = rewrite_intra_chapter_issues(quote_fixed, _polish_complete, allow=allow, max_targets=6)
    changed = bool(res["rewritten"] or quote_repairs)
    leak_guard = None
    if changed:
        # 限知二次门:改写单句无全局 context,可能把原文刻意模糊的表述"具体化点破"未揭示悬念。
        # 落库前复跑 find_leaks(与 /save-chapter、/check 同一泄露门),泄露增加则整体回退不落库。
        foc = ch.get("focalizer")
        if foc:
            try:
                from scribe3.verify import find_leaks_for_chapter as find_leaks
                before_leaks = len(find_leaks(ch["prose"], st, foc, seq))
                after_leaks = len(find_leaks(res["prose"], st, foc, seq))
                if after_leaks > before_leaks:
                    leak_guard = {"before": before_leaks, "after": after_leaks, "action": "rolled_back"}
                    res = {"rewritten": 0, "before": res["before"], "after": res["before"],
                           "prose": ch["prose"]}
                    quote_repairs = 0
                    changed = False
            except Exception as e:
                import logging
                logging.getLogger("scribe3").warning(
                    "polish-chapter find_leaks 二次门异常(保守起见回退不落库) work=%s seq=%s: %s",
                    work, seq, e)
                leak_guard = {"error": str(e), "action": "rolled_back"}
                res = {"rewritten": 0, "before": res["before"], "after": res["before"],
                       "prose": ch["prose"]}
                quote_repairs = 0
                changed = False
    if changed:
        from scribe3.finalize_gate import check_persist_gates, try_stamp_kind_final
        _fg = check_persist_gates(
            st, seq, res["prose"], focalizer=ch.get("focalizer") or None)
        if not _fg.get("allowed"):
            raise HTTPException(status_code=409, detail={
                "code": _fg.get("code") or "finalize_gate",
                "message": _fg.get("detail") or "精修结果未过定稿门闩,未落库",
                "blocking": _fg.get("blocking") or [],
                "craft": _fg.get("craft"),
                "rewritten_unsaved": res["rewritten"],
            })
        st.save_chapter(seq, res["prose"], title=ch.get("title", ""), focalizer=ch.get("focalizer"))
        _stamp = try_stamp_kind_final(
            st, seq, res["prose"], label="", stage="final",
            stats=_prose_stats(res["prose"]),
        )
        if not _stamp.get("stamped") and _stamp.get("code") == "craft_finalize":
            raise HTTPException(status_code=409, detail={
                "code": "craft_finalize",
                "message": "精修已过质控但 craft 未齐套，拒绝 kind=final",
                "blocking": _stamp.get("blocking") or [],
                "rewritten_unsaved": res["rewritten"],
            })
        from scribe3.ingest_policy import GateSnapshot
        from scribe3.api.services.ingest_bg import schedule_ingest
        schedule_ingest(
            st, work, seq, background=background, prose=res["prose"],
            gate=GateSnapshot(path="polish", finalize_verdict=None),
            source="polish", mode="bg",
        )
    resp = {"seq": seq, "rewritten": res["rewritten"],
            "intra_issues_before": res["before"], "intra_issues_after": res["after"]}
    if quote_repairs:
        resp["quote_repairs"] = quote_repairs
    if leak_guard:
        resp["leak_guard"] = leak_guard
    return resp

def semantic_repair(seq: int, background: BackgroundTasks, work: str = "main"):
    """完整候选稿的语义纪律修复；任一质量门失败均不落库。"""
    from scribe3.critique import semantic_repair_gate
    from scribe3.llm import hermes_complete
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        raise HTTPException(404, f"chapter {seq} not found or empty")
    original = ch["prose"]
    before = post_check(PostCheckReq(prose=original, focalizer=ch.get("focalizer") or "",
                                     brief=ch.get("summary") or ch.get("title") or ""), seq, work)
    raw_violations = (before.get("discipline") or {}).get("violations") or []
    violations = _semantic_repair_violations(original, before.get("quality") or {},
                                             before.get("leaks") or [], before.get("discipline") or {})
    if not violations:
        return {"status": "noop", "seq": seq, "discipline": before.get("discipline") or {},
                "advisory_violations": raw_violations}
    prompt = ("你是小说语义修复器。只修复下列纪律问题，保留全部事件顺序、人物关系、已知事实、"
              "叙述视角与章节结尾；不得删减到原文85%以下，不得解释。\n"
              f"违规类型:{'、'.join(violations)}\n\n【原文】\n{original}")
    from scribe3.llm_temps import TEMP_JUDGE
    candidate = (hermes_complete(prompt, max_tokens=max(2048, min(8192, len(original) * 2)),
                                 retries_override=1, thinking="disabled",
                                 temperature=TEMP_JUDGE,
                                 official_api=True) or "").strip()
    after = post_check(PostCheckReq(prose=candidate, focalizer=ch.get("focalizer") or "",
                                    brief=ch.get("summary") or ch.get("title") or ""), seq, work)
    after_actionable = _semantic_repair_violations(candidate, after.get("quality") or {},
                                                    after.get("leaks") or [], after.get("discipline") or {})
    gate = semantic_repair_gate(original, candidate, before.get("quality") or {}, after.get("quality") or {},
                                before.get("leaks") or [], after.get("leaks") or [],
                                {"violations": after_actionable,
                                 "degraded": bool(after.get("degraded")),
                                 "parse_failed": bool((after.get("discipline") or {}).get("parse_failed"))})
    if not gate["ok"]:
        return {"status": "rejected", "seq": seq, "gate": gate, "discipline": after.get("discipline") or {}}
    # G4：semantic_repair 写 kind=final 前 craft hard + 质控
    from scribe3.finalize_gate import check_persist_gates, try_stamp_kind_final
    _pg = check_persist_gates(
        st, seq, candidate, focalizer=ch.get("focalizer") or None)
    if not _pg.get("allowed"):
        return {
            "status": "rejected", "seq": seq, "gate": gate,
            "persist_gate": _pg,
            "code": _pg.get("code") or "craft_finalize",
            "message": _pg.get("detail") or "semantic repair 未过 craft/质控门",
        }
    st.save_chapter(seq, candidate, title=ch.get("title") or "", focalizer=ch.get("focalizer") or "")
    _stamp = try_stamp_kind_final(
        st, seq, candidate, label="semantic repair", stage="semantic_repair",
        stats=_prose_stats(candidate),
    )
    if not _stamp.get("stamped") and _stamp.get("code") == "craft_finalize":
        return {
            "status": "rejected", "seq": seq,
            "code": "craft_finalize",
            "message": "semantic repair 拒绝 kind=final（craft 未齐套）",
            "final_stamp": _stamp,
        }
    # 正文已变化 → 单入口策略(与 save/dedup 同 choke point)
    from scribe3.ingest_policy import GateSnapshot
    from scribe3.api.services.ingest_bg import schedule_ingest
    _ing = schedule_ingest(
        st, work, seq, background=background, prose=candidate,
        gate=GateSnapshot(path="semantic_repair", finalize_verdict=None),
        source="semantic_repair", mode="bg",
    )
    return {"status": "repaired", "seq": seq, "gate": gate,
            "discipline": after.get("discipline") or {},
            "ingesting": bool(_ing.get("enqueued")),
            "ingest": {
                "action": _ing.get("action"), "held": bool(_ing.get("held")),
                "reason": _ing.get("reason"),
            }}

def draft_check(req: DraftCheckReq, seq: int = 0, work: str = "main"):
    """块四b(§5.4):草稿阶段轻量确定性分析。对**任意草稿文本**跑确定性检测器
    (quality_flags 产品合计键 + 整行复读 + 排比 + 情感直说)+ 限知泄露预览(可选,只读)。
    与 /post-check 共用同一批确定性聚合,但入参是草稿文本、**不读章、不写库**:
    绝不跑 LLM ingest、绝不写 proposition/knows/台账/任何库——纯计算 + 只读预览。
    注册为 read-only POST(见 KNOWN_REST_WRITE_ROUTES)。各检测器 fail-soft。"""
    import logging
    from scribe3.critique import (quality_flags, find_duplicate_lines,
                                  find_parallelism, find_emotion_telling)
    from scribe3.qc_product_keys import (
        product_qc_breakdown_from_flags, product_qc_total, project_product_qc_breakdown,
    )
    degraded_stages: list[str] = []

    # Minor:quality_flags 也 fail-soft(与其余检测器一致)——抛错时降级归零而非整个端点 500。
    try:
        qf = quality_flags(req.prose)
        quality = product_qc_breakdown_from_flags(qf)
        quality["total"] = product_qc_total(quality)
    except Exception as e:
        logging.getLogger("scribe3").warning("draft_check quality_flags 失败: %s", e)
        degraded_stages.append("quality_flags")
        quality = project_product_qc_breakdown({})
        quality["total"] = 0

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
            from scribe3.verify import find_leaks_for_chapter as find_leaks
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

def latest_draft(seq: int, work: str = "main"):
    """取该章最新排演。版本表 → 冻结 chapter_draft → 旧章字段。"""
    st = _store_for(work)
    v = st.latest_draft_version(seq)
    frozen = None
    if hasattr(st, "get_frozen"):
        try:
            frozen = st.get_frozen("chapter_draft", int(seq))
        except Exception:
            frozen = None
    from scribe3.draft_read import resolve_latest_draft
    resolved = resolve_latest_draft(v, st.get_chapter(seq) or {}, frozen_draft=frozen)
    if not resolved:
        return {}
    v = resolved
    import json
    raw = v.get("stats")
    try:
        v["stats"] = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        # U-011:stats JSON 损坏≠没数据(add_chapter_version 必写它)——损坏被当空=序列化侧
        # 真 bug 被藏。log.error 让损坏可见 + 标 stats_corrupt,不静默当 {}。
        logging.getLogger("scribe3").error("latest_draft stats JSON 损坏 seq=%s: %r", seq, raw, exc_info=True)
        v["stats"] = {}
        v["stats_corrupt"] = True
    return v


def get_debug_flags():
    """O27：统一旗标控制台只读查询（当前值 + 默认 + 风险级）。"""
    from scribe3.feature_flags import get_all_flags
    return {"flags": get_all_flags()}


def get_injection_trace(work: str = "main"):
    """H9：最近一次写路径 budget_report + 并列 Run 卡。必须保留 annotations。"""
    from scribe3.api.services.write_assemble import get_last_write_budget_report
    from scribe3.context_budget import build_budget_report, context_fidelity
    from scribe3.run_card_store import get_last_run_card, latest_run_card, publicize
    try:
        from scribe3.injection_registry import registry_mode
        reg = registry_mode()
    except Exception:
        reg = "off"
    last = get_last_write_budget_report() or {}
    last_card = get_last_run_card()
    persisted = None
    try:
        from scribe3.api import app_impl as core
        from scribe3.run_card_store import run_card_persist_enabled
        st = core._store_for(work)
        if run_card_persist_enabled():
            persisted = latest_run_card(st, work=work, kind="write")
        else:
            from scribe3.pipeline_trace_store import chain_as_run_card_item, latest_pipeline_chain
            ch = latest_pipeline_chain(st, kind="write")
            if ch:
                persisted = ch.get("contrast_summary") or chain_as_run_card_item(ch)
                persisted = dict(persisted or {})
                persisted["request_id"] = ch.get("trace_id")
                persisted["run_id"] = ch.get("contrast_run_id")
    except Exception:
        persisted = None
    if not last:
        last = build_budget_report(work=work)
    card = persisted or last_card or None
    src = "db" if persisted else ("memory" if last_card else None)
    return {
        "surface": "debug.injection_trace",
        "work": work,
        "registry_mode": (card or last).get("registry_mode") or reg,
        "fidelity": last.get("fidelity") or context_fidelity(),
        "budget_report": last,
        "run_card": publicize(card) if card else None,
        "run_card_source": src,
        "note": (
            "run_card 为期望×实际×质量；budget_report 并列。永不回传 prompt。"
            f" source={src}；无 work 时为默认书+本进程 last。"
        ),
        "recall_shadow": _recall_shadow_card(),
    }


def _recall_shadow_card() -> dict:
    try:
        from scribe3.recall_service import summarize_recall_shadow
        return summarize_recall_shadow()
    except Exception:
        return {"by_path": {}, "n": 0}


def get_debug_recall_shadow(work: str = "main"):
    """召回影子按 path 分组的通过率。只读，不改输出。"""
    from scribe3.recall_service import summarize_recall_shadow
    agg = summarize_recall_shadow()
    return {
        "ok": True,
        "work": work,
        "surface": "debug.recall_shadow",
        "window": "持久化自 2026-08-22 翻主日起算；本进程环是启动以来窗口，pipeline observe 为跨请求账",
        **agg,
    }


def get_debug_run_cards(
    work: str = "main",
    chapter: int | None = None,
    kind: str | None = None,
    verdict: str | None = None,
    limit: int = 20,
):
    """列出本书 Run 卡（无段正文）。P3b 读 chain.contrast_summary。"""
    from scribe3.run_card_store import list_run_cards, publicize, run_card_persist_enabled
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "items": []}
    if not run_card_persist_enabled():
        from scribe3.pipeline_trace_store import chain_as_run_card_item, list_chains
        chains = list_chains(st, chapter=chapter, kind=kind, limit=limit)
        items = []
        for raw in chains:
            it = chain_as_run_card_item(raw)
            if verdict and it.get("verdict") != verdict:
                continue
            items.append(it)
        return {
            "ok": True, "work": work, "surface": "debug.run_cards",
            "count": len(items), "items": items, "source": "chain",
        }
    rows = list_run_cards(st, chapter=chapter, kind=kind, verdict=verdict, limit=limit)
    items = []
    for raw in rows:
        pub = publicize(raw) or {}
        items.append({
            "run_id": pub.get("run_id"),
            "request_id": pub.get("request_id"),
            "outcome_id": pub.get("outcome_id"),
            "kind": pub.get("kind"),
            "chapter": pub.get("chapter"),
            "phase": pub.get("phase"),
            "created_at": raw.get("created_at"),
            "verdict": pub.get("verdict"),
            "summary": pub.get("summary"),
            "assemble_ok": pub.get("assemble_ok"),
            "outcome_status": pub.get("outcome_status"),
            "prompt_hard_profile": pub.get("prompt_hard_profile"),
            "quality_flags": pub.get("quality_flags"),
        })
    return {
        "ok": True,
        "work": work,
        "surface": "debug.run_cards",
        "count": len(items),
        "items": items,
    }


def get_debug_run_card(run_id: str, work: str = "main"):
    """单次 Run 卡。P3b 按 contrast_run_id 读 chain。"""
    from scribe3.run_card_store import get_run_card, publicize, run_card_persist_enabled
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    if not run_card_persist_enabled() and hasattr(st, "get_pipeline_chain_by_contrast"):
        chain = st.get_pipeline_chain_by_contrast(run_id)
        if not chain:
            from scribe3.pipeline_trace_store import get_chain
            chain = get_chain(st, run_id)
        if not chain:
            return {"ok": False, "error": "not_found", "work": work, "run_id": run_id}
        cs = chain.get("contrast_summary") if isinstance(chain.get("contrast_summary"), dict) else {}
        pub = dict(cs) if cs else {
            "rows": [], "verdict": "green", "summary": {},
        }
        pub["ok"] = True
        pub["work"] = work
        pub["run_id"] = chain.get("contrast_run_id") or run_id
        pub["request_id"] = chain.get("trace_id")
        pub["surface"] = "debug.run_card"
        pub["created_at"] = chain.get("created_at")
        if not cs:
            pub["notes"] = ["no_contrast"]
        return pub
    raw = get_run_card(st, run_id)
    if not raw:
        return {"ok": False, "error": "not_found", "work": work, "run_id": run_id}
    pub = publicize(raw) or {}
    pub["ok"] = True
    pub["work"] = work
    pub["surface"] = "debug.run_card"
    pub["created_at"] = raw.get("created_at")
    return pub


def post_debug_run_cards_purge(work: str = "main", days: int | None = None):
    from scribe3.run_card_store import purge_run_cards, ttl_days
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    out = purge_run_cards(st, days=days)
    out["work"] = work
    out["default_ttl_days"] = ttl_days()
    return out


def get_debug_pipeline_traces(
    work: str = "main",
    chapter: int | None = None,
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 20,
):
    """链列表。status 只滤 chain；按 step 请走 /debug/pipeline-spans。"""
    from scribe3.pipeline_trace_store import get_chain, list_chains, list_spans, publicize_chain_list_item
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "items": []}
    qq = (q or "").strip()
    if qq:
        hit = get_chain(st, qq)
        if not hit:
            try:
                rows = list_chains(st, limit=100)
                for r in rows:
                    if r.get("outcome_id") == qq:
                        hit = r
                        break
            except Exception:
                hit = None
        if not hit:
            found = list_spans(st, trace_id=None, limit=1)
            try:
                found = st.list_pipeline_spans(trace_id=qq, limit=1) if hasattr(st, "list_pipeline_spans") else []
            except Exception:
                found = []
            if not found and hasattr(st, "list_pipeline_spans"):
                try:
                    # span_id lookup
                    rows = st._query(
                        "SELECT trace_id FROM pipeline_span WHERE span_id=$id LIMIT 1",
                        {"id": qq},
                    ) or []
                    if rows:
                        hit = get_chain(st, str(rows[0].get("trace_id") or ""))
                except Exception:
                    hit = None
            elif found:
                hit = get_chain(st, str(found[0].get("trace_id") or ""))
        if not hit:
            return {"ok": False, "error": "not_found", "work": work, "items": [], "count": 0}
        return {
            "ok": True, "work": work, "surface": "debug.pipeline_traces",
            "count": 1, "items": [publicize_chain_list_item(hit)],
        }
    rows = list_chains(st, chapter=chapter, kind=kind, status=status, limit=limit)
    items = [publicize_chain_list_item(r) for r in rows]
    return {
        "ok": True, "work": work, "surface": "debug.pipeline_traces",
        "count": len(items), "items": items,
    }


def get_debug_pipeline_trace(trace_id: str, work: str = "main", include: str | None = None):
    """单链 + spans。include=events,artifacts 才带飞行记录仪正文。"""
    from scribe3.pipeline_trace_store import get_chain, list_spans, publicize_chain_detail
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    raw = get_chain(st, trace_id)
    if not raw:
        return {"ok": False, "error": "not_found", "work": work, "trace_id": trace_id}
    spans = list_spans(st, trace_id=trace_id, limit=200)
    neighbors = {}
    try:
        if hasattr(st, "neighbor_traces"):
            neighbors = st.neighbor_traces(
                work=raw.get("work") or work,
                chapter=int(raw.get("chapter") or 0),
                kind=str(raw.get("kind") or "write"),
                created_at=raw.get("created_at"),
            ) or {}
    except Exception:
        neighbors = {}
    out = publicize_chain_detail(raw, spans, neighbors)
    out["work"] = work
    out["surface"] = "debug.pipeline_trace"
    out["item"] = dict(out)
    out["ok"] = True
    try:
        from scribe3.pipeline_recorder import pipeline_recorder_enabled
        out["recorder_enabled"] = pipeline_recorder_enabled()
    except Exception:
        out["recorder_enabled"] = True
    want = {p.strip() for p in str(include or "").split(",") if p.strip()}
    if "events" in want and hasattr(st, "list_pipeline_events"):
        ev = st.list_pipeline_events(work=work, trace_id=trace_id, limit=2048)
        out["events"] = ev
        out["event_total"] = len(ev)
    if "artifacts" in want and hasattr(st, "list_pipeline_artifacts"):
        arts = st.list_pipeline_artifacts(work=work, trace_id=trace_id, limit=256)
        out["artifacts"] = arts
        out["artifact_total"] = len(arts)
    return out


def get_debug_pipeline_trace_spans(
    trace_id: str, work: str = "main", layer: str | None = None,
):
    from scribe3.pipeline_trace import public_span
    from scribe3.pipeline_trace_store import list_spans
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "items": []}
    rows = list_spans(st, trace_id=trace_id, layer=layer, limit=200)
    items = [public_span(r) for r in rows]
    return {
        "ok": True, "work": work, "trace_id": trace_id,
        "count": len(items), "items": [i for i in items if i],
    }


def get_debug_pipeline_spans(
    work: str = "main",
    step_key: str | None = None,
    status: str | None = None,
    chapter: int | None = None,
    limit: int = 50,
):
    """按 step_key 检索 span，再批量取所属链。"""
    from scribe3.pipeline_trace import public_span
    from scribe3.pipeline_trace_store import get_chain, list_spans, publicize_chain_list_item
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "items": [], "chains": []}
    rows = list_spans(st, step_key=step_key, status=status, chapter=chapter, limit=limit)
    items = [public_span(r) for r in rows]
    items = [i for i in items if i]
    seen: set[str] = set()
    chains = []
    for it in items:
        tid = str(it.get("trace_id") or "")
        if not tid or tid in seen:
            continue
        seen.add(tid)
        raw = get_chain(st, tid)
        if raw:
            chains.append(publicize_chain_list_item(raw))
    return {
        "ok": True, "work": work, "surface": "debug.pipeline_spans",
        "count": len(items), "items": items, "chains": chains,
    }


def get_debug_pipeline_logs(
    work: str = "main",
    trace_id: str | None = None,
    step_key: str | None = None,
    code: str | None = None,
    empty: str | None = None,
    since: str | None = None,
    limit: int = 200,
):
    """逐步中文分析账本。empty 只接受 true/false。"""
    from scribe3.pipeline_trace import public_log
    from scribe3.pipeline_trace_store import list_logs
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "items": [], "count": 0}
    empty_b = None
    if empty is not None:
        ev = str(empty).strip().lower()
        if ev == "true":
            empty_b = True
        elif ev == "false":
            empty_b = False
        else:
            return {"ok": False, "error": "empty must be true or false", "items": [], "count": 0}
    rows = list_logs(
        st, work=work, trace_id=trace_id, step_key=step_key,
        code=code, empty=empty_b, since=since, limit=limit,
    )
    items = [public_log(r) for r in rows]
    items = [i for i in items if i]
    return {
        "ok": True, "work": work, "surface": "debug.pipeline_logs",
        "count": len(items), "items": items,
    }


def get_debug_pipeline_events(
    work: str = "main",
    trace_id: str | None = None,
    step_key: str | None = None,
    kind: str | None = None,
    empty: str | None = None,
    since: str | None = None,
    after_seq: int | None = None,
    limit: int | None = None,
    tag: str | None = None,
):
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "items": [], "total": 0, "truncated": False}
    empty_b = None
    if empty is not None:
        ev = str(empty).strip().lower()
        if ev == "true":
            empty_b = True
        elif ev == "false":
            empty_b = False
        else:
            return {"ok": False, "error": "empty must be true or false", "items": [], "total": 0}
    default_lim = 2048 if trace_id else 200
    lim = int(limit or default_lim)
    if not hasattr(st, "list_pipeline_events"):
        return {"ok": True, "work": work, "surface": "debug.pipeline_events",
                "items": [], "total": 0, "truncated": False, "next_seq": None}
    rows = st.list_pipeline_events(
        work=work, trace_id=trace_id, step_key=step_key, kind=kind,
        empty=empty_b, since=since, after_seq=after_seq, limit=lim + 1,
    )
    truncated = len(rows) > lim
    items = rows[:lim]
    want_tag = str(tag or "").strip()
    if want_tag:
        items = [
            r for r in items
            if str(((r or {}).get("payload") or {}).get("tag") or "") == want_tag
        ]
        truncated = False
    next_seq = items[-1].get("seq") if truncated and items else None
    return {
        "ok": True, "work": work, "surface": "debug.pipeline_events",
        "items": items, "total": len(items) if not truncated else len(items) + 1,
        "truncated": truncated, "next_seq": next_seq, "count": len(items),
    }


def get_debug_pipeline_artifacts(
    work: str = "main",
    trace_id: str | None = None,
    kind: str | None = None,
    name: str | None = None,
    limit: int = 256,
):
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "items": [], "total": 0, "truncated": False}
    if not hasattr(st, "list_pipeline_artifacts"):
        return {"ok": True, "work": work, "surface": "debug.pipeline_artifacts",
                "items": [], "total": 0, "truncated": False, "next_seq": None}
    lim = max(1, min(int(limit or 256), 256))
    rows = st.list_pipeline_artifacts(
        work=work, trace_id=trace_id, kind=kind, name=name, limit=lim + 1,
    )
    truncated = len(rows) > lim
    items = rows[:lim]
    return {
        "ok": True, "work": work, "surface": "debug.pipeline_artifacts",
        "items": items, "total": len(items) if not truncated else len(items) + 1,
        "truncated": truncated, "next_seq": None, "count": len(items),
    }


def get_debug_pipeline_artifact(artifact_id: str, work: str = "main"):
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    if not hasattr(st, "get_pipeline_artifact"):
        return {"ok": False, "error": "not_found", "artifact_id": artifact_id}
    row = st.get_pipeline_artifact(artifact_id)
    if not row:
        return {"ok": False, "error": "not_found", "work": work, "artifact_id": artifact_id}
    if str(row.get("work") or "") not in ("", work) and row.get("work") != work:
        return {"ok": False, "error": "forbidden", "work": work}
    return {"ok": True, "work": work, "surface": "debug.pipeline_artifact", "item": row}


def post_debug_pipeline_traces_purge(work: str = "main", days: int | None = None):
    from scribe3.pipeline_trace_store import ttl_days
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    d = ttl_days() if days is None else max(1, int(days))
    try:
        out = st.purge_pipeline_traces_older_than(d) if hasattr(st, "purge_pipeline_traces_older_than") else {"ok": False}
        out["work"] = work
        out["default_ttl_days"] = ttl_days()
        return out
    except Exception as e:
        return {"ok": False, "work": work, "error": str(e)[:160]}


def budget_probe_ep(req: dict | None = None):
    """PR-7：预算头寸探针。默认 mode=config；assemble 显式且只返回数字。

    与 injection-trace 同权（登录作者）。永不回传完整 prompt。
    注意：本函数可能被 rebind 到 app_impl 全局命名空间，勿依赖本模块 module-level 可变全局。
    """
    payload = req if isinstance(req, dict) else {}
    mode = str(payload.get("mode") or "config").strip().lower()

    from scribe3.context_budget import (
        build_budget_report,
        get_envelope_token_budget,
        get_prompt_hard,
        context_fidelity,
    )
    beat = payload.get("beat_type")
    work = payload.get("work")
    work_s = str(work).strip() if work not in (None, "") else None
    rep = build_budget_report(beat_type=str(beat) if beat else None, work=work_s)
    env = int(rep.get("envelope_token_budget") or get_envelope_token_budget())
    hard = int(rep.get("prompt_hard") or get_prompt_hard(work=work_s))
    l2_room = max(0, hard - env)
    out = {
        "mode": "config",
        "fidelity": rep.get("fidelity") or context_fidelity(),
        "L1_envelope": env,
        "prompt_hard": hard,
        "prompt_hard_profile": rep.get("prompt_hard_profile"),
        "novel_wide": rep.get("novel_wide"),
        "supplemental_soft": rep.get("supplemental_soft"),
        "supplemental_hard": rep.get("supplemental_hard"),
        "model_context_window": rep.get("model_context_window"),
        "wide_works": rep.get("wide_works"),
        "work": work_s,
        "work_unspecified_narrow": rep.get("work_unspecified_narrow"),
        "effective_L2_est": l2_room,
        "adaptive_profile": rep.get("adaptive_profile"),
        "registry_mode": rep.get("registry_mode"),
        "block_sum": sum((rep.get("block_budgets") or {}).values()),
        "event_graph_k": (rep.get("event_graph") or {}).get("k"),
        "surface": "debug.budget_probe",
        "note": "进程内配置快照，非跨副本；与 injection-trace 同权；永不回传完整 prompt。白名单非空且未传 work 时为窄档。",
    }
    if mode == "assemble":
        # 轻量：仅 domain_lengths 数字；禁止 instructions 全文
        domain_lengths = {}
        dropped = []
        try:
            work = str(payload.get("work") or "main")
            seq = int(payload.get("seq") or payload.get("chapter") or 0)
            if seq > 0:
                from scribe3.api import app_impl as core
                st = core._store_for(work)
                ch = st.get_chapter(seq) or {}
                # 粗估各域长度（不跑完整 LLM assemble）
                for k, v in (
                    ("synopsis", ch.get("synopsis")),
                    ("beats", ch.get("beats")),
                    ("scene_truth", ch.get("scene_truth")),
                    ("prose", (ch.get("prose") or "")[:2000]),
                    ("draft", (ch.get("draft") or "")[:2000]),
                ):
                    if v is None:
                        continue
                    domain_lengths[k] = max(1, len(str(v)) // 2)
            else:
                dropped.append("no_seq")
        except Exception as e:
            dropped.append(f"assemble_soft:{type(e).__name__}")
        out["mode"] = "assemble"
        out["domain_lengths"] = domain_lengths
        out["L0_note"] = "redline never full-drop"
        out["L1_from_domains"] = sum(domain_lengths.values())
        out["L2_room_est"] = l2_room
        out["dropped"] = dropped
        out["note"] = (
            "assemble 档仅数字/域名；无 instructions 全文；"
            "进程内；与 injection-trace 同权"
        )
    return out


def get_debug_locks():
    """PR-8：进程内 inflight + chapter lock 旗（只读）。"""
    from scribe3.concurrency_obs import inflight_snapshot
    from scribe3.chapter_lock import CHAPTER_OPS
    try:
        from scribe3.concurrency_lock import distributed_lock_enabled
        dist = bool(distributed_lock_enabled())
    except Exception:
        dist = False
    return {
        "surface": "debug.locks",
        "chapter_ops": list(CHAPTER_OPS),
        "distributed_lock": dist,
        "inflight": inflight_snapshot(),
        "note": "进程内快照；ingest_lease/approval_idempotency 独立表面见 lock-kinds 文档",
        "mutex_path": "chapter_lock_only",  # GAP-1
    }


def get_debug_audit_log(
    work: str = "main",
    table: str | None = None,
    kind: str | None = None,
    limit: int = 50,
):
    """GAP-3：读取 audit_event（只读）。"""
    from scribe3.audit_maintenance import query_audit_log, audit_ttl_days
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "rows": []}
    rows = query_audit_log(st, table=table, kind=kind, limit=limit)
    return {
        "ok": True,
        "work": work,
        "ttl_days": audit_ttl_days(),
        "count": len(rows),
        "rows": rows,
        "surface": "debug.audit_log",
    }


def post_debug_audit_purge(work: str = "main", days: int | None = None):
    """GAP-3：手动触发审计 TTL 清理。"""
    from scribe3.audit_maintenance import purge_audit_events, audit_ttl_days
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    out = purge_audit_events(st, days=days)
    out["work"] = work
    out["default_ttl_days"] = audit_ttl_days()
    return out


def get_debug_stats(work: str = "main"):
    """GAP-5：聚合统计 bundle。"""
    from scribe3.stats_views import read_stats_bundle
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}
    return {"ok": True, "work": work, **read_stats_bundle(st)}


def soft_event_led_ep(req: dict | None = None, work: str = "main"):
    """PR-4：EVENT_LED 唯一入口。Body include_llm 才跑 L1（旗默认关）。"""
    import os
    payload = req if isinstance(req, dict) else {}
    prose = str(payload.get("prose") or "")
    seq = payload.get("seq") or payload.get("chapter")
    drive = payload.get("drive") if isinstance(payload.get("drive"), dict) else None
    if not prose and seq is not None:
        try:
            from scribe3.api import app_impl as core
            st = core._store_for(str(payload.get("work") or work or "main"))
            ch = st.get_chapter(int(seq)) or {}
            prose = str(ch.get("prose") or ch.get("draft") or "")
            if drive is None and isinstance(ch.get("narrative_drive"), dict):
                drive = ch.get("narrative_drive")
        except Exception:
            pass
    from scribe3.narrative_drive import detect_event_led
    l0 = detect_event_led(prose, drive)
    l1 = None
    include_llm = payload.get("include_llm") in (True, 1, "1", "true", "yes")
    if include_llm:
        llm_on = (get_flag("SCRIBE3_EVENT_LED_LLM") or "0").strip().lower() in (
            "1", "true", "yes", "on",
        )
        if llm_on:
            try:
                from scribe3.narrative_drive import detect_event_led_llm
                l1 = detect_event_led_llm(prose, drive)
            except Exception as e:
                l1 = {
                    "severity": "advisory",
                    "status": "degraded",
                    "error": str(e)[:200],
                    "note": "L1 soft fail",
                }
        else:
            l1 = {
                "severity": "advisory",
                "status": "skipped",
                "note": "SCRIBE3_EVENT_LED_LLM off",
            }
    return {
        "l0": l0,
        "l1": l1,
        "severity": "advisory",
        "surface": "soft.event_led",
    }


def soft_discourse_ep(req: dict | None = None, work: str = "main"):
    """Week-1 话语层 soft 唯一入口。Body 可只含 seq；服务端取 prose|draft。

    有正文 → status=ok；无正文 → status=no_prose（HTTP 200，不 5xx）。
    """
    payload = req if isinstance(req, dict) else {}
    w = str(payload.get("work") or work or "main")
    seq = payload.get("seq") or payload.get("chapter")
    prose = str(payload.get("prose") or "")
    ch: dict = {}
    near: list = []
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(w)
        if seq is not None:
            ch = st.get_chapter(int(seq)) or {}
            if not prose.strip():
                prose = str(ch.get("prose") or ch.get("draft") or "")
            # 近章 ±1 synopsis（info_delta）
            s = int(seq)
            for nseq in (s - 1, s + 1):
                if nseq < 1:
                    continue
                try:
                    nc = st.get_chapter(nseq) or {}
                    if nc:
                        near.append(nc)
                except Exception:
                    pass
    except Exception:
        pass
    try:
        from scribe3.discourse_advisory import run_discourse_advisory
        out = run_discourse_advisory(
            prose if prose.strip() else None,
            ch or None,
            near_chapters=near,
            mode="soft",
        )
    except Exception as e:
        out = {
            "severity": "advisory",
            "not_a_kpi": True,
            "status": "degraded",
            "findings": [],
            "breath": {},
            "serial": {},
            "error": str(e)[:160],
        }
    out["surface"] = "soft.discourse"
    out["seq"] = int(seq) if seq is not None else None
    out["work"] = w
    return out


def soft_precheck_ep(req: dict | None = None):
    """P2 residual：大纲/节拍软预检 API → soft_precheck_plan（advisory）。

    Body: plan/beats/outline 任意 JSON；默认 hard_park=false。
    """
    from scribe3.novel_first_surface import soft_precheck_surface
    payload = req if isinstance(req, dict) else {}
    return soft_precheck_surface(payload)


def literary_distill_ep(req: dict | None = None):
    """P2 residual：文学蒸馏 API → literary_distill（bullets+raw）。

    Body: {\"recap\"|\"text\": \"...\"}；不读 tokens_saved。
    """
    from scribe3.novel_first_surface import literary_distill_surface
    payload = req if isinstance(req, dict) else {}
    return literary_distill_surface(
        recap=str(payload.get("recap") or ""),
        text=payload.get("text"),
        max_bullets=int(payload.get("max_bullets") or 12),
    )


def event_graph_ep(req: dict | None = None):
    """事件图预览 API（一跳/多跳 · 与写路径共用 surface）。

    Body: {events?, promises?, seed_id?, k?}。
    """
    from scribe3.novel_first_surface import event_graph_surface
    payload = req if isinstance(req, dict) else {}
    return event_graph_surface(
        events=payload.get("events"),
        promises=payload.get("promises"),
        seed_id=payload.get("seed_id"),
        k=int(payload.get("k") or 1),
        max_nodes=int(payload.get("max_nodes") or 64),
    )


def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['get_progress']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_progress', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_progress', _re)
    g['get_progress'] = _re
    router.add_api_route('/progress', _re, methods=['GET'], name='get_progress')

    _fn = g['chat_stream']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_stream', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_stream', _re)
    g['chat_stream'] = _re
    router.add_api_route('/chat/stream', _re, methods=['GET'], name='chat_stream')

    _fn = g['chat_agentic_stream']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_agentic_stream', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_agentic_stream', _re)
    g['chat_agentic_stream'] = _re
    router.add_api_route('/chat/agentic-stream', _re, methods=['GET'], name='chat_agentic_stream')

    _fn = g['chat_messages']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_messages', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_messages', _re)
    g['chat_messages'] = _re
    router.add_api_route('/chat/messages', _re, methods=['GET'], name='chat_messages')

    _fn = g['get_project_tree']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_project_tree', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_project_tree', _re)
    g['get_project_tree'] = _re
    router.add_api_route('/project-tree', _re, methods=['GET'], name='get_project_tree')

    _fn = g['issue_ledger']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'issue_ledger', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'issue_ledger', _re)
    g['issue_ledger'] = _re
    router.add_api_route('/issues', _re, methods=['GET'], name='issue_ledger')

    _fn = g['discipline']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'discipline', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'discipline', _re)
    g['discipline'] = _re
    router.add_api_route('/discipline', _re, methods=['GET'], name='discipline')

    _fn = g['tension_check']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'tension_check', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'tension_check', _re)
    g['tension_check'] = _re
    router.add_api_route('/tension-check', _re, methods=['POST'], name='tension_check')

    _fn = g['save_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'save_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'save_chapter', _re)
    g['save_chapter'] = _re
    router.add_api_route('/save-chapter', _re, methods=['POST'], name='save_chapter')

    # Rebind bare handlers then re-apply exclusive lock so FastAPI sees real params
    # (FunctionType on wraps(*args,**kwargs) would publish query args/kwargs).
    _fn = g['dedup_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'dedup_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    _re = core._exclusive_chapter_repair(_re)
    setattr(core, 'dedup_chapter', _re)
    g['dedup_chapter'] = _re
    router.add_api_route('/dedup-chapter', _re, methods=['POST'], name='dedup_chapter')

    _fn = g['polish_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'polish_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    _re = core._exclusive_chapter_repair(_re)
    setattr(core, 'polish_chapter', _re)
    g['polish_chapter'] = _re
    router.add_api_route('/polish-chapter', _re, methods=['POST'], name='polish_chapter')

    _fn = g['semantic_repair']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'semantic_repair', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    _re = core._exclusive_chapter_repair(_re)
    setattr(core, 'semantic_repair', _re)
    g['semantic_repair'] = _re
    router.add_api_route('/semantic-repair', _re, methods=['POST'], name='semantic_repair')

    _fn = g['draft_check']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'draft_check', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'draft_check', _re)
    g['draft_check'] = _re
    router.add_api_route('/draft-check', _re, methods=['POST'], name='draft_check')

    _fn = g['save_draft']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'save_draft', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'save_draft', _re)
    g['save_draft'] = _re
    router.add_api_route('/save-draft', _re, methods=['POST'], name='save_draft')

    _fn = g['latest_draft']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'latest_draft', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'latest_draft', _re)
    g['latest_draft'] = _re
    router.add_api_route('/latest-draft', _re, methods=['GET'], name='latest_draft')

    _fn = g['get_debug_flags']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_debug_flags', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_debug_flags', _re)
    g['get_debug_flags'] = _re
    router.add_api_route('/debug/flags', _re, methods=['GET'], name='get_debug_flags')

    _fn = g['get_injection_trace']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_injection_trace', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_injection_trace', _re)
    g['get_injection_trace'] = _re
    router.add_api_route('/debug/injection-trace', _re, methods=['GET'], name='get_injection_trace')

    for _name, _path, _methods in (
        ('budget_probe_ep', '/debug/budget-probe', ['POST']),
        ('get_debug_locks', '/debug/locks', ['GET']),
        ('get_debug_audit_log', '/debug/audit-log', ['GET']),
        ('post_debug_audit_purge', '/debug/audit-purge', ['POST']),
        ('get_debug_run_cards', '/debug/run-cards', ['GET']),
        ('get_debug_run_card', '/debug/run-cards/{run_id}', ['GET']),
        ('post_debug_run_cards_purge', '/debug/run-cards/purge', ['POST']),
        ('get_debug_pipeline_traces', '/debug/pipeline-traces', ['GET']),
        ('get_debug_pipeline_trace', '/debug/pipeline-traces/{trace_id}', ['GET']),
        ('get_debug_pipeline_trace_spans', '/debug/pipeline-traces/{trace_id}/spans', ['GET']),
        ('get_debug_pipeline_spans', '/debug/pipeline-spans', ['GET']),
        ('get_debug_pipeline_logs', '/debug/pipeline-logs', ['GET']),
        ('get_debug_recall_shadow', '/debug/recall-shadow', ['GET']),
        ('get_debug_pipeline_events', '/debug/pipeline-events', ['GET']),
        ('get_debug_pipeline_artifacts', '/debug/pipeline-artifacts', ['GET']),
        ('get_debug_pipeline_artifact', '/debug/pipeline-artifacts/{artifact_id}', ['GET']),
        ('post_debug_pipeline_traces_purge', '/debug/pipeline-traces/purge', ['POST']),
        ('get_debug_stats', '/debug/stats', ['GET']),
        ('soft_event_led_ep', '/soft/event-led', ['POST']),
        ('soft_discourse_ep', '/soft/discourse', ['POST']),
        ('soft_precheck_ep', '/soft-precheck', ['POST']),
        ('literary_distill_ep', '/literary-distill', ['POST']),
        ('event_graph_ep', '/event-graph', ['POST']),
    ):
        _fn = g[_name]
        _re = types.FunctionType(
            _fn.__code__, core.__dict__, _name, _fn.__defaults__, _fn.__closure__,
        )
        if _fn.__annotations__:
            _re.__annotations__ = dict(_fn.__annotations__)
        setattr(core, _name, _re)
        g[_name] = _re
        router.add_api_route(_path, _re, methods=_methods, name=_name)

_bind_and_register()
