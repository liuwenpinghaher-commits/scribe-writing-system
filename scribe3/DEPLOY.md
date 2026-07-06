# scribe3 部署指南

## 本地开发

```bash
# 1. 启动 SurrealDB
surreal start --bind 127.0.0.1:8001 --user root --pass root file:~/.scribe2-surreal/data.db
# ⚠ 勿用 memory 模式:重启即丢全部书稿;生产数据即在上述 file 路径(目录名带 scribe2 是历史遗留,勿删)

# 2. 启动后端(:3321)
cd scribe3 && .venv/bin/uvicorn scribe3.app:app --port 3321

# 3. 启动前端(:3311)
cd scribe3/web && npm install && npm run dev

# 4. Hermes 网关(已由 launchd 常驻)
#    scribe3 profile: :8643(挂 MCP)
#    default: :8642(速答/渲染/判官)
```

## Docker 部署

```bash
# 一键启动 SurrealDB + 后端 + 前端
docker compose up

# 前端: http://127.0.0.1:3311
# 后端: http://127.0.0.1:3321
# Hermes 网关用宿主已跑的 :8642/:8643
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SCRIBE3_SURREAL_URL` | `ws://127.0.0.1:8001/rpc` | SurrealDB 连接 |
| `SCRIBE3_SURREAL_USER` | `root` | DB 用户名 |
| `SCRIBE3_SURREAL_PASS` | `root` | DB 密码 |
| `HERMES_API` | `http://127.0.0.1:8642/v1` | Hermes 默认网关 |
| `HERMES_RESPONSES_API` | `http://127.0.0.1:8643/v1` | Hermes scribe3 profile 网关 |
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
