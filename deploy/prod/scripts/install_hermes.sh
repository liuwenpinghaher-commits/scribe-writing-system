#!/usr/bin/env bash
# 在服务器安装 Hermes Agent，并启用 default/scribe3/scribe3_write 三网关 systemd；
# 另从仓库 install plan/draft/deduce* units（若存在）。
# 前置: 已解压 hermes_config.tgz 到 ~/.hermes（含 .env 与 profiles），或稍后手工配置密钥。
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
HERMES_HOME="${HERMES_HOME:-/home/$DEPLOY_USER/.hermes}"
HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-$HERMES_HOME/hermes-agent}"
REPO_DIR="${SCRIBE3_REPO_DIR:-/opt/scribe3/app}"
UNIT_DIR="/etc/systemd/system"

echo "==> 确保 python3.11+ / venv / git / node(可选)"
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends python3 python3-venv python3-pip git curl

echo "==> 克隆 hermes-agent（若无）"
sudo -u "$DEPLOY_USER" mkdir -p "$HERMES_HOME"
if [ ! -d "$HERMES_AGENT_DIR/.git" ]; then
  # 与本地一致的 git 安装方式；仓库公开可直拉
  sudo -u "$DEPLOY_USER" git clone --depth 1 https://github.com/NousResearch/hermes-agent.git "$HERMES_AGENT_DIR" \
    || sudo -u "$DEPLOY_USER" git clone --depth 1 https://github.com/hermes-ai/hermes-agent.git "$HERMES_AGENT_DIR" \
    || {
      echo "无法克隆 hermes-agent，请设置 HERMES_AGENT_GIT_URL 后重试" >&2
      if [ -n "${HERMES_AGENT_GIT_URL:-}" ]; then
        sudo -u "$DEPLOY_USER" git clone --depth 1 "$HERMES_AGENT_GIT_URL" "$HERMES_AGENT_DIR"
      else
        exit 1
      fi
    }
fi

echo "==> venv + 安装"
sudo -u "$DEPLOY_USER" bash -lc "
  set -e
  cd '$HERMES_AGENT_DIR'
  python3 -m venv venv
  ./venv/bin/pip install -U pip wheel
  if [ -f requirements.txt ]; then ./venv/bin/pip install -r requirements.txt; fi
  if [ -f pyproject.toml ]; then ./venv/bin/pip install -e .; fi
"

echo "==> 写 systemd units"
PY="$HERMES_AGENT_DIR/venv/bin/python"
install_unit() {
  local name="$1" profile_arg="$2" workdir="$3" env_home="$4"
  local unit="hermes-gateway${name}.service"
  sudo tee "$UNIT_DIR/$unit" >/dev/null <<EOF
[Unit]
Description=Hermes gateway${name}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$workdir
Environment=HOME=/home/$DEPLOY_USER
Environment=HERMES_HOME=$env_home
Environment=VIRTUAL_ENV=$HERMES_AGENT_DIR/venv
Environment=PATH=$HERMES_AGENT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$PY -m hermes_cli.main $profile_arg gateway run --replace
Restart=always
RestartSec=5
StandardOutput=append:/opt/scribe3/logs/hermes${name}.log
StandardError=append:/opt/scribe3/logs/hermes${name}.err.log

[Install]
WantedBy=multi-user.target
EOF
}

install_unit "" "" "$HERMES_AGENT_DIR" "$HERMES_HOME"
install_unit "-scribe3" "--profile scribe3" "$HERMES_HOME/profiles/scribe3" "$HERMES_HOME/profiles/scribe3"
install_unit "-scribe3-write" "--profile scribe3_write" "$HERMES_HOME/profiles/scribe3_write" "$HERMES_HOME/profiles/scribe3_write"

sudo mkdir -p /opt/scribe3/logs
sudo chown -R "$DEPLOY_USER:$DEPLOY_USER" /opt/scribe3/logs "$HERMES_HOME"

echo "==> provision scribe3 网关 overlay（若 repo 在）"
if [ -d "$REPO_DIR/scribe3" ]; then
  sudo -u "$DEPLOY_USER" bash -lc "
    set -e
    cd '$REPO_DIR'
    python3 -m venv /opt/scribe3/venv-provision 2>/dev/null || true
    /opt/scribe3/venv-provision/bin/pip -q install -r scribe3/requirements.txt || true
    HERMES_HOME='$HERMES_HOME' /opt/scribe3/venv-provision/bin/python -m scribe3.scripts.provision_hermes --commit || \
      python3 -m scribe3.scripts.provision_hermes --commit || true
  " || echo "provision 跳过/失败：可稍后手动跑"
fi

echo "==> enable + start core gateways"
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-gateway.service hermes-gateway-scribe3.service hermes-gateway-scribe3-write.service

# plan/draft/deduce*：仓库固化 unit（可重复执行）
if [ -x "$REPO_DIR/deploy/prod/scripts/install_hermes_units.sh" ]; then
  echo "==> install stage gateway units (plan/draft/deduce*)"
  SCRIBE3_REPO_DIR="$REPO_DIR" DEPLOY_USER="$DEPLOY_USER" \
    bash "$REPO_DIR/deploy/prod/scripts/install_hermes_units.sh" || echo "warn: stage units install failed" >&2
elif [ -d "$REPO_DIR/deploy/prod/systemd" ]; then
  echo "==> copy stage units from repo"
  sudo cp "$REPO_DIR"/deploy/prod/systemd/hermes-gateway-scribe3-*.service "$UNIT_DIR/" 2>/dev/null || true
  sudo systemctl daemon-reload
  sudo systemctl enable --now \
    hermes-gateway-scribe3-plan hermes-gateway-scribe3-draft \
    hermes-gateway-scribe3-deduce hermes-gateway-scribe3-deduce-preview 2>/dev/null || true
fi

sleep 3
systemctl --no-pager --full status hermes-gateway.service hermes-gateway-scribe3.service hermes-gateway-scribe3-write.service || true

echo "Hermes 安装完成。探测:"
for p in 8642 8643 8644 8645 8646 8647 8648; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' -m 3 "http://172.18.0.1:${p}/v1/models" 2>/dev/null || echo fail)
  echo "  :${p} http=$code"
done

