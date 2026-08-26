"""P1.5 ruler freeze: stop = floor + (ceiling − floor) × 0.7."""
from __future__ import annotations

import json
from pathlib import Path

from scribe3.eval import verify_holdout_hash

EVAL = Path(__file__).resolve().parents[1] / "eval"
EXPECTED_HASH = "fb460682bfcff4f2345699068cf818893094e733b987f1c19a91c267dfda4649"


def _stop(floor: float, ceiling: float) -> float:
    return floor + (ceiling - floor) * 0.7


def test_stop_formula_frozen():
    got = verify_holdout_hash()
    assert got == EXPECTED_HASH
    doc = json.loads((EVAL / "stop.json").read_text(encoding="utf-8"))
    assert doc["holdout_sha256"] == EXPECTED_HASH
    r1, r2 = doc["r1"], doc["r2"]
    assert r1["ceiling"] == 1.0 and r1["floor"] == 0.0
    assert r2["ceiling"] == 1.0 and r2["floor"] == 0.25
    assert abs(r1["stop"] - _stop(r1["floor"], r1["ceiling"])) < 1e-9
    assert abs(r2["stop"] - _stop(r2["floor"], r2["ceiling"])) < 1e-9
    assert abs(r1["stop"] - 0.70) < 1e-9
    assert abs(r2["stop"] - 0.775) < 1e-9


def test_human_spotcheck_is_ten_percent():
    doc = json.loads((EVAL / "human_spotcheck.json").read_text(encoding="utf-8"))
    r1 = json.loads((EVAL / "r1_before.json").read_text(encoding="utf-8"))
    assert doc["seed"] == 20260826
    assert doc["n_scored"] == r1["n"] == 41
    assert doc["k"] == max(1, round(doc["n_scored"] * 0.1))
    assert len(doc["seqs"]) == doc["k"]
    assert set(doc["seqs"]).issubset({row["seq"] for row in r1["rows"]})
