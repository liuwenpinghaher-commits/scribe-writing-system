"""前端兼容桩(尚未真实化的端点):quality/cost/task/pending-writes + Wave C LLM 桩。"""
from fastapi.testclient import TestClient

from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_remaining_stubs(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        assert c.get(f"/works/{w}/cost", headers=H).json()["cost_usd"] == 0
        assert c.get(f"/works/{w}/quality", headers=H).json() == {}
        assert c.get(f"/works/{w}/quality/history", headers=H).json() == []
        assert c.get(f"/works/{w}/pending-writes", headers=H).json() == []
        assert c.post(f"/works/{w}/proactive-review", headers=H).json()["new_insights"] == 0
        assert c.post(f"/works/{w}/chapters/1/intent-check", headers=H).json()["status"] == "aligned"
        assert c.get(f"/works/{w}/pending-writes").status_code == 401  # 鉴权
    finally:
        app.dependency_overrides.clear()
