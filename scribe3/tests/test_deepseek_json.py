"""Task 5: DeepSeekClient.complete_json RED 测试。"""
import json

import pytest
from pydantic import BaseModel

from scribe3.deepseek_client import CompletionResult, DeepSeekClient, ProviderIdentity


class SampleSchema(BaseModel):
    score: int
    reason: str


def _identity():
    return ProviderIdentity(
        provider="deepseek", api_base="https://api.deepseek.com",
        model="deepseek-chat", official=True, transport="https",
    )


def _result(content: str) -> CompletionResult:
    return CompletionResult(
        content=content, model="deepseek-chat",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        finish_reason="stop", identity=_identity(), response_id="r1",
    )


class FakeTransport:
    def __init__(self, results: list[CompletionResult]):
        self._results = list(results)
        self._index = 0
        self.calls: list[dict] = []

    def post(self, url, **kwargs):
        self.calls.append(kwargs)
        if self._index >= len(self._results):
            raise RuntimeError("no more responses")
        r = self._results[self._index]
        self._index += 1

        class _Resp:
            status_code = 200
            def json(self_inner):
                return {
                    "id": r.response_id,
                    "model": r.model,
                    "choices": [{"message": {"content": r.content}, "finish_reason": "stop"}],
                    "usage": r.usage,
                }
        return _Resp()


class TestCompleteJson:
    def test_returns_parsed_pydantic_model(self):
        client = DeepSeekClient()
        result = _result(json.dumps({"score": 4, "reason": "好"}))
        client._complete_raw = lambda messages, **kw: result
        parsed = client.complete_json(
            [{"role": "user", "content": "评分"}], schema=SampleSchema,
        )
        assert isinstance(parsed, SampleSchema)
        assert parsed.score == 4
        assert parsed.reason == "好"

    def test_empty_content_raises(self):
        client = DeepSeekClient()
        client._complete_raw = lambda messages, **kw: _result("")
        with pytest.raises(ValueError, match="[Ee]mpty|空"):
            client.complete_json(
                [{"role": "user", "content": "评分"}], schema=SampleSchema,
            )

    def test_invalid_json_retries_then_succeeds(self):
        client = DeepSeekClient()
        calls = []
        def fake_raw(messages, **kw):
            calls.append(messages)
            if len(calls) == 1:
                return _result("not json at all")
            return _result(json.dumps({"score": 3, "reason": "修复后"}))
        client._complete_raw = fake_raw
        parsed = client.complete_json(
            [{"role": "user", "content": "评分"}], schema=SampleSchema,
        )
        assert parsed.score == 3
        assert len(calls) == 2

    def test_exceeds_max_repairs_raises(self):
        client = DeepSeekClient()
        client._complete_raw = lambda messages, **kw: _result("永远不是JSON")
        with pytest.raises(ValueError, match="JSON|格式"):
            client.complete_json(
                [{"role": "user", "content": "评分"}], schema=SampleSchema,
            )

    def test_schema_validation_failure_raises(self):
        client = DeepSeekClient()
        client._complete_raw = lambda messages, **kw: _result(
            json.dumps({"wrong_field": True})
        )
        with pytest.raises(ValueError, match="schema|校验|validation"):
            client.complete_json(
                [{"role": "user", "content": "评分"}], schema=SampleSchema,
            )

    def test_uses_json_response_format(self):
        client = DeepSeekClient()
        captured = {}
        def fake_raw(messages, **kw):
            captured.update(kw)
            return _result(json.dumps({"score": 1, "reason": "x"}))
        client._complete_raw = fake_raw
        client.complete_json(
            [{"role": "user", "content": "评分"}], schema=SampleSchema,
        )
        assert captured.get("response_format") == {"type": "json_object"}
