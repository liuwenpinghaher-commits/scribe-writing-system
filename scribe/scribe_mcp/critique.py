"""文学评改环(内核3 · C1-3)—— 出稿后自评分→不达标则定向重写。

设计要点(内核3):评改在生成"之后、定稿之前"形成闭环,而非事后摆设。
- 8 维 rubric 打分(1–5);overall<阈值则触发一次定向 revise。
- 纯函数(build_*_prompt / parse_critique)可离线单测;LLM 调用由调用方注入(complete_fn),便于测试与换模型。
"""
from __future__ import annotations

import json
import re

# 8 维评改维度(key, 中文名, 说明)
RUBRIC: list[tuple[str, str, str]] = [
    ("texture", "文字质感", "用词新鲜、具体、有节奏,不平庸"),
    ("surprise", "意外性", "有不落俗套的转折/代价/信息差,非顺滑可预测"),
    ("emotion_truth", "情感真实", "情绪由动作细节呈现(show),非直说(tell)"),
    ("pace", "节奏", "张弛得当,长短句交错,不拖沓不赶"),
    ("voice", "角色声音", "对白/视角符合人物,不串味、不齐平"),
    ("anti_slop", "无AI腔", "无套路微表情/空洞大词/总结升华/万能比喻"),
    ("intent_resonance", "北极星共鸣", "能让读者感受到作者设定的核心感受"),
    ("coherence", "连贯", "与上文/设定不矛盾,信息自洽"),
]
_KEYS = [k for k, _, _ in RUBRIC]


def build_critique_prompt(text: str, reader_feeling: str = "") -> str:
    dims = "\n".join(f"- {k}({zh}):{desc}" for k, zh, desc in RUBRIC)
    nf = f"本书北极星(读者应感受到):{reader_feeling}\n" if reader_feeling else ""
    return (
        "你是严苛的文学编辑。给下面这段中文小说正文按 8 维各打 1–5 分(5 最好),"
        "并指出最该改的具体问题。\n" + nf + "维度:\n" + dims + "\n\n"
        '只输出一行 JSON:{"scores":{"texture":n,...8维全},"issues":["具体问题1",...],'
        '"worst_dims":["最差维度key",...]}。\n\n正文:\n' + text
    )


def parse_critique(reply: str, threshold: float = 3.5) -> dict:
    """解析评改 JSON;鲁棒兜底。返回 {scores, issues, worst_dims, overall, pass}。"""
    scores: dict[str, int] = {}
    issues: list[str] = []
    worst: list[str] = []
    m = re.search(r"\{.*\}", reply or "", re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            raw = d.get("scores", {}) or {}
            for k in _KEYS:
                v = raw.get(k)
                if isinstance(v, (int, float)):
                    scores[k] = int(round(v))
            issues = [str(x) for x in (d.get("issues") or [])][:8]
            worst = [str(x) for x in (d.get("worst_dims") or []) if x in _KEYS][:4]
        except Exception:
            pass
    overall = round(sum(scores.values()) / len(scores), 2) if scores else 0.0
    if not worst and scores:  # 没给 worst 就取最低 2 维
        worst = [k for k, _ in sorted(scores.items(), key=lambda x: x[1])[:2]]
    return {"scores": scores, "issues": issues, "worst_dims": worst,
            "overall": overall, "pass": bool(scores) and overall >= threshold}


def build_revise_prompt(text: str, critique: dict) -> str:
    zh = {k: z for k, z, _ in RUBRIC}
    weak = "、".join(zh.get(k, k) for k in critique.get("worst_dims", [])) or "薄弱处"
    issues = "；".join(critique.get("issues", [])[:5]) or "套路化、不够具体"
    return (
        f"下面这段正文在【{weak}】上较弱,具体问题:{issues}。\n"
        "请在保留情节、人物、信息不变的前提下定向重写,只改这些薄弱处,其余尽量保留。"
        "要求 show 不 tell、克制、具体、有意外性。只输出重写后的完整正文,不要解释。\n\n正文:\n" + text
    )


def critique_revise(text: str, reader_feeling: str, complete_fn,
                    max_rounds: int = 1, threshold: float = 3.5) -> dict:
    """评改环:critique → 不达标则 revise(至多 max_rounds 轮)。
    complete_fn(prompt)->str 由调用方注入(真实=_volc_complete,测试=桩)。
    返回 {final, improved, rounds:[{critique, revised_applied}], first, last}。"""
    rounds: list[dict] = []
    cur = text
    first_overall = None
    improved = False
    revises_left = max(1, max_rounds)
    while True:
        crit = parse_critique(complete_fn(build_critique_prompt(cur, reader_feeling)), threshold)
        if first_overall is None:
            first_overall = crit["overall"]
        entry = {"critique": crit, "revised_applied": False}
        rounds.append(entry)
        if crit["pass"] or revises_left <= 0:
            break
        revised = complete_fn(build_revise_prompt(cur, crit)).strip()
        if revised and revised != cur:
            cur = revised
            improved = True
            entry["revised_applied"] = True
            revises_left -= 1
            continue  # 复评改后的稿,得到真实新分
        break
    return {"final": cur, "improved": improved, "rounds": rounds,
            "first_overall": first_overall,
            "last_overall": rounds[-1]["critique"]["overall"] if rounds else 0.0}
