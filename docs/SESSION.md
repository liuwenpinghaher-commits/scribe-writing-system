# SESSION.md · 跨会话交接（滚动状态）

> **用途**：本仓库无跨会话记忆。新会话先读 [`AGENTS.md`](../AGENTS.md)（长期规则）+ **本文件**（当前进度），再动手。
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
| **HEAD（写入时）** | `6dfcd1a3` — docs(README): list SESSION.md in 现行必读 for cross-session handoff |
| **进行中目标** | （无；跨会话交接模板与索引已打通） |
| **活跃分支** | `main`（另有 `codex/*`、`feat/*`、`fix/*`、`refactor/*` 等专题分支） |
| **未合并 / WIP** | 无 |

### 最近在做什么

- 部署链路：GHA 打包 tarball + scp 到服务器（避免整树 scp / 服务端 git pull 不稳）。
- 公网仅 80：路径反代 `/zhuanfang` → 访谈栈 `:3210`。
- 主线产品仍在 **`scribe3/`**（SurrealDB + FastAPI + MCP + React）。
- **本会话完成**：`docs/SESSION.md` 跨会话交接模板定稿；`AGENTS.md` 与 `docs/README.md` 已挂索引。

### 下一步（优先序）

1. （待填：下一会话目标）
2. （待填）
3. （待填）

### 已知坑 / 禁止事项（滚动）

- 不要提交 `artifacts/`、`surrealdb-docs-cache/`、`.codegraph/`、密钥、本地 DB。
- 根目录 `交付说明.md` 是早期 SQLite/`scribe/` **归档**，不是现行手册。
- 设计蓝图在 `设计文档/` 可能过期；冲突以 [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md) + 代码为准。
- 服务端从国内拉 GitHub 不可靠 → 部署走 CI scp，不要假设服务器能 `git pull`。
- SESSION 表里的 HEAD 容易过时：每次实质提交后立刻改并 push，否则下一会话会读到陈旧 SHA。

### 最近决策（一句话）

- 跨会话状态不靠对话记忆，靠 Git 里的滚动 `docs/SESSION.md` + 长期 `AGENTS.md`。

---

## 必读索引（勿在本文件重复长文）

| 文档 | 何时读 |
|------|--------|
| [`AGENTS.md`](../AGENTS.md) | 每次会话：主线、命令、写路径、卫生 |
| [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md) | 动架构 / 路径 / 写通道前 |
| [`PR_TEST_BASELINE.md`](./PR_TEST_BASELINE.md) | 开 PR / 本地门禁 |
| [`scribe3/README.md`](../scribe3/README.md) | 怎么跑主线 |
| [`scribe3/AGENTIC_BOUNDARY_DECISION.md`](../scribe3/AGENTIC_BOUNDARY_DECISION.md) | Agent 写世界状态边界 |

---

## 更新清单（会话结束前）

- [ ] 「当前状态」表格日期与 HEAD 已刷新
- [ ] 「进行中目标 / 下一步」与真实进度一致
- [ ] 新坑已写入「已知坑」
- [ ] 重要决策已一句话记下（或链到 adr）
- [ ] 已 `git push`，下一会话能拉到最新 SESSION
