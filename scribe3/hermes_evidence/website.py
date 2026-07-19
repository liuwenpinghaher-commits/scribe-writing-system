from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .models import sha256_bytes
from .policy import is_official_url

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
        if name != "url":
            continue
        if namespace != root_namespace:
            raise ValueError("Sitemap URL element has an invalid namespace")
        url_nodes.append(child)
    if not url_nodes:
        raise ValueError("Sitemap must contain direct URL elements")

    urls = set()
    for url_node in url_nodes:
        loc_nodes = []
        for child in url_node:
            namespace, name = _tag_parts(child.tag)
            if name != "loc":
                continue
            if namespace != root_namespace:
                raise ValueError("Sitemap loc element has an invalid namespace")
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
