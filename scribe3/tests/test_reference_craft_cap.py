"""P1：reference_craft 一次 push、最多 2 条。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_v1_caps_two_and_pushes_once():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "craft_briefs_for_write(st, str(work or \"main\"))[:2]" in src
    assert src.count('_push("reference_craft"') == 1
    assert '"\\n".join(_rf_parts)' in src or "'\\n'.join(_rf_parts)" in src
