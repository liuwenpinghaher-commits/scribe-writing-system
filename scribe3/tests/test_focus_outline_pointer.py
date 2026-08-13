"""P1：focus 只留 outline 指针，budget_report 可观测。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scribe3.api.services.write_assemble_context import (
    focus_has_outline_pointer_from_envelope,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_pointer_bool_from_envelope():
    env = SimpleNamespace(blocks=[
        SimpleNamespace(name="focus", text="- 当前第 3 章\n- 本章大纲/节拍:见 outline 域（勿重复展开）\n"),
        SimpleNamespace(name="outline", text="灰七去侧门"),
    ])
    assert focus_has_outline_pointer_from_envelope(env) is True
    assert focus_has_outline_pointer_from_envelope(
        SimpleNamespace(blocks=[SimpleNamespace(name="focus", text="- 当前第 3 章")])
    ) is False
    assert focus_has_outline_pointer_from_envelope(SimpleNamespace(blocks=[])) is False


def test_assembler_keeps_pointer_not_synopsis():
    src = (
        Path(__file__).resolve().parents[1] / "context_assembler.py"
    ).read_text(encoding="utf-8")
    assert "见 outline 域" in src
    assert "勿重复展开" in src
    assert "不再展开 synopsis/beats 全文" in src


def test_v1_reports_pointer():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "focus_has_outline_pointer_from_envelope" in src
    assert 'bud_rep["focus_has_outline_pointer"]' in src
