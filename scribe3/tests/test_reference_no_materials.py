"""P1：reference 空素材 omitted 记 no_materials。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scribe3.api.services.write_assemble_context import (
    reference_no_materials_from_envelope,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_flag_from_omitted():
    env = SimpleNamespace(omitted=[
        {"block": "reference", "reason": "no_materials"},
    ])
    assert reference_no_materials_from_envelope(env) is True
    assert reference_no_materials_from_envelope(
        SimpleNamespace(omitted=[{"block": "reference", "reason": "token_budget"}])
    ) is False
    assert reference_no_materials_from_envelope(SimpleNamespace(omitted=[])) is False


def test_assembler_and_disclaimer():
    src = (
        Path(__file__).resolve().parents[1] / "context_assembler.py"
    ).read_text(encoding="utf-8")
    assert 'reason="borrow_not_fact"' in src
    assert '"reason": "no_materials"' in src
    assert "只有免责声明、没有任何素材" in src
    assert "_REFERENCE_DISCLAIMER" in src


def test_v1_reports_flag():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "reference_no_materials_from_envelope" in src
    assert 'bud_rep["reference_no_materials"]' in src
