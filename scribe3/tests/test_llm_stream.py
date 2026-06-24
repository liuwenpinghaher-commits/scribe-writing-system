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
