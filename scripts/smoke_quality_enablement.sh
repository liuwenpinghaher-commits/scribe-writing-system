#!/usr/bin/env bash
# demo 质量使能冒烟（backend 容器内）
# 说明：GET /workflow/snapshot 在 AUTH 开启时返回 401，故用 in-process build_workflow_snapshot。
set -euo pipefail
KEY="${SSH_KEY:-$HOME/.ssh/id_tencent_lh}"
HOST="${DEPLOY_HOST:-82.157.130.140}"
USER="${DEPLOY_USER:-ubuntu}"
WORK="${1:-main}"
ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 "${USER}@${HOST}" \
  "docker exec -w /app -e PYTHONPATH=/app prod-backend-1 python3 -c \"
import json, urllib.request
from scribe3.director import build_workflow_snapshot
from scribe3.context_budget import generation_physical_order_names
from scribe3.settings import get_setting
from scribe3.density_trace_store import density_delta, slim_density_trace
h=urllib.request.urlopen('http://127.0.0.1:3321/health',timeout=5).status
assert h==200
class St:
  db_name='''${WORK}'''
  def get_intent(self): return {}
  def list_chapters(self): return []
  def characters(self): return []
  def effective_open_promises(self): return [{'id':'p1','text':'probe','status':'open'}]
  def open_promises(self): return self.effective_open_promises()
  def list_promises(self): return []
  def get_chapter(self,s): return {'synopsis':'','beats':[]}
  def count_canon_debt(self): return {}
  def list_canon_candidates(self,**k): return []
snap=build_workflow_snapshot(St(), work='''${WORK}''', seq=None)
assert 'creative_suggestions' in snap or 'next_step' in snap
o=generation_physical_order_names(v2=True)
assert o.index('outline')==o.index('drama_vacuum')+1
d=density_delta(slim_density_trace({'audit_meta_share':0.1,'drama_core_share':0.4,'provenance_in_prompt_tokens':0}), slim_density_trace({'audit_meta_share':0.12,'drama_core_share':0.35,'provenance_in_prompt_tokens':0}))
print(json.dumps({'health':h,'has_creative_suggestions':'creative_suggestions' in snap,'creative_len':len(snap.get('creative_suggestions') or []),'outline_after_drama':True,'create_mode_default':get_setting('SCRIBE3_CREATE_MODE'),'density_delta_ok':d is not None,'http_workflow':'auth_required_use_inprocess'},ensure_ascii=False))
print('SMOKE_QUALITY_ENABLEMENT_OK')
\""
