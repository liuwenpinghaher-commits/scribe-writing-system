"""本轮新章 6–10：驱动已上线 _parse_wordcount / WCG / 无 fallback。无 Surreal。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs" / "evidence" / "v634-newch-20260814"
sys.path.insert(0, str(ROOT / "scripts"))
from v634_evidence_checklist import _parse_wordcount  # noqa: E402
from scribe3.prose_sanitize import strip_pollution, visible_length


def test_parse_wordcount_newch_rollup_over_20k():
    text = (EV / "08-wordcount-rollup.md").read_text(encoding="utf-8")
    n = _parse_wordcount(text)
    assert n == 22576, n
    assert n >= 20000
    wc = json.loads((EV / "wordcount.json").read_text(encoding="utf-8"))
    assert wc["visible_new"] == n
    assert wc["slug"] == "book_79c0d45e"
    assert wc["pass"] is True


def test_wcg_still_pass_true():
    wcg = json.loads((EV / "00-world-complete-gate.json").read_text(encoding="utf-8"))
    assert wcg["pass"] is True
    assert int(wcg.get("fail_count") or 0) == 0
    assert wcg.get("slug") == "book_79c0d45e"


def test_serialize_excerpts_have_no_fallback():
    ser = EV / "04-serialize"
    files = sorted(ser.glob("ch*.md"))
    assert len(files) == 5
    for p in files:
        text = p.read_text(encoding="utf-8")
        assert "fallback" not in text
        clean = strip_pollution(text)
        assert "fallback" not in clean
        assert visible_length(text) > 80


if __name__ == "__main__":
    test_parse_wordcount_newch_rollup_over_20k()
    test_wcg_still_pass_true()
    test_serialize_excerpts_have_no_fallback()
    print("PASS test_v634_newch_wordcount")
