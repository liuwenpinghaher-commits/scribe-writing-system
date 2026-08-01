# 全量真人作者验收总控 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可重复的全量真人作者验收总控，证明每条专项旅程都通过真实 UI、TokenPlan/Qwen、Hermes/MCP 审批及 SurrealDB 只读回查，并在失败时留下可诊断证据。

**Architecture:** 总控不直接写任何正典；它以子进程顺序执行现有的隔离书真人旅程，每个子项独立产出 JSON。汇总器只接受显式成功结果、并将模型身份、工作 slug、artifact 路径与失败原因写为不可混淆的总报告。长篇 5 万字另作为显式长程阶段，不能以短链通过代替。

**Tech Stack:** Node.js、Playwright、现有 `web/e2e/*.mjs`、FastAPI、Hermes MCP、SurrealDB。

## Global Constraints

- 真人世界写入只能走网页 → Hermes `s3_*` → 作者批准；总控只读结果，不得用 REST 灌入正典。
- 所有真实模型断言必须为 `provider=qwen`、`model=qwen3.8-max-preview`、非空 `provider_request_id` 与正 usage。
- 每条短链使用独立作品；不得复用旧 `book_*` 或把字数作为质量通过条件。
- 失败立即保留结构化 artifact 并返回非零；不吞错、不降级为“部分通过”。

---

### Task 1: 统一专项旅程启动条件

**Files:**
- Modify: `scribe3/web/e2e/material_import_author_consumption.mjs`
- Modify: `scribe3/web/e2e/stream_stop_partial_recovery.mjs`
- Test: `scribe3/web/e2e/material_import_author_consumption.test.mjs`
- Test: `scribe3/web/e2e/stream_stop_partial_recovery_result.test.mjs`

- [x] 写会失败的静态回归测试，禁止以 `networkidle` 判定带 SSE 的页面可用。
- [x] 运行 `node --test e2e/material_import_author_consumption.test.mjs e2e/stream_stop_partial_recovery_result.test.mjs`，确认 RED。
- [x] 改用 `domcontentloaded` 加具体 UI 控件等待。
- [x] 重跑同一命令，确认 GREEN（10 passed）。

### Task 2: 全量总控的结果契约

**Files:**
- Create: `scribe3/web/e2e/full_author_acceptance_result.mjs`
- Test: `scribe3/web/e2e/full_author_acceptance_result.test.mjs`

- [ ] 写失败测试：仅在所有条目显式 `ok:true`，且 Qwen 证据完整时汇总为通过；缺 artifact、缺模型证据或任一非零子项必须失败。
- [ ] 运行 `node --test e2e/full_author_acceptance_result.test.mjs`，确认 RED。
- [ ] 实现纯结果归一化与报告写入 helper，不包含浏览器操作或世界写入。
- [ ] 重跑同一命令，确认 GREEN。

### Task 3: 全量短链总控

**Files:**
- Create: `scribe3/web/e2e/full_author_acceptance.mjs`
- Test: `scribe3/web/e2e/full_author_acceptance.test.mjs`
- Modify: `Makefile`

- [ ] 写失败测试，要求总控覆盖字段/图谱/演绎、素材、跨会话记忆、流式恢复、参考质量，并明确把 5 万字放入独立 long-run 阶段。
- [ ] 实现顺序子进程调度，为每项传入独立 artifact 路径；发生失败时中止后续子项，写总报告并返回非零。
- [ ] 新增 `make e2e-author-acceptance-short`，仅本机真调且不纳入无凭证 CI。
- [ ] 运行 Node 契约测试。

### Task 4: 运行短链真人验收并修复

**Files:**
- Modify only the failed journey or its真实产品路径
- Artifact: `artifacts/e2e-current/full-author-acceptance-*.json`

- [ ] 启动后端、前端与 scribe3 Hermes profile，先检查健康与运行模型身份。
- [ ] 运行短链总控；逐个分析非零结果，不用 mock 或 REST 旁路修复。
- [ ] 对每个修复增加回归测试并重跑该专项旅程。

### Task 5: 5 万字长程闭环

**Files:**
- Modify: `scribe3/web/e2e/hq_wordcount_push.mjs` 或拆出的长程控制器
- Test: 对应 Node 测试

- [ ] 新建隔离书，不使用旧默认 work。
- [ ] 逐章通过 Gate A/B/C、质量合同、参考/素材消费、TokenPlan trace；20 章后仅以 SurrealDB 回读的总字数 >= 50000 结案。
- [ ] 注入并验证刷新/重启、取消/部分稿、SSE 回放与并发冲突场景。
- [ ] 输出章节矩阵、质量趋势与所有真实调用证据。

### Task 6: 完成审计

- [ ] 执行相关 Node、前端、后端门禁。
- [ ] 对照本计划逐项检查 artifact、模型证据与真实回读；任何未做项保留为 partial/not_done。
- [ ] 未经新授权不提交、push 或清理其他 agent 的脏改动。
