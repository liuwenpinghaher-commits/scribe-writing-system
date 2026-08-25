#!/usr/bin/env bash
# =============================================================================
# scribe3 demo 主部署通道（不依赖 GitHub Actions）
#
# 主路径：本机 SSH → demo 机，与 GHA / github.com 可用性无关。
# GHA 仅是可选支路（workflow_dispatch），挂了也不影响本脚本。
#
# 用法：
#   ./scripts/deploy_demo.sh              # 默认 MODE=hot（Python 热更，推荐）
#   ./scripts/deploy_demo.sh hot
#   ./scripts/deploy_demo.sh frontend     # 构建 web 并热更静态资源（不 wipe 旧 hash）
#   ./scripts/deploy_demo.sh server-git   # 服务器 git pull origin/main 后热应用
#   ./scripts/deploy_demo.sh full         # 整树上传 + compose rebuild（重，慎用）
#   ./scripts/deploy_demo.sh prune        # 仅磁盘卫生：悬空镜像 + build cache + 部署残留
#
# 环境变量（均可选）：
#   DEPLOY_HOST  默认 82.157.130.140
#   DEPLOY_USER  默认 ubuntu
#   SSH_KEY      默认 ~/.ssh/id_tencent_lh
#   BACKEND_CONTAINER  默认 prod-backend-1
#   REMOTE_APP_DIR     默认 /opt/scribe3/app
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-hot}"
HOST="${DEPLOY_HOST:-82.157.130.140}"
USER="${DEPLOY_USER:-ubuntu}"
KEY="${SSH_KEY:-${DEPLOY_SSH_KEY_FILE:-$HOME/.ssh/id_tencent_lh}}"
# 本机 VPN/utun 会劫持 82.157，SSH banner 超时；绑局域网网卡绕过。
SSH_BIND_IFACE="${SSH_BIND_IFACE:-en0}"
SSH=(ssh -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o ServerAliveInterval=15)
SCP=(scp -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no)
if ifconfig "$SSH_BIND_IFACE" >/dev/null 2>&1; then
  SSH+=(-o "BindInterface=$SSH_BIND_IFACE")
  SCP+=(-o "BindInterface=$SSH_BIND_IFACE")
fi
REMOTE="${USER}@${HOST}"
CONTAINER="${BACKEND_CONTAINER:-prod-backend-1}"
APP_DIR="${REMOTE_APP_DIR:-/opt/scribe3/app}"

if [[ ! -f "$KEY" ]]; then
  echo "缺少 SSH 密钥: $KEY" >&2
  exit 1
fi

wait_health() {
  local c="$1"
  for i in $(seq 1 40); do
    if "${SSH[@]}" "$REMOTE" "docker exec '$c' python3 -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:3321/health',timeout=3).read()\"" >/dev/null 2>&1; then
      echo "HEALTH_OK ($c)"
      return 0
    fi
    sleep 2
  done
  echo "health timeout" >&2
  "${SSH[@]}" "$REMOTE" "docker logs '$c' --tail 40" >&2 || true
  return 1
}

# 部署后磁盘卫生：清本轮 /tmp 包 + 可选悬空镜像/build cache（不删在用镜像）
# 根因：compose --build / 多次 rebuild 留下 <none> 层；frontend npm ci 留 node_modules；scp 包不删。
remote_disk_hygiene() {
  local also_docker_prune="${1:-0}"
  local also_node_modules="${2:-0}"
  "${SSH[@]}" "$REMOTE" bash -s <<REMOTE
set -euo pipefail
APP_DIR='$APP_DIR'
ALSO_DOCKER='$also_docker_prune'
ALSO_NM='$also_node_modules'

# 1) 本仓库部署/验证常用残留（白名单，不动 tat_agent 等）
rm -f /tmp/web-src.tgz /tmp/scribe3-hot.tgz /tmp/scribe3-deploy.tgz \
  /tmp/scribe3-nginx-default.conf /tmp/scribe3.prod.env.bak 2>/dev/null || true
rm -rf /tmp/scribe3-web-verify /tmp/scribe3-session-vitest /tmp/scribe3-type-fix \
  /tmp/scribe3-sync-parts /tmp/scribe3-import.* /tmp/scribe3-frontend-build.* 2>/dev/null || true

# 2) frontend 构建残留：node_modules 仅构建需要，产物已在 dist / 容器内
if [ "\$ALSO_NM" = "1" ] && [ -d "\$APP_DIR/scribe3/web/node_modules" ]; then
  rm -rf "\$APP_DIR/scribe3/web/node_modules"
  echo "removed \$APP_DIR/scribe3/web/node_modules"
fi

# 3) Docker 悬空镜像 + buildkit 缓存（不 prune -a，保留 tag 过的在用镜像）
if [ "\$ALSO_DOCKER" = "1" ]; then
  if docker info >/dev/null 2>&1; then
    docker image prune -f || true
    docker builder prune -f || true
    echo "docker image/builder prune done"
  fi
fi

df -h / | tail -1 || true
REMOTE
}

mode_hot() {
  echo "==> [主路径] hot: 热更 scribe3 Python 包 → $REMOTE:$CONTAINER"
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' RETURN
  mkdir -p "$TMP/scribe3"
  rsync -a \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'web/node_modules' \
    --exclude 'web/dist' \
    --exclude 'web/e2e' \
    --exclude 'tests' \
    --exclude '.venv' \
    --exclude '._*' \
    --exclude '.DS_Store' \
    "$ROOT/scribe3/" "$TMP/scribe3/"
  find "$TMP/scribe3" -name '._*' -delete
  echo "==> compileall"
  python3 -m compileall -q -f "$TMP/scribe3" || {
    echo "compileall 失败，禁止上铜炉" >&2
    exit 1
  }
  COPYFILE_DISABLE=1 tar -C "$TMP" -czf "$TMP/scribe3-hot.tgz" scribe3
  ls -lh "$TMP/scribe3-hot.tgz"
  "${SCP[@]}" "$TMP/scribe3-hot.tgz" "$REMOTE:/tmp/scribe3-hot.tgz"
  "${SSH[@]}" "$REMOTE" bash -s <<REMOTE
set -euo pipefail
APP_DIR='$APP_DIR'
CONTAINER='$CONTAINER'
sudo mkdir -p "\$APP_DIR"
sudo tar -xzf /tmp/scribe3-hot.tgz -C "\$APP_DIR"
docker cp "\$APP_DIR/scribe3" "\$CONTAINER:/app/"
docker restart "\$CONTAINER"
rm -f /tmp/scribe3-hot.tgz
echo restarted
REMOTE
  wait_health "$CONTAINER"
  if [[ "${V634_SMOKE:-1}" != "0" ]]; then
    echo "==> v634 入口冒烟"
    if ! "${SSH[@]}" "$REMOTE" "docker exec '$CONTAINER' python3 -m scribe3.tools.v634_smoke --mode imports"; then
      echo "v634 冒烟失败，禁止宣布可验收" >&2
      exit 1
    fi
  fi
  echo "==> hot deploy 完成（未走 GitHub Actions）"
}

mode_frontend() {
  echo "==> [主路径] frontend: 构建 SPA 并热更静态文件（保留旧 assets，避免缓存断链）"
  FRONTEND="${FRONTEND_CONTAINER:-prod-frontend-1}"
  # 先同步 web 源码
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' RETURN
  mkdir -p "$TMP/scribe3/web"
  rsync -a \
    --exclude 'node_modules' \
    --exclude 'dist' \
    --exclude 'e2e' \
    "$ROOT/scribe3/web/" "$TMP/scribe3/web/"
  tar -C "$TMP" -czf "$TMP/web-src.tgz" scribe3/web
  "${SCP[@]}" "$TMP/web-src.tgz" "$REMOTE:/tmp/web-src.tgz"
  # nginx 配置一并同步
  "${SCP[@]}" "$ROOT/deploy/prod/nginx/default.conf" "$REMOTE:/tmp/scribe3-nginx-default.conf"
  "${SSH[@]}" "$REMOTE" bash -s <<REMOTE
set -euo pipefail
APP_DIR='$APP_DIR'
FRONTEND='$FRONTEND'
sudo tar -xzf /tmp/web-src.tgz -C "\$APP_DIR"
# 构建（完整 devDeps，vite 在 devDependencies）
# 构建后立刻删 node_modules，避免宿主机常驻 ~400MB+
docker run --rm \
  -v "\$APP_DIR/scribe3/web:/app" \
  -w /app \
  -e NODE_OPTIONS=--max-old-space-size=1536 \
  node:20-alpine \
  sh -c "rm -rf node_modules && npm ci && npm run build && rm -rf node_modules"
# 叠加拷贝：不删除旧 assets（旧 index 缓存仍能拉到旧 chunk）
docker cp "\$APP_DIR/scribe3/web/dist/." "\$FRONTEND:/usr/share/nginx/html/"
# 更新 nginx：assets 404 + index no-cache
if [ -f /tmp/scribe3-nginx-default.conf ]; then
  # 若挂载了 conf，写到 host 挂载源；否则 docker cp
  if docker inspect "\$FRONTEND" --format '{{range .Mounts}}{{.Source}}{{println}}{{end}}' | grep -q nginx; then
    CONF_SRC=\$(docker inspect "\$FRONTEND" --format '{{range .Mounts}}{{if eq .Destination "/etc/nginx/conf.d/default.conf"}}{{.Source}}{{end}}{{end}}')
    if [ -n "\$CONF_SRC" ] && [ -f "\$CONF_SRC" ] || [ -n "\$CONF_SRC" ]; then
      sudo cp /tmp/scribe3-nginx-default.conf "\$CONF_SRC" 2>/dev/null || true
    fi
  fi
  docker cp /tmp/scribe3-nginx-default.conf "\$FRONTEND:/etc/nginx/conf.d/default.conf" || true
  docker exec "\$FRONTEND" nginx -t
  docker exec "\$FRONTEND" nginx -s reload || docker restart "\$FRONTEND"
fi
rm -f /tmp/web-src.tgz /tmp/scribe3-nginx-default.conf
# frontend 路径用 docker run --rm，一般不堆镜像；仍清一次悬空 + builder 防 buildkit 涨
docker image prune -f >/dev/null 2>&1 || true
docker builder prune -f >/dev/null 2>&1 || true
echo FRONTEND_DEPLOY_OK
REMOTE
  echo "==> frontend deploy 完成。请浏览器强制刷新（Ctrl+Shift+R）"
}

mode_server_git() {
  echo "==> [主路径] server-git: 服务器 git pull + 热应用（需服务器能访问 origin）"
  "${SSH[@]}" "$REMOTE" bash -s <<REMOTE
set -euo pipefail
APP_DIR='$APP_DIR'
CONTAINER='$CONTAINER'
cd "\$APP_DIR"
# 不依赖 GHA；服务器本地 deploy key 拉代码
git fetch --prune origin main
git checkout main 2>/dev/null || git checkout -B main
git reset --hard origin/main
# 热应用 backend 源码（避免 compose rebuild 占满内存）
if docker ps --format '{{.Names}}' | grep -qx "\$CONTAINER"; then
  docker cp "\$APP_DIR/scribe3" "\$CONTAINER:/app/"
  docker restart "\$CONTAINER"
  echo restarted
else
  echo "容器 \$CONTAINER 未运行；请手动 deploy.sh 起栈" >&2
  exit 1
fi
REMOTE
  wait_health "$CONTAINER"
  if [[ "${V634_SMOKE:-1}" != "0" ]]; then
    echo "==> v634 入口冒烟"
    if ! "${SSH[@]}" "$REMOTE" "docker exec '$CONTAINER' python3 -m scribe3.tools.v634_smoke --mode imports"; then
      echo "v634 冒烟失败，禁止宣布可验收" >&2
      exit 1
    fi
  fi
  echo "==> server-git deploy 完成"
}

mode_full() {
  echo "==> [重路径] full: 整树上传 + compose rebuild（慎用，demo 内存紧）"
  echo "    确认 free -h 可用内存充足；Ctrl+C 可中止"
  sleep 2
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' RETURN
  mkdir -p "$TMP/app"
  rsync -a \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '**/.venv' \
    --exclude '**/__pycache__' \
    --exclude 'scribe3/web/dist' \
    --exclude 'scribe3/web/e2e/.snapshots' \
    --exclude 'surrealdb-docs-cache' \
    --exclude 'docs/external' \
    --exclude 'oh-story-claudecode-main' \
    --exclude 'artifacts' \
    --exclude '.codegraph' \
    --exclude '*.zip' \
    "$ROOT/" "$TMP/app/"
  rm -f "$TMP/app/deploy/prod/.env"
  tar -C "$TMP" -czf "$TMP/scribe3-deploy.tgz" app
  ls -lh "$TMP/scribe3-deploy.tgz"
  "${SCP[@]}" "$TMP/scribe3-deploy.tgz" "$REMOTE:/tmp/scribe3-deploy.tgz"
  "${SSH[@]}" "$REMOTE" bash -s <<REMOTE
set -euo pipefail
test -f /tmp/scribe3-deploy.tgz
test -f /opt/scribe3/app/deploy/prod/.env
cp -a /opt/scribe3/app/deploy/prod/.env /tmp/scribe3.prod.env.bak
mkdir -p /opt/scribe3
tar -xzf /tmp/scribe3-deploy.tgz -C /opt/scribe3
mkdir -p /opt/scribe3/app/deploy/prod
cp -a /tmp/scribe3.prod.env.bak /opt/scribe3/app/deploy/prod/.env
chmod 600 /opt/scribe3/app/deploy/prod/.env
chmod +x /opt/scribe3/app/deploy/prod/scripts/*.sh || true
export SCRIBE3_REPO_DIR=/opt/scribe3/app
export SKIP_GIT=1
bash /opt/scribe3/app/deploy/prod/scripts/deploy.sh
# deploy.sh 成功后会自行 image/builder prune；这里再清 tarball
rm -f /tmp/scribe3-deploy.tgz /tmp/scribe3.prod.env.bak
REMOTE
  echo "==> full deploy 完成"
}

mode_prune() {
  echo "==> [卫生] demo 磁盘：悬空镜像 + build cache + 部署残留 + web/node_modules"
  remote_disk_hygiene 1 1
  echo "==> prune 完成"
}

case "$MODE" in
  hot|backend) mode_hot ;;
  frontend|web) mode_frontend ;;
  server-git|pull) mode_server_git ;;
  full|rebuild) mode_full ;;
  prune|disk|hygiene) mode_prune ;;
  -h|--help|help)
    sed -n '2,22p' "$0"
    exit 0
    ;;
  *)
    echo "未知 MODE=$MODE（hot | frontend | server-git | full | prune）" >&2
    exit 1
    ;;
esac
