#!/usr/bin/env bash
# 将本机 scribe3 Python 包热更新到 demo 已部署 backend（无需 GHA / 全量 docker build）。
# 用法：
#   ./scripts/hot_deploy_backend.sh
#   DEPLOY_HOST=82.157.130.140 DEPLOY_USER=ubuntu SSH_KEY=~/.ssh/id_tencent_lh ./scripts/hot_deploy_backend.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${DEPLOY_HOST:-82.157.130.140}"
USER="${DEPLOY_USER:-ubuntu}"
KEY="${SSH_KEY:-$HOME/.ssh/id_tencent_lh}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15)
SCP=(scp -i "$KEY" -o StrictHostKeyChecking=no)
REMOTE="${USER}@${HOST}"
CONTAINER="${BACKEND_CONTAINER:-prod-backend-1}"
APP_DIR="${REMOTE_APP_DIR:-/opt/scribe3/app}"

echo "==> pack scribe3 tree (python only)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/scribe3"
rsync -a \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'web/node_modules' \
  --exclude 'web/dist' \
  --exclude 'tests' \
  --exclude '.venv' \
  "$ROOT/scribe3/" "$TMP/scribe3/"
# 迁移文件需要
if [ -d "$ROOT/scribe3/migrations" ]; then
  rsync -a "$ROOT/scribe3/migrations/" "$TMP/scribe3/migrations/"
fi
tar -C "$TMP" -czf "$TMP/scribe3-hot.tgz" scribe3
ls -lh "$TMP/scribe3-hot.tgz"

echo "==> upload + extract to $APP_DIR and $CONTAINER"
"${SCP[@]}" "$TMP/scribe3-hot.tgz" "$REMOTE:/tmp/scribe3-hot.tgz"
"${SSH[@]}" "$REMOTE" bash -s <<REMOTE
set -euo pipefail
APP_DIR='$APP_DIR'
CONTAINER='$CONTAINER'
sudo mkdir -p "\$APP_DIR"
sudo tar -xzf /tmp/scribe3-hot.tgz -C "\$APP_DIR"
# 同步进运行中容器
docker cp "\$APP_DIR/scribe3" "\$CONTAINER:/app/"
docker restart "\$CONTAINER"
echo restarted
# 等健康
for i in \$(seq 1 30); do
  if docker exec "\$CONTAINER" python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3321/health',timeout=3).read()" 2>/dev/null; then
    echo HEALTH_OK
    exit 0
  fi
  sleep 2
done
echo "health timeout" >&2
docker logs "\$CONTAINER" --tail 40 >&2 || true
exit 1
REMOTE

echo "==> hot deploy done"
