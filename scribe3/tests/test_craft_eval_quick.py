"""C: frozen quick set + default provider is not hermes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scribe3.eval import verify_holdout_hash
from scribe3.eval.lotm import probe_seqs, verify_probe_hash
from scribe3.eval.provider import complete_for_provider
from scribe3.eval.score_r1 import scored_seqs

EVAL = Path(__file__).resolve().parents[1] / "eval"


def test_quick_set_frozen_8_plus_4():
    doc = json.loads((EVAL / "quick.json").read_text(encoding="utf-8"))
    assert doc["seed"] == 20260826
    assert len(doc["tonglu"]) == 8
    assert len(doc["lotm"]) == 4
    assert len(set(doc["tonglu"])) == 8
    assert len(set(doc["lotm"])) == 4
    holdout_scored = set(scored_seqs())
    probe = set(probe_seqs())
    assert set(doc["tonglu"]) <= holdout_scored
    assert set(doc["lotm"]) <= probe
    expected = (EVAL / "quick.sha256").read_text(encoding="utf-8").strip()
    import hashlib

    blob = (EVAL / "quick.json").read_bytes()
    if not blob.endswith(b"\n"):
        blob += b"\n"
    assert hashlib.sha256(blob).hexdigest() == expected
    verify_holdout_hash()
    verify_probe_hash()


def test_default_provider_is_coding_not_hermes():
    with pytest.raises(SystemExit):
        complete_for_provider("coding")


def test_unknown_provider_fails_loud():
    with pytest.raises(SystemExit):
        complete_for_provider("mystery")


def test_run_r1_main_coding_refuses_silent_hermes():
    from scribe3.eval.run_r1 import main

    with pytest.raises(SystemExit, match="coding"):
        main(["--quick", "--label", "nope"])
