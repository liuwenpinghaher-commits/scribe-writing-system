"""Remaining health items: backfill batch, approval cache, settings flags, ADR, migration."""
from __future__ import annotations

import pathlib
import time

import pytest


def test_p1_12_backfill_single_batch_update():
    from scribe3.store.facts_knowledge import FactsKnowledgeMixin

    class St:
        def __init__(self):
            self.writes = []

        def _query(self, sql, vars=None):
            return [
                {"local": "a1", "attribute": "获知", "source": None},
                {"local": "a2", "attribute": "获知", "source": ""},
                {"local": "b1", "attribute": "自定义", "source": None},  # not noise
            ]

        def _execute_write(self, sql, vars=None):
            self.writes.append((sql, vars))

    st = St()
    out = FactsKnowledgeMixin.backfill_ingest_source_heuristic(st, dry_run=False)
    assert out["matched"] == 2
    assert out["updated"] == 2
    prop_writes = [w for w in st.writes if "UPDATE proposition" in w[0] and "source" in w[0]]
    assert len(prop_writes) == 1, st.writes  # 单条批量 UPDATE，非 per-row
    assert "IN $locals" in prop_writes[0][0]
    assert set(prop_writes[0][1]["locals"]) == {"a1", "a2"}


def test_p1_14_approval_cache_maxsize_prune():
    import scribe3.approval_idempotency as ai

    ai.clear_approval_cache()
    # shrink max for test
    old = ai._MAX_SIZE
    try:
        ai._MAX_SIZE = 8
        for i in range(20):
            ai.record_approved(f"fp{i:04d}", "tool", {"i": i})
        assert ai.approval_cache_size() <= 8
        # expired prune
        with ai._lock:
            for k, row in list(ai._CACHE.items())[:3]:
                row["ts"] = time.time() - ai._TTL_SEC - 10
            ai._prune_expired_unlocked()
        assert ai.approval_cache_size() <= 8
    finally:
        ai._MAX_SIZE = old
        ai.clear_approval_cache()


def test_p1_7_adr_rest_no_approval_exists():
    p = pathlib.Path("docs/adr/004-rest-no-approval.md")
    assert p.is_file()
    t = p.read_text(encoding="utf-8")
    assert "WRITE_GATED" in t
    assert "REST" in t and "MCP" in t


def test_p1_6_migration_removes_ghost_events():
    p = pathlib.Path("scribe3/migrations/131_drop_ghost_async_events.surql")
    assert p.is_file()
    t = p.read_text(encoding="utf-8")
    assert "REMOVE EVENT" in t
    assert "ev_chapter_saved" in t and "ev_promise_closed" in t


def test_p1_2_store_public_pilot_pulse_apis():
    from scribe3.store.pilot_ops import PilotOpsMixin
    from scribe3.store.surreal import SurrealStore

    for name in (
        "get_pilot_state_fields",
        "set_pilot_state",
        "set_pilot_parked",
        "get_chapter_quality_fields",
        "get_chapter_ingest_prose_fp",
        "find_active_learned_fact_local",
        "reader_knows_exists",
        "purge_audit_events_older_than",
        "query_audit_events",
        "upsert_bridge_proposition",
        "delete_bridge_proposition",
        "find_bridge_proposition_local",
    ):
        assert hasattr(SurrealStore, name), name
        assert hasattr(PilotOpsMixin, name), name


def test_p1_2_no_private_store_in_five_modules():
    """业务模块不得再直接 st/store._query / _execute_write（P1-2 清零）。"""
    import re

    roots = pathlib.Path("scribe3")
    targets = [
        roots / "pulse.py",
        roots / "pilot.py",
        roots / "ingest.py",
        roots / "codex_secret_bridge.py",
        roots / "audit_maintenance.py",
        roots / "api" / "services" / "pilot_runtime.py",
    ]
    # 匹配属性调用；排除 docstring 中反引号引用可选：只认标识符后的 ._query(
    pat = re.compile(r"(?<![\w.])(?:st|store|self)\._(?:query|execute_write)\s*\(")
    # pilot_runtime 用 _store_for(...)._execute_write 等
    pat2 = re.compile(r"\._(?:query|execute_write)\s*\(")
    for p in targets:
        text = p.read_text(encoding="utf-8")
        # strip pure comment lines and triple-quoted blocks roughly: keep simple
        # 允许文档字符串提及历史 API 名，但禁止真实调用（含括号）
        hits = []
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if pat2.search(line):
                # 模块 docstring 顶部可能仍有反引号说明——要求不含调用括号后的典型 SQL 上下文
                # 已用 \s*\( 故 docstring 中的 `_query` 无括号不算
                hits.append(f"{p}:{i}:{line.strip()[:120]}")
        assert not hits, "private store calls remain:\n" + "\n".join(hits)


def test_p1_2_drive_public_apis_fake_store():
    """驱动 PilotOpsMixin 公开方法至少一次（FakeStore）。"""
    from scribe3.store.pilot_ops import PilotOpsMixin

    class Fake(PilotOpsMixin):
        def __init__(self):
            self.queries = []
            self.writes = []

        def _query(self, sql, vars=None):
            self.queries.append((sql, vars))
            if "pilot_state" in sql:
                return [{"pilot_state": "idle", "pilot_state_at": 1, "pilot_parked": ""}]
            if "ingest_prose_fp" in sql:
                return [{"ingest_prose_fp": "abc", "ingest_status": "ok"}]
            if "qc_issues" in sql or ("ingest_status" in sql and "ingest_error" in sql):
                return [{"ingest_status": "ok", "ingest_error": None, "qc_issues": []}]

            if "attribute = '获知'" in sql:
                return [{"local": "x1", "value": "已知事实"}]
            if "reader_knows" in sql:
                return [{"proposition": "fact:x1"}]
            if "source=$src" in sql:
                return [{"local": "b1"}]
            if "audit_event" in sql:
                return [{"kind": "t", "source_table": "chapter"}]
            return []

        def _execute_write(self, sql, vars=None):
            self.writes.append((sql, vars))

    st = Fake()
    assert st.get_pilot_state_fields(1)["pilot_state"] == "idle"
    st.set_pilot_state(2, "draft", "park")
    st.set_pilot_parked(3, "err")
    assert st.get_chapter_quality_fields(1).get("ingest_status") == "ok"
    assert st.get_chapter_ingest_prose_fp(1) == "abc"
    assert st.find_active_learned_fact_local("已知事实") == "x1"
    assert st.reader_knows_exists("fact:x1") is True
    st.purge_audit_events_older_than(7)
    assert st.query_audit_events(limit=10)
    st.upsert_bridge_proposition(
        local="b1", entity_id="faction:A", attribute="origin", value="v", source="codex_bridge"
    )
    st.upsert_bridge_proposition(
        local=None, entity_id="faction:A", attribute="origin", value="v", source="codex_bridge"
    )
    st.delete_bridge_proposition("b1")
    assert st.find_bridge_proposition_local("faction:A", "origin", "codex_bridge") == "b1"
    assert st.writes and st.queries


def test_p1_4_pdc_uses_settings_registry(monkeypatch):
    from scribe3 import pressure_drive as pd

    monkeypatch.setenv("SCRIBE3_PDC", "0")
    # settings default False
    assert pd.pdc_flag_enabled() is False
    monkeypatch.setenv("SCRIBE3_PDC", "1")
    assert pd.pdc_flag_enabled() is True


def test_p1_4_session_secure_and_ttl(monkeypatch):
    from scribe3.auth import routes as ar
    from types import SimpleNamespace

    monkeypatch.delenv("SCRIBE3_SESSION_SECURE", raising=False)
    monkeypatch.setenv("SCRIBE3_SESSION_SECURE", "1")
    assert ar._cookie_secure(None) is True
    monkeypatch.setenv("SCRIBE3_SESSION_SECURE", "0")
    assert ar._cookie_secure(None) is False
    monkeypatch.delenv("SCRIBE3_SESSION_SECURE", raising=False)
    req = SimpleNamespace(
        headers={"x-forwarded-proto": "https"},
        url=SimpleNamespace(scheme="http"),
    )
    assert ar._cookie_secure(req) is True
    monkeypatch.setenv("SCRIBE3_SESSION_TTL_HOURS", "24")
    assert ar._session_ttl_seconds() == 24 * 3600


def test_p1_15_quality_retry_async_uses_asyncio_sleep(monkeypatch):
    import asyncio
    from scribe3.quality.store import QualityStore

    sleeps: list[float] = []

    async def fake_sleep(d):
        sleeps.append(d)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return None if calls["n"] < 3 else {"ok": True}

    out = asyncio.run(QualityStore._retry_read_async(loader, attempts=5))
    assert out == {"ok": True}
    assert len(sleeps) == 2
    # sync path still works
    calls["n"] = 0
    out2 = QualityStore._retry_read(loader, attempts=5)
    assert out2 == {"ok": True}


def test_p0_2_core_module_contract_imports():
    """Drive shipped entrypoints for write_assemble / pilot_runtime / rules_impl."""
    from scribe3.api.services.write_assemble import assemble_discussion_system
    from scribe3.api.services.pilot_runtime import _pilot_executor
    from scribe3.api.services.pilot_executor_body import build_pilot_executor_body
    from scribe3.api.services.pilot_actions import ACTION_KEYS
    from scribe3.critique.rules_impl import ADJACENT_MIN_LEN
    import inspect

    assert callable(assemble_discussion_system)
    src = inspect.getsource(assemble_discussion_system)
    assert "guard_discuss_instructions" in src
    m = _pilot_executor("main")
    assert set(m) >= set(ACTION_KEYS)
    m2 = build_pilot_executor_body("main")
    assert set(m2) == set(m) == set(ACTION_KEYS)
    assert ADJACENT_MIN_LEN >= 1


def test_p1_16_pilot_phase_modules():
    """阶段真拆：pilot_actions/* 存在且 facade 薄、runtime 不内嵌 body。"""
    rt = pathlib.Path("scribe3/api/services/pilot_runtime.py").read_text()
    body = pathlib.Path("scribe3/api/services/pilot_executor_body.py").read_text()
    actions = pathlib.Path("scribe3/api/services/pilot_actions")
    assert rt.count("\n") < 600
    assert body.count("\n") < 40  # facade only
    assert "build_pilot_executor_body" in rt
    assert "pilot_actions" in body or "build_pilot_executor_body" in body
    for name in (
        "outline.py",
        "beats.py",
        "deduce.py",
        "draft.py",
        "check.py",
        "deliver.py",
        "finalize.py",
        "__init__.py",
    ):
        assert (actions / name).is_file(), name
    # stage modules not tiny stubs
    assert (actions / "beats.py").read_text().count("\n") > 100
    from scribe3.api.services.pilot_actions.outline import build_actions as bo
    from scribe3.api.services.pilot_actions.finalize import build_actions as bf

    assert "propose_outline" in bo("main")
    assert "finalize" in bf("main")


def test_infra_context_public_apis_on_store():
    from scribe3.store.surreal import SurrealStore
    from scribe3.store.infra_ops import InfraOpsMixin
    from scribe3.store.context_ops import ContextOpsMixin

    for name in (
        "ensure_ingest_lease_table",
        "get_ingest_lease_row",
        "upsert_ingest_lease_row",
        "clear_ingest_lease_row",
        "create_only_ingest_lease",
        "cas_update_ingest_lease",
        "ensure_chapter_lease_fields",
        "get_chapter_lease_fields",
        "set_chapter_lease_fields",
        "clear_chapter_lease_fields",
        "cas_update_chapter_lease",
        "delete_cache_watch_older_than",
        "create_cache_watch_row",
        "create_only_context_manifest",
        "get_context_manifest_row",
        "create_only_context_outcome",
        "get_context_outcome_row",
    ):
        assert hasattr(SurrealStore, name), name
        assert hasattr(InfraOpsMixin, name) or hasattr(ContextOpsMixin, name), name


def test_infra_adapters_no_private_store_calls():
    import re
    import pathlib

    pat = re.compile(r"\._(?:query|execute_write|raw_query)\s*\(")
    for rel in (
        "scribe3/ingest_lease.py",
        "scribe3/context_store.py",
        "scribe3/context_cache.py",
    ):
        hits = []
        for i, line in enumerate(pathlib.Path(rel).read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if pat.search(line):
                hits.append(f"{rel}:{i}:{line.strip()[:100]}")
        assert not hits, hits


def test_p1_15_retry_read_no_sleep_in_async(monkeypatch):
    import asyncio
    import time
    from scribe3.quality.store import QualityStore

    slept = []

    def boom_sleep(d):
        slept.append(d)
        raise AssertionError("time.sleep must not run under event loop")

    monkeypatch.setattr(time, "sleep", boom_sleep)
    n = {"i": 0}

    def loader():
        n["i"] += 1
        return None if n["i"] < 3 else {"ok": 1}

    async def run():
        return QualityStore._retry_read(loader, attempts=5)

    out = asyncio.run(run())
    assert out == {"ok": 1}
    assert slept == []


def test_write_assemble_context_module_and_rules_parts():
    import pathlib
    from scribe3.api.services.write_assemble import _outline_block, assemble_discussion_system
    from scribe3.api.services import write_assemble_context as ctx
    from scribe3.critique.rules_impl import find_ai_tics

    assert callable(_outline_block) and callable(ctx._outline_block)
    assert callable(assemble_discussion_system)
    assert callable(find_ai_tics)
    parts = pathlib.Path("scribe3/critique/rules_parts")
    assert parts.is_dir()
    names = sorted(p.name for p in parts.glob("*.py"))
    assert any(n.startswith("01_") for n in names)
    assert any(n.startswith("07_") for n in names)
    body = pathlib.Path("scribe3/critique/rules_impl_body.py").read_text()
    assert "rules_parts" in body
    assert body.count("\n") < 80


def test_adapter_ops_public_surface():
    from scribe3.store.surreal import SurrealStore
    from scribe3.store.adapter_ops import AdapterOpsMixin

    for name in (
        "ping",
        "stats_chapter_count_view",
        "knowledge_frame_fn",
        "set_chapter_ingest_status",
        "write_chapter_ingest_hold",
        "create_inflight_lock",
        "upsert_chapter_review",
        "promise_exists",
        "delete_promise_record",
        "get_pilot_card",
        "set_pilot_card",
        "show_table_changes",
        "list_reference_fingerprints",
        "latest_quality_job_id_for_seq",
        "get_chapter_qc_and_pilot_card",
        "clear_chapter_prose_for_redraft",
    ):
        assert hasattr(SurrealStore, name), name
        assert hasattr(AdapterOpsMixin, name), name


def test_next_layer_adapters_no_private_store():
    """业务适配层（除 quality/store 域适配器）无私有 store 调用。"""
    import pathlib
    import re

    pat = re.compile(r"\._(?:query|execute_write|raw_query)\s*\(")
    allow = {
        "scribe3/quality/store.py",  # 域适配器，对标 ContextStore 已迁移前形态
    }
    roots = []
    for p in pathlib.Path("scribe3").rglob("*.py"):
        s = str(p).replace("\\", "/")
        if "/store/" in s or "/tests/" in s or "/tools/" in s or "__pycache__" in s:
            continue
        if s in allow:
            continue
        roots.append(s)
    hits = []
    for rel in sorted(roots):
        for i, line in enumerate(pathlib.Path(rel).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if pat.search(line):
                hits.append(f"{rel}:{i}:{line.strip()[:100]}")
    assert not hits, "private store calls remain:\n" + "\n".join(hits[:40])
