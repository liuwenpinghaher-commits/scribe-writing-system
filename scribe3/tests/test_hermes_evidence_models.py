from pathlib import Path
import inspect

import pytest

from scribe3.hermes_evidence import contains_sensitive_data
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


def test_filter_policy_version_has_one_models_authority():
    from scribe3.hermes_evidence import cli
    from scribe3.hermes_evidence.models import FILTER_POLICY_VERSION

    manifest = _manifest_with()
    assert manifest.filter_policy_version == FILTER_POLICY_VERSION
    assert cli.FILTER_POLICY_VERSION == FILTER_POLICY_VERSION
    assert "FILTER_POLICY_VERSION =" not in inspect.getsource(cli)


def _manifest_with(**changes: object) -> SnapshotManifest:
    values: dict[str, object] = {
        "snapshot_id": "website-20260719T000000Z",
        "source_kind": "website",
        "source_origin": "https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        "requested_ref": "sitemap",
        "resolved_sha": None,
        "release_tag": None,
        "fetched_at": "2026-07-19T00:00:00+00:00",
        "crawler_version": "1",
    }
    values.update(changes)
    return SnapshotManifest(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("case", "manifest"),
    [
        (
            "sensitive query key",
            _manifest_with(
                documents=[
                    DocumentRecord(
                        document_id="website:abc",
                        source_kind="website",
                        output_path="pages/a.md",
                        content_sha256=sha256_bytes(b"abc"),
                        byte_length=3,
                        text_length=3,
                        semantic_status="content",
                        requested_url="https://example.test/a?api_key=not-a-real-key",
                    )
                ]
            ),
        ),
        (
            "nested authorization",
            _manifest_with(
                failures=[{"request": {"Authorization": "Bearer not-a-real-token"}}]
            ),
        ),
        ("secret-shaped note", _manifest_with(notes=["sk-test_abcdef1234567890"])),
    ],
)
def test_write_manifest_rejects_suspicious_sensitive_data_before_writing(
    tmp_path: Path, case: str, manifest: SnapshotManifest
):
    path = tmp_path / f"{case}.json"

    with pytest.raises(ValueError, match="sensitive data") as error:
        write_manifest(path, manifest)

    assert not path.exists()
    assert "not-a-real" not in str(error.value)


@pytest.mark.parametrize(
    "example",
    [
        "Set HERMES_API_KEY=${API_KEY} before running.",
        "Set HERMES_API_KEY=$API_KEY before running.",
        "Set HERMES_API_KEY=YOUR_API_KEY before running.",
        "Set HERMES_API_KEY=[REDACTED] before running.",
        "Set HERMES_API_KEY=<redacted> before running.",
        "Set API_KEY in environment before running.",
    ],
)
def test_official_environment_variable_placeholder_is_allowed(
    tmp_path: Path, example: str
):
    manifest = _manifest_with(notes=[example])
    path = tmp_path / "manifest.json"

    assert not contains_sensitive_data(manifest.payload())
    write_manifest(path, manifest)
    assert path.exists()


@pytest.mark.parametrize(
    ("case", "manifest", "private_fragment"),
    [
        (
            "basic authorization in document error",
            _manifest_with(
                documents=[
                    DocumentRecord(
                        document_id="website:abc",
                        source_kind="website",
                        output_path="pages/a.md",
                        content_sha256=sha256_bytes(b"abc"),
                        byte_length=3,
                        text_length=3,
                        semantic_status="content",
                        error="Authorization: Basic aW52YWxpZC1leGFtcGxl",
                    )
                ]
            ),
            "aW52YWxpZC",
        ),
        (
            "cookie header in note",
            _manifest_with(notes=["Cookie: session=not-a-real-session"]),
            "not-a-real-session",
        ),
        (
            "credential assignments in note",
            _manifest_with(
                notes=[
                    "API_KEY=not-a-real-api-key SECRET=not-a-real-secret "
                    "TOKEN=not-a-real-token PASSWORD=not-a-real-password "
                    "CREDENTIAL=not-a-real-credential"
                ]
            ),
            "not-a-real-api-key",
        ),
        (
            "dotenv content in note",
            _manifest_with(notes=["# .env\nAPI_KEY=not-a-real-dotenv-value\nMODE=test"]),
            "not-a-real-dotenv-value",
        ),
    ],
)
def test_write_manifest_rejects_sensitive_free_strings_before_creating_parent(
    tmp_path: Path, case: str, manifest: SnapshotManifest, private_fragment: str
):
    path = tmp_path / case.replace(" ", "-") / "manifest.json"

    assert not path.parent.exists()
    with pytest.raises(ValueError, match="sensitive data") as error:
        write_manifest(path, manifest)

    assert not path.parent.exists()
    assert private_fragment not in str(error.value)


@pytest.mark.parametrize(
    ("case", "free_string", "private_fragment"),
    [
        ("authorization token", "Authorization: Token actual-secret", "actual-secret"),
        (
            "proxy authorization digest",
            "Proxy-Authorization: Digest actual-secret",
            "actual-secret",
        ),
        ("x api key", "X-API-Key: actual-secret", "actual-secret"),
        ("x auth token", "x_auth_token = actual-secret", "actual-secret"),
        ("client secret", "client-secret : actual-secret", "actual-secret"),
        ("password", "PASSWORD=actual-secret", "actual-secret"),
        ("credential", "credential : actual-secret", "actual-secret"),
        ("cookie", "Cookie: session=actual-secret", "actual-secret"),
        ("set cookie", "Set-Cookie: session=actual-secret", "actual-secret"),
        ("jsonish token", '{"token": "actual-secret"}', "actual-secret"),
    ],
)
def test_write_manifest_rejects_generic_sensitive_name_value_strings(
    tmp_path: Path, case: str, free_string: str, private_fragment: str
):
    path = tmp_path / case.replace(" ", "-") / "manifest.json"
    manifest = _manifest_with(notes=[free_string])

    assert not path.parent.exists()
    with pytest.raises(ValueError, match="sensitive data") as error:
        write_manifest(path, manifest)

    assert not path.parent.exists()
    assert private_fragment not in str(error.value)


@pytest.mark.parametrize(
    "free_string",
    [
        "API Key: actual-secret",
        "Access Token: actual-secret",
        "Client Secret = actual-secret",
    ],
)
def test_write_manifest_rejects_space_separated_sensitive_labels(
    tmp_path: Path, free_string: str
):
    path = tmp_path / "nested" / "manifest.json"

    with pytest.raises(ValueError, match="sensitive data"):
        write_manifest(path, _manifest_with(notes=[free_string]))

    assert not path.parent.exists()


@pytest.mark.parametrize(
    "free_string",
    [
        "Authorization: Bearer ${API_KEY}",
        "Proxy-Authorization: Custom $API_KEY",
        "Cookie: session=YOUR_API_KEY",
        "Set-Cookie: session=[REDACTED]",
    ],
)
def test_write_manifest_allows_placeholder_credentials_in_headers_and_cookies(
    tmp_path: Path, free_string: str
):
    path = tmp_path / "manifest.json"

    write_manifest(path, _manifest_with(notes=[free_string]))

    assert path.exists()


@pytest.mark.parametrize(
    "value",
    [
        {"token_count": 12, "usage_tokens": 7},
        {"credential_configured": True, "api_key_present": True},
        {"token": "${API_KEY}", "api key": None},
    ],
)
def test_contains_sensitive_data_allows_telemetry_and_nonsecret_sensitive_fields(
    value: object,
):
    assert not contains_sensitive_data(value)


@pytest.mark.parametrize(
    "value",
    [
        {"token": "actual-secret"},
        {"api key": "actual-secret"},
    ],
)
def test_contains_sensitive_data_rejects_actual_sensitive_mapping_values(value: object):
    assert contains_sensitive_data(value)


def test_contains_sensitive_data_continues_after_malformed_url():
    value = [
        "https://[::1/docs/hooks",
        {"token": "actual-secret"},
    ]

    assert contains_sensitive_data(value)


@pytest.mark.parametrize(
    "free_string",
    [
        "HTTP 401 response: Authorization: Bearer actual-secret",
        "response headers; Cookie: session=actual-secret",
        "status=ok; API Key: actual-secret",
        'context: {"Access_Token": "actual-secret"}',
        "prefix: CLIENT-secret = actual-secret",
    ],
)
def test_write_manifest_rejects_embedded_sensitive_label_values(
    tmp_path: Path, free_string: str
):
    path = tmp_path / "nested" / "manifest.json"

    with pytest.raises(ValueError, match="sensitive data"):
        write_manifest(path, _manifest_with(notes=[free_string]))

    assert not path.parent.exists()


@pytest.mark.parametrize(
    "free_string",
    [
        "HTTP 401: Authorization required",
        "Example: Authorization: Bearer ${API_KEY}",
        "headers; Cookie: session=${SESSION_TOKEN}",
    ],
)
def test_write_manifest_allows_embedded_documentation_and_placeholders(
    tmp_path: Path, free_string: str
):
    path = tmp_path / "manifest.json"

    write_manifest(path, _manifest_with(notes=[free_string]))

    assert path.exists()
