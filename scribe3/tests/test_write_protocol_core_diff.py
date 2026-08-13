"""P1：write_protocol 独立段，并与 CORE 尾注差集。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.prompt_blocks import _final_reminder_core
from scribe3.context_budget import (
    L0_NEVER_CUT,
    NOVEL_PROMPT_HARD,
    generation_physical_order_names,
    subtract_codex_canonical_echoes,
)


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000
    assert "write_protocol" in L0_NEVER_CUT


def test_order_protocol_between_identity_and_prefix():
    order = generation_physical_order_names()
    assert order.index("identity") < order.index("write_protocol")
    assert order.index("write_protocol") < order.index("prefix")


def test_drop_protocol_line_already_in_core():
    core = _final_reminder_core()
    proto = (
        "你是这部小说的主编\n"
        "情感不可直说(show, don't tell)\n"
        "若作者只是讨论则禁止输出围栏\n"
    )
    out = subtract_codex_canonical_echoes(proto, core)
    assert "情感不可直说" not in out
    assert "禁止输出围栏" in out
    assert "主编" in out


def test_real_protocol_howto_survives_core():
    blocks = (
        Path(__file__).resolve().parents[1]
        / "api/services/write_assemble_blocks.py"
    ).read_text(encoding="utf-8")
    assert "讨论 vs 动稿" in blocks
    assert "⟦PROPOSAL" in blocks
    proto = (
        "讨论 vs 动稿\n"
        "情感不可直说(show, don't tell)\n"
        "⟦PROPOSAL scope=chapter⟧\n"
    )
    out = subtract_codex_canonical_echoes(proto, _final_reminder_core())
    assert "讨论 vs 动稿" in out
    assert "⟦PROPOSAL" in out
    assert "情感不可直说" not in out


def test_v1_splits_and_subtracts_protocol():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "subtract_codex_canonical_echoes(" in src
    assert "_protocol_raw" in src
    assert '_push("write_protocol", "redline", _protocol_txt)' in src
    assert "write_protocol_echo_core_or_empty" in src
    assert 'bud_rep["write_protocol_injected"]' in src
    # 不再吞进 prefix
    assert "prefix = (\n        _write_protocol_block()" not in src
