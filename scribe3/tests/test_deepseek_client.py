import json
from dataclasses import fields

import httpx
import pytest

from scribe3 import deepseek_client as deepseek


FAKE_API_KEY = "unit-test-deepseek-key"


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    values = {
        "DEEPSEEK_API_KEY": FAKE_API_KEY,
        "llm.model": "deepseek-chat",
        "llm.timeout_seconds": 12.5,
        "llm.max_retries": 2,
    }
    monkeypatch.setattr(deepseek.settings, "get_setting", values.__getitem__)
    return values


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _safe_exception(error, secret=FAKE_API_KEY):
    assert isinstance(error, deepseek.DeepSeekError)
    assert secret not in str(error)
    assert secret not in repr(error)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert {"request", "response", "header", "headers", "cause"}.isdisjoint(vars(error))


def _successful_response(operation):
    if operation == "complete":
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "recovered"}}], "usage": {}},
        )
    return httpx.Response(
        200,
        text=(
            'data: {"model":"deepseek-chat","choices":[{"delta":{"content":"恢复"}}]}\n\n'
            "data: [DONE]\n\n"
        ),
    )


def _invoke(client, operation):
    messages = [{"role": "user", "content": "hello"}]
    if operation == "complete":
        return client.complete(messages)
    return list(client.stream(messages))


def test_registered_default_model_is_qwen38_max_preview():
    model_setting = next(item for item in deepseek.settings.REGISTRY if item.key == "llm.model")
    assert model_setting.default == "deepseek-v4-pro-0813"


def test_token_plan_route_exposes_literal_qwen_provider_contract():
    identity = deepseek.DeepSeekClient(client=None).identity("qwen3.8-max-preview")

    assert identity == deepseek.ProviderIdentity(
        provider="qwen",
        api_base="https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        model="qwen3.8-max-preview",
        official=True,
        transport="httpx",
    )


@pytest.mark.parametrize(
    ("model", "expected_model"),
    [(None, "deepseek-chat"), ("deepseek-reasoner", "deepseek-reasoner")],
    ids=["default-model", "explicit-model"],
)
def test_public_identity_resolves_model_without_key_or_transport(
    monkeypatch,
    model,
    expected_model,
):
    class ForbiddenTransport:
        def __getattribute__(self, name):
            raise AssertionError(f"identity touched transport attribute: {name}")

    monkeypatch.setattr(
        deepseek.DeepSeekClient,
        "_api_key",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("identity read API key")
        ),
    )
    client = deepseek.DeepSeekClient(client=ForbiddenTransport())

    assert client.identity(model) == deepseek.ProviderIdentity(
        provider="qwen",
        api_base=deepseek.OFFICIAL_API_BASE,
        model=expected_model,
        official=True,
        transport="httpx",
    )


def test_public_identity_preserves_explicit_empty_model_without_fallback(monkeypatch):
    class ForbiddenTransport:
        def __getattribute__(self, name):
            raise AssertionError(f"identity touched transport attribute: {name}")

    forbidden = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("identity used a forbidden fallback")
    )
    monkeypatch.setattr(deepseek.settings, "get_setting", forbidden)
    monkeypatch.setattr(deepseek.DeepSeekClient, "_api_key", forbidden)
    client = deepseek.DeepSeekClient(client=ForbiddenTransport())

    identity = client.identity("")
    assert identity.model == ""


def test_complete_uses_only_official_endpoint_and_preserves_usage(_settings):
    observed = {}

    def handler(request):
        body = json.loads(request.content)
        observed.update(
            url=str(request.url),
            authorized=request.headers.get("Authorization") == f"Bearer {FAKE_API_KEY}",
            body=body,
        )
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-complete-1",
                "model": "deepseek-chat",
                "choices": [
                    {"message": {"content": "完成文本"}, "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 3,
                    "total_tokens": 15,
                    "prompt_cache_hit_tokens": 7,
                    "prompt_cache_miss_tokens": 5,
                },
            },
        )

    with _client(handler) as transport:
        result = deepseek.DeepSeekClient(client=transport).complete(
            [{"role": "user", "content": "写一句话"}]
        )

    assert observed == {
        "url": deepseek._CHAT_COMPLETIONS_URL,
        "authorized": True,
        "body": {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "写一句话"}],
            "stream": False,
        },
    }
    assert result.content == "完成文本"
    assert result.response_id == "chatcmpl-complete-1"
    assert result.model == "deepseek-chat"
    assert result.finish_reason == "stop"
    assert result.identity == deepseek.ProviderIdentity(
        provider="qwen",
        api_base=deepseek.OFFICIAL_API_BASE,
        model="deepseek-chat",
        official=True,
        transport="httpx",
    )
    assert result.usage == {
        "prompt_tokens": 12,
        "completion_tokens": 3,
        "total_tokens": 15,
        "prompt_cache_hit_tokens": 7,
        "prompt_cache_miss_tokens": 5,
    }
    assert FAKE_API_KEY not in repr(result)
    assert "tools" not in observed["body"]


def test_complete_forwards_supported_optional_parameters():
    observed_body = {}

    def handler(request):
        observed_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "length"}],
                "usage": {},
            },
        )

    with _client(handler) as transport:
        result = deepseek.DeepSeekClient(client=transport).complete(
            [{"role": "user", "content": "hello"}],
            model="deepseek-reasoner",
            max_tokens=321,
            temperature=0.4,
            thinking="enabled",
        )

    assert observed_body == {
        "model": "deepseek-reasoner",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "max_tokens": 321 + 4096,
        "temperature": 0.4,
        "thinking": {"type": "enabled"},
        "enable_thinking": True,
    }
    assert result.identity.model == "deepseek-reasoner"


def test_complete_disabled_thinking_sends_enable_thinking_false_for_tokenplan():
    observed_body = {}

    def handler(request):
        observed_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]},
        )

    with _client(handler) as transport:
        deepseek.DeepSeekClient(client=transport).complete(
            [{"role": "user", "content": "hello"}],
            thinking="disabled",
        )

    assert observed_body["thinking"] == {"type": "disabled"}
    assert observed_body["enable_thinking"] is False


def test_complete_retries_when_thinking_fills_max_tokens():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body.get("max_tokens"))
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [{
                        "finish_reason": "length",
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "reasoning_content": "x" * 100,
                        },
                    }],
                },
            )
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"content": "落库"}}]},
        )

    with _client(handler) as transport:
        result = deepseek.DeepSeekClient(client=transport).complete(
            [{"role": "user", "content": "写"}],
            max_tokens=256,
            thinking="disabled",
            retry_count=1,
        )

    assert result.content == "落库"
    assert calls == [256, 4352]


@pytest.mark.parametrize("operation", ["complete", "stream"])
def test_call_timeout_overrides_setting_for_each_outbound_path(operation):
    observed_timeout = None

    def handler(request):
        nonlocal observed_timeout
        observed_timeout = request.extensions.get("timeout")
        return _successful_response(operation)

    with _client(handler) as transport:
        client = deepseek.DeepSeekClient(client=transport)
        messages = [{"role": "user", "content": "hello"}]
        if operation == "complete":
            client.complete(messages, timeout_seconds=7.25)
        else:
            list(client.stream(messages, timeout_seconds=7.25))

    assert observed_timeout == {
        "connect": 7.25,
        "read": 7.25,
        "write": 7.25,
        "pool": 7.25,
    }


@pytest.mark.parametrize("operation", ["complete", "stream"])
def test_call_retry_count_zero_disables_retries(operation):
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": {"message": "busy"}})

    with _client(handler) as transport:
        client = deepseek.DeepSeekClient(client=transport)
        messages = [{"role": "user", "content": "hello"}]
        with pytest.raises(deepseek.DeepSeekHTTPError):
            if operation == "complete":
                client.complete(messages, retry_count=0)
            else:
                list(client.stream(messages, retry_count=0))

    assert calls == 1


def test_missing_key_fails_before_transport(_settings):
    _settings["DEEPSEEK_API_KEY"] = ""
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekConfigurationError) as raised:
            deepseek.DeepSeekClient(client=transport).complete(
                [{"role": "user", "content": "hello"}]
            )

    assert calls == 0
    assert "DEEPSEEK_API_KEY" in str(raised.value)
    assert "Qwen" in str(raised.value)
    assert "DeepSeek 官方接口" not in str(raised.value)
    assert FAKE_API_KEY not in repr(raised.value)


@pytest.mark.parametrize("operation", ["complete", "stream"])
@pytest.mark.parametrize(
    "invalid_key",
    ["测试-key", "unit-test\nkey"],
    ids=["non-ascii", "control-character"],
)
def test_invalid_header_key_fails_safely_before_transport(
    _settings,
    operation,
    invalid_key,
):
    _settings["DEEPSEEK_API_KEY"] = invalid_key
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return _successful_response(operation)

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekConfigurationError) as raised:
            _invoke(deepseek.DeepSeekClient(client=transport), operation)

    assert calls == 0
    assert raised.value.status == "invalid_api_key"
    _safe_exception(raised.value, invalid_key)


def test_4xx_is_not_retried_and_exception_never_contains_key():
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": {"message": "unauthorized"}})

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekHTTPError) as raised:
            deepseek.DeepSeekClient(client=transport).complete(
                [{"role": "user", "content": "hello"}]
            )

    assert calls == 1
    assert raised.value.status_code == 401
    assert raised.value.retryable is False
    assert FAKE_API_KEY not in str(raised.value)
    assert FAKE_API_KEY not in repr(raised.value)
    assert raised.value.__cause__ is None


def test_5xx_retries_according_to_setting_then_succeeds():
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, json={"error": {"message": "busy"}})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "recovered"}}], "usage": {}},
        )

    with _client(handler) as transport:
        result = deepseek.DeepSeekClient(client=transport).complete(
            [{"role": "user", "content": "hello"}]
        )

    assert calls == 3
    assert result.content == "recovered"


def test_connection_errors_retry_according_to_setting_then_succeed():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ConnectError("test connection failure", request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "connected"}}], "usage": {}},
        )

    with _client(handler) as transport:
        result = deepseek.DeepSeekClient(client=transport).complete(
            [{"role": "user", "content": "hello"}]
        )

    assert calls == 3
    assert result.content == "connected"


@pytest.mark.parametrize("operation", ["complete", "stream"])
def test_proxy_error_is_safely_retried_for_both_outbound_paths(operation):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ProxyError(
                f"proxy rejected {FAKE_API_KEY}",
                request=request,
            )
        return _successful_response(operation)

    with _client(handler) as transport:
        result = _invoke(deepseek.DeepSeekClient(client=transport), operation)

    assert calls == 3
    if operation == "complete":
        assert result.content == "recovered"
    else:
        assert [event["delta"] for event in result if event["type"] == "delta"] == ["恢复"]


@pytest.mark.parametrize("operation", ["complete", "stream"])
def test_decoding_error_is_sanitized_without_retry(operation):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.DecodingError(
            f"cannot decode {FAKE_API_KEY}",
            request=request,
        )

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekTransportError) as raised:
            _invoke(deepseek.DeepSeekClient(client=transport), operation)

    assert calls == 1
    assert raised.value.retryable is False
    _safe_exception(raised.value)


def test_complete_keeps_only_official_content_and_usage():
    def handler(_request):
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-think-1",
                "model": "qwen3.8-max-preview",
                "choices": [{
                    "message": {
                        "content": "<think>盘动机</think>沈拾灯按册。",
                        "reasoning_content": "不该出现的推理",
                    },
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 8,
                    "completion_tokens": 50,
                    "total_tokens": 58,
                    "completion_tokens_details": {"reasoning_tokens": 40},
                },
            },
        )

    with _client(handler) as transport:
        result = deepseek.DeepSeekClient(client=transport).complete(
            [{"role": "user", "content": "写"}]
        )
    assert result.content == "沈拾灯按册。"
    assert result.usage["completion_tokens"] == 10
    assert result.usage["total_tokens"] == 18


@pytest.mark.parametrize(
    "payload",
    [
        {"choices": [], "usage": {}},
        {"choices": [{"message": {"content": ""}}], "usage": {}},
        {"choices": [{"message": {"content": "   "}}], "usage": {}},
    ],
    ids=["empty-choices", "empty-content", "blank-content"],
)
def test_invalid_completion_shape_fails_loud(payload):
    def handler(_request):
        return httpx.Response(200, json=payload)

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekResponseError) as raised:
            deepseek.DeepSeekClient(client=transport).complete(
                [{"role": "user", "content": "hello"}]
            )

    assert raised.value.status == "invalid_response"
    assert FAKE_API_KEY not in repr(raised.value)


def test_stream_parses_deltas_and_final_usage():
    observed = {}
    stream_body = "\n".join(
        [
            'data: {"model":"deepseek-chat","choices":[{"delta":{"content":"你"}}]}',
            "",
            'data: {"model":"deepseek-chat","choices":[{"delta":{"content":"好"}}]}',
            "",
            'data: {"model":"deepseek-chat","choices":[],"usage":{"prompt_tokens":4,"completion_tokens":2,"total_tokens":6,"prompt_cache_hit_tokens":3,"prompt_cache_miss_tokens":1}}',
            "",
            "data: [DONE]",
            "",
        ]
    )

    def handler(request):
        body = json.loads(request.content)
        observed.update(
            url=str(request.url),
            authorized=request.headers.get("Authorization") == f"Bearer {FAKE_API_KEY}",
            body=body,
        )
        return httpx.Response(200, text=stream_body)

    with _client(handler) as transport:
        events = list(
            deepseek.DeepSeekClient(client=transport).stream(
                [{"role": "user", "content": "问候"}]
            )
        )

    identity = deepseek.ProviderIdentity(
        provider="qwen",
        api_base=deepseek.OFFICIAL_API_BASE,
        model="deepseek-chat",
        official=True,
        transport="httpx",
    )
    assert observed == {
        "url": deepseek._CHAT_COMPLETIONS_URL,
        "authorized": True,
        "body": {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "问候"}],
            "stream": True,
            "stream_options": {"include_usage": True},
            },
        }
    assert events == [
        {"type": "delta", "delta": "你", "model": "deepseek-chat", "identity": identity},
        {"type": "delta", "delta": "好", "model": "deepseek-chat", "identity": identity},
        {
            "type": "usage",
            "usage": {
                "prompt_tokens": 4,
                "completion_tokens": 2,
                "total_tokens": 6,
                "prompt_cache_hit_tokens": 3,
                "prompt_cache_miss_tokens": 1,
            },
            "model": "deepseek-chat",
            "identity": identity,
        },
        {"type": "done", "model": "deepseek-chat", "identity": identity},
    ]
    assert FAKE_API_KEY not in repr(events)
    assert "tools" not in observed["body"]


def test_stream_done_preserves_real_provider_response_id_from_sse_payload():
    provider_response_id = "chatcmpl-provider-123"
    stream_body = "\n".join([
        f'data: {{"id":"{provider_response_id}","model":"deepseek-chat",'
        '"choices":[{"delta":{"content":"完成"}}]}',
        "",
        f'data: {{"id":"{provider_response_id}","model":"deepseek-chat",'
        '"choices":[],"usage":{"total_tokens":3}}',
        "",
        "data: [DONE]",
        "",
    ])

    def handler(_request):
        return httpx.Response(200, text=stream_body)

    with _client(handler) as transport:
        events = list(deepseek.DeepSeekClient(client=transport).stream(
            [{"role": "user", "content": "写"}],
        ))

    assert events[-1]["type"] == "done"
    assert events[-1]["response_id"] == provider_response_id


def test_stream_delta_exposes_observed_metadata_and_usage_before_cancel():
    """同一 SSE 帧的安全 metadata/usage 必须先于可取消 delta 向上游可见。"""
    response_id = "chatcmpl-seen-before-cancel"
    body = (
        f'data: {{"id":"{response_id}","model":"deepseek-reasoner",'
        '"choices":[{"delta":{"content":"半截正文"}}],'
        '"usage":{"prompt_tokens":7,"completion_tokens":1,"total_tokens":8}}\n\n'
    )

    def handler(_request):
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        stream = deepseek.DeepSeekClient(client=transport).stream(
            [{"role": "user", "content": "写"}],
        )
        usage = next(stream)
        delta = next(stream)
        stream.close()

    assert usage == {
        "type": "usage",
        "usage": {"prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8},
        "model": "deepseek-reasoner",
        "identity": delta["identity"],
    }
    assert delta["delta"] == "半截正文"
    assert delta["response_id"] == response_id
    assert delta["model"] == "deepseek-reasoner"


def test_stream_forwards_max_tokens_to_official_request():
    observed = {}

    def handler(request):
        observed.update(json.loads(request.content))
        return httpx.Response(
            200,
            text=(
                'data: {"model":"deepseek-chat",'
                '"choices":[{"delta":{"content":"完成"}}]}\n\n'
                "data: [DONE]\n\n"
            ),
        )

    with _client(handler) as transport:
        list(deepseek.DeepSeekClient(client=transport).stream(
            [{"role": "user", "content": "写"}], max_tokens=777,
        ))

    assert observed["max_tokens"] == 777 + 4096


def test_stream_omits_tokenplan_thinking_by_default_for_visible_prose_deltas():
    observed = {}

    def handler(request):
        observed.update(json.loads(request.content))
        return httpx.Response(
            200,
            text='data: {"model":"qwen3.8-max-preview","choices":[{"delta":{"content":"正文"}}]}\n\ndata: [DONE]\n\n',
        )

    with _client(handler) as transport:
        list(deepseek.DeepSeekClient(client=transport).stream(
            [{"role": "user", "content": "写一段正文"}],
        ))

    assert "thinking" not in observed


def test_stream_200_empty_sse_fails_loud_without_retry():
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="")

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekResponseError) as raised:
            list(
                deepseek.DeepSeekClient(client=transport).stream(
                    [{"role": "user", "content": "hello"}]
                )
            )

    assert calls == 1
    assert raised.value.status == "incomplete_stream"
    _safe_exception(raised.value)


def test_stream_error_payload_fails_loud_and_is_sanitized():
    body = (
        f'data: {{"error":{{"message":"provider leaked {FAKE_API_KEY}"}}}}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(_request):
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekResponseError) as raised:
            list(
                deepseek.DeepSeekClient(client=transport).stream(
                    [{"role": "user", "content": "hello"}]
                )
            )

    assert raised.value.status == "provider_error"
    _safe_exception(raised.value)


def test_provider_error_payload_preserves_safe_metadata_from_same_event():
    response_id = "chatcmpl-provider-error-1"
    body = (
        f'data: {{"id":"{response_id}","model":"deepseek-reasoner",'
        '"usage":{"prompt_tokens":5,"completion_tokens":1,"total_tokens":6},'
        '"error":{"message":"provider rejected"}}\n\n'
    )

    def handler(_request):
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekResponseError) as raised:
            list(deepseek.DeepSeekClient(client=transport).stream(
                [{"role": "user", "content": "写"}],
            ))

    assert raised.value.status == "provider_error"
    assert raised.value.response_id == response_id
    assert raised.value.model == "deepseek-reasoner"
    assert raised.value.usage == {
        "prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6,
    }
    _safe_exception(raised.value)


def test_stream_eof_after_first_delta_fails_without_retry():
    calls = 0
    body = 'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        events = deepseek.DeepSeekClient(client=transport).stream(
            [{"role": "user", "content": "hello"}]
        )
        first = next(events)
        with pytest.raises(deepseek.DeepSeekResponseError) as raised:
            next(events)

    assert first["delta"] == "partial"
    assert calls == 1
    assert raised.value.status == "incomplete_stream"
    _safe_exception(raised.value)


def test_incomplete_stream_error_preserves_observed_provider_metadata():
    response_id = "chatcmpl-partial-456"
    body = "\n".join([
        f'data: {{"id":"{response_id}","model":"deepseek-reasoner",'
        '"choices":[{"delta":{"content":"半截正文"}}]}',
        "",
        f'data: {{"id":"{response_id}","model":"deepseek-reasoner",'
        '"choices":[],"usage":{"prompt_tokens":8,"completion_tokens":2,'
        '"total_tokens":10}}',
        "",
    ])

    def handler(_request):
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        with pytest.raises(deepseek.DeepSeekResponseError) as raised:
            list(deepseek.DeepSeekClient(client=transport).stream(
                [{"role": "user", "content": "写"}],
            ))

    assert raised.value.status == "incomplete_stream"
    assert raised.value.response_id == response_id
    assert raised.value.model == "deepseek-reasoner"
    assert raised.value.usage == {
        "prompt_tokens": 8,
        "completion_tokens": 2,
        "total_tokens": 10,
    }
    _safe_exception(raised.value)


def test_stream_parses_multiline_data_as_one_sse_frame():
    body = "\n".join(
        [
            'data: {"model":"deepseek-chat",',
            'data: "choices":[{"delta":{"content":"多行"}}]}',
            "",
            'data: {"model":"deepseek-chat","choices":[],',
            'data: "usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}',
            "",
            "data: [DONE]",
            "",
        ]
    )

    def handler(_request):
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        events = list(
            deepseek.DeepSeekClient(client=transport).stream(
                [{"role": "user", "content": "hello"}]
            )
        )

    assert [event["type"] for event in events] == ["delta", "usage", "done"]
    assert events[0]["delta"] == "多行"
    assert events[1]["usage"] == {
        "prompt_tokens": 2,
        "completion_tokens": 1,
        "total_tokens": 3,
    }


def test_stream_ignores_one_utf8_bom_on_first_line():
    body = (
        '\ufeffdata: {"choices":[{"delta":{"content":"含BOM"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(_request):
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        events = list(
            deepseek.DeepSeekClient(client=transport).stream(
                [{"role": "user", "content": "hello"}]
            )
        )

    assert [event["delta"] for event in events if event["type"] == "delta"] == ["含BOM"]


def test_stream_done_without_usage_emits_explicit_done_event():
    body = (
        'data: {"model":"deepseek-chat","choices":[{"delta":{"content":"完成"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(_request):
        return httpx.Response(200, text=body)

    with _client(handler) as transport:
        events = list(
            deepseek.DeepSeekClient(client=transport).stream(
                [{"role": "user", "content": "hello"}]
            )
        )

    assert [event["type"] for event in events] == ["delta", "done"]
    assert events[-1] == {
        "type": "done",
        "model": "deepseek-chat",
        "identity": deepseek.ProviderIdentity(
            provider="qwen",
            api_base=deepseek.OFFICIAL_API_BASE,
            model="deepseek-chat",
            official=True,
            transport="httpx",
        ),
    }


def test_public_dataclasses_have_no_secret_or_header_fields():
    assert {field.name for field in fields(deepseek.ProviderIdentity)} == {
        "provider",
        "api_base",
        "model",
        "official",
        "transport",
    }
    assert {field.name for field in fields(deepseek.CompletionResult)} == {
        "content",
        "model",
        "usage",
        "finish_reason",
        "identity",
        "response_id",
    }
