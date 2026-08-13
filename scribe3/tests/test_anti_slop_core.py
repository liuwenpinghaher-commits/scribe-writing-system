"""P1：anti_slop 三处收成一处短核。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_blocks import _anti_slop_floor_block
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_short_core_covers_sincerity():
    text = _anti_slop_floor_block()
    assert "真诚相信" in text
    assert "他感到" in text
    assert "目光深邃" not in text
    assert len(text) < 280


def test_v1_no_longer_pushes_sincerity():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert '_push("sincerity"' not in src
    assert "_anti_slop_floor_block()" in src
