"""Test ingest idempotency (C枢纽 P07 + 优化#1 最小事务).

章级幂等:同一章 ingest 任意多次 → 账本收敛到"最后一次抽取结果"。
"""
from scribe3.ingest import apply_delta
from scribe3.ontology import Entity


class TestIngestIdempotency:
    """P07: 重复 ingest 不漂移,无悬挂知识边"""

    def test_reingest_changed_extraction_no_dangling(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        apply_delta(store, {"learned": [{"who": "甲", "fact": "A"}, {"who": "甲", "fact": "B"}], "did": []}, seq=5)
        facts_a = {f.value for f in store.facts_at(5) if f.attribute in ("获知", "行动")}
        assert "A" in facts_a and "B" in facts_a

        # 二次抽取条目变少
        apply_delta(store, {"learned": [{"who": "甲", "fact": "C"}], "did": []}, seq=5)
        facts_b = {f.value for f in store.facts_at(5) if f.attribute in ("获知", "行动")}
        assert facts_b == {"C"}  # 旧 A/B 已清,无残留

        # 无 knows 边指向已不存在的 fact
        edges = store.load_knowledge() if hasattr(store, "load_knowledge") else store.knowledge
        live_fids = {f.id for f in store.facts_at(5)}
        for e in edges:
            if e.since_chapter == 5:
                assert e.proposition_id in live_fids, f"悬挂边指向已删命题 {e.proposition_id}"

    def test_reingest_with_did_entries(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_entity(Entity("role:乙", "character", "乙"))
        apply_delta(store, {"learned": [], "did": [{"who": "甲", "action": "X", "seen_by": ["乙"]}]}, seq=3)
        fr = store.facts_at(3)
        did_facts = [f for f in fr if f.attribute == "行动"]
        assert len(did_facts) == 1

        # 二次抽取:died 变为 learned
        apply_delta(store, {"learned": [{"who": "甲", "fact": "Y"}], "did": []}, seq=3)
        fr2 = store.facts_at(3)
        new_facts = [f for f in fr2 if f.attribute in ("获知", "行动")]
        assert len(new_facts) == 1
        assert new_facts[0].value == "Y"

    def test_reingest_preserves_non_ingest_facts(self, store):
        """幂等清理只影响 ingest 产出,不动作者直编的命题"""
        store.add_entity(Entity("role:甲", "character", "甲"))
        from scribe3.ontology import Fact
        store.add_fact(Fact("fact:manual", "role:甲", "manual", "hand-written", valid_from=3))
        apply_delta(store, {"learned": [{"who": "甲", "fact": "Z"}], "did": []}, seq=3)
        apply_delta(store, {"learned": [{"who": "甲", "fact": "W"}], "did": []}, seq=3)

        # 手动命题未被 ingest purge 清理
        f = store.fact("fact:manual")
        assert f is not None and f.value == "hand-written"


class TestIngestDedup:
    """去双触发:gen3.py 不再显式调 /ingest"""

    def test_apply_delta_with_none_delta(self, store):
        """空 delta 应返回 0"""
        n = apply_delta(store, {"learned": [], "did": []}, seq=1)
        assert n == 0
