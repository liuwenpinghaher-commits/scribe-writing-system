# Hermes gateway systemd units (demo)

Installed on the demo host under `/etc/systemd/system/` with the same layout as
existing `hermes-gateway-scribe3*.service` units.

| Unit | Port | Profile | Docker host bind |
|------|------|---------|------------------|
| hermes-gateway | 8642 | default | 172.18.0.1 |
| hermes-gateway-scribe3 | 8643 | scribe3 | 172.18.0.1 |
| hermes-gateway-scribe3-write | 8644 | scribe3_write | 172.18.0.1 |
| hermes-gateway-scribe3-deduce | 8645 | scribe3_deduce | 172.18.0.1 |
| hermes-gateway-scribe3-deduce-preview | 8646 | scribe3_deduce_preview | 172.18.0.1 |
| hermes-gateway-scribe3-plan | 8647 | scribe3_plan | 172.18.0.1 |
| hermes-gateway-scribe3-draft | 8648 | scribe3_draft | 172.18.0.1 |

Install / reinstall on host（推荐一键）:

```bash
bash deploy/prod/scripts/install_hermes_units.sh
# 或手工:
sudo cp deploy/prod/systemd/hermes-gateway-scribe3-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-gateway-scribe3-plan hermes-gateway-scribe3-draft \
  hermes-gateway-scribe3-deduce hermes-gateway-scribe3-deduce-preview
```

`deploy/prod/scripts/deploy.sh` 会 **best-effort** 同步上述 unit（不阻断 compose）。

Restart all: `deploy/prod/scripts/restart-hermes-gateways.sh`

Notes:
- Profile `.env` must set `API_SERVER_PORT` correctly (write .env defaults to 8644).
- **全部** stage/core 网关 `API_SERVER_HOST=172.18.0.1`，backend 容器经网桥访问；**勿**绑 `127.0.0.1`。
- compose / `.env` 须有 `HERMES_PLAN_RUNS_API` / `HERMES_DRAFT_RUNS_API` / `HERMES_DEDUCE_*` 指向 `http://172.18.0.1:864x/v1`。
