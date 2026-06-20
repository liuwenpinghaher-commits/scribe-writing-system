import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scribe_mcp.db import Database
from scribe_mcp.foreshadow import ForeshadowStore
from scribe_mcp.pending import WRITE_GATED, execute_write


def _call(tool, **kwargs):
    """调用一个 FastMCP 工具,兼容 .fn / 直接可调 两种形态。"""
    fn = getattr(tool, "fn", None) or (tool if callable(tool) else None)
    if fn is None:
        raise AssertionError(f"无法调用工具 {tool!r}")
    return fn(**kwargs)


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


def test_every_gated_tool_has_dispatch_branch(tmp_path):
    """守护:WRITE_GATED 每个工具都能被 execute_write 派发(不漂移)。
    若新增门控工具但忘了 dispatch 分支,会落到 raise ValueError("未注册...") —— 此处提前抓住。"""
    db, fs = _db(tmp_path)
    wid = db.create_work("u1", "书")
    ch = db.save_chapter(wid, 1, "一")           # returns chapter_id (str)
    fid = fs.plant(wid, "伏笔", 1)                 # foreshadow_id for advance
    minimal = {
        "upsert_setting": {"work_id": wid, "type": "x", "name": "n", "content": {}},
        "save_chapter": {"work_id": wid, "seq": 2, "title": "二"},
        "save_snapshot": {"work_id": wid, "chapter_id": ch, "content": "正文"},
        "upsert_character": {"work_id": wid, "name": "角色"},
        "plant_foreshadow": {"work_id": wid, "summary": "s", "foreshadow_chapter": 1},
        "advance_foreshadow": {"foreshadow_id": fid, "to_state": "triggered"},
        "set_author_intent": {"work_id": wid, "reader_feeling": "紧张"},
    }
    for tool in WRITE_GATED:
        assert tool in minimal, f"测试缺 {tool} 的最小参数(WRITE_GATED 新增了工具?)"
        res = execute_write(db, fs, tool, minimal[tool])  # 不应抛“未注册”
        assert isinstance(res, dict)


def test_mcp_write_tool_enqueues_not_writes(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("SCRIBE_DB", str(tmp_path / "srv.db"))
    import scribe_mcp.server as srv
    importlib.reload(srv)  # 用新 SCRIBE_DB 重连
    wid = srv.db.create_work("u1", "书")

    out = _call(srv.upsert_setting, work_id=wid, type="character", name="沈舟", content={"k": "v"})
    assert out["status"] == "awaiting_approval" and out["pending_id"]
    assert srv.db.list_settings(wid) == []            # 未落库
    assert len(srv.db.list_pending_writes(wid)) == 1  # 已入队

    assert isinstance(_call(srv.list_settings, work_id=wid), list)  # 只读照常


def test_advance_foreshadow_bad_id_rejected(tmp_path, monkeypatch):
    import importlib, pytest
    monkeypatch.setenv("SCRIBE_DB", str(tmp_path / "srv2.db"))
    import scribe_mcp.server as srv
    importlib.reload(srv)
    wid = srv.db.create_work("u1", "书")
    with pytest.raises(ValueError):
        _call(srv.advance_foreshadow, foreshadow_id="nope", to_state="triggered")
    assert srv.db.list_pending_writes(wid) == []  # 没有孤儿待批行
