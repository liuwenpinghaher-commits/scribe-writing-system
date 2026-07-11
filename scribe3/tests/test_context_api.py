"""统一上下文与记忆系统 · Task 4:Context API + chat revision 绑定 TDD。

契约:
- POST /context/sessions:开会话并返回 revision=0 初始快照(work 固化进 session);
- GET /context/sessions/{id}:当前快照;
- POST /context/sessions/{id}/navigate:CAS 推进,失配 409 stale_context(带 latest);
- GET /context/sessions/{id}/snapshots/{revision}:历史版;
- POST /chat/write:SCRIBE3_CONTEXT_SNAPSHOT_V1 开关开时强制 context 绑定
  (缺失 400 / 过期 409 / 跨 work 409);开关关时旧调用方行为零变化。
"""
from types import SimpleNamespace

import pytest

import scribe3.app as A

from .test_app import _client


def _stub_events(*texts):
    """伪造 hermes responses 事件流(测试绝不真调 LLM)。"""
    def fn(message, instructions, with_tools=True, **kwargs):
        for t in texts:
            yield {"type": "response.output_text.delta", "delta": t}
    return fn


def _nav_payload(revision=0, nav_id="nav-1"):
    """NavigationIntent 的 model_dump 形状(navigate 端点 body)。"""
    return {
        "navigation_id": nav_id,
        "expected_revision": revision,
        "entry": "manuscript",
        "directory_path": ["manuscript", "chapter:3"],
        "focus": {"type": "chapter", "id": "chapter:3", "label": "第三章"},
        "detail_route": "chapter:3",
        "chapter": 3,
        "phase": "draft",
        "focalizer": None,
        "reason": "item",
    }


# I-2:两条 409 stale 路径(navigate / chat enforce)的 latest 必须同形同源——
# store 原始快照行的完整字段集(含模型外的 reason 与库内 ISO 串 captured_at)
_SNAPSHOT_FIELDS = {
    "session_id", "work", "revision", "previous_revision", "navigation_id",
    "thread_id", "entry", "directory_path", "focus", "detail_route",
    "chapter", "phase", "focalizer", "reason", "context_hash", "captured_at",
}


def _session(store, work="main"):
    """建会话并返回带属性访问的小对象(计划测试用 context_session.id 写法)。"""
    snap = store.create_context_session(work, "author:me", "device:test")
    return SimpleNamespace(id=snap["session_id"], thread_id=snap["thread_id"],
                           revision=snap["revision"], context_hash=snap["context_hash"],
                           work=snap["work"], snapshot=snap)


@pytest.fixture()
def context_session(store):
    """work=main 的上下文会话(store 已注入 A)。"""
    A.set_store(store)
    return _session(store, "main")


# ---------------- Context 会话端点 ----------------

def test_create_context_session_returns_initial_snapshot(store):
    c = _client(store)
    r = c.post("/context/sessions?work=main",
               json={"actor_id": "author:me", "device_id": "device:test"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"session_id", "work", "revision", "thread_id", "entry",
                         "directory_path", "focus", "detail_route", "context_hash"}
    assert body["work"] == "main" and body["revision"] == 0
    assert len(body["context_hash"]) == 64


def test_get_context_session_current_snapshot(store, context_session):
    c = _client(store)
    r = c.get(f"/context/sessions/{context_session.id}?work=main")
    assert r.status_code == 200
    assert r.json()["session_id"] == context_session.id
    assert r.json()["revision"] == 0


def test_get_context_session_not_found_404(store):
    c = _client(store)
    r = c.get("/context/sessions/no-such-session?work=main")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "context_session_not_found"


def test_navigation_returns_complete_snapshot(store, context_session):
    client = _client(store)
    response = client.post(f"/context/sessions/{context_session.id}/navigate?work=main",
                           json=_nav_payload())
    assert response.status_code == 200
    assert set(response.json()) >= {"entry", "directory_path", "focus", "detail_route",
                                    "thread_id", "revision", "context_hash"}
    assert response.json()["revision"] == 1
    assert response.json()["focus"]["id"] == "chapter:3"


def test_navigation_stale_revision_409_with_latest(store, context_session):
    c = _client(store)
    assert c.post(f"/context/sessions/{context_session.id}/navigate?work=main",
                  json=_nav_payload(revision=0, nav_id="nav-1")).status_code == 200
    r = c.post(f"/context/sessions/{context_session.id}/navigate?work=main",
               json=_nav_payload(revision=0, nav_id="nav-2"))
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["code"] == "stale_context"
    assert detail["expected"] == 0 and detail["actual"] == 1
    assert detail["latest"]["revision"] == 1
    assert set(detail["latest"]) >= _SNAPSHOT_FIELDS   # I-2:latest 形状钉死


def test_navigation_ended_session_409(store, context_session):
    """ended 守卫的 API 面:已结束会话 navigate → 409 context_session_ended
    (end 方法由后续任务建,先手工置状态——与 test_context_store 同手法)。"""
    store._raw_query(
        "UPDATE type::record('context_session', $sid) SET status='ended'",
        {"sid": context_session.id})
    c = _client(store)
    r = c.post(f"/context/sessions/{context_session.id}/navigate?work=main",
               json=_nav_payload())
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "context_session_ended"


def test_navigation_unknown_session_404(store):
    c = _client(store)
    r = c.post("/context/sessions/no-such-session/navigate?work=main", json=_nav_payload())
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "context_session_not_found"


def test_get_snapshot_by_revision(store, context_session):
    c = _client(store)
    c.post(f"/context/sessions/{context_session.id}/navigate?work=main", json=_nav_payload())
    r0 = c.get(f"/context/sessions/{context_session.id}/snapshots/0?work=main")
    assert r0.status_code == 200 and r0.json()["revision"] == 0
    r9 = c.get(f"/context/sessions/{context_session.id}/snapshots/9?work=main")
    assert r9.status_code == 404
    assert r9.json()["detail"]["code"] == "context_snapshot_not_found"


def test_context_endpoints_reject_work_mismatch(store):
    """work 绑定校验(Task 16 语义前置):以 session 落库 work 为准,请求不符 409。"""
    A.set_store(store)              # 同一 store 注入两个 work 槽位,模拟跨书访问
    A.set_store(store, "book-a")
    sess = _session(store, "book-a")
    c = _client(store)
    r_get = c.get(f"/context/sessions/{sess.id}?work=main")
    assert r_get.status_code == 409
    assert r_get.json()["detail"]["code"] == "context_work_mismatch"
    r_nav = c.post(f"/context/sessions/{sess.id}/navigate?work=main", json=_nav_payload())
    assert r_nav.status_code == 409
    assert r_nav.json()["detail"]["code"] == "context_work_mismatch"


# ---------------- chat 绑定强校验(开关门控) ----------------

def test_chat_write_rejects_stale_context(store, context_session, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("不应到达。"))
    response = _client(store).post("/chat/write?work=main", json={
        "msg": "续写", "chapter": 3, "phase": "draft",
        "context_session_id": context_session.id,
        "context_revision": 0,
        "context_hash": "o" * 64,   # 模型约束 min_length=64,用 64 位假 hash 表达"过期"
        "thread_id": context_session.thread_id,
    })
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "stale_context"
    assert detail["latest"]["revision"] == 0
    # I-2:chat 路径的 latest 与 navigate 路径同形(store 原始行,含 reason)
    assert set(detail["latest"]) >= _SNAPSHOT_FIELDS
    # 被拦在流开始之前:user 消息不落库(enforce 在 add_chat_message 之前)
    assert store.list_chat_messages(chapter=3) == []


def test_chat_write_rejects_stale_revision(store, context_session, monkeypatch):
    """revision 落后(会话已被 navigate 推进)→ 409,latest 带最新快照供前端对齐。"""
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("不应到达。"))
    store.advance_context(context_session.id, _nav_payload(revision=0))
    r = _client(store).post("/chat/write?work=main", json={
        "msg": "续写", "chapter": 3, "phase": "draft",
        "context_session_id": context_session.id,
        "context_revision": 0,
        "context_hash": context_session.context_hash,   # 旧 revision 的真 hash
        "thread_id": context_session.thread_id,
    })
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["code"] == "stale_context" and detail["latest"]["revision"] == 1


def test_chat_write_requires_binding_when_flag_on(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("不应到达。"))
    r = _client(store).post("/chat/write?work=main", json={"msg": "续写", "chapter": 3})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "context_binding_required"


def test_chat_write_partial_binding_400(store, context_session, monkeypatch):
    """三件套部分缺失(只给 session_id,body/header 均无 revision+hash)→ 同样 400。"""
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("不应到达。"))
    r = _client(store).post("/chat/write?work=main", json={
        "msg": "续写", "chapter": 3,
        "context_session_id": context_session.id,
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "context_binding_required"


def test_chat_write_header_channel_passes(store, context_session, monkeypatch):
    """I-1:api.js contextHeaders 通道——只带请求头(不带 body 字段)绑定当前快照 → 通过。"""
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("头通道,", "照常写。"))
    r = _client(store).post(
        "/chat/write?work=main",
        json={"msg": "续写", "chapter": 3, "phase": "draft"},
        headers={
            "X-Scribe-Context-Session": context_session.id,
            "X-Scribe-Context-Revision": str(context_session.revision),
            "X-Scribe-Context-Hash": context_session.context_hash,
        })
    assert r.status_code == 200
    assert "照常写" in r.text


def test_chat_write_header_channel_rejects_stale(store, context_session, monkeypatch):
    """I-1:头通道同样受过期校验——假 hash → 409 stale_context(校验不因通道而异)。"""
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("不应到达。"))
    r = _client(store).post(
        "/chat/write?work=main",
        json={"msg": "续写", "chapter": 3},
        headers={
            "X-Scribe-Context-Session": context_session.id,
            "X-Scribe-Context-Revision": "0",
            "X-Scribe-Context-Hash": "o" * 64,
        })
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "stale_context"


def test_chat_write_rejects_work_mismatch(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("不应到达。"))
    A.set_store(store)
    A.set_store(store, "book-a")
    sess = _session(store, "book-a")
    r = _client(store).post("/chat/write?work=main", json={
        "msg": "续写", "chapter": 3, "phase": "draft",
        "context_session_id": sess.id,
        "context_revision": 0,
        "context_hash": sess.context_hash,
        "thread_id": sess.thread_id,
    })
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "context_work_mismatch"


def test_chat_write_unknown_session_404_when_flag_on(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("不应到达。"))
    r = _client(store).post("/chat/write?work=main", json={
        "msg": "续写", "chapter": 3,
        "context_session_id": "no-such-session",
        "context_revision": 0,
        "context_hash": "o" * 64,
    })
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "context_session_not_found"


def test_chat_write_current_binding_passes(store, context_session, monkeypatch):
    """带最新 revision+hash → 正常走流式写作(200 且流有内容)。"""
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "true")
    monkeypatch.setattr(A, "_responses_events", _stub_events("好的,", "接着写。"))
    r = _client(store).post("/chat/write?work=main", json={
        "msg": "续写", "chapter": 3, "phase": "draft",
        "context_session_id": context_session.id,
        "context_revision": context_session.revision,
        "context_hash": context_session.context_hash,
        "thread_id": context_session.thread_id,
    })
    assert r.status_code == 200
    assert "接着写" in r.text


def test_chat_write_legacy_request_unaffected_when_flag_off(store, monkeypatch):
    """开关关(默认):不带 context 字段的旧请求完全不受影响——现有调用方零变化。"""
    monkeypatch.delenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", raising=False)
    monkeypatch.setattr(A, "_responses_events", _stub_events("旧调用方", "照常工作。"))
    r = _client(store).post("/chat/write?work=main",
                            json={"msg": "续写", "chapter": 2, "phase": "draft"})
    assert r.status_code == 200
    assert "照常工作" in r.text


def test_chat_write_flag_off_ignores_stale_fields(store, context_session, monkeypatch):
    """开关关时即便带了过期 context 字段也不校验(门控语义:关=完全不碰)。"""
    monkeypatch.delenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", raising=False)
    monkeypatch.setattr(A, "_responses_events", _stub_events("不校验,", "照常写。"))
    r = _client(store).post("/chat/write?work=main", json={
        "msg": "续写", "chapter": 3,
        "context_session_id": context_session.id,
        "context_revision": 0,
        "context_hash": "o" * 64,
    })
    assert r.status_code == 200
    assert "照常写" in r.text


def test_context_write_routes_registered_in_write_gate():
    """写路由审计门镜像(P02):context 写端点必须登记 KNOWN_REST_WRITE_ROUTES。"""
    from .test_consistency import TestWriteGate
    known = TestWriteGate.KNOWN_REST_WRITE_ROUTES
    assert ("POST", "/context/sessions") in known
    assert ("POST", "/context/sessions/{session_id}/navigate") in known
