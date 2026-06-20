from fastapi.testclient import TestClient
from scribe2.app import app, get_domain
from scribe2.conn import domain_from

def test_core_rest_flow(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    c = TestClient(app); H = {"X-Owner-Id": "u1"}
    w = c.post("/works", json={"title": "雨夜"}, headers=H).json()["work_id"]
    assert c.get("/works", headers=H).json()[0]["title"] == "雨夜"
    ch = c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H).json()["chapter_id"]
    c.post(f"/works/{w}/chapters/{ch}/prose", json={"content": "雨夜。", "lock": True}, headers=H)
    c.post(f"/works/{w}/settings", json={"name": "断魂剑", "desc": "失忆古剑"}, headers=H)
    hits = c.post(f"/works/{w}/search", json={"query": "失忆的剑", "k": 3}, headers=H).json()
    assert any("断魂剑" in (h.get("text") or "") for h in hits)
    assert c.get("/works").status_code == 401  # 无 owner 头
    app.dependency_overrides.clear()
