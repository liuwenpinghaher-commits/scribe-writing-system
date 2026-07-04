"""北极星方案任务9 · QD 多样性档案 TDD(蓝图 §5 P1 提前项:同质化是"承认了严重性
却给了最弱防护"的风险;文体特征轴同时供选择环当行为空间)。

口径依据《2026-07-05-QD多样性档案调研报告.md》:引号配对切分是公共前置
(Eisenberg&Finlayson:不去引号 POV 判定掉 13pt);断句按国标 GB/T 15834-2011
(分号不断句)+HarvestText 引号后断;对话占比=配对引号内字符比(Language Log 法,
只做书内基线偏离告警——同作者生涯可漂 30pt);MTLD 字级(0.72 英文经验值,中文
适用性属自定,面板须标注);告警=SPC 连续 8 点同侧移植(创作域无先例,自定嫁接)。
"""
import pytest

from scribe3.qd import (chapter_style_profile, sentence_lengths, split_quoted,
                        style_drift_alerts)


# ===== 公共前置:引号配对切分 =====

def test_split_quoted_pairs_and_ratio():
    text = "他说:“今晚别点灯。”她没应声。「知道了。」他才走。"
    narration, quoted_chars, total = split_quoted(text)
    assert "今晚别点灯" not in narration and "她没应声" in narration
    assert quoted_chars >= len("今晚别点灯。知道了。")
    assert 0 < quoted_chars < total


def test_split_quoted_unbalanced_failsoft():
    text = "他说:“话说了一半就断"
    narration, quoted_chars, total = split_quoted(text)
    assert total == len(text) and quoted_chars >= 0, "引号不平衡不崩,奇偶回退"


# ===== 断句(国标) =====

def test_sentence_lengths_gb_rules():
    text = "第一句到此。第二句有分号;却不断句!“引号内。”之后再断。"
    lens = sentence_lengths(text)
    assert len(lens) == 4, "分号不断句(GB/T 15834);句末标点后接后引号在引号后断"
    assert all(n > 0 for n in lens)


# ===== 章级六元组 =====

def test_chapter_style_profile_keys_and_dialogue_ratio():
    text = ("他把伞收了。院里没人,雨脚很密。" * 5
            + "“你来了。”“嗯。”“坐吧。”" * 5)
    p = chapter_style_profile(text)
    assert set(p) >= {"sent_cv", "sent_mean", "dialogue_ratio", "mtld_char",
                      "func_word_per_k", "punct_per_k", "pov"}
    assert 0.1 < p["dialogue_ratio"] < 0.9
    assert p["mtld_char"] > 0
    assert p["punct_per_k"]["comma"] > 0


def test_chapter_style_profile_pov_first_vs_third():
    first = "我把灯吹了。我们在黑里坐了半夜。我没说话。" * 4
    third = "他把灯吹了。两人在黑里坐了半夜。谁也没说话。" * 4
    quoted_trap = "“我来晚了。”他说。他把伞放下。" * 6   # 引号内的"我"不算(去引号先例)
    assert chapter_style_profile(first)["pov"]["mode"] == "first"
    assert chapter_style_profile(third)["pov"]["mode"] == "third"
    assert chapter_style_profile(quoted_trap)["pov"]["mode"] == "third", \
        "对话里的第一人称不污染叙述层判定(F1 0.928 先例的硬教训)"


# ===== 分布单调告警(SPC 移植,自定嫁接须如实标注) =====

def _prof(cv, ratio, seq):
    return {"seq": seq, "sent_cv": cv, "dialogue_ratio": ratio,
            "mtld_char": 50.0, "func_word_per_k": {}, "punct_per_k": {},
            "pov": {"mode": "third"}}


def test_style_drift_alert_cv_flattening():
    profiles = ([_prof(0.9, 0.3, i) for i in range(1, 6)]
                + [_prof(0.3, 0.3, i) for i in range(6, 14)])
    alerts = style_drift_alerts(profiles)
    assert any(a["rule"] == "sent_cv_flattening" for a in alerts), \
        "连续 8 章句长 CV 低于全书中位 → 磨平告警(SPC 连续同侧移植)"
    a = next(a for a in alerts if a["rule"] == "sent_cv_flattening")
    assert "自定" in a["note"] or "SPC" in a["note"], "自定嫁接口径须如实标注"


def test_style_drift_alert_dialogue_jump():
    profiles = [_prof(0.8, 0.30, i) for i in range(1, 6)] + [_prof(0.8, 0.62, 6)]
    alerts = style_drift_alerts(profiles)
    assert any(a["rule"] == "dialogue_ratio_jump" for a in alerts), \
        "对话占比偏离书内基线>15pt → 告警(只做书内自比,不设绝对带)"


def test_style_drift_no_alert_insufficient_data():
    assert style_drift_alerts([_prof(0.5, 0.3, 1), _prof(0.5, 0.3, 2)]) == [], \
        "数据不足不硬判(不足 8 章无 CV 告警、不足 4 章无跳变告警)"


# ===== 落库 + 书级面板 =====

def test_style_profile_persisted_on_save(store):
    store.save_chapter(1, "他把伞收了。院里没人。“你来了。”“嗯。”", title="一")
    rows = store.list_style_profiles()
    assert rows and rows[0]["seq"] == 1
    assert "sent_cv" in rows[0] and "dialogue_ratio" in rows[0]


def test_book_scorecard_has_style_diversity(store):
    from .test_app import _client
    store.save_chapter(1, "第一章正文。有人说话。“少说两句。”", title="一")
    data = _client(store).get("/north-star/book").json()
    sd = data["style_diversity"]
    assert sd["profiles_n"] == 1 and isinstance(sd["alerts"], list)
    assert sd["insufficient_window"] is True, \
        "窗口不足须显式标注,前端不得把空 alerts 当'无漂移'绿灯(P2-3)"
