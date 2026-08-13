"""P1：codex 与 canonical 差集后再 cap；观测 codex_chars。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import (
    DEFAULT_CODEX_INJECT_CAP,
    NOVEL_PROMPT_HARD,
    cap_codex_text,
    subtract_codex_canonical_echoes,
)


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000
    assert DEFAULT_CODEX_INJECT_CAP == 4500


def test_subtract_drops_echo_lines_keeps_unique():
    codex = (
        "【本书设定圣经】\n"
        "- 灰七：香债未清还欠一炉\n"
        "- 冷锅婆：铜炉鬼真名不可喊\n"
    )
    can = "权威事实(正典)\n- 灰七：香债未清还欠一炉\n"
    out = subtract_codex_canonical_echoes(codex, can)
    assert "香债未清还欠一炉" not in out
    assert "铜炉鬼真名不可喊" in out
    assert "【本书设定圣经】" in out


def test_subtract_noop_when_canonical_empty():
    src = "- 独自一行设定甲乙丙丁\n"
    assert subtract_codex_canonical_echoes(src, "") == src
    assert subtract_codex_canonical_echoes(src, None) == src


def test_cap_after_subtract():
    long = "- " + ("设定" * 3000)
    can = ""
    out = cap_codex_text(subtract_codex_canonical_echoes(long, can), 80)
    assert len(out) <= 80
    assert out.endswith("…")


def test_v1_subtracts_then_caps_and_reports_chars():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "subtract_codex_canonical_echoes(codex_input, env_text or \"\")" in src
    assert 'bud_rep["codex_chars"]' in src
    assert "_budget_report_holder[\"codex_chars\"]" in src
