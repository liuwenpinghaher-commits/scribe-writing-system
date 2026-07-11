"""Task 14:记忆溯源 trace 的持久化 + 服务端秘密屏蔽 + API 契约。

诚实边界:trace 基础设施(schema / 落库 / 屏蔽 / API)就绪,真实 trace 数据待
Task 16 检索接进生产 prompt 后填充。此处用桩 trace 数据验证 schema / 落库 / 屏蔽 / API,
不假装已有真实检索流。
"""
import json

from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.memory_models import MemoryCandidate, RejectedCandidate, RetrievalResult
from scribe3.store import build_memory_trace, mask_memory_trace

REJECT_REASONS = {
    "token_budget", "duplicate", "superseded",
    "conflicts_with_canonical", "wrong_work", "wrong_time",
}


def _stub_trace(trace_id="trace-1", *, secret=False):
    """桩 trace(模拟 Task 16 接线后一次检索的溯源)。secret=True 时选入证据携私密。"""
    return {
        "trace_id": trace_id,
        "work": "test",
        "thread_id": "ethread:test:1",
        "context_session_id": "sess-1",
        "snapshot_revision": 7,
        "snapshot_hash": "snaphash",
        "envelope_hash": "envhash",
        "query": "柳怀玉的来历",
        "channels": {"structured": 2, "bm25": 3, "vector": 3, "graph": 1},
        "selected": [
            {"source_id": "fact:origin", "source_kind": "canonical",
             "reason": "canonical", "confidence": 1.0, "importance": 4,
             "observed_at": None, "secret": secret,
             "text": ("柳怀玉的真实身份是前朝遗孤" if secret else "柳怀玉是铜炉旁的孤儿"),
             "channels": ["structured"]},
        ],
        "rejected": [
            {"source_id": "mem:99", "source_kind": "episodic",
             "reason": "conflicts_with_canonical", "confidence": 0.6,
             "observed_at": "2026-07-10T00:00:00+00:00", "secret": False,
             "text": "某段被正典压制的传闻"},
        ],
        "block_tokens": {"global": 40, "canonical": 120, "recent": 80,
                         "procedural": 0, "reference": 0, "uncertainty": 0},
        "latency_ms": {"total": 42, "retrieve": 30, "fuse": 12},
        "response_id": None,
        "run_id": None,
    }


def test_memory_trace_explains_selected_and_rejected_candidates(store):
    """计划 Step 1:trace 解释"选了什么、为什么"与"弃了什么、为什么"。"""
    store.save_memory_trace(_stub_trace("trace-1"))
    trace = store.get_memory_trace("trace-1")
    assert trace["snapshot_revision"] == 7
    assert trace["selected"][0]["source_id"]
    assert trace["selected"][0]["reason"]
    assert trace["rejected"][0]["reason"] in REJECT_REASONS
    assert trace["latency_ms"]["total"] >= 0


def test_memory_trace_lookup_by_session_and_revision(store):
    """API 端点的自然键(会话 + 快照版本)可反查 trace。"""
    store.save_memory_trace(_stub_trace("trace-2"))
    trace = store.get_memory_trace_for_snapshot("sess-1", 7)
    assert trace is not None
    assert trace["trace_id"] == "trace-2"
    # 通道/块 token 结构完整回读
    assert trace["channels"]["structured"] == 2
    assert trace["block_tokens"]["canonical"] == 120


def test_memory_trace_missing_returns_none(store):
    assert store.get_memory_trace("nope") is None
    assert store.get_memory_trace_for_snapshot("nope", 1) is None


def test_secret_value_never_enters_trace(store):
    """限知红线:私密证据的 value/text 在服务端(落库前)权威屏蔽,DB 与回读都不含明文。"""
    store.save_memory_trace(_stub_trace("trace-secret", secret=True))
    trace = store.get_memory_trace("trace-secret")
    item = trace["selected"][0]
    assert item["secret"] is True
    assert item.get("masked") is True
    assert item.get("text") in ("", None)
    assert "真实身份" not in json.dumps(trace, ensure_ascii=False)


def test_build_memory_trace_masks_secret_from_provenance():
    """build_memory_trace:RetrievalResult → trace,secret 由 provenance 判定并屏蔽。"""
    sel = MemoryCandidate(
        source_kind="canonical", source_id="fact:s", work="test",
        text="绝密真相全文", confidence=1.0, importance=4,
        provenance=[{"entity": "role:甲", "attribute": "身份", "secret": True}])
    rej = RejectedCandidate(
        candidate=MemoryCandidate(
            source_kind="episodic", source_id="mem:1", work="test", text="传闻"),
        reason="conflicts_with_canonical")
    result = RetrievalResult(selected=[sel], rejected=[rej])
    trace = build_memory_trace(
        trace_id="t", work="test", thread_id="th", context_session_id="s",
        snapshot_revision=3, result=result, query="q",
        latency_ms={"total": 5})
    s0 = trace["selected"][0]
    assert s0["secret"] is True
    assert s0["text"] in ("", None)
    assert "绝密" not in json.dumps(trace, ensure_ascii=False)
    assert trace["rejected"][0]["reason"] == "conflicts_with_canonical"
    assert trace["latency_ms"]["total"] == 5


def test_secret_never_at_rest_when_store_authority_and_provenance_unflagged(store):
    """必修1(at-rest 不变量,C1 对齐):候选 provenance【缺】secret 标记(retriever 漏标),
    但 source_id 是 store 权威秘密。save 后【直接 SELECT memory_trace 行】(绕过 get 的兜底
    mask)断言:秘密明文绝不 at-rest 入 DB,权威判定回写 secret=True。

    删掉 save_memory_trace 落库前的 store 权威屏蔽,本测试会红——现有从"会重掩的读路径"
    观测的秘密测试删掉落库前屏蔽仍会绿(get 兜底重掩),故必须直查 DB 行。"""
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:x", "character", "X"))
    store.add_fact(Fact("fact:sec", "role:x", "真身", "X其实是狐妖", valid_from=1, secret=True))
    trace = {
        "trace_id": "at-rest-secret", "work": "test", "thread_id": "ethread:test:1",
        "context_session_id": "sess-atrest", "snapshot_revision": 3, "query": "X的真身",
        "channels": {"structured": 1},
        "selected": [{
            "source_id": "fact:sec", "source_kind": "canonical", "reason": "canonical",
            "confidence": 1.0, "importance": 4, "secret": False,   # ← retriever 漏标
            "text": "X的真身其实是狐妖(retriever 漏标的绝密明文)",
            "provenance": [{"entity": "role:x", "attribute": "真身"}],
        }],
        "rejected": [], "block_tokens": {"canonical": 30}, "latency_ms": {"total": 3},
    }
    store.save_memory_trace(trace)
    # 直接查 DB 行——不经 get_memory_trace 的兜底 mask
    rows = store._query(
        "SELECT selected, rejected FROM memory_trace WHERE trace_id=$t LIMIT 1",
        {"t": "at-rest-secret"})
    assert rows, "trace 应已落库"
    raw = rows[0]
    assert "狐妖" not in json.dumps(raw, ensure_ascii=False), "秘密明文绝不 at-rest 入 DB"
    item = raw["selected"][0]
    assert item["secret"] is True                    # store 权威判定回写
    assert item.get("masked") is True
    assert item.get("text") in ("", None)


def test_build_memory_trace_with_store_masks_unflagged_secret(store):
    """必修1:build_memory_trace 传 store 时,retriever 漏标(provenance 无 secret)的 store
    权威秘密也在构建期屏蔽(Task 16 接线口径:传 store 即不漏)。"""
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:y", "character", "Y"))
    store.add_fact(Fact("fact:y", "role:y", "真身", "Y是刺客", valid_from=1, secret=True))
    cand = MemoryCandidate(
        source_kind="canonical", source_id="fact:y", work="test",
        text="Y其实是刺客的绝密明文", confidence=1.0, importance=4,
        provenance=[{"entity": "role:y", "attribute": "真身"}])   # 缺 secret 标记
    result = RetrievalResult(selected=[cand], rejected=[])
    trace = build_memory_trace(
        trace_id="t-store", work="test", thread_id="th", context_session_id="s",
        snapshot_revision=3, result=result, query="q", store=store)
    s0 = trace["selected"][0]
    assert s0["secret"] is True                       # store 权威判定,非 provenance
    assert s0["text"] in ("", None)
    assert "刺客" not in json.dumps(trace, ensure_ascii=False)


def test_mask_memory_trace_is_idempotent():
    """mask 幂等:重复屏蔽不误伤非私密证据、不复原私密。"""
    raw = _stub_trace("t", secret=True)
    once = mask_memory_trace(raw)
    twice = mask_memory_trace(once)
    assert twice["selected"][0].get("text") in ("", None)
    assert twice["rejected"][0]["text"] == "某段被正典压制的传闻"


def test_trace_api_returns_masked_trace(store):
    """GET /context/sessions/{id}/trace/{revision} 返回服务端已屏蔽的 trace。"""
    A.set_store(store, work="test")
    store.save_memory_trace(_stub_trace("trace-api", secret=True))
    c = TestClient(A.app)
    r = c.get("/context/sessions/sess-1/trace/7?work=test")
    assert r.status_code == 200
    body = r.json()
    item = body["selected"][0]
    assert item["secret"] is True
    assert "真实身份" not in json.dumps(body, ensure_ascii=False)


def test_trace_api_404_when_absent(store):
    A.set_store(store, work="test")
    c = TestClient(A.app)
    r = c.get("/context/sessions/none/trace/1?work=test")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "memory_trace_not_found"
