"""P1：storyline_polish 空 meta 不 push，skip_reason 可查。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.storyline_inject_polish import prepare_write_storyline_inject


class _St:
    def chapters_lite(self):
        return []

    def list_storylines(self):
        return []

    def open_promises(self):
        return []


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_flag_off_skip_reason(monkeypatch=None):
    import scribe3.storyline_inject_polish as m
    orig = m.storyline_inject_enabled
    m.storyline_inject_enabled = lambda: False
    try:
        out = prepare_write_storyline_inject(_St(), chapter=1, work="main")
    finally:
        m.storyline_inject_enabled = orig
    assert out["text"] == ""
    assert out["meta"].get("skip_reason") == "flag_off"


def test_empty_meta_skip_reason():
    import scribe3.storyline_inject_polish as m
    orig = m.storyline_inject_enabled
    m.storyline_inject_enabled = lambda: True
    try:
        out = prepare_write_storyline_inject(_St(), chapter=1, work="main")
    finally:
        m.storyline_inject_enabled = orig
    assert not (out.get("text") or "").strip()
    assert out["meta"].get("skip_reason") == "empty_meta"


def test_v1_only_pushes_when_text():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "if _txt.strip():" in src
    assert '_push("storyline_polish"' in src
    assert "prepare_write_storyline_inject" in src
