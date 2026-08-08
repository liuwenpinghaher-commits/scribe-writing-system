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

from scribe3.api.sse import sse_response

router = APIRouter(tags=['write'])


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


def chat_write(msg: str, chapter: int = 1, focalizer: str = "", phase: str = "",
               work: str = "main", short_mode: bool = False):
    """对话驱动写作(SSE):主编自判讨论 vs 动稿;动稿用 ⟦PROPOSAL⟧ 围栏回传新散文。
    事件:delta(对话,进右轨)/ tool(工具调用)/ proposal(草稿,进中区)/ done。
    P0门对抗审查 P2-1:改调 _assemble_write_instructions 单源——此前 GET 自带一套
    内联组装且已漂移(缺 _revelation_discipline_block 限知揭示纪律),旧注入点教训
    (每新开一个注入点都泄露过一次)对 GET 同样成立;现与 POST/loop 物理同源。
    不落库(台账 D-005,无生产调用方的兼容端点)。"""
    st = _store_for(work)
    # 明确动稿时，统一上下文已经给足正典、结构与限知材料；即使 UI 仍处在 draft，
    # 也不能再挂 MCP 让模型把未执行的工具调用混进提案或陷入工具循环。讨论/核查
    # （_is_write_intent=False）才保留 work 作用域工具，多书约束仍由提示层强制。
    _write_intent = _is_write_intent(msg)
    _wt = _work_has_tools(work) and _write_phase_allows_tools(phase) and not _write_intent
    outcome_binding = _WriteOutcomeBinding(st)
    instructions = _assemble_write_instructions(
        st, chapter=chapter, focalizer=focalizer, phase=phase,
        seed_words=[], short_mode=short_mode, with_tools=_wt, work=work,
        envelope_trace=outcome_binding.manifest_trace, request_text=msg)
    return sse_response(
        _stream_write(msg, instructions, expect_proposal=_write_intent,
                      with_tools=_wt, on_terminal=outcome_binding.persist),
    )

def chat_write_post(req: ChatWriteReq, request: Request, background: BackgroundTasks,
                    work: str = "main"):
    """POST 版写作对话(支持图片附件):前端用 fetch 流式读取。"""
    # 经验压力 E4:硬续写模式未确认重读则禁止生成(草稿存不受此限)
    try:
        from scribe3.api.services.write_assemble import check_generate_reread_gate
        _rg = check_generate_reread_gate(work, int(req.chapter or 1))
        if not _rg.get("allowed"):
            raise HTTPException(status_code=409, detail={
                "code": _rg.get("code") or "reread_required",
                "message": _rg.get("detail") or "请先确认续写重读",
            })
    except HTTPException:
        raise
    except Exception:
        pass
    st = _store_for(work)
    # Task 4:context 绑定强校验(SCRIBE3_CONTEXT_SNAPSHOT_V1 门控,产品默认开;显式关则不强制)。
    # 必须在 user 落库与 StreamingResponse 之前完成——流一旦开始,4xx 会退化成流中错误。
    # 双通道(I-1):body 三件套缺失时逐字段回退请求头 X-Scribe-Context-*
    # (api.js contextHeaders 产出),两通道都缺才 400。
    try:
        ContextService(st).enforce(req, work, headers=request.headers)
    except (ContextServiceError, StaleContextError) as e:
        raise _context_http_error(e) from e
    # P0a 零降级:前端带了 thread_id 就必须有效(404/409),绝不静默回落——
    # 同 chat_stream 的 _resolve_thread_or_raise 口径;必须在开流前抛(流中 4xx 会退化)。
    _resolve_thread_or_raise(work, req.thread_id)
    if req.thread_id:
        background.add_task(_maybe_summarize_thread, work, req.thread_id)   # P0b 增量摘要
    # 与 GET /chat/write 同一纪律：明确动稿已有完整上下文，draft/final 都应保持
    # 纯散文输出，不能夹带尚未执行的工具调用或进入无界的代理式联查。
    _write_intent = _is_write_intent(req.msg)
    _wt = _work_has_tools(work) and _write_phase_allows_tools(req.phase) and not _write_intent
    # 统一内核把 envelope 安全块清单回填这里，随 assistant 落 trace.context；
    # 编译失败会在开流前直接上抛，不存在 flag 关闭或旧链回退形成的空 trace。
    outcome_binding = _WriteOutcomeBinding(st)
    _envelope_trace = outcome_binding.manifest_trace
    # Task 16 最后一厘米:前端真实会话绑定(供 v1 检索路径落 memory_trace 给 ContextInspector);
    # 三件套优先 body,缺失回退请求头 X-Scribe-Context-*。仅 MEMORY_FABRIC 开 + 绑定齐备时
    # 被消费落 trace；fabric 关/无绑定时不影响写作字节(纯落库副作用,与 chat_message 同 best-effort)。
    _memory_trace_ctx = _write_context_binding(req, request.headers)
    instructions = _assemble_write_instructions(
        st, chapter=req.chapter, focalizer=req.focalizer, phase=req.phase,
        seed_words=req.seed_words, short_mode=req.short_mode, with_tools=_wt, work=work,
        envelope_trace=_envelope_trace, memory_trace_ctx=_memory_trace_ctx,
        request_text=req.msg)

    if req.images:
        content = [{"type": "input_text", "text": req.msg}]
        for img in req.images:
            content.append({"type": "input_image", "image_url": f"data:{img.type};base64,{img.data}"})
        message = [{"role": "user", "content": content}]
    else:
        message = req.msg

    # 北极星任务1:会话落库(蓝图 §4-② 第1级)——user 受理即写,assistant 流尽回调写;
    # 均 best-effort(D-004),落库失败只告警,绝不影响写作主链路。
    # turn id(P2-6):串起本轮 user/assistant,防并发会话交错污染蒸馏配对。
    import uuid
    turn_id = uuid.uuid4().hex[:12]
    user_text = req.msg + (f"\n[附图{len(req.images)}张]" if req.images else "")
    # Task 6:线程归属 + 本轮 context 绑定/焦点标签随消息落库(切焦点不切线程);
    # 全 optional,存量调用方(不传 thread_id)仍走 backfill 的默认线程回看。
    _bind = dict(thread_id=req.thread_id, context_session_id=req.context_session_id,
                 context_revision=req.context_revision, context_hash=req.context_hash,
                 focus=req.focus)
    try:
        st.add_chat_message(chapter=req.chapter, stage=req.phase, role="user",
                            text=user_text, turn=turn_id, **_bind)
    except Exception:
        logging.getLogger("scribe3").warning("chat_message user 落库失败(忽略)", exc_info=True)

    def _persist_assistant(text: str, trace: dict | None = None) -> None:
        # assistant 侧 response_id 取自 Hermes trace(便于按响应回溯本轮)。
        trace = dict(trace or {})
        # 统一内核成功编译后必有 envelope 安全块清单，随后并入 trace.context，
        # 供审计"主编这轮看到了哪些上下文块"。manifest 每块仅记
        # name/token/source id/被屏蔽 source id,绝无块正文与秘密 value(限知红线)。
        # 编译失败直接上抛，不会以旧链空 trace 伪装成功。
        _ctx = _envelope_trace.get("context")
        if _ctx:
            trace["context"] = _ctx
        # 无文本失败/取消只落硬 Outcome，不改变原有“无空 assistant 消息”口径。
        if not text:
            return
        resp_id = trace.get("response_id")
        st.add_chat_message(chapter=req.chapter, stage=req.phase, role="assistant",
                            text=text, turn=turn_id, trace=trace,
                            response_id=resp_id, **_bind)
        # Task 9:本轮作者意图捕获成经验记忆(幂等 + 同步 drain;每 8 轮/会话末 consolidate)。
        # 捕获作者原话(决策/偏好/不确定的真源),不碰正文生成与 prompt 组装(写作路径零改动)。
        _capture_turn_memory(st, work=work, thread_id=(req.thread_id or f"write:{work}"),
                             turn_id=turn_id, text=user_text, chapter=req.chapter)

    return sse_response(
        _stream_write(message, instructions, expect_proposal=_write_intent,
                      with_tools=_wt,
                      on_terminal=outcome_binding.persist,
                      on_complete=_persist_assistant),
    )

def qc(seq: int, work: str = "main"):
    """本章正文确定性体检(读已存正文,即算即返;全为确定性扫描,不打 LLM)。

    在原 quality_flags 五项(repetition/structural/purple/ai_tics/oversaturation)之外,
    补全 /save-chapter 同款的单章检测器:cross_repetition(跨章逐字复读)、
    duplicate_lines(整句重复)、emotion_telling(情感直说)。每项各自 fail-soft。

    返回每项为命中列表(前端取 length 显数、可点开看命中短语);另附
    cross_repetition_phrases 供高亮定位。cross_consistency 属全书聚合(非单章),
    留在 /post-check,不在此触发以免面板加载时跑全书查询。"""
    from scribe3.critique import (quality_flags, find_cross_chapter_repetitions,
                                  find_duplicate_lines, find_emotion_telling)
    import logging
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {}
    prose = ch["prose"]
    out = dict(quality_flags(prose))   # 五项:各为命中列表
    # U-011(作者要 fail-loud):检测器失败此前静默归空([]),与"真没问题"无区别=质控假绿。
    # 改成把失败记进 detector_errors 字段(照抄 leak_error 范式),前端据此显红字"检测器故障·
    # 本次未检"——既 fail-loud 又不 500 掉整个 QC 面板(其余检测器结果仍返回)。
    det_errs: dict[str, str] = {}
    # 跨章复读(比对前文最近 8 章逐字 ≥8 字重叠,母题白名单放行)
    cross_rep: list[dict] = []
    try:
        priors = [c["prose"] for c in st.recent_proses(seq, k=8) if c.get("prose")]
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        cross_rep = find_cross_chapter_repetitions(prose, priors, n=12, allow=allow)
    except Exception as e:
        logging.getLogger("scribe3").error("qc cross_repetition 失败 work=%s seq=%s", work, seq, exc_info=True)
        det_errs["cross_repetition"] = str(e)[:120]
    out["cross_repetition"] = cross_rep
    out["cross_repetition_phrases"] = [h.get("phrase") for h in cross_rep[:12]]
    # 整行复读
    try:
        out["duplicate_lines"] = find_duplicate_lines(prose)
    except Exception as e:
        logging.getLogger("scribe3").error("qc duplicate_lines 失败 work=%s seq=%s", work, seq, exc_info=True)
        out["duplicate_lines"] = []
        det_errs["duplicate_lines"] = str(e)[:120]
    # 情感直说
    try:
        out["emotion_telling"] = find_emotion_telling(prose)
    except Exception as e:
        logging.getLogger("scribe3").error("qc emotion_telling 失败 work=%s seq=%s", work, seq, exc_info=True)
        out["emotion_telling"] = []
        det_errs["emotion_telling"] = str(e)[:120]
    if det_errs:
        out["detector_errors"] = det_errs
    return out

def check_prose(req: CheckReq, seq: int | None = Query(default=None), work: str = "main"):
    """护栏轻检查:QC + 限知泄露,不落库(改造③ 停笔静默刷新用)。
    F-05: 新增顶层 issues 列表(带 range),兼容旧 qc/leaks 计数字段。

    章号解析：query ?seq= 优先，否则 body.seq / body.chapter（避免只传 body 时 422）。"""
    resolved = seq if seq is not None else (req.seq if req.seq is not None else req.chapter)
    if resolved is None:
        raise HTTPException(
            status_code=422,
            detail="需要章号：query ?seq= 或 body.seq / body.chapter",
        )
    seq = int(resolved)
    st = _store_for(work)
    from scribe3.critique import quality_flags, quality_issues
    # 方案B任务14:本书 craft 豁免——extra(升华正则加法)+ allow_words/allow_patterns
    # (前置 skip 判定,减法),fail-soft(取不到就退回 None,不影响本次检查)。
    import logging
    extra = allow_words = allow_pats = None
    try:
        extra = st.purple_patterns() if hasattr(st, "purple_patterns") else None
        allow_words = set(st.allow_words()) if hasattr(st, "allow_words") else None
        allow_pats = st.allow_patterns() if hasattr(st, "allow_patterns") else None
    except Exception as e:
        logging.getLogger("scribe3").warning("check 取 craft 豁免失败: %s", e)
    qf = quality_flags(req.prose, extra, allow_words, allow_pats)
    # U-011(作者要 fail-loud):find_leaks/quality_issues 失败此前静默返空——停笔静默检查面板
    # 显示"零泄露/零问题",与真干净的稿子无法区分=招牌能力(限知泄露检测)静默失效。
    # 改标 leaks_error/issues_error(同 /save-chapter 的 leak_error 范式),前端护栏面板显红。
    # 不 raise:这是停笔高频轻检查,raise 会把每次静默刷新变 500 噪声,error 字段已足够响。
    leaks = []
    leaks_error = None
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks_for_chapter as find_leaks
            leaks = [{"fact_id": lk.fact_id, "marker": lk.marker, "subject": lk.subject,
                      "range": list(lk.range) if lk.range else None}
                     for lk in find_leaks(req.prose, st, req.focalizer, seq)]
        except Exception as e:
            logging.getLogger("scribe3").error("check find_leaks 失败", exc_info=True)
            leaks_error = str(e)[:120]

    # F-05: 组装带 range 的 issues(白送类 QC + leaks)
    issues: list[dict] = []
    issues_error = None
    try:
        issues = quality_issues(req.prose, extra, allow_words, allow_pats)
    except Exception as e:
        logging.getLogger("scribe3").error("check quality_issues 失败", exc_info=True)
        issues_error = str(e)[:120]
    # 追加 leak issues
    for lk in leaks:
        issues.append({
            "type": "leak",
            "message": f"限知泄露:视角角色不该知道「{lk['marker']}」",
            "text": lk["marker"],
            "range": lk["range"],
            "meta": {"fact_id": lk["fact_id"], "subject": lk["subject"]},
        })

    resp = {"qc": {"repetition": len(qf["repetition"]),
                   "structural": len(qf["structural"]),
                   "purple": len(qf["purple"]),
                   "ai_tics": len(qf["ai_tics"]),
                   "oversaturation": len(qf["oversaturation"])},
            "leaks": leaks, "leaks_error": leaks_error,
            "issues": issues, "issues_error": issues_error}
    # 方案A任务8:整章 AI 味定档聚合,fail-soft(异常时不给该字段,不 500)。
    try:
        from scribe3.critique import aggregate_ai_grade
        resp["ai_grade"] = aggregate_ai_grade(qf, req.prose, short_mode=req.short_mode)
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning("check aggregate_ai_grade 失败: %s", e)
    return resp

def post_check(req: PostCheckReq, seq: int | None = Query(default=None), work: str = "main"):
    """生成后全量体检:五类确定性 QC + 限知泄露 + LLM 语义纪律判(fail-open)。
    不落库。注册为 read-only POST(见 KNOWN_REST_WRITE_ROUTES)。
    F-05: 新增顶层 issues 列表(带 range),兼容旧 quality/leaks 字段。
    M2-②: 新增 duplicate_lines/emotion_telling(B/C 检测器)+ cross_consistency(跨章矛盾)。

    章号：query ?seq= 优先，否则 body.seq / body.chapter。"""
    import logging
    from scribe3.critique import (quality_flags, quality_issues, discipline_truncate,
                                  find_duplicate_lines, find_emotion_telling,
                                  find_parallelism, find_poetic_fragments,
                                  find_unbalanced_quotes, find_watch_regression)
    resolved = seq if seq is not None else (req.seq if req.seq is not None else req.chapter)
    if resolved is None:
        raise HTTPException(
            status_code=422,
            detail="需要章号：query ?seq= 或 body.seq / body.chapter",
        )
    seq = int(resolved)
    st = _store_for(work)

    # 方案B任务14:本书 craft 豁免——extra(升华正则加法)+ allow_words/allow_patterns
    # (前置 skip 判定,减法),fail-soft(取不到就退回 None,不影响本次体检)。
    extra = allow_words = allow_pats = None
    try:
        extra = st.purple_patterns() if hasattr(st, "purple_patterns") else None
        allow_words = set(st.allow_words()) if hasattr(st, "allow_words") else None
        allow_pats = st.allow_patterns() if hasattr(st, "allow_patterns") else None
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check 取 craft 豁免失败: %s", e)

    # 方案B任务19:跨批开放伏笔账本注入 reviewer(scribe3 DB 优势区)——同一处取
    # craft 豁免的上下文里,顺手筛"预计回收章≤本章"的 open promise 作"继承的
    # 开放项",供下面 LLM 纪律判读作背景(未处理的坑要在 findings 里指出)。
    # fail-soft:取不到不影响本次体检其余字段。
    from scribe3.brief import inherited_open_block
    # U-011:degraded_stages 提前初始化,让下方 inherited_open 失败也能记进去(此前它在
    # degraded_stages 定义之前、失败只 log 不进 degraded=同函数其余检测器的假绿盲区)。
    degraded = False
    degraded_stages: list[str] = []
    inherited_open_promises: list[dict] = []
    inherited_text = ""
    try:
        inherited = inherited_open_block(st.promises_with_lifecycle(max_chapter=seq), chapter=seq)
        inherited_open_promises = inherited["items"]
        inherited_text = inherited["text"]
    except Exception as e:
        logging.getLogger("scribe3").error("post_check inherited_open_block 失败", exc_info=True)
        degraded = True
        degraded_stages.append("inherited_open")

    # 1. 确定性五类 QC
    qf = quality_flags(req.prose, extra, allow_words, allow_pats)
    qc_breakdown = {
        "repetition": len(qf["repetition"]),
        "structural": len(qf["structural"]),
        "purple": len(qf["purple"]),
        "ai_tics": len(qf["ai_tics"]),
        "oversaturation": len(qf["oversaturation"]),
    }
    qc_total = sum(qc_breakdown.values())

    # 2. 限知泄露(有 focalizer 才跑)
    leaks: list[dict] = []
    leaks_degraded = False
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks_for_chapter as find_leaks
            leaks = [{"fact_id": lk.fact_id, "marker": lk.marker, "subject": lk.subject,
                      "range": list(lk.range) if lk.range else None}
                     for lk in find_leaks(req.prose, st, req.focalizer, seq)]
        except Exception as e:
            logging.getLogger("scribe3").warning("post_check find_leaks 失败: %s", e)
            leaks_degraded = True

    # 3. LLM 语义纪律判(fail-open)
    discipline: dict = {}
    # U-011:degraded/degraded_stages 已在上方(inherited 之前)初始化,此处不再重置,
    # 让 inherited_open 的失败也累积进最终 degraded_stages。
    try:
        # 测试注入出口保持兼容；真实 Pilot quality 必须经统一上下文链。
        complete_fn = _complete_fn
        if complete_fn is None:
            from scribe3.llm import default_timeout
            # /post-check 是作者交互式只读体检，须限制单次尝试和输出预算；完整章节的
            # 纪律判在官方模型实测约 49 秒，高负载章节可超过 90 秒；30/90 秒都会把
            # 已连通的模型误判为降级。180 秒仍远低于生成级 600 秒，保留可控上界。
            def complete_fn(prompt: str, system: str | None = None) -> str:
                return _contextual_review_complete(
                    st, work, seq, "quality_chapter", prompt, system=system,
                    timeout=min(float(default_timeout()), 180.0),
                    max_tokens=480, retries_override=1,
                    thinking="disabled", temperature=0,
                )
        # 任务19:有到期继承开放项时拼进 brief——若调用方未传 brief,先补回
        # build_discipline_prompt 的默认纪律文案(DEFAULT_DISCIPLINE_BRIEF 单一来源,
        # 收尾清理批 Minor:消除手写字面量副本的漂移风险),再拼继承项,
        # 避免"继承开放项非空"顶掉默认纪律要求(两者都该在场)。
        brief_for_discipline = req.brief
        if inherited_text:
            from scribe3.critique import DEFAULT_DISCIPLINE_BRIEF
            base_brief = req.brief or DEFAULT_DISCIPLINE_BRIEF
            brief_for_discipline = base_brief + "\n\n" + inherited_text
        # 章后缓存互通：同正文指纹可复用纪律结果（终选/重分析/上次体检）
        try:
            from scribe3.chapter_analysis import run_discipline_with_cache
            discipline = run_discipline_with_cache(
                work=work,
                seq=seq,
                prose=req.prose,
                complete_fn=complete_fn,
                brief=brief_for_discipline or "",
                st=st,
                force=False,
            )
        except Exception:
            discipline = discipline_truncate(req.prose, brief_for_discipline, complete_fn)
        # 审计 E-2/#58:LLM 回复解析失败 → fail-open 放行但计 degraded(没查≠没病;
        # 不入 _PASS_CRITICAL_STAGES——纪律判是 S1 来源,不是 pass 门关键检测)。
        if discipline.get("parse_failed"):
            degraded = True
            degraded_stages.append("discipline_parse")
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check discipline 失败: %s", e)
        degraded = True
        degraded_stages.append("discipline")
    if leaks_degraded:
        degraded = True
        degraded_stages.append("find_leaks")

    # 4. 设定校验:物品状态/OOC/世界规则/命名一致性(fail-soft)
    setting: list[dict] = []
    try:
        setting = st.validate_setting(seq, req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check validate_setting 失败: %s", e)
        degraded = True
        degraded_stages.append("validate_setting")

    # F-05: 组装带 range 的顶层 issues(白送类 QC + leaks + discipline.cut_after)
    issues: list[dict] = []
    try:
        issues = quality_issues(req.prose, extra, allow_words, allow_pats)
    except Exception as e:
        # P0门审查 P1-4:issues 喂 loop 的 blocking 判据②(degeneration)与待批清单,
        # 该 stage 挂掉必须记 degraded——否则"没查被当没病",loop 会假绿宣 pass。
        logging.getLogger("scribe3").warning("post_check quality_issues 失败: %s", e)
        degraded = True
        degraded_stages.append("quality_issues")
    # leak issues
    for lk in leaks:
        issues.append({
            "type": "leak",
            "message": f"限知泄露:视角角色不该知道「{lk['marker']}」",
            "text": lk["marker"],
            "range": lk["range"],
            "meta": {"fact_id": lk["fact_id"], "subject": lk["subject"]},
        })
    # 纪律违规 issue(遗留处置 1-A)。violations 即报——此前 cut_after 为空时违规被
    # 静默吞;cut_after 只负责定位。severity 三重防误杀:单次 LLM 判默认 S2(advisory);
    # 仅确定性信号同向命中(共振表,≤5 条硬编码)才升 S1 → triage blocking 判据④;
    # 熔断开(近 10 次 loop S1 触发率>30%)时升格暂停。共振表(自定口径,待盲评池校准):
    #   knowledge_leak ↔ find_leaks 命中 或 god_view(kind=god_spoiler,叙述层知识泄露形态)
    #   god_view       ↔ god_view(kind∈{god_spoiler,explain_causality};批次一审查 P1-1:
    #                    summarize 的"此刻,他"/sublimation 是好稿常见句式或纯风格,
    #                    与全知违规同向性不足,拿来共振=为无关违规背书,故收窄强全知两类)
    #   exposition_dump↔ oversaturation>0
    #   double_climax / voice_collapse 无确定性对应物 → 恒 S2
    if discipline.get("violations") or discipline.get("cut_after"):
        cut = discipline.get("cut_after") or ""
        idx = req.prose.find(cut) if cut else -1
        rng = [idx, idx + len(cut)] if (cut and idx >= 0) else None
        _viol = set(discipline.get("violations") or [])
        _god_kinds = {(i.get("meta") or {}).get("kind")
                      for i in issues if i.get("type") == "god_view"}
        _resonance = (
            ("knowledge_leak" in _viol and (bool(leaks) or "god_spoiler" in _god_kinds))
            or ("god_view" in _viol
                and bool(_god_kinds & {"god_spoiler", "explain_causality"}))
            or ("exposition_dump" in _viol
                and (qc_breakdown.get("oversaturation") or 0) > 0)
        )
        _sev = "S1" if (_resonance and not _s1_circuit_open(work)) else "S2"
        issues.append({
            "type": "discipline",
            "message": f"纪律违规:{'、'.join(discipline.get('violations', []))}",
            "text": cut,
            "range": rng,
            "meta": {"violations": discipline.get("violations", []),
                     "extra": discipline.get("extra") or [],   # LLM 自由文本观察(D-024,不参与升格)
                     "severity": _sev, "resonance": _resonance},
        })
    # setting issues
    for hint in setting:
        evidence = hint.get("evidence") or ""
        idx = req.prose.find(evidence) if evidence else -1
        rng = [idx, idx + len(evidence)] if idx >= 0 and evidence else None
        issues.append({
            "type": "setting",
            "message": hint.get("description", "设定校验问题"),
            "text": evidence,
            "range": rng,
            "meta": {"entity": hint.get("entity"), "severity": hint.get("severity")},
        })

    # 方案A任务7:同义词循环(elegant_variation)——需要角色名单,纯函数层拿不到,
    # 不进 quality_flags;这里用 store 上下文取角色名单再调用,fail-soft(取不到角色/
    # store 异常时直接跳过,不影响 /post-check 整体 200)。
    try:
        from scribe3.critique import find_elegant_variation
        names = [c.name for c in st.characters()]
        for hit in find_elegant_variation(req.prose, names):
            issues.append({
                "type": "elegant_variation",
                "message": f"同义词循环:「{hit['name']}」被泛称({'、'.join(hit['aliases'])})反复替换指代,疑似刻意避重复过犹不及",
                "text": hit["name"],
                "range": hit["range"],
                "meta": {"aliases": hit["aliases"]},
            })
    except Exception as e:
        logging.getLogger("scribe3").error("post_check find_elegant_variation 失败", exc_info=True)
        degraded = True
        degraded_stages.append("elegant_variation")

    # M2-②: 接线 B/C 检测器 + 跨章矛盾(fail-soft;异常不阻断,记 degraded_stages)
    dup_lines: list[dict] = []
    try:
        dup_lines = find_duplicate_lines(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_duplicate_lines 失败: %s", e)
        degraded = True
        degraded_stages.append("find_duplicate_lines")

    emotion_telling: list[dict] = []
    try:
        # B14 审查(收尾清理批):allow_pats 已在本函数上文从 st.allow_patterns() 取出
        # (供 quality_flags/quality_issues 用),此前未传给 find_emotion_telling——
        # 题材豁免正则对直写情绪检测器不生效,这里补上,与其余检测器同一豁免机制。
        emotion_telling = find_emotion_telling(req.prose, allow_pats, short_mode=req.short_mode)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_emotion_telling 失败: %s", e)
        degraded = True
        degraded_stages.append("find_emotion_telling")

    cross_consistency: list[dict] = []
    try:
        cross_consistency = st.validate_cross_chapter_consistency()
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check validate_cross_chapter_consistency 失败: %s", e)
        degraded = True
        degraded_stages.append("validate_cross_chapter_consistency")

    # 方案B任务11:卷级张弛基线——接线落点说明:仓内无独立"全书体检/审计"端点
    # (/qc 显式注明 cross_consistency 属全书聚合但"留在 /post-check,不在此触发,以免
    # 面板加载时跑全书查询";/post-check 是仓内唯一已把"全书聚合"字段(cross_consistency/
    # orphan_edges)混入单章体检响应的端点),故本检测器同样落点于此,带 work 全章上下文
    # (遍历 st.list_chapters() 逐章解析 role/pressure,而非只看当前 seq)。fail-soft:
    # 书级扫描异常不阻断本次单章体检的其余字段。
    tension_monotony: list[dict] = []
    try:
        from scribe3.brief import find_tension_monotony, parse_chapter_meta, chapter_draft_text
        chapters_meta: list[dict] = []
        # R2-16:窄查(chapters_lite 只拉草料字段,不逐章 get_chapter 全行含 prose)——
        # 与 north_star_book 同一 tension 聚合的 2-D#5 先例对齐;chapter_draft_text 仅用
        # synopsis/beats/scene_truth,chapters_lite 全覆盖,行为等价、去掉全书 prose 拉取。
        for c in st.chapters_lite():
            meta = parse_chapter_meta(chapter_draft_text(c))
            if meta:
                chapters_meta.append({"seq": c["seq"], **meta})
        tension_monotony = find_tension_monotony(chapters_meta)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_tension_monotony 失败 work=%s: %s", work, e)
        degraded = True
        degraded_stages.append("find_tension_monotony")

    # 批E-B(P2-15):orphan_knowledge_edges 审计器接线——此前仅测试、零生产接线。
    # 真实孤儿路径:DELETE /facts 删命题时 knows 图边级联消失,但 reader_knows(独立表,
    # CREATE 非 RELATE)不级联 → 留悬挂边。全书聚合(非单章),同 cross_consistency 留在
    # /post-check;fail-soft。注:内部按边逐条 existence 查(N+1),仅在此按需体检跑,非热路径。
    orphan_edges: list[dict] = []
    try:
        orphan_edges = st.orphan_knowledge_edges()
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check orphan_knowledge_edges 失败: %s", e)
        degraded = True
        degraded_stages.append("orphan_knowledge_edges")

    # P1-10 彻查:4 个既有确定性检测器接线(此前已实现但全仓零生产接线)。
    # 排比/诗化分行/引号失配/更次倒退——均对单章成文,不需跨章上下文
    # (find_watch_regression 检测的是本章内更次序列的非单调,非跨章连续性);各自 fail-soft。
    parallelism: list[dict] = []
    try:
        parallelism = find_parallelism(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_parallelism 失败: %s", e)
        degraded = True
        degraded_stages.append("find_parallelism")

    poetic_fragments: list[dict] = []
    try:
        poetic_fragments = find_poetic_fragments(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_poetic_fragments 失败: %s", e)
        degraded = True
        degraded_stages.append("find_poetic_fragments")

    unbalanced_quotes: list[dict] = []
    try:
        unbalanced_quotes = find_unbalanced_quotes(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_unbalanced_quotes 失败: %s", e)
        degraded = True
        degraded_stages.append("find_unbalanced_quotes")

    watch_regression: list[dict] = []
    try:
        watch_regression = find_watch_regression(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check find_watch_regression 失败: %s", e)
        degraded = True
        degraded_stages.append("find_watch_regression")

    # 方案A任务8:整章 AI 味定档聚合,fail-soft(异常时不给该字段,记 degraded,不 500)。
    # 计划A尾巾(A8-Important):dup_lines/emotion_telling/parallelism/poetic_fragments
    # 上面已经算过一遍,precomputed 传进去复用,避免 aggregate_ai_grade 内部对同一份
    # req.prose 重新跑一遍这四个检测器。
    ai_grade = None
    try:
        from scribe3.critique import aggregate_ai_grade
        # P0门审查 P1-5:降级的输入检测器不得以空列表冒充结果喂 precomputed——
        # 假零会让 Gate 判不出 heavy(blocking 判据③被掏空)。缺谁让 aggregate 自己
        # 重算谁;重算仍挂会落本 except 记 aggregate_ai_grade 降级(pass 门关键 stage)。
        _pre: dict = {}
        if "find_duplicate_lines" not in degraded_stages:
            _pre["duplicate_lines"] = dup_lines
        if "find_emotion_telling" not in degraded_stages:
            _pre["emotion_telling"] = emotion_telling
        if "find_parallelism" not in degraded_stages:
            _pre["parallelism"] = parallelism
        if "find_poetic_fragments" not in degraded_stages:
            _pre["poetic_fragments"] = poetic_fragments
        ai_grade = aggregate_ai_grade(qf, req.prose, precomputed=_pre,
                                      short_mode=req.short_mode)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check aggregate_ai_grade 失败: %s", e)
        degraded = True
        degraded_stages.append("aggregate_ai_grade")

    # 方案A任务9(计划A最后一项):标点归一建议(report-only,不改写正文),fail-soft。
    punct_suggestions: list[dict] = []
    try:
        from scribe3.critique import normalize_punctuation_suggestions
        punct_suggestions = normalize_punctuation_suggestions(req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check normalize_punctuation_suggestions 失败: %s", e)
        degraded = True
        degraded_stages.append("normalize_punctuation_suggestions")

    # 批次三:时间线第一刀(季节冲突/时辰倒流/同章同主体双地),report-only——
    # 只进 advisory 通道(不设 meta.severity),永不 blocking;fail-soft 且不记
    # degraded(不在 _PASS_CRITICAL_STAGES,时间线没查成不动摇 pass 门)。
    try:
        from scribe3.critique import find_intra_chapter_time_conflicts
        for tc in find_intra_chapter_time_conflicts(req.prose):
            issues.append({"type": "timeline", "message": tc["note"], "text": tc["phrase"],
                           "range": tc["range"], "meta": {"kind": tc["kind"]}})
        for hint in st.validate_event_colocation(seq):
            issues.append({"type": "timeline", "message": hint["note"], "text": "",
                           "range": None, "meta": {"kind": "event_colocation",
                                                   "subject": hint["subject"]}})
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check timeline 检测失败(忽略): %s", e)

    # 强制闭环 ConStory+3(report-only/advisory):农历月倒退 / 压力跳变 / 记忆否认 proxy
    try:
        from scribe3.critique import (
            find_calendar_month_regression,
            find_memory_denial_hits,
            find_pressure_adjacent_jumps,
        )
        for tc in find_calendar_month_regression(req.prose):
            issues.append({"type": "timeline", "message": tc["note"], "text": tc["phrase"],
                           "range": tc.get("range"), "meta": {"kind": tc["kind"],
                                                             "constory": 1}})
        # 记忆否认:用本章 inherited 开着的 promise 文本作粗标记(有则检)
        _mk = []
        for p in (inherited_open_promises or [])[:12]:
            t = (p.get("text") or "")[:16]
            if len(t) >= 2:
                _mk.append(t)
        for hit in find_memory_denial_hits(req.prose, _mk):
            issues.append({"type": "memory", "message": hit["note"], "text": hit["phrase"],
                           "range": hit.get("range"), "meta": {"kind": hit["kind"],
                                                              "constory": 7}})
        try:
            from scribe3.brief import chapter_draft_text, parse_chapter_meta
            metas = []
            for c in st.chapters_lite() or []:
                m = parse_chapter_meta(chapter_draft_text(c))
                if m and m.get("pressure") is not None:
                    metas.append({"seq": c["seq"], "pressure": m["pressure"]})
            for j in find_pressure_adjacent_jumps(metas):
                issues.append({"type": "tension", "message": j["note"], "text": "",
                               "range": None, "meta": {"kind": j["kind"],
                                                      "constory": 18, **{k: j[k] for k in
                                                      ("seq_from", "seq_to", "delta") if k in j}}})
        except Exception as e2:
            logging.getLogger("scribe3").warning(
                "post_check pressure_jumps 失败(忽略): %s", e2)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check constory+3 失败(忽略): %s", e)

    # 方案B任务20:finding-merge 纪律——同位置"机械替换"(punct_suggestions)让位
    # "按功能改写"(issues),并给 degeneration issue 绑定 fix_action=regenerate
    # (回炉重打,不是改写)。fail-soft:异常时保留合并前的原始值,记 degraded_stages。
    try:
        from scribe3.critique import merge_findings
        issues, punct_suggestions = merge_findings(issues, punct_suggestions)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check merge_findings 失败: %s", e)
        degraded = True
        degraded_stages.append("merge_findings")

    # 北极星任务6:目的合同写后验收段(蓝图 §3-④)——结构类查库零噪声;认知类
    # LLM 三值判定(FABLES:supported 须逐字引文),只进面板与 advisory,永不进
    # blocking(宪法)。/post-check 是 read-only:此处只验收不落库,结算(settle)
    # 挂 loop pass finalize 与 /ingest 成功路径。fail-soft。
    fulfillment: dict = {"status": "not_available", "items": []}
    try:
        from scribe3.purpose import (check_fulfillment_structural,
                                     judge_knowledge_delta, parse_deltas)
        _pc_ds = parse_deltas((st.get_chapter(seq) or {}).get("deltas"))
        if _pc_ds:
            _items = check_fulfillment_structural(st, seq, _pc_ds)
            _kn_fn = _complete_fn
            if _kn_fn is None:
                from scribe3.llm import hermes_complete as _kn_fn
            for _it in _items:
                if (_it["kind"] == "knowledge" and _it["verdict"] == "not_checkable"
                        and _it.get("status") not in ("achieved", "waived")):
                    _j = judge_knowledge_delta(req.prose, _it, _kn_fn)
                    _it["verdict"] = _j["verdict"]
                    if _j.get("evidence"):
                        _it["evidence"] = _j["evidence"]
            fulfillment = {"status": "active", "items": _items,
                           "achieved": sum(1 for i in _items
                                           if i["verdict"] in ("achieved", "supported")),
                           "total": len(_items)}
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check fulfillment 失败(fail-soft): %s", e)
        degraded = True
        degraded_stages.append("fulfillment")

    from scribe3.critique import _degen_visible_length
    _visible_chars = _degen_visible_length(req.prose or "")
    resp = {
        "quality": {**qc_breakdown, "total": qc_total},
        "leaks": leaks,
        "leaks_degraded": leaks_degraded,
        "fulfillment": fulfillment,
        "s1_circuit_open": _s1_circuit_open(work),   # 1-A 熔断状态对调用方可见
        "visible_chars": _visible_chars,   # 2-B:A5 口径可见字数,triage 短文本降档判据源
        "discipline": discipline,
        "degraded": degraded,
        "degraded_stages": degraded_stages,
        "inherited_open_promises": inherited_open_promises,
        "setting": setting,
        "issues": issues,
        "duplicate_lines": dup_lines,
        "emotion_telling": emotion_telling,
        "cross_consistency": cross_consistency,
        "tension_monotony": tension_monotony,
        "orphan_edges": orphan_edges,
        "parallelism": parallelism,
        "poetic_fragments": poetic_fragments,
        "unbalanced_quotes": unbalanced_quotes,
        "watch_regression": watch_regression,
        "punct_suggestions": punct_suggestions,
    }
    if ai_grade is not None:
        resp["ai_grade"] = ai_grade
    return resp

def checkpoint(req: CheckpointReq, seq: int, background: BackgroundTasks, work: str = "main"):
    st = _store_for(work)
    vid = st.add_chapter_version(seq, req.prose, label=req.label,
                                 kind=req.kind, qc=req.qc)
    # kind=final → 这是正式定稿,知识图谱应同步更新(非 final 的草稿快照不 ingest)。
    # P0-1:走去重排队——"存为正文"里 save-chapter 已排的同章 ingest 仍在途时,这里跳过,
    # 不重复排(checkpoint 的职责是落 final 版本;ingest 由 save-chapter 负责)。
    # checkpoint 单独触达(无前置 save-chapter)时仍会正常排入,不丢 ingest。
    if req.kind == "final":
        _enqueue_ingest(background, work, seq)
    return {"status": "saved", "id": vid, "seq": seq, "kind": req.kind}



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    # 重绑后函数 globals=core.__dict__，须把本模块依赖注入 core，否则 NameError
    # （2026-08-08 产品验收：POST /chat/write → sse_response is not defined）。
    from scribe3.api.sse import sse_response as _sse_response
    core.sse_response = _sse_response
    g = globals()
    _fn = g['chat_write']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_write', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_write', _re)
    g['chat_write'] = _re
    router.add_api_route('/chat/write', _re, methods=['GET'], name='chat_write')

    _fn = g['chat_write_post']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chat_write_post', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chat_write_post', _re)
    g['chat_write_post'] = _re
    router.add_api_route('/chat/write', _re, methods=['POST'], name='chat_write_post')

    _fn = g['qc']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'qc', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'qc', _re)
    g['qc'] = _re
    router.add_api_route('/qc', _re, methods=['GET'], name='qc')

    _fn = g['check_prose']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'check_prose', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'check_prose', _re)
    g['check_prose'] = _re
    router.add_api_route('/check', _re, methods=['POST'], name='check_prose')

    _fn = g['post_check']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'post_check', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'post_check', _re)
    g['post_check'] = _re
    router.add_api_route('/post-check', _re, methods=['POST'], name='post_check')

    _fn = g['checkpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'checkpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'checkpoint', _re)
    g['checkpoint'] = _re
    router.add_api_route('/checkpoint', _re, methods=['POST'], name='checkpoint')

_bind_and_register()
