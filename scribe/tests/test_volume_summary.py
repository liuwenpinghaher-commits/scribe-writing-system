"""P0-1 卷层级 + P0-6 作品库汇总 自检。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def _db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    return Database(tmp.name)


def test_volume_and_chapter_assignment():
    db = _db()
    w = db.create_work("u", "书")
    v1 = db.create_volume(w, 1, "第一卷", "立人设")
    db.create_volume(w, 1, "第一卷(改)")  # upsert by work+seq
    vols = db.list_volumes(w)
    assert len(vols) == 1 and vols[0]["title"] == "第一卷(改)"
    cid = db.save_chapter(w, 1, "第一章", volume_id=v1)
    ch = db.get_chapter(w, 1)
    assert ch["volume_id"] == v1
    assert db.list_chapters(w)[0]["volume_id"] == v1


def test_work_summary_counts():
    db = _db()
    a = db.create_work("u", "A"); db.create_work("u", "B")
    db.save_chapter(a, 1, "一"); db.save_chapter(a, 2, "二")
    db.add_proactive_insight(a, "foreshadow_overdue", "x")
    db.create_option_set(a, "走向", [{"id": "A"}, {"id": "B"}])
    s = {x["title"]: x for x in db.work_summaries("u")}
    assert s["A"]["chapter_count"] == 2
    assert s["A"]["new_insight_count"] == 1
    assert s["A"]["pending_optionset_count"] == 1
    assert s["B"]["chapter_count"] == 0 and s["B"]["pending_optionset_count"] == 0


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()
