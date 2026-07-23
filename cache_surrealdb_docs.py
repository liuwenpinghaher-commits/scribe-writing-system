#!/usr/bin/env python3
"""Discover and cache SurrealDB documentation pages as Markdown."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


ROOT = "https://surrealdb.com"
DOCS_SITEMAP = f"{ROOT}/docs/sitemap.xml"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "surrealdb-docs-cache")


def get(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 documentation-archiver/1.0"})
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def sitemap_urls() -> list[str]:
    xml = get(DOCS_SITEMAP)
    return sorted(set(re.findall(r"<loc>([^<]+)</loc>", xml)))


def spectron_urls() -> list[str]:
    """Walk rendered/static HTML links because the current sitemap omits Spectron."""
    start = f"{ROOT}/docs/spectron"
    seen: set[str] = set()
    queue = deque([start])
    while queue:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            html = get(url)
        except Exception as exc:
            print(f"DISCOVERY_FAIL {url}: {exc}", file=sys.stderr)
            continue
        candidates = re.findall(r"(?:href|path)=[\"']((?:\\?/)?docs\\?/spectron[^\"']*)", html)
        candidates += re.findall(r"\\?/docs\\?/spectron(?:[/\\][A-Za-z0-9._~-]+)*", html)
        for raw in candidates:
            raw = raw.replace("\\/", "/").replace("\\", "")
            if not re.fullmatch(r"/?docs/spectron(?:/[A-Za-z0-9._~-]+)*", raw):
                continue
            if raw.startswith("/"):
                candidate = urljoin(ROOT, raw)
            else:
                candidate = urljoin(ROOT + "/", raw)
            parsed = urlparse(candidate)
            candidate = candidate.split("#", 1)[0].split("?", 1)[0].rstrip("/") or ROOT
            if parsed.netloc == "surrealdb.com" and parsed.path.startswith("/docs/spectron"):
                if candidate not in seen:
                    queue.append(candidate)
    return sorted(seen)


def file_for(url: str) -> Path:
    path = urlparse(url).path.rstrip("/")
    relative = path.lstrip("/")
    return OUT / (relative + "/index.md" if path in {"/docs", "/docs/spectron"} else relative + ".md")


async def crawl(urls: list[str]) -> tuple[list[dict], list[dict]]:
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        remove_overlay_elements=True,
        wait_until="domcontentloaded",
        page_timeout=30000,
        screenshot=False,
    )
    success: list[dict] = []
    failed: list[dict] = []
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        results = await crawler.arun_many(urls=urls, config=config, max_concurrent=16)
    fetched = datetime.now(timezone.utc).isoformat()
    for url, result in zip(urls, results):
        if not result.success:
            failed.append({"url": url, "error": result.error_message})
            print(f"FAIL {url}: {result.error_message}")
            continue
        target = file_for(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        title = (result.metadata or {}).get("title") or url
        body = str(result.markdown).strip()
        target.write_text(f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\nurl: {url}\nfetched_at: {fetched}\n---\n\n{body}\n", encoding="utf-8")
        success.append({"url": url, "title": title, "file": str(target.relative_to(OUT))})
        print(f"OK   {url}")
    return success, failed


def main() -> int:
    docs = sitemap_urls()
    spectron = spectron_urls()
    urls = sorted(set(docs + spectron))
    OUT.mkdir(parents=True, exist_ok=True)
    discovery = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sitemaps": [DOCS_SITEMAP],
        "docs_count": len(docs),
        "spectron_count": len(spectron),
        "url_count": len(urls),
        "urls": urls,
    }
    (OUT / "_discovery.json").write_text(json.dumps(discovery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discovered {len(docs)} docs + {len(spectron)} Spectron = {len(urls)} unique URLs")
    success, failed = asyncio.run(crawl(urls))
    summary = {"success_count": len(success), "failed_count": len(failed), "success": success, "failed": failed}
    (OUT / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Summary: {len(success)} OK, {len(failed)} failed")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
