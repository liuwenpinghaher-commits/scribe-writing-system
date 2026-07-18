"""S7 · 移植 scribe2 已验证的确定性 QC 纯函数(无 DB,无网络)。

跨段复读/排比开头/升华句——prompt 规则治不了已生成文本,确定性扫描才拦得住(scribe2 实证)。
"""
from scribe3.critique import (find_purple_prose, find_repetitions,
                              find_structural_repeats, merge_findings,
                              quality_flags)


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


# —— 章内精修治层(intra):章内 repetition / duplicate_lines / 排比,与跨章 dedup 对称 ——
from scribe3.critique import intra_repetition_sentences, rewrite_intra_chapter_issues


def test_intra_locates_duplicate_line_keeps_first():
    """整句一字不差重复 → 首现豁免、只标记后续一处。"""
    text = "沈砚摆了摆手，没让他说。风从门缝里挤进来。沈砚摆了摆手，没让他说。"
    marked = [t["sentence"] for t in intra_repetition_sentences(text)]
    assert sum(m == "沈砚摆了摆手，没让他说。" for m in marked) == 1


def test_intra_locates_parallelism_keeps_two():
    """连续排比开头(前3字相同≥4句)→ 保前2、其余标记打散。"""
    text = "他抬起手，摸向后颈。他抬起眼，看着来人。他抬起脚，跨过门槛。他抬起头，望了望天。"
    tgt = intra_repetition_sentences(text)
    assert len(tgt) == 2 and all("排比" in t["hint"] for t in tgt)


def test_rewrite_intra_reduces_intra_repetition_with_fake_llm():
    """假 LLM 把章内复读句换掉 → 章内硬伤下降。"""
    text = ("他伸手去摸那道疤，凉丝丝的。风停了。他伸手去摸那道疤，凉丝丝的。"
            "灯灭了。他伸手去摸那道疤，凉丝丝的。")
    def fake(prompt, system=None):
        return "指腹擦过那处旧痕，像触到一片冷铁。"
    res = rewrite_intra_chapter_issues(text, fake)
    assert res["before"] > 0 and res["rewritten"] >= 1 and res["after"] < res["before"]


def test_rewrite_intra_dedups_duplicate_line():
    """整句重复被改写消除:不再有一字不差的重复行。"""
    from scribe3.critique import find_duplicate_lines
    text = "沈砚摆了摆手，没让他说。别的话在这里说着。沈砚摆了摆手，没让他说。"
    def fake(prompt, system=None):
        return "他压下手，把话按了回去。"
    res = rewrite_intra_chapter_issues(text, fake)
    assert res["rewritten"] >= 1 and len(find_duplicate_lines(res["prose"])) == 0


def test_rewrite_intra_noop_when_clean():
    """无章内硬伤 → 不调 LLM、原样返回。"""
    called = []
    def fake(p, s=None):
        called.append(1); return "x"
    res = rewrite_intra_chapter_issues("清爽的一段，各句各表，写得毫不重样。", fake)
    assert res["rewritten"] == 0 and res["before"] == 0 and not called


def test_rewrite_intra_system_prompt_guards_limited_knowledge():
    """改写器 system 必须含限知/悬念守护——改写同样可能泄密(S-002 延续)。"""
    text = "沈砚摆了摆手，没让他说。风从门缝里挤进来。沈砚摆了摆手，没让他说。"
    seen = {}
    def fake(prompt, system=None):
        seen["sys"] = system or ""
        return "他压下手，把话按了回去。"
    rewrite_intra_chapter_issues(text, fake)
    assert "限知" in seen["sys"] and ("悬念" in seen["sys"] or "秘密" in seen["sys"])


def test_find_near_duplicate_paragraphs_catches_reworded():
    """近似段落重复(换几字重写同一画面)被检出,补精确检测器盲区(S-005;取材自真实第3章 89/91)。"""
    from scribe3.critique import find_near_duplicate_paragraphs
    a = "他坐在那里，看着门缝里的光慢慢移，从棺盖移到灶台，又从灶台移到他的鞋尖，鞋面上沾了点黑泥，是刚才捡纸钱时蹭的，已经干结，布着细碎的裂纹。"
    b = "他坐在条凳上，看着门缝里的光慢慢移，从棺盖移到灶台，又从灶台移到他的鞋尖。鞋面上沾了点黑泥，是刚才捡纸钱时蹭上的，此刻已经干透，表面绽出细密的裂纹。"
    text = a + "\n\n中间隔着一段完全不同的内容，讲的是别的人别的事，推动情节往前走了好一阵。\n\n" + b
    nd = find_near_duplicate_paragraphs(text)
    assert len(nd) >= 1 and nd[0]["sim"] >= 0.7


def test_find_near_duplicate_catches_sentence_level():
    """句子级近似重复(相邻句前半全同、后半改几字)也被抓——补段落级 40 阈值盲区(S-008,取材结局章)。"""
    from scribe3.critique import find_near_duplicate_paragraphs
    a = "他躺在自己的棺材里，手里的纸团硬邦邦的，是他此刻仅有的实在触感。"
    b = "他躺在自己的棺材里，手里的纸团硬邦邦的，是他还能攥住的唯一东西。"
    text = a + "\n\n柏木棺盖越来越烫，树脂被烤得渗出来，顺着棺壁的纹路往下淌。\n\n" + b
    nd = find_near_duplicate_paragraphs(text)
    assert len(nd) >= 1


def test_rewrite_intra_rollback_when_rewrite_worsens():
    """回滚门:改写消了排比却造出等量新整句重复(after≥before)→ 整体回退,不落更差版本(review P1-2)。"""
    text = "他抬起手，摸后颈。他抬起眼，看门口。他抬起脚，跨门槛。他抬起头，望天色。"
    def fake_dup(prompt, system=None):
        return "外面的天，慢慢亮了起来。"  # 排比句都改成同一句 → 排比消失但造出整句重复
    res = rewrite_intra_chapter_issues(text, fake_dup)
    assert res["rewritten"] == 0 and res["prose"] == text


def test_rewrite_intra_rejects_english_garbage():
    """改写混入英文占位词(someone)→ 弃用保留原句,英文异物不进正文(S-004)。"""
    text = "沈砚摆了摆手，没让他说。别的话在这里说着。沈砚摆了摆手，没让他说。"
    def fake_eng(prompt, system=None):
        return "他压下手，把话按回去，someone 在旁边看着。"
    res = rewrite_intra_chapter_issues(text, fake_eng)
    assert "someone" not in res["prose"]


def test_intra_motif_allow_all_branches():
    """allow 母题白名单在 duplicate 分支同样生效,不误改刻意复现的谶语(review P2-4)。"""
    text = "镇煞钉钉住的是命。张三那天走了很远的路。镇煞钉钉住的是命。"
    tgt = intra_repetition_sentences(text, allow={"镇煞钉"})
    assert not any("镇煞钉钉住的是命" in t["sentence"] for t in tgt)


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


class TestAiTicsLexicon:
    def test_tier1_word_hit_with_category(self):
        # 文本须避开毒句式区间——「眼中闪过一丝狡黠」整段归 toxic_pattern,
        # 其内部的 banned 命中会被重叠去重丢弃(见 test_banned_inside_toxic_deduped)。
        hits = find_ai_tics("她隐约露出几分狡黠。")
        kinds = {(h["kind"], h.get("category")) for h in hits}
        assert ("banned_word", "形容类") in kinds or ("banned_word", "情态类") in kinds

    def test_density_escalates_to_blocking(self):
        t = "他心中一动。她心头一震。他心下了然。她心中暗道。" * 3
        assert any(h.get("severity") == "blocking" for h in find_ai_tics(t))

    def test_isolated_hit_is_advisory(self):
        t = "他深吸一口气。" + "这是一段很长的普通叙述。" * 40
        hits = [h for h in find_ai_tics(t) if h["kind"] == "banned_word"]
        assert hits and all(h["severity"] == "advisory" for h in hits)

    def test_allow_words_exempt(self):
        # 世界观术语「凛冽刀」含一级词「凛冽」,白名单放行
        assert not [h for h in find_ai_tics("他拔出凛冽刀。", allow_words={"凛冽刀"})
                    if h["kind"] == "banned_word"]

    def test_short_text_single_hit_stays_advisory(self):
        """短文本单次命中不升 blocking:「他不禁打了个寒颤。」wc=9,密度 111‰>3‰,
        但孤立 1 处命中不构成"密度"现象(/check 端点常传很短的编辑片段)。"""
        hits = [h for h in find_ai_tics("他不禁打了个寒颤。") if h["kind"] == "banned_word"]
        assert hits and all(h["severity"] == "advisory" for h in hits)

    def test_single_sentence_cluster_stays_advisory(self):
        """单句击穿防护:一句内命中 3+ 词不算"密度现象",升 blocking 须命中分布在
        ≥craft.banned_min_sents 个不同句子(按 [。！？\n] 切分)。"""
        # 协调审查锁定用例:「眼中闪过一丝狡黠」句(banned 与 toxic 重叠部分已被去重丢弃)
        t = "她眼中闪过一丝狡黠。" + "这是一段很长的普通叙述。" * 40
        hits = [h for h in find_ai_tics(t) if h["kind"] == "banned_word"]
        assert all(h["severity"] == "advisory" for h in hits)
        # 无 toxic 干扰的单句 4 命中(不禁/隐约/几分/狡黠)同样不升 blocking
        t2 = "他不禁隐约觉出几分狡黠。" + "这是一段很长的普通叙述。" * 40
        hits2 = [h for h in find_ai_tics(t2) if h["kind"] == "banned_word"]
        assert hits2 and all(h["severity"] == "advisory" for h in hits2)
        # 对照:命中分散在 3+ 句的高密文本 → blocking
        t3 = "他心中一动。她心头一震。他心下了然。"
        hits3 = [h for h in find_ai_tics(t3) if h["kind"] == "banned_word"]
        assert hits3 and all(h["severity"] == "blocking" for h in hits3)

    def test_banned_inside_toxic_deduped(self):
        """banned 命中区间落在 toxic_pattern 区间内 → 丢弃 banned,只留更完整的 toxic
        一条代表(同 A1 惯例);丢弃的命中不计入密度/句子簇计数。"""
        hits = find_ai_tics("她眼中闪过一丝狡黠。")
        toxic = [h for h in hits if h["kind"] == "toxic_pattern"]
        banned = [h for h in hits if h["kind"] == "banned_word"]
        assert toxic, "毒句式应命中"
        # 该句 3 个 banned 词(眼中闪过/一丝/狡黠)全在 toxic 区间内,应全部被丢弃
        assert banned == [], f"toxic 区间内的 banned 应去重:{banned}"

    def test_toxic_pattern_hit(self):
        assert any(h["kind"] == "toxic_pattern" for h in find_ai_tics("她的声音不大，却带着一种不容置疑的力量。"))

    def test_simile_words_not_duplicated(self):
        # 比喻词归 find_oversaturation,find_ai_tics 不报
        assert not [h for h in find_ai_tics("山影仿佛巨兽。") if h["kind"] == "banned_word"]

    def test_contextual_tier2_density_only(self):
        assert not [h for h in find_ai_tics("突然,门开了。") if h["kind"] == "contextual_word"]
        t = "突然一声。好像有人。瞬间黑了。突然又响。好像更近。瞬间又亮。" * 4
        assert [h for h in find_ai_tics(t) if h["kind"] == "contextual_word"]


from scribe3.critique import quality_issues


def test_quality_issues_banned_word_entry():
    """quality_issues 层:banned_word 条目 message 含中文描述+类别,range 切片==phrase。"""
    text = "他不禁打了个寒颤。"
    entries = [i for i in quality_issues(text) if i["meta"].get("kind") == "banned_word"]
    assert entries, "应有 banned_word issue 条目"
    it = entries[0]
    assert it["type"] == "ai_tics"
    assert "禁用词" in it["message"] and "动作类" in it["message"]
    s, e = it["range"]
    assert text[s:e] == it["text"] == "不禁"


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
    assert "具体人物姓名" in p


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


# ==== 方案B任务13:情绪表达4级分级(oh-story style-craft.md:直写<思想<神态<动作)====
# 4 级是表达质量阶梯:L1直写情绪词/L2思想转述 是 telling,检测器上报;
# L3神态/L4动作是合法的 showing 手法,不扫描、不上报——语义写在 find_emotion_telling
# docstring 里,这里只测检测器实际覆盖的 L1/L2 两级。
class TestEmotionLevels:
    def test_level1_direct(self):
        hits = find_emotion_telling("他感到害怕。")
        assert hits[0]["level"] == 1     # 直写情绪词

    def test_level2_thought(self):
        hits = find_emotion_telling("他心中暗道,这下完了。")
        assert hits and hits[0]["level"] == 2   # 思想转述

    def test_kind_field_backward_compat(self):
        hits = find_emotion_telling("他感到害怕。")
        assert hits[0]["kind"] == "emotion_word" and "span" in hits[0]

    def test_summary_ratio(self):
        from scribe3.critique import emotion_telling_summary
        text = "他感到害怕。" + "他攥紧了刀柄。" * 9
        agg = emotion_telling_summary(text)
        assert agg["l1_count"] == 1 and 0 < agg["l1_ratio"] < 0.2


# ==== 方案B任务16:短篇模式开关——短篇要直写情绪+审判金句,长篇的克制/留白
# 引擎(craft.py ENGINES["restraint"])全线让位;检测器侧 short_mode=True 直接
# 放行,不因直写情绪判 telling。====
class TestShortMode:
    def test_emotion_telling_short_mode_off(self):
        assert find_emotion_telling("他感到害怕。") != []
        assert find_emotion_telling("他感到害怕。", short_mode=True) == []

    def test_quality_flags_short_mode(self):
        # quality_flags 不直接调 find_emotion_telling(该键不在其聚合字典里,见
        # quality_flags docstring"elegant_variation"一段的姊妹说明);short_mode 的
        # 落点在 aggregate_ai_grade——断言其 psych_ratio 指标在 short_mode 下归零、
        # Gate C(心理告知)不触发。
        from scribe3.critique import aggregate_ai_grade, quality_flags
        text = "他感到害怕。" + "他攥紧了刀柄。" * 20
        qf = quality_flags(text)
        g_normal = aggregate_ai_grade(qf, text)
        g_short = aggregate_ai_grade(qf, text, short_mode=True)
        assert g_normal["indicators"]["psych_ratio"]["value"] > 0
        assert g_short["indicators"]["psych_ratio"]["value"] == 0
        assert g_short["gates"]["C"]["hit"] is False


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


# ==== 方案B任务13:失败模式 rubric 轴(oh-story emotional-methods.md:太平/太赶/烂尾)====

def test_tension_rubric_prompt_has_pacing_axes():
    """prompt 含 pacing_flat(连续≥5节无情绪转折=太平)/pacing_rushed(转折铺垫<3节太赶,
    或反转后交代>2000字烂尾)两条 LLM 语义判定轴的关键词。"""
    from scribe3.critique import build_tension_rubric_prompt
    p = build_tension_rubric_prompt("……正文……")
    assert "pacing_flat" in p and "pacing_rushed" in p


def test_parse_tension_report_tolerates_missing_pacing_axes():
    """parse_tension_report 本身不校验字段结构(镜像 parse_knowledge_delta,只提取
    JSON 块 + json.loads),新轴缺省时不炸,其余字段照常解析;布尔字段一律用 .get()
    链式取值,与现有轴(如 hook/value_shift)同一容错口径。"""
    from scribe3.critique import parse_tension_report
    # 老响应完全没有新轴键
    rep = parse_tension_report('{"hook":{"present":true}}')
    assert rep is not None
    assert rep.get("pacing_flat", {}).get("present") is None
    assert rep.get("pacing_rushed", {}).get("present") is None
    # 新响应带新轴,布尔解析与现有轴一致
    rep2 = parse_tension_report(
        '{"hook":{"present":true},'
        '"pacing_flat":{"present":false,"note":"有转折"},'
        '"pacing_rushed":{"present":true,"note":"反转后交代过长"}}')
    assert rep2["pacing_flat"]["present"] is False
    assert rep2["pacing_rushed"]["present"] is True


# ==== 方案B任务13b:反转工具箱 rubric + 悬念/伏笔边界(oh-story reversal-toolkit.md)====

def test_reversal_rubric_prompt_has_axes_and_anti_sycophancy():
    """build_reversal_rubric_prompt:含 4 项机检轴关键词(铺垫<3处/揭示交代>300字/
    引入前文未现新信息/位置越出最佳区间50-85%)+ ANTI_SYCOPHANCY 常量文本(直接引用)。"""
    from scribe3.critique import build_reversal_rubric_prompt, ANTI_SYCOPHANCY
    p = build_reversal_rubric_prompt(
        "……正文……",
        beat_meta={"reversal_type": "身份反转", "setup_clues": ["c1", "c2", "c3"],
                   "reveal_position_pct": 70})
    assert ANTI_SYCOPHANCY in p
    assert "setup_insufficient" in p and "3" in p          # 铺垫<3处
    assert "reveal_overlong" in p and "300" in p            # 揭示交代>300字
    assert "unearned_new_info" in p                          # 引入前文未现新信息
    assert "position_out_of_range" in p and "50" in p and "85" in p   # 位置越出50-85%
    # 反转声明的三字段回填进 prompt
    assert "身份反转" in p and "c1" in p and "70" in p


def test_reversal_rubric_prompt_empty_when_no_beat_meta():
    """本章无反转不审:beat_meta 为空 dict 或 None → 返回空串。"""
    from scribe3.critique import build_reversal_rubric_prompt
    assert build_reversal_rubric_prompt("正文", beat_meta={}) == ""
    assert build_reversal_rubric_prompt("正文", beat_meta=None) == ""


def test_parse_reversal_report_ok_and_bad_json():
    """parse_reversal_report:照 parse_tension_report 的容错风格——合法 JSON 返 dict,
    坏 JSON 返 None。"""
    from scribe3.critique import parse_reversal_report
    rep = parse_reversal_report('{"findings":[],"verdict":"APPROVE"}')
    assert rep == {"findings": [], "verdict": "APPROVE"}
    assert parse_reversal_report("垃圾") is None
    assert parse_reversal_report("") is None
    assert parse_reversal_report(None) is None


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
        # 紧凑分支真正走到裸「是」且后一字是语气词:反问尾巴,不报 compact_shi
        assert not find_negation_flips("这不是假的是吗?")

    # —— 结构命中与维基宽命中重叠去重 ——
    def test_overlap_dedup_struct_wins(self):
        from scribe3.critique import find_negation_flips
        # bujin 宽正则与 compact_shi 结构命中 range 相交 → 只保留更精确的结构命中
        hits = find_negation_flips("他不仅救了人，而且不是懦夫是英雄。")
        assert len(hits) == 1 and hits[0]["variant"] == "compact_shi"

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


# ==== 方案A任务2:引号剥离豁免(stripQuoted,对齐 oh-story)====

class TestQuoteExemption:
    """台词/弹幕复沓是体裁正常形态,复读/排比/结构检测只判叙述层(oh-story stripQuoted 移植)。"""

    def test_dialogue_repetition_exempt(self):
        # 纯台词复沓(角色喊三遍)是体裁正常形态,不报
        t = "「救命啊救命啊救命啊!」她喊。\n「救命啊救命啊救命啊!」又是一声。\n「救命啊救命啊救命啊!」第三声。"
        assert find_repetitions(t) == []

    def test_dialogue_parallelism_exempt(self):
        from scribe3.critique import find_parallelism
        t = "“你走。”“你走。”“你走。”他连说三次。"
        assert all(p["prefix"] != "你走" for p in find_parallelism(t))

    def test_narration_repetition_still_caught(self):
        t = ("影子贴着墙根爬过去了。" * 3) + "「没事。」"
        assert find_repetitions(t, n=8, min_count=3)

    def test_mixed_line_outside_quotes_still_counted(self):
        # 混合行:引号外叙述仍计
        t = "他说「好」,影子贴着墙根爬。他说「好」,影子贴着墙根爬。他说「好」,影子贴着墙根爬。"
        hits = find_repetitions(t, n=6, min_count=3)
        assert any("影子" in h["phrase"] for h in hits)

    def test_dialogue_structural_repeats_exempt(self):
        # 台词同3字开头(你走吧…×4)不判 anaphora;极短对白(啊!/不!)不进 short 计数
        t = ("「你走吧娘。」「你走吧爹。」「你走吧哥。」「你走吧嫂。」他没接话。\n"
             "「啊！」「不！」「啊！」「不！」「啊！」屋里静了下来。")
        out = find_structural_repeats(t)
        assert not any(o["kind"] == "anaphora" for o in out), out
        assert not any(o["kind"] == "short" for o in out), out

    def test_strip_quoted_seven_pairs(self):
        from scribe3.critique import _strip_quoted
        assert _strip_quoted("a「一」b『二』c【三】d“四”e‘五’f\"六\"g'七'h") == "abcdefgh"


# ==== 方案A任务4:上帝视角检测器(find_god_view)====
# 归位纪律:①"这意味着/正是因为"已在 _EXPLAIN(find_oversaturation 管),此处只收
# "之所以…是因为";②不碰 verify.py 的 find_leaks(那是知识帧 fact-leak 检测器,与本检测器
# 的静态语言指纹分工不同);③"原来…"已被 LUANSHI_PURPLE_SEEDS[0] 部分覆盖,此处不再收。

class TestGodView:
    def test_god_spoiler(self):
        from scribe3.critique import find_god_view
        hits = find_god_view("她不知道的是，桥下的水早已改了道。")
        assert any(h["kind"] == "god_spoiler" for h in hits)

    def test_shubuzhi(self):
        from scribe3.critique import find_god_view
        hits = find_god_view("殊不知，那盏灯根本不是人点的。")
        assert any(h["kind"] == "god_spoiler" for h in hits)

    def test_duonianyihou(self):
        from scribe3.critique import find_god_view
        hits = find_god_view("多年以后,他仍会想起这个雨夜。")
        assert any(h["kind"] == "god_spoiler" for h in hits)

    def test_explain_causality(self):
        from scribe3.critique import find_god_view
        assert any(h["kind"] == "explain_causality"
                   for h in find_god_view("他之所以退后半步，是因为闻到了血腥味。"))

    def test_summarize_psych(self):
        from scribe3.critique import find_god_view
        assert any(h["kind"] == "summarize" for h in find_god_view("他终于明白，这一切都是命。"))

    def test_summarize_cike(self):
        # summarize 第二子模式:「此刻，他/她」镜头拉远式心理总结
        from scribe3.critique import find_god_view
        assert any(h["kind"] == "summarize" for h in find_god_view("此刻，他只想回家。"))

    def test_sublimation_indented(self):
        # 真实网文段首常带全角/半角缩进,行首锚须容忍缩进空白
        from scribe3.critique import find_god_view
        assert any(h["kind"] == "sublimation"
                   for h in find_god_view("    这一刻，他终于放下了心。"))

    def test_sublimation_midsentence_exempt(self):
        # 句中出现"这一刻"是合法叙述(刻意收窄防误伤),不报 sublimation
        from scribe3.critique import find_god_view
        assert not any(h["kind"] == "sublimation"
                       for h in find_god_view("爱情在这一刻绽放得热烈。"))

    def test_dialogue_exempt(self):
        from scribe3.critique import find_god_view
        assert not find_god_view("「殊不知他早跑了!」老板娘啐了一口。")

    def test_normal_prose_clean(self):
        from scribe3.critique import find_god_view
        assert find_god_view("灯芯爆了个花。他伸手拢住风。") == []

    def test_offsets_present(self):
        from scribe3.critique import find_god_view
        h = find_god_view("殊不知，灯早灭了。")[0]
        assert h["range"] is not None


# ==== 方案A任务5:模型退化检测(find_degeneration,oh-story check-degeneration.js 移植)====
# 复读循环(紧邻整行/长句打转)+ 占位拒绝语泄漏 + 工程词泄漏(tier1 blocking/tier2 advisory)+
# 截断——弱模型自己发现不了的退化指纹,靠确定性扫描兜底(report-only)。

class TestDegeneration:
    def test_adjacent_duplicate_line(self):
        from scribe3.critique import find_degeneration
        t = "夜风把幡子吹得笔直贴在杆上。\n夜风把幡子吹得笔直贴在杆上。\n他没回头。"
        assert any(h["kind"] == "adjacent_repeat" for h in find_degeneration(t))

    def test_long_sentence_loop(self):
        from scribe3.critique import find_degeneration
        t = ("他沿着河堤往北走了很久很久。其间。" * 3) + "然后停下。"
        assert any(h["kind"] == "sentence_loop" for h in find_degeneration(t))

    def test_ai_refusal_leak(self):
        from scribe3.critique import find_degeneration
        assert any(h["kind"] == "refusal" and h["severity"] == "blocking"
                   for h in find_degeneration("作为AI，我无法继续创作这个章节。"))

    def test_placeholder_leak(self):
        from scribe3.critique import find_degeneration
        assert any(h["kind"] == "placeholder" for h in find_degeneration("他转身离去。(此处省略三百字)"))

    def test_meta_tier1_blocking(self):
        from scribe3.critique import find_degeneration
        assert any(h["kind"] == "meta_leak" and h["tier"] == 1 and h["severity"] == "blocking"
                   for h in find_degeneration("按照细纲，他此时应当愤怒。"))

    def test_meta_tier1_dialogue_downgraded(self):
        from scribe3.critique import find_degeneration
        hits = [h for h in find_degeneration("「你的字数目标完成了?」他打趣道。") if h["kind"] == "meta_leak"]
        assert hits and hits[0]["severity"] == "advisory"

    def test_meta_tier2_advisory(self):
        from scribe3.critique import find_degeneration
        hits = [h for h in find_degeneration("上一章说过的那口井还在冒水。") if h["kind"] == "meta_leak"]
        assert hits and hits[0]["tier"] == 2 and hits[0]["severity"] == "advisory"

    def test_truncated_ending(self):
        from scribe3.critique import find_degeneration
        assert any(h["kind"] == "truncated" for h in find_degeneration("他抬起头,看见远处的"))

    def test_clean_prose_empty(self):
        from scribe3.critique import find_degeneration
        assert find_degeneration("灯灭了。他坐在黑里,听雨。「明天再说。」") == []

    def test_sentence_loop_mixed_line_precise_range(self):
        """混合行(叙述+引号内物件):句子在剥引号文本上计数,但 range/phrase 经下标映射
        精确还原回原文——range 指向第二次出现的行,phrase 与原文逐字一致(含该行自己的
        引号片段,而非第一行的或整行兜底)。"""
        from scribe3.critique import find_degeneration
        t = ("他说「东」,这句话十二个字十二个字十二个字。\n"
             "他说「西」,这句话十二个字十二个字十二个字。\n"
             "他说「南」,这句话十二个字十二个字十二个字。")
        hits = [h for h in find_degeneration(t) if h["kind"] == "sentence_loop"]
        assert hits and hits[0]["count"] == 3
        s, e = hits[0]["range"]
        # range 不变量:phrase 是原文精确子串
        assert t[s:e] == hits[0]["phrase"]
        # 指向第二次出现处:带的是第二行的引号片段「西」,不是第一行的「东」
        assert "「西」" in hits[0]["phrase"] and "「东」" not in hits[0]["phrase"]
        # 三行内容不同,不应误报 adjacent_repeat
        assert not any(h["kind"] == "adjacent_repeat" for h in find_degeneration(t))

    def test_mojibake(self):
        from scribe3.critique import find_degeneration
        assert any(h["severity"] == "blocking" for h in find_degeneration("他说�了一半。"))


# ==== 方案A任务6:句长方差/burstiness 检测器(find_rhythm_uniformity)====
# GPTZero/DetectGPT/Binoculars 公认头号 AI 破绽:句长分布异常均匀("节拍器")。
# 切句→剥引号只算叙述句→CV(变异系数)+相邻句长差比。report-only,句数不足不判。

class TestRhythmUniformity:
    def _mk(self, lens):  # 造指定句长序列的文本
        return "".join("字" * n + "。" for n in lens)

    def test_metronome_flagged(self):
        from scribe3.critique import find_rhythm_uniformity
        r = find_rhythm_uniformity(self._mk([18] * 30))
        assert r and r["verdict"] == "uniform" and r["cv"] < 0.1

    def test_bursty_human_prose_clean(self):
        from scribe3.critique import find_rhythm_uniformity
        r = find_rhythm_uniformity(self._mk([3, 41, 12, 7, 55, 2, 23, 9, 38, 5] * 3))
        assert r["verdict"] == "ok"

    def test_short_chapter_not_judged(self):
        from scribe3.critique import find_rhythm_uniformity
        assert find_rhythm_uniformity(self._mk([10, 20, 15])) is None

    def test_dialogue_stripped(self):
        # 弹幕/台词短句密集不该拉低 CV 判定
        from scribe3.critique import find_rhythm_uniformity
        t = self._mk([3, 41, 12, 7, 55, 2, 23, 9, 38, 5] * 2) + "「好。」「走。」「快。」" * 10
        assert find_rhythm_uniformity(t)["verdict"] == "ok"

    def test_low_cv_high_adj_ratio_stays_ok(self):
        """A6 审查(收尾清理批 Minor):verdict 是 cv 和 mean_adj_ratio 都低于地板值
        才判 uniform 的 AND 语义——纯交替句长(10,21,10,21,...)整体方差不大(cv 低,
        接近 0.35)但相邻句长每次都跳变(mean_adj_ratio 高,约 0.71,不算"缺乏突变"),
        锁住"仅 cv 低不足以判 uniform"。"""
        from scribe3.critique import find_rhythm_uniformity
        r = find_rhythm_uniformity(self._mk([10, 21] * 12))
        assert r["cv"] < 0.517, f"构造应满足 cv 低于地板值,实得 cv={r['cv']}"
        assert r["mean_adj_ratio"] >= 0.550, (
            f"构造应满足 mean_adj_ratio 不低于地板值,实得 mean_adj_ratio={r['mean_adj_ratio']}")
        assert r["verdict"] == "ok", "仅 cv 低、mean_adj_ratio 不低时不应判 uniform(AND 语义)"

    def test_strip_quoted_flips_verdict_on_dialogue_heavy_text(self):
        """A6 审查(收尾清理批 Minor):构造对话密集文本——叙述外壳「他说。」逐句
        完全相同(AI 味节拍器),但引号内台词长度剧烈起伏(bursty)。生产实现
        find_rhythm_uniformity 先 _strip_quoted 再切句计长,应准确判定为
        verdict="uniform"(揭穿被台词长度掩盖的单调叙述外壳);若不剥引号直接
        按整句(含台词)计长,则台词的剧烈起伏会拉高 cv/mean_adj_ratio,误判为
        "ok"——用手动复现的"不剥引号"算法验证确有翻转,锁住 _strip_quoted 这一步
        对判定正确性不可或缺。"""
        import re
        from scribe3.critique import find_rhythm_uniformity

        def mk_dialogue(lens):
            return "".join(f"「{'甲' * n}」他说。" for n in lens)

        lens_pattern = [3, 41, 12, 7, 55, 2, 23, 9, 38, 5] * 3
        text = mk_dialogue(lens_pattern)

        r = find_rhythm_uniformity(text)
        assert r["verdict"] == "uniform", (
            "剥引号后叙述外壳「他说」逐句相同,应判定为 uniform(节拍器)")

        # 手动复现"不剥引号"的算法(不调用 _strip_quoted),验证会翻转判定
        degen_re = re.compile(r"[一-鿿Ａ-ｚA-Za-z0-9]")
        segs = re.split(r"[。！？!?…]+", text)
        raw_lens = [n for n in (len(degen_re.findall(seg)) for seg in segs) if n > 0]
        mean = sum(raw_lens) / len(raw_lens)
        sigma = (sum((x - mean) ** 2 for x in raw_lens) / len(raw_lens)) ** 0.5
        cv_unstripped = sigma / mean if mean else 0.0
        adj = [abs(a - b) for a, b in zip(raw_lens, raw_lens[1:])]
        mean_adj_unstripped = (sum(adj) / len(adj) / mean) if adj and mean else 0.0
        from scribe3.critique import _RHYTHM_CV_FLOOR, _RHYTHM_ADJ_FLOOR
        verdict_unstripped = ("uniform" if (cv_unstripped < _RHYTHM_CV_FLOOR
                                            and mean_adj_unstripped < _RHYTHM_ADJ_FLOOR)
                              else "ok")
        assert verdict_unstripped == "ok", (
            "不剥引号时台词长度起伏应把判定拉回 ok,与剥引号后的 uniform 相反")
        assert verdict_unstripped != r["verdict"], "本用例应演示剥引号步骤翻转了判定结果"


# ==== 方案A任务7:副词密度 + 句内三段式 + 同义词循环三检测器 ====
# oh-story anti-ai-writing 模式2(副词表)+ 维基 rule of three + 维基 elegant variation。
# 三者均 report-only,宁可漏不滥杀:单次出现/单句三连合法,密度/循环才是AI腔信号。

class TestAdverbTriadVariation:
    def test_adverb_density(self):
        from scribe3.critique import find_adverb_density
        t = "他微微一笑。她淡淡开口。风缓缓吹过。他轻轻放下。" + "长句填充。" * 20
        r = find_adverb_density(t)   # 该文本千字密度远超3
        assert r and r["per_k"] > 3

    def test_adverb_sparse_clean(self):
        from scribe3.critique import find_adverb_density
        assert find_adverb_density("他微微一笑。" + "普通叙述句子填充内容。" * 200) is None

    def test_rule_of_three(self):
        from scribe3.critique import find_rule_of_three
        t = "院子里安静、破败、荒凉。屋里阴冷、潮湿、发霉。桌上干净、整齐、一尘不染。"
        assert len(find_rule_of_three(t)) >= 3

    def test_two_items_clean(self):
        from scribe3.critique import find_rule_of_three
        assert find_rule_of_three("院子安静、破败。") == []

    def test_four_items_multichar_not_reported(self):
        """规格审查锁 bug:负向环视 (?<!、) 只保证起点前一字不是顿号,不保证起点对齐
        分项边界——「院里安静、破败、荒凉、死寂。」曾从"破败"第二个字起匹配出
        「败、荒凉、死寂」,把半个词冒充分项,使四项列举被误报。全局切分后
        len(items)==4 → 不报。"""
        from scribe3.critique import find_rule_of_three
        assert find_rule_of_three("院里安静、破败、荒凉、死寂。") == []

    def test_four_items_leading_name_not_reported(self):
        """同上锁 bug:首项为短词(老李)时曾从「静、破败、荒凉」处击穿。四项 → 不报。"""
        from scribe3.critique import find_rule_of_three
        assert find_rule_of_three("老李、安静、破败、荒凉。") == []

    def test_comma_bounded_triple_reported(self):
        """边界:顿号列表止于逗号——「他带上刀、粮、水，然后出发。」逗号前的三项应命中。"""
        from scribe3.critique import find_rule_of_three
        hits = find_rule_of_three("他带上刀、粮、水，然后出发。")
        assert len(hits) == 1

    def test_elegant_variation(self):
        from scribe3.critique import find_elegant_variation
        t = "陈九抬头看天。那男人叹了口气。少年攥紧了拳。陈九转身就走。"
        hits = find_elegant_variation(t, names=["陈九"])
        assert hits and set(hits[0]["aliases"]) >= {"那男人", "少年"}

    def test_variation_far_apart_clean(self):
        from scribe3.critique import find_elegant_variation
        t = "陈九抬头看天。" + "无关叙述。" * 60 + "少年攥紧了拳。"
        assert find_elegant_variation(t, names=["陈九"]) == []

    def test_elegant_variation_quoted_generic_refs_exempt(self):
        """A7-Important 尾巾修复:find_elegant_variation 是模块里唯一不做引号豁免的
        检测器——台词「那男人到底是谁?那少年又是谁?」里的泛称是角色的疑问用词,
        不是叙述者刻意换用同义词避免重复,不该计入 aliases。落在引号区间内的泛称
        出现不触发命中,叙述层原正例(test_elegant_variation)不受影响仍应命中。"""
        from scribe3.critique import find_elegant_variation
        t = "陈九望着他们。「那男人到底是谁?那少年又是谁?」"
        assert find_elegant_variation(t, names=["陈九"]) == []

    def test_elegant_variation_name_in_quote_not_anchor(self):
        """同上修复的另一半:name 本身出现在引号内(台词里被人喊出名字)不作为触发
        锚点——「陈九,你听我说。」是台词提及,不是叙述者的"点名"动作。"""
        from scribe3.critique import find_elegant_variation
        t = "「陈九,你听我说。」他望着窗外。那男人叹气。少年低头。"
        assert find_elegant_variation(t, names=["陈九"]) == []


class TestAiGrade:
    def test_clean_chapter_light(self):
        from scribe3.critique import aggregate_ai_grade, quality_flags
        # 注:原计划文本用 "灯灭了。……" * 8 简单倍增拉长,实测该写法会把同一句话逐字
        # 复读 8 次,反而击穿 find_structural_repeats(anaphora)/find_repetitions/
        # find_duplicate_lines(均按"确定性命中即计数",这就是它们该做的事,不是误报)。
        # 改用 8 句互不重复但同样干净的叙述句,真机验证六项指标与 7 个 Gate 均为零命中。
        text = ("灯灭了。他坐在黑里听雨,雨点砸在瓦上,忽急忽缓。"
                "窗缝里钻进一点凉风,吹得烛芯歪了一下。"
                "楼下传来收伞的声响,又归于寂静。"
                "他摸黑倒了半杯茶,茶已经凉透。"
                "墙角的座钟走得很慢,像是在数着雨点。"
                "院子里的石阶湿了大半,水顺着瓦沟往下淌。"
                "远处狗叫了两声,随即也停了。"
                "他把手拢进袖子里,靠着墙闭上眼睛。")
        g = aggregate_ai_grade(quality_flags(text), text)
        assert g["grade"] == "light" and g["gates_hit"] == []

    def test_heavy_by_indicators(self):
        """6 指标本身高强度重复堆砌 → 多项指标各自越过 heavy 阈值,grade 由
        max(tiers) 走到 heavy(与 Gate 数强制无关,即使 gates_hit>=4 也是"顺带满足",
        非本测试要验证的分支)。原名 test_heavy_when_four_gates——审查发现该名字
        暗示在测「Gate 数强制 heavy」分支,实际该文本 6 指标已直接判 heavy,即使把
        _AI_GRADE_HEAVY_GATE_COUNT 从 4 改到 99(相当于关掉 Gate 强制分支)本测试
        仍然绿,是假绿,故改名并新增 test_four_gates_force_heavy 补齐真正的 Gate
        强制路径覆盖(见下)。"""
        from scribe3.critique import aggregate_ai_grade, quality_flags
        text = ("他心中一动,眼中闪过一丝狡黠。这不是恐惧而是愤怒。"
                "他感到害怕。殊不知,他终于明白这就是命。") * 12
        g = aggregate_ai_grade(quality_flags(text), text)
        assert g["grade"] == "heavy" and len(g["gates_hit"]) >= 4

    def test_four_gates_force_heavy(self):
        """真正验证"命中 Gate 数 >= _AI_GRADE_HEAVY_GATE_COUNT 强制 heavy"这条分支:
        构造 6 项指标全部落在 light/medium 档(没有任何一项自己够格 heavy)、但零星命中
        4 个不同 Gate(A 禁用词「隐约」1 处、B 否定翻转「不是恐惧而是愤怒」1 处、
        F 结尾升华「这一刻,...」句首 1 处、G 解释腔上帝感「殊不知」1 处)的文本——
        纯靠 Gate 计数把 grade 从"本该是 medium"顶到 heavy。

        变异验证(修复过程中人工执行,验证后已还原常量):把
        _AI_GRADE_HEAVY_GATE_COUNT 从 4 改成 99 重跑,本测试断言的 grade 从 "heavy"
        变成 "medium"(gates_hit 仍是 ["A","B","F","G"],指标本身从未到 heavy)——
        证明该分支确实被本测试覆盖到,不是像被替换掉的旧测试那样"改了阈值常量测试
        仍然绿"的假绿。"""
        from scribe3.critique import aggregate_ai_grade, quality_flags
        fillers = (
            "院子里的老槐树落了满地的叶子,风一吹又打着旋卷起来。"
            "他把外套裹紧,慢慢走向巷口那盏昏黄的路灯。"
            "隔壁修鞋匠的摊子已经收了,只剩一张空板凳歪在墙边。"
            "巷子尽头的猫跳上矮墙,盯着他看了一会儿又跳了下去。"
            "远处传来几声犬吠,很快又归于安静。"
            "他低头看了看表,时间比想象中晚了许多。"
            "路口的糖水铺子还亮着灯,老板娘正收拾着最后几张桌子。"
            "自行车链条发出轻微的吱嘎声,一路陪着他走到桥边。"
            "河面上飘着几片枯叶,顺着水流慢慢往下游去。"
            "对面楼里传来收音机的声音,断断续续放着旧歌。"
            "他数了数口袋里剩下的硬币,刚好够买一碗面。"
            "面馆的老板认得他,笑着多加了一个卤蛋。"
            "他坐在角落的位置,慢慢地把面吃完。"
            "走出面馆时,天边已经泛起一点鱼肚白。"
        )
        text = (
            "这一刻,他终于放下了心中的石头。"  # Gate F:句首升华
            "窗外隐约传来钟声,一下一下敲得人心里发沉。"  # Gate A:禁用词「隐约」1 处
            "这不是恐惧而是愤怒,他攥紧了拳头站在原地。"  # Gate B:否定翻转 1 处
            "殊不知,那把旧伞早已经不知去向,被人顺手扔进了河里。"  # Gate G:上帝视角 1 处
            + fillers  # 纯填充叙述,不触发任何检测器,只用来把 banned_density 稀释到 medium 档
        )
        g = aggregate_ai_grade(quality_flags(text), text)
        for name, ind in g["indicators"].items():
            assert ind["tier"] != "heavy", f"{name} 不该到 heavy 档(应全是 light/medium):{ind}"
        assert set(g["gates_hit"]) == {"A", "B", "F", "G"}
        assert g["grade"] == "heavy", "6 指标均未到 heavy,只能是 Gate 数(>=4)强制升级"

    def test_gate_mapping_keys(self):
        from scribe3.critique import aggregate_ai_grade, quality_flags
        g = aggregate_ai_grade(quality_flags("平常句子。" * 30), "平常句子。" * 30)
        assert set(g["gates"].keys()) == set("ABCDEFG")

    def test_empty_text_rhythm_uniform_value_is_string(self):
        """A8-Minor 尾巾修复:空文本骨架分支给 indicators.rhythm_uniform.value 写的是
        整数 0,与正常分支该键的字符串契约("ok"/"uniform")不一致——调用方若无差别地
        当字符串用会拿到类型错误。空文本时 rhythm 未判定,语义上等价于"ok"(未见异常
        节奏),故写 "ok" 而非 0。其余 5 个指标(非二值枚举语义)仍是数值 0,不受影响。"""
        from scribe3.critique import aggregate_ai_grade
        g = aggregate_ai_grade({}, "")
        assert g["indicators"]["rhythm_uniform"]["value"] == "ok"
        assert isinstance(g["indicators"]["rhythm_uniform"]["value"], str)
        for name, ind in g["indicators"].items():
            if name != "rhythm_uniform":
                assert ind["value"] == 0

    def test_precomputed_reused_not_recomputed(self, monkeypatch):
        """A8-Important 尾巾修复:/post-check 在调用 aggregate_ai_grade 前已经对同一份
        text 算过 find_duplicate_lines/find_emotion_telling/find_parallelism/
        find_poetic_fragments 四项(拼装响应里的 duplicate_lines/emotion_telling/
        parallelism/poetic_fragments 字段),aggregate_ai_grade 内部原先又对同一 text
        重算一遍——纯浪费。传 precomputed 后应直接复用,不二次调用 find_emotion_telling
        (用 monkeypatch 计数验证;其余三个检测器同一套 precomputed 机制,逻辑等价,
        不逐一重复断言)。"""
        import scribe3.critique as critique_mod
        text = ("灯灭了。他坐在黑里听雨,雨点砸在瓦上,忽急忽缓。"
                "窗缝里钻进一点凉风,吹得烛芯歪了一下。") * 3
        calls: list[str] = []
        orig_find_emotion_telling = critique_mod.find_emotion_telling

        def spy(t):
            calls.append(t)
            return orig_find_emotion_telling(t)

        monkeypatch.setattr(critique_mod, "find_emotion_telling", spy)
        precomputed = {
            "duplicate_lines": critique_mod.find_duplicate_lines(text),
            "emotion_telling": orig_find_emotion_telling(text),
            "parallelism": critique_mod.find_parallelism(text),
            "poetic_fragments": critique_mod.find_poetic_fragments(text),
        }
        calls.clear()  # 上面为构造 precomputed 手动调用过一次,清空后只统计聚合函数内部的调用
        qf = critique_mod.quality_flags(text)
        critique_mod.aggregate_ai_grade(qf, text, precomputed=precomputed)
        assert calls == [], "传入 precomputed 后 aggregate_ai_grade 不该再调用 find_emotion_telling"

    def test_no_precomputed_still_computes(self):
        """向后兼容:不传 precomputed(如 /check 端点)时行为与修复前一致,现算四项,
        不因新增可选参数而回归。"""
        from scribe3.critique import aggregate_ai_grade, quality_flags
        text = "灯灭了。他坐在黑里听雨,雨点砸在瓦上,忽急忽缓。" * 3
        g = aggregate_ai_grade(quality_flags(text), text)
        assert g["grade"] in ("light", "medium", "heavy")

    def test_parallel_run_ignores_scattered_whole_chapter_opener_tally(self):
        """真机冒烟发现的误判(2026-07-04):find_structural_repeats 的 anaphora
        "count" 是【全章同 3 字开头句子的总条数】(collections.Counter 全局计数),
        不是"连续排比的连排长度"——主角名字在整章里散布着当主语开头,是中文叙事
        最正常的形态(第三人称限知视角写谁都这样),不该判定为"AI 排比"。

        本用例复现:「苏纸鸢」开头的句子在 20 句里出现 10 次,但每次都被别的句子
        隔开,从未连续 2 句相邻(真实排比要求连续)。修复前 aggregate_ai_grade 把
        find_structural_repeats 的 anaphora 总计数(10)直接当"最大连排数"喂给
        parallel_run,判定 tier=heavy;find_parallelism(真正的连续排比检测器,逐句
        比对相邻指纹)在同一文本上正确给出 []——从未探测到长度>=3 的连续同头句。
        这就是真机 6 个已人工验收章节全部误判 heavy 的根因。

        修复后 parallel_run 只采信 find_parallelism 的连排计数,不再掺入
        find_structural_repeats 的全章总计数,该场景应判 light(value=0)。"""
        from scribe3.critique import aggregate_ai_grade, find_parallelism, quality_flags
        digits = "零一二三四五六七八九"
        parts = []
        for d in digits:
            parts.append(f"苏纸鸢想起{d}件往事。")
            parts.append(f"窗外的雨滴敲着船篷第{d}下。")
        text = "".join(parts)
        # 前提断言:真正的连续排比检测器在此文本上确认"没有连续同头句"
        assert find_parallelism(text) == [], "夹具设计前提被破坏:不应存在真正的连排"
        g = aggregate_ai_grade(quality_flags(text), text)
        assert g["indicators"]["parallel_run"]["value"] == 0
        assert g["indicators"]["parallel_run"]["tier"] == "light"

    def test_parallel_run_still_catches_real_consecutive_burst(self):
        """阈值重标定(2026-07-04 真机标定,见 _AI_GRADE_PARALLEL_LIGHT/_MEDIUM 常量
        注释)不能把 parallel_run 整体调哑——真正连续的排比堆砌(8 句连续同 2 字
        开头,find_parallelism 真连排检测器命中)仍必须单独判 heavy,不依赖其余
        指标凑数。这是与 test_parallel_run_ignores_scattered_whole_chapter_opener_
        tally 对称的正例回归锁。"""
        from scribe3.critique import aggregate_ai_grade, find_parallelism, quality_flags
        text = ("她穿过黑暗的巷子。她穿过潮湿的地下室。她穿过破碎的镜子。她穿过腐烂的花园。"
                "她穿过冰冷的走廊。她穿过燃烧的森林。她穿过寂静的墓地。她穿过无尽的深渊。")
        assert find_parallelism(text) and find_parallelism(text)[0]["count"] == 8
        g = aggregate_ai_grade(quality_flags(text), text)
        assert g["indicators"]["parallel_run"] == {"value": 8, "tier": "heavy"}
        assert g["grade"] == "heavy"

    def test_heavy_reverse_smoke(self):
        """任务 Step 4 反向对照:密集禁用词(一丝×多/隐约)+ 否定翻转(不是…而是…)+
        同句式 8 连排比 + 情感直说(感到害怕)混编的真 AI 味重灾文本,阈值放宽后
        仍必须整体判 heavy——防止本次标定为了消灭真机误判而把口子开得太大。
        禁用词特意塞进"她穿…"排比句自身的同一子句内(不用逗号另起分句),避免
        find_parallelism 的逗号分句边界把 8 连排比切断,三项指标(banned_density/
        parallel_run/psych_ratio)各自独立命中 heavy,不是靠单一指标撑场面。"""
        from scribe3.critique import aggregate_ai_grade, quality_flags
        text = (
            "她穿过飘着一丝寒气的黑暗巷子。她穿过弥漫一丝腥味的潮湿地下室。"
            "她穿过映着一丝血光的破碎镜子。她穿过散着一丝腐气的腐烂花园。"
            "她穿过传来隐约脚步的冰冷走廊。她穿过回荡隐约哭喊的燃烧森林。"
            "她穿过贴着一丝凉意的寂静墓地。她穿过再无一丝声响的无尽深渊。"
            "这不是恐惧而是绝望,她感到害怕,浑身发抖。"
        )
        g = aggregate_ai_grade(quality_flags(text), text)
        assert g["indicators"]["banned_density"]["tier"] == "heavy", g["indicators"]
        assert g["indicators"]["parallel_run"]["tier"] == "heavy", g["indicators"]
        assert g["grade"] == "heavy", g["indicators"]


# ===== 方案A任务9:标点归一建议生成器(report-only,移植 oh-story
# normalize-punctuation.js 的上下文判定,不落盘改写)=====

class TestNormalizePunct:
    def test_numeric_range_dash(self):
        from scribe3.critique import normalize_punctuation_suggestions
        s = normalize_punctuation_suggestions("三——五天后就到。")
        assert s and s[0]["suggestion"] == "到" and s[0]["original"] == "——"

    def test_ellipsis_to_period(self):
        from scribe3.critique import normalize_punctuation_suggestions
        s = normalize_punctuation_suggestions("他走了……天亮了。")
        assert any(x["original"] == "……" for x in s)

    def test_quoted_dialogue_untouched(self):
        from scribe3.critique import normalize_punctuation_suggestions
        assert normalize_punctuation_suggestions("「我……我不知道。」") == []

    def test_report_only_ranges(self):
        from scribe3.critique import normalize_punctuation_suggestions
        s = normalize_punctuation_suggestions("三——五天。")
        st, en = s[0]["range"]
        assert "三——五天。"[st:en] == "——"

    def test_ellipsis_at_paragraph_start_suggests_delete(self):
        """A9 规格审查补丁:ellipsis 分支缺 JS choosePauseReplacement 最前面的通用短路
        (double_hyphen 分支已对称实现)——before==""(段首)时省略号是多余的开场符号,
        应建议删除(suggestion=""),而不是像修复前那样误建议"，"。"""
        from scribe3.critique import normalize_punctuation_suggestions
        s = normalize_punctuation_suggestions("……天亮了，一切都结束了。")
        assert s and s[0]["kind"] == "ellipsis" and s[0]["suggestion"] == ""

    def test_ellipsis_after_opening_delim_suggests_delete(self):
        """同上短路的另一半:before 是开括号/开引号(_PUNCT_OPENING_DELIM_RE)时——
        如「（……）他没有再说话。」括号内起头的省略号——应建议删除(suggestion=""),
        而不是像修复前那样误建议"。"。"""
        from scribe3.critique import normalize_punctuation_suggestions
        s = normalize_punctuation_suggestions("（……）他没有再说话。")
        assert s and s[0]["kind"] == "ellipsis" and s[0]["suggestion"] == ""


# ==== 方案B任务18:反谄媚对抗注入 + 统一 Findings Schema ====

class TestFindingsSchema:
    """反 LLM 盖章通过的确定性纠偏:①每个 reviewer prompt 硬写"找问题不是验证正确性";
    ②统一 Findings Schema(severity S1-S4 + category 九类 + 六字段)可机器合并排序;
    ③分歧不自动妥协,verdict 汇总保守(任一 REJECT 即 REJECT,空评审=CONCERNS)。"""

    def test_anti_sycophancy_in_all_llm_prompts(self):
        from scribe3.critique import build_discipline_prompt, build_tension_rubric_prompt
        for p in (build_discipline_prompt("正文"), build_tension_rubric_prompt("正文")):
            assert "找问题" in p and "不是验证" in p

    def test_normalize_findings_sort_and_enum(self):
        from scribe3.critique import normalize_findings
        fs = [{"severity": "S3", "category": "prose", "location": "ch3", "evidence": "e", "issue": "i", "fix": "f"},
              {"severity": "S1", "category": "consistency", "location": "ch1", "evidence": "e", "issue": "i", "fix": "f"}]
        out = normalize_findings(fs)
        assert out[0]["severity"] == "S1"

    def test_normalize_rejects_bad_enum(self):
        from scribe3.critique import normalize_findings
        assert normalize_findings([{"severity": "P0", "category": "prose",
                                    "location": "", "evidence": "", "issue": "", "fix": ""}]) == []

    def test_merge_verdicts(self):
        from scribe3.critique import merge_verdicts
        assert merge_verdicts(["APPROVE", "REJECT", "CONCERNS"]) == "REJECT"
        assert merge_verdicts(["APPROVE", "CONCERNS"]) == "CONCERNS"
        assert merge_verdicts(["APPROVE", "APPROVE"]) == "APPROVE"
        assert merge_verdicts([]) == "CONCERNS"   # 无评审=不能盖章


# ==== 方案B任务14:题材豁免 allow_pattern/allow_word 新路径 ====
# 铁律:豁免是**前置 skip 判定**(减法),与 find_purple_prose 的 extra_patterns
# (加法标记,越加越标红)彻底分离,绝不复用后者。

class TestAllowPatternsExemption:
    def test_purple_prose_allow_skips_sentence(self):
        text = "他知道,回不去了。"
        assert find_purple_prose(text) != []
        assert find_purple_prose(text, allow_patterns=[r"回不去"]) == []

    def test_emotion_telling_allow(self):
        text = "他感到害怕。"
        assert find_emotion_telling(text) != []
        assert find_emotion_telling(text, allow_patterns=[r"感到害怕"]) == []


# ==== 方案B任务20:finding-merge 纪律 + degradation→重新生成 ====
# 背景(oh-story story-review/SKILL.md:151/:153):①合并多检测器 finding 时去重归口——
# 同位置"机械替换"(punct_suggestions)vs"按功能改写"(issue)两条冲突时丢机械的;
# ②degradation 类精确绑定"重新生成该段,不是改写"(对齐 continue-steer 回炉)。

class TestMergeFindings:
    def test_em_dash_dedup_prefers_functional(self):
        # 同 range 的 ai_tics.em_dash issue 与 punct suggestion 并存 → 丢 punct 建议(机械替换让位按功能改写)
        issues = [{"type": "ai_tics", "message": "AI腔:破折号过密", "text": "——",
                   "range": [5, 7], "meta": {"kind": "em_dash"}}]
        suggestions = [{"range": [5, 7], "original": "——", "suggestion": "到",
                        "reason": "数字区间用'到'", "kind": "numeric_range"}]
        merged_issues, merged_sug = merge_findings(issues, suggestions)
        assert merged_sug == [] and len(merged_issues) == 1

    def test_non_overlapping_both_kept(self):
        issues = [{"type": "ai_tics", "message": "m", "text": "——", "range": [5, 7], "meta": {"kind": "em_dash"}}]
        suggestions = [{"range": [20, 22], "original": "……", "suggestion": "。", "reason": "r", "kind": "ellipsis"}]
        mi, ms = merge_findings(issues, suggestions)
        assert len(mi) == 1 and len(ms) == 1

    def test_degeneration_gets_regenerate_action(self):
        issues = [{"type": "degeneration", "message": "模型退化:紧邻整行复读", "text": "x",
                   "range": [0, 10], "meta": {"kind": "adjacent_repeat"}},
                  {"type": "ai_tics", "message": "m", "text": "y", "range": [12, 14], "meta": {"kind": "banned_word"}}]
        mi, _ = merge_findings(issues, [])
        deg = [i for i in mi if i["type"] == "degeneration"]
        other = [i for i in mi if i["type"] != "degeneration"]
        assert all(i["meta"]["fix_action"] == "regenerate" for i in deg)
        assert all(i["meta"].get("fix_action", "rewrite") == "rewrite" for i in other)

    def test_does_not_mutate_input(self):
        """不修改入参(浅拷贝 meta),原 issue.meta 不应被污染上 fix_action。"""
        orig_meta = {"kind": "em_dash"}
        issues = [{"type": "ai_tics", "message": "m", "text": "——", "range": [5, 7], "meta": orig_meta}]
        merge_findings(issues, [])
        assert "fix_action" not in orig_meta


# ==== 方案B任务17:平台留存轴 + S1-S4 裁决(oh-story story-review/references/rubrics/
#      {qidian,fanqie,zhihu}.md)。严肃向定位:平台轴可选——只有显式传 platform 才用。====

class TestPlatformRubric:
    def test_qidian_prompt_content(self):
        from scribe3.critique import build_platform_rubric_prompt
        p = build_platform_rubric_prompt("正文……", platform="qidian")
        assert "爽点密度" in p and "追读比" in p
        assert "找问题" in p          # ANTI_SYCOPHANCY
        assert "S1" in p and "verdict" in p   # FindingsSchema 输出契约

    def test_fanqie_and_zhihu_supported(self):
        from scribe3.critique import build_platform_rubric_prompt
        assert "情绪节点" in build_platform_rubric_prompt("x", platform="fanqie")
        assert "完读率" in build_platform_rubric_prompt("x", platform="zhihu")

    def test_unknown_platform_raises(self):
        from scribe3.critique import build_platform_rubric_prompt
        import pytest
        with pytest.raises(ValueError):
            build_platform_rubric_prompt("x", platform="weibo")

    def test_parse_platform_report(self):
        from scribe3.critique import parse_platform_report
        raw = '{"findings":[{"severity":"S2","category":"platform","location":"ch1","evidence":"e","issue":"i","fix":"f"}],"verdict":"CONCERNS"}'
        rep = parse_platform_report(raw)
        assert rep["verdict"] == "CONCERNS" and rep["findings"][0]["severity"] == "S2"

    def test_parse_platform_report_bad_json(self):
        from scribe3.critique import parse_platform_report
        assert parse_platform_report("不是JSON") is None

    def test_parse_normalizes_findings(self):
        from scribe3.critique import parse_platform_report
        # findings 经 normalize_findings 清洗:非法 severity 丢弃
        raw = '{"findings":[{"severity":"P0","category":"platform","location":"","evidence":"","issue":"","fix":""}],"verdict":"APPROVE"}'
        assert parse_platform_report(raw)["findings"] == []


# ==== 方案B任务21:5 类推理一致性审计(oh-story consistency-checker.md 第三步
#      "推理型一致性审查")——规则边界悖论/设定层级冲突/跨章因果链/规则可滥用漏洞/
#      代价一致性,输出证据链(前提/规则→触发→矛盾→需裁决)。====

class TestReasoningAuditPrompt:
    def test_prompt_has_5_categories_and_evidence_chain_contract(self):
        from scribe3.critique import build_reasoning_audit_prompt
        p = build_reasoning_audit_prompt("规则:传送阵只能传死物", "事件1:活体传送")
        for kw in ("规则边界悖论", "设定层级冲突", "跨章因果链", "规则可滥用漏洞", "代价一致性"):
            assert kw in p, f"缺 5 类之一: {kw}"
        # 证据链输出契约:前提/规则→触发→矛盾→需裁决
        for kw in ("前提/规则", "触发", "矛盾", "裁决"):
            assert kw in p, f"缺证据链契约要素: {kw}"
        assert "找问题" in p and "不是验证" in p   # ANTI_SYCOPHANCY
        assert "S1" in p and "verdict" in p        # FindingsSchema 输出契约

    def test_prompt_consumes_rules_and_events_text(self):
        from scribe3.critique import build_reasoning_audit_prompt
        p = build_reasoning_audit_prompt("世界规则:禁止复活", "第8章:主角重伤三天不能动武")
        assert "世界规则:禁止复活" in p
        assert "第8章:主角重伤三天不能动武" in p

    def test_prompt_empty_rules_text_not_crash(self):
        from scribe3.critique import build_reasoning_audit_prompt
        p = build_reasoning_audit_prompt("", "第9章:当天全力战斗")
        assert "(无数据)" in p
        assert "第9章:当天全力战斗" in p

    def test_prompt_empty_events_text_not_crash(self):
        from scribe3.critique import build_reasoning_audit_prompt
        p = build_reasoning_audit_prompt("规则:每次预知损失寿命", "")
        assert "(无数据)" in p
        assert "规则:每次预知损失寿命" in p

    def test_prompt_both_empty_still_generates(self):
        from scribe3.critique import build_reasoning_audit_prompt
        p = build_reasoning_audit_prompt(None, None)
        assert isinstance(p, str) and p
        assert p.count("(无数据)") == 2


class TestParseReasoningAudit:
    def test_parse_ok(self):
        from scribe3.critique import parse_reasoning_audit
        raw = ('{"findings":[{"severity":"S1","category":"rule_boundary","location":"ch18",'
               '"evidence":"前提/规则:传送阵只能传死物;触发:第18章活体传送;矛盾点:无例外说明;'
               '需裁决:补例外来源","issue":"违反传送规则","fix":"补代价或改结果"}],'
               '"verdict":"REJECT"}')
        rep = parse_reasoning_audit(raw)
        assert rep["verdict"] == "REJECT"
        assert rep["findings"][0]["category"] == "rule_boundary"

    def test_parse_bad_json_returns_none(self):
        from scribe3.critique import parse_reasoning_audit
        assert parse_reasoning_audit("不是JSON,纯文本回复") is None
        assert parse_reasoning_audit("") is None
        assert parse_reasoning_audit(None) is None

    def test_parse_normalizes_and_defaults_verdict(self):
        from scribe3.critique import parse_reasoning_audit
        raw = '{"findings":[{"severity":"XX","category":"causal","location":"","evidence":"","issue":"","fix":""}]}'
        rep = parse_reasoning_audit(raw)
        assert rep["findings"] == []          # 非法 severity 被 normalize_findings 丢弃
        assert rep["verdict"] == "CONCERNS"    # 缺 verdict 保守归 CONCERNS


# ==== 方案B任务21:水字数确定性信号(rules/story-consistency.md:28)====
# same_emotion_run(连续≥3段同一情绪词)/static_scene(单段>500可见字且无对话无动作词)
# 两类确定性子集;"全章对话无新信息/连续2章无冲突"不做确定性,已挂进
# build_reasoning_audit_prompt 的"水字数征兆"节交 LLM 审议。

class TestFillerSignals:
    def test_same_emotion_run_detected(self):
        from scribe3.critique import find_filler_signals
        text = "他悲伤地站在雨里,久久不语。\n\n她也很悲伤,泪流满面地望着窗外。\n\n悲伤弥漫了整个屋子,无人开口。"
        out = find_filler_signals(text)
        hits = [f for f in out if f["kind"] == "same_emotion_run"]
        assert hits, "连续3段同情绪应命中 same_emotion_run"
        assert hits[0]["emotion"] == "悲伤"
        assert hits[0]["paragraphs"] == [0, 2]

    def test_mixed_emotion_not_detected(self):
        from scribe3.critique import find_filler_signals
        text = "他心中涌起一阵愤怒。\n\n她却只觉欣喜。\n\n他又陷入了孤独之中。"
        out = find_filler_signals(text)
        assert not [f for f in out if f["kind"] == "same_emotion_run"]

    def test_static_scene_long_no_dialogue_no_action(self):
        from scribe3.critique import find_filler_signals
        para = "远处云雾缭绕,山峦叠嶂,寂静无人,唯有风声掠过树梢,月色如水,笼罩着荒野。" * 20
        out = find_filler_signals(para)
        hits = [f for f in out if f["kind"] == "static_scene"]
        assert hits, "超500字无对话无动作词的静态场景应命中"
        assert hits[0]["chars"] > 500

    def test_static_scene_with_dialogue_not_detected(self):
        from scribe3.critique import find_filler_signals
        base = "远处云雾缭绕,山峦叠嶂,寂静无人,唯有风声掠过树梢,月色如水,笼罩着荒野。" * 20
        para = base + "“这里究竟是何处?”一人忽然低声问道。" + base
        out = find_filler_signals(para)
        assert not [f for f in out if f["kind"] == "static_scene"], "含对话的长段不应命中"

    def test_wired_into_quality_flags_and_issues(self):
        from scribe3.critique import quality_flags, quality_issues
        text = "他悲伤地站在雨里,久久不语。\n\n她也很悲伤,泪流满面地望着窗外。\n\n悲伤弥漫了整个屋子,无人开口。"
        flags = quality_flags(text)
        assert "filler" in flags and flags["filler"]
        issues = quality_issues(text)
        filler_issues = [i for i in issues if i["type"] == "filler"]
        assert filler_issues
        assert filler_issues[0]["range"] is None
        assert "水字数" in filler_issues[0]["message"]
