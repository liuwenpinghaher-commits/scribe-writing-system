"""移植自 scribe2/critique.py 的确定性 QC 纯函数(已验证资产)。

跨段复读/排比开头/单字断句/升华句——prompt 规则治不了已生成文本,确定性扫描+定向删才拦得住。
纯函数(无 DB/无网络),作渲染层质检兜底。语义级违规(双高潮/声音崩)是另一路(LLM 判官,后续)。
"""
import bisect
import bisect
import json
import logging
import re

_log = logging.getLogger("scribe3.critique")

_PUNCT_ONLY = re.compile(r"^[，。！？、；：「」『』“”‘’…—\-\d\s]+$")


def find_repetitions(text: str, n: int = 8, min_count: int = 3, top: int = 10) -> list[dict]:
    """长度≥n、出现≥min_count 次的子串(去重叠,保留最长代表)。跨段复读是单遍长程生成典型病。
    引号内(台词/弹幕)豁免——体裁正常形态,只判叙述层复读。"""
    from collections import Counter
    text = _strip_quoted(text)
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


def _cjk_ngrams(text: str, n: int) -> set[str]:
    """正文去空白后所有含中文的 n-gram 集合(用于跨文本逐字比对)。"""
    s = re.sub(r"\s+", "", text or "")
    return {s[i:i + n] for i in range(len(s) - n + 1)
            if re.search(r"[一-鿿]", s[i:i + n]) and not _PUNCT_ONLY.match(s[i:i + n])}


def _is_allowed(phrase: str, allow: set[str] | None) -> bool:
    """phrase 是否属于"刻意母题/专名"白名单(含任一 allow 词即放行)。
    乱世铜炉式母题(奈何谷/镇煞钉/大元炼真经/三百六十…)本应跨章复现,不算懒惰复读。"""
    if not allow:
        return False
    return any(a and a in phrase for a in allow)


def find_cross_chapter_repetitions(
    text: str, prior_texts: list[str], n: int = 8, top: int = 30,
    allow: set[str] | None = None,
) -> list[dict]:
    """新章中【逐字出现过在任一前文章节】的 ≥n 字独特子串(跨章复读)。

    单遍长程生成的典型病:模型在第 N 章自然复用自己偏爱的措辞/意象,而逐章 `find_repetitions`
    只扫单章内部、完全查不到这种跨章逐字搬运。这里把"新章 ∩ 前文"的逐字重叠揪出来——
    这是把"重复"从'事后逐章删'升级为'可跨章度量、可在生成时预防'的关键检测原语。

    allow:刻意母题/专名白名单——含其中任一词的短语放行(它们本应复现,不算懒惰复读),
    使指标只反映"动作/句式的偷懒重打",更贴近乱世铜炉对母题手法的纵容。

    返回去重叠后的最长代表短语 + 命中的前文章节序号(prior_idx,0-based)。
    """
    if not text or not prior_texts:
        return []
    new_grams = _cjk_ngrams(text, n)
    if not new_grams:
        return []
    prior_grams: dict[str, list[int]] = {}
    for idx, pt in enumerate(prior_texts):
        for g in _cjk_ngrams(pt, n):
            prior_grams.setdefault(g, []).append(idx)
    hits = [(g, prior_grams[g]) for g in new_grams
            if g in prior_grams and not _is_allowed(g, allow)]
    # 去重叠:长串优先,被它包含的短串丢弃,保留最长代表。
    hits.sort(key=lambda gv: (-len(gv[0]), gv[0]))
    chosen: list[tuple[str, list[int]]] = []
    for g, idxs in hits:
        if any(g in cg for cg, _ in chosen):
            continue
        chosen.append((g, idxs))
    return [{"phrase": g, "prior_chapters": idxs} for g, idxs in chosen[:top]]


def distinctive_phrases(text: str, n: int = 8, top: int = 40,
                        allow: set[str] | None = None) -> list[str]:
    """从一章正文里抽"独特措辞/意象"短语(≥n 字、含中文、剔标点),供下一章生成时作'避免逐字复用'清单。

    取每个起点的 n-gram 后做去重叠(保留较前出现的代表),再截断 top。这是源头预防的物料:
    把前文已用过的招式喂进写作 prompt,让模型在【生成时】就避开,而不是事后再删。
    allow:刻意母题/专名白名单——这些本应复现,不进"避免"清单(否则会逼模型回避母题、伤害质感)。
    """
    s = re.sub(r"\s+", "", text or "")
    seen: list[str] = []
    i = 0
    while i <= len(s) - n:
        g = s[i:i + n]
        if re.search(r"[一-鿿]", g) and not _PUNCT_ONLY.match(g) and not _is_allowed(g, allow):
            seen.append(g)
            i += n  # 跳过整段,避免相邻重叠 n-gram 刷屏
        else:
            i += 1
        if len(seen) >= top:
            break
    return seen


def cross_repetition_sentences(text: str, prior_texts: list[str], n: int = 8,
                               allow: set[str] | None = None) -> list[dict]:
    """定位本章中含【跨章逐字复读短语】的句子(定向改写目标)。
    与 find_cross_chapter_repetitions 同源,落到句子粒度。返回 [{sentence, phrases}]。"""
    hits = find_cross_chapter_repetitions(text, prior_texts, n=n, allow=allow)
    if not hits:
        return []
    phrases = [h["phrase"] for h in hits]
    sents = [s for s in re.split(r"(?<=[。！？\n])", text or "") if s.strip()]
    out: list[dict] = []
    for s in sents:
        cleaned = re.sub(r"\s+", "", s)
        hit = [p for p in phrases if p in cleaned]
        if hit:
            out.append({"sentence": s.strip(), "phrases": hit})
    return out


def rewrite_cross_repetitions(text: str, prior_texts: list[str], complete_fn,
                              n: int = 8, allow: set[str] | None = None) -> dict:
    """确定性事后跨章改写——系统哲学:'prompt 规则治不了已生成文本,确定性扫描+定向[改]才拦得住'。

    1) 确定性定位含跨章复读的句子;2) 逐句调 complete_fn 定向改写(换措辞/感官/句式,保意保限知);
    3) 字符串替换回原文。比'prompt 预防'可靠:不依赖模型记住上百条禁用词,只精准改犯规句。
    返回 {prose, rewritten, before, after}。complete_fn(prompt, system)->str。
    """
    before = len(find_cross_chapter_repetitions(text, prior_texts, n=n, allow=allow))
    targets = cross_repetition_sentences(text, prior_texts, n=n, allow=allow)
    if not targets:
        return {"prose": text, "rewritten": 0, "before": before, "after": before}
    new = text
    done = 0
    sys = ("你是小说定向改写器。只改写给你的这一句:保持原意、情节、限知视角、语气与上下文衔接完全不变,"
           "但**换一种措辞/感官/句式**,使其不再与前文逐字雷同。只输出改写后的这一句正文,不要引号、不要解释。")
    for t in targets:
        sent = t["sentence"]
        prompt = (f"前文已用过这些措辞(本句须避开逐字复用):{'、'.join(t['phrases'])}\n\n"
                  f"待改写的句子:{sent}")
        try:
            rw = (complete_fn(prompt, sys) or "").strip().strip('"“”')
        except Exception:
            rw = ""
        if rw and rw != sent and len(rw) >= 4:
            new = new.replace(sent, rw, 1)
            done += 1
    after = len(find_cross_chapter_repetitions(new, prior_texts, n=n, allow=allow))
    return {"prose": new, "rewritten": done, "before": before, "after": after}


_EDGE = re.compile(r'^[\s"\'“”‘’「」『』,，、:：;；…—]+|[\s"\'“”‘’「」『』,，、:：;；…—]+$')
_HAS_CJK = re.compile(r'[一-鿿]')


def find_structural_repeats(text: str, min_anaphora: int = 4, max_short: int = 4) -> list[dict]:
    """排比开头(同3字开头≥min_anaphora句)+ 单字/极短断句滥用。字面 n-gram 查不到这些。
    引号内(台词/弹幕)豁免——体裁正常形态,只判叙述层。"""
    from collections import Counter
    text = _strip_quoted(text)
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


LUANSHI_PURPLE_SEEDS = [
    r"原来[^。！？\n]{0,30}(就|早就|从一开始|没的选|没得选)",
    r"从[^,，。\n]{1,18}那一刻起",
    r"像[^。！？\n]{0,12}[滴颗][^。！？\n]{0,8}眼泪",
    r"影子[被]?拉得很[长短]",
    r"(有些|有的)[^。！？\n,，]{0,14}(就再也|再也)[^。！？\n]{0,14}",
    r"他知道[，,][^。！？\n]{0,4}(回不去|没的选|不一样了)",
    r"走下去|刀山火海",
]

_PURPLE_PATS = LUANSHI_PURPLE_SEEDS
_PURPLE_RE = [re.compile(p) for p in _PURPLE_PATS]


def find_purple_prose(text: str, extra_patterns: list[str] | None = None,
                      allow_patterns: list[str] | None = None) -> list[dict]:
    """升华/抒情/主题直陈句:替读者下结论、硬塞命运隐喻——冷笔大忌。生成后扫描+删。
    通用正则跨题材;题材专属升华句经 extra_patterns 注入(来自 craft_rule purple_regex,
    加法标记,越加越标红)。

    allow_patterns(方案B任务14):题材豁免正则,来自 craft_rule allow_pattern——前置
    skip 判定(减法),命中句匹配任一 allow 正则即放行不报。与 extra_patterns 彻底
    分离,绝不复用同一批正则(铁律:加法/减法两条独立路径)。
    """
    pats = list(_PURPLE_RE) + [re.compile(p) for p in (extra_patterns or [])]
    allow_pats = [re.compile(p) for p in (allow_patterns or [])]
    out: list[dict] = []
    for s in re.split(r"(?<=[。！？\n])", text or ""):
        st = s.strip()
        if not st or not any(rx.search(st) for rx in pats):
            continue
        if allow_pats and any(rx.search(st) for rx in allow_pats):
            continue  # 前置豁免:命中句落在题材别删清单里,不报
        out.append({"phrase": st[:30], "kind": "purple"})
    return out


# 通用 AI 腔硬检(E1/E2,题材无关,来自 hermes-novel hard-checks)
# E2「不是A——是B」结构性扫描,移植自 oh-story check-ai-patterns.js 的
# findNotIsComparisons/findPositiveFlipEnd——原正则 `不是.{1,15}——是` 只认破折号一种变体,
# 真实文本里"不是A而是B/不是A，是B/不是A。是B/不是A是B"同样是伪深刻制造器,须结构性扫。
_STOP_CHARS = set("。！？!?\n")
_SOFT_SEPARATORS = set("，,、；;：:")
_HARD_SEPARATORS = set("。.！!？?")
_MAX_NEGATIVE_SPAN = 80
_MAX_POSITIVE_SPAN = 80
# either-or「不是A就是B/也是B」里紧贴的"是"是连词的一部分,不是肯定项系动词;
# 也借此排掉「不是A,也不是B」这种第二个否定段(prev 为"也"时不算翻转)。
_COMPACT_EITHER_OR_PREV = set("不就也")
# 句尾语气/反问助词:"…,是吗/是吧/是嘛"是反问尾巴,不是否定后的肯定翻转。
_TAG_PARTICLES = set("吗吧嘛")
_TRAILING_NOISE = re.compile(r"[\s|\)）】\]]+$")

_WIKI_FLIPS = [
    ("bujin", re.compile(r"不仅[^。！？\n]{1,40}?(?:而且|还)[^。！？\n]{1,40}")),
    ("erfei", re.compile(r"[^。！？\n，,]{1,20}，?而非[^。！？\n]{1,20}")),
    ("yuqishuo", re.compile(r"与其说[^。！？\n]{1,40}?不如说[^。！？\n]{1,40}")),
]


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


def _find_positive_flip(candidate: str) -> tuple[int, str] | None:
    """在以"不是"开头的候选串里找肯定翻转点。返回 (候选串内结束下标, variant) 或 None。
    逐字符扫描,移植自 findPositiveFlipEnd(#166 假阳性坑验证过)。对 JS 的唯一主动扩展:
    compact 紧凑分支也查 TAG_PARTICLES(JS 只在软/硬分隔分支查),统一三分支的反问语气词
    口径——「这不是假的是吗」同样是反问尾巴,不该报 compact_shi。"""
    n = len(candidate)
    index = 2  # 跳过"不是"
    scanned = 0
    crossed_separator = False
    while index < n and scanned <= _MAX_NEGATIVE_SPAN:
        ch = candidate[index]

        if candidate[index:index + 2] == "而是":
            return index + 2, "compact_ershi"

        if ch in _SOFT_SEPARATORS:
            nxt = _skip_gap(candidate, index + 1)
            if candidate[nxt:nxt + 2] == "而是":
                return nxt + 2, "compact_ershi"
            if nxt < n and candidate[nxt] == "是" and (nxt + 1 >= n or candidate[nxt + 1] not in _TAG_PARTICLES):
                return nxt + 1, "soft_sep_shi"
            crossed_separator = True

        if ch in _HARD_SEPARATORS:
            nxt = _skip_gap(candidate, index + 1)
            if nxt < n and candidate[nxt] == "是" and (nxt + 1 >= n or candidate[nxt + 1] not in _TAG_PARTICLES):
                return nxt + 1, "hard_sep_shi"
            if ch != ".":
                break
            crossed_separator = True

        if ch in _STOP_CHARS:
            break

        # 首分句内的紧凑形式"不是A是B";跨分隔符后"只是/但是/还是/于是"的尾"是"是连词
        # 而非系动词(crossed_separator 挡掉),就/也 开头同理(either-or 惯用语排除)。
        if (ch == "是" and candidate[index - 1] not in _COMPACT_EITHER_OR_PREV
                and not crossed_separator
                and (index + 1 >= n or candidate[index + 1] not in _TAG_PARTICLES)):
            return index + 1, "compact_shi"

        index += 1
        scanned += 1

    return None


def _extract_flip_end(candidate: str, marker_end: int) -> int:
    """从翻转点向后扩到下一个 STOP_CHAR 或 MAX_POSITIVE_SPAN 上限(移植 extractFinding)。"""
    end = marker_end
    limit = min(len(candidate), marker_end + _MAX_POSITIVE_SPAN)
    while end < limit:
        if candidate[end] in _STOP_CHARS:
            break
        end += 1
    return end


def find_negation_flips(text: str) -> list[dict]:
    """否定翻转伪深刻句式:「不是A——是B」及其结构性变体(compact_ershi/soft_sep_shi/
    hard_sep_shi/compact_shi)+ 维基三变体(不仅…而且/而非/与其说…不如说)。

    移植自 oh-story check-ai-patterns.js 的 findNotIsComparisons——原正则只认
    破折号一种写法,真实生成文本里"不是A而是B/,是B/。是B/是B"同样是伪深刻制造器。
    结构性护栏(是不是反问/连词尾"是"/either-or/双重否定)照搬 JS 已验证语义,不是自造
    词表;唯一主动扩展见 _find_positive_flip(compact 分支也挡反问语气词)。
    report-only,不改文本;返回 offset 供前端定位。
    """
    s = text or ""
    struct_hits: list[dict] = []
    offset = 0
    n = len(s)
    while offset < n:
        start = s.find("不是", offset)
        if start < 0:
            break
        if start > 0 and s[start - 1] == "是":  # "是不是" 反问,跳过
            offset = start + 2
            continue
        candidate = s[start:]
        found = _find_positive_flip(candidate)
        if found is None:
            offset = start + 2
            continue
        marker_end, variant = found
        end = _extract_flip_end(candidate, marker_end)
        raw = _TRAILING_NOISE.sub("", candidate[:end])
        visible = re.sub(r"[\s，,。.！!?？、；;:：「」『』“”‘’…—\-（）()【】\[\]]", "", raw)
        if len(visible) >= 4:
            struct_hits.append({"variant": variant, "phrase": raw, "range": [start, start + len(raw)]})
        offset = start + max(len(raw), 2)

    out = list(struct_hits)
    for variant, pat in _WIKI_FLIPS:
        for m in pat.finditer(s):
            # 去重叠(仿 find_repetitions 惯例):维基宽正则若与结构扫描命中 range 相交,
            # 是同一处病灶(如「不仅…而且不是A是B」),保留更精确的结构命中,丢宽命中防虚增计数。
            if any(m.start() < h["range"][1] and h["range"][0] < m.end() for h in struct_hits):
                continue
            out.append({"variant": variant, "phrase": m.group(0), "range": [m.start(), m.end()]})

    return out


# ==== 方案A任务3:禁用词分级建表(来自 oh-story banned-words.md,已按归位纪律清洗)====
# 归位纪律:①比喻词(仿佛/如同/宛如/好似/犹如)不进表——已在 _SIMILE_WORDS,find_oversaturation 管;
# ②缓缓/微微/轻轻/淡淡 四个副词不进一级词表——它们走后续任务的密度检测,单次出现合法;
# ③不由得/不禁 保留进表(判断/心理类里的"轻度AI腔"信号)。
_BANNED_LEXICON: dict[str, tuple[str, ...]] = {
    "情态类": ("一丝", "一抹", "些许", "几分", "隐约"),
    "动作类": ("深吸一口气", "不禁"),
    "表情类": ("眼中闪过", "嘴角勾起", "眉头微皱", "眉眼低垂", "瞳孔微缩"),
    "心理类": ("心中一动", "心头一震", "心下了然", "心中暗道", "心底泛起", "不由得"),
    "判断类": ("不容置疑", "不容置喙", "不易察觉", "显而易见", "毫无疑问", "不可否认"),
    "形容类": ("闪烁着光芒", "狡黠", "深邃", "凛冽"),
    "过渡类": ("不由自主", "情不自禁", "自然而然"),
}
_CONTEXTUAL_WORDS = ("突然", "好像", "瞬间")   # 二级:仅密度超阈才报
_TOXIC_PATTERNS = [   # oh-story ★★★★/★★★ 毒句式(★★★★★否定翻转已由 find_negation_flips 承担)
    ("wandai", re.compile(r"[，,]带着(?:一种|一丝|几分)?[^，,。！？\n]{2,20}的[^，,。！？\n]{0,6}(?:力量|气息|意味)")),
    ("shengyin_buda", re.compile(r"声音不大[，,]却")),
    ("yanzhong_shanguo", re.compile(r"眼中闪过一丝[^，,。！？\n]{1,8}")),
    ("zuijiao_gouqi", re.compile(r"嘴角勾起一抹[^，,。！？\n]{1,8}")),
    ("xinzhong_yongqi", re.compile(r"心中涌起一股[^，,。！？\n]{1,8}")),
]

# ---- find_ai_tics 分级阈值(模块级命名常量,测试可引用)----
_BANNED_DENSITY_PER_K = 3.0   # banned_word 升 blocking 的千字密度阈值
_BANNED_MIN_SENTS = 3         # 升 blocking 还须命中分布在 ≥3 个不同句子(防单句 3+ 词击穿"密度"语义)
_CONTEXTUAL_PER_K = 1.5       # contextual_word 合计千字密度阈值
_CONTEXTUAL_MIN_HITS = 2      # contextual_word 至少命中处数(防极短文本分母失真)
_WANDAI_BLOCK_HITS = 2        # wandai 毒句式命中 ≥2 处时该类升 blocking

# banned_word 句子簇计数的句切分符(与协调审查口径一致:[。！？\n])
_AI_TIC_SENT_DELIM = re.compile(r"[。！？\n]")


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


def find_ai_tics(text: str, allow_words: set[str] | None = None) -> list[dict]:
    """AI 腔确定性检测,report-only,分级 blocking/advisory(密度阈值防单词误伤):

    - em_dash:全章破折号密度>2‰(原有,保持不动);
    - not_a_but_b:否定翻转伪深刻句式(原有,经 find_negation_flips,保持不动);
    - banned_word:一级禁用词表(7类,建表见 _BANNED_LEXICON)命中,allow_words 白名单豁免
      (与其在 allow_words 区间相交的命中放行);命中区间落在任一 toxic_pattern 区间内的
      丢弃(只留更完整的 toxic 一条代表,同 A1 惯例,且不计入密度/句子簇);升 blocking 须
      同时满足:千字总密度>_BANNED_DENSITY_PER_K 且命中分布在 ≥_BANNED_MIN_SENTS 个
      不同句子,否则 advisory;
    - contextual_word:二级词(突然/好像/瞬间)合计千字密度>_CONTEXTUAL_PER_K 且
      ≥_CONTEXTUAL_MIN_HITS 处才报,逐个给 range,advisory;
    - toxic_pattern:oh-story 毒句式命中即报 advisory;wandai 类命中≥_WANDAI_BLOCK_HITS
      处时该类全部升 blocking。
    """
    s = text or ""
    out: list[dict] = []
    dash = s.count("——")
    wc = len("".join(s.split()))
    if wc > 0 and dash * 1000 / wc > 2:
        out.append({"kind": "em_dash", "count": dash})
    for hit in find_negation_flips(s):
        out.append({"kind": "not_a_but_b", "phrase": hit["phrase"], "variant": hit["variant"]})

    # toxic_pattern 先算:banned_word 去重需要其区间(毒句式是更完整的病灶单位,
    # 「眼中闪过一丝狡黠」报一条 toxic 即可,其内部的 眼中闪过/一丝/狡黠 不再逐词重报)。
    toxic_by_name: dict[str, list[dict]] = {}
    for name, pat in _TOXIC_PATTERNS:
        for m in pat.finditer(s):
            toxic_by_name.setdefault(name, []).append({
                "kind": "toxic_pattern", "phrase": m.group(0), "pattern": name,
                "range": [m.start(), m.end()], "severity": "advisory",
            })
    toxic_spans = [(h["range"][0], h["range"][1])
                   for hits in toxic_by_name.values() for h in hits]

    # banned_word:一级词表;allow_words 豁免 + toxic 区间去重;密度×句子簇决定分级
    allow_spans = _allow_spans(s, allow_words)
    banned_hits: list[dict] = []
    for category, words in _BANNED_LEXICON.items():
        for w in words:
            for m in re.finditer(re.escape(w), s):
                if _in_any_span(m.start(), m.end(), allow_spans):
                    continue
                # 落在任一 toxic_pattern 区间内 → 丢弃(不上报,也不计入密度/句子簇)
                if any(t_s <= m.start() and m.end() <= t_e for t_s, t_e in toxic_spans):
                    continue
                banned_hits.append({
                    "kind": "banned_word", "phrase": w, "category": category,
                    "range": [m.start(), m.end()],
                })
    if banned_hits and wc > 0:
        density = len(banned_hits) * 1000 / wc
        # 短文本/单句护栏:密度公式对极短片段(如 /check 端点传入的编辑片段)分母过小
        # 恒超阈;且单句连中 3 词(AI 一句堆砌)也不构成跨文本的"密度现象"。
        # 取舍:升 blocking 须命中分布在 ≥_BANNED_MIN_SENTS 个【不同句子】(按 [。！？\n]
        # 切分)——比「命中总数≥3」更贴合意图(不可被单句击穿),比「wc≥500」不漏判
        # 400 字级真高密段落。
        delims = [m.start() for m in _AI_TIC_SENT_DELIM.finditer(s)]
        hit_sents = {bisect.bisect_left(delims, h["range"][0]) for h in banned_hits}
        severity = ("blocking"
                    if density > _BANNED_DENSITY_PER_K and len(hit_sents) >= _BANNED_MIN_SENTS
                    else "advisory")
        for h in banned_hits:
            h["severity"] = severity
        out.extend(banned_hits)

    # contextual_word:二级词,合计密度过阈值才报
    contextual_hits: list[dict] = []
    for w in _CONTEXTUAL_WORDS:
        for m in re.finditer(re.escape(w), s):
            contextual_hits.append({
                "kind": "contextual_word", "phrase": w,
                "range": [m.start(), m.end()], "severity": "advisory",
            })
    # 密度公式对极短文本(个位数字数)会因分母过小而失真——单次孤立出现不构成"密度"现象,
    # 至少要有 _CONTEXTUAL_MIN_HITS 处命中才谈得上密度超阈,防短文本单词误判。
    if (len(contextual_hits) >= _CONTEXTUAL_MIN_HITS and wc > 0
            and len(contextual_hits) * 1000 / wc > _CONTEXTUAL_PER_K):
        out.extend(contextual_hits)

    # toxic_pattern 上报:wandai 类 ≥_WANDAI_BLOCK_HITS 处升 blocking
    for name, hits in toxic_by_name.items():
        if name == "wandai" and len(hits) >= _WANDAI_BLOCK_HITS:
            for h in hits:
                h["severity"] = "blocking"
        out.extend(hits)

    return out


# 过度解释/过度饱和(留白引擎的确定性兜底;保守阈值,宁可漏不滥杀)
_EXPLAIN = ["这意味着", "也就是说", "换句话说", "正是因为", "说明了", "其实是", "无非是", "不过是", "正因如此"]
_EMO_LABEL = ["愤怒", "悲伤", "恐惧", "绝望", "痛苦", "欣喜", "喜悦", "忧伤", "焦虑", "孤独", "兴奋", "悲痛"]
_SIMILE_WORDS = ["仿佛", "如同", "宛如", "好似", "犹如"]            # 明确比喻词
_SIMILE_LIKE = re.compile(r"像[^,，。！？\n]{1,10}(一样|般|似的|似地)")  # "像…一样"精确模式,避开"好像/图像"


def find_oversaturation(text: str, per_k_explain: float = 3.0,
                        per_k_emo: float = 5.0, per_k_simile: float = 6.0) -> list[dict]:
    """过度解释/过度饱和检测(每千字密度超保守阈值)。留白引擎的确定性兜底。"""
    s = text or ""
    n = len("".join(s.split())) or 1
    k = n / 1000.0
    explain = sum(s.count(w) for w in _EXPLAIN)
    emo = sum(s.count(w) for w in _EMO_LABEL)
    simile = sum(s.count(w) for w in _SIMILE_WORDS) + len(_SIMILE_LIKE.findall(s))
    out: list[dict] = []
    for label, cnt, thr in (("explain", explain, per_k_explain),
                            ("emo_label", emo, per_k_emo),
                            ("simile", simile, per_k_simile)):
        if cnt / k > thr:
            out.append({"kind": label, "count": cnt, "per_k": round(cnt / k, 1)})
    return out


# ==== 方案A任务7:副词密度 + 句内三段式 + 同义词循环三检测器 ====
# 归位纪律(承接 A3 _BANNED_LEXICON 注释②):微微/淡淡/缓缓/轻轻 四个副词【不进】禁用词表
# ——单次出现是正常修辞,只有密度异常才是 AI 腔信号,故单独走密度检测,report-only。
_ADVERB_WORDS = ("微微", "淡淡", "缓缓", "轻轻")   # oh-story anti-ai-writing 模式2


def find_adverb_density(text: str, per_k_max: float = 3.0) -> dict | None:
    """副词密度检测(oh-story anti-ai-writing 模式2)。_strip_quoted 后按可见字数
    (_degen_visible_length,复用 A5 口径)计千字密度——单次出现合法,密度超阈才报;
    未超阈或全文无命中返回 None(report-only,advisory 性质)。"""
    s = _strip_quoted(text or "")
    wc = _degen_visible_length(s)
    if wc == 0:
        return None
    words: dict[str, int] = {w: c for w in _ADVERB_WORDS if (c := s.count(w)) > 0}
    count = sum(words.values())
    if count == 0:
        return None
    per_k = count * 1000 / wc
    if per_k <= per_k_max:
        return None
    return {"words": words, "per_k": round(per_k, 2), "count": count}


# 句内顿号三连(维基 rule of three):恰好三项 X、Y、Z(每项 1-6 字)。
# 实现是"先全局切分再判长度",不是局部正则近似——负向环视 (?<!、) 只能保证起点前
# 一字不是顿号,不能保证起点对齐分项边界(多字词场景被击穿:「院里安静、破败、荒凉、
# 死寂。」曾从"破败"第二个字起匹配出「败、荒凉、死寂」,把半个词冒充分项,使四项
# 列举被误报,污染密度门)。全局切分:句读([。！？\n])切句,句内再按逗号/分号切段
# (顿号列表止于逗号,「他带上刀、粮、水，然后出发」逗号前是完整候选序列),每段
# 完整 split("、") 后 len(items)==3 且每项 1-6 字才命中——≥4 项、2 项、超长项都
# 整体不报,不存在"从列表中间截出伪三连"的起点。
_RULE_OF_THREE_SEG_RE = re.compile(r"[^。！？\n，,；;]+")   # 句读+逗号/分号界定的候选段
_RULE_OF_THREE_ITEM_MAX = 6   # 每分项最大字数(超长项是正常叙述,不是排比分项)


def find_rule_of_three(text: str) -> list[dict]:
    """句内三段式(维基 rule of three)检测:恰好三项顿号并列(全局切分判定,见上方
    模块注释)。引号内(台词/弹幕)豁免——体裁正常形态,只判叙述层;range 覆盖三项
    整体(段内去空白后的起止)。report-only,不做密度门(密度门在 quality_flags/
    quality_issues 聚合处实现,见 _rule_of_three_gated)。"""
    s = text or ""
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    for m in _RULE_OF_THREE_SEG_RE.finditer(s):
        seg = m.group(0)
        if "、" not in seg:
            continue
        core = seg.strip()
        items = core.split("、")
        # 恰好三项、每项非空且 1-6 字:≥4 项是铺陈列举,2 项是普通并列,均不报;
        # 任一项超长(如首项带主语状语的长叙述)说明这不是干净的排比分项,也不报。
        if len(items) != 3 or not all(1 <= len(it) <= _RULE_OF_THREE_ITEM_MAX for it in items):
            continue
        start = m.start() + seg.find(core)
        end = start + len(core)
        if _in_any_span(start, end, quoted):
            continue
        out.append({"phrase": core, "range": [start, end]})
    return out


# rule_of_three 报告门:单句偶尔三连打比方是正常修辞,只有千字密度超阈才谈得上
# "句内三段式滥用"这一 AI 腔信号——故聚合层(quality_flags/quality_issues)只有
# 密度 >_RULE_OF_THREE_GATE_PER_K 才整体上报,否则该章不计入(见 _rule_of_three_gated)。
_RULE_OF_THREE_GATE_PER_K = 2.0


def _rule_of_three_gated(text: str) -> list[dict]:
    """find_rule_of_three 的报告门:命中千字密度(可见字数口径)须 >_RULE_OF_THREE_GATE_PER_K
    才整体上报,否则返回空列表(单次修辞合法,密度才是信号)。"""
    hits = find_rule_of_three(text)
    if not hits:
        return []
    wc = _degen_visible_length(_strip_quoted(text or "")) or 1
    per_k = len(hits) * 1000 / wc
    return hits if per_k > _RULE_OF_THREE_GATE_PER_K else []


# 同义词循环/精致变异(维基 elegant variation):角色被点名后,后文频繁改用"那男人/
# 少年"等泛称替换指代,过犹不及的"避免重复"手法。泛称表刻意只收 2 字以上的确定性
# 词——不收单字词或过泛词如"男人/女人"(会子串误报,如"那男人"里已含"男人")。
_GENERIC_REFS = ("那男人", "那女人", "少年", "青年", "老者", "主人公", "主角")


def find_elegant_variation(text: str, names: list[str], window: int = 200) -> list[dict]:
    """同义词循环检测(确定性近似,维基 elegant variation/同义词轮换)。对每个 name 的
    每次出现,查其后 window 字符内是否出现 ≥2 个【不同】泛称 → 报命中;同一 name 多次
    出现只报首个触发的一处(去噪,避免同一角色刷屏)。report-only。

    引号豁免(A7-Important 尾巾修复,原实现是模块里唯一不做引号豁免的检测器):
    ①name 本身若落在引号内(台词里提及其名)不作为触发锚点——台词里说出角色名不算
    叙述层"点名"; ②窗口内的泛称若落在引号内(如台词「那男人到底是谁?」里的泛称
    是角色的疑问用词,不是叙述者刻意避重复换用的同义词)不计入 aliases。两处都用
    _quoted_ranges(text) 判定,与模块内其余检测器(find_god_view/find_rule_of_three
    等)同一套引号区间口径。"""
    s = text or ""
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    for name in names or []:
        if not name:
            continue
        for m in re.finditer(re.escape(name), s):
            if _in_any_span(m.start(), m.end(), quoted):
                continue  # name 本身在引号内(台词提及),不作为触发锚点
            window_text = s[m.end():m.end() + window]
            aliases = []
            for g in _GENERIC_REFS:
                for gm in re.finditer(re.escape(g), window_text):
                    abs_start, abs_end = m.end() + gm.start(), m.end() + gm.end()
                    if not _in_any_span(abs_start, abs_end, quoted):
                        aliases.append(g)
                        break  # 该泛称找到一处不落引号内的出现即计入,不重复计数
            if len(aliases) >= 2:
                out.append({"name": name, "aliases": aliases, "range": [m.start(), m.end()]})
                break  # 同一 name 多次命中只报首处
    return out


def quality_flags(text: str, extra_patterns: list[str] | None = None,
                  allow_words: set[str] | None = None,
                  allow_patterns: list[str] | None = None) -> dict:
    """聚合十类确定性质检(渲染层兜底)。extra_patterns 来自本书 craft_rule purple_regex;
    allow_words 为禁用词白名单(世界观术语/专名豁免,per-work 接线见后续任务),透传给 find_ai_tics。
    allow_patterns(方案B任务14):题材豁免正则,来自本书 craft_rule allow_pattern,前置
    skip 判定(减法),透传给 find_purple_prose——与 extra_patterns 的加法标记路径分离。

    注意:"rhythm"/"adverb" 两键与其余八键类型不同——其余键均为**命中列表**(list[dict],
    空列表=无命中,调用方惯用 len() 计数);"rhythm" 是 find_rhythm_uniformity 的返回值,
    类型为 **dict(判定结果) 或 None(句数不足未判)**;"adverb" 是 find_adverb_density 的
    返回值,类型为 **dict(超阈命中详情) 或 None(未超阈/无命中)**。对 quality_flags 结果做
    "逐键当 list 处理"(len()/迭代)的调用方须显式排除或跳过这两键(现有消费点均按显式键名
    取值,未见通配遍历,不受影响;新增消费方引入前先 grep quality_flags 确认)。

    "rule_of_three" 键经密度报告门(_rule_of_three_gated):单次三连合法,只有千字密度
    超 _RULE_OF_THREE_GATE_PER_K 才整体上报,否则该章返回空列表——与其余"命中即入列"
    键的语义略有差异,调用方按空列表=无问题的既有惯例读取即可,无需特殊处理。

    "elegant_variation"(同义词循环)因需要角色名单,纯函数层拿不到,不在此聚合——
    接线在 scribe3/app.py 的 /post-check(取 store 角色上下文后调用 find_elegant_variation),
    仅并入 issues,不进 quality_flags。"""
    return {
        "repetition": find_repetitions(text),
        "structural": find_structural_repeats(text),
        "purple": find_purple_prose(text, extra_patterns, allow_patterns),
        "ai_tics": find_ai_tics(text, allow_words),
        "oversaturation": find_oversaturation(text),
        "god_view": find_god_view(text),
        "degeneration": find_degeneration(text),
        "rhythm": find_rhythm_uniformity(text),
        "adverb": find_adverb_density(text),
        "rule_of_three": _rule_of_three_gated(text),
    }


# ==== 护栏可操作性:问题定位到句(F-05) ====

def locate_phrase(text: str, phrase: str, max_hits: int = 20) -> list[tuple[int, int]]:
    """在原始 text 里定位"去空白后等于 phrase"的所有片段,返回含空白原文的 [start,end)。

    phrase 来自 find_repetitions 等(已去空白);text 含空白/换行。
    做法:把 text 折成"去空白字符序列 + 各字符的原始下标映射",在去空白序列上 str.find,
    再用映射把命中区间还原回原始 text 的 [start, end)。
    """
    if not phrase or not text:
        return []
    stripped_chars: list[str] = []
    orig_idx: list[int] = []  # stripped_chars[i] 在原始 text 的下标
    for i, ch in enumerate(text):
        if not ch.isspace():
            stripped_chars.append(ch)
            orig_idx.append(i)
    stripped = "".join(stripped_chars)
    plen = len(phrase)
    if plen == 0 or len(stripped) < plen:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    while len(out) < max_hits:
        j = stripped.find(phrase, start)
        if j < 0:
            break
        s = orig_idx[j]
        e = orig_idx[j + plen - 1] + 1  # 闭区间末字符 +1 → 半开
        out.append((s, e))
        start = j + 1
    return out


def quality_issues(text: str, extra_patterns: list[str] | None = None,
                   allow_words: set[str] | None = None,
                   allow_patterns: list[str] | None = None) -> list[dict]:
    """六类 QC 的"带 offset"展开形式(与 quality_flags 并存)。
    仅对"白送类"(finditer 直接给 offset)和"去空白 n-gram 可 locate_phrase"的类别补 range。
    返回结构: {type, message, text, range:[start,end], meta}。
    range 为 None 表示无法定位(前端兜底用 text.indexOf 回退)。
    allow_words:禁用词白名单,透传给 find_ai_tics 的 banned_word 豁免。
    allow_patterns(方案B任务14):题材豁免正则,前置 skip 判定(减法),命中句匹配即
    从 purple 一类里放行不报——与 extra_patterns 加法路径分离。
    """
    issues: list[dict] = []
    s = text or ""

    # ① AI 腔 · not_a_but_b — 白送:find_negation_flips 直接给 offset
    for hit in find_negation_flips(s):
        issues.append({
            "type": "ai_tics",
            "message": "AI腔:否定翻转伪深刻句式(不是A——是B 及变体)",
            "text": hit["phrase"],
            "range": hit["range"],
            "meta": {"kind": "not_a_but_b", "variant": hit["variant"]},
        })

    # ② AI 腔 · em_dash — 密度超阈值才报,逐个给 offset
    dash = s.count("——")
    wc = len("".join(s.split()))
    if wc > 0 and dash * 1000 / wc > 2:
        for m in re.finditer("——", s):
            issues.append({
                "type": "ai_tics",
                "message": "AI腔:破折号过密",
                "text": "——",
                "range": [m.start(), m.end()],
                "meta": {"kind": "em_dash"},
            })

    # ②b AI 腔 · banned_word/contextual_word/toxic_pattern — 建表分级命中,白送 offset
    _ai_tics_msg = {
        "banned_word": "AI腔:禁用词命中",
        "contextual_word": "AI腔:高频套语密度过高",
        "toxic_pattern": "AI腔:毒句式命中",
    }
    for hit in find_ai_tics(s, allow_words):
        kind = hit["kind"]
        if kind not in _ai_tics_msg:
            continue  # em_dash/not_a_but_b 已在①②处理,避免重复
        category = hit.get("category")
        msg = _ai_tics_msg[kind] + (f"({category})" if category else "")
        issues.append({
            "type": "ai_tics",
            "message": msg,
            "text": hit["phrase"],
            "range": hit["range"],
            "meta": {k: v for k, v in hit.items() if k not in ("range", "phrase")},
        })

    # ③ 升华 · purple — 整句 locate,逐句给 offset
    pats = list(_PURPLE_RE) + [re.compile(p) for p in (extra_patterns or [])]
    allow_pats = [re.compile(p) for p in (allow_patterns or [])]
    for sent in re.split(r"(?<=[。！？\n])", s):
        st = sent.strip()
        if not st:
            continue
        if any(rx.search(st) for rx in pats):
            if allow_pats and any(rx.search(st) for rx in allow_pats):
                continue  # 前置豁免:命中句落在题材别删清单里,不报
            # 用 locate_phrase 在原文找整句起止(去空白后匹配)
            phrase_key = re.sub(r"\s+", "", st)
            hits = locate_phrase(s, phrase_key, max_hits=1)
            rng = list(hits[0]) if hits else None
            issues.append({
                "type": "purple",
                "message": "升华/抒情:替读者下结论",
                "text": st,
                "range": rng,
                "meta": {"kind": "purple"},
            })

    # ④ 复读(章内)— 去空白 n-gram,用 locate_phrase 找第一处出现(MVP 只标第一处)
    for r in find_repetitions(s):
        hits = locate_phrase(s, r["phrase"], max_hits=1)
        rng = list(hits[0]) if hits else None
        issues.append({
            "type": "repetition",
            "message": f"复读:此措辞出现 {r['count']} 次",
            "text": s[rng[0]:rng[1]] if rng else r["phrase"],
            "range": rng,
            "meta": {"count": r["count"]},
        })

    # ⑤ 结构重复 — phrase 是描述文本而非原文,须找回命中句原文 + offset(spec 最重那条)
    issues.extend(_structural_issues(s))

    # ⑥ 过饱和 — 密度超阈值的类别,用 finditer 逐处命中收 offset
    issues.extend(_oversaturation_issues(s))

    # ⑦ 上帝视角/解释腔 — find_god_view 白送 offset,逐条展开
    _god_view_msg = {
        "god_spoiler": "上帝视角/解释腔:剧透式全知插话",
        "explain_causality": "上帝视角/解释腔:替读者点破因果",
        "summarize": "上帝视角/解释腔:替角色心理下总结",
        "sublimation": "上帝视角/解释腔:升华式盖棺陈词",
    }
    for hit in find_god_view(s):
        issues.append({
            "type": "god_view",
            "message": _god_view_msg.get(hit["kind"], "上帝视角/解释腔"),
            "text": hit["phrase"],
            "range": hit["range"],
            "meta": {"kind": hit["kind"]},
        })

    # ⑧ 模型退化(方案A任务5)— find_degeneration 白送 offset,逐条展开;
    # meta_leak 按 tier 区分消息(工程词泄漏(tier1)/(tier2)),其余按 kind 固定文案。
    _degeneration_msg = {
        "adjacent_repeat": "模型退化:紧邻整行复读",
        "sentence_loop": "模型退化:长句打转复读",
        "refusal": "模型退化:AI拒绝语泄漏",
        "mojibake": "模型退化:乱码",
        "english_ai": "模型退化:英文AI腔泄漏",
        "placeholder": "模型退化:占位符泄漏",
        "truncated": "模型退化:疑似中途截断",
    }
    for hit in find_degeneration(s):
        kind = hit["kind"]
        if kind == "meta_leak":
            msg = f"工程词泄漏(tier{hit['tier']}):{hit['phrase']}"
        else:
            msg = _degeneration_msg.get(kind, "模型退化")
        meta = {k: v for k, v in hit.items() if k not in ("range", "phrase")}
        issues.append({
            "type": "degeneration",
            "message": msg,
            "text": hit["phrase"],
            "range": hit["range"],
            "meta": meta,
        })

    # ⑨ 句长方差/burstiness(方案A任务6)— 章级判定,非逐处命中,无法给 offset,range=None。
    # 仅 verdict=="uniform"(节拍器)才报一条;"ok"或句数不足(None)不报。
    rhythm = find_rhythm_uniformity(s)
    if rhythm and rhythm["verdict"] == "uniform":
        issues.append({
            "type": "rhythm",
            "message": f"节奏单调:句长分布异常均匀(cv={rhythm['cv']},疑似AI节拍器)",
            "text": "",
            "range": None,
            "meta": rhythm,
        })

    # ⑩ 副词密度(方案A任务7)— 章级判定(千字密度),非逐处命中,range=None。
    adverb = find_adverb_density(s)
    if adverb:
        issues.append({
            "type": "adverb",
            "message": f"副词密度过高:「{'/'.join(adverb['words'])}」千字{adverb['per_k']}处(阈值3.0),疑似AI腔",
            "text": "",
            "range": None,
            "meta": adverb,
        })

    # ⑪ 句内三段式(方案A任务7)— 密度报告门(_rule_of_three_gated)过阈才逐条上报,带 range。
    for r in _rule_of_three_gated(s):
        issues.append({
            "type": "rule_of_three",
            "message": "句内三段式:「X、Y、Z」排比式并列密度过高,疑似AI腔",
            "text": r["phrase"],
            "range": r["range"],
            "meta": {},
        })

    return issues


# 结构重复的句切分:与 find_structural_repeats 同口径([。！？\n]+ 分句 + 去标点边缘),
# 但额外记录每句在原文里的 [start,end)(用 finditer 在原文上扫,边缘去空白后再夹回)。
_SENT_SPLIT = re.compile(r"[。！？\n]+")


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


def _oversaturation_issues(text: str) -> list[dict]:
    """find_oversaturation 的带 offset 展开:仅对超阈值的类别,用 finditer 逐处命中收 offset。"""
    flags = find_oversaturation(text)
    if not flags:
        return []
    over_kinds = {f["kind"] for f in flags}
    msg = {"explain": "过饱和:过度解释词密度过高",
           "emo_label": "过饱和:情绪标签词密度过高",
           "simile": "过饱和:比喻词密度过高"}
    issues: list[dict] = []
    if "explain" in over_kinds:
        for w in _EXPLAIN:
            for m in re.finditer(re.escape(w), text):
                issues.append({"type": "oversaturation", "message": msg["explain"],
                               "text": w, "range": [m.start(), m.end()],
                               "meta": {"kind": "explain"}})
    if "emo_label" in over_kinds:
        for w in _EMO_LABEL:
            for m in re.finditer(re.escape(w), text):
                issues.append({"type": "oversaturation", "message": msg["emo_label"],
                               "text": w, "range": [m.start(), m.end()],
                               "meta": {"kind": "emo_label"}})
    if "simile" in over_kinds:
        for w in _SIMILE_WORDS:
            for m in re.finditer(re.escape(w), text):
                issues.append({"type": "oversaturation", "message": msg["simile"],
                               "text": w, "range": [m.start(), m.end()],
                               "meta": {"kind": "simile"}})
        for m in _SIMILE_LIKE.finditer(text):
            issues.append({"type": "oversaturation", "message": msg["simile"],
                           "text": m.group(0), "range": [m.start(), m.end()],
                           "meta": {"kind": "simile"}})
    return issues


# ==== 方案B任务18:反谄媚对抗注入 + 统一 Findings Schema ====
# 背景(oh-story story-review/SKILL.md):LLM 评审默认倾向"找亮点、给通过"(谄媚/盖章通过),
# 确定性纠偏是在每个 reviewer prompt 里硬写"你的任务是找问题,不是验证正确性"——
# 用最严苛的标准审视,宁可误报不可漏报。仅对"评审性"prompt(discipline 纪律判官/
# tension 张力评审)注入;build_knowledge_extract_prompt/build_voice_fold_prompt 是
# 抽取/折叠而非评审,不注入(它们的任务本就是"如实抽取",不存在"验证正确性"的谄媚风险)。
ANTI_SYCOPHANCY = "你的任务是找问题,不是验证正确性;以最严苛的标准审视,宁可误报不可漏报。"

# 统一 Findings Schema:后续 reviewer 编排(方案B任务19/21 与 loop 化)公用契约。
# severity 从重到轻 S1(阻断)→S4(建议);category 覆盖九类问题域。
# 现有 parse_discipline/parse_tension_report 的输出**不强改**(向后兼容,各自 caller
# 仍按老字段消费);新消费方(未来的多 reviewer 编排层)用 normalize_findings 清洗
# 各 reviewer 的原始输出,统一成可机器合并排序的一张表。
FINDING_SEVERITIES = ("S1", "S2", "S3", "S4")
FINDING_CATEGORIES = (
    "structure", "character", "prose", "consistency", "platform",
    "factual", "format", "causal", "rule_boundary",
)


def normalize_findings(findings: list) -> list:
    """清洗一批 finding dict,统一成 Findings Schema:severity(S1-S4)、category(九类)、
    location/evidence/issue/fix(允许空串,但键缺失时补 "" 而非直接判非法)。

    枚举(severity/category)非法即整条丢弃(记 warning);其余四个字段只做"键缺失补齐",
    不因空串拒绝(找不到具体证据/定位时,评审仍可先报问题,后续再补)。
    返回按 severity 排序(S1 最前,S4 最后)的新列表,供多 reviewer 结果机器合并展示。
    """
    order = {s: i for i, s in enumerate(FINDING_SEVERITIES)}
    out: list[dict] = []
    for f in findings or []:
        severity = f.get("severity")
        category = f.get("category")
        if severity not in FINDING_SEVERITIES:
            _log.warning("normalize_findings 丢弃:非法 severity=%r | finding=%r", severity, f)
            continue
        if category not in FINDING_CATEGORIES:
            _log.warning("normalize_findings 丢弃:非法 category=%r | finding=%r", category, f)
            continue
        out.append({
            "severity": severity,
            "category": category,
            "location": f.get("location") or "",
            "evidence": f.get("evidence") or "",
            "issue": f.get("issue") or "",
            "fix": f.get("fix") or "",
        })
    out.sort(key=lambda d: order[d["severity"]])
    return out


_VERDICT_RANK = {"REJECT": 2, "CONCERNS": 1, "APPROVE": 0}


def merge_verdicts(verdicts: list) -> str:
    """多 reviewer VERDICT 汇总:分歧不自动妥协,取【最严重】者——任一 REJECT 即 REJECT,
    无 REJECT 但有 CONCERNS 即 CONCERNS,全 APPROVE 才 APPROVE。空列表(无评审跑过)
    保守视为 CONCERNS——不能盖章。非法 verdict 值按 CONCERNS 计(同样保守,记 warning)。
    """
    if not verdicts:
        return "CONCERNS"
    worst = "APPROVE"
    for v in verdicts:
        if v not in _VERDICT_RANK:
            _log.warning("merge_verdicts 遇到非法值,按 CONCERNS 计: %r", v)
            v = "CONCERNS"
        if _VERDICT_RANK[v] > _VERDICT_RANK[worst]:
            worst = v
    return worst


def _ranges_overlap(a: list[int] | None, b: list[int] | None) -> bool:
    """标准半开区间相交判定([a0,a1) 与 [b0,b1) 有交集);任一侧为 None 视为不相交。"""
    if not a or not b:
        return False
    a0, a1 = a
    b0, b1 = b
    return a0 < b1 and b0 < a1


# ==== 方案B任务20:finding-merge 纪律 + degradation→重新生成 ====
# 背景(oh-story story-review/SKILL.md:151/:153):
# ①合并多检测器 finding 时要去重归口——同一位置若同时存在"机械替换"(如标点归一
#   punct_suggestions)与"按功能改写"(如 ai_tics/god_view 等 issue)两条建议,两者冲突,
#   丢弃机械替换那条,只留按功能改写的 issue(机械替换不理解上下文,盲改易破坏语义,
#   按功能改写的判断优先级更高)。
# ②degradation 类(find_degeneration 产出的 type=="degeneration" issue)要精确绑定
#   "重新生成该段"而不是"改写"——对齐 scribe3 已验证的 continue-steer 回炉机制(模型退化
#   是生成过程本身失控,局部改写治标不治本,必须整段回炉重打)。
# 这里的 fix_action(regenerate/rewrite)是 loop 化回炉编排的 severity/action 分流依据
# 之一,与设计文档「blocking→regenerate / advisory→rewrite」的两态合流一致。
def merge_findings(issues: list[dict], punct_suggestions: list[dict]) -> tuple[list[dict], list[dict]]:
    """合并 issues 与 punct_suggestions 前的去重归口 + fix_action 绑定,不修改入参。

    - 去重归口:punct_suggestions 中 range 与任一 issue.range 相交的一条 → 丢弃
      (「按功能改写」的 issue 优先于「机械替换」建议;issue.range 为 None 的不参与相交判定,
      issues 本身一律不丢)。
    - fix_action 绑定:type=="degeneration" 的 issue,meta 加 "fix_action": "regenerate"
      (重新生成该段);其余 issue meta 加 "fix_action": "rewrite"(默认按功能改写)。
    - 返回全新列表 + 浅拷贝后的 meta dict,不原地修改传入的 issues/punct_suggestions。
    """
    merged_issues: list[dict] = []
    issue_ranges: list[list[int] | None] = []
    for iss in issues:
        new_iss = dict(iss)
        meta = dict(iss.get("meta") or {})
        meta["fix_action"] = "regenerate" if iss.get("type") == "degeneration" else "rewrite"
        new_iss["meta"] = meta
        merged_issues.append(new_iss)
        issue_ranges.append(iss.get("range"))

    merged_suggestions: list[dict] = []
    for sug in punct_suggestions:
        srange = sug.get("range")
        if any(_ranges_overlap(srange, ir) for ir in issue_ranges):
            continue
        merged_suggestions.append(sug)

    return merged_issues, merged_suggestions


# ==== LLM 语义判官(纪律闸)——确定性检测的盲区:双高潮/声音崩/解说倾泻/知识泄露 ====
def build_discipline_prompt(text: str, brief: str = "", known: dict | None = None) -> str:
    kb = ""
    if known:
        lines = "\n".join(f"  · {who} 只知道:{('、'.join(facts[:8]) or '(仅其私密内核)')}"
                          for who, facts in known.items())
        kb = ("\n\n【各角色截至本章已知(判 knowledge_leak 的事实依据;角色说出此清单之外的他人私密=泄露)】\n"
              + lines)
    return (
        ANTI_SYCOPHANCY + "\n\n"
        "你是叙事结构【纪律判官】。下面是一章志怪小说。本章的命题/纪律要求:\n" +
        (brief or "(默认:乱世铜炉式克制——单一戏剧主线、不偷跑后续章剧情、terse 角色不大段独白、不解说倾泻)") +
        "\n\n判定是否违反以下纪律(任一即违规):\n"
        "① double_climax:出现第二场打斗/救援/开挂,或偷跑了本不属于本章的后续剧情、凭空发明新登场角色;\n"
        "② voice_collapse:声细如蚊/半截就断的 terse 角色崩成大段流畅独白、系统结算音、或与主角同温;\n"
        "③ exposition_dump:大段身世/前史/规则的集中倾泻(本该零星渗出);\n"
        "④ knowledge_leak:某角色说出或表现出知晓【其视角不可能知道】的他人私密信息;\n"
        "⑤ god_view:评判性副词补语(如“关切得恰到好处”)、剧透点破潜台词(如“谁都看得出他在撒谎”)、"
        "定性盖棺比喻——属上帝腔,标记之(这些无标志词的隐蔽层交你语义判断,不做正则)。\n"
        "若违规,找出正文里【复发/穿帮开始的前一句】(从这句之后整段都该砍掉),逐字填入 cut_after。\n"
        '只输出一行 JSON:{"ok": true/false, "violations": ["double_climax"...], "cut_after": "复发前最后一句的原文逐字,守纪则空"}。'
        + kb + "\n\n【正文】\n" + text)


def parse_discipline(reply: str) -> dict:
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        d = json.loads(m.group(0)) if m else {}
        return {"ok": bool(d.get("ok", True)), "violations": list(d.get("violations") or []),
                "cut_after": (d.get("cut_after") or "").strip()}
    except Exception as e:
        _log.warning("parse_discipline 失败,纪律默认放行: %s | reply[:120]=%r", e, (reply or "")[:120])
        return {"ok": True, "violations": [], "cut_after": ""}   # 解析失败不阻断(fail-open)


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


# ==== 声音演变折叠(fold_voice_flags:LLM 把开放 flag 折进 voice_profile)====

def build_voice_fold_prompt(current_profile: dict | None, flags: list[dict]) -> str:
    """构建声音演变折叠 prompt。
    current_profile: 当前 voice_profile dict(可为 None/空)。
    flags: list[{character, trigger_chapter, reason, id}]。
    要求 LLM 输出一行 JSON,至少含 style_summary;可含 tone_rules/catchphrases。
    """
    profile_str = "（尚无声音指纹,请从零建立）"
    if current_profile:
        parts = []
        if current_profile.get("style_summary"):
            parts.append(f"style_summary: {current_profile['style_summary']}")
        if current_profile.get("tone_rules"):
            parts.append(f"tone_rules: {current_profile['tone_rules']}")
        if current_profile.get("catchphrases"):
            parts.append(f"catchphrases: {current_profile['catchphrases']}")
        if parts:
            profile_str = "\n".join(parts)

    flag_lines = "\n".join(
        f"  · 第{f.get('trigger_chapter', '?')}章:{f.get('reason', '')}"
        for f in flags
    )

    return (
        "你是专业小说声音编辑。下面是某角色的当前声音指纹,以及情节驱动的声音演变信号。\n\n"
        "【当前声音指纹】\n" + profile_str + "\n\n"
        "【情节声音演变信号(需要折叠进声音指纹)】\n" + flag_lines + "\n\n"
        "请根据上述演变信号,输出一个**更新后**的声音指纹 JSON,反映角色经历这些情节后声音的演变。\n"
        "字段要求:style_summary(必填,一句话描述), tone_rules(选填,list), catchphrases(选填,list)。\n"
        "保持风格克制,不要为角色代写台词,只描述声音特征的变化。\n"
        '只输出一行 JSON,例如:{"style_summary":"...", "tone_rules":["..."], "catchphrases":["..."]}\n'
        "不要任何解释或额外文字。"
    )


def parse_voice_profile_from_fold(reply: str) -> dict | None:
    """解析 LLM 声音折叠回复。
    成功:返回含 style_summary 的 dict。
    失败(坏 JSON / 无 style_summary):返回 None(调用方据此 fail-soft,不改现有 profile)。
    """
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            _log.warning("parse_voice_profile_from_fold 无 JSON 块: reply[:120]=%r",
                         (reply or "")[:120])
            return None
        d = json.loads(m.group(0))
        if not d.get("style_summary"):
            _log.warning("parse_voice_profile_from_fold: 缺 style_summary,拒绝: %r", d)
            return None
        return d
    except Exception as e:
        _log.warning("parse_voice_profile_from_fold 失败: %s | reply[:120]=%r",
                     e, (reply or "")[:120])
        return None


# ==== 知识账本抽取(定稿时抽"本章谁新知道什么/做了什么",喂单一真相源)====
def build_knowledge_extract_prompt(prose: str, motif_names: list[str] | None = None,
                                   promise_items: list[dict] | None = None,
                                   belief_chars: list[dict] | None = None) -> str:
    motif_seg = ""
    motif_schema = ""
    if motif_names:
        names = "、".join(motif_names)
        motif_seg = (
            f"再抽【motif:本章触及了以下【已立母题】中的哪些({names})——"
            "只能从这些里选,严禁发明新母题;每条给母题名(motif)+本章一句体现它的引文(evidence);"
            "没触及则输出空列表】。\n")
        motif_schema = ',"motif":[{"motif":母题名,"evidence":引文}]'
    promise_seg = ""
    promise_schema = ""
    if promise_items:
        listing = "；".join(f"「{(p.get('text') or '')[:40]}」" for p in promise_items)
        promise_seg = (
            f"再抽【promise_touch:本章推进/呼应/兑现了以下【已埋伏笔】中的哪些({listing})——"
            "只能从这些里选,严禁发明;仅出现相近意象或字眼、并不指向该悬念的不算触及;"
            "每条给伏笔原文片段(text,须与上列某条逐字对应)"
            "+本章一句体现推进的引文(evidence);没触及则输出空列表】。\n")
        promise_schema = ',"promise_touch":[{"text":伏笔原文,"evidence":引文}]'
    belief_seg = ""
    belief_schema = ""
    if belief_chars:
        desc = "；".join(f"{c['name']}(其信念:「{c['lie']}」)" for c in belief_chars)
        belief_seg = (
            f"再抽【belief:下列角色本章结束时对各自核心错误信念的信奉度(0-100,{desc})——"
            "只评这些角色;每条给角色名(who)+信奉度(value)+一句依据(why);"
            "本章无相关表现的角色不输出】。\n")
        belief_schema = ',"belief":[{"who":角色名,"value":0到100整数,"why":依据}]'
    return (
        "读下面一章小说正文,抽取本章【各角色新知道了什么(learned)、做了什么且被谁看见(did)】——"
        "用于维护'谁知道什么'的知识账本(防后续章里某角色说出他视角不可能知道的信息)。"
        "再抽【voice_shift:哪些角色这章经历了可能改变其说话方式/声音的重大事件(创伤/背叛/重大转折/身份剧变)】——"
        "只列谁+什么事,不要替他写新独白。\n"
        "再抽【arc:哪些角色在本章经历了可量化的弧光质变——能力获得/丧失、重要关系建立/破裂、性格明显转折】——"
        "每条列:角色名(who)、变化类型(change_type:ability/relation/personality)、"
        "一句话摘要(summary)、快照(snapshot:对 ability 填{技能:状态}、"
        "对 relation 填{对象角色:关系描述}、对 personality 填字符串描述)。"
        "没有明确弧光质变时 arc 输出空列表。\n"
        "再抽【events:本章推动剧情的关键情节事件(动作/冲突/转折,通常 2-6 个)】——"
        "每条列:事件类型短标签(type,≤12字,如「对峙」「揭露」「立誓」)、"
        "参与者(participants:{SUBJ:主动方角色名, OBJ:受动方角色名, WITNESS:在场见证角色名};"
        "只填有的槽位,没有的槽位省略)、该事件为何发生的动机/目标(goal,一句话)、"
        "因果来由(caused_by:本章前面第几个事件直接导致了它,填其序号数组(从0起,只能指向本章更早的事件);"
        "本章第一个或无明确前因的事件填空数组[])。"
        "按事件在本章的发生先后顺序输出;没有明确事件时 events 输出空列表。\n"
        + motif_seg + promise_seg + belief_seg +
        '只输出一行 JSON:{"learned":[{"who":角色名,"fact":新知道的事(短句)}],'
        '"did":[{"who":角色名,"action":所为(短句),"seen_by":[在场看见的角色名]}],'
        '"voice_shift":[{"who":角色名,"reason":重大事件(短句)}],'
        '"arc":[{"who":角色名,"change_type":"ability|relation|personality",'
        '"summary":一句话摘要,"snapshot":{...}}],'
        '"events":[{"type":类型标签,"participants":{"SUBJ":角色名,"OBJ":角色名,"WITNESS":角色名},'
        '"goal":动机目标,"caused_by":[前序事件序号]}]'
        + motif_schema + promise_schema + belief_schema + '}。\n\n'
        "【正文】\n" + prose)


def parse_knowledge_delta(reply: str) -> dict | None:
    """解析 LLM 回复的知识 delta JSON。
    成功:返回 {"learned":..., "did":..., "voice_shift":..., "arc":...}(四字段均为 list)。
    arc 字段为可选——旧模型/旧响应不含该字段时默认空列表(向后兼容,不破坏现有调用)。
    失败(坏 JSON / 截断 / 无 {} 匹配):返回 None——调用方据此跳过 purge,防止数据丢失。"""
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            _log.warning("parse_knowledge_delta 无 JSON 块,知识不回写: reply[:120]=%r", (reply or "")[:120])
            return None
        d = json.loads(m.group(0))
        return {"learned": list(d.get("learned") or []), "did": list(d.get("did") or []),
                "voice_shift": list(d.get("voice_shift") or []),
                "arc": list(d.get("arc") or []),
                "motif": list(d.get("motif") or []),
                "promise_touch": list(d.get("promise_touch") or []),
                "belief": list(d.get("belief") or []),
                # 批D P1-5:事件抽取。旧模型/旧响应不含该字段时默认空列表(向后兼容)。
                "events": list(d.get("events") or [])}
    except Exception as e:
        _log.warning("parse_knowledge_delta 失败,知识不回写: %s | reply[:120]=%r", e, (reply or "")[:120])
        return None


# ==== M2a: 叙事张力盲评 rubric(对成文单章,LLM 单次合并评审)====

def build_tension_rubric_prompt(prose: str) -> str:
    """张力盲评 prompt:戏剧问题/结局语法/价值反转/微张力荒漠/续读钩子/节奏失败模式,
    单次调用合并评审。

    方案B任务13新增两条节奏失败模式轴(oh-story emotional-methods.md 语义判定,
    LLM 通读判断,确定性正则判不了):
    - pacing_flat:   连续≥5节没有情绪转折即"太平"(读者会跳读)。
    - pacing_rushed: 转折前铺垫不足3节即"太赶"(反转没立住);或反转后交代解释
      超过2000字即"烂尾"(高潮后拖沓收不住)。
    """
    return (
        ANTI_SYCOPHANCY + "\n\n"
        "你是叙事张力评审。读下面一章小说正文,只输出一个 JSON(不要任何其他文字):\n"
        '{"dramatic_question":{"present":布尔,"answered_escalated":布尔,"note":一句},'
        '"outcomes":[{"scene":场景一句概括,"type":"yes"|"yes_but"|"no_and"|"no"}],'
        '"value_shift":{"present":布尔,"note":"哪个价值从什么极翻到什么极"},'
        '"micro_tension":{"deserts":[连续500字以上无POV情绪对立/念头交战的段落开头8字]},'
        '"hook":{"present":布尔,"type":"危险临近|信息截断|选择悬置|反转|不祥预示|无","strength":"strong"|"soft"},'
        '"pacing_flat":{"present":布尔,"note":一句},'
        '"pacing_rushed":{"present":布尔,"note":一句}}\n'
        "判定标准:dramatic_question=本章是否有一个悬着的小问题且章末被回答并升级;"
        "outcomes=各场景结局语法(顺利达成记 yes——它是泄气信号);"
        "value_shift=至少一场发生价值极性反转;hook=章末最后几行是否有续读钩子;"
        "pacing_flat=是否存在连续5节以上没有任何情绪转折(太平,读者会跳读);"
        "pacing_rushed=是否存在转折前铺垫不足3节就发生(太赶,反转立不住),"
        "或反转后交代解释超过2000字仍未收住(烂尾)。\n\n"
        f"正文:\n{prose}")


def parse_tension_report(raw: str) -> dict | None:
    """解析张力盲评 JSON。镜像 parse_knowledge_delta:提取首个 {...} 块,json.loads,失败返 None。
    坏 JSON / 截断 / 空 / None 一律 fail-safe 返回 None,调用方据此标 rubric_failed 不崩。"""
    try:
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            _log.warning("parse_tension_report 无 JSON 块: raw[:120]=%r", (raw or "")[:120])
            return None
        return json.loads(m.group(0))
    except Exception as e:
        _log.warning("parse_tension_report 失败: %s | raw[:120]=%r", e, (raw or "")[:120])
        return None


# ==== 方案B任务13b:反转工具箱 rubric + 悬念/伏笔边界
#      (oh-story reversal-toolkit.md 7类反转 + hooks-suspense.md 悬念vs伏笔边界)====

_REVERSAL_TYPES = ("身份反转", "动机反转", "因果反转", "立场反转",
                    "信息差反转", "时间线反转", "道德反转")


def build_reversal_rubric_prompt(prose: str, beat_meta: dict | None) -> str:
    """反转机检 rubric prompt(oh-story reversal-toolkit.md 7类反转)。

    beat_meta 无 reversal_type(空 dict / None)→ 本章未标注反转,不审,返回空串
    (镜像 _deduction_block/_outline_block 的"无内容即空串"约定)。
    beat_meta 含 reversal_type → 组装:7类枚举说明 + 本章反转声明(type/setup_clues/
    reveal_position_pct)+ 4 条机检轴 + 输出契约(与方案B任务18 normalize_findings 的
    FindingsSchema 六字段一致,供多 reviewer 结果统一合并)+ ANTI_SYCOPHANCY。

    悬念/伏笔边界(oh-story hooks-suspense.md):不建新表——短期悬念对应 promise
    账本里 tier:chapter(本章内起落即兑现的钩子),长期伏笔对应 tier:arc/book
    (跨章/跨卷才兑现);两账本语义分离,reversal 的 setup_clues 多数指向后者,
    评审时须按此区分对待,不得混为一谈。
    """
    if not beat_meta or not beat_meta.get("reversal_type"):
        return ""
    rtype = beat_meta.get("reversal_type")
    clues = beat_meta.get("setup_clues") or []
    pct = beat_meta.get("reveal_position_pct")
    types_list = "、".join(_REVERSAL_TYPES)
    clues_str = "；".join(str(c) for c in clues) if clues else "(未标注)"
    return (
        ANTI_SYCOPHANCY + "\n\n"
        "你是叙事反转机制评审。反转共 7 类(" + types_list + ")。\n"
        f"本章声明的反转:类型={rtype};铺垫线索(setup_clues)={clues_str};"
        f"揭示位置(reveal_position_pct)={pct}。\n"
        "悬念/伏笔边界:短期悬念(本章内起落的钩子)记 tier:chapter;长期伏笔"
        "(跨章/跨卷才兑现)记 tier:arc/book——两账本语义分离,本反转的铺垫属于哪一账本,"
        "评审时须区分对待,不得混为一谈。\n"
        "检查以下 4 项机检轴(任一命中即问题):\n"
        "① setup_insufficient:声明的铺垫线索(setup_clues)少于 3 处,或正文里找不到"
        "对应线索的真实着落;\n"
        "② reveal_overlong:揭示/交代反转真相的文字超过 300 字(该收在动作与留白,"
        "不该大段解说);\n"
        "③ unearned_new_info:揭示时引入了前文完全未出现过的新信息(伏笔没有真正埋过,"
        "反转是硬凭空冒出来的);\n"
        "④ position_out_of_range:揭示位置(reveal_position_pct)越出本章 50%-85% 的"
        "最佳区间(太早显得仓促无蓄力,太晚来不及消化)。\n"
        '只输出一行 JSON:{"findings":[{"severity":"S1"|"S2"|"S3"|"S4",'
        '"category":"structure"|"character"|"prose"|"consistency"|"platform"|'
        '"factual"|"format"|"causal"|"rule_boundary","location":定位,"evidence":引文,'
        '"issue":问题描述,"fix":修复建议}],"verdict":"APPROVE"|"CONCERNS"|"REJECT"}。\n\n'
        f"正文:\n{prose}")


def parse_reversal_report(raw: str) -> dict | None:
    """解析反转机检 JSON。镜像 parse_tension_report:提取首个 {...} 块,json.loads,
    坏 JSON / 截断 / 空 / None 一律 fail-safe 返回 None,调用方据此标 rubric_failed 不崩。"""
    try:
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            _log.warning("parse_reversal_report 无 JSON 块: raw[:120]=%r", (raw or "")[:120])
            return None
        return json.loads(m.group(0))
    except Exception as e:
        _log.warning("parse_reversal_report 失败: %s | raw[:120]=%r", e, (raw or "")[:120])
        return None


# ==== M2: 确定性文本质检——整行精确复读 + 叙述层情感直说 ====

# 句子切分:按换行符 + 中文句末标点(。！？…)拆句(带 capture group 保留分隔符)
_SENT_DELIM_CAP = re.compile(r"([。！？…]+)")

# 对话包裹检测:中文弯引号 “”("") 和直角引号 「」(「」)
# 用 Unicode 码点写死避免编辑器保存时字符变形
_DIALOGUE_RE = re.compile(
    r"[“「][^”」]{0,200}[”」]", re.S
)

# 情绪直说正则:叙述层主语 + 情绪动词/词语 + 具体情绪词
_EMOTION_WORD_RE = re.compile(
    r"(?:他|她|它)?(?:感到|觉得|心里|心中|心头)(?:一阵|一)?"
    r"(?:害怕|恐惧|惧|难过|悲伤|愧疚|不忍|心疼|疼痛|高兴|欢喜|愤怒|绝望|紧张|安心|悲痛|痛苦|焦虑|孤独|兴奋|恐慌)"
)

# 直接评语正则:对人物下定性评语
_VERDICT_RE = re.compile(
    r"(?:他|她)(?:其实)?(?:不是|是)(?:个)?(?:坏人|好人|善人|恶人|好角色|坏角色)"
)

# 标签化生理-情感套语(weak 命中,kind=cliche)
_CLICHE_RE = re.compile(
    r"心里像被(?:什么)?(?:揪|攥|堵|压|刺|扎|灼|撕)(?:住|着|了|痛)?"
)

# 方案B任务13:情绪表达4级(oh-story style-craft.md:直写<思想<神态<动作,表达质量阶梯)
# L2 思想转述——用叙述层动词直接转述人物内心念头(而非具体情绪词),同属 telling。
_THOUGHT_REPORT_RE = re.compile(r"(?:心中暗道|心想|心道|暗想|暗忖)")


def _strip_dialogue(text: str) -> str:
    """去除文本中被中文弯引号/直角引号包裹的对话片段,返回剩余叙述层文本。
    这是粗略过滤:减少对话内情感词误报(宁可漏检不误报)。"""
    return _DIALOGUE_RE.sub("", text or "")


# 7 对引号(对齐 oh-story stripQuoted):台词/弹幕复沓是体裁常态,复读/排比/结构检测只判叙述层。
# 与 _DIALOGUE_RE(仅“”「」两对,供 find_emotion_telling 用)分开维护——语义不同、互不影响。
_QUOTED_SPANS = [re.compile(p, re.S) for p in (
    r"「[^」]*」", r"『[^』]*』", r"【[^】]*】",
    r"“[^”]*”", r"‘[^’]*’", r'"[^"]*"', r"'[^']*'",
)]


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


# ==== 方案A任务4:上帝视角/解释腔检测器(find_god_view)====
# 纯静态语言指纹,与 verify.py 的 find_leaks(知识帧 fact-leak 检测,判"角色说出其视角
# 不可能知道的信息")分工不同——那里查的是知识账本语义,这里只查字面句式。
# 归位纪律:①"这意味着/正是因为"已在 _EXPLAIN(find_oversaturation 管),此处只收
# "之所以…是因为";②"原来…"已被 LUANSHI_PURPLE_SEEDS[0] 部分覆盖,此处不再收。
_GOD_VIEW_PATTERNS = [   # oh-story anti-ai-writing 模式8 + 总结/升华句式,纯语言层
    ("god_spoiler", re.compile(r"(她|他)不知道的是|殊不知|多年以后|冥冥之中|仿佛预示着")),
    ("explain_causality", re.compile(r"之所以[^。！？\n]{1,30}(?:，)?是因为")),
    ("summarize", re.compile(r"(?:他|她)(?:终于明白|这才意识到|这才明白)|此刻[，,](?:他|她)")),
    # sublimation 只锚"行首(容忍全角/半角/Tab 缩进)开头的整句"——刻意收窄防误伤:
    # 句中出现"这一刻/这就是"(如"爱情在这一刻绽放")是合法叙述,不报;
    # 段首起句的"这一刻，…。/这就是…。"才是升华式盖棺陈词(宁可漏不滥杀)。
    ("sublimation", re.compile(r"^[ 　\t]*(?:这一刻|这就是)[^。！？\n]{2,30}[。！？]", re.M)),
]


def find_god_view(text: str) -> list[dict]:
    """上帝视角/解释腔语言指纹(oh-story anti-ai-writing 模式8)。对话内豁免(叙述层才算破 POV)。
    与 verify.find_leaks(知识帧事实泄露)分工:此处只查静态语言指纹,report-only,宁可漏不滥杀。"""
    s = text or ""
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    for kind, pat in _GOD_VIEW_PATTERNS:
        for m in pat.finditer(s):
            if _in_any_span(m.start(), m.end(), quoted):
                continue
            out.append({"kind": kind, "phrase": m.group(0), "range": [m.start(), m.end()]})
    return out


def find_duplicate_lines(text: str, min_chars: int = 6) -> list[dict]:
    """检测精确重复的整行或整句(>=2次,字符总长>=min_chars)。

    切分策略:先按换行拆行,再对每行按中文句末标点(。！？…)拆句
    (分隔符附在前一句末,保留句末标点使句子有自然长度);
    归一化首尾空白后做完全相同比对。
    排除:纯标点/空串、字符总长不足 min_chars 的短句。
    返回 [{"line": <重复的句/行>, "count": <次数>}],按 count 降序。
    """
    from collections import Counter

    raw = text or ""
    segments: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 用带 capture group 的 split 保留分隔符,再把分隔符拼回前一句
        parts = _SENT_DELIM_CAP.split(line)
        buf = ""
        for part in parts:
            if _SENT_DELIM_CAP.fullmatch(part):
                # 这是标点分隔符:追加到当前缓冲区,然后 flush
                buf += part
                normed = buf.strip()
                if normed:
                    segments.append(normed)
                buf = ""
            else:
                buf += part
        # 行末无句末标点时 flush 余量
        normed = buf.strip()
        if normed:
            segments.append(normed)

    counts: Counter[str] = Counter(segments)
    out: list[dict] = []
    for seg, cnt in counts.items():
        if cnt < 2:
            continue
        # 排除字符总长不足 min_chars 的短句(含标点一起算)
        if len(seg) < min_chars:
            continue
        # 排除纯标点/空串
        if _PUNCT_ONLY.match(seg):
            continue
        out.append({"line": seg, "count": cnt})

    out.sort(key=lambda x: -x["count"])
    return out


def find_parallelism(text: str, min_run: int = 3, prefix_len: int = 2) -> list[dict]:
    """检测排比/同句式复读(AI 抒情腔):连续 >=min_run 个句子以相同的起首
    (前 prefix_len 个汉字)开头,或相邻句反复用同一引导词(就像/穿过/有些/不是…)。

    乱世铜炉志怪笔记体忌排比抒情;opus 评判反复点名"同句式≥3连"是 AI 腔。
    切句:按换行 + 中文句末标点(。!?…)+ 逗号分句(排比常以逗号断)。
    归一:剥离起首引号/破折号等装饰符后取前 prefix_len 个汉字为指纹。
    返回 [{"prefix": <起首>, "count": <连排数>, "sample": <首句>}],按 count 降序。
    仅在指纹是汉字(非纯标点/数字)时计入。
    引号内(台词/弹幕)豁免——体裁正常形态,只判叙述层排比。
    """
    text = _strip_quoted(text)
    raw = text or ""
    # 句/读切分:句末标点与逗号、顿号都作为排比分句边界
    pieces: list[str] = []
    for line in raw.split("\n"):
        for seg in re.split(r"[。！？…,，、;；\n]", line):
            seg = seg.strip().lstrip("\"'“”‘’—…·　 ")
            if seg:
                pieces.append(seg)

    def fp(s: str) -> str:
        # 取前 prefix_len 个汉字作指纹
        han = re.findall(r"[一-鿿]", s)
        return "".join(han[:prefix_len]) if len(han) >= prefix_len else ""

    out: list[dict] = []
    i = 0
    n = len(pieces)
    while i < n:
        f = fp(pieces[i])
        if not f:
            i += 1
            continue
        j = i + 1
        while j < n and fp(pieces[j]) == f:
            j += 1
        run = j - i
        if run >= min_run:
            out.append({"prefix": f, "count": run, "sample": pieces[i][:24]})
        i = j if j > i else i + 1

    out.sort(key=lambda x: -x["count"])
    return out


_ONOMAT_LINE = re.compile(r"^[咔笃啪嗒砰咚哗叮当吱嘎咯吧噗嘀嗡][——\-—.。…、，！]*$")


def find_poetic_fragments(text: str, max_len: int = 6) -> list[dict]:
    """诗化分行/拟声悬停检测(AI 抒情/恐怖腔):孤立的短句(非对白)独立成行,或拟声词成行。
    排除对白行(含引号)与纯标点。返回 [{"line","kind","ending"}];kind=onomatopoeia|fragment,
    ending=True 表示该碎句正是全文末行(章节拟声/单字煞尾——opus 评判明令禁止)。"""
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    out: list[dict] = []
    n = len(lines)
    for i, l in enumerate(lines):
        if len(l) > max_len:
            continue
        if any(q in l for q in "“”\"'「」『』"):  # 对白,放过
            continue
        if _PUNCT_ONLY.match(l):
            continue
        kind = "onomatopoeia" if _ONOMAT_LINE.match(l) else "fragment"
        out.append({"line": l, "kind": kind, "ending": i == n - 1})
    return out


def find_unbalanced_quotes(text: str) -> list[dict]:
    """引号开闭不配对(中文“”/「」)。返回失衡项;空列表=配对正常。"""
    t = text or ""
    issues: list[dict] = []
    for op, cl in (("“", "”"), ("「", "」"), ("『", "』")):
        a, b = t.count(op), t.count(cl)
        if a != b:
            issues.append({"pair": op + cl, "open": a, "close": b})
    if t.count('"') % 2:
        issues.append({"pair": '"', "count": t.count('"')})
    return issues


_WATCH_MAP = {"一更": 1, "二更": 2, "两更": 2, "三更": 3, "四更": 4, "五更": 5}


def find_watch_regression(text: str) -> list[dict]:
    """更次倒退检测:文中更次(一更→五更)序列若非单调递增(后文更次 < 已达最大更次)即报。
    志怪夜戏常见硬伤——开篇四更、后文又'三更'。返回倒退点 [{"label","pos","after_max"}]。"""
    seq = []
    for m in re.finditer(r"[一二两三四五]更", text or ""):
        w = _WATCH_MAP.get(m.group(0))
        if w:
            seq.append((m.start(), w, m.group(0)))
    out: list[dict] = []
    mx = 0
    for pos, w, label in seq:
        if w < mx:
            out.append({"label": label, "pos": pos, "after_max": mx})
        mx = max(mx, w)
    return out


def find_emotion_telling(text: str, allow_patterns: list[str] | None = None,
                         short_mode: bool = False) -> list[dict]:
    """检测叙述层直陈情绪/直接评语/思想转述的句子(确定性正则,宁缺勿滥)。

    方案B任务13:情绪表达4级(oh-story style-craft.md)是一条"直写 < 思想 < 神态 <
    动作"的表达质量阶梯——直写情绪词最生硬,动作/神态侧写最含蓄高级。本检测器只
    上报前两级(L1/L2)确定性可判的 telling,L3(神态)/L4(动作)是合法的 showing
    手法,语义上不该报——因此不扫描,不构成检测规则。

    规则(L1,level=1,直写):
    - emotion_word: (他|她|它)?(感到|觉得|心里|心中|心头)(一阵|一)?(情绪词)
    - verdict:      (他|她)(其实)?(不是|是)(个)?(坏人|好人|善人|恶人)
    - cliche(weak): 心里像被什么(揪|攥|堵)住 等标签化套语

    规则(L2,level=2,思想转述):
    - thought_report: 心中暗道|心想|心道|暗想|暗忖——用叙述层动词直接转述人物内心
      念头,不点名具体情绪词,但仍是 telling(比直写情绪词含蓄一级,仍非 showing)。

    对话内情感词处理:粗略去除中文弯引号包裹片段后再扫描(减少误报)。
    返回 [{"span": <命中片段>, "kind": "emotion_word"|"verdict"|"cliche"|"thought_report",
    "level": 1|2}](kind/span 字段向后兼容既有调用方)。

    allow_patterns(方案B任务14):题材豁免正则,来自 craft_rule allow_pattern——前置
    skip 判定(减法),命中 span 匹配任一 allow 正则即放行不报。与其余检测器同一豁免
    机制,独立于本函数既有的 level 分级逻辑(B13),不改动分级判定,只在收录前多一道
    豁免过滤。

    short_mode(方案B任务16):短篇模式开关——短篇要直写情绪+审判金句(见
    scribe3/genres.py 四题材包的 keep_list),长篇的"留白/克制"引擎(craft.py
    ENGINES["restraint"])全线让位。short_mode=True 时本检测器直接返回 []
    (不做任何 telling 判定,视图层/AI味定档不再因直写情绪而扣分),优先级高于
    allow_patterns(两者语义重叠时 short_mode 是更彻底的整体开关)。
    """
    if short_mode:
        return []
    s = _strip_dialogue(text or "")
    allow_pats = [re.compile(p) for p in (allow_patterns or [])]

    def _allowed(span: str) -> bool:
        return bool(allow_pats) and any(rx.search(span) for rx in allow_pats)

    out: list[dict] = []

    for m in _EMOTION_WORD_RE.finditer(s):
        if _allowed(m.group(0)):
            continue
        out.append({"span": m.group(0), "kind": "emotion_word", "level": 1})

    for m in _VERDICT_RE.finditer(s):
        if _allowed(m.group(0)):
            continue
        out.append({"span": m.group(0), "kind": "verdict", "level": 1})

    for m in _CLICHE_RE.finditer(s):
        # 避免与 emotion_word 重叠上报
        span = m.group(0)
        if _allowed(span):
            continue
        if not any(r["span"] in span or span in r["span"] for r in out):
            out.append({"span": span, "kind": "cliche", "level": 1})

    for m in _THOUGHT_REPORT_RE.finditer(s):
        if _allowed(m.group(0)):
            continue
        out.append({"span": m.group(0), "kind": "thought_report", "level": 2})

    return out


def emotion_telling_summary(text: str, hits: list[dict] | None = None) -> dict:
    """情绪表达4级分级聚合(方案B任务13),供整章定档/前端聚合展示消费。

    按 find_emotion_telling 命中的 level 拆分 L1(直写)/L2(思想转述)计数:
      l1_count / l2_count  各级命中数
      l1_ratio             l1_count / 句数(句子按 [。！？\\n] 切分,与 aggregate_ai_grade
                            _SENT_SPLIT 同口径)
      total                L1+L2 合计命中数

    hits 可选:调用方已算好 find_emotion_telling(text) 结果时直接传入复用,避免重算
    (见 aggregate_ai_grade 的 C 指标用法);缺省则内部现算。
    """
    hits = find_emotion_telling(text) if hits is None else hits
    l1_count = sum(1 for h in hits if h.get("level") == 1)
    l2_count = sum(1 for h in hits if h.get("level") == 2)
    sent_count = len([s for s in _SENT_SPLIT.split(text or "") if s.strip()]) or 1
    return {
        "l1_count": l1_count,
        "l2_count": l2_count,
        "l1_ratio": l1_count / sent_count,
        "total": len(hits),
    }


# ==== 方案A任务5:模型退化检测(find_degeneration,移植自 oh-story
# skills/story-deslop/scripts/check-degeneration.js)====
# 弱模型/长程生成典型退化指纹,模型自己发现不了,靠确定性扫描+定向重写才拦得住:
#   - 复读/打转(verbatim repetition):长句反复出现,或紧邻整行一字不差重复;
#   - 占位/拒绝语泄漏:作为AI/我无法继续/此处省略/乱码/英文 AI 腔;
#   - 工程词泄漏:细纲/情节点/本章/下一章 等写作流水线术语漏进正文;
#   - 中途截断:正文末尾未以句末/收尾标点结束。
# report-only,不改文本;kind 与阈值常量均与 JS 源逐字对照。

# 复读阈值(逐字移植 JS 源):长句(可见字数≥REPEAT_MIN_LEN)出现≥REPEAT_MIN_COUNT 次判
# 为打转(sentence_loop);紧邻整行重复(可见字数≥ADJACENT_MIN_LEN)判为即时循环
# (adjacent_repeat)。短句/弹幕/对话刷屏豁免——通俗网文的排比/复沓/弹幕是体裁正常手法。
REPEAT_MIN_LEN = 12
REPEAT_MIN_COUNT = 3
ADJACENT_MIN_LEN = 8

# 可见字符集(逐字移植 JS visibleLength):中文 + 全角字母数字 + 半角字母数字。
_DEGEN_VISIBLE_RE = re.compile(r"[一-鿿Ａ-ｚA-Za-z0-9]")


def _degen_visible_length(s: str) -> int:
    """可见字数(剔除标点/空白后的有效字符计数),移植自 JS visibleLength。"""
    return len(_DEGEN_VISIBLE_RE.findall(s or ""))


# 占位/拒绝语泄漏:hard=任何行都判(正文里永不合法);soft=仅"非对话叙述行"判(角色台词
# 里可能合法,如"对不起,我无法答应你"是正常对话)。对话行判定:该行剥引号后剩余可见
# 字符数 <2(近乎整行都是台词/物件名,叙述几乎为零)。均为 blocking(与 JS 一致:
# findPlaceholders 无论 hard/soft,命中一律 severity='blocking')。
_DEGEN_PLACEHOLDER_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(
        r'作为(一个)?(AI|人工智能|大?语言模型|智能助手|聊天助手)'
        r'(?=[，,。、；;：:！!？?\s）)」』"】]|我|无法|不能|没法|$)'
    ), "refusal", False),
    (re.compile(r"�"), "mojibake", True),
    (re.compile(r"^(Sure|Certainly|Here'?s|As an AI|I (?:cannot|can't|am unable|apologize))"),
     "english_ai", True),
    (re.compile(r"[（(](此处|以下|这里|下文|后续)?\s*(省略|略)(去|过)?[^）)]{0,10}[）)]"),
     "placeholder", True),
    (re.compile(r"(未完待续|TODO|占位符|placeholder)"), "placeholder", True),
    (re.compile(
        r"我(无法|不能)(继续(写|创作|生成|下去)|生成(内容|文本|正文)?|创作|续写|完成(这个|本)?(章|篇|创作|请求))"
    ), "refusal", False),
]

# 工程词泄漏(逐字移植):tier1=纯写作流水线术语,正文里几乎永不合法;tier2=章节结构/
# 歧义词,角色在故事内真实阅读/讨论"第X章"、或故事内系统/界面用语时属例外,恒 advisory
# 交人/LLM 判。tier1 命中若落在对话行(引号内)降级 advisory——写手/编剧题材角色可能
# 真讨论创作;tier2 恒 advisory。
_DEGEN_META_TIER1_RE = re.compile(r"细纲|情节点|卷纲|功能标签|目标情绪|字数目标|章首钩子|章尾钩子")
_DEGEN_META_TIER2_RE = re.compile(
    r"第[一二三四五六七八九十百千万两0-9]+章|本章|这一章|上一章|下一章|上章|下章|前一章|后一章|前文|后文|伏笔|读者|任务描述"
)
# 标题行(如"第一章 桥下")属"正文标题行"而非泄漏,排除对首个内容行的误判(移植自 JS
# findMetaLeak 里的首行标题豁免逻辑,check-degeneration.js:278-282)。
_DEGEN_TITLE_RE = re.compile(r"^第[一二三四五六七八九十百千万两0-9]+章")

# 截断判定:全文最后一个非空行须以句末/收尾标点结束,否则疑似中途被切断(advisory——
# 与 JS 的 blocking 不同,此处按方案A任务5要求降级,交人/LLM 判)。
_DEGEN_TRUNCATED_END_RE = re.compile(r'[。！？…”」』"]$')


def _degen_body_lines(text: str) -> list[dict]:
    """按行拆分 + 剔除空行,记录每行【去首尾空白后的内容】在原始 text 里的起始 offset,
    供各子检测器还原 range。"""
    body: list[dict] = []
    pos = 0
    for raw in (text or "").split("\n"):
        trimmed = raw.strip()
        if trimmed:
            lead = len(raw) - len(raw.lstrip())
            body.append({"start": pos + lead, "line": trimmed})
        pos += len(raw) + 1  # +1 补回被 split 吃掉的换行符
    return body


def _degen_adjacent_repeat(body: list[dict]) -> list[dict]:
    """紧邻整行一字不差重复(即时循环)。range 指向第二次出现处。"""
    out: list[dict] = []
    for i in range(1, len(body)):
        cur, prev = body[i], body[i - 1]
        if cur["line"] != prev["line"]:
            continue
        if _degen_visible_length(_strip_quoted(cur["line"])) < ADJACENT_MIN_LEN:
            continue
        out.append({
            "kind": "adjacent_repeat",
            "severity": "blocking",
            "phrase": cur["line"],
            "range": [cur["start"], cur["start"] + len(cur["line"])],
        })
    return out


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


def _degen_sentence_loop(body: list[dict]) -> list[dict]:
    """长句(引号外、可见字数≥REPEAT_MIN_LEN)出现≥REPEAT_MIN_COUNT 次判为打转。
    只豁免引号内台词,引号外叙述句(含"叙述+引号内物件"混合行)仍参与计数。
    range 指向该句第二次出现处(方案A任务5要求,与 JS 的"首次出现"不同)。

    定位:句子在【剥引号文本】上计数,经 _strip_quoted_with_map 的下标映射精确还原回
    原文区间——混合行(叙述+引号)的句子若跨过引号片段,range/phrase 为原文里覆盖该句
    首尾字符的连续区间(中间夹着的引号片段一并包含,保证 phrase == 原文[start:end])。
    """
    counts: dict[str, int] = {}
    # (句子, 行, 行内起, 行内止):起止为原文行坐标,入队时即映射好,回填不再 find
    occurrences: list[tuple[str, dict, int, int]] = []
    for b in body:
        stripped, idx_map = _strip_quoted_with_map(b["line"])
        # 用 finditer 取非分隔符连续段(与 re.split 的非空片段等价),自带片段起点
        for m in re.finditer(r"[^。！？!?]+", stripped):
            piece = m.group(0)
            st = piece.strip()
            if _degen_visible_length(st) < REPEAT_MIN_LEN:
                continue
            lead = len(piece) - len(piece.lstrip())
            ss = m.start() + lead          # st 在剥引号文本里的 [ss, se)
            se = ss + len(st)
            line_start = idx_map[ss]                # 映射回原文行坐标
            line_end = idx_map[se - 1] + 1
            counts[st] = counts.get(st, 0) + 1
            occurrences.append((st, b, line_start, line_end))
    flagged = {s for s, c in counts.items() if c >= REPEAT_MIN_COUNT}
    if not flagged:
        return []
    out: list[dict] = []
    seen: dict[str, int] = {}
    for st, b, line_start, line_end in occurrences:
        if st not in flagged:
            continue
        seen[st] = seen.get(st, 0) + 1
        if seen[st] != 2:  # 只在第二次出现时报一条(range 指向第二次出现处)
            continue
        out.append({
            "kind": "sentence_loop",
            "severity": "blocking",
            "phrase": b["line"][line_start:line_end],  # 原文精确子串,与 range 逐字一致
            "range": [b["start"] + line_start, b["start"] + line_end],
            "count": counts[st],
        })
    return out


def _degen_placeholders(body: list[dict]) -> list[dict]:
    """占位符/拒绝语/乱码/英文 AI 腔泄漏。一行只报一条(命中优先级同 JS 数组顺序)。"""
    out: list[dict] = []
    for b in body:
        line = b["line"]
        dialogue = _degen_visible_length(_strip_quoted(line)) < 2
        for pat, kind, hard in _DEGEN_PLACEHOLDER_PATTERNS:
            if not hard and dialogue:
                continue  # soft 拒绝语在对话行里可能是正常台词,豁免
            m = pat.search(line)
            if not m:
                continue
            start, end = b["start"] + m.start(), b["start"] + m.end()
            out.append({
                "kind": kind,
                "severity": "blocking",
                "phrase": m.group(0),  # 精确匹配片段,与 range 保持一致(range 不变量)
                "range": [start, end],
            })
            break  # 一行一条足矣
    return out


def _degen_meta_leak(body: list[dict], quoted_ranges: list[tuple[int, int]]) -> list[dict]:
    """工程词泄漏:tier1 优先于 tier2(命中 tier1 即跳过 tier2,同一行不叠报)。
    首个内容行若是章节标题("第N章…")豁免,避免每章标题都被 tier2 的"第X章"命中误报。
    tier1 命中落在【引号内】(_quoted_ranges)降级 advisory;tier2 恒 advisory。"""
    out: list[dict] = []
    first_seen = False
    for b in body:
        line = b["line"]
        if not first_seen:
            first_seen = True
            if _DEGEN_TITLE_RE.match(line):
                continue
        m = _DEGEN_META_TIER1_RE.search(line)
        if m:
            start, end = b["start"] + m.start(), b["start"] + m.end()
            dialogue = _in_any_span(start, end, quoted_ranges)
            out.append({
                "kind": "meta_leak",
                "tier": 1,
                "severity": "advisory" if dialogue else "blocking",
                "phrase": m.group(0),
                "range": [start, end],
            })
            continue  # tier1 命中即可,不再叠 tier2
        m = _DEGEN_META_TIER2_RE.search(line)
        if m:
            start, end = b["start"] + m.start(), b["start"] + m.end()
            out.append({
                "kind": "meta_leak",
                "tier": 2,
                "severity": "advisory",
                "phrase": m.group(0),
                "range": [start, end],
            })
    return out


def _degen_truncated(body: list[dict]) -> list[dict]:
    """全文最后一个非空行未以句末/收尾标点结束 → 疑似被模型中途切断。
    phrase/range 取行尾最多 24 字(不经 compact,保证 range 精确指向 phrase,不含全行)。"""
    if not body:
        return []
    last = body[-1]
    if _DEGEN_TRUNCATED_END_RE.search(last["line"]):
        return []
    tail = last["line"][-24:]
    tail_start = last["start"] + len(last["line"]) - len(tail)
    return [{
        "kind": "truncated",
        "severity": "advisory",
        "phrase": tail,
        "range": [tail_start, tail_start + len(tail)],
    }]


def find_degeneration(text: str) -> list[dict]:
    """模型退化指纹汇总检测(report-only):复读/打转 + 占位拒绝语泄漏 + 工程词泄漏
    (tier1/tier2)+ 中途截断。移植自 oh-story check-degeneration.js,阈值/正则逐字对照,
    仅 truncated 的 severity 按方案A任务5要求由 blocking 降级为 advisory。
    返回统一 {"kind","severity","phrase","range"[,"tier"]}。
    """
    s = text or ""
    body = _degen_body_lines(s)
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    out.extend(_degen_adjacent_repeat(body))
    out.extend(_degen_sentence_loop(body))
    out.extend(_degen_placeholders(body))
    out.extend(_degen_meta_leak(body, quoted))
    out.extend(_degen_truncated(body))
    return out


# ==== 方案A任务6:句长方差/burstiness 检测器(find_rhythm_uniformity)====
# GPTZero/DetectGPT/Binoculars 公认头号 AI 破绽:句长分布异常均匀("节拍器")——
# 人类文本天然 bursty(长短句剧烈交替),LLM 默认输出句长收敛。确定性量化,report-only。
#
# 阈值已用 tools/calibrate_rhythm.py 真机标定回填(2026-07-04):经 REST 拉取本机三本已
# 存在库、已人工/流程验收过质量的作品(book_bfd18b78「铜炉试炼·三轮验证」5章、
# book_c256380e「纸命」双POV 4章、main「乱世铜炉·设定参照」18章)共 27 章正文,
# 逐章跑检测器取 CV / mean_adj_ratio 分位数:
#   CV             P10=0.517  P50=0.591  P90=0.776
#   mean_adj_ratio P10=0.550  P50=0.616  P90=0.754
# 取 P10(约 10% 已验收章节比该值更"均匀")作为新地板值——用回填后阈值复核这 27 章,
# 2/27(book_bfd18b78 第1章、main 第18章)恰好落在 P10 边界以下被判 uniform,
# 与"P10=约一成样本比该值更均匀"的定义相符,非阈值算错;report-only/advisory 性质,
# 该假阳性率可接受。样本仅 27 章,后续语料增长应重跑脚本复核阈值。
_RHYTHM_MIN_SENTS = 20     # 句数下限:样本太少 CV 波动大,不判(避免短章误报)
_RHYTHM_CV_FLOOR = 0.517   # 变异系数(sigma/mean)低于此值视为"过于均匀"
_RHYTHM_ADJ_FLOOR = 0.550  # 相邻句长差绝对值均值 / 句长均值,低于此值视为"缺乏突变"


def find_rhythm_uniformity(text: str) -> dict | None:
    """句长方差/burstiness 量化(GPTZero/DetectGPT/Binoculars 公认头号 AI 破绽:句长分布
    异常均匀=节拍器)。report-only,不改写、不阻塞。

    做法:剥引号(_strip_quoted)只算叙述句的可见字长(复用 _DEGEN_VISIBLE_RE,与 A5
    退化检测同口径),按句末标点切句 → 句长序列 → CV(变异系数=标准差/均值)+
    相邻句长差比(缺乏突变的另一侧写照,单独用 CV 会被"逐渐变长的等差数列"骗过)。
    两者都低于阈值才判 verdict="uniform"(节拍器),否则"ok"。
    句数 < _RHYTHM_MIN_SENTS 时样本太薄,直接返回 None(不判,不误报短章/片段)。
    """
    s = _strip_quoted(text or "")
    lens = [n for n in (_degen_visible_length(seg) for seg in re.split(r"[。！？!?…]+", s)) if n > 0]
    if len(lens) < _RHYTHM_MIN_SENTS:
        return None
    mean = sum(lens) / len(lens)
    sigma = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
    cv = sigma / mean if mean else 0.0
    adj = [abs(a - b) for a, b in zip(lens, lens[1:])]
    mean_adj_ratio = (sum(adj) / len(adj) / mean) if adj and mean else 0.0
    verdict = "uniform" if (cv < _RHYTHM_CV_FLOOR and mean_adj_ratio < _RHYTHM_ADJ_FLOOR) else "ok"
    return {"cv": round(cv, 3), "sigma": round(sigma, 1), "mean": round(mean, 1),
            "mean_adj_ratio": round(mean_adj_ratio, 3), "n_sentences": len(lens), "verdict": verdict}


# ==== 方案A任务8:整章 AI 味定档聚合(aggregate_ai_grade)+ 7-Gate 骨架 ====
# 把 quality_flags 的分项确定性命中,聚合成"可决策的章级结论"——写作闭环回炉触发依据。
# report-only,不改文本。指标口径与 7-Gate 映射均来自 oh-story story-deslop SKILL.md
# 附录§H.2。三档阈值(轻/中/重)是【临时标定,待真机校准】,先用宽松值把骨架跑通。
_AI_GRADE_BANNED_LIGHT, _AI_GRADE_BANNED_MEDIUM = 1.0, 3.0        # ①千字禁用词密度
_AI_GRADE_PARALLEL_LIGHT, _AI_GRADE_PARALLEL_MEDIUM = 3, 5        # ②排比/结构复读最大连排数
_AI_GRADE_PSYCH_LIGHT, _AI_GRADE_PSYCH_MEDIUM = 2.0, 5.0          # ③情感直说占句子数百分比
_AI_GRADE_DIALOGUE_LIGHT, _AI_GRADE_DIALOGUE_MEDIUM = 2.0, 4.0    # ④千字对话腔标记密度
_AI_GRADE_REPEAT_LIGHT, _AI_GRADE_REPEAT_MEDIUM = 1.0, 2.0        # ⑥千字复读密度
_AI_GRADE_HEAVY_GATE_COUNT = 4    # oh-story"4+ Gate 有问题=重度",命中≥此数强制 heavy

_GRADE_ORDER = {"light": 0, "medium": 1, "heavy": 2}

# 对话腔调标记:引号收尾紧跟极短"XX说/XX道"型提示语(如「……」他说。/「……」淡淡道,)
_AI_GRADE_DIALOGUE_TAG_RE = re.compile(r"[”」]\s*[^\n。！？]{0,6}(说|道)[。，]")


def _ai_grade_tier(value: float, light_max: float, medium_max: float) -> str:
    """三档判定:value < light_max → light;light_max <= value <= medium_max → medium;
    value > medium_max → heavy(与 6 指标"轻<X/中X-Y/重>Y"的区间语义对齐)。"""
    if value < light_max:
        return "light"
    if value <= medium_max:
        return "medium"
    return "heavy"


def aggregate_ai_grade(flags: dict, text: str, precomputed: dict | None = None,
                       short_mode: bool = False) -> dict:
    """整章 AI 味定档聚合:quality_flags(text) 的分项命中 → 6 指标(千字/占比口径,轻中重
    三档)→ 7-Gate 骨架(A-G)→ 章级 grade(light/medium/heavy)。

    6 指标(oh-story story-deslop SKILL.md AI味6指标):
      ① banned_density   ai_tics 里 banned_word/contextual_word 命中数/千字(可见字数口径)
      ② parallel_run      flags["structural"] + find_parallelism(text) 的最大连排 count
      ③ psych_ratio       find_emotion_telling(text) 命中数 / 句子数(百分比)
      ④ dialogue_tag_density  「XX说/道」型提示语命中数/千字
      ⑤ rhythm_uniform    flags["rhythm"] 的 verdict(ok=轻/uniform=重,无中档;缺失=轻)
      ⑥ repeat_density    (flags["repetition"] + find_duplicate_lines(text) 命中数)/千字

    7-Gate 映射(附录§H.2,A-G 对应禁用词/句式套路/心理告知/节奏均匀/对话腔调/结尾升华/
    解释腔上帝感):详见各 gate_*_hit 计算处注释。

    flags 里缺的键(旧调用方传部分 dict)一律 .get 容错;text 为空/纯空白返回 light 空骨架。

    precomputed(计划A尾巾 A8-Important 修复):调用方(/post-check)在调用本函数前往往
    已经对同一份 text 跑过 find_duplicate_lines/find_emotion_telling/find_parallelism/
    find_poetic_fragments(拼装 duplicate_lines/emotion_telling/parallelism/
    poetic_fragments 等响应字段),本函数原先又对同一 text 重算一遍这四个检测器——
    纯浪费。precomputed 允许调用方把已算好的结果直接传进来复用,键名与上述四个检测器
    同名;缺哪个键就现算哪个,兼容 /check 等没有预算过的旧调用方(不传即整体现算,
    行为与修复前一致)。

    short_mode(方案B任务16):短篇模式开关,透传自 find_emotion_telling。True 时
    ③psych_ratio 强制归零(不管 precomputed 是否带了 emotion_telling 键,short_mode
    整体覆盖——短篇直写情绪不算 AI 味),Gate C(心理告知)因而不会触发。"""
    flags = flags or {}
    text = text or ""
    precomputed = precomputed or {}
    indicator_names = ("banned_density", "parallel_run", "psych_ratio",
                        "dialogue_tag_density", "rhythm_uniform", "repeat_density")
    if not text.strip():
        return {
            "grade": "light",
            "gates": {g: {"hit": False, "count": 0} for g in "ABCDEFG"},
            "gates_hit": [],
            "indicators": {name: {"value": "ok" if name == "rhythm_uniform" else 0, "tier": "light"}
                           for name in indicator_names},
        }

    ai_tics = flags.get("ai_tics") or []
    structural = flags.get("structural") or []
    purple = flags.get("purple") or []
    god_view = flags.get("god_view") or []
    repetition = flags.get("repetition") or []
    rhythm = flags.get("rhythm")

    visible = _degen_visible_length(text)
    per_k = 1000.0 / visible if visible else 0.0

    # ①banned_density
    banned_hits = [h for h in ai_tics if h.get("kind") in ("banned_word", "contextual_word")]
    banned_density = len(banned_hits) * per_k
    banned_tier = _ai_grade_tier(banned_density, _AI_GRADE_BANNED_LIGHT, _AI_GRADE_BANNED_MEDIUM)

    # ②parallel_run:结构复读(anaphora/short 均计,与 find_parallelism 同口径取最大连排数)
    parallelism_hits = (precomputed["parallelism"] if "parallelism" in precomputed
                        else find_parallelism(text))
    parallel_counts = ([s.get("count", 0) for s in structural]
                       + [p.get("count", 0) for p in parallelism_hits])
    parallel_run = max(parallel_counts) if parallel_counts else 0
    parallel_tier = _ai_grade_tier(parallel_run, _AI_GRADE_PARALLEL_LIGHT, _AI_GRADE_PARALLEL_MEDIUM)

    # ③psych_ratio(方案B任务13:改用 emotion_telling_summary 同口径统计,复用其
    # L1+L2 命中计数,不再自己重复一遍"数命中"逻辑;total=len(emotion_hits) 恒成立,
    # 与修复前数值等价——旧调用方文本从无 L2 思想转述模式,l2_count 恒为 0)
    if short_mode:
        emotion_hits: list[dict] = []
    else:
        emotion_hits = (precomputed["emotion_telling"] if "emotion_telling" in precomputed
                        else find_emotion_telling(text))
    emo_summary = emotion_telling_summary(text, hits=emotion_hits)
    sent_count = len([s for s in _SENT_SPLIT.split(text) if s.strip()]) or 1
    psych_ratio = emo_summary["total"] / sent_count * 100
    psych_tier = _ai_grade_tier(psych_ratio, _AI_GRADE_PSYCH_LIGHT, _AI_GRADE_PSYCH_MEDIUM)

    # ④dialogue_tag_density
    dialogue_hits = len(_AI_GRADE_DIALOGUE_TAG_RE.findall(text))
    dialogue_density = dialogue_hits * per_k
    dialogue_tier = _ai_grade_tier(dialogue_density, _AI_GRADE_DIALOGUE_LIGHT,
                                   _AI_GRADE_DIALOGUE_MEDIUM)

    # ⑤rhythm_uniform:二值指标,无中档;None(句数不足未判)按轻处理
    rhythm_verdict = rhythm.get("verdict") if isinstance(rhythm, dict) else None
    rhythm_tier = "heavy" if rhythm_verdict == "uniform" else "light"

    # ⑥repeat_density
    dup_lines = (precomputed["duplicate_lines"] if "duplicate_lines" in precomputed
                else find_duplicate_lines(text))
    repeat_count = len(repetition) + len(dup_lines)
    repeat_density = repeat_count * per_k
    repeat_tier = _ai_grade_tier(repeat_density, _AI_GRADE_REPEAT_LIGHT, _AI_GRADE_REPEAT_MEDIUM)

    indicators = {
        "banned_density": {"value": round(banned_density, 2), "tier": banned_tier},
        "parallel_run": {"value": parallel_run, "tier": parallel_tier},
        "psych_ratio": {"value": round(psych_ratio, 2), "tier": psych_tier},
        "dialogue_tag_density": {"value": round(dialogue_density, 2), "tier": dialogue_tier},
        "rhythm_uniform": {"value": rhythm_verdict or "ok", "tier": rhythm_tier},
        "repeat_density": {"value": round(repeat_density, 2), "tier": repeat_tier},
    }

    # ---- 7-Gate 映射(附录§H.2)----
    # A 禁用词:ai_tics 的 banned_word/contextual_word 命中且 banned_density 达"中"档(含重)
    gate_a_hit = bool(banned_hits) and _GRADE_ORDER[banned_tier] >= _GRADE_ORDER["medium"]

    # B 句式套路:not_a_but_b(否定翻转)+ toxic_pattern(毒句式)+ purple(升华/抒情直陈)
    # 命中数合计 >= 1
    not_a_but_b_hits = [h for h in ai_tics if h.get("kind") == "not_a_but_b"]
    toxic_hits = [h for h in ai_tics if h.get("kind") == "toxic_pattern"]
    gate_b_count = len(not_a_but_b_hits) + len(toxic_hits) + len(purple)
    gate_b_hit = gate_b_count >= 1

    # C 心理告知:psych_ratio 达"中"档(含重)
    gate_c_hit = _GRADE_ORDER[psych_tier] >= _GRADE_ORDER["medium"]

    # D 节奏均匀:rhythm uniform 或 structural.short(极短断句滥用)或 poetic_fragments 命中
    short_structural = [s for s in structural if s.get("kind") == "short"]
    poetic_hits = (precomputed["poetic_fragments"] if "poetic_fragments" in precomputed
                  else find_poetic_fragments(text))
    gate_d_hit = rhythm_verdict == "uniform" or bool(short_structural) or bool(poetic_hits)
    gate_d_count = (1 if rhythm_verdict == "uniform" else 0) + len(short_structural) + len(poetic_hits)

    # E 对话腔调:dialogue_tag_density 达"中"档(含重)
    gate_e_hit = _GRADE_ORDER[dialogue_tier] >= _GRADE_ORDER["medium"]

    # F 结尾升华 / G 解释腔上帝感:god_view 按 kind 拆分,sublimation 归 F,其余归 G
    sublimation_hits = [h for h in god_view if h.get("kind") == "sublimation"]
    other_god_hits = [h for h in god_view if h.get("kind") != "sublimation"]
    gate_f_hit = len(sublimation_hits) >= 1
    gate_g_hit = len(other_god_hits) >= 1

    gates = {
        "A": {"hit": gate_a_hit, "count": len(banned_hits)},
        "B": {"hit": gate_b_hit, "count": gate_b_count},
        "C": {"hit": gate_c_hit, "count": len(emotion_hits)},
        "D": {"hit": gate_d_hit, "count": gate_d_count},
        "E": {"hit": gate_e_hit, "count": dialogue_hits},
        "F": {"hit": gate_f_hit, "count": len(sublimation_hits)},
        "G": {"hit": gate_g_hit, "count": len(other_god_hits)},
    }
    gates_hit = [g for g in "ABCDEFG" if gates[g]["hit"]]

    # grade:6 指标最高档;命中 Gate 数 >= _AI_GRADE_HEAVY_GATE_COUNT 强制 heavy
    # (oh-story"4+ Gate 有问题=重度")。
    tiers = [banned_tier, parallel_tier, psych_tier, dialogue_tier, rhythm_tier, repeat_tier]
    grade = max(tiers, key=lambda t: _GRADE_ORDER[t])
    if len(gates_hit) >= _AI_GRADE_HEAVY_GATE_COUNT:
        grade = "heavy"

    return {"grade": grade, "gates": gates, "gates_hit": gates_hit, "indicators": indicators}


# ==== 方案A任务9(计划A最后一项):标点归一建议生成器(report-only)====
# 移植自 oh-story story-deslop/scripts/normalize-punctuation.js 的
# choosePauseReplacement 上下文判定——但那是全仓唯一会 fs.writeFileSync 落盘改写
# 正文的脚本;scribe3 守 report-only 纪律,这里只出"建议"清单,不动原文一个字符。
#
# 范围刻意收窄到 JS 里"会真正改写成中文标点"的三种确定性情形:
#   ① numeric_range: 数字/汉字数字区间 X——Y(或 X—Y / X--Y)→ 建议"到";
#   ② ellipsis:      句中 ……/ASCII ...(非数字区间)→ 建议"。"或"，"(上下文判定,见下);
#   ③ double_hyphen:  半角双连字符 --(非数字区间)→ 建议"——"或删除(句首/引号后)。
#   ④ 【未移植】JS 原版的冒号分支(前瞻后文出现"因为/原来/答案"等词 → 建议"："):
#     那是改写器语义(替标点重排句子的语气),前瞻词表在中文叙述里误报面大
#     ("因为"作普通连词满地都是),scribe3 守 report-only 纪律宁可漏不滥报,刻意不做。
# 单独出现、不落入以上三类的 ——/—(如纯粹的插入语破折号)刻意不报——那是
# find_ai_tics 的 em_dash 密度门(见 quality_flags["ai_tics"] 里 "kind":"em_dash")
# 已经覆盖的信号,本函数重复上报只会制造噪声;两者可能同位置命中的去重合并
# 留给计划B任务20(finding-merge)按 "kind"+"range" 做,故此处每条建议都带 kind。
_PUNCT_PAUSE_RE = re.compile(r"…+|\.{3,}|——|—|--+")
# 数字区间的"数字"按 oh-story 原意扩展到汉字数字(JS 原版只认 ASCII \d,三——五
# 这种汉字数字区间在中文小说里更常见,故此处一并收纳,不是 JS 的字面直译)。
_PUNCT_DIGIT_RE = re.compile(r"[0-9〇一二三四五六七八九十百千万]")
_PUNCT_OPENING_DELIM_RE = re.compile(r"[「『（(“‘]")
_PUNCT_CLOSING_QUOTE_RE = re.compile(r"[”」』]")
_PUNCT_SENTENCE_END_RE = re.compile(r"[，,。.!！?？;；:：…]")


def _punct_prev_non_space(text: str, idx: int) -> str:
    """从 idx 起向左找第一个非空白字符,取不到返回空串(JS previousNonSpace 移植)。"""
    i = idx
    while i >= 0:
        if not text[i].isspace():
            return text[i]
        i -= 1
    return ""


def _punct_next_non_space(text: str, idx: int) -> str:
    """从 idx 起向右找第一个非空白字符,取不到返回空串(JS nextNonSpace 移植)。"""
    i = idx
    while i < len(text):
        if not text[i].isspace():
            return text[i]
        i += 1
    return ""


def normalize_punctuation_suggestions(text: str) -> list[dict]:
    """标点归一建议生成器(report-only,不改写原文,只出建议清单)。

    引号内(7 对,复用 _quoted_ranges)一律跳过——台词/弹幕里的迟疑省略号、破折号
    是合法演技(角色说话打断/欲言又止),不是 AI 腔标点滥用,只判叙述层。

    返回 list[{"range":[s,e], "original", "suggestion", "reason", "kind"}]。
    suggestion 为空串表示"建议删除"。"""
    s = text or ""
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    for m in _PUNCT_PAUSE_RE.finditer(s):
        start, end = m.start(), m.end()
        if _in_any_span(start, end, quoted):
            continue
        token = m.group(0)
        before = _punct_prev_non_space(s, start - 1)
        after = _punct_next_non_space(s, end)

        # ①数字/汉字数字区间——三种 token(……/——/—/--+)均可能表区间,最优先判定
        # (对齐 JS choosePauseReplacement 把 digit-range 分支放在最前的顺序)。
        if before and after and _PUNCT_DIGIT_RE.match(before) and _PUNCT_DIGIT_RE.match(after):
            out.append({"range": [start, end], "original": token, "suggestion": "到",
                        "reason": "数字区间用'到'", "kind": "numeric_range"})
            continue

        is_ellipsis = "…" in token or token.startswith(".")
        is_double_hyphen = token.startswith("-") and not is_ellipsis

        if is_ellipsis:
            rest = s[end:].lstrip()
            # A9 规格审查补丁:JS choosePauseReplacement 最前面的两条通用短路
            # (double_hyphen 分支已对称实现,此前 ellipsis 分支漏移植)——
            # 段首(before=="")或紧跟开括号/开引号的省略号是多余的开场符号,
            # 直接建议删除,不落入下方句中"。/，"判定(那会误报)。
            if not before or _PUNCT_OPENING_DELIM_RE.match(before):
                suggestion = ""
            elif not rest:
                # 段尾:后面没有任何非空白内容,直接补句号收尾
                # (段首情形已被上方短路接走,此处 before 必非空)。
                suggestion = "。"
            elif _PUNCT_CLOSING_QUOTE_RE.match(rest[0]):
                # 紧跟收尾引号(对齐 JS isClosingQuote 分支):前面已是句末标点
                # 就不重复加句号,否则补句号收尾。
                suggestion = "" if _PUNCT_SENTENCE_END_RE.match(before or "") else "。"
            else:
                # 句中场景:看省略号之后先遇到句末标点(。！？)还是先遇到逗号类
                # 停顿(，,；;)。先遇句末且中途无逗号打断,说明后半截是个紧凑的
                # 独立小句——省略号在此起"场景/时间转折"的句末作用,建议"。";
                # 反之说明还在同一句里延续,省略号只是停顿,建议"，"。
                # (中文没有 JS 原版"后接大写字母=新句"的信号,这是移植时的对应判据。)
                m_end = re.search(r"[。！？]", rest)
                m_comma = re.search(r"[，,；;]", rest)
                if m_end and (not m_comma or m_end.start() < m_comma.start()):
                    suggestion = "。"
                else:
                    suggestion = "，"
            reason = f"省略号规范化为'{suggestion}'" if suggestion else "省略号冗余,建议删除"
            out.append({"range": [start, end], "original": token, "suggestion": suggestion,
                        "reason": reason, "kind": "ellipsis"})
        elif is_double_hyphen:
            # 对齐 JS isOpeningDelimiter 分支:半角双连字符若紧跟句首/开引号,
            # 那是误输入的多余符号,建议删除;否则规范化为全角破折号。
            if not before or _PUNCT_OPENING_DELIM_RE.match(before):
                suggestion, reason = "", "半角双连字符位于句首/引号后,建议删除"
            else:
                suggestion, reason = "——", "半角双连字符规范化为全角破折号"
            out.append({"range": [start, end], "original": token, "suggestion": suggestion,
                        "reason": reason, "kind": "double_hyphen"})
        # else:单独出现的 ——/—(非数字区间、非双连字符)不在本函数范围——
        # 已由 find_ai_tics 的 em_dash 密度门覆盖,见模块顶部说明。
    return out
