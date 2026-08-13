"""P1：revelation_discipline 相对 CORE 只留一句。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.prompt_blocks import (
    _final_reminder_core,
    _revelation_discipline_block,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.injection_compact import clip_revelation_to_core_delta


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_empty_without_focalizer():
    assert _revelation_discipline_block("") == ""
    assert _revelation_discipline_block(None) == ""
    assert clip_revelation_to_core_delta("", _final_reminder_core()) == ""


def test_keeps_only_one_unique_bullet():
    core = _final_reminder_core()
    block = (
        "## 限知揭示纪律(本章 灰七 限知视角,务必遵守)\n"
        "- 限知不自悟真相\n"
        "- 配角不得整段向焦点者批发背景来历\n"
        "- 禁 as-you-know 与廉价偷听交底\n"
    )
    out = clip_revelation_to_core_delta(block, core)
    assert "配角不得整段" in out
    assert out.count("- ") == 1
    assert "as-you-know" not in out
    assert "不自悟真相" not in out
    assert out.startswith("## 限知揭示纪律")


def test_real_block_clips_to_one_delta():
    block = _revelation_discipline_block("灰七")
    assert block.count("- ") >= 3
    out = clip_revelation_to_core_delta(block, _final_reminder_core())
    assert "限知揭示纪律" in out
    assert "灰七" in out
    assert out.count("- ") == 1


def test_v1_wires_clip_and_skip():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "clip_revelation_to_core_delta" in src
    assert "revelation_skip_no_focalizer" in src
    assert "revelation_echo_core" in src
    assert 'bud_rep["revelation_injected"]' in src
    assert '_push("revelation_discipline", "redline", _rev)' in src
