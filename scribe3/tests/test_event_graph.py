"""Test Event persistence with graph edges (B枢纽 P03).

真库 Event 的 participants/effects/causal_in 通过图边持久化,
不再蒸发于 add_event(store.py:178-180)。
"""
import pytest

from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge
from scribe3.knowledge import project_frame


class TestEventGraphPersistence:
    """真库 Event 的 participants/effects/causal_in 往返不丢"""

    def test_event_participants_roundtrip(self, store):
        store.add_entity(Entity("role:老道", "character", "老道"))
        store.add_entity(Entity("role:焦三", "character", "焦三"))
        ev = Event("ev:对峙", "对峙", story_time=1,
                   participants={"SUBJ": "role:老道", "OBJ": "role:焦三"})
        store.add_event(ev)
        events = store.events_at(1)
        assert len(events) == 1
        assert events[0].participants == {"SUBJ": "role:老道", "OBJ": "role:焦三"}

    def test_event_effects_roundtrip(self, store):
        store.add_entity(Entity("role:焦三", "character", "焦三"))
        store.add_fact(Fact("fact:取丹", "role:焦三", "行动", "取出尸丹", valid_from=1))
        ev = Event("ev:取丹", "action", story_time=1,
                   participants={"SUBJ": "role:焦三"},
                   effects=["fact:取丹"])
        store.add_event(ev)
        events = store.events_at(1)
        assert len(events) == 1
        assert "fact:取丹" in events[0].effects

    def test_event_causal_roundtrip(self, store):
        store.add_entity(Entity("role:老道", "character", "老道"))
        ev1 = Event("ev:对峙", "对峙", story_time=1,
                    participants={"SUBJ": "role:老道"})
        store.add_event(ev1)
        ev2 = Event("ev:动手", "action", story_time=1,
                    participants={"SUBJ": "role:老道"},
                    causal_in=[("ev:对峙", "enables")])
        store.add_event(ev2)
        events = store.events_at(1)
        ev_found = [e for e in events if e.id == "ev:动手"]
        assert len(ev_found) == 1
        assert ev_found[0].causal_in == [("ev:对峙", "enables")]


class TestEventPersistedParadigm:
    """B 图边落地后,限知不破:老道帧不应含焦三私密"""

    def test_pov_holds_after_event_graph_edges(self, store):
        from scribe3.scenario import luanshi_leak_world
        luanshi_leak_world(store)
        from scribe3.render import build_render_prompt
        p = build_render_prompt(store, 1, "role:老道")
        assert "治眼" not in p, "老道帧不该含焦三的私密设定"
