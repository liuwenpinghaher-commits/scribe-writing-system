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

## 设置中心

统一配置台账,取代散落的环境变量手改。

- **配置优先级**(高到低):SQLite 设置台账(界面改的)→ 环境变量 → 代码注册表默认值。
  注册表在 `scribe3/settings.py`(`REGISTRY`,51 项,分 connection/llm/craft/flags/gateway 五类)。
- **台账路径**:`~/.scribe2-surreal/scribe3_settings.sqlite3`(env `SCRIBE3_SETTINGS_DB` 可改);
  变更审计表同库。
- **生效方式两类**:
  - `effect='hot'` 项:界面改完立即生效(读点每次调 `get_setting()`,写入即失效进程内缓存,
    跨进程靠 2s TTL 自然收敛)。
  - `effect='restart'` 项:仍走原 env 读取路径,由启动期 `apply_restart_overrides()` 把 DB 覆盖
    灌进 `os.environ`;改完需重启后端才生效(界面对这类项有黄标提示「重启后生效」)。
  - ⚠️ 运维事实:后端启动如带 flag env(如 `SCRIBE3_*_V1=1`),该 env 只在**界面未覆盖**该项时
    才是生效值——界面(DB)覆盖优先于 env,别被"改了 env 却没变化"迷惑,先看界面有没有存过值。
- ⚠️ **启动方式**:app.py 顶层 `import httpx`,系统 `python3` 通常缺该依赖会直接崩;必须用
  `scribe3/.venv/bin/python -m scribe3.app` 启动(2026-07-12 实测),不要裸用 `python3 scribe3/app.py`
  或系统解释器起 uvicorn。
- **网关文件编辑**:界面上编辑 Hermes 网关配置文件时自动备份到同目录 `<file>.bak.<时间戳毫秒>`;
  `/gateway/restart` 走 nohup 后台起 + 轮询等就绪,不阻塞请求线程。
- **入口**:前端顶栏齿轮图标 → 设置中心(七分区:连接与服务/LLM 与用量/工艺阈值/灰度开关/
  Hermes 网关/本书设置/个人偏好,外加变更历史)。

## CI

GitHub Actions `.github/workflows/ci.yml` 在 push/PR 时跑:
- backend: `pytest scribe3/tests`
- frontend: `npm run test` + `npm run build`
