# CURRENT · 架构真相（scribe3）

> **本文是当前实现的唯一入口说明。**  
> 若与 `交付说明.md`、早期 `scribe/` 叙事、部分设计文档冲突，**以本文 + `scribe3/` 代码为准**。  
> 更新：2026-08-02（对话驱动正典写 + 作者直管非正典素材 + 审批过期语义）

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
| `scribe3/store/` | **`SurrealStore` 包**（mixin 门面：`connection` / `events` / `recall` / `chapters` / …） |
| `scribe3/mcp.py` | 领域 MCP（`s3_*` 工具 + `WRITE_GATED` + `commit_if_approved`） |
| `scribe3/live.py` | Surreal LIVE → SSE（凭证与 store 同源 env/settings） |
| `scribe3/web/` | React + Vite 写作台前端 |
| `scribe3/hermes_skills/` | Hermes 技能 |
| `设计文档/` | 第一性原理与历史设计（部分可能过期，见索引） |
| `交付说明.md` | **归档向**早期 `scribe/` + SQLite 批次叙事，勿当现行运维手册 |

**已不存在** 运行时单文件 `scribe3/store.py` 巨石；持久层以 `scribe3/store/` 包为准。

历史/旁路（非主线运行时）：`scribe/`（若仍存在）、`oh-story-claudecode-main/`、各类 zip/缓存。

## 3. 运行时栈（以代码为准）

```text
浏览器 (scribe3/web, dev 常见 :3311)
    → FastAPI scribe3.app (常见 :3321)
        → SurrealDB (ns=scribe3, db=work_id)   ← 世界正典唯一真相源
        → Hermes / 配置的 LLM（写作与主编对话）
    → MCP server "scribe3"（主编工具 s3_*）
```

- **存储：SurrealDB**（一书一 `db=<work slug>`）。**不是** GBrain / 外挂第二真相库；过程记忆若开启走仓内 `memory_fabric`（默认关），不得替代正典。  
- **端口：** 以 `scribe3/README.md` 为准（示例 API `:3321`、前端 `:3311`）。  
- **DB 凭证：** `SCRIBE3_SURREAL_URL` / `SCRIBE3_SURREAL_USER` / `SCRIBE3_SURREAL_PASS`（store 与 live 同源）。

## 4. 写路径（现行产品铁律）

| 通道 | 用途 | 门控 |
|------|------|------|
| **MCP `s3_*` 写工具（正典主路径）** | 主编改世界状态 / 结构 / 意图 | `WRITE_GATED` + elicitation + `commit_if_approved` |
| **前端创作 UI** | 设定/大纲/卷章 meta / 节拍等 | **只读检视 +「让主编…」种子**（`s3-chief-seed`）；禁止表单失焦直写世界语义 |
| **REST 世界写** | 测试夹具 / 紧急运维 | **`SCRIBE3_EMERGENCY_REST_WRITE` 默认关** → 403；测试 conftest 默认开 |
| **素材库** | 作者的非正典参考记忆 | 作者通过 `/materials` 直接新建/编辑/置顶/归档/删除；删除保留影响确认令牌；主编仅可 `s3_material_recall` 等只读搜索、召回和引用 |
| **工程配额** | 字数目标 / 逾期阈值 | `PUT /intent-goals`（**不经**世界闸）；叙事北极星仍 `s3_set_intent` / 闸内 `PUT /intent` |
| 正文 | `/chat/write` 提案卡接受 | 与世界写分离 |
| 知识反哺 | 自动 `_enqueue_ingest` + 手动 `POST /ingest` | 进程内 `(work,seq)` 在途去重；多 worker 前须跨进程锁 |

`commit_if_approved` 约定：

- 拒绝 → `status=declined`，不写  
- 超时 / elicitation 会话已失效 → `status=expired`，不写，不得伪装成作者拒绝
- 批准且写入成功 → `status=written`  
- 写入抛错 / 返回 `False` / 返回 `{error: ...}` → `status=error`（**不得假绿 written**）

结构写 MCP（示例，均待批）：`s3_add_volume` / `s3_patch_volume` / `s3_add_chapter` / `s3_patch_chapter_meta` / `s3_patch_chapter_plan` / `s3_set_char_anchors` / `s3_set_intent` 等。

素材不是世界事实，不因“主编会召回它”就转为正典。当作者决定把素材中的内容转为设定/事实时，应新发起对应正典 MCP 写入并审批，而不是让主编改写素材本身。

决策全文：`scribe3/AGENTIC_BOUNDARY_DECISION.md`、`设计文档/2026-07-22-对话驱动写入-禁表单直填-决策与改造方案.md`。

## 5. 限知与图（摘要）

- 投影：`project_frame` / `dramatic_irony`（真库可跑）  
- 生产：`add_event` 带 `effects` 时自动 `see_event`（目击者 `knows`）；ingest `did` 合成事件挂 effects  
- 召回：`hybrid_recall` / `semantic_recall(chapter=…)` 时间门；`graph_recall` knowers 同样尊重 `knows.since/until`；`graph()` 尊重 `until_chapter`  
- 多目击者：`participants` 同槽可 `list[str]`（MCP `s3_add_event` 同 role 多人保留 list）

## 5b. 讨论 vs 写作 · 上下文与记忆

| 路径 | 上下文 | 限知 |
|------|--------|------|
| **写作** `/chat/write` | `CreativeContextEngine` + 八块 envelope；目的合同/教训**内联**；章前简报操作必达段（伏笔/开环/心跳/弧光/因果）、作者偏好、声音锚；draft/final **门控素材参考**（借鉴非事实，确定性排序）；**默认挂 MemoryRetriever** | 有 `focalizer` 时 `project_frame` 硬裁 |
| **讨论** `/chat/stream` 等 | 仍 `_editor_system` 散点栈，**不是**写作 envelope | 默认作者全知联查面；**不得**当成限知渲染已统一 |

- **上下文产品默认开（非灰度休眠）**：`SCRIBE3_CONTEXT_SNAPSHOT_V1` / `SCRIBE3_MEMORY_FABRIC_V1` / `SCRIBE3_CONTEXT_INSPECTOR_V1` **默认 true**；`GET /capabilities` 在默认 env 下报对应 flags true。仅显式 env/DB=0 可关（测试隔离），不是产品 fallback。  
- **MEMORY_FABRIC 开时**：写作 capture/retrieve 与 HTTP `/memory/*` 可用；组装/捕获故障 **fail-loud**（HTTP 500），不得空串假「无数据」。显式关 → 403。  
- **`context_inspector_v1` 默认开**：前端 ContextInspector 默认渲染；capabilities 报关才隐藏。  
- **pending 正典待审**：`GET/POST /memory/pending-claims…` + 主编区 **PendingClaimsPanel**（批准入正典 / 拒绝）。  
- 过程记忆**不得**替代 Surreal 正典；非 GBrain。  
- `SCRIBE3_EMERGENCY_REST_WRITE` **仍默认关**（与上下文产品无关）。

## 6. 怎么跑（最小）

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

## 7. 文档优先级

1. **本文** + `scribe3/README.md` + 根目录 `AGENTS.md`  
2. `scribe3/AGENTIC_BOUNDARY_DECISION.md`（协作边界决策）  
3. [`PR_TEST_BASELINE.md`](./PR_TEST_BASELINE.md)（验证门禁）  
4. 计划：`docs/superpowers/plans/2026-07-22-phase2-dialogue-write-phase3-limited-knowledge-tdd.md`  
5. 仍有效的 `设计文档/` 条目（需带日期；冲突时以代码为准）  
6. `交付说明.md` → 历史交付快照（已标归档）

## 8. 已知结构性债（非完整列表）

- `api/app_impl.py` 仍偏巨石 → 见 `docs/ARCHITECTURE_SPLIT_ROADMAP.md`  
- 部分拖拽排序/删卷仍走 REST（运维操作）；世界语义新建/改文案以对话审批为主  
- 批量 WriteProposal 服务端卡未做（仍 per-tool elicit）  
- 工作区易堆积 e2e 产物/缓存 → 见根目录 `.gitignore`
