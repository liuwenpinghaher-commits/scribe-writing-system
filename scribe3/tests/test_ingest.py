"""S7⑤ · 章节回写 ingest —— 闭合写循环(对话写作→存→回写→下章限知反映新知)。

apply_delta 纯应用(不连网);ingest_chapter 走注入的 complete_fn。
P18: apply_delta 要求角色已存在(不再自动建,防幻觉角色污染)。
"""
from scribe3.ingest import apply_delta, ingest_chapter
from scribe3.knowledge import project_frame
from scribe3.ontology import Entity


def _ensure_chars(store, *names):
    for n in names:
        oid = f"role:{n}"
        if store.entity(oid) is None:
            store.add_entity(Entity(oid, "character", n))


def test_learned_makes_knower_know(store):
    _ensure_chars(store, "焦三")
    apply_delta(store, {"learned": [{"who": "焦三", "fact": "老道是流云观追索者"}], "did": []}, seq=3)
    fr = project_frame(store, "role:焦三", 3)
    assert any("追索者" in f.value for f in fr.facts), "焦三第3章起知道"


def test_did_witnesses_know(store):
    _ensure_chars(store, "焦三", "阿萤")
    apply_delta(store, {"learned": [], "did": [{"who": "焦三", "action": "取出尸丹", "seen_by": ["阿萤"]}]}, seq=2)
    assert any("尸丹" in f.value for f in project_frame(store, "role:焦三", 2).facts), "当事人知道"
    assert any("尸丹" in f.value for f in project_frame(store, "role:阿萤", 2).facts), "在场者也知道"


def test_non_witness_does_not_know(store):
    _ensure_chars(store, "焦三", "老道")
    apply_delta(store, {"learned": [], "did": [{"who": "焦三", "action": "取出尸丹", "seen_by": []}]}, seq=2)
    assert not project_frame(store, "role:老道", 2).knows("fact:d2-0"), "不在场者不知"


def test_ingest_chapter_end_to_end(store):
    _ensure_chars(store, "焦三")
    store.save_chapter(1, "焦三在乱岗取出尸丹。", focalizer="role:焦三")
    fake = lambda _p: '{"learned":[{"who":"焦三","fact":"尸丹能聚魂"}],"did":[]}'
    r = ingest_chapter(store, 1, fake)
    assert r["applied"] == 1
    assert any("聚魂" in f.value for f in project_frame(store, "role:焦三", 1).facts)


def test_apply_delta_writes_voice_flag(store):
    _ensure_chars(store, "焦三")
    from scribe3.ingest import apply_delta
    delta = {"learned": [], "did": [],
             "voice_shift": [{"who": "焦三", "reason": "被师父背叛"}]}
    apply_delta(store, delta, 10)
    flags = store.list_voice_flags("open")
    assert any(f["character"] == "焦三" and f["seq"] == 10 for f in flags)


# ── P0 数据丢失修复测试 ────────────────────────────────────────────────────────

def test_parse_knowledge_delta_signals_failure_on_garbage():
    from scribe3.critique import parse_knowledge_delta
    # 坏 JSON / 截断 → 返回失败信号(None),而非静默空 delta
    assert parse_knowledge_delta("这不是JSON{截断") is None


def test_parse_knowledge_delta_ok_empty():
    from scribe3.critique import parse_knowledge_delta
    d = parse_knowledge_delta('{"learned":[],"did":[],"voice_shift":[]}')
    assert d == {"learned": [], "did": [], "voice_shift": []}


def test_ingest_chapter_parse_fail_does_not_purge(store):
    from scribe3.ingest import ingest_chapter
    from scribe3.ontology import Fact
    # 先种一条本章既有 ingest 命题
    _ensure_chars(store, "甲")
    store.save_chapter(5, "正文内容五", focalizer=None)
    store.add_fact(Fact("fact:k5-0", "role:甲", "获知", "旧知识", valid_from=5), ingest_seq=5)
    # complete_fn 返回坏 JSON → 解析失败
    r = ingest_chapter(store, 5, lambda *a, **k: "坏的不是JSON{")
    assert r.get("parse_failed") is True
    # 既有 ingest 命题未被删
    facts = store.facts_at(5)
    assert any(f.id == "fact:fact:k5-0" or "k5-0" in f.id for f in facts), \
        "解析失败不应 purge 既有知识"


def test_ingest_chapter_ok_empty_still_purges(store):
    from scribe3.ingest import ingest_chapter
    from scribe3.ontology import Fact
    _ensure_chars(store, "乙")
    store.save_chapter(6, "正文六", focalizer=None)
    store.add_fact(Fact("fact:k6-0", "role:乙", "获知", "将被清", valid_from=6), ingest_seq=6)
    r = ingest_chapter(store, 6, lambda *a, **k: '{"learned":[],"did":[],"voice_shift":[]}')
    assert r.get("parse_failed") is not True
    assert r["applied"] == 0
    # 合法空 delta 仍幂等 purge+重写 → 旧的被清
    facts = store.facts_at(6)
    assert not any("k6-0" in f.id for f in facts), "合法空 delta 应 purge 旧 ingest 命题"
