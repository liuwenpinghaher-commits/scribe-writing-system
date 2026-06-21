"""文学评改环(移植自 scribe_mcp,底座无关):8 维 rubric 打分 → 不达标则定向重写。
纯函数(build_*/parse)可离线单测;LLM 由调用方注入(complete_fn)。
"""
from __future__ import annotations

import json
import re

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
    if not worst and scores:
        worst = [k for k, _ in sorted(scores.items(), key=lambda x: x[1])[:2]]
    return {"scores": scores, "issues": issues, "worst_dims": worst,
            "overall": overall, "pass": bool(scores) and overall >= threshold}


# 每个薄弱维度的具体改写指令(逼模型真改,而非"尽量保留"导致原样返回)
_DIM_FIX = {
    "surprise": "加入一处不落俗套的反转/代价/信息差,打破顺滑预期",
    "emotion_truth": "把直说的情绪改成身体本能反应(指节发力/呼吸一滞/手停在半空),show 不 tell",
    "voice": "改掉不符人物身份/认知的书面语,换成该人物会用的口语",
    "anti_slop": "删掉套路微表情、空洞大词、万能比喻、重复句式(就是问题里点到的那些)",
    "texture": "换更新鲜具体的动词与意象,去掉平庸用词",
    "pace": "长短句交错,删去拖沓与赘述",
    "intent_resonance": "朝北极星的核心感受用力,别用治愈/圆满消解它",
    "coherence": "修正与设定/上文的矛盾,使信息自洽",
}


def build_revise_prompt(text: str, critique: dict) -> str:
    zh = {k: z for k, z, _ in RUBRIC}
    worst = critique.get("worst_dims") or _KEYS[:2]
    fixes = "\n".join(f"- {zh.get(k, k)}:{_DIM_FIX.get(k, '加强')}" for k in worst)
    issues = "；".join(critique.get("issues", [])[:5]) or "套路化、不够具体"
    return (
        "你是顶尖文学编辑,重写下面这段正文,把它从草稿改到能发表的水准。\n"
        f"**针对性大改这几处薄弱点(不是只换词,是放手改写对应段落):**\n{fixes}\n"
        f"**具体问题:**{issues}\n"
        "保留情节主线、人物、关键信息不变;但放手改写薄弱段落——加反转/代价、把情绪落到动作、"
        "换掉俗套与书面腔,show 不 tell、克制、有意外。\n"
        "只输出重写后的完整正文,不要解释,不要原样照抄原文。\n\n原文:\n" + text
    )


def critique_revise(text: str, reader_feeling: str, complete_fn,
                    max_rounds: int = 1, threshold: float = 3.5) -> dict:
    """评改环:critique → 定向重写 → **重新打分,只在真变好时采纳(取优,绝不退步)**,可多轮。"""
    def crit_of(t):
        return parse_critique(complete_fn(build_critique_prompt(t, reader_feeling)), threshold)
    best, best_crit = text, crit_of(text)
    first_overall = best_crit["overall"]
    rounds: list[dict] = [{"critique": best_crit, "revised_applied": False}]
    left = max(1, max_rounds)
    while not best_crit["pass"] and left > 0:
        left -= 1
        cand = complete_fn(build_revise_prompt(best, best_crit)).strip()
        if not cand or cand == best:
            break
        cand_crit = crit_of(cand)
        applied = cand_crit["overall"] > best_crit["overall"]   # 取优:重写真打赢才采纳
        rounds.append({"critique": cand_crit, "revised_applied": applied})
        if not applied:
            break                                               # 没赢即停,保留 best(原稿/上轮)
        best, best_crit = cand, cand_crit
    return {"final": best, "improved": best != text, "rounds": rounds,
            "first_overall": first_overall, "last_overall": best_crit["overall"]}
