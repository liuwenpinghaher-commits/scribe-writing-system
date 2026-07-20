"""Creative Context OS 的 Manifest/Outcome 窄存储真实 SurrealDB 合同测试。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

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
from scribe3.ontology import Entity, Fact


def _manifest(rendered_input="输入指纹"):
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
    return build_context_manifest(request, ContextPolicy.for_task("draft"), envelope, rendered_input)


def _outcome(manifest, **overrides):
    from scribe3.context_outcome import ContextOutcomeTrace

    payload = {
        "outcome_id": "outcome-context-store-1",
        "request_id": manifest.request_id,
        "manifest_id": manifest.manifest_hash,
        "actual_input_hash": manifest.actual_input_hash,
        "status": "succeeded",
        "provider": "provider-a",
        "model": "model-a",
        "provider_request_id": "provider-request-1",
        "usage": {"input_tokens": 12, "output_tokens": 34},
        "output_hash": "a" * 64,
    }
    payload.update(overrides)
    return ContextOutcomeTrace(**payload)


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


def test_new_manifests_reuse_the_readonly_policy_snapshot(store):
    from scribe3.context_store import ContextStore

    context_store = ContextStore(store)
    context_store.save_manifest(_manifest())
    context_store.save_manifest(_manifest("同策略的另一份实际输入"))

    rows = store._query("SELECT * FROM context_policy_snapshot")
    assert len(rows) == 1


def test_outcome_requires_existing_manifest_triple_and_round_trips_pydantic_contract(store):
    from scribe3.context_outcome import ContextOutcomeTrace
    from scribe3.context_store import ContextStore

    manifest = _manifest()
    context_store = ContextStore(store)
    context_store.save_manifest(manifest)
    outcome = _outcome(manifest)

    assert context_store.save_outcome(outcome) == outcome
    assert context_store.get_outcome(
        manifest.request_id, manifest.manifest_hash, manifest.actual_input_hash,
    ) == outcome

    with pytest.raises(ValueError, match="三元组"):
        context_store.save_outcome(outcome.model_copy(update={"actual_input_hash": "0" * 64}))


def test_outcome_status_is_closed_in_pydantic_and_real_surrealdb(store):
    from scribe3.context_outcome import ContextOutcomeTrace, OUTCOME_STATUSES

    manifest = _manifest()
    expected = ("succeeded", "failed", "incomplete_stream", "cancelled")
    assert OUTCOME_STATUSES == expected
    assert get_args(ContextOutcomeTrace.model_fields["status"].annotation) == expected
    status_assert = "ASSERT $value IN ['succeeded', 'failed', 'incomplete_stream', 'cancelled']"
    migrations = Path(__file__).parents[1] / "migrations"
    assert status_assert in (migrations / "091_creative_context_core.surql").read_text()
    assert status_assert in (migrations / "092_creative_context_core_immutability.surql").read_text()
    for status in OUTCOME_STATUSES:
        assert _outcome(manifest, status=status).status == status
        store._raw_query(
            "CREATE type::record('context_outcome_trace', $outcome_id) SET "
            "outcome_id=$outcome_id, request_id=$request_id, manifest_id=$manifest_id, "
            "actual_input_hash=$actual_input_hash, status=$status, created_at=time::now()",
            {"outcome_id": f"valid-status-{status}", "request_id": manifest.request_id,
             "manifest_id": manifest.manifest_hash,
             "actual_input_hash": hashlib.sha256(status.encode()).hexdigest(),
             "status": status},
        )
    with pytest.raises(ValidationError, match="status"):
        _outcome(manifest, status="completed")

    with pytest.raises(Exception, match="status"):
        store._raw_query(
            "CREATE type::record('context_outcome_trace', $outcome_id) SET "
            "outcome_id=$outcome_id, request_id=$request_id, manifest_id=$manifest_id, "
            "actual_input_hash=$actual_input_hash, status=$status, created_at=time::now()",
            {"outcome_id": "invalid-status", "request_id": manifest.request_id,
             "manifest_id": manifest.manifest_hash,
             "actual_input_hash": manifest.actual_input_hash, "status": "completed"},
        )


def test_outcome_error_is_redacted_before_at_rest_and_secret_lookup_fails_loud(store, monkeypatch):
    from scribe3.context_store import ContextStore

    story_secret = "fixture-story-secret-keepout"
    auth_sentinel = "fixture-auth-token-keepout"
    cookie_sentinel = "fixture-cookie-keepout"
    store.add_entity(Entity("role:context-secret", "character", "受控角色"))
    store.add_fact(Fact("fact:context-secret", "role:context-secret", "真名", story_secret,
                        valid_from=1, secret=True))
    manifest = _manifest()
    context_store = ContextStore(store)
    context_store.save_manifest(manifest)
    outcome = _outcome(
        manifest,
        error=(f"upstream story={story_secret}; Authorization: Bearer {auth_sentinel}; "
               f"Cookie: session={cookie_sentinel}"),
    )

    persisted = context_store.save_outcome(outcome)
    assert all(sentinel not in (persisted.error or "")
               for sentinel in (story_secret, auth_sentinel, cookie_sentinel))
    row = store._query(
        "SELECT error FROM context_outcome_trace WHERE outcome_id=$outcome_id",
        {"outcome_id": outcome.outcome_id},
    )[0]
    assert all(sentinel not in row["error"]
               for sentinel in (story_secret, auth_sentinel, cookie_sentinel))
    assert "已屏蔽·认证" in row["error"]
    assert "秘密事实已屏蔽" in row["error"]
    assert context_store.save_outcome(outcome) == persisted

    manifest_2 = _manifest("另一次输入")
    context_store.save_manifest(manifest_2)
    monkeypatch.setattr(store, "_secret_proposition_values",
                        lambda: (_ for _ in ()).throw(RuntimeError("secret lookup unavailable")))
    with pytest.raises(RuntimeError, match="secret lookup unavailable"):
        context_store.save_outcome(_outcome(manifest_2, outcome_id="outcome-fail-loud"))
    assert not store._query(
        "SELECT * FROM context_outcome_trace WHERE outcome_id='outcome-fail-loud'"
    )


def test_creative_context_core_rows_are_readonly_after_create(store):
    from scribe3.context_store import ContextStore

    manifest = _manifest()
    context_store = ContextStore(store)
    context_store.save_manifest(manifest)
    outcome = _outcome(manifest)
    context_store.save_outcome(outcome)
    policy_id = context_store._policy_snapshot_id(manifest.policy_version)
    source_ref = context_store._source_ref(manifest.manifest_hash, 0)
    updates = [
        ("context_policy_snapshot", policy_id, "policy_snapshot_id", "tampered-policy-id"),
        ("context_policy_snapshot", policy_id, "policy_version", "tampered-policy"),
        ("context_manifest", manifest.manifest_hash, "manifest_id", "tampered-manifest-id"),
        ("context_manifest", manifest.manifest_hash, "request_id", "tampered-request"),
        ("context_manifest_source", context_store._source_record_id(source_ref), "source_ref",
         "tampered-source-ref"),
        ("context_manifest_source", context_store._source_record_id(source_ref), "content_digest",
         "f" * 64),
        ("context_outcome_trace", outcome.outcome_id, "outcome_id", "tampered-outcome-id"),
        ("context_outcome_trace", outcome.outcome_id, "status", "failed"),
    ]
    for table, record_id, field, replacement in updates:
        before = store._query(
            f"SELECT {field} FROM type::record('{table}', $record_id)",
            {"record_id": record_id},
        )[0][field]
        with pytest.raises(Exception, match="readonly|read-only|READONLY"):
            store._raw_query(
                f"UPDATE type::record('{table}', $record_id) SET {field}=$replacement",
                {"record_id": record_id, "replacement": replacement},
            )
        after = store._query(
            f"SELECT {field} FROM type::record('{table}', $record_id)",
            {"record_id": record_id},
        )[0][field]
        assert after == before
