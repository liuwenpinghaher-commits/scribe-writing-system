"""PR-2b · parse_chapter_meta stakes / 章末钩子 正则单测（无 Surreal / 无网络）。"""
from __future__ import annotations

from scribe3.brief import parse_chapter_meta


def test_parses_stakes_and_hook_fullwidth_colon():
    text = (
        "沈砚夜探盐帮总舵，被灰印反噬。\n"
        "压力级:5\n"
        "chapter_role:高压\n"
        "stakes:若失败，他将永久失去对潮闸密钥的控制\n"
        "章末钩子:井底有人喊他的旧名\n"
    )
    meta = parse_chapter_meta(text)
    assert meta is not None
    assert meta["pressure"] == 5
    assert meta["role"] == "高压"
    assert "永久失去" in meta["stakes"]
    assert "井底" in meta["hook"]
    assert "warnings" not in meta


def test_parses_stakes_alias_and_hook_alias():
    text = "推进一场交易。赌注:若失败，关系链断裂\nhook:门后传来第二声叩击"
    meta = parse_chapter_meta(text)
    assert meta == {
        "stakes": "若失败，关系链断裂",
        "hook": "门后传来第二声叩击",
    }


def test_halfwidth_colon_and_case_insensitive_stakes():
    text = "Stakes: lose the only map\n章末钩子:潮声停了半拍"
    meta = parse_chapter_meta(text)
    assert meta["stakes"] == "lose the only map"
    assert meta["hook"] == "潮声停了半拍"


def test_high_pressure_missing_stakes_warns():
    text = "本章对峙。压力级:4\nchapter_role:高压\n章末钩子:灯灭了"
    meta = parse_chapter_meta(text)
    assert meta["pressure"] == 4
    assert meta["hook"] == "灯灭了"
    assert "stakes" not in meta
    assert meta.get("warnings") == ["missing_stakes_high_pressure"]


def test_low_pressure_missing_stakes_no_warn():
    text = "休整。压力级:2\nchapter_role:低压\n章末钩子:信未拆"
    meta = parse_chapter_meta(text)
    assert meta == {"pressure": 2, "role": "低压", "hook": "信未拆"}


def test_stakes_only_returns_dict():
    assert parse_chapter_meta("stakes:若失败，空船沉底") == {
        "stakes": "若失败，空船沉底",
    }


def test_empty_labels_without_value_are_ignored():
    """仅有空标签且无其它字段 → None（旧数据兼容）。"""
    assert parse_chapter_meta("stakes:\n章末钩子:  \n") is None


def test_parses_from_beats_list_with_stakes():
    beats = [
        {"text": "开场铺垫"},
        {"text": "压力级:3 stakes:若失败，证人消失 章末钩子:雨里多出一双脚印"},
    ]
    meta = parse_chapter_meta(beats)
    assert meta["pressure"] == 3
    assert meta["stakes"] == "若失败，证人消失"
    assert meta["hook"] == "雨里多出一双脚印"
    assert "warnings" not in meta
