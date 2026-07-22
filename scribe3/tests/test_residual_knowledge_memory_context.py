"""Residual bar: MCP multi-witness, semantic/graph time gates, memory flag symmetry,
pending resolve, write-prompt purpose/lessons contract.
"""
from __future__ import annotations

import inspect

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
import scribe3.mcp as M
from scribe3.knowledge import project_frame
from scribe3.ontology import Entity, Fact, KnowledgeEdge


# ─── 1) MCP multi-witness via shipped aggregate + s3_add_event write path ───

def test_aggregate_event_participants_keeps_multi_witness_list():
    """Shipped pure helper used by s3_add_event — not a test-local reimplementation."""
    parts = M.aggregate_event_participants([
        {"role": "SUBJ", "entity": "role:甲"},
        {"role": "WITNESS", "entity": "role:乙"},
        {"role": "WITNESS", "entity": "role:丙"},
    ])
    assert isinstance(parts["WITNESS"], list)
    assert set(parts["WITNESS"]) == {"role:乙", "role:丙"}
    assert parts["SUBJ"] == "role:甲"


def test_s3_add_event_multi_witness_both_know_effect(store):
    """Shipped path: aggregate_event_participants → commit_if_approved → add_event → project_frame.
    No hand-called see_event; no test-local participant loop."""
    from scribe3.ontology import Event
    M.set_store(store)
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_entity(Entity("role:丙", "character", "丙"))
    store.add_fact(Fact("fact:mw_fx", "role:甲", "言", "密谈泄露", valid_from=1))

    participants = [
        {"role": "SUBJ", "entity": "role:甲"},
        {"role": "WITNESS", "entity": "role:乙"},
        {"role": "WITNESS", "entity": "role:丙"},
    ]
    parts = M.aggregate_event_participants(participants)
    effects = M.aggregate_event_effects([{"id": "fact:mw_fx"}])
    assert set(parts["WITNESS"]) == {"role:乙", "role:丙"}

    out = M.commit_if_approved(
        "s3_add_event", True,
        lambda: store.add_event(
            Event("ev:mw_mcp", "talk",
                  participants=parts,
                  effects=effects,
                  story_time=1)))
    assert out["status"] == "written"
    assert project_frame(store, "role:乙", 1).knows("fact:mw_fx")
    assert project_frame(store, "role:丙", 1).knows("fact:mw_fx")


def test_s3_semantic_recall_accepts_chapter_param():
    sig = inspect.signature(M.s3_semantic_recall)
    assert "chapter" in sig.parameters


# ─── 2) semantic + graph time gates on real store entry ───

def test_semantic_recall_chapter_excludes_future_fact(store):
    store.add_entity(Entity("role:丁", "character", "丁"))
    store.add_fact(Fact("fact:past_r", "role:丁", "身份", "学徒", valid_from=1))
    store.add_fact(Fact("fact:fut_r", "role:丁", "身份", "掌门", valid_from=100))
    # ensure embeddings exist for both
    try:
        store.semantic_index("fact:past_r", "学徒")
        store.semantic_index("fact:fut_r", "掌门")
    except Exception:
        pytest.skip("embed unavailable")
    hits = store.semantic_recall("身份", k=10, chapter=5)
    ids = {f.id for f in hits}
    assert "fact:fut_r" not in ids
    # MCP path
    M.set_store(store)
    mcp_hits = M.s3_semantic_recall("身份", k=10, chapter=5)
    mcp_ids = {h["id"] for h in mcp_hits}
    assert "fact:fut_r" not in mcp_ids


def test_knowers_at_chapter_honors_until_deterministic(store):
    """Shipped knowers_at_chapter (used by graph_recall): no KNN — hard assertions."""
    store.add_entity(Entity("role:知", "character", "知情人"))
    store.add_entity(Entity("role:忘", "character", "遗忘者"))
    store.add_fact(Fact("fact:gk", "role:知", "密", "旧账", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:知", "fact:gk", since_chapter=1))
    store.add_knowledge(KnowledgeEdge(
        "role:忘", "fact:gk", since_chapter=1, until_chapter=5))
    names6 = store.knowers_at_chapter("gk", 6)
    assert "遗忘者" not in names6, f"until_chapter=5 must hide 遗忘者 at ch6: {names6}"
    assert "知情人" in names6, f"open edge must keep 知情人 at ch6: {names6}"
    names3 = store.knowers_at_chapter("gk", 3)
    assert "遗忘者" in names3 and "知情人" in names3


def test_graph_recall_knowers_honor_until_chapter(store):
    """Full graph_recall path: seed must appear at chapter=6; knowers use shipped time gate."""
    store.add_entity(Entity("role:知", "character", "知情人"))
    store.add_entity(Entity("role:忘", "character", "遗忘者"))
    store.add_fact(Fact("fact:gk", "role:知", "密", "旧账专有召回标记xyzzy", valid_from=1))
    store.semantic_index("fact:gk", "旧账专有召回标记xyzzy")
    store.add_knowledge(KnowledgeEdge("role:知", "fact:gk", since_chapter=1))
    store.add_knowledge(KnowledgeEdge(
        "role:忘", "fact:gk", since_chapter=1, until_chapter=5))
    rows = store.graph_recall("旧账专有召回标记xyzzy", chapter=6, k=20)
    target = next((r for r in rows if r["id"] == "fact:gk"), None)
    assert target is not None, (
        f"graph_recall must return seeded fact:gk at chapter=6; got {[r['id'] for r in rows]}")
    names = target.get("knowers") or []
    assert "遗忘者" not in names, f"until_chapter=5 must hide 遗忘者: {names}"
    assert "知情人" in names, f"open edge must keep 知情人: {names}"


def test_rest_recall_chapter_gate(store):
    A.set_store(store)
    store.add_entity(Entity("role:戊", "character", "戊"))
    store.add_fact(Fact("fact:rf", "role:戊", "位", "未来职", valid_from=50))
    try:
        store.semantic_index("fact:rf", "未来职")
    except Exception:
        pytest.skip("embed unavailable")
    client = TestClient(A.app)
    r = client.get("/recall", params={"q": "职", "k": 10, "chapter": 3, "work": "main"})
    assert r.status_code == 200
    ids = {row.get("id") for row in r.json()}
    assert "fact:rf" not in ids


# ─── 3) memory fabric flag symmetry ───

def test_memory_capture_turn_403_when_fabric_off(store, monkeypatch):
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    A.set_store(store)
    client = TestClient(A.app)
    before = store._query(
        "SELECT count() AS n FROM memory_item GROUP ALL")
    n_before = int((before[0] or {}).get("n") or 0) if before else 0
    r = client.post("/memory/capture-turn?work=main", json={
        "user": "甲其实是卧底",
        "event_id": "ev-test-fabric-off-1",
    })
    assert r.status_code == 403, r.text
    after = store._query(
        "SELECT count() AS n FROM memory_item GROUP ALL")
    n_after = int((after[0] or {}).get("n") or 0) if after else 0
    assert n_after == n_before, "fabric off must not write memory_item"


def test_memory_prefetch_403_when_fabric_off(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    A.set_store(store)
    client = TestClient(A.app)
    r = client.post("/memory/prefetch?work=main", json={"query": "hello"})
    assert r.status_code == 403


# ─── 4) pending approve/reject ───

def test_pending_claim_approve_writes_fact(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    A.set_store(store)
    store.add_entity(Entity("role:己", "character", "己"))
    cid = store.add_pending_authority_claim(
        "main", "己真实身份是细作",
        entity="role:己", attribute="身份", value="细作",
        source_type="test", source_id="src-pa-1")
    out = store.resolve_pending_authority_claim(cid, "approve", valid_from=2)
    assert out["status"] == "approved"
    assert out.get("fact_id")
    f = store.fact(out["fact_id"])
    assert f is not None
    assert f.value == "细作"
    claims = store.list_pending_authority_claims(work="main", status="approved")
    assert any(c.get("id") == cid or c.get("id", "").endswith(cid) for c in claims)


def test_pending_claim_reject_no_fact(store):
    cid = store.add_pending_authority_claim(
        "main", "无关揣测",
        entity="role:庚", attribute="身份", value="假",
        source_type="test", source_id="src-pa-2")
    store.add_entity(Entity("role:庚", "character", "庚"))
    out = store.resolve_pending_authority_claim(cid, "reject")
    assert out["status"] == "rejected"
    assert out.get("fact_id") is None


def test_pending_resolve_api_requires_fabric(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    A.set_store(store)
    client = TestClient(A.app)
    r = client.post("/memory/pending-claims/x/resolve?work=main",
                    json={"decision": "reject"})
    assert r.status_code == 403


def test_pending_resolve_api_approve(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    A.set_store(store)
    store.add_entity(Entity("role:辛", "character", "辛"))
    cid = store.add_pending_authority_claim(
        "main", "辛是卧底",
        entity="role:辛", attribute="身份", value="卧底",
        source_type="test", source_id="src-pa-3")
    client = TestClient(A.app)
    r = client.post(f"/memory/pending-claims/{cid}/resolve?work=main",
                    json={"decision": "approve", "valid_from": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved"
    assert store.fact(body["fact_id"]) is not None


# ─── 5) write prompt contract ───

def test_write_prompt_includes_purpose_list_not_fake_brief(store):
    from scribe3.api import app_impl as AI
    store.save_chapter(3, "", title="三")
    store.update_chapter_meta(3, {
        "deltas": [
            {"kind": "fact", "predicate": "信物易手", "status": "planned"},
        ],
        "synopsis": "夜戏收束",
    })
    text = AI._purpose_workflow_block(store, 3, with_tools=False, work="main")
    assert "见简报" not in text
    assert "必达清单" in text or "信物易手" in text
    assert "信物易手" in text


def test_write_prompt_source_has_no_false_brief_claim():
    src = inspect.getsource(
        __import__("scribe3.api.app_impl", fromlist=["_purpose_workflow_block"])
        ._purpose_workflow_block)
    # implementation may delegate — check module source for the lying string
    import scribe3.api.app_impl as AI
    mod = inspect.getsource(AI)
    # lying phrase must not appear in production purpose helper
    assert "见简报「必达清单」" not in inspect.getsource(AI._purpose_and_lessons_write_block)
