#!/usr/bin/env bash
# Scribe 固定端口启动:后端 3320 · 前端 3310(永久约定,勿改)
# 用法: ./run.sh          # 同时起前后端(前台,Ctrl-C 全停)
#       ./run.sh api      # 只起后端
#       ./run.sh web      # 只起前端
set -euo pipefail
cd "$(dirname "$0")"

API_PORT=3320
WEB_PORT=3310

start_api() { exec .venv/bin/uvicorn scribe_mcp.api:app --port "$API_PORT"; }
start_web() { cd web-app && exec npm run dev; }   # 端口由 vite.config.ts 锁 3310

case "${1:-all}" in
  api) start_api ;;
  web) start_web ;;
  all)
    .venv/bin/uvicorn scribe_mcp.api:app --port "$API_PORT" &
    API_PID=$!
    ( cd web-app && npm run dev ) &
    WEB_PID=$!
    trap 'kill $API_PID $WEB_PID 2>/dev/null' INT TERM
    echo "后端 http://127.0.0.1:$API_PORT  ·  前端 http://127.0.0.1:$WEB_PORT"
    wait
    ;;
  *) echo "用法: ./run.sh [all|api|web]"; exit 1 ;;
esac
