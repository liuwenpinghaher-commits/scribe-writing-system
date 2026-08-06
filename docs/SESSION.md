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
| **HEAD（写入时）** | (本提交) — session 单飞/父史边界 + 技法标尺异步 + 旅程布局 |
| **进行中目标** | 已收口本地 WIP 并 push；等 GHA deploy 后 demo 冒烟 |
| **活跃分支** | `main` |
| **未合并 / WIP** | 无（工作区已清） |

### 最近在做什么

- **会话可靠性（H1/H2/M2/H4）**：
  - 新建/fork 单飞守卫；创建后 `switchThread` 失败可对同 `thread_id` 重试绑定（不二次 create）
  - 归档当前 → 切 `updated_at` 最新 remaining active（`pickLatestActiveThread`）
  - fork 父近窗注入边界标记；`create`/`fork` 写 `created_at`
- **技法标尺**：`segments` map-reduce、异步 import/fingerprint job、multipart 导入；写路径 `craft_briefs_for_write`
- **旅程布局**：仅 journey tab 会话↔详情换位 + `visibleLayoutShares`
- **验证（本机）**：`test_editorial_thread` + `test_quality_references` + `test_reference_craft` + quality api 的 reference/fingerprint/import 共 63 passed；评价端点 10 fail 属本机 Surreal soft-schema / `ORDER BY created_at` 环境问题，与本次 diff 无直接关系
- **前端单测**：Grok 运行机无 `web/node_modules`，未跑 vitest；逻辑有 `sessionThreadOps.test.js` / 既有测试文件，待 CI 或 demo 构建验证

### 下一步（优先序）

1. **push main → 等 `deploy-lighthouse` → demo 冒烟**：会话新建/归档跳转、标尺导入 job、旅程 tab 栏序
2. 若冒烟红：在 demo 已部署栈上看日志修，勿在 Grok 机起重栈
3. Director P0 仍欠 demo 旅程/胶囊冒烟（可与本次一并点）
4. SESSION 旧条目里的 Phase 1 路由抽出仍可择机做（非阻塞）

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
