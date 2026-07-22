# CURRENT · 架构真相（scribe3）

> **本文是当前实现的唯一入口说明。**  
> 若与 `交付说明.md`、早期 `scribe/` 叙事、部分设计文档冲突，**以本文 + `scribe3/` 代码为准**。  
> 更新：2026-07-22

## 1. 产品是什么

人机协同长篇写作系统：**人出想象与裁决，AI（主编）主笔**。  
核心保证：

1. 限知渲染：角色不知道的事，物理上进不了其 prompt（知识帧投影优先，判官兜底）。
2. 世界状态可审计：事实/事件/知识边/伏笔等落在领域库。
3. 写操作可门控：Agent 侧 MCP 写工具经审批门控（`commit_if_approved`）。

## 2. 当前主线代码

| 路径 | 职责 |
|------|------|
| `scribe3/` | **主产品**（greenfield 故事本体 v2 + 写作台） |
| `scribe3/app.py` | FastAPI 薄入口（实现见 `api/app_impl.py`） |
| `scribe3/api/app_impl.py` | FastAPI 路由与共享辅助 |
| `scribe3/store/` | `SurrealStore` 包（原 `store.py` 拆分） |
| `scribe3/store.py` | `SurrealStore`（SurrealDB） |
| `scribe3/mcp.py` | 领域 MCP（`s3_*` 工具） |
| `scribe3/web/` | React + Vite 写作台前端 |
| `scribe3/hermes_skills/` | Hermes 技能 |
| `设计文档/` | 第一性原理与历史设计（部分可能过期，见索引） |
| `交付说明.md` | **归档向**早期 `scribe/` + SQLite 批次叙事，勿当现行运维手册 |

历史/旁路（非主线运行时）：`scribe/`（若仍存在）、`oh-story-claudecode-main/`、各类 zip/缓存。

## 3. 运行时栈（以代码为准）

```text
浏览器 (scribe3/web, dev 常见 :3311)
    → FastAPI scribe3.app (常见 :3321)
        → SurrealDB (ns=scribe3, db=work_id)
        → Hermes / doubao（写作与主编对话，环境相关）
    → MCP server "scribe3"（主编工具 s3_*）
```

- **存储：SurrealDB**，不是交付说明里的 SQLite 主路径。  
- **端口：** 以 `scribe3/README.md` 为准（示例 API `:3321`、前端 `:3311`）；旧文 `:8801`/`:5174` 属早期 `scribe/` 叙事。  
- **书隔离：** `work` / Surreal `db` 名；MCP `_store_for(work)`。

## 4. 写路径（现状摘要）

| 通道 | 用途 | 门控 |
|------|------|------|
| MCP `s3_*` 写工具 | 主编/Agent 改世界状态 | `WRITE_GATED` + elicitation + `commit_if_approved` |
| REST 写 | 仍存在于 `app.py`（测试/兼容/部分 UI 历史路径） | **未在本文强制关闭**；产品策略见 `scribe3/AGENTIC_BOUNDARY_DECISION.md`（若有未提交修订以代码审查为准） |
| 前端 | 写作台、Codex、北极星条等 | WIP 方向：已有记录只读 +「让主编写入」种子；新建条目仍可能本地表单 |

`commit_if_approved` 约定：

- 拒绝 → `status=declined`，不写  
- 批准且写入成功 → `status=written`  
- 写入抛错 / 返回 `False` / 返回 `{error: ...}` → `status=error`（**不得假绿 written**）

## 5. 怎么跑（最小）

见 `scribe3/README.md`。摘要：

```bash
# 后端
scribe3/.venv/bin/python -m scribe3.app

# 前端
cd scribe3/web && npm install && npm run dev

# 单测（示例）
scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q
```

Makefile 根目录提供：

- `make test-baseline` — PR 默认（`test-mcp` + `test-web-readonly`）
- `make e2e-det` / `e2e-frontend` / `e2e-real` — 更重的 e2e（需环境就绪）

## 6. 文档优先级

1. **本文** + `scribe3/README.md` + 根目录 `AGENTS.md`  
2. `scribe3/AGENTIC_BOUNDARY_DECISION.md`（协作边界决策）  
3. [`PR_TEST_BASELINE.md`](./PR_TEST_BASELINE.md)（验证门禁）  
4. 仍有效的 `设计文档/` 条目（需带日期；冲突时以代码为准）  
5. `交付说明.md` → 历史交付快照（已标归档）

## 7. 已知结构性债（非完整列表）

- `app.py` / `store.py` 体量过大 → 见 `docs/ARCHITECTURE_SPLIT_ROADMAP.md`  
- 设计文档与实现多世代并存 → 依赖本文做路由  
- 工作区易堆积 e2e 产物/缓存 → 见根目录 `.gitignore`
