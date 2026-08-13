"""P1：volume_intro 保持 compact，空不 push。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.injection_compact import compact_volume_intro


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_compact_when_title_already_in_synopsis():
    long_intro = "本卷写铜炉巷的香债与夜审，灰七要在侧门把假片换成热灰。" * 3
    out = compact_volume_intro(
        long_intro,
        synopsis="灰七要去侧门查昨夜脚印，铜炉巷香债未了",
        outline_text="",
        volume_title="铜炉巷",
        volume_goal="还香债",
    )
    assert out.startswith("卷钩：")
    assert len(out) <= 120


def test_empty_input_stays_empty():
    assert compact_volume_intro("") == ""
    assert compact_volume_intro("   ") == ""


def test_v1_skips_empty_after_compact():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "compact_volume_intro" in src
    assert "empty_volume_intro" in src
    assert "if (_vol_intro or \"\").strip():" in src
    assert '_push("volume_intro", "supplemental", _vi)' in src
    assert 'bud_rep["volume_intro_injected"]' in src
