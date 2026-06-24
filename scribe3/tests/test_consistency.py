"""P21 facts_at 内存/真库对拍 + P23 单写点 spy + P04 load_knowledge 缓存。"""
from scribe3.ontology import Entity, Fact, World
from scribe3.knowledge import project_frame, dramatic_irony


class TestFactsAtParity:
    """P21: World.facts_at 与 SurrealStore.facts_at 逐章一致"""

    def test_parity_memory_vs_store(self, store):
        w = World()
        store.add_entity(Entity("role:x", "character", "x"))
        w.add_entity(Entity("role:x", "character", "x"))
        seed = [
            Fact("fact:a", "role:x", "attr", "va", valid_from=1),
            Fact("fact:b", "role:x", "attr", "vb", valid_from=2, valid_to=5),
            Fact("fact:c", "role:x", "attr", "vc", valid_from=3),
        ]
        for f in seed:
            w.add_fact(f)
            store.add_fact(f)
        for ch in range(1, 7):
            mem = {f.id for f in w.facts_at(ch)}
            db = {f.id for f in store.facts_at(ch)}
            assert mem == db, f"第{ch}章漂移: memory={mem} store={db}"


class TestSingleWritePoint:
    """P23: 所有世界状态写经 _execute_write"""

    def test_add_methods_use_execute_write(self, store, monkeypatch):
        calls = []
        orig = store._execute_write
        def spy(surql, vars):
            calls.append(surql)
            orig(surql, vars)
        monkeypatch.setattr(store, "_execute_write", spy)
        from scribe3.ontology import Entity, Fact, KnowledgeEdge
        store.add_entity(Entity("role:s", "character", "s"))
        store.add_fact(Fact("fact:s1", "role:s", "attr", "val", valid_from=1))
        store.add_knowledge(KnowledgeEdge("role:s", "fact:s1", since_chapter=1, acquired_via="saw"))
        assert len(calls) >= 3, "add_entity/add_fact/add_knowledge 都应经 _execute_write"
        for s in calls:
            assert any(kw in s for kw in ["CREATE", "UPSERT", "RELATE"]), f"写语句: {s}"


class TestLoadKnowledgeCaching:
    """P04: dramatic_irony 只调一次 load_knowledge(去 N+1)"""

    def test_dramatic_irony_single_load(self, store, monkeypatch):
        from scribe3.scenario import luanshi_leak_world
        luanshi_leak_world(store)
        calls = {"n": 0}
        orig = store.load_knowledge
        def counting():
            calls["n"] += 1
            return orig()
        monkeypatch.setattr(store, "load_knowledge", counting)
        dramatic_irony(store, "role:老道", 1)
        assert calls["n"] == 1, f"dramatic_irony 应只调 1 次 load_knowledge,实际 {calls['n']}"
