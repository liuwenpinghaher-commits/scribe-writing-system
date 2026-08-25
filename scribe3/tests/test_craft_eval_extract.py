"""P1 extract pipeline: slice source, never read holdout gold."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scribe3.eval.card_schema import CARD_HEADINGS
from scribe3.eval.extract_card import (
    HoldoutGoldBlocked,
    empty_shell_card,
    load_gold_card,
    load_source_slice,
    missing_headings,
    parse_card,
    pick_dev_fewshot,
)

EVAL = Path(__file__).resolve().parents[1] / "eval"


def test_gold_dev_card_has_all_headings():
    md = load_gold_card(1)
    parts = parse_card(md)
    assert missing_headings(parts) == []
    assert "许了六两银子酬金" in parts["书证"] or "六两" in md


def test_holdout_gold_is_blocked():
    holdout = json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"]
    with pytest.raises(HoldoutGoldBlocked):
        load_gold_card(holdout[0])


def test_source_slice_intro_has_nightfall():
    text = load_source_slice(0)
    assert "夜幕渐落" in text
    assert "时闻盂" in text or "贺客" in text


def test_fewshot_never_picks_holdout():
    holdout = set(json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"])
    shot = pick_dev_fewshot(exclude=1)
    assert shot
    # first heading line of a card: "# {seq}"
    first = shot.strip().splitlines()[0]
    seq = int(first.split()[1]) if first.startswith("# ") else -1
    # title line is "# 1 第一章" — seq is token 1
    token = first[2:].split()[0]
    seq = int(token)
    assert seq not in holdout


def test_empty_shell_card_has_all_headings():
    md = empty_shell_card(85, "苏醒(免费外篇)")
    assert missing_headings(parse_card(md)) == []
    assert "正文几乎没有" in parse_card(md)["打开书"]


def test_card_heading_count():
    assert len(CARD_HEADINGS) == 21
