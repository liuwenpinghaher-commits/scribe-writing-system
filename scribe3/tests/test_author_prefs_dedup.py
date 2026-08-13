"""P1：author_prefs 与 envelope/procedural 整行去重。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD, subtract_codex_canonical_echoes


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_pref_line_dropped_if_in_envelope():
    prefs = "【作者偏好】\n- 少用翻译腔形容词堆砌\n- 章末留半句钩\n"
    env = "## 程序/工艺\n- 少用翻译腔形容词堆砌\n"
    out = subtract_codex_canonical_echoes(prefs, env)
    assert "少用翻译腔形容词堆砌" not in out
    assert "章末留半句钩" in out


def test_v1_subtracts_prefs_against_envelope():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "subtract_codex_canonical_echoes(" in src
    assert 'empty_author_prefs' in src
    assert "_author_prefs_block_safe()" in src
