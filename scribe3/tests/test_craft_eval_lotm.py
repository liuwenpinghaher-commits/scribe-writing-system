"""B: 节/章 read-side alias + LOTM chapter map / probe freeze."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scribe3.eval import verify_holdout_hash
from scribe3.eval.card_schema import CARD_HEADINGS, canonical_heading
from scribe3.eval.extract_card import missing_headings, parse_card
from scribe3.eval.lotm import (
    GOLD_DIR,
    load_gold_card,
    load_source_slice,
    probe_seqs,
    verify_probe_hash,
)
from scribe3.eval.score_r1 import load_label_card, score_pair

EVAL = Path(__file__).resolve().parents[1] / "eval"
ROOT = Path(__file__).resolve().parents[2]


def test_canonical_heading_jie_zhang():
    assert canonical_heading("留给下一章的日子") == "留给下一节的日子"
    assert canonical_heading("这一节回不去的事") == "这一节回不去的事"
    assert canonical_heading("打开书") == "打开书"


def test_lotm_card_parses_as_jie_headings():
    md = (GOLD_DIR / "0.md").read_text(encoding="utf-8")
    parts = parse_card(md)
    assert missing_headings(parts) == []
    assert "留给下一节的日子" in parts
    assert "这一节回不去的事" in parts
    assert "周明瑞" in parts["打开书"]


def test_jie_zhang_alias_does_not_change_tonglu_gold_score():
    gold = load_label_card(1)
    pred = gold.replace("这一节", "这一章").replace("下一节", "下一章")
    assert "这一章" in pred
    a = score_pair(gold, gold)
    b = score_pair(pred, gold)
    assert a["score"] == b["score"] == 1.0


def test_tonglu_r1_before_artifact_frozen():
    doc = json.loads((EVAL / "r1_before.json").read_text(encoding="utf-8"))
    assert doc["mean"] == 0.439
    assert doc["n"] == 41
    assert doc["holdout_sha256"] == verify_holdout_hash()


def test_tonglu_r2_before_artifact_frozen():
    doc = json.loads((EVAL / "r2_before.json").read_text(encoding="utf-8"))
    assert doc["score"] == 0.2256
    assert doc["n"] == 164
    assert doc["by_kind"]["cut"] == 0.0


def test_rescore_r1_before_preds_mean_unchanged():
    pred_dir = EVAL / "preds" / "r1_before"
    if not pred_dir.exists():
        return
    rows = []
    for path in sorted(pred_dir.glob("*.md")):
        seq = int(path.stem)
        rows.append(score_pair(path.read_text(encoding="utf-8"), load_label_card(seq))["score"])
    assert len(rows) == 41
    mean = round(sum(rows) / len(rows), 4)
    assert mean == 0.439


def test_chapters_lotm_covers_1394():
    ch = json.loads((EVAL / "chapters_lotm.json").read_text(encoding="utf-8"))
    seqs = [c["seq"] for c in ch["chapters"]]
    assert seqs == list(range(1394))
    assert ch["line_base"] == 1
    first, last = ch["chapters"][0], ch["chapters"][-1]
    assert first["start"] == 13
    assert last["seq"] == 1393
    assert first["end"] >= first["start"]
    for a, b in zip(ch["chapters"], ch["chapters"][1:]):
        assert b["start"] == a["end"] + 1, (a["seq"], b["seq"])


def test_lotm_source_slice_ch0_has_pain():
    text = load_source_slice(0)
    assert "痛！" in text
    assert "左轮" in text


def test_lotm_citation_spotcheck_hits():
    spots = json.loads((EVAL / "citation_spotcheck_lotm.json").read_text(encoding="utf-8"))
    assert len(spots) >= 20
    misses = [s["quote"] for s in spots if not s["hit"]]
    assert misses == []


def test_probe_lotm_frozen_seed_and_hash():
    doc = json.loads((EVAL / "probe_lotm.json").read_text(encoding="utf-8"))
    assert doc["seed"] == 20260826
    assert doc["n"] == 20
    assert len(doc["probe"]) == 20
    assert len(set(doc["probe"])) == 20
    assert all(0 <= n <= 1393 for n in doc["probe"])
    got = verify_probe_hash()
    expected = (EVAL / "probe_lotm.sha256").read_text(encoding="utf-8").strip()
    assert got == expected
    assert len(got) == 64


def test_probe_not_in_card_headings_count():
    assert len(CARD_HEADINGS) == 21


def test_mixed_fewshot_skips_holdout_and_probe():
    from scribe3.eval.lotm import pick_mixed_fewshot

    holdout = set(json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"])
    probe = set(probe_seqs())
    shot = pick_mixed_fewshot(exclude=8, book="tonglu")
    assert shot
    first = shot.strip().splitlines()[0]
    seq = int(first[2:].split()[0])
    assert seq not in holdout
    assert seq not in probe


def test_lotm_probe_gold_ceiling_runs():
    seqs = probe_seqs()
    assert len(seqs) == 20
    scores = []
    for seq in seqs:
        gold = load_gold_card(seq)
        scores.append(score_pair(gold, gold)["score"])
    assert len(scores) == 20
    assert sum(scores) / 20 == 1.0
