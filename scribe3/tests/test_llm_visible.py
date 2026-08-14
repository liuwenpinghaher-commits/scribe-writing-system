"""正式输出剥 thinking：不计、不记、不落库。禁止 Surreal。"""
from __future__ import annotations

from scribe3.llm_visible import (
    PROVIDER_MAX_TOKENS_HARD,
    VisibleStreamFilter,
    strip_thinking_markup,
    visible_message_text,
    visible_usage,
    with_thinking_headroom,
)


def test_thinking_headroom_leaves_official_budget():
    assert with_thinking_headroom(16384) == PROVIDER_MAX_TOKENS_HARD
    assert with_thinking_headroom(8192) == 16384
    assert with_thinking_headroom(777) == 777 + 4096
    assert with_thinking_headroom(123, thinking="disabled") == 123
    assert with_thinking_headroom(None) is None


def test_strip_think_block_keeps_official_prose():
    raw = "<think>先盘一下霍三刀的动机</think>沈拾灯把灯册按在腕上。"
    assert strip_thinking_markup(raw) == "沈拾灯把灯册按在腕上。"


def test_strip_unclosed_think_drops_tail():
    raw = "前半。<think>这段推理还没结束"
    assert strip_thinking_markup(raw) == "前半。"


def test_visible_message_ignores_reasoning_fields():
    msg = {
        "content": "正式正文",
        "reasoning_content": "模型心里的盘算" * 20,
        "thinking": "不该进字数",
    }
    assert visible_message_text(msg) == "正式正文"


def test_visible_message_empty_when_only_thinking():
    msg = {"content": "<think>只有推理</think>", "reasoning_content": "还是推理"}
    assert visible_message_text(msg) == ""


def test_visible_usage_subtracts_reasoning_tokens():
    usage = {
        "prompt_tokens": 10,
        "completion_tokens": 100,
        "total_tokens": 110,
        "completion_tokens_details": {"reasoning_tokens": 80},
    }
    out = visible_usage(usage)
    assert out["completion_tokens"] == 20
    assert out["total_tokens"] == 30
    assert "completion_tokens_details" not in out


def test_stream_filter_splits_think_tags_across_chunks():
    filt = VisibleStreamFilter()
    assert filt.feed("<th") == ""
    assert filt.feed("ink>秘密推理") == ""
    assert filt.feed("</think>场面开始") == "场面开始"
    assert filt.flush() == ""


def test_iceberg_cn_len_does_not_count_think():
    from scribe3.iceberg import cn_len
    fat_think = "<think>" + ("推" * 800) + "</think>沈拾灯按册。"
    assert cn_len(fat_think) == cn_len("沈拾灯按册。")
    assert cn_len(fat_think) < 20


def test_record_provider_usage_stores_official_tokens_only():
    import os
    import tempfile
    import scribe3.usage as U
    with tempfile.TemporaryDirectory() as td:
        prev = os.environ.get("SCRIBE3_LLM_LEDGER")
        os.environ["SCRIBE3_LLM_LEDGER"] = td + "/l.sqlite3"
        try:
            assert U.record_provider_usage(
                provider="qwen",
                model="qwen3.8-max-preview",
                transport="httpx",
                status="completed",
                http_status=200,
                usage={
                    "prompt_tokens": 12,
                    "completion_tokens": 90,
                    "total_tokens": 102,
                    "completion_tokens_details": {"reasoning_tokens": 70},
                },
            ) is True
            summary = U.provider_usage_summary(days=7)
            groups = summary["days"][0]["groups"]
            row = next(g for g in groups if g["status"] == "completed")
            assert row["output_tokens"] == 20
            assert row["total_tokens"] == 32
        finally:
            if prev is None:
                os.environ.pop("SCRIBE3_LLM_LEDGER", None)
            else:
                os.environ["SCRIBE3_LLM_LEDGER"] = prev
