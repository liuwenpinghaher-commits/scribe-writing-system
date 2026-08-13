"""P1：fabric 开时 query 兜底 + recent_item_count。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scribe3.api.services.write_stream import _build_write_retrieval_query
from scribe3.api.services.write_assemble_context import (
    recent_item_count_from_envelope,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


class _St:
    def __init__(self, syn=""):
        self.syn = syn

    def get_chapter(self, seq):
        return {"synopsis": self.syn} if self.syn else {}


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_query_prefers_seed_then_request_then_synopsis():
    assert _build_write_retrieval_query(
        _St("章纲"), chapter=1, seed_words=["侧门", "油灯"], request_text="忽略",
    ) == "侧门 油灯"
    assert _build_write_retrieval_query(
        _St("章纲"), chapter=1, seed_words=[], request_text="作者本轮要写拦门",
    ) == "作者本轮要写拦门"
    assert _build_write_retrieval_query(
        _St("灰七去侧门"), chapter=1, seed_words=[], request_text="",
    ) == "灰七去侧门"


def test_query_empty_without_seed_request_or_synopsis():
    assert _build_write_retrieval_query(
        _St(""), chapter=9, seed_words=[], request_text="",
    ) == ""


def test_recent_item_count_counts_dash_lines():
    env = SimpleNamespace(blocks=[
        SimpleNamespace(name="global", text="北极星:x"),
        SimpleNamespace(name="recent", text="- 本章已写结尾:甲\n- 上一章结尾:乙\n"),
    ])
    assert recent_item_count_from_envelope(env) == 2
    assert recent_item_count_from_envelope(SimpleNamespace(blocks=[])) == 0


def test_v1_fallback_and_report_key():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert 'recent_query_fallback' in src
    assert '第{chapter}章续写' in src
    assert 'bud_rep["recent_item_count"]' in src
    assert "recent_item_count_from_envelope" in src
