"""写作层移植 Phase1:生成上下文领域实体(北极星/角色含声音/伏笔/章记忆+全局)。
表早在 schema 定义,这里补 Domain repo 方法。"""
from scribe2.domain import Domain
from scribe2.store import Store


def _dom(db):
    d = Domain(Store(db))
    d.s.init_schema()
    return d


def test_author_intent_roundtrip(db):
    d = _dom(db)
    w = d.create_work("书")
    d.set_intent(w, reader_feeling="苍凉克制的宿命感",
                 core_emotional_arc="少年由避世到入世担当",
                 red_lines=["不用现代词", "不煽情"])
    it = d.get_intent(w)
    assert it["reader_feeling"] == "苍凉克制的宿命感"
    assert it["core_emotional_arc"].startswith("少年")
    assert "不煽情" in it["red_lines"]


def test_character_with_voice(db):
    d = _dom(db)
    w = d.create_work("书")
    d.add_character(w, "渡叔", motivation="守渡四十年替无名死者摆渡", voice="极静带谶语")
    chars = d.list_characters(w)
    c = next(x for x in chars if x["name"] == "渡叔")
    assert c["voice"] == "极静带谶语"
    assert "守渡" in c["motivation"]


def test_foreshadow_plant_and_list_open(db):
    d = _dom(db)
    w = d.create_work("书")
    fid = d.plant_foreshadow(w, "长明灯某夜灭一次", chapter=1, importance="high")
    assert fid
    opens = d.list_open_foreshadows(w)
    assert any(f["summary"] == "长明灯某夜灭一次" for f in opens)
    # 推进到已了结后不再出现在 open
    d.advance_foreshadow(fid, "paid")
    assert all(f["summary"] != "长明灯某夜灭一次" for f in d.list_open_foreshadows(w))


def test_chapter_memory_and_global(db):
    d = _dom(db)
    w = d.create_work("书")
    d.save_chapter_memory(w, 1, "第一章:阿砚逃难至九原渡被渡叔收留")
    d.save_chapter_memory(w, 2, "第二章:阿砚学撑船、识三不渡")
    mems = d.list_chapter_memories(w)
    assert [m["seq"] for m in mems] == [1, 2]
    # upto 过滤(写第3章时只看 < 3 的,不剧透)
    assert [m["seq"] for m in d.list_chapter_memories(w, upto=1)] == [1]
    d.set_global_memory(w, "全书主线:乱世渡口、渡魂先渡人")
    assert "渡魂先渡人" in d.get_global_memory(w)
