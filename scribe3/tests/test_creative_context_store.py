"""Creative Context OS 的 Manifest/Outcome 窄存储真实 SurrealDB 合同测试。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest

from scribe3.context_manifest import build_context_manifest
from scribe3.context_models import (
    ContextBlock,
    ContextEnvelope,
    ContextFocus,
    ContextRequest,
    ContextSnapshot,
    ContextSource,
)
from scribe3.context_policy import ContextPolicy


def _manifest():
    request = ContextRequest(
        request_id="request-context-store-1",
        task_kind="draft",
        target_ref="chapter:1",
        navigation_snapshot_id="navigation:context-store-1",
        work="book-context-store",
        chapter=1,
        phase="draft",
        policy_version="generation.v1",
    )
    snapshot = ContextSnapshot(
        session_id="session-context-store-1", work=request.work, revision=1,
        thread_id="ethread:book-context-store:author", entry="write",
        directory_path=("write",),
        focus=ContextFocus(type="chapter", id="chapter:1", label="第一章"),
        detail_route="chapter:1", chapter=1, phase="draft", focalizer=None,
        previous_revision=0, navigation_id="nav-context-store-1",
        captured_at=datetime(2026, 7, 20, tzinfo=timezone.utc), context_hash="",
    ).with_hash()
    canonical = ContextSource(
        source_id="fact:context-store-1", source_kind="canonical", work=request.work,
        content_digest=hashlib.sha256(b"canonical-digest-only").hexdigest(),
    )
    recent = ContextSource(
        source_id="memory:context-store-1", source_kind="recent", work=request.work,
        masked=True, reason="secret_masked",
        content_digest=hashlib.sha256(b"recent-digest-only").hexdigest(),
    )
    envelope = ContextEnvelope(
        snapshot=snapshot,
        blocks=[
            ContextBlock(name="canonical", text="", token_estimate=0, sources=[canonical]),
            ContextBlock(name="recent", text="", token_estimate=0, sources=[recent]),
        ],
        total_token_estimate=0, omitted=[],
        assembled_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        envelope_hash="e" * 64,
    )
    return build_context_manifest(request, ContextPolicy.for_task("draft"), envelope, "输入指纹")


def test_save_manifest_writes_main_and_sources_in_one_real_transaction(store, monkeypatch):
    from scribe3.context_store import ContextStore

    manifest = _manifest()
    calls: list[str] = []
    original = store._raw_query

    def record(surql, vars=None):
        calls.append(surql)
        return original(surql, vars)

    monkeypatch.setattr(store, "_raw_query", record)
    saved = ContextStore(store).save_manifest(manifest)

    assert saved == manifest
    commits = [sql for sql in calls if sql.startswith("BEGIN TRANSACTION;")]
    assert len(commits) == 1
    assert commits[0].count("context_manifest_source") == len(manifest.sources)
    assert store._query(
        "SELECT * FROM context_manifest WHERE manifest_id=$manifest_id",
        {"manifest_id": manifest.manifest_hash},
    )
    rows = store._query(
        "SELECT * FROM context_manifest_source WHERE manifest_id=$manifest_id ORDER BY source_ref",
        {"manifest_id": manifest.manifest_hash},
    )
    assert len(rows) == len(manifest.sources)
    assert [
        (row["block"], row["source_id"], row["source_kind"], row["content_digest"])
        for row in rows
    ] == [
        (source.block, source.source_id, source.source_kind, source.content_digest)
        for source in manifest.sources
    ], "每条收集语句的同名变量必须在同一事务内保持各自的值"
    assert all("text" not in row for row in rows)


def test_repeated_manifest_id_is_idempotent_and_round_trips_pydantic_contract(store):
    from scribe3.context_store import ContextStore

    manifest = _manifest()
    context_store = ContextStore(store)

    assert context_store.save_manifest(manifest) == manifest
    assert context_store.save_manifest(manifest) == manifest
    assert context_store.get_manifest(manifest.manifest_hash) == manifest
    assert store._query("SELECT * FROM context_manifest")
    assert len(store._query("SELECT * FROM context_manifest")) == 1
    assert len(store._query("SELECT * FROM context_manifest_source")) == len(manifest.sources)


def test_outcome_requires_existing_manifest_triple_and_round_trips_pydantic_contract(store):
    from scribe3.context_outcome import ContextOutcomeTrace
    from scribe3.context_store import ContextStore

    manifest = _manifest()
    context_store = ContextStore(store)
    context_store.save_manifest(manifest)
    outcome = ContextOutcomeTrace(
        outcome_id="outcome-context-store-1",
        request_id=manifest.request_id,
        manifest_id=manifest.manifest_hash,
        actual_input_hash=manifest.actual_input_hash,
        status="completed",
        provider="provider-a",
        model="model-a",
        provider_request_id="provider-request-1",
        usage={"input_tokens": 12, "output_tokens": 34},
        output_hash="a" * 64,
    )

    assert context_store.save_outcome(outcome) == outcome
    assert context_store.get_outcome(
        manifest.request_id, manifest.manifest_hash, manifest.actual_input_hash,
    ) == outcome

    with pytest.raises(ValueError, match="三元组"):
        context_store.save_outcome(outcome.model_copy(update={"actual_input_hash": "0" * 64}))
