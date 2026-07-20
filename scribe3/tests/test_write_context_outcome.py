"""``/chat/write`` 的 Manifest / Outcome 真实生产链。"""
from __future__ import annotations

import hashlib

import httpx
import pytest

import scribe3.app as A
from scribe3.context_store import ContextStore

from .test_app import _client


def _outcomes(store):
    return store._query(
        "SELECT outcome_id, request_id, manifest_id, actual_input_hash, status, "
        "provider, model, provider_request_id, usage, output_hash, error "
        "FROM context_outcome_trace",
        {},
    )


def test_unified_engine_failure_never_runs_legacy_scattered_chain(store, monkeypatch):
    from scribe3.context_engine import CreativeContextEngine

    def engine_failure(*args, **kwargs):
        raise RuntimeError("engine-failure-sentinel")

    monkeypatch.setattr(CreativeContextEngine, "compile", engine_failure)
    monkeypatch.setattr(
        A, "_editor_write_system",
        lambda *args, **kwargs: pytest.fail("统一引擎失败后不得进入旧散点链"),
    )

    with pytest.raises(RuntimeError, match="engine-failure-sentinel"):
        A._assemble_write_instructions(
            store, chapter=1, focalizer="", phase="final", seed_words=[],
            short_mode=False, with_tools=False, work="main",
        )


def test_chat_write_completed_persists_exact_input_and_raw_provider_output_hash(
    store, monkeypatch,
):
    captured = {}
    raw_delta = "处理说明。⟦PROPOSAL scope=chapter⟧供应商原始正文⟦/PROPOSAL⟧"

    def events(message, instructions, with_tools=True):
        captured["instructions"] = instructions
        captured["with_tools"] = with_tools
        yield {"type": "response.output_text.delta", "delta": raw_delta}
        yield {
            "type": "response.completed",
            "response": {
                "id": "deepseek-response-1",
                "model": "deepseek-chat",
                "usage": {"prompt_tokens": 31, "completion_tokens": 7},
            },
            "trace": {
                "provider": "deepseek", "api_base": "https://api.deepseek.com",
                "model": "deepseek-chat", "official": True, "transport": "httpx",
            },
        }

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "直接写本章", "chapter": 1, "phase": "final",
    })

    assert response.status_code == 200
    assert captured["with_tools"] is False
    rows = _outcomes(store)
    assert len(rows) == 1
    outcome = rows[0]
    manifest = ContextStore(store).get_manifest(outcome["manifest_id"])
    assert manifest is not None
    assert manifest.actual_input_hash == hashlib.sha256(
        captured["instructions"].encode("utf-8")
    ).hexdigest()
    assert outcome["actual_input_hash"] == manifest.actual_input_hash
    assert outcome["status"] == "succeeded"
    assert outcome["provider"] == "deepseek"
    assert outcome["model"] == "deepseek-chat"
    assert outcome["provider_request_id"] == "deepseek-response-1"
    assert outcome["usage"] == {"prompt_tokens": 31, "completion_tokens": 7}
    assert outcome["output_hash"] == hashlib.sha256(raw_delta.encode("utf-8")).hexdigest()

    assistant = [
        message for message in store.list_chat_messages(chapter=1)
        if message["role"] == "assistant"
    ][0]
    assert "供应商原始正文" not in assistant["text"]
    assert outcome["output_hash"] != hashlib.sha256(
        assistant["text"].encode("utf-8")
    ).hexdigest()


def test_real_official_sse_provider_id_reaches_context_outcome(store, monkeypatch):
    from scribe3 import deepseek_client as deepseek
    from scribe3 import llm

    provider_response_id = "chatcmpl-outcome-789"
    values = {
        "DEEPSEEK_API_KEY": "unit-test-deepseek-key",
        "llm.model": "deepseek-chat",
        "llm.timeout_seconds": 12.5,
        "llm.max_retries": 1,
    }
    monkeypatch.setattr(deepseek.settings, "get_setting", values.__getitem__)
    stream_body = "\n".join([
        f'data: {{"id":"{provider_response_id}","model":"deepseek-chat",'
        '"choices":[{"delta":{"content":"完成。"}}]}',
        "",
        f'data: {{"id":"{provider_response_id}","model":"deepseek-chat",'
        '"choices":[],"usage":{"total_tokens":4}}',
        "",
        "data: [DONE]",
        "",
    ])

    def handler(_request):
        return httpx.Response(200, text=stream_body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        monkeypatch.setattr(
            llm,
            "DeepSeekClient",
            lambda: deepseek.DeepSeekClient(client=transport),
        )
        monkeypatch.setattr(llm, "_tick_daily", lambda: None)
        monkeypatch.setattr(A, "_responses_events", None)
        response = _client(store).post("/chat/write", json={
            "msg": "直接写", "chapter": 7, "phase": "final",
        })

    assert response.status_code == 200
    rows = _outcomes(store)
    assert len(rows) == 1
    assert rows[0]["provider"] == "deepseek"
    assert rows[0]["provider_request_id"] == provider_response_id


def test_tool_route_records_hermes_provider_and_safely_narrows_nested_usage(
    store, monkeypatch,
):
    def events(message, instructions, with_tools=True):
        assert with_tools is True
        yield {"type": "response.output_text.delta", "delta": "已核实。"}
        yield {
            "type": "response.completed",
            "response": {
                "id": "hermes-response-1",
                "model": "gateway-model",
                "usage": {
                    "input_tokens": 19,
                    "output_tokens": 4,
                    "input_tokens_details": {"cached_tokens": 3},
                },
            },
        }

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "查询第一章后给建议", "chapter": 1, "phase": "draft",
    })

    assert response.status_code == 200
    rows = _outcomes(store)
    assert len(rows) == 1
    assert rows[0]["status"] == "succeeded"
    assert rows[0]["provider"] == "hermes_gateway"
    assert rows[0]["model"] == "gateway-model"
    assert rows[0]["provider_request_id"] == "hermes-response-1"
    assert rows[0]["usage"] == {"input_tokens": 19, "output_tokens": 4}


@pytest.mark.parametrize(
    ("terminal_event", "expected_status", "raw_delta"),
    [
        (
            {"type": "response.failed", "response": {
                "id": "failed-response", "model": "deepseek-reasoner",
                "error": "provider rejected request",
            }},
            "failed",
            "",
        ),
        (None, "incomplete_stream", "partial-provider-delta"),
    ],
)
def test_chat_write_persists_failed_and_incomplete_outcomes_even_without_ui_text(
    store, monkeypatch, terminal_event, expected_status, raw_delta,
):
    def events(message, instructions, with_tools=True):
        if raw_delta:
            yield {"type": "response.output_text.delta", "delta": raw_delta}
        if terminal_event is not None:
            yield terminal_event

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "直接写", "chapter": 2, "phase": "final",
    })

    assert response.status_code == 200
    rows = _outcomes(store)
    assert len(rows) == 1
    assert rows[0]["status"] == expected_status
    assert rows[0]["output_hash"] == hashlib.sha256(raw_delta.encode("utf-8")).hexdigest()
    if expected_status == "failed":
        assert rows[0]["provider"] == "deepseek"
        assert rows[0]["model"] == "deepseek-reasoner"
        assert rows[0]["provider_request_id"] == "failed-response"
        assert rows[0]["error"] == "provider rejected request"


def test_official_incomplete_stream_exception_is_not_misclassified_as_failed(
    store, monkeypatch,
):
    class IncompleteStreamError(RuntimeError):
        status = "incomplete_stream"

    raw_delta = "official-partial-delta"

    def events(message, instructions, with_tools=True):
        assert with_tools is False
        yield {"type": "response.output_text.delta", "delta": raw_delta}
        raise IncompleteStreamError("official stream ended without done")

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "直接写", "chapter": 4, "phase": "final",
    })

    assert response.status_code == 200
    rows = _outcomes(store)
    assert len(rows) == 1
    assert rows[0]["status"] == "incomplete_stream"
    assert rows[0]["output_hash"] == hashlib.sha256(raw_delta.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("terminal_event", "expected_status", "expected_error"),
    [
        (
            {"event": "response.incomplete", "response": {
                "id": "explicit-incomplete", "model": "gateway-model",
                "usage": {"total_tokens": 12},
                "incomplete_details": {"reason": "max_output_tokens"},
            }},
            "incomplete_stream",
            '{"reason": "max_output_tokens"}',
        ),
        (
            {"type": "response.failed", "response": {
                "id": "explicit-failed", "model": "gateway-model",
                "usage": {"total_tokens": 9}, "error": "provider_failed",
            }},
            "failed",
            "provider_failed",
        ),
        (
            {"type": "response.cancelled", "response": {
                "id": "explicit-cancelled", "model": "gateway-model",
                "usage": {"total_tokens": 6}, "error": "provider_cancelled",
            }},
            "cancelled",
            "provider_cancelled",
        ),
    ],
)
def test_explicit_non_success_terminal_preserves_provider_metadata(
    store, monkeypatch, terminal_event, expected_status, expected_error,
):
    def events(message, instructions, with_tools=True):
        assert with_tools is True
        yield terminal_event

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "查询后给建议", "chapter": 6, "phase": "draft",
    })

    assert response.status_code == 200
    rows = _outcomes(store)
    assert len(rows) == 1
    outcome = rows[0]
    assert outcome["status"] == expected_status
    assert outcome["provider"] == "hermes_gateway"
    assert outcome["model"] == "gateway-model"
    assert outcome["provider_request_id"] == terminal_event["response"]["id"]
    assert outcome["usage"] == terminal_event["response"]["usage"]
    assert outcome["error"] == expected_error


def test_cancelled_stream_persists_cancelled_outcome_with_partial_raw_hash(
    store, monkeypatch,
):
    envelope_trace = {}
    instructions = A._assemble_write_instructions(
        store, chapter=3, focalizer="", phase="final", seed_words=[],
        short_mode=False, with_tools=False, work="main",
        envelope_trace=envelope_trace,
    )
    raw_delta = "provider-partial-before-cancel"

    def events(message, actual_instructions, with_tools=True):
        assert actual_instructions == instructions
        yield {"type": "response.output_text.delta", "delta": raw_delta}
        yield {"type": "response.output_text.delta", "delta": "never-consumed"}

    monkeypatch.setattr(A, "_responses_events", events)
    stream = A._stream_write(
        "写第三章", instructions, with_tools=False,
        on_complete=lambda _text, trace: A._save_write_context_outcome(
            store, envelope_trace, trace,
        ),
    )

    next(stream)
    stream.close()

    rows = _outcomes(store)
    assert len(rows) == 1
    assert rows[0]["status"] == "cancelled"
    assert rows[0]["output_hash"] == hashlib.sha256(raw_delta.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("terminal_event", "expected_status"),
    [
        (
            {"type": "response.completed", "response": {"id": "terminal-completed"}},
            "succeeded",
        ),
        (
            {"type": "response.failed", "response": {
                "id": "terminal-failed", "error": "terminal failure",
            }},
            "failed",
        ),
    ],
)
def test_client_close_after_provider_terminal_does_not_relabel_it_cancelled(
    store, monkeypatch, terminal_event, expected_status,
):
    envelope_trace = {}
    instructions = A._assemble_write_instructions(
        store, chapter=5, focalizer="", phase="final", seed_words=[],
        short_mode=False, with_tools=False, work="main",
        envelope_trace=envelope_trace,
    )

    def events(message, actual_instructions, with_tools=True):
        assert actual_instructions == instructions
        yield {"type": "response.output_text.delta", "delta": "terminal-delta"}
        yield terminal_event

    monkeypatch.setattr(A, "_responses_events", events)
    stream = A._stream_write(
        "写第五章", instructions, with_tools=False,
        on_complete=lambda _text, trace: A._save_write_context_outcome(
            store, envelope_trace, trace,
        ),
    )

    for chunk in stream:
        if '"done": true' in chunk:
            break
    stream.close()

    rows = _outcomes(store)
    assert len(rows) == 1
    assert rows[0]["status"] == expected_status
