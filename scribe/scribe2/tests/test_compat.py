"""Build4 前端兼容层:外围桩端点 200+空(前端切 scribe2 不 404);volumes 真实。"""
from fastapi.testclient import TestClient

from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_compat_stubs_and_volumes(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        # 外围列表桩 → 200 + 空
        for ep in ["insights", "option-sets", "threads", "materials",
                   "imaginations", "relations", "timeline", "agent-memory"]:
            r = c.get(f"/works/{w}/{ep}", headers=H)
            assert r.status_code == 200 and r.json() == [], ep
        # 对象桩
        assert c.get(f"/works/{w}/cost", headers=H).json()["cost_usd"] == 0
        assert c.post(f"/works/{w}/proactive-review", headers=H).json()["new_insights"] == 0
        # volumes 真实
        c.post(f"/works/{w}/volumes", json={"seq": 1, "title": "上卷"}, headers=H)
        vols = c.get(f"/works/{w}/volumes", headers=H).json()
        assert any(v.get("title") == "上卷" for v in vols)
        # 鉴权仍生效
        assert c.get(f"/works/{w}/insights").status_code == 401
    finally:
        app.dependency_overrides.clear()
