"""门槛自动校验自检:符号状态矛盾 + AI 腔 → consistency_flag。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.consistency import run_auto_check  # noqa: E402


def _setup():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    db = Database(tmp.name)
    return db, db.create_work("u", "书")


def test_lost_item_reappears_flagged():
    db, w = _setup()
    db.upsert_setting(w, "item", "青铜匕首", {"state": "destroyed"})  # 已损毁
    cid = db.save_chapter(w, 1, "第一章")
    db.save_snapshot(w, cid, "他握紧了青铜匕首,刀锋在月下泛光。", created_by="ai")
    flags = run_auto_check(db, w, 1)
    classes = {db.list_consistency_flags(w)[0]["error_class"]}
    assert any(True for _ in flags) and "item_state_contradiction" in classes


def test_aislop_flagged_and_clean_passes():
    db, w = _setup()
    cid = db.save_chapter(w, 1)
    db.save_snapshot(w, cid, "这一刻他终于明白了,他心中充满了无比的喜悦。", created_by="ai")
    f1 = run_auto_check(db, w, 1)
    assert any(c["error_class"] == "narrative_style" for c in db.list_consistency_flags(w))
    # 干净章节:无 flag
    db2, w2 = _setup()
    c2 = db2.save_chapter(w2, 1)
    db2.save_snapshot(w2, c2, "他把伞收了,水珠顺着伞骨滴在台阶上。", created_by="ai")
    assert run_auto_check(db2, w2, 1) == []


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()
