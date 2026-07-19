import asyncio
from pathlib import Path

import pytest

from scribe3.hermes_evidence.policy import (
    classify_repo_path,
    contains_secret,
    is_official_url,
    select_repo_document,
)
from scribe3.hermes_evidence.website import discover_sitemap, output_path_for_url


def test_website_batch_uses_returned_url_not_request_order(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    body_a = "# A\n" + ("body a " * 40)
    body_b = "# B\n" + ("body b " * 40)

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=urls[1],
                final_url=urls[1],
                status=200,
                success=True,
                markdown=body_b,
                title="B",
                mime_type="text/html",
            ),
            CrawlPage(
                url=urls[0],
                final_url=urls[0],
                status=200,
                success=True,
                markdown=body_a,
                title="A",
                mime_type="text/html",
            ),
        ]

    urls = [
        "https://hermes-agent.nousresearch.com/docs/a",
        "https://hermes-agent.nousresearch.com/docs/b",
    ]
    manifest = asyncio.run(
        crawl_website(
            urls,
            fake_fetch,
            "website-test",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )
    )

    assert (tmp_path / "pages/a.md").read_text() == body_a.strip() + "\n"
    assert (tmp_path / "pages/b.md").read_text() == body_b.strip() + "\n"
    assert not manifest.failures


def test_website_crawl_rejects_output_path_collision_before_fetch(tmp_path):
    from scribe3.hermes_evidence.website import RetryPolicy, crawl_website

    urls = [
        "https://hermes-agent.nousresearch.com/docs/a?lang=en",
        "https://hermes-agent.nousresearch.com/docs/a?lang=zh",
    ]

    async def must_not_fetch(batch):
        pytest.fail("colliding output paths reached the fetch adapter")

    with pytest.raises(ValueError, match="output path collision"):
        asyncio.run(
            crawl_website(
                urls,
                must_not_fetch,
                "collision-test",
                tmp_path,
                "2026-07-20T00:00:00+00:00",
                policy=RetryPolicy(sleep=lambda delay: None),
            )
        )
    assert not any(tmp_path.iterdir())


def test_website_crawl_reverifies_manifest_files_before_completion(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, RetryPolicy, crawl_website

    urls = [
        "https://hermes-agent.nousresearch.com/docs/a",
        "https://hermes-agent.nousresearch.com/docs/b",
    ]
    calls = 0

    def page(url):
        return CrawlPage(
            url=url,
            final_url=url,
            status=200,
            success=True,
            markdown="# Page\n" + ("public documentation " * 20),
            title="Page",
            mime_type="text/html",
        )

    async def mutating_fetch(batch):
        nonlocal calls
        calls += 1
        if calls == 2:
            saved = tmp_path / "pages/a.md"
            saved.write_text(
                "Authorization: Bearer " + ("x" * 40) + (" hidden" * 30),
                encoding="utf-8",
            )
        return [page(url) for url in batch]

    manifest = asyncio.run(
        crawl_website(
            urls,
            mutating_fetch,
            "manifest-reverify",
            tmp_path,
            "2026-07-20T00:00:00+00:00",
            policy=RetryPolicy(
                max_concurrency=1,
                sleep=lambda delay: None,
            ),
        )
    )

    assert [document.logical_key for document in manifest.documents] == [urls[1]]
    assert manifest.failures == [
        {"requested_url": urls[0], "error": "stored_content_mismatch"}
    ]
    assert not (tmp_path / "pages/a.md").exists()


def test_website_crawl_removes_immediate_mismatch_pollution(tmp_path, monkeypatch):
    import scribe3.hermes_evidence.website as website

    url = "https://hermes-agent.nousresearch.com/docs/immediate-mismatch"
    relative_path = Path("pages/immediate-mismatch.md")
    real_secure_read = website._secure_read
    corrupted = False

    def corrupting_read(root, candidate, *, missing_ok=False):
        nonlocal corrupted
        if candidate == relative_path and not corrupted:
            corrupted = True
            (Path(root) / candidate).write_text(
                "Cookie: session=" + ("x" * 40) + (" hidden" * 30),
                encoding="utf-8",
            )
        return real_secure_read(root, candidate, missing_ok=missing_ok)

    monkeypatch.setattr(website, "_secure_read", corrupting_read)

    async def fake_fetch(urls):
        return [
            website.CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown="# Safe\n" + ("public documentation " * 20),
                title="Safe",
                mime_type="text/html",
            )
        ]

    manifest = asyncio.run(
        website.crawl_website(
            [url],
            fake_fetch,
            "immediate-mismatch",
            tmp_path,
            "2026-07-20T00:00:00+00:00",
        )
    )

    assert corrupted
    assert manifest.documents == []
    assert manifest.failures == [
        {"requested_url": url, "error": "stored_content_mismatch"}
    ]
    assert not (tmp_path / relative_path).exists()


def test_website_retry_after_wins_and_events_are_sanitized():
    from scribe3.hermes_evidence.models import contains_sensitive_data
    from scribe3.hermes_evidence.website import (
        CrawlCheckpoint,
        CrawlPage,
        RetryPolicy,
        fetch_with_bounded_retry,
    )

    url = "https://hermes-agent.nousresearch.com/docs/retry-after"
    calls = []
    slept = []

    async def fake_fetch(urls):
        calls.append(list(urls))
        if len(calls) == 1:
            return [
                CrawlPage(
                    url=url,
                    final_url=url,
                    status=429,
                    success=False,
                    markdown="Authorization: Bearer must-not-be-persisted",
                    title="",
                    mime_type="text/html",
                    error="response body must-not-be-persisted",
                    retry_after="2",
                )
            ]
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown="# Ready\n" + ("content " * 40),
                title="Ready",
                mime_type="text/html",
            )
        ]

    checkpoint = CrawlCheckpoint(snapshot_id="retry")
    result = asyncio.run(
        fetch_with_bounded_retry(
            [url],
            fake_fetch,
            RetryPolicy(sleep=slept.append, jitter=lambda delay: 999),
            checkpoint,
        )
    )

    assert [page.status for page in result.pages] == [200]
    assert calls == [[url], [url]]
    assert slept == [2.0]
    assert checkpoint.retry_events == list(result.retry_events)
    assert result.retry_events == (
        {
            "requested_url": url,
            "attempt": 1,
            "status": 429,
            "delay_seconds": 2.0,
        },
    )
    assert not contains_sensitive_data(result.retry_events)


@pytest.mark.parametrize("unsafe_retry_after", ["31", "inf", "nan"])
def test_website_retry_after_has_independent_server_limit(unsafe_retry_after):
    from scribe3.hermes_evidence.website import (
        CrawlCheckpoint,
        CrawlPage,
        RetryPolicy,
        fetch_with_bounded_retry,
    )

    url = "https://hermes-agent.nousresearch.com/docs/server-retry-limit"

    def page(status, retry_after):
        return CrawlPage(
            url=url,
            final_url=url,
            status=status,
            success=status == 200,
            markdown="# Ready\n" + ("public documentation " * 20),
            title="Ready",
            mime_type="text/html",
            retry_after=retry_after,
        )

    honored_sleeps = []
    honored_calls = 0

    async def honored_fetch(urls):
        nonlocal honored_calls
        honored_calls += 1
        return [page(429, "20") if honored_calls == 1 else page(200, None)]

    policy = RetryPolicy(
        base_delay=1,
        max_delay=2,
        max_retry_after=30,
        jitter=lambda delay: 0,
        sleep=honored_sleeps.append,
    )
    asyncio.run(
        fetch_with_bounded_retry(
            [url], honored_fetch, policy, CrawlCheckpoint(snapshot_id="honored")
        )
    )
    assert honored_sleeps == [20.0]

    bounded_sleeps = []
    bounded_calls = 0

    async def bounded_fetch(urls):
        nonlocal bounded_calls
        bounded_calls += 1
        return [
            page(429, unsafe_retry_after)
            if bounded_calls == 1
            else page(200, None)
        ]

    asyncio.run(
        fetch_with_bounded_retry(
            [url],
            bounded_fetch,
            RetryPolicy(
                base_delay=1,
                max_delay=2,
                max_retry_after=30,
                jitter=lambda delay: 0,
                sleep=bounded_sleeps.append,
            ),
            CrawlCheckpoint(snapshot_id="bounded"),
        )
    )
    assert bounded_sleeps == [1.0]


def test_website_retry_is_bounded_for_503_timeout_and_skips_404():
    from scribe3.hermes_evidence.website import (
        CrawlCheckpoint,
        CrawlPage,
        RetryPolicy,
        fetch_with_bounded_retry,
    )

    retry_url = "https://hermes-agent.nousresearch.com/docs/retry-503"
    timeout_url = "https://hermes-agent.nousresearch.com/docs/timeout"
    missing_url = "https://hermes-agent.nousresearch.com/docs/missing"
    slept = []
    calls_503 = 0

    async def retry_503(urls):
        nonlocal calls_503
        calls_503 += 1
        if calls_503 == 1:
            return [
                CrawlPage(
                    url=retry_url,
                    final_url=retry_url,
                    status=503,
                    success=False,
                    markdown="secret response body",
                    title="",
                    mime_type="text/html",
                )
            ]
        return [
            CrawlPage(
                url=retry_url,
                final_url=retry_url,
                status=200,
                success=True,
                markdown="# Ready\n" + ("content " * 40),
                title="Ready",
                mime_type="text/html",
            )
        ]

    policy = RetryPolicy(
        base_delay=2,
        max_delay=2.25,
        jitter=lambda delay: 0.25,
        sleep=slept.append,
    )
    retried = asyncio.run(
        fetch_with_bounded_retry(
            [retry_url], retry_503, policy, CrawlCheckpoint(snapshot_id="503")
        )
    )
    assert calls_503 == 2
    assert slept == [2.25]
    assert [page.status for page in retried.pages] == [200]

    timeout_calls = 0

    async def always_timeout(urls):
        nonlocal timeout_calls
        timeout_calls += 1
        raise TimeoutError("secret timeout detail")

    timeout = asyncio.run(
        fetch_with_bounded_retry(
            [timeout_url],
            always_timeout,
            RetryPolicy(sleep=lambda delay: None, jitter=lambda delay: 0),
            CrawlCheckpoint(snapshot_id="timeout"),
        )
    )
    assert timeout_calls == 3
    assert timeout.pages == ()
    assert timeout.failures == (
        {"requested_url": timeout_url, "error": "TimeoutError"},
    )
    assert len(timeout.retry_events) == 2

    not_found_calls = 0

    async def not_found(urls):
        nonlocal not_found_calls
        not_found_calls += 1
        return [
            CrawlPage(
                url=missing_url,
                final_url=missing_url,
                status=404,
                success=False,
                markdown="secret response body",
                title="",
                mime_type="text/html",
                error="secret error detail",
            )
        ]

    not_found_result = asyncio.run(
        fetch_with_bounded_retry(
            [missing_url],
            not_found,
            RetryPolicy(sleep=lambda delay: None),
            CrawlCheckpoint(snapshot_id="404"),
        )
    )
    assert not_found_calls == 1
    assert [page.status for page in not_found_result.pages] == [404]
    assert not not_found_result.retry_events


def test_website_exponential_backoff_stays_capped_on_every_retry():
    from scribe3.hermes_evidence.website import (
        CrawlCheckpoint,
        CrawlPage,
        RetryPolicy,
        fetch_with_bounded_retry,
    )

    url = "https://hermes-agent.nousresearch.com/docs/capped"
    slept = []

    async def unavailable(urls):
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=503,
                success=False,
                markdown="response body must not be recorded",
                title="",
                mime_type="text/html",
            )
        ]

    result = asyncio.run(
        fetch_with_bounded_retry(
            [url],
            unavailable,
            RetryPolicy(
                base_delay=2,
                max_delay=2.5,
                jitter=lambda delay: 1,
                sleep=slept.append,
            ),
            CrawlCheckpoint(snapshot_id="capped"),
        )
    )

    assert slept == [2.5, 2.5]
    assert [event["delay_seconds"] for event in result.retry_events] == [2.5, 2.5]
    assert [page.status for page in result.pages] == [503]


def test_website_retry_policy_caps_batch_and_concurrency():
    from scribe3.hermes_evidence.website import RetryPolicy

    policy = RetryPolicy()
    assert policy.max_attempts == 3
    assert policy.batch_size == 40
    assert policy.max_concurrency == 5
    assert RetryPolicy(max_concurrency=2).max_concurrency == 2
    with pytest.raises(ValueError, match="max_concurrency"):
        RetryPolicy(max_concurrency=6)
    with pytest.raises(ValueError, match="batch_size"):
        RetryPolicy(batch_size=41)


def test_website_retry_rejects_sensitive_url_before_fetch_or_event_recording():
    from scribe3.hermes_evidence.website import (
        CrawlCheckpoint,
        RetryPolicy,
        fetch_with_bounded_retry,
    )

    checkpoint = CrawlCheckpoint(snapshot_id="unsafe-url")

    async def must_not_fetch(urls):
        pytest.fail("unsafe URL reached fetch adapter")

    with pytest.raises(ValueError, match="official website URL"):
        asyncio.run(
            fetch_with_bounded_retry(
                [
                    "https://hermes-agent.nousresearch.com/docs/a"
                    "?token=must-not-be-persisted"
                ],
                must_not_fetch,
                RetryPolicy(sleep=lambda delay: None),
                checkpoint,
            )
        )
    assert checkpoint.retry_events == []


def test_website_checkpoint_resumes_only_hash_and_size_verified_pages(tmp_path):
    import json

    from scribe3.hermes_evidence.website import CrawlPage, RetryPolicy, crawl_website

    urls = [
        f"https://hermes-agent.nousresearch.com/docs/{name}"
        for name in ("a", "b", "c")
    ]

    def page(url):
        name = url.rsplit("/", 1)[-1]
        return CrawlPage(
            url=url,
            final_url=url,
            status=200,
            success=True,
            markdown=f"# {name.upper()}\n" + (f"content {name} " * 30),
            title=name.upper(),
            mime_type="text/html",
        )

    first_calls = []

    async def interrupted_fetch(batch):
        first_calls.append(list(batch))
        if batch == [urls[2]]:
            raise KeyboardInterrupt
        return [page(url) for url in reversed(batch)]

    policy = RetryPolicy(
        max_concurrency=1,
        sleep=lambda delay: None,
        jitter=lambda delay: 0,
    )
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(
            crawl_website(
                urls,
                interrupted_fetch,
                "resume-test",
                tmp_path,
                "2026-07-19T00:00:00+00:00",
                policy=policy,
            )
        )

    checkpoint_path = tmp_path / "checkpoint.json"
    interrupted = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert first_calls == [[urls[0]], [urls[1]], [urls[2]]]
    assert set(interrupted["completed"]) == set(urls[:2])
    assert interrupted["complete"] is False
    assert not list(tmp_path.rglob("*.tmp"))

    a_path = tmp_path / "pages/a.md"
    original_a = a_path.read_bytes()
    a_path.write_bytes(bytes([original_a[0] ^ 1]) + original_a[1:])
    assert a_path.stat().st_size == interrupted["completed"][urls[0]]["byte_length"]

    resumed_calls = []

    async def resumed_fetch(batch):
        resumed_calls.append(list(batch))
        assert len(batch) <= 1
        return [page(url) for url in reversed(batch)]

    manifest = asyncio.run(
        crawl_website(
            urls,
            resumed_fetch,
            "resume-test",
            tmp_path,
            "2026-07-19T00:00:01+00:00",
            policy=policy,
        )
    )

    assert resumed_calls == [[urls[0]], [urls[2]]]
    assert [document.logical_key for document in manifest.documents] == urls
    completed = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert completed["complete"] is True
    for url, entry in completed["completed"].items():
        body = (tmp_path / entry["output_path"]).read_bytes()
        assert len(body) == entry["byte_length"]
        from scribe3.hermes_evidence.models import sha256_bytes

        assert sha256_bytes(body) == entry["content_sha256"]


def test_website_resume_requires_path_size_and_hash_to_all_match(tmp_path):
    import json

    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    urls = [
        f"https://hermes-agent.nousresearch.com/docs/{name}"
        for name in ("path", "size", "hash", "verified")
    ]

    def page(url):
        name = url.rsplit("/", 1)[-1]
        return CrawlPage(
            url=url,
            final_url=url,
            status=200,
            success=True,
            markdown=f"# {name}\n" + (f"public {name} content " * 20),
            title=name,
            mime_type="text/html",
        )

    async def initial_fetch(batch):
        return [page(url) for url in reversed(batch)]

    asyncio.run(
        crawl_website(
            urls,
            initial_fetch,
            "triple-check",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )
    )
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["completed"][urls[0]]["output_path"] = "pages/not-the-recorded-path.md"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    size_path = tmp_path / checkpoint["completed"][urls[1]]["output_path"]
    size_path.write_bytes(size_path.read_bytes() + b"x")
    hash_path = tmp_path / checkpoint["completed"][urls[2]]["output_path"]
    original = hash_path.read_bytes()
    hash_path.write_bytes(bytes([original[0] ^ 1]) + original[1:])

    resumed_batches = []

    async def resumed_fetch(batch):
        resumed_batches.append(list(batch))
        return [page(url) for url in reversed(batch)]

    manifest = asyncio.run(
        crawl_website(
            urls,
            resumed_fetch,
            "triple-check",
            tmp_path,
            "2026-07-19T00:00:01+00:00",
        )
    )

    assert resumed_batches == [urls[:3]]
    assert [document.logical_key for document in manifest.documents] == urls


def test_website_resume_revalidates_final_url_and_stored_body_policy(tmp_path):
    import json

    from scribe3.hermes_evidence.models import (
        contains_sensitive_data,
        document_id_for,
        sha256_bytes,
    )
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    redirect_url = "https://hermes-agent.nousresearch.com/docs/resume-redirect"
    secret_url = "https://hermes-agent.nousresearch.com/docs/resume-secret"
    urls = [redirect_url, secret_url]

    def safe_page(url):
        return CrawlPage(
            url=url,
            final_url=url,
            status=200,
            success=True,
            markdown="# Safe\n" + ("public documentation " * 20),
            title="Safe",
            mime_type="text/html",
        )

    async def initial_fetch(batch):
        return [safe_page(url) for url in reversed(batch)]

    asyncio.run(
        crawl_website(
            urls,
            initial_fetch,
            "resume-policy",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )
    )
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["completed"][redirect_url]["final_url"] = (
        "https://example.test/cross-origin"
    )

    secret_entry = checkpoint["completed"][secret_url]
    secret_body = ("API_KEY=" + ("x" * 32) + (" hidden" * 30) + "\n").encode()
    secret_path = tmp_path / secret_entry["output_path"]
    secret_path.write_bytes(secret_body)
    secret_hash = sha256_bytes(secret_body)
    secret_entry["content_sha256"] = secret_hash
    secret_entry["byte_length"] = len(secret_body)
    secret_entry["text_length"] = len(secret_body.decode())
    secret_entry["document_id"] = document_id_for("website", secret_url, secret_hash)
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    resumed_batches = []

    async def resumed_fetch(batch):
        resumed_batches.append(list(batch))
        return [safe_page(url) for url in reversed(batch)]

    manifest = asyncio.run(
        crawl_website(
            urls,
            resumed_fetch,
            "resume-policy",
            tmp_path,
            "2026-07-19T00:00:01+00:00",
        )
    )

    assert resumed_batches == [urls]
    assert [document.logical_key for document in manifest.documents] == urls
    assert not contains_sensitive_data(manifest.payload())
    assert not contains_sensitive_data(secret_path.read_text(encoding="utf-8"))


def test_website_resume_removes_rejected_old_page_when_refetch_fails(tmp_path):
    import json

    from scribe3.hermes_evidence.models import document_id_for, sha256_bytes
    from scribe3.hermes_evidence.website import CrawlPage, RetryPolicy, crawl_website

    url = "https://hermes-agent.nousresearch.com/docs/rejected-old-page"

    async def initial_fetch(urls):
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown="# Safe\n" + ("public documentation " * 20),
                title="Safe",
                mime_type="text/html",
            )
        ]

    asyncio.run(
        crawl_website(
            [url],
            initial_fetch,
            "remove-rejected",
            tmp_path,
            "2026-07-20T00:00:00+00:00",
        )
    )
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    entry = checkpoint["completed"][url]
    page_path = tmp_path / entry["output_path"]
    secret_body = ("API_KEY=" + ("x" * 32) + (" hidden" * 30) + "\n").encode()
    page_path.write_bytes(secret_body)
    secret_hash = sha256_bytes(secret_body)
    entry["content_sha256"] = secret_hash
    entry["byte_length"] = len(secret_body)
    entry["text_length"] = len(secret_body.decode())
    entry["document_id"] = document_id_for("website", url, secret_hash)
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    async def timeout_fetch(urls):
        raise TimeoutError("must not be persisted")

    manifest = asyncio.run(
        crawl_website(
            [url],
            timeout_fetch,
            "remove-rejected",
            tmp_path,
            "2026-07-20T00:00:01+00:00",
            policy=RetryPolicy(
                max_attempts=1,
                sleep=lambda delay: None,
            ),
        )
    )

    assert manifest.documents == []
    assert manifest.failures == [
        {"requested_url": url, "error": "TimeoutError"}
    ]
    assert not page_path.exists()


def test_website_crawl_honors_lower_concurrency_and_integrates_retry(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, RetryPolicy, crawl_website

    urls = [
        f"https://hermes-agent.nousresearch.com/docs/page-{index}"
        for index in range(6)
    ]
    attempts = {url: 0 for url in urls}
    batches = []

    async def fake_fetch(batch):
        batches.append(list(batch))
        assert len(batch) <= 2
        pages = []
        for url in reversed(batch):
            attempts[url] += 1
            status = 503 if url == urls[0] and attempts[url] == 1 else 200
            pages.append(
                CrawlPage(
                    url=url,
                    final_url=url,
                    status=status,
                    success=status == 200,
                    markdown="# Page\n" + ("substantive content " * 20),
                    title="Page",
                    mime_type="text/html",
                )
            )
        return pages

    manifest = asyncio.run(
        crawl_website(
            urls,
            fake_fetch,
            "concurrency-test",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
            policy=RetryPolicy(
                max_concurrency=2,
                sleep=lambda delay: None,
                jitter=lambda delay: 0,
            ),
        )
    )

    assert attempts[urls[0]] == 2
    assert all(attempts[url] == 1 for url in urls[1:])
    assert len(manifest.documents) == 6
    assert len(manifest.retry_events) == 1
    assert all(len(batch) <= 2 for batch in batches)


def test_website_crawl_rejects_redirect_secret_short_and_duplicate_results(tmp_path):
    from scribe3.hermes_evidence.models import contains_sensitive_data
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    redirect_url = "https://hermes-agent.nousresearch.com/docs/redirect"
    secret_url = "https://hermes-agent.nousresearch.com/docs/secret"
    short_url = "https://hermes-agent.nousresearch.com/docs/short"
    duplicate_url = "https://hermes-agent.nousresearch.com/docs/duplicate"

    async def fake_fetch(urls):
        common = {
            "status": 200,
            "success": True,
            "title": "Page",
            "mime_type": "text/html",
        }
        return [
            CrawlPage(
                url=redirect_url,
                final_url="https://example.test/stolen",
                markdown="# Redirect\n" + ("content " * 30),
                **common,
            ),
            CrawlPage(
                url=secret_url,
                final_url=secret_url,
                markdown="API_KEY=" + ("x" * 32) + (" content" * 30),
                **common,
            ),
            CrawlPage(
                url=short_url,
                final_url=short_url,
                markdown="# Short\nerror",
                **common,
            ),
            CrawlPage(
                url=duplicate_url,
                final_url=duplicate_url,
                markdown="# First\n" + ("content " * 30),
                **common,
            ),
            CrawlPage(
                url=duplicate_url,
                final_url=duplicate_url,
                markdown="# Second\n" + ("other " * 40),
                **common,
            ),
        ]

    urls = [redirect_url, secret_url, short_url, duplicate_url]
    manifest = asyncio.run(
        crawl_website(
            urls,
            fake_fetch,
            "fail-closed-test",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )
    )

    assert manifest.documents == []
    assert {row["requested_url"]: row["error"] for row in manifest.failures} == {
        redirect_url: "cross_origin_redirect",
        secret_url: "suspected_secret",
        short_url: "short_content",
        duplicate_url: "duplicate_result",
    }
    assert not contains_sensitive_data(manifest.failures)
    assert not list((tmp_path / "pages").glob("*.md"))


def test_website_crawl_rejects_redirect_to_official_github_source(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    url = "https://hermes-agent.nousresearch.com/docs/github-redirect"

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=url,
                final_url="https://github.com/NousResearch/hermes-agent",
                status=200,
                success=True,
                markdown="# Repository\n" + ("public documentation " * 20),
                title="Repository",
                mime_type="text/html",
            )
        ]

    manifest = asyncio.run(
        crawl_website(
            [url],
            fake_fetch,
            "website-github-redirect",
            tmp_path,
            "2026-07-20T00:00:00+00:00",
        )
    )

    assert manifest.documents == []
    assert manifest.failures == [
        {"requested_url": url, "error": "cross_origin_redirect"}
    ]
    assert not (tmp_path / "pages/github-redirect.md").exists()


def test_website_crawl_refuses_symlink_output_and_checkpoint_paths(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    url = "https://hermes-agent.nousresearch.com/docs/a"

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown="# A\n" + ("content " * 40),
                title="A",
                mime_type="text/html",
            )
        ]

    outside_page = tmp_path / "outside-page.md"
    outside_page.write_text("do not overwrite", encoding="utf-8")
    page_root = tmp_path / "page-root"
    (page_root / "pages").mkdir(parents=True)
    (page_root / "pages/a.md").symlink_to(outside_page)

    manifest = asyncio.run(
        crawl_website(
            [url],
            fake_fetch,
            "symlink-page",
            page_root,
            "2026-07-19T00:00:00+00:00",
        )
    )
    assert outside_page.read_text(encoding="utf-8") == "do not overwrite"
    assert manifest.documents == []
    assert manifest.failures == [
        {"requested_url": url, "error": "unsafe_output_path"}
    ]

    outside_checkpoint = tmp_path / "outside-checkpoint.json"
    outside_checkpoint.write_text("do not overwrite", encoding="utf-8")
    checkpoint_root = tmp_path / "checkpoint-root"
    checkpoint_root.mkdir()
    (checkpoint_root / "checkpoint.json").symlink_to(outside_checkpoint)
    with pytest.raises(RuntimeError, match="unsafe checkpoint path"):
        asyncio.run(
            crawl_website(
                [url],
                fake_fetch,
                "symlink-checkpoint",
                checkpoint_root,
                "2026-07-19T00:00:00+00:00",
            )
        )
    assert outside_checkpoint.read_text(encoding="utf-8") == "do not overwrite"


def test_website_atomic_write_resists_parent_symlink_swap_race(
    tmp_path, monkeypatch
):
    import scribe3.hermes_evidence.website as website

    url = "https://hermes-agent.nousresearch.com/docs/race"
    out_root = tmp_path / "evidence"
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_page = outside / "race.md"
    outside_page.write_text("outside sentinel", encoding="utf-8")
    real_replace = website.os.replace
    swapped = False

    def swapping_replace(source, destination, *args, **kwargs):
        nonlocal swapped
        destination_name = website.os.fspath(destination)
        if not swapped and destination_name.endswith("race.md"):
            swapped = True
            pages = out_root / "pages"
            pages.rename(out_root / "pages-before-swap")
            pages.symlink_to(outside, target_is_directory=True)
            moved_temporary = out_root / "pages-before-swap" / website.os.path.basename(
                website.os.fspath(source)
            )
            (outside / moved_temporary.name).write_bytes(moved_temporary.read_bytes())
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(website.os, "replace", swapping_replace)

    async def fake_fetch(urls):
        return [
            website.CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown="# Race\n" + ("public documentation " * 20),
                title="Race",
                mime_type="text/html",
            )
        ]

    manifest = asyncio.run(
        website.crawl_website(
            [url],
            fake_fetch,
            "symlink-swap-race",
            out_root,
            "2026-07-20T00:00:00+00:00",
        )
    )

    assert swapped
    assert outside_page.read_text(encoding="utf-8") == "outside sentinel"
    assert manifest.documents == []
    assert manifest.failures == [
        {"requested_url": url, "error": "unsafe_output_path"}
    ]


def test_website_atomic_write_closes_root_fd_when_parent_open_fails(tmp_path):
    import os

    import scribe3.hermes_evidence.website as website

    out_root = tmp_path / "evidence"
    outside = tmp_path / "outside"
    out_root.mkdir()
    outside.mkdir()
    (out_root / "pages").symlink_to(outside, target_is_directory=True)

    baseline = len(os.listdir("/dev/fd"))
    for _ in range(40):
        with pytest.raises(website._UnsafeOutputPath):
            website._atomic_write(out_root, Path("pages/a.md"), b"safe")
    after_failures = len(os.listdir("/dev/fd"))

    assert after_failures <= baseline + 2


def test_website_crawl_rejects_sensitive_response_metadata_before_writing(tmp_path):
    from scribe3.hermes_evidence.models import contains_sensitive_data
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    url = "https://hermes-agent.nousresearch.com/docs/metadata"

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown="# Safe body\n" + ("public documentation " * 20),
                title="API_KEY=" + ("x" * 32),
                mime_type="text/html",
            )
        ]

    manifest = asyncio.run(
        crawl_website(
            [url],
            fake_fetch,
            "sensitive-metadata",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )
    )

    assert manifest.documents == []
    assert manifest.failures == [
        {"requested_url": url, "error": "suspected_secret_metadata"}
    ]
    assert not contains_sensitive_data(manifest.payload())
    assert not (tmp_path / "pages/metadata.md").exists()


def test_website_crawl_keeps_navigation_but_rejects_soft_error_without_leak(tmp_path):
    from scribe3.hermes_evidence.models import contains_sensitive_data
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    soft_url = "https://hermes-agent.nousresearch.com/docs/soft-error"
    search_url = "https://hermes-agent.nousresearch.com/docs/search"

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=soft_url,
                final_url=soft_url,
                status=200,
                success=False,
                markdown="# Error\n" + ("misleading long body " * 20),
                title="Error",
                mime_type="text/html",
                error="Authorization: Bearer must-not-be-persisted",
            ),
            CrawlPage(
                url=search_url,
                final_url=search_url,
                status=200,
                success=True,
                markdown="# Search\nnavigation",
                title="Search",
                mime_type="text/html",
            ),
        ]

    manifest = asyncio.run(
        crawl_website(
            [soft_url, search_url],
            fake_fetch,
            "soft-error",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )
    )

    assert [document.logical_key for document in manifest.documents] == [search_url]
    assert manifest.documents[0].semantic_status == "navigation_only"
    assert manifest.failures == [
        {"requested_url": soft_url, "error": "http_200"}
    ]
    assert not contains_sensitive_data(manifest.payload())


@pytest.mark.parametrize(
    ("title", "heading", "detail", "expected_error"),
    [
        (
            "404 - Page Not Found",
            "# 404 - Page Not Found",
            "The page you requested could not be found.",
            "soft_404",
        ),
        (
            "Sign in",
            "# Sign in",
            "Sign in to continue. Enter your password to access this page.",
            "soft_login",
        ),
        (
            "Just a moment...",
            "# Verify you are human",
            "Checking your browser before accessing this Cloudflare protected site.",
            "soft_anti_bot",
        ),
        (
            "Service Unavailable",
            "# Service Unavailable",
            "The server is temporarily unavailable. Please try again later.",
            "soft_server_error",
        ),
    ],
)
def test_website_crawl_rejects_semantic_soft_error_pages(
    tmp_path, title, heading, detail, expected_error
):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    url = "https://hermes-agent.nousresearch.com/docs/semantic-error"

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown=f"{heading}\n{detail}\n" + ("diagnostic page text " * 20),
                title=title,
                mime_type="text/html",
            )
        ]

    manifest = asyncio.run(
        crawl_website(
            [url],
            fake_fetch,
            f"semantic-{expected_error}",
            tmp_path,
            "2026-07-20T00:00:00+00:00",
        )
    )

    assert manifest.documents == []
    assert manifest.failures == [
        {"requested_url": url, "error": expected_error}
    ]
    assert not (tmp_path / "pages/semantic-error.md").exists()


def test_website_crawl_does_not_misclassify_normal_error_documentation(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    url = "https://hermes-agent.nousresearch.com/docs/handling-404-errors"
    body = (
        "# Handling 404 errors\n"
        "This guide explains how applications should handle an HTTP 404 response.\n"
        + ("Documented recovery behavior and examples. " * 12)
    )

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown=body,
                title="Handling 404 errors",
                mime_type="text/html",
            )
        ]

    manifest = asyncio.run(
        crawl_website(
            [url],
            fake_fetch,
            "normal-error-doc",
            tmp_path,
            "2026-07-20T00:00:00+00:00",
        )
    )

    assert [document.logical_key for document in manifest.documents] == [url]
    assert not manifest.failures


@pytest.mark.parametrize(
    ("slug", "title", "heading", "detail"),
    [
        (
            "404-tutorial",
            "404 - Page Not Found",
            "# 404 - Page Not Found",
            "This guide explains how to recover when a page or resource could not be found in an API response.",
        ),
        (
            "login-tutorial",
            "Sign in",
            "# Sign in",
            "This tutorial explains how users sign in to continue and when to enter your password safely.",
        ),
        (
            "anti-bot-tutorial",
            "Just a moment...",
            "# Verify you are human",
            "This documentation explains how Cloudflare uses checking your browser and verify you are human pages.",
        ),
        (
            "server-error-tutorial",
            "Service Unavailable",
            "# Service Unavailable",
            "This troubleshooting guide explains how a server can be unavailable and why clients should try again later.",
        ),
    ],
)
def test_website_soft_error_exact_heading_does_not_override_tutorial_structure(
    tmp_path, slug, title, heading, detail
):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    url = f"https://hermes-agent.nousresearch.com/docs/{slug}"
    body = f"{heading}\n{detail}\n" + ("Documented examples and recovery steps. " * 12)

    async def fake_fetch(urls):
        return [
            CrawlPage(
                url=url,
                final_url=url,
                status=200,
                success=True,
                markdown=body,
                title=title,
                mime_type="text/html",
            )
        ]

    manifest = asyncio.run(
        crawl_website(
            [url],
            fake_fetch,
            f"tutorial-{slug}",
            tmp_path,
            "2026-07-20T00:00:00+00:00",
        )
    )

    assert [document.logical_key for document in manifest.documents] == [url]
    assert not manifest.failures


def test_website_content_identity_is_timestamp_independent_and_supersedes(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    url = "https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks"
    fixture = Path(
        "scribe3/tests/fixtures/hermes_evidence/pages/hooks.md"
    ).read_text(encoding="utf-8")

    def fetcher(markdown):
        async def fake_fetch(urls):
            return [
                CrawlPage(
                    url=url,
                    final_url=url,
                    status=200,
                    success=True,
                    markdown=markdown,
                    title="Hooks",
                    mime_type="text/html",
                )
            ]

        return fake_fetch

    first = asyncio.run(
        crawl_website(
            [url], fetcher(fixture), "first", tmp_path / "first", "2026-07-19T00:00:00Z"
        )
    )
    identical = asyncio.run(
        crawl_website(
            [url],
            fetcher("\n" + fixture + "\n\n"),
            "second",
            tmp_path / "second",
            "2026-07-20T00:00:00Z",
            previous=first,
        )
    )
    changed = asyncio.run(
        crawl_website(
            [url],
            fetcher(fixture + "\nChanged public documentation paragraph."),
            "third",
            tmp_path / "third",
            "2026-07-21T00:00:00Z",
            previous=identical,
        )
    )

    first_document = first.documents[0]
    identical_document = identical.documents[0]
    changed_document = changed.documents[0]
    assert first_document.document_id == identical_document.document_id
    assert identical_document.supersedes_document_id is None
    assert changed_document.document_id != identical_document.document_id
    assert changed_document.supersedes_document_id == identical_document.document_id
    saved = tmp_path / "second" / identical_document.output_path
    assert saved.read_text(encoding="utf-8") == fixture.strip() + "\n"
    assert "2026-07-20" not in saved.read_text(encoding="utf-8")


def test_sitemap_is_unique_sorted_and_official():
    xml = Path("scribe3/tests/fixtures/hermes_evidence/sitemap.xml").read_bytes()

    assert discover_sitemap(xml) == [
        "https://hermes-agent.nousresearch.com/docs/",
        "https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks",
    ]


def test_sitemap_discovery_preserves_raw_hash_and_classifies_paths():
    from scribe3.hermes_evidence.website import discover_sitemap_snapshot

    xml = Path("scribe3/tests/fixtures/hermes_evidence/sitemap.xml").read_bytes()
    result = discover_sitemap_snapshot(xml)

    assert len(result.raw_sha256) == 64
    assert result.urls == tuple(sorted(set(result.urls)))
    assert result.page_kinds[result.urls[0]] in {"content", "directory", "search"}


def test_sitemap_rejects_malformed_xml_and_non_docs_urls():
    with pytest.raises(ValueError, match="invalid XML"):
        discover_sitemap(b"<urlset>")
    with pytest.raises(ValueError, match="non-official"):
        discover_sitemap(
            b"<urlset><url><loc>https://hermes-agent.nousresearch.com/docs-evil</loc>"
            b"</url></urlset>"
        )


def test_official_host_and_output_path_are_fail_closed():
    assert is_official_url("https://hermes-agent.nousresearch.com/docs/a")
    assert is_official_url("https://github.com/NousResearch/hermes-agent")
    assert not is_official_url("https://example.com/copied-doc")
    assert output_path_for_url("https://hermes-agent.nousresearch.com/docs/a/b") == Path(
        "pages/a/b.md"
    )
    with pytest.raises(ValueError):
        output_path_for_url("https://example.com/docs/a")


@pytest.mark.parametrize(
    "url",
    [
        "https://hermes-agent.nousresearch.com/docs-evil/a",
        "https://github.com/NousResearch/hermes-agent-evil",
        "https://github.com/OtherOrg/hermes-agent",
        "https://api.github.com/repos/NousResearch/hermes-agent-evil/contents/a.md",
        "https://raw.githubusercontent.com/NousResearch/hermes-agent-evil/main/a.md",
    ],
)
def test_official_url_path_boundaries_are_strict(url: str):
    assert not is_official_url(url)


def test_official_url_rejects_malformed_port_without_raising():
    assert not is_official_url("https://hermes-agent.nousresearch.com:invalid/docs/a")


@pytest.mark.parametrize(
    "path",
    [
        "/docs/./outside",
        "/docs/../outside",
        "/docs/%2e%2e/outside",
        "/docs/%252e%252e/outside",
        "/docs/a%2fb",
        "/docs/a%5cb",
        "/docs/a%0a",
    ],
)
def test_policy_and_output_mapper_reject_encoded_or_raw_path_escapes(path: str):
    url = f"https://hermes-agent.nousresearch.com{path}"

    assert not is_official_url(url)
    with pytest.raises(ValueError):
        output_path_for_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@hermes-agent.nousresearch.com/docs/a",
        "https://hermes-agent.nousresearch.com/docs/a#fragment",
        "https://hermes-agent.nousresearch.com/docs/a?token=actual-secret",
        "https://hermes-agent.nousresearch.com/docs/a?api_key=actual-secret",
    ],
)
def test_policy_rejects_noncanonical_or_sensitive_official_urls(url: str):
    assert not is_official_url(url)


def test_policy_rejects_raw_control_characters_before_url_parsing():
    assert not is_official_url("https://hermes-agent.nousresearch.com/docs/a\n")


def test_api_allows_non_sensitive_query_but_output_mapper_rejects_repository_url():
    url = "https://api.github.com/repos/NousResearch/hermes-agent/git/trees/main?recursive=1"

    assert is_official_url(url)
    with pytest.raises(ValueError):
        output_path_for_url(url)


def test_sitemap_requires_exact_sitemap_structure_and_namespace():
    official_url = b"https://hermes-agent.nousresearch.com/docs/a"
    cases = [
        b"<not-urlset><fake-loc>" + official_url + b"</fake-loc></not-urlset>",
        b'<urlset xmlns="https://example.test/sitemap"><url><loc>'
        + official_url
        + b"</loc></url></urlset>",
        b"<urlset><url></url></urlset>",
        b"<urlset><url><loc>" + official_url + b"</loc><loc>" + official_url + b"</loc></url></urlset>",
        b"<urlset><wrapper><url><loc>" + official_url + b"</loc></url></wrapper></urlset>",
    ]

    for xml in cases:
        with pytest.raises(ValueError):
            discover_sitemap(xml)


def test_sitemap_ignores_standard_fields_and_non_url_extensions():
    xml = b"""<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"
        xmlns:image=\"https://www.google.com/schemas/sitemap-image/1.1\">
      <url><loc>https://hermes-agent.nousresearch.com/docs/a</loc><lastmod>2026-07-19</lastmod>
        <changefreq>daily</changefreq><priority>0.5</priority><image:image /></url>
    </urlset>"""

    assert discover_sitemap(xml) == ["https://hermes-agent.nousresearch.com/docs/a"]


@pytest.mark.parametrize(
    "xml",
    [
        b"<urlset><url><loc>https://hermes-agent.nousresearch.com/docs/a</loc></url><unexpected /></urlset>",
        b"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        b"<url><loc>https://hermes-agent.nousresearch.com/docs/a</loc></url><unexpected />"
        b"</urlset>",
        b"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\" xmlns:bad=\"https://example.test/bad\">"
        b"<url><loc>https://hermes-agent.nousresearch.com/docs/a</loc></url><bad:unexpected />"
        b"</urlset>",
    ],
)
def test_sitemap_rejects_non_url_root_children_in_any_namespace(xml: bytes):
    with pytest.raises(ValueError):
        discover_sitemap(xml)


@pytest.mark.parametrize(
    "xml",
    [
        b"<urlset><url><loc>https://hermes-agent.nousresearch.com/docs/a</loc><unexpected /></url></urlset>",
        b"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        b"<url><loc>https://hermes-agent.nousresearch.com/docs/a</loc><unexpected /></url>"
        b"</urlset>",
    ],
)
def test_sitemap_rejects_unknown_same_namespace_url_children(xml: bytes):
    with pytest.raises(ValueError):
        discover_sitemap(xml)


def test_repo_policy_keeps_docs_and_classifies_skills():
    assert select_repo_document("website/docs/user-guide/features/hooks.md")
    assert select_repo_document("optional-skills/creative/creative-ideation/SKILL.md")
    assert not select_repo_document("agent/run_loop.py")
    assert classify_repo_path("optional-skills/creative/x/SKILL.md") == (
        "en",
        "optional-skill",
        True,
        False,
    )


def test_secret_scanner_rejects_secret_shapes_without_echoing_values():
    assert contains_secret("API_KEY=" + "x" * 32)
    assert contains_secret("Authorization: Bearer " + "x" * 32)
    assert not contains_secret("Use ${API_KEY} from the environment")


def _assert_selected_partition(manifest, expected_logical_keys):
    payload = manifest.payload()
    success_keys = {
        document.logical_key for document in manifest.documents if not document.error
    }
    failure_keys = {row["logical_key"] for row in manifest.failures}
    exclusion_keys = {row["logical_key"] for row in manifest.exclusions}

    assert manifest.expected_document_count == (
        payload["success_count"] + payload["failed_count"] + payload["excluded_count"]
    )
    assert success_keys | failure_keys | exclusion_keys == set(expected_logical_keys)
    assert not (
        success_keys & failure_keys
        or success_keys & exclusion_keys
        or failure_keys & exclusion_keys
    )


def test_repository_snapshot_resolves_fixed_ref_and_preserves_selected_paths(tmp_path):
    import json

    from scribe3.hermes_evidence.github import snapshot_repository

    fixture = json.loads(
        Path("scribe3/tests/fixtures/hermes_evidence/tree.json").read_text(
            encoding="utf-8"
        )
    )

    class FakeClient:
        def resolve_ref(self, ref):
            assert ref == "main"
            return "a" * 40

        def tree_payload(self, sha):
            assert sha == "a" * 40
            return fixture

        def blob(self, sha):
            return {
                "b" * 40: b"# H\n",
                "d" * 40: b"# S\n",
            }[sha]

    manifest = snapshot_repository(
        FakeClient(),
        "main",
        "main-aaaaaaaa",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert manifest.resolved_sha == "a" * 40
    assert manifest.expected_document_count == 2
    assert [document.repo_path for document in manifest.documents] == [
        "README.md",
        "skills/x/SKILL.md",
    ]
    assert [document.source_blob_sha for document in manifest.documents] == [
        "b" * 40,
        "d" * 40,
    ]
    assert (tmp_path / "README.md").read_text() == "# H\n"
    assert (tmp_path / "skills/x/SKILL.md").read_text() == "# S\n"
    _assert_selected_partition(manifest, {"README.md", "skills/x/SKILL.md"})


def test_repository_snapshot_rejects_recursive_tree_without_explicit_complete_flag(
    tmp_path,
):
    from scribe3.hermes_evidence.github import snapshot_repository

    class FakeClient:
        def resolve_ref(self, ref):
            return "a" * 40

        def tree_payload(self, sha):
            return {"tree": []}

    with pytest.raises(RuntimeError, match="truncated"):
        snapshot_repository(
            FakeClient(),
            "main",
            "main-aaaaaaaa",
            tmp_path,
            "2026-07-19T00:00:00+00:00",
        )


def test_repository_snapshot_classifies_selected_special_entries_before_download(
    tmp_path,
):
    from scribe3.hermes_evidence.github import MAX_DOCUMENT_BYTES, snapshot_repository

    class FakeClient:
        def __init__(self):
            self.requested_blobs = []

        def resolve_ref(self, ref):
            return "a" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {
                        "path": "docs/selected-submodule.md",
                        "type": "commit",
                        "sha": "sub-selected",
                    },
                    {"path": "vendor/runtime", "type": "commit", "sha": "sub-note"},
                    {
                        "path": "docs/link.md",
                        "type": "blob",
                        "mode": "120000",
                        "sha": "link",
                        "size": 9,
                    },
                    {
                        "path": "docs/large.pdf",
                        "type": "blob",
                        "sha": "large",
                        "size": MAX_DOCUMENT_BYTES + 1,
                    },
                    {
                        "path": "docs/lfs.pdf",
                        "type": "blob",
                        "sha": "lfs",
                        "size": 130,
                    },
                    {
                        "path": "docs/failed.md",
                        "type": "blob",
                        "sha": "failed",
                        "size": 5,
                    },
                    {
                        "path": "docs/saved.md",
                        "type": "blob",
                        "sha": "saved",
                        "size": 7,
                    },
                ],
            }

        def blob(self, sha):
            self.requested_blobs.append(sha)
            if sha == "lfs":
                return (
                    b"version https://git-lfs.github.com/spec/v1\n"
                    b"oid sha256:" + b"c" * 64 + b"\nsize 200\n"
                )
            if sha == "failed":
                raise OSError("response body must not be copied into the manifest")
            return b"# saved\n"

    client = FakeClient()
    manifest = snapshot_repository(
        client,
        "main",
        "main-aaaaaaaa",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert manifest.expected_document_count == 6
    assert [document.repo_path for document in manifest.documents] == ["docs/saved.md"]
    assert {row["repo_path"]: row["reason"] for row in manifest.exclusions} == {
        "docs/large.pdf": "oversized_attachment",
        "docs/lfs.pdf": "git_lfs_pointer",
        "docs/link.md": "git_symlink",
        "docs/selected-submodule.md": "git_submodule",
    }
    assert manifest.failures == [
        {
            "logical_key": "docs/failed.md",
            "repo_path": "docs/failed.md",
            "source_blob_sha": "failed",
            "error": "OSError",
        }
    ]
    assert all(row["logical_key"] == row["repo_path"] for row in manifest.exclusions)
    assert {row["source_blob_sha"] for row in manifest.exclusions} == {
        "large",
        "lfs",
        "link",
        "sub-selected",
    }
    lfs = next(row for row in manifest.exclusions if row["reason"] == "git_lfs_pointer")
    assert len(lfs["content_sha256"]) == 64
    _assert_selected_partition(
        manifest,
        {
            "docs/failed.md",
            "docs/large.pdf",
            "docs/lfs.pdf",
            "docs/link.md",
            "docs/saved.md",
            "docs/selected-submodule.md",
        },
    )
    assert "repository_submodule:vendor/runtime" in manifest.notes
    assert client.requested_blobs == ["failed", "lfs", "saved"]
    assert not (tmp_path / "docs/lfs.pdf").exists()


def test_repository_snapshot_is_deterministic_for_the_same_fixed_ref(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    class FakeClient:
        def resolve_ref(self, ref):
            return "d" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/b.md", "type": "blob", "sha": "blob-b", "size": 3},
                    {"path": "docs/a.md", "type": "blob", "sha": "blob-a", "size": 3},
                    {"path": "docs/c.md", "type": "blob", "sha": "blob-c", "size": 3},
                    {
                        "path": "docs/d.md",
                        "type": "blob",
                        "mode": "120000",
                        "sha": "blob-d",
                        "size": 3,
                    },
                ],
            }

        def blob(self, sha):
            if sha == "blob-b":
                return b"version https://git-lfs.github.com/spec/v1\n"
            if sha == "blob-c":
                raise OSError("must not be persisted")
            return b"A\n"

    manifests = [
        snapshot_repository(
            FakeClient(),
            "d" * 40,
            f"fixed-{index}",
            tmp_path / str(index),
            "2026-07-19T00:00:00+00:00",
            source_kind="main",
        )
        for index in range(2)
    ]

    def identity(manifest):
        successes = [
            (
                "success",
                document.logical_key,
                document.source_blob_sha,
                document.content_sha256,
            )
            for document in manifest.documents
            if not document.error
        ]
        failures = [
            (
                "failure",
                row["logical_key"],
                row["source_blob_sha"],
                row.get("content_sha256"),
            )
            for row in manifest.failures
        ]
        exclusions = [
            (
                "exclusion",
                row["logical_key"],
                row["source_blob_sha"],
                row.get("content_sha256"),
            )
            for row in manifest.exclusions
        ]
        return sorted(successes + failures + exclusions)

    assert identity(manifests[0]) == identity(manifests[1])
    for manifest in manifests:
        _assert_selected_partition(
            manifest, {"docs/a.md", "docs/b.md", "docs/c.md", "docs/d.md"}
        )


def test_repository_snapshot_preserves_pdf_and_writes_extracted_sidecar(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    pdf = b"%PDF-1.7\nexact-original-bytes"

    class FakeClient:
        def resolve_ref(self, ref):
            return "e" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/guide.pdf", "type": "blob", "sha": "pdf", "size": len(pdf)}
                ],
            }

        def blob(self, sha):
            return pdf

    def fake_extractor(source, target):
        assert source.read_bytes() == pdf
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Extracted text\n", encoding="utf-8")

    manifest = snapshot_repository(
        FakeClient(),
        "v1.0.0",
        "release-v1",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
        pdf_extractor=fake_extractor,
    )

    document = manifest.documents[0]
    assert (tmp_path / "docs/guide.pdf").read_bytes() == pdf
    assert (tmp_path / document.extracted_text_path).read_text() == "Extracted text\n"
    assert document.extracted_text_path == "_extracted/docs/guide.pdf.txt"
    assert len(document.extracted_text_sha256) == 64
    assert document.text_length == len("Extracted text\n")
    assert document.semantic_status == "content"
    _assert_selected_partition(manifest, {"docs/guide.pdf"})


def test_repository_snapshot_keeps_pdf_binary_when_extraction_fails(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    pdf = b"%PDF-1.4\nexact-original-bytes"

    class FakeClient:
        def resolve_ref(self, ref):
            return "f" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/guide.pdf", "type": "blob", "sha": "pdf", "size": len(pdf)}
                ],
            }

        def blob(self, sha):
            return pdf

    def failed_extractor(source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("partial and untrusted", encoding="utf-8")
        raise RuntimeError("sensitive process output must not be persisted")

    manifest = snapshot_repository(
        FakeClient(),
        "main",
        "main-pdf",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
        pdf_extractor=failed_extractor,
    )

    assert (tmp_path / "docs/guide.pdf").read_bytes() == pdf
    assert not (tmp_path / "_extracted/docs/guide.pdf.txt").exists()
    assert manifest.documents[0].semantic_status == "binary_attachment"
    assert manifest.documents[0].error == "pdf_text_extraction_failed"
    assert manifest.exclusions == []
    assert manifest.failures == [
        {
            "logical_key": "docs/guide.pdf",
            "repo_path": "docs/guide.pdf",
            "source_blob_sha": "pdf",
            "content_sha256": manifest.documents[0].content_sha256,
            "error": "pdf_text_extraction_failed",
        }
    ]
    payload = manifest.payload()
    assert payload["success_count"] == 0
    assert payload["failed_count"] == 1
    assert payload["excluded_count"] == 0
    assert manifest.expected_document_count == 1
    _assert_selected_partition(manifest, {"docs/guide.pdf"})


def test_repository_snapshot_keeps_invalid_pdf_only_as_failure(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    body = b"not-a-pdf"

    class FakeClient:
        def resolve_ref(self, ref):
            return "a" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/bad.pdf", "type": "blob", "sha": "bad", "size": len(body)}
                ],
            }

        def blob(self, sha):
            return body

    manifest = snapshot_repository(
        FakeClient(),
        "main",
        "main-invalid-pdf",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert (tmp_path / "docs/bad.pdf").read_bytes() == body
    assert manifest.documents == []
    assert manifest.exclusions == []
    assert manifest.failures == [
        {
            "logical_key": "docs/bad.pdf",
            "repo_path": "docs/bad.pdf",
            "source_blob_sha": "bad",
            "content_sha256": manifest.failures[0]["content_sha256"],
            "error": "invalid_pdf_signature",
        }
    ]
    assert len(manifest.failures[0]["content_sha256"]) == 64
    _assert_selected_partition(manifest, {"docs/bad.pdf"})


def test_repository_snapshot_requires_explicit_source_layer_for_fixed_sha(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    sha = "a" * 40

    class FakeClient:
        def resolve_ref(self, ref):
            return sha

        def tree_payload(self, resolved_sha):
            return {"truncated": False, "tree": []}

    args = (
        FakeClient(),
        sha,
        "fixed-source-layer",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )
    with pytest.raises(ValueError, match="source_kind"):
        snapshot_repository(*args)
    with pytest.raises(ValueError, match="release_tag"):
        snapshot_repository(*args, source_kind="release")
    with pytest.raises(ValueError, match="release_tag"):
        snapshot_repository(*args, source_kind="main", release_tag="v1.0.0")

    release = snapshot_repository(
        *args, source_kind="release", release_tag="v1.0.0"
    )
    main = snapshot_repository(*args, source_kind="main")
    assert (release.source_kind, release.release_tag, release.resolved_sha) == (
        "release",
        "v1.0.0",
        sha,
    )
    assert (main.source_kind, main.release_tag, main.resolved_sha) == (
        "main",
        None,
        sha,
    )
    _assert_selected_partition(release, set())
    _assert_selected_partition(main, set())


def test_repository_snapshot_records_non_bytes_blob_without_persisting_value(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository
    from scribe3.hermes_evidence.models import contains_sensitive_data

    class FakeClient:
        def resolve_ref(self, ref):
            return "a" * 40

        def tree_payload(self, sha):
            return {
                "truncated": False,
                "tree": [
                    {"path": "docs/bad.md", "type": "blob", "sha": "bad", "size": 3}
                ],
            }

        def blob(self, sha):
            return "Authorization: Bearer must-not-be-persisted"

    manifest = snapshot_repository(
        FakeClient(),
        "main",
        "main-invalid-blob",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert manifest.failures == [
        {
            "logical_key": "docs/bad.md",
            "repo_path": "docs/bad.md",
            "source_blob_sha": "bad",
            "error": "TypeError",
        }
    ]
    assert not contains_sensitive_data(manifest.failures)
    _assert_selected_partition(manifest, {"docs/bad.md"})


def test_github_client_uses_only_fixed_official_git_endpoints(monkeypatch):
    import base64

    from scribe3.hermes_evidence.github import API, GitHubClient

    commit_sha = "a" * 40
    tag_sha = "b" * 40
    blob_sha = "c" * 40
    requested = []
    responses = {
        f"{API}/git/ref/tags/v1.0.0": {
            "object": {"type": "tag", "sha": tag_sha}
        },
        f"{API}/git/tags/{tag_sha}": {
            "object": {"type": "commit", "sha": commit_sha}
        },
        f"{API}/commits/main": {"sha": commit_sha},
        f"{API}/git/trees/{commit_sha}?recursive=1": {
            "truncated": False,
            "tree": [{"path": "README.md", "type": "blob", "sha": blob_sha}],
        },
        f"{API}/git/blobs/{blob_sha}": {
            "encoding": "base64",
            "content": base64.b64encode(b"# README\n").decode("ascii"),
        },
    }

    def fake_json(url):
        requested.append(url)
        return responses[url]

    client = GitHubClient()
    monkeypatch.setattr(client, "_json", fake_json)

    assert client.resolve_ref("v1.0.0") == commit_sha
    assert client.resolve_ref("main") == commit_sha
    assert client.resolve_ref(commit_sha) == commit_sha
    assert client.tree(commit_sha) == responses[
        f"{API}/git/trees/{commit_sha}?recursive=1"
    ]["tree"]
    assert client.blob(blob_sha) == b"# README\n"
    assert all(url.startswith(f"{API}/") for url in requested)
    with pytest.raises(ValueError):
        client.resolve_ref("../../other-repository")


def test_github_client_preserves_only_safe_rate_limit_and_retry_metadata(tmp_path):
    import io
    import urllib.error

    from scribe3.hermes_evidence.github import API, GitHubClient, snapshot_repository
    from scribe3.hermes_evidence.models import contains_sensitive_data

    commit_sha = "a" * 40
    response_body = io.BytesIO((f'{{"sha":"{commit_sha}"}}').encode("ascii"))
    response_body.headers = {
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Remaining": "41",
        "Authorization": "Bearer must-not-be-persisted",
    }
    tree_body = io.BytesIO(b'{"truncated":false,"tree":[]}')
    tree_body.headers = {}
    responses = [
        urllib.error.HTTPError(
            f"{API}/commits/main",
            429,
            "must-not-be-persisted",
            {
                "Retry-After": "2",
                "X-RateLimit-Remaining": "0",
                "Set-Cookie": "must-not-be-persisted",
            },
            io.BytesIO(b"must-not-be-persisted"),
        ),
        response_body,
        tree_body,
    ]
    slept = []

    def opener(request, timeout):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    client = GitHubClient(opener=opener, sleep=slept.append, max_retries=1)
    manifest = snapshot_repository(
        client,
        "main",
        "fixed-rate-metadata",
        tmp_path,
        "2026-07-19T00:00:00+00:00",
    )

    assert slept == [2]
    assert any(event.get("x-ratelimit-remaining") == 41 for event in manifest.retry_events)
    assert not contains_sensitive_data(manifest.retry_events)
    _assert_selected_partition(manifest, set())


def test_github_redirect_handler_rejects_unsafe_location_before_following():
    import urllib.request

    from scribe3.hermes_evidence.github import API, OfficialGitHubRedirectHandler

    sha = "a" * 40
    handler = OfficialGitHubRedirectHandler()
    original = urllib.request.Request(f"{API}/commits/main")
    unsafe_locations = [
        "https://example.test/repos/NousResearch/hermes-agent/commits/main",
        "https://api.github.com/repos/Other/hermes-agent/commits/main",
        f"https://user:pass@api.github.com/repos/NousResearch/hermes-agent/git/blobs/{sha}",
        f"{API}/git/blobs/{sha}?token=must-not-be-persisted",
        f"{API}/git/trees/../blobs/{sha}",
    ]

    for location in unsafe_locations:
        with pytest.raises(RuntimeError) as caught:
            handler.redirect_request(original, None, 302, "Found", {}, location)
        assert str(caught.value) == "refusing unsafe GitHub redirect"

    safe_location = f"{API}/git/blobs/{sha}"
    redirected = handler.redirect_request(
        original, None, 302, "Found", {}, safe_location
    )
    assert redirected.full_url == safe_location


def test_github_client_revalidates_final_response_url_before_reading_body():
    import io

    from scribe3.hermes_evidence.github import API, GitHubClient

    sha = "a" * 40

    def response(final_url):
        stream = io.BytesIO((f'{{"sha":"{sha}"}}').encode("ascii"))
        stream.headers = {}
        stream.geturl = lambda: final_url
        return stream

    unsafe = GitHubClient(
        opener=lambda request, timeout: response(
            "https://example.test/repos/NousResearch/hermes-agent/commits/main"
        ),
        max_retries=0,
    )
    with pytest.raises(RuntimeError) as caught:
        unsafe.resolve_ref("main")
    assert str(caught.value) == "GitHub API response left the official repository"

    safe = GitHubClient(
        opener=lambda request, timeout: response(f"{API}/commits/main"),
        max_retries=0,
    )
    assert safe.resolve_ref("main") == sha


def test_repository_snapshot_slices_retry_events_per_call_when_client_is_reused(
    tmp_path,
):
    from scribe3.hermes_evidence.github import snapshot_repository

    class FakeClient:
        def __init__(self):
            self.retry_events = [{"event": "old-history"}]
            self.current_ref = None

        def resolve_ref(self, ref):
            self.current_ref = ref
            self.retry_events.append({"event": "resolve", "ref": ref})
            return "a" * 40

        def tree_payload(self, sha):
            self.retry_events.append({"event": "tree", "ref": self.current_ref})
            return {
                "truncated": False,
                "tree": [
                    {
                        "path": "README.md",
                        "type": "blob",
                        "sha": "blob",
                        "size": 4,
                    }
                ],
            }

        def blob(self, sha):
            self.retry_events.append({"event": "blob", "ref": self.current_ref})
            return b"# H\n"

    client = FakeClient()
    release = snapshot_repository(
        client,
        "v1.0.0",
        "release-events",
        tmp_path / "release",
        "2026-07-20T00:00:00+00:00",
    )
    main = snapshot_repository(
        client,
        "main",
        "main-events",
        tmp_path / "main",
        "2026-07-20T00:00:01+00:00",
    )

    assert release.retry_events == [
        {"event": "resolve", "ref": "v1.0.0"},
        {"event": "tree", "ref": "v1.0.0"},
        {"event": "blob", "ref": "v1.0.0"},
    ]
    assert main.retry_events == [
        {"event": "resolve", "ref": "main"},
        {"event": "tree", "ref": "main"},
        {"event": "blob", "ref": "main"},
    ]
    assert client.retry_events == [
        {"event": "old-history"},
        *release.retry_events,
        *main.retry_events,
    ]


def test_repository_snapshot_rejects_concurrent_calls_for_the_same_client(tmp_path):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from scribe3.hermes_evidence.github import snapshot_repository

    class BlockingClient:
        def __init__(self):
            self.retry_events = []
            self.entered = threading.Event()
            self.release = threading.Event()

        def resolve_ref(self, ref):
            self.entered.set()
            assert self.release.wait(timeout=2)
            return "a" * 40

        def tree_payload(self, sha):
            return {"truncated": False, "tree": []}

    client = BlockingClient()
    with ThreadPoolExecutor(max_workers=1) as executor:
        running = executor.submit(
            snapshot_repository,
            client,
            "main",
            "main-running",
            tmp_path / "running",
            "2026-07-20T00:00:00+00:00",
        )
        assert client.entered.wait(timeout=2)
        try:
            with pytest.raises(RuntimeError) as caught:
                snapshot_repository(
                    client,
                    "main",
                    "main-concurrent",
                    tmp_path / "concurrent",
                    "2026-07-20T00:00:01+00:00",
                )
            assert str(caught.value) == (
                "concurrent snapshot calls for one client are not supported"
            )
        finally:
            client.release.set()
        running.result(timeout=2)
