# SESSION.md · 跨会话交接（滚动状态）

> **用途**：本仓库唯一跨会话记忆。新会话先读 [`AGENTS.md`](../AGENTS.md)（长期规则）+ **本文件**（当前进度），再动手。
>
> **维护**：每次有实质进展或结束工作前，更新下方「当前状态」区块并提交。只改事实，不堆长文。

---

## 新会话开场（复制粘贴）

```
继续 https://github.com/liuwenpinghaher-commits/scribe-writing-system
先读 AGENTS.md 和 docs/SESSION.md，再继续。
```

---

## 当前状态

| 项 | 值 |
|----|----|
| **更新于** | 2026-08-06 |
| **默认分支** | `main` |
| **HEAD（写入时）** | (本提交) — 旅程 5 万字 v2 执行结案 |
| **进行中目标** | v2 书 `book_2524fd8a` 50165 字已交付；可选收紧 craft skip residual |
| **活跃分支** | `main` |
| **未合并 / WIP** | 无 |

### 最近在做什么

- **会话可靠性（H1/H2/M2/H4）**：
  - 新建/fork 单飞守卫；创建后 `switchThread` 失败可对同 `thread_id` 重试绑定（不二次 create）
  - 归档当前 → 切 `updated_at` 最新 remaining active（`pickLatestActiveThread`）
  - fork 父近窗注入边界标记；`create`/`fork` 写 `created_at`
- **技法标尺**：`segments` map-reduce、异步 import/fingerprint job、multipart 导入；写路径 `craft_briefs_for_write`
- **旅程布局**：仅 journey tab 会话↔详情换位 + `visibleLayoutShares`
- **验证（本机）**：`test_editorial_thread` + `test_quality_references` + `test_reference_craft` + quality api 的 reference/fingerprint/import 共 63 passed；评价端点 10 fail 属本机 Surreal soft-schema / `ORDER BY created_at` 环境问题，与本次 diff 无直接关系
- **前端单测**：Grok 运行机无 `web/node_modules`，未跑 vitest；逻辑有 `sessionThreadOps.test.js` / 既有测试文件，待 CI 或 demo 构建验证

### Demo 冒烟（2026-08-06，已部署栈）

- `GET /api/health` `/api/ready` 200；L1 登录 cookie 后：
  - `POST /chat/threads` 写 `created_at`、无 parent；`POST .../fork` 有 parent + `created_at`
  - `GET /references`、`/references/approved-fingerprints` 200
  - `GET /workflow/snapshot` 200（旅程 stations 有 current）
- 前端构建产物含「技法标尺」文案
- 注：GHA `deploy-lighthouse` #53（e0edbcb）当时仍在 rsync；冒烟时容器已含会话边界/async_job/segments（早前 rebuild 已带入）

### 最近在做什么（2026-08-06 续）

- **验收方案定稿**：[`docs/e2e-director-journey-5w.md`](./e2e-director-journey-5w.md) — Director 五站全链路 + 约 5 万字真连载；工艺/导演/质量/规模/缺陷五线 PASS；禁字数单门闩。
- **进度台账**：[`设计文档/2026-08-06-旅程5万字-进度.md`](../设计文档/2026-08-06-旅程5万字-进度.md)（执行未开始）。

### 旅程 5 万字（v2 已执行）

- **主书**：`book_2524fd8a`《旅程五站·v2·20260806》**50165 字 / 10 章**（书库列表可见）  
- **真路径**：`EMERGENCY=0`；世界写 = orchestration **approve+execute**；REST 角色 403  
- **迁移**：Surreal 2.1 修复后 **SCHEMA_SOFT=0 可建书**  
- **证据**：`docs/e2e-journey-5w-run-v2-20260806.md`；demo artifacts `e2e-journey-5w-v2-20260806-book_2524fd8a`  
- **v1** 作废；空壳 `…-A` 已归档  

### 下一步（优先序）

1. 浏览器打开 demo 选 **旅程五站·v2·20260806** 确认正文  
2. 可选：减少 craft skip residual、加强 pilot 全文生成  
3. Phase 1 路由抽出（非阻塞）

### 已知坑 / 禁止事项（滚动）

- 不要提交 `artifacts/`、`surrealdb-docs-cache/`、`.codegraph/`、密钥、本地 DB。
- 根目录 `交付说明.md` 是早期 SQLite/`scribe/` **归档**，不是现行手册。
- 设计蓝图在 `设计文档/` 可能过期；冲突以 [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md) + 代码为准。
- 服务端从国内拉 GitHub 不可靠 → 部署走 CI scp，不要假设服务器能 `git pull`。
- SESSION 表里的 HEAD 容易过时：每次实质提交后立刻改并 push。
- **app_impl.py ~554k**：GitHub Contents API 整文件更新不现实；大块搬迁用入口接线 / 路由剥除。
- 公网部署务必设非空 `SCRIBE3_API_TOKEN` / L1 AUTH；前端登录页只挡 UI。
- Query token 会出现在浏览器 Network；可选后续只对 SSE 路径前缀接受 `?token=`。
- Grok 运行机 **1.6G 无 swap 友好**：禁止本机 `npm ci` / 全量 vitest / 临时 Surreal 全量集成；验收打 **已部署 demo**。

### 最近决策（一句话）

- 跨会话状态靠 Git 里的滚动 `docs/SESSION.md` + 长期 `AGENTS.md`。
- 会话创建绑定失败必须用户可见并可重试同 id，禁止静默停旧会话。
- 参考作品产品名对齐为「技法标尺」；分析必须分段覆盖全书。
- 旅程 tab 换位是横切特例，不改其它 view/阶段全局栏序。
- **5 万字旅程验收**：Director 五站为轴；PASS = 导演+工艺+质量+规模+缺陷五线；禁止字数单门闩。

---

## 必读索引（勿在本文件重复长文）

| 文档 | 何时读 |
|------|--------|
| [`AGENTS.md`](../AGENTS.md) | 每次会话：主线、命令、写路径、卫生 |
| [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md) | 动架构 / 路径 / 写通道前 |
| [`ARCHITECTURE_SPLIT_ROADMAP.md`](./ARCHITECTURE_SPLIT_ROADMAP.md) | Phase 1 路由拆出顺序 |
| [`PR_TEST_BASELINE.md`](./PR_TEST_BASELINE.md) | 开 PR / 本地门禁 |
| [`scribe3/README.md`](../scribe3/README.md) | 怎么跑主线 |
| [`scribe3/AGENTIC_BOUNDARY_DECISION.md`](../scribe3/AGENTIC_BOUNDARY_DECISION.md) | Agent 写世界状态边界 |

---

## 更新清单（会话结束前）

- [x] 「当前状态」表格日期与 HEAD 已刷新
- [x] 「进行中目标 / 下一步」与真实进度一致
- [x] 新坑已写入「已知坑」（Grok 机资源）
- [x] 重要决策已一句话记下
- [ ] 已 `git push`，下一会话能拉到最新 SESSION
