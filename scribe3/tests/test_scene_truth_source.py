"""P1：scene_truth 路径写入 budget_report。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_context import (
    scene_truth_source_from_segment_names,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_source_enum():
    assert scene_truth_source_from_segment_names(["scene_truth_proj", "prefix"]) == "proj"
    assert scene_truth_source_from_segment_names(["deduction_final", "prefix"]) == "deduction_final"
    assert scene_truth_source_from_segment_names(["prefix", "envelope"]) == "none"
    # 双路径同时出现时以 deduce 终检段为准
    assert scene_truth_source_from_segment_names(
        ["scene_truth_proj", "deduction_final"]
    ) == "proj"


def test_v1_phase_split_and_report():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert 'if normalized_phase == "deduce":' in src
    assert '_push("scene_truth_proj", "redline", _st)' in src
    assert '_push("deduction_final", "redline"' in src
    assert 'bud_rep["scene_truth_source"]' in src
    assert "scene_truth_source_from_segment_names" in src
    # draft 不把终检合同抄进正文
    assert src.count("演绎终检合同") == 1
