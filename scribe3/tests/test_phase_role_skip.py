"""P1：phase_role 保持去重，空 phase 不 push。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.injection_compact import dedup_phase_role


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_dedup_keeps_unique_drops_craft_echo():
    craft = "你此刻是写手:重限知帧——严格贴焦点者所知所感铺陈。"
    raw = (
        "你此刻是写手:重限知帧——严格贴焦点者所知所感铺陈\n"
        "先把这章的冲突时钟钉死\n"
    )
    out = dedup_phase_role(raw, craft_text=craft, anti_slop_text="")
    assert "冲突时钟" in out
    assert "限知帧" not in out


def test_dedup_empty_when_fully_covered():
    craft = "你此刻是规划者:重事件因果与结构骨架"
    assert dedup_phase_role(craft, craft_text=craft, anti_slop_text="") == ""
    assert dedup_phase_role("", craft_text="x", anti_slop_text="") == ""


def test_helper_empty_phase_and_v1_skip():
    helpers = (
        Path(__file__).resolve().parents[1] / "api/services/misc_helpers.py"
    ).read_text(encoding="utf-8")
    v1 = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "phase 空 → 返回空串" in helpers
    assert 'return f"\\n\\n{block}" if block else ""' in helpers
    assert "phase_role_skip_empty" in v1
    assert 'bud_rep["phase_role_injected"]' in v1
    assert "if (_pr_raw or \"\").strip():" in v1
    assert '_push("phase_role", "supplemental", _pr)' in v1
