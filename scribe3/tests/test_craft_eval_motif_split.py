"""A: motif split — 账 is book-specific, not a shared craft rule."""
from __future__ import annotations

import json
from pathlib import Path

from scribe3.eval.motif_split import (
    BLACKLIST_TERMS,
    classify_feature,
    split_motifs,
)

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "scribe3/eval"


def test_zhang_is_book_specific():
    rows = split_motifs()
    zhang = next(r for r in rows if r["name"] == "账")
    assert zhang["bucket"] == "单本母题"
    assert zhang["rate_tonglu"] - zhang["rate_lotm"] >= 0.15
    assert zhang["rate_tonglu"] > 0.5
    assert zhang["rate_lotm"] < 0.25


def test_classify_uses_15_point_gap():
    assert classify_feature(0.63, 0.14) == "单本母题"
    assert classify_feature(0.40, 0.38) == "通则"
    assert classify_feature(0.02, 0.01, n_tonglu=214, n_lotm=1394) == "不确定"


def test_blacklist_covers_ledger_family():
    doc = json.loads((EVAL / "motif_blacklist.json").read_text(encoding="utf-8"))
    terms = set(doc["terms"])
    for t in BLACKLIST_TERMS:
        assert t in terms
    assert "账" in terms
    assert "盘点" in terms
    assert "对账" in terms


def test_分层_md_has_three_buckets():
    md = (ROOT / "docs/worlds/两本对照/母题分层.md").read_text(encoding="utf-8")
    assert "## 通则" in md
    assert "## 单本母题" in md
    assert "## 不确定" in md
    assert "账" in md.split("## 单本母题", 1)[1].split("## ", 1)[0]
