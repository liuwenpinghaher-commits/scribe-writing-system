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
