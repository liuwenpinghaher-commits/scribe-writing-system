#!/usr/bin/env bash
# [已退役·回退用] 旧 scribe_mcp 启动(SQLite + doubao 直连)。数据在 scribe.db。
# 新底座见 ./run.sh(scribe2 + SurrealDB + Hermes)。仅在需访问旧 SQLite 数据时用本脚本。
set -euo pipefail
cd "$(dirname "$0")"

API_PORT=3320
WEB_PORT=3310

case "${1:-all}" in
  api) exec .venv/bin/uvicorn scribe_mcp.api:app --port "$API_PORT" ;;
  web) cd web-app && exec npm run dev ;;
  all)
    .venv/bin/uvicorn scribe_mcp.api:app --port "$API_PORT" &
    API_PID=$!
    ( cd web-app && npm run dev ) &
    WEB_PID=$!
    trap 'kill $API_PID $WEB_PID 2>/dev/null' INT TERM
    echo "[legacy] 后端 http://127.0.0.1:$API_PORT  ·  前端 http://127.0.0.1:$WEB_PORT"
    wait
    ;;
  *) echo "用法: ./run_legacy.sh [all|api|web]"; exit 1 ;;
esac
