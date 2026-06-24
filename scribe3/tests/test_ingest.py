"""S7⑤ · 章节回写 ingest —— 闭合写循环(render→存→回写→下章限知反映新知)。

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
