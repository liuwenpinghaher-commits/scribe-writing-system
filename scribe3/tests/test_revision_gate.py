"""P1：非修订请求不注入修订纪律。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_blocks import (
    _write_revision_block,
    is_revision_request,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_is_revision_request_phase_and_hints():
    assert not is_revision_request()
    assert not is_revision_request(phase="draft")
    assert not is_revision_request(phase="final")
    assert not is_revision_request(request_text="续写本章，灰七去侧门")
    assert not is_revision_request(request_text="改天再写改名的那段铺垫")
    assert is_revision_request(phase="revise")
    assert is_revision_request(phase="REWRITE")
    assert is_revision_request(request_text="请改这段，只动最小片段")
    assert is_revision_request(extra_instructions="作者要求重写高潮")
    assert is_revision_request(request_text="按 span 级改选中句")


def test_revision_block_is_short_discipline():
    txt = _write_revision_block()
    assert "修订纪律" in txt
    assert "span" in txt
    assert "整章自评重写" in txt
    assert len(txt) < 400


def test_v1_gates_revision_push():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "is_revision_request(" in src
    assert 'revision_skip_not_requested' in src
    assert 'bud_rep["revision_injected"]' in src
    assert 'bud_rep["revision_skip_reason"]' in src
    assert '_push("revision", "redline", _revision_txt)' in src
    # 空则不 push
    assert "if _revision_txt:" in src
