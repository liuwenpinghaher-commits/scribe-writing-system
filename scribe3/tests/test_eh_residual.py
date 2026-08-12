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


def test_p1_4_pdc_uses_settings_registry(monkeypatch):
    from scribe3 import pressure_drive as pd

    monkeypatch.setenv("SCRIBE3_PDC", "0")
    # settings default False
    assert pd.pdc_flag_enabled() is False
    monkeypatch.setenv("SCRIBE3_PDC", "1")
    assert pd.pdc_flag_enabled() is True


def test_p0_2_core_module_contract_imports():
    """Drive shipped entrypoints for write_assemble / pilot_runtime / rules_impl."""
    from scribe3.api.services.write_assemble import assemble_discussion_system
    from scribe3.api.services.pilot_runtime import _pilot_executor
    from scribe3.api.services.pilot_executor_body import build_pilot_executor_body
    from scribe3.critique.rules_impl import ADJACENT_MIN_LEN
    import inspect

    assert callable(assemble_discussion_system)
    src = inspect.getsource(assemble_discussion_system)
    assert "guard_discuss_instructions" in src
    m = _pilot_executor("main")
    assert set(m) >= {"draft_loop", "finalize", "propose_outline"}
    m2 = build_pilot_executor_body("main")
    assert set(m2) == set(m)
    assert ADJACENT_MIN_LEN >= 1


def test_p1_16_pilot_body_not_in_runtime_module():
    rt = pathlib.Path("scribe3/api/services/pilot_runtime.py").read_text()
    body = pathlib.Path("scribe3/api/services/pilot_executor_body.py").read_text()
    # runtime should be thin relative to body
    assert rt.count("\n") < 600
    assert body.count("\n") > 500
    assert "build_pilot_executor_body" in rt
