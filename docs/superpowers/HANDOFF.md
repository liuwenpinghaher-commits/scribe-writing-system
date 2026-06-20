# Scribe 底座重构 · 接力说明(新会话从这里续)

> 新会话第一步:读本文件 + 下面两份 spec/plan,然后从「下一步」继续。

## 正在做什么
把 Scribe **彻底重构**成:**Hermes(agent 大脑)+ SurrealDB(关系+向量+图 一体数据层)+ 一套干净 MCP 工具 + 保留的前端**。Clean rebuild,旧码最后统一删,零遗留。

## 真相源文档(必读)
- 设计 spec:`docs/superpowers/specs/2026-06-20-scribe-hermes-surrealdb-rearchitecture-design.md`
- 第1段计划(已执行):`docs/superpowers/plans/2026-06-20-scribe-surrealdb-knowledge-layer.md`
- 第2段计划(已执行):`docs/superpowers/plans/2026-06-20-scribe-surrealdb-domain-rest.md`

## 当前状态(2026-06-20)
- **分支**:`feat/surrealdb-knowledge-layer`(已 commit,工作树干净)
- **新包**:`scribe2/`(基于 SurrealDB,**不碰旧 `scribe_mcp/`**)
- **已完成 段1+段2,15 测试全绿**:
  - 段1 知识层 `scribe2/store.py`:连接 + 数据驱动 schema(HNSW 向量 + BM25 全文)+ bge-small-zh 嵌入(512维)+ 图 RELATE/遍历 + `search_knowledge`(向量 cosine + 按书过滤 + 图扩展)
  - 段2 领域/REST:`domain.py`(work/卷/章 + 版本 snapshot + 设定 + search)、`conn.py`(env 连接)、`app.py`(FastAPI 核心端点跑在 SurrealDB)
- 跑测试:`cd scribe && .venv/bin/python -m pytest scribe2/tests/ -q`

## 已解决的真坑(别再踩)
1. **项目路径含中文「写作 3.0」→ surreal v3.1.5 子进程 SIGABRT**:起 surreal 必须用 ASCII cwd(`/tmp`)+ 净化 env(见 `scribe2/tests/conftest.py`)。生产 DB 也要 ASCII 路径。
2. surreal 二进制在 `~/.surrealdb/surreal`(不在 PATH);SDK `from surrealdb import Surreal, RecordID`,query 返回干净 `list[dict]`。
3. SurrealQL:用 SDK 原生 `create/select/merge`(`type::thing` 解析坑);FTS 用 `FULLTEXT ANALYZER … BM25`(非 SEARCH);KNN `<|k|>` 已废弃,用 `vector::similarity::cosine` 排序;`->edge->?.*` 物化字段;类方法名 `list` 遮蔽内置 → `from __future__ import annotations`。

## 下一步(段3 → 段5)
- **段3**:一套干净 MCP 工具 `scribe2/mcp.py`(FastMCP)——读/检索/写,**写工具标 `requires_approval`**;暴露 `search_knowledge`、`create_chapter`、`save_prose`、`add_setting` 等领域动作给 Hermes。
- **段4**:Hermes run 集成 —— 主编对话经 `POST Hermes /v1/runs`(挂 scribe MCP、session-key=书、主编人格)+ SSE 事件 + `/approval` 审批门;前端对话改 run 驱动 + 审批卡。**先实测 Hermes `/v1/runs` + 审批事件 schema**(Hermes 源码在 `scribe/vendor/hermes-agent`,API 在 `gateway/platforms/api_server.py`)。
- **段5**:记忆→Hermes memory(session-key 作用域)、技能→Hermes skills、主动引擎→Hermes cron;生成全经 Hermes(退役直连火山);前端 `api.ts` BASE 切到新 scribe2 app;**删旧 `scribe_mcp/` + `scribe.db` + 旧测试 + agent_memory/agent_skills 表**(clean rebuild 收尾)。

## 在新会话怎么续
直接说:**「读 docs/superpowers/HANDOFF.md,从段3继续(出计划+执行)」**。
端口约定不变:前端 3310 / 旧后端 3320(新 scribe2 app 上线后再切)。
