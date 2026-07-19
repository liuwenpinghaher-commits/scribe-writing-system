"""Test streaming LLM retry logic (G枢纽 P15).

流式重试:仅覆盖"建立连接 + 首字节到达前"的瞬时错重试。
一旦开始正常 yield,中途断流按失败上抛(避免重发 delta)。
n次 不重试,与 hermes_complete 重试语义一致。
"""
import httpx
import pytest

# 直接测重试逻辑,不连网;用闭包工厂模拟 make_stream
class TestStreamWithRetry:
    """_stream_with_retry 核心行为"""

    def test_retries_on_connect_error_before_first_yield(self):
        from scribe3.llm import _stream_with_retry

        calls = []

        def factory():
            calls.append(1)
            raise httpx.ConnectError("connection refused")

        with pytest.raises(Exception):
            list(_stream_with_retry(factory, max_retries=3))

        assert len(calls) == 3  # 重试了 3 次

    def test_succeeds_after_one_retry(self):
        from scribe3.llm import _stream_with_retry

        calls = []

        def factory():
            calls.append(1)
            if len(calls) < 2:
                raise httpx.ConnectError("timeout")
            yield "a"
            yield "b"

        result = list(_stream_with_retry(factory, max_retries=3))
        assert result == ["a", "b"]
        assert len(calls) == 2  # 失败 1 次,第 2 次成功

    def test_does_not_retry_after_first_yield(self):
        from scribe3.llm import _stream_with_retry

        calls = []

        def factory():
            calls.append(1)
            yield "x"
            raise httpx.ReadTimeout("mid-stream timeout")

        try:
            list(_stream_with_retry(factory, max_retries=3))
        except httpx.ReadTimeout:
            pass

        assert len(calls) == 1  # 已 yield,不重试

    def test_does_not_retry_on_4xx(self):
        from scribe3.llm import _stream_with_retry

        calls = []

        def factory():
            calls.append(1)
            resp = httpx.Response(400)
            raise httpx.HTTPStatusError("bad request", request=httpx.Request("POST", "http://x"), response=resp)

        with pytest.raises(httpx.HTTPStatusError):
            list(_stream_with_retry(factory, max_retries=3))

        assert len(calls) == 1  # 4xx 不重试

    def test_retries_on_5xx_before_first_yield(self):
        from scribe3.llm import _stream_with_retry

        calls = []

        def factory():
            calls.append(1)
            if len(calls) < 3:
                resp = httpx.Response(503)
                raise httpx.HTTPStatusError("server error", request=httpx.Request("POST", "http://x"), response=resp)
            yield "ok"

        result = list(_stream_with_retry(factory, max_retries=3))
        assert result == ["ok"]
        assert len(calls) == 3  # 5xx 重试

    def test_handles_remote_protocol_error(self):
        from scribe3.llm import _stream_with_retry

        calls = []

        def factory():
            calls.append(1)
            if len(calls) < 2:
                raise httpx.RemoteProtocolError("protocol error")
            yield "recovered"

        result = list(_stream_with_retry(factory, max_retries=3))
        assert result == ["recovered"]
        assert len(calls) == 2

    def test_raises_last_error_when_all_retries_exhausted(self):
        from scribe3.llm import _stream_with_retry

        errors = [httpx.ConnectError("e1"), httpx.ReadTimeout("e2"), httpx.RemoteProtocolError("e3")]

        def factory():
            raise errors.pop(0)

        with pytest.raises(httpx.RemoteProtocolError):
            list(_stream_with_retry(factory, max_retries=3))


class TestHermesCompleteRetryOverride:
    """章内精修可以把单句调用限制为一次，避免把超时放大成整章阻塞。"""

    def test_override_limits_transient_failure_to_one_attempt(self, monkeypatch):
        from scribe3 import llm

        calls = []

        def fail_once(*_args, **_kwargs):
            calls.append(1)
            raise httpx.ReadTimeout("simulated timeout")

        monkeypatch.setattr(llm, "_tick_daily", lambda: None)
        monkeypatch.setattr(llm, "_api_key", lambda: "test-key")
        monkeypatch.setattr(llm, "max_retries", lambda: 3)
        monkeypatch.setattr(llm.httpx, "post", fail_once)

        with pytest.raises(httpx.ReadTimeout):
            llm.hermes_complete("只试一次", model="test-model", retries_override=1)

        assert len(calls) == 1


def test_responses_events_without_tools_uses_official_deepseek_completion_stream(monkeypatch):
    """无工具生成不能经过会强制挂 MCP 的 Hermes Responses 代理层。"""
    from scribe3 import llm, settings

    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter([
                'data: {"choices":[{"delta":{"content":"雨落"}}]}',
                'data: {"choices":[{"delta":{"content":"闸板。"}}]}',
                'data: [DONE]',
            ])

    def fake_stream(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return FakeResp()

    monkeypatch.setattr(llm, "_tick_daily", lambda: None)
    monkeypatch.setattr(settings, "get_setting", lambda key: {
        "DEEPSEEK_API_KEY": "test-deepseek-key",
        "llm.max_retries": 1,
    }.get(key))
    monkeypatch.setattr(llm.httpx, "stream", fake_stream)

    events = list(llm.hermes_responses_events(
        "写一段场景投影", "只据事实输出", model="deepseek-chat", with_tools=False,
    ))

    assert events == [
        {"type": "response.output_text.delta", "delta": "雨落"},
        {"type": "response.output_text.delta", "delta": "闸板。"},
        {"type": "response.completed", "response": {"id": None}},
    ]
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-deepseek-key"
    assert captured["json"] == {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "只据事实输出"},
            {"role": "user", "content": "写一段场景投影"},
        ],
        "stream": True,
    }
