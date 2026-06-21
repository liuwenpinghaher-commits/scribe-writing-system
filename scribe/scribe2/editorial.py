"""WaveC LLM 编辑功能:北极星偏离检测、全文体检生札记、决策方案生成、
素材提炼/蒸馏、全书分析(关系/事件/角色状态)。LLM 由 complete_fn 注入(便于测试)。
"""
from __future__ import annotations

import json
import re


def _pj(reply: str, default):
    m = re.search(r"\{.*\}|\[.*\]", reply or "", re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return default


def _prose(d, work, seq):
    ch = next((c for c in d.list_chapters(work) if c.get("seq") == seq), None)
    return d.latest_prose(d._idpart(ch["id"])) if ch else ""


def intent_check(d, work, seq, complete_fn) -> dict:
    intent = d.get_intent(work) or {}
    text = _prose(d, work, seq)
    if not text.strip():
        return {"status": "aligned", "reason": "本章暂无正文", "red_lines": []}
    prompt = (f"本书北极星(读者应感受到):{intent.get('reader_feeling', '')}\n"
              f"红线(绝不可破):{'；'.join(intent.get('red_lines') or [])}\n"
              "判断下面这章正文是否偏离北极星或触碰红线。\n"
              '只输出一行JSON:{"status":"aligned|soft_deviation|hard_violation",'
              '"reason":"简述","red_lines":["被触碰的红线",...]}\n\n正文:\n' + text[:3000])
    v = _pj(complete_fn(prompt), {"status": "aligned", "reason": "", "red_lines": []})
    # 前端契约:red_lines 为 [{text, level}]
    rls = [{"text": str(x), "level": "hard"} for x in (v.get("red_lines") or [])]
    return {"status": v.get("status", "aligned"), "reason": v.get("reason", ""),
            "red_lines": rls}


def proactive_review(d, work, complete_fn) -> int:
    chs = d.list_chapters(work)
    text = "\n\n".join(d.latest_prose(d._idpart(c["id"]))[:1500] for c in chs[-2:])
    if not text.strip():
        return 0
    rf = (d.get_intent(work) or {}).get("reader_feeling", "")
    prompt = (f"你是严苛主编。北极星:{rf}。审读最近正文,挑出最该提醒作者的问题"
              "(节奏/一致性/伏笔未收/人物声音/AI腔),每条给可执行建议。\n"
              '只输出JSON:{"insights":[{"summary":"问题","suggested_action":"建议",'
              '"severity":"info|warning|critical"},...]}\n\n正文:\n' + text)
    data = _pj(complete_fn(prompt), {"insights": []})
    n = 0
    for ins in (data.get("insights") or [])[:6]:
        d.add_insight(work, ins.get("summary", ""), ins.get("suggested_action", ""),
                      ins.get("severity", "info"))
        n += 1
    return n


def generate_options(d, work, decision_point, n, complete_fn) -> str:
    rf = (d.get_intent(work) or {}).get("reader_feeling", "")
    prompt = (f"北极星:{rf}。针对剧情决策点「{decision_point}」给 {n} 个走向不同的方案,"
              "每个含取舍与代价。\n"
              '只输出JSON:{"options":[{"id":"a","approach":"做法","tradeoff":"取舍",'
              '"emotional_direction":"情感走向","character_cost":"人物代价",'
              '"plot_consequence":"情节后果"},...]}')
    data = _pj(complete_fn(prompt), {"options": []})
    return d.add_option_set(work, {"text": decision_point}, (data.get("options") or [])[:n])


def process_material(d, mid, complete_fn) -> dict:
    m = d.s.get("material", mid)
    if not m:
        return {"summary": "", "tags": []}
    prompt = ("给下面素材做一句话摘要 + 3-5 个标签。\n"
              '只输出JSON:{"summary":"...","tags":["...",...]}\n\n素材:\n'
              + (m.get("content", "") or "")[:2000])
    data = _pj(complete_fn(prompt), {"summary": "", "tags": []})
    d.update_material(mid, {"title": data.get("summary", ""),
                            "tags": ",".join(data.get("tags") or []), "status": "processed"})
    return {"summary": data.get("summary", ""), "tags": data.get("tags") or []}


def distill_material(d, work, mid, target, complete_fn) -> dict:
    m = d.s.get("material", mid)
    if not m:
        return {"ok": False}
    if target == "setting":
        prompt = ("把下面素材提炼成一条小说设定(名称+描述)。\n"
                  '只输出JSON:{"name":"...","description":"..."}\n\n素材:\n'
                  + (m.get("content", "") or "")[:2000])
        data = _pj(complete_fn(prompt), {})
        if data.get("name"):
            d.add_setting(work, data["name"], data.get("description", ""))
    return {"ok": True}


def analyze(d, work, complete_fn) -> dict:
    chars = [c.get("name") for c in d.list_characters(work) if c.get("name")]
    rels = events = states = 0
    for ch in d.list_chapters(work):
        seq = ch.get("seq")
        text = d.latest_prose(d._idpart(ch["id"]))
        if not text.strip():
            continue
        prompt = (f"已知角色:{'、'.join(chars)}。从本章抽取:实体关系、关键事件、角色状态变化。\n"
                  '只输出JSON:{"relations":[{"src":"","dst":"","relation":""}],'
                  '"events":["事件"],"states":[{"character":"","state_desc":"","change_type":""}]}'
                  "\n\n正文:\n" + text[:2500])
        data = _pj(complete_fn(prompt), {})
        for r in (data.get("relations") or [])[:8]:
            if r.get("src") and r.get("dst"):
                d.add_relation(work, r["src"], r["dst"], r.get("relation", ""), valid_from_chapter=seq)
                rels += 1
        for e in (data.get("events") or [])[:6]:
            d.add_timeline_event(work, seq, str(e)); events += 1
        for s in (data.get("states") or [])[:6]:
            if s.get("character"):
                d.add_char_state(work, s["character"], seq, s.get("state_desc", ""),
                                 s.get("change_type", "")); states += 1
    return {"analyzed": True, "relations": rels, "events": events, "states": states}
