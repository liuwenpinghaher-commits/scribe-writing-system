"""WaveC:质量聚合/成本/impact/任务态(非LLM)+ LLM 编辑功能(mock _complete)。"""
from fastapi.testclient import TestClient

import scribe2.app as appmod
from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_quality_cost_impact_task(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "九原渡"}, headers=H).json()["work_id"]
        c.post(f"/works/{w}/characters", json={"name": "渡叔"}, headers=H)
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        c.post(f"/works/{w}/chapters/1/prose", json={"content": "渡叔立于船头,独眼望浊浪。"}, headers=H)
        d.plant_foreshadow(w, "长明灯灭", 1, "high")
        # 质量
        q = c.get(f"/works/{w}/quality", headers=H).json()
        assert q["chapters"] == 1 and q["words"] == 11 and q["foreshadow"]["planted"] == 1
        assert "consistency" in q and "cost" in q
        # impact(章节提及渡叔)
        imp = c.get(f"/works/{w}/impact?name=渡叔", headers=H).json()
        assert imp and imp[0]["seq"] == 1
        # 成本账本
        d.record_cost(w, 1000, 0.002)
        assert c.get(f"/works/{w}/cost", headers=H).json()["tokens"] == 1000
        # 质量历史
        d.snapshot_quality(w)
        assert c.get(f"/works/{w}/quality/history", headers=H).json()
        # 任务态状态机
        t = c.get(f"/works/{w}/chapters/1/task", headers=H).json()
        assert t["status"] == "PLANNING" and "AWAITING_OUTLINE_CHOICE" in t["next"]
        t2 = c.post(f"/works/{w}/chapters/1/task/advance", json={"to": "AWAITING_OUTLINE_CHOICE"}, headers=H).json()
        assert t2["status"] == "AWAITING_OUTLINE_CHOICE"
        # 非法转移 400
        assert c.post(f"/works/{w}/chapters/1/task/advance", json={"to": "DONE"}, headers=H).status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_llm_editorial(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/author-intent", json={"reader_feeling": "苍凉", "red_lines": ["不煽情"]}, headers=H)
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        c.post(f"/works/{w}/chapters/1/prose", json={"content": "渡叔立于船头。"}, headers=H)
        # intent-check
        monkeypatch.setattr(appmod, "_complete",
                            lambda p, **k: '{"status":"soft_deviation","reason":"略平","red_lines":[]}')
        v = c.post(f"/works/{w}/chapters/1/intent-check", headers=H).json()
        assert v["status"] == "soft_deviation"
        # proactive-review → 生札记
        monkeypatch.setattr(appmod, "_complete",
                            lambda p, **k: '{"insights":[{"summary":"节奏偏慢","suggested_action":"删冗句","severity":"warning"}]}')
        assert c.post(f"/works/{w}/proactive-review", headers=H).json()["new_insights"] == 1
        assert any(x["summary"] == "节奏偏慢" for x in c.get(f"/works/{w}/insights", headers=H).json())
        # generate-options → 方案
        monkeypatch.setattr(appmod, "_complete",
                            lambda p, **k: '{"options":[{"id":"a","approach":"破例"},{"id":"b","approach":"守规"}]}')
        oid = c.post(f"/works/{w}/option-sets/generate", json={"decision_point": "破不破例", "n": 2}, headers=H).json()["option_set_id"]
        assert oid and len(c.get(f"/works/{w}/option-sets", headers=H).json()) == 1
        # analyze → 关系/事件/状态
        monkeypatch.setattr(appmod, "_complete",
                            lambda p, **k: '{"relations":[{"src":"阿砚","dst":"渡叔","relation":"师徒"}],"events":["拜师"],"states":[{"character":"阿砚","state_desc":"入门","change_type":"转变"}]}')
        a = c.post(f"/works/{w}/analyze", headers=H).json()
        assert a["relations"] == 1 and a["events"] == 1 and a["states"] == 1
        assert c.get(f"/works/{w}/relations", headers=H).json()
    finally:
        app.dependency_overrides.clear()
