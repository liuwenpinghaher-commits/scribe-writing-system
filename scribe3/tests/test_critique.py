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
