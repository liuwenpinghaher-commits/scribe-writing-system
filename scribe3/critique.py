"""移植自 scribe2/critique.py 的确定性 QC 纯函数(已验证资产)。

跨段复读/排比开头/单字断句/升华句——prompt 规则治不了已生成文本,确定性扫描+定向删才拦得住。
纯函数(无 DB/无网络),作渲染层质检兜底。语义级违规(双高潮/声音崩)是另一路(LLM 判官,后续)。
"""
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
    r"天地为炉|万物为铜|在炉[子火]?里",
    r"从[^,，。\n]{1,18}那一刻起",
    r"像[^。！？\n]{0,12}[滴颗][^。！？\n]{0,8}眼泪",
    r"影子[被]?拉得很[长短]",
    r"(有些|有的)[^。！？\n,，]{0,14}(就再也|再也)[^。！？\n]{0,14}",
    r"他知道[，,][^。！？\n]{0,4}(回不去|没的选|不一样了)",
    r"走下去|刀山火海",
]
_PURPLE_RE = [re.compile(p) for p in _PURPLE_PATS]


def find_purple_prose(text: str) -> list[dict]:
    """升华/抒情/主题直陈句:替读者下结论、硬塞命运隐喻——志怪冷笔大忌。生成后扫描+删。"""
    out: list[dict] = []
    for s in re.split(r"(?<=[。！？\n])", text or ""):
        st = s.strip()
        if st and any(rx.search(st) for rx in _PURPLE_RE):
            out.append({"phrase": st[:30], "kind": "purple"})
    return out


def quality_flags(text: str) -> dict:
    """聚合三类确定性质检(渲染层兜底)。"""
    return {
        "repetition": find_repetitions(text),
        "structural": find_structural_repeats(text),
        "purple": find_purple_prose(text),
    }
