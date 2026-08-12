#!/usr/bin/env bash
# =============================================================================
# 工程健康度 / 分层锁 — demo 已部署栈冒烟（不启第二套库）
#
# 用法：
#   ./scripts/smoke_eh.sh
#
# 环境变量（可选）：
#   PUBLIC_BASE   默认 https://tonglu.qing.blue
#   DEPLOY_HOST   默认 82.157.130.140
#   DEPLOY_USER   默认 ubuntu
#   SSH_KEY       默认 ~/.ssh/id_tencent_lh
#   BACKEND_CONTAINER  默认 prod-backend-1
#   SKIP_SSH=1    仅公网 HTTP，不做容器内 migration/分层检查
# =============================================================================
set -euo pipefail

PUBLIC_BASE="${PUBLIC_BASE:-https://tonglu.qing.blue}"
HOST="${DEPLOY_HOST:-82.157.130.140}"
USER="${DEPLOY_USER:-ubuntu}"
KEY="${SSH_KEY:-${DEPLOY_SSH_KEY_FILE:-$HOME/.ssh/id_tencent_lh}}"
CONTAINER="${BACKEND_CONTAINER:-prod-backend-1}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15)

fail() { echo "DEMO_EH_FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

echo "==> EH smoke · base=${PUBLIC_BASE}"

# 1) ready / health（API 前缀，勿打 SPA）
ready_body=$(curl -skS -m 15 "${PUBLIC_BASE}/api/ready") || fail "curl ready"
echo "$ready_body" | grep -q '"ready"[[:space:]]*:[[:space:]]*true' \
  || fail "ready not true: $ready_body"
ok "api/ready true"

health_body=$(curl -skS -m 15 "${PUBLIC_BASE}/api/health") || fail "curl health"
echo "$health_body" | grep -q '"ok"[[:space:]]*:[[:space:]]*true' \
  || fail "health ok not true: ${health_body:0:200}"
echo "$health_body" | grep -q '"db"[[:space:]]*:[[:space:]]*"ok"' \
  || fail "health db not ok: ${health_body:0:200}"
ok "api/health ok/db=ok"

if [[ "${SKIP_SSH:-0}" == "1" ]]; then
  echo "SKIP_SSH=1 · skip container checks"
  echo "DEMO_EH_OK"
  exit 0
fi

[[ -f "$KEY" ]] || fail "missing SSH key: $KEY"

# 2) migration 131 + 业务层私有 store = 0（容器内与已部署代码一致）
"${SSH[@]}" "${USER}@${HOST}" "docker exec ${CONTAINER} python -c \"
from scribe3.store.surreal import SurrealStore
st = SurrealStore(db='main')
ids = [str(r.get('id','')) for r in (st._query('SELECT meta::id(id) AS id FROM _migration') or [])]
assert any('131' in i for i in ids), ids[-5:]
print('migration_131', [i for i in ids if '131' in i])
# public APIs still present
assert hasattr(SurrealStore, 'ping')
assert hasattr(SurrealStore, 'create_only_quality_job')
import pathlib, re
pat = re.compile(r'\\\\._(query|execute_write|raw_query)\\\\s*\\\\(')
hits = []
for p in pathlib.Path('scribe3').rglob('*.py'):
    s = str(p)
    if '/store/' in s or '/tests/' in s or '/tools/' in s:
        continue
    for i, line in enumerate(p.read_text(errors='replace').splitlines(), 1):
        if line.lstrip().startswith('#'):
            continue
        if pat.search(line):
            hits.append(f'{s}:{i}')
assert not hits, hits[:10]
print('private_business_hits', 0)
\"" || fail "container migration/layer check"

ok "migration 131 + business private store = 0"
echo "DEMO_EH_OK"
