# Hermes Official Evidence Cache and Capability Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可复现、版本隔离、全量可检索的 Hermes 官方证据库，并完成每项 Hermes 能力对 Scribe3 小说质量第一性目标的代码与运行时审计。

**Architecture:** 新增独立的 `scribe3.hermes_evidence` 工具包，分别负责 Manifest、来源策略、官网抓取、GitHub 固定快照、完整性、版本差异、运行时去敏探测和能力矩阵。现有 `docs/external/hermes-agent-docs/_crawl_hermes_agent_docs.py` 只保留兼容入口；生成的官网、release、main 三套不可变快照统一落入现有缓存根目录。

**Tech Stack:** Python 3.14、stdlib dataclasses/urllib/hashlib/json、Crawl4AI、pytest、GitHub REST API、Hermes HTTP API、Poppler `pdftotext` 26.04.0、Markdown/JSON。

## Global Constraints

- SurrealDB 和 Scribe3 现有领域模型是小说业务数据的唯一持久化权威。
- `CreativeContextEngine` 是业务上下文的唯一规划、检索、协调、装配和验证内核。
- 官方证据缓存不得进入小说业务召回空间，不得包含用户正文、secret、token、cookie、Authorization 或 `.env` 内容。
- 官方来源仅允许 `hermes-agent.nousresearch.com/docs` 和 `github.com/NousResearch/hermes-agent` 及其官方 API/附件。
- 官网、`v2026.7.7.2` release、固定 main SHA、skills corpus、runtime-observed 必须分层，最新主干能力不得冒充本机能力。
- 每个批抓结果按返回对象的 URL 绑定，禁止用结果数组位置配对请求 URL。
- Sitemap/tree 集合不完整、Git tree `truncated=true`、软404、短正文或未解释失败都必须使完整性门失败。
- 保留现有未跟踪 `cache_surrealdb_docs.py` 和 `surrealdb-docs-cache/`，不得修改、暂存或提交。
- 不执行 `hermes update`；本计划只冻结证据和审计当前运行时。
- 不使用可视化伴侣。

## File Structure

### New package

- `scribe3/hermes_evidence/__init__.py`：稳定公共导出。
- `scribe3/hermes_evidence/models.py`：Manifest、文档记录、完整性和能力记录数据模型。
- `scribe3/hermes_evidence/policy.py`：官方来源白名单、路径分类、secret扫描和文档筛选。
- `scribe3/hermes_evidence/website.py`：Sitemap发现、Crawl4AI批抓、Markdown规范化。
- `scribe3/hermes_evidence/github.py`：固定ref、recursive tree、raw blob下载和仓库快照。
- `scribe3/hermes_evidence/integrity.py`：集合、哈希、标题、软404、重复和内部链接验收。
- `scribe3/hermes_evidence/diffing.py`：官网快照差异、release/main路径和内容差异。
- `scribe3/hermes_evidence/runtime_snapshot.py`：当前Hermes去敏版本、CLI和HTTP能力快照。
- `scribe3/hermes_evidence/capability_audit.py`：能力矩阵校验、状态判定和Markdown报告。
- `scribe3/hermes_evidence/cli.py`：`discover/crawl/snapshot/integrity/runtime/audit/all` 命令。
- `scribe3/hermes_evidence/capabilities.yaml`：全能力目录、合法消费者和第一性评价字段。

### Compatibility and generated artifacts

- Modify `docs/external/hermes-agent-docs/_crawl_hermes_agent_docs.py`：转发到新CLI的官网抓取入口。
- Create `docs/external/hermes-agent-docs/README.md`：缓存语义、刷新和检索说明。
- Generate `docs/external/hermes-agent-docs/manifests/*.json`。
- Generate `docs/external/hermes-agent-docs/snapshots/website/{snapshot_id}/pages/**`。
- Generate `docs/external/hermes-agent-docs/snapshots/upstream/v2026.7.7.2/**`。
- Generate `docs/external/hermes-agent-docs/snapshots/upstream/main-{full_sha}/**`。
- Generate `docs/external/hermes-agent-docs/reports/*.md` 与 `current.json`。
- Create `docs/superpowers/2026-07-19-hermes官方证据与能力审计报告.md`。
- Modify `docs/superpowers/specs/2026-07-19-scribe3-creative-quality-os-design.md`：只合入证据充分的Hermes边界优化。

### Tests

- `scribe3/tests/test_hermes_evidence_models.py`
- `scribe3/tests/test_hermes_evidence_sources.py`
- `scribe3/tests/test_hermes_evidence_integrity.py`
- `scribe3/tests/test_hermes_evidence_runtime.py`
- `scribe3/tests/test_hermes_capability_audit.py`
- `scribe3/tests/fixtures/hermes_evidence/sitemap.xml`
- `scribe3/tests/fixtures/hermes_evidence/tree.json`
- `scribe3/tests/fixtures/hermes_evidence/pages/*.md`

---

### Task 1: Stable Manifest Models

**Files:**
- Create: `scribe3/hermes_evidence/__init__.py`
- Create: `scribe3/hermes_evidence/models.py`
- Test: `scribe3/tests/test_hermes_evidence_models.py`

**Interfaces:**
- Produces: `sha256_bytes(data: bytes) -> str`
- Produces: `stable_json_bytes(value: object) -> bytes`
- Produces: `document_id_for(source_kind: str, logical_key: str, content_sha256: str) -> str`
- Produces: `DocumentRecord`, `SnapshotManifest`, `IntegrityReport`, `CapabilityRecord`
- Produces: `write_manifest(path: Path, manifest: SnapshotManifest) -> str`

- [ ] **Step 1: Write failing model tests**

```python
from pathlib import Path

from scribe3.hermes_evidence.models import (
    DocumentRecord, SnapshotManifest, sha256_bytes, write_manifest,
)


def test_manifest_is_stable_and_hashes_exact_bytes(tmp_path: Path):
    doc = DocumentRecord(
        document_id="website:abc",
        source_kind="website",
        output_path="pages/a.md",
        content_sha256=sha256_bytes(b"abc"),
        byte_length=3,
        text_length=3,
        semantic_status="content",
        requested_url="https://hermes-agent.nousresearch.com/docs/a",
        final_url="https://hermes-agent.nousresearch.com/docs/a",
    )
    manifest = SnapshotManifest(
        snapshot_id="website-20260719T000000Z",
        source_kind="website",
        source_origin="https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        requested_ref="sitemap",
        resolved_sha=None,
        release_tag=None,
        fetched_at="2026-07-19T00:00:00+00:00",
        crawler_version="1",
        documents=[doc],
    )
    first = write_manifest(tmp_path / "m1.json", manifest)
    second = write_manifest(tmp_path / "m2.json", manifest)
    assert first == second
    assert (tmp_path / "m1.json").read_bytes() == (tmp_path / "m2.json").read_bytes()
    assert doc.content_sha256 == sha256_bytes(b"abc")
```

- [ ] **Step 2: Run the test and confirm import failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_models.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'scribe3.hermes_evidence'`.

- [ ] **Step 3: Implement the immutable models**

```python
# scribe3/hermes_evidence/models.py
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

SourceKind = Literal["website", "release", "main", "runtime"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    source_kind: SourceKind
    output_path: str
    content_sha256: str
    byte_length: int
    text_length: int
    semantic_status: str
    requested_url: str | None = None
    final_url: str | None = None
    repo_path: str | None = None
    language: str = "en"
    category: str = "core"
    mime_type: str = "text/markdown"
    http_status: int | None = None
    title: str | None = None
    h1: str | None = None
    source_commit: str | None = None
    website_snapshot_id: str | None = None
    is_skill: bool = False
    is_runtime_contract: bool = False
    excluded_reason: str | None = None
    error: str | None = None
    supersedes_document_id: str | None = None
    logical_key: str = ""
    source_blob_sha: str | None = None
    extracted_text_path: str | None = None
    extracted_text_sha256: str | None = None


@dataclass
class SnapshotManifest:
    snapshot_id: str
    source_kind: SourceKind
    source_origin: str
    requested_ref: str
    resolved_sha: str | None
    release_tag: str | None
    fetched_at: str
    crawler_version: str
    documents: list[DocumentRecord] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    exclusions: list[dict] = field(default_factory=list)
    previous_snapshot_id: str | None = None
    notes: list[str] = field(default_factory=list)
    discovery_sha256: str | None = None
    expected_document_count: int | None = None
    tree_truncated: bool | None = None
    filter_policy_version: str = "1"
    retry_events: list[dict] = field(default_factory=list)

    def payload(self) -> dict:
        data = asdict(self)
        data["document_count"] = len(self.documents)
        data["total_bytes"] = sum(d.byte_length for d in self.documents)
        data["success_count"] = len([d for d in self.documents if not d.error])
        data["failed_count"] = len(self.failures)
        data["excluded_count"] = len(self.exclusions)
        data["completeness_status"] = "pass" if not self.failures else "fail"
        return data


@dataclass(frozen=True)
class IntegrityReport:
    snapshot_id: str
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    duplicate_groups: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    name: str
    category: str
    official_evidence_refs: tuple[str, ...]
    documented_in_release: bool
    documented_in_main: bool
    runtime_advertised: bool | None
    runtime_probed: bool | None
    current_scribe_config_refs: tuple[str, ...]
    current_scribe_consumer_refs: tuple[str, ...]
    current_state: str
    first_principle_contribution: str
    authority_risk: str
    quality_hypothesis: str
    decision: str
    verification_plan: str
    rollback_boundary: str
    evidence_confidence: str


def write_manifest(path: Path, manifest: SnapshotManifest) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.payload()
    digest = sha256_bytes(stable_json_bytes(payload))
    payload["manifest_sha256"] = digest
    path.write_bytes(stable_json_bytes(payload))
    return digest


def document_id_for(source_kind: str, logical_key: str, content_sha256: str) -> str:
    identity = sha256_bytes(logical_key.encode("utf-8"))[:16]
    return f"{source_kind}:{identity}:{content_sha256[:16]}"
```

`logical_key` is the normalized requested URL for website documents and the repository path for Git snapshots. Identical content at the same logical key keeps the same `document_id`; a content change produces a new ID and sets `supersedes_document_id` to the previous snapshot's document ID.

```python
# scribe3/hermes_evidence/__init__.py
from .models import CapabilityRecord, DocumentRecord, IntegrityReport, SnapshotManifest

__all__ = ["CapabilityRecord", "DocumentRecord", "IntegrityReport", "SnapshotManifest"]
```

- [ ] **Step 4: Run the focused test**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_models.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit the model layer**

```bash
git add scribe3/hermes_evidence/__init__.py scribe3/hermes_evidence/models.py scribe3/tests/test_hermes_evidence_models.py
git commit -m "feat: add Hermes evidence manifest models"
```

### Task 2: Source Policy and Website Discovery

**Files:**
- Create: `scribe3/hermes_evidence/policy.py`
- Create: `scribe3/hermes_evidence/website.py`
- Create: `scribe3/tests/fixtures/hermes_evidence/sitemap.xml`
- Test: `scribe3/tests/test_hermes_evidence_sources.py`

**Interfaces:**
- Consumes: `sha256_bytes`
- Produces: `is_official_url(url: str) -> bool`
- Produces: `discover_sitemap(xml_bytes: bytes) -> list[str]`
- Produces: `discover_sitemap_snapshot(xml_bytes: bytes) -> SitemapDiscovery`
- Produces: `output_path_for_url(url: str) -> Path`
- Produces: `select_repo_document(path: str) -> bool`
- Produces: `classify_repo_path(path: str) -> tuple[str, str, bool, bool]`
- Produces: `contains_secret(text: str) -> bool`

- [ ] **Step 1: Add discovery and policy tests**

```python
from pathlib import Path

import pytest

from scribe3.hermes_evidence.policy import (
    classify_repo_path, contains_secret, is_official_url, select_repo_document,
)
from scribe3.hermes_evidence.website import discover_sitemap, output_path_for_url


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


def test_official_host_and_output_path_are_fail_closed():
    assert is_official_url("https://hermes-agent.nousresearch.com/docs/a")
    assert is_official_url("https://github.com/NousResearch/hermes-agent")
    assert not is_official_url("https://example.com/copied-doc")
    assert output_path_for_url("https://hermes-agent.nousresearch.com/docs/a/b") == Path("pages/a/b.md")
    with pytest.raises(ValueError):
        output_path_for_url("https://example.com/docs/a")


def test_repo_policy_keeps_docs_and_classifies_skills():
    assert select_repo_document("website/docs/user-guide/features/hooks.md")
    assert select_repo_document("optional-skills/creative/creative-ideation/SKILL.md")
    assert not select_repo_document("agent/run_loop.py")
    assert classify_repo_path("optional-skills/creative/x/SKILL.md") == (
        "en", "optional-skill", True, False,
    )


def test_secret_scanner_rejects_secret_shapes_without_echoing_values():
    assert contains_secret("API_KEY=" + "x" * 32)
    assert contains_secret("Authorization: Bearer " + "x" * 32)
    assert not contains_secret("Use ${API_KEY} from the environment")
```

Fixture:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks</loc></url>
  <url><loc>https://hermes-agent.nousresearch.com/docs/</loc></url>
  <url><loc>https://hermes-agent.nousresearch.com/docs/</loc></url>
</urlset>
```

- [ ] **Step 2: Run and verify failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py -q`

Expected: FAIL because `policy.py` and `website.py` do not exist.

- [ ] **Step 3: Implement source policy**

```python
# scribe3/hermes_evidence/policy.py
from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import urlparse

OFFICIAL_HOSTS = {"hermes-agent.nousresearch.com", "github.com", "api.github.com", "raw.githubusercontent.com"}
DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".adoc", ".pdf"}
SECRET_PATTERNS = (
    re.compile(r"(?i)(?:api[_ -]?key|token|client_secret)\s*[:=]\s*[A-Za-z0-9_\-]{24,}"),
    re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9_\-.]{24,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)


def is_official_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        return False
    if parsed.hostname in {"github.com", "api.github.com", "raw.githubusercontent.com"}:
        return "NousResearch" in parsed.path or "nousresearch" in parsed.path.lower()
    return parsed.path.startswith("/docs")


def contains_secret(text: str) -> bool:
    scrubbed = re.sub(r"\$\{[A-Z0-9_]+\}", "ENV_REF", text)
    return any(pattern.search(scrubbed) for pattern in SECRET_PATTERNS)


def select_repo_document(path: str) -> bool:
    p = PurePosixPath(path)
    if p.suffix.lower() not in DOC_EXTENSIONS:
        return False
    blocked = {"node_modules", "venv", ".git", "dist", "build"}
    return not any(part in blocked for part in p.parts)


def classify_repo_path(path: str) -> tuple[str, str, bool, bool]:
    language = "zh-Hans" if "/i18n/zh-Hans/" in f"/{path}" or path.endswith(".zh-CN.md") else "en"
    if path.startswith("optional-skills/"):
        return language, "optional-skill", True, False
    if path.startswith("skills/"):
        return language, "bundled-skill", True, False
    if path.startswith("website/docs/") or path.startswith("docs/"):
        return language, "core-doc", False, True
    if path.startswith("plugins/"):
        return language, "plugin-doc", False, True
    return language, "project-doc", False, False
```

- [ ] **Step 4: Implement Sitemap discovery and path mapping**

```python
# scribe3/hermes_evidence/website.py
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .policy import is_official_url
from .models import sha256_bytes


@dataclass(frozen=True)
class SitemapDiscovery:
    raw_sha256: str
    urls: tuple[str, ...]
    page_kinds: dict[str, str]


def discover_sitemap(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    urls = {node.text.strip() for node in root.iter() if node.tag.endswith("loc") and node.text}
    invalid = sorted(url for url in urls if not is_official_url(url))
    if invalid:
        raise ValueError(f"Sitemap contains non-official URL(s): {len(invalid)}")
    return sorted(urls)


def discover_sitemap_snapshot(xml_bytes: bytes) -> SitemapDiscovery:
    urls = tuple(discover_sitemap(xml_bytes))
    kinds = {}
    for url in urls:
        path = urlparse(url).path.rstrip("/")
        kinds[url] = "search" if path.endswith("/search") else (
            "directory" if path in {"/docs", "/docs/user-guide", "/docs/developer-guide"}
            else "content"
        )
    return SitemapDiscovery(sha256_bytes(xml_bytes), urls, kinds)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "index"


def output_path_for_url(url: str) -> Path:
    if not is_official_url(url):
        raise ValueError("non-official website URL")
    parts = [part for part in urlparse(url).path.split("/") if part]
    if parts and parts[0] == "docs":
        parts = parts[1:]
    if not parts:
        return Path("pages/index.md")
    return Path("pages", *(_slug(p) for p in parts[:-1]), f"{_slug(parts[-1])}.md")
```

- [ ] **Step 5: Run focused tests and commit**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py -q`

Expected: `4 passed`.

```bash
git add scribe3/hermes_evidence/policy.py scribe3/hermes_evidence/website.py scribe3/tests/test_hermes_evidence_sources.py scribe3/tests/fixtures/hermes_evidence/sitemap.xml
git commit -m "feat: discover official Hermes evidence sources"
```

### Task 3: GitHub Fixed-Ref Snapshotter

**Files:**
- Create: `scribe3/hermes_evidence/github.py`
- Create: `scribe3/tests/fixtures/hermes_evidence/tree.json`
- Modify: `scribe3/tests/test_hermes_evidence_sources.py`

**Interfaces:**
- Consumes: `select_repo_document`, `classify_repo_path`, `DocumentRecord`, `SnapshotManifest`
- Produces: `GitHubClient.resolve_ref(ref: str) -> str`
- Produces: `GitHubClient.tree(sha: str) -> list[dict]`
- Produces: `snapshot_repository(client, ref, snapshot_id, out_root, fetched_at) -> SnapshotManifest`

- [ ] **Step 1: Add a fake-client fixed-ref test**

```python
def test_repository_snapshot_rejects_truncated_tree_and_preserves_paths(tmp_path):
    from scribe3.hermes_evidence.github import snapshot_repository

    class FakeClient:
        def resolve_ref(self, ref): return "a" * 40
        def tree_payload(self, sha):
            return {"truncated": False, "tree": [
                {"path": "README.md", "type": "blob", "sha": "b1", "size": 4},
                {"path": "agent.py", "type": "blob", "sha": "b2", "size": 4},
                {"path": "skills/x/SKILL.md", "type": "blob", "sha": "b3", "size": 5},
            ]}
        def blob(self, sha): return {"b1": b"# H\n", "b3": b"# S\n"}[sha]

    manifest = snapshot_repository(
        FakeClient(), "main", "main-aaaaaaaa", tmp_path, "2026-07-19T00:00:00+00:00",
    )
    assert [d.repo_path for d in manifest.documents] == ["README.md", "skills/x/SKILL.md"]
    assert (tmp_path / "README.md").read_text() == "# H\n"
    assert (tmp_path / "skills/x/SKILL.md").read_text() == "# S\n"
```

Add a second test whose tree contains a `type="commit"` submodule, a Git LFS pointer, a symlink mode, and an oversized attachment. Assert each appears in `manifest.exclusions` with a distinct reason; none is silently counted as a saved document. Add a third test that resolves the same fixed ref twice and asserts identical selected paths and content hashes.

- [ ] **Step 2: Run and verify failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py -q`

Expected: FAIL because `github.py` does not exist.

- [ ] **Step 3: Implement the GitHub client and snapshotter**

```python
# scribe3/hermes_evidence/github.py
from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

from .models import (
    DocumentRecord, SnapshotManifest, document_id_for, sha256_bytes,
    stable_json_bytes,
)
from .policy import classify_repo_path, contains_secret, select_repo_document

API = "https://api.github.com/repos/NousResearch/hermes-agent"
MAX_DOCUMENT_BYTES = 50 * 1024 * 1024


class GitHubClient:
    def _json(self, url: str) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "scribe3-hermes-evidence/1"})
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)

    def resolve_ref(self, ref: str) -> str:
        if len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower()):
            return ref.lower()
        if ref.startswith("v"):
            obj = self._json(f"{API}/git/ref/tags/{ref}")["object"]
            if obj["type"] == "tag":
                obj = self._json(obj["url"])["object"]
            return obj["sha"]
        return self._json(f"{API}/commits/{ref}")["sha"]

    def tree_payload(self, sha: str) -> dict:
        return self._json(f"{API}/git/trees/{sha}?recursive=1")

    def blob(self, sha: str) -> bytes:
        payload = self._json(f"{API}/git/blobs/{sha}")
        if payload.get("encoding") != "base64":
            raise ValueError("unsupported GitHub blob encoding")
        return base64.b64decode(payload["content"])


def snapshot_repository(client, ref: str, snapshot_id: str, out_root: Path,
                        fetched_at: str) -> SnapshotManifest:
    sha = client.resolve_ref(ref)
    tree = client.tree_payload(sha)
    if tree.get("truncated") is not False:
        raise RuntimeError("GitHub recursive tree is truncated")
    docs, failures, exclusions = [], [], []
    for item in sorted(tree.get("tree", []), key=lambda row: row.get("path", "")):
        path = item.get("path", "")
        if item.get("type") == "commit":
            exclusions.append({"repo_path": path, "reason": "git_submodule"})
            continue
        if item.get("type") != "blob" or not select_repo_document(path):
            continue
        if item.get("mode") == "120000":
            exclusions.append({"repo_path": path, "reason": "git_symlink"})
            continue
        if int(item.get("size") or 0) > MAX_DOCUMENT_BYTES:
            exclusions.append({"repo_path": path, "reason": "oversized_attachment"})
            continue
        try:
            body = client.blob(item["sha"])
            if body.startswith(b"version https://git-lfs.github.com/spec/v1"):
                exclusions.append({"repo_path": path, "reason": "git_lfs_pointer"})
                continue
            text = body.decode("utf-8") if not path.lower().endswith(".pdf") else ""
            if text and contains_secret(text):
                failures.append({"repo_path": path, "error": "suspected_secret"})
                continue
            target = out_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            language, category, is_skill, is_contract = classify_repo_path(path)
            docs.append(DocumentRecord(
                document_id=document_id_for(
                    "release" if ref.startswith("v") else "main", path, sha256_bytes(body),
                ),
                source_kind="release" if ref.startswith("v") else "main",
                repo_path=path, output_path=path, content_sha256=sha256_bytes(body),
                byte_length=len(body), text_length=len(text),
                semantic_status="binary_attachment" if path.lower().endswith(".pdf") else "content",
                language=language, category=category, source_commit=sha,
                logical_key=path, source_blob_sha=item["sha"],
                is_skill=is_skill, is_runtime_contract=is_contract,
                mime_type="application/pdf" if path.lower().endswith(".pdf") else "text/markdown",
            ))
        except Exception as exc:
            failures.append({"repo_path": path, "error": type(exc).__name__})
    return SnapshotManifest(
        snapshot_id=snapshot_id, source_kind="release" if ref.startswith("v") else "main",
        source_origin="https://github.com/NousResearch/hermes-agent", requested_ref=ref,
        resolved_sha=sha, release_tag=ref if ref.startswith("v") else None,
        fetched_at=fetched_at, crawler_version="1", documents=docs, failures=failures,
        exclusions=exclusions, discovery_sha256=sha256_bytes(stable_json_bytes(tree)),
        expected_document_count=len(docs) + len(failures) + len([
            row for row in exclusions if row["reason"] in {
                "git_lfs_pointer", "git_symlink", "oversized_attachment",
            }
        ]),
        tree_truncated=False,
    )
```

The production implementation must compute `expected_document_count` from the selected-tree set before downloads rather than infer it from success output. Submodules outside selected document paths remain a tree-level note; selected LFS/symlink/oversized documents require explicit exclusions. GitHub API rate-limit headers and retry events are preserved in the Manifest without storing authentication headers.

For PDF documents, preserve and hash the exact PDF bytes, verify the `%PDF-` signature, then invoke `/opt/homebrew/bin/pdftotext` through an argument vector to create a deterministic UTF-8 sidecar under `_extracted/`. Record the sidecar path/hash/text length. If extraction fails, retain the binary as an explicit `binary_attachment` exclusion from semantic search and fail full-text capability coverage; never pretend zero-length PDF text is a valid article.

- [ ] **Step 4: Run focused tests and commit**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py -q`

Expected: all tests pass.

```bash
git add scribe3/hermes_evidence/github.py scribe3/tests/test_hermes_evidence_sources.py scribe3/tests/fixtures/hermes_evidence/tree.json
git commit -m "feat: snapshot versioned Hermes repository docs"
```

### Task 4: Website Batch Crawler

**Files:**
- Modify: `scribe3/hermes_evidence/website.py`
- Create: `scribe3/tests/fixtures/hermes_evidence/pages/hooks.md`
- Modify: `scribe3/tests/test_hermes_evidence_sources.py`

**Interfaces:**
- Produces: `CrawlPage`
- Produces: `RetryPolicy`, `CrawlCheckpoint`
- Produces: `normalize_markdown(value: object) -> str`
- Produces: `async fetch_with_bounded_retry(urls, fetch_many, policy, checkpoint) -> CrawlBatchResult`
- Produces: `async crawl_website(urls, fetch_many, snapshot_id, out_root, fetched_at) -> SnapshotManifest`

- [ ] **Step 1: Add the out-of-order result regression test**

```python
import asyncio


def test_website_batch_uses_returned_url_not_request_order(tmp_path):
    from scribe3.hermes_evidence.website import CrawlPage, crawl_website

    async def fake_fetch(urls):
        return [
            CrawlPage(url=urls[1], final_url=urls[1], status=200, success=True,
                      markdown="# B\nbody b", title="B", mime_type="text/html"),
            CrawlPage(url=urls[0], final_url=urls[0], status=200, success=True,
                      markdown="# A\nbody a", title="A", mime_type="text/html"),
        ]

    urls = [
        "https://hermes-agent.nousresearch.com/docs/a",
        "https://hermes-agent.nousresearch.com/docs/b",
    ]
    manifest = asyncio.run(crawl_website(
        urls, fake_fetch, "website-test", tmp_path, "2026-07-19T00:00:00+00:00",
    ))
    assert (tmp_path / "pages/a.md").read_text().endswith("# A\nbody a\n")
    assert (tmp_path / "pages/b.md").read_text().endswith("# B\nbody b\n")
    assert not manifest.failures
```

- [ ] **Step 2: Run and verify failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py::test_website_batch_uses_returned_url_not_request_order -q`

Expected: FAIL because `CrawlPage` and `crawl_website` are missing.

- [ ] **Step 3: Implement result-bound crawling**

Append to `website.py`:

```python
from dataclasses import dataclass
from typing import Awaitable, Callable

from .models import DocumentRecord, SnapshotManifest, document_id_for, sha256_bytes
from .policy import contains_secret


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


def normalize_markdown(value: object) -> str:
    text = re.sub(r"\n{3,}", "\n\n", str(value or "").strip())
    return text + "\n" if text else ""


def _h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


async def crawl_website(urls: list[str],
                        fetch_many: Callable[[list[str]], Awaitable[list[CrawlPage]]],
                        snapshot_id: str, out_root: Path, fetched_at: str,
                        discovery_sha256: str | None = None,
                        previous: SnapshotManifest | None = None,
                        retry_events: list[dict] | None = None) -> SnapshotManifest:
    expected = set(urls)
    results = await fetch_many(urls)
    by_url = {page.url: page for page in results}
    docs, failures = [], []
    for url in sorted(expected):
        page = by_url.get(url)
        if page is None:
            failures.append({"requested_url": url, "error": "missing_result"})
            continue
        if not is_official_url(page.final_url):
            failures.append({"requested_url": url, "error": "cross_origin_redirect"})
            continue
        body = normalize_markdown(page.markdown)
        navigation_only = url.rstrip("/").endswith("/search")
        if not page.success or page.status != 200:
            failures.append({"requested_url": url, "error": page.error or f"http_{page.status}"})
            continue
        if contains_secret(body):
            failures.append({"requested_url": url, "error": "suspected_secret"})
            continue
        if len(body.strip()) < 200 and not navigation_only:
            failures.append({"requested_url": url, "error": "short_content"})
            continue
        rel = output_path_for_url(url)
        raw = body.encode("utf-8")
        target = out_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        content_sha256 = sha256_bytes(raw)
        prior = next((item for item in (previous.documents if previous else [])
                      if item.logical_key == url), None)
        document_id = document_id_for("website", url, content_sha256)
        docs.append(DocumentRecord(
            document_id=document_id, source_kind="website",
            requested_url=url, final_url=page.final_url, output_path=rel.as_posix(),
            content_sha256=content_sha256, byte_length=len(raw), text_length=len(body),
            semantic_status="navigation_only" if navigation_only else "content",
            http_status=page.status, title=page.title, h1=_h1(body),
            website_snapshot_id=snapshot_id, mime_type=page.mime_type,
            logical_key=url,
            supersedes_document_id=(prior.document_id if prior and prior.document_id != document_id else None),
            is_skill="/skills/" in url, is_runtime_contract="/developer-guide/" in url,
        ))
    extras = sorted(set(by_url) - expected)
    failures.extend({"requested_url": url, "error": "unexpected_result"} for url in extras)
    return SnapshotManifest(
        snapshot_id=snapshot_id, source_kind="website",
        source_origin="https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        requested_ref="sitemap", resolved_sha=None, release_tag=None,
        fetched_at=fetched_at, crawler_version="1", documents=docs, failures=failures,
        previous_snapshot_id=previous.snapshot_id if previous else None,
        discovery_sha256=discovery_sha256, expected_document_count=len(expected),
        retry_events=list(retry_events or []),
    )
```

- [ ] **Step 4: Add bounded retry and Retry-After tests**

Simulate, without sleeping, these sequences:

- `429` with `Retry-After: 2`, then success;
- `503`, then success;
- timeout on all attempts;
- a permanent `404` that is not retried;
- an interrupted batch after two content-hash-verified pages.

Assert the default maximum is three attempts, exponential backoff is capped, server `Retry-After` wins when valid, jitter is injectable for deterministic tests, and every retry is appended to `retry_events` without response bodies or headers that may contain secrets.

- [ ] **Step 5: Implement atomic checkpoint and resume**

After every batch of at most 40 URLs:

1. fsync each completed page;
2. verify its stored content hash;
3. atomically replace `checkpoint.json`;
4. record completed logical keys and retry history;
5. on resume, reuse only files whose path, size and hash all match;
6. refetch missing or mismatched files;
7. never mark an interrupted snapshot complete.

The Crawl4AI adapter uses maximum concurrency 5 by default, honors a lower configured value and never retries indefinitely.

- [ ] **Step 6: Add content-identity and previous-snapshot tests**

Run two snapshots for the same URL. Identical normalized Markdown must keep the same `document_id`; changed Markdown must produce a different ID and set `supersedes_document_id` to the prior ID. The saved `.md` file contains normalized content only so `content_sha256` is reproducible across snapshot timestamps.

- [ ] **Step 7: Run focused tests and commit**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py -q`

Expected: all tests pass.

```bash
git add scribe3/hermes_evidence/website.py scribe3/tests/test_hermes_evidence_sources.py scribe3/tests/fixtures/hermes_evidence/pages/hooks.md
git commit -m "feat: crawl Hermes docs without result cross-wiring"
```

### Task 5: Integrity and Version Diff Gates

**Files:**
- Create: `scribe3/hermes_evidence/integrity.py`
- Create: `scribe3/hermes_evidence/diffing.py`
- Test: `scribe3/tests/test_hermes_evidence_integrity.py`

**Interfaces:**
- Produces: `classify_semantic_document(record: DocumentRecord, body: bytes) -> tuple[str, ...]`
- Produces: `extract_internal_doc_links(record: DocumentRecord, body: str) -> set[str]`
- Produces: `validate_snapshot(manifest, root, expected_logical_keys, duplicate_explanations) -> IntegrityReport`
- Produces: `diff_manifests(old, new) -> dict[str, list[str]]`

- [ ] **Step 1: Write failing integrity tests**

```python
from scribe3.hermes_evidence.diffing import diff_manifests
from scribe3.hermes_evidence.integrity import validate_snapshot
from scribe3.hermes_evidence.models import DocumentRecord, SnapshotManifest, sha256_bytes


def _manifest(documents):
    return SnapshotManifest("s", "website", "official", "sitemap", None, None,
                            "2026-07-19T00:00:00+00:00", "1", documents=documents)


def test_integrity_fails_missing_expected_and_hash_mismatch(tmp_path):
    body = b"# A\n" + b"x" * 300
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages/a.md").write_bytes(body)
    doc = DocumentRecord(
        "a", "website", "pages/a.md", "0" * 64, len(body), len(body),
        "content", logical_key="a",
    )
    report = validate_snapshot(_manifest([doc]), tmp_path, {"a", "b"})
    assert not report.ok
    assert any("missing expected" in error for error in report.errors)
    assert any("hash mismatch" in error for error in report.errors)


def test_diff_reports_path_add_change_remove():
    old = _manifest([
        DocumentRecord("old-a", "website", "a.md", "1", 1, 1, "content", logical_key="a"),
        DocumentRecord("old-b", "website", "b.md", "2", 1, 1, "content", logical_key="b"),
    ])
    new = _manifest([
        DocumentRecord("new-b", "website", "b.md", "3", 1, 1, "content", logical_key="b"),
        DocumentRecord("new-c", "website", "c.md", "4", 1, 1, "content", logical_key="c"),
    ])
    assert diff_manifests(old, new) == {"added": ["c"], "changed": ["b"], "removed": ["a"]}
```

- [ ] **Step 2: Run and verify failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_integrity.py -q`

Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement the gates**

```python
# scribe3/hermes_evidence/integrity.py
from pathlib import Path

from .models import IntegrityReport, SnapshotManifest, sha256_bytes


def validate_snapshot(manifest: SnapshotManifest, root: Path,
                      expected_logical_keys: set[str],
                      duplicate_explanations: set[frozenset[str]] | None = None) -> IntegrityReport:
    errors, warnings, hashes = [], [], {}
    successes = {d.logical_key or d.document_id for d in manifest.documents}
    failed = {row.get("logical_key") or row.get("requested_url") or row.get("repo_path")
              for row in manifest.failures}
    excluded = {row.get("logical_key") or row.get("requested_url") or row.get("repo_path")
                for row in manifest.exclusions}
    classified = successes | (failed - {None}) | (excluded - {None})
    missing = sorted(expected_logical_keys - classified)
    extra = sorted(classified - expected_logical_keys)
    if missing:
        errors.append(f"missing expected document(s): {len(missing)}")
    if extra:
        errors.append(f"unexpected document(s): {len(extra)}")
    if manifest.failures:
        errors.append(f"manifest failures: {len(manifest.failures)}")
    for doc in manifest.documents:
        path = root / doc.output_path
        if not path.is_file():
            errors.append(f"missing file: {doc.output_path}")
            continue
        digest = sha256_bytes(path.read_bytes())
        if digest != doc.content_sha256:
            errors.append(f"hash mismatch: {doc.output_path}")
        hashes.setdefault(digest, []).append(doc.document_id)
        if doc.text_length < 200 and doc.semantic_status not in {"navigation_only", "binary_attachment"}:
            errors.append(f"unexpected short content: {doc.document_id}")
        if doc.title and doc.h1 and doc.title.casefold() != doc.h1.casefold():
            warnings.append(f"title h1 mismatch: {doc.document_id}")
    duplicates = tuple(tuple(ids) for ids in hashes.values() if len(ids) > 1)
    explained = duplicate_explanations or set()
    unexplained = [group for group in duplicates if frozenset(group) not in explained]
    if unexplained:
        errors.append(f"unexplained duplicate body groups: {len(unexplained)}")
    return IntegrityReport(manifest.snapshot_id, not errors, tuple(errors),
                           tuple(warnings), duplicates)
```

```python
# scribe3/hermes_evidence/diffing.py
from .models import SnapshotManifest


def diff_manifests(old: SnapshotManifest, new: SnapshotManifest) -> dict[str, list[str]]:
    before = {d.logical_key or d.document_id: d.content_sha256 for d in old.documents}
    after = {d.logical_key or d.document_id: d.content_sha256 for d in new.documents}
    return {
        "added": sorted(set(after) - set(before)),
        "changed": sorted(key for key in set(before) & set(after) if before[key] != after[key]),
        "removed": sorted(set(before) - set(after)),
    }
```

Extend `validate_snapshot()` with fail-closed semantic checks for:

- soft 404, login, anti-bot and server-error phrases combined with title/status evidence;
- empty/link-only/navigation-heavy Markdown;
- unexpected short content outside `navigation_only`;
- MIME/extension mismatch;
- title/H1/path conflict severe enough to indicate wrong-page capture;
- cross-origin redirect;
- every internal official documentation link resolving to a cached logical key or a recorded exclusion;
- Manifest `manifest_sha256`, file bytes/hash, snapshot/source-kind isolation and source commit consistency;
- `expected = success union failed union excluded`, followed by the stricter completion rule `failed` must be empty.

Warnings are not allowed to hide G0–G6 failures. Any intentional duplicate or navigation shell needs a persisted explanation keyed by the exact logical-key set.

- [ ] **Step 4: Add semantic, internal-link, and version-isolation tests**

Fixtures must include a healthy article, search shell, soft 404 with HTTP 200, login page, wrong title/H1, link-only page, cross-domain redirect, missing internal link, duplicate body and MIME mismatch. Also construct a release record, main record and runtime record for the same capability and assert the audit cannot merge their evidence tiers.

- [ ] **Step 5: Run a fixed-ref reproducibility test**

Snapshot `v2026.7.7.2` twice into different temporary roots. Assert equal selected logical-key sets, equal blob SHAs, equal content hashes and equal Manifest payload after excluding only `fetched_at`, `snapshot_id`, `previous_snapshot_id` and the Manifest's own hash.

- [ ] **Step 6: Run tests and commit**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_integrity.py -q`

Expected: `2 passed`.

```bash
git add scribe3/hermes_evidence/integrity.py scribe3/hermes_evidence/diffing.py scribe3/tests/test_hermes_evidence_integrity.py
git commit -m "feat: verify Hermes evidence integrity and diffs"
```

### Task 6: CLI, Crawl4AI Adapter, and Legacy Wrapper

**Files:**
- Create: `scribe3/hermes_evidence/cli.py`
- Modify: `docs/external/hermes-agent-docs/_crawl_hermes_agent_docs.py`
- Create: `docs/external/hermes-agent-docs/README.md`
- Modify: `scribe3/tests/test_hermes_evidence_sources.py`

**Interfaces:**
- Produces: `async crawl4ai_fetch_many(urls: list[str]) -> list[CrawlPage]`
- Produces: `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Add CLI dry-run test**

```python
def test_cli_discover_writes_no_snapshot(tmp_path, monkeypatch):
    from scribe3.hermes_evidence import cli
    monkeypatch.setattr(cli, "CACHE_ROOT", tmp_path)
    monkeypatch.setattr(cli, "fetch_bytes", lambda url: Path(
        "scribe3/tests/fixtures/hermes_evidence/sitemap.xml").read_bytes())
    assert cli.main(["discover", "--json"]) == 0
    assert not (tmp_path / "snapshots").exists()
```

- [ ] **Step 2: Run and verify failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py::test_cli_discover_writes_no_snapshot -q`

Expected: FAIL because `cli.py` is missing.

- [ ] **Step 3: Implement the CLI and real Crawl4AI adapter**

`cli.py` must implement these exact commands:

```text
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli discover --json
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli website --concurrency 5 --batch-size 40
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli website --resume
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli repository --ref v2026.7.7.2
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli repository --ref main
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli integrity --all
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli all
```

Use `AsyncWebCrawler.arun_many`, convert every result using `result.url`, `result.redirected_url or result.url`, `result.status_code`, `result.success`, `result.markdown`, `result.metadata["title"]`, and `result.error_message`. Bind results by returned canonical URL and redirect metadata, never by result-array position. Configure primary selector `.theme-doc-markdown`, fallback selector `main`, batches of 40 and maximum concurrency 5. Route 429/5xx/timeout through the bounded retry/checkpoint layer; retry failed/short non-search pages with fallback, but never retry permanent semantic failures indefinitely.

`main()` returns 0 only when the selected operation has no failures and integrity passes; network or semantic failures return 2. `--resume` must require a matching source, filter-policy version, Sitemap hash and snapshot ID; incompatible checkpoints fail rather than being reused.

- [ ] **Step 4: Replace the old crawler body with a compatibility wrapper**

```python
#!/usr/bin/env python3
from scribe3.hermes_evidence.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["website"]))
```

- [ ] **Step 5: Document exact cache semantics**

`README.md` must state: official allowlist, snapshot immutability, release/main/runtime distinctions, refresh commands, integrity command, dynamic search-page semantics, secret exclusion and the rule that skill documents are procedural evidence rather than runtime contracts.

- [ ] **Step 6: Run tests and CLI discovery**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_sources.py -q
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli discover --json
```

Expected: tests pass; discovery prints valid JSON containing the current Sitemap count and writes no snapshot.

- [ ] **Step 7: Commit**

```bash
git add scribe3/hermes_evidence/cli.py docs/external/hermes-agent-docs/_crawl_hermes_agent_docs.py docs/external/hermes-agent-docs/README.md scribe3/tests/test_hermes_evidence_sources.py
git commit -m "feat: add reproducible Hermes evidence cache CLI"
```

### Task 7: Generate and Validate All Official Snapshots

**Files:**
- Generate: `docs/external/hermes-agent-docs/manifests/**`
- Generate: `docs/external/hermes-agent-docs/snapshots/**`
- Generate: `docs/external/hermes-agent-docs/reports/coverage-*.md`
- Generate: `docs/external/hermes-agent-docs/current.json`

**Interfaces:**
- Consumes: the CLI from Task 6
- Produces: three immutable, integrity-passing snapshots and current pointers

- [ ] **Step 1: Record pre-crawl disk and Git baseline**

Run:

```bash
git status --short
du -sh docs/external/hermes-agent-docs
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli discover --json
```

Expected: only intended worktree changes plus the user-owned SurrealDB cache; discovery succeeds.

- [ ] **Step 2: Run the full snapshot command**

Run: `scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli all`

Expected: exit 0; website success equals Sitemap effective-content plus explicit `navigation_only`; release and main trees report `truncated=false`; no failure records.

The `all` command first writes immutable snapshot directories and temporary manifests. It may atomically replace `current.json` only after all three snapshots pass G0–G6. A failed refresh must leave the prior current pointer untouched.

- [ ] **Step 3: Run independent integrity checks**

Run every generated Manifest through:

```bash
for manifest_path in docs/external/hermes-agent-docs/manifests/*.json; do
  scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli integrity --manifest "$manifest_path" || exit 1
done
```

Expected: every command exits 0 with `ok=true`, zero missing files, zero hash mismatches and zero unexplained short pages.

- [ ] **Step 4: Check cache size and secret patterns**

Run:

```bash
du -sh docs/external/hermes-agent-docs
rg -n 'sk-[A-Za-z0-9]{20,}|Authorization: Bearer [A-Za-z0-9_.-]{24,}' docs/external/hermes-agent-docs/snapshots
```

Expected: size is reported; `rg` returns no matches. `${API_KEY}` documentation references are permitted.

- [ ] **Step 5: Report generated scale before staging**

Run:

```bash
find docs/external/hermes-agent-docs/snapshots -type f | wc -l
du -sh docs/external/hermes-agent-docs
git diff --stat -- docs/external/hermes-agent-docs
git status --short -- docs/external/hermes-agent-docs
```

Record exact website/release/main document counts, skill count, bytes, exclusions, retries and Git delta in the task update before any `git add`.

- [ ] **Step 6: Commit immutable snapshots separately**

```bash
git add docs/external/hermes-agent-docs
git commit -m "docs: cache complete versioned Hermes evidence"
```

Before committing, verify `git status --short` does not include `cache_surrealdb_docs.py` or `surrealdb-docs-cache/` in the staged set.

### Task 8: Redacted Runtime Snapshot

**Files:**
- Create: `scribe3/hermes_evidence/runtime_snapshot.py`
- Test: `scribe3/tests/test_hermes_evidence_runtime.py`
- Generate: `docs/external/hermes-agent-docs/manifests/runtime-observed-*.json`

**Interfaces:**
- Produces: `redact(value: object) -> object`
- Produces: `capture_runtime(home: Path, runtimes: dict[str, HermesRuntime]) -> dict`
- Produces: `capture_runtime_contracts(runtimes, isolated_work_id) -> RuntimeContractSnapshot`

- [ ] **Step 1: Write redaction tests**

```python
from scribe3.hermes_evidence.runtime_snapshot import redact


def test_redact_removes_secret_keys_and_authorization_values():
    raw = {"api_key": "secret", "Authorization": "Bearer secret", "features": {"runs": True}}
    assert redact(raw) == {"api_key": "[REDACTED]", "Authorization": "[REDACTED]",
                           "features": {"runs": True}}
```

- [ ] **Step 2: Run and verify failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_runtime.py -q`

Expected: FAIL because module is missing.

- [ ] **Step 3: Implement redacted capture**

`redact()` recursively replaces values whose lowercase keys contain `key`, `token`, `secret`, `password`, `authorization`, `cookie` or `credential`. `capture_runtime()` records:

- `hermes --version` output;
- local Git HEAD/branch/dirty paths, never diff contents;
- `HermesRuntime.probe()` for default/read/write;
- CLI command names from `hermes --help`;
- toolset and skill names/counts;
- observed timestamp.

It must not read `.env` contents or full profile YAML. Serialize only after `redact()` and scan serialized bytes with `contains_secret()`.

- [ ] **Step 4: Add fixture tests for real event-shape normalization**

Use redacted fixtures for Responses SSE, Runs SSE, `approval.request`, tool result, usage, error and Memory Provider lifecycle. Assert runtime evidence preserves event type/order, approval correlation, tool name/result shape, profile/toolset and provider/model identity while replacing IDs, timestamps, durations and secret-bearing values.

- [ ] **Step 5: Probe all claimed current runtime paths**

Against the current, unchanged Hermes installation:

- probe default/read/write health, capabilities and toolsets;
- stream one Responses request;
- stream one read-only Runs request;
- issue one approval-required proposal against an isolated test work, record deny as zero write and approve as a traceable isolated write;
- reconnect to an interrupted stream/session;
- observe Memory Provider initialize/retrieve/store/close lifecycle without reading production content into the report;
- record actual provider/model/fallback identity and usage-field shape;
- record failure and retry semantics for one malformed request.

If a path cannot be safely probed, mark it `runtime_probed=false` with the exact reason. Do not infer success from capability advertisement.

- [ ] **Step 6: Run tests and capture current runtime**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_runtime.py scribe3/tests/test_hermes_runtime.py -q
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli runtime
```

Expected: tests pass; runtime Manifest contains three profiles and no secret values.

- [ ] **Step 7: Commit**

```bash
git add scribe3/hermes_evidence/runtime_snapshot.py scribe3/tests/test_hermes_evidence_runtime.py docs/external/hermes-agent-docs/manifests/runtime-observed-*.json
git commit -m "docs: capture redacted Hermes runtime evidence"
```

### Task 9: Full Capability Matrix and First-Principles Audit

**Files:**
- Create: `scribe3/hermes_evidence/capability_audit.py`
- Create: `scribe3/hermes_evidence/capabilities.yaml`
- Test: `scribe3/tests/test_hermes_capability_audit.py`
- Generate: `docs/external/hermes-agent-docs/reports/capability-matrix-*.md`
- Create: `docs/superpowers/2026-07-19-hermes官方证据与能力审计报告.md`

**Interfaces:**
- Produces: `load_capabilities(path: Path) -> list[CapabilityRecord]`
- Produces: `validate_capabilities(records) -> list[str]`
- Produces: `render_capability_report(records) -> str`

- [ ] **Step 1: Write completeness tests**

```python
from pathlib import Path

from scribe3.hermes_evidence.capability_audit import load_capabilities, validate_capabilities


def test_capability_catalog_has_all_domains_and_no_empty_decisions():
    records = load_capabilities(Path("scribe3/hermes_evidence/capabilities.yaml"))
    assert not validate_capabilities(records)
    assert {r.category for r in records} >= {
        "runtime", "providers", "responses-runs", "sessions", "context",
        "memory", "tools-mcp", "skills-plugins", "orchestration", "operations", "creative-practice",
    }
    assert len({r.capability_id for r in records}) == len(records)
```

- [ ] **Step 2: Run and verify failure**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_capability_audit.py -q`

Expected: FAIL because the module/catalogue do not exist.

- [ ] **Step 3: Implement YAML loading, validation and report rendering**

`validate_capabilities()` returns an error for every record missing any field from `CapabilityRecord`, duplicate ID, illegal state/decision, absent official evidence, missing code/runtime judgment, empty quality hypothesis, empty verification plan or empty rollback boundary.

Allowed states: `used`, `partial`, `configured_only`, `unused`, `incompatible`, `unknown`.

Allowed decisions: `adopt`, `optimize`, `borrow_design`, `defer`, `reject`.

`render_capability_report()` emits one row per capability and dedicated sections for:

- current fully used;
- configured without business consumer;
- main-only future capability;
- authority conflict;
- recommended P0/P1/P2 optimization;
- rejected with reason;
- required runtime/business experiment.

- [ ] **Step 4: Populate every capability domain**

The YAML must contain explicit records for at least:

```text
chat-completions, responses, runs, sse, approval, run-recovery,
profiles, model-provider, credential-pool, fallback, provider-routing, moa,
sessions, checkpoints, trajectory, usage-insights,
prompt-assembly, context-files, context-references, compression, prompt-cache, context-engine-plugin,
memory-provider, memory, honcho,
mcp, toolsets, tool-filtering, tool-search, tool-approval,
skills, plugins, plugin-llm-access, curator,
hooks, cron, batch, persistent-goals, delegation, kanban,
api-server, gateway, multi-profile, dashboard, observability,
doctor, security-audit, backup, update,
creative-ideation, humanizer, research, evaluation-practice
```

Each record must cite a cached document ID; map current code using exact symbols such as `HermesRuntime`, `HermesEventAdapter`, `Scribe3MemoryProvider`, `provision`, `hermesRunInstructions`, `useHermesRunRecovery`, `_assemble_write_instructions`, and `CreativeContextEngine` design location.

- [ ] **Step 5: Run audit validation and render reports**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_capability_audit.py -q
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli audit
```

Expected: test passes; audit exits 0; no `unknown` decision lacks a concrete experiment; Markdown contains every capability ID.

- [ ] **Step 6: Perform runtime truth checks for all `used` and `partial` records**

Use CodeGraph before file reads, then run focused probes. A capability may be marked `used` only when configuration, runtime load, code call and business consumer are all evidenced. Downgrade unsupported claims to `partial`, `configured_only` or `unknown`; do not edit evidence to fit old reports.

- [ ] **Step 7: Commit the matrix and report**

```bash
git add scribe3/hermes_evidence/capability_audit.py scribe3/hermes_evidence/capabilities.yaml scribe3/tests/test_hermes_capability_audit.py docs/external/hermes-agent-docs/reports docs/superpowers/2026-07-19-hermes官方证据与能力审计报告.md
git commit -m "docs: audit all Hermes capabilities against Scribe3"
```

### Task 10: Deepen Creative Context OS with Accepted Findings

**Files:**
- Modify: `docs/superpowers/specs/2026-07-19-scribe3-creative-quality-os-design.md`
- Modify: `docs/superpowers/2026-07-19-hermes官方证据与能力审计报告.md`

**Interfaces:**
- Consumes: complete capability audit
- Produces: evidence-linked Hermes adoption boundaries in Creative Context OS

- [ ] **Step 1: Add only evidence-approved deltas**

The spec update must explicitly record decisions for Context Engine Plugin, Memory Provider lifecycle observability, compression boundaries, hooks/trajectory, Tool Search experiment, batch/goals/delegation/MoA, skills and provider/fallback proof. Every adopted item cites the capability ID and cached evidence path. Rejected items retain reasons.

- [ ] **Step 2: Run a contradiction scan**

Run:

```bash
rg -n 'Hermes|Context Engine|Memory Provider|Tool Search|fallback|MoA|delegation|trajectory|hooks' docs/superpowers/specs/2026-07-19-scribe3-creative-quality-os-design.md docs/superpowers/2026-07-19-hermes官方证据与能力审计报告.md
```

Expected: Hermes never becomes canon/context authority; main-only capabilities are labeled future/unverified; provider fallback is never called official DeepSeek without provider proof.

- [ ] **Step 3: Commit the design deepening**

```bash
git add docs/superpowers/specs/2026-07-19-scribe3-creative-quality-os-design.md docs/superpowers/2026-07-19-hermes官方证据与能力审计报告.md
git commit -m "docs: deepen Creative Context OS with Hermes evidence"
```

### Task 11: Final Verification and Handoff

**Files:**
- Verify all files from Tasks 1-10

- [ ] **Step 1: Run focused evidence tests**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_hermes_evidence_models.py \
  scribe3/tests/test_hermes_evidence_sources.py \
  scribe3/tests/test_hermes_evidence_integrity.py \
  scribe3/tests/test_hermes_evidence_runtime.py \
  scribe3/tests/test_hermes_capability_audit.py -q
```

Expected: all pass.

- [ ] **Step 2: Re-run full integrity and audit**

Run:

```bash
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli integrity --all
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli audit
```

Expected: both exit 0; all snapshot gates pass; all capability records complete.

- [ ] **Step 3: Run impacted runtime regression**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_runtime.py scribe3/tests/test_provision_hermes.py -q
```

Expected: all pass; evidence tools did not alter runtime behavior.

- [ ] **Step 4: Verify repository hygiene**

Run:

```bash
git diff --check
git status --short
git diff --cached --name-only
```

Expected: no whitespace errors; user-owned SurrealDB cache remains untracked and unstaged; no secret or generated cache outside the intended Hermes directory.

- [ ] **Step 5: Record final cache metrics**

Report exact snapshot IDs, refs, document counts, failures/exclusions, bytes, integrity status, audit record count, commits and remaining unverified business experiments. Do not claim runtime upgrade or quality uplift from this plan.

---

## Spec Traceability

| Design requirement | Implementation task | Passing evidence |
|---|---:|---|
| Manifest and content identity | 1, 4 | stable serialization, logical-key/content identity and supersession tests |
| Official allowlist and Sitemap truth | 2 | source-policy, raw Sitemap hash and classification tests |
| Fixed release/main snapshots | 3 | ref resolution, non-truncated tree, blob/LFS/submodule and reproducibility tests |
| Retry, rate limit, interruption recovery | 4, 6 | bounded retry, Retry-After, atomic checkpoint and resume tests |
| G0–G6 integrity gates | 5, 7 | set equality, semantic, internal-link, secret, version-isolation and full-cache reports |
| Website/release/main/skills/runtime separation | 3, 7, 8 | separate immutable manifests and runtime-observed contract snapshot |
| Four-layer current-use proof | 8, 9 | docs, config, code consumer and live runtime probes per capability |
| First-principles quality decision | 9 | full capability catalogue with quality hypothesis, authority risk, decision, verification and rollback |
| Creative Context OS deepening | 10 | evidence-linked accepted/rejected deltas without authority duplication |
| Delivery and Git boundary | 7, 11 | actual cache scale report, secret scan, untouched Surreal cache and intentional commits only |
