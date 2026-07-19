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
