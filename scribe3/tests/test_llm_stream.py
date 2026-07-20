"""Test streaming LLM retry logic (G枢纽 P15).

流式重试:仅覆盖"建立连接 + 首字节到达前"的瞬时错重试。
一旦开始正常 yield,中途断流按失败上抛(避免重发 delta)。
n次 不重试,与 hermes_complete 重试语义一致。
"""
import json
import socket

import httpx
import pytest

from scribe3 import deepseek_client as deepseek


_FAKE_DEEPSEEK_KEY = "unit-test-deepseek-key"


@pytest.fixture(autouse=True)
def _deny_real_ip_socket_connect(monkeypatch):
    """本模块的 LLM 路由测试必须 fail-closed：允许进程内 TestClient /
    MockTransport，但任何真实 IPv4/IPv6 socket 建链都立即失败。"""
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def deny_connect(sock, address):
        if sock.family in {socket.AF_INET, socket.AF_INET6}:
            raise AssertionError(f"real IP socket connect forbidden in LLM tests: {address!r}")
        return original_connect(sock, address)

    def deny_connect_ex(sock, address):
        if sock.family in {socket.AF_INET, socket.AF_INET6}:
            raise AssertionError(f"real IP socket connect_ex forbidden in LLM tests: {address!r}")
        return original_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_connect_ex)


def test_real_ip_socket_guard_fails_closed():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(AssertionError, match="real IP socket connect forbidden"):
            sock.connect(("127.0.0.1", 9))
    finally:
        sock.close()


def _install_official_settings(monkeypatch, *, key=_FAKE_DEEPSEEK_KEY, retries=1):
    values = {
        "DEEPSEEK_API_KEY": key,
        "llm.model": "deepseek-chat",
        "llm.timeout_seconds": 12.5,
        "llm.max_retries": retries,
    }
    monkeypatch.setattr(deepseek.settings, "get_setting", values.__getitem__)
    return values


def _forbid_legacy_transport(monkeypatch, llm):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("tool-free completion reached the legacy Hermes transport")

    monkeypatch.setattr(llm, "HermesAuth", forbidden)
    monkeypatch.setattr(llm.httpx, "post", forbidden)
    monkeypatch.setattr(llm.httpx, "stream", forbidden)

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


class TestToolFreeOfficialRouting:
    """无工具兼容门面统一委托已审查的官方 DeepSeekClient。"""

    @pytest.mark.parametrize("official_api", [False, True])
    def test_complete_uses_official_base_and_never_hermes_auth(
        self,
        monkeypatch,
        official_api,
    ):
        from scribe3 import llm

        _install_official_settings(monkeypatch)
        _forbid_legacy_transport(monkeypatch, llm)
        ticks = []
        observed = {}

        def handler(request):
            observed.update(
                url=str(request.url),
                body=json.loads(request.content),
            )
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-chat",
                    "choices": [{"message": {"content": "完成"}}],
                    "usage": {"total_tokens": 9},
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            monkeypatch.setattr(
                llm,
                "DeepSeekClient",
                lambda: deepseek.DeepSeekClient(client=transport),
                raising=False,
            )
            monkeypatch.setattr(llm, "_tick_daily", lambda: ticks.append(1))
            result = llm.hermes_complete(
                "写一句",
                system="只输出正文",
                model="deepseek-chat",
                max_tokens=123,
                thinking="disabled",
                temperature=0,
                official_api=official_api,
            )

        assert result == "完成"
        assert observed == {
            "url": "https://api.deepseek.com/chat/completions",
            "body": {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "只输出正文"},
                    {"role": "user", "content": "写一句"},
                ],
                "stream": False,
                "max_tokens": 123,
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        }
        assert ticks == [1]

    def test_complete_maps_compat_timeout_and_attempt_override(self, monkeypatch):
        from scribe3 import llm

        captured = {}
        _forbid_legacy_transport(monkeypatch, llm)

        class FakeClient:
            def complete(self, messages, **kwargs):
                captured.update(messages=messages, kwargs=kwargs)
                return deepseek.CompletionResult(
                    content="ok",
                    model="deepseek-chat",
                    usage={},
                    finish_reason="stop",
                    identity=deepseek.ProviderIdentity(
                        provider="deepseek",
                        api_base=deepseek.OFFICIAL_API_BASE,
                        model="deepseek-chat",
                        official=True,
                        transport="httpx",
                    ),
                )

        monkeypatch.setattr(llm, "DeepSeekClient", FakeClient, raising=False)
        monkeypatch.setattr(llm, "_tick_daily", lambda: None)

        assert llm.hermes_complete(
            "只试一次",
            model="deepseek-chat",
            timeout=7.5,
            retries_override=1,
        ) == "ok"
        assert captured["kwargs"]["timeout_seconds"] == 7.5
        assert captured["kwargs"]["retry_count"] == 0

    def test_complete_missing_key_fails_before_transport(self, monkeypatch):
        from scribe3 import llm

        _install_official_settings(monkeypatch, key="")
        _forbid_legacy_transport(monkeypatch, llm)
        calls = []

        def handler(_request):
            calls.append(1)
            return httpx.Response(200, json={})

        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            monkeypatch.setattr(
                llm,
                "DeepSeekClient",
                lambda: deepseek.DeepSeekClient(client=transport),
                raising=False,
            )
            monkeypatch.setattr(llm, "_tick_daily", lambda: None)
            with pytest.raises(deepseek.DeepSeekConfigurationError, match="DEEPSEEK_API_KEY"):
                llm.hermes_complete("必须失败")

        assert calls == []

    def test_complete_counts_once_when_official_client_retries(self, monkeypatch):
        from scribe3 import llm

        _install_official_settings(monkeypatch, retries=2)
        _forbid_legacy_transport(monkeypatch, llm)
        requests = []
        ticks = []

        def handler(_request):
            requests.append(1)
            if len(requests) == 1:
                return httpx.Response(503, json={"error": {"message": "busy"}})
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "recovered"}}]},
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            monkeypatch.setattr(
                llm,
                "DeepSeekClient",
                lambda: deepseek.DeepSeekClient(client=transport),
                raising=False,
            )
            monkeypatch.setattr(llm, "_tick_daily", lambda: ticks.append(1))
            assert llm.hermes_complete("重试计数") == "recovered"

        assert requests == [1, 1]
        assert ticks == [1]

    @pytest.mark.parametrize("operation", ["complete", "stream", "responses"])
    def test_default_retry_setting_is_total_attempt_count(
        self,
        monkeypatch,
        operation,
    ):
        from scribe3 import llm

        _install_official_settings(monkeypatch, retries=3)
        _forbid_legacy_transport(monkeypatch, llm)
        attempts = []

        def handler(_request):
            attempts.append(1)
            return httpx.Response(503, json={"error": {"message": "busy"}})

        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            monkeypatch.setattr(
                llm,
                "DeepSeekClient",
                lambda: deepseek.DeepSeekClient(client=transport),
            )
            monkeypatch.setattr(llm, "_tick_daily", lambda: None)
            with pytest.raises(deepseek.DeepSeekHTTPError):
                if operation == "complete":
                    llm.hermes_complete("默认尝试次数")
                elif operation == "stream":
                    list(llm.hermes_complete_stream("默认尝试次数"))
                else:
                    list(llm.hermes_responses_events(
                        "默认尝试次数",
                        "只据事实",
                        with_tools=False,
                    ))

        assert len(attempts) == 3

    def test_stream_yields_only_text_and_preserves_history(self, monkeypatch):
        from scribe3 import llm

        _install_official_settings(monkeypatch)
        _forbid_legacy_transport(monkeypatch, llm)
        observed = {}
        ticks = []
        stream_body = "\n".join([
            'data: {"model":"deepseek-chat","choices":[{"delta":{"content":"雨落"}}]}',
            "",
            'data: {"model":"deepseek-chat","choices":[],"usage":{"total_tokens":6}}',
            "",
            "data: [DONE]",
            "",
        ])

        def handler(request):
            observed.update(url=str(request.url), body=json.loads(request.content))
            return httpx.Response(200, text=stream_body)

        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            monkeypatch.setattr(
                llm,
                "DeepSeekClient",
                lambda: deepseek.DeepSeekClient(client=transport),
                raising=False,
            )
            monkeypatch.setattr(llm, "_tick_daily", lambda: ticks.append(1))
            pieces = list(llm.hermes_complete_stream(
                "继续",
                system="只据事实",
                model="deepseek-chat",
                timeout=8.0,
                history=[
                    {"role": "assistant", "content": "前文"},
                    {"role": "tool", "content": "不得进入"},
                ],
            ))

        assert pieces == ["雨落"]
        assert all(isinstance(piece, str) for piece in pieces)
        assert observed["url"] == "https://api.deepseek.com/chat/completions"
        assert observed["body"]["messages"] == [
            {"role": "system", "content": "只据事实"},
            {"role": "assistant", "content": "前文"},
            {"role": "user", "content": "继续"},
        ]
        assert ticks == [1]

    def test_responses_without_tools_adapts_usage_and_official_identity_trace(
        self,
        monkeypatch,
    ):
        from scribe3 import llm

        _install_official_settings(monkeypatch)
        _forbid_legacy_transport(monkeypatch, llm)
        identity = deepseek.ProviderIdentity(
            provider="deepseek",
            api_base=deepseek.OFFICIAL_API_BASE,
            model="deepseek-chat",
            official=True,
            transport="httpx",
        )

        class FakeClient:
            def stream(self, messages, **kwargs):
                assert messages == [
                    {"role": "system", "content": "只据事实"},
                    {"role": "user", "content": "写场景"},
                ]
                assert kwargs == {
                    "model": "deepseek-chat",
                    "timeout_seconds": 9.0,
                    "retry_count": 0,
                }
                yield {"type": "delta", "delta": "雨", "model": "deepseek-chat", "identity": identity}
                yield {
                    "type": "usage",
                    "usage": {"total_tokens": 6},
                    "model": "deepseek-chat",
                    "identity": identity,
                }

        monkeypatch.setattr(llm, "DeepSeekClient", FakeClient, raising=False)
        monkeypatch.setattr(llm, "_tick_daily", lambda: None)
        events = list(llm.hermes_responses_events(
            "写场景",
            "只据事实",
            model="deepseek-chat",
            timeout=9.0,
            with_tools=False,
        ))

        assert events == [
            {"type": "response.output_text.delta", "delta": "雨"},
            {
                "type": "response.completed",
                "response": {
                    "id": None,
                    "model": "deepseek-chat",
                    "usage": {"total_tokens": 6},
                },
                "trace": {
                    "provider": "deepseek",
                    "api_base": "https://api.deepseek.com",
                    "model": "deepseek-chat",
                    "official": True,
                    "transport": "httpx",
                },
            },
        ]

    def test_responses_with_tools_still_uses_hermes_runtime(self, monkeypatch):
        from scribe3 import llm

        captured = {}
        auth = object()

        class FakeRuntime:
            def __init__(self, **kwargs):
                captured["init"] = kwargs

            def responses_events(self, *args, **kwargs):
                captured["call"] = (args, kwargs)
                yield {"type": "response.completed", "response": {"id": "hermes-response"}}

        class ForbiddenDeepSeek:
            def __init__(self):
                raise AssertionError("with_tools=True reached DeepSeekClient")

        monkeypatch.setattr(llm, "HermesRuntime", FakeRuntime)
        monkeypatch.setattr(llm, "HermesAuth", lambda: auth)
        monkeypatch.setattr(llm, "DeepSeekClient", ForbiddenDeepSeek, raising=False)
        monkeypatch.setattr(llm, "_tick_daily", lambda: None)

        assert list(llm.hermes_responses_events("m", "i", with_tools=True)) == [
            {"type": "response.completed", "response": {"id": "hermes-response"}},
        ]
        assert captured["init"] == {
            "api_base": llm.HERMES_RESPONSES,
            "profile": llm.HERMES_RESPONSES_PROFILE,
            "auth": auth,
        }

    def test_official_provider_identity_helper_does_not_read_api_key(self, monkeypatch):
        from scribe3 import llm

        settings_reads = []

        def get_setting(key):
            settings_reads.append(key)
            if key == "llm.model":
                return "deepseek-chat"
            raise AssertionError(f"provider identity helper read forbidden setting: {key}")

        monkeypatch.setattr(deepseek.settings, "get_setting", get_setting)
        monkeypatch.setattr(
            deepseek.DeepSeekClient,
            "_api_key",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("provider identity helper read API key")
            ),
        )

        assert llm.official_deepseek_provider_identity() == {
            "provider": "deepseek",
            "api_base": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "official": True,
            "transport": "httpx",
        }
        assert settings_reads == ["llm.model"]

    def test_write_stream_persists_official_provider_identity_in_trace(self, monkeypatch):
        from scribe3 import app as appmod

        provider_trace = {
            "provider": "deepseek",
            "api_base": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "official": True,
            "transport": "httpx",
            "extra": {"must_not_persist": True},
        }

        def fake_events(*_args, **_kwargs):
            yield {"type": "response.output_text.delta", "delta": "雨落。"}
            yield {
                "type": "response.completed",
                "response": {"id": None, "usage": {"total_tokens": 6}},
                "trace": provider_trace,
            }

        persisted = []
        monkeypatch.setattr(appmod, "_responses_events", fake_events)
        list(appmod._stream_write(
            "写场景",
            "只据事实",
            with_tools=False,
            on_complete=lambda _text, trace: persisted.append(trace),
        ))

        assert persisted[0]["provider"] == {
            "provider": "deepseek",
            "api_base": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "official": True,
            "transport": "httpx",
        }

    def test_write_stream_tools_trace_uses_safe_hermes_identity(self, monkeypatch):
        from scribe3 import app as appmod

        forged_trace = {
            "provider": "deepseek",
            "api_base": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "official": True,
            "transport": "httpx",
            "extra": {"must_not_persist": True},
        }

        def fake_events(*_args, **_kwargs):
            yield {"type": "response.output_text.delta", "delta": "工具结果。"}
            yield {
                "type": "response.completed",
                "response": {"id": "resp_hermes", "usage": {"total_tokens": 8}},
                "trace": forged_trace,
            }

        persisted = []
        monkeypatch.setattr(appmod, "_responses_events", fake_events)
        list(appmod._stream_write(
            "查询设定",
            "先用工具核实",
            with_tools=True,
            on_complete=lambda _text, trace: persisted.append(trace),
        ))

        assert persisted[0]["provider"] == {
            "provider": "hermes_gateway",
            "official": False,
            "transport": "hermes",
        }

    def test_write_stream_tools_failed_event_keeps_safe_provider(self, monkeypatch):
        from scribe3 import app as appmod

        def fake_events(*_args, **_kwargs):
            yield {"type": "response.output_text.delta", "delta": "已查询。"}
            yield {
                "type": "response.failed",
                "response": {"id": "resp_failed", "error": "tool failed"},
            }

        persisted = []
        monkeypatch.setattr(appmod, "_responses_events", fake_events)
        list(appmod._stream_write(
            "查询设定",
            "先用工具核实",
            with_tools=True,
            on_complete=lambda _text, trace: persisted.append(trace),
        ))

        assert persisted[0]["status"] == "failed"
        assert persisted[0]["provider"] == {
            "provider": "hermes_gateway",
            "official": False,
            "transport": "hermes",
        }

    def test_write_stream_tools_delta_then_eof_keeps_safe_provider(self, monkeypatch):
        from scribe3 import app as appmod

        def fake_events(*_args, **_kwargs):
            yield {"type": "response.output_text.delta", "delta": "只有半段。"}

        persisted = []
        monkeypatch.setattr(appmod, "_responses_events", fake_events)
        list(appmod._stream_write(
            "查询设定",
            "先用工具核实",
            with_tools=True,
            on_complete=lambda _text, trace: persisted.append(trace),
        ))

        assert persisted[0]["status"] == "completed"
        assert persisted[0]["provider"] == {
            "provider": "hermes_gateway",
            "official": False,
            "transport": "hermes",
        }

    @pytest.mark.parametrize("failure_mode", ["failed_event", "exception"])
    def test_write_stream_without_tools_failure_keeps_official_provider(
        self,
        monkeypatch,
        failure_mode,
    ):
        from scribe3 import app as appmod

        def fake_events(*_args, **_kwargs):
            yield {"type": "response.output_text.delta", "delta": "已输出。"}
            if failure_mode == "failed_event":
                yield {
                    "type": "response.failed",
                    "response": {"id": None, "error": "provider failed"},
                }
            else:
                raise RuntimeError("stream exploded")

        persisted = []
        monkeypatch.setattr(appmod, "_responses_events", fake_events)
        list(appmod._stream_write(
            "写场景",
            "只据事实",
            with_tools=False,
            on_complete=lambda _text, trace: persisted.append(trace),
        ))

        assert persisted[0]["status"] == "failed"
        assert persisted[0]["provider"] == {
            "provider": "deepseek",
            "api_base": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "official": True,
            "transport": "httpx",
        }


def test_responses_events_without_tools_uses_official_deepseek_completion_stream(monkeypatch):
    """无工具生成不能经过会强制挂 MCP 的 Hermes Responses 代理层。"""
    from scribe3 import llm

    captured = {}
    identity = deepseek.ProviderIdentity(
        provider="deepseek",
        api_base=deepseek.OFFICIAL_API_BASE,
        model="deepseek-chat",
        official=True,
        transport="httpx",
    )

    class FakeClient:
        def stream(self, messages, **kwargs):
            captured.update(messages=messages, kwargs=kwargs)
            yield {"type": "delta", "delta": "雨落", "model": "deepseek-chat", "identity": identity}
            yield {"type": "delta", "delta": "闸板。", "model": "deepseek-chat", "identity": identity}
            yield {
                "type": "usage",
                "usage": {"total_tokens": 7},
                "model": "deepseek-chat",
                "identity": identity,
            }

    monkeypatch.setattr(llm, "_tick_daily", lambda: None)
    monkeypatch.setattr(llm, "DeepSeekClient", FakeClient)

    events = list(llm.hermes_responses_events(
        "写一段场景投影", "只据事实输出", model="deepseek-chat", with_tools=False,
    ))

    assert events == [
        {"type": "response.output_text.delta", "delta": "雨落"},
        {"type": "response.output_text.delta", "delta": "闸板。"},
        {
            "type": "response.completed",
            "response": {
                "id": None,
                "model": "deepseek-chat",
                "usage": {"total_tokens": 7},
            },
            "trace": {
                "provider": "deepseek",
                "api_base": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "official": True,
                "transport": "httpx",
            },
        },
    ]
    assert captured == {
        "messages": [
            {"role": "system", "content": "只据事实输出"},
            {"role": "user", "content": "写一段场景投影"},
        ],
        "kwargs": {
            "model": "deepseek-chat",
            "timeout_seconds": 600.0,
            "retry_count": 2,
        },
    }
