"""Critique rules family: quality (package C · importable)."""
from __future__ import annotations

from scribe3.critique.rules import style as _prev_mod

globals().update({
    k: v for k, v in vars(_prev_mod).items()
    if not k.startswith("__")
})


def _pkg(name: str):
    """Resolve free names from fully-built critique package (package C)."""
    try:
        from scribe3 import critique as _c
        return getattr(_c, name)
    except Exception:
        return globals().get(name)


def _find_positive_flip(candidate: str) -> tuple[int, str] | None:
    """在以"不是"开头的候选串里找肯定翻转点。返回 (候选串内结束下标, variant) 或 None。
    逐字符扫描,移植自 findPositiveFlipEnd(#166 假阳性坑验证过)。对 JS 的唯一主动扩展:
    compact 紧凑分支也查 TAG_PARTICLES(JS 只在软/硬分隔分支查),统一三分支的反问语气词
    口径——「这不是假的是吗」同样是反问尾巴,不该报 compact_shi。"""
    n = len(candidate)
    index = 2  # 跳过"不是"
    scanned = 0
    crossed_separator = False
    max_negative_span = _th("craft.max_negative_span")
    while index < n and scanned <= max_negative_span:
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
    limit = min(len(candidate), marker_end + _th("craft.max_positive_span"))
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


def find_filler_signals(text: str) -> list[dict]:
    """水字数确定性信号检测(rules/story-consistency.md:28)。两类:

    ① same_emotion_run:连续 ≥3 段(按 _split_paragraphs 切段)都命中同一个 _EMO_LABEL
      词 → {"kind":"same_emotion_run","emotion":该情绪词,"paragraphs":[起段号,止段号]}
      (0-indexed,闭区间,同一 run 内只报一条)。
    ② static_scene:单段可见字数(_degen_visible_length)>500,且段内无对话(7 对引号
      _QUOTED_SPANS 任一未命中)、无动作词(_FILLER_ACTION_WORDS)→
      {"kind":"static_scene","paragraph":段号,"chars":可见字数}——疑似停滞场景描写;
      段内一旦有对话或动作词,说明场景仍在推进,不报。

    全 advisory。"全章对话无新信息/连续2章无冲突"两条判据需要通读语义,不在此做
    确定性判定,已挂进 build_reasoning_audit_prompt 的"水字数征兆"节交 LLM 审议。
    """
    paragraphs = _split_paragraphs(text)
    out: list[dict] = []

    # ① same_emotion_run:逐段记它命中的 _EMO_LABEL 词(未命中记 None),再找连续 run。
    para_emo: list[str | None] = [next((w for w in _EMO_LABEL if w in p), None) for p in paragraphs]
    i, n = 0, len(para_emo)
    while i < n:
        emo = para_emo[i]
        if emo is None:
            i += 1
            continue
        j = i
        while j < n and para_emo[j] == emo:
            j += 1
        if j - i >= 3:
            out.append({"kind": "same_emotion_run", "emotion": emo, "paragraphs": [i, j - 1]})
        i = j

    # ② static_scene:单段可见字数超阈 + 无对话 + 无动作词。
    for idx, p in enumerate(paragraphs):
        visible = _pkg("_degen_visible_length")(p)
        if visible <= 500:
            continue
        if any(rx.search(p) for rx in _QUOTED_SPANS):
            continue  # 段内有对话/弹幕,场景仍在推进
        if any(w in p for w in _FILLER_ACTION_WORDS):
            continue  # 段内有动作词,场景仍在推进
        out.append({"kind": "static_scene", "paragraph": idx, "chars": visible})

    return out


def quality_flags(text: str, extra_patterns: list[str] | None = None,
                  allow_words: set[str] | None = None,
                  allow_patterns: list[str] | None = None) -> dict:
    """聚合十一类确定性质检(渲染层兜底)。extra_patterns 来自本书 craft_rule purple_regex;
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
    超 craft.rule_of_three_gate_per_k 才整体上报,否则该章返回空列表——与其余"命中即入列"
    键的语义略有差异,调用方按空列表=无问题的既有惯例读取即可,无需特殊处理。

    "elegant_variation"(同义词循环)因需要角色名单,纯函数层拿不到,不在此聚合——
    接线在 scribe3/app.py 的 /post-check(取 store 角色上下文后调用 find_elegant_variation),
    仅并入 issues,不进 quality_flags。

    "filler"(方案B任务21:水字数确定性信号)键为 find_filler_signals 的命中列表,
    与其余"命中列表"键(repetition/structural/…)同一读取惯例(空列表=无命中)。"""
    return {
        "repetition": _pkg("find_repetitions")(text),
        "structural": _pkg("find_structural_repeats")(text),
        "purple": _pkg("find_purple_prose")(text, extra_patterns, allow_patterns),
        "ai_tics": _pkg("find_ai_tics")(text, allow_words),
        "oversaturation": _pkg("find_oversaturation")(text),
        "god_view": _pkg("find_god_view")(text),
        "degeneration": _pkg("find_degeneration")(text),
        "rhythm": _pkg("find_rhythm_uniformity")(text),
        "adverb": _pkg("find_adverb_density")(text),
        "rule_of_three": _pkg("_rule_of_three_gated")(text),
        "filler": _pkg("find_filler_signals")(text),
    }


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

    # ⑫ 水字数确定性信号(方案B任务21)— same_emotion_run 跨多段、static_scene 是整段
    # 判定,均无法给精确 offset,range=None(前端按 text.indexOf 兜底,同⑨⑩既有惯例)。
    for f in find_filler_signals(s):
        if f["kind"] == "same_emotion_run":
            span = f["paragraphs"][1] - f["paragraphs"][0] + 1
            msg = f"水字数:连续{span}段情绪均为「{f['emotion']}」,疑似情绪停滞不推进"
        else:
            msg = f"水字数:第{f['paragraph']}段场景描写达{f['chars']}字且无对话无动作,疑似停滞"
        issues.append({
            "type": "filler",
            "message": msg,
            "text": "",
            "range": None,
            "meta": f,
        })

    return issues


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


