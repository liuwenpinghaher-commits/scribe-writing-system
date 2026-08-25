"""P0 freeze: holdout hash + chapter map integrity."""
from __future__ import annotations

import json
from pathlib import Path

from scribe3.eval import verify_holdout_hash

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "scribe3/eval"


def test_holdout_hash_frozen():
    got = verify_holdout_hash()
    assert len(got) == 64
    doc = json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))
    assert doc["seed"] == 20260826
    assert doc["n_holdout"] == 43
    assert len(doc["holdout"]) == 43
    assert len(set(doc["holdout"]) & set(doc["dev"])) == 0
    assert len(doc["holdout"]) + len(doc["dev"]) == 214


def test_chapters_map_covers_index():
    ch = json.loads((EVAL / "chapters.json").read_text(encoding="utf-8"))
    seqs = [c["seq"] for c in ch["chapters"]]
    assert seqs == list(range(214))
    assert ch["missed"] == []
    live = [c for c in ch["chapters"] if not c.get("span_empty")]
    ordered = sorted(live, key=lambda c: c["start"])
    for a, b in zip(ordered, ordered[1:]):
        assert b["start"] > a["end"], (a["seq"], b["seq"])
    intro = ch["chapters"][0]
    assert intro["start"] >= 0
    assert intro["end"] > intro["start"]
    last = ch["chapters"][213]
    assert "闻风而动" in (last.get("matched_title") or "")


def test_citation_spotcheck_hits():
    spots = json.loads((EVAL / "citation_spotcheck.json").read_text(encoding="utf-8"))
    assert len(spots) >= 20
    misses = [s["quote"] for s in spots if not s["hit"]]
    assert misses == []


def test_holdout_chapters_not_all_skipped():
    holdout = json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"]
    ch = {c["seq"]: c for c in json.loads((EVAL / "chapters.json").read_text(encoding="utf-8"))["chapters"]}
    scored = [n for n in holdout if not ch[n].get("r1_skip_reason")]
    assert len(scored) >= 30
