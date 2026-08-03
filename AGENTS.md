# AGENTS.md · 本仓库协作说明

## 新会话必读

本仓库**无跨会话记忆**。每次新开会话：

1. 读本文件（长期规则）
2. 读 [`docs/SESSION.md`](docs/SESSION.md)（滚动当前状态 / 下一步）
3. 再动手

结束工作前更新 `docs/SESSION.md` 并 push。

## 主线

- 产品代码在 **`scribe3/`**（SurrealDB + FastAPI + MCP + React 写作台）。
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

## 写路径约定

- Agent 改世界状态：MCP `s3_*` + 审批；`commit_if_approved` 失败必须 `status=error`。
- 前端已有 Codex/北极星记录：倾向只读，写入走「让主编写入」种子。
- REST 写仍存在；未在本文件强制关闭。细节见 `scribe3/AGENTIC_BOUNDARY_DECISION.md`。

## 改动卫生

- 不要提交 `artifacts/`、`surrealdb-docs-cache/`、`.codegraph/`、密钥、本地 DB。
- 大文件拆分按 [`docs/ARCHITECTURE_SPLIT_ROADMAP.md`](docs/ARCHITECTURE_SPLIT_ROADMAP.md)，禁止无测试的巨型搬家 PR。

## 多书

- Surreal `NS=scribe3`，一书一 `db=<work slug>`；MCP/API 传 `work`。
