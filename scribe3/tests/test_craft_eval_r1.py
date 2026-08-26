"""R1 scorer: gold-vs-gold ceiling, empty-card floor."""
from __future__ import annotations

from scribe3.eval.score_r1 import ceiling_on_dev, floor_on_dev, score_pair, scored_seqs, turned


def test_turned_parser():
    assert turned("翻了。开头还在排队。") is True
    assert turned("没翻。热闹像翻了。") is False
    assert turned("正文未写到。") is None


def test_gold_vs_gold_is_ceiling():
    r = ceiling_on_dev(limit=15)
    assert r["n"] == 15
    assert r["mean"] == 1.0


def test_empty_shell_is_floor():
    r = floor_on_dev()
    assert r["score"] < 0.5
    assert r["fields"]["这场戏有没有翻"]["ok"] is False


def test_holdout_scored_set_excludes_skips():
    seqs = scored_seqs()
    assert len(seqs) >= 30
    assert 85 not in seqs
    assert 101 not in seqs
