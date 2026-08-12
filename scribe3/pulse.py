"""章级脉搏聚合(主编主动化 T1,方案 §三.感知层)。

六维 {dimension, severity, items, degraded?}:promise/arc/relation/tension/causal/quality。
原则:
- 零新检测器——纯复用简报指令(brief)、确定性张力、因果欠账、QC/ingest 缓存;
- 北极星宪法:不造总分,只有分维 severity(info|nudge|decision);
- 逐维 fail-soft 隔离:单维数据源故障 → 该维 degraded=True + info,其余维照常;
- decision 条目全部源自确定性信号(时机引擎只对 decision 开口,防误报唠叨)。
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("scribe3.pulse")

_SEV_ORDER = {"info": 0, "nudge": 1, "decision": 2}
_ARC_JUMP_MAX = 15   # 单章 lie_belief 位移>此值=顿悟太便宜(工艺引擎 M3,自定口径)


def _item(msg: str, sev: str = "info", action: dict | None = None) -> dict:
    return {"message": msg, "severity": sev, "action": action}


def _dim(name: str, items: list[dict], degraded: bool = False) -> dict:
    sev = "info"
    for it in items:
        if _SEV_ORDER[it["severity"]] > _SEV_ORDER[sev]:
            sev = it["severity"]
    return {"dimension": name, "severity": sev, "items": items, **({"degraded": True} if degraded else {})}


def _chat_action(hint: str) -> dict:
    return {"kind": "chat", "payload": hint}


def _promise_dim(st, seq: int) -> dict:
    from scribe3.brief import promise_directives
    rows = st.promises_with_lifecycle(max_chapter=seq)
    d = promise_directives(rows)
    items = ([_item(m, "decision", _chat_action(f"这条伏笔需要决策:{m}——帮我权衡三选一")) for m in d["decisions"]]
             + [_item(m, "nudge", _chat_action(f"简报指令:{m}——这章怎么落?")) for m in d["directives"]]
             + [_item(m, "info") for m in d["reminders"]])
    if not items:
        items = [_item("伏笔台账无到期项")]
    return _dim("promise", items)


def _arc_tracking_flag(st) -> Any:
    """作品级 arc_tracking：intent 优先，settings_store 备选。"""
    try:
        if hasattr(st, "get_intent"):
            intent = st.get_intent() or {}
            if intent.get("arc_tracking") is not None:
                return intent
    except Exception:
        pass
    try:
        from scribe3 import settings_store
        work = str(getattr(st, "db_name", None) or getattr(st, "db", None) or "main")
        raw = settings_store.get_override(f"arc_tracking:{work}")
        if raw is not None:
            return str(raw)
    except Exception:
        pass
    return None


def _arc_dim(st, seq: int) -> dict:
    """弧光维：诚实分级；配置态永不 degraded（仅传感器故障由 chapter_pulse 设）。"""
    from scribe3 import arc_signals as AS

    # 作品级静音
    if AS.is_arc_tracking_off(_arc_tracking_flag(st)):
        return _dim("arc", [_item(AS.tracking_off_message())])

    chars = list(st.characters() or [])
    anchors_by_id: dict = {}
    for c in chars:
        try:
            anchors_by_id[c.id] = st.char_anchors(c.id) or {}
        except Exception:
            anchors_by_id[c.id] = {}
    parts = AS.partition_arc_chars(chars, anchors_by_id)
    with_lie = parts["with_lie"]
    no_lie = parts["eligible_no_lie"]
    items: list[dict] = []

    # 冷启动：主档缺 lie（作者 UI 用 tools=False，不暴露 MCP 工具名）
    for row in no_lie:
        name = row["name"]
        msg = AS.format_cold_start_decision(name, tools=False)
        seed = (
            f"请为角色「{name}」登记弧光内核并写入落库（需我审批）。\n"
            f"请先读取该角色现有设定，再补全并提交：\n"
            f"- 错误信念(Lie)：角色信以为真、阻碍成长的一句信念\n"
            f"- 幽灵伤(Ghost)：造成 Lie 的往事创伤\n"
            f"- 真相(Truth)：故事要教会角色的、与 Lie 对冲的认识\n"
            f"- 想要(Want) / 需要(Need) / 弧型(arc_type)\n"
            f"- 私议程(private_agenda，可选)\n"
            f"工具：s3_get 相关读后，用 s3_set_char_anchors 写入（MERGE 只传要改的字段）。"
            f"未获批准不得声称已落库。"
        )
        items.append(_item(msg, "decision", _chat_action(seed)))

    if not with_lie and not no_lie:
        # 合法未启用 — info 静音，禁止「未见跳变」假绿
        return _dim("arc", [_item(AS.quiet_arc_message())])

    # 有 lie：采样 / 跳变 / 节拍 focus
    n_samples = 0
    unmeasured_names: list[str] = []
    for row in with_lie:
        cid = row["id"]
        belief = None
        try:
            belief = st.latest_lie_belief(cid, seq)
        except Exception:
            belief = None
        if belief is not None:
            n_samples += 1
        else:
            unmeasured_names.append(row["name"])

        plan = []
        try:
            plan = st.list_arc_plan(cid) or []
        except Exception:
            plan = []
        anchors = row.get("anchors") or {}
        focus = AS.arc_beat_focus(
            plan,
            belief=belief,
            next_ch=seq,
            arc_type=anchors.get("arc_type"),
            slack=AS.ARC_BELIEF_SLACK,
        )
        if focus and (focus.get("status") or "") in (
            "overdue_miss", "overdue_unmeasured",
        ):
            msg = AS.format_beat_decision(row["name"], focus, tools=False)
            items.append(_item(
                msg, "decision",
                _chat_action(
                    f"角色「{row['name']}」弧光节拍逾期，请帮我三选一："
                    f"① 补事件并记录信奉度；② 展期/重规划里程碑；③ 改写 Lie/弧型。"
                    f"先读现有弧光锚与计划，再提交待批写入。"
                )))
        elif focus and (focus.get("status") or "") == "due":
            bn = focus.get("beat_name") or "—"
            items.append(_item(
                f"弧光节拍·{row['name']}：本章应到达「{bn}」(第{focus.get('target_chapter')}章)",
                "nudge",
                _chat_action(f"{row['name']} 本章节拍「{bn}」怎么落?")))

    if unmeasured_names and with_lie:
        # 有 lie 全未测或部分未测 → nudge（不全靠假绿）
        if n_samples == 0:
            items.append(_item(
                AS.format_unmeasured_nudge(unmeasured_names),
                "nudge",
                _chat_action("这些角色还没有信奉度采样，怎么补?")))

    for j in st.lie_belief_jumps(threshold=_ARC_JUMP_MAX):
        if j["chapter"] > seq:
            continue
        name = str(j["character_id"]).split(":")[-1]
        gap = j.get("gap") or 1
        move = abs(j["cur"] - j["prev"])
        if gap <= 1:
            items.append(_item(
                f"弧光跳变:{name} 信奉度 第{j['prev_chapter']}章 {j['prev']} → 第{j['chapter']}章 {j['cur']}"
                f"(单章位移 {move} > {_ARC_JUMP_MAX},顿悟太便宜——补事件背书或摊到多章)",
                "decision", _chat_action(f"{name} 这次信念位移是不是太陡了?帮我看第{j['chapter']}章怎么补")))
        else:
            items.append(_item(
                f"弧光节奏留意:{name} 信奉度 第{j['prev_chapter']}→{j['chapter']}章(跨 {gap} 章)位移 {move}"
                f"——若中间无铺垫章,补一次刷新;有则忽略",
                "nudge", _chat_action(f"{name} 第{j['prev_chapter']}到{j['chapter']}章的信念变化衔接够吗?")))

    if not items:
        if n_samples > 0:
            items = [_item(AS.healthy_arc_message(n_samples))]
        elif with_lie:
            items = [_item(AS.format_unmeasured_nudge(
                [r["name"] for r in with_lie]), "nudge")]
        else:
            items = [_item(AS.quiet_arc_message())]
    return _dim("arc", items)


def _relation_dim(st, seq: int) -> dict:
    from scribe3.brief import heat_of
    items: list[dict] = []
    by_pair: dict[tuple, int] = {}
    for t in st.list_relation_touches() or []:
        pair = tuple(sorted([t.get("a") or "", t.get("b") or ""]))
        by_pair[pair] = max(by_pair.get(pair, 0), t.get("chapter") or 0)
    for (pa, pb), last in by_pair.items():
        if heat_of(last or None, seq) == "cold":
            label = f"{str(pa).split(':')[-1]}↔{str(pb).split(':')[-1]}"
            items.append(_item(
                f"关系冷却:{label} 距上次有效互动已 {seq - last} 章",
                "nudge", _chat_action(f"{label} 这条线冷了,这章要不要安排一次有效触碰?")))
    if not items:
        items = [_item("关系线无冷却对")]
    return _dim("relation", items)


def _tension_dim(st, seq: int) -> dict:
    from scribe3.brief import tension_deterministic
    items = [_item(f"{t['detail']}——{t['fix']}", "nudge", _chat_action(f"张力项不达:{t['item']},{t['fix']}——聊聊?"))
             for t in tension_deterministic(st, seq) if not t["pass"]]
    if not items:
        items = [_item("确定性张力三项全过")]
    d = _dim("tension", items)
    # 前端 sparkline 数据:全书压力级序列(作者自标的目标节奏,窄查询,非 LLM 打分)
    try:
        from scribe3.brief import chapter_draft_text, parse_chapter_meta
        d["curve"] = [{"seq": c["seq"],
                       "pressure": (parse_chapter_meta(chapter_draft_text(c)) or {}).get("pressure")}
                      for c in st.chapters_lite()]
    except Exception:
        d["curve"] = []
    return d


def _causal_dim(st, seq: int) -> dict:
    n = st.causal_debt_total()
    if n > 0:
        return _dim("causal", [_item(f"因果欠账存量 {n} 条(事件缺动机/入因)", "nudge",
                                     _chat_action("因果欠账催收:哪几条该在本章还?"))])
    return _dim("causal", [_item("因果账本无欠账")])


def _quality_dim(st, seq: int) -> dict:
    # get_chapter 显式字段列表不含 qc_issues——仅 store 公共 API（P1-2 清零）
    ch = st.get_chapter_quality_fields(seq) or {}
    items: list[dict] = []
    ist = ch.get("ingest_status")
    if ist in ("failed", "parse_failed"):
        items.append(_item(
            f"本章反哺(ingest)未成功:{ch.get('ingest_error') or ist}——知识账本落后,后续章简报吃陈旧数据",
            "nudge", _chat_action("本章反哺失败了,帮我看看要不要手动重跑?")))
    qc = ch.get("qc_issues")
    qn = len(qc) if isinstance(qc, list) else (qc or 0)
    if qn:
        items.append(_item(f"确定性 QC 缓存命中 {qn} 处(存稿时自动检)", "nudge",
                           _chat_action("本章 QC 有命中,按清单过一遍?")))
    if not items:
        items = [_item("质量缓存干净")]
    return _dim("quality", items)


def _scene_dim(st, seq: int) -> dict:
    """经验压力 E2:场景动能 advisory 可见面(不进 blocking)。"""
    try:
        from scribe3.experience import exp_state
        from scribe3.experience.scene_grid import diagnose_scene_grid
        work = str(getattr(st, "db_name", None) or getattr(st, "db", None) or "main")
        g = exp_state.get_scene_grid(work, seq)
        issues = diagnose_scene_grid(g, seq=seq) if g else diagnose_scene_grid(None, seq=seq)
        hard = [i for i in issues if i.get("code") not in ("empty_grid",)]
        if not hard and issues:
            return _dim("scene", [_item("本场动能六格为空(默认不拦定稿)", "info")])
        if hard:
            return _dim("scene", [
                _item(i.get("message") or i.get("code"), "nudge",
                      _chat_action("本场 Scene–Sequel 断链,补反应/决定?"))
                for i in hard[:4]
            ])
        return _dim("scene", [_item("场景动能未见断链")])
    except Exception:
        return _dim("scene", [_item("场景动能未检", "info")], degraded=True)


_DIMS = (("promise", _promise_dim), ("arc", _arc_dim), ("relation", _relation_dim),
         ("tension", _tension_dim), ("causal", _causal_dim), ("quality", _quality_dim),
         ("scene", _scene_dim))


def chapter_pulse(st, seq: int) -> dict:
    dims = []
    for name, fn in _DIMS:
        try:
            dims.append(fn(st, seq))
        except Exception as e:
            _log.warning("pulse 维度 %s 失败(该维降级,其余照常): %s", name, e)
            dims.append(_dim(name, [_item(f"该维检测未跑成(没查≠没病):{str(e)[:60]}")], degraded=True))
    return {"seq": seq, "dimensions": dims}
