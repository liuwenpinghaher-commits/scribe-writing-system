"""P0 author paths under emergency REST off: MCP world writes + author-owned materials."""
from __future__ import annotations

import inspect

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
import scribe3.mcp as M
from scribe3.ontology import Entity


@pytest.fixture()
def emergency_off(monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)


def test_new_mcp_tools_in_write_gated():
    for name in (
        "s3_reorder_chapters", "s3_delete_volume",
        "s3_add_motif",
    ):
        assert name in M.WRITE_GATED
        assert M.requires_approval(name) is True


def test_reorder_chapters_mcp_accept(store, emergency_off):
    M.set_store(store)
    vid = store.add_volume("卷一", sort_order=0)
    store.create_chapter(title="甲", volume_id=vid)
    store.create_chapter(title="乙", volume_id=vid)
    chs = sorted(store.list_chapters(), key=lambda c: c.get("seq") or 0)
    seqs = [c["seq"] for c in chs]
    rev = list(reversed(seqs))

    def _write():
        n = store.reorder_chapters(vid, rev)
        return {"count": n, "order": rev}

    out = M.commit_if_approved("s3_reorder_chapters", True, _write)
    assert out["status"] == "written"
    # emergency REST off: form REST reorder still 403
    A.set_store(store)
    client = TestClient(A.app)
    r = client.post("/chapters/reorder?work=main", json={"volume": vid, "order": seqs})
    assert r.status_code == 403


def test_delete_volume_mcp_accept(store, emergency_off):
    M.set_store(store)
    vid = store.add_volume("待删卷", sort_order=1)
    store.create_chapter(title="留章", volume_id=vid)

    def _write():
        if not store.delete_volume(vid):
            return False
        return {"volume_id": vid}

    out = M.commit_if_approved("s3_delete_volume", True, _write)
    assert out["status"] == "written"
    assert not any(v.get("id") == vid for v in store.list_volumes())
    # chapters remain
    assert any(c.get("title") == "留章" for c in store.list_chapters())


def test_author_material_crud_remains_available_under_emergency_off(store, emergency_off):
    """素材是作者非正典记忆；世界写紧急开关关闭时仍可直接新建、编辑、删除。"""
    A.set_store(store)
    client = TestClient(A.app)
    created = client.post("/materials?work=main", json={
        "title": "密室白描", "body": "寒气", "kind": "snippet",
        "source": "《乱世》札记", "pinned": True,
        "origin": "chief",  # 客户端不得伪造主编来源
    })
    assert created.status_code == 200, created.text
    mid = created.json()["id"]

    edited = client.patch(f"/materials/{mid}?work=main", json={
        "title": "密室冷硬白描", "pinned": False,
    })
    assert edited.status_code == 200, edited.text
    row = store.get_material(mid)
    assert row["title"] == "密室冷硬白描"
    assert row["pinned"] is False
    assert row["origin"] == "manual"

    deleted = client.delete(f"/materials/{mid}?work=main")
    assert deleted.status_code == 200, deleted.text
    assert store.get_material(mid) is None


def test_material_write_tools_are_not_available_to_chief():
    for name in ("s3_add_material", "s3_patch_material", "s3_delete_material"):
        assert name not in M.WRITE_GATED
        assert not hasattr(M, name)


def test_register_purpose_goes_through_commit(store, emergency_off):
    """s3_register_purpose 须 commit_if_approved: 拒绝不写、假章 error。"""
    M.set_store(store)
    store.create_chapter(title="一")
    # declined path via commit helper
    out = M.commit_if_approved(
        "s3_register_purpose", False,
        lambda: store.update_chapter_meta(1, {"purpose_text": "x", "deltas": []}) or False,
    )
    assert out["status"] == "declined"
    # missing chapter → False → error (no written fake-green)
    out2 = M.commit_if_approved(
        "s3_register_purpose", True,
        lambda: store.update_chapter_meta(999, {"purpose_text": "x", "deltas": []}) or False,
    )
    assert out2["status"] == "error"


def test_add_character_mcp_accept_under_emergency_off(store, emergency_off):
    """Codex create author path = MCP, not REST form."""
    M.set_store(store)
    from scribe3.ontology import Entity

    def _write():
        store.add_entity(Entity("role:新角", "character", "新角"))
        return {"oid": "role:新角"}

    out = M.commit_if_approved("s3_add_character", True, _write)
    assert out["status"] == "written"
    A.set_store(store)
    client = TestClient(A.app)
    r = client.post("/characters?work=main", json={"name": "REST角"})
    assert r.status_code == 403


def test_craft_gate_throw_blocks_save(store, monkeypatch, emergency_off):
    """check_finalize_for_save raise → 503, no silent write."""
    A.set_store(store)
    store.save_chapter(1, "", title="一")

    def _boom(*a, **k):
        raise RuntimeError("gate exploded")

    monkeypatch.setattr(
        "scribe3.finalize_gate.check_finalize_for_save", _boom)
    client = TestClient(A.app)
    long_prose = "甲乙丙丁" * 200  # substantial
    r = client.post("/save-chapter?work=main", json={
        "seq": 1, "prose": long_prose, "title": "一",
    })
    assert r.status_code == 503, r.text
    body = r.json()
    detail = body.get("detail") or body
    code = detail.get("code") if isinstance(detail, dict) else None
    assert code == "finalize_gate_error" or "定稿门" in str(detail)
    # prose not updated to long_prose
    ch = store.get_chapter(1)
    assert (ch.get("prose") or "") != long_prose


def test_pending_approve_without_entity_on_default_fabric(store, monkeypatch):
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    A.set_store(store)
    # product capture style: text only, no entity
    cid = store.add_pending_authority_claim(
        "main", "辛其实是卧底细作",
        entity=None, attribute=None, value=None,
        source_type="test", source_id="src-empty-ent")
    client = TestClient(A.app)
    r = client.post(f"/memory/pending-claims/{cid}/resolve?work=main",
                    json={"decision": "approve", "valid_from": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved"
    assert body.get("fact_id")
    f = store.fact(body["fact_id"])
    assert f is not None
    assert "卧底" in (f.value or "") or "细作" in (f.value or "") or f.value


def test_pending_reject_on_default_fabric(store, monkeypatch):
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    A.set_store(store)
    cid = store.add_pending_authority_claim(
        "main", "无关揣测",
        entity=None, value=None,
        source_type="test", source_id="src-rej")
    client = TestClient(A.app)
    r = client.post(f"/memory/pending-claims/{cid}/resolve?work=main",
                    json={"decision": "reject"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
    assert r.json().get("fact_id") is None


def test_s3_reorder_signature():
    sig = inspect.signature(M.s3_reorder_chapters)
    for p in ("volume_id", "order", "work"):
        assert p in sig.parameters
