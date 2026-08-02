#!/usr/bin/env bash
# 在服务器上导入 export_local_data.sh 产出的 tarball。
# 要求: Surreal 容器已在跑，且 SURREAL 凭证与 compose .env 一致。
# 用法:
#   bash deploy/prod/scripts/import_data.sh /path/to/scribe3-cloud-migrate-xxx.tgz
set -euo pipefail

TGZ="${1:-}"
if [ -z "$TGZ" ] || [ ! -f "$TGZ" ]; then
  echo "用法: $0 /path/to/migrate.tgz" >&2
  exit 1
fi

REPO_DIR="${SCRIBE3_REPO_DIR:-/opt/scribe3/app}"
ENV_FILE="${ENV_FILE:-$REPO_DIR/deploy/prod/.env}"
DATA_DIR="${SCRIBE3_DATA_DIR:-/opt/scribe3/data}"
COMPOSE_FILE="${COMPOSE_FILE:-$REPO_DIR/deploy/prod/docker-compose.yml}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

USER="${SURREAL_USER:-root}"
PASS="${SURREAL_PASS:-root}"
NS="${SCRIBE3_SURREAL_NS:-scribe3}"

WORKDIR="$(mktemp -d /tmp/scribe3-import.XXXXXX)"
trap 'rm -rf "$WORKDIR"' EXIT
tar -xzf "$TGZ" -C "$WORKDIR"
SRC="$(find "$WORKDIR" -maxdepth 1 -type d -name 'scribe3-cloud-migrate-*' | head -1)"
[ -n "$SRC" ] || SRC="$WORKDIR"

echo "==> 等待 surreal 容器"
cd "$REPO_DIR"
for i in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T surreal \
      /surreal isready --endpoint http://127.0.0.1:8000 >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# 通过 docker network：在临时容器里 import，或 docker exec + 管道
# surreal 官方镜像带 /surreal；从 backend 同网访问 hostname surreal:8000
echo "==> 导入 surql"
shopt -s nullglob
for f in "$SRC"/surql/*.surql; do
  db="$(basename "$f" .surql)"
  echo "  import $db"
  # 把文件拷进 surreal 容器再 import
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" cp "$f" "surreal:/tmp/${db}.surql"
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T surreal \
    /surreal import --endpoint http://127.0.0.1:8000 -u "$USER" -p "$PASS" \
    --ns "$NS" --db "$db" "/tmp/${db}.surql" \
    || {
      # 兼容部分版本 CLI 路径
      docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T surreal \
        surreal import --endpoint http://127.0.0.1:8000 -u "$USER" -p "$PASS" \
        --ns "$NS" --db "$db" "/tmp/${db}.surql"
    }
done

echo "==> settings / ledger → $DATA_DIR/settings"
mkdir -p "$DATA_DIR/settings"
if [ -d "$SRC/settings" ]; then
  cp -a "$SRC"/settings/. "$DATA_DIR/settings/" || true
  chown -R "${DEPLOY_USER:-ubuntu}:${DEPLOY_USER:-ubuntu}" "$DATA_DIR/settings" || true
fi

echo "==> Hermes 配置 → $HOME/.hermes（若包内有）"
if [ -f "$SRC/hermes/hermes_config.tgz" ]; then
  mkdir -p "${HERMES_HOME:-$HOME/.hermes}"
  tar -xzf "$SRC/hermes/hermes_config.tgz" -C "${HERMES_HOME:-$HOME/.hermes}"
  echo "  已解压 Hermes 配置；请再跑 install_hermes.sh + provision"
fi

echo "==> 重启 backend 以加载 settings 卷"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart backend || true
echo "导入完成"

