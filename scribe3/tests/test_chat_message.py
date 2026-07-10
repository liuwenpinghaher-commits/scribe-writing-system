"""北极星方案任务1 · chat_message 会话落库 TDD。

蓝图 §4-② 第1级:POST /chat/write 每轮追加写 user/assistant 两条,
让对话不再是全系统唯一不留痕的环节(目的推导链与纠偏信号的原材料)。
台账:D-002(work 由 store 自动填)/ D-003(assistant 存围栏外散文+提案标记,
不复述提案正文)/ D-004(best-effort,落库失败不断流)/ D-005(GET 版不落库)。
"""
import pytest

import scribe3.app as A

from .test_app import _client


def _stub_events(*texts):
    """伪造 hermes responses 事件流:每个 text 一个 output_text.delta。"""
    def fn(message, instructions, with_tools=True):
        for t in texts:
            yield {"type": "response.output_text.delta", "delta": t}
    return fn


def test_store_add_and_list_chat_messages(store):
    """store 层:追加写 + 按章升序拉取;work 由 store 用自身 db 名自动填,ts 非空。"""
    store.add_chat_message(chapter=3, stage="draft", role="user", text="第一句")
    store.add_chat_message(chapter=3, stage="draft", role="assistant", text="第二句")
    store.add_chat_message(chapter=4, stage="", role="user", text="别章不混入")
    msgs = store.list_chat_messages(chapter=3)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert [m["text"] for m in msgs] == ["第一句", "第二句"]
    assert all(m["work"] == "test" for m in msgs), "work 应由 store 自动填(conftest db=test)"
    assert all(m["chapter"] == 3 for m in msgs)
    assert msgs[0]["stage"] == "draft"
    assert all(m.get("ts") for m in msgs)


def test_store_chat_message_trace_roundtrip(store):
    trace = {
        "response_id": "resp_1",
        "tool_calls": [{"name": "s3_get_chapter", "arguments": "{\"seq\":1}"}],
        "usage": {"input_tokens": 12},
    }
    store.add_chat_message(
        chapter=3,
        stage="draft",
        role="assistant",
        text="答",
        trace=trace,
    )
    msg = store.list_chat_messages(chapter=3)[0]
    assert msg["trace"]["response_id"] == "resp_1"
    assert msg["trace"]["tool_calls"][0]["name"] == "s3_get_chapter"
    assert msg["trace"]["usage"]["input_tokens"] == 12


def test_store_ai_run_trace_roundtrip(store):
    store.upsert_ai_run_trace(
        "run_1",
        status="created",
        session_key="scribe3|work:test|runs",
        input_text="请新增角色",
        instructions="先核实再写入",
    )
    store.append_ai_run_trace_event(
        "run_1",
        {"type": "tool.started", "call_id": "call_1", "name": "s3_add_character", "arguments": "{}"},
    )
    store.append_ai_run_trace_event(
        "run_1",
        {"type": "approval.requested", "approval_id": "ap_1", "message": "允许写入?"},
    )
    store.append_ai_run_trace_event(
        "run_1",
        {"type": "approval.resolved", "approval_id": "ap_1", "decision": "approve"},
    )
    store.upsert_ai_run_trace("run_1", status="completed", usage={"total_tokens": 42})

    trace = store.get_ai_run_trace("run_1")
    assert trace["work"] == "test"
    assert trace["run_id"] == "run_1"
    assert trace["status"] == "completed"
    assert trace["session_key"] == "scribe3|work:test|runs"
    assert trace["input_text"] == "请新增角色"
    assert trace["tool_calls"][0]["call_id"] == "call_1"
    assert trace["approvals"][0]["approval_id"] == "ap_1"
    assert trace["approvals"][1]["decision"] == "approve"
    assert trace["usage"]["total_tokens"] == 42


def test_ai_run_trace_links_write_tool_approval_and_effect(store):
    store.upsert_ai_run_trace(
        "run_write_1",
        status="created",
        session_key="scribe3|work:test|runs",
        input_text="请新增命题",
        instructions="先核实再写入",
    )
    store.append_ai_run_trace_event(
        "run_write_1",
        {
            "kind": "tool.started",
            "call_id": "call_fact_1",
            "name": "s3_add_fact",
            "arguments": (
                '{"oid":"fact:ai_run_trace_fact","entity":"role:甲",'
                '"attribute":"状态","value":"已确认","valid_from":1}'
            ),
        },
    )
    store.append_ai_run_trace_event(
        "run_write_1",
        {
            "kind": "approval.requested",
            "approval_id": "ap_fact_1",
            "message": "允许写入命题?",
        },
    )
    store.append_ai_run_trace_event(
        "run_write_1",
        {
            "kind": "approval.resolved",
            "approval_id": "ap_fact_1",
            "decision": "approve",
        },
    )
    store.append_ai_run_trace_event(
        "run_write_1",
        {
            "kind": "tool.output",
            "call_id": "call_fact_1",
            "output": '{"status":"written","tool":"s3_add_fact"}',
        },
    )

    trace = store.get_ai_run_trace("run_write_1")
    tool_call = trace["tool_calls"][0]
    tool_output = trace["tool_outputs"][0]
    requested, resolved = trace["approvals"]

    assert tool_call["approval_id"] == "ap_fact_1"
    assert requested["call_id"] == "call_fact_1"
    assert resolved["call_id"] == "call_fact_1"
    assert tool_output["tool"] == "s3_add_fact"
    assert tool_output["approval_id"] == "ap_fact_1"
    assert tool_output["decision"] == "approve"
    assert tool_output["result_status"] == "written"
    assert tool_output["write_effect"]["objects"] == [{"type": "fact", "id": "fact:ai_run_trace_fact"}]


def test_ai_run_trace_infers_written_effect_from_real_hermes_empty_tool_output(store):
    store.upsert_ai_run_trace("run_real_shape", status="created")
    store.append_ai_run_trace_event(
        "run_real_shape",
        {
            "kind": "tool.started",
            "run_id": "run_real_shape",
            "name": "s3_add_fact",
            "arguments": "",
            "source_type": "tool.started",
        },
    )
    store.append_ai_run_trace_event(
        "run_real_shape",
        {
            "kind": "approval.requested",
            "run_id": "run_real_shape",
            "message": "批准写入?新增事实 fact:real_empty_output:role:Codex·验收状态=已落库",
            "source_type": "approval.request",
        },
    )
    store.append_ai_run_trace_event(
        "run_real_shape",
        {
            "kind": "approval.resolved",
            "run_id": "run_real_shape",
            "decision": "once",
            "source_type": "approval.responded",
        },
    )
    store.append_ai_run_trace_event(
        "run_real_shape",
        {
            "kind": "tool.output",
            "run_id": "run_real_shape",
            "name": "s3_add_fact",
            "output": "",
            "source_type": "tool.completed",
        },
    )

    trace = store.get_ai_run_trace("run_real_shape")
    tool_output = trace["tool_outputs"][0]
    assert tool_output["tool"] == "s3_add_fact"
    assert tool_output["decision"] == "once"
    assert tool_output["result_status"] == "written"
    assert {"type": "fact", "id": "fact:real_empty_output"} in tool_output["write_effect"]["objects"]


def test_chat_write_post_persists_user_and_assistant(store, monkeypatch):
    """POST /chat/write 一轮 → user+assistant 各一条,章/阶段(phase→stage)正确。"""
    monkeypatch.setattr(A, "_responses_events", _stub_events("好的,", "开头压着写。"))
    r = _client(store).post("/chat/write",
                            json={"msg": "这章开头怎么写", "chapter": 2, "phase": "draft"})
    assert r.status_code == 200
    msgs = store.list_chat_messages(chapter=2)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["text"] == "这章开头怎么写"
    assert msgs[0]["stage"] == "draft"
    assert "开头压着写" in msgs[1]["text"]


def test_chat_write_post_persists_hermes_trace(store, monkeypatch):
    def fake_events(message, instructions, with_tools=True):
        yield {"type": "response.output_item.added",
               "item": {"type": "function_call", "name": "s3_get_chapter",
                        "arguments": "{\"seq\":2}", "call_id": "call_1"}}
        yield {"type": "response.output_item.done",
               "item": {"type": "function_call_output", "call_id": "call_1",
                        "output": "{\"title\":\"第二章\"}"}}
        yield {"type": "response.output_text.delta", "delta": "已查第二章。"}
        yield {"type": "response.completed",
               "response": {"id": "resp_2", "usage": {"input_tokens": 20, "output_tokens": 5}}}

    monkeypatch.setattr(A, "_responses_events", fake_events)
    r = _client(store).post("/chat/write",
                            json={"msg": "查第二章", "chapter": 2, "phase": "draft"})
    assert r.status_code == 200
    assistant = [m for m in store.list_chat_messages(chapter=2) if m["role"] == "assistant"][0]
    trace = assistant["trace"]
    assert trace["status"] == "completed"
    assert trace["response_id"] == "resp_2"
    assert trace["tool_calls"][0]["name"] == "s3_get_chapter"
    assert trace["tool_outputs"][0]["output"] == "{\"title\":\"第二章\"}"
    assert trace["usage"]["output_tokens"] == 5


def test_chat_write_post_streams_approval_events(store, monkeypatch):
    def fake_events(message, instructions, with_tools=True):
        yield {"type": "approval.request", "run_id": "run_1", "approval_id": "ap_1",
               "message": "允许写入设定?"}
        yield {"type": "approval.resolved", "run_id": "run_1", "approval_id": "ap_1",
               "decision": "approve"}
        yield {"type": "response.output_text.delta", "delta": "已继续。"}

    monkeypatch.setattr(A, "_responses_events", fake_events)
    r = _client(store).post("/chat/write", json={"msg": "登记设定", "chapter": 2, "phase": "draft"})
    assert r.status_code == 200
    assert '"approval"' in r.text and "允许写入设定?" in r.text
    assert '"approval_resolved"' in r.text and "approve" in r.text
    assistant = [m for m in store.list_chat_messages(chapter=2) if m["role"] == "assistant"][0]
    assert assistant["trace"]["approvals"][0]["approval_id"] == "ap_1"


def test_chat_write_post_proposal_marker_not_fulltext(store, monkeypatch):
    """assistant 落库:围栏外散文保留,提案正文不复述,只留 ⟦提案 scope=…⟧ 标记(D-003)。"""
    prose = "雨夜他没点灯,摸黑把香插进了炉里。" * 20
    monkeypatch.setattr(A, "_responses_events", _stub_events(
        "我的想法:先冷后热。", f"⟦PROPOSAL scope=chapter⟧{prose}⟦/PROPOSAL⟧", "以上。"))
    _client(store).post("/chat/write", json={"msg": "写这章", "chapter": 5})
    msgs = store.list_chat_messages(chapter=5)
    ats = [m for m in msgs if m["role"] == "assistant"]
    assert len(ats) == 1
    at = ats[0]["text"]
    assert "先冷后热" in at and "以上" in at, "围栏外散文(决策讨论)应完整保留"
    assert "⟦提案 scope=chapter" in at, "应含提案发生标记"
    assert "摸黑把香插进了炉里" not in at, "提案正文不得复述进对话表(与版本库分家)"


def test_chat_write_post_best_effort_on_store_failure(store, monkeypatch):
    """落库炸不断流(D-004 降级路径):add_chat_message 抛异常,SSE 仍完整走到 done。"""
    monkeypatch.setattr(A, "_responses_events", _stub_events("回答。"))

    def boom(*a, **kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(store, "add_chat_message", boom, raising=False)
    r = _client(store).post("/chat/write", json={"msg": "问", "chapter": 1})
    assert r.status_code == 200
    assert '"done": true' in r.text, "落库失败时写作主链路必须不受影响"


def test_chat_write_get_does_not_persist(store, monkeypatch):
    """GET 版是无生产调用方的兼容端点,不落库(D-005)。"""
    monkeypatch.setattr(A, "_responses_events", _stub_events("答"))
    _client(store).get("/chat/write", params={"msg": "问", "chapter": 1})
    assert store.list_chat_messages(chapter=1) == []


def test_turn_id_pairs_user_and_assistant(store, monkeypatch):
    """P0门审查 P2-6:同轮 user/assistant 共享 turn id,并发会话可配对。"""
    monkeypatch.setattr(A, "_responses_events", _stub_events("答。"))
    _client(store).post("/chat/write", json={"msg": "问", "chapter": 9})
    msgs = store.list_chat_messages(chapter=9)
    assert len(msgs) == 2
    assert msgs[0].get("turn") and msgs[0]["turn"] == msgs[1]["turn"], \
        "user 与 assistant 必须共享同一 turn id"


def test_list_chat_messages_limit_takes_latest(store):
    """P0门审查 P2-6:limit 取最新 N 条(升序返回),超量后回看不能只见最老。"""
    for i in range(6):
        store.add_chat_message(chapter=1, stage="", role="user", text=f"m{i}")
    msgs = store.list_chat_messages(chapter=1, limit=2)
    assert [m["text"] for m in msgs] == ["m4", "m5"], "应取最新两条且升序"
    assert store.list_chat_messages(chapter=1, limit=0), "非法 limit 夹取到 1,不 500"


def test_stream_write_on_complete_survives_client_disconnect(monkeypatch):
    """P0门审查 P1-6:客户端断流(GeneratorExit)也要落已累积的半截 assistant 文本。"""
    captured = {}

    def fake_events(msg, instructions, with_tools=True):
        yield {"type": "response.output_text.delta", "delta": "前半"}
        yield {"type": "response.output_text.delta", "delta": "后半"}

    monkeypatch.setattr(A, "_responses_events", fake_events)
    gen = A._stream_write("msg", "instr", on_complete=lambda t: captured.update(text=t))
    next(gen)          # 客户端只收到第一帧
    gen.close()        # 断开:Starlette 语义 = 在 yield 点抛 GeneratorExit
    assert captured.get("text") == "前半", "断流也须留痕半截文本(finally 落库)"


def test_chat_messages_endpoint(store, monkeypatch):
    """GET /chat/messages 回看端点:按章拉取,ts 序列化为字符串。"""
    monkeypatch.setattr(A, "_responses_events", _stub_events("答。"))
    c = _client(store)
    c.post("/chat/write", json={"msg": "问", "chapter": 7})
    data = c.get("/chat/messages", params={"chapter": 7}).json()
    assert [m["role"] for m in data] == ["user", "assistant"]
    assert isinstance(data[0]["ts"], str) and data[0]["ts"]
