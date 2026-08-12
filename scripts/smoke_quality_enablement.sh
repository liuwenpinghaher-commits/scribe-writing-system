#!/usr/bin/env bash
# demo 质量使能冒烟：在 backend 容器内打真路径（勿猜公网 SPA path）
set -euo pipefail
KEY="${SSH_KEY:-$HOME/.ssh/id_tencent_lh}"
HOST="${DEPLOY_HOST:-82.157.130.140}"
USER="${DEPLOY_USER:-ubuntu}"
WORK="${1:-main}"

ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 "${USER}@${HOST}" \
  "docker exec -w /app -e PYTHONPATH=/app prod-backend-1 python3 - <<'PY'
import json, urllib.request
from urllib.parse import urlencode

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:3321'+path, timeout=8) as r:
        return r.status, json.loads(r.read().decode())

h, _ = get('/health')
assert h == 200
# 真路由：director.workflow_snapshot_ep
st, body = get('/workflow/snapshot?' + urlencode({'work': '${WORK}'}))
assert st == 200
assert 'creative_suggestions' in body or 'next_step' in body, list(body.keys())[:20]
from scribe3.context_budget import generation_physical_order_names
from scribe3.settings import get_setting
o = generation_physical_order_names(v2=True)
assert o.index('outline') == o.index('drama_vacuum') + 1
print(json.dumps({
    'health': h,
    'workflow_status': st,
    'has_creative_suggestions': 'creative_suggestions' in body,
    'creative_len': len(body.get('creative_suggestions') or []),
    'outline_after_drama': True,
    'create_mode_default': get_setting('SCRIBE3_CREATE_MODE'),
}, ensure_ascii=False))
print('SMOKE_QUALITY_ENABLEMENT_OK')
PY"
