"""Test transaction context manager (G枢纽 P06).

关键多步写包事务:要么全成,要么全不落。
使用单条多语句 BEGIN/COMMIT 模式(SurrealDB 3.x 支持)。
"""
import pytest

from scribe3.ontology import Entity, Fact, KnowledgeEdge


class TestTransaction:
    """transaction() for simple writes + grant_public atomic"""

    def test_transaction_upserts_commit(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        with store.transaction():
            store.add_fact(Fact("fact:tx1", "role:甲", "获知", "A", valid_from=1))
            store.add_fact(Fact("fact:tx2", "role:甲", "获知", "B", valid_from=1))
        assert store.fact("fact:tx1") is not None
        assert store.fact("fact:tx2") is not None

    def test_grant_public_gives_edges_to_all(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_entity(Entity("role:乙", "character", "乙"))
        store.add_fact(Fact("fact:pub", "role:甲", "获知", "公开", valid_from=1))
        store.grant_public("fact:pub", 1)
        edges = store.knowledge
        pub_edges = [e for e in edges if e.proposition_id == "fact:pub"]
        assert len(pub_edges) >= 2

    def test_transaction_empty_noop(self, store):
        with store.transaction():
            pass


class TestOpenChapterConstant:
    """P42: 哨兵常量"""

    def test_open_chapter_constant_exists(self):
        from scribe3.store import _OPEN_CHAPTER
        assert _OPEN_CHAPTER == 9999

    def test_all_chapters_constant_exists(self):
        from scribe3.store import _ALL_CHAPTERS
        assert _ALL_CHAPTERS == 99999
