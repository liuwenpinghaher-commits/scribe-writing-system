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
        "保留情节主线、人物、关键信息不变。**外科式行改**:只动问题指向的那几句/段,其余原句尽量原样保留,"
        "别整段重写丢掉原有好句子。在这几处:加反转/代价、把情绪落到动作、换掉俗套与书面腔,show 不 tell、克制、有意外。\n"
        "只输出重写后的完整正文,不要解释,不要原样照抄原文。\n\n原文:\n" + text
    )


def build_compare_prompt(a: str, b: str, worst_dims: list | None = None) -> str:
    """成对比较 A/B(LLM 绝对打分噪声大,成对判断更可靠)。"""
    zh = {k: z for k, z, _ in RUBRIC}
    focus = "、".join(zh.get(k, k) for k in (worst_dims or [])) or "整体"
    return (
        f"下面是同一段小说正文的两个版本,B 是 A 的修订版。重点比较【{focus}】:"
        "B 是否真的比 A 更好(更具体、有意外、情绪落到动作、无俗套,且没丢掉 A 原有的优点)?\n"
        '只输出一行 JSON:{"verdict":"B_better|same|A_better","why":"一句话"}。\n\n'
        "A:\n" + a + "\n\nB:\n" + b
    )


def parse_compare(reply: str) -> str:
    m = re.search(r"\{.*\}", reply or "", re.S)
    if m:
        try:
            v = json.loads(m.group(0)).get("verdict", "")
            if v in ("B_better", "same", "A_better"):
                return v
        except Exception:
            pass
    return "same"   # 解析失败=保守判持平(不采纳)


def critique_revise(text: str, reader_feeling: str, complete_fn,
                    max_rounds: int = 1, threshold: float = 3.5) -> dict:
    """评改环(优化版):① 闸门看 critique 的**具体问题**(噪声小),不看噪声大的绝对分;
    ② 外科行改;③ 取优用**成对比较**(B 更好才采纳),绝不退步。可多轮。"""
    def crit_of(t):
        return parse_critique(complete_fn(build_critique_prompt(t, reader_feeling)), threshold)
    best, crit = text, crit_of(text)
    first_overall = crit["overall"]
    rounds: list[dict] = [{"critique": crit, "revised_applied": False}]
    left = max(1, max_rounds)
    while crit.get("issues") and left > 0:           # ① 有具体问题才改(不被噪声分逼着改)
        left -= 1
        cand = complete_fn(build_revise_prompt(best, crit)).strip()
        if not cand or cand == best:
            break
        verdict = parse_compare(complete_fn(build_compare_prompt(best, cand, crit.get("worst_dims"))))  # ③ 成对取优
        applied = verdict == "B_better"
        if applied:
            best = cand
            crit = crit_of(best)
        rounds.append({"critique": crit, "revised_applied": applied, "verdict": verdict})
        if not applied:
            break
    return {"final": best, "improved": best != text, "rounds": rounds,
            "first_overall": first_overall, "last_overall": crit["overall"]}


# ==== 生成后去重(规则治不了已生成文本的复读,确定性扫描+定向改写能拦)====
_PUNCT_ONLY = re.compile(r"^[，。！？、；：「」『』""''…—\-\d\s]+$")


def find_repetitions(text: str, n: int = 8, min_count: int = 3, top: int = 10) -> list[dict]:
    """确定性重复检测:找长度≥n、出现≥min_count 次的子串(去重叠,保留最长代表)。
    跨段复读是单遍长程生成的典型病——prompt 规则治不了已生成文本,确定性扫描才拦得住。"""
    from collections import Counter
    s = re.sub(r"\s+", "", text or "")
    if len(s) < n:
        return []
    grams = Counter(s[i:i + n] for i in range(len(s) - n + 1))
    cand = [(g, c) for g, c in grams.items() if c >= min_count and not _PUNCT_ONLY.match(g)]
    cand.sort(key=lambda x: (-x[1], -len(x[0])))
    chosen: list[tuple[str, int]] = []
    for g, c in cand:
        if any(g in cg for cg, _ in chosen):   # 已被更长代表覆盖,跳过
            continue
        chosen.append((g, c))
    return [{"phrase": g, "count": c} for g, c in chosen[:top]]


def build_dedup_prompt(text: str, reps: list[dict]) -> str:
    lst = "\n".join(f"· 「{r['phrase']}」(全篇约重复 {r['count']} 次)" for r in reps)
    return (
        "下面这段正文里,以下词句/句式在全篇机械【重复】,严重拉低文学质感:\n" + lst +
        "\n\n做一次外科式【去重】改写:每个重复意象/句式全篇最多留 2 次(最有力那处保留),"
        "其余改写成不同说法或删除;若两个场景结构雷同(如两次对峙),把后一次改出差异或合并。"
        "保持情节连贯、人物声音一致、字数基本不变。只输出改写后的完整正文,不要解释。\n\n【正文】\n" + text)


def revise_dedup(text: str, complete_fn, n: int = 8, min_count: int = 3, max_passes: int = 2) -> dict:
    """生成后去重通道:扫描复读→定向改写,循环至干净或到 max_passes(长章单遍不够)。守护改写过短则弃用。"""
    reps0 = find_repetitions(text, n=n, min_count=min_count)
    if not reps0:
        return {"text": text, "reps": [], "changed": False}
    cur, changed = text, False
    for _ in range(max_passes):
        reps = find_repetitions(cur, n=n, min_count=min_count)
        if not reps:
            break
        out = (complete_fn(build_dedup_prompt(cur, reps)) or "").strip()
        if len(out) < len(cur) * 0.6 or out == cur:   # 守护:改没了/没动→停
            break
        cur, changed = out, True
    return {"text": cur, "reps": reps0, "changed": changed}
