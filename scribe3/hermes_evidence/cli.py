from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import re
import sys
import urllib.request
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from .github import GitHubClient, snapshot_repository
from .integrity import validate_snapshot
from .models import (
    DocumentRecord,
    FILTER_POLICY_VERSION,
    SnapshotManifest,
    contains_sensitive_data,
    sha256_bytes,
    stable_json_bytes,
)
from .website import (
    CrawlPage,
    RetryPolicy,
    _UnsafeOutputPath,
    _atomic_write,
    _ensure_safe_directory,
    _safe_directory_exists,
    _secure_read,
    crawl_website,
    discover_sitemap_snapshot,
    output_path_for_url,
)


CACHE_ROOT = (
    Path(__file__).resolve().parents[2] / "docs/external/hermes-agent-docs"
)
SOURCE_SITEMAP = "https://hermes-agent.nousresearch.com/docs/sitemap.xml"
DEFAULT_RELEASE_REF = "v2026.7.7.2"
_RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_TAG_PATTERN = re.compile(r"v[A-Za-z0-9][A-Za-z0-9._-]*")
_SNAPSHOT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def fetch_bytes(url: str) -> bytes:
    if url != SOURCE_SITEMAP:
        raise ValueError("refusing non-official Sitemap URL")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "scribe3-hermes-evidence/1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        final_url = response.geturl()
        if final_url != SOURCE_SITEMAP:
            raise RuntimeError("Sitemap response left the official URL")
        return response.read()


def _load_crawl4ai() -> SimpleNamespace:
    try:
        from crawl4ai import (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
        )
        try:
            from crawl4ai import SemaphoreDispatcher
        except ImportError:
            SemaphoreDispatcher = None
    except ImportError as error:
        raise RuntimeError("Crawl4AI is not installed") from error
    return SimpleNamespace(
        AsyncWebCrawler=AsyncWebCrawler,
        BrowserConfig=BrowserConfig,
        CacheMode=CacheMode,
        CrawlerRunConfig=CrawlerRunConfig,
        SemaphoreDispatcher=SemaphoreDispatcher,
    )


def _preflight_crawl4ai_runtime(runtime: SimpleNamespace) -> None:
    async def launch_browser() -> None:
        browser_config = runtime.BrowserConfig(headless=True, verbose=False)
        async with runtime.AsyncWebCrawler(config=browser_config):
            pass

    asyncio.run(launch_browser())


def _markdown_text(value: object) -> str | None:
    if isinstance(value, str):
        return value
    for name in ("raw_markdown", "fit_markdown"):
        try:
            candidate = getattr(value, name, None)
        except Exception:
            return None
        if isinstance(candidate, str):
            return candidate
    return None


def _markdown_h1(value: str) -> str | None:
    for line in value.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return None


def _fixed_crawl_failure(error: str, *, url: str = "<untrusted-result-url>") -> CrawlPage:
    return CrawlPage(
        url=url,
        final_url=url,
        status=0,
        success=False,
        markdown="",
        title="",
        mime_type="text/html",
        error=error,
    )


def _result_page(result: object) -> CrawlPage:
    try:
        url = result.url
        redirected_url = result.redirected_url
        status_code = result.status_code
        success = result.success
        markdown_value = result.markdown
        metadata = result.metadata
        error_message = result.error_message
    except Exception:
        return _fixed_crawl_failure("invalid_result")

    try:
        output_path_for_url(url)
    except (TypeError, ValueError):
        return _fixed_crawl_failure("invalid_result")
    if (
        isinstance(status_code, bool)
        or not isinstance(status_code, int)
        or not 0 <= status_code <= 599
        or not isinstance(success, bool)
        or not isinstance(error_message, str)
    ):
        return _fixed_crawl_failure("invalid_result", url=url)
    final_url = redirected_url or url
    if not isinstance(final_url, str):
        return _fixed_crawl_failure("invalid_result", url=url)

    status = status_code
    error = ""
    if success:
        markdown = _markdown_text(markdown_value)
        if not isinstance(metadata, Mapping):
            return _fixed_crawl_failure("invalid_result", url=url)
        title = metadata.get("title")
        if markdown is None:
            return _fixed_crawl_failure("invalid_result", url=url)
        if not isinstance(title, str) or not title.strip():
            title = _markdown_h1(markdown)
        if not isinstance(title, str):
            return _fixed_crawl_failure("invalid_result", url=url)
        if contains_sensitive_data({"title": title}):
            return _fixed_crawl_failure("invalid_result", url=url)
    else:
        timed_out = "timeout" in error_message.casefold() or "timed out" in error_message.casefold()
        if status == 0 and timed_out:
            status = 408
            error = "timeout"
        elif status:
            error = f"http_{status}"
        else:
            error = "crawl_failed"
        markdown = ""
        title = ""

    retry_after = None
    try:
        headers = getattr(result, "response_headers", None)
    except Exception:
        headers = None
    if isinstance(headers, Mapping):
        value = headers.get("Retry-After") or headers.get("retry-after")
        if isinstance(value, str) and value.isascii() and value.isdigit():
            retry_after = value
    return CrawlPage(
        url=url,
        final_url=final_url,
        status=status,
        success=success,
        markdown=markdown,
        title=title,
        mime_type="text/html",
        error=error,
        retry_after=retry_after,
    )


async def _arun_many(crawler, urls, config, runtime, max_concurrency):
    parameters = inspect.signature(crawler.arun_many).parameters
    if "dispatcher" in parameters:
        if runtime.SemaphoreDispatcher is None:
            raise RuntimeError("Crawl4AI dispatcher is unavailable")
        dispatcher_parameters = inspect.signature(
            runtime.SemaphoreDispatcher
        ).parameters
        dispatcher_options = {}
        if "semaphore_count" in dispatcher_parameters:
            dispatcher_options["semaphore_count"] = max_concurrency
        if "max_session_permit" in dispatcher_parameters:
            dispatcher_options["max_session_permit"] = max_concurrency
        if not dispatcher_options:
            raise RuntimeError("unsupported Crawl4AI dispatcher signature")
        dispatcher = runtime.SemaphoreDispatcher(**dispatcher_options)
        return await crawler.arun_many(
            urls=urls,
            config=config,
            dispatcher=dispatcher,
        )
    if "max_concurrent" in parameters:
        return await crawler.arun_many(
            urls=urls,
            config=config,
            max_concurrent=max_concurrency,
        )
    raise RuntimeError("unsupported Crawl4AI arun_many signature")


async def crawl4ai_fetch_many(
    urls: list[str], *, max_concurrency: int = 5
) -> list[CrawlPage]:
    if not 1 <= max_concurrency <= 5:
        raise ValueError("max_concurrency must be between one and five")
    runtime = _load_crawl4ai()
    browser_config = runtime.BrowserConfig(headless=True, verbose=False)
    cache_mode = getattr(runtime.CacheMode, "BYPASS", None)
    primary_config = runtime.CrawlerRunConfig(
        cache_mode=cache_mode,
        remove_overlay_elements=False,
        wait_until="domcontentloaded",
        delay_before_return_html=1.0,
        page_timeout=30000,
        css_selector=".theme-doc-markdown",
        screenshot=False,
        verbose=False,
    )
    fallback_config = runtime.CrawlerRunConfig(
        cache_mode=cache_mode,
        remove_overlay_elements=False,
        wait_until="domcontentloaded",
        delay_before_return_html=1.0,
        page_timeout=30000,
        css_selector="main",
        screenshot=False,
        verbose=False,
    )
    unscoped_config = runtime.CrawlerRunConfig(
        cache_mode=cache_mode,
        remove_overlay_elements=False,
        wait_until="domcontentloaded",
        delay_before_return_html=1.0,
        page_timeout=30000,
        screenshot=False,
        verbose=False,
    )
    async with runtime.AsyncWebCrawler(config=browser_config) as crawler:
        primary_results = await _arun_many(
            crawler, urls, primary_config, runtime, max_concurrency
        )
        pages = [_result_page(result) for result in primary_results]
        requested_urls = frozenset(urls)

        def eligible_for_fallback(page: CrawlPage) -> bool:
            if page.url not in requested_urls:
                return False
            try:
                output_path_for_url(page.final_url)
            except (TypeError, ValueError):
                return False
            navigation_only = page.url.rstrip("/").endswith("/search")
            return bool(
                page.status not in _RETRYABLE_STATUS_CODES
                and (
                    not page.success
                    or (
                        len(page.markdown.strip()) < 200
                        and not navigation_only
                    )
                )
            )

        fallback_urls = list(
            dict.fromkeys(
                page.url
                for page in pages
                if eligible_for_fallback(page)
            )
        )
        if not fallback_urls:
            return pages
        fallback_results = await _arun_many(
            crawler, fallback_urls, fallback_config, runtime, max_concurrency
        )
        fallback_pages = [_result_page(result) for result in fallback_results]
        replacements = {
            page.url: page
            for page in fallback_pages
            if page.url in fallback_urls
        }
        replaced = [replacements.get(page.url, page) for page in pages]
        replaced.extend(
            page for page in fallback_pages if page.url not in fallback_urls
        )
        unscoped_urls = list(
            dict.fromkeys(
                page.url
                for page in replaced
                if eligible_for_fallback(page)
            )
        )
        if not unscoped_urls:
            return replaced
        unscoped_results = await _arun_many(
            crawler, unscoped_urls, unscoped_config, runtime, max_concurrency
        )
        unscoped_pages = [_result_page(result) for result in unscoped_results]
        unscoped_replacements = {
            page.url: page
            for page in unscoped_pages
            if page.url in unscoped_urls
        }
        final = [unscoped_replacements.get(page.url, page) for page in replaced]
        final.extend(
            page for page in unscoped_pages if page.url not in unscoped_urls
        )
        return final


@dataclass(frozen=True)
class _OperationResult:
    status: int
    pointer: dict | None = None
    error: str | None = None


class _PinnedGitHubClient:
    def __init__(self, client: object, requested_ref: str, resolved_sha: str) -> None:
        self._client = client
        self._requested_ref = requested_ref
        self._resolved_sha = resolved_sha

    def resolve_ref(self, ref: str) -> str:
        if ref != self._requested_ref:
            raise ValueError("pinned GitHub ref mismatch")
        return self._resolved_sha

    def __getattr__(self, name: str):
        return getattr(self._client, name)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _timestamp_token(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("evidence timestamp must be timezone-aware")
    utc = parsed.astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


def _read_json_file(path: Path) -> object:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("required JSON file is missing or unsafe")
    try:
        value = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("invalid JSON file") from error
    if contains_sensitive_data(value):
        raise RuntimeError("JSON file contains suspected sensitive data")
    return value


def _safe_relative_path(value: object) -> Path:
    if not isinstance(value, str):
        raise RuntimeError("cache pointer path is invalid")
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise RuntimeError("cache pointer path is invalid")
    return path


def _load_current(*, required: bool) -> dict | None:
    try:
        raw = _secure_read(CACHE_ROOT, Path("current.json"), missing_ok=True)
    except (OSError, _UnsafeOutputPath) as error:
        raise RuntimeError("current pointer is unsafe") from error
    if raw is None:
        if required:
            raise RuntimeError("current pointer is missing")
        return None
    try:
        current = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("current pointer is invalid") from error
    if (
        not isinstance(current, dict)
        or current.get("schema_version") != 1
        or contains_sensitive_data(current)
    ):
        raise RuntimeError("current pointer is invalid")
    return current


def _cache_relative(path: Path) -> str:
    try:
        relative = Path(path).relative_to(CACHE_ROOT)
    except ValueError as error:
        raise RuntimeError("cache path escaped cache root") from error
    if not relative.parts or ".." in relative.parts:
        raise RuntimeError("cache path escaped cache root")
    return relative.as_posix()


def _write_current(current: dict) -> None:
    if current.get("schema_version") != 1 or contains_sensitive_data(current):
        raise RuntimeError("refusing invalid current pointer")
    _atomic_write(CACHE_ROOT, Path("current.json"), stable_json_bytes(current))


def _prepare_cache_directories(*relative_paths: Path) -> None:
    try:
        for relative_path in relative_paths:
            _ensure_safe_directory(CACHE_ROOT, relative_path)
    except _UnsafeOutputPath as error:
        raise RuntimeError("cache output path is unsafe") from error


def _write_cache_manifest(relative_path: Path, manifest: SnapshotManifest) -> str:
    payload = manifest.payload()
    if contains_sensitive_data(payload):
        raise ValueError("Manifest contains sensitive data and cannot be persisted")
    digest = sha256_bytes(stable_json_bytes(payload))
    payload["manifest_sha256"] = digest
    _atomic_write(
        CACHE_ROOT,
        relative_path,
        stable_json_bytes(payload),
        replace_existing=False,
    )
    return digest


def _replace_current_layers(pointers: Mapping[str, dict]) -> None:
    current = _load_current(required=False) or {"schema_version": 1}
    updated = dict(current)
    updated.update(pointers)
    _write_current(updated)


def _manifest_from_path(path: Path) -> SnapshotManifest:
    stored = _read_json_file(path)
    if not isinstance(stored, dict):
        raise RuntimeError("serialized manifest must be an object")
    manifest_fields = {item.name for item in fields(SnapshotManifest)}
    computed_fields = {
        "document_count",
        "total_bytes",
        "success_count",
        "failed_count",
        "excluded_count",
        "completeness_status",
        "manifest_sha256",
    }
    if set(stored) - manifest_fields - computed_fields:
        raise RuntimeError("serialized manifest contains unknown fields")
    payload = {
        key: value for key, value in stored.items() if key in manifest_fields
    }
    rows = payload.get("documents")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError("serialized manifest documents are invalid")
    try:
        payload["documents"] = [DocumentRecord(**row) for row in rows]
        manifest = SnapshotManifest(**payload)
    except (TypeError, ValueError) as error:
        raise RuntimeError("serialized manifest fields are invalid") from error
    if not all(
        isinstance(value, list)
        for value in (
            manifest.failures,
            manifest.exclusions,
            manifest.notes,
            manifest.retry_events,
        )
    ):
        raise RuntimeError("serialized manifest collections are invalid")
    return manifest


def _row_identity(row: object) -> str | None:
    if not isinstance(row, Mapping):
        return None
    for name in ("logical_key", "requested_url", "repo_path", "document_id"):
        value = row.get(name)
        if isinstance(value, str) and value:
            return value
    return None


def _expected_keys(manifest: SnapshotManifest) -> set[str]:
    keys = {
        document.logical_key or document.document_id
        for document in manifest.documents
    }
    for row in (*manifest.failures, *manifest.exclusions):
        identity = _row_identity(row)
        if identity is not None:
            keys.add(identity)
    return keys


def _snapshot_root_for_manifest(manifest: SnapshotManifest) -> Path:
    if manifest.source_kind == "website":
        if _SNAPSHOT_ID_PATTERN.fullmatch(manifest.snapshot_id) is None:
            raise RuntimeError("website snapshot ID is invalid")
        return CACHE_ROOT / "snapshots/website" / manifest.snapshot_id
    if manifest.source_kind == "release":
        if (
            not isinstance(manifest.release_tag, str)
            or _TAG_PATTERN.fullmatch(manifest.release_tag) is None
        ):
            raise RuntimeError("release snapshot identity is invalid")
        return CACHE_ROOT / "snapshots/upstream" / manifest.release_tag
    if manifest.source_kind == "main":
        if (
            not isinstance(manifest.resolved_sha, str)
            or _SHA_PATTERN.fullmatch(manifest.resolved_sha) is None
        ):
            raise RuntimeError("main snapshot identity is invalid")
        return CACHE_ROOT / "snapshots/upstream" / f"main-{manifest.resolved_sha}"
    if manifest.source_kind == "runtime":
        if _SNAPSHOT_ID_PATTERN.fullmatch(manifest.snapshot_id) is None:
            raise RuntimeError("runtime snapshot identity is invalid")
        return CACHE_ROOT / "snapshots/runtime" / manifest.snapshot_id
    raise RuntimeError("unknown evidence source layer")


def _manifest_digest(path: Path) -> str:
    value = _read_json_file(path)
    if not isinstance(value, dict):
        raise RuntimeError("serialized manifest must be an object")
    digest = value.get("manifest_sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise RuntimeError("serialized manifest digest is invalid")
    return digest


def _pointer_for(
    manifest: SnapshotManifest,
    manifest_path: Path,
    snapshot_root: Path,
    manifest_sha256: str,
) -> dict:
    return {
        "source_kind": manifest.source_kind,
        "snapshot_id": manifest.snapshot_id,
        "manifest_path": _cache_relative(manifest_path),
        "snapshot_root": _cache_relative(snapshot_root),
        "manifest_sha256": manifest_sha256,
        "resolved_sha": manifest.resolved_sha,
        "release_tag": manifest.release_tag,
    }


def _validate_pointer(pointer: object, manifest: SnapshotManifest, manifest_path: Path) -> None:
    if not isinstance(pointer, Mapping):
        raise RuntimeError("current snapshot pointer is invalid")
    snapshot_root = _snapshot_root_for_manifest(manifest)
    expected = {
        "source_kind": manifest.source_kind,
        "snapshot_id": manifest.snapshot_id,
        "manifest_path": _cache_relative(manifest_path),
        "snapshot_root": _cache_relative(snapshot_root),
        "manifest_sha256": _manifest_digest(manifest_path),
        "resolved_sha": manifest.resolved_sha,
        "release_tag": manifest.release_tag,
    }
    if dict(pointer) != expected:
        raise RuntimeError("current snapshot pointer does not match manifest")


def _integrity_manifest(
    manifest_path: Path, *, pointer: object | None = None, emit: bool
):
    manifest_path = Path(manifest_path)
    manifest = _manifest_from_path(manifest_path)
    snapshot_root = _snapshot_root_for_manifest(manifest)
    if pointer is not None:
        _validate_pointer(pointer, manifest, manifest_path)
    report = validate_snapshot(
        manifest,
        snapshot_root,
        _expected_keys(manifest),
        manifest_path=manifest_path,
    )
    if emit:
        print(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True))
    return report


def _incomplete_website_snapshots() -> list[tuple[Path, dict, dict]]:
    root = CACHE_ROOT / "snapshots/website"
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("website snapshot root is unsafe")
    candidates = []
    for snapshot_root in sorted(root.iterdir()):
        if snapshot_root.is_symlink() or not snapshot_root.is_dir():
            raise RuntimeError("website snapshot entry is unsafe")
        checkpoint_path = snapshot_root / "checkpoint.json"
        if not checkpoint_path.exists():
            continue
        checkpoint = _read_json_file(checkpoint_path)
        if not isinstance(checkpoint, dict) or not isinstance(
            checkpoint.get("complete"), bool
        ):
            raise RuntimeError("website checkpoint is invalid")
        if checkpoint["complete"]:
            continue
        state = _read_json_file(snapshot_root / "resume.json")
        if not isinstance(state, dict):
            raise RuntimeError("website resume state is invalid")
        candidates.append((snapshot_root, state, checkpoint))
    return candidates


def _website_resume_root(discovery) -> tuple[Path, str]:
    candidates = _incomplete_website_snapshots()
    if len(candidates) != 1:
        raise RuntimeError("resume requires exactly one incomplete snapshot")
    snapshot_root, state, checkpoint = candidates[0]
    snapshot_id = snapshot_root.name
    expected_state = {
        "source_origin": SOURCE_SITEMAP,
        "filter_policy_version": FILTER_POLICY_VERSION,
        "discovery_sha256": discovery.raw_sha256,
        "snapshot_id": snapshot_id,
    }
    if state != expected_state or checkpoint.get("snapshot_id") != snapshot_id:
        raise RuntimeError("incompatible website checkpoint")
    return snapshot_root, snapshot_id


def _current_layer_manifest(layer: str) -> SnapshotManifest | None:
    current = _load_current(required=False)
    if current is None or layer not in current:
        return None
    pointer = current[layer]
    if not isinstance(pointer, Mapping):
        raise RuntimeError("current layer pointer is invalid")
    manifest_path = CACHE_ROOT / _safe_relative_path(pointer.get("manifest_path"))
    manifest = _manifest_from_path(manifest_path)
    _validate_pointer(pointer, manifest, manifest_path)
    return manifest


def _website_operation(
    *,
    concurrency: int,
    batch_size: int,
    resume: bool | None,
    update_current: bool,
    emit: bool = True,
) -> _OperationResult:
    runtime = _load_crawl4ai()
    _preflight_crawl4ai_runtime(runtime)
    _prepare_cache_directories(Path("snapshots/website"), Path("manifests"))
    discovery = discover_sitemap_snapshot(fetch_bytes(SOURCE_SITEMAP))
    incomplete = _incomplete_website_snapshots()
    if resume is True or (resume is None and incomplete):
        snapshot_root, snapshot_id = _website_resume_root(discovery)
        fetched_at = _utc_now()
    else:
        if incomplete:
            raise RuntimeError("an incomplete website snapshot requires --resume")
        fetched_at = _utc_now()
        snapshot_id = f"website-{_timestamp_token(fetched_at)}"
        snapshot_root = CACHE_ROOT / "snapshots/website" / snapshot_id
        snapshot_relative = Path("snapshots/website") / snapshot_id
        if _safe_directory_exists(CACHE_ROOT, snapshot_relative):
            raise RuntimeError("website snapshot already exists")
        _ensure_safe_directory(CACHE_ROOT, snapshot_relative, exist_ok=False)
        state = {
            "source_origin": SOURCE_SITEMAP,
            "filter_policy_version": FILTER_POLICY_VERSION,
            "discovery_sha256": discovery.raw_sha256,
            "snapshot_id": snapshot_id,
        }
        _atomic_write(
            CACHE_ROOT,
            snapshot_relative / "resume.json",
            stable_json_bytes(state),
        )

    previous = _current_layer_manifest("website")

    async def fetch_many(batch: list[str]) -> list[CrawlPage]:
        return await crawl4ai_fetch_many(
            batch, max_concurrency=concurrency
        )

    manifest = asyncio.run(
        crawl_website(
            list(discovery.urls),
            fetch_many,
            snapshot_id,
            snapshot_root,
            fetched_at,
            discovery_sha256=discovery.raw_sha256,
            previous=previous,
            policy=RetryPolicy(
                batch_size=batch_size,
                max_concurrency=concurrency,
            ),
        )
    )
    manifest_relative = Path("manifests") / f"{snapshot_id}.json"
    manifest_path = CACHE_ROOT / manifest_relative
    if _secure_read(CACHE_ROOT, manifest_relative, missing_ok=True) is not None:
        raise RuntimeError("website manifest already exists")
    digest = _write_cache_manifest(manifest_relative, manifest)
    report = validate_snapshot(
        manifest,
        snapshot_root,
        set(discovery.urls),
        manifest_path=manifest_path,
    )
    if not report.ok:
        if emit:
            print(
                json.dumps(
                    {
                        "error": "integrity_failed",
                        "ok": False,
                        "source_kind": "website",
                        "stage": "integrity",
                    },
                    sort_keys=True,
                )
            )
        return _OperationResult(2, error="integrity_failed")
    pointer = _pointer_for(manifest, manifest_path, snapshot_root, digest)
    if update_current:
        _replace_current_layers({"website": pointer})
    if emit:
        print(
            json.dumps(
                {
                    "ok": True,
                    "source_kind": "website",
                    "snapshot_id": snapshot_id,
                    "document_count": len(manifest.documents),
                },
                sort_keys=True,
            )
        )
    return _OperationResult(0, pointer)


def _repository_operation(
    ref: str, *, update_current: bool, emit: bool = True
) -> _OperationResult:
    _prepare_cache_directories(Path("snapshots/upstream"), Path("manifests"))
    if ref == "main":
        source_kind = "main"
        release_tag = None
    elif _TAG_PATTERN.fullmatch(ref):
        source_kind = "release"
        release_tag = ref
    else:
        raise ValueError("repository ref must be main or a version tag")

    client = GitHubClient()
    resolved_sha = client.resolve_ref(ref)
    if not isinstance(resolved_sha, str) or _SHA_PATTERN.fullmatch(resolved_sha) is None:
        raise RuntimeError("repository ref did not resolve to a fixed SHA")
    pinned = _PinnedGitHubClient(client, ref, resolved_sha)
    if source_kind == "main":
        snapshot_id = f"main-{resolved_sha}"
        directory_name = snapshot_id
        manifest_name = f"upstream-{snapshot_id}.json"
    else:
        snapshot_id = f"release-{ref}-{resolved_sha}"
        directory_name = ref
        manifest_name = f"upstream-{ref}.json"
    snapshot_relative = Path("snapshots/upstream") / directory_name
    manifest_relative = Path("manifests") / manifest_name
    snapshot_root = CACHE_ROOT / snapshot_relative
    manifest_path = CACHE_ROOT / manifest_relative
    root_exists = _safe_directory_exists(CACHE_ROOT, snapshot_relative)
    manifest_exists = (
        _secure_read(CACHE_ROOT, manifest_relative, missing_ok=True) is not None
    )
    if root_exists != manifest_exists:
        raise RuntimeError("repository snapshot is incomplete")
    if root_exists:
        manifest = _manifest_from_path(manifest_path)
        if (
            manifest.source_kind != source_kind
            or manifest.snapshot_id != snapshot_id
            or manifest.requested_ref != ref
            or manifest.resolved_sha != resolved_sha
            or manifest.release_tag != release_tag
            or _snapshot_root_for_manifest(manifest) != snapshot_root
        ):
            raise RuntimeError("repository snapshot identity mismatch")
        report = validate_snapshot(
            manifest,
            snapshot_root,
            _expected_keys(manifest),
            manifest_path=manifest_path,
        )
        if not report.ok:
            if emit:
                print(
                    json.dumps(
                        {
                            "error": "integrity_failed",
                            "ok": False,
                            "source_kind": source_kind,
                            "stage": "integrity",
                        },
                        sort_keys=True,
                    )
                )
            return _OperationResult(2, error="integrity_failed")
        pointer = _pointer_for(
            manifest,
            manifest_path,
            snapshot_root,
            _manifest_digest(manifest_path),
        )
        if update_current:
            _replace_current_layers({source_kind: pointer})
        if emit:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "reused": True,
                        "source_kind": source_kind,
                        "snapshot_id": snapshot_id,
                        "resolved_sha": resolved_sha,
                    },
                    sort_keys=True,
                )
            )
        return _OperationResult(0, pointer)
    _ensure_safe_directory(CACHE_ROOT, snapshot_relative, exist_ok=False)
    manifest = snapshot_repository(
        pinned,
        ref,
        snapshot_id,
        snapshot_root,
        _utc_now(),
        source_kind=source_kind,
        release_tag=release_tag,
    )
    digest = _write_cache_manifest(manifest_relative, manifest)
    report = validate_snapshot(
        manifest,
        snapshot_root,
        _expected_keys(manifest),
        manifest_path=manifest_path,
    )
    if not report.ok:
        if emit:
            print(
                json.dumps(
                    {
                        "error": "integrity_failed",
                        "ok": False,
                        "source_kind": source_kind,
                        "stage": "integrity",
                    },
                    sort_keys=True,
                )
            )
        return _OperationResult(2, error="integrity_failed")
    pointer = _pointer_for(manifest, manifest_path, snapshot_root, digest)
    if update_current:
        _replace_current_layers({source_kind: pointer})
    if emit:
        print(
            json.dumps(
                {
                    "ok": True,
                    "source_kind": source_kind,
                    "snapshot_id": snapshot_id,
                    "resolved_sha": resolved_sha,
                },
                sort_keys=True,
            )
        )
    return _OperationResult(0, pointer)


def _integrity_all() -> int:
    current = _load_current(required=True)
    reports = {}
    for layer in ("website", "release", "main"):
        pointer = current.get(layer)
        if not isinstance(pointer, Mapping):
            raise RuntimeError("current pointer is missing an evidence layer")
        manifest_path = CACHE_ROOT / _safe_relative_path(
            pointer.get("manifest_path")
        )
        report = _integrity_manifest(
            manifest_path, pointer=pointer, emit=False
        )
        reports[layer] = asdict(report)
    print(json.dumps(reports, ensure_ascii=False, sort_keys=True))
    return 0 if all(report["ok"] for report in reports.values()) else 2


def _all_operation() -> int:
    stage = "website"
    try:
        website = _website_operation(
            concurrency=5,
            batch_size=40,
            resume=None,
            update_current=False,
            emit=False,
        )
        if website.status != 0:
            return _emit_all_failure(stage, website.error)
        stage = "release"
        release = _repository_operation(
            DEFAULT_RELEASE_REF, update_current=False, emit=False
        )
        if release.status != 0:
            return _emit_all_failure(stage, release.error)
        stage = "main"
        main_result = _repository_operation(
            "main", update_current=False, emit=False
        )
        if main_result.status != 0:
            return _emit_all_failure(stage, main_result.error)
        pointers = {
            "website": website.pointer,
            "release": release.pointer,
            "main": main_result.pointer,
        }
        stage = "final_integrity"
        for pointer in pointers.values():
            if not isinstance(pointer, Mapping):
                raise RuntimeError("completed operation did not produce a pointer")
            manifest_path = CACHE_ROOT / _safe_relative_path(
                pointer.get("manifest_path")
            )
            if not _integrity_manifest(
                manifest_path, pointer=pointer, emit=False
            ).ok:
                return _emit_all_failure(stage, "integrity_failed")
        stage = "current"
        _replace_current_layers(pointers)
    except Exception:
        return _emit_all_failure(stage, "operation_failed")
    print(json.dumps({"ok": True, "current": pointers}, sort_keys=True))
    return 0


def _emit_all_failure(stage: str, error: str | None) -> int:
    print(
        json.dumps(
            {
                "error": error or "operation_failed",
                "ok": False,
                "stage": stage,
            },
            sort_keys=True,
        )
    )
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scribe3-hermes-evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover = subparsers.add_parser("discover")
    discover.add_argument("--json", action="store_true", dest="as_json")
    website = subparsers.add_parser("website")
    website.add_argument("--concurrency", type=int, choices=range(1, 6), default=5)
    website.add_argument("--batch-size", type=int, choices=range(1, 41), default=40)
    website.add_argument("--resume", action="store_true")
    repository = subparsers.add_parser("repository")
    repository.add_argument("--ref", required=True)
    integrity = subparsers.add_parser("integrity")
    integrity_group = integrity.add_mutually_exclusive_group(required=True)
    integrity_group.add_argument("--manifest", type=Path)
    integrity_group.add_argument("--all", action="store_true", dest="all_manifests")
    subparsers.add_parser("all")
    return parser


def _discover(as_json: bool) -> int:
    discovery = discover_sitemap_snapshot(fetch_bytes(SOURCE_SITEMAP))
    payload = {
        "source_sitemap": SOURCE_SITEMAP,
        "sitemap_sha256": discovery.raw_sha256,
        "url_count": len(discovery.urls),
        "page_kinds": discovery.page_kinds,
        "urls": list(discovery.urls),
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Sitemap URLs: {payload['url_count']}")
        print(f"Sitemap SHA-256: {payload['sitemap_sha256']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "discover":
            return _discover(args.as_json)
        if args.command == "website":
            return _website_operation(
                concurrency=args.concurrency,
                batch_size=args.batch_size,
                resume=args.resume,
                update_current=True,
            ).status
        if args.command == "repository":
            return _repository_operation(args.ref, update_current=True).status
        if args.command == "integrity":
            if args.all_manifests:
                return _integrity_all()
            report = _integrity_manifest(args.manifest, emit=True)
            return 0 if report.ok else 2
        if args.command == "all":
            return _all_operation()
    except Exception:
        print("Hermes evidence operation failed", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
