"""主编 agentic:streamChat 走 /v1/responses,主编调 scribe2 MCP 工具。
mock responses 事件流,验证 SSE 吐 tool(工具调用)+delta(回复)+done,且落讨论线程。
"""
from fastapi.testclient import TestClient

import scribe2.app as appmod
from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_chat_stream_agentic_emits_tool_then_reply_and_persists(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "雾港迷案"}, headers=H).json()["work_id"]
        c.post(f"/works/{w}/characters", json={"name": "沈舟", "motivation": "查父亲沉船真相"}, headers=H)
        # mock:主编先调 list_characters 工具,再流式回答(OpenAI Responses 标准事件)
        events = [
            {"type": "response.output_item.added",
             "item": {"type": "function_call", "name": "list_characters", "arguments": "{}"}},
            {"type": "response.output_text.delta", "delta": "沈舟的动机"},
            {"type": "response.output_text.delta", "delta": "是查父亲沉船的真相。"},
        ]
        monkeypatch.setattr(appmod, "_responses_events",
                            lambda message, instructions, model=None: iter(events))
        r = c.post(f"/works/{w}/chat/stream", json={"message": "沈舟动机?"}, headers=H)
        assert r.status_code == 200
        body = r.text
        assert "list_characters" in body                 # 主编调了 scribe2 工具
        assert '"tool"' in body                            # 工具事件
        assert "沈舟的动机是查父亲沉船的真相" in body       # 流式回复拼接
        assert "thread_id" in body                         # done 事件
        # 对话落讨论线程
        assert c.get(f"/works/{w}/threads", headers=H).json()
    finally:
        app.dependency_overrides.clear()
