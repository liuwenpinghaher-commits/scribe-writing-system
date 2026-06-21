"""段3:scribe2 MCP 写作工具(圣经读写 + 生成 + ingest)+ 审批注册正确。"""
import scribe2.mcp as m
from scribe2.domain import Domain
from scribe2.store import Store


def _setdom(db):
    d = Domain(Store(db)); d.s.init_schema()
    m.set_domain(d)
    return d


def test_mcp_bible_and_generation(db, monkeypatch):
    _setdom(db)
    w = m.create_work("书")["work_id"]
    m.set_author_intent(w, reader_feeling="苍凉克制", red_lines=["不煽情"])
    assert m.get_author_intent(w)["reader_feeling"] == "苍凉克制"
    m.upsert_character(w, "渡叔", voice="极静带谶语")
    assert any(c["voice"] == "极静带谶语" for c in m.list_characters(w))
    m.plant_foreshadow(w, "长明灯某夜灭", 1, "high")
    assert any(f["summary"] == "长明灯某夜灭" for f in m.list_open_foreshadows(w))
    monkeypatch.setattr(m, "_complete", lambda p, **k: "渡叔立于船头,独眼望浊浪。")
    assert "渡叔立于船头" in m.write_continue(w, 1, "写渡叔夜渡")["content"]
    # 审批:碰正典的写工具需审批;生成草稿/只读不需
    assert m.requires_approval("set_author_intent")
    assert m.requires_approval("upsert_character")
    assert m.requires_approval("plant_foreshadow")
    assert not m.requires_approval("write_continue")
    assert not m.requires_approval("get_author_intent")


def test_mcp_ingest_builds_memory(db, monkeypatch):
    _setdom(db)
    w = m.create_work("书")["work_id"]
    ch = m.create_chapter(w, 1, "夜渡")["chapter_id"]
    m.save_prose(w, ch, "渡叔立于船头,独眼望浊浪,阿砚蜷在供桌下。")
    monkeypatch.setattr(m, "_complete", lambda p, **k: "第一章:渡叔夜渡,阿砚躲庙。")
    m.ingest_chapter(w, 1)
    mem = m.get_memory(w)
    assert any(mm["seq"] == 1 for mm in mem["chapters"])
    assert "渡叔夜渡" in mem["global"]
