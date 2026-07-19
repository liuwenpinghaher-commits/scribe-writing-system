from pathlib import Path
from dataclasses import replace
import hashlib
import json
import os
import threading

import pytest

from scribe3.hermes_evidence.diffing import diff_manifests
from scribe3.hermes_evidence.integrity import (
    classify_semantic_document,
    extract_internal_doc_links,
    validate_snapshot as _production_validate_snapshot,
)
from scribe3.hermes_evidence.models import (
    DocumentRecord,
    SnapshotManifest,
    document_id_for,
    sha256_bytes,
    stable_json_bytes,
    write_manifest,
)
from scribe3.hermes_evidence.policy import classify_repo_path
from scribe3.hermes_evidence.website import output_path_for_url


def validate_snapshot(
    manifest,
    root,
    expected_logical_keys,
    duplicate_explanations=None,
    *,
    manifest_path=None,
):
    return _production_validate_snapshot(
        manifest,
        root,
        expected_logical_keys,
        duplicate_explanations,
        manifest_path=manifest_path or Path(root) / "manifest.json",
    )


def _manifest(documents):
    return SnapshotManifest(
        "s",
        "website",
        "https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        "sitemap",
        None,
        None,
        "2026-07-19T00:00:00+00:00",
        "1",
        documents=documents,
    )


def test_integrity_fails_missing_expected_and_hash_mismatch(tmp_path: Path):
    body = b"# A\n" + b"x" * 300
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages/a.md").write_bytes(body)
    doc = DocumentRecord(
        "a",
        "website",
        "pages/a.md",
        "0" * 64,
        len(body),
        len(body),
        "content",
        logical_key="a",
    )
    report = validate_snapshot(_manifest([doc]), tmp_path, {"a", "b"})
    assert not report.ok
    assert any("missing expected" in error for error in report.errors)
    assert any("hash mismatch" in error for error in report.errors)


def test_diff_reports_path_add_change_remove():
    old = _manifest(
        [
            DocumentRecord(
                "old-a", "website", "a.md", "1", 1, 1, "content", logical_key="a"
            ),
            DocumentRecord(
                "old-b", "website", "b.md", "2", 1, 1, "content", logical_key="b"
            ),
        ]
    )
    new = _manifest(
        [
            DocumentRecord(
                "new-b", "website", "b.md", "3", 1, 1, "content", logical_key="b"
            ),
            DocumentRecord(
                "new-c", "website", "c.md", "4", 1, 1, "content", logical_key="c"
            ),
        ]
    )
    assert diff_manifests(old, new) == {
        "added": ["c"],
        "changed": ["b"],
        "removed": ["a"],
    }


def _semantic_record(**changes):
    values = {
        "document_id": "website:semantic",
        "source_kind": "website",
        "output_path": "pages/guide.md",
        "content_sha256": "0" * 64,
        "byte_length": 0,
        "text_length": 0,
        "semantic_status": "content",
        "requested_url": "https://hermes-agent.nousresearch.com/docs/guide",
        "final_url": "https://hermes-agent.nousresearch.com/docs/guide",
        "mime_type": "text/html",
        "http_status": 200,
        "title": "Guide",
        "h1": "Guide",
        "logical_key": "https://hermes-agent.nousresearch.com/docs/guide",
    }
    values.update(changes)
    return DocumentRecord(**values)


@pytest.mark.parametrize(
    ("title", "lead"),
    [
        ("404 handling", "This guide explains how to troubleshoot 404 handling."),
        ("Login troubleshooting", "This tutorial shows how to debug login failures."),
    ],
)
def test_semantic_classifier_accepts_real_documentation_about_error_topics(
    title: str, lead: str
):
    body = f"# {title}\n\n{lead}\n\n" + ("Useful procedure and examples. " * 15)
    record = _semantic_record(
        title=title,
        h1=title,
        byte_length=len(body.encode()),
        text_length=len(body),
    )

    assert classify_semantic_document(record, body.encode()) == ()


@pytest.mark.parametrize(
    ("title", "body", "expected"),
    [
        (
            "404 - Page Not Found",
            "# 404 - Page Not Found\n\nThe requested page could not be found.\n" + "x" * 220,
            "soft_404",
        ),
        (
            "Sign In",
            "# Sign In\n\nSign in to continue and access this page.\n" + "x" * 220,
            "soft_login",
        ),
        (
            "Just a moment",
            "# Just a moment\n\nChecking your browser. Verify you are human. Cloudflare.\n"
            + "x" * 220,
            "soft_anti_bot",
        ),
        (
            "Service Unavailable",
            "# Service Unavailable\n\nThe server is unavailable. Try again later.\n"
            + "x" * 220,
            "soft_server_error",
        ),
    ],
)
def test_semantic_classifier_rejects_soft_error_pages(
    title: str, body: str, expected: str
):
    record = _semantic_record(
        title=title,
        h1=title,
        byte_length=len(body.encode()),
        text_length=len(body),
    )

    assert expected in classify_semantic_document(record, body.encode())


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Please sign in to continue and access this page.", "soft_login"),
        ("You must sign in to continue to access this page.", "soft_login"),
        ("The requested page could not be found. Try another location.", "soft_404"),
        ("Browser verification is required before you continue.", "soft_anti_bot"),
        ("Access denied. You are not authorized to view this page.", "soft_access_denied"),
        ("Service temporarily unavailable. Please try again later.", "soft_server_error"),
    ],
)
def test_semantic_classifier_rejects_soft_error_opening_variants(
    body: str, expected: str
):
    text = body + "\n\n" + ("Generic response content. " * 15)
    record = _semantic_record(
        title="Hermes Agent",
        h1=None,
        byte_length=len(text.encode()),
        text_length=len(text),
    )

    assert expected in classify_semantic_document(record, text.encode())


@pytest.mark.parametrize(
    "lead",
    [
        "This documentation describes how sign in errors are handled.",
        "This tutorial shows how browser verification failures are diagnosed.",
        "This troubleshooting guide explains service unavailable responses.",
    ],
)
def test_semantic_classifier_keeps_documentation_lead_false_positive_guard(lead: str):
    text = lead + "\n\n" + ("Detailed public procedure and examples. " * 12)
    record = _semantic_record(
        title="Troubleshooting",
        h1=None,
        byte_length=len(text.encode()),
        text_length=len(text),
    )

    assert not set(classify_semantic_document(record, text.encode())) & {
        "soft_login",
        "soft_404",
        "soft_anti_bot",
        "soft_access_denied",
        "soft_server_error",
    }


def test_semantic_classifier_does_not_treat_setup_instruction_as_login_wall():
    text = (
        "Please sign in to continue with the setup steps below.\n\n"
        + ("Detailed public procedure and examples. " * 12)
    )
    record = _semantic_record(
        title="Authentication setup",
        h1=None,
        byte_length=len(text.encode()),
        text_length=len(text),
    )

    assert "soft_login" not in classify_semantic_document(record, text.encode())


def test_semantic_classifier_rejects_empty_link_only_and_navigation_heavy_content():
    empty = _semantic_record(byte_length=0, text_length=0)
    assert "empty_content" in classify_semantic_document(empty, b"")

    links = "# Links\n\n" + "\n".join(
        f"- [Documentation item {index}](/docs/item-{index})" for index in range(12)
    )
    link_record = _semantic_record(
        title="Links",
        h1="Links",
        byte_length=len(links.encode()),
        text_length=len(links),
    )
    link_errors = classify_semantic_document(link_record, links.encode())
    assert "link_only_content" in link_errors or "navigation_heavy_content" in link_errors

    search_record = replace(
        link_record,
        semantic_status="navigation_only",
        requested_url="https://hermes-agent.nousresearch.com/docs/search",
        final_url="https://hermes-agent.nousresearch.com/docs/search",
        logical_key="https://hermes-agent.nousresearch.com/docs/search",
    )
    assert not {
        "link_only_content",
        "navigation_heavy_content",
        "unexpected_short_content",
    } & set(classify_semantic_document(search_record, links.encode()))


def test_semantic_classifier_rejects_cross_origin_mime_mismatch_and_secret_residual():
    body = ("# Guide\n\nPublic documentation. " + "details " * 40).encode()
    record = _semantic_record(byte_length=len(body), text_length=len(body.decode()))
    unsafe = replace(
        record,
        final_url="https://example.test/docs/guide",
        mime_type="application/pdf",
    )
    errors = classify_semantic_document(unsafe, body)
    assert "cross_origin_redirect" in errors
    assert "mime_extension_mismatch" in errors

    secret_body = body + b"\nAuthorization: Bearer " + (b"x" * 32)
    assert "suspected_secret" in classify_semantic_document(record, secret_body)


def test_extract_internal_doc_links_normalizes_website_and_repository_links():
    website = _semantic_record(
        requested_url="https://hermes-agent.nousresearch.com/docs/guides/start",
        final_url="https://hermes-agent.nousresearch.com/docs/guides/start",
        logical_key="https://hermes-agent.nousresearch.com/docs/guides/start",
    )
    website_body = """
[Hooks](../hooks)
[Tools](/docs/tools#usage)
[Absolute](https://hermes-agent.nousresearch.com/docs/reference?view=all#x)
[External](https://example.test/docs/no)
[Same page](#section)
"""
    assert extract_internal_doc_links(website, website_body) == {
        "https://hermes-agent.nousresearch.com/docs/hooks",
        "https://hermes-agent.nousresearch.com/docs/reference",
        "https://hermes-agent.nousresearch.com/docs/tools",
    }

    repository = DocumentRecord(
        "release:guide",
        "release",
        "docs/guides/start.md",
        "0" * 64,
        0,
        0,
        "content",
        repo_path="docs/guides/start.md",
        logical_key="docs/guides/start.md",
    )
    repository_body = """
[Hooks](../hooks.md#setup)
[Readme](/README.md)
[Website](https://hermes-agent.nousresearch.com/docs/tools)
[Image](../image.png)
"""
    assert extract_internal_doc_links(repository, repository_body) == {
        "README.md",
        "docs/hooks.md",
    }


def _article(title: str, links: str = "") -> str:
    return (
        f"# {title}\n\n"
        f"This guide explains the {title.lower()} capability with safe examples.\n\n"
        + ("Detailed public procedure and expected behavior. " * 10)
        + links
    ).rstrip() + "\n"


def _write_website_document(
    root: Path,
    slug: str,
    body: str,
    *,
    semantic_status: str = "content",
    title: str | None = None,
    h1: str | None = None,
    final_url: str | None = None,
    mime_type: str = "text/html",
) -> DocumentRecord:
    logical_key = f"https://hermes-agent.nousresearch.com/docs/{slug}"
    output_path = output_path_for_url(logical_key)
    target = root / output_path
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = body.encode("utf-8")
    target.write_bytes(raw)
    heading = body.splitlines()[0].removeprefix("# ") if body else None
    digest = sha256_bytes(raw)
    return DocumentRecord(
        document_id_for("website", logical_key, digest),
        "website",
        output_path.as_posix(),
        digest,
        len(raw),
        len(body),
        semantic_status,
        requested_url=logical_key,
        final_url=final_url or logical_key,
        mime_type=mime_type,
        http_status=200,
        title=title if title is not None else heading,
        h1=h1 if h1 is not None else heading,
        website_snapshot_id="website-s",
        logical_key=logical_key,
    )


def _website_snapshot(documents, **changes):
    values = {
        "snapshot_id": "website-s",
        "source_kind": "website",
        "source_origin": "https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        "requested_ref": "sitemap",
        "resolved_sha": None,
        "release_tag": None,
        "fetched_at": "2026-07-20T00:00:00+00:00",
        "crawler_version": "1",
        "documents": list(documents),
        "expected_document_count": len(documents),
    }
    values.update(changes)
    return SnapshotManifest(**values)


def _persist_manifest(root: Path, manifest: SnapshotManifest) -> None:
    write_manifest(root / "manifest.json", manifest)


def _explanation_note(
    group: frozenset[str], *, kind: str | None = None, reason: str = "intentional"
) -> str:
    payload = {
        "version": 1,
        "kind": kind or ("navigation" if len(group) == 1 else "duplicate"),
        "logical_keys": sorted(group),
        "reason": reason,
    }
    return "integrity_explanation:v1:" + stable_json_bytes(payload).decode().strip()


def _persisted_explanations(*groups: frozenset[str]) -> list[str]:
    return [_explanation_note(group) for group in groups]


def _git_blob_sha(body: bytes) -> str:
    header = f"blob {len(body)}\0".encode("ascii")
    return hashlib.sha1(header + body, usedforsecurity=False).hexdigest()


def _write_release_document(root: Path, repo_path: str, body: str) -> DocumentRecord:
    raw = body.encode()
    target = root / repo_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    digest = sha256_bytes(raw)
    language, category, is_skill, is_runtime_contract = classify_repo_path(repo_path)
    return DocumentRecord(
        document_id_for("release", repo_path, digest),
        "release",
        repo_path,
        digest,
        len(raw),
        len(body),
        "content",
        repo_path=repo_path,
        language=language,
        category=category,
        source_commit="a" * 40,
        source_blob_sha=_git_blob_sha(raw),
        logical_key=repo_path,
        is_skill=is_skill,
        is_runtime_contract=is_runtime_contract,
    )


def _release_snapshot(documents: list[DocumentRecord]) -> SnapshotManifest:
    return SnapshotManifest(
        "release-s",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        documents=documents,
        expected_document_count=len(documents),
        tree_truncated=False,
    )


def test_validate_snapshot_accepts_complete_articles_and_explained_search_shell(
    tmp_path: Path,
):
    hooks = _write_website_document(
        tmp_path,
        "hooks",
        _article("Hooks", "\n[Tools](/docs/tools)\n[Search](/docs/search)"),
    )
    tools = _write_website_document(
        tmp_path,
        "tools",
        _article("Tools", "\n[Hooks](/docs/hooks)"),
    )
    search_body = "# Search\n\n[Hooks](/docs/hooks)\n[Tools](/docs/tools)\n"
    search = _write_website_document(
        tmp_path,
        "search",
        search_body,
        semantic_status="navigation_only",
    )
    manifest = _website_snapshot([hooks, tools, search])
    manifest.notes = _persisted_explanations(frozenset({search.logical_key}))
    _persist_manifest(tmp_path, manifest)
    expected = {document.logical_key for document in manifest.documents}

    report = validate_snapshot(
        manifest,
        tmp_path,
        expected,
        {frozenset({search.logical_key})},
    )

    assert report.ok, report.errors
    assert not report.warnings


def test_validate_snapshot_requires_exact_persisted_navigation_explanation(
    tmp_path: Path,
):
    search = _write_website_document(
        tmp_path,
        "search",
        "# Search\n\n[Hooks](/docs/hooks)\n",
        semantic_status="navigation_only",
    )
    manifest = _website_snapshot(
        [search], exclusions=[{"logical_key": "https://hermes-agent.nousresearch.com/docs/hooks", "reason": "not_in_sitemap"}], expected_document_count=2
    )
    _persist_manifest(tmp_path, manifest)

    missing = validate_snapshot(
        manifest,
        tmp_path,
        {search.logical_key, "https://hermes-agent.nousresearch.com/docs/hooks"},
    )
    stale = validate_snapshot(
        manifest,
        tmp_path,
        {search.logical_key, "https://hermes-agent.nousresearch.com/docs/hooks"},
        {frozenset({"not-the-search-page"})},
    )

    assert any("navigation explanation" in error for error in missing.errors)
    assert any("explanation cross-check mismatch" in error for error in stale.errors)


def test_validate_snapshot_rechecks_sizes_text_semantics_and_secret_residual(
    tmp_path: Path,
):
    body = _article("Hooks") + "Authorization: Bearer " + ("x" * 32) + "\n"
    document = _write_website_document(tmp_path, "hooks", body)
    document = replace(
        document,
        byte_length=document.byte_length + 1,
        text_length=document.text_length + 1,
    )
    manifest = _website_snapshot([document])
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {document.logical_key})

    assert any("byte length mismatch" in error for error in report.errors)
    assert any("text length mismatch" in error for error in report.errors)
    assert any("suspected_secret" in error for error in report.errors)


def test_validate_snapshot_rejects_symlink_and_path_escape(tmp_path: Path):
    body = _article("Hooks")
    raw = body.encode()
    digest = sha256_bytes(raw)
    outside = tmp_path / "outside.md"
    outside.write_bytes(raw)

    symlink_root = tmp_path / "symlink-snapshot"
    (symlink_root / "pages").mkdir(parents=True)
    (symlink_root / "pages/hooks.md").symlink_to(outside)
    symlink_url = "https://hermes-agent.nousresearch.com/docs/hooks"
    symlink_doc = DocumentRecord(
        document_id_for("website", symlink_url, digest),
        "website",
        "pages/hooks.md",
        digest,
        len(raw),
        len(body),
        "content",
        requested_url=symlink_url,
        final_url=symlink_url,
        mime_type="text/html",
        http_status=200,
        title="Hooks",
        h1="Hooks",
        website_snapshot_id="website-s",
        logical_key=symlink_url,
    )
    symlink_manifest = _website_snapshot([symlink_doc])
    _persist_manifest(symlink_root, symlink_manifest)

    escape_root = tmp_path / "escape-snapshot"
    escape_root.mkdir()
    escape_url = "https://hermes-agent.nousresearch.com/docs/escape"
    escape_doc = replace(
        symlink_doc,
        document_id=document_id_for("website", escape_url, digest),
        output_path="../outside.md",
        requested_url=escape_url,
        final_url=escape_url,
        logical_key=escape_url,
    )
    escape_manifest = _website_snapshot([escape_doc])
    _persist_manifest(escape_root, escape_manifest)

    symlink_report = validate_snapshot(symlink_manifest, symlink_root, {symlink_url})
    escape_report = validate_snapshot(escape_manifest, escape_root, {escape_url})

    assert any("unsafe file" in error for error in symlink_report.errors)
    assert any("unsafe file" in error for error in escape_report.errors)


def test_validate_snapshot_requires_and_verifies_canonical_serialized_manifest(
    tmp_path: Path,
):
    missing_root = tmp_path / "missing"
    document = _write_website_document(missing_root, "hooks", _article("Hooks"))
    manifest = _website_snapshot([document])
    missing = validate_snapshot(manifest, missing_root, {document.logical_key})
    assert any("missing serialized manifest" in error for error in missing.errors)

    tampered_root = tmp_path / "tampered"
    document = _write_website_document(tampered_root, "hooks", _article("Hooks"))
    manifest = _website_snapshot([document])
    _persist_manifest(tampered_root, manifest)
    path = tampered_root / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["notes"] = ["tampered without recomputing hash"]
    path.write_bytes(stable_json_bytes(payload))

    tampered = validate_snapshot(manifest, tampered_root, {document.logical_key})
    assert any("manifest hash mismatch" in error for error in tampered.errors)


def test_validate_snapshot_rejects_missing_internal_link_and_wrong_page_identity(
    tmp_path: Path,
):
    body = _article("Accounts", "\n[Missing](/docs/missing)")
    document = _write_website_document(
        tmp_path,
        "hooks",
        body,
        title="Billing Portal",
        h1="Accounts",
    )
    manifest = _website_snapshot([document])
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {document.logical_key})

    assert any("unresolved internal link" in error for error in report.errors)
    assert any("wrong_page_identity" in error for error in report.errors)


def test_validate_snapshot_requires_exact_nonoverlapping_expected_partition(
    tmp_path: Path,
):
    document = _write_website_document(tmp_path, "hooks", _article("Hooks"))
    manifest = _website_snapshot(
        [document],
        exclusions=[{"logical_key": document.logical_key, "reason": "duplicate"}],
        expected_document_count=1,
    )
    _persist_manifest(tmp_path, manifest)

    overlap = validate_snapshot(manifest, tmp_path, {document.logical_key})
    wrong_count = validate_snapshot(
        replace(manifest, expected_document_count=2),
        tmp_path,
        {document.logical_key},
    )

    assert any("partition overlap" in error for error in overlap.errors)
    assert any("expected document count mismatch" in error for error in wrong_count.errors)


def test_validate_snapshot_requires_exact_duplicate_explanation(tmp_path: Path):
    body = _article("Shared")
    first = _write_website_document(tmp_path, "first", body)
    second = _write_website_document(tmp_path, "second", body)
    manifest = _website_snapshot([first, second])
    _persist_manifest(tmp_path, manifest)
    expected = {first.logical_key, second.logical_key}

    unexplained = validate_snapshot(manifest, tmp_path, expected)
    manifest.notes = _persisted_explanations(frozenset(expected))
    _persist_manifest(tmp_path, manifest)
    explained = validate_snapshot(
        manifest,
        tmp_path,
        expected,
        {frozenset(expected)},
    )

    assert any("unexplained duplicate" in error for error in unexplained.errors)
    assert explained.ok, explained.errors
    assert explained.duplicate_groups == (tuple(sorted(expected)),)


def test_validate_snapshot_rejects_source_kind_commit_and_version_tier_merging(
    tmp_path: Path,
):
    capability = "hooks-capability"
    records = []
    for source_kind, output_path, commit, marker in [
        ("release", "release.md", "a" * 40, "release"),
        ("main", "main.md", "b" * 40, "main"),
        ("runtime", "runtime.md", None, "runtime"),
    ]:
        body = _article(marker.title()).encode()
        (tmp_path / output_path).write_bytes(body)
        digest = sha256_bytes(body)
        records.append(
            DocumentRecord(
                document_id_for(source_kind, capability, digest),
                source_kind,
                output_path,
                digest,
                len(body),
                len(body.decode()),
                "content",
                repo_path=output_path if source_kind != "runtime" else None,
                mime_type="text/markdown",
                source_commit=commit,
                logical_key=capability,
                is_runtime_contract=source_kind == "runtime",
            )
        )
    manifest = SnapshotManifest(
        "release-s",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        documents=records,
        expected_document_count=1,
    )
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {capability})

    assert any("source kind mismatch" in error for error in report.errors)
    assert any("source commit mismatch" in error for error in report.errors)
    assert any("duplicate logical key" in error for error in report.errors)


def test_diff_refuses_cross_tier_comparison_and_duplicate_logical_keys():
    release = SnapshotManifest(
        "release",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        documents=[
            DocumentRecord(
                "release:hooks",
                "release",
                "hooks.md",
                "1",
                1,
                1,
                "content",
                logical_key="hooks",
            )
        ],
        tree_truncated=False,
    )
    main = replace(
        release,
        snapshot_id="main",
        source_kind="main",
        requested_ref="main",
        release_tag=None,
        documents=[replace(release.documents[0], source_kind="main")],
    )
    runtime = replace(
        release,
        snapshot_id="runtime",
        source_kind="runtime",
        requested_ref="runtime",
        resolved_sha=None,
        release_tag=None,
        documents=[replace(release.documents[0], source_kind="runtime")],
    )

    for other in (main, runtime):
        with pytest.raises(ValueError, match="source kind"):
            diff_manifests(release, other)

    duplicate = replace(
        release,
        documents=[release.documents[0], replace(release.documents[0], document_id="x")],
    )
    with pytest.raises(ValueError, match="duplicate logical key"):
        diff_manifests(duplicate, release)


def test_fixed_release_snapshot_is_reproducible_with_controlled_github_fixture(
    tmp_path: Path,
):
    from scribe3.hermes_evidence.github import snapshot_repository

    commit_sha = "a" * 40
    hooks_body = _article("Hooks").encode()
    skill_body = _article("Skill").encode()
    blobs = {
        _git_blob_sha(hooks_body): hooks_body,
        _git_blob_sha(skill_body): skill_body,
    }
    blob_shas = list(blobs)

    class FakeGitHubClient:
        def resolve_ref(self, ref):
            assert ref == "v2026.7.7.2"
            return commit_sha

        def tree_payload(self, sha):
            assert sha == commit_sha
            return {
                "truncated": False,
                "tree": [
                    {
                        "path": "skills/x/SKILL.md",
                        "type": "blob",
                        "sha": blob_shas[1],
                        "size": len(blobs[blob_shas[1]]),
                    },
                    {
                        "path": "docs/hooks.md",
                        "type": "blob",
                        "sha": blob_shas[0],
                        "size": len(blobs[blob_shas[0]]),
                    },
                ],
            }

        def blob(self, sha):
            return blobs[sha]

    manifests = [
        snapshot_repository(
            FakeGitHubClient(),
            "v2026.7.7.2",
            f"release-run-{index}",
            tmp_path / f"run-{index}",
            f"2026-07-20T00:00:0{index}+00:00",
        )
        for index in range(2)
    ]
    for index, manifest in enumerate(manifests):
        write_manifest(tmp_path / f"run-{index}/manifest.json", manifest)

    assert [
        {document.logical_key for document in manifest.documents}
        for manifest in manifests
    ] == [
        {"docs/hooks.md", "skills/x/SKILL.md"},
        {"docs/hooks.md", "skills/x/SKILL.md"},
    ]
    assert [
        {document.logical_key: document.source_blob_sha for document in manifest.documents}
        for manifest in manifests
    ][0] == [
        {document.logical_key: document.source_blob_sha for document in manifest.documents}
        for manifest in manifests
    ][1]
    assert [
        {document.logical_key: document.content_sha256 for document in manifest.documents}
        for manifest in manifests
    ][0] == [
        {document.logical_key: document.content_sha256 for document in manifest.documents}
        for manifest in manifests
    ][1]

    serialized = [
        json.loads((tmp_path / f"run-{index}/manifest.json").read_text(encoding="utf-8"))
        for index in range(2)
    ]
    for payload in serialized:
        for unstable in (
            "fetched_at",
            "snapshot_id",
            "previous_snapshot_id",
            "manifest_sha256",
        ):
            payload.pop(unstable, None)
    assert serialized[0] == serialized[1]


def test_validate_snapshot_binds_git_blob_identity_to_actual_bytes(tmp_path: Path):
    body = _article("Hooks").encode()
    output = tmp_path / "docs/hooks.md"
    output.parent.mkdir(parents=True)
    output.write_bytes(body)
    logical_key = "docs/hooks.md"
    digest = sha256_bytes(body)
    document = DocumentRecord(
        document_id_for("release", logical_key, digest),
        "release",
        logical_key,
        digest,
        len(body),
        len(body.decode()),
        "content",
        repo_path=logical_key,
        source_commit="a" * 40,
        source_blob_sha="b" * 40,
        logical_key=logical_key,
    )
    manifest = SnapshotManifest(
        "release",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        documents=[document],
        expected_document_count=1,
    )
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {logical_key})
    assert any("git blob hash mismatch" in error for error in report.errors)


def test_validate_snapshot_rejects_document_error_even_if_excluded(tmp_path: Path):
    document = _write_website_document(tmp_path, "hooks", _article("Hooks"))
    document = replace(document, error="pdf_text_extraction_failed")
    manifest = _website_snapshot(
        [document],
        exclusions=[{"logical_key": document.logical_key, "reason": "failed"}],
        expected_document_count=1,
    )
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {document.logical_key})
    assert any("document error" in error for error in report.errors)


def test_validate_snapshot_requires_explanations_to_be_manifest_hashed(tmp_path: Path):
    body = _article("Shared")
    first = _write_website_document(tmp_path, "first", body)
    second = _write_website_document(tmp_path, "second", body)
    group = frozenset({first.logical_key, second.logical_key})
    manifest = _website_snapshot([first, second])
    _persist_manifest(tmp_path, manifest)

    unpersisted = validate_snapshot(manifest, tmp_path, set(group), {group})
    assert any("explanation cross-check mismatch" in error for error in unpersisted.errors)

    manifest.notes = _persisted_explanations(group)
    _persist_manifest(tmp_path, manifest)
    persisted = validate_snapshot(manifest, tmp_path, set(group), {group})
    assert persisted.ok, persisted.errors


def test_extract_internal_doc_links_closes_reference_html_and_autolinks():
    record = _semantic_record()
    body = """
[Hooks][hooks]
[hooks]: /docs/hooks
<a href="/docs/html">HTML</a>
<https://hermes-agent.nousresearch.com/docs/autolink>
"""
    assert extract_internal_doc_links(record, body) == {
        "https://hermes-agent.nousresearch.com/docs/autolink",
        "https://hermes-agent.nousresearch.com/docs/hooks",
        "https://hermes-agent.nousresearch.com/docs/html",
    }


def test_wrong_page_identity_combines_path_title_h1_without_topic_false_positive():
    legitimate_body = _article("Getting Started")
    legitimate = _semantic_record(
        output_path="pages/getting-started.md",
        requested_url="https://hermes-agent.nousresearch.com/docs/getting-started",
        final_url="https://hermes-agent.nousresearch.com/docs/getting-started",
        logical_key="https://hermes-agent.nousresearch.com/docs/getting-started",
        title="Installation",
        h1="Getting Started",
        byte_length=len(legitimate_body.encode()),
        text_length=len(legitimate_body),
    )
    assert "wrong_page_identity" not in classify_semantic_document(
        legitimate, legitimate_body.encode()
    )

    wrong_body = _article("Billing Portal")
    wrong = _semantic_record(
        output_path="pages/hooks.md",
        requested_url="https://hermes-agent.nousresearch.com/docs/hooks",
        final_url="https://hermes-agent.nousresearch.com/docs/hooks",
        logical_key="https://hermes-agent.nousresearch.com/docs/hooks",
        title="Billing Portal",
        h1="Billing Portal",
        byte_length=len(wrong_body.encode()),
        text_length=len(wrong_body),
    )
    assert "wrong_page_identity" in classify_semantic_document(
        wrong, wrong_body.encode()
    )


def test_validate_snapshot_rejects_fifo_without_blocking(tmp_path: Path):
    (tmp_path / "pages").mkdir()
    fifo = tmp_path / "pages/hooks.md"
    os.mkfifo(fifo)
    logical_key = "https://hermes-agent.nousresearch.com/docs/hooks"
    document = DocumentRecord(
        document_id_for("website", logical_key, "0" * 64),
        "website",
        "pages/hooks.md",
        "0" * 64,
        0,
        0,
        "content",
        requested_url=logical_key,
        final_url=logical_key,
        http_status=200,
        website_snapshot_id="website-s",
        logical_key=logical_key,
    )
    manifest = _website_snapshot([document])
    _persist_manifest(tmp_path, manifest)
    reports = []
    worker = threading.Thread(
        target=lambda: reports.append(validate_snapshot(manifest, tmp_path, {logical_key})),
        daemon=True,
    )
    worker.start()
    worker.join(timeout=0.25)

    assert not worker.is_alive(), "FIFO validation blocked"
    assert any("unsafe file" in error for error in reports[0].errors)


def test_validate_snapshot_uses_explicit_manifest_path_separate_from_snapshot_root(
    tmp_path: Path,
):
    snapshot_root = tmp_path / "snapshots/website-s"
    manifest_path = tmp_path / "manifests/website-s.json"
    document = _write_website_document(snapshot_root, "hooks", _article("Hooks"))
    manifest = _website_snapshot([document])
    write_manifest(manifest_path, manifest)

    report = validate_snapshot(
        manifest,
        snapshot_root,
        {document.logical_key},
        manifest_path=manifest_path,
    )
    missing_path = _production_validate_snapshot(
        manifest, snapshot_root, {document.logical_key}
    )

    assert report.ok, report.errors
    assert any("manifest path required" in error for error in missing_path.errors)


def test_validate_snapshot_rejects_duplicate_and_conflicting_partition_rows(
    tmp_path: Path,
):
    root = tmp_path / "snapshot"
    root.mkdir()
    key = "https://hermes-agent.nousresearch.com/docs/excluded"
    conflict = "https://hermes-agent.nousresearch.com/docs/other"
    manifest = _website_snapshot(
        [],
        exclusions=[
            {"logical_key": key, "requested_url": key, "reason": "not selected"},
            {"logical_key": key, "requested_url": conflict, "reason": "conflict"},
        ],
        expected_document_count=1,
    )
    manifest_path = tmp_path / "manifests/partition.json"
    write_manifest(manifest_path, manifest)

    report = validate_snapshot(
        manifest, root, {key}, manifest_path=manifest_path
    )

    assert any("duplicate exclusion identity" in error for error in report.errors)
    assert any("conflicting row identity" in error for error in report.errors)


def test_validate_snapshot_rejects_unknown_runtime_masquerade_and_truncated_repo(
    tmp_path: Path,
):
    root = tmp_path / "snapshot"
    root.mkdir()

    unknown = SnapshotManifest(
        "unknown",
        "mystery",  # type: ignore[arg-type]
        "mystery",
        "mystery",
        None,
        None,
        "2026-07-20T00:00:00+00:00",
        "1",
        expected_document_count=0,
    )
    unknown_path = tmp_path / "manifests/unknown.json"
    write_manifest(unknown_path, unknown)
    unknown_report = validate_snapshot(
        unknown, root, set(), manifest_path=unknown_path
    )

    runtime = SnapshotManifest(
        "runtime",
        "runtime",
        "https://github.com/NousResearch/hermes-agent",
        "main",
        "a" * 40,
        None,
        "2026-07-20T00:00:00+00:00",
        "1",
        expected_document_count=0,
        tree_truncated=False,
    )
    runtime_path = tmp_path / "manifests/runtime.json"
    write_manifest(runtime_path, runtime)
    runtime_report = validate_snapshot(
        runtime, root, set(), manifest_path=runtime_path
    )

    release = SnapshotManifest(
        "release",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        expected_document_count=0,
        tree_truncated=True,
    )
    release_path = tmp_path / "manifests/release.json"
    write_manifest(release_path, release)
    release_report = validate_snapshot(
        release, root, set(), manifest_path=release_path
    )

    assert any("unknown source kind" in error for error in unknown_report.errors)
    assert any("invalid runtime source identity" in error for error in runtime_report.errors)
    assert any("repository tree incomplete" in error for error in release_report.errors)


def test_validate_snapshot_rejects_repository_path_and_skill_classification_drift(
    tmp_path: Path,
):
    body = _article("Skill").encode()
    output = tmp_path / "skills/x/SKILL.md"
    output.parent.mkdir(parents=True)
    output.write_bytes(body)
    logical_key = "skills/x/SKILL.md"
    digest = sha256_bytes(body)
    document = DocumentRecord(
        document_id_for("release", logical_key, digest),
        "release",
        "wrong/output.md",
        digest,
        len(body),
        len(body.decode()),
        "content",
        repo_path=logical_key,
        source_commit="a" * 40,
        source_blob_sha=_git_blob_sha(body),
        logical_key=logical_key,
        is_skill=False,
    )
    manifest = SnapshotManifest(
        "release",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        documents=[document],
        expected_document_count=1,
        tree_truncated=False,
    )
    manifest_path = tmp_path / "manifests/skill.json"
    write_manifest(manifest_path, manifest)

    report = validate_snapshot(
        manifest, tmp_path, {logical_key}, manifest_path=manifest_path
    )

    assert any("repository path identity mismatch" in error for error in report.errors)
    assert any("repository classification mismatch" in error for error in report.errors)


def test_diff_rejects_unknown_and_internally_inconsistent_source_identity():
    unknown = SnapshotManifest(
        "unknown",
        "mystery",  # type: ignore[arg-type]
        "mystery",
        "mystery",
        None,
        None,
        "2026-07-20T00:00:00+00:00",
        "1",
        tree_truncated=None,
    )
    with pytest.raises(ValueError, match="source identity"):
        diff_manifests(unknown, unknown)

    malformed_main = SnapshotManifest(
        "main",
        "main",
        "https://github.com/NousResearch/hermes-agent",
        "main",
        "a" * 40,
        "v-wrong",
        "2026-07-20T00:00:00+00:00",
        "1",
        tree_truncated=False,
    )
    with pytest.raises(ValueError, match="source identity"):
        diff_manifests(malformed_main, malformed_main)


def test_validate_snapshot_applies_text_semantics_to_pdf_sidecar(tmp_path: Path):
    root = tmp_path / "snapshot"
    pdf = b"%PDF-1.7\npublic-binary"
    pdf_path = root / "docs/guide.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(pdf)
    sidecar = root / "_extracted/docs/guide.pdf.txt"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("x", encoding="utf-8")
    logical_key = "docs/guide.pdf"
    digest = sha256_bytes(pdf)
    document = DocumentRecord(
        document_id_for("release", logical_key, digest),
        "release",
        logical_key,
        digest,
        len(pdf),
        1,
        "content",
        repo_path=logical_key,
        source_commit="a" * 40,
        source_blob_sha=_git_blob_sha(pdf),
        logical_key=logical_key,
        mime_type="application/pdf",
        extracted_text_path="_extracted/docs/guide.pdf.txt",
        extracted_text_sha256=sha256_bytes(b"x"),
    )
    manifest = SnapshotManifest(
        "release-pdf",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        documents=[document],
        expected_document_count=1,
        tree_truncated=False,
    )
    manifest_path = tmp_path / "manifests/pdf.json"
    write_manifest(manifest_path, manifest)

    report = validate_snapshot(
        manifest, root, {logical_key}, manifest_path=manifest_path
    )
    assert any("unexpected_short_content" in error for error in report.errors)

    noncanonical = replace(document, extracted_text_path="sidecar.txt")
    (root / "sidecar.txt").write_text("x", encoding="utf-8")
    noncanonical_manifest = replace(manifest, documents=[noncanonical])
    noncanonical_path = tmp_path / "manifests/pdf-noncanonical.json"
    write_manifest(noncanonical_path, noncanonical_manifest)
    noncanonical_report = validate_snapshot(
        noncanonical_manifest,
        root,
        {logical_key},
        manifest_path=noncanonical_path,
    )
    assert any("noncanonical extracted text path" in error for error in noncanonical_report.errors)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Sign in to continue and access this page. " + "x" * 220, "soft_login"),
        ("Page not found. The requested resource does not exist. " + "x" * 220, "soft_404"),
        ("Checking your browser. Verify you are human. " + "x" * 220, "soft_anti_bot"),
        ("Access denied. You do not have permission to view this page. " + "x" * 220, "soft_access_denied"),
        ("Service unavailable. The server is unavailable; try again later. " + "x" * 220, "soft_server_error"),
    ],
)
def test_semantic_classifier_rejects_strong_body_errors_without_metadata(
    body: str, expected: str
):
    record = _semantic_record(
        title=None,
        h1=None,
        byte_length=len(body.encode()),
        text_length=len(body),
    )
    assert expected in classify_semantic_document(record, body.encode())


def test_semantic_classifier_does_not_misread_metadata_free_troubleshooting():
    body = (
        "This guide explains how to troubleshoot sign in to continue, page not found, "
        "access denied, and service unavailable responses.\n\n" + "Procedure details. " * 20
    )
    record = _semantic_record(
        title=None,
        h1=None,
        byte_length=len(body.encode()),
        text_length=len(body),
    )
    assert not {
        "soft_login",
        "soft_404",
        "soft_access_denied",
        "soft_server_error",
    } & set(classify_semantic_document(record, body.encode()))


def test_internal_link_canonicalization_supports_shortcuts_html_and_directories():
    website = _semantic_record()
    website_body = """
[Hooks][]
[Tools]
[hooks]: /docs/hooks/
[tools]: /docs/tools/index.html?view=all#usage
<a href=/docs/html/>HTML</a>
"""
    assert extract_internal_doc_links(website, website_body) == {
        "https://hermes-agent.nousresearch.com/docs/hooks",
        "https://hermes-agent.nousresearch.com/docs/html",
        "https://hermes-agent.nousresearch.com/docs/tools",
    }

    repository = DocumentRecord(
        "release:start",
        "release",
        "docs/start.md",
        "0" * 64,
        0,
        0,
        "content",
        repo_path="docs/start.md",
        logical_key="docs/start.md",
    )
    assert extract_internal_doc_links(
        repository,
        "[Guide](guide/)\n[Readme](guide/README.md?x=1#top)\n",
    ) == {"docs/guide/README.md"}


def test_repository_absolute_links_accept_same_release_ref_and_commit(tmp_path: Path):
    links = (
        "\n[Guide](https://github.com/NousResearch/hermes-agent/blob/v2026.7.7.2/docs/guide.md)"
        "\n[Reference](https://raw.githubusercontent.com/NousResearch/hermes-agent/"
        + ("a" * 40)
        + "/docs/reference.md)"
    )
    start = _write_release_document(tmp_path, "docs/start.md", _article("Start", links))
    guide = _write_release_document(tmp_path, "docs/guide.md", _article("Guide"))
    reference = _write_release_document(
        tmp_path, "docs/reference.md", _article("Reference")
    )
    manifest = _release_snapshot([start, guide, reference])
    _persist_manifest(tmp_path, manifest)
    available = {document.logical_key for document in manifest.documents}

    assert extract_internal_doc_links(
        start,
        (tmp_path / start.output_path).read_text(),
        allowed_repository_refs={manifest.requested_ref, manifest.resolved_sha},
        available_logical_keys=available,
    ) == {"docs/guide.md", "docs/reference.md"}
    report = validate_snapshot(manifest, tmp_path, available)
    assert report.ok, report.errors


def test_repository_absolute_document_link_missing_from_cache_fails(tmp_path: Path):
    links = (
        "\n[Missing](https://github.com/NousResearch/hermes-agent/blob/"
        "v2026.7.7.2/docs/missing.md)"
    )
    start = _write_release_document(tmp_path, "docs/start.md", _article("Start", links))
    manifest = _release_snapshot([start])
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {start.logical_key})

    assert any("unresolved internal link" in error for error in report.errors)


def test_repository_absolute_document_link_rejects_cross_ref(tmp_path: Path):
    links = (
        "\n[Wrong ref](https://github.com/NousResearch/hermes-agent/blob/"
        "main/docs/guide.md)"
    )
    start = _write_release_document(tmp_path, "docs/start.md", _article("Start", links))
    guide = _write_release_document(tmp_path, "docs/guide.md", _article("Guide"))
    manifest = _release_snapshot([start, guide])
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(
        manifest, tmp_path, {start.logical_key, guide.logical_key}
    )

    assert any("invalid internal link" in error for error in report.errors)


def test_repository_absolute_asset_links_are_not_invalid_documents(tmp_path: Path):
    links = "".join(
        f"\n[Asset {index}](https://github.com/NousResearch/hermes-agent/blob/"
        f"v2026.7.7.2/assets/example{suffix})"
        for index, suffix in enumerate((".py", ".png", ".svg", ".json"))
    )
    start = _write_release_document(tmp_path, "docs/start.md", _article("Start", links))
    manifest = _release_snapshot([start])
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {start.logical_key})

    assert report.ok, report.errors


def test_repository_tree_links_resolve_to_cached_readme_or_index(tmp_path: Path):
    links = (
        "\n[Guide](https://github.com/NousResearch/hermes-agent/tree/v2026.7.7.2/docs/guide)"
        "\n[Tutorial](https://github.com/NousResearch/hermes-agent/tree/v2026.7.7.2/docs/tutorial)"
    )
    start = _write_release_document(tmp_path, "docs/start.md", _article("Start", links))
    readme = _write_release_document(
        tmp_path, "docs/guide/README.md", _article("README")
    )
    index = _write_release_document(
        tmp_path, "docs/tutorial/index.md", _article("Index")
    )
    manifest = _release_snapshot([start, readme, index])
    _persist_manifest(tmp_path, manifest)
    available = {document.logical_key for document in manifest.documents}

    assert extract_internal_doc_links(
        start,
        (tmp_path / start.output_path).read_text(),
        allowed_repository_refs={manifest.release_tag},
        available_logical_keys=available,
    ) == {"docs/guide/README.md", "docs/tutorial/index.md"}
    report = validate_snapshot(manifest, tmp_path, available)
    assert report.ok, report.errors


def test_validate_snapshot_rejects_illegal_official_links_but_ignores_external(
    tmp_path: Path,
):
    body = _article(
        "Hooks",
        "\n[HTTP official](http://hermes-agent.nousresearch.com/docs/tools)"
        "\n[Traversal](/docs/../private)"
        "\n[External](https://example.test/docs/outside)",
    )
    document = _write_website_document(tmp_path, "hooks", body)
    manifest = _website_snapshot([document])
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {document.logical_key})
    assert any("invalid internal link" in error for error in report.errors)


def test_website_link_closure_ignores_safe_same_host_non_document_resources(
    tmp_path: Path,
):
    body = _article(
        "Hooks",
        "\n[Home](https://hermes-agent.nousresearch.com/)"
        "\n[Installer](https://hermes-agent.nousresearch.com/install.sh)"
        "\n[Text asset](/docs/assets/files/llms.txt)"
        "\n[Image asset](/docs/img/logo.png)",
    )
    document = _write_website_document(tmp_path, "hooks", body)
    manifest = _website_snapshot([document])
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {document.logical_key})

    assert report.ok, report.errors


def test_validate_snapshot_accepts_audited_website_link_exclusions(
    tmp_path: Path,
):
    missing = "https://hermes-agent.nousresearch.com/docs/integrations/mcp"
    locale = "https://hermes-agent.nousresearch.com/docs/zh-Hans/search"
    body = _article("Hooks", f"\n[Missing]({missing})\n[Locale]({locale})")
    document = _write_website_document(tmp_path, "hooks", body)
    manifest = _website_snapshot(
        [document],
        exclusions=[
            {
                "logical_key": missing,
                "scope": "internal_link",
                "reason": "not_in_sitemap",
            },
            {
                "logical_key": locale,
                "scope": "internal_link",
                "reason": "not_in_sitemap",
            },
        ],
    )
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {document.logical_key})

    assert report.ok, report.errors


def test_validate_snapshot_rejects_stale_website_link_exclusion(tmp_path: Path):
    stale = "https://hermes-agent.nousresearch.com/docs/stale"
    document = _write_website_document(tmp_path, "hooks", _article("Hooks"))
    manifest = _website_snapshot(
        [document],
        exclusions=[
            {
                "logical_key": stale,
                "scope": "internal_link",
                "reason": "not_in_sitemap",
            }
        ],
    )
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, {document.logical_key})

    assert any("stale link exclusion" in error for error in report.errors)


def test_validate_snapshot_rejects_digest_only_explanation_and_detects_reason_tamper(
    tmp_path: Path,
):
    body = _article("Shared")
    first = _write_website_document(tmp_path, "first", body)
    second = _write_website_document(tmp_path, "second", body)
    group = frozenset({first.logical_key, second.logical_key})
    digest = sha256_bytes(stable_json_bytes(sorted(group)))
    manifest = _website_snapshot(
        [first, second],
        notes=[f"integrity_explanation_sha256:{digest}"],
    )
    _persist_manifest(tmp_path, manifest)

    digest_only = validate_snapshot(manifest, tmp_path, set(group), {group})
    assert any("invalid persisted explanation" in error for error in digest_only.errors)

    manifest.notes = [_explanation_note(group, reason="same upstream body")]
    _persist_manifest(tmp_path, manifest)
    path = tmp_path / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["notes"] = [payload["notes"][0].replace("same upstream body", "tampered")]
    path.write_bytes(stable_json_bytes(payload))
    tampered = validate_snapshot(manifest, tmp_path, set(group))
    assert any("manifest hash mismatch" in error for error in tampered.errors)


def test_validate_snapshot_reads_explanation_from_manifest_without_external_override(
    tmp_path: Path,
):
    body = _article("Shared")
    first = _write_website_document(tmp_path, "first", body)
    second = _write_website_document(tmp_path, "second", body)
    group = frozenset({first.logical_key, second.logical_key})
    manifest = _website_snapshot(
        [first, second],
        notes=[_explanation_note(group, reason="intentional mirrored page")],
    )
    _persist_manifest(tmp_path, manifest)

    report = validate_snapshot(manifest, tmp_path, set(group))
    assert report.ok, report.errors


def test_secure_read_rejects_name_swap_after_read_before_descriptor_close(
    tmp_path: Path, monkeypatch
):
    import scribe3.hermes_evidence.integrity as integrity

    document = _write_website_document(tmp_path, "hooks", _article("Hooks"))
    manifest = _website_snapshot([document])
    _persist_manifest(tmp_path, manifest)
    expected = tmp_path / document.output_path
    moved = expected.with_name("hooks-old.md")
    real_read = integrity._read_fd
    calls = 0

    def swapping_read(descriptor):
        nonlocal calls
        data = real_read(descriptor)
        calls += 1
        if calls == 2:
            expected.rename(moved)
            expected.write_bytes(data)
        return data

    monkeypatch.setattr(integrity, "_read_fd", swapping_read)
    baseline_fds = len(os.listdir("/dev/fd"))
    report = validate_snapshot(manifest, tmp_path, {document.logical_key})
    final_fds = len(os.listdir("/dev/fd"))

    assert any("unsafe file" in error for error in report.errors)
    assert final_fds <= baseline_fds + 1


@pytest.mark.parametrize(
    "url",
    [
        "https://user@hermes-agent.nousresearch.com/docs/hooks",
        "https://hermes-agent.nousresearch.com:443/docs/hooks",
        "https://hermes-agent.nousresearch.com:bad/docs/hooks",
        "https://hermes-agent.nousresearch.com/docs/hooks?api_key=private-value",
        "https://hermes-agent.nousresearch.com/not-docs/hooks",
        "https://github.com/NousResearch/hermes-agent/docs/hooks",
    ],
)
def test_semantic_classifier_rejects_noncanonical_website_urls(url: str):
    body = _article("Hooks").encode()
    record = _semantic_record(
        requested_url=url,
        final_url=url,
        logical_key=url,
        byte_length=len(body),
        text_length=len(body.decode()),
    )
    assert "invalid_website_url" in classify_semantic_document(record, body)


def test_validate_snapshot_enforces_website_identity_and_output_path(tmp_path: Path):
    root = tmp_path / "website"
    document = _write_website_document(root, "hooks", _article("Hooks"))

    requested_mismatch = replace(
        document,
        requested_url="https://hermes-agent.nousresearch.com/docs/tools",
    )
    manifest = _website_snapshot([requested_mismatch])
    _persist_manifest(root, manifest)
    report = validate_snapshot(manifest, root, {document.logical_key})
    assert any("website logical key mismatch" in error for error in report.errors)

    wrong_output = output_path_for_url(
        "https://hermes-agent.nousresearch.com/docs/tools"
    ).as_posix()
    (root / wrong_output).parent.mkdir(parents=True, exist_ok=True)
    (root / wrong_output).write_bytes((root / document.output_path).read_bytes())
    output_mismatch = replace(document, output_path=wrong_output)
    manifest = _website_snapshot([output_mismatch])
    _persist_manifest(root, manifest)
    report = validate_snapshot(manifest, root, {document.logical_key})
    assert any("website output path mismatch" in error for error in report.errors)


def test_validate_snapshot_enforces_all_website_source_boundaries(tmp_path: Path):
    root = tmp_path / "website"
    document = _write_website_document(root, "hooks", _article("Hooks"))
    invalid = replace(
        document,
        source_kind="release",
        website_snapshot_id="another-snapshot",
        source_commit="a" * 40,
        source_blob_sha="b" * 40,
        repo_path="docs/hooks.md",
    )
    manifest = _website_snapshot([invalid])
    _persist_manifest(root, manifest)

    report = validate_snapshot(manifest, root, {document.logical_key})

    assert any("source kind mismatch" in error for error in report.errors)
    assert any("website snapshot mismatch" in error for error in report.errors)
    assert any("website document contains repository identity" in error for error in report.errors)
    assert any("website document contains repository path" in error for error in report.errors)


@pytest.mark.parametrize(
    "url",
    [
        "https://[::1/docs/hooks",
        "https://user@hermes-agent.nousresearch.com/docs/hooks",
        "https://hermes-agent.nousresearch.com:443/docs/hooks",
        "https://hermes-agent.nousresearch.com/docs/hooks?view=all",
        "https://hermes-agent.nousresearch.com/docs/hooks?token=private-value",
    ],
)
def test_validate_snapshot_reports_invalid_website_urls_without_raising(
    tmp_path: Path, url: str
):
    root = tmp_path / "website"
    document = _write_website_document(root, "hooks", _article("Hooks"))
    invalid = replace(
        document,
        document_id=document_id_for("website", url, document.content_sha256),
        requested_url=url,
        final_url=url,
        logical_key=url,
    )
    manifest = _website_snapshot([invalid])
    payload = manifest.payload()
    payload["manifest_sha256"] = sha256_bytes(stable_json_bytes(payload))
    (root / "manifest.json").write_bytes(stable_json_bytes(payload))

    report = validate_snapshot(manifest, root, {url})

    assert any("invalid website URL" in error for error in report.errors)


def test_integrity_report_redacts_every_field_when_manifest_contains_secret(
    tmp_path: Path,
):
    private = "must-not-appear-anywhere"
    root = tmp_path / "snapshot"
    root.mkdir()
    secret_key = f"https://hermes-agent.nousresearch.com/docs/hooks?token={private}"
    document = DocumentRecord(
        f"token={private}",
        "website",
        f"pages/token={private}.md",
        "0" * 64,
        1,
        1,
        "content",
        requested_url=secret_key,
        final_url=secret_key,
        http_status=200,
        website_snapshot_id=f"token={private}",
        logical_key=secret_key,
    )
    manifest = _website_snapshot(
        [document],
        snapshot_id=f"token={private}",
        notes=[f"token={private}"],
    )
    manifest_path = tmp_path / "manifests/secret.json"
    payload = manifest.payload()
    digest = sha256_bytes(stable_json_bytes(payload))
    payload["manifest_sha256"] = digest
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(stable_json_bytes(payload))

    report = validate_snapshot(
        manifest,
        root,
        {secret_key},
        manifest_path=manifest_path,
    )
    assert private not in repr(report)
    assert report.snapshot_id == "[redacted]"
    assert any("invalid website URL" in error for error in report.errors)


def _valid_release_pdf_fixture(root: Path):
    pdf = b"%PDF-1.7\npublic-binary"
    pdf_path = root / "docs/guide.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(pdf)
    sidecar_text = _article("PDF Guide")
    sidecar_bytes = sidecar_text.encode()
    sidecar_path = root / "_extracted/docs/guide.pdf.txt"
    sidecar_path.parent.mkdir(parents=True)
    sidecar_path.write_bytes(sidecar_bytes)
    logical_key = "docs/guide.pdf"
    digest = sha256_bytes(pdf)
    document = DocumentRecord(
        document_id_for("release", logical_key, digest),
        "release",
        logical_key,
        digest,
        len(pdf),
        len(sidecar_text),
        "content",
        repo_path=logical_key,
        category="core-doc",
        source_commit="a" * 40,
        source_blob_sha=_git_blob_sha(pdf),
        logical_key=logical_key,
        mime_type="application/pdf",
        is_runtime_contract=True,
        extracted_text_path="_extracted/docs/guide.pdf.txt",
        extracted_text_sha256=sha256_bytes(sidecar_bytes),
    )
    manifest = SnapshotManifest(
        "release-pdf-valid",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v2026.7.7.2",
        "a" * 40,
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        documents=[document],
        expected_document_count=1,
        tree_truncated=False,
    )
    return document, manifest, logical_key


def test_validate_snapshot_requires_complete_sidecar_for_every_successful_pdf(
    tmp_path: Path,
):
    root = tmp_path / "snapshot"
    document, manifest, logical_key = _valid_release_pdf_fixture(root)
    valid_path = tmp_path / "manifests/valid.json"
    write_manifest(valid_path, manifest)
    valid = validate_snapshot(
        manifest, root, {logical_key}, manifest_path=valid_path
    )
    assert valid.ok, valid.errors

    cases = [
        replace(
            document,
            text_length=0,
            extracted_text_path=None,
            extracted_text_sha256=None,
        ),
        replace(document, extracted_text_path=None),
        replace(document, extracted_text_sha256=None),
    ]
    for index, invalid_document in enumerate(cases):
        invalid_manifest = replace(manifest, documents=[invalid_document])
        manifest_path = tmp_path / f"manifests/invalid-{index}.json"
        write_manifest(manifest_path, invalid_manifest)
        report = validate_snapshot(
            invalid_manifest,
            root,
            {logical_key},
            manifest_path=manifest_path,
        )
        assert any("PDF sidecar required" in error for error in report.errors)


@pytest.mark.parametrize("same_length", [True, False])
def test_secure_read_rejects_in_place_rewrite_after_read(
    tmp_path: Path, monkeypatch, same_length: bool
):
    import scribe3.hermes_evidence.integrity as integrity

    document = _write_website_document(tmp_path, "hooks", _article("Hooks"))
    manifest = _website_snapshot([document])
    _persist_manifest(tmp_path, manifest)
    expected = tmp_path / document.output_path
    real_read = integrity._read_fd
    calls = 0

    def rewriting_read(descriptor):
        nonlocal calls
        data = real_read(descriptor)
        calls += 1
        if calls == 2:
            replacement = b"z" * (len(data) if same_length else max(1, len(data) // 2))
            with expected.open("r+b") as stream:
                stream.seek(0)
                stream.write(replacement)
                stream.truncate()
                stream.flush()
                os.fsync(stream.fileno())
        return data

    monkeypatch.setattr(integrity, "_read_fd", rewriting_read)
    baseline_fds = len(os.listdir("/dev/fd"))
    report = validate_snapshot(manifest, tmp_path, {document.logical_key})
    final_fds = len(os.listdir("/dev/fd"))

    assert any("unsafe file" in error for error in report.errors)
    assert final_fds <= baseline_fds + 1


def test_validate_snapshot_checks_actual_h1_and_empty_manifest_version_identity(
    tmp_path: Path,
):
    website_root = tmp_path / "website"
    document = _write_website_document(website_root, "hooks", _article("Hooks"))
    document = replace(document, h1="Different Stored Heading")
    website = _website_snapshot([document])
    _persist_manifest(website_root, website)

    website_report = validate_snapshot(website, website_root, {document.logical_key})
    assert any("stored h1 mismatch" in error for error in website_report.errors)

    release_root = tmp_path / "release"
    release_root.mkdir()
    release = SnapshotManifest(
        "release-empty",
        "release",
        "https://github.com/NousResearch/hermes-agent",
        "v-wrong-ref",
        "not-a-commit",
        "v2026.7.7.2",
        "2026-07-20T00:00:00+00:00",
        "1",
        expected_document_count=0,
    )
    _persist_manifest(release_root, release)
    release_report = validate_snapshot(release, release_root, set())
    assert any("invalid resolved source commit" in error for error in release_report.errors)
    assert any("release ref mismatch" in error for error in release_report.errors)


def test_validate_snapshot_requires_exclusion_reason_and_never_echoes_secrets(
    tmp_path: Path,
):
    root = tmp_path / "excluded"
    root.mkdir()
    excluded_key = "https://hermes-agent.nousresearch.com/docs/excluded"
    manifest = _website_snapshot(
        [],
        exclusions=[{"logical_key": excluded_key}],
        expected_document_count=1,
    )
    _persist_manifest(root, manifest)
    report = validate_snapshot(manifest, root, {excluded_key})
    assert any("exclusion missing reason" in error for error in report.errors)

    secret_root = tmp_path / "secret"
    private = "must-not-be-echoed"
    body = _article("Hooks") + f"Authorization: Bearer {private}\n"
    document = _write_website_document(secret_root, "hooks", body)
    secret_key = document.logical_key + f"?api_key={private}"
    document = replace(
        document,
        logical_key=secret_key,
        text_length=document.text_length + 1,
    )
    secret_manifest = _website_snapshot([document])
    payload = secret_manifest.payload()
    digest = sha256_bytes(stable_json_bytes(payload))
    payload["manifest_sha256"] = digest
    (secret_root / "manifest.json").write_bytes(stable_json_bytes(payload))

    secret_report = validate_snapshot(secret_manifest, secret_root, {secret_key})
    assert not secret_report.ok
    assert private not in repr(secret_report)
