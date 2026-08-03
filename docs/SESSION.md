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
| **HEAD（写入时）** | `0597e8e` — refactor(api): wire intent_northstar router; strip inline intent paths |
| **进行中目标** | Phase 1 App 路由拆出（ARCHITECTURE_SPLIT_ROADMAP） |
| **活跃分支** | `main` |
| **未合并 / WIP** | 无 |

### 最近在做什么

- **Phase 1 · health**：`scribe3/api/health.py` + 入口 `app.py` 接线并剥内联 `/health`/`/ready`（完成）。
- **Phase 1 · intent / north-star chapter**：`scribe3/api/intent_northstar.py` 已有（GET/PUT `/intent`、PUT `/intent-goals`、GET `/north-star/chapter/{seq}`）；入口接线并剥内联路径（完成）。`north_star_book` 仍留 app_impl（依赖多，延后）。
- quality / quality_eval routers 早已在 app_impl 内 `include_router`。
- 跨会话交接模板与索引此前已打通。
- **本会话**：只同步 SESSION（上一会话抽出 intent 后未刷新本文件）。

### 下一步（优先序）

1. **promises / clues 抽出** → `scribe3/api/promises.py`（GET `/promises`、`/promises/ledger`、`/promises/{pid}`、POST `/promises-new`、PATCH/DELETE `/promises/{pid}`、advance/mark-herring/abandon、clues、timeline 等），同 health/intent 模式：新建 router + 入口剥路径 + include_router；app_impl 内联函数物理删除延后。
2. 可选：抽出 `/north-star/book` 进 `intent_northstar`（或独立 slice）。
3. 有条件时在 app_impl 物理删除已抽出的 health/intent 内联函数与分区地图注释更新（非阻塞；554k 巨石，优先本地 clone 小 diff）。
4. codex → chapters → chat/hermes 再往后。

### 已知坑 / 禁止事项（滚动）

- 不要提交 `artifacts/`、`surrealdb-docs-cache/`、`.codegraph/`、密钥、本地 DB。
- 根目录 `交付说明.md` 是早期 SQLite/`scribe/` **归档**，不是现行手册。
- 设计蓝图在 `设计文档/` 可能过期；冲突以 [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md) + 代码为准。
- 服务端从国内拉 GitHub 不可靠 → 部署走 CI scp，不要假设服务器能 `git pull`。
- SESSION 表里的 HEAD 容易过时：每次实质提交后立刻改并 push，否则下一会话会读到陈旧 SHA。
- **app_impl.py ~554k**：GitHub Contents API 整文件更新不现实；大块搬迁用入口接线 / 路由剥除，或本地 clone 后小 diff PR。保持 auth middleware、emergency_rest_write、`_store_for` / `app.state.store_for` 不动。

### 最近决策（一句话）

- 跨会话状态不靠对话记忆，靠 Git 里的滚动 `docs/SESSION.md` + 长期 `AGENTS.md`。
- Phase 1 抽出模式：入口 `app.py` 剥路由 + include_router，避免动 554k 巨石；行为与路径不变；内联函数物理删除延后。
- intent 抽出时 `north_star_book` 因依赖多暂留 app_impl。

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
- [x] 新坑已写入「已知坑」（app_impl 大文件）
- [x] 重要决策已一句话记下
- [x] 已 `git push`，下一会话能拉到最新 SESSION
