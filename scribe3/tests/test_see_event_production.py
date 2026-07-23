"""生产路径: add_event 带 effects → 自动 see_event; ingest did 挂 effects。

禁止测试里手调 see_event——只走 store.add_event / apply_delta。
"""
from scribe3.ingest import apply_delta
from scribe3.knowledge import project_frame
from scribe3.ontology import Entity, Event, Fact


def test_add_event_with_effects_grants_witness_knowledge(store):
    """带 effects 的 add_event 后,SUBJ/WITNESS 均自动获得 knows(不手调 see_event)。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:秘密", "role:甲", "持有", "令牌", valid_from=2))
    store.add_event(Event(
        "ev:揭示", "揭示",
        participants={"SUBJ": "role:甲", "WITNESS": "role:乙"},
        effects=["fact:秘密"],
        story_time=2,
    ))
    assert project_frame(store, "role:乙", 2).knows("fact:秘密"), "目击者乙应知道 effects"
    assert project_frame(store, "role:甲", 2).knows("fact:秘密"), "当事人甲应知道 effects"


def test_add_event_no_effects_no_spurious_edges(store):
    """effects=[] 不产生 knows 边。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:无关", "role:甲", "状态", "在场", valid_from=1))
    store.add_event(Event(
        "ev:路过", "路过",
        participants={"SUBJ": "role:甲", "WITNESS": "role:乙"},
        effects=[],
        story_time=1,
    ))
    edges = store.load_knowledge()
    assert not any(e.proposition_id == "fact:无关" for e in edges), (
        "无 effects 时不应凭空产生 knows 边"
    )


def test_ingest_did_wires_effects_and_witness_knowledge(store):
    """did 落命题 + 合成/挂载 effects 事件 → 目击者 project_frame 知道(不手调 see_event)。"""
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_entity(Entity("role:阿萤", "character", "阿萤"))
    apply_delta(store, {
        "learned": [],
        "did": [{"who": "焦三", "action": "取出尸丹", "seen_by": ["阿萤"]}],
    }, seq=2)

    facts = [f for f in store.facts_at(2)
             if f.attribute == "行动" and "尸丹" in (f.value or "")]
    assert len(facts) == 1, f"did 应落 1 条行动命题,实际 {facts}"
    fid = facts[0].id

    evs = store.events_at(2)
    assert any(fid in (e.effects or []) for e in evs), (
        f"事件应挂 effects 含 {fid}, 实际 {[e.effects for e in evs]}"
    )

    assert project_frame(store, "role:阿萤", 2).knows(fid), "目击者阿萤应知道 did 命题"
    assert project_frame(store, "role:焦三", 2).knows(fid), "当事人焦三应知道 did 命题"
