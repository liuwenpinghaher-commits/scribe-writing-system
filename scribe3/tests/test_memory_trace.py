"""Task 14:记忆溯源 trace 的持久化 + 服务端秘密屏蔽 + API 契约。

诚实边界:trace 基础设施(schema / 落库 / 屏蔽 / API)就绪,真实 trace 数据待
Task 16 检索接进生产 prompt 后填充。此处用桩 trace 数据验证 schema / 落库 / 屏蔽 / API,
不假装已有真实检索流。
"""
import json
import math

from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.memory_models import MemoryCandidate, RejectedCandidate, RetrievalResult
from scribe3.ontology import Entity, Fact
from scribe3.store import build_memory_trace, mask_memory_trace


def _patch_embed(monkeypatch):
    """确定性假 embedding(不加载真模型/服务)——检索的 bm25/vector 通道需要。"""
    def fake(texts):
        out = []
        for t in texts:
            v = [0.0] * 512
            for ch in (t or ""):
                if ch.strip():
                    v[ord(ch) % 512] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out
    monkeypatch.setattr("scribe3.embed.embed", fake)


def _enable_wiring_flags(monkeypatch):
    """统一 assembler 恒启用；测试只需打开 MEMORY_FABRIC 检索开关。"""
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")

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


# ===========================================================================
# Task 16 最后一厘米:检索发生(MEMORY_FABRIC+ASSEMBLER 开)时把 RetrievalResult
# 落 memory_trace,让 ContextInspector 有真数据。以下测试锁死接线契约。
# ===========================================================================

def _write_ctx(session_id="sess-w", revision=3, thread_id="ethread:test:1"):
    """模拟前端 WriteChat.runContextBind 发来的真实会话绑定(chat/write body)。"""
    return {"context_session_id": session_id, "context_revision": revision,
            "context_hash": "h" * 64, "thread_id": thread_id}


def test_write_path_lands_memory_trace_for_inspector(store, monkeypatch):
    """①flag 开 + 检索发生 → memory_trace 表落库 → GET /context/sessions/{id}/trace/{rev}
    返真数据(selected/channels/block_tokens)。键用【前端真实会话】,Inspector 查得到。"""
    _patch_embed(monkeypatch)
    _enable_wiring_flags(monkeypatch)
    A.set_store(store, work="test")
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:loc", "role:甲", "location", "城东", valid_from=1))
    store.add_memory_item(work="test", kind="episodic", text="甲昨夜在集市买了油纸伞",
                          scope_type="work", scope_id="test",
                          source_type="chat", source_id="turn:1")

    instr = A._assemble_write_instructions(
        store, chapter=1, focalizer="", phase="draft",
        seed_words=["集市", "油纸伞"], short_mode=False, work="test",
        memory_trace_ctx=_write_ctx("sess-w", 3))
    assert isinstance(instr, str) and instr           # 组装照常产出 prompt

    # store 侧:按 (会话, 版本) 反查到刚落的 trace
    trace = store.get_memory_trace_for_snapshot("sess-w", 3)
    assert trace is not None, "检索发生后必须落 memory_trace(Inspector 数据源)"
    assert trace["work"] == "test"
    assert trace["selected"], "至少应含 canonical 候选(领域直查)"
    assert any(s["source_kind"] == "canonical" for s in trace["selected"])
    assert "structured" in trace["channels"]          # 通道计数落库
    assert "canonical" in trace["block_tokens"]       # 块 token 落库

    # API 侧(前端 ContextInspector 走这条):同一 session/revision 返 200 真数据
    c = TestClient(A.app)
    r = c.get("/context/sessions/sess-w/trace/3?work=test")
    assert r.status_code == 200
    body = r.json()
    assert body["selected"] and body["snapshot_revision"] == 3


def test_write_path_trace_never_at_rest_secret(store, monkeypatch):
    """②含秘密候选 → trace 无秘密 value(DB at-rest)。复用 build/save 双重权威屏蔽——
    即便 retriever 漏标 provenance.secret,source_id ∈ store 权威秘密即抹空。"""
    _patch_embed(monkeypatch)
    from scribe3.context_assembler import ContextAssembler
    store.add_entity(Entity("role:z", "character", "Z"))
    store.add_fact(Fact("fact:zsec", "role:z", "真身", "Z是刺客头子", valid_from=1, secret=True))
    # 秘密候选:provenance 缺 secret 标记(模拟 retriever 漏标),但 source_id 是权威秘密
    cand = MemoryCandidate(
        source_kind="canonical", source_id="fact:zsec", work="test",
        text="Z是刺客头子的绝密明文", confidence=1.0, importance=4,
        channels={"structured"}, provenance=[{"entity": "role:z", "attribute": "真身"}])
    result = RetrievalResult(selected=[cand], rejected=[])
    snap = A._write_snapshot(store, chapter=1, focalizer="", phase="draft", work="test")
    env = ContextAssembler(store, None).assemble(snap, "", "plan")   # 真 envelope(retriever None)

    A._save_write_memory_trace(store, snap=snap, envelope=env, result=result,
                               query="Z的真身", work="test", ctx=_write_ctx("sess-z", 2))

    # 直查 DB 行(绕过 get 的兜底 mask):秘密明文绝不 at-rest
    rows = store._query(
        "SELECT selected FROM memory_trace WHERE context_session_id=$s AND snapshot_revision=$r LIMIT 1",
        {"s": "sess-z", "r": 2})
    assert rows, "trace 应已落库"
    assert "刺客" not in json.dumps(rows[0], ensure_ascii=False), "秘密明文绝不 at-rest 入 DB"
    item = rows[0]["selected"][0]
    assert item["secret"] is True and item.get("masked") is True
    assert item.get("text") in ("", None)


def test_write_path_no_trace_when_memory_fabric_off_and_byte_equivalent(store, monkeypatch):
    """③检索关 → 不落 trace(Inspector 404),且带不带 memory_trace_ctx 组装【字节等价】。"""
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    store.add_fact(Fact("fact:m", "role:m", "mood", "沉郁", valid_from=1))

    kw = dict(chapter=2, focalizer="", phase="draft", seed_words=["雨"],
              short_mode=False, work="test")
    a = A._assemble_write_instructions(store, memory_trace_ctx=None, **kw)
    b = A._assemble_write_instructions(store, memory_trace_ctx=_write_ctx("sess-off", 1), **kw)
    assert a == b, "flag 关:memory_trace_ctx 绝不改写作字节(字节等价)"
    assert store.get_memory_trace_for_snapshot("sess-off", 1) is None, "flag 关不落 trace"


def test_write_path_trace_ctx_does_not_change_prompt_bytes(store, monkeypatch):
    """flag 开时,落 trace 是纯副作用:带/不带 memory_trace_ctx 的 prompt 字节完全一致。"""
    _patch_embed(monkeypatch)
    _enable_wiring_flags(monkeypatch)
    store.add_fact(Fact("fact:loc2", "role:甲", "location", "城南", valid_from=1))

    kw = dict(chapter=1, focalizer="", phase="draft", seed_words=["城南"],
              short_mode=False, work="test")
    a = A._assemble_write_instructions(store, memory_trace_ctx=None, **kw)
    b = A._assemble_write_instructions(store, memory_trace_ctx=_write_ctx("sess-p", 5), **kw)
    assert a == b, "落 memory_trace 是纯副作用,绝不改 envelope/prompt 字节"


def test_write_path_trace_failure_does_not_block_writing(store, monkeypatch):
    """④trace 落库失败 → fail-soft,写作照常返回 prompt(与 chat_message 同纪律)。"""
    _patch_embed(monkeypatch)
    _enable_wiring_flags(monkeypatch)
    store.add_fact(Fact("fact:loc3", "role:甲", "location", "城西", valid_from=1))

    def _boom(_trace):
        raise RuntimeError("模拟落库故障")
    monkeypatch.setattr(store, "save_memory_trace", _boom)

    instr = A._assemble_write_instructions(
        store, chapter=1, focalizer="", phase="draft", seed_words=["城西"],
        short_mode=False, work="test", memory_trace_ctx=_write_ctx("sess-fail", 1))
    assert isinstance(instr, str) and instr, "trace 落库失败绝不阻断写作主链路"


def test_write_path_trace_is_idempotent_per_revision(store, monkeypatch):
    """幂等:同一 (会话, 版本) 反复写只留最新一条(trace_id 确定性 + save 先删后建)。"""
    _patch_embed(monkeypatch)
    _enable_wiring_flags(monkeypatch)
    store.add_fact(Fact("fact:loc4", "role:甲", "location", "城北", valid_from=1))

    kw = dict(chapter=1, focalizer="", phase="draft", seed_words=["城北"],
              short_mode=False, work="test", memory_trace_ctx=_write_ctx("sess-idem", 4))
    A._assemble_write_instructions(store, **kw)
    A._assemble_write_instructions(store, **kw)
    rows = store._query(
        "SELECT trace_id FROM memory_trace WHERE context_session_id=$s AND snapshot_revision=$r",
        {"s": "sess-idem", "r": 4})
    assert len(rows) == 1, f"同一快照版本应只留一条 trace,实得 {len(rows)}"


def test_assemble_retrieval_out_is_byte_equivalent(store, monkeypatch):
    """assembler 契约:传/不传 retrieval_out 收集器,envelope 字节【完全一致】——
    收集只是把已算出的 RetrievalResult(rejected/channels)顺带暴露,绝不改组装。"""
    _patch_embed(monkeypatch)
    from scribe3.context_assembler import ContextAssembler, render_envelope_text
    from scribe3.memory_retrieval import MemoryRetriever
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:loc5", "role:甲", "location", "城东", valid_from=1))
    store.add_memory_item(work="test", kind="episodic", text="甲在集市买伞",
                          scope_type="work", scope_id="test",
                          source_type="chat", source_id="turn:9")
    snap = A._write_snapshot(store, chapter=5, focalizer="", phase="final", work="test")
    asm = ContextAssembler(store, MemoryRetriever(store))

    env_no = asm.assemble(snap, "集市 伞", "write")
    out: dict = {}
    env_yes = asm.assemble(snap, "集市 伞", "write", retrieval_out=out)
    assert render_envelope_text(env_no) == render_envelope_text(env_yes)
    assert env_no.envelope_hash == env_yes.envelope_hash
    assert out.get("result") is not None            # 收集器确实拿到 RetrievalResult
    assert hasattr(out["result"], "selected") and hasattr(out["result"], "rejected")
