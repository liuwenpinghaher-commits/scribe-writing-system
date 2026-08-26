"""R1 round: 打开书 must learn the skeleton, not the tiny seq-0 card."""
from __future__ import annotations

import json
from pathlib import Path

from scribe3.eval.extract_card import (
    build_extract_prompt,
    parse_card,
    pick_dev_fewshot,
)

EVAL = Path(__file__).resolve().parents[1] / "eval"


def test_fewshot_openbook_is_complete_dev_card_not_seq0():
    holdout = set(json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"])
    shot = pick_dev_fewshot(exclude=8)
    assert shot
    first = shot.strip().splitlines()[0]
    seq = int(first[2:].split()[0])
    assert seq not in holdout
    assert seq != 0
    ob = parse_card(shot)["打开书"]
    assert "读完" in ob
    assert len(ob) >= 400


def test_extract_prompt_asks_openbook_who_event_after():
    prompt = build_extract_prompt(seq=1, title="x", source="夜幕渐落。", fewshot=None)
    assert "打开书" in prompt
    assert "读完" in prompt
    assert "眼睛" in prompt or "说书" in prompt
