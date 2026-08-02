#!/usr/bin/env bash
# 在腾讯云 Ubuntu 24.04 上首次初始化 scribe3 部署环境。
# 用法（在服务器上，建议 sudo）:
#   curl -fsSL ... | bash   或
#   sudo bash deploy/prod/scripts/bootstrap_server.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/liuwenpinghaher-commits/scribe-writing-system.git}"
REPO_DIR="${SCRIBE3_REPO_DIR:-/opt/scribe3/app}"
DATA_DIR="${SCRIBE3_DATA_DIR:-/opt/scribe3/data}"
DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
BRANCH="${DEPLOY_BRANCH:-main}"

export DEBIAN_FRONTEND=noninteractive

echo "==> apt 基础包"
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq ufw \
  python3 python3-venv python3-pip \
  docker.io docker-compose-v2

echo "==> docker 权限"
systemctl enable --now docker
usermod -aG docker "$DEPLOY_USER" || true

echo "==> 目录"
mkdir -p "$DATA_DIR/surreal" "$DATA_DIR/settings" "$DATA_DIR/backups" "$DATA_DIR/hermes" \
  /opt/scribe3/logs /opt/scribe3/bin
chown -R "$DEPLOY_USER:$DEPLOY_USER" /opt/scribe3

echo "==> 克隆/更新仓库 → $REPO_DIR"
if [ -d "$REPO_DIR/.git" ]; then
  sudo -u "$DEPLOY_USER" git -C "$REPO_DIR" fetch --all --prune
  sudo -u "$DEPLOY_USER" git -C "$REPO_DIR" checkout "$BRANCH"
  sudo -u "$DEPLOY_USER" git -C "$REPO_DIR" reset --hard "origin/$BRANCH"
else
  # 私有仓：需事先配置 git 凭证或 deploy key；也可先 rsync 代码再 git remote add
  mkdir -p "$(dirname "$REPO_DIR")"
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    auth_url="https://x-access-token:${GITHUB_TOKEN}@github.com/liuwenpinghaher-commits/scribe-writing-system.git"
    sudo -u "$DEPLOY_USER" git clone --branch "$BRANCH" "$auth_url" "$REPO_DIR"
    sudo -u "$DEPLOY_USER" git -C "$REPO_DIR" remote set-url origin "$REPO_URL"
  else
    sudo -u "$DEPLOY_USER" git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR" || {
      echo "clone 失败：私有仓请 export GITHUB_TOKEN=... 或预置 deploy key" >&2
      mkdir -p "$REPO_DIR"
      chown -R "$DEPLOY_USER:$DEPLOY_USER" "$REPO_DIR"
    }
  fi
fi

echo "==> 防火墙（若 ufw 启用）"
if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
  ufw allow OpenSSH || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi

echo "==> 安装 SurrealDB CLI（导入/备份用）"
if ! command -v surreal >/dev/null 2>&1; then
  curl -sSf https://install.surrealdb.com | sh
  # install 脚本默认装到 ~/.surrealdb；root 下链到 /usr/local/bin
  if [ -x "$HOME/.surrealdb/surreal" ]; then
    install -m 755 "$HOME/.surrealdb/surreal" /usr/local/bin/surreal
  fi
fi
surreal version || true

echo "==> bootstrap 完成"
echo "下一步:"
echo "  1) 配置 $REPO_DIR/deploy/prod/.env"
echo "  2) 导入数据: deploy/prod/scripts/import_data.sh"
echo "  3) 部署栈:   deploy/prod/scripts/deploy.sh"
echo "  4) 安装 Hermes: deploy/prod/scripts/install_hermes.sh"

