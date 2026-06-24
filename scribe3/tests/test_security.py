"""Test security hardening (F枢纽 本地最小集).

P14: /facts /recall /frame /irony 不应泄露 secret value。
"""
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.ontology import Entity, Fact


class TestSecretStripping:
    """P14: 非投影端点剥离 secret value"""

    def test_facts_endpoint_hides_secret(self, store):
        A.set_store(store, work="test")
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:secret", "role:甲", "获知", "绝密信息", valid_from=1, secret=True))
        c = TestClient(A.app)
        r = c.get("/facts?chapter=1&work=test")
        assert r.status_code == 200
        for item in r.json():
            if item["id"] == "fact:secret":
                assert item["value"] is None, "secret value 应为 null"
                assert item["is_secret"] is True

    def test_non_secret_value_preserved(self, store):
        A.set_store(store, work="test")
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:pub", "role:甲", "获知", "公开信息", valid_from=1, secret=False))
        c = TestClient(A.app)
        r = c.get("/facts?chapter=1&work=test")
        assert r.status_code == 200
        for item in r.json():
            if item["id"] == "fact:pub":
                assert item["value"] == "公开信息"
                assert item["is_secret"] is False

    def test_frame_does_not_expose_secret(self, store):
        A.set_store(store, work="test")
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:s2", "role:甲", "获知", "私密", valid_from=1, secret=True))
        c = TestClient(A.app)
        r = c.get("/frame?focalizer=role:甲&chapter=1&work=test")
        assert r.status_code == 200
        for item in r.json():
            if item.get("is_secret"):
                assert item["value"] is None
