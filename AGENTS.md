# AGENTS.md · 本仓库协作说明

## 用户交互语言（强制）

- **与用户的一切交互必须使用中文**（简体）。
- 代码/命令/API 标识可按惯例保留英文；面向用户的说明、结论、提问一律中文。
- 全局同源规则：`~/.grok/rules/chinese-communication.md`。

## 新会话必读

本仓库**无跨会话记忆**。每次新开会话：

1. 读本文件（长期规则）
2. 读 [`docs/SESSION.md`](docs/SESSION.md)（滚动当前状态 / 下一步）
3. 再动手

结束工作前更新 `docs/SESSION.md` 并 push。

## 主线

- **产品名（UI）：铜炉** / 拼音 **tonglu**（仅品牌与界面文案，见 [`docs/brand/README.md`](docs/brand/README.md)）。
- 产品代码在 **`scribe3/`**（SurrealDB + FastAPI + MCP + React 写作台）。
- **SurrealDB 唯一支持 3.x**（demo **3.2.4**）。禁止 2.x 兼容回退、禁止 `type::thing` 回流（护栏见 `tests/test_migrations_surreal3.py`）。store 集成测须 `SURREAL_BIN` 指向 3.x。
- 先读 [`docs/CURRENT_ARCHITECTURE.md`](docs/CURRENT_ARCHITECTURE.md)。
- 设计蓝图在 `设计文档/`（可能过期）；冲突时以 CURRENT + 代码为准。
- 根目录 `交付说明.md` 是早期 SQLite/`scribe/` **归档**，不要当现行手册。

## 常用命令

```bash
# MCP 门控单测
scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q

# 前端单测
cd scribe3/web && npm test

# 后端（示例端口见 scribe3/README）
scribe3/.venv/bin/python -m scribe3.app
```

更多门禁见 [`docs/PR_TEST_BASELINE.md`](docs/PR_TEST_BASELINE.md)。

## 工程健康度交付门（分层锁）

结案：[`docs/plans/2026-08-12-engineering-health-closure.md`](docs/plans/2026-08-12-engineering-health-closure.md)。

- **禁止**业务层直接 `st._query` / `_execute_write` / `_raw_query`（仅 `scribe3/store/*` 可）。  
- 回归钉：`scribe3/tests/test_eh_residual.py::test_next_layer_adapters_no_private_store`。  
- 推 main / 涉 store 分层改动后建议：

```bash
.venv/bin/python -m pytest scribe3/tests/test_eh_residual.py scribe3/tests/test_eh_health_batch.py -q --tb=line
./scripts/smoke_eh.sh   # 已部署 demo → DEMO_EH_OK
```

- **不要**在 Grok 运行机跑全量 pytest / 本机 Surreal；验证 = 已部署 demo。

## 写路径约定

- Agent 改世界状态：MCP `s3_*` + 审批；`commit_if_approved` 失败必须 `status=error`。
- 前端已有 Codex/北极星记录：倾向只读，写入走「让主编写入」种子。
- REST 写仍存在；未在本文件强制关闭。细节见 `scribe3/AGENTIC_BOUNDARY_DECISION.md`。

## 翻主纪律

- 换主路必须把依据和代码一起交：谁让改（作者授意或实施判断为最优）、为何这样最好、和旧路差在哪、怎么退（关旗或 revert）。
- 没有依据落账 = 擅自。对照日志只作旁观，不挡决策。不要再设观察期。
- 台账模板见 [`docs/plans/2026-08-22-round8-ledger.md`](docs/plans/2026-08-22-round8-ledger.md)。

## 改动卫生

- 不要提交 `artifacts/`、`surrealdb-docs-cache/`、`.codegraph/`、密钥、本地 DB。
- 大文件拆分按 [`docs/ARCHITECTURE_SPLIT_ROADMAP.md`](docs/ARCHITECTURE_SPLIT_ROADMAP.md)，禁止无测试的巨型搬家 PR。

## 多书

- Surreal `NS=scribe3`，一书一 `db=<work slug>`；MCP/API 传 `work`。

## 铜炉拆文（给人开下一本）

真源：[`docs/worlds/乱世铜炉-拆文/`](docs/worlds/乱世铜炉-拆文/)。翻序：参照本 〇 → 二十二 → 章法 → 七场批注 → `因文.md` → `对照.md`。不要按 Qoder 提纲重拆，不要给 214 节写因文，不要把情节灌进 Surreal。
