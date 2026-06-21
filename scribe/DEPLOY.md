# Scribe2 部署(新底座)

新底座 = **SurrealDB**(知识/向量/图)+ **scribe2**(REST/MCP)+ **Hermes**(生成 / 主编 agentic)。
已取代旧 `scribe_mcp`(SQLite + doubao 直连)。

## 端口(永久约定,勿漂移)

| 服务 | 端口 | 说明 |
|---|---|---|
| SurrealDB | 8001 | surrealkv 持久化:`~/.scribe2-surreal/data.db` |
| scribe2 后端 | 3320 | `uvicorn scribe2.app:app`,`SURREAL_URL=ws://127.0.0.1:8001/rpc` |
| 前端 | 3310 | vite(`vite.config.ts` strictPort 锁死);BASE 经 `VITE_API` 默认 3320 |
| Hermes 网关 | 8642 | 挂 `scribe2` MCP server(主编 agentic 调工具)|

## 启动

```bash
cd scribe
./run.sh          # SurrealDB:8001 + scribe2:3320 + 前端:3310(前台)
./run.sh api      # 只起 SurrealDB + 后端
./run.sh web      # 只起前端
```

打开 http://localhost:3310 (注意用 localhost,vite v8 对 127.0.0.1 有 host 校验)。

## 主编 agentic(主编主笔)

前端「主编对话」→ scribe2 `/works/{w}/chat/stream` → Hermes `/v1/responses`
(`tools=[{type:mcp, server_label:scribe2}]`)→ 主编自己调 scribe2 的只读工具
(search_knowledge / list_characters / get_memory / list_open_foreshadows …)查
SurrealDB 真实数据回答,不凭空编。

Hermes 挂载在 `~/.hermes/config.yaml` 的 `mcp_servers.scribe2`(command `python -m scribe2.mcp`,
env `SURREAL_URL`)。改动后需 `hermes gateway restart`。验证:`hermes mcp test scribe2`、
`python tools/chief_agentic_smoke.py`。

## 数据迁移

109k《九原渡》已由 `tools/migrate_jiuyuandu.py` 从旧 `scribe.db` 迁入 SurrealDB
(32 章 / 109,691 字 / 5 角色 / 7 设定 / 6 伏笔 / 32 章记忆)。当前由 SurrealDB:8001 持有,
正文同时存于 `out/九原渡/*.md`、圣经存于 `tools/bible_jiuyuandu.json`。

## 旧 scribe_mcp(已彻底移除)

旧底座 `scribe_mcp`(SQLite + doubao 直连)及其代码/测试/驱动脚本、`scribe.db`、Hermes
的 `scribe` MCP 挂载,均已删除,避免与新底座混淆。`scribe.db` 删除前已备份到仓库外
`~/scribe-archive/scribe.db.20260621.bak`(如需彻底清理可自行删该备份);代码删除走 git,
可经历史恢复。新底座是唯一系统。
