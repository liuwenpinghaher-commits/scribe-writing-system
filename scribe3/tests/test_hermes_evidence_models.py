from pathlib import Path

from scribe3.hermes_evidence.models import (
    DocumentRecord,
    SnapshotManifest,
    sha256_bytes,
    write_manifest,
)


def test_manifest_is_stable_and_hashes_exact_bytes(tmp_path: Path):
    doc = DocumentRecord(
        document_id="website:abc",
        source_kind="website",
        output_path="pages/a.md",
        content_sha256=sha256_bytes(b"abc"),
        byte_length=3,
        text_length=3,
        semantic_status="content",
        requested_url="https://hermes-agent.nousresearch.com/docs/a",
        final_url="https://hermes-agent.nousresearch.com/docs/a",
    )
    manifest = SnapshotManifest(
        snapshot_id="website-20260719T000000Z",
        source_kind="website",
        source_origin="https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        requested_ref="sitemap",
        resolved_sha=None,
        release_tag=None,
        fetched_at="2026-07-19T00:00:00+00:00",
        crawler_version="1",
        documents=[doc],
    )
    first = write_manifest(tmp_path / "m1.json", manifest)
    second = write_manifest(tmp_path / "m2.json", manifest)
    assert first == second
    assert (tmp_path / "m1.json").read_bytes() == (tmp_path / "m2.json").read_bytes()
    assert doc.content_sha256 == sha256_bytes(b"abc")
