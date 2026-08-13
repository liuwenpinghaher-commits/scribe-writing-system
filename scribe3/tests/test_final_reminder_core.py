"""P1：final_reminder 默认短核。禁止本机 Surreal。"""
from __future__ import annotations

import os

from scribe3.api.services.prompt_blocks import (
    _final_reminder,
    _final_reminder_core,
    _final_reminder_full,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD, join_generation_segments


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_default_is_core_not_eleven():
    os.environ.pop("SCRIBE3_FINAL_REMINDER_CORE", None)
    text = _final_reminder()
    assert text == _final_reminder_core()
    assert len(text) < len(_final_reminder_full())
    assert "as-you-know-Bob" not in text  # ⑪ 长段不在短核
    assert "情感不可直说" in text
    assert "show" in text
    assert "PROPOSAL" in text
    assert "乱世铜炉" not in text


def test_full_only_when_core_off():
    os.environ["SCRIBE3_FINAL_REMINDER_CORE"] = "0"
    try:
        text = _final_reminder()
        assert text == _final_reminder_full()
        assert "⑪" in text or "as-you-know" in text
    finally:
        os.environ.pop("SCRIBE3_FINAL_REMINDER_CORE", None)


def test_book_style_override():
    os.environ.pop("SCRIBE3_FINAL_REMINDER_CORE", None)
    os.environ["SCRIBE3_PROSE_STYLE"] = "冷硬科幻白描，禁古白话"
    try:
        text = _final_reminder()
        assert "冷硬科幻白描" in text
        assert "乱世铜炉" not in text
    finally:
        os.environ.pop("SCRIBE3_PROSE_STYLE", None)


def test_join_keeps_final_reminder():
    os.environ.pop("SCRIBE3_FINAL_REMINDER_CORE", None)
    fr = _final_reminder()
    _out, rep = join_generation_segments([
        {"name": "prefix", "layer": "redline", "text": "P"},
        {"name": "final_reminder", "layer": "redline", "text": fr},
    ])
    assert rep.get("final_reminder_kept") is True
    assert len(fr) == rep["domain_lengths"]["final_reminder"]
