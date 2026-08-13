"""P1：budget_report 必带 envelope 八块长度。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scribe3.api.services.write_assemble_context import (
    ENVELOPE_BLOCK_NAMES,
    envelope_block_lengths_from_envelope,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000
    assert ENVELOPE_BLOCK_NAMES == (
        "focus", "global", "canonical", "recent",
        "procedural", "reference", "uncertainty", "provenance",
    )


def test_eight_keys_even_when_sparse():
    env = SimpleNamespace(blocks=[
        SimpleNamespace(name="focus", text="焦"),
        SimpleNamespace(name="canonical", text="正典事实"),
    ])
    lens = envelope_block_lengths_from_envelope(env)
    assert set(lens) == set(ENVELOPE_BLOCK_NAMES)
    assert lens["focus"] == 1
    assert lens["canonical"] == 4
    assert lens["provenance"] == 0
    assert lens["global"] == 0


def test_v1_writes_report_key():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "envelope_block_lengths_from_envelope" in src
    assert 'bud_rep["envelope_block_lengths"]' in src
    assert '_push("envelope", "envelope"' in src
