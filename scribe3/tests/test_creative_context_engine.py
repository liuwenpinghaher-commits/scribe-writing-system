"""Creative Context OS 统一编译引擎纵向合同。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest

from scribe3.context_assembler import ContextAssembler, render_envelope_text
from scribe3.context_engine import CreativeContextEngine
from scribe3.context_models import ContextFocus, ContextRequest, ContextSnapshot
from scribe3.context_store import ContextStore


def _snapshot() -> ContextSnapshot:
    return ContextSnapshot(
        session_id="ctx-engine", work="book-a", revision=3,
        thread_id="thread-engine", entry="chapter", directory_path=("chapter",),
        focus=ContextFocus(type="chapter", id="chapter:1", label="第一章"),
        detail_route="chapter:1", chapter=1, phase="draft", focalizer=None,
        previous_revision=2, navigation_id="navigation-engine",
        captured_at=datetime(2026, 7, 20, tzinfo=timezone.utc), context_hash="",
    ).with_hash()


def _request(**overrides) -> ContextRequest:
    payload = {
        "request_id": "request-engine",
        "task_kind": "draft",
        "target_ref": "chapter:1",
        "navigation_snapshot_id": "navigation-engine",
        "work": "book-a",
        "chapter": 1,
        "phase": "draft",
        "required_slots": ("focus", "global"),
        "forbidden_source_kinds": (),
        "policy_version": "generation.v1",
    }
    payload.update(overrides)
    return ContextRequest(**payload)


def test_compile_uses_existing_assembler_once_and_hashes_final_rendered_bytes(
    store, monkeypatch,
):
    calls = []
    real_assemble = ContextAssembler.assemble

    def assemble_spy(self, snapshot, user_query, mode="discussion", **kwargs):
        calls.append((snapshot, user_query, mode, kwargs))
        return real_assemble(self, snapshot, user_query, mode, **kwargs)

    monkeypatch.setattr(ContextAssembler, "assemble", assemble_spy)
    rendered_by_callback = []

    def render(envelope):
        rendered = "系统前缀\n" + render_envelope_text(envelope) + "\n【最终硬协议】"
        rendered_by_callback.append(rendered)
        return rendered

    result = CreativeContextEngine(store).compile(
        _request(), _snapshot(), "续写雨夜", "write", render,
    )

    assert len(calls) == 1
    assert calls[0][1:3] == ("续写雨夜", "write")
    assert result.rendered_input == rendered_by_callback[0]
    expected = hashlib.sha256(result.rendered_input.encode("utf-8")).hexdigest()
    assert result.manifest.actual_input_hash == expected
    assert result.manifest.actual_input_bytes == len(result.rendered_input.encode("utf-8"))
    assert ContextStore(store).get_manifest(result.manifest.manifest_hash) == result.manifest


def test_compile_fails_loud_when_required_slot_has_no_model_input(store):
    request = _request(required_slots=("canonical",))

    with pytest.raises(ValueError, match="canonical"):
        CreativeContextEngine(store).compile(
            request, _snapshot(), "", "write", render_envelope_text,
        )

    assert store._query("SELECT manifest_id FROM context_manifest", {}) == []


def test_compile_filters_forbidden_source_kinds_before_render_and_manifest(store):
    marker = "forbidden-reference-marker"

    class Candidate:
        source_kind = "reference"
        source_id = "material:forbidden"
        text = marker
        work = "book-a"
        provenance = []

    class Retriever:
        def retrieve(self, work, snapshot, query, k):
            return [Candidate()]

    result = CreativeContextEngine(store, retriever=Retriever()).compile(
        _request(forbidden_source_kinds=("reference",)),
        _snapshot(), "参考素材", "write", render_envelope_text,
    )

    assert marker not in result.rendered_input
    assert all(
        source.source_kind != "reference"
        for block in result.envelope.blocks
        for source in block.sources
    )
    assert not any(
        source.source_kind == "reference" and source.included
        for source in result.manifest.sources
    )
    assert any(
        source.source_kind == "reference" and not source.included
        for source in result.manifest.sources
    )


def test_compile_filters_original_kind_before_assembler_remaps_it(store):
    marker = "forbidden-episodic-marker"

    class Candidate:
        source_kind = "episodic"
        source_id = "episode:forbidden"
        text = marker
        work = "book-a"
        provenance = []

    class Retriever:
        def retrieve(self, work, snapshot, query, k):
            return [Candidate()]

    result = CreativeContextEngine(store, retriever=Retriever()).compile(
        _request(forbidden_source_kinds=("episodic",)),
        _snapshot(), "经验回忆", "write", render_envelope_text,
    )

    assert marker not in result.rendered_input
    assert not any(
        source.source_id == "episode:forbidden" and source.included
        for source in result.manifest.sources
    )
    assert any(
        source.source_id == "episode:forbidden" and not source.included
        for source in result.manifest.sources
    )
    assert any(
        omitted.get("source_id") == "episode:forbidden"
        and omitted.get("reason") == "forbidden_source_kind"
        for omitted in result.envelope.omitted
    )


def test_compile_filters_provenance_created_after_primary_blocks(store):
    result = CreativeContextEngine(store).compile(
        _request(forbidden_source_kinds=("provenance",)),
        _snapshot(), "", "write", render_envelope_text,
    )

    provenance = next(block for block in result.envelope.blocks if block.name == "provenance")
    assert provenance.text == ""
    assert provenance.sources == []
    assert not any(
        source.source_kind == "provenance" and source.included
        for source in result.manifest.sources
    )
    assert any(
        source.source_kind == "provenance" and not source.included
        for source in result.manifest.sources
    )


def test_compile_registers_supplemental_render_contributions_with_content_revision(store):
    from scribe3.context_models import ContextSource

    dynamic = "【动态领域块】只允许登记后的内容进入最终输入"
    digest = hashlib.sha256(dynamic.encode("utf-8")).hexdigest()

    def render(envelope):
        return (
            render_envelope_text(envelope) + "\n\n" + dynamic,
            (
                ContextSource(
                    source_id="chapter:1:dynamic",
                    source_kind="scene_truth",
                    work="book-a",
                    content_digest=digest,
                ),
            ),
        )

    result = CreativeContextEngine(store).compile(
        _request(), _snapshot(), "", "write", render,
    )

    source = next(
        source for source in result.manifest.sources
        if source.source_id == "chapter:1:dynamic"
    )
    assert source.included is True
    assert source.block == "supplemental"
    assert source.content_digest == digest
    assert source.revision == f"content-sha256:{digest}"
    assert dynamic in result.rendered_input


def test_compile_rejects_forbidden_supplemental_render_source(store):
    from scribe3.context_models import ContextSource

    marker = "raw-reference-renderer-bypass"

    def render(_envelope):
        return (
            marker,
            (
                ContextSource(
                    source_id="reference:raw:renderer",
                    source_kind="raw_reference_text",
                    work="book-a",
                    content_digest=hashlib.sha256(marker.encode("utf-8")).hexdigest(),
                ),
            ),
        )

    with pytest.raises(ValueError, match="forbidden"):
        CreativeContextEngine(store).compile(
            _request(), _snapshot(), "", "write", render,
        )

    assert store._query("SELECT manifest_id FROM context_manifest", {}) == []


def test_compile_inherits_policy_forbidden_kinds_and_persists_omitted_proof(store):
    marker = "raw-reference-must-never-reach-model"

    class Candidate:
        source_kind = "raw_reference_text"
        source_id = "reference:raw:1"
        text = marker
        work = "book-a"
        revision = "reference-rev-7"
        provenance = []

    class Retriever:
        def retrieve(self, work, snapshot, query, k):
            return [Candidate()]

    result = CreativeContextEngine(store, retriever=Retriever()).compile(
        _request(), _snapshot(), "参考原文", "write", render_envelope_text,
    )

    assert "raw_reference_text" in result.request.forbidden_source_kinds
    assert marker not in result.rendered_input
    omitted = next(
        source for source in result.manifest.sources
        if source.source_id == "reference:raw:1"
    )
    assert omitted.included is False
    assert omitted.reason_code == "forbidden_source_kind"
    assert omitted.revision == "reference-rev-7"
    assert omitted.content_digest == hashlib.sha256(marker.encode("utf-8")).hexdigest()
