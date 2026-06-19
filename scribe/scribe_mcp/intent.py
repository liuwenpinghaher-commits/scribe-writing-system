"""偏离检测(P0-7)—— 判断一章是否偏离北极星/红线。

红线支持 hard/soft 分级;LLM 给裁决,parse_verdict 鲁棒解析(纯函数可单测)。
status:aligned(对齐)/ soft_deviation(软偏离)/ hard_violation(硬红线违反)。
"""
from __future__ import annotations

import json
import re

STATUSES = {"aligned", "soft_deviation", "hard_violation"}


def red_lines(intent: dict) -> list[dict]:
    """把 do_not_betray 归一化为 [{text, level}](字符串视为 hard)。"""
    raw = (intent or {}).get("do_not_betray") or "[]"
    try:
        items = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        items = []
    out: list[dict] = []
    for it in items or []:
        if isinstance(it, str) and it.strip():
            out.append({"text": it.strip(), "level": "hard"})
        elif isinstance(it, dict) and it.get("text"):
            lv = it.get("level", "hard")
            out.append({"text": str(it["text"]), "level": lv if lv in ("hard", "soft") else "hard"})
    return out


def build_prompt(intent: dict, content: str, red: list[dict]) -> str:
    lines = "\n".join(f"- [{r['level']}] {r['text']}" for r in red) or "(无)"
    return (
        "你是严格的责编。判断下面这章正文是否偏离作品的北极星与红线。\n"
        f"北极星(读者应感受到):{(intent or {}).get('reader_feeling', '') or '(未设定)'}\n"
        f"红线(hard=绝不可破;soft=尽量不破):\n{lines}\n\n"
        '只输出一行 JSON:{"status":"aligned|soft_deviation|hard_violation","reason":"一句话理由"}。\n\n'
        f"正文:\n{content}"
    )


def parse_verdict(text: str) -> dict:
    """从模型回复鲁棒抽取裁决;抽不到则按关键词回退,最终回退 aligned。"""
    m = re.search(r"\{.*?\}", text or "", re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            st = d.get("status")
            if st in STATUSES:
                return {"status": st, "reason": str(d.get("reason", ""))[:200]}
        except Exception:
            pass
    low = (text or "").lower()
    if "hard_violation" in low or "硬红线" in (text or "") or "违反红线" in (text or ""):
        return {"status": "hard_violation", "reason": (text or "")[:160]}
    if "soft_deviation" in low or "偏离" in (text or ""):
        return {"status": "soft_deviation", "reason": (text or "")[:160]}
    return {"status": "aligned", "reason": (text or "")[:160]}
