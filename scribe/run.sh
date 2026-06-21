#!/usr/bin/env bash
# Scribe2 固定端口启动:SurrealDB :8001 · 后端 scribe2 :3320 · 前端 :3310(永久约定,勿改)
# 新底座 = SurrealDB(知识/向量/图)+ scribe2(REST)+ Hermes(生成/主编 agentic)。
# 用法: ./run.sh        # 起 SurrealDB+前后端(前台,Ctrl-C 停前后端)
#       ./run.sh api    # 只起 SurrealDB+后端
#       ./run.sh web    # 只起前端
set -euo pipefail
cd "$(dirname "$0")"

API_PORT=3320
WEB_PORT=3310
SURREAL_PORT=8001
export SURREAL_URL="ws://127.0.0.1:${SURREAL_PORT}/rpc"
SURREAL_DATA="$HOME/.scribe2-surreal/data.db"
SURREAL_BIN="$HOME/.surrealdb/surreal"

ensure_surreal() {
  if lsof -nP -iTCP:${SURREAL_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    echo "SurrealDB :${SURREAL_PORT} 已在运行"
  else
    mkdir -p "$HOME/.scribe2-surreal"
    # 净环境 + ASCII cwd 启动(避中文路径坑);surrealkv 文件持久化
    ( cd /tmp && env -i PATH=/usr/bin:/bin HOME="$HOME" nohup "$SURREAL_BIN" start \
        "surrealkv://${SURREAL_DATA}" --bind 127.0.0.1:${SURREAL_PORT} \
        --user root --pass root > /tmp/scribe2_surreal.log 2>&1 & )
    sleep 3
    echo "SurrealDB :${SURREAL_PORT} 已启动(数据 ${SURREAL_DATA})"
  fi
}

start_api() { ensure_surreal; exec .venv/bin/uvicorn scribe2.app:app --port "$API_PORT"; }
start_web() { cd web-app && exec npm run dev; }   # 端口由 vite.config.ts 锁 3310

case "${1:-all}" in
  api) start_api ;;
  web) start_web ;;
  all)
    ensure_surreal
    .venv/bin/uvicorn scribe2.app:app --port "$API_PORT" &
    API_PID=$!
    ( cd web-app && npm run dev ) &
    WEB_PID=$!
    trap 'kill $API_PID $WEB_PID 2>/dev/null' INT TERM
    echo "SurrealDB :$SURREAL_PORT · 后端(scribe2) http://127.0.0.1:$API_PORT · 前端 http://127.0.0.1:$WEB_PORT"
    wait
    ;;
  *) echo "用法: ./run.sh [all|api|web]"; exit 1 ;;
esac
