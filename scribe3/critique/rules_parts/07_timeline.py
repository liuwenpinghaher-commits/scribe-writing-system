# part 07_timeline (shared namespace; do not import standalone)
def find_intra_chapter_time_conflicts(text: str) -> list[dict]:
    """章内时间标记冲突(第一刀两式):
    ① season_conflict —— 叙述层出现两个不同季节族词(台词/回忆句豁免);
    ② time_regression —— 时辰档后退≥2(台词/回忆豁免,跨日衔接词重置)。
    返回 [{kind, phrase, range, note}],供 /post-check 组装 type="timeline" issue。"""
    s = text or ""
    if not s.strip():
        return []
    quoted = _quoted_ranges(s)

    def _exempt(pos: int, end: int) -> bool:
        if any(a <= pos < b for a, b in quoted):
            return True
        st, en = _sentence_span(s, pos)
        return bool(_MEMORY_RE.search(s[st:en]))

    out: list[dict] = []
    # ① 季节族冲突:首个"与先前族不同"的命中即报一条(全文最多一条,防刷屏)
    seen_fam: dict[str, tuple[str, int]] = {}
    for m in _SEASON_RE.finditer(s):
        if _exempt(m.start(), m.end()):
            continue
        fam = _SEASON_OF[m.group(0)]
        if seen_fam and fam not in seen_fam:
            first_w, first_pos = next(iter(seen_fam.values()))
            out.append({"kind": "season_conflict", "phrase": m.group(0),
                        "range": [m.start(), m.end()],
                        "note": (f"章内季节冲突:前文「{first_w}」(第{first_pos}字起)与"
                                 f"「{m.group(0)}」分属不同季节;若是闪回/跨季过场请忽略")})
            break
        seen_fam.setdefault(fam, (m.group(0), m.start()))
    # ② 时辰倒流:相邻叙述层时辰档后退≥2 且其间无跨日衔接。
    # 真章冒烟(9 达标章 7 误报,全数属三类)后收窄:
    #   a) 跨夜顺行:夜档(≥7)→晨档(≤2)是守夜文常态(深夜→五更=进入新一天);
    #   b) 非时点用法:比喻(像/如/似/仿佛 3字内)、追述系词(前2字含"是")、
    #      参照(后接"前",如"黎明前的黑暗";注:后接"的"不豁免——"正午的日头"是真时点);
    #   c) 复合词/人名(如"柳三更"):前字为汉字且前2字窗无时点引导字 → 词内成分豁免。
    def _non_temporal(mm) -> bool:
        st0, en0 = mm.start(), mm.end()
        pre3, pre2 = s[max(0, st0 - 3):st0], s[max(0, st0 - 2):st0]
        if any(w in pre3 for w in ("像", "如", "似", "仿佛", "好比")):
            return True
        if "是" in pre2:
            return True
        if s[en0:en0 + 1] == "前":
            return True
        pre1 = s[st0 - 1:st0]
        if pre1 and not re.match(r"[\s,。;:!?、「」『』“”‘’]", pre1):
            if not any(w in pre2 for w in ("到", "至", "近", "约", "才", "刚", "已",
                                           "将", "过", "入", "交", "挨", "从", "自", "于")):
                return True
        return False

    prev: tuple[str, int, int] | None = None   # (word, step, end_pos)
    for m in _TIME_RE.finditer(s):
        if _exempt(m.start(), m.end()) or _non_temporal(m):
            continue
        step = _TIME_STEP_OF[m.group(0)]
        if prev is not None:
            pw, ps, pe = prev
            if ps >= 7 and step <= 2:
                prev = (m.group(0), step, m.end())   # a) 跨夜顺行,新的一天
                continue
            if step <= ps - 2 and not _DAY_BREAK_RE.search(s[pe:m.start()]):
                out.append({"kind": "time_regression", "phrase": m.group(0),
                            "range": [m.start(), m.end()],
                            "note": (f"章内时辰倒流:「{pw}」之后出现「{m.group(0)}」且无"
                                     f"跨日衔接(次日/天亮等);若是回叙请补衔接或忽略")})
        prev = (m.group(0), step, m.end())
    return out


# ===== 写作强制闭环 · ConStory 确定性补检(+3)=====
# 对照基线:设计文档/2026-07-05-ConStory19类覆盖对照.md
#  #1 扩:农历月份倒退  #18 proxy:相邻章 pressure 跳变  #7 proxy:帧内否认标记

_MONTH_MAP = {
    "正月": 1, "元月": 1, "一月": 1, "二月": 2, "三月": 3, "四月": 4,
    "五月": 5, "六月": 6, "七月": 7, "八月": 8, "九月": 9, "十月": 10,
    "冬月": 11, "十一月": 11, "腊月": 12, "十二月": 12,
}
_MONTH_RE = re.compile("|".join(sorted(_MONTH_MAP.keys(), key=len, reverse=True)))

# 角色对已知事项的粗否认(需与 known_markers 交叉才报)
_MEMORY_DENIAL_RE = re.compile(
    r"(?:从?来)?不(?:知道|清楚|晓得|明白|记得|知情)|毫无印象|闻所未闻|第一次听说"
)


def find_calendar_month_regression(text: str) -> list[dict]:
    """章内农历/序数月份倒退(ConStory #1 扩:绝对时间标记单调)。

    叙述层出现「正月…腊月」序数,后文月份 < 已达最大月且无跨年衔接词 → 报。
    台词/引号内豁免。纯确定性,report-only。
    """
    s = text or ""
    if not s.strip():
        return []
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    mx = 0
    last_label = ""
    for m in _MONTH_RE.finditer(s):
        if any(a <= m.start() < b for a, b in quoted):
            continue
        label = m.group(0)
        mon = _MONTH_MAP.get(label)
        if mon is None:
            continue
        if mon < mx:
            # 跨年:前文附近有「次年/翌年/来年/转年/又一年」
            window = s[max(0, m.start() - 24):m.start()]
            if re.search(r"次(?:年|岁)|翌年|来年|转年|又一年|第二年", window):
                mx = mon
                last_label = label
                continue
            out.append({
                "kind": "calendar_month_regression",
                "phrase": label,
                "range": [m.start(), m.end()],
                "note": (f"章内月份倒退:前文已至「{last_label}」又见「{label}」"
                         f"且无跨年衔接;若是闪回请补衔接或忽略"),
            })
        else:
            mx = mon
            last_label = label
    return out


def find_pressure_adjacent_jumps(chapters_meta: list[dict], *, threshold: int = 3) -> list[dict]:
    """相邻章 pressure 跳变 |Δ|≥threshold(ConStory #18 基调突变 proxy)。

    chapters_meta: [{seq, pressure}, ...] 缺 pressure 的章跳过不打断相邻对。
    纯确定性;卷级/书级复盘与 post-check 共用。
    """
    entries = sorted(
        (m for m in (chapters_meta or [])
         if m.get("pressure") is not None and m.get("seq") is not None),
        key=lambda m: int(m["seq"]),
    )
    out: list[dict] = []
    for a, b in zip(entries, entries[1:]):
        pa, pb = int(a["pressure"]), int(b["pressure"])
        if abs(pb - pa) >= threshold:
            out.append({
                "kind": "pressure_jump",
                "seq_from": int(a["seq"]),
                "seq_to": int(b["seq"]),
                "pressure_from": pa,
                "pressure_to": pb,
                "delta": pb - pa,
                "note": (f"第{a['seq']}→{b['seq']}章压力级 {pa}→{pb}"
                         f"(|Δ|={abs(pb-pa)}≥{threshold}),基调突变 proxy"),
            })
    return out


def find_memory_denial_hits(text: str, known_markers: list[str] | None = None) -> list[dict]:
    """叙述/对白中对已知标记的否认句(ConStory #7 记忆矛盾半确定 proxy)。

    known_markers: 调用方从限知帧/已揭示 fact 抽出的短标记(≥2 字)。
    同句(。！？换行切)同时命中否认模板 + 任一标记 → 报。
    无标记时返回 [](不裸扫否认,防误报)。
    """
    s = text or ""
    markers = [m for m in (known_markers or []) if m and len(str(m).strip()) >= 2]
    if not s.strip() or not markers:
        return []
    # 按句切
    parts = re.split(r"(?<=[。！？!?\n])", s)
    out: list[dict] = []
    pos = 0
    for part in parts:
        if not part:
            continue
        if _MEMORY_DENIAL_RE.search(part):
            for mk in markers[:24]:
                if mk in part:
                    out.append({
                        "kind": "memory_denial",
                        "phrase": mk,
                        "range": [pos, pos + len(part)],
                        "note": (f"疑似记忆矛盾:同句否认知晓却出现标记「{mk}」;"
                                 f"若是否认第三方请忽略"),
                    })
                    break
        pos += len(part)
    return out


__all__ = ['_ai_grade_tier', '_ai_tic_rewrite_sentences', '_allow_spans', '_cjk_ngrams', '_degen_adjacent_repeat', '_degen_body_lines', '_degen_meta_leak', '_degen_placeholders', '_degen_sentence_loop', '_degen_truncated', '_degen_visible_length', '_extract_flip_end', '_find_positive_flip', '_in_any_span', '_is_allowed', '_merge_spans', '_oversaturation_issues', '_punct_next_non_space', '_punct_prev_non_space', '_quoted_ranges', '_ranges_overlap', '_replace_whole_sentence', '_rule_of_three_gated', '_sentence_span', '_sentence_spans', '_skip_gap', '_split_paragraphs', '_strip_dialogue', '_strip_quoted', '_strip_quoted_with_map', '_structural_issues', '_th', '_valid_rewrite', 'aggregate_ai_grade', 'build_discipline_prompt', 'build_knowledge_extract_prompt', 'build_platform_rubric_prompt', 'build_reasoning_audit_prompt', 'build_reversal_rubric_prompt', 'build_tension_rubric_prompt', 'build_voice_fold_prompt', 'cross_repetition_sentences', 'discipline_truncate', 'distinctive_phrases', 'emotion_telling_summary', 'find_adverb_density', 'find_ai_tics', 'find_cross_chapter_repetitions', 'find_degeneration', 'find_duplicate_lines', 'find_elegant_variation', 'find_emotion_telling', 'find_filler_signals', 'find_god_view', 'find_intra_chapter_time_conflicts', 'find_near_duplicate_paragraphs', 'find_negation_flips', 'find_oversaturation', 'find_parallelism', 'find_poetic_fragments', 'find_purple_prose', 'find_repetitions', 'find_rhythm_uniformity', 'find_rule_of_three', 'find_structural_repeats', 'find_unbalanced_quotes', 'find_watch_regression', 'find_calendar_month_regression', 'find_pressure_adjacent_jumps', 'find_memory_denial_hits', 'intra_repetition_sentences', 'locate_phrase', 'merge_findings', 'merge_verdicts', 'normalize_findings', 'normalize_punctuation_suggestions', 'parse_discipline', 'parse_knowledge_delta', 'parse_platform_report', 'parse_reasoning_audit', 'parse_reversal_report', 'parse_tension_report', 'parse_voice_profile_from_fold', 'quality_flags', 'quality_issues', 'repair_nested_dialogue_opens', 'rewrite_cross_repetitions', 'rewrite_intra_chapter_issues', 'semantic_repair_gate']
