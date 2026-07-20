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


def test_registered_default_model_is_deepseek_chat():
    model_setting = next(item for item in deepseek.settings.REGISTRY if item.key == "llm.model")
    assert model_setting.default == "deepseek-chat"


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
        "url": "https://api.deepseek.com/chat/completions",
        "authorized": True,
        "body": {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "写一句话"}],
            "stream": False,
        },
    }
    assert result.content == "完成文本"
    assert result.model == "deepseek-chat"
    assert result.finish_reason == "stop"
    assert result.identity == deepseek.ProviderIdentity(
        provider="deepseek",
        api_base="https://api.deepseek.com",
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
        "max_tokens": 321,
        "temperature": 0.4,
        "thinking": {"type": "enabled"},
    }
    assert result.identity.model == "deepseek-reasoner"


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
    assert FAKE_API_KEY not in repr(raised.value)


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
            'data: {"model":"deepseek-chat","choices":[{"delta":{"content":"好"}}]}',
            'data: {"model":"deepseek-chat","choices":[],"usage":{"prompt_tokens":4,"completion_tokens":2,"total_tokens":6,"prompt_cache_hit_tokens":3,"prompt_cache_miss_tokens":1}}',
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
        provider="deepseek",
        api_base="https://api.deepseek.com",
        model="deepseek-chat",
        official=True,
        transport="httpx",
    )
    assert observed == {
        "url": "https://api.deepseek.com/chat/completions",
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
    ]
    assert FAKE_API_KEY not in repr(events)
    assert "tools" not in observed["body"]


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
    }
