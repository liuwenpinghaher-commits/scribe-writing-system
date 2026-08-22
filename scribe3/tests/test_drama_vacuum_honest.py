"""P1：drama_vacuum 仅无 goal∧conflict；短句禁工程词。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.drama_beats import (
    DRAMA_VACUUM_WARN_TEXT,
    format_drama_vacuum_warn,
    should_inject_drama_vacuum,
)
from scribe3.injection_registry import DRAMA_CORE_NAMES


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_hook_only_still_vacuum():
    beats = [{"hook": "井底有声", "text": "出门"}]
    assert should_inject_drama_vacuum(beats, chapter_hook="井底有声") is True
    assert "GCD" not in format_drama_vacuum_warn(beats=beats)
    assert "作者执行" not in format_drama_vacuum_warn(beats=beats)
    assert "缺目标与阻力" in format_drama_vacuum_warn(beats=beats)


def test_goal_and_conflict_suppress_vacuum():
    beats = [{"goal": "夺回铜匙", "conflict": "麻三娘拦门"}]
    assert should_inject_drama_vacuum(beats) is False
    assert format_drama_vacuum_warn(beats=beats) == ""


def test_thick_beat_text_suppresses_vacuum():
    """冰山场面纸写在 text，GCD 可空；不得再灌缺目标。"""
    beats = [{"text": "进场。冷锅婆空锅拦门。" + ("场面" * 40)}]
    assert should_inject_drama_vacuum(beats) is False
    assert format_drama_vacuum_warn(beats=beats) == ""


def test_vacuum_not_in_drama_core():
    assert "drama_vacuum" not in DRAMA_CORE_NAMES


def test_copy_has_no_engineering_words():
    assert "GCD" not in DRAMA_VACUUM_WARN_TEXT
    assert "巷志" not in DRAMA_VACUUM_WARN_TEXT
    assert "作者执行" not in DRAMA_VACUUM_WARN_TEXT


def test_v1_uses_should_inject():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "should_inject_drama_vacuum" in src
    assert 'drama_vacuum_injected' in src
