"""Task 5: DeepSeekClient.complete_json RED 测试。"""
import json
import threading
import time

import pytest
from pydantic import BaseModel

from scribe3.deepseek_client import (
    CompletionResult, DeepSeekClient, DeepSeekTransportError, ProviderIdentity,
)


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
    def test_hard_deadline_closes_a_stalled_provider_socket(self, monkeypatch):
        """质量评价不能在上游持续回传/卡读时无限占住作者的快照请求。"""
        class BlockingClient:
            def __init__(self):
                self.closed = threading.Event()

            def post(self, *_args, **_kwargs):
                if not self.closed.wait(1):
                    raise AssertionError("硬时限没有关闭阻塞中的 HTTP 客户端")
                raise __import__("httpx").ReadTimeout("hard deadline elapsed")

            def close(self):
                self.closed.set()

        transport = BlockingClient()
        client = DeepSeekClient(client=transport)
        monkeypatch.setattr(client, "_api_key", lambda _identity: "test-key")
        started = time.monotonic()

        with pytest.raises(DeepSeekTransportError):
            client.complete(
                [{"role": "user", "content": "质量判断"}],
                timeout_seconds=0.02, retry_count=0, hard_deadline=True,
            )

        assert transport.closed.is_set()
        assert time.monotonic() - started < 0.5

    def test_hard_deadline_returns_when_transport_ignores_cross_thread_close(self, monkeypatch):
        """总时限不能依赖 transport 是否响应另一个线程发出的 close。"""
        class CloseIgnoringClient:
            def post(self, *_args, **_kwargs):
                time.sleep(0.15)
                raise __import__("httpx").ReadTimeout("late transport failure")

            def close(self):
                pass

        client = DeepSeekClient(client=CloseIgnoringClient())
        monkeypatch.setattr(client, "_api_key", lambda _identity: "test-key")
        started = time.monotonic()

        with pytest.raises(DeepSeekTransportError):
            client.complete(
                [{"role": "user", "content": "质量判断"}],
                timeout_seconds=0.02, retry_count=0, hard_deadline=True,
            )

        assert time.monotonic() - started < 0.10

    def test_hard_deadline_does_not_wait_for_blocking_transport_close(self, monkeypatch):
        """真实 socket 关闭若阻塞，质量作业仍必须立刻回到可重试失败。"""
        class CloseBlockingClient:
            def __init__(self):
                self.close_started = threading.Event()
                self.closed = threading.Event()

            def post(self, *_args, **_kwargs):
                self.closed.wait(1)
                raise __import__("httpx").ReadTimeout("transport closed late")

            def close(self):
                self.close_started.set()
                time.sleep(0.20)
                self.closed.set()

        transport = CloseBlockingClient()
        client = DeepSeekClient(client=transport)
        monkeypatch.setattr(client, "_api_key", lambda _identity: "test-key")
        started = time.monotonic()

        with pytest.raises(DeepSeekTransportError):
            client.complete(
                [{"role": "user", "content": "质量判断"}],
                timeout_seconds=0.02, retry_count=0, hard_deadline=True,
            )

        assert time.monotonic() - started < 0.10
        assert transport.close_started.wait(0.10)

    def test_hard_deadline_does_not_wait_for_owned_client_close(self, monkeypatch):
        """自动创建的 httpx client 退出作用域时也不得重新阻塞硬截止。"""
        class CloseBlockingClient:
            def post(self, *_args, **_kwargs):
                time.sleep(1)

            def close(self):
                time.sleep(0.20)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        monkeypatch.setattr("scribe3.deepseek_client.httpx.Client", CloseBlockingClient)
        client = DeepSeekClient()
        monkeypatch.setattr(client, "_api_key", lambda _identity: "test-key")
        started = time.monotonic()

        with pytest.raises(DeepSeekTransportError):
            client.complete(
                [{"role": "user", "content": "质量判断"}],
                timeout_seconds=0.02, retry_count=0, hard_deadline=True,
            )

        assert time.monotonic() - started < 0.10

    def test_returns_parsed_schema_with_final_provider_metadata(self):
        client = DeepSeekClient()
        completion = _result(json.dumps({"score": 4, "reason": "好"}))
        client._complete_raw = lambda messages, **kw: completion

        parsed, metadata = client.complete_json_with_result(
            [{"role": "user", "content": "评分"}], schema=SampleSchema,
        )

        assert parsed == SampleSchema(score=4, reason="好")
        assert metadata is completion

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

    def test_json_repair_reissues_original_task_without_echoing_invalid_model_text(self):
        client = DeepSeekClient()
        calls = []

        def fake_raw(messages, **kw):
            calls.append(messages)
            return (_result("not json at all") if len(calls) == 1
                    else _result(json.dumps({"score": 3, "reason": "修复后"})))

        client._complete_raw = fake_raw
        client.complete_json([{"role": "user", "content": "评分"}], schema=SampleSchema)

        retry = calls[1]
        assert all(message.get("content") != "not json at all" for message in retry)
        assert "score" in retry[-1]["content"]

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

    def test_initial_json_request_carries_schema_contract_before_any_repair(self):
        """模型偶发忽略 json_object 时，首轮也必须有可执行的字段约束，而非等失败后才补。"""
        client = DeepSeekClient()
        captured = {}

        def fake_raw(messages, **_kw):
            captured["messages"] = messages
            return _result(json.dumps({"score": 1, "reason": "x"}))

        client._complete_raw = fake_raw
        client.complete_json([{"role": "user", "content": "评分"}], schema=SampleSchema)

        initial_contract = captured["messages"][-1]
        assert initial_contract["role"] == "user"
        assert "JSON Schema" in initial_contract["content"]
        assert '"score"' in initial_contract["content"]

    def test_forwards_bounded_completion_controls_to_json_request(self):
        """质量链必须能为单次结构化判断收紧通用 600 秒/无上限输出默认值。"""
        client = DeepSeekClient()
        captured = {}

        def fake_raw(messages, **kw):
            captured.update(kw)
            return _result(json.dumps({"score": 4, "reason": "有证据"}))

        client._complete_raw = fake_raw
        client.complete_json_with_result(
            [{"role": "user", "content": "评分"}], schema=SampleSchema,
            max_tokens=800, thinking="disabled", timeout_seconds=75, retry_count=0,
            max_repairs=0,
        )

        assert captured["max_tokens"] == 800
        assert captured["thinking"] == "disabled"
        assert captured["timeout_seconds"] == 75
        assert captured["retry_count"] == 0
