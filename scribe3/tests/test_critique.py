"""S7 · 移植 scribe2 已验证的确定性 QC 纯函数(无 DB,无网络)。

跨段复读/排比开头/升华句——prompt 规则治不了已生成文本,确定性扫描才拦得住(scribe2 实证)。
"""
from scribe3.critique import (find_purple_prose, find_repetitions,
                              find_structural_repeats, quality_flags)


def test_find_repetitions():
    text = "她在乱葬岗等他" * 4
    reps = find_repetitions(text, n=6, min_count=3)
    assert reps and reps[0]["count"] >= 3


def test_find_structural_repeats_anaphora():
    text = "他想起娘亲。他想起爹爹。他想起家门。他想起旧路。"
    out = find_structural_repeats(text)
    assert any(o["kind"] == "anaphora" for o in out), "同3字开头≥4句=排比"


def test_find_purple_prose():
    out = find_purple_prose("他知道,回不去了。")
    assert out, "升华/主题直陈句应被抓"


def test_quality_flags_aggregates():
    flags = quality_flags("他想起娘亲。他想起爹爹。他想起家门。他想起旧路。")
    assert flags["structural"], "应聚合出结构性问题"
    assert "repetition" in flags and "purple" in flags


from scribe3.critique import find_ai_tics, find_purple_prose


def test_purple_generic_stays():
    """通用升华句(跨题材)仍被抓。"""
    assert find_purple_prose("他知道,回不去了。")


def test_purple_themed_via_extra_patterns():
    """题材升华句(天地为炉)不再硬编码,经 extra_patterns 注入才命中。"""
    text = "炉火映脸,天地为炉,万物为铜。"
    assert not find_purple_prose(text), "题材正则已移出通用层,默认不命中"
    assert find_purple_prose(text, extra_patterns=[r"天地为炉|万物为铜"]), "题材正则经注入命中"


def test_find_ai_tics_em_dash_abuse():
    """E1:全章破折号 > 5。"""
    text = "他——她——它——你——我——他们——又来了"
    hits = find_ai_tics(text)
    assert any(h["kind"] == "em_dash" for h in hits)


def test_find_ai_tics_not_a_but_b():
    """E2:不是A——是B 句式。"""
    hits = find_ai_tics("那不是恐惧——是渴望。")
    assert any(h["kind"] == "not_a_but_b" for h in hits)


def test_quality_flags_includes_ai_tics():
    flags = quality_flags("那不是恐惧——是渴望。")
    assert "ai_tics" in flags


from scribe3.critique import find_oversaturation


def test_oversaturation_explain():
    """解释连接词密集 → explain 项。"""
    text = "这意味着他输了。也就是说没救了。换句话说,正是因为他来晚了。其实是命。"
    hits = find_oversaturation(text, per_k_explain=3.0)
    assert any(h["kind"] == "explain" for h in hits)


def test_oversaturation_emo_label():
    """命名情绪词密集 → emo_label 项。"""
    text = "他愤怒,她悲伤,他恐惧,她绝望,他痛苦,她焦虑。"
    hits = find_oversaturation(text, per_k_emo=5.0)
    assert any(h["kind"] == "emo_label" for h in hits)


from scribe3.critique import distinctive_phrases, find_cross_chapter_repetitions


def test_cross_chapter_repetition_catches_verbatim_reuse():
    """跨章逐字搬运:本章复用前文 ≥8 字独特短语 → 被抓(逐章 QC 的盲区)。"""
    ch1 = "胡不为惨叫一声，那钉尾露在外面，像一截从肉里长出来的骨头，嗡鸣声越来越响。"
    ch2 = "她站在门口。胡不为惨叫一声，钉尾露在外面，像一截白骨。夜色很沉。"
    hits = find_cross_chapter_repetitions(ch2, [ch1], n=8)
    phrases = [h["phrase"] for h in hits]
    assert hits, "应抓到跨章逐字复读"
    assert any("胡不为惨叫一声" in p for p in phrases)
    assert all(h["prior_chapters"] == [0] for h in hits), "命中前文第0章"


def test_cross_chapter_repetition_clean_when_no_reuse():
    """无逐字搬运 → 空(不误报近义改写)。"""
    ch1 = "老槐树下，单嫣望着那枚钉，心知封印将松。"
    ch2 = "暴雨砸在奈何谷，胡不为提着灯笼，脚下泥泞难行。"
    assert find_cross_chapter_repetitions(ch2, [ch1], n=8) == []


def test_cross_chapter_repetition_empty_priors():
    """首章无前文 → 空(不抛)。"""
    assert find_cross_chapter_repetitions("任意正文一段话。", [], n=8) == []


def test_distinctive_phrases_extracts_avoid_list():
    """抽独特措辞供'避免清单':返回若干 ≥8 字、含中文短语,且都是原文的逐字片段。"""
    text = "七月正午的阳光泼在地上，像熔化的铜汁，唯独这棵三百年的老槐撑开一团浓绿。"
    cleaned = "".join(text.split())
    phrases = distinctive_phrases(text, n=8, top=10)
    assert phrases and all(len(p) == 8 for p in phrases)
    assert all(p in cleaned for p in phrases), "每条都是原文逐字片段"
    # 这些片段拼接能复原正文主体(非重叠窗口覆盖)
    assert "".join(phrases) in cleaned


def test_distinctive_phrases_allow_filters_motifs():
    """母题/专名经 allow 白名单排除,不进避免清单(否则逼模型回避母题伤质感)。"""
    text = "他攥着三百六十枚镇煞钉，走进了奈何谷深处的石室墓穴。"
    phrases = distinctive_phrases(text, n=8, top=10, allow={"镇煞钉", "奈何谷"})
    assert all("镇煞钉" not in p and "奈何谷" not in p for p in phrases)


from scribe3.critique import cross_repetition_sentences, rewrite_cross_repetitions


def test_cross_repetition_sentences_locates_offenders():
    """落到句子粒度:含跨章复读短语的句子被定位为改写目标。"""
    ch1 = "胡不为惨叫一声，钉尾露在外面，像一截白骨。"
    ch2 = "夜色很沉。胡不为惨叫一声，钉尾露在外面，他踉跄后退。风穿过空院。"
    tgts = cross_repetition_sentences(ch2, [ch1], n=8)
    assert tgts, "应定位到犯规句"
    assert any("胡不为惨叫一声" in t["sentence"] for t in tgts)
    assert all("phrases" in t and t["phrases"] for t in tgts)


def test_rewrite_cross_repetitions_with_fake_llm_reduces_reps():
    """确定性事后改写:用假 LLM 把犯规句换成不雷同的句子 → 跨章复读降到 0。"""
    ch1 = "胡不为惨叫一声，钉尾露在外面，像一截白骨。"
    ch2 = "天黑了。胡不为惨叫一声，钉尾露在外面，他踉跄后退。"
    def fake_complete(prompt, system=None):
        return "他闷哼着缩起手，那截铁器从血肉里探出，森森发白。"
    res = rewrite_cross_repetitions(ch2, [ch1], fake_complete, n=8)
    assert res["before"] > 0 and res["rewritten"] >= 1
    assert res["after"] < res["before"], "改写后跨章复读应下降"


def test_rewrite_cross_repetitions_noop_when_clean():
    """无跨章复读 → 不调 LLM、原样返回。"""
    called = []
    def fake(p, s=None):
        called.append(1); return "x"
    res = rewrite_cross_repetitions("全新的一段话，毫无雷同。", ["前文完全不同的内容。"], fake, n=8)
    assert res["rewritten"] == 0 and not called


def test_oversaturation_clean_passes():
    """正常克制文本(含'好像/画像'等非比喻)不误报。"""
    text = ("胡不为把钉子收进怀里。雨砸在乱葬岗的烂泥上,溅起细点。"
            "他想起那张旧画像,墙上的影子在动。") * 3
    hits = find_oversaturation(text)
    assert hits == [], f"正常文本不该报饱和:{hits}"


def test_oversaturation_simile_no_false_positive_on_xiang():
    """simile 用精确模式:'好像/图像/想象'不算比喻,'像刀一样'才算。"""
    bad = "好像图像想象好像图像想象好像图像"
    assert not any(h["kind"] == "simile" for h in find_oversaturation(bad))
    good = "冷得像刀子一样。痛得像针扎似的。沉得像铅块般。亮得像白昼一样。" * 2
    assert any(h["kind"] == "simile" for h in find_oversaturation(good, per_k_simile=6.0))


def test_quality_flags_has_oversaturation():
    flags = quality_flags("这意味着结束。也就是说没了。换句话说,其实是命。")
    assert "oversaturation" in flags


from scribe3.critique import build_knowledge_extract_prompt, parse_knowledge_delta


def test_extract_prompt_has_voice_shift():
    p = build_knowledge_extract_prompt("正文")
    assert "voice_shift" in p


def test_parse_voice_shift():
    reply = '{"learned":[],"did":[],"voice_shift":[{"who":"焦三","reason":"被背叛"}]}'
    d = parse_knowledge_delta(reply)
    assert d["voice_shift"] == [{"who": "焦三", "reason": "被背叛"}]
    assert d["learned"] == [] and d["did"] == []


# ==== 批D P1-5: 事件抽取 prompt + 解析 ====

def test_extract_prompt_has_events():
    p = build_knowledge_extract_prompt("正文")
    assert "events" in p


def test_parse_events():
    reply = ('{"learned":[],"did":[],"events":[{"type":"对峙",'
             '"participants":{"SUBJ":"老道","OBJ":"焦三"},"goal":"索丹","caused_by":[]}]}')
    d = parse_knowledge_delta(reply)
    assert len(d["events"]) == 1
    assert d["events"][0]["type"] == "对峙"
    assert d["events"][0]["participants"]["SUBJ"] == "老道"


def test_parse_events_defaults_empty_when_absent():
    """旧模型/旧响应不含 events 字段时默认空列表(向后兼容)。"""
    d = parse_knowledge_delta('{"learned":[],"did":[]}')
    assert d["events"] == []


# ==== F-05: locate_phrase + quality_issues 单测 ====

from scribe3.critique import locate_phrase, quality_issues


def test_locate_phrase_basic():
    """去空白 phrase 能在含空白原文中准确定位。"""
    text = "他端着药碗,知道回不去了。"
    phrase = "他端着药碗"
    hits = locate_phrase(text, phrase)
    assert len(hits) == 1
    s, e = hits[0]
    assert text[s:e] == phrase


def test_locate_phrase_with_whitespace_in_text():
    """text 含换行/空白时,去空白 phrase 仍能正确映射回原始偏移。"""
    text = "他端着\n药碗,知道\n回不去了。"
    phrase = "他端着药碗"
    hits = locate_phrase(text, phrase)
    assert len(hits) == 1
    s, e = hits[0]
    assert "".join(text[s:e].split()) == phrase


def test_locate_phrase_multiple_occurrences():
    """phrase 多处出现各给 range。"""
    text = "镇煞钉在这,镇煞钉在那。"
    phrase = "镇煞钉"
    hits = locate_phrase(text, phrase)
    assert len(hits) == 2
    for s, e in hits:
        assert text[s:e] == phrase


def test_locate_phrase_not_found():
    """找不到返回空列表。"""
    assert locate_phrase("一段正文", "不存在的词语") == []


def test_locate_phrase_range_invariant():
    """返回的每个 [s,e) 满足 0<=s<e<=len(text)。"""
    text = "她在乱葬岗等他" * 4
    phrase = "她在乱葬"
    for s, e in locate_phrase(text, phrase):
        assert 0 <= s < e <= len(text)


def test_quality_issues_not_a_but_b_range():
    """AI腔 not_a_but_b:range 命中原文,prose[s:e] == text。"""
    prose = "那不是恐惧——是渴望。别的不管。"
    issues = quality_issues(prose)
    nab = [i for i in issues if i["type"] == "ai_tics" and i["meta"]["kind"] == "not_a_but_b"]
    assert nab, "应检出 not_a_but_b"
    for iss in nab:
        s, e = iss["range"]
        assert prose[s:e] == iss["text"], f"range 不匹配: {prose[s:e]!r} != {iss['text']!r}"


def test_quality_issues_purple_range():
    """升华句:range 指向原文对应位置(去空白后一致)。"""
    prose = "他知道,回不去了。其他内容。"
    issues = quality_issues(prose)
    purples = [i for i in issues if i["type"] == "purple"]
    assert purples, "应检出升华句"
    for iss in purples:
        if iss["range"] is not None:
            s, e = iss["range"]
            assert "".join(prose[s:e].split()) == "".join(iss["text"].split())


def test_quality_issues_repetition_range():
    """复读:range 指向原文第一处出现,切片非空。"""
    prose = "她在乱葬岗等他" * 4
    issues = quality_issues(prose)
    reps = [i for i in issues if i["type"] == "repetition"]
    assert reps, "应检出复读"
    for iss in reps:
        if iss["range"] is not None:
            s, e = iss["range"]
            assert 0 <= s < e <= len(prose)
            assert len(prose[s:e]) > 0


def test_quality_issues_range_invariant():
    """凡有 range 的 issue,prose[s:e] 去空白 == text 去空白。"""
    prose = ("那不是恐惧——是渴望。他知道,回不去了。" + "她在乱葬岗等他" * 4)
    issues = quality_issues(prose)
    for iss in issues:
        if iss.get("range") is not None:
            s, e = iss["range"]
            assert 0 <= s < e <= len(prose), f"range 越界: {iss}"
            assert "".join(prose[s:e].split()) == "".join(iss["text"].split()), (
                f"range 不一致 type={iss['type']}: prose[{s}:{e}]={prose[s:e]!r} text={iss['text']!r}"
            )


# ==== F-05 进阶: structural / oversaturation 带 offset ====

def test_quality_issues_structural_anaphora_range():
    """结构·排比开头:每个命中句逐句给 range,且 range 指向原文该句、含同 3 字开头。"""
    prose = "他想起娘亲。他想起爹爹。他想起家门。他想起旧路。后续别的内容。"
    issues = quality_issues(prose)
    structs = [i for i in issues if i["type"] == "structural" and i["meta"].get("kind") == "anaphora"]
    assert structs, "应检出排比开头并逐句定位"
    # 至少 4 句(min_anaphora=4),每句 range 命中原文且以「他想起」开头
    for iss in structs:
        s, e = iss["range"]
        assert prose[s:e] == iss["text"]
        assert iss["text"].startswith("他想起")
    assert len(structs) >= 4


def test_quality_issues_structural_short_range():
    """结构·单字/极短断句:逐个短句给 range,prose[s:e] == text。"""
    # 5 个极短句(>max_short=4)触发 short 类
    prose = "走。停。退。冲。逃。后面写一段正常长度的描述凑字数避免误判。"
    issues = quality_issues(prose)
    shorts = [i for i in issues if i["type"] == "structural" and i["meta"].get("kind") == "short"]
    assert shorts, "应检出极短断句滥用并逐处定位"
    for iss in shorts:
        s, e = iss["range"]
        assert prose[s:e] == iss["text"]
        assert 1 <= len("".join(iss["text"].split())) <= 2


def test_quality_issues_oversaturation_range():
    """过饱和·解释词:超阈值后逐处命中给 range,prose[s:e] == text。"""
    prose = "这意味着没用。这意味着完了。这意味着结束。这意味着重来。这意味着如此。"
    issues = quality_issues(prose, None)
    over = [i for i in issues if i["type"] == "oversaturation"]
    assert over, "解释词密度超阈值应逐处定位"
    for iss in over:
        s, e = iss["range"]
        assert prose[s:e] == iss["text"]


def test_quality_issues_structural_range_invariant():
    """structural / oversaturation 也满足全局 range 不变量。"""
    prose = ("他想起娘亲。他想起爹爹。他想起家门。他想起旧路。"
             "这意味着没用。这意味着完了。这意味着结束。这意味着重来。")
    issues = quality_issues(prose, None)
    types_seen = {i["type"] for i in issues if i.get("range") is not None}
    assert "structural" in types_seen
    for iss in issues:
        if iss.get("range") is not None:
            s, e = iss["range"]
            assert 0 <= s < e <= len(prose), f"range 越界: {iss}"
            assert "".join(prose[s:e].split()) == "".join(iss["text"].split())


# ==== M2: find_duplicate_lines + find_emotion_telling ====

from scribe3.critique import find_duplicate_lines, find_emotion_telling


class TestFindDuplicateLines:
    """find_duplicate_lines(text, min_chars=8) -> list[{"line": str, "count": int}]"""

    def test_exact_duplicate_line_caught(self):
        """整行精确复读2次 -> 命中 count=2。"""
        text = "天,终于亮了。\n\n天,终于亮了。"
        hits = find_duplicate_lines(text)
        assert hits, "应检出精确复读"
        assert any(h["line"] == "天,终于亮了。" and h["count"] == 2 for h in hits)

    def test_no_duplicate_returns_empty(self):
        """无重复行 -> 空列表。"""
        text = "天渐渐亮了。\n\n雨终于停了。"
        assert find_duplicate_lines(text) == []

    def test_short_line_not_reported(self):
        """短于 min_chars 的行不误报(即使重复)。"""
        text = "走。\n走。\n走。"
        hits = find_duplicate_lines(text, min_chars=8)
        assert hits == [], f"短行不应报告:{hits}"

    def test_pure_punctuation_not_reported(self):
        """纯标点/空串不误报。"""
        text = "。\n。\n。\n——\n——\n——"
        hits = find_duplicate_lines(text, min_chars=8)
        assert hits == [], f"纯标点不应报告:{hits}"

    def test_triplicate_reports_correct_count(self):
        """同行出现3次 -> count=3。"""
        line = "他端着药碗,站在廊下不动。"
        text = "\n".join([line] * 3)
        hits = find_duplicate_lines(text)
        assert hits
        match = [h for h in hits if h["line"] == line]
        assert match and match[0]["count"] == 3

    def test_results_sorted_by_count_desc(self):
        """返回结果按 count 降序。"""
        line_a = "她在乱葬岗等他,直到天光大亮。"
        line_b = "风从门缝里挤进来,带着腥气。"
        text = "\n".join([line_a] * 3 + [line_b] * 2)
        hits = find_duplicate_lines(text)
        assert len(hits) >= 2
        assert hits[0]["count"] >= hits[1]["count"]

    def test_sentence_split_within_line(self):
        """同一段落内句末切分:句子重复也能检出。"""
        text = "他抬头看了看天。他抬头看了看天。"
        hits = find_duplicate_lines(text)
        assert hits, "句内重复句应检出"

    def test_whitespace_normalized(self):
        """首尾空白归一化后比较:带多余空格的同行应合并计数。"""
        text = "  天,终于亮了。  \n天,终于亮了。\n  天,终于亮了。  "
        # min_chars 用默认值(6),允许 7 字符句通过
        hits = find_duplicate_lines(text)
        assert hits
        assert any(h["count"] == 3 for h in hits)


class TestFindEmotionTelling:
    """find_emotion_telling(text) -> list[{"span": str, "kind": str}]"""

    def test_emotion_word_caught(self):
        """情绪直说:他感到一阵恐惧 -> 命中 emotion_word。"""
        hits = find_emotion_telling("他感到一阵恐惧,转身就跑。")
        assert hits, "应检出情绪直说"
        assert any(h["kind"] == "emotion_word" for h in hits)

    def test_verdict_caught(self):
        """直接评语:他不是个坏人 -> 命中 verdict。"""
        hits = find_emotion_telling("他不是个坏人,只是走错了路。")
        assert hits, "应检出直接评语"
        assert any(h["kind"] == "verdict" for h in hits)

    def test_pure_action_no_hit(self):
        """纯动作物象:他攥紧了拳头,后背沁出冷汗 -> 不命中。"""
        hits = find_emotion_telling("他攥紧了拳头,后背沁出冷汗。")
        assert hits == [], f"纯动作不应触发:{hits}"

    def test_dialogue_emotion_not_telling(self):
        """对话内情感词:角色说的话里有情感词 -> 不算叙述层 telling。"""
        # 用原始字符串避免 Python 引号冲突；“” 是中文双引号
        text = "她颤声说：“我感到害怕。”"
        hits = find_emotion_telling(text)
        assert hits == [], f"对话内情感词不应误报:{hits}"

    def test_juede_variant(self):
        """觉得变体:她觉得难过。"""
        hits = find_emotion_telling("她觉得难过,眼眶发红。")
        assert hits

    def test_xinli_variant(self):
        """心里变体:他心里一阵愧疚。"""
        hits = find_emotion_telling("他心里一阵愧疚,迈不开步。")
        assert hits

    def test_she_verdict(self):
        """评语用她:她是个好人。"""
        hits = find_emotion_telling("她是个好人,从来不计较。")
        assert hits
        assert any(h["kind"] == "verdict" for h in hits)

    def test_cliche_optional(self):
        """标签化生理-情感套语(cliche):心里像被什么揪住 -> 返回(kind='cliche'或emotion_word均可)。"""
        hits = find_emotion_telling("他心里像被什么揪住,说不出话。")
        # cliche 是 weak 命中,实现可选;若返回则 kind 须合规
        if hits:
            assert hits[0]["kind"] in ("emotion_word", "cliche")

    def test_multiple_variants_in_text(self):
        """多处 telling -> 每处都检出。"""
        text = "他感到恐惧。她觉得悲伤。他不是个坏人。"
        hits = find_emotion_telling(text)
        assert len(hits) >= 2, f"应检出>=2处telling:{hits}"

    def test_span_field_present(self):
        """返回值有 span 字段且非空。"""
        hits = find_emotion_telling("他感到绝望,瘫坐在地。")
        assert hits
        assert all("span" in h and h["span"] for h in hits)


class TestFindParallelism:
    """排比/同句式≥3连检测器(堵 AI 抒情腔,opus 评判反复点名)。"""

    def test_anaphora_run_detected(self):
        from scribe3.critique import find_parallelism
        t = "就像她没待过，就像她没剔过纸鸢，就像她没见过指骨。"
        hits = find_parallelism(t)
        assert any(h["prefix"] == "就像" and h["count"] >= 3 for h in hits), hits

    def test_normal_prose_no_false_positive(self):
        from scribe3.critique import find_parallelism
        t = "柳怀玉捏着竹篾。门外站着青衣女子。河水拍打着岸边的石头。"
        assert find_parallelism(t) == []

    def test_two_run_not_flagged(self):
        from scribe3.critique import find_parallelism
        t = "穿过人群，穿过花香。"  # 仅2连,不足min_run=3
        assert find_parallelism(t) == []


class TestSceneDetectors:
    """诗化分行/拟声煞尾 + 引号配对 + 更次倒退(opus评判揪出的机制硬伤)。"""

    def test_onomatopoeia_ending(self):
        from scribe3.critique import find_poetic_fragments
        t = "他站在黑暗里。\n咔——\n咔——\n咔——"
        pf = find_poetic_fragments(t)
        assert any(x["kind"] == "onomatopoeia" for x in pf)
        assert any(x["ending"] for x in pf), "末行拟声应标 ending"

    def test_dialogue_not_flagged(self):
        from scribe3.critique import find_poetic_fragments
        t = '“是。”\n“不急。”'
        assert find_poetic_fragments(t) == [], "对白不应判为诗化碎句"

    def test_watch_regression(self):
        from scribe3.critique import find_watch_regression
        assert find_watch_regression("四更天了。后来三更天。")
        assert find_watch_regression("四更天了。天快亮了,五更。") == []

    def test_unbalanced_quotes(self):
        from scribe3.critique import find_unbalanced_quotes
        assert find_unbalanced_quotes("他说“进来")
        assert find_unbalanced_quotes("他说“进来罢。”") == []


# ==== Task9 M2a: 张力检查 rubric prompt + 解析(纯函数,不打 LLM)====

def test_tension_rubric_prompt_and_parse():
    from scribe3.critique import build_tension_rubric_prompt, parse_tension_report
    p = build_tension_rubric_prompt("……正文……")
    for k in ("dramatic_question", "outcomes", "value_shift", "micro_tension", "hook"):
        assert k in p
    rep = parse_tension_report(
        '{"dramatic_question":{"present":true,"answered_escalated":true,"note":"能否验尸"},'
        '"outcomes":[{"scene":"义庄对峙","type":"yes_but"}],'
        '"value_shift":{"present":true,"note":"信任→怀疑"},'
        '"micro_tension":{"deserts":[]},'
        '"hook":{"present":true,"type":"信息截断","strength":"strong"}}')
    assert rep["dramatic_question"]["present"] is True
    assert parse_tension_report("垃圾") is None


def test_parse_tension_report_robust_to_bad_json():
    from scribe3.critique import parse_tension_report
    assert parse_tension_report("") is None
    assert parse_tension_report(None) is None
    # 截断/坏 JSON:提到 { 但 json.loads 失败 → None(镜像 parse_knowledge_delta)
    assert parse_tension_report('{"dramatic_question":{"present":tru') is None
    # 前后有解说文字但内含合法 JSON 块 → 仍能提取
    rep = parse_tension_report('好的,报告如下:{"hook":{"present":true}} 完毕')
    assert rep is not None and rep["hook"]["present"] is True


# ==== 方案A任务1:否定翻转 4+3 变体检测器(find_negation_flips) ====

class TestNegationFlips:
    """否定翻转 4 变体 + 维基 3 变体 + 结构性护栏(oh-story check-ai-patterns.js 移植)。"""

    # —— 4 变体正例 ——
    def test_compact_ershi(self):
        from scribe3.critique import find_negation_flips
        assert any(h["variant"] == "compact_ershi"
                   for h in find_negation_flips("这不是逃避而是选择。"))

    def test_soft_sep_shi(self):
        from scribe3.critique import find_negation_flips
        hits = find_negation_flips("这不是结束，是开始。")
        assert hits and hits[0]["range"] is not None

    def test_hard_sep_shi(self):
        from scribe3.critique import find_negation_flips
        assert find_negation_flips("这不是恐惧。是愤怒。")

    def test_compact_shi(self):
        from scribe3.critique import find_negation_flips
        assert find_negation_flips("那不是灯火是磷光。")

    def test_legacy_dash_still_caught(self):
        from scribe3.critique import find_negation_flips
        assert find_negation_flips("不是风声——是脚步声。")

    # —— 结构性护栏负例(照搬 oh-story,别自己发明) ——
    def test_shibushi_question_skipped(self):
        from scribe3.critique import find_negation_flips
        assert not find_negation_flips("你说这是不是天意?")

    def test_conjunction_after_sep_skipped(self):
        from scribe3.critique import find_negation_flips
        # 跨分隔符后首字非「是/而」不判:但是/还是/于是 的尾「是」是连词
        assert not find_negation_flips("他不是英雄，但是他很勇敢。")

    def test_either_or_skipped(self):
        from scribe3.critique import find_negation_flips
        assert not find_negation_flips("他不是疯了就是傻了。")

    def test_double_negation_skipped(self):
        from scribe3.critique import find_negation_flips
        assert not find_negation_flips("这不是雨，也不是雪。")

    def test_tag_particle_skipped(self):
        from scribe3.critique import find_negation_flips
        assert not find_negation_flips("你不是早知道了吗?")

    # —— 维基三变体 ——
    def test_bujin_erqie(self):
        from scribe3.critique import find_negation_flips
        assert any(h["variant"] == "bujin" for h in find_negation_flips("他不仅救了人，而且分文不取。"))

    def test_erfei(self):
        from scribe3.critique import find_negation_flips
        assert any(h["variant"] == "erfei" for h in find_negation_flips("他要的是命，而非钱。"))

    def test_yuqishuo(self):
        from scribe3.critique import find_negation_flips
        assert any(h["variant"] == "yuqishuo" for h in find_negation_flips("与其说是庙，不如说是坟。"))
