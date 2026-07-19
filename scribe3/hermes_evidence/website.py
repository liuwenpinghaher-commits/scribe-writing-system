from __future__ import annotations

import asyncio
import inspect
import json
import math
import os
import re
import secrets
import stat
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlparse

from .models import (
    DocumentRecord,
    SnapshotManifest,
    contains_sensitive_data,
    document_id_for,
    sha256_bytes,
    stable_json_bytes,
)
from .policy import contains_secret, is_official_url

_SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


@dataclass(frozen=True)
class SitemapDiscovery:
    raw_sha256: str
    urls: tuple[str, ...]
    page_kinds: dict[str, str]


def discover_sitemap(xml_bytes: bytes) -> list[str]:
    """Parse an official docs sitemap into unique, sorted URLs."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise ValueError("Sitemap contains invalid XML") from error
    root_namespace, root_name = _tag_parts(root.tag)
    if root_name != "urlset" or root_namespace not in {"", _SITEMAP_NAMESPACE}:
        raise ValueError("Sitemap root must be a urlset")

    url_nodes = []
    for child in root:
        namespace, name = _tag_parts(child.tag)
        if name != "url" or namespace != root_namespace:
            raise ValueError("Sitemap root must contain only direct URL elements")
        url_nodes.append(child)
    if not url_nodes:
        raise ValueError("Sitemap must contain direct URL elements")

    urls = set()
    for url_node in url_nodes:
        loc_nodes = []
        for child in url_node:
            namespace, name = _tag_parts(child.tag)
            if namespace != root_namespace:
                continue
            if name not in {"loc", "lastmod", "changefreq", "priority"}:
                raise ValueError("Sitemap URL contains an unexpected standard element")
            if name == "loc":
                loc_nodes.append(child)
        if len(loc_nodes) != 1 or len(loc_nodes[0]) or not loc_nodes[0].text or not loc_nodes[0].text.strip():
            raise ValueError("Sitemap URL must contain exactly one non-empty loc")
        urls.add(loc_nodes[0].text.strip())

    invalid = sorted(url for url in urls if not is_official_url(url))
    if invalid:
        raise ValueError(f"Sitemap contains non-official URL(s): {len(invalid)}")
    return sorted(urls)


def _tag_parts(tag: object) -> tuple[str, str]:
    if not isinstance(tag, str):
        return "", ""
    if tag.startswith("{"):
        namespace, separator, local_name = tag[1:].partition("}")
        if separator:
            return namespace, local_name
    return "", tag


def _page_kind(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    if path.endswith("/search"):
        return "search"
    if path in {"/docs", "/docs/user-guide", "/docs/developer-guide"}:
        return "directory"
    return "content"


def discover_sitemap_snapshot(xml_bytes: bytes) -> SitemapDiscovery:
    urls = tuple(discover_sitemap(xml_bytes))
    return SitemapDiscovery(
        raw_sha256=sha256_bytes(xml_bytes),
        urls=urls,
        page_kinds={url: _page_kind(url) for url in urls},
    )


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "index"


def output_path_for_url(url: str) -> Path:
    """Map an official docs URL to its deterministic cache-relative Markdown path."""
    parsed = urlparse(url)
    if not is_official_url(url) or parsed.hostname != "hermes-agent.nousresearch.com":
        raise ValueError("non-official website URL")
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0] == "docs":
        parts = parts[1:]
    if not parts:
        return Path("pages/index.md")
    return Path("pages", *(_slug(part) for part in parts[:-1]), f"{_slug(parts[-1])}.md")


def _is_official_website_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    try:
        output_path_for_url(url)
    except ValueError:
        return False
    return True


def _output_paths_for_urls(urls: list[str]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    owners: dict[str, str] = {}
    for url in urls:
        relative_path = output_path_for_url(url)
        key = relative_path.as_posix()
        owner = owners.get(key)
        if owner is not None and owner != url:
            raise ValueError("website output path collision")
        owners[key] = url
        paths[url] = relative_path
    return paths


@dataclass(frozen=True)
class CrawlPage:
    url: str
    final_url: str
    status: int
    success: bool
    markdown: str
    title: str
    mime_type: str
    error: str = ""
    retry_after: str | None = None


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    max_retry_after: float = 300.0
    batch_size: int = 40
    max_concurrency: int = 5
    jitter: Callable[[float], float] = lambda delay: 0.0
    sleep: Callable[[float], object] = asyncio.sleep

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if (
            not math.isfinite(self.base_delay)
            or not math.isfinite(self.max_delay)
            or self.base_delay < 0
            or self.max_delay < 0
        ):
            raise ValueError("retry delays must be non-negative")
        if not math.isfinite(self.max_retry_after) or self.max_retry_after < 0:
            raise ValueError("max_retry_after must be finite and non-negative")
        if not 1 <= self.batch_size <= 40:
            raise ValueError("batch_size must be between one and 40")
        if not 1 <= self.max_concurrency <= 5:
            raise ValueError("max_concurrency must be between one and five")


@dataclass
class CrawlCheckpoint:
    snapshot_id: str
    completed: dict[str, dict] = field(default_factory=dict)
    retry_events: list[dict] = field(default_factory=list)
    complete: bool = False


@dataclass(frozen=True)
class CrawlBatchResult:
    pages: tuple[CrawlPage, ...]
    failures: tuple[dict, ...]
    retry_events: tuple[dict, ...]


_RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def _retry_after_seconds(value: object, maximum: float) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    if not math.isfinite(seconds) or seconds < 0 or seconds > maximum:
        return None
    return seconds


def _retry_delay(page: CrawlPage | None, attempt: int, policy: RetryPolicy) -> float:
    if page is not None:
        server_delay = _retry_after_seconds(
            page.retry_after, policy.max_retry_after
        )
        if server_delay is not None:
            return server_delay
    exponential = min(policy.base_delay * (2 ** (attempt - 1)), policy.max_delay)
    jitter = max(0.0, float(policy.jitter(exponential)))
    return min(exponential + jitter, policy.max_delay)


async def _sleep(delay: float, policy: RetryPolicy) -> None:
    result = policy.sleep(delay)
    if inspect.isawaitable(result):
        await result


async def fetch_with_bounded_retry(
    urls: list[str],
    fetch_many: Callable[[list[str]], Awaitable[list[CrawlPage]]],
    policy: RetryPolicy,
    checkpoint: CrawlCheckpoint,
) -> CrawlBatchResult:
    if len(urls) != len(set(urls)):
        raise ValueError("website retry URLs must be unique")
    for url in urls:
        output_path_for_url(url)
    pending = list(dict.fromkeys(urls))
    terminal_pages: dict[str, CrawlPage] = {}
    terminal_failures: dict[str, dict] = {}
    event_start = len(checkpoint.retry_events)

    for attempt in range(1, policy.max_attempts + 1):
        if not pending:
            break
        requested = list(pending)
        pending = []
        pages_by_url: dict[str, CrawlPage] = {}
        duplicate_urls: set[str] = set()
        unexpected_urls: set[str] = set()
        fetch_error: str | None = None
        try:
            results = await fetch_many(requested)
            for page in results:
                if page.url not in requested:
                    unexpected_urls.add(page.url)
                elif page.url in pages_by_url:
                    duplicate_urls.add(page.url)
                else:
                    pages_by_url[page.url] = page
        except (TimeoutError, OSError) as exc:
            fetch_error = type(exc).__name__

        for url in sorted(unexpected_urls):
            safe_url = url if is_official_url(url) else "<untrusted-result-url>"
            terminal_failures[safe_url] = {
                "requested_url": safe_url,
                "error": "unexpected_result",
            }

        retry_delays: list[float] = []
        for url in requested:
            if url in duplicate_urls:
                terminal_failures[url] = {
                    "requested_url": url,
                    "error": "duplicate_result",
                }
                continue
            page = pages_by_url.get(url)
            retryable = fetch_error is not None or page is None or (
                not page.success and page.status in _RETRYABLE_STATUS_CODES
            )
            if not retryable:
                if page is not None:
                    terminal_pages[url] = page
                else:
                    terminal_failures[url] = {
                        "requested_url": url,
                        "error": "missing_result",
                    }
                continue

            if attempt >= policy.max_attempts:
                if page is not None:
                    terminal_pages[url] = page
                else:
                    terminal_failures[url] = {
                        "requested_url": url,
                        "error": fetch_error or "missing_result",
                    }
                continue

            delay = _retry_delay(page, attempt, policy)
            event: dict[str, object] = {
                "requested_url": url,
                "attempt": attempt,
            }
            if page is not None:
                event["status"] = page.status
            else:
                event["error"] = fetch_error or "missing_result"
            event["delay_seconds"] = delay
            checkpoint.retry_events.append(event)
            retry_delays.append(delay)
            pending.append(url)

        if retry_delays:
            await _sleep(max(retry_delays), policy)

    ordered_pages = tuple(terminal_pages[url] for url in urls if url in terminal_pages)
    ordered_failures = tuple(
        terminal_failures[url] for url in urls if url in terminal_failures
    ) + tuple(
        terminal_failures[url]
        for url in sorted(terminal_failures)
        if url not in urls
    )
    return CrawlBatchResult(
        pages=ordered_pages,
        failures=ordered_failures,
        retry_events=tuple(checkpoint.retry_events[event_start:]),
    )


def normalize_markdown(value: object) -> str:
    text = re.sub(r"\n{3,}", "\n\n", str(value or "").strip())
    return text + "\n" if text else ""


def _h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _soft_error_marker(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip().lower()).strip(" .!|:-")


def _semantic_soft_error(title: object, body: str) -> str | None:
    markers = {_soft_error_marker(title), _soft_error_marker(_h1(body))}
    sample = body[:2000].lower()

    soft_404_markers = {
        "404",
        "404 page not found",
        "404 - page not found",
        "error 404",
        "page not found",
        "not found",
    }
    if markers & soft_404_markers and re.search(
        r"(?:page|resource).{0,40}(?:could not be found|does not exist|not found)",
        sample,
    ):
        return "soft_404"

    if markers & {"sign in", "log in", "login", "authentication required"} and re.search(
        r"(?:sign in|log in).{0,60}(?:continue|access)|enter your password",
        sample,
    ):
        return "soft_login"

    if markers & {
        "just a moment",
        "verify you are human",
        "attention required",
    } and re.search(
        r"checking your browser|verify you are human|cloudflare|captcha",
        sample,
    ):
        return "soft_anti_bot"

    if markers & {
        "500",
        "500 internal server error",
        "internal server error",
        "bad gateway",
        "service unavailable",
    } and re.search(
        r"server.{0,40}(?:error|unavailable)|bad gateway|try again later",
        sample,
    ):
        return "soft_server_error"
    return None


class _UnsafeOutputPath(RuntimeError):
    pass


_DIRECTORY_OPEN_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_READ_FLAGS = (
    os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
)


def _relative_parts(relative_path: Path) -> tuple[str, ...]:
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or ".." in relative_path.parts
        or "." in relative_path.parts
        or any("/" in part or "\x00" in part for part in relative_path.parts)
    ):
        raise _UnsafeOutputPath("unsafe relative output path")
    return tuple(relative_path.parts)


def _open_root_fd(root: Path, *, create: bool) -> int:
    root = Path(root)
    if create:
        if root.is_symlink():
            raise _UnsafeOutputPath("output root must not be a symlink")
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise _UnsafeOutputPath("cannot create output root") from error
    try:
        descriptor = os.open(root, _DIRECTORY_OPEN_FLAGS)
    except OSError as error:
        raise _UnsafeOutputPath("cannot safely open output root") from error
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise _UnsafeOutputPath("output root is not a directory")
    return descriptor


def _open_parent_fd(
    root_fd: int, parent_parts: tuple[str, ...], *, create: bool
) -> int:
    current = os.dup(root_fd)
    try:
        for part in parent_parts:
            if create:
                try:
                    os.mkdir(part, mode=0o755, dir_fd=current)
                except FileExistsError:
                    pass
            try:
                following = os.open(part, _DIRECTORY_OPEN_FLAGS, dir_fd=current)
            except OSError as error:
                raise _UnsafeOutputPath(
                    "output directory cannot be opened without following symlinks"
                ) from error
            os.close(current)
            current = following
        return current
    except BaseException:
        os.close(current)
        raise


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _directory_identity_is_current(
    root: Path,
    root_fd: int,
    parent_parts: tuple[str, ...],
    parent_fd: int,
) -> bool:
    try:
        current_root = _open_root_fd(root, create=False)
        try:
            if not _same_inode(os.fstat(root_fd), os.fstat(current_root)):
                return False
            current_parent = _open_parent_fd(
                current_root, parent_parts, create=False
            )
            try:
                return _same_inode(os.fstat(parent_fd), os.fstat(current_parent))
            finally:
                os.close(current_parent)
        finally:
            os.close(current_root)
    except _UnsafeOutputPath:
        return False


def _read_fd(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _secure_read(
    root: Path, relative_path: Path, *, missing_ok: bool = False
) -> bytes | None:
    parts = _relative_parts(relative_path)
    root_fd = _open_root_fd(root, create=True)
    try:
        try:
            parent_fd = _open_parent_fd(root_fd, parts[:-1], create=False)
        except _UnsafeOutputPath:
            if missing_ok:
                return None
            raise
        try:
            try:
                descriptor = os.open(parts[-1], _FILE_READ_FLAGS, dir_fd=parent_fd)
            except FileNotFoundError:
                if missing_ok:
                    return None
                raise
            except OSError as error:
                raise _UnsafeOutputPath("output file cannot be opened safely") from error
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise _UnsafeOutputPath("output target is not a regular file")
                data = _read_fd(descriptor)
            finally:
                os.close(descriptor)
            if not _directory_identity_is_current(
                Path(root), root_fd, parts[:-1], parent_fd
            ):
                raise _UnsafeOutputPath("output directory identity changed")
            return data
        finally:
            os.close(parent_fd)
    finally:
        os.close(root_fd)


def _atomic_write(root: Path, relative_path: Path, data: bytes) -> None:
    parts = _relative_parts(relative_path)
    root_fd = _open_root_fd(root, create=True)
    parent_fd = _open_parent_fd(root_fd, parts[:-1], create=True)
    temporary_name = f".{parts[-1]}.{secrets.token_hex(8)}.tmp"
    temporary_exists = False
    try:
        try:
            existing = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise _UnsafeOutputPath("output target is not a regular file")

        flags = (
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(
            temporary_name, flags, 0o600, dir_fd=parent_fd
        )
        temporary_exists = True
        try:
            remaining = memoryview(data)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("short atomic write")
                remaining = remaining[written:]
            os.fsync(descriptor)
            stored = _read_fd(descriptor)
            if sha256_bytes(stored) != sha256_bytes(data):
                raise OSError("atomic write verification failed")
        finally:
            os.close(descriptor)

        os.replace(
            temporary_name,
            parts[-1],
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        temporary_exists = False
        os.fsync(parent_fd)
        if not _directory_identity_is_current(
            Path(root), root_fd, parts[:-1], parent_fd
        ):
            try:
                os.unlink(parts[-1], dir_fd=parent_fd)
                os.fsync(parent_fd)
            except FileNotFoundError:
                pass
            raise _UnsafeOutputPath("output directory identity changed")

        final_descriptor = os.open(
            parts[-1], _FILE_READ_FLAGS, dir_fd=parent_fd
        )
        try:
            final_stat = os.fstat(final_descriptor)
            if not stat.S_ISREG(final_stat.st_mode):
                raise _UnsafeOutputPath("output target is not a regular file")
            final_data = _read_fd(final_descriptor)
            if len(final_data) != len(data) or sha256_bytes(
                final_data
            ) != sha256_bytes(data):
                raise OSError("stored content mismatch")
        finally:
            os.close(final_descriptor)
    finally:
        if temporary_exists:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)
        os.close(root_fd)


def _secure_unlink(root: Path, relative_path: Path) -> None:
    parts = _relative_parts(relative_path)
    root_fd = _open_root_fd(root, create=True)
    try:
        try:
            parent_fd = _open_parent_fd(root_fd, parts[:-1], create=False)
        except _UnsafeOutputPath:
            return
        try:
            try:
                target = os.stat(
                    parts[-1], dir_fd=parent_fd, follow_symlinks=False
                )
            except FileNotFoundError:
                return
            if stat.S_ISDIR(target.st_mode):
                raise _UnsafeOutputPath("refusing to remove output directory")
            os.unlink(parts[-1], dir_fd=parent_fd)
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        os.close(root_fd)


def _checkpoint_payload(checkpoint: CrawlCheckpoint) -> dict:
    return {
        "snapshot_id": checkpoint.snapshot_id,
        "completed": checkpoint.completed,
        "retry_events": checkpoint.retry_events,
        "complete": checkpoint.complete,
    }


def _write_checkpoint(root: Path, checkpoint: CrawlCheckpoint) -> None:
    payload = _checkpoint_payload(checkpoint)
    if contains_sensitive_data(payload):
        raise RuntimeError("checkpoint contains sensitive data")
    try:
        _atomic_write(Path(root), Path("checkpoint.json"), stable_json_bytes(payload))
    except _UnsafeOutputPath as error:
        raise RuntimeError("unsafe checkpoint path") from error


def _load_checkpoint(root: Path, snapshot_id: str) -> CrawlCheckpoint:
    try:
        raw = _secure_read(
            Path(root), Path("checkpoint.json"), missing_ok=True
        )
    except _UnsafeOutputPath as error:
        raise RuntimeError("unsafe checkpoint path") from error
    if raw is None:
        return CrawlCheckpoint(snapshot_id=snapshot_id)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("invalid checkpoint") from error
    if contains_sensitive_data(payload):
        raise RuntimeError("checkpoint contains sensitive data")
    if not isinstance(payload, Mapping) or payload.get("snapshot_id") != snapshot_id:
        return CrawlCheckpoint(snapshot_id=snapshot_id)
    completed = payload.get("completed")
    retry_events = payload.get("retry_events")
    complete = payload.get("complete")
    if (
        not isinstance(completed, dict)
        or not isinstance(retry_events, list)
        or not isinstance(complete, bool)
        or not all(
            isinstance(key, str) and isinstance(value, dict)
            for key, value in completed.items()
        )
        or not all(isinstance(event, dict) for event in retry_events)
    ):
        raise RuntimeError("invalid checkpoint")
    return CrawlCheckpoint(
        snapshot_id=snapshot_id,
        completed=completed,
        retry_events=retry_events,
        complete=complete,
    )


def _verified_checkpoint_document(
    root: Path, url: str, snapshot_id: str, payload: object
) -> DocumentRecord | None:
    if not isinstance(payload, dict):
        return None
    try:
        document = DocumentRecord(**payload)
        expected_path = output_path_for_url(url)
        if (
            document.logical_key != url
            or document.requested_url != url
            or document.output_path != expected_path.as_posix()
            or document.source_kind != "website"
            or document.website_snapshot_id != snapshot_id
            or not _is_official_website_url(document.final_url)
            or document.http_status != 200
            or document.document_id
            != document_id_for("website", url, document.content_sha256)
        ):
            return None
        body = _secure_read(root, expected_path, missing_ok=True)
        if body is None:
            return None
        if len(body) != document.byte_length:
            return None
        if sha256_bytes(body) != document.content_sha256:
            return None
        text = body.decode("utf-8")
        navigation_only = url.rstrip("/").endswith("/search")
        if (
            normalize_markdown(text) != text
            or contains_secret(text)
            or contains_sensitive_data(
                {"title": document.title, "mime_type": document.mime_type}
            )
            or document.text_length != len(text)
            or (len(text.strip()) < 200 and not navigation_only)
            or _semantic_soft_error(document.title, text) is not None
            or document.semantic_status
            != ("navigation_only" if navigation_only else "content")
            or document.h1 != _h1(text)
        ):
            return None
        return document
    except (TypeError, ValueError, OSError, UnicodeError, _UnsafeOutputPath):
        return None


def _safe_failure_error(page: CrawlPage) -> str:
    if (
        page.error
        and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", page.error)
        and not contains_sensitive_data(page.error)
    ):
        return page.error
    return f"http_{page.status}"


def _remove_rejected_output(root: Path, relative_path: Path) -> None:
    try:
        _secure_unlink(root, relative_path)
    except _UnsafeOutputPath:
        return


def _document_for_page(
    url: str,
    page: CrawlPage,
    body: str,
    snapshot_id: str,
    relative_path: Path,
    previous: SnapshotManifest | None,
) -> DocumentRecord:
    raw = body.encode("utf-8")
    content_sha256 = sha256_bytes(raw)
    prior = next(
        (
            item
            for item in (previous.documents if previous else [])
            if item.logical_key == url
        ),
        None,
    )
    document_id = document_id_for("website", url, content_sha256)
    return DocumentRecord(
        document_id=document_id,
        source_kind="website",
        requested_url=url,
        final_url=page.final_url,
        output_path=relative_path.as_posix(),
        content_sha256=content_sha256,
        byte_length=len(raw),
        text_length=len(body),
        semantic_status=(
            "navigation_only" if url.rstrip("/").endswith("/search") else "content"
        ),
        http_status=page.status,
        title=page.title,
        h1=_h1(body),
        website_snapshot_id=snapshot_id,
        mime_type=page.mime_type,
        logical_key=url,
        supersedes_document_id=(
            prior.document_id if prior and prior.document_id != document_id else None
        ),
        is_skill="/skills/" in url,
        is_runtime_contract="/developer-guide/" in url,
    )


async def crawl_website(
    urls: list[str],
    fetch_many: Callable[[list[str]], Awaitable[list[CrawlPage]]],
    snapshot_id: str,
    out_root: Path,
    fetched_at: str,
    discovery_sha256: str | None = None,
    previous: SnapshotManifest | None = None,
    retry_events: list[dict] | None = None,
    policy: RetryPolicy | None = None,
) -> SnapshotManifest:
    if len(urls) != len(set(urls)):
        raise ValueError("website URLs must be unique")
    output_paths = _output_paths_for_urls(urls)
    expected = list(urls)
    active_policy = policy or RetryPolicy()
    checkpoint = _load_checkpoint(Path(out_root), snapshot_id)
    if retry_events and not checkpoint.retry_events:
        checkpoint.retry_events.extend(retry_events)
    checkpoint.complete = False
    _write_checkpoint(Path(out_root), checkpoint)

    documents_by_url: dict[str, DocumentRecord] = {}
    failures: list[dict] = []
    for url in expected:
        checkpoint_entry = checkpoint.completed.get(url)
        resumed = _verified_checkpoint_document(
            Path(out_root), url, snapshot_id, checkpoint_entry
        )
        if resumed is not None:
            documents_by_url[url] = resumed
        else:
            if checkpoint_entry is not None:
                _remove_rejected_output(Path(out_root), output_paths[url])
            checkpoint.completed.pop(url, None)

    pending = [url for url in expected if url not in documents_by_url]
    fetch_batch_size = min(active_policy.batch_size, active_policy.max_concurrency)
    try:
        for offset in range(0, len(pending), fetch_batch_size):
            batch = pending[offset : offset + fetch_batch_size]
            batch_result = await fetch_with_bounded_retry(
                batch, fetch_many, active_policy, checkpoint
            )
            failures.extend(batch_result.failures)
            pages_by_url = {page.url: page for page in batch_result.pages}
            failed_urls = {
                row.get("requested_url")
                for row in batch_result.failures
                if isinstance(row, dict)
            }
            for url in batch:
                if url in failed_urls:
                    continue
                page = pages_by_url.get(url)
                if page is None:
                    failures.append({"requested_url": url, "error": "missing_result"})
                    continue
                if not _is_official_website_url(page.final_url):
                    failures.append(
                        {"requested_url": url, "error": "cross_origin_redirect"}
                    )
                    continue
                if not page.success or page.status != 200:
                    failures.append(
                        {"requested_url": url, "error": _safe_failure_error(page)}
                    )
                    continue
                if contains_sensitive_data(
                    {"title": page.title, "mime_type": page.mime_type}
                ):
                    failures.append(
                        {
                            "requested_url": url,
                            "error": "suspected_secret_metadata",
                        }
                    )
                    continue

                body = normalize_markdown(page.markdown)
                navigation_only = url.rstrip("/").endswith("/search")
                if contains_secret(body):
                    failures.append({"requested_url": url, "error": "suspected_secret"})
                    continue
                semantic_error = _semantic_soft_error(page.title, body)
                if semantic_error is not None:
                    failures.append(
                        {"requested_url": url, "error": semantic_error}
                    )
                    continue
                if len(body.strip()) < 200 and not navigation_only:
                    failures.append({"requested_url": url, "error": "short_content"})
                    continue

                relative_path = output_paths[url]
                raw = body.encode("utf-8")
                try:
                    _atomic_write(Path(out_root), relative_path, raw)
                    stored = _secure_read(Path(out_root), relative_path)
                except _UnsafeOutputPath:
                    failures.append(
                        {"requested_url": url, "error": "unsafe_output_path"}
                    )
                    continue
                if (
                    stored is None
                    or len(stored) != len(raw)
                    or sha256_bytes(stored) != sha256_bytes(raw)
                ):
                    failures.append(
                        {"requested_url": url, "error": "stored_content_mismatch"}
                    )
                    continue
                document = _document_for_page(
                    url,
                    page,
                    body,
                    snapshot_id,
                    relative_path,
                    previous,
                )
                documents_by_url[url] = document
                checkpoint.completed[url] = asdict(document)
            _write_checkpoint(Path(out_root), checkpoint)
    except BaseException:
        checkpoint.complete = False
        _write_checkpoint(Path(out_root), checkpoint)
        raise

    verified_documents: dict[str, DocumentRecord] = {}
    for url, document in documents_by_url.items():
        try:
            body = _secure_read(
                Path(out_root), output_paths[url], missing_ok=True
            )
            matches = (
                body is not None
                and len(body) == document.byte_length
                and sha256_bytes(body) == document.content_sha256
            )
        except (OSError, _UnsafeOutputPath):
            matches = False
        if matches:
            verified_documents[url] = document
        else:
            checkpoint.completed.pop(url, None)
            if not any(row.get("requested_url") == url for row in failures):
                failures.append(
                    {"requested_url": url, "error": "stored_content_mismatch"}
                )

    checkpoint.complete = True
    _write_checkpoint(Path(out_root), checkpoint)
    documents = [
        verified_documents[url] for url in expected if url in verified_documents
    ]
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        source_kind="website",
        source_origin="https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        requested_ref="sitemap",
        resolved_sha=None,
        release_tag=None,
        fetched_at=fetched_at,
        crawler_version="1",
        documents=documents,
        failures=failures,
        previous_snapshot_id=previous.snapshot_id if previous else None,
        discovery_sha256=discovery_sha256,
        expected_document_count=len(expected),
        retry_events=list(checkpoint.retry_events),
    )
