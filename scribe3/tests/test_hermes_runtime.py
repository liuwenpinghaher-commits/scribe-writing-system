import json
import threading

from fastapi.testclient import TestClient


def test_api_key_prefers_env_then_profile_then_default(tmp_path, monkeypatch):
    from scribe3.hermes_runtime import HermesAuth

    hermes_home = tmp_path / ".hermes"
    profile_dir = hermes_home / "profiles" / "scribe3"
    profile_dir.mkdir(parents=True)
    (hermes_home / ".env").write_text("API_SERVER_KEY=default-key\n", encoding="utf-8")
    (profile_dir / ".env").write_text("API_SERVER_KEY=profile-key\n", encoding="utf-8")

    monkeypatch.delenv("API_SERVER_KEY", raising=False)
    auth = HermesAuth(home=hermes_home)
    assert auth.api_key("scribe3") == "profile-key"

    (profile_dir / ".env").unlink()
    assert auth.api_key("scribe3") == "default-key"

    monkeypatch.setenv("API_SERVER_KEY", "env-key")
    assert auth.api_key("scribe3") == "env-key"


def test_runtime_probe_normalizes_health_and_capabilities(monkeypatch):
    from scribe3.hermes_runtime import HermesAuth, HermesRuntime
    import scribe3.hermes_runtime as runtime

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    def fake_get(url, **_kw):
        if url.endswith("/health/detailed"):
            return FakeResp({"status": "ok", "api_server": {"state": "connected"}})
        if url.endswith("/v1/capabilities"):
            return FakeResp({
                "responses_api": True,
                "run_submission": True,
                "run_approval_response": True,
                "session_management": True,
            })
        if url.endswith("/v1/skills"):
            return FakeResp({"data": [{"name": "scribe-novel-v2", "enabled": True}]})
        if url.endswith("/v1/toolsets"):
            return FakeResp({"data": [{"name": "scribe3", "tools": ["s3_get_chapter"]}]})
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(runtime.httpx, "get", fake_get)
    rt = HermesRuntime(
        api_base="http://127.0.0.1:8643/v1",
        profile="scribe3",
        auth=HermesAuth(env={"API_SERVER_KEY": "test-key"}),
    )

    status = rt.probe()
    assert status["profile"] == "scribe3"
    assert status["root_url"] == "http://127.0.0.1:8643"
    assert status["ok"] is True
    assert status["health"]["api_server"]["state"] == "connected"
    assert status["capabilities"]["responses_api"] is True
    assert status["capabilities"]["run_approval_response"] is True
    assert status["features"]["responses_api"] is True
    assert status["features"]["run_approval_response"] is True
    assert status["skills"][0]["name"] == "scribe-novel-v2"
    assert status["toolsets"][0]["name"] == "scribe3"


def test_responses_events_sends_conversation_store_session_and_tools(monkeypatch):
    from scribe3.hermes_runtime import HermesAuth, HermesRuntime
    import scribe3.hermes_runtime as runtime

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
                'data: {"type":"response.output_text.delta","delta":"好"}',
                "data: [DONE]",
            ])

    def fake_stream(method, url, **kw):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kw["headers"]
        captured["body"] = kw["json"]
        return FakeResp()

    monkeypatch.setattr(runtime.httpx, "stream", fake_stream)
    rt = HermesRuntime(
        api_base="http://127.0.0.1:8643/v1",
        profile="scribe3",
        auth=HermesAuth(env={"API_SERVER_KEY": "test-key"}),
    )

    events = list(rt.responses_events(
        "查伏笔",
        "先核实真实数据",
        conversation="conv_123",
        session_key="work:main:chapter:7",
        store=True,
        with_tools=True,
    ))

    assert events == [{"type": "response.output_text.delta", "delta": "好"}]
    assert captured["method"] == "POST"
    assert captured["url"] == "http://127.0.0.1:8643/v1/responses"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["headers"]["X-Hermes-Session-Key"] == "work:main:chapter:7"
    assert captured["body"]["conversation"] == "conv_123"
    assert captured["body"]["store"] is True
    assert captured["body"]["tools"] == [{"type": "mcp", "server_label": "scribe3_read"}]


def test_responses_carries_conversation_previous_response_and_context_headers(monkeypatch):
    """Task 11:responses_events 除 conversation/session 外,还须带 previous_response_id
    续接 + X-Scribe-Context-Revision/Hash 头(动态上下文层的服务端可观测游标)。"""
    from scribe3.hermes_runtime import HermesAuth, HermesRuntime
    import scribe3.hermes_runtime as runtime_module

    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter([])

    def fake_stream(method, url, **kw):
        captured["headers"] = kw["headers"]
        captured["json"] = kw["json"]
        return FakeResp()

    monkeypatch.setattr(runtime_module.httpx, "stream", fake_stream)
    runtime = HermesRuntime(
        api_base="http://127.0.0.1:8643/v1",
        profile="scribe3",
        auth=HermesAuth(env={"API_SERVER_KEY": "test-key"}),
    )

    list(runtime.responses_events(
        "继续", "dynamic", conversation="conv-1", previous_response_id="resp-9",
        session_key="scribe3|work:book-a|thread:thread-1",
        context_revision=7, context_hash="a" * 64,
    ))

    assert captured["json"]["conversation"] == "conv-1"
    assert captured["json"]["previous_response_id"] == "resp-9"
    assert captured["headers"]["X-Hermes-Session-Key"] == "scribe3|work:book-a|thread:thread-1"
    assert captured["headers"]["X-Scribe-Context-Revision"] == "7"
    assert captured["headers"]["X-Scribe-Context-Hash"] == "a" * 64


def test_responses_omits_context_headers_when_not_provided(monkeypatch):
    """默认路径(未开 envelope)不发 previous_response_id/context 头——旧行为字节不变。"""
    from scribe3.hermes_runtime import HermesAuth, HermesRuntime
    import scribe3.hermes_runtime as runtime_module

    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter([])

    def fake_stream(method, url, **kw):
        captured["headers"] = kw["headers"]
        captured["json"] = kw["json"]
        return FakeResp()

    monkeypatch.setattr(runtime_module.httpx, "stream", fake_stream)
    runtime = HermesRuntime(
        api_base="http://127.0.0.1:8643/v1",
        profile="scribe3",
        auth=HermesAuth(env={"API_SERVER_KEY": "test-key"}),
    )

    list(runtime.responses_events("m", "i", session_key="scribe3|work:x|thread:t"))

    assert "previous_response_id" not in captured["json"]
    assert "X-Scribe-Context-Revision" not in captured["headers"]
    assert "X-Scribe-Context-Hash" not in captured["headers"]


def test_hermes_turn_context_exposes_thread_stable_session_key():
    """HermesTurnContext 把 work+thread 打包为稳定 session key(切章不换)。"""
    from scribe3.hermes_runtime import HermesTurnContext

    turn = HermesTurnContext(
        work="book-a", thread_id="thread-1",
        conversation_id="conv-1", previous_response_id="resp-9",
        context_session_id="cs-1", context_revision=7, context_hash="a" * 64,
        envelope_hash="b" * 64,
    )
    assert turn.session_key == "scribe3|work:book-a|thread:thread-1"


def test_event_adapter_maps_responses_events_to_internal_events():
    from scribe3.hermes_runtime import HermesEventAdapter

    adapter = HermesEventAdapter()

    assert adapter.adapt({"type": "response.output_text.delta", "delta": "甲"}) == {
        "kind": "text.delta",
        "delta": "甲",
        "source_type": "response.output_text.delta",
    }
    assert adapter.adapt({
        "type": "response.output_item.added",
        "item": {"type": "function_call", "name": "s3_list_promises", "arguments": "{}",
                 "call_id": "call_1"},
    }) == {
        "kind": "tool.started",
        "name": "s3_list_promises",
        "arguments": "{}",
        "call_id": "call_1",
        "source_type": "response.output_item.added",
    }
    assert adapter.adapt({
        "type": "response.output_item.done",
        "item": {"type": "function_call_output", "call_id": "call_1", "output": "{\"ok\":true}"},
    }) == {
        "kind": "tool.output",
        "call_id": "call_1",
        "output": "{\"ok\":true}",
        "output_available": True,
        "source_type": "response.output_item.done",
    }
    assert adapter.adapt({
        "type": "response.completed",
        "response": {"id": "resp_1", "usage": {"input_tokens": 10}},
    }) == {
        "kind": "run.completed",
        "response_id": "resp_1",
        "usage": {"input_tokens": 10},
        "source_type": "response.completed",
    }
    raw = {"type": "response.unknown", "x": 1}
    assert adapter.adapt(raw) == {"kind": "raw", "event": raw, "source_type": "response.unknown"}


def test_event_adapter_maps_runs_events_to_internal_events():
    from scribe3.hermes_runtime import HermesEventAdapter

    adapter = HermesEventAdapter()

    assert adapter.adapt({"type": "message.delta", "delta": "乙"}) == {
        "kind": "text.delta",
        "delta": "乙",
        "source_type": "message.delta",
    }
    assert adapter.adapt({
        "type": "tool.start",
        "name": "s3_add_fact",
        "arguments": "{\"oid\":\"fact:x\"}",
        "call_id": "call_2",
    }) == {
        "kind": "tool.started",
        "name": "s3_add_fact",
        "arguments": "{\"oid\":\"fact:x\"}",
        "call_id": "call_2",
        "source_type": "tool.start",
    }
    assert adapter.adapt({
        "type": "approval.request",
        "run_id": "run_1",
        "approval_id": "ap_1",
        "tool_call_id": "call_2",
        "tool_name": "s3_add_fact",
        "message": "批准写入?",
    }) == {
        "kind": "approval.requested",
        "run_id": "run_1",
        "approval_id": "ap_1",
        "call_id": "call_2",
        "name": "s3_add_fact",
        "message": "批准写入?",
        "pattern_key": None,
        "choices": None,
        "source_type": "approval.request",
    }
    assert adapter.adapt({
        "type": "approval.resolved",
        "run_id": "run_1",
        "approval_id": "ap_1",
        "tool_call_id": "call_2",
        "tool_name": "s3_add_fact",
        "decision": "approve",
    }) == {
        "kind": "approval.resolved",
        "run_id": "run_1",
        "approval_id": "ap_1",
        "call_id": "call_2",
        "name": "s3_add_fact",
        "decision": "approve",
        "source_type": "approval.resolved",
    }
    assert adapter.adapt({
        "type": "run.completed",
        "run_id": "run_1",
        "model": "qwen3.8-max-preview",
        "usage": {"total_tokens": 30},
    }) == {
        "kind": "run.completed",
        "run_id": "run_1",
        "model": "qwen3.8-max-preview",
        "usage": {"total_tokens": 30},
        "source_type": "run.completed",
    }


def test_event_adapter_maps_real_runs_event_field_payloads():
    from scribe3.hermes_runtime import HermesEventAdapter

    adapter = HermesEventAdapter()

    assert adapter.adapt({
        "event": "tool.started",
        "run_id": "run_real",
        "tool": "mcp_scribe3_write_s3_add_fact",
        "timestamp": 1783629590.8621252,
    }) == {
        "kind": "tool.started",
        "run_id": "run_real",
        "name": "s3_add_fact",
        "arguments": "",
        "call_id": "synthetic:1",
        "source_type": "tool.started",
    }
    assert adapter.adapt({
        "event": "approval.request",
        "run_id": "run_real",
        "command": "批准写入?新增事实 fact:x:role:y·状态=已确认",
        "description": "Approval requested by MCP server 'scribe3_write'.",
        "pattern_key": "mcp_elicitation",
        "choices": ["once", "session", "always", "deny"],
    }) == {
        "kind": "approval.requested",
        "run_id": "run_real",
        # MCP elicitation 常无 Hermes approval_id:合成稳定 id 供前端 approve 绑定
        "approval_id": "mcp:run_real::mcp_elicitation",
        "call_id": None,
        "name": "",
        "message": "批准写入?新增事实 fact:x:role:y·状态=已确认",
        "pattern_key": "mcp_elicitation",
        "choices": ["once", "session", "always", "deny"],
        "source_type": "approval.request",
    }
    assert adapter.adapt({
        "event": "tool.completed",
        "run_id": "run_real",
        "tool": "mcp_scribe3_write_s3_add_fact",
        "result": {"status": "written", "tool": "s3_add_fact"},
    }) == {
        "kind": "tool.output",
        "run_id": "run_real",
        "name": "s3_add_fact",
        "call_id": "synthetic:1",
        "output": {"status": "written", "tool": "s3_add_fact"},
        "output_available": True,
        "completion": {},
        "source_type": "tool.completed",
    }
    assert adapter.adapt({
        "event": "approval.responded",
        "run_id": "run_real",
        "choice": "once",
        "resolved": 1,
    }) == {
        "kind": "approval.resolved",
        "run_id": "run_real",
        "approval_id": None,
        "call_id": None,
        "name": "",
        "decision": "once",
        "source_type": "approval.responded",
    }


def test_event_adapter_correlates_idless_real_tool_completion_with_its_start():
    """真实 Hermes Runs 事件可能没有 call_id；不能因此把已完成的只读工具误判成未输出。"""
    from scribe3.hermes_runtime import HermesEventAdapter

    adapter = HermesEventAdapter()
    started = adapter.adapt({
        "event": "tool.started", "run_id": "run_real", "tool": "mcp_scribe3_deduce_preview_s3_get_chapter",
    })
    completed = adapter.adapt({
        "event": "tool.completed", "run_id": "run_real", "tool": "mcp_scribe3_deduce_preview_s3_get_chapter",
        "result": {"seq": 1, "title": "预览审阅章"},
    })

    assert started["call_id"], "无 call_id 的真实 started 事件必须获得流内审计 ID"
    assert completed["call_id"] == started["call_id"]
    assert completed["output"] == {"seq": 1, "title": "预览审阅章"}


def test_event_adapter_marks_upstream_omitted_tool_result_as_unavailable():
    """Hermes 0.18.2 Runs 真实事件仅给完成回执时，不能伪装成空工具输出。"""
    from scribe3.hermes_runtime import HermesEventAdapter

    adapter = HermesEventAdapter()
    adapter.adapt({
        "event": "tool.started", "run_id": "run_real", "tool": "mcp_scribe3_read__s3_get_intent",
    })

    completed = adapter.adapt({
        "event": "tool.completed", "run_id": "run_real",
        "tool": "mcp_scribe3_read__s3_get_intent", "duration": 0.012, "error": False,
    })

    assert completed["output"] == ""
    assert completed["output_available"] is False
    assert completed["completion"] == {"duration": 0.012, "error": False}


def test_event_adapter_preserves_runs_completed_final_output():
    """Runs 终态自带的最终回答是质量判断的可复核证据，不能在适配层丢弃。"""
    from scribe3.hermes_runtime import HermesEventAdapter

    completed = HermesEventAdapter().adapt({
        "event": "run.completed", "run_id": "run_final",
        "output": "已核实：创作意图为空。", "usage": {"total_tokens": 42},
    })

    assert completed["kind"] == "run.completed"
    assert completed["output"] == "已核实：创作意图为空。"
    assert completed["usage"] == {"total_tokens": 42}


def test_runs_api_methods_send_session_key_and_parse_events(monkeypatch):
    from scribe3.hermes_runtime import HermesAuth, HermesRuntime
    import scribe3.hermes_runtime as runtime

    calls = []

    class FakeResp:
        def __init__(self, payload=None, lines=None):
            self._payload = payload or {}
            self._lines = lines or []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

        def iter_lines(self):
            return iter(self._lines)

    def fake_post(url, **kw):
        calls.append(("POST", url, kw))
        if url.endswith("/v1/runs"):
            return FakeResp({"run_id": "run_1", "status": "started"})
        if url.endswith("/v1/runs/run_1/approval"):
            return FakeResp({"status": "recorded"})
        if url.endswith("/v1/runs/run_1/stop"):
            return FakeResp({"status": "stopping"})
        raise AssertionError(f"unexpected POST {url}")

    def fake_get(url, **kw):
        calls.append(("GET", url, kw))
        if url.endswith("/v1/runs/run_1"):
            return FakeResp({"run_id": "run_1", "status": "completed"})
        raise AssertionError(f"unexpected GET {url}")

    def fake_stream(method, url, **kw):
        calls.append((method, url, kw))
        return FakeResp(lines=[
            'data: {"type":"run.started","run_id":"run_1"}',
            'data: {"type":"message.delta","delta":"好"}',
            "data: [DONE]",
        ])

    monkeypatch.setattr(runtime.httpx, "post", fake_post)
    monkeypatch.setattr(runtime.httpx, "get", fake_get)
    monkeypatch.setattr(runtime.httpx, "stream", fake_stream)
    rt = HermesRuntime(
        api_base="http://127.0.0.1:8643/v1",
        profile="scribe3",
        auth=HermesAuth(env={"API_SERVER_KEY": "test-key"}),
    )

    created = rt.create_run("整理本章", instructions="用工具核实", session_id="sess_1",
                            session_key="work:main")
    status = rt.run_status("run_1", session_key="work:main")
    events = list(rt.run_events("run_1", session_key="work:main"))
    approval = rt.approve_run("run_1", {"approval_id": "ap_1", "decision": "approve"},
                              session_key="work:main")
    stopped = rt.stop_run("run_1", session_key="work:main")

    assert created["run_id"] == "run_1"
    assert status["status"] == "completed"
    assert events[1]["delta"] == "好"
    assert approval["status"] == "recorded"
    assert stopped["status"] == "stopping"
    post_run = calls[0][2]
    assert post_run["headers"]["X-Hermes-Session-Key"] == "work:main"
    assert post_run["json"]["session_id"] == "sess_1"
    assert post_run["json"]["instructions"] == "用工具核实"


def test_llm_responses_events_exposes_store_conversation_and_session(monkeypatch):
    import scribe3.llm as llm

    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter(["data: " + json.dumps({"type": "response.completed"})])

    def fake_stream(method, url, **kw):
        captured["headers"] = kw["headers"]
        captured["body"] = kw["json"]
        return FakeResp()

    monkeypatch.setenv("API_SERVER_KEY", "env-key")
    monkeypatch.setattr(llm.httpx, "stream", fake_stream)

    list(llm.hermes_responses_events(
        "m",
        "i",
        conversation="conv_456",
        session_key="work:main",
        store=True,
        with_tools=True,
    ))

    assert captured["headers"]["X-Hermes-Session-Key"] == "work:main"
    assert captured["body"]["conversation"] == "conv_456"
    assert captured["body"]["store"] is True
    assert captured["body"]["tools"] == [{"type": "mcp", "server_label": "scribe3_read"}]


def test_llm_responses_events_defaults_to_read_only_mcp_surface(monkeypatch):
    import scribe3.llm as llm

    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter(["data: " + json.dumps({"type": "response.completed"})])

    def fake_stream(method, url, **kw):
        captured["body"] = kw["json"]
        return FakeResp()

    monkeypatch.setenv("API_SERVER_KEY", "env-key")
    monkeypatch.setattr(llm.httpx, "stream", fake_stream)

    list(llm.hermes_responses_events("m", "i", with_tools=True))

    assert captured["body"]["tools"] == [{"type": "mcp", "server_label": "scribe3_read"}]


def test_ai_runtime_status_endpoint_returns_runtime_snapshot(monkeypatch):
    import scribe3.app as appmod

    monkeypatch.setattr(appmod, "_hermes_runtime_status", lambda: {
        "ok": True,
        "profiles": [
            {"profile": "default", "ok": True, "capabilities": {"chat_completions": True}},
            {"profile": "scribe3", "ok": True, "capabilities": {"responses_api": True}},
        ],
    })

    resp = TestClient(appmod.app).get("/ai/runtime-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["profiles"][1]["profile"] == "scribe3"
    assert body["profiles"][1]["capabilities"]["responses_api"] is True


def test_runtime_status_exposes_both_deduce_profiles_and_safe_config_summaries(monkeypatch):
    """Gate B 的两条独立工具面必须同样进入真实运行态审计，不能只存在于路由表。"""
    import scribe3.app as appmod
    import scribe3.hermes_runtime as hermes_runtime
    import scribe3.llm as llm

    class Runtime:
        def __init__(self, *, api_base, profile):
            self.api_base = api_base
            self.profile = profile

        def probe(self):
            return {"profile": self.profile, "api_base": self.api_base, "ok": True,
                    "capabilities": {"run_submission": True}}

    class Store:
        def count_failed_memory_events(self):
            return 0

    monkeypatch.setattr(hermes_runtime, "HermesRuntime", Runtime)
    monkeypatch.setattr(llm, "HERMES", "http://default.test/v1")
    monkeypatch.setattr(llm, "HERMES_RESPONSES", "http://read.test/v1")
    monkeypatch.setattr(llm, "HERMES_RUNS", "http://write.test/v1")
    monkeypatch.setattr(llm, "HERMES_DEDUCE_RUNS", "http://deduce.test/v1")
    monkeypatch.setattr(llm, "HERMES_DEDUCE_PREVIEW_RUNS", "http://preview.test/v1")
    monkeypatch.setattr(appmod, "_hermes_profile_config_summary", lambda profile: {"profile": profile})
    monkeypatch.setattr(appmod, "_hermes_cron_status", lambda _profile: {})
    monkeypatch.setattr(appmod, "_summarize_hermes_runtime", lambda profiles, **_kw: {"issues": [], "profiles": profiles})
    monkeypatch.setattr(appmod, "_context_memory_metrics", lambda: {})
    monkeypatch.setattr(appmod, "_store_for", lambda _work: Store())

    status = appmod._hermes_runtime_status()

    assert [item["profile"] for item in status["profiles"]] == [
        "default", "scribe3", "scribe3_write", "scribe3_deduce", "scribe3_deduce_preview",
    ]
    assert status["profile_configs"]["scribe3_deduce"] == {"profile": "scribe3_deduce"}
    assert status["profile_configs"]["scribe3_deduce_preview"] == {"profile": "scribe3_deduce_preview"}


def test_gateway_control_surfaces_include_both_deduce_profiles(monkeypatch):
    """Gate B profile 必须可被只读探活与受控重启；未知 profile 仍应 fail-closed。"""
    import subprocess
    import scribe3.app as appmod
    import scribe3.settings as settings

    values = {
        "HERMES_API": "http://default.test/v1",
        "HERMES_RESPONSES_API": "http://read.test/v1",
        "HERMES_RESPONSES_PROFILE": "scribe3",
        "HERMES_RUNS_API": "http://write.test/v1",
        "HERMES_RUNS_PROFILE": "scribe3_write",
        "HERMES_DEDUCE_RUNS_API": "http://deduce.test/v1",
        "HERMES_DEDUCE_PREVIEW_RUNS_API": "http://preview.test/v1",
        "gateway.hermes_bin": "/usr/local/bin/hermes",
    }
    monkeypatch.setattr(settings, "get_setting", values.__getitem__)
    monkeypatch.setattr(appmod.os.path, "isfile", lambda _path: True)
    monkeypatch.setattr(appmod.os, "access", lambda _path, _mode: True)
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    class Response:
        status_code = 200

    monkeypatch.setattr("httpx.get", lambda *_args, **_kwargs: Response())
    client = TestClient(appmod.app)

    listed = client.get("/gateway/status")
    assert listed.status_code == 200
    assert [item["profile"] for item in listed.json()["gateways"]] == [
        "(default)", "scribe3", "scribe3_write", "scribe3_deduce", "scribe3_deduce_preview",
    ]

    restarted = client.post("/gateway/restart", json={"profile": "scribe3_deduce_preview"})
    assert restarted.status_code == 200
    assert restarted.json()["profile"] == "scribe3_deduce_preview"
    assert restarted.json()["online"] is True


def test_profile_config_summary_counts_mcp_tools_without_secrets(tmp_path):
    import scribe3.app as appmod

    profile_dir = tmp_path / "profiles" / "scribe3"
    profile_dir.mkdir(parents=True)
    (profile_dir / "config.yaml").write_text(
        """
model:
  api_key: should-not-leak
mcp_servers:
  scribe3_read:
    enabled: true
    command: /tmp/run_mcp.sh
    tools:
      include: [s3_get_chapter, s3_list_promises]
  scribe3_write:
    enabled: true
    command: /tmp/run_mcp.sh
    tools:
      include: [s3_save_chapter]
platform_toolsets:
  api_server: [mcp-scribe3_read]
""",
        encoding="utf-8",
    )

    summary = appmod._hermes_profile_config_summary("scribe3", home=tmp_path)

    assert summary["profile"] == "scribe3"
    assert summary["api_server_toolsets"] == ["mcp-scribe3_read"]
    assert summary["mcp_toolsets"]["scribe3_read"]["tool_count"] == 2
    assert summary["api_server_mcp_tool_count"] == 2
    assert "should-not-leak" not in json.dumps(summary, ensure_ascii=False)


def test_profile_config_summary_counts_bare_mcp_server_toolset_keys(tmp_path):
    """Hermes 0.18.2 接受 mcp_servers 裸键，不得误报成原生工具面。"""
    import scribe3.app as appmod

    profile_dir = tmp_path / "profiles" / "scribe3_write"
    profile_dir.mkdir(parents=True)
    (profile_dir / "config.yaml").write_text(
        """
mcp_servers:
  scribe3_read:
    tools:
      include: [s3_get_intent]
  scribe3_write:
    tools:
      include: [s3_add_fact, s3_add_event]
platform_toolsets:
  api_server: [scribe3_read, scribe3_write]
""",
        encoding="utf-8",
    )

    summary = appmod._hermes_profile_config_summary(
        "scribe3_write", home=tmp_path,
    )

    assert summary["api_server_toolsets"] == ["scribe3_read", "scribe3_write"]
    assert summary["api_server_mcp_tool_count"] == 3
    assert summary["api_server_native_toolsets"] == []


def test_runtime_status_summary_reports_gateway_policy_and_degradation():
    import scribe3.app as appmod

    profiles = [
        {
            "profile": "default",
            "ok": True,
            "features": {"chat_completions": True},
            "health": {"version": "0.18.0"},
        },
        {
            "profile": "scribe3",
            "ok": True,
            "features": {"responses_api": True},
            "skills": [{"name": "scribe-novel-v2"}],
            "health": {"version": "0.18.0"},
        },
        {
            "profile": "scribe3_write",
            "ok": False,
            "features": {"run_submission": True, "run_approval_response": False},
            "skills": [{"name": "scribe-novel-v2"}],
            "health": {"version": "0.18.0"},
            "error": "connection refused",
        },
    ]
    configs = {
        "scribe3": {
            "api_server_toolsets": ["scribe3_read"],
            "api_server_mcp_tool_count": 32,
            "api_server_native_toolsets": [],
        },
        "scribe3_write": {
            "api_server_toolsets": ["scribe3_read", "scribe3_write", "file"],
            "api_server_mcp_tool_count": 56,
            "api_server_native_toolsets": ["file"],
        },
    }

    summary = appmod._summarize_hermes_runtime(
        profiles,
        profile_configs=configs,
        cron={"checked": True, "gateway_running": True, "active_jobs": 1,
              "scribe3_qc": {"present": True, "active": True, "last_status": "ok"}},
    )

    assert summary["chat"]["available"] is True
    assert summary["read"]["available"] is True
    assert summary["read"]["mcp_tool_count"] == 32
    assert summary["read"]["scribe_skill_loaded"] is True
    assert summary["write"]["available"] is False
    assert summary["write"]["mcp_tool_count"] == 56
    assert summary["degraded"]["write_runs"] is True
    assert summary["cron"]["scribe3_qc"]["last_status"] == "ok"
    codes = {issue["code"] for issue in summary["issues"]}
    assert "write_gateway_unavailable" in codes
    assert "write_native_toolsets_enabled" in codes


def test_hermes_cron_status_parses_qc_job_last_status(monkeypatch):
    import scribe3.app as appmod

    class FakeCompleted:
        def __init__(self, stdout):
            self.stdout = stdout
            self.stderr = ""

    def fake_run(cmd, **_kwargs):
        if cmd[-1] == "status":
            return FakeCompleted("""
✓ Gateway is running — cron jobs will fire automatically
  1 active job(s)
""")
        if cmd[-1] == "list":
            return FakeCompleted("""
  dc4bd8e87938 [active]
    Name:      scribe3-体检
    Schedule:  every 360m
    Repeat:    ∞
    Next run:  2026-07-10T06:03:07.173673+08:00
    Deliver:   local
    Script:    scribe3_qc.sh
    Mode:      no-agent (script stdout delivered directly)
    Last run:  2026-07-10T00:03:07.173673+08:00  ok
""")
        raise AssertionError(cmd)

    monkeypatch.setattr(appmod.subprocess if hasattr(appmod, "subprocess") else __import__("subprocess"),
                        "run", fake_run)

    status = appmod._hermes_cron_status("scribe3")

    assert status["checked"] is True
    assert status["gateway_running"] is True
    assert status["active_jobs"] == 1
    assert status["scribe3_qc"] == {"present": True, "active": True, "last_status": "ok"}


def test_ai_runs_runtime_uses_dedicated_write_gateway(monkeypatch):
    import scribe3.app as appmod
    import scribe3.llm as llm

    monkeypatch.setattr(llm, "HERMES_RUNS", "http://127.0.0.1:8644/v1", raising=False)
    monkeypatch.setattr(llm, "HERMES_RUNS_PROFILE", "scribe3_write", raising=False)

    rt = appmod._hermes_runs_runtime()

    assert rt.api_base == "http://127.0.0.1:8644/v1"
    assert rt.profile == "scribe3_write"


def test_ai_runs_endpoints_proxy_runtime_and_stream_approvals(store, monkeypatch):
    import scribe3.app as appmod

    calls = []

    class FakeRuntime:
        approved = threading.Event()

        def create_run(self, input_text, **kwargs):
            calls.append(("create", input_text, kwargs))
            return {"run_id": "run_1", "status": "queued"}

        def run_status(self, run_id, **kwargs):
            calls.append(("status", run_id, kwargs))
            return {"run_id": run_id, "status": "waiting_for_approval"}

        def run_events(self, run_id, **kwargs):
            calls.append(("events", run_id, kwargs))
            def stream():
                yield {
                    "type": "approval.request", "run_id": run_id,
                    "approval_id": "ap_1", "message": "允许写入设定?",
                }
                assert self.approved.wait(1), "批准前 collector 不应自行结束事件流"
                yield {
                    "type": "approval.resolved", "run_id": run_id,
                    "approval_id": "ap_1", "decision": "approve",
                }
                yield {"type": "run.completed", "run_id": run_id}
            return stream()

        def approve_run(self, run_id, approval, **kwargs):
            calls.append(("approve", run_id, approval, kwargs))
            self.approved.set()
            return {"run_id": run_id, "status": "resumed"}

        def stop_run(self, run_id, **kwargs):
            calls.append(("stop", run_id, kwargs))
            return {"run_id": run_id, "status": "stopped"}

    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda: FakeRuntime())
    monkeypatch.setitem(appmod._stores, "book_x", store)
    client = TestClient(appmod.app)

    created = client.post("/ai/runs?work=book_x", json={
        "input": "整理本章设定",
        "instructions": "先核实再写入。",
        "session_id": "ui-session",
        "previous_response_id": "resp_1",
    })
    assert created.status_code == 200
    assert created.json()["run_id"] == "run_1"

    status = client.get("/ai/runs/run_1?work=book_x")
    assert status.json()["status"] == "waiting_for_approval"

    events = client.get("/ai/runs/run_1/events?work=book_x")
    assert events.status_code == 200
    # 审批卡交给浏览器后，该 SSE 必须释放 Hermes 事件流；审批端点会作为
    # 唯一收集者续读工具完成和终态，防止刷新后的旧生成器抢占事件。
    assert '"approval"' in events.text
    assert '"approval_resolved"' not in events.text

    approval = client.post("/ai/runs/run_1/approval?work=book_x", json={
        "approval_id": "ap_1",
        "decision": "approve",
        "message": "同意",
    })
    assert approval.json()["status"] == "resumed"

    stopped = client.post("/ai/runs/run_1/stop?work=book_x")
    assert stopped.json()["status"] == "stopped"

    create_call = calls[0]
    assert create_call[0] == "create"
    assert "work=book_x" in create_call[2]["instructions"]
    assert create_call[2]["session_key"] == "scribe3|work:book_x|runs"
    # Run 创建后服务端 collector 会立即开始消费事件；浏览器随后查询状态的先后由线程
    # 调度决定，不能再用固定索引断言旧的“先 status、后 events”时序。
    assert ("status", "run_1", {"session_key": "scribe3|work:book_x|runs"}) in calls
    assert calls.count(("events", "run_1", {"session_key": "scribe3|work:book_x|runs"})) == 1
    assert (
        "approve",
        "run_1",
        {"approval_id": "ap_1", "choice": "once"},
        {"session_key": "scribe3|work:book_x|runs"},
    ) in calls
    # 首次 events 请求已启动服务端唯一 collector；批准不再重新打开 Hermes
    # event stream，避免刷新后的浏览器流与审批收尾竞争消费者。
    assert ("stop", "run_1", {"session_key": "scribe3|work:book_x|runs"}) in calls


def test_duplicate_approved_run_request_is_idempotent_when_hermes_has_no_pending_approval(store, monkeypatch):
    """刷新/重放的同一作者决定不能被 Hermes 的无待审项响应放大成 502。"""
    import httpx
    import scribe3.app as appmod

    run_id = "run_approval_replay"
    appmod.set_store(store, work="test")
    store.upsert_ai_run_trace(run_id, status="completed", session_key="scribe3|work:test|runs")
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.started", "call_id": "call_replay", "name": "s3_add_character",
        "arguments": '{"oid":"role:重放安全"}',
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.requested", "call_id": "call_replay", "approval_id": "ap_replay",
        "message": "批准写入?新增角色 role:重放安全=重放安全",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.resolved", "call_id": "call_replay", "approval_id": "ap_replay",
        "choice": "once", "source": "user",
    })

    class ReplayRuntime:
        def approve_run(self, *_args, **_kwargs):
            request = httpx.Request("POST", "http://hermes.test/v1/runs/approval")
            response = httpx.Response(400, request=request, json={
                "error": {"code": "approval_not_pending", "message": "already resolved"},
            })
            raise httpx.HTTPStatusError("approval no longer pending", request=request, response=response)

    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda *_args, **_kwargs: ReplayRuntime())
    client = TestClient(appmod.app)

    response = client.post(f"/ai/runs/{run_id}/approval?work=test", json={
        "approval_id": "ap_replay", "decision": "approve",
    })

    assert response.status_code == 200
    assert response.json() == {
        "run_id": run_id,
        "status": "completed",
        "already_resolved": True,
    }


def test_ai_runs_endpoints_persist_run_trace(store, monkeypatch):
    import scribe3.app as appmod

    appmod.set_store(store, work="test")

    class FakeRuntime:
        def create_run(self, input_text, **kwargs):
            return {"run_id": "run_trace_1", "status": "queued"}

        def run_events(self, run_id, **kwargs):
            return iter([
                {"type": "tool.start", "name": "s3_add_fact", "arguments": "{\"oid\":\"fact:x\"}", "call_id": "call_9"},
                {"type": "tool.complete", "call_id": "call_9", "output": "{\"ok\":true}"},
                {"type": "approval.request", "run_id": run_id, "approval_id": "ap_9", "message": "允许写入命题?"},
                {"type": "run.completed", "run_id": run_id,
                 "model": "qwen3.8-max-preview", "usage": {"total_tokens": 77}},
            ])

        def approve_run(self, run_id, approval, **kwargs):
            return {"run_id": run_id, "status": "resumed"}

        def stop_run(self, run_id, **kwargs):
            return {"run_id": run_id, "status": "stopped"}

    monkeypatch.setattr(appmod, "_hermes_runs_runtime", lambda: FakeRuntime())
    client = TestClient(appmod.app)

    created = client.post("/ai/runs?work=test", json={
        "input": "请新增命题",
        "instructions": "先核实再写入",
    })
    assert created.status_code == 200
    assert created.json()["run_id"] == "run_trace_1"

    events = client.get("/ai/runs/run_trace_1/events?work=test")
    assert events.status_code == 200
    approval = client.post("/ai/runs/run_trace_1/approval?work=test", json={
        "approval_id": "ap_9",
        "decision": "approve",
        "message": "同意",
    })
    assert approval.status_code == 200
    stopped = client.post("/ai/runs/run_trace_1/stop?work=test")
    assert stopped.status_code == 200

    trace = store.get_ai_run_trace("run_trace_1")
    assert trace["work"] == "test"
    assert trace["status"] == "stopped"
    assert trace["session_key"] == "scribe3|work:test|runs"
    assert trace["input_text"] == "请新增命题"
    assert trace["tool_calls"][0]["call_id"] == "call_9"
    assert trace["tool_outputs"][0]["call_id"] == "call_9"
    assert trace["approvals"][0]["approval_id"] == "ap_9"
    assert trace["approvals"][1]["decision"] == "approve"
    assert any(
        row.get("source") == "user" and row.get("decision") == "approve"
        for row in trace["approvals"]
    )
    assert trace["usage"]["total_tokens"] == 77
    assert trace["response"]["model"] == "qwen3.8-max-preview"

    trace_resp = client.get("/ai/runs/run_trace_1/trace?work=test")
    assert trace_resp.status_code == 200
    assert trace_resp.json()["run_id"] == "run_trace_1"
    assert trace_resp.json()["tool_outputs"][0]["call_id"] == "call_9"


def test_probe_degraded_disk_still_ok(monkeypatch):
    """U-001 回归:health=degraded 但网关本身在跑(gateway running + api_server connected)
    时 probe 必须判 ok=True,并标 degraded 与原因。

    病史(2026-07-13):Hermes 的 readiness 里 disk 检查报 degraded(实测它测的挂载点与
    本机 df 对不上),导致整个 health.status='degraded' → 旧实现 ok=(status=='ok') 判 False
    → /ai/runtime-status 顶层 ok=False → 前端 ContextInspector 常驻红字「Hermes 离线 ·
    记忆检索不可用」。而主编/写作/记忆检索全部正常——纯误报,且"记忆检索不可用"这句话本身
    也是错的(记忆检索走 scribe3 后端+SurrealDB,与 Hermes 磁盘无关)。
    """
    from scribe3 import hermes_runtime as runtime
    from scribe3.hermes_runtime import HermesAuth, HermesRuntime

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    # 真机结构(Hermes 0.18.2 实测):api_server 在 platforms 下,不是顶层——
    # 首版修复读了顶层(照抄既有测试的简化 fixture),真机仍误判离线,靠重启后实测才发现。
    degraded_health = {
        "status": "degraded",
        "gateway_state": "running",
        "platforms": {"api_server": {"state": "connected"}},
        "readiness": {"status": "degraded", "checks": {
            "gateway": {"status": "ok", "state": "running"},
            "model": {"status": "ok"},
            "disk": {"status": "degraded", "used_percent": 90.0},
        }},
    }

    def fake_get(url, **_kw):
        if url.endswith("/health/detailed"):
            return FakeResp(degraded_health)
        if url.endswith("/v1/capabilities"):
            return FakeResp({"responses_api": True, "chat_completions": True})
        if url.endswith("/v1/skills"):
            return FakeResp({"data": []})
        if url.endswith("/v1/toolsets"):
            return FakeResp({"data": []})
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(runtime.httpx, "get", fake_get)
    rt = HermesRuntime(api_base="http://127.0.0.1:8642/v1", profile="default",
                       auth=HermesAuth(env={"API_SERVER_KEY": "k"}))
    status = rt.probe()

    assert status["ok"] is True, "网关在跑就该判可用,degraded≠离线"
    assert status["degraded"] is True
    assert "disk" in status["degraded_reasons"]


def test_probe_gateway_down_is_not_ok(monkeypatch):
    """反向:网关真的没起来(gateway_state 非 running / api_server 未连)→ ok=False。"""
    from scribe3 import hermes_runtime as runtime
    from scribe3.hermes_runtime import HermesAuth, HermesRuntime

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    def fake_get(url, **_kw):
        if url.endswith("/health/detailed"):
            return FakeResp({"status": "degraded", "gateway_state": "stopped",
                             "api_server": {"state": "disconnected"}})
        if url.endswith("/v1/capabilities"):
            return FakeResp({})
        if url.endswith("/v1/skills") or url.endswith("/v1/toolsets"):
            return FakeResp({"data": []})
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(runtime.httpx, "get", fake_get)
    rt = HermesRuntime(api_base="http://127.0.0.1:8642/v1", profile="default",
                       auth=HermesAuth(env={"API_SERVER_KEY": "k"}))
    assert rt.probe()["ok"] is False
