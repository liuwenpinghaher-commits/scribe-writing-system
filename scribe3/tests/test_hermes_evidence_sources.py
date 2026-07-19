from pathlib import Path

import pytest

from scribe3.hermes_evidence.policy import (
    classify_repo_path,
    contains_secret,
    is_official_url,
    select_repo_document,
)
from scribe3.hermes_evidence.website import discover_sitemap, output_path_for_url


def test_sitemap_is_unique_sorted_and_official():
    xml = Path("scribe3/tests/fixtures/hermes_evidence/sitemap.xml").read_bytes()

    assert discover_sitemap(xml) == [
        "https://hermes-agent.nousresearch.com/docs/",
        "https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks",
    ]


def test_sitemap_discovery_preserves_raw_hash_and_classifies_paths():
    from scribe3.hermes_evidence.website import discover_sitemap_snapshot

    xml = Path("scribe3/tests/fixtures/hermes_evidence/sitemap.xml").read_bytes()
    result = discover_sitemap_snapshot(xml)

    assert len(result.raw_sha256) == 64
    assert result.urls == tuple(sorted(set(result.urls)))
    assert result.page_kinds[result.urls[0]] in {"content", "directory", "search"}


def test_sitemap_rejects_malformed_xml_and_non_docs_urls():
    with pytest.raises(ValueError, match="invalid XML"):
        discover_sitemap(b"<urlset>")
    with pytest.raises(ValueError, match="non-official"):
        discover_sitemap(
            b"<urlset><url><loc>https://hermes-agent.nousresearch.com/docs-evil</loc>"
            b"</url></urlset>"
        )


def test_official_host_and_output_path_are_fail_closed():
    assert is_official_url("https://hermes-agent.nousresearch.com/docs/a")
    assert is_official_url("https://github.com/NousResearch/hermes-agent")
    assert not is_official_url("https://example.com/copied-doc")
    assert output_path_for_url("https://hermes-agent.nousresearch.com/docs/a/b") == Path(
        "pages/a/b.md"
    )
    with pytest.raises(ValueError):
        output_path_for_url("https://example.com/docs/a")


@pytest.mark.parametrize(
    "url",
    [
        "https://hermes-agent.nousresearch.com/docs-evil/a",
        "https://github.com/NousResearch/hermes-agent-evil",
        "https://github.com/OtherOrg/hermes-agent",
        "https://api.github.com/repos/NousResearch/hermes-agent-evil/contents/a.md",
        "https://raw.githubusercontent.com/NousResearch/hermes-agent-evil/main/a.md",
    ],
)
def test_official_url_path_boundaries_are_strict(url: str):
    assert not is_official_url(url)


def test_official_url_rejects_malformed_port_without_raising():
    assert not is_official_url("https://hermes-agent.nousresearch.com:invalid/docs/a")


@pytest.mark.parametrize(
    "path",
    [
        "/docs/./outside",
        "/docs/../outside",
        "/docs/%2e%2e/outside",
        "/docs/%252e%252e/outside",
        "/docs/a%2fb",
        "/docs/a%5cb",
        "/docs/a%0a",
    ],
)
def test_policy_and_output_mapper_reject_encoded_or_raw_path_escapes(path: str):
    url = f"https://hermes-agent.nousresearch.com{path}"

    assert not is_official_url(url)
    with pytest.raises(ValueError):
        output_path_for_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@hermes-agent.nousresearch.com/docs/a",
        "https://hermes-agent.nousresearch.com/docs/a#fragment",
        "https://hermes-agent.nousresearch.com/docs/a?token=actual-secret",
        "https://hermes-agent.nousresearch.com/docs/a?api_key=actual-secret",
    ],
)
def test_policy_rejects_noncanonical_or_sensitive_official_urls(url: str):
    assert not is_official_url(url)


def test_policy_rejects_raw_control_characters_before_url_parsing():
    assert not is_official_url("https://hermes-agent.nousresearch.com/docs/a\n")


def test_api_allows_non_sensitive_query_but_output_mapper_rejects_repository_url():
    url = "https://api.github.com/repos/NousResearch/hermes-agent/git/trees/main?recursive=1"

    assert is_official_url(url)
    with pytest.raises(ValueError):
        output_path_for_url(url)


def test_sitemap_requires_exact_sitemap_structure_and_namespace():
    official_url = b"https://hermes-agent.nousresearch.com/docs/a"
    cases = [
        b"<not-urlset><fake-loc>" + official_url + b"</fake-loc></not-urlset>",
        b'<urlset xmlns="https://example.test/sitemap"><url><loc>'
        + official_url
        + b"</loc></url></urlset>",
        b"<urlset><url></url></urlset>",
        b"<urlset><url><loc>" + official_url + b"</loc><loc>" + official_url + b"</loc></url></urlset>",
        b"<urlset><wrapper><url><loc>" + official_url + b"</loc></url></wrapper></urlset>",
    ]

    for xml in cases:
        with pytest.raises(ValueError):
            discover_sitemap(xml)


def test_sitemap_ignores_standard_fields_and_non_url_extensions():
    xml = b"""<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"
        xmlns:image=\"https://www.google.com/schemas/sitemap-image/1.1\">
      <url><loc>https://hermes-agent.nousresearch.com/docs/a</loc><lastmod>2026-07-19</lastmod>
        <changefreq>daily</changefreq><priority>0.5</priority><image:image /></url>
    </urlset>"""

    assert discover_sitemap(xml) == ["https://hermes-agent.nousresearch.com/docs/a"]


@pytest.mark.parametrize(
    "xml",
    [
        b"<urlset><url><loc>https://hermes-agent.nousresearch.com/docs/a</loc></url><unexpected /></urlset>",
        b"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        b"<url><loc>https://hermes-agent.nousresearch.com/docs/a</loc></url><unexpected />"
        b"</urlset>",
        b"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\" xmlns:bad=\"https://example.test/bad\">"
        b"<url><loc>https://hermes-agent.nousresearch.com/docs/a</loc></url><bad:unexpected />"
        b"</urlset>",
    ],
)
def test_sitemap_rejects_non_url_root_children_in_any_namespace(xml: bytes):
    with pytest.raises(ValueError):
        discover_sitemap(xml)


@pytest.mark.parametrize(
    "xml",
    [
        b"<urlset><url><loc>https://hermes-agent.nousresearch.com/docs/a</loc><unexpected /></url></urlset>",
        b"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        b"<url><loc>https://hermes-agent.nousresearch.com/docs/a</loc><unexpected /></url>"
        b"</urlset>",
    ],
)
def test_sitemap_rejects_unknown_same_namespace_url_children(xml: bytes):
    with pytest.raises(ValueError):
        discover_sitemap(xml)


def test_repo_policy_keeps_docs_and_classifies_skills():
    assert select_repo_document("website/docs/user-guide/features/hooks.md")
    assert select_repo_document("optional-skills/creative/creative-ideation/SKILL.md")
    assert not select_repo_document("agent/run_loop.py")
    assert classify_repo_path("optional-skills/creative/x/SKILL.md") == (
        "en",
        "optional-skill",
        True,
        False,
    )


def test_secret_scanner_rejects_secret_shapes_without_echoing_values():
    assert contains_secret("API_KEY=" + "x" * 32)
    assert contains_secret("Authorization: Bearer " + "x" * 32)
    assert not contains_secret("Use ${API_KEY} from the environment")


def test_repository_snapshot_resolves_fixed_ref_and_preserves_selected_paths(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    class FakeClient:
        def resolve_ref(self, ref):
            assert ref == "main"
            return "a" * 40

        def tree_payload(self, sha):
            assert sha == "a" * 40
            return {
                "truncated": False,
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "b1", "size": 4},
                    {"path": "agent.py", "type": "blob", "sha": "b2", "size": 4},
                    {
                        "path": "skills/x/SKILL.md",
                        "type": "blob",
                        "sha": "b3",
                        "size": 4,
                    },
                ],
            }

        def blob(self, sha):
            return {"b1": b"# H\n", "b3": b"# S\n"}[sha]

    manifest = snapshot_repository(
        FakeClient(),
        "main",
        "main-aaaaaaaa",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert manifest.resolved_sha == "a" * 40
    assert manifest.expected_document_count == 2
    assert [document.repo_path for document in manifest.documents] == [
        "README.md",
        "skills/x/SKILL.md",
    ]
    assert [document.source_blob_sha for document in manifest.documents] == ["b1", "b3"]
    assert (tmp_path / "README.md").read_text() == "# H\n"
    assert (tmp_path / "skills/x/SKILL.md").read_text() == "# S\n"


def test_repository_snapshot_rejects_recursive_tree_without_explicit_complete_flag(
    tmp_path,
):
    from scribe3.hermes_evidence.github import snapshot_repository

    class FakeClient:
        def resolve_ref(self, ref):
            return "a" * 40

        def tree_payload(self, sha):
            return {"tree": []}

    with pytest.raises(RuntimeError, match="truncated"):
        snapshot_repository(
            FakeClient(),
            "main",
            "main-aaaaaaaa",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )


def test_repository_snapshot_classifies_selected_special_entries_before_download(
    tmp_path,
):
    from scribe3.hermes_evidence.github import MAX_DOCUMENT_BYTES, snapshot_repository

    class FakeClient:
        def __init__(self):
            self.requested_blobs = []

        def resolve_ref(self, ref):
            return "a" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {
                        "path": "docs/selected-submodule.md",
                        "type": "commit",
                        "sha": "sub-selected",
                    },
                    {"path": "vendor/runtime", "type": "commit", "sha": "sub-note"},
                    {
                        "path": "docs/link.md",
                        "type": "blob",
                        "mode": "120000",
                        "sha": "link",
                        "size": 9,
                    },
                    {
                        "path": "docs/large.pdf",
                        "type": "blob",
                        "sha": "large",
                        "size": MAX_DOCUMENT_BYTES + 1,
                    },
                    {
                        "path": "docs/lfs.pdf",
                        "type": "blob",
                        "sha": "lfs",
                        "size": 130,
                    },
                    {
                        "path": "docs/failed.md",
                        "type": "blob",
                        "sha": "failed",
                        "size": 5,
                    },
                    {
                        "path": "docs/saved.md",
                        "type": "blob",
                        "sha": "saved",
                        "size": 7,
                    },
                ],
            }

        def blob(self, sha):
            self.requested_blobs.append(sha)
            if sha == "lfs":
                return (
                    b"version https://git-lfs.github.com/spec/v1\n"
                    b"oid sha256:" + b"c" * 64 + b"\nsize 200\n"
                )
            if sha == "failed":
                raise OSError("response body must not be copied into the manifest")
            return b"# saved\n"

    client = FakeClient()
    manifest = snapshot_repository(
        client,
        "main",
        "main-aaaaaaaa",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert manifest.expected_document_count == 6
    assert [document.repo_path for document in manifest.documents] == ["docs/saved.md"]
    assert {row["repo_path"]: row["reason"] for row in manifest.exclusions} == {
        "docs/large.pdf": "oversized_attachment",
        "docs/lfs.pdf": "git_lfs_pointer",
        "docs/link.md": "git_symlink",
        "docs/selected-submodule.md": "git_submodule",
    }
    assert manifest.failures == [{"repo_path": "docs/failed.md", "error": "OSError"}]
    assert "repository_submodule:vendor/runtime" in manifest.notes
    assert client.requested_blobs == ["failed", "lfs", "saved"]
    assert not (tmp_path / "docs/lfs.pdf").exists()


def test_repository_snapshot_is_deterministic_for_the_same_fixed_ref(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    class FakeClient:
        def resolve_ref(self, ref):
            return "d" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/b.md", "type": "blob", "sha": "blob-b", "size": 3},
                    {"path": "docs/a.md", "type": "blob", "sha": "blob-a", "size": 3},
                ],
            }

        def blob(self, sha):
            return {"blob-a": b"A\n", "blob-b": b"B\n"}[sha]

    manifests = [
        snapshot_repository(
            FakeClient(),
            "d" * 40,
            f"fixed-{index}",
            tmp_path / str(index),
            "2026-07-19T00:00:00+00:00",
        )
        for index in range(2)
    ]

    def identity(manifest):
        return [
            (document.logical_key, document.source_blob_sha, document.content_sha256)
            for document in manifest.documents
        ]

    assert identity(manifests[0]) == identity(manifests[1])


def test_repository_snapshot_preserves_pdf_and_writes_extracted_sidecar(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    pdf = b"%PDF-1.7\nexact-original-bytes"

    class FakeClient:
        def resolve_ref(self, ref):
            return "e" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/guide.pdf", "type": "blob", "sha": "pdf", "size": len(pdf)}
                ],
            }

        def blob(self, sha):
            return pdf

    def fake_extractor(source, target):
        assert source.read_bytes() == pdf
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Extracted text\n", encoding="utf-8")

    manifest = snapshot_repository(
        FakeClient(),
        "v1.0.0",
        "release-v1",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
        pdf_extractor=fake_extractor,
    )

    document = manifest.documents[0]
    assert (tmp_path / "docs/guide.pdf").read_bytes() == pdf
    assert (tmp_path / document.extracted_text_path).read_text() == "Extracted text\n"
    assert document.extracted_text_path == "_extracted/docs/guide.pdf.txt"
    assert len(document.extracted_text_sha256) == 64
    assert document.text_length == len("Extracted text\n")
    assert document.semantic_status == "content"


def test_repository_snapshot_keeps_pdf_binary_when_extraction_fails(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    pdf = b"%PDF-1.4\nexact-original-bytes"

    class FakeClient:
        def resolve_ref(self, ref):
            return "f" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/guide.pdf", "type": "blob", "sha": "pdf", "size": len(pdf)}
                ],
            }

        def blob(self, sha):
            return pdf

    def failed_extractor(source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("partial and untrusted", encoding="utf-8")
        raise RuntimeError("sensitive process output must not be persisted")

    manifest = snapshot_repository(
        FakeClient(),
        "main",
        "main-pdf",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
        pdf_extractor=failed_extractor,
    )

    assert (tmp_path / "docs/guide.pdf").read_bytes() == pdf
    assert not (tmp_path / "_extracted/docs/guide.pdf.txt").exists()
    assert manifest.documents[0].semantic_status == "binary_attachment"
    assert manifest.exclusions == [
        {"repo_path": "docs/guide.pdf", "reason": "binary_attachment"}
    ]
    assert manifest.failures == [
        {"repo_path": "docs/guide.pdf", "error": "pdf_extraction_failed"}
    ]


def test_github_client_uses_only_fixed_official_git_endpoints(monkeypatch):
    import base64

    from scribe3.hermes_evidence.github import API, GitHubClient

    commit_sha = "a" * 40
    tag_sha = "b" * 40
    blob_sha = "c" * 40
    requested = []
    responses = {
        f"{API}/git/ref/tags/v1.0.0": {
            "object": {"type": "tag", "sha": tag_sha}
        },
        f"{API}/git/tags/{tag_sha}": {
            "object": {"type": "commit", "sha": commit_sha}
        },
        f"{API}/commits/main": {"sha": commit_sha},
        f"{API}/git/trees/{commit_sha}?recursive=1": {
            "truncated": False,
            "tree": [{"path": "README.md", "type": "blob", "sha": blob_sha}],
        },
        f"{API}/git/blobs/{blob_sha}": {
            "encoding": "base64",
            "content": base64.b64encode(b"# README\n").decode("ascii"),
        },
    }

    def fake_json(url):
        requested.append(url)
        return responses[url]

    client = GitHubClient()
    monkeypatch.setattr(client, "_json", fake_json)

    assert client.resolve_ref("v1.0.0") == commit_sha
    assert client.resolve_ref("main") == commit_sha
    assert client.resolve_ref(commit_sha) == commit_sha
    assert client.tree(commit_sha) == responses[
        f"{API}/git/trees/{commit_sha}?recursive=1"
    ]["tree"]
    assert client.blob(blob_sha) == b"# README\n"
    assert all(url.startswith(f"{API}/") for url in requested)
    with pytest.raises(ValueError):
        client.resolve_ref("../../other-repository")


def test_github_client_preserves_only_safe_rate_limit_and_retry_metadata(tmp_path):
    import io
    import urllib.error

    from scribe3.hermes_evidence.github import API, GitHubClient, snapshot_repository
    from scribe3.hermes_evidence.models import contains_sensitive_data

    commit_sha = "a" * 40
    response_body = io.BytesIO((f'{{"sha":"{commit_sha}"}}').encode("ascii"))
    response_body.headers = {
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Remaining": "41",
        "Authorization": "Bearer must-not-be-persisted",
    }
    responses = [
        urllib.error.HTTPError(
            f"{API}/commits/main",
            429,
            "must-not-be-persisted",
            {
                "Retry-After": "2",
                "X-RateLimit-Remaining": "0",
                "Set-Cookie": "must-not-be-persisted",
            },
            io.BytesIO(b"must-not-be-persisted"),
        ),
        response_body,
    ]
    slept = []

    def opener(request, timeout):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    client = GitHubClient(opener=opener, sleep=slept.append, max_retries=1)
    assert client.resolve_ref("main") == commit_sha

    class SnapshotClient:
        retry_events = client.retry_events

        def resolve_ref(self, ref):
            return commit_sha

        def tree_payload(self, sha):
            return {"truncated": False, "tree": []}

    manifest = snapshot_repository(
        SnapshotClient(),
        commit_sha,
        "fixed-rate-metadata",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert slept == [2]
    assert any(event.get("x-ratelimit-remaining") == 41 for event in manifest.retry_events)
    assert not contains_sensitive_data(manifest.retry_events)
