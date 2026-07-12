"""Task 8 · 统一多通道 MemoryRetriever 测试。

分两层:
1) 纯函数层(fuse/RRF/final_score/正典压制)——不碰 DB,毫秒级,是本任务的核心契约。
2) store-backed 冒烟层——验证四通道真机取数 + Task 7 retriever 协议对齐;
   铁律:绝不真调 embedding 服务,一律 monkeypatch scribe3.embed.embed。
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

from scribe3.memory_models import MemoryCandidate, RetrievalQuery, RetrievalResult
from scribe3.memory_retrieval import (
    MemoryRetriever,
    channel_weights,
    final_score,
    fuse,
    half_life_days,
    reciprocal_rank_fusion,
)
from scribe3.ontology import Entity, Fact

NOW = datetime(2026, 7, 10, tzinfo=timezone.utc)


# ---------- 纯函数测试助手 ----------

def _cand(source_id: str, source_kind: str = "working", **kw) -> MemoryCandidate:
    kw.setdefault("text", source_id)
    kw.setdefault("work", "w")
    if source_kind != "canonical":
        kw.setdefault("observed_at", NOW)   # 经验候选衰减需要 observed_at
    return MemoryCandidate(source_id=source_id, source_kind=source_kind, **kw)


def retriever(**channels) -> RetrievalResult:
    """测试助手:把各通道的 id 列表直接喂给纯 fuse,得 RetrievalResult。"""
    ids = {i for lst in channels.values() for i in lst}
    cands = {i: _cand(i) for i in ids}
    return fuse(channels, cands, now=NOW, focus_ids=set())


def fact(entity: str, attribute: str, value: str, valid_from: int) -> MemoryCandidate:
    """场景 canonical:城东事实。provenance 带 (entity,attribute) 供正典压制判定。
    canonical 来自领域表(不进 memory_item),observed_at 恒 None。"""
    return MemoryCandidate(
        source_kind="canonical", source_id="fact:location-east",
        text=f"{entity} 的 {attribute} 是 {value}", work="w",
        confidence=1.0, importance=4,
        provenance=[{"entity": entity, "attribute": attribute}],
    )


def episode(text: str, observed_at: str) -> MemoryCandidate:
    """与上面 canonical 同 (entity,attribute)=(role:a,location) → 应被正典压制。"""
    return MemoryCandidate(
        source_kind="episodic", source_id="ep:west", text=text, work="w",
        observed_at=datetime.fromisoformat(observed_at).replace(tzinfo=timezone.utc),
        provenance=[{"entity": "role:a", "attribute": "location"}],
    )


def retrieve_with(canonical: MemoryCandidate, episodic: MemoryCandidate) -> RetrievalResult:
    cands = {canonical.source_id: canonical, episodic.source_id: episodic}
    channels = {"structured": [canonical.source_id], "vector": [episodic.source_id]}
    return fuse(channels, cands, now=NOW, focus_ids=set())


# ---------- 计划原文两条核心失败测试 ----------

def test_rrf_combines_structured_bm25_vector_and_graph():
    result = retriever(structured=["a"], bm25=["b", "a"], vector=["c", "a"], graph=["d", "a"])
    assert result.ids[0] == "a"
    assert result.by_id("a").channels == {"structured", "bm25", "vector", "graph"}


def test_canonical_candidate_suppresses_conflicting_episode():
    result = retrieve_with(
        canonical=fact("role:a", "location", "城东", valid_from=8),
        episodic=episode("甲还在城西", observed_at="2026-07-01"),
    )
    assert result.selected_ids == ["fact:location-east"]
    assert result.rejected[0].reason == "conflicts_with_canonical"


# ---------- RRF 纯函数 ----------

def test_rrf_weights_structured_channel_higher():
    """structured 通道权重 2.0 > 其余;同 rank 下 structured 命中得分更高。"""
    scores = reciprocal_rank_fusion({"structured": ["x"], "bm25": ["y"]})
    assert scores["x"] > scores["y"]
    assert channel_weights()["structured"] == 2.0


# ---------- 分类衰减 / 冲突顺序 ----------

def test_canonical_final_score_pins_above_experiential():
    """canonical 恒 rrf+1.0 置顶,压过任何经验候选。"""
    canon = _cand("fact:c", "canonical")
    canon.rrf_score = 0.01
    work = _cand("mem:w", "working", importance=5, confidence=1.0)
    work.rrf_score = 0.9
    assert final_score(canon, NOW, set()) > final_score(work, NOW, set())


def test_decay_working_faster_than_procedural():
    """同龄下 working(半衰期3天)衰减快于 procedural(180天)。"""
    old = datetime(2026, 6, 20, tzinfo=timezone.utc)   # 20 天前
    w = _cand("mem:w", "working", observed_at=old)
    w.rrf_score = 1.0
    p = _cand("mem:p", "procedural", observed_at=old)
    p.rrf_score = 1.0
    assert final_score(p, NOW, set()) > final_score(w, NOW, set())
    assert half_life_days()["working"] < half_life_days()["procedural"]


def test_pinned_skips_decay():
    """pinned 候选不衰减(decay=1.0)且叠加 pin_bonus。"""
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pinned = _cand("mem:pin", "working", observed_at=old, pinned=True)
    pinned.rrf_score = 1.0
    plain = _cand("mem:plain", "working", observed_at=old, pinned=False)
    plain.rrf_score = 1.0
    assert final_score(pinned, NOW, set()) > final_score(plain, NOW, set())


def test_focus_bonus_applied_when_linked():
    """候选 linked_ids 命中 focus_ids → focus_bonus 加权。"""
    linked = _cand("mem:l", "episodic", linked_ids={"role:甲"})
    linked.rrf_score = 0.5
    base = final_score(linked, NOW, set())
    boosted = final_score(linked, NOW, {"role:甲"})
    assert boosted > base


def test_reference_not_suppressed_by_canonical():
    """宪法级:reference 绝不参与剧情真假裁决——正典压制只针对 episodic,
    reference 即便同 (entity,attribute) 也不进 conflicts_with_canonical。"""
    canon = fact("role:a", "location", "城东", valid_from=8)
    ref = MemoryCandidate(
        source_kind="reference", source_id="ref:atlas", text="城西地理志", work="w",
        observed_at=NOW, provenance=[{"entity": "role:a", "attribute": "location"}],
    )
    # 注意:reference 是 source_kind,不是通道;候选走 vector 通道进入融合。
    result = fuse({"structured": ["fact:location-east"], "vector": ["ref:atlas"]},
                  {"fact:location-east": canon, "ref:atlas": ref}, now=NOW, focus_ids=set())
    assert "ref:atlas" in result.selected_ids
    assert not any(r.candidate.source_id == "ref:atlas" for r in result.rejected)


# ---------- store-backed 冒烟:四通道真机 + Task 7 协议对齐 ----------

def _patch_embed(monkeypatch):
    """确定性假 embedding(按字符散列进 512 维),绝不加载真模型/服务。"""
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


def test_retrieve_satisfies_task7_protocol_and_mixes_sources(store, monkeypatch):
    """MemoryRetriever.retrieve 满足 Task7 协议:返回 list[候选],含 canonical(领域直查)
    与经验记忆(memory_item),各候选具备协议属性。"""
    _patch_embed(monkeypatch)
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:loc", "role:甲", "location", "城东", valid_from=1))
    store.add_memory_item(work="w", kind="episodic",
                          text="甲昨夜在集市买了一把油纸伞", scope_type="work",
                          scope_id="w", source_type="chat", source_id="turn:1")

    snapshot = {"work": "w", "chapter": 5,
                "focus": {"type": "character", "id": "role:甲", "label": "甲"}}
    cands = MemoryRetriever(store).retrieve("w", snapshot, "集市 油纸伞", k=10)

    assert isinstance(cands, list) and cands
    for c in cands:   # Task7 协议鸭子类型
        assert hasattr(c, "source_kind") and hasattr(c, "source_id")
        assert hasattr(c, "text") and hasattr(c, "work")
        assert hasattr(c, "provenance") and hasattr(c, "observed_at")
    kinds = {c.source_kind for c in cands}
    assert "canonical" in kinds, f"应含领域直查 canonical,实得 {kinds}"
    assert "episodic" in kinds, f"应含 memory_item 经验候选,实得 {kinds}"


def test_retrieve_fail_soft_on_empty_memory(store, monkeypatch):
    """空 memory_item 表:三经验通道降级空,仍返回 canonical,不崩。"""
    _patch_embed(monkeypatch)
    store.add_fact(Fact("fact:only", "role:x", "mood", "沉郁", valid_from=1))
    snapshot = {"work": "w", "chapter": 3}
    cands = MemoryRetriever(store).retrieve("w", snapshot, "无匹配查询词", k=5)
    assert all(c.source_kind == "canonical" for c in cands)


def test_add_memory_item_persists_and_bm25_recalls(store, monkeypatch):
    """add_memory_item 落库(jieba tokens + embedding),BM25 通道可召回。"""
    _patch_embed(monkeypatch)
    mid = store.add_memory_item(work="w", kind="procedural",
                                text="写刑讯场景先立寒气再落刀,冷硬白描不抒情",
                                scope_type="work", scope_id="w",
                                source_type="lesson", source_id="lesson:1")
    assert mid
    hits = store.memory_bm25("w", "刑讯 寒气 白描", k=5)
    assert any(mid == h for h in hits), f"BM25 应召回刚写入的经验,实得 {hits}"


# ---------- I-3 检索层活化路径已通:provenance 带 (entity,attribute) 时正典压制生效 ----------

def test_real_episodic_suppressed_when_provenance_carries_entity_attribute(store, monkeypatch):
    """诚实边界:本测试验证【检索层活化路径】——add_memory_item 一旦带 (entity,attribute)
    provenance(此处显式给出),与 canonical 矛盾的经验记忆即被正典压制进 rejected、
    unconflictable_count 归零。但【生产捕获】对自由文本的 (entity,attribute) 精确抽取
    仍待后续(高风险稳定断言已被前置拦入待审;进 memory_item 的经验记忆当前不带精确
    attribute),故此处手喂 (entity,attribute) 以验证机制,不代表生产已自动抽取——
    生产哨兵见 test_memory_capture.test_p1_production_signature_wires_linked_ids_and_known_from。"""
    _patch_embed(monkeypatch)
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:loc", "role:甲", "location", "城东", valid_from=1))
    # 与 canonical(甲/location/城东)直接矛盾的经验记忆,回填 (entity,attribute)
    mid = store.add_memory_item(work="w", kind="episodic", text="甲还在城西盘桓未走",
                                scope_type="work", scope_id="w",
                                source_type="chat", source_id="turn:9",
                                entity="role:甲", attribute="location")

    snapshot = {"work": "w", "chapter": 5,
                "focus": {"type": "character", "id": "role:甲"}}
    result = MemoryRetriever(store).retrieve_full(
        RetrievalQuery(work="w", snapshot=snapshot, query="甲 城西", k=10))

    # 回填后:矛盾 episodic 进 rejected 且不再选入。
    rej = [r for r in result.rejected if r.candidate.source_id == f"mem:{mid}"]
    assert rej and rej[0].reason == "conflicts_with_canonical", \
        "回填 (entity,attribute) 后,矛盾 episodic 必须被正典压制"
    assert f"mem:{mid}" not in result.selected_ids
    # 活化缺口归零:不再有"压制不了的" episodic。
    assert result.unconflictable_count == 0


def test_real_experiential_unlinked_focus_bonus_noop(store, monkeypatch):
    """I-2 诚实缺口:真机经验候选缺 linked_ids → focus 加权对其恒 0。
    telemetry unlinked_count 记账;回填 linked_ids 后应下降。"""
    _patch_embed(monkeypatch)
    store.add_memory_item(work="w", kind="episodic", text="甲在集市与旧友叙话",
                          scope_type="work", scope_id="w",
                          source_type="chat", source_id="turn:3")
    snapshot = {"work": "w", "chapter": 5, "focus": {"type": "character", "id": "role:甲"}}
    result = MemoryRetriever(store).retrieve_full(
        RetrievalQuery(work="w", snapshot=snapshot, query="集市 旧友", k=10))
    assert result.unlinked_count >= 1
    # 该经验候选 linked_ids 为空 → 不会因 focus 命中而加权(如实反映未接线)
    exp = [c for c in result.selected if c.source_kind == "episodic"]
    assert exp and all(not c.linked_ids for c in exp)


# ---------- I-4 限知红线:经验记忆按 known_from/to 时态过滤 ----------

def test_memory_bm25_honors_known_from_temporal_gate(store, monkeypatch):
    """known_from=20 的记忆:写第 5 章时不召回、写第 25 章时召回、讨论模式(无章)不过滤。"""
    _patch_embed(monkeypatch)
    mid = store.add_memory_item(work="w", kind="episodic",
                                text="甲在城西暗中打探盐帮消息", known_from=20,
                                scope_type="work", scope_id="w",
                                source_type="chat", source_id="turn:20")
    assert mid not in store.memory_bm25("w", "城西 打探 盐帮", k=5, chapter=5), \
        "第 20 章才被知道的记忆不得倒灌进第 5 章"
    assert mid in store.memory_bm25("w", "城西 打探 盐帮", k=5, chapter=25), \
        "第 25 章应召回(known_from=20 已满足)"
    assert mid in store.memory_bm25("w", "城西 打探 盐帮", k=5, chapter=None), \
        "讨论模式(chapter=None)fail-open,不做时态过滤"


def test_retrieve_temporal_gate_end_to_end(store, monkeypatch):
    """端到端:known_from=20 的记忆在 chapter=5 检索不出、chapter=25 检索得到。"""
    _patch_embed(monkeypatch)
    mid = store.add_memory_item(work="w", kind="episodic",
                                text="甲在城西暗中打探盐帮消息", known_from=20,
                                scope_type="work", scope_id="w",
                                source_type="chat", source_id="turn:20")
    r5 = MemoryRetriever(store).retrieve("w", {"work": "w", "chapter": 5}, "城西 打探 盐帮", k=10)
    assert f"mem:{mid}" not in [c.source_id for c in r5]
    r25 = MemoryRetriever(store).retrieve("w", {"work": "w", "chapter": 25}, "城西 打探 盐帮", k=10)
    assert f"mem:{mid}" in [c.source_id for c in r25]


# ---------- M-1 graph 通道真机召回 ----------

def test_memory_graph_channel_recalls_neighbor(store, monkeypatch):
    """add_memory_relation 建联想边 → graph 通道从种子一跳召回邻居;
    retrieve 中 bm25 命中种子(刺客/蹲守),邻居(暗门)仅经 graph 浮现。"""
    _patch_embed(monkeypatch)
    a = store.add_memory_item(work="w", kind="episodic", text="刺客在屋脊蹲守整夜",
                              scope_type="work", scope_id="w",
                              source_type="chat", source_id="turn:a")
    b = store.add_memory_item(work="w", kind="reference", text="宅邸后墙有一道暗门",
                              scope_type="work", scope_id="w",
                              source_type="note", source_id="turn:b")
    store.add_memory_relation(a, b, "same_topic")

    # store 层:种子 a 的邻居含 b
    assert b in store.memory_graph("w", [a], k=5)

    # retrieve 层:query 只命中 a(bm25 种子),b 经 graph 通道浮现
    result = MemoryRetriever(store).retrieve_full(
        RetrievalQuery(work="w", snapshot={"work": "w", "chapter": 9}, query="刺客 蹲守", k=10))
    b_cand = result.by_id(f"mem:{b}")
    assert b_cand is not None, "邻居 b 应经 graph 通道进入候选"
    assert "graph" in b_cand.channels
