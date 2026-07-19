from __future__ import annotations

import json
import hashlib
import html
import os
import re
import stat
from collections import Counter
from dataclasses import dataclass
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
from .policy import (
    DOC_EXTENSIONS,
    OFFICIAL_WEBSITE_HOST,
    classify_repo_path,
    contains_secret,
    select_repo_document,
)
from .website import (
    _FILE_READ_FLAGS,
    _UnsafeOutputPath,
    _directory_identity_is_current,
    _h1,
    _has_documentation_lead,
    _is_official_website_url,
    _open_parent_fd,
    _open_root_fd,
    _read_fd,
    _relative_parts,
    _semantic_soft_error,
    output_path_for_url,
    normalize_markdown,
)

_MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
_REFERENCE_DEFINITION_PATTERN = re.compile(
    r"(?m)^[ \t]*\[([^\]]+)\]:[ \t]*<?([^>\s]+)>?(?:[ \t]+.*)?$"
)
_REFERENCE_LINK_WITH_LABEL_PATTERN = re.compile(
    r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]"
)
_SHORTCUT_REFERENCE_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\](?![\[(])")
_HTML_LINK_PATTERN = re.compile(
    r'''(?ix)<a\s+[^>]*href\s*=\s*(?:(["'])(.*?)\1|([^\s>]+))[^>]*>'''
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
ALLOWED_SOURCE_KINDS = frozenset({"website", "release", "main", "runtime"})
RUNTIME_SOURCE_ORIGIN = "hermes-runtime"
RUNTIME_REQUESTED_REF = "runtime"


def _is_canonical_website_url(value: object) -> bool:
    if not isinstance(value, str) or not _is_official_website_url(value):
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except (UnicodeError, ValueError):
        return False
    return (
        not parsed.query
        and not parsed.fragment
        and value
        == urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    )


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
        try:
            path = urlsplit(record.requested_url or record.logical_key).path
        except (UnicodeError, ValueError):
            return set()
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


def _strong_body_soft_error(body: str) -> str | None:
    if _has_documentation_lead(body):
        return None
    lines = body.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and lines[index].startswith("# "):
        index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    paragraph: list[str] = []
    while index < len(lines) and lines[index].strip():
        paragraph.append(lines[index].strip())
        index += 1
    opening = re.sub(r"\s+", " ", " ".join(paragraph)[:800].casefold())
    patterns = (
        (
            "soft_login",
            r"^(?:(?:please|you must)\s+)?(?:sign in|log in)\b"
            r".{0,80}\b(?:access|view)\s+(?:this|the)\s+"
            r"(?:page|content|resource)\b",
        ),
        ("soft_404", r"^(?:(?:404\b.{0,40})?page not found\b|the requested page could not be found\b)"),
        ("soft_anti_bot", r"^(?:browser verification\b|checking your browser\b|verify you are human\b)"),
        ("soft_access_denied", r"^access denied\b.*\b(?:permission|authorized)\b"),
        ("soft_server_error", r"^(?:service(?: temporarily)? unavailable|internal server error|bad gateway)\b.*\b(?:server|try again later|unavailable)\b"),
    )
    for error, pattern in patterns:
        if re.search(pattern, opening):
            return error
    return None


def _semantic_text_errors(record: DocumentRecord, text: str) -> set[str]:
    errors: set[str] = set()
    if contains_secret(text):
        errors.add("suspected_secret")
    semantic_error = _semantic_soft_error(record.title, text)
    if semantic_error is None:
        semantic_error = _strong_body_soft_error(text)
    if semantic_error is not None:
        errors.add(semantic_error)
    if _wrong_page_identity(record, text):
        errors.add("wrong_page_identity")
    errors.update(_content_shape_errors(record, text))
    return errors


def classify_semantic_document(
    record: DocumentRecord, body: bytes
) -> tuple[str, ...]:
    """Return fail-closed semantic violations for one persisted document."""
    errors: set[str] = set()
    if not _mime_matches(record):
        errors.add("mime_extension_mismatch")
    if record.source_kind == "website":
        try:
            valid_urls = _is_canonical_website_url(
                record.requested_url
            ) and _is_canonical_website_url(record.final_url)
        except (UnicodeError, ValueError):
            valid_urls = False
        try:
            requested = urlsplit(record.requested_url or "")
            final = urlsplit(record.final_url or "")
            requested_port = requested.port
            final_port = final.port
        except (UnicodeError, ValueError):
            requested = urlsplit("")
            final = urlsplit("")
            requested_port = final_port = None
            valid_urls = False
        if not valid_urls:
            errors.add("invalid_website_url")
        if (
            final.scheme != "https"
            or final.hostname != OFFICIAL_WEBSITE_HOST
            or final_port is not None
            or (requested.scheme, requested.hostname, requested_port)
            != (final.scheme, final.hostname, final_port)
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

    errors.update(_semantic_text_errors(record, text))
    return tuple(sorted(errors))


@dataclass(frozen=True)
class _ParsedInternalLinks:
    internal: frozenset[str]
    invalid_count: int = 0


_OFFICIAL_REPOSITORY_HOSTS = frozenset(
    {"github.com", "raw.githubusercontent.com"}
)
_OFFICIAL_REPOSITORY_PARTS = ("NousResearch", "hermes-agent")


def _normalize_repository_target(
    path: str,
    *,
    directory: bool,
    available_logical_keys: frozenset[str],
) -> tuple[str, str | None]:
    decoded_path = path
    if not decoded_path or decoded_path.startswith("/"):
        return "invalid_internal", None
    candidate = PurePosixPath(decoded_path)
    normalized_parts: list[str] = []
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not normalized_parts:
                return "invalid_internal", None
            normalized_parts.pop()
        else:
            normalized_parts.append(part)
    normalized = "/".join(normalized_parts)
    if not normalized:
        return "invalid_internal", None
    if directory:
        candidates = (
            f"{normalized.rstrip('/')}/README.md",
            f"{normalized.rstrip('/')}/index.md",
        )
        for directory_index in candidates:
            if directory_index in available_logical_keys:
                return "internal", directory_index
        return "internal", candidates[0]
    if select_repo_document(normalized):
        return "internal", normalized
    if PurePosixPath(normalized).suffix.lower() in DOC_EXTENSIONS:
        return "invalid_internal", None
    return "external", None


def _absolute_repository_target(
    parsed_target,
    *,
    allowed_repository_refs: frozenset[str],
    available_logical_keys: frozenset[str],
) -> tuple[str, str | None]:
    host = parsed_target.hostname
    if host not in _OFFICIAL_REPOSITORY_HOSTS:
        return "external", None
    try:
        explicit_port = parsed_target.port is not None
    except (UnicodeError, ValueError):
        return "invalid_internal", None
    if (
        parsed_target.scheme != "https"
        or explicit_port
        or parsed_target.username is not None
        or parsed_target.password is not None
        or contains_sensitive_data(parsed_target.geturl())
    ):
        return "invalid_internal", None
    decoded_path = unquote(parsed_target.path)
    if decoded_path.count("/") != parsed_target.path.count("/"):
        return "invalid_internal", None
    parts = tuple(part for part in decoded_path.split("/") if part)
    if parts[:2] != _OFFICIAL_REPOSITORY_PARTS:
        return "external", None
    if host == "github.com":
        if len(parts) < 5 or parts[2] not in {"blob", "tree"}:
            return "external", None
        action = parts[2]
        ref = parts[3]
        repo_path = "/".join(parts[4:])
        directory = action == "tree"
    else:
        if len(parts) < 4:
            return "invalid_internal", None
        ref = parts[2]
        repo_path = "/".join(parts[3:])
        directory = False
    if not ref or ref not in allowed_repository_refs:
        return "invalid_internal", None
    return _normalize_repository_target(
        repo_path,
        directory=directory,
        available_logical_keys=available_logical_keys,
    )


def _classify_link_target(
    record: DocumentRecord,
    raw_target: str,
    *,
    allowed_repository_refs: frozenset[str] = frozenset(),
    available_logical_keys: frozenset[str] = frozenset(),
) -> tuple[str, str | None]:
    target = html.unescape(raw_target).strip().strip("<>")
    if not target or target.startswith("#"):
        return "external", None
    try:
        parsed_target = urlsplit(target)
        _ = parsed_target.port
    except (UnicodeError, ValueError):
        return "invalid_internal", None
    if parsed_target.scheme not in {"", "https"}:
        if parsed_target.hostname in {
            OFFICIAL_WEBSITE_HOST,
            *_OFFICIAL_REPOSITORY_HOSTS,
        }:
            return "invalid_internal", None
        return "external", None

    if record.source_kind == "website":
        base = record.final_url or record.requested_url or record.logical_key
        try:
            resolved_url = urljoin(base, target)
            resolved = urlsplit(resolved_url)
            _ = resolved.port
        except (UnicodeError, ValueError):
            return "invalid_internal", None
        if resolved.hostname != OFFICIAL_WEBSITE_HOST:
            return "external", None
        decoded_target_path = unquote(parsed_target.path)
        if (
            decoded_target_path.count("/") != parsed_target.path.count("/")
            or (
                ".." in PurePosixPath(decoded_target_path).parts
                and not resolved.path.startswith("/docs")
            )
        ):
            return "invalid_internal", None
        if (
            resolved.scheme != "https"
            or resolved.port is not None
            or resolved.username is not None
            or resolved.password is not None
            or contains_sensitive_data(resolved_url)
        ):
            return "invalid_internal", None
        if not resolved.path.startswith("/docs"):
            return "external", None
        suffix = PurePosixPath(resolved.path).suffix.lower()
        if suffix and suffix not in DOC_EXTENSIONS | {".htm", ".html"}:
            return "external", None
        clean_url = urlunsplit(
            (resolved.scheme, resolved.netloc, resolved.path, "", "")
        )
        if (
            not _is_official_website_url(clean_url)
        ):
            return "invalid_internal", None
        path = resolved.path.rstrip("/") or "/docs"
        path = re.sub(r"/(?:index(?:\.html?)?)$", "", path, flags=re.IGNORECASE)
        normalized = urlunsplit(
            (
                "https",
                OFFICIAL_WEBSITE_HOST,
                path or "/docs",
                "",
                "",
            )
        )
        return "internal", normalized

    if record.source_kind not in {"release", "main"}:
        return "external", None
    if parsed_target.netloc:
        return _absolute_repository_target(
            parsed_target,
            allowed_repository_refs=allowed_repository_refs,
            available_logical_keys=available_logical_keys,
        )
    decoded_path = unquote(parsed_target.path)
    if not decoded_path:
        return "external", None
    if decoded_path.startswith("/"):
        candidate = PurePosixPath(decoded_path.lstrip("/"))
    else:
        base_path = PurePosixPath(record.repo_path or record.logical_key)
        candidate = base_path.parent / decoded_path
    return _normalize_repository_target(
        candidate.as_posix(),
        directory=decoded_path.endswith("/") or not candidate.suffix,
        available_logical_keys=available_logical_keys,
    )


def _parse_internal_doc_links(
    record: DocumentRecord,
    body: str,
    *,
    allowed_repository_refs: frozenset[str] = frozenset(),
    available_logical_keys: frozenset[str] = frozenset(),
) -> _ParsedInternalLinks:
    definitions = {
        match.group(1).strip().casefold(): match.group(2)
        for match in _REFERENCE_DEFINITION_PATTERN.finditer(body)
    }
    targets = [match.group(1) for match in _MARKDOWN_LINK_PATTERN.finditer(body)]
    for match in _REFERENCE_LINK_WITH_LABEL_PATTERN.finditer(body):
        reference = (match.group(2) or match.group(1)).strip().casefold()
        target = definitions.get(reference)
        if target:
            targets.append(target)
    for match in _SHORTCUT_REFERENCE_PATTERN.finditer(body):
        target = definitions.get(match.group(1).strip().casefold())
        if target:
            targets.append(target)
    targets.extend(
        match.group(2) or match.group(3) for match in _HTML_LINK_PATTERN.finditer(body)
    )
    targets.extend(match.group(1) for match in _AUTOLINK_PATTERN.finditer(body))
    internal: set[str] = set()
    invalid_count = 0
    for target in targets:
        state, normalized = _classify_link_target(
            record,
            target,
            allowed_repository_refs=allowed_repository_refs,
            available_logical_keys=available_logical_keys,
        )
        if state == "internal" and normalized is not None:
            internal.add(normalized)
        elif state == "invalid_internal":
            invalid_count += 1
    return _ParsedInternalLinks(frozenset(internal), invalid_count)


def extract_internal_doc_links(
    record: DocumentRecord,
    body: str,
    *,
    allowed_repository_refs: set[str | None] | None = None,
    available_logical_keys: set[str] | None = None,
) -> set[str]:
    """Extract same-tier official documentation links as normalized logical keys."""
    refs = allowed_repository_refs
    if refs is None:
        refs = {record.source_commit}
    return set(
        _parse_internal_doc_links(
            record,
            body,
            allowed_repository_refs=frozenset(
                ref for ref in refs if isinstance(ref, str) and ref
            ),
            available_logical_keys=frozenset(available_logical_keys or set()),
        ).internal
    )


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
                opened_stat = os.fstat(descriptor)
                if not stat.S_ISREG(opened_stat.st_mode):
                    raise _UnsafeOutputPath("evidence target is not a regular file")
                data = _read_fd(descriptor)
                final_descriptor_stat = os.fstat(descriptor)
                try:
                    final_name_stat = os.stat(
                        parts[-1], dir_fd=parent_fd, follow_symlinks=False
                    )
                except OSError as error:
                    raise _UnsafeOutputPath(
                        "evidence target identity changed"
                    ) from error
                stable_fields = (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
                descriptor_changed = any(
                    getattr(opened_stat, field)
                    != getattr(final_descriptor_stat, field)
                    for field in stable_fields
                )
                name_changed = any(
                    getattr(final_descriptor_stat, field)
                    != getattr(final_name_stat, field)
                    for field in stable_fields
                )
                if (
                    not stat.S_ISREG(final_name_stat.st_mode)
                    or descriptor_changed
                    or name_changed
                    or not _directory_identity_is_current(
                        root, root_fd, parts[:-1], parent_fd
                    )
                ):
                    raise _UnsafeOutputPath("evidence target identity changed")
                return data
            finally:
                os.close(descriptor)
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


def _row_identity_errors(row: object) -> list[str]:
    if not isinstance(row, dict):
        return ["empty row identity"]
    identities = [
        row.get(field)
        for field in ("logical_key", "requested_url", "repo_path")
        if field in row
    ]
    nonempty = [value for value in identities if isinstance(value, str) and value]
    errors: list[str] = []
    if not nonempty:
        errors.append("empty row identity")
    if len(set(nonempty)) > 1:
        errors.append("conflicting row identity")
    if any(not isinstance(value, str) or not value for value in identities):
        errors.append("empty row identity")
    return errors


def _serialized_manifest_errors(
    manifest: SnapshotManifest, manifest_path: Path | None
) -> list[str]:
    errors: list[str] = []
    if manifest_path is None:
        return ["manifest path required"]
    path = Path(manifest_path)
    if not path.name or path.name in {".", ".."}:
        return ["invalid manifest path"]
    try:
        raw = _secure_regular_read(path.parent, Path(path.name), missing_ok=True)
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
        requested_url = document.requested_url
        logical_key_valid = (
            isinstance(document.logical_key, str)
            and bool(document.logical_key)
            and document.logical_key == requested_url
        )
        if not logical_key_valid:
            errors.append("website logical key mismatch")
        try:
            valid_urls = _is_canonical_website_url(
                requested_url
            ) and _is_canonical_website_url(document.final_url)
        except (UnicodeError, ValueError):
            valid_urls = False
        if not valid_urls:
            errors.append("invalid website URL")
        try:
            expected_output_path = output_path_for_url(document.logical_key).as_posix()
        except (AttributeError, TypeError, UnicodeError, ValueError):
            expected_output_path = None
        if expected_output_path is None or document.output_path != expected_output_path:
            errors.append("website output path mismatch")
        if document.website_snapshot_id != manifest.snapshot_id:
            errors.append("website snapshot mismatch")
        if document.source_commit is not None or document.source_blob_sha is not None:
            errors.append("website document contains repository identity")
        if document.repo_path is not None:
            errors.append("website document contains repository path")
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
        path_identity_valid = (
            bool(document.repo_path)
            and document.repo_path == logical_key
            and document.output_path == document.repo_path
            and select_repo_document(document.repo_path)
        )
        if not path_identity_valid:
            errors.append("repository path identity mismatch")
        if document.repo_path and (
            document.language,
            document.category,
            document.is_skill,
            document.is_runtime_contract,
        ) != classify_repo_path(document.repo_path):
            errors.append("repository classification mismatch")
    elif manifest.source_kind == "runtime":
        if (
            document.source_commit is not None
            or document.source_blob_sha is not None
            or document.website_snapshot_id is not None
        ):
            errors.append("runtime document contains snapshot identity")
        if not document.is_runtime_contract:
            errors.append("runtime evidence not marked runtime contract")
        if document.repo_path is not None:
            errors.append("runtime document contains repository path")
    return errors


def _manifest_layer_errors(manifest: SnapshotManifest) -> list[str]:
    errors: list[str] = []
    github_origin = "https://github.com/NousResearch/hermes-agent"
    website_origin = "https://hermes-agent.nousresearch.com/docs/sitemap.xml"
    if manifest.source_kind not in ALLOWED_SOURCE_KINDS:
        return ["unknown source kind"]
    if manifest.source_kind == "website":
        if manifest.source_origin != website_origin or manifest.requested_ref != "sitemap":
            errors.append("invalid website source identity")
        if manifest.resolved_sha is not None or manifest.release_tag is not None:
            errors.append("website manifest contains repository version identity")
        if manifest.tree_truncated is not None:
            errors.append("invalid website tree identity")
    elif manifest.source_kind in {"release", "main"}:
        if manifest.source_origin != github_origin:
            errors.append("invalid repository source identity")
        if (
            not isinstance(manifest.resolved_sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", manifest.resolved_sha) is None
        ):
            errors.append("invalid resolved source commit")
        if manifest.tree_truncated is not False:
            errors.append("repository tree incomplete")
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
        if (
            manifest.source_origin != RUNTIME_SOURCE_ORIGIN
            or manifest.requested_ref != RUNTIME_REQUESTED_REF
        ):
            errors.append("invalid runtime source identity")
        if manifest.resolved_sha is not None or manifest.release_tag is not None:
            errors.append("runtime manifest contains repository version identity")
        if manifest.tree_truncated is not None:
            errors.append("invalid runtime tree identity")
    return errors


def _closure_key(source_kind: str, logical_key: str) -> str:
    if source_kind != "website":
        return logical_key
    try:
        parsed = urlsplit(logical_key)
    except (UnicodeError, ValueError):
        return logical_key
    if parsed.scheme == "https" and parsed.hostname == OFFICIAL_WEBSITE_HOST:
        path = parsed.path.rstrip("/") or "/docs"
        return urlunsplit(("https", OFFICIAL_WEBSITE_HOST, path, "", ""))
    return logical_key


def _persisted_explanations(
    notes: list[str], errors: list[str]
) -> dict[frozenset[str], str]:
    prefix = "integrity_explanation:v1:"
    legacy_prefix = "integrity_explanation_sha256:"
    parsed: dict[frozenset[str], str] = {}
    for note in notes:
        if note.startswith(legacy_prefix):
            errors.append("invalid persisted explanation")
            continue
        if not note.startswith("integrity_explanation:"):
            continue
        if not note.startswith(prefix):
            errors.append("invalid persisted explanation")
            continue
        try:
            payload = json.loads(note.removeprefix(prefix))
        except json.JSONDecodeError:
            errors.append("invalid persisted explanation")
            continue
        if not isinstance(payload, dict):
            errors.append("invalid persisted explanation")
            continue
        kind = payload.get("kind")
        logical_keys = payload.get("logical_keys")
        reason = payload.get("reason")
        canonical = prefix + stable_json_bytes(payload).decode("utf-8").strip()
        valid_keys = (
            isinstance(logical_keys, list)
            and bool(logical_keys)
            and all(isinstance(key, str) and key for key in logical_keys)
            and logical_keys == sorted(set(logical_keys))
        )
        if (
            payload.get("version") != 1
            or kind not in {"duplicate", "navigation"}
            or not valid_keys
            or not isinstance(reason, str)
            or not reason.strip()
            or note != canonical
        ):
            errors.append("invalid persisted explanation")
            continue
        group = frozenset(logical_keys)
        if group in parsed:
            errors.append("duplicate persisted explanation")
            continue
        parsed[group] = kind
    return parsed


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
    if not (has_path and has_hash) or document.text_length <= 0:
        errors.append("PDF sidecar required")
    if has_path != has_hash:
        errors.append("incomplete extracted text identity")
        return None
    if not has_path:
        if document.text_length != 0:
            errors.append("text length mismatch")
        return None
    expected_sidecar = f"_extracted/{document.repo_path}.txt"
    if document.extracted_text_path != expected_sidecar:
        errors.append("noncanonical extracted text path")
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
    errors.extend(sorted(_semantic_text_errors(document, text)))
    return text


def validate_snapshot(
    manifest: SnapshotManifest,
    root: Path,
    expected_logical_keys: set[str],
    duplicate_explanations: set[frozenset[str]] | None = None,
    *,
    manifest_path: Path | None = None,
) -> IntegrityReport:
    errors: list[str] = []
    warnings: list[str] = []
    hashes: dict[str, list[str]] = {}
    texts: dict[str, str] = {}
    root = Path(root)
    supplied_explanations = duplicate_explanations

    manifest_sensitive = contains_sensitive_data(manifest.payload())
    if manifest_sensitive:
        errors.append("manifest contains suspected secret")
    errors.extend(_serialized_manifest_errors(manifest, manifest_path))
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
    link_exclusion_rows = [
        row
        for row in manifest.exclusions
        if isinstance(row, dict) and row.get("scope") == "internal_link"
    ]
    document_exclusion_rows = [
        row for row in manifest.exclusions if row not in link_exclusion_rows
    ]
    for row in (*manifest.failures, *manifest.exclusions):
        errors.extend(_row_identity_errors(row))
    failed_rows = [_row_identity(row) for row in manifest.failures]
    excluded_rows = [_row_identity(row) for row in document_exclusion_rows]
    link_excluded_rows = [_row_identity(row) for row in link_exclusion_rows]
    failed_counts = Counter(failed_rows)
    excluded_counts = Counter(
        _row_identity(row) for row in manifest.exclusions
    )
    if any(identity is not None and count > 1 for identity, count in failed_counts.items()):
        errors.append("duplicate failure identity")
    if any(
        identity is not None and count > 1
        for identity, count in excluded_counts.items()
    ):
        errors.append("duplicate exclusion identity")
    failed = set(failed_rows)
    excluded = set(excluded_rows)
    link_excluded = set(link_excluded_rows)
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
    if None in link_excluded:
        errors.append("manifest link exclusion missing logical key")
    failed.discard(None)
    excluded.discard(None)
    link_excluded.discard(None)
    for row in link_exclusion_rows:
        logical_key = _row_identity(row)
        if (
            set(row) != {"logical_key", "scope", "reason"}
            or row.get("reason") != "not_in_sitemap"
            or not _is_canonical_website_url(logical_key)
            or manifest.source_kind != "website"
        ):
            errors.append("invalid internal link exclusion")
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
    if link_excluded & (expected_logical_keys | classified):
        errors.append("internal link exclusion overlaps discovery scope")
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
    persisted = _persisted_explanations(manifest.notes, errors)
    persisted_groups = set(persisted)
    for group, kind in persisted.items():
        expected_kind = "navigation" if len(group) == 1 else "duplicate"
        if kind != expected_kind:
            errors.append("persisted explanation kind mismatch")
    missing_explanations = required_explanations - persisted_groups
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
    stale_explanations = persisted_groups - required_explanations
    if stale_explanations:
        errors.append(f"stale persisted explanation(s): {len(stale_explanations)}")
    if (
        supplied_explanations is not None
        and supplied_explanations != persisted_groups
    ):
        errors.append("explanation cross-check mismatch")

    closure = {
        _closure_key(manifest.source_kind, key) for key in successes | excluded
    }
    unresolved: set[str] = set()
    observed_internal_links: set[str] = set()
    invalid_internal_links = 0
    documents_by_key = {
        document.logical_key or document.document_id: document
        for document in manifest.documents
    }
    allowed_repository_refs = frozenset(
        ref
        for ref in (
            manifest.requested_ref,
            manifest.release_tag,
            manifest.resolved_sha,
        )
        if isinstance(ref, str) and ref
    )
    available_logical_keys = frozenset(successes | excluded)
    for logical_key, text in texts.items():
        document = documents_by_key[logical_key]
        parsed_links = _parse_internal_doc_links(
            document,
            text,
            allowed_repository_refs=allowed_repository_refs,
            available_logical_keys=available_logical_keys,
        )
        invalid_internal_links += parsed_links.invalid_count
        for link in parsed_links.internal:
            closure_link = _closure_key(manifest.source_kind, link)
            observed_internal_links.add(closure_link)
            if closure_link not in closure and closure_link not in link_excluded:
                unresolved.add(link)
    stale_link_exclusions = link_excluded - observed_internal_links
    if stale_link_exclusions:
        errors.append(
            f"stale link exclusion(s): {len(stale_link_exclusions)}"
        )
    if invalid_internal_links:
        errors.append(f"invalid internal link(s): {invalid_internal_links}")
    if unresolved:
        errors.append(f"unresolved internal link(s): {len(unresolved)}")
    reported_duplicates = duplicates
    if contains_sensitive_data(duplicates):
        reported_duplicates = (("[redacted]",),)
    return IntegrityReport(
        "[redacted]" if manifest_sensitive else manifest.snapshot_id,
        not errors,
        tuple(errors),
        tuple(warnings),
        reported_duplicates,
    )
