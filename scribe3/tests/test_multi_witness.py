"""多目击者:同 role 多 involves 不得被 dict 压扁;see_event 全覆盖。"""
from __future__ import annotations

from scribe3.knowledge import project_frame
from scribe3.ontology import Entity, Event, Fact


def test_multiple_witnesses_same_slot_all_know(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_entity(Entity("role:丙", "character", "丙"))
    store.add_fact(Fact("fact:y_mw", "role:甲", "言", "密谈", valid_from=1))
    # 同 WITNESS 槽两位目击者:实现须接受 list 值或重复边
    store.add_event(Event(
        "ev:mw1", "talk",
        participants={
            "SUBJ": "role:甲",
            "WITNESS": ["role:乙", "role:丙"],
        },
        effects=["fact:y_mw"],
        story_time=1,
    ))
    assert project_frame(store, "role:乙", 1).knows("fact:y_mw")
    assert project_frame(store, "role:丙", 1).knows("fact:y_mw")
    # 读回不得只剩一个 WITNESS
    evs = store.events_at(1)
    assert len(evs) == 1
    w = evs[0].participants.get("WITNESS")
    if isinstance(w, list):
        assert set(w) >= {"role:乙", "role:丙"}
    else:
        # 若实现用 WITNESS / WITNESS_2 等键,收集所有值
        oids = set()
        for k, v in evs[0].participants.items():
            if "WITNESS" in k.upper() or k == "WITNESS":
                if isinstance(v, list):
                    oids.update(v)
                elif v:
                    oids.add(v)
        assert oids >= {"role:乙", "role:丙"}, f"读回丢失目击者: {evs[0].participants}"
