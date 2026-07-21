# Hermes 证据库与 SurrealDB/Hermes 升级 SDD 进度

- 分支：`codex/hermes-surreal-upgrade-execution`
- 起点：`31bb5fb`
- 证据库计划：`docs/superpowers/plans/2026-07-19-hermes-official-evidence-cache-and-capability-audit.md`
- 升级计划：`docs/superpowers/plans/2026-07-19-hermes-main-and-surrealdb-320-safe-upgrade.md`
- 用户确认的执行边界：隔离 worktree；允许任务级 commit；所有门通过后再 push。
- 不得触碰主工作树未跟踪的 `cache_surrealdb_docs.py` 和 `surrealdb-docs-cache/`。

## 基线

- 2026-07-19：`test_hermes_runtime.py` + `test_provision_hermes.py`：33 passed，3 条既有警告。
- 2026-07-19：前端 Vitest：80 files / 493 tests passed。

## Hermes 官方证据库与能力审计

- Evidence Task 1: complete (commits 31bb5fb..8405713, review clean; 44 tests passed)
- Evidence Task 2: complete (commits 8405713..982463c, review clean; 32 source tests + 44 model regressions passed)
- Evidence Task 3: complete (commits 982463c..550b28c, final review PASS; 47 source tests + 91 model/source tests passed)
- Evidence Task 4: complete (commits 550b28c..0bc0b60, review clean; 88 source tests passed)
- Evidence Task 5: complete (commits 0bc0b60..372af68, final review PASS; 79 focused tests + 133 model/source regressions passed)
- Evidence Task 6: complete (commits 372af68..d6a6ee6, final review Approved; 262 targeted tests passed; Crawl4AI 0.9.2 doctor + Hermes single-page live smoke passed)
- Evidence Task 7: stopped_sufficient（官网365篇零失败快照已足够支持按需能力审计；`current.json` 从未生成，不标记为 complete）
- Evidence Task 8: narrowed_non_blocking（仅审计 Runs、approval、Memory Provider lifecycle、context boundary、provider identity）
- Evidence Task 9: narrowed_non_blocking（仅审计 Runs、approval、Memory Provider lifecycle、context boundary、provider identity）
- Evidence Task 10: narrowed_non_blocking（仅审计 Runs、approval、Memory Provider lifecycle、context boundary、provider identity）
- Evidence Task 11: pending

2026-07-20 执行边界：官网365篇零失败快照作为按需能力审计的足够证据；不再要求 release/main/website 三套全量快照共同生成 `current.json`，不再运行 `scribe3.hermes_evidence.cli all`。Evidence Task 11 不再把全量镜像完整性作为业务实施前置门。

## 小说质量 P0 运行时基础

- 计划：`docs/superpowers/plans/2026-07-20-scribe3-quality-p0-runtime-foundation.md`
- Quality Runtime Task 1: complete（commits 4346d01..069d2ed，复审 Approved；冻结过度证据抓取并重排进度）
- Quality Runtime Task 2: complete（commits 37c2879..43fe328，复审 Approved；51 passed，`0 = unlimited` 且一致快照）
- Quality Runtime Task 3: complete（commits c069441..ee35187，复审 Approved；2 files / 23 tests passed）
- Quality Runtime Task 4: complete（commits 7611a4d..451753f，三轮复审 Approved；25 client + 14 settings tests passed）
- Quality Runtime Task 5: complete（commits 0b55d69..b5b8f02，三轮复审 Approved；87 route + 3 Hermes boundary tests passed）
- Quality Runtime Task 6: complete（commits 9cbbc47..0d54143，四轮复审 Approved；104 backend + 36 frontend tests passed）
- Quality Runtime P0 final fixes: complete（commit 223d586，限定6项复审 READY；495 backend + 41 frontend tests passed，Vite build成功）

## Creative Context OS 纵向能力建设

- 实施计划：`docs/superpowers/plans/2026-07-20-creative-context-vertical-slice.md`
- Creative Context Task 1: complete（commits 197a061..86fa24e，复审 Approved；43 passed）
- Creative Context Task 2: complete（commits 86fa24e..491319f，复审 Approved；9 storage/migration + 5 redactor tests passed）
- Creative Context Task 3: complete（commits 491319f..511a44e，独立复审 Ready；338 focused + 336 app + 513 frontend tests passed，Vite build成功）

## Hermes main / SurrealDB 3.2.0 安全升级

- 2026-07-19 用户指令：先跳过全部 SurrealDB / Hermes Agent 升级、canary、服务切换和生产数据动作；仅继续证据缓存与能力审计。

- Upgrade Task 1: deferred by user
- Upgrade Task 2: deferred by user
- Upgrade Task 3: deferred by user
- Upgrade Task 4: deferred by user
- Upgrade Task 5: deferred by user
- Upgrade Task 6: deferred by user
- Upgrade Task 7: deferred by user
- Upgrade Task 8: deferred by user
- Upgrade Task 9: deferred by user
- Upgrade Task 10: deferred by user
- Upgrade Task 11: deferred by user
- Upgrade Task 12: deferred by user

## Review ledger

- Minor findings: Evidence Task 4 review — `website.py` now combines retry scheduling, soft-error classification, safe filesystem/checkpoint persistence, and crawl orchestration; helpers remain understandable, but final whole-branch review must decide whether module extraction is warranted after correctness fixes.
- Minor findings: Evidence Task 4 re-review — exact error-like titles/H1 could false-positive on legitimate failure-handling documentation; controller elected to fix this within Task 4 rather than defer it.
- Minor findings: Evidence Task 4 final review — one fd-count regression permits a +2 single-run tolerance; reviewer verified descriptor/parent/root finally paths and found no actual leak. Final whole-branch review should decide whether stricter repeated-count coverage is warranted.
- Minor findings: Evidence Task 5 review — `integrity.py` imports Task 4 private semantic/safe-I/O helpers; final whole-branch review must decide whether to promote stable package-internal `semantics`/`safe_io` modules after behavior is proven.
- Minor findings: Evidence Task 5 review — implementation and tests are large mixed-responsibility files; final whole-branch review must triage a behavior-preserving split only after correctness gates pass.
- Minor findings: Evidence Task 5 review — task report was accidentally committed outside the plan's product-file set; controller elected to untrack it in the fix wave while preserving the local report.
- Minor findings resolved: Evidence Task 5 local report now leads with the authoritative split-path and structured-explanation contract; historical RED/GREEN text is explicitly labeled non-authoritative.
- Minor findings: Evidence Task 6 review — `cli.py` combines adapter, cache state, operations, and argparse; final whole-branch review must triage a behavior-preserving internal split after runtime proof.
- Minor findings: Evidence Task 6 review — filter-policy version has duplicate authorities in models/CLI; controller elected to unify this in the fix wave.
- Open blockers: none
- Deferred cross-task checks: real-network GitHub/PDF extraction proof and recall-space isolation are owned by Evidence Tasks 7 and 8; main-worktree SurrealDB cache paths verified untracked after Task 1.
- Deferred cross-task checks: redirect-final URL revalidation and page-body secret scanning are owned by Evidence Tasks 4 and 6.
- Deferred cross-task checks from Evidence Task 4 review: real Crawl4AI concurrency is owned by Task 6; live Sitemap completeness and full snapshot gates are owned by Tasks 5 and 7; business recall/CreativeContextEngine isolation and release/main/runtime whole-branch separation are owned by Tasks 7-11. Controller confirms no Hermes update was executed in Tasks 1-4.
