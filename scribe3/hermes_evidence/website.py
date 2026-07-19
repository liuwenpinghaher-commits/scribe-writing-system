from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .models import sha256_bytes
from .policy import is_official_url


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
    if not root.tag.endswith("urlset"):
        raise ValueError("Sitemap root must be a urlset")

    urls = {node.text.strip() for node in root.iter() if node.tag.endswith("loc") and node.text and node.text.strip()}
    invalid = sorted(url for url in urls if not is_official_url(url))
    if invalid:
        raise ValueError(f"Sitemap contains non-official URL(s): {len(invalid)}")
    return sorted(urls)


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
    if not is_official_url(url):
        raise ValueError("non-official website URL")
    parts = [part for part in urlparse(url).path.split("/") if part]
    if parts and parts[0] == "docs":
        parts = parts[1:]
    if not parts:
        return Path("pages/index.md")
    return Path("pages", *(_slug(part) for part in parts[:-1]), f"{_slug(parts[-1])}.md")
