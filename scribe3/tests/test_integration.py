"""集成测试:端到端管线验证 B+C 落地后链路正确(分析报告优化#5)。

验证顺序:建角色+事件(带图边)→ 存稿 → ingest → see_event → 限知渲染。
"""
from scribe3.ingest import apply_delta
from scribe3.knowledge import project_frame, see_event
from scribe3.ontology import Entity, Event, Fact


class TestEndToEndPipeline:
    """全管线:写章→ingest→限知渲染,验证 B+C 协同正确"""

    def test_full_pipeline_witness_gets_knowledge(self, store):
        """在场目击者经 see_event 获得知识边"""
        store.add_entity(Entity("role:老道", "character", "老道"))
        store.add_entity(Entity("role:焦三", "character", "焦三"))
        store.add_entity(Entity("role:阿萤", "character", "阿萤"))

        ef = Fact("fact:取丹", "role:焦三", "行动", "取出尸丹", valid_from=2, secret=True)
        store.add_fact(ef)
        ev = Event("ev:取丹", "action", story_time=2,
                   participants={"SUBJ": "role:焦三", "WITNESS": "role:老道"},
                   effects=["fact:取丹"])
        store.add_event(ev)
        see_event(store, store.events_at(2)[0])

        assert project_frame(store, "role:焦三", 2).knows("fact:取丹"), "当事人知道"
        assert project_frame(store, "role:老道", 2).knows("fact:取丹"), "在场目击者知道"
        assert not project_frame(store, "role:阿萤", 2).knows("fact:取丹"), "不在场者不知"

    def test_ingest_then_render_limited_pov(self, store):
        """Ingest 后限知渲染:帧外私密不进 prompt"""
        store.add_entity(Entity("role:焦三", "character", "焦三"))
        store.add_entity(Entity("role:老道", "character", "老道"))
        store.add_fact(Fact("fact:治眼", "role:焦三", "获知", "天生治眼神通", valid_from=1, secret=True))

        apply_delta(store, {"learned": [{"who": "焦三", "fact": "学会御剑术"}],
                            "did": [{"who": "焦三", "action": "在乱岗取丹", "seen_by": ["老道"]}]}, seq=1)

        from scribe3.render import build_render_prompt
        p = build_render_prompt(store, 2, "role:老道")
        assert "治眼" not in p, "老道帧不该含焦三私密(治眼)"
        assert "御剑术" not in p, "老道帧不该含焦三独自学会的事"
        assert "取丹" in p, "老道在场看到取丹"

    def test_reingest_preserves_pov(self, store):
        """重复 ingest 后限知不变"""
        store.add_entity(Entity("role:焦三", "character", "焦三"))
        store.add_fact(Fact("fact:秘密", "role:焦三", "获知", "私密信息", valid_from=1, secret=True))

        apply_delta(store, {"learned": [{"who": "焦三", "fact": "发现宝藏"}], "did": []}, seq=1)
        apply_delta(store, {"learned": [{"who": "焦三", "fact": "发现秘道"}], "did": []}, seq=1)

        fr = project_frame(store, "role:焦三", 1)
        assert any("秘道" in f.value for f in fr.facts)
        assert not any("宝藏" in f.value for f in fr.facts), "旧 ingest 产出已被清理"

    def test_event_graph_survives_reingest(self, store):
        """Event 图边在 ingest 后不受影响(B 不污染 C)"""
        store.add_entity(Entity("role:焦三", "character", "焦三"))
        ev = Event("ev:测试", "test", story_time=1,
                   participants={"SUBJ": "role:焦三"})
        store.add_event(ev)

        apply_delta(store, {"learned": [{"who": "焦三", "fact": "某事实"}], "did": []}, seq=1)

        events = store.events_at(1)
        assert len(events) >= 1
        assert "role:焦三" in events[0].participants.values(), "Event 参与者不受 ingest 影响"
