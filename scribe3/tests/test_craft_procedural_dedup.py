"""P1：craft 与 envelope procedural 整行去重。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD, subtract_codex_canonical_echoes


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_craft_line_dropped_if_in_procedural():
    craft = "【工艺】\n- 工艺:少用翻译腔堆砌\n- 工艺:章末留钩\n"
    env = "## 工艺方法(已采纳的写作方法/教训)\n- 工艺:少用翻译腔堆砌\n"
    out = subtract_codex_canonical_echoes(craft, env)
    assert "少用翻译腔堆砌" not in out
    assert "章末留钩" in out


def test_v1_subtracts_craft_against_envelope():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "subtract_codex_canonical_echoes(craft, env_text or \"\")" in src
    assert 'empty_craft' in src
