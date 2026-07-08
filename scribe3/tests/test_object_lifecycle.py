from scribe3.ontology import Entity, Fact, KnowledgeEdge
import scribe3.app as A
from fastapi.testclient import TestClient

from .test_app import _client


def _nonraising_client(store):
    A.set_store(store)
    A.set_complete_fn(lambda prompt, **kw: "渲染的散文。")
    return TestClient(A.app, raise_server_exceptions=False)


def test_object_lifecycle_missing_objects_return_404(store):
    c = _client(store)

    assert c.get("/objects/material/not-there/impact").status_code == 404
    assert c.delete("/objects/material/not-there").status_code == 404
    assert c.get("/objects/role/没人/impact").status_code == 404
    assert c.delete("/objects/fact/不存在").status_code == 404


def test_material_delete_requires_impact_token_and_cleans_references(store):
    mid = store.add_material("密室白描", "冷硬密室寒气逼人", "snippet")
    store.add_material_reference(mid, 3, "手法", "适合刑讯", "brief")
    c = _client(store)

    impact = c.get(f"/objects/material/{mid}/impact").json()
    assert impact["object"] == {"type": "material", "id": mid, "label": "密室白描"}
    assert any(r["kind"] == "material_reference" and r["count"] == 1 for r in impact["references"])
    token = impact["confirm_impact_token"]

    blocked = c.delete(f"/objects/material/{mid}")
    assert blocked.status_code == 409
    assert blocked.json()["confirm_impact_token"] == token

    deleted = c.delete(f"/objects/material/{mid}", params={"confirm_impact_token": token})
    assert deleted.status_code == 200
    assert store.get_material(mid) is None
    assert store.material_refs_by_material(mid) == []


def test_archive_material_marks_archived_without_deleting_references(store):
    mid = store.add_material("可归档资料", "暂时不用但不能删除", "note")
    store.add_material_reference(mid, 4, "final", "正文采用", "write")
    c = _client(store)

    archived = c.post(f"/objects/material/{mid}/archive")

    assert archived.status_code == 200
    assert archived.json()["object"] == {"type": "material", "id": mid, "label": "可归档资料"}
    assert store.get_material(mid)["archived"] is True
    assert store.material_refs_by_material(mid)[0]["material_id"] == mid


def test_archive_material_hides_from_default_list_but_keeps_archived_view(store):
    mid = store.add_material("归档后隐藏素材", "默认素材库不再展示", "note")
    c = _client(store)

    archived = c.post(f"/objects/material/{mid}/archive")

    assert archived.status_code == 200
    assert all(m["id"] != mid for m in c.get("/materials").json())
    archived_rows = c.get("/materials", params={"view": "archived"}).json()
    assert any(m["id"] == mid for m in archived_rows)


def test_archive_role_hides_from_default_entities_without_deleting_object(store):
    store.add_entity(Entity("role:归档角色", "character", "归档角色"))
    c = _nonraising_client(store)

    archived = c.post("/objects/role/归档角色/archive")

    assert archived.status_code == 200
    assert not any(e["id"] == "role:归档角色" for e in c.get("/entities").json())
    assert c.get("/objects/role/归档角色/impact").status_code == 200


def test_archive_fact_hides_from_default_facts_without_deleting_object(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:归档命题", "role:甲", "状态", "已归档", valid_from=1))
    c = _nonraising_client(store)

    archived = c.post("/objects/fact/归档命题/archive")

    assert archived.status_code == 200
    assert not any(f["id"] == "fact:归档命题" for f in c.get("/facts", params={"chapter": 1}).json())
    assert c.get("/objects/fact/归档命题/impact").status_code == 200


def test_archive_missing_object_returns_404(store):
    c = _client(store)

    assert c.post("/objects/material/not-there/archive").status_code == 404


def test_fact_delete_requires_impact_token_when_known_by_character(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:秘密", "role:甲", "秘密", "井底有骨", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:秘密", since_chapter=1))
    c = _client(store)

    impact = c.get("/objects/fact/秘密/impact").json()
    assert impact["object"]["type"] == "fact"
    assert any(r["kind"] == "knowledge_edge" and r["count"] == 1 for r in impact["references"])
    token = impact["confirm_impact_token"]

    blocked = c.delete("/objects/fact/秘密")
    assert blocked.status_code == 409
    assert blocked.json()["confirm_impact_token"] == token

    deleted = c.delete("/objects/fact/秘密", params={"confirm_impact_token": token})
    assert deleted.status_code == 200
    assert store.fact("fact:秘密") is None
