# Hermes gateway systemd units (demo)

Installed on the demo host under `/etc/systemd/system/` with the same layout as
existing `hermes-gateway-scribe3*.service` units.

| Unit | Port | Profile | Docker host bind |
|------|------|---------|------------------|
| hermes-gateway | 8642 | default | 172.18.0.1 |
| hermes-gateway-scribe3 | 8643 | scribe3 | 172.18.0.1 |
| hermes-gateway-scribe3-write | 8644 | scribe3_write | 172.18.0.1 |
| hermes-gateway-scribe3-deduce | 8645 | scribe3_deduce | 127.0.0.1 |
| hermes-gateway-scribe3-deduce-preview | 8646 | scribe3_deduce_preview | 127.0.0.1 |
| hermes-gateway-scribe3-plan | 8647 | scribe3_plan | 172.18.0.1 |
| hermes-gateway-scribe3-draft | 8648 | scribe3_draft | 172.18.0.1 |

Install / reinstall on host:

```bash
sudo cp deploy/prod/systemd/hermes-gateway-scribe3-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-gateway-scribe3-plan hermes-gateway-scribe3-draft \
  hermes-gateway-scribe3-deduce hermes-gateway-scribe3-deduce-preview
```

Restart all: `deploy/prod/scripts/restart-hermes-gateways.sh`

Notes:
- Profile `.env` must set `API_SERVER_PORT` correctly (write .env defaults to 8644).
- `API_SERVER_HOST=172.18.0.1` so backend containers reach plan/draft/write.
