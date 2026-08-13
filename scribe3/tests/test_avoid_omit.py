"""P1：默认 omit 独立 avoid 段。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import NOVEL_PROMPT_HARD
from scribe3.injection_compact import should_omit_avoid_domain


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_omit_flag_defaults_on():
    assert should_omit_avoid_domain() is True


def test_v1_records_skip_and_does_not_push_when_omitted():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "should_omit_avoid_domain" in src
    assert "avoid_merged_into_antislop" in src
    assert "empty_avoid" in src
    assert 'bud_rep["avoid_injected"]' in src
    assert 'bud_rep["avoid_skip_reason"]' in src
    assert '_push("avoid", "supplemental", _av)' in src
    # 词表不得焊进 L0 prefix
    assert 'prefix = (\n        _avoid_directive' not in src
