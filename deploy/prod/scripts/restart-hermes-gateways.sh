#!/usr/bin/env bash
# Restart all scribe3 Hermes gateway systemd units (demo/prod host).
set -euo pipefail
units=(
  hermes-gateway
  hermes-gateway-scribe3
  hermes-gateway-scribe3-write
  hermes-gateway-scribe3-plan
  hermes-gateway-scribe3-draft
  hermes-gateway-scribe3-deduce
  hermes-gateway-scribe3-deduce-preview
)
for u in "${units[@]}"; do
  if systemctl cat "${u}.service" &>/dev/null; then
    echo "restart ${u}"
    sudo systemctl restart "${u}.service" || true
  fi
done
systemctl is-active "${units[@]/%/.service}" 2>/dev/null || true
ss -lntp | grep -E '864[2-8]' || true
