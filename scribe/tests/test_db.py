"""Scribe 数据层自检(纯 stdlib,可直接 `python tests/test_db.py` 或 pytest)。

覆盖 Batch 0 关键不变量:CRUD、章节 upsert、想象状态、多本书隔离(防串味)、human-lock 写保护(工程9)。
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def _fresh_db() -> Database:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return Database(tmp.name)


def test_work_crud_and_intent():
    db = _fresh_db()
    wid = db.create_work("user-1", "测试书", premise="一个关于背叛的故事", genre="悬疑")
    w = db.get_work(wid)
    assert w and w["title"] == "测试书" and w["owner_id"] == "user-1"
    db.set_author_intent(wid, reader_feeling="让读者在结尾脊背发凉",
                         do_not_betray=["主角不能突然圣母"])
    intent = db.get_author_intent(wid)
    assert intent and "脊背发凉" in intent["reader_feeling"]
    assert "圣母" in intent["do_not_betray"]


def test_chapter_upsert():
    db = _fresh_db()
    wid = db.create_work("u", "书")
    c1 = db.save_chapter(wid, 1, title="第一章", outline={"events": ["开场"]})
    c2 = db.save_chapter(wid, 1, title="第一章(改)", outline={"events": ["新开场"]})
    assert c1 == c2, "同 work+seq 必须 upsert 到同一行"
    ch = db.get_chapter(wid, 1)
    assert ch["title"] == "第一章(改)"


def test_imagination_capture():
    db = _fresh_db()
    wid = db.create_work("u", "书")
    db.capture_imagination(wid, "我想要一场雨夜的背叛", type_="scene_wish")
    items = db.list_imaginations(wid, status="captured")
    assert len(items) == 1 and items[0]["raw_text"] == "我想要一场雨夜的背叛"


def test_multi_book_isolation():
    """多本书:A 书设定绝不出现在 B 书(00 §2.7,防串味,硬门 11b)。"""
    db = _fresh_db()
    a = db.create_work("u", "A书")
    b = db.create_work("u", "B书")
    db.upsert_setting(a, "term", "魔法体系", {"desc": "源石"})
    db.upsert_setting(b, "term", "科技体系", {"desc": "曲速"})
    a_settings = {s["name"] for s in db.list_settings(a)}
    b_settings = {s["name"] for s in db.list_settings(b)}
    assert a_settings == {"魔法体系"}
    assert b_settings == {"科技体系"}
    assert "魔法体系" not in b_settings, "串味!A 书设定泄漏到 B 书"
    # 同 owner 能看到两本书
    assert {w["title"] for w in db.list_works("u")} == {"A书", "B书"}


def test_human_lock_protects_manuscript():
    """工程9:AI 不能覆盖 human-locked 的 human-final 分支。"""
    db = _fresh_db()
    wid = db.create_work("u", "书")
    cid = db.save_chapter(wid, 1)
    snap = db.save_snapshot(wid, cid, "作者定稿的正文", created_by="human",
                            branch_label="human-final")
    db.lock_snapshot(snap)
    # AI 可以开 ai-draft 平行分支
    db.save_snapshot(wid, cid, "AI 的新草稿", created_by="ai", branch_label="ai-draft")
    # 但 AI 不能写 human-final
    try:
        db.save_snapshot(wid, cid, "AI 想覆盖定稿", created_by="ai", branch_label="human-final")
        raise AssertionError("AI 竟然写入了 human-final —— 手稿保护失效!")
    except PermissionError:
        pass
    branches = {s["branch_label"] for s in db.list_snapshots(cid)}
    assert branches == {"human-final", "ai-draft"}


def test_pending_writes_queue_roundtrip(tmp_path):
    from scribe_mcp.db import Database
    db = Database(str(tmp_path / "t.db"))
    wid = db.create_work("u1", "书")
    pid = db.enqueue_pending_write(wid, "upsert_setting",
                                   {"work_id": wid, "type": "character", "name": "沈舟", "content": {"k": "v"}})
    assert pid
    pend = db.list_pending_writes(wid, "pending")
    assert len(pend) == 1
    row = pend[0]
    assert row["tool_name"] == "upsert_setting"
    assert row["args"] == {"work_id": wid, "type": "character", "name": "沈舟", "content": {"k": "v"}}
    assert row["status"] == "pending"
    one = db.get_pending_write(pid)
    assert one["id"] == pid and one["args"]["name"] == "沈舟"
    db.mark_pending_decided(pid, "approved", {"setting_id": "s1"})
    assert db.list_pending_writes(wid, "pending") == []
    done = db.get_pending_write(pid)
    assert done["status"] == "approved" and done["result"] == {"setting_id": "s1"}
    assert done["decided_at"]


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()
