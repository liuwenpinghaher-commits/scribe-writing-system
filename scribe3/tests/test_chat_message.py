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


def test_chat_messages_endpoint(store, monkeypatch):
    """GET /chat/messages 回看端点:按章拉取,ts 序列化为字符串。"""
    monkeypatch.setattr(A, "_responses_events", _stub_events("答。"))
    c = _client(store)
    c.post("/chat/write", json={"msg": "问", "chapter": 7})
    data = c.get("/chat/messages", params={"chapter": 7}).json()
    assert [m["role"] for m in data] == ["user", "assistant"]
    assert isinstance(data[0]["ts"], str) and data[0]["ts"]
