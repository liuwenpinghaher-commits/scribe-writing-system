#!/usr/bin/env python3
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


ROOT = Path(__file__).resolve().parent
URLS_FILE = ROOT / "urls.txt"
OUT_ROOT = ROOT / "pages"
SUMMARY_FILE = ROOT / "_summary.json"
INDEX_FILE = ROOT / "_index.md"
SOURCE_SITEMAP = "https://hermes-agent.nousresearch.com/docs/sitemap.xml"


def slug_part(value: str) -> str:
    value = value.strip("/") or "index"
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    return value.strip("-") or "index"


def output_path(url: str) -> Path:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if parts and parts[0] == "docs":
        parts = parts[1:]
    if not parts:
        return OUT_ROOT / "index.md"
    *dirs, leaf = parts
    return OUT_ROOT.joinpath(*(slug_part(p) for p in dirs), f"{slug_part(leaf)}.md")


def normalize_markdown(markdown: object) -> str:
    text = str(markdown or "").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text + "\n" if text else ""


def title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return re.sub(r"\s*\[.*?\]\(.*?\)\s*$", "", match.group(1)).strip() or fallback
    return fallback


def front_matter(title: str, url: str, crawled_at: str) -> str:
    clean_title = (title or url).replace("\n", " ").strip()
    return (
        "---\n"
        f"title: {json.dumps(clean_title, ensure_ascii=False)}\n"
        f"url: {json.dumps(url, ensure_ascii=False)}\n"
        "source: \"Hermes Agent Docs\"\n"
        f"crawled_at: {json.dumps(crawled_at)}\n"
        "---\n\n"
        f"Source: {url}\n\n"
    )


def load_urls() -> list[str]:
    urls = []
    for line in URLS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return list(dict.fromkeys(urls))


def write_summary(crawled_at: str, urls: list[str], success: list[dict], failed: list[dict]) -> None:
    SUMMARY_FILE.write_text(json.dumps({
        "source_sitemap": SOURCE_SITEMAP,
        "crawled_at": crawled_at,
        "url_count": len(urls),
        "success_count": len(success),
        "failed_count": len(failed),
        "success": success,
        "failed": failed,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


async def crawl_one(crawler: AsyncWebCrawler, url: str, config: CrawlerRunConfig):
    result = await crawler.arun(url=url, config=config)
    return result


async def crawl_all(max_concurrent: int = 5) -> int:
    urls = load_urls()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    crawled_at = datetime.now(timezone.utc).isoformat()
    browser_config = BrowserConfig(headless=True, verbose=False)
    primary_config = CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        remove_overlay_elements=True,
        wait_until="domcontentloaded",
        delay_before_return_html=1.0,
        page_timeout=30000,
        css_selector=".theme-doc-markdown",
        screenshot=False,
    )
    fallback_config = CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        remove_overlay_elements=True,
        wait_until="domcontentloaded",
        delay_before_return_html=1.0,
        page_timeout=30000,
        css_selector="main",
        screenshot=False,
    )

    success = []
    failed = []
    print(f"Batch crawling {len(urls)} Hermes Agent docs URL(s), max {max_concurrent} concurrent", flush=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for start in range(0, len(urls), 40):
            chunk = urls[start:start + 40]
            print(f"Chunk {start + 1}-{start + len(chunk)} / {len(urls)}", flush=True)
            results = await crawler.arun_many(
                urls=chunk,
                config=primary_config,
                max_concurrent=max_concurrent,
            )
            for result in results:
                url = result.url
                body = normalize_markdown(result.markdown) if result.success else ""
                used_fallback = False
                if (not result.success) or len(body) < 80:
                    retry = await crawl_one(crawler, url, fallback_config)
                    used_fallback = True
                    result = retry
                    body = normalize_markdown(result.markdown) if result.success else ""

                if not result.success or not body:
                    error = result.error_message or "empty markdown"
                    failed.append({"url": url, "error": error})
                    print(f"FAIL {url}: {error}", flush=True)
                    continue

                metadata_title = (result.metadata or {}).get("title") or url
                title = title_from_markdown(body, metadata_title)
                path = output_path(url)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(front_matter(title, url, crawled_at) + body, encoding="utf-8")
                rel = path.relative_to(ROOT).as_posix()
                success.append({
                    "url": url,
                    "title": title,
                    "file": rel,
                    "fallback": used_fallback,
                })
                marker = "OK/F" if used_fallback else "OK  "
                print(f"{marker} {url} -> {rel}", flush=True)

            write_summary(crawled_at, urls, success, failed)

    index_lines = [
        "# Hermes Agent Docs Markdown Export",
        "",
        f"- Source sitemap: {SOURCE_SITEMAP}",
        f"- Crawled at: {crawled_at}",
        f"- Success: {len(success)}",
        f"- Failed: {len(failed)}",
        "",
        "## Pages",
        "",
    ]
    for item in success:
        index_lines.append(f"- [{item['title']}]({item['file']}) - {item['url']}")
    if failed:
        index_lines.extend(["", "## Failed", ""])
        for item in failed:
            index_lines.append(f"- {item['url']} - {item['error']}")
    INDEX_FILE.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    write_summary(crawled_at, urls, success, failed)

    print(f"Summary: {len(success)} OK, {len(failed)} failed", flush=True)
    print(f"Markdown root: {OUT_ROOT}", flush=True)
    print(f"Index: {INDEX_FILE}", flush=True)
    print(f"Summary JSON: {SUMMARY_FILE}", flush=True)
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(crawl_all()))
