# app.py / store.py 拆分路线图

> 目标：降低审查与并行改动冲突，**不**做一次性大爆炸重构。  
> 约束：行为与 API 路径兼容；每步可测、可回滚。  
> 关联：`docs/CURRENT_ARCHITECTURE.md`

## 现状

| 文件 | 量级（约） | 问题 |
|------|------------|------|
| `scribe3/app.py` | ~9k 行 | 路由、鉴权、Hermes、业务编排耦合 |
| `scribe3/store.py` | ~6k 行 | 全领域持久化单文件，难并行 |

## 原则

1. **先加缝，再搬砖**：先抽 router/package 边界，再搬函数。  
2. **测试锁行为**：每搬一个域，搬对应 `tests/`。  
3. **Store 按聚合拆，App 按 HTTP 资源拆**。  
4. **禁止**跨 PR 改语义 + 大搬迁；搬迁 PR 不改行为。

## Phase 0 — 基线（0.5–1 天）

- [x] 固定 PR 最低测试：见 `docs/PR_TEST_BASELINE.md` + `Makefile` 的 `test-mcp` / `test-web-readonly`  
- [x] 在 `app.py` 模块 docstring 分区地图（auth / runtime / context / chapters / codex / …）  
- [x] 在 `store.py` 模块 docstring 按聚合归桶（entity/fact/event/promise/intent/…）  
- [ ] （后续）导出自动 `def` 清单脚本到 `scripts/` 可选

## Phase 0.5 — 入口物理拆分（已完成）

- [x] `scribe3/app.py` → 薄入口；实现在 `scribe3/api/app_impl.py`
- [x] `scribe3/store.py` → `scribe3/store/` 包（mixin 门面 + `SurrealStore`）
- [x] `apply_schema` migrations 路径适配 package 布局

## Phase 1 — App 路由拆出（1–2 周，可多 PR）

目标结构：

```text
scribe3/
  app.py                 # 创建 FastAPI、middleware、include_router
  api/
    deps.py              # store 依赖、auth
    chapters.py
    codex.py
    promises.py
    intent_northstar.py
    chat_hermes.py
    health.py
```

顺序建议：

1. `health` + 只读探测  
2. `intent` / north-star  
3. `promises` / clues  
4. `codex`（character/faction/…）  
5. `chapters` + ingest  
6. `chat` / hermes 代理  

验收：旧路径 URL 不变；全量 API 测绿。

## Phase 2 — Store 按聚合拆（2–4 周）

目标结构：

```text
scribe3/store/
  __init__.py            # SurrealStore 门面，组合 mixin 或子仓储
  base.py                # 连接、schema、execute_write、_jsonable 辅助
  characters.py
  facts_knowledge.py
  events.py
  promises.py
  intent.py
  factions_items_terms.py
  chapters.py
```

策略：

- **先用 Mixin 多继承**保持 `SurrealStore` 类名稳定（MCP/app 少改）。  
- 每个 mixin 只碰本表 SurrealQL。  
- `execute_write` / 事务辅助留在 `base.py`。

验收：store 单测按文件拆分后仍全绿；无公开方法改名。

## Phase 3 — 领域服务层（可选，其后）

```text
scribe3/services/
  purpose.py             # 已有 purpose 可迁入
  ingest_flow.py
  voice_fold.py
```

App/MCP 变薄：HTTP/MCP 只做校验与编排，服务层调 store。

## Phase 4 — 反腐与生成物

- MCP 工具按域拆 `mcp/tools_*.py`，`mcp.py` 只注册  
- OpenAPI 标签与前端 `api` client 分区对齐  

## 并行开发约定（专家团/多人）

| 角色 | 可并行目录 |
|------|------------|
| A | `api/chapters.py` + 对应 tests |
| B | `store/promises.py` mixin |
| C | `web/src/...` 单一视图 |
| 合并 | 先 store 门面，再 api include，最后前端 |

本地并行用 **独立 git worktree + 分支**，避免同改 `app.py` 中段。

## 非目标（本路线图不做）

- 更换 Surreal → 其它 DB  
- 一次性重写前端  
- 强制关闭全部 REST 写（产品边界另案）

## 完成定义

- `app.py` < ~800 行（组装为主）  
- `store/base.py` + 各聚合文件，单文件 < ~1200 行  
- CI 可按路径 selective 测  
- 新功能默认落在域文件，不再堆进巨石中部
