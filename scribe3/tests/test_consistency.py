"""P21 facts_at 内存/真库对拍 + P23 单写点 spy + P04 load_knowledge 缓存
+ S4 知识边孤儿对拍(W3#8)。"""
from scribe3.ontology import Entity, Fact, KnowledgeEdge, World
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
            # UPDATE:add_fact 写入后经单点 _execute_write 补 embedding(P1),亦为合法写
            assert any(kw in s for kw in ["CREATE", "UPSERT", "RELATE", "UPDATE"]), f"写语句: {s}"


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


class TestWriteGate:
    """P02: 所有写端点(含未来新增)必须显式登记授权语义"""

    KNOWN_REST_WRITE_ROUTES = {
        ("POST", "/characters"), ("PATCH", "/characters/{local}"), ("DELETE", "/characters/{local}"),
        ("POST", "/facts"), ("PATCH", "/facts/{local}"), ("DELETE", "/facts/{local}"),
        ("POST", "/promises-new"), ("PATCH", "/promises/{pid}"), ("DELETE", "/promises/{pid}"),
        ("POST", "/promises/{pid}/advance"), ("POST", "/promises/{pid}/mark-herring"),
        ("POST", "/promises/{pid}/clues"), ("DELETE", "/promises/{pid}/clues/{idx}"),
        ("POST", "/motifs-new"), ("PATCH", "/motifs/{mid}"), ("DELETE", "/motifs/{mid}"),
        ("POST", "/intent"), ("PUT", "/intent"), ("POST", "/works"), ("DELETE", "/works/{slug}"),
        ("PATCH", "/works/{slug}"), ("POST", "/save-chapter"), ("POST", "/ingest"),
        ("POST", "/checkpoint"),
        ("POST", "/check"),   # 护栏轻检查:不落库,read-only POST
        ("POST", "/post-check"),   # 生成后全量体检:QC+泄露+纪律LLM,不落库,read-only POST
        ("POST", "/dedup-chapter"),   # QC治层:确定性事后跨章改写并存回(作者可信通道)
        ("POST", "/chat/write"),
        ("POST", "/world-rules"), ("DELETE", "/world-rules"),
        ("POST", "/factions"), ("DELETE", "/factions"),
        ("POST", "/items"), ("DELETE", "/items"),
        ("POST", "/terms"), ("DELETE", "/terms"),
        ("POST", "/char-states"),
        ("POST", "/ingest-unverified/{uid}/accept"),
        ("POST", "/ingest-unverified/{uid}/ignore"),
        ("POST", "/facts/supersede"),
        ("POST", "/knowledge/forget"),
        ("POST", "/character-relations"),
        ("POST", "/character-relations/evolve"),
        ("POST", "/character-relations/end"),
        ("POST", "/voice-flags/{fid}/resolve"),
        ("POST", "/voice-flags/fold"),
        # F-01 大纲/卷章树手稿支
        ("POST", "/chapters/reorder"),
        ("PATCH", "/chapters/{seq}"),
        ("POST", "/volumes"),
        ("PATCH", "/volumes/{vid}"),
        ("DELETE", "/volumes/{vid}"),
    }

    def test_no_unaudited_write_route(self):
        import scribe3.app as A
        actual = set()
        for route in A.app.routes:
            methods = getattr(route, "methods", set())
            if methods is None:
                continue
            for m in methods:
                if m in {"POST", "PUT", "PATCH", "DELETE"}:
                    actual.add((m, route.path))
        # 健康检查除外;背景任务端点不在此列
        exempt = {("GET", "/health")}
        unknown = actual - self.KNOWN_REST_WRITE_ROUTES - exempt
        assert not unknown, f"新写路径未登记授权语义: {unknown}"


class TestOrphanKnowledgeEdges:
    """S4 (W3#8): knows/reader_knows 孤儿边扫描 — 指向已删命题的悬挂边不应存在。"""

    def test_normal_ingest_no_orphans(self, store):
        """正常 ingest + purge 后不留孤儿边。"""
        from scribe3.ingest import apply_delta
        store.add_entity(Entity("role:甲", "character", "甲"))
        apply_delta(store, {
            "learned": [{"who": "甲", "fact": "天道不可违"}],
            "did": [],
        }, seq=1)
        orphans = store.orphan_knowledge_edges()
        assert orphans == [], f"正常 ingest 后不应有孤儿边,实际: {orphans}"

    def test_purge_leaves_no_orphans(self, store):
        """purge_ingest 清掉命题时,同批次 knows/reader_knows 边也被清。"""
        from scribe3.ingest import apply_delta
        store.add_entity(Entity("role:乙", "character", "乙"))
        apply_delta(store, {
            "learned": [{"who": "乙", "fact": "玄妙之道难测"}],
            "did": [],
        }, seq=2)
        # 重新 ingest(purge + 重写)
        apply_delta(store, {
            "learned": [{"who": "乙", "fact": "玄妙之道难测"}],
            "did": [],
        }, seq=2)
        orphans = store.orphan_knowledge_edges()
        assert orphans == [], f"purge 后不应有孤儿边,实际: {orphans}"

    def test_delete_proposition_cascades_knows_edge(self, store):
        """SurrealDB 图语义保障:删命题时 knows 边级联消失 → orphan_knowledge_edges 不会有遗留。
        这是对 SurrealDB 不变量的回归测试——确保级联删除正常工作。"""
        store.add_entity(Entity("role:丙", "character", "丙"))
        store.add_fact(Fact("fact:cascade_test", "role:丙", "获知", "级联删除验证值", valid_from=1))
        store.add_knowledge(KnowledgeEdge("role:丙", "fact:cascade_test", since_chapter=1,
                                          acquired_via="learned"))
        # 确认目前无孤儿、knows 边存在
        assert store.orphan_knowledge_edges() == []
        # 删掉命题:SurrealDB 会级联清理 knows 边
        store.delete_record("fact:cascade_test")
        # 级联后:knows 边消失,孤儿扫描仍返回空(因为边本身被级联删了)
        orphans = store.orphan_knowledge_edges()
        assert orphans == [], \
            f"SurrealDB 级联删除后不应有孤儿边(边已随节点消失),实际: {orphans}"
        # 额外验证:knows 边确实已消失
        knows_rows = store._query("SELECT id FROM knows")
        assert not knows_rows, "删命题后 knows 边应已级联消失"

    def test_reader_knows_delete_proposition_cascades(self, store):
        """reader_knows 表(非图边,是独立表)在命题删除后依赖 orphan_knowledge_edges 检出悬挂。
        注意:reader_knows 用的是 CREATE(非 RELATE),SurrealDB 不级联——这是需要 orphan 扫描保护的场景。"""
        store.add_entity(Entity("role:丁", "character", "丁"))
        store.add_fact(Fact("fact:rk_test", "role:丁", "获知", "读者知识测试", valid_from=1))
        store.add_knowledge(KnowledgeEdge("reader", "fact:rk_test", since_chapter=1,
                                          acquired_via="narrated"))
        assert store.orphan_knowledge_edges() == []
        # 删掉命题
        store.delete_record("fact:rk_test")
        # reader_knows 行本身不级联删除(独立表),orphan 扫描应能检出
        orphans = store.orphan_knowledge_edges()
        assert len(orphans) >= 1, \
            f"reader_knows 孤儿边应被 orphan_knowledge_edges 检出,实际: {orphans}"
        assert any("rk_test" in str(o) for o in orphans), \
            f"孤儿边记录应含 rk_test 引用,实际: {orphans}"
