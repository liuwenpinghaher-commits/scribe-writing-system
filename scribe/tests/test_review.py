"""主动引擎(全文体检)自检:超期伏笔→札记、去重、状态流转。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.foreshadow import ForeshadowStore  # noqa: E402
from scribe_mcp.review import run_proactive_review  # noqa: E402


def _setup():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    db = Database(tmp.name)
    return db, ForeshadowStore(db.conn), db.create_work("u", "书")


def test_overdue_creates_insight_and_dedups():
    db, fs, w = _setup()
    fs.plant(w, "胎记伏笔", foreshadow_chapter=5)         # 第5章埋
    fs.plant(w, "近的伏笔", foreshadow_chapter=80)        # 近期,不超期
    # 当前第 70 章,阈值 50:只有第5章那个超期(70-5=65>=50)
    new1 = run_proactive_review(db, w, current_chapter=70, overdue_threshold=50)
    assert len(new1) == 1, f"应生成 1 条札记,实得 {len(new1)}"
    ins = db.list_proactive_insights(w, "new")
    assert len(ins) == 1 and ins[0]["kind"] == "foreshadow_overdue"
    # 再次体检:同一伏笔不重复刷(去重)
    new2 = run_proactive_review(db, w, current_chapter=72, overdue_threshold=50)
    assert new2 == [], "去重失败,重复生成了札记"


def test_insight_status_flow():
    db, fs, w = _setup()
    fs.plant(w, "x", 1)
    run_proactive_review(db, w, current_chapter=100)
    iid = db.list_proactive_insights(w, "new")[0]["id"]
    db.update_insight_status(iid, "dismissed")
    assert db.list_proactive_insights(w, "new") == []
    assert len(db.list_proactive_insights(w, "dismissed")) == 1


def test_review_all_works():
    from scribe_mcp.review import review_all_works
    db, fs, w1 = _setup()
    w2 = db.create_work("u", "书2")
    db.save_chapter(w1, 100, "x"); db.save_chapter(w2, 100, "y")
    fs.plant(w1, "w1超期伏笔", 1)
    ForeshadowStore(db.conn).plant(w2, "w2超期伏笔", 1)
    res = review_all_works(db)
    assert res.get(w1, 0) == 1 and res.get(w2, 0) == 1, f"两书各应 1 条:{res}"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()
