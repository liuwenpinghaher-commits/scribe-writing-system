"""讨论近窗不随 96k 膨胀。禁止本机 Surreal。"""
from __future__ import annotations

import inspect
from pathlib import Path

from scribe3.api.services.prompt_blocks import (
    DISCUSS_LAST_ASSISTANT_CHARS,
    DISCUSS_MAX_CHARS_EACH,
    DISCUSS_MAX_MSGS,
    DISCUSS_MAX_TOTAL_CHARS,
    DISCUSS_SUMMARY_CHARS,
    _thread_history_for_prompt,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget_untouched():
    assert NOVEL_PROMPT_HARD == 48000


def test_discuss_defaults_pinned():
    assert DISCUSS_MAX_MSGS == 12
    assert DISCUSS_MAX_CHARS_EACH == 600
    assert DISCUSS_LAST_ASSISTANT_CHARS == 2400
    assert DISCUSS_MAX_TOTAL_CHARS == 8000
    assert DISCUSS_SUMMARY_CHARS == 1600
    sig = inspect.signature(_thread_history_for_prompt)
    assert sig.parameters["max_msgs"].default == 12
    assert sig.parameters["max_chars_each"].default == 600
    assert sig.parameters["last_assistant_chars"].default == 2400
    assert sig.parameters["max_total_chars"].default == 8000


def test_agentic_does_not_pass_conversation_history():
    src = (
        Path(__file__).resolve().parents[1] / "api/routers/misc_routes.py"
    ).read_text(encoding="utf-8")
    # 写/讨论 agentic 口只传 previous_response_id，不塞 conversation_history
    agentic = src[src.find("def chat_agentic_stream") : src.find("def chat_agentic_stream") + 8000]
    assert "previous_response_id=turn.previous_response_id" in agentic
    assert "conversation_history=" not in agentic
