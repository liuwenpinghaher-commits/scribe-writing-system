#!/usr/bin/env bash
# 从仓库 deploy/prod/systemd 安装/刷新 Hermes gateway systemd units（demo/prod 宿主机）。
# 不装 hermes-agent 本身；只做 unit 固化 + enable。
set -euo pipefail

REPO_DIR="${SCRIBE3_REPO_DIR:-/opt/scribe3/app}"
UNIT_SRC="${HERMES_UNIT_SRC:-$REPO_DIR/deploy/prod/systemd}"
UNIT_DIR="/etc/systemd/system"

units=(
  hermes-gateway-scribe3-plan.service
  hermes-gateway-scribe3-draft.service
  hermes-gateway-scribe3-deduce.service
  hermes-gateway-scribe3-deduce-preview.service
)

if [ ! -d "$UNIT_SRC" ]; then
  echo "缺少 unit 目录: $UNIT_SRC" >&2
  exit 1
fi

sudo mkdir -p /opt/scribe3/logs
sudo chown -R "${DEPLOY_USER:-ubuntu}:${DEPLOY_USER:-ubuntu}" /opt/scribe3/logs 2>/dev/null || true

echo "==> 安装 systemd units from $UNIT_SRC"
for u in "${units[@]}"; do
  if [ ! -f "$UNIT_SRC/$u" ]; then
    echo "warn: 跳过缺失 $u" >&2
    continue
  fi
  sudo cp "$UNIT_SRC/$u" "$UNIT_DIR/$u"
  echo "  installed $u"
done

sudo systemctl daemon-reload

enable_list=()
for u in "${units[@]}"; do
  if [ -f "$UNIT_DIR/$u" ]; then
    enable_list+=("${u%.service}")
  fi
done

if [ "${#enable_list[@]}" -gt 0 ]; then
  echo "==> enable --now ${enable_list[*]}"
  sudo systemctl enable --now "${enable_list[@]}"
fi

echo "==> status"
systemctl is-enabled "${enable_list[@]/%/.service}" 2>/dev/null || true
systemctl is-active "${enable_list[@]/%/.service}" 2>/dev/null || true
ss -lntp 2>/dev/null | grep -E '864[2-8]' || true
echo "done."
