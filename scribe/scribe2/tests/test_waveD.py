"""WaveD:流式 SSE —— streamAction 逐字生成 / streamChat 主编对话(mock 流式)。"""
from fastapi.testclient import TestClient

import scribe2.app as appmod
from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_stream_action_sse(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/author-intent", json={"reader_feeling": "苍凉"}, headers=H)
        c.post(f"/works/{w}/characters", json={"name": "渡叔", "voice": "极静"}, headers=H)
        monkeypatch.setattr(appmod, "_complete_stream", lambda prompt, **k: iter(["渡叔", "立于", "船头。"]))
        r = c.post(f"/works/{w}/chapters/1/actions/continue/stream",
                   json={"instruction": "写夜渡", "target_chars": 300}, headers=H)
        assert r.status_code == 200
        body = r.text
        assert "渡叔" in body and "立于" in body          # 逐字 delta
        assert '"done": true' in body or '"done":true' in body
        assert "渡叔立于船头" in body                       # done 事件含完整拼接
    finally:
        app.dependency_overrides.clear()


def test_stream_chat_sse_persists_thread(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.post(f"/works/{w}/characters", json={"name": "沈舟", "motivation": "查父亲沉船真相"}, headers=H)
        monkeypatch.setattr(appmod, "_complete_stream", lambda msg, **k: iter(["沈舟", "动机是查真相。"]))
        r = c.post(f"/works/{w}/chat/stream", json={"message": "沈舟动机?"}, headers=H)
        assert r.status_code == 200
        assert "沈舟" in r.text and "thread_id" in r.text
        # 对话落讨论线程
        assert c.get(f"/works/{w}/threads", headers=H).json()
    finally:
        app.dependency_overrides.clear()
