"""WaveA REST:作品库汇总/章详情/prose(seq)/段落/分支/状态/移动/反馈/删除。"""
from fastapi.testclient import TestClient

from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_waveA_rest_flow(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "九原渡"}, headers=H).json()["work_id"]
        c.post(f"/works/{w}/characters", json={"name": "渡叔", "voice": "极静"}, headers=H)
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        c.put(f"/works/{w}/chapters", json={"seq": 2, "title": "二"}, headers=H)
        c.post(f"/works/{w}/chapters/1/prose", json={"content": "渡叔立于船头。"}, headers=H)
        # 作品库汇总带计数
        summ = c.get("/works", headers=H).json()
        s = next(x for x in summ if x["id"] == w)
        assert s["chapter_count"] == 2 and s["word_count"] == 6 and s["new_insight_count"] == 0
        # 章详情带快照
        ch = c.get(f"/works/{w}/chapters/1", headers=H).json()
        assert ch["seq"] == 1 and len(ch["snapshots"]) == 1
        # 段落重建 + 引用
        c.post(f"/works/{w}/chapters/1/segments/rebuild", headers=H)
        segs = c.get(f"/works/{w}/chapters/1/segments", headers=H).json()
        assert segs and "渡叔" in segs[0]["text"]
        # 状态 + 移动
        c.post(f"/works/{w}/chapters/1/status", json={"status": "done"}, headers=H)
        assert c.get(f"/works/{w}/chapters/1", headers=H).json()["status"] == "done"
        assert c.post(f"/works/{w}/chapters/1/move/down", headers=H).json()["moved"] is True
        # 分支
        c.post(f"/works/{w}/chapters/2/prose", json={"content": "二章定稿。"}, headers=H)
        c.post(f"/works/{w}/chapters/2/branches", json={"label": "走向B", "content": "另一种二章。"}, headers=H)
        labels = {b["label"] for b in c.get(f"/works/{w}/chapters/2/branches", headers=H).json()}
        assert "走向B" in labels
        assert c.post(f"/works/{w}/chapters/2/branches/走向B/merge", headers=H).json()["merged"]
        # 反馈
        assert c.post(f"/works/{w}/chapters/2/feedback", json={"nl_critique": "慢"}, headers=H).json()["feedback_id"]
        # 删除作品
        assert c.delete(f"/works/{w}", headers=H).json()["ok"]
        assert all(x["id"] != w for x in c.get("/works", headers=H).json())
    finally:
        app.dependency_overrides.clear()


def test_save_prose_autosegments(db):
    """存正文即自动分段(否则切「阅读/引用」视图会空,显示'还没有正文')。"""
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H)
        c.post(f"/works/{w}/chapters/1/prose", json={"content": "第一段。\n\n第二段。"}, headers=H)
        segs = c.get(f"/works/{w}/chapters/1/segments", headers=H).json()  # 未显式 rebuild
        assert len(segs) == 2, "存正文应自动分段,无需显式 rebuild"
    finally:
        app.dependency_overrides.clear()
