"""Creative Context OS 第一条纵向链的纯合同测试。"""
from datetime import datetime, timezone

import hashlib
import json

import pytest
from pydantic import ValidationError

from scribe3.context_assembler import _Item, _render_block
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


def _snapshot() -> ContextSnapshot:
    return ContextSnapshot(
        session_id="session-1", work="book-a", revision=1, thread_id="thread-1",
        entry="write", directory_path=("write",),
        focus=ContextFocus(type="chapter", id="chapter:1", label="第一章"),
        detail_route="chapter:1", chapter=1, phase="draft", focalizer=None,
        previous_revision=None, navigation_id="nav-1",
        captured_at=datetime(2026, 7, 20, tzinfo=timezone.utc), context_hash="",
    ).with_hash()


def _request(**overrides) -> ContextRequest:
    payload = {
        "request_id": "request-1",
        "task_kind": "draft",
        "target_ref": "chapter:1",
        "navigation_snapshot_id": "navigation:nav-1",
        "work": "book-a",
        "chapter": 1,
        "scene_key": "scene-1",
        "phase": "draft",
        "actor_role": "writer",
        "pov_character": "role:jia",
        "story_time_window": "chapter:1",
        "knowledge_cutoff": "chapter:1",
        "author_intent_ref": "intent:main",
        "quality_contract_revision": "quality.v1",
        "required_slots": ("focus", "canonical"),
        "forbidden_source_kinds": (),
        "budget_profile": "generation.default",
        "freshness_requirement": "current_navigation",
        "policy_version": "generation.v1",
    }
    payload.update(overrides)
    return ContextRequest(**payload)


def _envelope(*, source: ContextSource | None = None) -> ContextEnvelope:
    source = source or ContextSource(
        source_id="fact:1", source_kind="canonical", work="book-a",
        content_digest=hashlib.sha256("甲在城里".encode("utf-8")).hexdigest(),
    )
    block = ContextBlock(
        name="canonical", text="## 权威事实\n甲在城里", token_estimate=12,
        sources=[source],
    )
    return ContextEnvelope(
        snapshot=_snapshot(), blocks=[block], total_token_estimate=12,
        omitted=[], assembled_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        envelope_hash="e" * 64,
    )


def test_draft_and_final_resolve_to_generation_v1_policy():
    assert ContextPolicy.for_task("draft").version == "generation.v1"
    assert ContextPolicy.for_task("final").version == "generation.v1"


def test_unknown_task_kind_is_rejected():
    with pytest.raises((ValueError, ValidationError)):
        _request(task_kind="teleport")


def test_request_keeps_navigation_snapshot_as_identity_not_content_snapshot():
    request = _request()
    assert request.navigation_snapshot_id == "navigation:nav-1"
    assert "navigation_snapshot" not in request.model_dump()
    assert "context_snapshot" not in request.model_dump()


def test_rendered_selected_source_gets_content_digest():
    source = ContextSource(source_id="fact:1", source_kind="canonical", work="book-a")
    _render_block("canonical", [_Item("甲在城里", source)])
    assert source.content_digest == hashlib.sha256("甲在城里".encode("utf-8")).hexdigest()


def test_manifest_actual_input_hash_changes_for_every_input_byte():
    request = _request()
    policy = ContextPolicy.for_task(request.task_kind)
    envelope = _envelope()
    first = build_context_manifest(request, policy, envelope, "甲在城里")
    second = build_context_manifest(request, policy, envelope, "甲在城外")
    assert first.actual_input_hash != second.actual_input_hash
    assert first.actual_input_hash == hashlib.sha256("甲在城里".encode("utf-8")).hexdigest()


def test_manifest_json_contains_no_source_body_and_rejects_reference_as_canon():
    request = _request()
    policy = ContextPolicy.for_task(request.task_kind)
    manifest = build_context_manifest(request, policy, _envelope(), "甲在城里")
    blob = json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False)
    assert "甲在城里" not in blob
    assert all("text" not in source.model_dump() for source in manifest.sources)

    reference = ContextSource(
        source_id="material:1", source_kind="reference", work="book-a",
        content_digest="f" * 64,
    )
    with pytest.raises(ValueError, match="reference"):
        build_context_manifest(request, policy, _envelope(source=reference), "甲在城里")


def test_manifest_rejects_same_version_forged_policy_that_allows_reference_canon():
    request = _request()
    forged = ContextPolicy(
        version="generation.v1", task_kinds=("draft",),
        canonical_source_kinds=("canonical", "reference"),
    )
    reference = ContextSource(
        source_id="material:1", source_kind="reference", work="book-a",
        content_digest="f" * 64,
    )
    with pytest.raises(ValueError):
        build_context_manifest(request, forged, _envelope(source=reference), "甲在城里")


def test_manifest_never_serializes_free_form_secret_reason():
    secret = "绝不能进入 Manifest 的秘密正文:甲是狐妖"
    source = ContextSource(
        source_id="fact:1", source_kind="canonical", work="book-a",
        reason=secret,
        content_digest=hashlib.sha256("甲在城里".encode("utf-8")).hexdigest(),
    )
    manifest = build_context_manifest(
        _request(), ContextPolicy.for_task("draft"), _envelope(source=source), "甲在城里"
    )
    blob = json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False)
    assert secret not in blob
    assert manifest.sources[0].reason_code == "unspecified"


def test_manifest_rejects_bytes_that_are_not_valid_utf8():
    with pytest.raises(ValueError, match="UTF-8"):
        build_context_manifest(
            _request(), ContextPolicy.for_task("draft"), _envelope(), b"\xff"
        )


def test_content_digest_rejects_forged_non_sha256_value_and_normalizes_case():
    with pytest.raises(ValidationError, match="SHA-256"):
        ContextSource(
            source_id="fact:1", source_kind="canonical", work="book-a",
            content_digest="forged",
        )
    source = ContextSource(
        source_id="fact:1", source_kind="canonical", work="book-a",
        content_digest="A" * 64,
    )
    assert source.content_digest == "a" * 64
    with pytest.raises(ValidationError, match="SHA-256"):
        source.content_digest = "forged-after-construction"
