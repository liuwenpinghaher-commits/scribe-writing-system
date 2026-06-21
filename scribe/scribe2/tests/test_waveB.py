"""WaveB:编辑功能 CRUD(札记/方案/议题/素材/想象/偏好/agent记忆技能/关系/角色状态/时间线/卷)。"""
from fastapi.testclient import TestClient

from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_waveB_editorial_crud(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "九原渡"}, headers=H).json()["work_id"]
        # 札记
        iid = d.add_insight(w, "渡叔动机前后矛盾", "去第3章核对", "warning")
        ins = c.get(f"/works/{w}/insights", headers=H).json()
        assert any(x["summary"] == "渡叔动机前后矛盾" for x in ins)
        c.post(f"/works/{w}/insights/{iid}/ack", headers=H)
        assert all(x["summary"] != "渡叔动机前后矛盾" for x in c.get(f"/works/{w}/insights", headers=H).json())
        # 方案
        oid = d.add_option_set(w, {"text": "阿砚该不该破例"}, [{"id": "a", "approach": "破"}, {"id": "b", "approach": "守"}])
        assert len(c.get(f"/works/{w}/option-sets", headers=H).json()) == 1
        c.post(f"/works/{w}/option-sets/{oid}/choose", json={"chosen_option_id": "a"}, headers=H)
        assert c.get(f"/works/{w}/option-sets", headers=H).json() == []  # chosen → 不再待决
        # 议题
        d.add_thread(w, "一致性预警", "渡叔年龄")
        th = c.get(f"/works/{w}/threads?status=open", headers=H).json()
        assert th and th[0]["trigger"] == "一致性预警"
        c.post(f"/works/{w}/threads/{d._idpart(th[0]['id'])}/resolve", headers=H)
        assert c.get(f"/works/{w}/threads?status=open", headers=H).json() == []
        # 素材
        mid = c.post(f"/works/{w}/materials", json={"content": "明代渡口考据", "type": "reference"}, headers=H).json()["material_id"]
        assert any(m.get("content") == "明代渡口考据" for m in c.get(f"/works/{w}/materials", headers=H).json())
        c.delete(f"/works/{w}/materials/{mid}", headers=H)
        assert c.get(f"/works/{w}/materials", headers=H).json() == []
        # 想象
        c.post(f"/works/{w}/imaginations", json={"raw_text": "让小满最后开口"}, headers=H)
        imgs = c.get(f"/works/{w}/imaginations", headers=H).json()
        assert imgs and imgs[0]["raw_text"] == "让小满最后开口"
        c.post(f"/works/{w}/imaginations/{d._idpart(imgs[0]['id'])}/status/used", headers=H)
        # 偏好
        assert c.post(f"/works/{w}/preference", json={"source": "intentional", "polarity": "+"}, headers=H).json()["signal_id"]
        # agent 记忆 + 技能
        c.post(f"/works/{w}/agent-memory", json={"namespace": "style", "key": "tone", "value": {"x": 1}, "scope": "work"}, headers=H)
        assert c.get(f"/works/{w}/agent-memory", headers=H).json()
        sid = c.post(f"/works/{w}/agent-skills", json={"name": "查伏笔", "spec": {"steps": []}}, headers=H).json()["skill_id"]
        assert c.post(f"/works/{w}/agent-skills/{sid}/approve", headers=H).json()["status"] == "approved"
        # 关系 + 角色状态 + 时间线
        d.add_relation(w, "阿砚", "渡叔", "师徒", valid_from_chapter=2)
        assert c.get(f"/works/{w}/relations", headers=H).json()
        d.add_char_state(w, "阿砚", 1, "逃难少年", "出场")
        assert c.get(f"/works/{w}/characters/阿砚/states", headers=H).json()[0]["state_desc"] == "逃难少年"
        d.add_timeline_event(w, 1, "阿砚至渡口")
        assert c.get(f"/works/{w}/timeline", headers=H).json()[0]["description"] == "阿砚至渡口"
        # 卷
        c.post(f"/works/{w}/volumes", json={"seq": 1, "title": "立渡"}, headers=H)
        assert any(v.get("title") == "立渡" for v in c.get(f"/works/{w}/volumes", headers=H).json())
        # 作品库汇总:待决方案计数(此时方案已选,应为0)
        s = next(x for x in c.get("/works", headers=H).json() if x["id"] == w)
        assert s["pending_optionset_count"] == 0
    finally:
        app.dependency_overrides.clear()
