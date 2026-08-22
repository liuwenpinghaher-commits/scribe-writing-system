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
        "provider, model, provider_request_id, transport_provider, transport_request_id, "
        "reasoning_provider, reasoning_model, reasoning_request_id, "
        "usage, output_hash, error "
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


@pytest.mark.parametrize(
    ("changed_key", "source_kind"),
    [
        ("secret_guard", "secret_guard"),
        ("codex", "codex_named"),
        ("craft", "craft"),
        ("avoid", "avoid"),
        ("purpose", "purpose"),
        ("scene_truth", "scene_truth"),
        ("extra", "request_constraint"),
        ("seed", "seed_words"),
    ],
)
def test_dynamic_domain_input_changes_its_registered_manifest_source(
    store, monkeypatch, changed_key, source_kind,
):
    from scribe3 import craft as craft_mod

    holder = {
        "secret_guard": "\n【秘密纪律·甲】",
        "codex": "设定甲",
        "craft": "【工艺甲】",
        "avoid": "\n【避用甲】",
        "purpose": "\n【目的甲】",
        "scene_truth": "场景真相甲",
        "extra": "额外约束甲",
        "seed": "种子甲",
    }
    monkeypatch.setattr(A, "_secret_guard_block", lambda *_: holder["secret_guard"])
    monkeypatch.setattr(A, "_codex_block", lambda *args, **kwargs: holder["codex"])
    monkeypatch.setattr(
        A, "_codex_segments",
        lambda *args, **kwargs: (holder["codex"], "", {}),
    )
    monkeypatch.setattr(A, "_avoid_directive", lambda *_: holder["avoid"])
    monkeypatch.setattr(A, "_purpose_workflow_block", lambda *args, **kwargs: holder["purpose"])
    monkeypatch.setattr(
        craft_mod, "build_craft_block", lambda *args, **kwargs: holder["craft"],
    )
    original_get_chapter = store.get_chapter

    def get_chapter(seq):
        row = dict(original_get_chapter(seq) or {})
        if seq == 9:
            row["scene_truth"] = holder["scene_truth"]
        return row

    monkeypatch.setattr(store, "get_chapter", get_chapter)

    def compile_once():
        trace = {}
        A._assemble_write_instructions(
            store, chapter=9, focalizer="", phase="deduce",
            seed_words=[holder["seed"]], short_mode=False,
            with_tools=False, work="main", envelope_trace=trace,
            extra_instructions=holder["extra"],
        )
        manifest = ContextStore(store).get_manifest(trace["manifest_id"])
        assert manifest is not None
        sources = {
            source.source_kind: source
            for source in manifest.sources
            if source.included and source.block == "supplemental"
        }
        assert source_kind in sources
        assert all(source.revision for source in manifest.sources if source.included)
        return sources[source_kind]

    before = compile_once()
    holder[changed_key] += "·变更"
    after = compile_once()

    assert before.source_id == after.source_id
    assert before.content_digest != after.content_digest
    assert before.revision != after.revision


def test_final_manifest_separates_scene_truth_deductions_and_protocol(store):
    truth = "井底沉着妹妹的骨殖。"
    deductions = [
        {
            "character_id": "role:old-fan",
            "character_name": "老范",
            "prose": "老范只听见井底水声。",
        },
        {
            "character_id": "role:mute-aunt",
            "character_name": "哑姑",
            "prose": "哑姑知道井底埋着骨殖。",
        },
    ]
    store.save_chapter(9, "", title="九")
    store.update_chapter_meta(9, {
        "scene_truth": truth,
        "deductions": deductions,
    })
    trace = {}

    rendered = A._assemble_write_instructions(
        store, chapter=9, focalizer="role:old-fan", phase="final",
        seed_words=[], short_mode=False, with_tools=False, work="main",
        envelope_trace=trace,
    )

    manifest = ContextStore(store).get_manifest(trace["manifest_id"])
    assert manifest is not None
    supplemental = [
        source for source in manifest.sources
        if source.included and source.block == "supplemental"
    ]
    scene_sources = [source for source in supplemental if source.source_kind == "scene_truth"]
    deduction_sources = [source for source in supplemental if source.source_kind == "deduction"]
    protocol_sources = [
        source for source in supplemental if source.source_kind == "deduction_protocol"
    ]
    assert len(scene_sources) == 1
    assert len(deduction_sources) == 2
    assert len(protocol_sources) == 2
    assert len({source.source_id for source in scene_sources + deduction_sources}) == 3
    assert all(source.revision.startswith("content-sha256:") for source in supplemental)
    assert "本章演绎" in rendered and truth in rendered
    assert all(item["prose"] in rendered for item in deductions)


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
    assert outcome["transport_provider"] == "httpx"
    assert outcome["transport_request_id"] == "deepseek-response-1"
    assert outcome["reasoning_provider"] == "deepseek"
    assert outcome["reasoning_model"] == "deepseek-chat"
    assert outcome["reasoning_request_id"] == "deepseek-response-1"
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
    # 官方直连身份现为 qwen(deepseek_client.OFFICIAL_PROVIDER);兼容历史 deepseek 标签
    assert rows[0]["provider"] in ("qwen", "deepseek")
    assert rows[0]["provider_request_id"] == provider_response_id


def test_real_official_sse_cancel_preserves_observed_metadata_and_usage(
    store, monkeypatch,
):
    from scribe3 import deepseek_client as deepseek
    from scribe3 import llm

    response_id = "chatcmpl-seen-before-cancel"
    usage = {"prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8}
    values = {
        "DEEPSEEK_API_KEY": "unit-test-deepseek-key",
        "llm.model": "deepseek-chat",
        "llm.timeout_seconds": 12.5,
        "llm.max_retries": 1,
    }
    monkeypatch.setattr(deepseek.settings, "get_setting", values.__getitem__)
    body = (
        f'data: {{"id":"{response_id}","model":"deepseek-reasoner",'
        '"choices":[{"delta":{"content":"半截正文"}}],'
        '"usage":{"prompt_tokens":7,"completion_tokens":1,"total_tokens":8}}\n\n'
    )

    def handler(_request):
        return httpx.Response(200, text=body)

    binding = A._WriteOutcomeBinding(store)
    instructions = A._assemble_write_instructions(
        store, chapter=16, focalizer="", phase="final", seed_words=[],
        short_mode=False, with_tools=False, work="main",
        envelope_trace=binding.manifest_trace,
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        monkeypatch.setattr(
            llm, "DeepSeekClient", lambda: deepseek.DeepSeekClient(client=transport),
        )
        monkeypatch.setattr(llm, "_tick_daily", lambda: None)
        monkeypatch.setattr(A, "_responses_events", None)
        stream = A._stream_write(
            "直接写", instructions, with_tools=False,
            on_terminal=binding.persist,
        )
        assert "半截正文" in next(stream)
        stream.close()

    outcome = _outcomes(store)[0]
    assert outcome["status"] == "cancelled"
    assert outcome["provider"] in ("qwen", "deepseek")
    assert outcome["provider_request_id"] == response_id
    assert outcome["model"]  # 来自 SSE 或官方默认模型
    assert outcome["usage"] == usage


_TERMINALS_BEFORE_TRANSPORT_ERROR = [
    (
        {"type": "response.completed", "response": {
            "id": "terminal-completed", "model": "gateway-model",
            "usage": {"total_tokens": 3},
        }},
        "succeeded",
    ),
    (
        {"type": "response.failed", "response": {
            "id": "terminal-failed", "model": "gateway-model",
            "usage": {"total_tokens": 4}, "error": "provider_failed",
        }},
        "failed",
    ),
    (
        {"type": "response.incomplete", "response": {
            "id": "terminal-incomplete", "model": "gateway-model",
            "usage": {"total_tokens": 5}, "error": "provider_incomplete",
        }},
        "incomplete_stream",
    ),
    (
        {"type": "response.cancelled", "response": {
            "id": "terminal-cancelled", "model": "gateway-model",
            "usage": {"total_tokens": 6}, "error": "provider_cancelled",
        }},
        "cancelled",
    ),
]


@pytest.mark.parametrize(
    ("terminal_event", "expected_status"),
    _TERMINALS_BEFORE_TRANSPORT_ERROR,
)
def test_stream_provider_terminal_survives_late_transport_error(
    store, monkeypatch, terminal_event, expected_status,
):
    def events(message, instructions, with_tools=True):
        yield {"type": "response.output_text.delta", "delta": "正文"}
        yield terminal_event
        raise RuntimeError("transport-after-terminal")

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "查询后给建议", "chapter": 17, "phase": "draft",
    })

    assert response.status_code == 200
    outcome = _outcomes(store)[0]
    assert outcome["status"] == expected_status
    assert outcome["provider_request_id"] == terminal_event["response"]["id"]
    assert outcome["model"] == "gateway-model"
    assert outcome["usage"] == terminal_event["response"]["usage"]


@pytest.mark.parametrize(
    ("terminal_event", "expected_status"),
    [(event, status if status != "succeeded" else "completed")
     for event, status in _TERMINALS_BEFORE_TRANSPORT_ERROR],
)
def test_collect_provider_terminal_survives_late_transport_error(
    monkeypatch, terminal_event, expected_status,
):
    traces = []

    def events(message, instructions, with_tools=True):
        yield {"type": "response.output_text.delta", "delta": "正文"}
        yield terminal_event
        raise RuntimeError("transport-after-terminal")

    monkeypatch.setattr(A, "_responses_events", events)
    if expected_status == "completed":
        A._collect_write(
            "写", "instructions", with_tools=True,
            on_terminal=lambda trace: traces.append(dict(trace)),
        )
    else:
        with pytest.raises(RuntimeError):
            A._collect_write(
                "写", "instructions", with_tools=True,
                on_terminal=lambda trace: traces.append(dict(trace)),
            )

    assert traces[0]["status"] == expected_status
    assert traces[0]["response_id"] == terminal_event["response"]["id"]
    assert traces[0]["model"] == "gateway-model"
    assert traces[0]["usage"] == terminal_event["response"]["usage"]


@pytest.mark.parametrize("collector", ["stream", "collect"])
def test_first_provider_terminal_freezes_status_and_metadata(store, monkeypatch, collector):
    first = {
        "type": "response.completed",
        "response": {
            "id": "first-terminal", "model": "first-model",
            "usage": {"total_tokens": 11},
        },
        "trace": {
            "provider": "deepseek", "model": "first-model",
            "transport": "httpx", "provider_request_id": "reasoning-first",
        },
    }
    later = {
        "type": "response.failed",
        "response": {
            "id": "later-terminal", "model": "later-model",
            "usage": {"total_tokens": 99}, "error": "must-not-win",
        },
        "trace": {
            "provider": "other-provider", "model": "later-model",
            "transport": "other-transport", "provider_request_id": "reasoning-later",
        },
    }

    def events(*_args, **_kwargs):
        yield {"type": "response.output_text.delta", "delta": "正文"}
        yield first
        yield later
        raise RuntimeError("late-transport-error")

    monkeypatch.setattr(A, "_responses_events", events)
    if collector == "stream":
        response = _client(store).post("/chat/write", json={
            "msg": "查询后给建议", "chapter": 18, "phase": "draft",
        })
        assert response.status_code == 200
        outcome = _outcomes(store)[0]
        assert outcome["status"] == "succeeded"
        assert outcome["provider_request_id"] == "first-terminal"
        assert outcome["model"] == "first-model"
        assert outcome["usage"] == {"total_tokens": 11}
    else:
        traces = []
        A._collect_write(
            "写", "instructions", with_tools=True,
            on_terminal=lambda trace: traces.append(dict(trace)),
        )
        assert traces[0]["status"] == "completed"
        assert traces[0]["response_id"] == "first-terminal"
        assert traces[0]["model"] == "first-model"
        assert traces[0]["usage"] == {"total_tokens": 11}


def test_hermes_outcome_separates_gateway_transport_from_reasoning_provider(
    store, monkeypatch,
):
    def events(*_args, **_kwargs):
        yield {
            "type": "response.completed",
            "response": {
                "id": "gateway-response", "model": "reasoning-model",
                "usage": {"total_tokens": 8},
            },
            "trace": {
                "provider": "reasoning-provider", "model": "reasoning-model",
                "provider_request_id": "reasoning-response", "transport": "provider-http",
            },
        }

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "查询后给建议", "chapter": 19, "phase": "draft",
    })

    assert response.status_code == 200
    outcome = _outcomes(store)[0]
    assert outcome["provider"] == "hermes_gateway"  # 兼容字段
    assert outcome["transport_provider"] == "hermes_gateway"
    assert outcome["transport_request_id"] == "gateway-response"
    assert outcome["reasoning_provider"] == "reasoning-provider"
    assert outcome["reasoning_model"] == "reasoning-model"
    assert outcome["reasoning_request_id"] == "reasoning-response"


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
    assert rows[0]["transport_provider"] == "hermes_gateway"
    assert rows[0]["transport_request_id"] == "hermes-response-1"
    assert rows[0]["reasoning_provider"] is None
    assert rows[0]["reasoning_request_id"] is None
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
        assert rows[0]["provider"] in ("qwen", "deepseek")
        assert rows[0]["model"]
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


def test_incomplete_exception_metadata_reaches_context_outcome(store, monkeypatch):
    from scribe3.deepseek_client import ProviderIdentity

    class IncompleteStreamError(RuntimeError):
        status = "incomplete_stream"
        response_id = "chatcmpl-partial-outcome"
        usage = {"prompt_tokens": 13, "completion_tokens": 2, "total_tokens": 15}
        model = "deepseek-reasoner"
        identity = ProviderIdentity(
            provider="deepseek",
            api_base="https://api.deepseek.com",
            model=model,
            official=True,
            transport="httpx",
        )

    def events(message, instructions, with_tools=True):
        yield {"type": "response.output_text.delta", "delta": "半截供应商正文"}
        raise IncompleteStreamError("official stream ended without done")

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).post("/chat/write", json={
        "msg": "直接写", "chapter": 15, "phase": "final",
    })

    assert response.status_code == 200
    outcome = _outcomes(store)[0]
    assert outcome["status"] == "incomplete_stream"
    assert outcome["provider"] == "deepseek"
    assert outcome["model"] == "deepseek-reasoner"
    assert outcome["provider_request_id"] == "chatcmpl-partial-outcome"
    assert outcome["usage"] == IncompleteStreamError.usage


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


def test_get_chat_write_persists_outcome_bound_to_actual_provider_input(
    store, monkeypatch,
):
    captured = {}

    def events(message, instructions, with_tools=True):
        captured["instructions"] = instructions
        yield {"type": "response.output_text.delta", "delta": "GET 端点回复"}
        yield {
            "type": "response.completed",
            "response": {"id": "get-write-1", "model": "deepseek-chat", "usage": {}},
        }

    monkeypatch.setattr(A, "_responses_events", events)
    response = _client(store).get("/chat/write", params={
        "msg": "直接写", "chapter": 11, "phase": "final",
    })

    assert response.status_code == 200
    outcome = _outcomes(store)[0]
    manifest = ContextStore(store).get_manifest(outcome["manifest_id"])
    assert manifest is not None
    assert outcome["provider_request_id"] == "get-write-1"
    assert manifest.actual_input_hash == hashlib.sha256(
        captured["instructions"].encode("utf-8")
    ).hexdigest()


def test_repair_attempts_compile_constraints_and_persist_independent_outcomes(
    store, monkeypatch, tmp_path,
):
    from scribe3 import loop as loop_mod

    A.set_store(store)
    captured: list[str] = []

    def events(message, instructions, with_tools=True):
        captured.append(instructions)
        response_id = f"repair-{len(captured)}"
        yield {
            "type": "response.output_text.delta",
            "delta": "⟦PROPOSAL scope=chapter⟧本轮修复稿⟦/PROPOSAL⟧",
        }
        yield {
            "type": "response.completed",
            "response": {"id": response_id, "model": "deepseek-chat", "usage": {}},
        }

    def run_loop(**kwargs):
        kwargs["generate"](0, "【约束甲】禁止复读")
        kwargs["generate"](1, "【约束乙】隐藏秘密")
        return {"verdict": "needs_human", "rounds": []}

    monkeypatch.setattr(A, "_responses_events", events)
    monkeypatch.setattr(loop_mod, "run_chapter_loop", run_loop)
    monkeypatch.setattr(A, "_loop_journal_path", lambda *_: tmp_path / "loop.json")

    result = A.loop_chapter(A.LoopChapterReq(chapter=12, phase="final"), work="main")

    assert result["verdict"] == "needs_human"
    assert "【约束甲】禁止复读" in captured[0]
    assert "【约束乙】隐藏秘密" in captured[1]
    rows = _outcomes(store)
    assert len(rows) == 2
    assert len({row["manifest_id"] for row in rows}) == 2
    assert {row["provider_request_id"] for row in rows} == {"repair-1", "repair-2"}
    assert {row["actual_input_hash"] for row in rows} == {
        hashlib.sha256(instructions.encode("utf-8")).hexdigest()
        for instructions in captured
    }


def test_selection_strategies_compile_and_persist_independent_outcomes(
    store, monkeypatch, tmp_path,
):
    from scribe3 import selection as selection_mod

    A.set_store(store)
    store.save_chapter(13, "选择环原稿")
    captured: list[str] = []

    def events(message, instructions, with_tools=True):
        captured.append(instructions)
        response_id = f"selection-{len(captured)}"
        yield {
            "type": "response.output_text.delta",
            "delta": "⟦PROPOSAL scope=chapter⟧本轮候选稿⟦/PROPOSAL⟧",
        }
        yield {
            "type": "response.completed",
            "response": {"id": response_id, "model": "deepseek-chat", "usage": {}},
        }

    def run_selection(**kwargs):
        kwargs["generate"]({"key": "alpha", "directive": "策略甲：冷开场"})
        kwargs["generate"]({"key": "beta", "directive": "策略乙：慢炖"})
        return {"verdict": "awaiting_human", "candidates": []}

    monkeypatch.setattr(A, "_responses_events", events)
    monkeypatch.setattr(selection_mod, "run_selection", run_selection)
    monkeypatch.setattr(A, "_loop_journal_path", lambda *_: tmp_path / "loop.json")

    result = A.select_chapter(
        A.SelectChapterReq(chapter=13, force=True), work="main",
    )

    assert result["verdict"] == "awaiting_human"
    assert "策略甲：冷开场" in captured[0]
    assert "策略乙：慢炖" in captured[1]
    rows = _outcomes(store)
    assert len(rows) == 2
    assert len({row["manifest_id"] for row in rows}) == 2
    assert {row["provider_request_id"] for row in rows} == {
        "selection-1", "selection-2",
    }
    assert {row["actual_input_hash"] for row in rows} == {
        hashlib.sha256(instructions.encode("utf-8")).hexdigest()
        for instructions in captured
    }


def test_pilot_uses_event_collector_and_persists_outcome(
    store, monkeypatch,
):
    captured = {}

    def events(message, instructions, with_tools=True, max_tokens=None):
        captured.update(
            message=message,
            instructions=instructions,
            with_tools=with_tools,
            max_tokens=max_tokens,
        )
        yield {"type": "response.output_text.delta", "delta": "  Pilot 纯文本  "}
        yield {
            "type": "response.completed",
            "response": {"id": "pilot-1", "model": "deepseek-chat", "usage": {}},
        }

    monkeypatch.setattr(A, "_responses_events", events)

    result = A._pilot_llm_gen(
        store, "main", 14, "plan", "规划下一章", max_tokens=777,
    )

    assert result == "Pilot 纯文本"
    assert captured["with_tools"] is False
    assert captured["max_tokens"] == 777
    outcome = _outcomes(store)[0]
    assert outcome["provider_request_id"] == "pilot-1"
    assert outcome["actual_input_hash"] == hashlib.sha256(
        captured["instructions"].encode("utf-8")
    ).hexdigest()


def test_hard_outcome_failure_propagates_before_best_effort_chat_callback(monkeypatch):
    chat_callbacks = []

    def events(message, instructions, with_tools=True):
        yield {"type": "response.output_text.delta", "delta": "正文"}
        yield {"type": "response.completed", "response": {"id": "terminal-1"}}

    def fail_outcome(_trace):
        raise RuntimeError("outcome-save-failed")

    monkeypatch.setattr(A, "_responses_events", events)

    with pytest.raises(RuntimeError, match="outcome-save-failed"):
        list(A._stream_write(
            "写", "instructions", with_tools=False,
            on_terminal=fail_outcome,
            on_complete=lambda *_args: chat_callbacks.append(True),
        ))

    assert chat_callbacks == []
