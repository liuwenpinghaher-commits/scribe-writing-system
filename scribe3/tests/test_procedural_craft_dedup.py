"""P1：envelope procedural 相对 craft compact 去重。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scribe3.api.services.write_assemble_context import procedural_stats_from_envelope
from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.injection_compact import (
    filter_procedural_lines,
    line_echoes_cover,
)


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_line_echoes_cover_compact_and_per_line():
    craft = (
        "## 写作引擎(题材无关,渲染时遵守)\n"
        "- 【身体先行】情感的展示顺序永远是 身体→行动→沉默→语言。\n"
        "- [purple_regex] 少用翻译腔堆砌 — 乱世铜炉升华句\n"
    )
    assert line_echoes_cover("- 工艺:少用翻译腔堆砌", craft)
    assert line_echoes_cover("少用 翻译腔 堆砌", craft)
    assert not line_echoes_cover("- 工艺:限知章配角勿批发真相", craft)
    assert not line_echoes_cover("", craft)
    assert not line_echoes_cover("- 工艺:少用翻译腔堆砌", "")


def test_filter_drops_craft_echo_keeps_unique_lesson():
    craft = "- [note] 限知章配角勿批发真相 — 工艺卫生\n- 【留白】情绪不解释\n"
    kept, n = filter_procedural_lines(
        [
            "- 工艺:限知章配角勿批发真相",
            "- 工艺:作者偏好潮票Alpha只写可见动作",
        ],
        craft,
    )
    assert n == 1
    assert kept == ["- 工艺:作者偏好潮票Alpha只写可见动作"]


def test_stats_count_items_and_dedup_omitted():
    env = SimpleNamespace(
        blocks=[
            SimpleNamespace(name="recent", text="- 甲\n"),
            SimpleNamespace(
                name="procedural",
                text="## 工艺方法\n- 工艺:只写可见动作\n",
            ),
        ],
        omitted=[
            {"block": "procedural", "reason": "deduped_by_craft"},
            {"block": "procedural", "reason": "token_budget"},
            {"block": "canonical", "reason": "deduped_by_craft"},
        ],
    )
    stats = procedural_stats_from_envelope(env)
    assert stats["procedural_item_count"] == 1
    assert stats["procedural_dedup_dropped"] == 1
    assert procedural_stats_from_envelope(SimpleNamespace(blocks=[], omitted=[])) == {
        "procedural_item_count": 0,
        "procedural_dedup_dropped": 0,
    }


def test_assembler_and_v1_wire_compact_dedup():
    root = Path(__file__).resolve().parents[1]
    asm = (root / "context_assembler.py").read_text(encoding="utf-8")
    v1 = (root / "api/services/write_assemble_v1.py").read_text(encoding="utf-8")
    assert "def _dedup_procedural_against_craft(" in asm
    assert 'deduped_by_craft' in asm
    assert "line_echoes_cover" in asm
    assert "build_craft_block" in asm
    assert "def _procedural_rule_text(" in asm
    # 查询失败仍 fail-loud，不得悄悄吞
    assert "list_craft_rules() or []" in asm
    assert "procedural_stats_from_envelope" in v1
    assert 'bud_rep["procedural_item_count"]' in v1
    assert 'bud_rep["procedural_dedup_dropped"]' in v1
