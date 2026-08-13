"""P1：discourse_soft 与 final_reminder CORE 差集。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD, subtract_codex_canonical_echoes


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_drop_line_already_in_core():
    core = "（硬纪律·短核:① 围栏;③ 情感不可直说(show, don't tell);）"
    disc = "【话语】\n情感不可直说(show, don't tell)\n换气短句推进\n"
    out = subtract_codex_canonical_echoes(disc, core)
    assert "情感不可直说" not in out
    assert "换气短句推进" in out


def test_v1_subtracts_discourse_against_final_reminder():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "subtract_codex_canonical_echoes(_d_txt, _fr or \"\")" in src
    assert "echo_core_or_empty" in src
