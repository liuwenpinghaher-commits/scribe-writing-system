"""移植自 scribe2/critique.py 的确定性 QC 纯函数(已验证资产)。

跨段复读/排比开头/单字断句/升华句——prompt 规则治不了已生成文本,确定性扫描+定向删才拦得住。
纯函数(无 DB/无网络),作渲染层质检兜底。语义级违规(双高潮/声音崩)是另一路(LLM 判官,后续)。
"""
import json
import re

_PUNCT_ONLY = re.compile(r"^[，。！？、；：「」『』“”‘’…—\-\d\s]+$")


def find_repetitions(text: str, n: int = 8, min_count: int = 3, top: int = 10) -> list[dict]:
    """长度≥n、出现≥min_count 次的子串(去重叠,保留最长代表)。跨段复读是单遍长程生成典型病。"""
    from collections import Counter
    s = re.sub(r"\s+", "", text or "")
    if len(s) < n:
        return []
    grams = Counter(s[i:i + n] for i in range(len(s) - n + 1))
    cand = [(g, c) for g, c in grams.items() if c >= min_count and not _PUNCT_ONLY.match(g)]
    cand.sort(key=lambda x: (-x[1], -len(x[0])))
    chosen: list[tuple[str, int]] = []
    for g, c in cand:
        if any(g in cg for cg, _ in chosen):
            continue
        chosen.append((g, c))
    return [{"phrase": g, "count": c} for g, c in chosen[:top]]


_EDGE = re.compile(r'^[\s"\'“”‘’「」『』,，、:：;；…—]+|[\s"\'“”‘’「」『』,，、:：;；…—]+$')
_HAS_CJK = re.compile(r'[一-鿿]')


def find_structural_repeats(text: str, min_anaphora: int = 4, max_short: int = 4) -> list[dict]:
    """排比开头(同3字开头≥min_anaphora句)+ 单字/极短断句滥用。字面 n-gram 查不到这些。"""
    from collections import Counter
    raw = re.split(r"[。！？\n]+", text or "")
    sents = [t for t in (_EDGE.sub("", s) for s in raw) if t]
    out: list[dict] = []
    openers = Counter(s[:3] for s in sents if len(s) >= 4 and not _PUNCT_ONLY.match(s[:3]))
    for op, c in openers.items():
        if c >= min_anaphora:
            out.append({"phrase": f"{op}…(排比开头)", "count": c, "kind": "anaphora"})
    short = [s for s in sents if 1 <= len(s) <= 2 and _HAS_CJK.search(s)]
    if len(short) > max_short:
        out.append({"phrase": "单字/极短断句(如 " + "/".join(short[:5]) + ")", "count": len(short), "kind": "short"})
    return sorted(out, key=lambda x: -x["count"])[:8]


_PURPLE_PATS = [
    r"原来[^。！？\n]{0,30}(就|早就|从一开始|没的选|没得选)",
    r"从[^,，。\n]{1,18}那一刻起",
    r"像[^。！？\n]{0,12}[滴颗][^。！？\n]{0,8}眼泪",
    r"影子[被]?拉得很[长短]",
    r"(有些|有的)[^。！？\n,，]{0,14}(就再也|再也)[^。！？\n]{0,14}",
    r"他知道[，,][^。！？\n]{0,4}(回不去|没的选|不一样了)",
    r"走下去|刀山火海",
]
_PURPLE_RE = [re.compile(p) for p in _PURPLE_PATS]


def find_purple_prose(text: str, extra_patterns: list[str] | None = None) -> list[dict]:
    """升华/抒情/主题直陈句:替读者下结论、硬塞命运隐喻——冷笔大忌。生成后扫描+删。
    通用正则跨题材;题材专属升华句经 extra_patterns 注入(来自 craft_rule purple_regex)。"""
    pats = list(_PURPLE_RE) + [re.compile(p) for p in (extra_patterns or [])]
    out: list[dict] = []
    for s in re.split(r"(?<=[。！？\n])", text or ""):
        st = s.strip()
        if st and any(rx.search(st) for rx in pats):
            out.append({"phrase": st[:30], "kind": "purple"})
    return out


# 通用 AI 腔硬检(E1/E2,题材无关,来自 hermes-novel hard-checks)
_NOT_A_BUT_B = re.compile(r"不是.{1,15}——是")


def find_ai_tics(text: str) -> list[dict]:
    """E1 破折号全章>5;E2「不是A——是B」句式(LLM 最常见的伪深刻制造器)。"""
    out: list[dict] = []
    dash = (text or "").count("——")
    if dash > 5:
        out.append({"kind": "em_dash", "count": dash})
    for m in _NOT_A_BUT_B.finditer(text or ""):
        out.append({"kind": "not_a_but_b", "phrase": m.group(0)})
    return out


def quality_flags(text: str, extra_patterns: list[str] | None = None) -> dict:
    """聚合四类确定性质检(渲染层兜底)。extra_patterns 来自本书 craft_rule purple_regex。"""
    return {
        "repetition": find_repetitions(text),
        "structural": find_structural_repeats(text),
        "purple": find_purple_prose(text, extra_patterns),
        "ai_tics": find_ai_tics(text),
    }


# ==== LLM 语义判官(纪律闸)——确定性检测的盲区:双高潮/声音崩/解说倾泻/知识泄露 ====
def build_discipline_prompt(text: str, brief: str = "", known: dict | None = None) -> str:
    kb = ""
    if known:
        lines = "\n".join(f"  · {who} 只知道:{('、'.join(facts[:8]) or '(仅其私密内核)')}"
                          for who, facts in known.items())
        kb = ("\n\n【各角色截至本章已知(判 knowledge_leak 的事实依据;角色说出此清单之外的他人私密=泄露)】\n"
              + lines)
    return (
        "你是叙事结构【纪律判官】。下面是一章志怪小说。本章的命题/纪律要求:\n" +
        (brief or "(默认:乱世铜炉式克制——单一戏剧主线、不偷跑后续章剧情、terse 角色不大段独白、不解说倾泻)") +
        "\n\n判定是否违反以下纪律(任一即违规):\n"
        "① double_climax:出现第二场打斗/救援/开挂,或偷跑了本不属于本章的后续剧情、凭空发明新登场角色;\n"
        "② voice_collapse:声细如蚊/半截就断的 terse 角色崩成大段流畅独白、系统结算音、或与主角同温;\n"
        "③ exposition_dump:大段身世/前史/规则的集中倾泻(本该零星渗出);\n"
        "④ knowledge_leak:某角色说出或表现出知晓【其视角不可能知道】的他人私密信息。\n"
        "若违规,找出正文里【复发/穿帮开始的前一句】(从这句之后整段都该砍掉),逐字填入 cut_after。\n"
        '只输出一行 JSON:{"ok": true/false, "violations": ["double_climax"...], "cut_after": "复发前最后一句的原文逐字,守纪则空"}。'
        + kb + "\n\n【正文】\n" + text)


def parse_discipline(reply: str) -> dict:
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        d = json.loads(m.group(0)) if m else {}
        return {"ok": bool(d.get("ok", True)), "violations": list(d.get("violations") or []),
                "cut_after": (d.get("cut_after") or "").strip()}
    except Exception:
        return {"ok": True, "violations": [], "cut_after": ""}   # 解析失败不阻断


def discipline_truncate(text: str, brief: str, complete_fn, known: dict | None = None) -> dict:
    """判定违规→复发点靠后(留≥40%)则截到复发点;复发太早只标记不砍(交回重生)。"""
    v = parse_discipline(complete_fn(build_discipline_prompt(text, brief, known)))
    if v["ok"] or not v["cut_after"]:
        return {"text": text, "violations": v["violations"], "changed": False}
    idx = text.find(v["cut_after"])
    if idx < 0:
        return {"text": text, "violations": v["violations"], "changed": False}
    cut = text[:idx + len(v["cut_after"])]
    if len(cut) < len(text) * 0.4:
        return {"text": text, "violations": v["violations"], "changed": False, "cut_after": v["cut_after"]}
    return {"text": cut, "violations": v["violations"], "changed": True}


# ==== 知识账本抽取(定稿时抽"本章谁新知道什么/做了什么",喂单一真相源)====
def build_knowledge_extract_prompt(prose: str) -> str:
    return (
        "读下面一章小说正文,抽取本章【各角色新知道了什么(learned)、做了什么且被谁看见(did)】——"
        "用于维护'谁知道什么'的知识账本(防后续章里某角色说出他视角不可能知道的信息)。\n"
        '只输出一行 JSON:{"learned":[{"who":角色名,"fact":新知道的事(短句)}],'
        '"did":[{"who":角色名,"action":所为(短句),"seen_by":[在场看见的角色名]}]}。\n\n'
        "【正文】\n" + prose)


def parse_knowledge_delta(reply: str) -> dict:
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        d = json.loads(m.group(0)) if m else {}
        return {"learned": list(d.get("learned") or []), "did": list(d.get("did") or [])}
    except Exception:
        return {"learned": [], "did": []}
