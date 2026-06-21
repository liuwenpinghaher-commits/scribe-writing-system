"""写作层移植 Phase2:build_writing_context 读 SurrealDB 组装富上下文(质量核心)。"""
from scribe2.domain import Domain
from scribe2.store import Store
from scribe2.writing import build_writing_context


def _dom(db):
    d = Domain(Store(db)); d.s.init_schema()
    return d


def test_context_injects_bible_and_constraints(db):
    d = _dom(db)
    w = d.create_work("九原渡")
    d.set_intent(w, reader_feeling="苍凉克制的宿命感",
                 core_emotional_arc="少年由避世到担当", red_lines=["不用现代词", "不煽情"])
    d.add_character(w, "渡叔", motivation="守渡四十年替无名死者摆渡", voice="极静带谶语")
    d.add_setting(w, "九原渡", "浊河北岸的古渡,生死之界")
    d.save_chapter_memory(w, 1, "第一章:阿砚逃难至九原渡被渡叔收留")
    d.set_global_memory(w, "全书主线:乱世渡口,渡魂先渡人")

    ctx = build_writing_context(d, w, seq=2)
    assert "苍凉克制的宿命感" in ctx          # 北极星
    assert "渡叔" in ctx and "极静带谶语" in ctx  # 角色声音指纹
    assert "九原渡" in ctx                     # 关键设定
    assert "渡魂先渡人" in ctx                  # 全书主线记忆
    assert "第一章" in ctx                      # 最近章梗概(upto seq-1)
    assert "不煽情" in ctx                      # 红线
    assert ("show" in ctx or "克制" in ctx)     # antislop 文学约束块


def test_context_upto_does_not_leak_future(db):
    # 写第2章时不应注入第2章及以后的章梗概(防剧透/时间错位)
    d = _dom(db)
    w = d.create_work("书")
    d.save_chapter_memory(w, 1, "第一章梗概A")
    d.save_chapter_memory(w, 2, "第二章梗概B")
    ctx = build_writing_context(d, w, seq=2)
    assert "第一章梗概A" in ctx
    assert "第二章梗概B" not in ctx
