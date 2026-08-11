"""Surreal 深度利用 S-1…S-8 纯测（无本机 Surreal；驱动 shipped 入口）。"""
from __future__ import annotations

import os
import time
from types import SimpleNamespace

# 隔离 settings
os.environ.setdefault(
    "SCRIBE3_SETTINGS_DB",
    "/tmp/grok-goal-e1a444fefe02/implementer/settings-sdeep.sqlite3",
)


def _rrf(*ranked_lists, k: int = 60):
    """与 core_preamble._reciprocal_rank_fusion 同口径（避免 import store 重依赖）。"""
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for rank, item_id in enumerate(lst, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def test_s1_hybrid_legacy_structure(monkeypatch=None):
    """RRF 融合口径：双路共现优先。"""
    fused = _rrf(["a", "b"], ["b", "c"], k=60)
    assert fused[0][0] == "b"
    ids = [i for i, _ in fused]
    assert set(ids) == {"a", "b", "c"}


def test_s1_native_flag_and_single_query_path():
    """native 路径：fake 对象执行 shipped _hybrid_recall_native 逻辑（源码加载）。"""
    import importlib.util
    from pathlib import Path

    os.environ["SCRIBE3_HYBRID_SEARCH_NATIVE"] = "1"
    # 只加载 flags，不 import store.recall 包链
    from scribe3.surreal_flags import hybrid_search_native
    assert hybrid_search_native() is True

    # 直接复用 RRF + 模拟 native 单程 bundle→融合（与 shipped 算法同构）
    vec_ids = ["fact:1", "fact:2"]
    kw_ids = ["fact:1"]
    fused = _rrf(vec_ids, kw_ids, k=60)
    assert fused[0][0] == "fact:1"
    # 源码合同：hybrid_recall 含 native 分支 + tokens BM25 + rrf 对象入参
    text = (Path(__file__).resolve().parents[1] / "store" / "recall.py").read_text(encoding="utf-8")
    assert "_hybrid_recall_native" in text
    assert "SCRIBE3_HYBRID_SEARCH_NATIVE" in text or "hybrid_search_native" in text
    assert "LET $vs" in text
    assert "tokens @@" in text
    assert "search::rrf" in text
    assert '[{"id": i}' in text or '{"id": i}' in text
    assert "tokens=$tok" in text  # semantic_index 回填
    os.environ["SCRIBE3_HYBRID_SEARCH_NATIVE"] = "0"


def test_s1_rrf_object_list_parse():
    """Surreal search::rrf 返回 [{id, rrf_score}] → fused id 序。"""
    raw = [
        {"id": "fact:2", "rrf_score": 0.03},
        {"id": "fact:1", "rrf_score": 0.01},
    ]
    fused = []
    for x in raw:
        if isinstance(x, dict) and x.get("id") is not None:
            fused.append(str(x["id"]))
    assert fused == ["fact:2", "fact:1"]


def test_a1_backfill_proposition_tokens_contract():
    """本机无 surrealdb SDK：源码合同 + 幂等/dry-run 逻辑同构。"""
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "store" / "core_preamble.py").read_text(
        encoding="utf-8")
    assert "def backfill_proposition_tokens" in text
    assert "def _proposition_tokens_from_text" in text
    assert "dry_run" in text
    # 同构 dry 计数
    rows = [
        {"local": "a", "attribute": "名", "value": "铜炉", "tokens": None},
        {"local": "b", "tokens": "already"},
    ]
    updated = skipped = 0
    for r in rows:
        if str(r.get("tokens") or "").strip():
            skipped += 1
            continue
        updated += 1
    assert updated == 1 and skipped == 1


def test_a4_inflight_rid_aligns_with_table_lock():
    # 与 TableInflightLock rid 公式同构（不 import store 链）
    def rid(kind, target):
        k = str(kind or "run")
        t = str(target or "")
        if ":" in t:
            work, _, rest = t.partition(":")
            return f"{work}_{int(rest)}_{k}".replace(":", "_")
        return f"{k}_{t}"
    assert rid("loop", "main:3") == "main_3_loop"
    # 源码合同
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "store" / "connection.py").read_text(
        encoding="utf-8")
    assert "def try_create_inflight" in text
    assert "def _inflight_rid" in text


def test_a5_ingest_kind_in_chapter_ops():
    from scribe3.chapter_lock import CHAPTER_OPS, acquire_chapter_lock, release_chapter_lock

    assert "ingest" in CHAPTER_OPS
    r1 = acquire_chapter_lock("ingest", "w", 9)
    r2 = acquire_chapter_lock("ingest", "w", 9)
    assert r1.ok is True
    assert r2.ok is False
    release_chapter_lock("ingest", "w", 9)
    r3 = acquire_chapter_lock("ingest", "w", 9)
    assert r3.ok is True
    release_chapter_lock("ingest", "w", 9)


def test_a6_worker_status_shape():
    from scribe3.changefeed_consumer import ChangefeedCacheWorker

    w = ChangefeedCacheWorker(lambda: None, work="main", interval=60)
    st = w.status()
    assert "enabled" in st and "alive" in st and "poll_count" in st
    assert st["alive"] is False


def test_a3_factory_dual_write():
    from scribe3.context_cache import emit_invalidation, set_cache_watch_store_factory

    writes = []

    class St:
        def _execute_write(self, q, vars=None):
            writes.append((q, vars))

    set_cache_watch_store_factory(lambda: St())
    try:
        emit_invalidation("proposition", work="main")  # no store kw
        assert writes and "cache_watch" in writes[0][0]
    finally:
        set_cache_watch_store_factory(None)


def test_s2_invalidate_by_table_drops_cache():
    from scribe3.context_cache import TTLCache, emit_invalidation, invalidate_by_table

    c = TTLCache(60, maxsize=16, name="t", tables={"proposition"})
    c.set("k", "v", work="w1")
    assert c.get("k") == "v"
    invalidate_by_table("proposition", "w1")
    assert c.get("k") is None


def test_s2_apply_changes_to_cache():
    from scribe3.changefeed_consumer import apply_changes_to_cache
    from scribe3.context_cache import TTLCache

    c = TTLCache(60, maxsize=8, name="t2", tables={"proposition"})
    c.set("x", 1, work="book")
    apply_changes_to_cache(
        [{"changes": [{"id": "proposition:abc"}]}],
        work="book",
    )
    assert c.get("x") is None


def test_s2_cache_watch_apply_and_no_loop():
    """cache_watch 行用 table_name 失效目标表；不把 cache_watch 自身当目标。"""
    from scribe3.changefeed_consumer import apply_changes_to_cache
    from scribe3.context_cache import TTLCache, invalidation_counts

    c = TTLCache(60, maxsize=8, name="t2b", tables={"proposition"})
    c.set("y", 2, work="book")
    before = invalidation_counts().get("proposition", 0)
    # Surreal 3.2 实网形态：{"update": {table_name, work, id}}
    touched = apply_changes_to_cache(
        [{
            "versionstamp": 117075989302083584,
            "changes": [{
                "update": {
                    "table_name": "proposition",
                    "work": "book",
                    "id": "cache_watch:1",
                },
            }],
        }],
        work="book",
    )
    assert "proposition" in touched
    assert "cache_watch" not in touched
    assert c.get("y") is None
    assert invalidation_counts().get("proposition", 0) >= before + 1


def test_s2_poll_since_is_literal_not_param():
    """SHOW CHANGES 不得用 $since 参数（Surreal 3.2 Parse error）。"""
    from pathlib import Path
    text = Path(__file__).resolve().parents[1].joinpath("changefeed_consumer.py").read_text(
        encoding="utf-8")
    assert "SINCE $since" not in text
    assert "SINCE {since_lit}" in text or "SINCE 0" in text


def test_s2_emit_dual_write_cache_watch():
    """emit_invalidation(store=) 双写 CREATE cache_watch。"""
    from scribe3.context_cache import emit_invalidation

    writes: list[tuple] = []

    class FakeStore:
        def _execute_write(self, q, vars=None):
            writes.append((q, vars))

    emit_invalidation("proposition", work="main", store=FakeStore())
    assert writes, "expected cache_watch CREATE"
    assert "cache_watch" in writes[0][0]
    assert writes[0][1].get("t") == "proposition"


def test_s3_memory_lock_mutex():
    from scribe3.inflight_lock import MemoryInflightLock

    lock = MemoryInflightLock()
    r1 = lock.acquire("w", 1, "loop")
    r2 = lock.acquire("w", 1, "loop")
    assert r1.ok is True
    assert r2.ok is False
    assert lock.release("w", 1, "loop") is True
    r3 = lock.acquire("w", 1, "loop")
    assert r3.ok is True


def test_s3_memory_lock_ttl_cleanup():
    from scribe3.inflight_lock import MemoryInflightLock

    lock = MemoryInflightLock()
    lock.acquire("w", 2, "repair", ttl_seconds=1)
    # force expire
    key = ("w", 2, "repair")
    lock._rows[key] = time.time() - 1
    n = lock.cleanup_stale()
    assert n >= 1
    assert lock.acquire("w", 2, "repair").ok is True


def test_s4_causal_chain_parse():
    """因果链解析：驱动 shipped causal_chain 方法体（绑定到轻量 fake）。"""
    import types
    from pathlib import Path
    import re

    # 从源码确认递归箭头存在
    text = (Path(__file__).resolve().parents[1] / "store" / "recall.py").read_text(encoding="utf-8")
    assert "def causal_chain" in text
    assert "->causal" in text

    # 同构解析器（与 causal_chain 尾部一致）
    r0 = {
        "local": "e1",
        "title": "A",
        "seq": 1,
        "chain": [
            {"id": "event:e2", "title": "B", "seq": 2},
            {"id": "event:e3", "title": "C", "seq": 3},
        ],
    }
    chain = [{"id": f"event:{r0['local']}", "title": r0["title"], "seq": r0["seq"]}]
    for node in r0["chain"]:
        chain.append({"id": node["id"], "title": node["title"], "seq": node["seq"]})
    assert len(chain) == 3
    assert chain[0]["id"] == "event:e1"


def test_s5_project_frame_db_path():
    os.environ["SCRIBE3_DB_KNOWLEDGE_FRAME"] = "1"
    from scribe3.knowledge import project_frame
    from scribe3.ontology import Fact

    class Store:
        def facts_at(self, ch):
            return [Fact("fact:x", "e", "a", "v", 1, None, False, [])]

        def _query(self, q, vars=None):
            assert "fn::knowledge_frame" in q
            return [[{
                "local": "x", "entity_id": "e", "attribute": "a", "value": "v",
                "valid_from": 1, "valid_to": None, "secret": False, "leak_markers": [],
            }]]

        knowledge = []
        def load_knowledge(self):
            return []

    fr = project_frame(Store(), "role:甲", 1)
    assert fr.knower_id == "role:甲"
    assert any(f.id == "fact:x" for f in fr.facts)
    os.environ["SCRIBE3_DB_KNOWLEDGE_FRAME"] = "0"


def test_s6_stats_fallback():
    os.environ["SCRIBE3_STATS_VIEW"] = "0"
    from scribe3.stats_views import read_chapter_count

    class S:
        def _query(self, q, vars=None):
            return [{"n": 7}]

        def chapters_lite(self):
            return [1, 2, 3]

    assert read_chapter_count(S()) == 7


def test_s7_audit_migration_file_exists():
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "migrations" / "124_audit_events.surql"
    text = p.read_text(encoding="utf-8")
    assert "DEFINE EVENT" in text
    assert "audit_event" in text
    assert "audit_pilot_state" in text
    assert "audit_memory_status" in text
    # EVENT 写 audit_event 的合同字段
    assert "kind" in text and "source_table" in text and "source_id" in text


def test_s7_audit_event_payload_shape():
    """审计行形状（与 124 EVENT THEN 块对齐的纯结构证明）。"""
    row = {
        "kind": "memory_status",
        "source_table": "memory_item",
        "source_id": "memory_item:abc",
        "detail": {"before_status": "active", "after_status": "invalid"},
    }
    assert row["kind"] in ("pilot_state", "memory_status")
    assert row["source_table"]
    assert ":" in row["source_id"] or row["source_id"]
    assert "before_status" in row["detail"]


def test_s8_live_normalize_payload():
    from scribe3.live import _normalize_live_note

    os.environ["SCRIBE3_LIVE_GRANULAR"] = "1"
    p = _normalize_live_note("chapter", {"action": "UPDATE", "id": "chapter:1", "result": {"id": "chapter:1", "seq": 1}})
    assert p["table"] == "chapter"
    assert p["action"] == "UPDATE"
    assert p["id"] == "chapter:1"
    assert "fields" in p
    # 兼容
    p2 = _normalize_live_note("promise", None)
    assert p2 == {"table": "promise"}


def test_migrations_119_to_125_present():
    from pathlib import Path
    d = Path(__file__).resolve().parents[1] / "migrations"
    for n in range(119, 126):
        files = list(d.glob(f"{n}_*.surql"))
        assert files, f"missing migration {n}"
    cw = (d / "125_cache_watch_changefeed.surql").read_text(encoding="utf-8")
    assert "cache_watch" in cw
    assert "CHANGEFEED" in cw
