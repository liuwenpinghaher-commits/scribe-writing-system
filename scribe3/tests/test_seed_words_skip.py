"""P1：空 soak 不 push seed_words。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_soak_empty_and_v1_skip():
    impl = (
        Path(__file__).resolve().parents[1] / "api/app_impl.py"
    ).read_text(encoding="utf-8")
    v1 = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "if not seed_words:" in impl
    assert 'return ""' in impl
    assert "empty_seed_words" in v1
    assert "if (_sw_raw or \"\").strip():" in v1
    assert '_push("seed_words", "supplemental", _sw)' in v1
    assert 'bud_rep["seed_words_injected"]' in v1
    assert 'bud_rep["seed_words_skip_reason"]' in v1
