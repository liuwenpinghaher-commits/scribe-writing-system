"""Private critique helpers."""
from __future__ import annotations

from scribe3.critique._common import *  # noqa: F403

def _th(key: str):
    """工艺阈值取值:设置中心热生效(DB→env→注册表默认)。"""
    from scribe3.settings import get_setting
    return get_setting(key)


def _is_allowed(phrase: str, allow: set[str] | None) -> bool:
    """phrase 是否属于"刻意母题/专名"白名单(含任一 allow 词即放行)。
    乱世铜炉式母题(奈何谷/镇煞钉/大元炼真经/三百六十…)本应跨章复现,不算懒惰复读。"""
    if not allow:
        return False
    return any(a and a in phrase for a in allow)


def _valid_rewrite(rw: str, sent: str) -> bool:
    """LLM 定向改写结果合法性校验:doubao 偶发混入英文占位词(如 someone)或元叙述/拒答前缀。
    改写不应引入原句没有的 ASCII 字母(中文正文异物);不应是解释/拒答。命中即弃用、保留原句。"""
    if re.search(r"[A-Za-z]", rw) and not re.search(r"[A-Za-z]", sent):
        return False
    if any(bad in rw for bad in ("抱歉", "无法", "作为", "以下是", "改写后", "这句话", "这一句")):
        return False
    return True


def _replace_whole_sentence(text: str, sent: str, rw: str) -> str:
    """只替换作为完整句出现的 sent(前为文首/句末标点/换行),避免命中更早长句的同形尾部子串
    (review P2-2)。仅替换第一处;找不到句界处的 sent 时原样返回,不误替换。"""
    m = re.search(r"(?:^|(?<=[。！？…\n]))" + re.escape(sent), text)
    if not m:
        return text
    return text[:m.start()] + rw + text[m.start() + len(sent):]


def _skip_gap(s: str, i: int) -> int:
    """跳过行内空白,若随后紧跟换行则再跳一次换行后的行首空白(移植自 JS skipGap)。"""
    n = len(s)
    while i < n and s[i] in " \t\r":
        i += 1
    if i < n and s[i] == "\n":
        i += 1
        while i < n and s[i] in " \t\r":
            i += 1
    return i


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """区间排序+合并为【有序、互不重叠】列表(供 _in_any_span 二分)。
    相交判定等价性:查询区间与"若干区间的并集"相交 ⟺ 与其中任一原区间相交,
    故合并不改变 _in_any_span 的判定结果,只是把病态文本(对话密集×命中密集)下的
    线性扫描 O(n²) 降为 O(log n) 每查询。"""
    if not spans:
        return []
    spans = sorted(spans)
    merged: list[tuple[int, int]] = [spans[0]]
    for s, e in spans[1:]:
        ls, le = merged[-1]
        if s <= le:
            if e > le:
                merged[-1] = (ls, e)
        else:
            merged.append((s, e))
    return merged


def _allow_spans(text: str, allow_words: set[str] | None) -> list[tuple[int, int]]:
    """allow_words 里每个词在 text 中的所有命中区间(finditer),供豁免判定用。
    出口经 _merge_spans 排序合并(满足 _in_any_span 的有序互不重叠前置条件)。"""
    if not allow_words:
        return []
    spans: list[tuple[int, int]] = []
    for w in allow_words:
        if not w:
            continue
        for m in re.finditer(re.escape(w), text):
            spans.append((m.start(), m.end()))
    return _merge_spans(spans)


def _in_any_span(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    """[start,end) 与 spans 中任一区间相交即返回 True(豁免路径:与 find_purple_prose
    的 extra_patterns 加法标记机制无关,这是独立的区间相交判定)。
    前置条件:spans 须为 _merge_spans 的产物(有序、互不重叠)——现有三处调用
    (find_ai_tics 的 _allow_spans、find_god_view/_degen_meta_leak 的 _quoted_ranges)
    均已满足。二分找"最右一个 s_start < end"的区间,唯一可能相交的候选。"""
    if not spans:
        return False
    i = bisect.bisect_left(spans, (end,)) - 1  # spans[i] 是最右一个 s_start < end
    return i >= 0 and spans[i][1] > start


def _split_paragraphs(text: str) -> list[str]:
    """段落切分:优先按空行(\\n\\n)切;全文无空行(单换行排版)时退化按 \\n 切——两种
    排版在渲染稿里都常见,不做正则近似,直接双策略回退(不产出空段)。"""
    s = text or ""
    paras = [p for p in s.split("\n\n") if p.strip()]
    if len(paras) <= 1:
        paras = [p for p in s.split("\n") if p.strip()]
    return paras


def _sentence_spans(text: str) -> list[tuple[str, int, int]]:
    """把 text 按句切,返回 [(去边缘后的句, start, end)]。
    start/end 指向原文里【去边缘后核心子串】的 [start,end),保证 text[start:end] == 句。"""
    out: list[tuple[str, int, int]] = []
    pos = 0
    for piece in re.split(r"([。！？\n]+)", text or ""):
        if not piece:
            continue
        if _SENT_SPLIT.fullmatch(piece):
            pos += len(piece)
            continue
        core = _EDGE.sub("", piece)
        if core:
            # core 是 piece 去掉首尾标点/空白后的子串;在 piece 内 find 得相对偏移
            rel = piece.find(core)
            if rel >= 0:
                out.append((core, pos + rel, pos + rel + len(core)))
        pos += len(piece)
    return out


def _structural_issues(text: str) -> list[dict]:
    """find_structural_repeats 的带 offset 展开:anaphora 逐句给 range,short 逐处给 range。"""
    flags = find_structural_repeats(text)
    if not flags:
        return []
    spans = _sentence_spans(text)
    issues: list[dict] = []
    for f in flags:
        kind = f.get("kind")
        if kind == "anaphora":
            opener = (f["phrase"].split("…")[0])[:3]
            for core, s, e in spans:
                if len(core) >= 4 and core[:3] == opener:
                    issues.append({
                        "type": "structural",
                        "message": f"结构重复:排比开头「{opener}…」出现 {f['count']} 次",
                        "text": core,
                        "range": [s, e],
                        "meta": {"count": f["count"], "kind": "anaphora"},
                    })
        elif kind == "short":
            for core, s, e in spans:
                if 1 <= len(core) <= 2 and _HAS_CJK.search(core):
                    issues.append({
                        "type": "structural",
                        "message": f"结构重复:单字/极短断句滥用(共 {f['count']} 处)",
                        "text": core,
                        "range": [s, e],
                        "meta": {"count": f["count"], "kind": "short"},
                    })
    return issues


def _ranges_overlap(a: list[int] | None, b: list[int] | None) -> bool:
    """标准半开区间相交判定([a0,a1) 与 [b0,b1) 有交集);任一侧为 None 视为不相交。"""
    if not a or not b:
        return False
    a0, a1 = a
    b0, b1 = b
    return a0 < b1 and b0 < a1


def _strip_quoted(text: str) -> str:
    """剥 7 对引号内片段(oh-story stripQuoted):台词/弹幕复沓是体裁常态,复读/排比只判叙述层。"""
    s = text or ""
    for rx in _QUOTED_SPANS:
        s = rx.sub("", s)
    return s


def _quoted_ranges(text: str) -> list[tuple[int, int]]:
    """7 对引号包裹片段在原文里的 [start,end) 区间(与 _strip_quoted 共用同一份
    _QUOTED_SPANS,只是不删字符、只记区间)。与 A3 的 _allow_spans 同为"区间列表"手法,
    供 find_god_view 判定命中是否落在台词/弹幕内——叙述层才算破 POV,人物台词里说
    "殊不知"只是口癖,不算上帝视角。"""
    s = text or ""
    spans: list[tuple[int, int]] = []
    for rx in _QUOTED_SPANS:
        for m in rx.finditer(s):
            spans.append((m.start(), m.end()))
    # 7 对正则各自命中可能交叠(如嵌套异种引号),出口排序合并,
    # 满足 _in_any_span 的有序互不重叠前置条件(二分判定)。
    return _merge_spans(spans)


def _strip_quoted_with_map(text: str) -> tuple[str, list[int]]:
    """_strip_quoted 的带 offset 映射版:返回 (剥引号后文本, 每个剩余字符在原 text 里的下标)。

    与 _strip_quoted 完全同序地逐个正则删除引号包裹片段(保证两者输出逐字一致),但同步
    维护"剩余字符→原始下标"映射——参照 locate_phrase 的"折叠字符+下标映射"手法,使
    在剥引号文本上定位到的区间可精确还原回原文 offset(混合行不再需要 find 兜底)。
    """
    chars = list(text or "")
    idxs = list(range(len(chars)))
    for rx in _QUOTED_SPANS:
        s = "".join(chars)
        keep = [True] * len(s)
        for m in rx.finditer(s):
            for i in range(m.start(), m.end()):
                keep[i] = False
        chars = [c for c, k in zip(chars, keep) if k]
        idxs = [i for i, k in zip(idxs, keep) if k]
    return "".join(chars), idxs


def _sentence_span(s: str, pos: int) -> tuple[int, int]:
    """pos 所在句的 [start,end)(以中文句号/叹问/换行为界)。"""
    st = pos
    while st > 0 and s[st - 1] not in _SENT_BOUND:
        st -= 1
    en = pos
    while en < len(s) and s[en] not in _SENT_BOUND:
        en += 1
    return st, min(en + 1, len(s))


