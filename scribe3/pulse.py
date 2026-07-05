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


def _arc_dim(st, seq: int) -> dict:
    items: list[dict] = []
    for j in st.lie_belief_jumps(threshold=_ARC_JUMP_MAX):
        if j["chapter"] > seq:
            continue
        name = str(j["character_id"]).split(":")[-1]
        gap = j.get("gap") or 1
        move = abs(j["cur"] - j["prev"])
        if gap <= 1:
            # 相邻章大位移=顿悟太便宜(强信号 → decision)
            items.append(_item(
                f"弧光跳变:{name} 信奉度 第{j['prev_chapter']}章 {j['prev']} → 第{j['chapter']}章 {j['cur']}"
                f"(单章位移 {move} > {_ARC_JUMP_MAX},顿悟太便宜——补事件背书或摊到多章)",
                "decision", _chat_action(f"{name} 这次信念位移是不是太陡了?帮我看第{j['chapter']}章怎么补")))
        else:
            # 审查 P1-4:跨多章记录稀疏,可能是渐变——降 nudge,文案如实说跨章
            items.append(_item(
                f"弧光节奏留意:{name} 信奉度 第{j['prev_chapter']}→{j['chapter']}章(跨 {gap} 章)位移 {move}"
                f"——若中间无铺垫章,补一次刷新;有则忽略",
                "nudge", _chat_action(f"{name} 第{j['prev_chapter']}到{j['chapter']}章的信念变化衔接够吗?")))
    if not items:
        items = [_item("弧光节奏未见跳变")]
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
    # 审查 P1-6:get_chapter 显式字段列表不含 qc_issues(QC 分支曾恒死)——直查窄字段
    rows = st._query(
        "SELECT ingest_status, ingest_error, qc_issues FROM type::record('chapter',$seq)",
        {"seq": seq})
    ch = rows[0] if rows else {}
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


_DIMS = (("promise", _promise_dim), ("arc", _arc_dim), ("relation", _relation_dim),
         ("tension", _tension_dim), ("causal", _causal_dim), ("quality", _quality_dim))


def chapter_pulse(st, seq: int) -> dict:
    dims = []
    for name, fn in _DIMS:
        try:
            dims.append(fn(st, seq))
        except Exception as e:
            _log.warning("pulse 维度 %s 失败(该维降级,其余照常): %s", name, e)
            dims.append(_dim(name, [_item(f"该维检测未跑成(没查≠没病):{str(e)[:60]}")], degraded=True))
    return {"seq": seq, "dimensions": dims}
