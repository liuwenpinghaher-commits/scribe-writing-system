import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scribe_mcp.db import Database
from scribe_mcp.foreshadow import ForeshadowStore
from scribe_mcp.pending import WRITE_GATED, execute_write


def _db(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    return db, ForeshadowStore(db.conn)


def test_write_gated_set_covers_canonical_writes():
    assert {"upsert_setting", "save_chapter", "save_snapshot", "upsert_character",
            "plant_foreshadow", "advance_foreshadow", "set_author_intent"} <= WRITE_GATED
    assert "list_settings" not in WRITE_GATED
    assert "search_book" not in WRITE_GATED


def test_execute_write_upsert_setting_persists(tmp_path):
    db, fs = _db(tmp_path)
    wid = db.create_work("u1", "书")
    res = execute_write(db, fs, "upsert_setting",
                        {"work_id": wid, "type": "character", "name": "沈舟", "content": {"动机": "复仇"}})
    assert "setting_id" in res
    names = [s["name"] for s in db.list_settings(wid)]
    assert "沈舟" in names


def test_execute_write_plant_foreshadow_persists(tmp_path):
    db, fs = _db(tmp_path)
    wid = db.create_work("u1", "书")
    res = execute_write(db, fs, "plant_foreshadow",
                        {"work_id": wid, "summary": "断剑", "foreshadow_chapter": 1})
    assert "foreshadow_id" in res
    assert len(fs.list_open(wid)) == 1


def test_execute_write_unknown_tool_raises(tmp_path):
    db, fs = _db(tmp_path)
    try:
        execute_write(db, fs, "rm_rf", {"work_id": "w"})
        assert False, "未注册工具应抛错"
    except ValueError:
        pass
