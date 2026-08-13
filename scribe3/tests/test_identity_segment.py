"""P1：identity 独立 _push，不吞进 prefix。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import (
    L0_NEVER_CUT,
    NOVEL_PROMPT_HARD,
    generation_physical_order_names,
)


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000
    assert "identity" in L0_NEVER_CUT


def test_order_identity_before_prefix():
    order = generation_physical_order_names()
    assert order.index("identity") < order.index("prefix")


def test_v1_pushes_identity_separately():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert src.count('_push("identity", "redline", _identity_txt)') == 1
    assert "_editor_identity_block()" in src
