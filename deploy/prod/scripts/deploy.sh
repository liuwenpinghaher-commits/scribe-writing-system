#!/usr/bin/env bash
# 在服务器上：拉代码并重建生产 compose（供手工或 GitHub Actions 调用）。
# 不依赖开发者本机网络。
set -euo pipefail

REPO_DIR="${SCRIBE3_REPO_DIR:-/opt/scribe3/app}"
BRANCH="${DEPLOY_BRANCH:-main}"
REMOTE="${GIT_REMOTE:-origin}"
COMPOSE_FILE="${COMPOSE_FILE:-deploy/prod/docker-compose.yml}"
ENV_FILE="${ENV_FILE:-deploy/prod/.env}"

cd "$REPO_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "缺少 $ENV_FILE — 先从 .env.example 复制并填写" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

if [ "${SKIP_GIT:-0}" = "1" ]; then
  echo "==> SKIP_GIT=1，使用当前工作树（通常由 CI scp 同步）"
elif git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "==> git fetch/reset $REMOTE/$BRANCH (best-effort)"
  if git fetch --prune "$REMOTE"; then
    git checkout "$BRANCH" 2>/dev/null || git checkout -B "$BRANCH"
    git reset --hard "$REMOTE/$BRANCH" || echo "warn: reset failed, continue with working tree" >&2
  else
    echo "warn: git fetch failed (private repo credentials?). Deploying current working tree." >&2
  fi
else
  echo "warn: no git remote; deploying current working tree under $REPO_DIR" >&2
fi

if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi
echo "==> $DOCKER compose up --build"
# 使用 docker compose v2 插件（无权限时回退 sudo）
$DOCKER compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull || true
$DOCKER compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build --remove-orphans

echo "==> 等待健康"
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${SCRIBE3_HTTP_PORT:-80}/healthz" >/dev/null 2>&1 \
    || curl -fsS "http://127.0.0.1:${SCRIBE3_HTTP_PORT:-80}/api/health" >/dev/null 2>&1; then
    echo "健康检查通过"
    curl -fsS "http://127.0.0.1:${SCRIBE3_HTTP_PORT:-80}/api/health" || true
    echo
    $DOCKER compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    exit 0
  fi
  sleep 3
done

echo "健康检查超时，最近日志:" >&2
$DOCKER compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=80 backend surreal frontend >&2 || true
exit 1

