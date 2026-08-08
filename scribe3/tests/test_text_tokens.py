"""tokenize_for_fts 单元测试（不依赖 Surreal）。"""
from __future__ import annotations

from scribe3.text_tokens import tokenize_for_fts


def test_tonglu_query_expands_to_chars():
    q = tokenize_for_fts("铜炉")
    parts = set(q.split())
    assert "铜" in parts and "炉" in parts
    assert "铜炉" in parts


def test_sentence_has_cross_unigram_bigram():
    # 句中常切成 铜 / 炉，应补 铜炉 bigram
    t = tokenize_for_fts("玉佩纹路与铜炉底部暗纹同源")
    parts = set(t.split())
    assert "铜" in parts and "炉" in parts
    assert "铜炉" in parts
