# scribe3 部署指南

## 本地开发

```bash
# 1. 启动 SurrealDB(2026-07-10 起带护栏参数,SurrealDB 官方文档优化批)
surreal start --no-banner --bind 127.0.0.1:8001 --user root --pass root \
  --slow-log-threshold 500ms --query-timeout 60s --transaction-timeout 30s \
  --log info "surrealkv:$HOME/.scribe2-surreal/data.db"
# ⚠ 勿用 memory 模式:重启即丢全部书稿;生产数据即在上述路径(目录名带 scribe2 是历史遗留,勿删)
# 护栏:>500ms 慢查询进日志(nohup 时重定向到 /tmp/scribe3-surreal.log)、语句组 60s/事务 30s 超时防失控递归。
# 掉线恢复:store 层已带自动重连(S-1),SurrealDB 重启后**后端不需要重启**,请求自愈。
# 备份:scribe3/scripts/surreal_backup.sh 逐书 surreal export 到 ~/.scribe3-backups/(保留最近 14 份);
#      书稿是不可再生资产,建议 cron 每日跑一次;恢复用 surreal import(脚本头注释有命令)。

# 2. 启动后端(:3321)
cd scribe3 && .venv/bin/uvicorn scribe3.app:app --port 3321

# 3. 启动前端(:3311)
cd scribe3/web && npm install && npm run dev

# 4. Hermes 网关(已由 launchd/screen 常驻)
#    default: :8642(速答/渲染/判官)
#    scribe3 read profile: :8643(只读 MCP)
#    scribe3_write profile: :8644(读 + 写 MCP,用于 Runs/Approval)
```

## Docker 部署

```bash
# 一键启动 SurrealDB + 后端 + 前端
docker compose up

# 前端: http://127.0.0.1:3311
# 后端: http://127.0.0.1:3321
# Hermes 网关用宿主已跑的 :8642/:8643/:8644
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SCRIBE3_SURREAL_URL` | `ws://127.0.0.1:8001/rpc` | SurrealDB 连接 |
| `SCRIBE3_SURREAL_USER` | `root` | DB 用户名 |
| `SCRIBE3_SURREAL_PASS` | `root` | DB 密码 |
| `HERMES_API` | `http://127.0.0.1:8642/v1` | Hermes 默认网关 |
| `HERMES_RESPONSES_API` | `http://127.0.0.1:8643/v1` | Hermes scribe3 只读 profile 网关 |
| `HERMES_RESPONSES_PROFILE` | `scribe3` | Responses/API key profile |
| `HERMES_RUNS_API` | `http://127.0.0.1:8644/v1` | Hermes scribe3_write 写入审批网关 |
| `HERMES_RUNS_PROFILE` | `scribe3_write` | Runs/API key profile |
| `API_SERVER_KEY` | (从 ~/.hermes/.env 读) | Hermes API key |
| `SCRIBE3_CORS_ORIGINS` | `http://127.0.0.1:3311` | CORS 白名单(逗号分隔) |
| `SCRIBE3_API_TOKEN` | (不设=本地放行) | 可选 bearer token 认证 |
| `SCRIBE3_MAX_CONCURRENT` | `3` | LLM 并发上限 |
| `SCRIBE3_DAILY_CALL_CAP` | `500` | LLM 日调用上限 |
| `SCRIBE3_WORK` | `main` | MCP 当前书 DB 名 |
| `VITE_API_BASE` | `http://127.0.0.1:3321` | 前端后端地址(构建期注入) |

## CI

GitHub Actions `.github/workflows/ci.yml` 在 push/PR 时跑:
- backend: `pytest scribe3/tests`
- frontend: `npm run test` + `npm run build`
