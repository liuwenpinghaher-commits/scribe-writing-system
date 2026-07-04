"""北极星方案任务8 · 章后复盘蒸馏(蓝图 §4-② 第2级,沉淀环)。

一章 ingest 后触发一次 LLM pass,对本章主编对话**只提取三类**:
决策及理由(decision)/ 用户纠偏(correction,最值钱)/ 踩过的坑(pitfall)。
产出结构化 lesson(非摘要全文):原子条目 + 适用条件(AutoGuide 条件→规则式,
禁无条件断言)+ 证据指针(chat turn id)。

两条铁律(蓝图):①蒸馏产物升格 craft_rule 必须待批,永不自动生效(升格动作
复用既有 s3_craft_rule_add 待批通道,本模块只产候选清单);②严格分家——
世界状态归本体(ingest 管),lesson 严禁复述"戊丢了信物"类事实(prompt 负例
few-shot + kind 白名单双防线,Mem0 先例)。

调研依据《2026-07-05-复盘蒸馏调研报告.md》五建议全采纳。
"""
from __future__ import annotations

import json
import logging

_log = logging.getLogger("scribe3.lesson")

LESSON_KINDS = ("decision", "correction", "pitfall")
DISTILL_MAX = 5          # 单章蒸馏条数上限(量控:lesson 无节制累加会稀释 brief 硬指令)
MERGE_SIM = 0.97         # 软去重自动合并线(P1门审查 P1-3 自 0.92 收紧:embedding 对否定
                         # 不敏感,反向纠偏会被 0.92 档旧课吞并反向强化;0.92-0.97 灰区
                         # 直接新增不合并;台账 D-017 更新)
RECALL_MIN_SIM = 0.48    # 召回相似度下限(bge-small-zh 真机标定:相关≥0.52/无关≤0.35,
                         # 台账 D-017;宁缺勿滥——Power of Noise)


def build_distill_prompt(messages: list[dict]) -> str:
    """蒸馏 prompt:三类枚举 + 原子条目 + 条件→规则 + 负例 few-shot(防世界状态越界)。"""
    lines = []
    for m in messages:
        role = "作者" if m.get("role") == "user" else "主编"
        lines.append(f"[{m.get('turn') or '?'}] {role}:{(m.get('text') or '')[:400]}")
    convo = "\n".join(lines[-80:])   # 只取最近 80 条,防超长
    return (
        "从下面这章的作者-主编对话里提取写作方法教训(lesson),只提取三类:\n"
        "- decision:做过的写法决策及理由(POV 选择/反转位置/节奏取舍)\n"
        "- correction:作者对 AI 的纠偏(最值钱——作者把 X 改成 Y,归纳成偏好规则)\n"
        "- pitfall:踩过的坑(什么写法被证明不行)\n"
        f"只输出 JSON 数组(最多 {DISTILL_MAX} 条),每条:\n"
        '{"kind":"decision"|"correction"|"pitfall","text":"一句话规则(原子,一条一个可执行结论)",'
        '"condition":"适用条件(什么场景下用,没有明确条件就留空)","evidence_turns":["turn id"]}\n'
        "硬规则:\n"
        "1. text 写成「条件→做法」式的可复用规则,禁止无条件的空泛断言;\n"
        "2. **严禁复述世界状态**(剧情事实/人物状态/世界观设定,如「戊丢了信物」「甲是卧底」)"
        "——那些归本体账本管,不是写作方法;对话里只有剧情讨论、没有方法教训时,返回空数组 [];\n"
        "3. 禁止摘抄对话原文,必须归纳改写;\n"
        "4. 拿不准算不算方法教训的,宁可不要。\n"
        f"对话记录:\n{convo}"
    )


def parse_distill(raw: str) -> list[dict]:
    """解析蒸馏输出;fail-soft:坏 JSON → [];kind 白名单(世界状态越界防线之二);
    条数上限截断。"""
    s = (raw or "").strip()
    i, j = s.find("["), s.rfind("]")
    if not (0 <= i < j):
        return []
    try:
        arr = json.loads(s[i:j + 1])
    except Exception:
        return []
    if not isinstance(arr, list):
        return []
    out: list[dict] = []
    for d in arr[:DISTILL_MAX]:
        if not isinstance(d, dict) or d.get("kind") not in LESSON_KINDS:
            continue
        text = str(d.get("text") or "").strip()
        if not text:
            continue
        out.append({"kind": d["kind"], "text": text[:200],
                    "condition": str(d.get("condition") or "")[:80],
                    "evidence_turns": [str(t) for t in (d.get("evidence_turns") or [])][:6]})
    return out


def distill_chapter(st, seq: int, complete_fn) -> dict:
    """对第 seq 章会话跑一次蒸馏并落库(带软去重)。挂 ingest 成功路径事件驱动
    (蓝图定死:不走 cron——cron 适合定时巡检,不适合章粒度事件)。
    fail-soft:LLM/落库任何故障只告警,绝不拖垮调用方(ingest 主链)。
    返回 {added, merged} 或 {skipped: 原因}。"""
    try:
        msgs = st.list_chat_messages(chapter=seq)
    except Exception as e:
        _log.warning("distill 拉会话失败(跳过): %s", e)
        return {"added": 0, "merged": 0, "skipped": "messages_unavailable"}
    if not msgs:
        return {"added": 0, "merged": 0, "skipped": "no_messages"}
    # P1门审查 P1-1:幂等标记——每次存稿都触发 ingest→蒸馏,同一段对话反复蒸馏会
    # 把 importance 虚增到升格阈(真机复现 3 次→4)且每次白烧一发长 prompt;
    # (消息数+最新 turn)未变即跳过。标记读写 fail-soft(挂了宁可多蒸不静默丢)。
    _count, _last = len(msgs), str(msgs[-1].get("turn") or msgs[-1].get("ts") or "")
    try:
        mk = st.get_distill_marker(seq)
        if mk and mk.get("msg_count") == _count and str(mk.get("last_turn") or "") == _last:
            return {"added": 0, "merged": 0, "skipped": "already_distilled"}
    except Exception as e:
        _log.warning("distill 幂等标记读取失败(照常蒸馏): %s", e)
    raw = complete_fn(build_distill_prompt(msgs))
    items = parse_distill(str(raw))
    added = merged = 0
    for it in items:
        try:
            if st.add_lesson(seq, it["kind"], it["text"], condition=it["condition"],
                             evidence_turns=it["evidence_turns"]):
                added += 1
            else:
                merged += 1
        except Exception as e:
            _log.warning("distill 落库单条失败(跳过该条): %s", e)
    try:
        st.set_distill_marker(seq, _count, _last)
    except Exception as e:
        _log.warning("distill 幂等标记写入失败(忽略): %s", e)
    return {"added": added, "merged": merged}


def render_lessons_section(last_lessons: list[dict], recalled: list[dict]) -> dict:
    """brief"上章复盘要点"段(蓝图 §4-② 反哺边①,软指令):上章蒸馏要点直取 +
    历史教训语义召回(k 小、有下限,宁缺勿滥——Power of Noise:相关但不适用比
    无关更毒)。全空 → text=""(不渲染)。"""
    parts: list[str] = []
    if last_lessons:
        lines = [f"- [{d['kind']}] {d['text']}"
                 + (f"(适用:{d['condition']})" if d.get("condition") else "")
                 for d in last_lessons[:3]]
        parts.append("【上章复盘要点】上一章沉淀的写作方法,本章适用则照做:\n" + "\n".join(lines))
    if recalled:
        lines = [f"- [{d['kind']}] {d['text']}"
                 + (f"(适用:{d['condition']})" if d.get("condition") else "")
                 for d in recalled[:3]]
        parts.append("【历史教训·语义召回】写过类似场景时的教训:\n" + "\n".join(lines))
    return {"text": "\n\n".join(parts), "count": len(last_lessons[:3]) + len(recalled[:3])}
