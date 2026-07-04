"""北极星方案任务6 · 章节目的合同(蓝图 §3-④,第四块拼图)。

定位:用户 OKR 直觉里可救的内核——目的分解出的不是分数,是"本章承诺改变的世界
状态清单(delta)",验"做没做"不验"好不好"。本体在此获得第四个岗位:合同登记处
与验收员(登记每章承诺的状态变化、预演可实现性、验收是否兑现)。

纯函数模块(读 store 只经调用方传入的 st),接线点:
- 登记校验:app PATCH /chapters + mcp s3_register_purpose(elicitation 待批)
- 写前预演:rehearse_delta(Sabre 准则:验证"信息通道存在",纯结构化零 LLM)
- 写后验收:/post-check fulfillment 段(结构类查库零噪声;认知类 LLM 三值判定
  ——FABLES 纪律:supported 必须带逐字引文;只进面板与 advisory,永不进 blocking)
- 结算:settle_purpose(achieved 置位/未达成 carried 滚下章/waived 终态防烂尾)
- 注入:brief 的"本章必达清单+上章滚入"段(空 delta 章不渲染,渐进采纳)
调研依据见《2026-07-05-目的合同调研报告.md》六建议。
"""
from __future__ import annotations

import json
import logging

_log = logging.getLogger("scribe3.purpose")

DELTA_KINDS = ("knowledge", "promise", "fact", "heat")
DELTA_STATUSES = ("planned", "achieved", "carried", "waived")
MAX_DELTAS = 7   # 调研建议6b:每章条数上限,超限=目的过载(纪律成本是头号生存风险)


def parse_deltas(raw) -> list[dict]:
    """章表 deltas 字段(JSON 串或 list)→ 规范化 list;坏数据 fail-soft 空。"""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "[]")
        except Exception:
            return []
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for d in raw:
        if not isinstance(d, dict) or d.get("kind") not in DELTA_KINDS:
            continue
        item = {"kind": d["kind"],
                "subject": str(d.get("subject") or ""),
                "predicate": str(d.get("predicate") or ""),
                "status": d.get("status") if d.get("status") in DELTA_STATUSES else "planned"}
        if d.get("ref"):
            item["ref"] = str(d["ref"])
        if d.get("carried_from") is not None:
            item["carried_from"] = int(d["carried_from"])
        out.append(item)
    return out


def validate_deltas(deltas: list[dict]) -> str | None:
    """条数量控(调研:合同过满是纪律失守前兆)。"""
    if len(deltas) > MAX_DELTAS:
        return (f"目的过载:deltas {len(deltas)} 条超上限 {MAX_DELTAS}"
                f"——拆到后续章,或把非必达项降为普通备忘")
    return None


def rehearse_delta(st, chapter: int, delta: dict, focalizer: str | None) -> str | None:
    """写前预演(蓝图:本体第一次在写之前对"该写什么"说出有内容的话——不是提议
    情节,是校验目的的可实现性)。只对 kind=knowledge 且带 ref 的正向获知目标预查:
    限知章读者视野≈焦点者视野,ref 为帧外私密 → 不可实现,写前报错。
    返回 None=可实现;str=报错文案。负向目标(仍不知)/无 ref/全知章不预演;
    预演基础设施故障 → 放行不拦(fail-open,预演是辅助不是闸门)。"""
    if delta.get("kind") != "knowledge" or not delta.get("ref"):
        return None
    if not focalizer or "不知" in (delta.get("predicate") or ""):
        return None
    try:
        facts = {f.id: f for f in st.facts_at(chapter)}
    except Exception as e:
        _log.warning("rehearse facts_at 失败(放行不拦): %s", e)
        return None
    f = facts.get(delta["ref"])
    if f is None:
        return (f"目的引用的事实 {delta['ref']} 本章尚未确立"
                f"——先登记该事实(或把 valid_from 提前),再挂此目的")
    if not getattr(f, "secret", False):
        return None   # 公开事实任何视角都可传达
    try:
        from scribe3.knowledge import project_frame
        frame = project_frame(st, focalizer, chapter)
    except Exception as e:
        _log.warning("rehearse project_frame 失败(放行不拦): %s", e)
        return None
    if frame.knows(f.id):
        return None
    return (f"目的「{delta.get('predicate')}」在当前限知结构下不可实现:焦点者 "
            f"{focalizer} 的知识帧不含私密 {delta['ref']}"
            f"——换 POV,或先安排 {focalizer} 的获知渠道")


def check_fulfillment_structural(st, seq: int, deltas: list[dict]) -> list[dict]:
    """结构类(promise/fact/heat 且带 ref)纯查库验收,零噪声;
    knowledge/无 ref → not_checkable(认知类由 LLM 针对性判定,只进 advisory)。
    已终态(achieved/waived)原样回显。"""
    out: list[dict] = []
    for d in deltas:
        if d.get("status") in ("achieved", "waived"):
            out.append({**d, "verdict": d["status"]})
            continue
        v = "not_checkable"
        ref = d.get("ref")
        try:
            if d["kind"] == "promise" and ref:
                touched = any((t.get("chapter") == seq)
                              for t in st.list_promise_touches(ref))
                if not touched:
                    p = next((x for x in st.list_promises() if x.get("id") == ref), None)
                    touched = bool(p and p.get("payoff_chapter") == seq)
                v = "achieved" if touched else "not_achieved"
            elif d["kind"] == "fact" and ref:
                v = "achieved" if any(f.id == ref for f in st.facts_at(seq)) else "not_achieved"
            elif d["kind"] == "heat" and ref and "|" in str(ref):
                a, b = str(ref).split("|", 1)
                ts = st.list_relation_touches(a, b) or []
                v = "achieved" if any(t.get("chapter") == seq for t in ts) else "not_achieved"
        except Exception as e:
            _log.warning("fulfillment 结构验收失败(fail-soft not_checkable): %s", e)
            v = "not_checkable"
        out.append({**d, "verdict": v})
    return out


def _extract_json(raw: str) -> str:
    s = (raw or "").strip()
    i, j = s.find("{"), s.rfind("}")
    return s[i:j + 1] if 0 <= i < j else "{}"


def judge_knowledge_delta(prose: str, delta: dict, complete_fn) -> dict:
    """认知类针对性 LLM 判定(聚焦二元比开放抽取可靠一个量级,蓝图 §3-④)。
    FABLES 纪律:supported 必须带逐字引文,引文非逐字 → 降级 not_enough_info;
    三值 supported/contradicted/not_enough_info(二值会把"部分传达"灰区硬塌缩);
    LLM 挂 → not_checkable(fail-open 不编造)。结果只进面板与 advisory(宪法)。"""
    prompt = (
        "只判断一件事:下面这段散文是否向读者传达了指定信息。\n"
        f"指定信息:{delta.get('predicate')}\n"
        '只输出一行 JSON:{"verdict":"supported"|"contradicted"|"not_enough_info",'
        '"evidence":"支持判断的原文引文(supported 时必填,逐字摘自散文)"}\n'
        "规则:没有逐字引文就不许判 supported;暗示过弱、需要读者大量脑补 → not_enough_info;"
        "散文明确否定了该信息 → contradicted。\n"
        f"散文:\n{prose[:6000]}"
    )
    try:
        raw = complete_fn(prompt)
        data = json.loads(_extract_json(str(raw)))
        verdict = data.get("verdict")
        if verdict not in ("supported", "contradicted", "not_enough_info"):
            return {"verdict": "not_checkable"}
        if verdict == "supported":
            ev = str(data.get("evidence") or "")
            if not ev or ev not in (prose or ""):
                return {"verdict": "not_enough_info",
                        "note": "引文缺失或非逐字,按 FABLES 纪律降级"}
            return {"verdict": "supported", "evidence": ev}
        return {"verdict": verdict}
    except Exception as e:
        _log.warning("judge_knowledge_delta LLM 失败(fail-open): %s", e)
        return {"verdict": "not_checkable"}


def settle_purpose(st, seq: int, results: list[dict]) -> dict:
    """写后结算(写库动作——/post-check 是 read-only,结算挂 loop pass finalize 与
    /ingest 成功路径)。achieved/supported → achieved;not_achieved/contradicted →
    carried 并复制进下一章合同(carried_from=seq,按 (kind,predicate) 幂等去重;
    下一章不存在则只标本章,brief 滚入段仍会展示);not_enough_info/not_checkable →
    保持原状(人工面板处置);waived 终态不复活。返回 {achieved, carried, total}。"""
    cur: list[dict] = []
    carried_new: list[dict] = []
    for r in results:
        d = {k: r[k] for k in ("kind", "subject", "predicate", "status") if k in r}
        for opt in ("ref", "carried_from"):
            if r.get(opt) is not None:
                d[opt] = r[opt]
        v = r.get("verdict")
        if d.get("status") == "waived":
            pass
        elif v in ("achieved", "supported"):
            d["status"] = "achieved"
        elif v in ("not_achieved", "contradicted"):
            d["status"] = "carried"
            carried_new.append({**d, "status": "carried", "carried_from": seq})
        cur.append(d)
    st.update_chapter_meta(seq, {"deltas": cur})
    if carried_new and st.get_chapter(seq + 1):
        nxt = parse_deltas((st.get_chapter(seq + 1) or {}).get("deltas"))
        existing = {(d.get("kind"), d.get("predicate")) for d in nxt}
        add = [d for d in carried_new if (d["kind"], d["predicate"]) not in existing]
        if add:
            st.update_chapter_meta(seq + 1, {"deltas": nxt + add})
    return {"achieved": sum(1 for d in cur if d["status"] == "achieved"),
            "carried": sum(1 for d in cur if d["status"] == "carried"),
            "total": len(cur)}


def render_purpose_section(deltas: list[dict], carried_prev: list[dict]) -> dict:
    """brief 注入段:本章必达清单(强于提醒文案,弱于 project_frame 物理裁剪)+
    上章未达成滚入(与因果欠账催收同渠道语气)。全空 → text=""(不渲染,渐进采纳)。"""
    parts: list[str] = []
    live = [d for d in deltas if d.get("status") in ("planned", "carried")]
    if live:
        lines = [f"- [{d['kind']}] {d['predicate']}"
                 + (f"(第{d['carried_from']}章滚入)" if d.get("carried_from") is not None else "")
                 for d in live]
        parts.append("【本章目的合同·必达清单】写完后逐条验收「做没做」,验的是状态变化不是好坏:\n"
                     + "\n".join(lines))
    if carried_prev:
        lines = [f"- [{d['kind']}] {d['predicate']}(第{d.get('carried_from', '?')}章起未达成)"
                 for d in carried_prev]
        parts.append("【上章未达成目的·滚入】本章优先兑现;确实不该做了就请作者置 waived(记原因),别让欠账烂尾:\n"
                     + "\n".join(lines))
    return {"text": "\n\n".join(parts), "count": len(live) + len(carried_prev)}
