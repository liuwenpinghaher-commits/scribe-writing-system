"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import logging

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

router = APIRouter(tags=['chapters'])


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


def chapter_pulse_ep(seq: int = Query(ge=1), work: str = "main"):
    """主编主动化 T1:六维脉搏(promise/arc/relation/tension/causal/quality)。
    只读聚合,零新检测器;decision 级=时机引擎开口依据(全部源自确定性信号);
    宪法:无总分,分维 severity。"""
    from scribe3.pulse import chapter_pulse
    return chapter_pulse(_store_for(work), seq)

def chapter_brief(seq: int = Query(ge=1), focalizer: str = "", work: str = "main"):
    """Task7 章前创作简报(只读):弧光指令 + 伏笔窗口分流 + 开环账本 + 待激活角色。
    与 _editor_write_system 的注入同源(assemble_chapter_brief 单源)。"""
    from scribe3.brief import assemble_chapter_brief
    return assemble_chapter_brief(_store_for(work), seq, focalizer=focalizer)

def loop_chapter(req: LoopChapterReq, work: str = "main"):
    """北极星任务4:修复环编排端点(蓝图 §3-①)。同步长请求(D-009:单用户本地工具
    形态;响应带 journal_path 留 202 演进位)。编排纯逻辑在 scribe3/loop.py(依赖注入),
    本端点只绑真实现:
    - generate 复用 chat_write 完整组装链(_assemble_write_instructions 同一函数,
      宪法:regenerate 绝不另起简化 prompt);负面约束段追加在 instructions 尾部;
    - post_check 直接调用 /post-check 端点函数(判据零漂移);
    - blocking→自动回炉≤2轮 / advisory→清单待批不重写 / pass→落库+final版+同步 ingest;
    - loop 自动轮不写 chat_message(D-010,journal 已留痕)。"""
    from scribe3.loop import run_chapter_loop
    from scribe3.pipeline_journal import PipelineJournal
    st = _store_for(work)
    # P0门审查 P1-3:同章 loop 互斥——在途拒 409,防双生成/双落库/双 ingest。
    _lkey = (work, req.chapter)
    with _loop_inflight_lock:
        if _lkey in _loop_inflight:
            raise HTTPException(status_code=409,
                                detail=f"chapter {req.chapter} 已有 loop 在途(同章互斥)")
        _loop_inflight.add(_lkey)
    # P2门审查 P2-1(loop 侧同修):journal 构造若抛异常须释放互斥,否则该章永久 409。
    try:
        jp = _loop_journal_path(work, req.chapter)
        journal = PipelineJournal(jp)
    except Exception:
        with _loop_inflight_lock:
            _loop_inflight.discard(_lkey)
        raise

    def _generate(attempt: int, constraints: str) -> str:
        with_tools = _work_has_tools(work) and _write_phase_allows_tools(req.phase)
        msg = req.msg or (f"按本章简报、大纲与全部纪律写第 {req.chapter} 章完整正文,"
                          f"用 ⟦PROPOSAL scope=chapter⟧ 围栏交稿。")
        outcome_binding = _WriteOutcomeBinding(st)
        instructions = _assemble_write_instructions(
            st, chapter=req.chapter, focalizer=req.focalizer, phase=req.phase,
            seed_words=[], short_mode=req.short_mode,
            with_tools=with_tools, work=work,
            envelope_trace=outcome_binding.manifest_trace,
            extra_instructions=constraints, request_text=msg)
        # 整章 loop/pilot 默认拉高生成上限：None 时常被网关截成 ~1.5k 字短稿，
        # 无法支撑连载验收「约 5k×10」真路径；8192 与 Hermes 长文档常见帽一致。
        text, proposals = _collect_write(
            msg, instructions, with_tools=with_tools,
            on_terminal=outcome_binding.persist,
            max_tokens=8192,
        )
        # P0门审查 P1-7:只认 scope=chapter 围栏(scene/selection 片段不能当整章);
        # 无合格围栏时兜底散文必须过长度门——否则一段短聊天语可能四判据全绿直通
        # pass,把既有整章正文静默覆盖掉。
        chapter_props = [p for p in proposals if p.get("scope") == "chapter"]
        if chapter_props:
            return chapter_props[-1]["prose"]
        body = _strip_preamble(text)
        if len(body.strip()) >= _FALLBACK_MIN_CHARS:
            return body
        raise HTTPException(status_code=422, detail=(
            f"第 {attempt} 轮未产出合格章稿(无 scope=chapter 围栏且散文不足 "
            f"{_FALLBACK_MIN_CHARS} 字)——请检查驱动语是否要求用围栏交稿"))

    _last_post: dict = {}   # 北极星任务6:finalize 结算要用最后一轮 fulfillment 结果

    def _post_check(prose: str) -> dict:
        resp = post_check(PostCheckReq(prose=prose, focalizer=req.focalizer,
                                       short_mode=req.short_mode),
                          seq=req.chapter, work=work)
        _last_post.clear()
        _last_post.update(resp)
        return resp

    def _persist_version(prose: str, attempt: int, verdict: str) -> str:
        return st.add_chapter_version(
            req.chapter, prose, label=f"loop第{attempt}稿·{verdict}",
            kind="checkpoint", stage="draft", stats=_prose_stats(prose))

    def _finalize(prose: str) -> dict:
        title = (st.get_chapter(req.chapter) or {}).get("title") or ""
        st.save_chapter(req.chapter, prose, title=title, focalizer=req.focalizer or None)
        try:
            st.add_chapter_version(req.chapter, prose, label="loop过审", kind="final",
                                   stage="final", stats=_prose_stats(prose))
        except Exception as e:
            logging.getLogger("scribe3").warning("loop final 留版失败(不阻断): %s", e)
        # 经 IngestPolicy + 共享 lease(与 /ingest、MCP 同 choke point)。
        # loop 仅在 pass finalize 时调用 → gate verdict=pass; distill 由单入口处理。
        try:
            from scribe3.llm import hermes_complete
            from scribe3.ingest_policy import GateSnapshot
            from scribe3.api.services.ingest_bg import schedule_ingest
            _dfn2 = _complete_fn if _complete_fn is not None else hermes_complete
            _ing = schedule_ingest(
                st, work, req.chapter,
                prose=prose,
                gate=GateSnapshot(path="loop", craft_allowed=True, finalize_verdict="pass"),
                source="loop", mode="sync", complete_fn=_dfn2, distill=True,
            )
            if _ing.get("held"):
                return {
                    "ok": False,
                    "error": f"ingest held: {_ing.get('hold_reason') or _ing.get('reason')}",
                    "held": True,
                    "confirm_token": _ing.get("confirm_token"),
                }
            if _ing.get("reason") == "lease_busy":
                return {
                    "ok": False,
                    "error": "同章 ingest 租约占用,正文已落库,稍后可手动 /ingest",
                    "lease_busy": True,
                }
            r = _ing.get("ingest") or {}
            if r.get("skipped") or _ing.get("reason") == "same_prose_fp_ingest":
                return {
                    "ok": True, "skipped": True,
                    "reason": r.get("reason") or _ing.get("reason"),
                    "parse_failed": False, "lesson_error": None,
                }
            # 北极星任务6:结算必须在 ingest **之后**
            try:
                from scribe3.purpose import (check_fulfillment_structural,
                                             parse_deltas, settle_purpose)
                _ds = parse_deltas((st.get_chapter(req.chapter) or {}).get("deltas"))
                if _ds:
                    _struct = check_fulfillment_structural(st, req.chapter, _ds)
                    _kn = {(i.get("kind"), i.get("predicate")): i
                           for i in ((_last_post.get("fulfillment") or {}).get("items") or [])
                           if i.get("kind") == "knowledge"}
                    _merged = []
                    for _it in _struct:
                        if _it["kind"] == "knowledge" and _it["verdict"] == "not_checkable":
                            _j = _kn.get((_it["kind"], _it["predicate"]))
                            if _j and _j.get("verdict"):
                                _it = {**_it, "verdict": _j["verdict"]}
                        _merged.append(_it)
                    settle_purpose(st, req.chapter, _merged)
            except Exception as se:
                logging.getLogger("scribe3").warning("loop 目的合同结算失败(忽略): %s", se)
            lesson_err = None
            if _ing.get("distilled") is False:
                lesson_err = "distill_failed"
            # ingest 后刷新 scorecard(P2-3 单源;在 settle 之后)
            _refresh_scorecard_after_ingest(st, req.chapter)
            return {
                "ok": True,
                "parse_failed": bool(r.get("parse_failed")),
                "lesson_error": lesson_err,
                "ingest_action": _ing.get("action"),
            }
        except Exception as e:
            logging.getLogger("scribe3").warning("loop ingest 失败(正文已落库,如实上报): %s", e)
            mark_chapter_ingest_status(st, req.chapter, "failed", str(e))
            return {"ok": False, "error": str(e)[:160]}

    try:
        result = run_chapter_loop(chapter=req.chapter, generate=_generate,
                                  post_check=_post_check, persist_version=_persist_version,
                                  finalize=_finalize, journal=journal)
    finally:
        with _loop_inflight_lock:
            _loop_inflight.discard(_lkey)
    # 遗留处置 1-A:熔断数据源。审查 P2-1:记"S1 是某轮唯一 blocking 来源"而非"S1 出现
    # 过"——与泄密/退化同场时章确有硬伤,S1 非决定性,计入会污染误杀率分子、熔断偏易开。
    def _s1_sole_blocking(rounds):
        for r0 in rounds:
            bl = r0.get("blocking") or []
            if bl and all(b.get("detector") == "findings_schema" for b in bl):
                return True
        return False
    _s1_record(work, _s1_sole_blocking(result.get("rounds", [])))
    # 遗留处置 1-C(#2):rounds 明细(含 blocking 原因)落 journal 旁,复用选择环
    # .result.json 模式——审计与盲评池的"为什么"单文件可查,不再只活在 HTTP 响应里。
    try:
        with open(str(jp) + ".result.json", "w", encoding="utf-8") as _f:
            json.dump(result, _f, ensure_ascii=False, indent=1)
    except Exception as e:
        logging.getLogger("scribe3").warning("loop 结果落盘失败(忽略): %s", e)
    result["journal_path"] = str(jp)
    return result

def chapters(work: str = "main"):
    return _store_for(work).list_chapters()

def archived_chapters(work: str = "main"):
    """归档箱:列出已归档但尚未永久删除的章节。"""
    return _store_for(work).archived_chapters()

def create_chapter(req: ChapterCreateReq, work: str = "main"):
    """新建空章:seq 使用历史最大章号+1,不复用归档章。"""
    try:
        ch = _store_for(work).create_chapter(req.title or "", req.volume)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"status": "created", **ch}

def archive_chapter(seq: int, req: ChapterArchiveReq | None = None, work: str = "main"):
    """归档章节:默认删除动作,隐藏但保留正文、版本和关联。"""
    ok = _store_for(work).archive_chapter(seq, (req.reason if req else "") or "")
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "archived", "seq": seq}

def restore_chapter(seq: int, work: str = "main"):
    ok = _store_for(work).restore_chapter(seq)
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "restored", "seq": seq}

def restore_chapter_version(
    seq: int,
    req: RestoreVersionReq,
    background: BackgroundTasks,
    work: str = "main",
):
    """版本存档恢复专用通道(与普通 save-chapter 分离)。

    - **跳过工艺门闩**:恢复是作者明确意图,不得因 GATE-B 半成品态 409 卡死
    - **留审计 checkpoint**:版本史可看到「从存档恢复」
    - **默认 reingest**:知识账本与恢复后正文对齐(可显式 reingest=false)
    - 闸:与 /save-chapter 同级(不在世界写前缀清单)
    """
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    prose = (req.prose or "").strip()
    if req.version_id:
        ver = st.get_chapter_version(req.version_id)
        if not ver:
            raise HTTPException(status_code=404, detail=f"version '{req.version_id}' not found")
        if int(ver.get("seq") or 0) != int(seq):
            raise HTTPException(status_code=422, detail="version 不属于本章")
        prose = ver.get("prose") or ""
    if not prose.strip():
        raise HTTPException(status_code=422, detail="恢复正文为空")
    # 在途生成护栏与 save-chapter 对称
    with _loop_inflight_lock:
        if (work, seq) in _loop_inflight:
            raise HTTPException(status_code=409, detail=(
                f"第 {seq} 章生成在途,完成后再恢复存档"))
    _guard_pilot_busy(work, seq)
    title = ch.get("title") or ""
    focalizer = ch.get("focalizer") or None
    st.save_chapter(seq, prose, title=title, focalizer=focalizer)
    vid = ""
    try:
        vid = st.add_chapter_version(
            seq, prose, label=(req.label or "从存档恢复").strip() or "从存档恢复",
            kind="checkpoint", stage="final", stats=_prose_stats(prose))
    except Exception as e:
        logging.getLogger("scribe3").warning(
            "restore-version 留 checkpoint 失败 work=%s seq=%s: %s", work, seq, e)
    ingested = False
    ingest_meta = None
    if req.reingest:
        from scribe3.ingest_policy import GateSnapshot
        from scribe3.api.services.ingest_bg import schedule_ingest
        _ing = schedule_ingest(
            st, work, seq, background=background, prose=prose,
            gate=GateSnapshot(path="restore", finalize_verdict=None),
            source="restore", mode="bg",
        )
        ingested = bool(_ing.get("enqueued"))
        ingest_meta = {
            "action": _ing.get("action"), "held": bool(_ing.get("held")),
            "reason": _ing.get("reason"),
            "confirm_token": _ing.get("confirm_token"),
        }
    out_restore = {
        "status": "restored",
        "seq": seq,
        "version_id": vid or None,
        "reingest_enqueued": bool(ingested),
        "chars": len("".join(prose.split())),
    }
    if ingest_meta is not None:
        out_restore["ingest"] = ingest_meta
    return out_restore

def chapter_impact(seq: int, work: str = "main"):
    impact = _store_for(work).chapter_lifecycle_impact(seq)
    if impact is None:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return impact

def delete_chapter(seq: int, confirm_impact_token: str | None = None, work: str = "main"):
    """永久删除章节。必须先读取 impact 并带回 confirm_impact_token。"""
    st = _store_for(work)
    impact = st.chapter_lifecycle_impact(seq)
    if impact is None:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    if confirm_impact_token != impact["confirm_impact_token"]:
        return JSONResponse(status_code=409, content=impact)
    ok = st.delete_chapter_permanent(seq)
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "deleted", "seq": seq, "impact": impact}

def get_outline(work: str = "main"):
    """聚合大纲:卷 + 章(梗概/字数/QC/视角/sort_order/label + 场景数)。
    章按 sort_order 升序;sort_order=NONE 时回退 seq。不回正文全文。"""
    return _store_for(work).outline()

def reorder_chapters(req: ReorderReq, work: str = "main"):
    """拖拽重排:改 sort_order(及 volume),绝不动 seq(故事时间轴主键)。
    R2.5: 目标 volume 不存在→422。
    """
    try:
        count = _store_for(work).reorder_chapters(req.volume, req.order)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"status": "reordered", "volume": req.volume, "count": count}

def grounded_deduction_fallback(seq: int, character_id: str, work: str = "main"):
    """返回可逐字追溯的角色投影兜底稿；只读，不写章节。"""
    ch = _store_for(work).get_chapter(seq)
    if not ch:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    truth = (ch.get("scene_truth") or "").strip()
    if not truth:
        raise HTTPException(status_code=422, detail="请先填写场景真相，才能生成可追溯投影")
    candidate = _verbatim_deduction_fallback(truth, character_id)
    if not candidate:
        raise HTTPException(status_code=422, detail="场景真相未包含该角色可安全摘录的事实，不能伪造投影")
    return {"seq": seq, "character_id": character_id, "candidate": candidate,
            "mode": "verbatim_fallback"}

def review_deduction_grounding(seq: int, req: DeductionGroundingReq, work: str = "main"):
    """审查角色投影；证据始终从服务端本章场景真相读取，客户端不能替换来源。"""
    from scribe3.deduce_helpers import has_five_layer_headings, missing_layer_headings

    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    truth = (ch.get("scene_truth") or "").strip()
    if not truth:
        raise HTTPException(status_code=422, detail="请先填写场景真相，角色投影才能进行事实对齐")
    result = _grounding_review(
        truth, req.candidate, mode="deduction", st=st, work=work, chapter=seq,
    )
    structure_ok = has_five_layer_headings(req.candidate)
    missing_h = missing_layer_headings(req.candidate)
    # 五层可检测：结构缺失不单独 fail-closed（兼容旧散文），但机读字段必出
    return {
        "seq": seq,
        "character_id": req.character_id,
        **result,
        "structure": {
            "ok": structure_ok,
            "missing_headings": missing_h,
            "five_layers": structure_ok,
        },
        "scene_truth_revision": int(ch.get("scene_truth_revision") or 0),
    }

def patch_chapter(seq: int, req: ChapterMetaReq, work: str = "main"):
    """改章梗概/卷归属/标签/标题,不碰正文/embedding/qc。
    R2.3: 用 exclude_unset=True(区分"没传"与"传了 null"),让 volume=None 能清空卷归属。
    R2.5: 目标 volume 不存在→422。
    """
    fields = req.model_dump(exclude_unset=True)
    # 北极星任务6:目的合同登记校验——strict 解析(P1-5:非法条目 422 指明第几条,
    # 绝不静默丢弃后整体覆盖=静默数据销毁)+ 条数量控 + 认知类写前预演
    # (不可实现 → 422 带原因;预演降级放行时响应带旗,P2-2)。
    _rehearse_degraded = False
    if "purpose_text" in fields and fields["purpose_text"]:
        fields["purpose_text"] = str(fields["purpose_text"])[:200]
    if "deltas" in fields and fields["deltas"] is not None:
        from scribe3.purpose import (parse_deltas_strict, rehearse_delta_ex,
                                     validate_deltas)
        _ds, _errs = parse_deltas_strict(fields["deltas"])
        if _errs:
            raise HTTPException(status_code=422,
                                detail="deltas 有非法条目,未写入:" + ";".join(_errs))
        _err = validate_deltas(_ds)
        if _err:
            raise HTTPException(status_code=422, detail=_err)
        _foc = (_store_for(work).get_chapter(seq) or {}).get("focalizer")
        for _d in _ds:
            _rerr, _rdeg = rehearse_delta_ex(_store_for(work), seq, _d, _foc)
            _rehearse_degraded = _rehearse_degraded or _rdeg
            if _rerr:
                raise HTTPException(status_code=422, detail=_rerr)
        fields["deltas"] = _ds   # 存规范化后的清单
    try:
        ok = _store_for(work).update_chapter_meta(seq, fields)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    _resp = {"status": "updated", "seq": seq}
    if _rehearse_degraded:
        _resp["rehearse_degraded"] = True   # P2-2:预演故障放行须对调用方可见
    return _resp


class GcdFieldsReq(BaseModel):
    """GCD 字段微调：仅 beats，拍数守恒（emergency REST 闸外）。"""
    beats: list = Field(default_factory=list)


def patch_chapter_gcd_fields(seq: int, req: GcdFieldsReq, work: str = "main"):
    """novel-first：作者微调节拍 GCD/text，不开放 synopsis/volume 等 meta。

    路径 ``PATCH /chapters/{seq}/gcd-fields`` 不在 emergency 世界写闸内。
    """
    from scribe3.chapter_gcd_rest import (
        normalize_beats_for_store,
        validate_gcd_beats_patch,
    )
    st = _store_for(work)
    ch = st.get_chapter(seq) or {}
    if not ch and not st.get_chapter(seq):
        # get may return {} for missing
        pass
    old_beats = ch.get("beats") if ch else None
    if not ch:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    ok, reason = validate_gcd_beats_patch(old_beats, req.beats)
    if not ok:
        raise HTTPException(
            status_code=422,
            detail=f"GCD field patch rejected: {reason}",
        )
    try:
        written = st.update_chapter_meta(
            seq, {"beats": normalize_beats_for_store(req.beats)},
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not written:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "updated", "seq": seq, "gcd_fields": True}


def list_volumes(work: str = "main"):
    return _store_for(work).list_volumes()

def add_volume(req: VolumeReq, work: str = "main"):
    vid = _store_for(work).add_volume(
        title=req.title, sort_order=req.sort_order,
        intro=req.intro, color=req.color)
    return {"status": "created", "id": vid}

def update_volume(vid: str, req: VolumePatchReq, work: str = "main"):
    fields = req.model_dump(exclude_none=True)
    found = _store_for(work).update_volume(vid, fields)
    if not found:
        raise HTTPException(status_code=404, detail=f"volume '{vid}' 不存在")
    return {"status": "updated", "id": vid}

def delete_volume(vid: str, work: str = "main"):
    """删卷:该卷下的章 volume 置 NONE(章不删),再删卷记录。卷不存在→404。"""
    found = _store_for(work).delete_volume(vid)
    if not found:
        raise HTTPException(status_code=404, detail=f"volume '{vid}' 不存在")
    return {"status": "deleted", "id": vid}

def get_chapter(seq: int, work: str = "main"):
    return _store_for(work).get_chapter(seq) or {}


def get_chapter_execution_soft_status(seq: int = Query(ge=1), work: str = "main"):
    """章执行软状态（只读 · advisory only）。

    聚合 narrative_drive 三行摘要、大纲 stakes 探测、soft_fulfill 与 drive/prose drift。
    与 full_check 同源 ``soft_fulfill_drive``；永不 blocking、不触发 park/清稿。
    """
    from scribe3.execution_contract import chapter_execution_soft_status

    ch = _store_for(work).get_chapter(seq) or {}
    return chapter_execution_soft_status(
        seq=seq,
        prose=ch.get("prose") or "",
        drive=ch.get("narrative_drive") if isinstance(ch.get("narrative_drive"), dict) else {},
        synopsis=ch.get("synopsis") or "",
    )


def chapter_versions(seq: int, work: str = "main"):
    return _store_for(work).list_chapter_versions(seq)

def chapter_version(vid: str, work: str = "main"):
    v = _store_for(work).get_chapter_version(vid)
    if not v:
        raise HTTPException(status_code=404, detail="version not found")
    return v

def select_chapter(req: SelectChapterReq, work: str = "main"):
    """选择环(北极星任务11,蓝图 §4-①):关键章同一合同出 3 个策略多样候选 →
    确定性过滤(triage blocking 杀)→ rubric 全循环赛只排序(无共识则不排)→
    候选留版本,响应供对比页,终选走 /select/finalize(人)。
    关键章判定:chapter_role∈{高压,关系回收} 或含 reversal_type(节拍标注,
    parse_chapter_meta);非关键章 422(force=true 可越过)。同章互斥 409。"""
    from scribe3.brief import chapter_draft_text, parse_chapter_meta
    from scribe3.pipeline_journal import PipelineJournal
    from scribe3.qd import chapter_style_profile
    from scribe3.selection import STRATEGIES, is_key_chapter, run_selection
    st = _store_for(work)
    ch = st.get_chapter(req.chapter)
    if not ch:
        raise HTTPException(status_code=404, detail=f"chapter {req.chapter} 不存在")
    _draft_txt = chapter_draft_text(ch)
    meta = parse_chapter_meta(_draft_txt) or {}
    # reversal_type 不在 parse_chapter_meta 输出里(它只抓压力级/role)——
    # 关键章判定的反转分支从草料文本直接正则(方案B任务13b 的标注规范同源)。
    import re as _re
    _rev = _re.search(r"reversal_type\s*[::]\s*(\S+)", _draft_txt)
    if _rev:
        meta["reversal_type"] = _rev.group(1)
    if not is_key_chapter(meta) and not req.force:
        raise HTTPException(status_code=422, detail=(
            "非关键章不触发选择环(N 倍成本只花刀刃):节拍标注 chapter_role 为 高压/关系回收 "
            "或标注 reversal_type 后再试;确要出候选传 force=true"))
    _guard_pilot_busy(work, req.chapter)   # D1:pilot 非 loop 步在途/连写中不出候选(防互踩,同终选 R2-3)
    # B4:选择环单次 ~10 发 LLM,启动前预检剩余日帽——撞帽半途炸不如提前如实拦
    from scribe3.llm import daily_remaining
    _sel_est = 10
    _remaining = daily_remaining()
    if _remaining is not None and _remaining < _sel_est:
        raise HTTPException(status_code=429, detail=(
            f"LLM 日帽剩余不足:选择环约需 {_sel_est} 发,当前剩 {_remaining} 发。"
            f"次日 0 点重置,或调大 SCRIBE3_DAILY_CALL_CAP"))
    _skey = (work, req.chapter)
    with _loop_inflight_lock:   # 与修复环共用同章互斥(同章不得同时 loop 与选择)
        if _skey in _loop_inflight:
            raise HTTPException(status_code=409, detail=f"chapter {req.chapter} 已有生成在途")
        _loop_inflight.add(_skey)
    # P2门审查 P2-1:journal 构造放锁后 try 内(构造抛异常曾致锁永不释放、该章全 409);
    # 且只替换**文件名**(str.replace 全路径会把含 loop_ch 的目录段也改写)。
    try:
        jp = _loop_journal_path(work, req.chapter)
        jp = jp.with_name(jp.name.replace("loop_ch", "select_ch", 1))
        journal = PipelineJournal(jp)
    except Exception:
        with _loop_inflight_lock:
            _loop_inflight.discard(_skey)
        raise

    def _generate(strategy: dict) -> str:
        outcome_binding = _WriteOutcomeBinding(st)
        strategy_instructions = (
            "【选择环候选策略(本候选必须执行)】" + strategy["directive"]
        )
        msg = ((req.msg + "\n") if req.msg else "") + (
            f"写第 {req.chapter} 章完整正文,严格执行上面的候选策略,"
            f"用 ⟦PROPOSAL scope=chapter⟧ 围栏交稿。")
        instructions = _assemble_write_instructions(
            st, chapter=req.chapter, focalizer=ch.get("focalizer") or "", phase="final",
            seed_words=[], short_mode=False, with_tools=False, work=work,
            envelope_trace=outcome_binding.manifest_trace,
            extra_instructions=strategy_instructions,
            request_text=msg)   # 候选生成不挂工具(纯写作)
        text, proposals = _collect_write(
            msg, instructions, with_tools=False,
            on_terminal=outcome_binding.persist,
        )
        chapter_props = [p for p in proposals if p.get("scope") == "chapter"]
        if chapter_props:
            return chapter_props[-1]["prose"]
        body = _strip_preamble(text)
        if len(body.strip()) >= _FALLBACK_MIN_CHARS:
            return body
        # B2:业务层不抛 HTTPException(HTTP 语义应留给端点层)——抛普通异常,由 run_selection
        # 的 B1 容错捕获成"该候选生成失败"跳过,不污染 HTTP 语义、不拖垮其余候选。
        raise RuntimeError(f"策略 {strategy['key']} 未产出合格章稿(无围栏且散文不足)")

    def _post_check(prose: str) -> dict:
        return post_check(PostCheckReq(prose=prose, focalizer=ch.get("focalizer") or ""),
                          seq=req.chapter, work=work)

    def _persist(prose: str, strategy_key: str) -> str:
        # kind 枚举 DB 级 ASSERT 仅 checkpoint/final(migration 先例)——候选语义由
        # label 前缀「选择环候选·」承载,免改已有表 schema(免影子库演练,D-019 附注)。
        # C1(彻查 D-10):候选用独立 stage="candidate",不用 "draft"——否则
        # latest_draft_version(按 stage='draft' 取最新)会把选择环候选当"最新草稿",
        # 污染作者草稿 tab 的「刷新恢复」。version_id 不变,CandidateCard 展开全文不受影响。
        return st.add_chapter_version(req.chapter, prose, kind="checkpoint", stage="candidate",
                                      label=f"选择环候选·{strategy_key}",
                                      stats=_prose_stats(prose))

    def _judge(a: str, b: str) -> str:
        """成对比较(rubric 初筛员,只排序)。LLM 失败 → **恒返回 "A"(先手)**:
        位置对换下同对两方向都判先手 = w1≠w2 矛盾 → round_robin 判 inconsistent →
        consensus=False 交人。P2门审查 P1-1:此前的"交替返回"推理是反的——交替
        ("A","B") 在位置对换下恰好等于两方向一致判先手胜,产出零矛盾的确定性
        **假共识**(已复现);恒定先手才是被双向对换必然识破的降级形态。"""
        prompt = ("两份同一章级合同下的候选章稿,只判哪份更好(贴合同/张力/文风三维综合),"
                  '只输出一个字母 A 或 B。\n'
                  f"【A】\n{a[:2800]}\n【B】\n{b[:2800]}")
        try:
            fn = _complete_fn
            if fn is None:
                from scribe3.llm import hermes_complete as fn
            raw = str(fn(prompt)).strip().upper()
            # P2门审查 P3:取独立的 A/B token(防 "ANSWER" 里的 A 误判)
            import re as _re2
            m = _re2.search(r"(?<![A-Z0-9])([AB])(?![A-Z0-9])", raw)
            if m:
                return m.group(1)
        except Exception as e:
            logging.getLogger("scribe3").warning("selection judge 失败(降级为无共识): %s", e)
        return "A"

    def _save_result(res: dict) -> None:
        """P2门审查 P2-3:结果元数据落 journal 旁文件——同步长请求断连/切章后,
        候选的 filtered/rank/profile 不再只活在一次 HTTP 响应里(prose 本就在版本库)。"""
        import json as _j2
        try:
            with open(str(jp) + ".result.json", "w", encoding="utf-8") as f:
                _j2.dump(res, f, ensure_ascii=False)
        except Exception as e:
            logging.getLogger("scribe3").warning("selection 结果落盘失败(忽略): %s", e)

    try:
        result = run_selection(chapter=req.chapter, generate=_generate,
                               post_check=_post_check, persist_candidate=_persist,
                               profile_fn=chapter_style_profile, judge_fn=_judge,
                               journal=journal, save_result=_save_result)
    finally:
        with _loop_inflight_lock:
            _loop_inflight.discard(_skey)
    result["journal_path"] = str(jp)
    result["key_chapter"] = is_key_chapter(meta)
    return result

def select_finalize(req: SelectFinalizeReq, background: BackgroundTasks, work: str = "main"):
    """选择环终选(人):选中候选落正文 + 留 final 版 + **终选理由入 lesson 流**
    (蓝图:理由是沉淀环最贵的输入;强制一句,轴+自由文本双格式)。"""
    if not (req.reason_text or "").strip():
        raise HTTPException(status_code=422, detail="终选必须留一句理由(入 lesson 流)")
    # P2门审查 P1-3:同章 loop/选择在途时禁止终选——否则 loop pass 的 save+ingest
    # 与终选落库互踩(正文与知识表错位)。检查即可,不持锁。
    with _loop_inflight_lock:
        if (work, req.chapter) in _loop_inflight:
            raise HTTPException(status_code=409,
                                detail=f"chapter {req.chapter} 有生成在途,完成后再终选")
    _guard_pilot_busy(work, req.chapter)   # R2-3:pilot 非 loop 步在途/连写中也拦
    st = _store_for(work)
    ver = st.get_chapter_version(req.version_id)
    if not ver or ver.get("seq") != req.chapter:
        raise HTTPException(status_code=404, detail="候选版本不存在或不属于该章")
    if not _is_selection_candidate_version(ver):
        raise HTTPException(
            status_code=422,
            detail="只能终选选择环候选版本(stage=candidate 且非过滤击杀稿);"
                   "不可把普通存档/击杀稿定稿",
        )
    prose = ver.get("prose") or ""
    title = (st.get_chapter(req.chapter) or {}).get("title") or ""
    foc = (st.get_chapter(req.chapter) or {}).get("focalizer")
    # 门A:终选共用 check_finalize_for_save 单源(危险旁路不提供——终选即人审)
    try:
        from scribe3.finalize_gate import check_finalize_for_save
        _fg = check_finalize_for_save(
            st, req.chapter, prose, focalizer=foc or None, danger_draft=False)
        if not _fg.get("allowed"):
            raise HTTPException(status_code=409, detail={
                "code": _fg.get("code") or "finalize_gate",
                "message": _fg.get("detail") or "终选定稿被定稿门闩拦截",
                "blocking": _fg.get("blocking") or [],
            })
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger("scribe3").error(
            "select_finalize 定稿门闩失败(阻断) ch=%s: %s", req.chapter, e, exc_info=True)
        raise HTTPException(status_code=503, detail={
            "code": "finalize_gate_error",
            "message": f"定稿门闩评估失败: {e}",
        }) from e
    st.save_chapter(req.chapter, prose, title=title, focalizer=foc)
    # C3(D-13):终选定稿 → 单入口策略(finalize 已通过 → pass 快照)
    from scribe3.ingest_policy import GateSnapshot
    from scribe3.api.services.ingest_bg import schedule_ingest
    _fin_verdict = str((_fg or {}).get("verdict") or "pass").lower()
    if (_fg or {}).get("advisory_items") and _fin_verdict in ("", "pass", "ok"):
        _fin_verdict = "advisory"
    schedule_ingest(
        st, work, req.chapter, background=background, prose=prose,
        gate=GateSnapshot(
            path="select_finalize", craft_allowed=True,
            finalize_verdict=_fin_verdict,
        ),
        source="select_finalize", mode="bg",
    )
    try:
        st.add_chapter_version(req.chapter, prose, label=f"终选定稿·{ver.get('label') or ''}",
                               kind="final", stage="final", stats=_prose_stats(prose))
    except Exception as e:
        logging.getLogger("scribe3").warning("终选留 final 版失败(正文已落库): %s", e)
    lesson_saved, lesson_error = True, None
    try:
        st.add_lesson(req.chapter, "decision",
                      f"第{req.chapter}章关键章终选胜在{(req.reason_axis or '其他')[:12]}:"
                      f"{req.reason_text.strip()[:160]}",
                      condition="关键章多候选终选")
    except Exception as e:
        # U-011:终选理由是"沉淀环最贵的输入"(docstring 原话)——失败此前只 warning,作者
        # 以为理由存了。不 raise(定稿已落库),但响应带 lesson_saved=false 让前端可提示重试。
        logging.getLogger("scribe3").error("终选理由入 lesson 失败(定稿不受影响)", exc_info=True)
        lesson_saved, lesson_error = False, str(e)[:120]
    return {"status": "finalized", "chapter": req.chapter, "version_id": req.version_id,
            "lesson_saved": lesson_saved, "lesson_error": lesson_error,
            "note": "正文已落库;已排后台反哺(ingest)更新知识账本"}

def select_latest(chapter: int, work: str = "main"):
    """读本章最近一次选择环备料结果(.result.json),刷新页面后可恢复对比态。
    无结果 → 404。不含 prose 全文(仍走 version_id 拉)。"""
    import json as _j
    jp = _loop_journal_path(work, chapter)
    rp = jp.with_name(jp.name.replace("loop_ch", "select_ch", 1))
    path = str(rp) + ".result.json"
    try:
        with open(path, encoding="utf-8") as f:
            body = _j.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="本章尚无选择环备料结果")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取选择环结果失败:{e}")
    if not isinstance(body, dict):
        raise HTTPException(status_code=500, detail="选择环结果文件损坏")
    body.setdefault("chapter", chapter)
    body["result_path"] = path
    return body

def select_light(req: SelectLightReq, work: str = "main"):
    """L1 轻选择:同一合同出 2 条策略短变体(开场/切入包,约 ≤800 字)。
    成本约 2 发 LLM,非 L2 三整章。点选走 /select/light/pick 写入草稿种子。"""
    from scribe3.selection import L1_MAX_CHARS, L1_STRATEGIES, run_light_selection
    from scribe3.pipeline_journal import PipelineJournal
    st = _store_for(work)
    ch = st.get_chapter(req.chapter)
    if not ch:
        raise HTTPException(status_code=404, detail=f"chapter {req.chapter} 不存在")
    _guard_pilot_busy(work, req.chapter)
    from scribe3.llm import daily_remaining
    _l1_est = 2
    _remaining = daily_remaining()
    if _remaining is not None and _remaining < _l1_est:
        raise HTTPException(status_code=429, detail=(
            f"LLM 日帽剩余不足:L1 轻选择约需 {_l1_est} 发,当前剩 {_remaining} 发"))
    _skey = (work, req.chapter)
    with _loop_inflight_lock:
        if _skey in _loop_inflight:
            raise HTTPException(status_code=409, detail=f"chapter {req.chapter} 已有生成在途")
        _loop_inflight.add(_skey)
    try:
        jp = _select_l1_result_path(work, req.chapter)
        journal = PipelineJournal(jp)
    except Exception:
        with _loop_inflight_lock:
            _loop_inflight.discard(_skey)
        raise

    def _generate(strategy: dict) -> str:
        outcome_binding = _WriteOutcomeBinding(st)
        strategy_instructions = (
            "【L1 轻选择·策略短包(非整章)】" + strategy["directive"] +
            f"\n只写开场/切入片段,控制在 {L1_MAX_CHARS} 字以内;"
            "不要写完整章,不要收尾总结。用 ⟦PROPOSAL scope=chapter⟧ 围栏交稿。"
        )
        msg = ((req.msg + "\n") if req.msg else "") + (
            f"为第 {req.chapter} 章写一则策略短开场(≤{L1_MAX_CHARS}字),严格执行上面策略,"
            f"用 ⟦PROPOSAL scope=chapter⟧ 围栏。")
        instructions = _assemble_write_instructions(
            st, chapter=req.chapter, focalizer=ch.get("focalizer") or "", phase="final",
            seed_words=[], short_mode=True, with_tools=False, work=work,
            envelope_trace=outcome_binding.manifest_trace,
            extra_instructions=strategy_instructions, request_text=msg)
        text, proposals = _collect_write(
            msg, instructions, with_tools=False,
            on_terminal=outcome_binding.persist,
        )
        chapter_props = [p for p in proposals if p.get("scope") == "chapter"]
        if chapter_props:
            return chapter_props[-1]["prose"]
        body = _strip_preamble(text)
        if len(body.strip()) >= 40:
            return body
        raise RuntimeError(f"L1 策略 {strategy['key']} 未产出合格短包")

    def _persist(text: str, strategy_key: str) -> str:
        return st.add_chapter_version(
            req.chapter, text, kind="checkpoint", stage="light_variant",
            label=f"选择环L1·{strategy_key}",
            stats=_prose_stats(text))

    def _save_result(res: dict) -> None:
        import json as _j2
        try:
            with open(str(jp) + ".result.json", "w", encoding="utf-8") as f:
                _j2.dump(res, f, ensure_ascii=False)
        except Exception as e:
            logging.getLogger("scribe3").warning("L1 结果落盘失败(忽略): %s", e)

    try:
        result = run_light_selection(
            chapter=req.chapter, generate=_generate, persist_variant=_persist,
            journal=journal, save_result=_save_result, max_chars=L1_MAX_CHARS)
    finally:
        with _loop_inflight_lock:
            _loop_inflight.discard(_skey)
    result["journal_path"] = str(jp)
    result["strategies"] = [s["key"] for s in L1_STRATEGIES]
    result["tier_note"] = (
        "L1 轻选择(2 短包·约 2 发 LLM)。日常多路径请用此入口;"
        "关键章整章 3 候选请用「出 3 候选」L2(约 10 发·数分钟)。"
    )
    return result

def select_light_pick(req: SelectLightPickReq, work: str = "main"):
    """L1 点选:将选中短变体写入写作种子——与 /save-draft 同路径:
    chapter.draft + chapter_version(stage='draft'),供 GET /latest-draft 恢复。
    另记一条 lesson。不替代 L2 finalize(不直接覆盖定稿 prose)。"""
    import json as _j
    from scribe3.selection import apply_light_pick
    if not req.version_id and not req.strategy:
        raise HTTPException(status_code=422, detail="须提供 version_id 或 strategy")
    st = _store_for(work)
    if not st.get_chapter(req.chapter):
        raise HTTPException(status_code=404, detail=f"chapter {req.chapter} 不存在")
    # 优先从落盘 L1 结果取 variants(含 text);回退从 version 全文
    variants = []
    rp = _select_l1_result_path(work, req.chapter)
    path = str(rp) + ".result.json"
    try:
        with open(path, encoding="utf-8") as f:
            body = _j.load(f)
        variants = list(body.get("variants") or [])
    except Exception:
        variants = []
    if not variants and req.version_id:
        ver = st.get_chapter_version(req.version_id)
        if not ver or ver.get("seq") != req.chapter:
            raise HTTPException(status_code=404, detail="L1 变体版本不存在")
        label = str(ver.get("label") or "")
        if not label.startswith("选择环L1·"):
            raise HTTPException(status_code=422, detail="非 L1 轻变体版本,不可经 light/pick")
        sk = label.split("·", 1)[-1] if "·" in label else (req.strategy or "unknown")
        variants = [{
            "strategy": sk,
            "version_id": req.version_id,
            "text": ver.get("prose") or "",
            "directive": "",
        }]
    try:
        picked = apply_light_pick(
            variants=variants, version_id=req.version_id, strategy=req.strategy)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # 与 /save-draft 对齐——产品 DraftTab 读 GET /latest-draft(stage='draft')
    prose = picked["text"]
    st.save_chapter_draft(req.chapter, prose)
    stats = _prose_stats(prose)
    draft_vid = st.add_chapter_version(
        req.chapter, prose,
        label=f"L1轻选·{picked['strategy']}",
        kind="checkpoint",
        stage="draft",
        summary=f"L1 采纳策略 {picked['strategy']}",
        stats=stats,
    )
    try:
        st.add_lesson(
            req.chapter, "decision",
            f"第{req.chapter}章 L1 轻选择采纳策略 {picked['strategy']}:"
            f"{(prose or '')[:120]}",
            condition="L1轻选择短变体",
        )
    except Exception as e:
        logging.getLogger("scribe3").warning("L1 pick lesson 失败(草稿已落): %s", e)
    try:
        with open(path, encoding="utf-8") as f:
            body = _j.load(f)
        if isinstance(body, dict):
            body["picked"] = picked
            body["verdict"] = "picked"
            body["draft_version_id"] = draft_vid
            with open(path, "w", encoding="utf-8") as f:
                _j.dump(body, f, ensure_ascii=False)
    except Exception:
        pass
    return {
        "status": "picked",
        "tier": "L1",
        "chapter": req.chapter,
        "picked": picked,
        "draft_seeded": True,
        "id": draft_vid,
        "stage": "draft",
        "stats": stats,
        "note": "已写入草稿种子(stage=draft);请在正文/主编槽基于此策略扩写。关键章整章 3 候选仍用 L2。",
    }

def select_light_latest(chapter: int, work: str = "main"):
    """读本章最近一次 L1 轻选择结果。"""
    import json as _j
    path = str(_select_l1_result_path(work, chapter)) + ".result.json"
    try:
        with open(path, encoding="utf-8") as f:
            body = _j.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="本章尚无 L1 轻选择结果")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取 L1 结果失败:{e}")
    if not isinstance(body, dict):
        raise HTTPException(status_code=500, detail="L1 结果文件损坏")
    body.setdefault("chapter", chapter)
    body.setdefault("tier", "L1")
    body["result_path"] = path
    return body



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['chapter_pulse_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chapter_pulse_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chapter_pulse_ep', _re)
    g['chapter_pulse_ep'] = _re
    router.add_api_route('/chapter-pulse', _re, methods=['GET'], name='chapter_pulse_ep')

    _fn = g['chapter_brief']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chapter_brief', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chapter_brief', _re)
    g['chapter_brief'] = _re
    router.add_api_route('/chapter-brief', _re, methods=['GET'], name='chapter_brief')

    _fn = g['loop_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'loop_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'loop_chapter', _re)
    g['loop_chapter'] = _re
    router.add_api_route('/loop/chapter', _re, methods=['POST'], name='loop_chapter')

    _fn = g['chapters']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chapters', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chapters', _re)
    g['chapters'] = _re
    router.add_api_route('/chapters', _re, methods=['GET'], name='chapters')

    _fn = g['archived_chapters']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'archived_chapters', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'archived_chapters', _re)
    g['archived_chapters'] = _re
    router.add_api_route('/chapters/archived', _re, methods=['GET'], name='archived_chapters')

    _fn = g['create_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'create_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'create_chapter', _re)
    g['create_chapter'] = _re
    router.add_api_route('/chapters', _re, methods=['POST'], name='create_chapter')

    _fn = g['archive_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'archive_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'archive_chapter', _re)
    g['archive_chapter'] = _re
    router.add_api_route('/chapters/{seq}/archive', _re, methods=['POST'], name='archive_chapter')

    _fn = g['restore_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'restore_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'restore_chapter', _re)
    g['restore_chapter'] = _re
    router.add_api_route('/chapters/{seq}/restore', _re, methods=['POST'], name='restore_chapter')

    _fn = g['restore_chapter_version']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'restore_chapter_version', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'restore_chapter_version', _re)
    g['restore_chapter_version'] = _re
    router.add_api_route('/chapters/{seq}/restore-version', _re, methods=['POST'], name='restore_chapter_version')

    _fn = g['chapter_impact']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chapter_impact', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chapter_impact', _re)
    g['chapter_impact'] = _re
    router.add_api_route('/chapters/{seq}/impact', _re, methods=['GET'], name='chapter_impact')

    _fn = g['delete_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'delete_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'delete_chapter', _re)
    g['delete_chapter'] = _re
    router.add_api_route('/chapters/{seq}', _re, methods=['DELETE'], name='delete_chapter')

    _fn = g['get_outline']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_outline', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_outline', _re)
    g['get_outline'] = _re
    router.add_api_route('/outline', _re, methods=['GET'], name='get_outline')

    _fn = g['reorder_chapters']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'reorder_chapters', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'reorder_chapters', _re)
    g['reorder_chapters'] = _re
    router.add_api_route('/chapters/reorder', _re, methods=['POST'], name='reorder_chapters')

    _fn = g['grounded_deduction_fallback']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'grounded_deduction_fallback', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'grounded_deduction_fallback', _re)
    g['grounded_deduction_fallback'] = _re
    router.add_api_route('/chapters/{seq}/deductions/grounded-fallback', _re, methods=['GET'], name='grounded_deduction_fallback')

    _fn = g['review_deduction_grounding']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'review_deduction_grounding', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'review_deduction_grounding', _re)
    g['review_deduction_grounding'] = _re
    router.add_api_route('/chapters/{seq}/deductions/grounding', _re, methods=['POST'], name='review_deduction_grounding')

    _fn = g['patch_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'patch_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'patch_chapter', _re)
    g['patch_chapter'] = _re
    router.add_api_route('/chapters/{seq}', _re, methods=['PATCH'], name='patch_chapter')

    _fn = g['patch_chapter_gcd_fields']
    _re = types.FunctionType(
        _fn.__code__, core.__dict__, 'patch_chapter_gcd_fields',
        _fn.__defaults__, _fn.__closure__,
    )
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'patch_chapter_gcd_fields', _re)
    g['patch_chapter_gcd_fields'] = _re
    router.add_api_route(
        '/chapters/{seq}/gcd-fields', _re, methods=['PATCH'],
        name='patch_chapter_gcd_fields',
    )

    _fn = g['list_volumes']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'list_volumes', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'list_volumes', _re)
    g['list_volumes'] = _re
    router.add_api_route('/volumes', _re, methods=['GET'], name='list_volumes')

    _fn = g['add_volume']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_volume', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_volume', _re)
    g['add_volume'] = _re
    router.add_api_route('/volumes', _re, methods=['POST'], name='add_volume')

    _fn = g['update_volume']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'update_volume', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'update_volume', _re)
    g['update_volume'] = _re
    router.add_api_route('/volumes/{vid}', _re, methods=['PATCH'], name='update_volume')

    _fn = g['delete_volume']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'delete_volume', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'delete_volume', _re)
    g['delete_volume'] = _re
    router.add_api_route('/volumes/{vid}', _re, methods=['DELETE'], name='delete_volume')

    _fn = g['get_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_chapter', _re)
    g['get_chapter'] = _re
    router.add_api_route('/chapter', _re, methods=['GET'], name='get_chapter')

    _fn = g['get_chapter_execution_soft_status']
    _re = types.FunctionType(
        _fn.__code__, core.__dict__, 'get_chapter_execution_soft_status',
        _fn.__defaults__, _fn.__closure__,
    )
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_chapter_execution_soft_status', _re)
    g['get_chapter_execution_soft_status'] = _re
    router.add_api_route(
        '/chapter/execution-soft-status', _re, methods=['GET'],
        name='get_chapter_execution_soft_status',
    )

    _fn = g['chapter_versions']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chapter_versions', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chapter_versions', _re)
    g['chapter_versions'] = _re
    router.add_api_route('/chapter-versions', _re, methods=['GET'], name='chapter_versions')

    _fn = g['chapter_version']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chapter_version', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chapter_version', _re)
    g['chapter_version'] = _re
    router.add_api_route('/chapter-version/{vid}', _re, methods=['GET'], name='chapter_version')

    _fn = g['select_chapter']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'select_chapter', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'select_chapter', _re)
    g['select_chapter'] = _re
    router.add_api_route('/select/chapter', _re, methods=['POST'], name='select_chapter')

    _fn = g['select_finalize']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'select_finalize', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'select_finalize', _re)
    g['select_finalize'] = _re
    router.add_api_route('/select/finalize', _re, methods=['POST'], name='select_finalize')

    _fn = g['select_latest']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'select_latest', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'select_latest', _re)
    g['select_latest'] = _re
    router.add_api_route('/select/latest', _re, methods=['GET'], name='select_latest')

    _fn = g['select_light']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'select_light', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'select_light', _re)
    g['select_light'] = _re
    router.add_api_route('/select/light', _re, methods=['POST'], name='select_light')

    _fn = g['select_light_pick']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'select_light_pick', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'select_light_pick', _re)
    g['select_light_pick'] = _re
    router.add_api_route('/select/light/pick', _re, methods=['POST'], name='select_light_pick')

    _fn = g['select_light_latest']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'select_light_latest', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'select_light_latest', _re)
    g['select_light_latest'] = _re
    router.add_api_route('/select/light/latest', _re, methods=['GET'], name='select_light_latest')

_bind_and_register()
