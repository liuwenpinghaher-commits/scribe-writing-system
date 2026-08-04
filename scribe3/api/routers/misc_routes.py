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
                seq: int | None = None, thread: str | None = None):
    """主编对话(SSE 流式)。注入本书设定上下文,经 Hermes 逐字回流。
    seq(时机C):当前讨论章号,注入脉搏速览——主编讨论时能主动带出超期伏笔等信号。
    U-005:讨论也留痕(挂本 work 稳定主编线程,与写作时间线连续)——此前讨论从不落库。
    U-009:留痕反哺为对话记忆(history 注入)——此前单遍无续接,主编每轮失忆。"""
    from scribe3.llm import hermes_complete_stream
    st = _store_for(work)
    thread_id = _editor_turn_context(
        work, thread_row=_resolve_thread_or_raise(work, thread)).thread_id
    # P0b:流结束后增量摘要(阈值内秒退零成本;失败 summary_error 前端红字)
    background.add_task(_maybe_summarize_thread, work, thread_id)

    def gen():
        # U-011:上下文组装(设定圣经/脉搏/历史)挪进流内——组装崩时 error 帧携带【异常原文】
        # 到前端内联显示(作者能看见真实原因),而不是开流前 500 → 前端只见笼统"连接中断"。
        try:
            sysmsg = _editor_system(st) + _pulse_digest(st, seq) + _DISCUSSION_DIRECTIVE
            history = _thread_history_for_prompt(st, thread_id)   # 先于 _ChatTurnLog 落本轮 user
        except Exception as e:
            logging.getLogger("scribe3").error("chat_stream 上下文组装失败", exc_info=True)
            yield f"data: {json.dumps({'error': f'上下文组装失败:{type(e).__name__}: {str(e)[:200]}'}, ensure_ascii=False)}\n\n"
            yield 'data: {"done": true}\n\n'
            return
        with _ChatTurnLog(st, user_text=msg, chapter=seq or 0, stage="discuss",
                          thread_id=thread_id) as clog:
            try:
                for delta in hermes_complete_stream(msg, system=sysmsg, history=history):
                    clog.feed(delta)
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            except Exception as e:  # 失败如实回流,不静默
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")

def chat_agentic_stream(msg: str, background: BackgroundTasks, work: str = "main",
                        seq: int | None = None, thread: str | None = None):
    """主编 agentic 对话(SSE):经 scribe3 网关 /v1/responses,主编自调 s3_ 工具查 SurrealDB 真实数据。
    事件:tool(工具调用提示)/delta(回复片段)/done。"""
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.llm import hermes_responses_events
    fn = _responses_events or hermes_responses_events
    adapter = HermesEventAdapter()
    # H-01:工具 work-scoped,所有作品都可挂工具;提示必须钉死当前 work,防跨书读写。
    with_tools = _work_has_tools(work)

    # Task 11:稳定 session key = work+thread(切章不换 Hermes session,主编历史连续);
    # 会话续接锚 conversation/previous_response 从线程行取(掉链常态,由 Scribe 侧重建兜底)。
    turn = _editor_turn_context(work, thread_row=_resolve_thread_or_raise(work, thread))
    st = _store_for(work)
    background.add_task(_maybe_summarize_thread, work, turn.thread_id)   # P0b 增量摘要

    def _build_instructions() -> str:
        # U-011:组装挪进流内(经 gen 的 try)——设定/脉搏取数崩时 error 帧带异常原文到前端,
        # 而不是开流前 500 只显"连接中断"。
        ins = _editor_system(st) + _pulse_digest(st, seq)
        if with_tools:
            ins += _s3_work_scope_block(work) + (
                "\n\n你能调用 s3_ 工具实时查询/操作这部书的 SurrealDB(知识帧 s3_project_frame、反讽 s3_dramatic_irony、"
                "伏笔 s3_list_promises、母题 s3_list_motifs、章节 s3_get_chapter、确定性QC s3_qc_chapter、纪律判官 "
                "s3_discipline_check、语义召回 s3_semantic_recall、因果 s3_causal_complete 等)。"
                "回答前先用只读工具核实真实数据,不臆测;引用数据时说明来自哪个工具。"
                "写操作(加角色/事实/伏笔等)会进入待批,不会立即生效。"
            )
            from scribe3.craft_skills import skills_index_block
            ins += skills_index_block()   # P1 定案B:技法索引(渐进披露,全文靠 s3_skill_read)
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
        # U-005:agentic 讨论/审批也留痕(此前从不落库——《印迹》批准写入 15 世界规则 +
        # 6 势力的整场对话凭空消失)。工具调用/审批帧【不】进对话留痕(它们已在 ai_run_trace
        # 有账;灌进历史会把对话淹没),只留 user + assistant 最终文本。
        with _ChatTurnLog(st, user_text=msg, chapter=seq or 0, stage="discuss",
                          thread_id=turn.thread_id) as clog:
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
                    # U-003 回滚(v2):曾想给主编 agentic 联查挂专属 CHIEF label 隔离
                    # reveal 工具,真机实测证明 server_label 不过滤——挂了等于两条路径
                    # 都拿到。故与写作路径共用同一个 READ label;当前 6 把 *_reveal
                    # 工具不挂在任何网关上(见 SCRIBE3_READ_MCP_LABEL 定义处注释)。
                    server_label=SCRIBE3_READ_MCP_LABEL,
                )
                for ev in events:
                    app_ev = adapter.adapt(ev)
                    if app_ev["kind"] == "text.delta":
                        d = app_ev.get("delta", "")
                        if d:
                            clog.feed(d)
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
                        clog.set_response_id(resp_id)
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
    # 工艺优先:实质正文须过 GATE-A(首篇)/GATE-B;见 verify_craft_compliance.evaluate_save_craft_gate
    try:
        from scribe3.verify_craft_compliance import evaluate_save_craft_gate
        cg = evaluate_save_craft_gate(
            st, req.seq, req.prose, skip=bool(req.skip_craft_gate))
        if not cg.get("allowed"):
            raise HTTPException(status_code=409, detail={
                "code": cg.get("code") or "craft_gate",
                "message": cg.get("detail") or "工艺门闩未通过",
                "blocking": cg.get("blocking") or [],
                "root_causes": cg.get("root_causes") or [],
                "reports": cg.get("reports") or {},
            })
    except HTTPException:
        raise
    except Exception as e:
        # fail-loud:门闩评估抛错不得静默放行实质正文(防门闩故障=无门)
        import logging
        logging.getLogger("scribe3").error(
            "craft gate 评估失败(阻断存稿) work=%s seq=%s: %s", work, req.seq, e,
            exc_info=True)
        raise HTTPException(status_code=503, detail={
            "code": "craft_gate_error",
            "message": f"工艺门闩评估失败,已阻断存稿: {e}",
        }) from e
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
            raise HTTPException(status_code=409, detail={
                "code": fg_decision.get("code") or "finalize_gate",
                "message": fg_decision.get("detail") or "定稿门闩未通过",
                "verdict": fg_decision.get("verdict"),
                "blocking": fg_decision.get("blocking") or [],
                "advisory_items": fg_decision.get("advisory_items") or [],
                "danger_draft_hint": "显式传 danger_draft=true 可旁路(危险,仅草稿)",
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
    enqueued = _enqueue_ingest(background, work, req.seq)
    out = {"status": "saved", "seq": req.seq,
            "qc": {"repetition": len(qf["repetition"]), "structural": len(qf["structural"]),
                   "purple": len(qf["purple"]), "cross_repetition": len(cross_rep),
                   "duplicate_lines": dup_lines_count, "emotion_telling": emotion_telling_count},
            "cross_repetition_phrases": [h["phrase"] for h in cross_rep[:12]],
            "leaks": leaks, "leak_error": leak_error,
            "qc_errors": qc_errs or None, "ingesting": bool(enqueued),
            "ingest_enqueued": bool(enqueued)}
    if fg_decision is not None:
        out["finalize_gate"] = {
            "code": fg_decision.get("code"),
            "verdict": fg_decision.get("verdict"),
            "danger_draft": bool(req.danger_draft),
            "advisory_count": len(fg_decision.get("advisory_items") or []),
            "blocking_count": len(fg_decision.get("blocking") or []),
        }
    return out

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
        # KR1: final 覆写前过定稿门闩(与 save-chapter 单源)
        from scribe3.finalize_gate import check_finalize_for_save
        _fg = check_finalize_for_save(
            st, seq, res["prose"], focalizer=ch.get("focalizer") or None)
        if not _fg.get("allowed"):
            raise HTTPException(status_code=409, detail={
                "code": _fg.get("code") or "finalize_gate",
                "message": _fg.get("detail") or "去重改写结果未过定稿门闩,未落库",
                "blocking": _fg.get("blocking") or [],
                "rewritten_unsaved": res["rewritten"],
            })
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
        from scribe3.finalize_gate import check_finalize_for_save
        _fg = check_finalize_for_save(
            st, seq, res["prose"], focalizer=ch.get("focalizer") or None)
        if not _fg.get("allowed"):
            raise HTTPException(status_code=409, detail={
                "code": _fg.get("code") or "finalize_gate",
                "message": _fg.get("detail") or "精修结果未过定稿门闩,未落库",
                "blocking": _fg.get("blocking") or [],
                "rewritten_unsaved": res["rewritten"],
            })
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
    candidate = (hermes_complete(prompt, max_tokens=max(2048, min(8192, len(original) * 2)),
                                 retries_override=1, thinking="disabled",
                                 temperature=0,
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
    st.save_chapter(seq, candidate, title=ch.get("title") or "", focalizer=ch.get("focalizer") or "")
    st.add_chapter_version(seq, candidate, label="semantic repair", kind="final", stage="semantic_repair",
                           stats=_prose_stats(candidate))
    # 正文已变化，必须与手动存稿/去重改写保持同一账本更新语义；队列去重会避免双跑。
    _enqueue_ingest(background, work, seq)
    return {"status": "repaired", "seq": seq, "gate": gate,
            "discipline": after.get("discipline") or {}, "ingesting": True}

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
    """取该章最新 draft 版(prose+stats),供刷新恢复。无 draft 版返回空对象 {}。"""
    v = _store_for(work).latest_draft_version(seq)
    if not v:
        return {}
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

_bind_and_register()
