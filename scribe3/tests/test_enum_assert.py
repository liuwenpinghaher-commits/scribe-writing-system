"""Test enum ASSERT constraints (D枢纽 枚举受控).

验证 DB 层 ASSERT $value IN [...] 拒绝脏值,以及 Python Enum 与 surql ASSERT 域一致。
"""
import pytest
from surrealdb import RecordID

from scribe3.enums import (
    AcquiredVia, CraftRuleKind, EntityKind, FlagStatus,
    PromiseKind, PromiseStatus, VoiceKind,
)
from scribe3.ontology import Entity, Fact


class TestAcquiredViaAssert:
    """knows.acquired_via ASSERT IN ['saw','told','inferred','given','learned']"""

    def test_dirty_acquired_via_rejected(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:t1", "role:甲", "attr", "val", valid_from=1))
        with pytest.raises(Exception):
            store._db.query(
                "RELATE $k->knows->$p SET since_chapter=1, acquired_via='telepathy'",
                {"k": RecordID("character", "甲"), "p": RecordID("proposition", "t1")},
            )

    def test_learned_accepted(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:t2", "role:甲", "attr", "val", valid_from=1))
        store._db.query(
            "RELATE $k->knows->$p SET since_chapter=1, acquired_via='learned'",
            {"k": RecordID("character", "甲"), "p": RecordID("proposition", "t2")},
        )

    def test_saw_accepted(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:t3", "role:甲", "attr", "val", valid_from=1))
        store._db.query(
            "RELATE $k->knows->$p SET since_chapter=1, acquired_via='saw'",
            {"k": RecordID("character", "甲"), "p": RecordID("proposition", "t3")},
        )


class TestPromiseKindAssert:
    """promise.kind ASSERT IN ['promise','red_herring']"""

    def test_dirty_promise_kind_rejected(self, store):
        with pytest.raises(Exception):
            store._db.query(
                "CREATE promise:bad SET text='x', setup_chapter=1, "
                "status='open', kind='foreshadow'"
            )

    def test_promise_accepted(self, store):
        store._db.query(
            "CREATE promise:ok SET text='x', setup_chapter=1, "
            "status='open', kind='promise'"
        )


class TestPromiseStatusAssert:
    """promise.status ASSERT IN ['open','closed']"""

    def test_dirty_promise_status_rejected(self, store):
        with pytest.raises(Exception):
            store._db.query(
                "CREATE promise:bad2 SET text='x', setup_chapter=1, "
                "status='pending', kind='promise'"
            )


class TestVoiceKindAssert:
    """voice_sample.kind ASSERT IN ['free','pressure','relation','narration']"""

    def test_dirty_voice_kind_rejected(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        with pytest.raises(Exception):
            store._db.query(
                "CREATE voice_sample SET character='role:甲', "
                "kind='monologue', text='x', since_chapter=1"
            )

    def test_free_accepted(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store._db.query(
            "CREATE voice_sample SET character='role:甲', "
            "kind='free', text='x', since_chapter=1"
        )


class TestEnumParity:
    """Python Enum 成员集 == surql ASSERT 域(防两层漂移)"""

    def test_acquired_via_members(self):
        vals = {e.value for e in AcquiredVia}
        assert vals == {"saw", "told", "inferred", "given", "learned"}

    def test_acquired_via_has_learned(self):
        assert AcquiredVia.learned.value == "learned"

    def test_promise_kind_members(self):
        vals = {e.value for e in PromiseKind}
        assert vals == {"promise", "red_herring"}

    def test_promise_status_members(self):
        vals = {e.value for e in PromiseStatus}
        assert vals == {"open", "closed"}

    def test_voice_kind_members(self):
        vals = {e.value for e in VoiceKind}
        assert vals == {"free", "pressure", "relation", "narration"}

    def test_flag_status_members(self):
        vals = {e.value for e in FlagStatus}
        assert vals == {"open", "done"}

    def test_craft_rule_kind_members(self):
        vals = {e.value for e in CraftRuleKind}
        assert vals == {"purple_regex", "artifact_craft", "cover_action"}

    def test_entity_kind_members(self):
        vals = {e.value for e in EntityKind}
        assert vals == {"character", "item", "place", "faction"}
