"""移植自 scribe2/critique.py 的确定性 QC 纯函数(已验证资产)。

跨段复读/排比开头/单字断句/升华句——prompt 规则治不了已生成文本,确定性扫描+定向删才拦得住。
纯函数(无 DB/无网络),作渲染层质检兜底。语义级违规(双高潮/声音崩)是另一路(LLM 判官,后续)。
"""
import json
import logging
import re

_log = logging.getLogger("scribe3.critique")

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
    wc = len("".join((text or "").split()))
    if wc > 0 and dash * 1000 / wc > 2:
        out.append({"kind": "em_dash", "count": dash})
    for m in _NOT_A_BUT_B.finditer(text or ""):
        out.append({"kind": "not_a_but_b", "phrase": m.group(0)})
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


def quality_flags(text: str, extra_patterns: list[str] | None = None) -> dict:
    """聚合五类确定性质检(渲染层兜底)。extra_patterns 来自本书 craft_rule purple_regex。"""
    return {
        "repetition": find_repetitions(text),
        "structural": find_structural_repeats(text),
        "purple": find_purple_prose(text, extra_patterns),
        "ai_tics": find_ai_tics(text),
        "oversaturation": find_oversaturation(text),
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


def quality_issues(text: str, extra_patterns: list[str] | None = None) -> list[dict]:
    """五类 QC 的"带 offset"展开形式(与 quality_flags 并存)。
    仅对"白送类"(finditer 直接给 offset)和"去空白 n-gram 可 locate_phrase"的类别补 range。
    返回结构: {type, message, text, range:[start,end], meta}。
    range 为 None 表示无法定位(前端兜底用 text.indexOf 回退)。
    """
    issues: list[dict] = []
    s = text or ""

    # ① AI 腔 · not_a_but_b — 白送:finditer 直接给 offset
    for m in _NOT_A_BUT_B.finditer(s):
        issues.append({
            "type": "ai_tics",
            "message": "AI腔:「不是A——是B」伪深刻句式",
            "text": m.group(0),
            "range": [m.start(), m.end()],
            "meta": {"kind": "not_a_but_b"},
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

    # ③ 升华 · purple — 整句 locate,逐句给 offset
    pats = list(_PURPLE_RE) + [re.compile(p) for p in (extra_patterns or [])]
    for sent in re.split(r"(?<=[。！？\n])", s):
        st = sent.strip()
        if not st:
            continue
        if any(rx.search(st) for rx in pats):
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
    """张力盲评 prompt:戏剧问题/结局语法/价值反转/微张力荒漠/续读钩子,单次调用合并评审。"""
    return (
        "你是叙事张力评审。读下面一章小说正文,只输出一个 JSON(不要任何其他文字):\n"
        '{"dramatic_question":{"present":布尔,"answered_escalated":布尔,"note":一句},'
        '"outcomes":[{"scene":场景一句概括,"type":"yes"|"yes_but"|"no_and"|"no"}],'
        '"value_shift":{"present":布尔,"note":"哪个价值从什么极翻到什么极"},'
        '"micro_tension":{"deserts":[连续500字以上无POV情绪对立/念头交战的段落开头8字]},'
        '"hook":{"present":布尔,"type":"危险临近|信息截断|选择悬置|反转|不祥预示|无","strength":"strong"|"soft"}}\n'
        "判定标准:dramatic_question=本章是否有一个悬着的小问题且章末被回答并升级;"
        "outcomes=各场景结局语法(顺利达成记 yes——它是泄气信号);"
        "value_shift=至少一场发生价值极性反转;hook=章末最后几行是否有续读钩子。\n\n"
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


def _strip_dialogue(text: str) -> str:
    """去除文本中被中文弯引号/直角引号包裹的对话片段,返回剩余叙述层文本。
    这是粗略过滤:减少对话内情感词误报(宁可漏检不误报)。"""
    return _DIALOGUE_RE.sub("", text or "")


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
    """
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


def find_emotion_telling(text: str) -> list[dict]:
    """检测叙述层直陈情绪/直接评语的句子(确定性正则,宁缺勿滥)。

    规则:
    - emotion_word: (他|她|它)?(感到|觉得|心里|心中|心头)(一阵|一)?(情绪词)
    - verdict:      (他|她)(其实)?(不是|是)(个)?(坏人|好人|善人|恶人)
    - cliche(weak): 心里像被什么(揪|攥|堵)住 等标签化套语

    对话内情感词处理:粗略去除中文弯引号包裹片段后再扫描(减少误报)。
    返回 [{"span": <命中片段>, "kind": "emotion_word"|"verdict"|"cliche"}]。
    """
    s = _strip_dialogue(text or "")
    out: list[dict] = []

    for m in _EMOTION_WORD_RE.finditer(s):
        out.append({"span": m.group(0), "kind": "emotion_word"})

    for m in _VERDICT_RE.finditer(s):
        out.append({"span": m.group(0), "kind": "verdict"})

    for m in _CLICHE_RE.finditer(s):
        # 避免与 emotion_word 重叠上报
        span = m.group(0)
        if not any(r["span"] in span or span in r["span"] for r in out):
            out.append({"span": span, "kind": "cliche"})

    return out
