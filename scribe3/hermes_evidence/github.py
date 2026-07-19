from __future__ import annotations

import base64
import binascii
import json
import re
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qsl, quote, urlsplit

from .models import (
    DocumentRecord,
    SnapshotManifest,
    document_id_for,
    sha256_bytes,
    stable_json_bytes,
)
from .policy import (
    classify_repo_path,
    contains_secret,
    is_official_url,
    select_repo_document,
)
from .website import _atomic_write

API = "https://api.github.com/repos/NousResearch/hermes-agent"
MAX_DOCUMENT_BYTES = 50 * 1024 * 1024
PDFTOTEXT = "/opt/homebrew/bin/pdftotext"

_SHA_PATTERN = re.compile(r"[0-9a-fA-F]{40}")
_TAG_PATTERN = re.compile(r"v[A-Za-z0-9][A-Za-z0-9._-]*")
_RETRYABLE_HTTP_STATUSES = frozenset({429, 502, 503, 504})
_RATE_INTEGER_HEADERS = (
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
    "x-ratelimit-used",
    "retry-after",
)
_RATE_RESOURCE_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,32}")
_LFS_HEADER = b"version https://git-lfs.github.com/spec/v1"
_ACTIVE_SNAPSHOT_CLIENTS: set[int] = set()
_ACTIVE_SNAPSHOT_CLIENTS_LOCK = threading.Lock()

PdfExtractor = Callable[[Path, Path], None]


def _commit_sha(value: object) -> str:
    if not isinstance(value, str) or _SHA_PATTERN.fullmatch(value) is None:
        raise ValueError("GitHub response did not contain a full commit SHA")
    return value.lower()


def _safe_api_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.github.com"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            return False
    except ValueError:
        return False

    prefix = "/repos/NousResearch/hermes-agent/"
    if not parsed.path.startswith(prefix):
        return False
    endpoint = parsed.path[len(prefix) :]
    allowed_path = bool(
        re.fullmatch(r"commits/(?:main|[0-9a-fA-F]{40})", endpoint)
        or re.fullmatch(r"git/ref/tags/v[A-Za-z0-9][A-Za-z0-9._-]*", endpoint)
        or re.fullmatch(r"git/tags/[0-9a-fA-F]{40}", endpoint)
        or re.fullmatch(r"git/trees/[0-9a-fA-F]{40}", endpoint)
        or re.fullmatch(r"git/blobs/[0-9a-fA-F]{40}", endpoint)
    )
    if not allowed_path:
        return False
    query = parse_qsl(parsed.query, keep_blank_values=True)
    return query == [("recursive", "1")] if endpoint.startswith("git/trees/") else not query


class OfficialGitHubRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_official_url(newurl) or not _safe_api_url(newurl):
            raise RuntimeError("refusing unsafe GitHub redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _header_value(headers: object, name: str) -> str | None:
    getter = getattr(headers, "get", None)
    if callable(getter):
        value = getter(name)
        if isinstance(value, str):
            return value
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if (
                isinstance(key, str)
                and key.casefold() == name.casefold()
                and isinstance(value, str)
            ):
                return value
    return None


def _safe_rate_limit_fields(headers: object) -> dict[str, int | str]:
    fields: dict[str, int | str] = {}
    for name in _RATE_INTEGER_HEADERS:
        value = _header_value(headers, name)
        if value is not None and value.isascii() and value.isdigit():
            fields[name] = int(value)
    resource = _header_value(headers, "x-ratelimit-resource")
    if resource is not None and _RATE_RESOURCE_PATTERN.fullmatch(resource):
        fields["x-ratelimit-resource"] = resource
    return fields


def _default_pdf_extractor(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [PDFTOTEXT, "-enc", "UTF-8", str(source), str(target)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _safe_output_relative(repo_path: str, *, extracted: bool = False) -> Path:
    candidate = PurePosixPath(repo_path)
    if (
        not repo_path
        or candidate.is_absolute()
        or str(candidate) != repo_path
        or ".." in candidate.parts
        or "\\" in repo_path
        or "\x00" in repo_path
    ):
        raise ValueError("repository path is not canonical")
    return (
        Path("_extracted") / f"{repo_path}.txt"
        if extracted
        else Path(repo_path)
    )


def _source_layer(
    ref: str,
    source_kind: str | None,
    release_tag: str | None,
) -> tuple[str, str | None]:
    if source_kind not in {None, "release", "main"}:
        raise ValueError("source_kind must be release or main")

    if ref == "main":
        inferred_kind = "main"
    elif _TAG_PATTERN.fullmatch(ref):
        inferred_kind = "release"
    elif _SHA_PATTERN.fullmatch(ref):
        if source_kind is None:
            raise ValueError("source_kind is required for a fixed SHA")
        inferred_kind = source_kind
    else:
        raise ValueError("unsupported requested ref")

    if source_kind is not None and not _SHA_PATTERN.fullmatch(ref):
        if source_kind != inferred_kind:
            raise ValueError("source_kind conflicts with requested ref")
    resolved_kind = source_kind or inferred_kind

    if resolved_kind == "release":
        if source_kind == "release" and release_tag is None:
            raise ValueError("release_tag is required for release source_kind")
        resolved_tag = release_tag or ref
        if _TAG_PATTERN.fullmatch(resolved_tag) is None:
            raise ValueError("release_tag must be a version tag")
        if _TAG_PATTERN.fullmatch(ref) and resolved_tag != ref:
            raise ValueError("release_tag conflicts with requested ref")
        return resolved_kind, resolved_tag

    if release_tag is not None:
        raise ValueError("release_tag is not allowed for main source_kind")
    return resolved_kind, None


def _mime_type(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    return {
        ".adoc": "text/asciidoc",
        ".md": "text/markdown",
        ".mdx": "text/markdown",
        ".pdf": "application/pdf",
        ".rst": "text/x-rst",
    }[suffix]


class GitHubClient:
    def __init__(
        self,
        *,
        opener: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 2,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self._opener = opener or urllib.request.build_opener(
            OfficialGitHubRedirectHandler()
        ).open
        self._sleep = sleep
        self._max_retries = max_retries
        self.retry_events: list[dict] = []

    def _record_rate_limit(self, headers: object, endpoint: str) -> None:
        fields = _safe_rate_limit_fields(headers)
        if fields:
            self.retry_events.append(
                {"event": "github_rate_limit", "endpoint": endpoint, **fields}
            )

    def _record_retry(
        self,
        *,
        endpoint: str,
        attempt: int,
        status: int | None = None,
        error: str | None = None,
        delay_seconds: int = 0,
    ) -> None:
        event: dict[str, object] = {
            "event": "github_retry",
            "endpoint": endpoint,
            "attempt": attempt,
            "delay_seconds": delay_seconds,
        }
        if status is not None:
            event["status"] = status
        if error is not None:
            event["error"] = error
        self.retry_events.append(event)

    def _json(self, url: str) -> dict:
        if not _safe_api_url(url):
            raise ValueError("refusing non-official GitHub API endpoint")
        endpoint = urlsplit(url).path.removeprefix(
            "/repos/NousResearch/hermes-agent/"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "scribe3-hermes-evidence/1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        for attempt in range(self._max_retries + 1):
            try:
                with self._opener(request, timeout=60) as response:
                    geturl = getattr(response, "geturl", None)
                    final_url = geturl() if callable(geturl) else url
                    if not is_official_url(final_url) or not _safe_api_url(final_url):
                        raise RuntimeError(
                            "GitHub API response left the official repository"
                        )
                    self._record_rate_limit(getattr(response, "headers", {}), endpoint)
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise ValueError("GitHub API response must be an object")
                return payload
            except urllib.error.HTTPError as exc:
                self._record_rate_limit(exc.headers, endpoint)
                remaining = _header_value(exc.headers, "x-ratelimit-remaining")
                retryable = exc.code in _RETRYABLE_HTTP_STATUSES or (
                    exc.code == 403 and remaining == "0"
                )
                if not retryable or attempt >= self._max_retries:
                    raise RuntimeError("GitHub API request failed") from None
                retry_after = _header_value(exc.headers, "retry-after")
                delay = min(int(retry_after), 60) if retry_after and retry_after.isdigit() else 0
                self._record_retry(
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    status=exc.code,
                    delay_seconds=delay,
                )
                if delay:
                    self._sleep(delay)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt >= self._max_retries:
                    raise RuntimeError("GitHub API request failed") from None
                self._record_retry(
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=type(exc).__name__,
                )
        raise RuntimeError("GitHub API request failed")

    def resolve_ref(self, ref: str) -> str:
        if _SHA_PATTERN.fullmatch(ref):
            return ref.lower()
        if ref == "main":
            return _commit_sha(self._json(f"{API}/commits/main").get("sha"))
        if _TAG_PATTERN.fullmatch(ref) is None:
            raise ValueError("only main, version tags, and fixed SHAs are supported")

        payload = self._json(f"{API}/git/ref/tags/{quote(ref, safe='')}")
        obj = payload.get("object")
        if not isinstance(obj, Mapping):
            raise ValueError("GitHub tag response did not contain an object")
        for _ in range(8):
            object_type = obj.get("type")
            sha = _commit_sha(obj.get("sha"))
            if object_type == "commit":
                return sha
            if object_type != "tag":
                raise ValueError("GitHub ref did not resolve to a commit")
            tag_payload = self._json(f"{API}/git/tags/{sha}")
            obj = tag_payload.get("object")
            if not isinstance(obj, Mapping):
                raise ValueError("GitHub annotated tag did not contain an object")
        raise ValueError("GitHub annotated tag chain is too deep")

    def tree_payload(self, sha: str) -> dict:
        commit_sha = _commit_sha(sha)
        payload = self._json(f"{API}/git/trees/{commit_sha}?recursive=1")
        if not isinstance(payload.get("tree"), list):
            raise ValueError("GitHub tree response did not contain a tree")
        return payload

    def tree(self, sha: str) -> list[dict]:
        payload = self.tree_payload(sha)
        if payload.get("truncated") is not False:
            raise RuntimeError("GitHub recursive tree is truncated")
        return payload["tree"]

    def blob(self, sha: str) -> bytes:
        blob_sha = _commit_sha(sha)
        payload = self._json(f"{API}/git/blobs/{blob_sha}")
        if payload.get("encoding") != "base64" or not isinstance(
            payload.get("content"), str
        ):
            raise ValueError("unsupported GitHub blob encoding")
        encoded = "".join(payload["content"].split())
        try:
            return base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("invalid GitHub blob content") from exc


def _document_record(
    *,
    source_kind: str,
    repo_path: str,
    body: bytes,
    text_length: int,
    semantic_status: str,
    source_commit: str,
    source_blob_sha: str,
    error: str | None = None,
    extracted_text_path: str | None = None,
    extracted_text_sha256: str | None = None,
) -> DocumentRecord:
    content_sha256 = sha256_bytes(body)
    language, category, is_skill, is_contract = classify_repo_path(repo_path)
    return DocumentRecord(
        document_id=document_id_for(source_kind, repo_path, content_sha256),
        source_kind=source_kind,
        repo_path=repo_path,
        output_path=repo_path,
        content_sha256=content_sha256,
        byte_length=len(body),
        text_length=text_length,
        semantic_status=semantic_status,
        language=language,
        category=category,
        source_commit=source_commit,
        logical_key=repo_path,
        source_blob_sha=source_blob_sha,
        error=error,
        is_skill=is_skill,
        is_runtime_contract=is_contract,
        mime_type=_mime_type(repo_path),
        extracted_text_path=extracted_text_path,
        extracted_text_sha256=extracted_text_sha256,
    )


def _snapshot_repository_call(
    client: object,
    ref: str,
    snapshot_id: str,
    out_root: Path,
    fetched_at: str,
    *,
    pdf_extractor: PdfExtractor | None = None,
    source_kind: str | None = None,
    release_tag: str | None = None,
    event_start: int,
) -> SnapshotManifest:
    resolved_source_kind, resolved_release_tag = _source_layer(
        ref, source_kind, release_tag
    )
    resolved_sha = _commit_sha(client.resolve_ref(ref))
    tree = client.tree_payload(resolved_sha)
    if not isinstance(tree, dict) or tree.get("truncated") is not False:
        raise RuntimeError("GitHub recursive tree is truncated")
    rows = tree.get("tree")
    if not isinstance(rows, list):
        raise ValueError("GitHub recursive tree is missing")

    sorted_rows: list[dict] = []
    seen_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise ValueError("GitHub tree entry is invalid")
        path = row["path"]
        if path in seen_paths:
            raise ValueError("GitHub tree contains duplicate paths")
        seen_paths.add(path)
        sorted_rows.append(row)
    sorted_rows.sort(key=lambda row: row["path"])

    selected_rows: list[dict] = []
    notes: list[str] = []
    for row in sorted_rows:
        path = row["path"]
        selected = select_repo_document(path)
        if row.get("type") == "commit":
            if selected:
                selected_rows.append(row)
            else:
                notes.append(f"repository_submodule:{path}")
        elif selected:
            selected_rows.append(row)

    extractor = pdf_extractor or _default_pdf_extractor
    documents: list[DocumentRecord] = []
    failures: list[dict] = []
    exclusions: list[dict] = []

    for row in selected_rows:
        repo_path = row["path"]
        entry_type = row.get("type")
        source_blob_sha = row.get("sha") if isinstance(row.get("sha"), str) else None
        identity = {
            "logical_key": repo_path,
            "repo_path": repo_path,
            "source_blob_sha": source_blob_sha,
        }
        if entry_type == "commit":
            exclusions.append({**identity, "reason": "git_submodule"})
            continue
        if entry_type != "blob":
            exclusions.append({**identity, "reason": "unsupported_tree_entry"})
            continue
        if row.get("mode") == "120000":
            exclusions.append({**identity, "reason": "git_symlink"})
            continue
        size = row.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            failures.append({**identity, "error": "invalid_tree_entry"})
            continue
        if size > MAX_DOCUMENT_BYTES:
            exclusions.append({**identity, "reason": "oversized_attachment"})
            continue

        body: bytes | None = None
        try:
            target_relative = _safe_output_relative(repo_path)
            blob_sha = source_blob_sha
            if not blob_sha:
                raise ValueError("tree entry is missing blob SHA")
            body = client.blob(blob_sha)
            if not isinstance(body, bytes):
                raise TypeError("GitHub blob must be bytes")
            if body.startswith(_LFS_HEADER):
                exclusions.append(
                    {
                        **identity,
                        "content_sha256": sha256_bytes(body),
                        "reason": "git_lfs_pointer",
                    }
                )
                continue
            if len(body) > MAX_DOCUMENT_BYTES:
                exclusions.append(
                    {
                        **identity,
                        "content_sha256": sha256_bytes(body),
                        "reason": "oversized_attachment",
                    }
                )
                continue

            if repo_path.lower().endswith(".pdf"):
                _atomic_write(
                    Path(out_root),
                    target_relative,
                    body,
                    replace_existing=False,
                )
                if not body.startswith(b"%PDF-"):
                    failures.append(
                        {
                            **identity,
                            "content_sha256": sha256_bytes(body),
                            "error": "invalid_pdf_signature",
                        }
                    )
                    continue

                sidecar_relative = _safe_output_relative(repo_path, extracted=True)
                try:
                    with tempfile.TemporaryDirectory(
                        prefix="scribe3-hermes-pdf-"
                    ) as temporary_directory:
                        temporary_root = Path(temporary_directory)
                        temporary_source = temporary_root / "source.pdf"
                        temporary_sidecar = temporary_root / "sidecar.txt"
                        temporary_source.write_bytes(body)
                        extractor(temporary_source, temporary_sidecar)
                        if (
                            temporary_sidecar.is_symlink()
                            or not temporary_sidecar.is_file()
                        ):
                            raise ValueError(
                                "PDF extraction did not produce a regular file"
                            )
                        extracted_bytes = temporary_sidecar.read_bytes()
                    extracted_text = extracted_bytes.decode("utf-8")
                    if not extracted_text.strip():
                        raise ValueError("PDF extraction produced no text")
                    _atomic_write(
                        Path(out_root),
                        sidecar_relative,
                        extracted_bytes,
                        replace_existing=False,
                    )
                except Exception:
                    documents.append(
                        _document_record(
                            source_kind=resolved_source_kind,
                            repo_path=repo_path,
                            body=body,
                            text_length=0,
                            semantic_status="binary_attachment",
                            source_commit=resolved_sha,
                            source_blob_sha=blob_sha,
                            error="pdf_text_extraction_failed",
                        )
                    )
                    failures.append(
                        {
                            **identity,
                            "content_sha256": sha256_bytes(body),
                            "error": "pdf_text_extraction_failed",
                        }
                    )
                    continue

                documents.append(
                    _document_record(
                        source_kind=resolved_source_kind,
                        repo_path=repo_path,
                        body=body,
                        text_length=len(extracted_text),
                        semantic_status="content",
                        source_commit=resolved_sha,
                        source_blob_sha=blob_sha,
                        extracted_text_path=sidecar_relative.as_posix(),
                        extracted_text_sha256=sha256_bytes(extracted_bytes),
                    )
                )
                continue

            text = body.decode("utf-8")
            if contains_secret(text):
                failures.append(
                    {
                        **identity,
                        "content_sha256": sha256_bytes(body),
                        "error": "suspected_secret",
                    }
                )
                continue
            _atomic_write(
                Path(out_root),
                target_relative,
                body,
                replace_existing=False,
            )
            documents.append(
                _document_record(
                    source_kind=resolved_source_kind,
                    repo_path=repo_path,
                    body=body,
                    text_length=len(text),
                    semantic_status="content",
                    source_commit=resolved_sha,
                    source_blob_sha=blob_sha,
                )
            )
        except Exception as exc:
            failure = {**identity, "error": type(exc).__name__}
            if isinstance(body, bytes):
                failure["content_sha256"] = sha256_bytes(body)
            failures.append(failure)

    retry_events = list(getattr(client, "retry_events", ()))[event_start:]
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        source_kind=resolved_source_kind,
        source_origin="https://github.com/NousResearch/hermes-agent",
        requested_ref=ref,
        resolved_sha=resolved_sha,
        release_tag=resolved_release_tag,
        fetched_at=fetched_at,
        crawler_version="1",
        documents=documents,
        failures=failures,
        exclusions=exclusions,
        notes=notes,
        discovery_sha256=sha256_bytes(stable_json_bytes(tree)),
        expected_document_count=len(selected_rows),
        tree_truncated=False,
        retry_events=retry_events,
    )


def snapshot_repository(
    client: object,
    ref: str,
    snapshot_id: str,
    out_root: Path,
    fetched_at: str,
    *,
    pdf_extractor: PdfExtractor | None = None,
    source_kind: str | None = None,
    release_tag: str | None = None,
) -> SnapshotManifest:
    """Snapshot one ref while requiring exclusive, serial use of *client*.

    Concurrent snapshots for the same client are rejected. Callers must also avoid
    direct client operations until this call returns so the event slice stays local.
    """
    client_identity = id(client)
    with _ACTIVE_SNAPSHOT_CLIENTS_LOCK:
        if client_identity in _ACTIVE_SNAPSHOT_CLIENTS:
            raise RuntimeError(
                "concurrent snapshot calls for one client are not supported"
            )
        _ACTIVE_SNAPSHOT_CLIENTS.add(client_identity)
        try:
            event_start = len(getattr(client, "retry_events", ()))
        except TypeError:
            _ACTIVE_SNAPSHOT_CLIENTS.remove(client_identity)
            raise TypeError("client retry_events history must be a sequence") from None

    try:
        return _snapshot_repository_call(
            client,
            ref,
            snapshot_id,
            out_root,
            fetched_at,
            pdf_extractor=pdf_extractor,
            source_kind=source_kind,
            release_tag=release_tag,
            event_start=event_start,
        )
    finally:
        with _ACTIVE_SNAPSHOT_CLIENTS_LOCK:
            _ACTIVE_SNAPSHOT_CLIENTS.discard(client_identity)
