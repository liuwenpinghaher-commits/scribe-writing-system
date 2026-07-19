from __future__ import annotations

import json
import hashlib
import html
import os
import re
import stat
from collections import Counter
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from .models import (
    DocumentRecord,
    IntegrityReport,
    SnapshotManifest,
    contains_sensitive_data,
    document_id_for,
    sha256_bytes,
    stable_json_bytes,
)
from .policy import OFFICIAL_WEBSITE_HOST, contains_secret, select_repo_document
from .website import (
    _FILE_READ_FLAGS,
    _UnsafeOutputPath,
    _directory_identity_is_current,
    _h1,
    _open_parent_fd,
    _open_root_fd,
    _read_fd,
    _relative_parts,
    _semantic_soft_error,
    normalize_markdown,
)

_MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
_REFERENCE_DEFINITION_PATTERN = re.compile(
    r"(?m)^\s*\[([^\]]+)\]:\s*<?([^>\s]+)>?(?:\s+.*)?$"
)
_REFERENCE_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\[([^\]]+)\]")
_HTML_LINK_PATTERN = re.compile(
    r"(?i)<a\s+[^>]*href\s*=\s*([\"'])(.*?)\1[^>]*>"
)
_AUTOLINK_PATTERN = re.compile(r"<(https://[^>\s]+)>")
_HEADING_PATTERN = re.compile(r"^#{1,6}\s+")
_LINK_LINE_PATTERN = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(?:\[[^\]]*\]\([^)]+\)\s*)+$"
)
_TEXT_MIME_BY_SUFFIX = {
    ".adoc": frozenset({"text/asciidoc", "text/plain"}),
    ".md": frozenset({"text/markdown", "text/plain"}),
    ".mdx": frozenset({"text/markdown", "text/plain"}),
    ".rst": frozenset({"text/x-rst", "text/plain"}),
}


def _mime_matches(record: DocumentRecord) -> bool:
    suffix = PurePosixPath(record.output_path).suffix.lower()
    mime = record.mime_type.split(";", maxsplit=1)[0].strip().lower()
    if record.source_kind == "website" and suffix in {".md", ".mdx"}:
        return mime in {"text/html", "application/xhtml+xml", "text/markdown"}
    if suffix == ".pdf":
        return mime == "application/pdf"
    if suffix == ".json":
        return mime == "application/json"
    if suffix in _TEXT_MIME_BY_SUFFIX:
        return mime in _TEXT_MIME_BY_SUFFIX[suffix]
    return False


def _content_shape_errors(record: DocumentRecord, body: str) -> set[str]:
    errors: set[str] = set()
    stripped = body.strip()
    if not stripped:
        errors.add("empty_content")
    if len(stripped) < 200 and record.semantic_status not in {
        "navigation_only",
        "binary_attachment",
    }:
        errors.add("unexpected_short_content")

    content_lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not _HEADING_PATTERN.match(line.strip())
    ]
    link_lines = [line for line in content_lines if _LINK_LINE_PATTERN.fullmatch(line)]
    if (
        record.semantic_status != "navigation_only"
        and content_lines
        and len(link_lines) == len(content_lines)
    ):
        errors.add("link_only_content")
    elif (
        record.semantic_status != "navigation_only"
        and len(content_lines) >= 4
        and len(link_lines) / len(content_lines) >= 0.7
    ):
        errors.add("navigation_heavy_content")
    return errors


def _identity_terms(value: str | None) -> set[str]:
    ignored = {"agent", "docs", "documentation", "guide", "hermes", "the"}
    return {
        token
        for token in re.findall(r"[^\W_]+", (value or "").casefold())
        if len(token) > 1 and token not in ignored
    }


def _path_terms(record: DocumentRecord) -> set[str]:
    if record.source_kind == "website":
        path = urlsplit(record.requested_url or record.logical_key).path
        value = PurePosixPath(path).name
    else:
        value = PurePosixPath(record.repo_path or record.output_path).stem
    ignored = {
        "docs",
        "documentation",
        "first",
        "guide",
        "index",
        "item",
        "overview",
        "page",
        "readme",
        "second",
        "search",
    }
    return _identity_terms(value.replace("-", " ")) - ignored


def _wrong_page_identity(record: DocumentRecord, body: str) -> bool:
    title_terms = _identity_terms(record.title)
    h1_terms = _identity_terms(record.h1)
    path_terms = _path_terms(record)
    if not title_terms or not h1_terms or not path_terms:
        return False
    title_matches = bool(title_terms & path_terms)
    h1_matches = bool(h1_terms & path_terms)
    lead_terms = _identity_terms(body[:1200])
    return bool(
        not title_matches
        and not h1_matches
        and path_terms.isdisjoint(lead_terms)
    )


def classify_semantic_document(
    record: DocumentRecord, body: bytes
) -> tuple[str, ...]:
    """Return fail-closed semantic violations for one persisted document."""
    errors: set[str] = set()
    if not _mime_matches(record):
        errors.add("mime_extension_mismatch")
    if record.source_kind == "website":
        requested = urlsplit(record.requested_url or "")
        final = urlsplit(record.final_url or "")
        if (
            final.scheme != "https"
            or final.hostname != OFFICIAL_WEBSITE_HOST
            or final.port is not None
            or (requested.scheme, requested.hostname, requested.port)
            != (final.scheme, final.hostname, final.port)
        ):
            errors.add("cross_origin_redirect")

    if PurePosixPath(record.output_path).suffix.lower() == ".pdf":
        if not body.startswith(b"%PDF-"):
            errors.add("invalid_pdf_signature")
        return tuple(sorted(errors))

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        errors.add("invalid_utf8")
        return tuple(sorted(errors))

    if contains_secret(text):
        errors.add("suspected_secret")
    semantic_error = _semantic_soft_error(record.title, text)
    if semantic_error is not None:
        errors.add(semantic_error)
    if _wrong_page_identity(record, text):
        errors.add("wrong_page_identity")
    errors.update(_content_shape_errors(record, text))
    return tuple(sorted(errors))


def _normalized_internal_link(
    record: DocumentRecord, raw_target: str
) -> str | None:
    target = html.unescape(raw_target).strip().strip("<>")
    if not target or target.startswith("#"):
        return None
    parsed_target = urlsplit(target)
    if parsed_target.scheme not in {"", "https"}:
        return None

    if record.source_kind == "website":
        base = record.final_url or record.requested_url or record.logical_key
        resolved = urlsplit(urljoin(base, target))
        if (
            resolved.scheme != "https"
            or resolved.hostname != OFFICIAL_WEBSITE_HOST
            or resolved.port is not None
            or not (
                resolved.path == "/docs" or resolved.path.startswith("/docs/")
            )
        ):
            return None
        return urlunsplit(
            (
                "https",
                OFFICIAL_WEBSITE_HOST,
                resolved.path.rstrip("/") or "/docs",
                "",
                "",
            )
        )

    if record.source_kind not in {"release", "main"} or parsed_target.netloc:
        return None
    decoded_path = unquote(parsed_target.path)
    if not decoded_path:
        return None
    if decoded_path.startswith("/"):
        candidate = PurePosixPath(decoded_path.lstrip("/"))
    else:
        base_path = PurePosixPath(record.repo_path or record.logical_key)
        candidate = base_path.parent / decoded_path
    normalized_parts: list[str] = []
    escaped = False
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not normalized_parts:
                escaped = True
                break
            normalized_parts.pop()
        else:
            normalized_parts.append(part)
    normalized = "/".join(normalized_parts)
    if not escaped and select_repo_document(normalized):
        return normalized
    return None


def extract_internal_doc_links(record: DocumentRecord, body: str) -> set[str]:
    """Extract same-tier official documentation links as normalized logical keys."""
    definitions = {
        match.group(1).strip().casefold(): match.group(2)
        for match in _REFERENCE_DEFINITION_PATTERN.finditer(body)
    }
    targets = [match.group(1) for match in _MARKDOWN_LINK_PATTERN.finditer(body)]
    for match in _REFERENCE_LINK_PATTERN.finditer(body):
        target = definitions.get(match.group(1).strip().casefold())
        if target:
            targets.append(target)
    targets.extend(match.group(2) for match in _HTML_LINK_PATTERN.finditer(body))
    targets.extend(match.group(1) for match in _AUTOLINK_PATTERN.finditer(body))
    links = {
        normalized
        for target in targets
        if (normalized := _normalized_internal_link(record, target)) is not None
    }
    return links


def _secure_regular_read(
    root: Path, relative_path: Path, *, missing_ok: bool = False
) -> bytes | None:
    """Read a regular file without following links or blocking on special files."""
    parts = _relative_parts(relative_path)
    root_fd = _open_root_fd(root, create=False)
    try:
        try:
            parent_fd = _open_parent_fd(root_fd, parts[:-1], create=False)
        except _UnsafeOutputPath:
            if missing_ok:
                return None
            raise
        try:
            try:
                descriptor = os.open(
                    parts[-1],
                    _FILE_READ_FLAGS | getattr(os, "O_NONBLOCK", 0),
                    dir_fd=parent_fd,
                )
            except FileNotFoundError:
                if missing_ok:
                    return None
                raise
            except OSError as error:
                raise _UnsafeOutputPath("evidence file cannot be opened safely") from error
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise _UnsafeOutputPath("evidence target is not a regular file")
                data = _read_fd(descriptor)
            finally:
                os.close(descriptor)
            if not _directory_identity_is_current(root, root_fd, parts[:-1], parent_fd):
                raise _UnsafeOutputPath("evidence directory identity changed")
            return data
        finally:
            os.close(parent_fd)
    finally:
        os.close(root_fd)


def _row_identity(row: object) -> str | None:
    if not isinstance(row, dict):
        return None
    for field in ("logical_key", "requested_url", "repo_path"):
        value = row.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def _serialized_manifest_errors(manifest: SnapshotManifest, root: Path) -> list[str]:
    errors: list[str] = []
    try:
        raw = _secure_regular_read(Path(root), Path("manifest.json"), missing_ok=True)
    except (OSError, _UnsafeOutputPath):
        return ["unsafe serialized manifest"]
    if raw is None:
        return ["missing serialized manifest"]
    try:
        stored = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return ["invalid serialized manifest"]
    if not isinstance(stored, dict):
        return ["invalid serialized manifest"]
    if contains_sensitive_data(stored):
        errors.append("serialized manifest contains suspected secret")

    declared = stored.pop("manifest_sha256", None)
    if not isinstance(declared, str) or re.fullmatch(r"[0-9a-f]{64}", declared) is None:
        errors.append("invalid manifest hash")
    else:
        calculated = sha256_bytes(stable_json_bytes(stored))
        if calculated != declared:
            errors.append("manifest hash mismatch")
        canonical = dict(stored)
        canonical["manifest_sha256"] = declared
        if raw != stable_json_bytes(canonical):
            errors.append("serialized manifest is not canonical")
    if stored != manifest.payload():
        errors.append("serialized manifest payload mismatch")
    return errors


def _source_layer_errors(
    manifest: SnapshotManifest, document: DocumentRecord
) -> list[str]:
    errors: list[str] = []
    logical_key = document.logical_key or document.document_id
    if document.source_kind != manifest.source_kind:
        errors.append("source kind mismatch")
    expected_id = document_id_for(
        document.source_kind, logical_key, document.content_sha256
    )
    if document.document_id != expected_id:
        errors.append("document identity mismatch")

    if manifest.source_kind == "website":
        if document.website_snapshot_id != manifest.snapshot_id:
            errors.append("website snapshot mismatch")
        if document.source_commit is not None or document.source_blob_sha is not None:
            errors.append("website document contains repository identity")
        if document.http_status != 200:
            errors.append("website status mismatch")
    elif manifest.source_kind in {"release", "main"}:
        if document.source_commit != manifest.resolved_sha:
            errors.append("source commit mismatch")
        if document.website_snapshot_id is not None:
            errors.append("repository document contains website identity")
        if (
            not isinstance(document.source_blob_sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", document.source_blob_sha) is None
        ):
            errors.append("invalid source blob identity")
    elif manifest.source_kind == "runtime":
        if (
            document.source_commit is not None
            or document.source_blob_sha is not None
            or document.website_snapshot_id is not None
        ):
            errors.append("runtime document contains snapshot identity")
        if not document.is_runtime_contract:
            errors.append("runtime evidence not marked runtime contract")
    return errors


def _manifest_layer_errors(manifest: SnapshotManifest) -> list[str]:
    errors: list[str] = []
    github_origin = "https://github.com/NousResearch/hermes-agent"
    website_origin = "https://hermes-agent.nousresearch.com/docs/sitemap.xml"
    if manifest.source_kind == "website":
        if manifest.source_origin != website_origin or manifest.requested_ref != "sitemap":
            errors.append("invalid website source identity")
        if manifest.resolved_sha is not None or manifest.release_tag is not None:
            errors.append("website manifest contains repository version identity")
    elif manifest.source_kind in {"release", "main"}:
        if manifest.source_origin != github_origin:
            errors.append("invalid repository source identity")
        if (
            not isinstance(manifest.resolved_sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", manifest.resolved_sha) is None
        ):
            errors.append("invalid resolved source commit")
        if manifest.source_kind == "release":
            if (
                not isinstance(manifest.release_tag, str)
                or re.fullmatch(r"v[A-Za-z0-9][A-Za-z0-9._-]*", manifest.release_tag)
                is None
            ):
                errors.append("release manifest missing version tag")
            requested_is_commit = (
                re.fullmatch(r"[0-9a-f]{40}", manifest.requested_ref) is not None
            )
            if (
                manifest.requested_ref != manifest.release_tag
                and not (
                    requested_is_commit
                    and manifest.requested_ref == manifest.resolved_sha
                )
            ):
                errors.append("release ref mismatch")
        else:
            if manifest.release_tag is not None:
                errors.append("main manifest contains release tag")
            if manifest.requested_ref not in {"main", manifest.resolved_sha}:
                errors.append("main ref mismatch")
    elif manifest.source_kind == "runtime":
        if manifest.resolved_sha is not None or manifest.release_tag is not None:
            errors.append("runtime manifest contains repository version identity")
    return errors


def _closure_key(source_kind: str, logical_key: str) -> str:
    if source_kind != "website":
        return logical_key
    parsed = urlsplit(logical_key)
    if parsed.scheme == "https" and parsed.hostname == OFFICIAL_WEBSITE_HOST:
        path = parsed.path.rstrip("/") or "/docs"
        return urlunsplit(("https", OFFICIAL_WEBSITE_HOST, path, "", ""))
    return logical_key


def _document_text(
    root: Path, document: DocumentRecord, body: bytes, errors: list[str]
) -> str | None:
    if PurePosixPath(document.output_path).suffix.lower() != ".pdf":
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if len(text) != document.text_length:
            errors.append("text length mismatch")
        return text

    has_path = document.extracted_text_path is not None
    has_hash = document.extracted_text_sha256 is not None
    if has_path != has_hash:
        errors.append("incomplete extracted text identity")
        return None
    if not has_path:
        if document.text_length != 0:
            errors.append("text length mismatch")
        return None
    try:
        extracted = _secure_regular_read(
            root, Path(document.extracted_text_path or ""), missing_ok=True
        )
    except (OSError, _UnsafeOutputPath):
        errors.append("unsafe extracted text file")
        return None
    if extracted is None:
        errors.append("missing extracted text file")
        return None
    if sha256_bytes(extracted) != document.extracted_text_sha256:
        errors.append("extracted text hash mismatch")
    try:
        text = extracted.decode("utf-8")
    except UnicodeDecodeError:
        errors.append("invalid extracted text encoding")
        return None
    if len(text) != document.text_length:
        errors.append("text length mismatch")
    if contains_secret(text):
        errors.append("suspected_secret")
    return text


def validate_snapshot(
    manifest: SnapshotManifest,
    root: Path,
    expected_logical_keys: set[str],
    duplicate_explanations: set[frozenset[str]] | None = None,
) -> IntegrityReport:
    errors: list[str] = []
    warnings: list[str] = []
    hashes: dict[str, list[str]] = {}
    texts: dict[str, str] = {}
    root = Path(root)
    explanations = duplicate_explanations or set()

    if contains_sensitive_data(manifest.payload()):
        errors.append("manifest contains suspected secret")
    errors.extend(_serialized_manifest_errors(manifest, root))
    errors.extend(_manifest_layer_errors(manifest))

    document_keys = [
        document.logical_key or document.document_id
        for document in manifest.documents
    ]
    duplicate_keys = sorted(
        key for key, count in Counter(document_keys).items() if count > 1
    )
    if duplicate_keys:
        errors.append(f"duplicate logical key(s): {len(duplicate_keys)}")
    successes = {
        document.logical_key or document.document_id
        for document in manifest.documents
        if not document.error
    }
    failed = {_row_identity(row) for row in manifest.failures}
    excluded = {_row_identity(row) for row in manifest.exclusions}
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get("error"), str)
        or not row["error"]
        for row in manifest.failures
    ):
        errors.append("manifest failure missing error classification")
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get("reason"), str)
        or not row["reason"]
        for row in manifest.exclusions
    ):
        errors.append("manifest exclusion missing reason")
    if None in failed:
        errors.append("manifest failure missing logical key")
    if None in excluded:
        errors.append("manifest exclusion missing logical key")
    failed.discard(None)
    excluded.discard(None)
    overlaps = (successes & failed) | (successes & excluded) | (failed & excluded)
    if overlaps:
        errors.append(f"expected partition overlap: {len(overlaps)}")
    classified = successes | failed | excluded
    missing = sorted(expected_logical_keys - classified)
    extra = sorted(classified - expected_logical_keys)
    if missing:
        errors.append(f"missing expected document(s): {len(missing)}")
    if extra:
        errors.append(f"unexpected document(s): {len(extra)}")
    if manifest.expected_document_count != len(expected_logical_keys):
        errors.append("expected document count mismatch")
    if manifest.failures:
        errors.append(f"manifest failures: {len(manifest.failures)}")

    for document in manifest.documents:
        logical_key = document.logical_key or document.document_id
        if document.error:
            errors.append("document error present")
        errors.extend(_source_layer_errors(manifest, document))
        try:
            body = _secure_regular_read(
                root, Path(document.output_path), missing_ok=True
            )
        except (OSError, _UnsafeOutputPath):
            errors.append("unsafe file")
            continue
        if body is None:
            errors.append("missing file")
            continue
        if len(body) != document.byte_length:
            errors.append("byte length mismatch")
        digest = sha256_bytes(body)
        if digest != document.content_sha256:
            errors.append("hash mismatch")
        if document.source_kind in {"release", "main"}:
            header = f"blob {len(body)}\0".encode("ascii")
            git_blob_sha = hashlib.sha1(
                header + body, usedforsecurity=False
            ).hexdigest()
            if git_blob_sha != document.source_blob_sha:
                errors.append("git blob hash mismatch")
        hashes.setdefault(digest, []).append(logical_key)
        semantic_errors = classify_semantic_document(document, body)
        errors.extend(semantic_errors)
        text = _document_text(root, document, body, errors)
        if text is not None:
            texts[logical_key] = text
            if document.source_kind == "website":
                if normalize_markdown(text) != text:
                    errors.append("noncanonical website markdown")
                if _h1(text) != document.h1:
                    errors.append("stored h1 mismatch")
        if (
            document.title
            and document.h1
            and document.title.casefold() != document.h1.casefold()
            and "wrong_page_identity" not in semantic_errors
        ):
            warnings.append("title h1 mismatch")

    duplicates = tuple(
        tuple(sorted(logical_keys))
        for logical_keys in hashes.values()
        if len(logical_keys) > 1
    )
    duplicates = tuple(sorted(duplicates))
    required_explanations = {frozenset(group) for group in duplicates}
    required_explanations.update(
        frozenset({document.logical_key or document.document_id})
        for document in manifest.documents
        if document.semantic_status == "navigation_only"
    )
    missing_explanations = required_explanations - explanations
    unexplained_duplicates = [
        group
        for group in duplicates
        if frozenset(group) in missing_explanations
    ]
    if unexplained_duplicates:
        errors.append(
            f"unexplained duplicate body groups: {len(unexplained_duplicates)}"
        )
    missing_navigation = [
        group for group in missing_explanations if len(group) == 1
    ]
    if missing_navigation:
        errors.append(
            f"missing navigation explanation(s): {len(missing_navigation)}"
        )
    stale_explanations = explanations - required_explanations
    if stale_explanations:
        errors.append(f"stale duplicate explanation(s): {len(stale_explanations)}")
    explanation_prefix = "integrity_explanation_sha256:"
    persisted_explanation_hashes = {
        note.removeprefix(explanation_prefix)
        for note in manifest.notes
        if note.startswith(explanation_prefix)
    }
    supplied_explanation_hashes = {
        sha256_bytes(stable_json_bytes(sorted(group))) for group in explanations
    }
    if supplied_explanation_hashes - persisted_explanation_hashes:
        errors.append("unpersisted explanation(s)")
    if persisted_explanation_hashes - supplied_explanation_hashes:
        errors.append("unused persisted explanation(s)")

    closure = {
        _closure_key(manifest.source_kind, key) for key in successes | excluded
    }
    unresolved: set[str] = set()
    documents_by_key = {
        document.logical_key or document.document_id: document
        for document in manifest.documents
    }
    for logical_key, text in texts.items():
        document = documents_by_key[logical_key]
        for link in extract_internal_doc_links(document, text):
            if _closure_key(manifest.source_kind, link) not in closure:
                unresolved.add(link)
    if unresolved:
        errors.append(f"unresolved internal link(s): {len(unresolved)}")
    reported_duplicates = duplicates
    if contains_sensitive_data(duplicates):
        reported_duplicates = (("[redacted]",),)
    return IntegrityReport(
        manifest.snapshot_id,
        not errors,
        tuple(errors),
        tuple(warnings),
        reported_duplicates,
    )
