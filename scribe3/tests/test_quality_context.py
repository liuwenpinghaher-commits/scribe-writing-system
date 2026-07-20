"""Task 3: 三类质量任务的 CreativeContext Policy 隔离测试。"""
from datetime import datetime, timezone

import hashlib
import pytest

from scribe3.context_models import (
    ContextBlock,
    ContextEnvelope,
    ContextFocus,
    ContextRequest,
    ContextSnapshot,
    ContextSource,
)
from scribe3.context_policy import ContextPolicy


def _snapshot(**overrides) -> ContextSnapshot:
    payload = {
        "session_id": "session-q", "work": "book-q", "revision": 1,
        "thread_id": "thread-q", "entry": "quality",
        "directory_path": ("quality",),
        "focus": ContextFocus(type="chapter", id="chapter:3", label="第三章"),
        "detail_route": "chapter:3", "chapter": 3, "phase": None,
        "focalizer": None, "previous_revision": None,
        "navigation_id": "nav-q",
        "captured_at": datetime(2026, 7, 21, tzinfo=timezone.utc),
        "context_hash": "",
    }
    payload.update(overrides)
    return ContextSnapshot(**payload).with_hash()


def _request(task_kind: str, **overrides) -> ContextRequest:
    policy = ContextPolicy.for_task(task_kind)
    payload = {
        "request_id": "req-q-1",
        "task_kind": task_kind,
        "target_ref": "chapter_version:abc",
        "navigation_snapshot_id": "nav-q",
        "work": "book-q",
        "chapter": 3,
        "required_slots": (),
        "forbidden_source_kinds": (),
        "policy_version": policy.version,
    }
    payload.update(overrides)
    return ContextRequest(**payload)


def _source(source_kind: str, **overrides) -> ContextSource:
    payload = {
        "source_id": f"src-{source_kind}",
        "source_kind": source_kind,
        "work": "book-q",
        "revision": "rev-1",
        "content_digest": hashlib.sha256(b"test").hexdigest(),
    }
    payload.update(overrides)
    return ContextSource(**payload)


def _envelope(*sources: ContextSource, block_name: str = "canonical") -> ContextEnvelope:
    block = ContextBlock(
        name=block_name, text="内容", token_estimate=10,
        sources=list(sources),
    )
    return ContextEnvelope(
        snapshot=_snapshot(), blocks=[block], total_token_estimate=10,
        omitted=[], assembled_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        envelope_hash="f" * 64,
    )


class TestQualityChapterPolicy:
    def test_resolves_to_quality_chapter_v1(self):
        policy = ContextPolicy.for_task("quality_chapter")
        assert policy.version == "quality-chapter.v1"

    def test_forbids_generation_prompt_and_reasoning(self):
        policy = ContextPolicy.for_task("quality_chapter")
        assert "generation_prompt" in policy.forbidden_source_kinds
        assert "generation_reasoning" in policy.forbidden_source_kinds
        assert "model_inference" in policy.forbidden_source_kinds

    def test_forbids_reference_original_text(self):
        policy = ContextPolicy.for_task("quality_chapter")
        assert "reference_work_text" in policy.forbidden_source_kinds
        assert "raw_reference_text" in policy.forbidden_source_kinds

    def test_request_accepts_quality_chapter_task_kind(self):
        request = _request("quality_chapter")
        assert request.task_kind == "quality_chapter"
        assert request.policy_version == "quality-chapter.v1"


class TestReferenceFingerprintPolicy:
    def test_resolves_to_reference_fingerprint_v1(self):
        policy = ContextPolicy.for_task("reference_fingerprint")
        assert policy.version == "reference-fingerprint.v1"

    def test_forbids_this_book_prose_and_canonical(self):
        policy = ContextPolicy.for_task("reference_fingerprint")
        assert "chapter_prose" in policy.forbidden_source_kinds
        assert "canonical" in policy.forbidden_source_kinds
        assert "generation_prompt" in policy.forbidden_source_kinds
        assert "generation_reasoning" in policy.forbidden_source_kinds
        assert "model_inference" in policy.forbidden_source_kinds

    def test_request_accepts_reference_fingerprint_task_kind(self):
        request = _request("reference_fingerprint")
        assert request.task_kind == "reference_fingerprint"
        assert request.policy_version == "reference-fingerprint.v1"

    def test_envelope_rejects_canonical_source_in_canonical_block(self):
        policy = ContextPolicy.for_task("reference_fingerprint")
        env = _envelope(_source("canonical"), block_name="canonical")
        with pytest.raises(ValueError, match="canonical"):
            policy.validate_envelope(env)


class TestReferenceComparePolicy:
    def test_resolves_to_reference_compare_v1(self):
        policy = ContextPolicy.for_task("reference_compare")
        assert policy.version == "reference-compare.v1"

    def test_forbids_reference_original_text(self):
        policy = ContextPolicy.for_task("reference_compare")
        assert "reference_work_text" in policy.forbidden_source_kinds
        assert "raw_reference_text" in policy.forbidden_source_kinds
        assert "generation_prompt" in policy.forbidden_source_kinds
        assert "generation_reasoning" in policy.forbidden_source_kinds
        assert "model_inference" in policy.forbidden_source_kinds

    def test_request_accepts_reference_compare_task_kind(self):
        request = _request("reference_compare")
        assert request.task_kind == "reference_compare"
        assert request.policy_version == "reference-compare.v1"


class TestPolicyIsolationInvariants:
    def test_all_three_quality_policies_exist_and_are_distinct(self):
        p1 = ContextPolicy.for_task("quality_chapter")
        p2 = ContextPolicy.for_task("reference_fingerprint")
        p3 = ContextPolicy.for_task("reference_compare")
        assert len({p1.version, p2.version, p3.version}) == 3

    def test_every_policy_forbids_model_inference(self):
        for kind in ("quality_chapter", "reference_fingerprint", "reference_compare"):
            policy = ContextPolicy.for_task(kind)
            assert "model_inference" in policy.forbidden_source_kinds, kind

    def test_reference_fingerprint_cannot_see_this_book_chapter_prose(self):
        policy = ContextPolicy.for_task("reference_fingerprint")
        assert "chapter_prose" in policy.forbidden_source_kinds

    def test_reference_compare_cannot_see_reference_original_text(self):
        policy = ContextPolicy.for_task("reference_compare")
        assert "reference_work_text" in policy.forbidden_source_kinds
        assert "raw_reference_text" in policy.forbidden_source_kinds

    def test_quality_chapter_cannot_see_generation_artifacts(self):
        policy = ContextPolicy.for_task("quality_chapter")
        assert "generation_prompt" in policy.forbidden_source_kinds
        assert "generation_reasoning" in policy.forbidden_source_kinds

    def test_policy_schema_hash_is_stable_per_version(self):
        p1 = ContextPolicy.for_task("quality_chapter")
        p2 = ContextPolicy.by_version("quality-chapter.v1")
        assert p1.schema_hash == p2.schema_hash

    def test_safe_payload_contains_no_prose_or_secret(self):
        for kind in ("quality_chapter", "reference_fingerprint", "reference_compare"):
            policy = ContextPolicy.for_task(kind)
            payload = policy.safe_payload()
            assert "prose" not in str(payload).lower() or "chapter_prose" in str(
                payload.get("forbidden_source_kinds", [])
            )
            assert "secret" not in payload


class TestRequiredSlotsFailLoud:
    def test_missing_required_slot_raises(self):
        from scribe3.context_engine import CreativeContextEngine

        request = _request(
            "quality_chapter",
            required_slots=("frozen_prose", "approved_contract"),
        )
        snapshot = _snapshot()
        env = _envelope(_source("chapter_prose"), block_name="focus")
        with pytest.raises(ValueError, match="必需 context slot 缺失"):
            CreativeContextEngine._validate_request(request, snapshot, env)

    def test_present_required_slot_passes(self):
        from scribe3.context_engine import CreativeContextEngine

        request = _request(
            "quality_chapter",
            required_slots=("focus",),
        )
        snapshot = _snapshot()
        env = _envelope(_source("chapter_prose"), block_name="focus")
        CreativeContextEngine._validate_request(request, snapshot, env)


class TestSourceRevisionAndDigest:
    def test_source_requires_revision_for_quality_tasks(self):
        source = _source("frozen_prose", revision="rev-42")
        assert source.revision == "rev-42"

    def test_source_content_digest_validated(self):
        source = _source("frozen_prose")
        assert len(source.content_digest) == 64

    def test_invalid_digest_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _source("frozen_prose", content_digest="not-a-hash")
