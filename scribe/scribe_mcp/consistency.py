"""门槛:规则版一致性自动校验(SCORE 符号状态 + 反平庸)。

写完一章自动跑(零 LLM,可离线验证),产出 consistency_flag(error_class 见 00 §5)。
当前规则:
  1) 符号状态矛盾:设定里 state∈{lost,destroyed} 的物品名,却出现在本章正文 → item_state_contradiction。
  2) 叙事风格:本章正文 high 级 AI 腔命中 → narrative_style(可作"写得不好"的门槛提示)。
LLM 级语义校验(OOC/因果断裂)由 ReviewAgent 另做(门槛1),此处只做可机检部分。
"""
from __future__ import annotations

import json
import re

from .antislop import detect
from .db import Database

# 00 §5 一致性错误类(19 类),供 LLM 深检归类
ERROR_CLASSES = [
    "时序矛盾", "因果断裂", "人物OOC", "视角越界", "命名不一致", "世界规则冲突",
    "物品状态矛盾", "地理矛盾", "能力前后不符", "关系矛盾", "时间线冲突", "数值矛盾",
    "知识越界", "设定违背", "伏笔遗忘", "情节重复", "硬伤(死而复生等)", "季节天气矛盾", "称谓矛盾",
]


def run_auto_check(db: Database, work_id: str, seq: int) -> list[str]:
    """返回新建 consistency_flag 的 id 列表。"""
    ch = db.get_chapter(work_id, seq)
    if not ch:
        return []
    snaps = db.list_snapshots(ch["id"])
    text = snaps[-1]["content"] if snaps else ""
    if not text:
        return []
    flags: list[str] = []

    # 规则1:符号状态矛盾(已遗失/损毁的物品再次出现)—— SCORE 思路
    for s in db.list_settings(work_id):
        if s["type"] != "item":
            continue
        try:
            st = json.loads(s["content"] or "{}").get("state")
        except Exception:
            st = None
        if st in ("lost", "destroyed") and s["name"] and s["name"] in text:
            flags.append(db.raise_consistency_flag(
                work_id, "item_state_contradiction", seq, "major",
                f"物品「{s['name']}」状态为 {st},却在第 {seq} 章再次出现",
                {"item": s["name"], "state": st}))

    # 规则2:叙事风格(high 级 AI 腔)
    highs = [h for h in detect(text) if h["severity"] == "high"]
    if highs:
        flags.append(db.raise_consistency_flag(
            work_id, "narrative_style", seq, "minor",
            f"第 {seq} 章检测到 {len(highs)} 处疑似 AI 腔(顿悟升华/情感直说等)",
            {"hits": [h["rule"] for h in highs]}))

    return flags


# ---- C2-2 LLM 深度一致性(19 类,需上下文)----
def build_deep_check_prompt(prose: str, context: str, seq: int) -> str:
    cls = "、".join(ERROR_CLASSES)
    return (
        f"你是小说连贯性审校。对照【已知设定与前情】,检查第 {seq} 章正文有无矛盾。\n"
        f"错误类别(只能从中选):{cls}。\n\n【已知设定与前情】\n{context or '(无)'}\n\n"
        f"【第 {seq} 章正文】\n{prose}\n\n"
        '只输出 JSON 数组,每个矛盾:{"error_class":"上面类别之一","severity":"critical|major|minor",'
        '"detail":"矛盾点+依据(引用冲突双方)"}。没有矛盾就输出 []。不要臆造,只报有据可查的。'
    )


def parse_deep_flags(reply: str) -> list[dict]:
    """解析深检 JSON 数组,过滤非法类别。"""
    m = re.search(r"\[.*\]", reply or "", re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    out = []
    for o in arr:
        if isinstance(o, dict) and o.get("error_class") in ERROR_CLASSES and o.get("detail"):
            sev = o.get("severity")
            out.append({"error_class": o["error_class"],
                        "severity": sev if sev in ("critical", "major", "minor") else "major",
                        "detail": str(o["detail"])[:300]})
    return out


def _deep_context(db: Database, work_id: str, seq: int) -> str:
    """装配深检所需上下文:全书记忆 + 人物状态 + 关系 + 设定(均截至上一章,防误判)。"""
    parts = []
    g = db.get_memory(work_id, "global")
    if g and g.get("summary_text"):
        parts.append("主线:" + g["summary_text"][:300])
    cs = []
    for c in db.list_characters(work_id)[:12]:
        st = db.get_char_state_at(c["id"], seq - 1)
        cs.append(f"{c['name']}" + (f"({st['state_desc'][:30]})" if st else ""))
    if cs:
        parts.append("人物:" + "、".join(cs))
    rels = db.list_relations(work_id, upto_seq=seq - 1)
    if rels:
        parts.append("关系:" + ";".join(f"{r['src_entity']}-{r['relation']}-{r['dst_entity']}" for r in rels[:10]))
    for s in db.list_settings(work_id)[:12]:
        try:
            desc = json.loads(s.get("content") or "{}").get("description", "")
        except Exception:
            desc = ""
        parts.append(f"设定·{s['name']}:{desc[:40]}" if desc else f"设定·{s['name']}")
    return "\n".join(parts)


def run_deep_check(db: Database, complete_fn, work_id: str, seq: int) -> list[str]:
    """LLM 深度一致性检查(19 类),产出 consistency_flag。返回新建 flag id 列表。"""
    ch = db.get_chapter(work_id, seq)
    if not ch:
        return []
    snaps = db.list_snapshots(ch["id"])
    prose = snaps[-1]["content"] if snaps else ""
    if not prose.strip():
        return []
    ctx = _deep_context(db, work_id, seq)
    found = parse_deep_flags(complete_fn(build_deep_check_prompt(prose, ctx, seq)))
    ids = []
    for f in found:
        ids.append(db.raise_consistency_flag(
            work_id, f["error_class"], seq, f["severity"], f["detail"], {"by": "llm_deep"}))
    return ids
