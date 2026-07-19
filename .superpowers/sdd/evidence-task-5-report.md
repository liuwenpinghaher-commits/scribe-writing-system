# Evidence Task 5 报告：Integrity and Version Diff Gates

## 状态

已完成。仅实现 Task 5 的完整性校验、版本 diff 与测试；未执行真实外网抓取、Hermes/SurrealDB 升级、服务切换、数据库动作，也未触碰主工作树 Surreal cache。

## 实现内容

- 新增 `validate_snapshot()`：
  - 要求并验证 `root/manifest.json` 的规范序列化、`manifest_sha256` 和内存 Manifest payload 一致性；
  - 校验 expected 集合等于 success/failed/excluded 的无重叠精确分区，并强制 failures 为空、`document.error` 为空；
  - 使用 no-follow、目录身份复核、`O_NONBLOCK` 与 `fstat` 的安全普通文件读取，拒绝 symlink、path escape、FIFO 和其他特殊文件；
  - 复核实际 bytes、SHA-256、byte/text length、UTF-8、PDF/sidecar、Git Blob SHA-1、source commit、source kind、release tag/ref 与 snapshot identity；
  - 扫描正文和 Manifest secret，错误报告不回显不可信 logical key、路径或 secret；
  - 复用 Task 4 的 `_semantic_soft_error` 与 Markdown 规范化语义，拒绝 soft 404/login/anti-bot/server error、空白、纯链接、导航过重、短正文、MIME 错配、跨域 redirect、严重 title/H1/path 冲突；
  - 闭合 inline/reference-style/HTML/autolink 的 website/repository 内链；目标必须存在于缓存成功集或带理由 exclusion；
  - duplicate/navigation explanation 必须精确匹配，并以 logical-key 集合的稳定摘要写入 Manifest `notes`，纳入 Manifest 自哈希边界。
- 新增 `classify_semantic_document()` 与 `extract_internal_doc_links()`。
- 新增 `diff_manifests()`：报告 added/changed/removed，拒绝跨 website/release/main/runtime 层比较、Manifest 内 source-kind 冲突和重复 logical key。
- 固定 ref 可复现测试使用受控 fake GitHub adapter 对 `v2026.7.7.2` 连续快照两次，比较 logical keys、Blob SHAs、content hashes，以及只剔除 `fetched_at`、`snapshot_id`、`previous_snapshot_id`、`manifest_sha256` 后的序列化 Manifest payload。

## 文件

- `scribe3/hermes_evidence/integrity.py`
- `scribe3/hermes_evidence/diffing.py`
- `scribe3/tests/test_hermes_evidence_integrity.py`
- `.superpowers/sdd/evidence-task-5-report.md`

## TDD RED / GREEN 证据

1. 基础模块与 diff
   - RED：`scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_integrity.py -q`
   - 关键输出：`ModuleNotFoundError: No module named 'scribe3.hermes_evidence.diffing'`，`1 error`。
   - GREEN：同命令；`2 passed in 0.03s`。
2. 语义与内链接口
   - RED：同命令；`ImportError: cannot import name 'classify_semantic_document'`，`1 error`。
   - GREEN：同命令；`11 passed in 0.05s`。
3. 完整性与隔离门
   - RED：同命令；`7 failed, 13 passed in 0.13s`。失败对应导航说明、size/text/secret、symlink/逃逸、Manifest hash、内链/错页、分区、source 层混合。
   - GREEN：同命令；`20 passed in 0.06s`。
4. diff 分层与 fixed-ref fixture
   - RED：同命令；`1 failed, 21 passed in 0.10s`，跨层 diff 未拒绝。
   - GREEN：同命令；`22 passed in 0.07s`。
5. 自审补强
   - RED：同命令；`2 failed, 22 passed in 0.12s`，实际 H1 与 exclusion reason 未校验。
   - GREEN 中间态：规范化 fixture 后 `24 passed in 0.09s`。
   - 脱敏定向 RED：`...::test_validate_snapshot_requires_exclusion_reason_and_never_echoes_secrets -q`；`1 failed`，定位 text-length 错误回显 logical key。
   - 脱敏定向 GREEN：同命令；`1 passed in 0.04s`。
6. 只读代码审查整改
   - RED：focused 命令；`6 failed, 24 passed in 0.46s`，覆盖 Git Blob 绑定、document.error、解释持久化、标准链接、错页防误报、FIFO 阻塞。
   - 第一版 GREEN 检查暴露过严错页判定：`4 failed, 26 passed in 0.14s`。
   - 最终 GREEN：focused 命令；`30 passed in 0.08s`。

## 最终验证

- `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_integrity.py -q`
  - `30 passed in 0.08s`
- `scribe3/.venv/bin/python -m pytest scribe3/tests/test_hermes_evidence_models.py scribe3/tests/test_hermes_evidence_sources.py -q`
  - `132 passed in 0.26s`
- `scribe3/.venv/bin/python -m compileall -q scribe3/hermes_evidence/integrity.py scribe3/hermes_evidence/diffing.py`
  - 退出码 0。
- `git diff --check`
  - 退出码 0。

## 自审

- 对照简报逐项检查了健康文章、搜索壳、HTTP 200 soft 404、login、anti-bot、server error、正常 404/login 教程防误报、错 title/H1/path、纯链接、跨域 redirect、缺失内链、重复正文、MIME、symlink、path escape、FIFO、secret 残留、release/main/runtime 同 capability 分层。
- 只读审查最初报告 6 个 Important；已全部加入失败测试并修复。最终无已知 Critical/Important 遗留。
- Task 4 软错误规则没有复制；Task 5 直接共享其判定和安全目录 helper，只增加了非阻塞普通文件读取薄层。
- 未修改 Task 1–4 上游模型或接口，未修改业务召回、SurrealDB 或 CreativeContextEngine。

## 疑虑与边界

- fixed-ref 结果只证明受控 fake GitHub adapter/fixture 的可复现性；真实 GitHub/PDF 两次快照属于 Task 7，本任务未执行、也不声称已验证。
- 当前模型没有结构化 explanation 字段，因此采用 `SnapshotManifest.notes` 中 `integrity_explanation_sha256:<digest>` 作为受 `manifest_sha256` 保护的持久化边界；调用参数必须与这些摘要精确一致。
- Task 5 复用了 Task 4 包内私有安全 helper；这是为避免越界重构 Task 4。若后续公开 API，需要由独立任务统一提升为稳定公共 helper。

## 提交

- 提交消息：`feat: verify Hermes evidence integrity and diffs`
- 本报告与实现将进入同一提交；提交 SHA 无法自包含于其自身内容，最终回执给出实际 SHA。
- 不 push。
