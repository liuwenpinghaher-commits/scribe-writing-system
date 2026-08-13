"""R14：无真声口材料不注入空壳。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_context import (
    _voice_anchor_block,
    voice_anchor_registered_from_text,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


class _St:
    def get_voice_profile(self, focalizer):
        return None

    def list_voice_profiles(self):
        return []


class _StWith:
    def get_voice_profile(self, focalizer):
        return {"style_summary": "冷硬短句，少解释"}

    def list_voice_profiles(self):
        return [{"character_id": "role:灰七", "style_summary": "冷硬短句"}]


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_unregistered_line_when_no_profile():
    txt = _voice_anchor_block(_St(), "灰七")
    assert txt == ""
    assert voice_anchor_registered_from_text(txt) is False
    assert _voice_anchor_block(_St(), "") == ""
    assert voice_anchor_registered_from_text("") is False


def test_registered_when_profile_exists():
    txt = _voice_anchor_block(_StWith(), "灰七")
    assert "冷硬短句" in txt
    assert "未登记声口" not in txt
    assert voice_anchor_registered_from_text(txt) is True


def test_v1_reports_registered():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "_voice_anchor_block" in src
    assert 'bud_rep["voice_anchor_registered"]' in src
    assert "voice_anchor_registered_from_text" in src
