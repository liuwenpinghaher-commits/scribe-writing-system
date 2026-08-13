"""P1：uncertainty 正典取代行优先于低信心闲聊。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scribe3.api.services.write_assemble_context import (
    prioritize_superseded_items,
    uncertainty_stats_from_envelope,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_prioritize_superseded_first():
    items = [
        SimpleNamespace(text="待确认:巷口有人", source=SimpleNamespace(reason="")),
        SimpleNamespace(
            text="旧推测已被正典取代",
            source=SimpleNamespace(reason="superseded_by_canonical"),
        ),
        SimpleNamespace(text="待确认:闲聊", source=SimpleNamespace(reason="low")),
    ]
    out = prioritize_superseded_items(items)
    assert out[0].source.reason == "superseded_by_canonical"
    assert [it.text for it in out[1:]] == ["待确认:巷口有人", "待确认:闲聊"]


def test_stats_count_superseded_and_pending():
    env = SimpleNamespace(blocks=[
        SimpleNamespace(
            name="uncertainty",
            text=(
                "## 不确定\n"
                "- 旧推测已被正典取代(存疑,勿据此写):ep:1\n"
                "- 待确认:甲兄是否已死\n"
            ),
        ),
    ])
    stats = uncertainty_stats_from_envelope(env)
    assert stats["uncertainty_superseded_count"] == 1
    assert stats["uncertainty_pending_count"] == 1


def test_assembler_and_v1_wire_priority():
    asm = (
        Path(__file__).resolve().parents[1] / "context_assembler.py"
    ).read_text(encoding="utf-8")
    v1 = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "prioritize_superseded_items" in asm
    assert 'k == "uncertainty"' in asm
    assert "正典取代行必须先于低信心闲聊" in asm
    assert "uncertainty_stats_from_envelope" in v1
    assert 'bud_rep["uncertainty_superseded_count"]' in v1
