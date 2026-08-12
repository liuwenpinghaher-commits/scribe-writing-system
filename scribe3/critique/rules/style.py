"""Critique rules family: style (package C · importable)."""
from __future__ import annotations

from scribe3.critique.rules import repetition as _prev_mod

globals().update({
    k: v for k, v in vars(_prev_mod).items()
    if not k.startswith("__")
})

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
    # 短句要同时满足数量与密度才算滥用：长章里零星的姓名/应答是正常节奏，
    # 不能和几十字内连续碎句同等处罚。2‰ 保留原有短文本高密拦截，放行长章稀疏短句。
    short_per_k = len(short) * 1000 / max(1, len("".join(text.split())))
    if len(short) > max_short and short_per_k > 2:
        out.append({"phrase": "单字/极短断句(如 " + "/".join(short[:5]) + ")", "count": len(short), "kind": "short"})
    return sorted(out, key=lambda x: -x["count"])[:8]


def repair_nested_dialogue_opens(text: str) -> str:
    """修正明确的中文对白右引号缺失。

    双引号尚未闭合又出现新的开引号不是合法嵌套（内层应使用单引号）。若旧开引号
    后已有句末标点，便在第一处句末标点后补右引号；没有句末标点时保守地不动。
    该函数不处理 EOF 悬挂引号，避免猜测作者尚未完成的长对白。
    """
    out: list[str] = []
    open_at: int | None = None
    for ch in text or "":
        if ch == "“":
            if open_at is not None:
                segment = "".join(out[open_at + 1:])
                terminal = re.search(r"[。！？]", segment)
                if terminal:
                    insert_at = open_at + 1 + terminal.end()
                    out.insert(insert_at, "”")
            open_at = len(out)
        elif ch == "”":
            open_at = None
        out.append(ch)
    return "".join(out)


def _strip_dialogue(text: str) -> str:
    """去除文本中被中文弯引号/直角引号包裹的对话片段,返回剩余叙述层文本。
    这是粗略过滤:减少对话内情感词误报(宁可漏检不误报)。"""
    return _DIALOGUE_RE.sub("", text or "")


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


def _ai_tic_rewrite_sentences(text: str, allow: set[str] | None = None) -> list[tuple[str, str]]:
    """把可保义自动处理的 AI 腔命中提升为完整句。

    语境词仍只报告；一级禁词已是质量规则的显式命中，按句交给模型保义改写，但会尊重
    作者白名单。这里处理否定翻转、破折号密集、完整毒句式和一级禁词，且同一句只返回
    一次，供定位器和回滚门共用。
    """
    sents = [s for s in _INTRA_SENT_SPLIT.split(text or "") if s.strip()]
    marked: dict[str, str] = {}
    for hit in find_ai_tics(text, allow_words=allow):
        if hit.get("kind") not in _AUTO_REWRITE_AI_TIC_KINDS:
            continue
        bad = str(hit.get("text") or hit.get("phrase") or "").strip()
        if not bad and hit.get("kind") == "em_dash":
            bad = "——"
        if not bad:
            continue
        # hard_sep_shi（“不是……。是……”）的命中横跨两个句界，不能从逐句列表里
        # 找到完整 bad。把紧随命中的末句标点一并作为一个可替换单元，既保留两句关系，
        # 也满足 _replace_whole_sentence 的句界护栏。
        if hit.get("kind") == "not_a_but_b" and "。" in bad:
            for m in re.finditer(re.escape(bad), text or ""):
                start = max((text or "").rfind(mark, 0, m.start()) for mark in "。！？…\n") + 1
                end = m.end()
                if end < len(text) and text[end] in "。！？…":
                    end += 1
                marked.setdefault(text[start:end].strip(), bad)
            continue
        for s in sents:
            if bad in s:
                marked.setdefault(s.strip(), bad)
                if hit.get("kind") != "em_dash":
                    break
    return list(marked.items())


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


def find_ai_tics(text: str, allow_words: set[str] | None = None) -> list[dict]:
    """AI 腔确定性检测,report-only,分级 blocking/advisory(密度阈值防单词误伤):

    - em_dash:全章破折号密度>2‰(原有,保持不动);
    - not_a_but_b:否定翻转伪深刻句式(原有,经 find_negation_flips,保持不动);
    - banned_word:一级禁用词表(7类,建表见 _BANNED_LEXICON)命中,allow_words 白名单豁免
      (与其在 allow_words 区间相交的命中放行);命中区间落在任一 toxic_pattern 区间内的
      丢弃(只留更完整的 toxic 一条代表,同 A1 惯例,且不计入密度/句子簇);升 blocking 须
      同时满足:千字总密度>craft.banned_density_per_k 且命中分布在 ≥craft.banned_min_sents 个
      不同句子,否则 advisory;
    - contextual_word:二级词(突然/好像/瞬间)合计千字密度>craft.contextual_per_k 且
      ≥craft.contextual_min_hits 处才报,逐个给 range,advisory;
    - toxic_pattern:oh-story 毒句式命中即报 advisory;wandai 类命中≥craft.wandai_block_hits
      处时该类全部升 blocking。
    """
    banned_density_per_k = _th("craft.banned_density_per_k")
    banned_min_sents = _th("craft.banned_min_sents")
    contextual_per_k = _th("craft.contextual_per_k")
    contextual_min_hits = _th("craft.contextual_min_hits")
    wandai_block_hits = _th("craft.wandai_block_hits")
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
        # 取舍:升 blocking 须命中分布在 ≥craft.banned_min_sents 个【不同句子】(按 [。！？\n]
        # 切分)——比「命中总数≥3」更贴合意图(不可被单句击穿),比「wc≥500」不漏判
        # 400 字级真高密段落。
        delims = [m.start() for m in _AI_TIC_SENT_DELIM.finditer(s)]
        hit_sents = {bisect.bisect_left(delims, h["range"][0]) for h in banned_hits}
        severity = ("blocking"
                    if density > banned_density_per_k and len(hit_sents) >= banned_min_sents
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
    # 至少要有 craft.contextual_min_hits 处命中才谈得上密度超阈,防短文本单词误判。
    if (len(contextual_hits) >= contextual_min_hits and wc > 0
            and len(contextual_hits) * 1000 / wc > contextual_per_k):
        out.extend(contextual_hits)

    # toxic_pattern 上报:wandai 类 ≥craft.wandai_block_hits 处升 blocking
    for name, hits in toxic_by_name.items():
        if name == "wandai" and len(hits) >= wandai_block_hits:
            for h in hits:
                h["severity"] = "blocking"
        out.extend(hits)

    return out


def find_oversaturation(text: str, per_k_explain: float | None = None,
                        per_k_emo: float = 5.0, per_k_simile: float = 6.0) -> list[dict]:
    """过度解释/过度饱和检测(每千字密度超保守阈值)。留白引擎的确定性兜底。"""
    per_k_explain = per_k_explain if per_k_explain is not None else _th("craft.oversaturation_per_k")
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


def find_adverb_density(text: str, per_k_max: float | None = None) -> dict | None:
    """副词密度检测(oh-story anti-ai-writing 模式2)。_strip_quoted 后按可见字数
    (_degen_visible_length,复用 A5 口径)计千字密度——单次出现合法,密度超阈才报;
    未超阈或全文无命中返回 None(report-only,advisory 性质)。"""
    per_k_max = per_k_max if per_k_max is not None else _th("craft.adverb_per_k_max")
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


def find_rule_of_three(text: str) -> list[dict]:
    """句内三段式(维基 rule of three)检测:恰好三项顿号并列(全局切分判定,见上方
    模块注释)。引号内(台词/弹幕)豁免——体裁正常形态,只判叙述层;range 覆盖三项
    整体(段内去空白后的起止)。report-only,不做密度门(密度门在 quality_flags/
    quality_issues 聚合处实现,见 _rule_of_three_gated)。"""
    s = text or ""
    quoted = _quoted_ranges(s)
    item_max = _th("craft.rule_of_three_item_max")
    out: list[dict] = []
    for m in _RULE_OF_THREE_SEG_RE.finditer(s):
        seg = m.group(0)
        if "、" not in seg:
            continue
        core = seg.strip()
        items = core.split("、")
        # 恰好三项、每项非空且 1-6 字:≥4 项是铺陈列举,2 项是普通并列,均不报;
        # 任一项超长(如首项带主语状语的长叙述)说明这不是干净的排比分项,也不报。
        if len(items) != 3 or not all(1 <= len(it) <= item_max for it in items):
            continue
        start = m.start() + seg.find(core)
        end = start + len(core)
        if _in_any_span(start, end, quoted):
            continue
        out.append({"phrase": core, "range": [start, end]})
    return out


def _rule_of_three_gated(text: str) -> list[dict]:
    """find_rule_of_three 的报告门:命中千字密度(可见字数口径)须 >craft.rule_of_three_gate_per_k
    才整体上报,否则返回空列表(单次修辞合法,密度才是信号)。"""
    hits = find_rule_of_three(text)
    if not hits:
        return []
    wc = _degen_visible_length(_strip_quoted(text or "")) or 1
    per_k = len(hits) * 1000 / wc
    return hits if per_k > _th("craft.rule_of_three_gate_per_k") else []


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


