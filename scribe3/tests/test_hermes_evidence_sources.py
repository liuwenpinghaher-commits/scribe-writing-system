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
