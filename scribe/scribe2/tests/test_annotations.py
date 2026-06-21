"""划词交互后端:批注(annotation)+ 高亮(highlight)CRUD + 段级改写(passage-rewrite)。
都锚在选中文字 quote 上。"""
from fastapi.testclient import TestClient

import scribe2.app as appmod
from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_annotation_crud(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        aid = c.post(f"/works/{w}/chapters/1/annotations",
                     json={"quote": "渡叔立于船头", "note": "这里呼应第3章伏笔", "target": "self"},
                     headers=H).json()["annotation_id"]
        assert aid
        # 按章列 + 全书列(侧栏)
        ch_ann = c.get(f"/works/{w}/chapters/1/annotations", headers=H).json()
        assert len(ch_ann) == 1 and ch_ann[0]["note"] == "这里呼应第3章伏笔"
        assert ch_ann[0]["quote"] == "渡叔立于船头" and ch_ann[0]["seq"] == 1
        all_ann = c.get(f"/works/{w}/annotations", headers=H).json()
        assert len(all_ann) == 1
        # 删
        assert c.delete(f"/works/{w}/annotations/{aid}", headers=H).json()["ok"]
        assert c.get(f"/works/{w}/chapters/1/annotations", headers=H).json() == []
    finally:
        app.dependency_overrides.clear()


def test_highlight_crud(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        hid = c.post(f"/works/{w}/chapters/1/highlights",
                     json={"quote": "白碴树干戳着灰天", "color": "amber"}, headers=H).json()["highlight_id"]
        hl = c.get(f"/works/{w}/chapters/1/highlights", headers=H).json()
        assert len(hl) == 1 and hl[0]["color"] == "amber" and hl[0]["quote"] == "白碴树干戳着灰天"
        assert c.delete(f"/works/{w}/highlights/{hid}", headers=H).json()["ok"]
        assert c.get(f"/works/{w}/chapters/1/highlights", headers=H).json() == []
    finally:
        app.dependency_overrides.clear()


def test_rewrite_passage(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/author-intent", json={"reader_feeling": "苍凉"}, headers=H)
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        c.post(f"/works/{w}/chapters/1/prose", json={"content": "渡叔笑了笑，嘴角勾起一抹弧度。"}, headers=H)
        # 主编只重写选中段(mock Hermes)
        monkeypatch.setattr(appmod, "_complete", lambda *a, **k: "渡叔没笑。")
        r = c.post(f"/works/{w}/chapters/1/rewrite-passage",
                   json={"passage": "渡叔笑了笑，嘴角勾起一抹弧度。", "instruction": "去掉AI腔，更冷"},
                   headers=H)
        assert r.status_code == 200
        assert r.json()["rewritten"] == "渡叔没笑。"
    finally:
        app.dependency_overrides.clear()
