"""P1：canonical 丢掉已在 codex 的 fact 行。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import (
    NOVEL_PROMPT_HARD,
    subtract_canonical_lines_in_codex,
)


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_drops_canon_line_already_in_codex():
    env = (
        "## 权威事实(正典表:事实/事件/承诺/知识帧)\n"
        "- 甲是铜炉巷里的人\n"
        "- 昨夜侧门有新脚印\n"
        "## 近期(工作摘要·近期事件/决策)\n"
        "- 甲是铜炉巷里的人\n"
    )
    codex = "设定：甲是铜炉巷里的人。势力规矩另见。\n"
    out, n = subtract_canonical_lines_in_codex(env, codex)
    assert n == 1
    canon, recent = out.split("## 近期", 1)
    assert "甲是铜炉巷里的人" not in canon
    assert "昨夜侧门有新脚印" in canon
    assert "甲是铜炉巷里的人" in recent


def test_empty_inputs():
    assert subtract_canonical_lines_in_codex("", "x") == ("", 0)
    assert subtract_canonical_lines_in_codex("## 权威事实\n- 甲在村里\n", "")[1] == 0


def test_v1_subtracts_before_push():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "subtract_canonical_lines_in_codex" in src
    assert 'bud_rep["canonical_codex_echoes_dropped"]' in src
    assert '_push("envelope", "envelope"' in src
