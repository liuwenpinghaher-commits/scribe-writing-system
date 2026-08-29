# AGENTS.md · 本仓库协作说明

语言与表达以家目录 `~/AGENTS.md` 为准（简体中文；读一遍就懂；专家团默认关）。

## 新会话

1. 读本文件
2. 读 [`docs/SESSION.md`](docs/SESSION.md) 的 **「当前状态」** 最近一条（不要通读全文）
3. 再动手

结束工作若改了方向，更新 `docs/SESSION.md` 对应小节。未经要求不要 push。

## 主线

- UI 产品名：**铜炉** / 拼音 **tonglu**（[`docs/brand/README.md`](docs/brand/README.md)）。
- 代码在 **`scribe3/`**（SurrealDB + FastAPI + MCP + React）。
- **只支持 SurrealDB 3.x**（demo **3.2.4**）。禁止 2.x 兼容、禁止 `type::thing`（`tests/test_migrations_surreal3.py`）。store 集成测须 `SURREAL_BIN` 指向 3.x。
- 架构真源：[`docs/CURRENT_ARCHITECTURE.md`](docs/CURRENT_ARCHITECTURE.md)。`设计文档/` 可能过期。根目录 `交付说明.md` 是 SQLite/`scribe/` 归档。

## 常用命令

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q
cd scribe3/web && npm test
scribe3/.venv/bin/python -m scribe3.app
```

门禁清单：[`docs/PR_TEST_BASELINE.md`](docs/PR_TEST_BASELINE.md)。不要在 Grok 运行机跑全量 pytest / 本机 Surreal；现网验证看已部署 demo。

## 写与分层

- 业务层禁止直接 `st._query` / `_execute_write` / `_raw_query`（仅 `scribe3/store/*` 可）。回归：`scribe3/tests/test_eh_residual.py::test_next_layer_adapters_no_private_store`。
- Agent 改世界状态：MCP `s3_*` + 审批；`commit_if_approved` 失败必须 `status=error`。REST 写仍在，见 `scribe3/AGENTIC_BOUNDARY_DECISION.md`。
- 换主路必须写清：谁让改、为何优于旧路、怎么退（关 flag 或 revert）。没有依据 = 擅自。
- 不要提交 `artifacts/`、`surrealdb-docs-cache/`、`.codegraph/`、密钥、本地 DB。
- Surreal `NS=scribe3`，一书一 `db=<work slug>`；MCP/API 传 `work`。

## 铜炉拆文

真源：[`docs/worlds/乱世铜炉-拆文/`](docs/worlds/乱世铜炉-拆文/)。翻序：参照本 〇 → 二十二 → 章法 → 七场批注 → `因文.md` → `对照.md`。不要按 Qoder 提纲重拆，不要给 214 节写因文，不要把情节灌进 Surreal。
