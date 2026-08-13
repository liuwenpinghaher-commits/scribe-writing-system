"""P1：pressure_drive 差集空键 + 禁复述 drama goal。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.injection_compact import (
    collect_drama_goal_phrases,
    drama_gcd_view_from_chapter,
    strip_pressure_goal_echoes,
)


CH = {
    "beats": [
        {"goal": "夺回铜匙", "conflict": "麻三娘拦门", "turn": "匙落入井", "cost": "暴露行踪"},
    ],
}


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_gcd_view_from_beats_when_no_drama_dict():
    view = drama_gcd_view_from_chapter(CH)
    assert view["goal"] == "夺回铜匙"
    assert view["conflict"] == "麻三娘拦门"
    assert collect_drama_goal_phrases(CH) == ["夺回铜匙"]


def test_strip_goal_line_from_pressure():
    pd = (
        "## 压力驱动合同（遵守力学，勿复述本段）\n"
        "- 目标：夺回铜匙\n"
        "- 分叉：退须改局\n"
    )
    out = strip_pressure_goal_echoes(pd, ["夺回铜匙"])
    assert "夺回铜匙" not in out
    assert "退须改局" in out


def test_v1_retries_empty_drama_and_strips_goal():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "drama_gcd_view_from_chapter" in src
    assert "strip_pressure_goal_echoes" in src
    assert 'pressure_diff_fail' in src
    assert "pressure_diff_keys(_pdc, {})" in src
