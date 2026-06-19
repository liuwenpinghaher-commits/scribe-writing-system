"""记忆与抽取(实现4 · C2-1/C2-4)—— 章摄取:一次 LLM 调用产出
摘要(memory_entries)+ 角色状态(char_states)+ 时间线(timeline_events)+ 关系(entity_relations)。

设计:写完一章后台调用,把"刚发生了什么"沉淀成可检索的结构化记忆,供后续章节注入(防久远遗忘/矛盾)。
纯解析 parse_ingest 可离线单测;LLM 调用由调用方注入 complete_fn。
"""
from __future__ import annotations

import json
import re


def build_ingest_prompt(seq: int, prose: str, char_names: list[str]) -> str:
    names = "、".join(char_names[:20]) or "(未登记)"
    return (
        f"你是小说的记忆抽取器。阅读第 {seq} 章正文,抽取关键事实。已登记角色:{names}。\n"
        '只输出一行 JSON:{"summary":"2-3句话本章梗概",'
        '"char_states":[{"name":"角色名","state":"该角色本章后的新状态/变化","change_type":"ability|relation|personality|status"}],'
        '"timeline":[{"description":"本章发生的关键事件","order":整数(本章内先后)}],'
        '"relations":[{"src":"实体A","dst":"实体B","relation":"关系(如 师徒/敌对/结盟)"}]}。\n'
        "只记真正发生的、对后续有影响的事;没有就给空数组。\n\n正文:\n" + prose
    )


def parse_ingest(reply: str) -> dict:
    """鲁棒解析章摄取 JSON。返回 {summary, char_states[], timeline[], relations[]}。"""
    out = {"summary": "", "char_states": [], "timeline": [], "relations": []}
    m = re.search(r"\{.*\}", reply or "", re.S)
    if not m:
        return out
    try:
        d = json.loads(m.group(0))
    except Exception:
        return out
    out["summary"] = str(d.get("summary", ""))[:500]
    for c in d.get("char_states") or []:
        if isinstance(c, dict) and c.get("name") and c.get("state"):
            out["char_states"].append({"name": str(c["name"]), "state": str(c["state"])[:200],
                                       "change_type": str(c.get("change_type", ""))[:20]})
    for t in d.get("timeline") or []:
        if isinstance(t, dict) and t.get("description"):
            order = t.get("order")
            out["timeline"].append({"description": str(t["description"])[:200],
                                    "order": int(order) if isinstance(order, (int, float)) else None})
    for r in d.get("relations") or []:
        if isinstance(r, dict) and r.get("src") and r.get("dst") and r.get("relation"):
            out["relations"].append({"src": str(r["src"]), "dst": str(r["dst"]),
                                     "relation": str(r["relation"])[:40]})
    return out


def ingest_chapter(db, complete_fn, work_id: str, seq: int) -> dict:
    """对一章做记忆抽取并落库(章摘要+角色状态+时间线+关系)。返回写入计数。"""
    ch = db.get_chapter(work_id, seq)
    if not ch:
        return {"ok": False}
    snaps = db.list_snapshots(ch["id"])
    prose = snaps[-1]["content"] if snaps else ""
    if not prose.strip():
        return {"ok": False}
    names = [c["name"] for c in db.list_characters(work_id)]
    data = parse_ingest(complete_fn(build_ingest_prompt(seq, prose, names)))
    if data["summary"]:
        db.upsert_memory(work_id, f"chapter:{seq}", data["summary"], source_chapter_range=str(seq))
    cnt = {"char_states": 0, "timeline": 0, "relations": 0}
    for c in data["char_states"]:
        ch_row = db.get_character_by_name(work_id, c["name"])
        if ch_row:
            db.add_char_state(ch_row["id"], seq, c["state"], c["change_type"])
            cnt["char_states"] += 1
    for t in data["timeline"]:
        db.add_timeline_event(work_id, seq, t["description"], t["order"])
        cnt["timeline"] += 1
    for r in data["relations"]:
        db.add_relation(work_id, r["src"], r["dst"], r["relation"], valid_from=seq)
        cnt["relations"] += 1
    rollup_global(db, complete_fn, work_id)
    return {"ok": True, "summary": data["summary"], **cnt}


def rollup_global(db, complete_fn, work_id: str) -> str:
    """把各章摘要滚动合并成全局梗概(scope=global),供写作注入。章数少时直接拼接。"""
    mems = db.list_chapter_memories(work_id)
    if not mems:
        return ""
    joined = "\n".join(f"第{m['seq']}章:{m['summary_text']}" for m in mems)
    if len(mems) <= 6:
        glob = joined  # 章少直接用,省一次 LLM
    else:
        prompt = ("把下面的分章梗概压缩成一段不超过 200 字的全书主线记忆"
                  "(保留人物关系、关键转折、未决悬念):\n\n" + joined)
        glob = complete_fn(prompt).strip()[:600]
    db.upsert_memory(work_id, "global", glob,
                     source_chapter_range=f"1-{mems[-1]['seq']}")
    return glob
