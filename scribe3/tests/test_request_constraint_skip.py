"""P1：空 extra 不 push request_constraint。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_v1_skips_blank_extra():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert 'if (extra_instructions or "").strip():' in src
    assert "empty_request_constraint" in src
    assert '_push("request_constraint", "supplemental", _rc)' in src
    assert 'bud_rep["request_constraint_injected"]' in src
    assert 'bud_rep["request_constraint_skip_reason"]' in src
    # 不把整段聊天无条件塞进 prefix
    assert "prefix += extra_instructions" not in src
