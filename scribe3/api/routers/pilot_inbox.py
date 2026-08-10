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

router = APIRouter(tags=['pilot_inbox'])


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


def pilot_step(req: PilotStepReq, work: str = "main"):
    """推进一步。approve 级动作(finalize)不在此执行——必须走 /pilot/approve(宪法)。

    手动 mode:outline_proposed 须走 approve(大纲品味检查点,业界 HITL);
    连写 mode=run 仍可连续推进(批量生产,与既有连写合同一致)。
    """
    from scribe3.pilot import NEXT, read_state, step
    st = _store_for(work)
    if not st.get_chapter(req.seq):
        raise HTTPException(status_code=404, detail=f"第 {req.seq} 章不存在(先建章或用 /pilot/run 自动建)")
    if req.steer.strip():
        # P2-8:与 /ideas 一致改追加(覆盖会清掉 Inbox 攒的想法),帽 2000
        _prev_s = _pilot_steer(st, req.seq)
        _merged = ((_prev_s + "\n") if _prev_s else "") + req.steer.strip()
        st._execute_write("UPDATE type::record('chapter',$seq) SET pilot_steer=$s",
                          {"seq": req.seq, "s": _merged[-2000:]})
    cur = read_state(st, req.seq)["state"]
    nxt = NEXT.get(cur)
    if nxt and nxt[0] == "finalize":
        raise HTTPException(status_code=409, detail="终选是宪法级动作:请走 /pilot/approve(作者背书)")
    # 大纲检查点:手动驾驶禁止 step 硬闯(放行=approve);run 连写不拦
    if (req.mode or "manual") != "run" and cur == "outline_proposed":
        raise HTTPException(
            status_code=409,
            detail="大纲待作者放行:请点收件箱「放行」或驾驶舱「确认大纲并继续」(/pilot/approve)")
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中(/pilot/pause 先停),防并发双跑")
    # 可选：高风险设定债挡推进（须先收件箱处理）
    try:
        import os
        from scribe3 import settings as _settings
        flag = False
        try:
            flag = bool(_settings.get_setting("SCRIBE3_CANON_DEBT_BLOCK_HIGH"))
        except Exception:
            flag = (os.environ.get("SCRIBE3_CANON_DEBT_BLOCK_HIGH") or "").strip().lower() in (
                "1", "true", "yes", "on",
            )
        if flag:
            debt = st.count_canon_debt() if hasattr(st, "count_canon_debt") else {}
            hi = int((debt or {}).get("high") or 0)
            if hi > 0:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "canon_debt_high",
                        "message": f"有 {hi} 条高风险设定待确认，请先到设定收件箱处理后再推进。",
                        "debt": debt,
                        "open": "view:canon-inbox",
                    },
                )
    except HTTPException:
        raise
    except Exception:
        pass
    _k = (work, req.seq)
    with _pilot_inflight_lock:
        if _k in _pilot_inflight:
            raise HTTPException(status_code=409, detail=f"第 {req.seq} 章 pilot 已在推进")
        _pilot_inflight.add(_k)
    try:
        # R2-9:手动步也传 journal(此前只 approve/run 传,手动步零留痕——生产实锤)
        return step(st, req.seq, _pilot_executor(work), mode=req.mode,
                    journal=_pilot_journal(work, req.seq))
    finally:
        with _pilot_inflight_lock:
            _pilot_inflight.discard(_k)

def add_idea(req: IdeaIn, work: str = "main"):
    """想法收件箱(主编主动化 T8):作者唯一的输入负担——丢一句话,主编路由落位。
    宪法:setting 类永不自动动圣经(pending_approval 进决策收件箱);
    outline/steer 落该章 pilot_steer(propose_outline/draft 时最高优先吃它);
    revise 生成定向修订提案进收件箱;unclear 只问一个澄清问题。"""
    import json as _json
    st = _store_for(work)
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="想法不能为空")
    complete_fn = _complete_fn
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    route = {"kind": "unclear", "target_seq": None, "note": "", "question": "能再说具体点吗?"}
    try:
        raw = complete_fn(_IDEA_ROUTE_PROMPT.replace("{max_ch}", str(st.max_chapter()))
                          .replace("{text}", text[:500]))
        import re as _re
        m = _re.search(r"\{.*\}", raw or "", _re.S)
        if m:
            d = _json.loads(m.group(0))
            if d.get("kind") in ("outline", "steer", "setting", "revise", "unclear"):
                route = {"kind": d["kind"],
                         "target_seq": d.get("target_seq"),
                         "note": str(d.get("note") or "")[:200],
                         "question": str(d.get("question") or "")[:200]}
    except Exception as e:
        logging.getLogger("scribe3").warning("idea 路由失败(落 unclear): %s", e)
    kind = route["kind"]
    # 审查 P1-3:target_seq 脏值(LLM 返回"第3章"/越界/负数)一律降级,绝不 500 丢想法
    tseq = None
    try:
        tseq = int(route.get("target_seq"))
    except (TypeError, ValueError):
        tseq = None
    if kind in ("outline", "steer") and (tseq is None or not st.get_chapter(tseq)):
        kind, route["note"] = "unclear", (route.get("note") or "")
        route["question"] = f"这想法该落到第几章?(路由到的章 {route.get('target_seq')!r} 不存在)"
    status = "routed"
    if kind in ("outline", "steer"):
        # 追加进该章 pilot_steer(想法可累积,帽 2000 字防膨胀;pilot 提案/草稿最高优先注入)
        prev = _pilot_steer(st, tseq)
        merged = ((prev + "\n") if prev else "") + text
        st._execute_write("UPDATE type::record('chapter',$seq) SET pilot_steer=$s",
                          {"seq": tseq, "s": merged[-2000:]})
        status = "done"
    elif kind in ("setting", "revise"):
        status = "pending_approval"   # 宪法:动圣经/改旧章永远等人
    elif kind == "unclear":
        status = "unclear"
    # 想法本体先落库;unclear 必须落 question(旧库缺字段时收件箱靠懒回填兜底)
    from scribe3.inbox import idea_unclear_question, DEFAULT_UNCLEAR_QUESTION
    q = (route.get("question") or "").strip() or DEFAULT_UNCLEAR_QUESTION
    if kind == "unclear":
        q = idea_unclear_question({"question": q, "note": route.get("note"), "text": text})
    st._execute_write(
        "CREATE idea SET text=$t, route_kind=$k, target_seq=$sq, note=$n, status=$st_, "
        "question=$q, created_at=time::now()",
        {"t": text, "k": kind, "sq": tseq, "n": route["note"], "st_": status,
         "q": q if kind == "unclear" else None})
    return {"kind": kind, "target_seq": tseq, "status": status,
            "note": route["note"], "question": q if kind == "unclear" else None}

def resolve_idea(req: IdeaResolveReq, work: str = "main"):
    """审查 P1-4:想法处理完毕出收件箱(status→done)——决策收件箱不积压噪声。"""
    _store_for(work)._execute_write(
        "UPDATE type::record('idea',$id) SET status='done'", {"id": req.id})
    return {"ok": True}

def pilot_dismiss(req: PilotDismissReq, work: str = "main"):
    """审查 P1-6:pilot 僵尸态出口——作者绕开 pilot 手写的章,一键退出编排
    (清 pilot_state,不动任何正文/草料;想再用 pilot 从头 step 即可)。"""
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中——请先 /pilot/pause 再退出 pilot")
    # R2-13:一并清 pilot_steer——否则陈旧作者意图重启 pilot 时以「最高优先」静默复活(不可见的行为漂移)
    _store_for(work)._execute_write(
        "UPDATE type::record('chapter',$seq) SET pilot_state=NONE, pilot_state_at=NONE, "
        "pilot_parked=NONE, pilot_card=NONE, pilot_steer=NONE", {"seq": req.seq})
    return {"seq": req.seq, "pilot_state": None}

def pilot_status(seq: int, work: str = "main"):
    from scribe3.pilot import status
    return status(_store_for(work), seq)

def pilot_approve(req: PilotApproveReq, work: str = "main"):
    """作者背书放行当前停靠动作(propose 停靠=继续推进;delivered→finalize=终选)。"""
    from scribe3.pilot import read_state, step
    st = _store_for(work)
    cur = read_state(st, req.seq)["state"]
    if req.expect_state and cur != req.expect_state:
        raise HTTPException(status_code=409, detail=(
            f"状态已变({req.expect_state} → {cur}),为防误背书请刷新收件箱再操作"))
    if cur == "finalized":
        return {"seq": req.seq, "state": cur, "note": "已定稿"}
    # R2-3:连写运行中不许 approve(防 stale 放行与 run 并发双跑同章)
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="连写进行中(/pilot/pause 先停),防并发双跑")
    _k = (work, req.seq)
    with _pilot_inflight_lock:
        if _k in _pilot_inflight:
            raise HTTPException(status_code=409, detail=f"第 {req.seq} 章pilot 已在推进")
        _pilot_inflight.add(_k)
    try:
        return step(st, req.seq, _pilot_executor(work), mode="manual",
                    journal=_pilot_journal(work, req.seq))
    finally:
        with _pilot_inflight_lock:
            _pilot_inflight.discard(_k)

def pilot_run(req: PilotRunReq, background: BackgroundTasks, work: str = "main"):
    if req.until_seq < req.start_seq:
        raise HTTPException(status_code=422, detail="until_seq 须 ≥ start_seq")
    if _pilot_run_state.get(work, {}).get("running"):
        raise HTTPException(status_code=409, detail="该书连写已在进行(/pilot/pause 可停)")
    # R2-3:有手动 pilot 步在途也不启动连写(防同章同 action 并发双跑)
    with _pilot_inflight_lock:
        if any(w == work for (w, _s) in _pilot_inflight):
            raise HTTPException(status_code=409, detail="有 pilot 步在途,请稍候再启动连写")
    background.add_task(_pilot_run_bg, work, req.start_seq, req.until_seq)
    return {"running": True, "start": req.start_seq, "until": req.until_seq,
            "note": "逐章推进到交付;终选(宪法)在收件箱等你;/pilot/pause 随时停"}

def pilot_pause(work: str = "main"):
    state = _pilot_run_state.get(work)
    if state:
        state["running"] = False
    return {"paused": True}

def pilot_run_status(work: str = "main"):
    return _pilot_run_state.get(work) or {"running": False, "stopped": ""}

def pilot_reset(req: PilotApproveReq, work: str = "main"):
    """stalled/parked 解卡:清 parked 标记(状态不回退——版本库无损,重跑当前步即可)。"""
    from scribe3.pilot import read_state, write_state
    st = _store_for(work)
    s = read_state(st, req.seq)
    write_state(st, req.seq, s["state"], parked="")
    return {"seq": req.seq, "state": s["state"], "parked": ""}

def decision_inbox(work: str = "main", seq: int | None = None):
    """主编主动化 T4:决策收件箱——所有「等作者」的事项一处集中。

    源:needs_human journal · lesson · pilot · idea(pending+unclear) · pulse · digest。
    旧 unclear 无 question → idea_unclear_question 推导并懒回填。
    """
    import glob as _glob
    import json as _json
    from scribe3.inbox import (
        dedupe_degraded, idea_inbox_item, needs_question_backfill,
        sort_items, idea_unclear_question,
    )
    st = _store_for(work)
    items: list[dict] = []
    degraded: list[str] = []
    focus_seq = int(seq) if seq is not None else None

    def _deg(src: str) -> None:
        if src not in degraded:
            degraded.append(src)

    # ① needs_human
    base = (os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR")
            or os.path.expanduser("~/.scribe3-loop-journals"))
    latest: dict[int, tuple[int, str]] = {}
    for fp in _glob.glob(os.path.join(base, work, "loop_ch*.json")):
        try:
            bn = os.path.basename(fp)
            s_ = int(bn.split("_")[1][2:])
            ns_ = int(bn.rsplit("_", 1)[1].split(".")[0])
            if s_ not in latest or ns_ > latest[s_][0]:
                latest[s_] = (ns_, fp)
        except Exception:
            _deg("needs_human")
            continue
    seen_nh: set[int] = set()
    _pilot_parked_seqs: set[int] = set()
    try:
        for rr in st._query("SELECT seq, pilot_parked FROM chapter:.. WHERE pilot_parked != NONE"):
            if (rr.get("pilot_parked") or "").strip():
                _pilot_parked_seqs.add(rr.get("seq"))
    except Exception:
        _deg("needs_human")
    for s_, (_ns, fp) in latest.items():
        if s_ in _pilot_parked_seqs:
            continue
        try:
            with open(fp, encoding="utf-8") as _fh:
                stages = (_json.loads(_fh.read()) or {}).get("stages_completed") or []
            if any("_needs_human" in x for x in stages):
                seen_nh.add(s_)
        except Exception:
            _deg("needs_human")
            continue
    for s in sorted(seen_nh):
        items.append({
            "id": f"needs_human:{s}", "kind": "needs_human", "seq": s,
            "message": f"第 {s} 章 loop 三稿全被拦(needs_human):三稿在版本库,请裁决——真不行还是检测器过严?",
            "action": {"kind": "chat",
                       "payload": f"第 {s} 章三稿全被拦(needs_human),帮我并排评估版本库三稿:哪稿其实成立?检测器是不是过严?给裁决建议"},
        })
    # ② lesson
    try:
        for r in st.list_lessons():
            if (r.get("importance") or 0) >= 4 and not r.get("invalid_at"):
                lid = r.get("id") or ""
                items.append({
                    "id": f"lesson:{lid}", "kind": "promotable_lesson", "lesson_id": lid,
                    "message": f"教训已达升格阈(重要性 {r.get('importance')}):「{(r.get('text') or '')[:60]}」——认可则在主编对话让其走待批升格",
                    "action": {"kind": "chat", "payload": f"这条教训「{(r.get('text') or '')[:40]}」我认可,想升格为长期工艺规则——请到章内写作对话(主编在那挂 s3_craft_rule_add)走待批升格"},
                })
    except Exception as e:
        logging.getLogger("scribe3").warning("inbox lessons 失败(忽略): %s", e)
        _deg("lessons")
    # ⑤ pilot
    try:
        rows = st._query(
            "SELECT seq, pilot_state, pilot_parked, pilot_card, synopsis FROM chapter:.. "
            "WHERE pilot_state != NONE ORDER BY seq")
        for r in rows:
            ps, seq_p = r.get("pilot_state"), r.get("seq")
            if r.get("pilot_parked"):
                park_txt = str(r["pilot_parked"])
                items.append({
                    "id": f"pilot_parked:{seq_p}", "kind": "pilot_parked", "seq": seq_p,
                    "message": f"第 {seq_p} 章 pilot 停靠:{park_txt}",
                    "action": {"kind": "chat",
                               "payload": f"第 {seq_p} 章 pilot 停在「{park_txt[:60]}」,帮我分析怎么解"},
                    "resolve": {"kind": "pilot_reset", "payload": seq_p},
                })
            elif ps == "outline_proposed":
                items.append({
                    "id": f"pilot_outline:{seq_p}", "kind": "pilot_outline", "seq": seq_p,
                    "message": f"第 {seq_p} 章大纲提案待放行:{(r.get('synopsis') or '')[:80]}",
                    "action": {"kind": "pilot_approve", "payload": seq_p,
                               "expect_state": "outline_proposed"},
                })
            elif ps == "delivered":
                card = {}
                try:
                    card = _json.loads(r.get("pilot_card") or "{}")
                except Exception:
                    pass
                if not isinstance(card, dict):
                    card = {}
                lc = (card.get("low_confidence") or "").strip()
                items.append({
                    "id": f"pilot_delivered:{seq_p}", "kind": "pilot_delivered", "seq": seq_p,
                    "message": f"第 {seq_p} 章已交付({card.get('words', '?')} 字)"
                               + (f";主编拿不准:{lc[:100]}" if lc and lc != "无" else ";主编自评无拿不准处"),
                    "card": card or None,
                    "action": {"kind": "pilot_approve", "payload": seq_p,
                               "expect_state": "delivered"},
                })
    except Exception as e:
        logging.getLogger("scribe3").warning("inbox pilot 失败(忽略): %s", e)
        _deg("pilot")
    # ④ ideas: pending_approval + unclear(含旧库无 question 的懒回填)
    try:
        for r in st._query(
                "SELECT meta::id(id) AS id, text, route_kind, note, status, question "
                "FROM idea WHERE status IN ['pending_approval', 'unclear']"):
            item = idea_inbox_item(r)
            items.append(item)
            # 懒回填:旧 unclear 缺 question → 写入推导问句,下次不再空
            if needs_question_backfill(r) and r.get("id"):
                try:
                    q = idea_unclear_question(r)
                    st._execute_write(
                        "UPDATE type::record('idea',$id) SET question=$q",
                        {"id": r["id"], "q": q})
                except Exception:
                    logging.getLogger("scribe3").debug(
                        "idea question 懒回填失败 id=%s", r.get("id"), exc_info=True)
    except Exception as e:
        logging.getLogger("scribe3").warning("inbox ideas 失败(忽略): %s", e)
        _deg("ideas")
    # ③ pulse
    if focus_seq is not None:
        try:
            from scribe3.pulse import chapter_pulse
            for d in chapter_pulse(st, focus_seq)["dimensions"]:
                for it in d["items"]:
                    if it["severity"] == "decision":
                        dim = d["dimension"]
                        items.append({
                            "id": f"pulse:{focus_seq}:{dim}:{(it.get('message') or '')[:24]}",
                            "kind": "pulse_decision", "dimension": dim,
                            "seq": focus_seq, "message": it["message"],
                            "action": it.get("action"),
                        })
        except Exception as e:
            logging.getLogger("scribe3").warning("inbox pulse 失败(忽略): %s", e)
            _deg("pulse")
    # ⑥ digest
    try:
        dg = st.latest_chief_digest()
        if dg:
            msg = f"[{dg['day']}] {dg['body']}"
            if dg.get("error"):
                msg += f"(部分来源失败:{dg['error']})"
            items.append({
                "id": f"digest:{dg.get('day') or 'latest'}",
                "kind": "daily_digest", "message": msg,
                "action": {"kind": "chat",
                           "payload": f"这是今日摘报:{dg['body']}——帮我把最该处理的一件事挑出来,给具体下一步"},
            })
    except Exception as e:
        logging.getLogger("scribe3").warning("inbox digest 失败(忽略): %s", e)
        _deg("digest")

    sort_items(items, focus_seq)
    return {
        "items": items,
        "count": len(items),
        "degraded_sources": dedupe_degraded(degraded),
        "focus_seq": focus_seq,
    }

def lessons_promotable(work: str = "main", threshold: int = 4):
    """升格候选队列(北极星任务8):importance ≥ threshold 的有效 lesson。
    只列候选——升格动作必须由作者在主编对话让其调用 s3_craft_rule_add
    (elicitation 待批);蒸馏产物升格永不自动生效(宪法条款,防自评自改变体)。"""
    rows = [r for r in _store_for(work).list_lessons()
            if (r.get("importance") or 0) >= threshold]
    for r in rows:
        r["note"] = ("已达升格阈:如认可,请在主编对话中让其调用 s3_craft_rule_add"
                     "(elicitation 待批)升格为 craft_rule;系统绝不自动升格")
    return rows

def north_star_book(work: str = "main"):
    """书级北极星 scorecard(北极星任务7,蓝图 §3-③ 后半):四维面板——张弛分布/
    伏笔回收率/跨章矛盾密度/目的达成率 + 因果欠账存量(§3-② 溢出承载)。
    绝不合成加权总分(宪法):北极星语义=所有 setpoint 在区间内 + 各维无恶化趋势,
    面板全绿只证明机器没失职,"是不是好小说"的裁决留给人。
    按需现算不建缓存表(D-016:底座对表 Q2 裁决弃 DB EVENT 聚合;章级变更已走
    /live 推送,前端因章变而重取书级)。各维独立 fail-soft,空书 no_data 不假绿。"""
    st = _store_for(work)
    out: dict = {}
    try:   # ① 张弛分布(find_tension_monotony,与 /post-check 同源组装)
        from scribe3.brief import chapter_draft_text, find_tension_monotony, parse_chapter_meta
        metas: list[dict] = []
        # 2-D(#5):窄查询一次拉草料字段(chapter_draft_text 只吃 synopsis/beats/
        # scene_truth),不再逐章 get_chapter 拉 prose/embedding 全行
        for c in st.chapters_lite():
            m = parse_chapter_meta(chapter_draft_text(c))
            if m:
                metas.append({"seq": c["seq"], **m})
        out["tension"] = {"no_data": not metas, "chapters_with_meta": len(metas),
                          "findings": find_tension_monotony(metas) if metas else []}
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book tension 失败: %s", e)
        out["tension"] = {"no_data": True, "degraded": True}
    try:   # ② 伏笔回收率 = payoff/(open+payoff),另列超期数(蓝图公式)
        rows = st.promises_with_lifecycle()
        payoff = sum(1 for p in rows if p.get("payoff_chapter"))
        open_ = sum(1 for p in rows if p.get("status") == "open")
        overdue = sum(1 for p in rows if (p.get("window") or {}).get("state") == "overdue")
        denom = payoff + open_
        out["promise_recovery"] = ({"no_data": True} if not rows else
                                   {"no_data": False, "payoff": payoff, "open": open_,
                                    "overdue": overdue,
                                    "rate": (payoff / denom) if denom else None})
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book promise 失败: %s", e)
        out["promise_recovery"] = {"no_data": True, "degraded": True}
    try:   # ③ 跨章矛盾密度(CED 口径归一"错误/万字";仅自比趋势)
        cc = st.validate_cross_chapter_consistency() or []
        total_wc = st.total_word_count()
        out["contradiction_density"] = {
            "no_data": total_wc == 0, "issues": len(cc), "total_chars": total_wc,
            "per_10k": (len(cc) / total_wc * 10000) if total_wc else None,
            "self_compare_only": True,
            "note": "口径同 ConStory CED、检测器不同,数字不可对标外部基准(蓝图 v2 口径警示)"}
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book contradiction 失败: %s", e)
        out["contradiction_density"] = {"no_data": True, "degraded": True,
                                        "self_compare_only": True}
    try:   # ④ 目的达成率(任务6 deltas 聚合;waived 出分母)
        # P1门审查 P1-4:按 (kind,predicate) 链尾状态去重——carried 滚动副本会把
        # 还清的债永久挂账、分母每滚一次膨胀(一条最终达成的 delta 被计成 50%)。
        from scribe3.purpose import parse_deltas
        tail: dict = {}   # (kind, predicate) -> (seq, status)
        for c in st.chapters_lite():   # 2-D(#5):deltas 从窄查询取,不拉全行
            for d in parse_deltas(c.get("deltas")):
                key = (d["kind"], d["predicate"])
                prev = tail.get(key)
                if prev is None or c["seq"] >= prev[0]:
                    tail[key] = (c["seq"], d["status"])
        statuses = [s for _, s in tail.values()]
        tot = len(statuses)
        ach = statuses.count("achieved")
        carried = statuses.count("carried")
        waived = statuses.count("waived")
        denom = tot - waived
        out["fulfillment"] = ({"no_data": True} if tot == 0 else
                              {"no_data": False, "achieved": ach, "total": tot,
                               "carried_backlog": carried, "waived": waived,
                               "rate": (ach / denom) if denom else None,
                               "note": "按目的链尾状态去重统计(滚动副本不重复计账)"})
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book fulfillment 失败: %s", e)
        out["fulfillment"] = {"no_data": True, "degraded": True}
    try:   # 附加信息位:因果欠账存量(非四维,§3-② brief top-5 溢出的面板承载)
        out["causal_debt_total"] = st.causal_debt_total()
    except Exception as e:
        # U-011:与同函数其余维度(fulfillment 等)一致,失败标 degraded + log.error,
        # 不再零日志零标记(None 与"真 0 欠账"不可分)。
        logging.getLogger("scribe3").error("north_star causal_debt_total 失败", exc_info=True)
        out["causal_debt_total"] = None
        out["causal_debt_degraded"] = True
    try:   # ⑤ QD 文体多样性档案(北极星任务9):分布单调告警,只进面板不进任何门禁
        from scribe3.qd import CV_FLAT_RUN, style_drift_alerts
        profs = st.list_style_profiles()
        out["style_diversity"] = {"no_data": not profs, "profiles_n": len(profs),
                                  "alerts": style_drift_alerts(profs),
                                  # P2-3:窗口不足≠无漂移——前端不得把空 alerts 当绿灯
                                  "insufficient_window": len(profs) < CV_FLAT_RUN + 3,
                                  "latest": (profs[-1] if profs else None)}
    except Exception as e:
        logging.getLogger("scribe3").warning("north_star_book style_diversity 失败: %s", e)
        out["style_diversity"] = {"no_data": True, "degraded": True, "alerts": []}
    return out

async def live(work: str = "main"):
    if _live_count.get(work, 0) >= _LIVE_MAX:
        raise HTTPException(status_code=429, detail=f"too many live connections for {work}")
    _live_count[work] = _live_count.get(work, 0) + 1
    url = os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")

    async def counted_live_stream():
        try:
            async for event in live_stream(url, "scribe3", work, _LIVE_TABLES):
                yield event
        finally:
            # 返回 StreamingResponse 不代表浏览器已断开；必须等其 body iterator
            # 真正关闭后才释放这一 work 的 LIVE 配额。
            _live_count[work] = max(0, _live_count.get(work, 0) - 1)

    from scribe3.api.sse import sse_response
    return sse_response(counted_live_stream())


def ensure_narrative_drive_volume_ep(
    req: NarrativeDriveEnsureReq,
    work: str = "main",
):
    """OI-2b：书级 narrative_drive 批量 ensure（运维/已登录会话）。

    - 默认 ``dry_run=True``，须显式 ``dry_run=false`` 才写库
    - 须 ``SCRIBE3_NARRATIVE_ENGINE=1``
    - **永不 park**；不暴露公网匿名（走既有 session/auth 中间件）
    - ``include_author`` / ``force`` 危险，默认关
    """
    from scribe3.novel_quality_flags import narrative_engine_enabled
    from scribe3.narrative_drive import ensure_narrative_drive_range

    if not narrative_engine_enabled():
        raise HTTPException(
            status_code=400,
            detail="SCRIBE3_NARRATIVE_ENGINE 未开启，拒绝 ensure",
        )
    recompose = (req.recompose_if or "").strip() or None
    if recompose and recompose not in ("outline_enrich", "always"):
        raise HTTPException(
            status_code=400,
            detail="recompose_if 仅支持 outline_enrich|always|省略",
        )
    max_seqs = int(req.max_seqs or 200)
    if max_seqs < 1 or max_seqs > 500:
        raise HTTPException(status_code=400, detail="max_seqs 须在 1..500")
    st = _store_for(work)
    force = bool(req.force) or recompose == "always"
    stats = ensure_narrative_drive_range(
        st,
        seqs=req.seqs,
        force=force,
        steer=req.steer or "",
        recompose_if=recompose if recompose != "always" else None,
        dry_run=bool(req.dry_run),
        max_seqs=max_seqs,
        include_author=bool(req.include_author),
    )
    return {"ok": True, "work": work, **stats}


def _bind_and_register() -> None:
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['pilot_step']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_step', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_step', _re)
    g['pilot_step'] = _re
    router.add_api_route('/pilot/step', _re, methods=['POST'], name='pilot_step')

    _fn = g['add_idea']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_idea', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_idea', _re)
    g['add_idea'] = _re
    router.add_api_route('/ideas', _re, methods=['POST'], name='add_idea')

    _fn = g['resolve_idea']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'resolve_idea', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'resolve_idea', _re)
    g['resolve_idea'] = _re
    router.add_api_route('/ideas/resolve', _re, methods=['POST'], name='resolve_idea')

    _fn = g['pilot_dismiss']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_dismiss', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_dismiss', _re)
    g['pilot_dismiss'] = _re
    router.add_api_route('/pilot/dismiss', _re, methods=['POST'], name='pilot_dismiss')

    _fn = g['pilot_status']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_status', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_status', _re)
    g['pilot_status'] = _re
    router.add_api_route('/pilot/status', _re, methods=['GET'], name='pilot_status')

    _fn = g['pilot_approve']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_approve', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_approve', _re)
    g['pilot_approve'] = _re
    router.add_api_route('/pilot/approve', _re, methods=['POST'], name='pilot_approve')

    _fn = g['pilot_run']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_run', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_run', _re)
    g['pilot_run'] = _re
    router.add_api_route('/pilot/run', _re, methods=['POST'], name='pilot_run')

    _fn = g['pilot_pause']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_pause', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_pause', _re)
    g['pilot_pause'] = _re
    router.add_api_route('/pilot/pause', _re, methods=['POST'], name='pilot_pause')

    _fn = g['pilot_run_status']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_run_status', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_run_status', _re)
    g['pilot_run_status'] = _re
    router.add_api_route('/pilot/run-status', _re, methods=['GET'], name='pilot_run_status')

    _fn = g['pilot_reset']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'pilot_reset', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'pilot_reset', _re)
    g['pilot_reset'] = _re
    router.add_api_route('/pilot/reset-step', _re, methods=['POST'], name='pilot_reset')

    _fn = g['ensure_narrative_drive_volume_ep']
    _re = types.FunctionType(
        _fn.__code__, core.__dict__, 'ensure_narrative_drive_volume_ep',
        _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'ensure_narrative_drive_volume_ep', _re)
    g['ensure_narrative_drive_volume_ep'] = _re
    router.add_api_route(
        '/narrative-drive/ensure', _re, methods=['POST'],
        name='ensure_narrative_drive_volume_ep')

    _fn = g['decision_inbox']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'decision_inbox', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'decision_inbox', _re)
    g['decision_inbox'] = _re
    router.add_api_route('/inbox', _re, methods=['GET'], name='decision_inbox')

    _fn = g['lessons_promotable']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'lessons_promotable', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'lessons_promotable', _re)
    g['lessons_promotable'] = _re
    router.add_api_route('/lessons/promotable', _re, methods=['GET'], name='lessons_promotable')

    _fn = g['north_star_book']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'north_star_book', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'north_star_book', _re)
    g['north_star_book'] = _re
    router.add_api_route('/north-star/book', _re, methods=['GET'], name='north_star_book')

    _fn = g['live']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'live', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'live', _re)
    g['live'] = _re
    router.add_api_route('/live', _re, methods=['GET'], name='live')

_bind_and_register()
