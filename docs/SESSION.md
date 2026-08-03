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
| **更新于** | 2026-08-03 |
| **默认分支** | `main` |
| **HEAD（写入时）** | (this commit) — feat: EventSource ?token= + query→Bearer bridge |
| **进行中目标** | 登录门完整（fetch + SSE）；下一阶段 Phase 1 路由抽出 |
| **活跃分支** | `main` |
| **未合并 / WIP** | 无 |

### 最近在做什么

- **登录页落地**：`Login.jsx` + `App.jsx` 鉴权门（checking / ok / need_login）。
- **Bearer 注入**：`authFetch.js` 全局 `fetch` 包装；localStorage `s3-api-token`；401 → 清 token + `s3-auth-required`。
- **EventSource token（本轮）**：
  - 前端 `withTokenQuery(url)` 给 SSE URL 挂 `?token=`（浏览器 EventSource 无法设 header）。
  - 覆盖：`aiRunEvents`、`live`、`chatStream`、`materialImportProgressUrl`（api.js 待本提交或紧随提交）。
  - 后端 `scribe3/api/token_bridge.py` 最外层 middleware：无 Authorization 时从 query `token` 注入 `Authorization: Bearer`，现有 app_impl auth 不变。
  - `app.py` 入口 `install_token_query_bridge(_impl.app)`（Phase 1 风格，不动 554k app_impl）。
- 空 token 仍本地放行（与后端 `SCRIBE3_API_TOKEN` 空=不鉴权一致）。

### 下一步（优先序）

1. 确认 api.js 四处 EventSource 已包 `withTokenQuery`（若本提交未含则立即补）。
2. 可选：token helpers 收敛 / Login 内联副本清理。
3. **promises / clues 抽出** → `scribe3/api/promises.py`（原 Phase 1 路线）。
4. 有条件时在 app_impl 物理删除已抽出的 health/intent 内联函数（非阻塞；554k 巨石）。

### 已知坑 / 禁止事项（滚动）

- 不要提交 `artifacts/`、`surrealdb-docs-cache/`、`.codegraph/`、密钥、本地 DB。
- 根目录 `交付说明.md` 是早期 SQLite/`scribe/` **归档**，不是现行手册。
- 设计蓝图在 `设计文档/` 可能过期；冲突以 [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md) + 代码为准。
- 服务端从国内拉 GitHub 不可靠 → 部署走 CI scp，不要假设服务器能 `git pull`。
- SESSION 表里的 HEAD 容易过时：每次实质提交后立刻改并 push。
- **app_impl.py ~554k**：GitHub Contents API 整文件更新不现实；大块搬迁用入口接线 / 路由剥除，或本地 clone 后小 diff PR。保持 auth middleware、emergency_rest_write、`_store_for` / `app.state.store_for` 不动。
- 公网部署务必设非空 `SCRIBE3_API_TOKEN`；前端登录页只挡 UI，真正门在后端 middleware。
- Query token 会出现在浏览器 Network / 可能代理日志；单共享 secret 场景可接受。可选后续只对 SSE 路径前缀接受 `?token=`。

### 最近决策（一句话）

- 跨会话状态不靠对话记忆，靠 Git 里的滚动 `docs/SESSION.md` + 长期 `AGENTS.md`。
- 登录不引入多用户：单共享 Bearer，与现有 `SCRIBE3_API_TOKEN` 对齐。
- fetch 层全局拦截优于改 554 行 api.js 每个 wrapper（可后续再内聚）。
- EventSource 用 `?token=` + 入口桥接注入 Authorization，避免动 app_impl 554k。

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
- [x] 新坑已写入「已知坑」（query token 可见性）
- [x] 重要决策已一句话记下
- [ ] 已 `git push`，下一会话能拉到最新 SESSION
