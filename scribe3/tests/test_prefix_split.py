"""P1：prefix 只留身份+协议+anti_slop+章号；旁路独立 push。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import (
    NOVEL_PROMPT_HARD,
    generation_physical_order_names,
)


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_physical_order_prefix_then_bylines():
    order = generation_physical_order_names()
    assert order.index("prefix") < order.index("revision")
    assert order.index("revision") < order.index("continue_snapshot")
    assert order.index("continue_snapshot") < order.index("secret_guard")


def test_v1_prefix_no_longer_swallows_bylines():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert '_push("revision", "redline", _revision_txt)' in src
    assert '_push("continue_snapshot", "redline", _continue_txt)' in src
    assert 'bud_rep["continue_snapshot_skip_reason"] = _continue_skip' in src
    assert '_continue_skip = "empty_snapshot"' in src
    assert '_continue_skip = "reread_ack_required"' in src
    assert '_continue_skip = "continue_snapshot_error"' in src
    assert '_push("structure_diversity", "redline", _sd_txt)' in src
    assert '_push("tool_scope", "redline", _tool_txt)' in src
    assert "prefix += _domain_input(\n                    f\"chapter:{chapter}:continue-snapshot\"" not in src
    assert "_editor_identity_block()" in src
    assert "_anti_slop_floor_block()" in src
