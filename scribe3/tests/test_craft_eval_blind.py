"""Blind judge parser: tab/colon answers, no extra prose required."""
from __future__ import annotations

from scribe3.eval.blind_r1 import parse_blind
from scribe3.eval.card_schema import R1_HARD_FIELDS


def test_parse_blind_tab_lines():
    text = "\n".join(
        [
            "这场戏有没有翻\t是",
            "留给下一节的日子\t否",
            "这一节回不去的事\t是",
            "热怎么变冷\t否",
            "打开书\t否",
        ]
    )
    out = parse_blind(text)
    assert [out[n] for n in R1_HARD_FIELDS] == [True, False, True, False, False]


def test_parse_blind_colon_and_noise():
    text = "打开书：否\n这场戏有没有翻: 是\n废话一行\n热怎么变冷\t是"
    out = parse_blind(text)
    assert out["打开书"] is False
    assert out["这场戏有没有翻"] is True
    assert out["热怎么变冷"] is True
    assert out["留给下一节的日子"] is None
