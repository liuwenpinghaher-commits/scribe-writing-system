"""统一上下文系统 · Task 16-B:性能缓存 + 运行指标 + feature flags 下发。

覆盖(诚实区分做实 vs 就绪):
- 【做实】embedding sha256 缓存命中 + model_version 失效(捕获恒开,生产有效)。
- 【做实】GET /capabilities 只读上报 4 个真实灰度开关；兼容键 assembler_v1
  如实表示统一内核已启用，不再受旧环境变量控制。
- 【做实】runtime-status 指标块:cross_work / memory pending·failed / spectron / 会话数,不含秘密。
- 【就绪】RetrievalResult 缓存 30s TTL + 表级失效(待 16-C 检索接进生产才有生产命中)。
- 【就绪】GlobalContextCard 缓存 work+authority_revision 60s + 正典写入失效。
"""
import json

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3 import context_cache as cc
from scribe3 import embed as E
from scribe3.memory_models import RetrievalQuery
from scribe3.memory_retrieval import MemoryRetriever


# ───────────────────────── feature flags ─────────────────────────

def test_flag_enabled_reads_env(monkeypatch):
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    # 产品默认开
    assert cc.flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is True
    for truthy in ("1", "true", "YES", "On"):
        monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", truthy)
        assert cc.flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is True
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "off")
    assert cc.flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is False


def test_capabilities_endpoint_reports_flags(monkeypatch):
    """上下文产品三件套默认开；assembler_v1 恒真；editorial 仍默认关。"""
    for f in cc.FLAGS:
        monkeypatch.delenv(f, raising=False)
    client = TestClient(A.app)
    data = client.get("/capabilities").json()
    flags = data["flags"]
    assert set(flags) >= {
        "snapshot_v1", "editorial_thread_v1", "memory_fabric_v1",
        "context_inspector_v1", "assembler_v1",
    }
    assert "spectron_shadow" not in flags
    assert flags["assembler_v1"] is True
    assert flags["snapshot_v1"] is True
    assert flags["memory_fabric_v1"] is True
    assert flags["context_inspector_v1"] is True
    assert flags["editorial_thread_v1"] is False
    assert "versions" in data
    # 显式关 → capabilities 立即翻假(测试隔离/运维关闸)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    flags2 = client.get("/capabilities").json()["flags"]
    assert flags2["memory_fabric_v1"] is False
    assert flags2["context_inspector_v1"] is True


def test_capabilities_never_leaks_secret_values(monkeypatch):
    monkeypatch.setenv("SCRIBE3_API_TOKEN", "super-secret-token-xyz")
    client = TestClient(A.app)
    blob = json.dumps(client.get("/capabilities").json(), ensure_ascii=False)
    assert "super-secret-token-xyz" not in blob


# ───────────────────────── embedding 缓存(做实)─────────────────────────

def test_embedding_cache_hit_by_sha256(monkeypatch):
    """相同规范化文本第二次命中缓存,底层只算一次(捕获恒开,省真机 embed 成本)。"""
    E.clear_cache()
    calls = {"n": 0}

    def fake_compute(texts):
        calls["n"] += len(texts)
        return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr(E, "_compute", fake_compute)
    v1 = E.embed(["王子的真名"])
    v2 = E.embed(["王子的真名"])       # 命中缓存
    assert v1 == v2
    assert calls["n"] == 1             # 只算过一次
    # 规范化:仅空白差异视为同一文本(sha256(normalized))
    E.embed(["  王子的真名  "])
    assert calls["n"] == 1


def test_embedding_cache_invalidated_by_model_version(monkeypatch):
    """model_version 变更 → 键变 → 缓存未命中重算(换模型不返回旧向量)。"""
    E.clear_cache()
    calls = {"n": 0}

    def fake_compute(texts):
        calls["n"] += len(texts)
        return [[float(calls["n"])] for _ in texts]

    monkeypatch.setattr(E, "_compute", fake_compute)
    monkeypatch.setattr(E, "model_version", lambda: "v1")
    E.embed(["同一句"])
    assert calls["n"] == 1
    monkeypatch.setattr(E, "model_version", lambda: "v2")
    E.embed(["同一句"])                # 版本变 → 重算
    assert calls["n"] == 2


def test_embedding_cache_batch_partial_hit(monkeypatch):
    E.clear_cache()
    calls = {"batches": []}

    def fake_compute(texts):
        calls["batches"].append(list(texts))
        return [[float(len(t))] for t in texts]

    monkeypatch.setattr(E, "_compute", fake_compute)
    E.embed(["甲"])
    calls["batches"].clear()
    out = E.embed(["甲", "乙丙"])       # "甲"命中,"乙丙"新算 → 只把未命中项送算
    assert calls["batches"] == [["乙丙"]]
    assert out[0] == [1.0]              # len("甲")=1,来自缓存


# ───────────────────────── TTL 缓存 + 表级失效 ─────────────────────────

def test_ttl_cache_expires(monkeypatch):
    clk = {"t": 1000.0}
    c = cc.TTLCache(30, name="unit", clock=lambda: clk["t"])
    c.set(("k",), "V", work="w")
    assert c.get(("k",)) == "V"
    clk["t"] += 31                      # 越过 TTL
    assert c.get(("k",)) is None


def test_ttl_cache_table_invalidation_is_work_scoped():
    c = cc.TTLCache(60, name="unit2", tables={"proposition"})
    cc._register_for_test(c)
    c.set(("a",), 1, work="book-a")
    c.set(("b",), 2, work="book-b")
    cc.emit_invalidation("proposition", work="book-a")
    assert c.get(("a",)) is None        # book-a 被清
    assert c.get(("b",)) == 2           # book-b 不受影响


def test_retrieval_result_cache_hit_and_table_invalidation(store, monkeypatch):
    """就绪层:同键 30s 内命中缓存;memory_item/正典表级失效后重算。
    生产统一内核只在 MEMORY_FABRIC 开启时注入检索器；本测试直接锁定缓存语义。"""
    cc.RETRIEVAL_CACHE.clear()
    r = MemoryRetriever(store)
    calls = {"n": 0}
    real = r.retrieve_full

    def spy(rq):
        calls["n"] += 1
        return real(rq)

    monkeypatch.setattr(r, "retrieve_full", spy)
    # query="" 避免向量通道加载 embedding 模型(structured 通道对空库返回空)
    rq = RetrievalQuery(work="test", snapshot={"context_hash": "h1", "chapter": 3}, query="")
    r.retrieve_full_cached(rq)
    r.retrieve_full_cached(rq)
    assert calls["n"] == 1              # 第二次命中缓存
    cc.emit_invalidation("memory_item", work="test")
    r.retrieve_full_cached(rq)
    assert calls["n"] == 2              # 表级失效后重算


def test_global_card_cache_hit_and_canonical_invalidation():
    cc.GLOBAL_CARD_CACHE.clear()
    work = "gc_perf_test"
    cc._reset_authority_for_test(work)
    calls = {"n": 0}

    def build():
        calls["n"] += 1
        return {"global": calls["n"]}

    a = cc.cached_global_card(work, build)
    b = cc.cached_global_card(work, build)
    assert a == b and calls["n"] == 1  # 60s 内命中
    rev_before = cc.authority_revision(work)
    cc.emit_invalidation("proposition", work=work)   # 正典写入
    assert cc.authority_revision(work) == rev_before + 1
    cc.cached_global_card(work, build)
    assert calls["n"] == 2             # 权威版本推进 + 缓存清 → 重算


def test_approval_and_stale_check_are_not_cached():
    """安全红线:approval 决策与 stale 检查绝不进任何缓存(键结构里不存在它们)。"""
    # 缓存只暴露 embedding / global card / retrieval 三类;无 approval/stale 缓存 API
    assert not hasattr(cc, "APPROVAL_CACHE")
    assert not hasattr(cc, "STALE_CACHE")


# ───────────────────────── runtime-status 指标 ─────────────────────────

def test_context_memory_metrics_has_real_counters_no_secrets(store):
    A.set_store(store)
    A._bump_cross_work_rejection()
    cc.reset_metrics_for_test()
    cc.record_stale_rejection()
    m = A._context_memory_metrics()
    # 当前就有真实值的指标
    assert m["cross_work_rejections"] >= 1
    assert isinstance(m["memory_events_pending"], int)
    assert isinstance(m["memory_events_failed"], int)
    assert isinstance(m["context_sessions_active"], int)
    assert "spectron_shadow" not in m
    assert "hermes_memory_provider" in m
    # 采集骨架(待 16-C 接线):键在,当前为 0/None
    assert "retrieval_p50" in m and "retrieval_p95" in m
    assert "context_tokens_p95" in m
    assert m["stale_rejections"] == 1
    # 不含 prompt / 秘密:所有值均为原始标量/浅字典,无长文本 blob
    blob = json.dumps(m, ensure_ascii=False, default=str)
    assert "prompt" not in blob.lower()
    for v in m.values():
        assert isinstance(v, (int, float, bool, str, dict, type(None)))


def test_runtime_tree_has_no_spectron_adapter_or_reserved_dependency():
    """当前 SurrealDB 是唯一记忆权威；运行时不得保留第二套适配器入口。"""
    from pathlib import Path

    root = Path(__file__).parents[1]
    forbidden_paths = (
        root / "spectron_adapter.py",
        root / "tools" / "spectron_shadow_eval.py",
        root / "tests" / "test_spectron_adapter.py",
    )
    assert not any(path.exists() for path in forbidden_paths)
    runtime_files = [
        path for path in root.rglob("*.py")
        if "tests" not in path.parts and "docs" not in path.parts
    ] + [root / "requirements-dev.txt"]
    offenders = [
        str(path.relative_to(root)) for path in runtime_files
        if "spectron" in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []


def test_runtime_status_includes_context_memory_block(store, monkeypatch):
    A.set_store(store)
    # 桩掉 Hermes 探测,避免真网络(3×5s)
    monkeypatch.setattr(
        "scribe3.hermes_runtime.HermesRuntime.probe",
        lambda self, **kw: {"profile": self.profile, "ok": True, "issues": []},
    )
    status = A._hermes_runtime_status()
    assert "context_memory" in status
    assert "cross_work_rejections" in status["context_memory"]


# ═════════════════ Task 16-C:MEMORY_FABRIC_V1 对称门控检索接线 ═════════════════
# 同一 flag 对称门控 capture(写)+ retrieval(读)。
# 产品默认开 = 捕获 + 检索进写作 envelope;显式关(env=0)= 不写不读(测试隔离)。
import math                                                    # noqa: E402

from scribe3.context_assembler import (                        # noqa: E402
    ContextAssembler,
    render_envelope_text,
)
from scribe3.ontology import Entity, Fact                      # noqa: E402


def _patch_embed(monkeypatch):
    """确定性假 embedding(与 test_memory_retrieval 同款),绝不加载真模型/服务。"""
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


def _write_envelope_text(store, *, chapter, query, focalizer=None, work="w"):
    """经真实写作组装链(_write_snapshot → ContextAssembler(注入写检索器))产出 envelope 正文。
    读到什么由 _get_write_retriever(st) 的 flag 门决定——正是本任务接线点。"""
    snap = A._write_snapshot(store, chapter=chapter, focalizer=focalizer,
                             phase="draft", work=work)
    env = ContextAssembler(store, A._get_write_retriever(store)).assemble(snap, query, "write")
    return render_envelope_text(env), env


# ---- ① flag 关:检索器 None + 捕获短路 = 零变化(字节等价证据)----

def test_get_write_retriever_attached_by_default(store, monkeypatch):
    """产品默认 fabric 开 → 写路径恒挂 MemoryRetriever(无灰度休眠)。"""
    monkeypatch.delenv("SCRIBE3_MEMORY_FABRIC_V1", raising=False)
    r = A._get_write_retriever(store)
    assert r is not None, "default-on:写检索器必须挂上"
    assert type(r).__name__ == "MemoryRetriever"


def test_get_write_retriever_none_when_fabric_explicitly_off(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    assert A._get_write_retriever(store) is None, \
        "显式关:写检索器 None(仅测试/运维隔离)"


def test_capture_symmetric_flag_gate(store, monkeypatch):
    """对称门控:默认开时 capture 放行;显式关时最前短路。"""
    import scribe3.memory_capture as mc
    calls = {"n": 0}

    def spy(self, event):
        calls["n"] += 1
        return {"skipped": True}      # 只证门控是否放行,不真跑 drain/embed

    monkeypatch.setattr(mc.MemoryCapture, "capture_event", spy)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    A._capture_turn_memory(store, work="w", thread_id="t", turn_id="c1",
                           text="作者:甲其实是暗桩,先埋着别揭穿", chapter=3)
    assert calls["n"] == 0, "显式关:捕获必须最前短路"
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    A._capture_turn_memory(store, work="w", thread_id="t", turn_id="c1",
                           text="作者:甲其实是暗桩,先埋着别揭穿", chapter=3)
    assert calls["n"] == 1, "fabric 开:捕获放行写入"


def test_capture_writes_nothing_to_db_when_fabric_off(store, monkeypatch):
    """显式关端到端零写:连 memory_event 都不落库。"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    A._capture_turn_memory(store, work="w", thread_id="t", turn_id="z1",
                           text="作者:甲其实是暗桩,先埋着", chapter=3)
    assert store.count_memory_events() == 0, "fabric 关:不得写入任何记忆事件"


def test_memory_absent_from_write_envelope_when_fabric_off(store, monkeypatch):
    """MEMORY_FABRIC 显式关 → 检索器 None → 经验记忆不进统一 envelope。"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    store.add_memory_item(work="w", kind="episodic",
                          text="甲在城西暗巷向盐帮递了口信", known_from=1,
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:1")
    text, _ = _write_envelope_text(store, chapter=6, query="城西 盐帮 口信")
    assert "城西暗巷向盐帮递了口信" not in text
    assert A._get_write_retriever(store) is None


# ---- ② flag 开:检索进写作 envelope(经 Task 8 检索器)----

def test_get_write_retriever_wired_when_fabric_on(store, monkeypatch):
    from scribe3.memory_retrieval import MemoryRetriever as _MR
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    assert isinstance(A._get_write_retriever(store), _MR), \
        "fabric 开:写检索器接 Task 8 MemoryRetriever"


def test_memory_retrieved_into_write_envelope_when_fabric_on(store, monkeypatch):
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    store.add_memory_item(work="w", kind="episodic",
                          text="甲在城西暗巷向盐帮递了口信", known_from=1,
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:1")
    text, _ = _write_envelope_text(store, chapter=6, query="城西 盐帮 口信")
    assert "城西暗巷向盐帮递了口信" in text, "接线后经验记忆应经检索进入写作 envelope"


# ---- ③ 剧透门(known_from):写第 5 章挡住 known_from=20 的记忆 ----

def test_write_envelope_spoiler_gate_blocks_future_memory(store, monkeypatch):
    """核心红线:known_from=20 记忆写第 5 章不进 envelope、写第 25 章才进。
    本测试同时锁死缓存正确性——若缓存键漏掉 chapter 维度,ch5 缓存会被 ch25 命中而穿帮。"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    store.add_memory_item(work="w", kind="episodic",
                          text="盐帮总舵真正藏在城北枯井之下", known_from=20,
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:20")
    q = "盐帮 总舵 城北 枯井"
    early, _ = _write_envelope_text(store, chapter=5, query=q)
    assert "城北枯井" not in early, "写第 5 章:known_from=20 记忆必须被剧透门挡在 envelope 外"
    late, _ = _write_envelope_text(store, chapter=25, query=q)
    assert "城北枯井" in late, "写第 25 章:known_from=20 已满足,记忆应进入 envelope"


def test_spoiler_gate_survives_cache_key_isolation(store, monkeypatch):
    """回归锁:同 work+query 下,ch25 先检索(缓存)再 ch5 检索——ch5 绝不得命中 ch25 缓存。
    (canonical_payload 不含 context_hash,缓存键须回退整份快照 sha256 才能按章隔离。)"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    store.add_memory_item(work="w", kind="episodic",
                          text="盐帮总舵真正藏在城北枯井之下", known_from=20,
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:20")
    q = "盐帮 总舵 城北 枯井"
    late, _ = _write_envelope_text(store, chapter=25, query=q)   # 先让 ch25 结果进缓存
    assert "城北枯井" in late
    early, _ = _write_envelope_text(store, chapter=5, query=q)   # ch5 必须另起一把键
    assert "城北枯井" not in early, "剧透门不得被缓存击穿:ch5 不得命中 ch25 缓存"


# ---- ④ 秘密屏蔽(C1):秘密 value 物理不入 envelope ----

def test_write_envelope_masks_secret_fact_value(store, monkeypatch):
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:truename", "role:甲", "真名", "元十三郎",
                        valid_from=1, secret=True))
    text, env = _write_envelope_text(store, chapter=6, query="甲 真名")
    assert "元十三郎" not in text, "秘密 value 必须物理屏蔽,绝不入写作 envelope"
    masked = [s.source_id for b in env.blocks for s in b.sources if s.masked]
    assert masked, "被屏蔽秘密源须留痕 masked=True(限知留痕范式)"


# ---- ⑤ work 隔离:跨书记忆不串 ----

def test_write_retrieval_is_work_scoped(store, monkeypatch):
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    store.add_memory_item(work="other-book", kind="episodic",
                          text="另一本书的机密线索不可外泄", known_from=1,
                          scope_type="work", scope_id="other-book",
                          source_type="chat", source_id="turn:x")
    text, _ = _write_envelope_text(store, chapter=6, query="机密 线索", work="w")
    assert "另一本书的机密线索" not in text, "跨书记忆不得串入本书写作 envelope"


# ---- ⑥ 缓存 + 指标接入 ----

def test_retrieve_wires_cache_and_latency_metric(store, monkeypatch):
    """retrieve() 走 retrieve_full_cached:同键第二次命中缓存(retrieve_full 只算一次),
    且 miss 分支填 record_retrieval_latency(retrieval_p50/p95 从 0 变真实)。"""
    _patch_embed(monkeypatch)
    r = MemoryRetriever(store)
    calls = {"n": 0}
    real = r.retrieve_full

    def spy(rq):
        calls["n"] += 1
        return real(rq)

    monkeypatch.setattr(r, "retrieve_full", spy)
    snap = {"work": "w", "chapter": 6, "context_hash": "wh1"}
    r.retrieve("w", snap, "城西 盐帮", k=10)
    r.retrieve("w", snap, "城西 盐帮", k=10)
    assert calls["n"] == 1, "retrieve 应走带缓存路径:同键第二次命中不重算"
    assert cc.metrics_snapshot()["retrieval_samples"] >= 1, "miss 分支须记检索延迟"


def test_context_tokens_recorded_on_unified_assembly(store, monkeypatch):
    """统一内核接线 record_context_tokens:context_tokens_p95/samples 由 0 变真实。"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    instr = A._assemble_write_instructions(
        store, chapter=6, focalizer="", phase="draft",
        seed_words=[], short_mode=False, work="w")
    assert instr
    assert cc.metrics_snapshot()["context_tokens_samples"] >= 1, \
        "统一内核应采样 envelope token 估算"


# ═════ I1 哨兵:半空转真修复 —— 真生产组装函数(seed_words 作 query)读通经验回路 ═════
# 关键:驱动真 _assemble_write_instructions(生产入口),不走测试辅助注入的有意义 query。
# 生产原为 assemble(snap,"",...) 空 query → bm25/vector 硬返 [] → episodic/working 全空,
# 只 canonical(retriever=None 降级即可得)浮现;I1 用 seed_words/章纲作 query 把经验回路读通。

def test_experiential_memory_read_into_prompt_via_production_path(store, monkeypatch):
    """半空转真修复哨兵:MEMORY_FABRIC 开 + seed_words → episodic 记忆真进生产 prompt。
    断言整句(非种子词碎片,soak 块只回显种子词)——证明记忆经检索进入,而非种子回声。"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    store.add_memory_item(work="w", kind="episodic",
                          text="甲在城西暗巷向盐帮递了口信", known_from=1,
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:1")
    instr = A._assemble_write_instructions(
        store, chapter=6, focalizer="", phase="draft",
        seed_words=["城西", "盐帮", "口信"], short_mode=False, work="w")
    assert "甲在城西暗巷向盐帮递了口信" in instr, \
        "经验回路读通:seed_words 作 query,episodic 记忆经检索进入生产写作 prompt(不只 canonical)"


def test_spoiler_gate_holds_under_meaningful_query_production_path(store, monkeypatch):
    """有意义 query 也不得绕过 known_from 门:known_from=20 记忆写 ch5 仍被剧透门挡在 prompt 外。"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    store.add_memory_item(work="w", kind="episodic",
                          text="盐帮总舵真正藏在城北枯井之下", known_from=20,
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:20")
    seeds = ["盐帮", "总舵", "城北", "枯井"]
    early = A._assemble_write_instructions(
        store, chapter=5, focalizer="", phase="draft",
        seed_words=seeds, short_mode=False, work="w")
    assert "盐帮总舵真正藏在城北枯井之下" not in early, \
        "有意义 query 下,known_from=20 记忆写 ch5 仍须被剧透门挡在生产 prompt 外"
    late = A._assemble_write_instructions(
        store, chapter=25, focalizer="", phase="draft",
        seed_words=seeds, short_mode=False, work="w")
    assert "盐帮总舵真正藏在城北枯井之下" in late, \
        "写 ch25:known_from=20 已满足,记忆进生产 prompt(证明确是 known 门而非检索失灵)"


def test_production_path_byte_equivalent_when_fabric_off(store, monkeypatch):
    """MEMORY_FABRIC 显式关时 retriever=None、query 为空，经验记忆不进 prompt。"""
    _patch_embed(monkeypatch)
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "0")
    store.add_memory_item(work="w", kind="episodic",
                          text="甲在城西暗巷向盐帮递了口信", known_from=1,
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:1")
    instr = A._assemble_write_instructions(
        store, chapter=6, focalizer="", phase="draft",
        seed_words=["城西", "盐帮", "口信"], short_mode=False, work="w")
    assert "甲在城西暗巷向盐帮递了口信" not in instr, "fabric 关:经验记忆不得进 prompt"
    assert "作者此刻问" not in instr, "fabric 关:query 仍空,focus 块不得出现检索 query 回显"


def test_build_write_retrieval_query_prefers_seed_words_then_synopsis(store):
    """query 源:seed_words 优先(最自然靶向)→ 无则退章纲 synopsis → 都无则空串(不崩)。"""
    # ① seed_words 优先
    assert A._build_write_retrieval_query(
        store, chapter=1, seed_words=["寒气", "刑讯"]) == "寒气 刑讯"
    # ② 无种子词 → 退章纲 synopsis
    store.save_chapter(3, "正文", title="三", focalizer=None)
    store.update_chapter_meta(3, {"synopsis": "甲夜探盐帮总舵"})
    assert A._build_write_retrieval_query(store, chapter=3, seed_words=[]) == "甲夜探盐帮总舵"
    # ③ 无种子词无章纲 → 空串兜底(保守退化为只出 canonical,不崩)
    assert A._build_write_retrieval_query(store, chapter=999, seed_words=[]) == ""


# ═════ M1/M2:记忆写入 / 作废 的缓存失效对称(I1 修后成真窗口,连带补齐)═════

def test_add_memory_item_emits_cache_invalidation(store, monkeypatch):
    """M2:新记忆写入发 memory_item 表级失效 → RETRIEVAL_CACHE 同 work 被清(新记忆无 ≤30s 延迟)。"""
    _patch_embed(monkeypatch)
    r = MemoryRetriever(store)
    snap = {"work": "w", "chapter": 9, "context_hash": "h-m2"}
    r.retrieve("w", snap, "刺客 蹲守", k=10)                 # 建缓存条目(work=w)
    key = cc.retrieval_key("w", "h-m2", "刺客 蹲守")
    assert cc.RETRIEVAL_CACHE.get(key) is not None, "前置:检索结果应已缓存"
    store.add_memory_item(work="w", kind="episodic", text="刺客在屋脊蹲守整夜",
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:new")
    assert cc.RETRIEVAL_CACHE.get(key) is None, "M2:新记忆写入应清同 work 检索缓存"


def test_invalidate_memory_emits_cache_invalidation(store, monkeypatch):
    """M1:作废记忆发 memory_item 表级失效 → 已作废记忆不在 RETRIEVAL_CACHE 残留 ≤30s。"""
    _patch_embed(monkeypatch)
    mid = store.add_memory_item(work="w", kind="episodic", text="甲曾在城西现身",
                                scope_type="work", scope_id="w",
                                source_type="chat", source_id="turn:inv")
    r = MemoryRetriever(store)
    snap = {"work": "w", "chapter": 9, "context_hash": "h-m1"}
    r.retrieve("w", snap, "甲 城西", k=10)                    # add 的 emit 在前,此处重新缓存
    key = cc.retrieval_key("w", "h-m1", "甲 城西")
    assert cc.RETRIEVAL_CACHE.get(key) is not None, "前置:检索结果应已缓存"
    store.invalidate_memory(mid)
    assert cc.RETRIEVAL_CACHE.get(key) is None, \
        "M1:作废记忆应清同 work 检索缓存(否则已作废记忆缓存命中倒灌 prompt ≤30s)"
