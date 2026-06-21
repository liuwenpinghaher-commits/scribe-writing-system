import asyncio

import scribe2.mcp as M
from scribe2.conn import domain_from


def test_approval_registry_and_core_tools(db):
    d = domain_from(db); d.s.init_schema()
    M.set_domain(d)
    assert M.requires_approval("create_work") is True
    assert M.requires_approval("search_knowledge") is False
    w = M.create_work("雨夜", genre="悬疑")["work_id"]
    assert d.get_work(w)["title"] == "雨夜"
    d.add_setting(w, name="断魂剑", desc="会让持有者失忆的古剑")
    hits = M.search_knowledge(w, "失忆的剑", k=3)
    assert any("断魂剑" in (h.get("text") or "") for h in hits)


def test_read_tools(db):
    d = domain_from(db); d.s.init_schema()
    M.set_domain(d)
    w = M.create_work("书")["work_id"]
    c = d.add_chapter(w, 1, "一")
    d.save_prose(w, c, "初稿。")
    assert M.get_work(w)["title"] == "书"
    assert any(x["title"] == "书" for x in M.list_works())
    assert [x["seq"] for x in M.list_chapters(w)] == [1]
    assert M.latest_prose(c) == "初稿。"
    assert len(M.list_snapshots(c)) == 1
    assert M.list_settings(w) == []
    for t in ["get_work", "list_works", "list_chapters", "list_snapshots", "latest_prose", "list_settings"]:
        assert M.requires_approval(t) is False


def test_write_tools(db):
    d = domain_from(db); d.s.init_schema()
    M.set_domain(d)
    w = M.create_work("书")["work_id"]
    v = M.create_volume(w, seq=1, title="上卷")["volume_id"]
    c = M.create_chapter(w, seq=1, title="一", volume_id=v)["chapter_id"]
    M.save_prose(w, c, "雨夜。", lock=True)
    M.add_setting(w, name="断魂剑", desc="失忆古剑")
    assert d.latest_prose(c) == "雨夜。"
    assert [x["seq"] for x in d.list_chapters(w)] == [1]
    assert any("断魂剑" in (h.get("text") or "") for h in M.search_knowledge(w, "失忆的剑", k=3))
    for t in ["create_work", "create_volume", "create_chapter", "save_prose", "add_setting"]:
        assert M.requires_approval(t) is True


def test_tools_discoverable_and_annotated(db):
    tools = {t.name: t for t in asyncio.run(M.mcp.list_tools())}
    expected = {
        "search_knowledge", "get_work", "list_works", "list_chapters",
        "list_snapshots", "latest_prose", "list_settings",
        "create_work", "create_volume", "create_chapter",
        "save_prose", "add_setting",
        # 段3 写作工具
        "get_author_intent", "list_characters", "list_open_foreshadows", "get_memory",
        "write_continue", "set_author_intent", "upsert_character",
        "plant_foreshadow", "advance_foreshadow", "ingest_chapter",
        "critique_chapter", "check_chapter", "list_consistency_flags",
        "list_foreshadows_status", "add_foreshadow_beat",
    }
    assert expected <= set(tools), f"缺工具: {expected - set(tools)}"
    for name in expected:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is (name not in M.WRITE_TOOLS), f"{name} 注解/登记不一致"
    for name in expected:
        assert (tools[name].description or "").strip(), f"{name} 缺描述"
    assert M.WRITE_TOOLS == {
        "create_work", "create_volume", "create_chapter", "save_prose", "add_setting",
        "set_author_intent", "upsert_character", "plant_foreshadow",
        "advance_foreshadow", "ingest_chapter", "check_chapter",
        "add_motif", "add_char_state", "add_foreshadow_beat",
    }
