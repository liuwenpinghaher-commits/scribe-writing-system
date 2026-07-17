#!/usr/bin/env bash
# H-11 Hermes 升级/日常体检 smoke(v018 审查):对 default/read/write 三网关做体检。
#
# 用法:
#   scribe3/scripts/hermes_smoke.sh          # 只读检查,不烧 token
#   scribe3/scripts/hermes_smoke.sh --live   # 额外真发 1 次 :8643 Responses 短文本(烧 1 笔调用)
#
# 覆盖(对应设计文档 §6.1 运行时验收):
#   1. 三网关 /health(版本)与 /health/detailed(status ok)
#   2. /v1/capabilities:read 网关须有 responses_api,write 网关须有 run_submission + run_approval_response
#   3. :8643 /v1/skills 含 scribe-novel-v2
#   4. hermes -p scribe3 cron list(best-effort,CLI 不在则跳过)
#   5. --live:一发短 Responses,验证端到端出字
#
# 密钥安全:API_SERVER_KEY 从各 profile .env 读取,只用于请求头,绝不回显。
# 升级演练全流程(HERMES_HOME 隔离/回滚锚)见 scribe3/HERMES_UPGRADE_EVAL.md。
set -u

DEFAULT_API="${HERMES_DEFAULT:-http://127.0.0.1:8642}"
READ_API="${HERMES_READ:-http://127.0.0.1:8643}"
WRITE_API="${HERMES_WRITE:-http://127.0.0.1:8644}"
LIVE=0
[ "${1:-}" = "--live" ] && LIVE=1

PASS=0
FAIL=0

ok()   { PASS=$((PASS+1)); echo "  ✅ $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  ❌ $1"; }
note() { echo "  ·  $1"; }

key_for() {
  # $1 = profile 目录名(空串 = default)
  local env_file="$HOME/.hermes/.env"
  [ -n "$1" ] && env_file="$HOME/.hermes/profiles/$1/.env"
  grep '^API_SERVER_KEY=' "$env_file" 2>/dev/null | head -1 | cut -d= -f2-
}

jget() {
  # $1=url $2=key $3=python 表达式(变量 d 为解析后的 JSON)
  curl -sS --max-time 10 -H "Authorization: Bearer $2" "$1" 2>/dev/null \
    | python3 -c "import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('__PARSE_ERROR__'); raise SystemExit
print($3)" 2>/dev/null
}

check_gateway() {
  # $1=名字 $2=base url $3=profile 目录名 $4=必须具备的 capabilities(逗号分隔)
  local name="$1" base="$2" profile="$3" need_caps="$4"
  local key; key="$(key_for "$profile")"
  echo "== $name ($base)"
  if [ -z "$key" ]; then
    bad "读不到 API_SERVER_KEY(profile='$profile' .env)"
    return
  fi

  local ver
  ver="$(jget "$base/health" "$key" "d.get('version','?')")"
  if [ -n "$ver" ] && [ "$ver" != "__PARSE_ERROR__" ]; then
    ok "/health 可达,version=$ver"
  else
    bad "/health 不可达或非 JSON"
    return
  fi

  local st
  # U-001 判据(与 hermes_runtime._health_ok 同源):看"网关能不能干活",不看 status 字面。
  # 周边检查(disk/负载)degraded 但 gateway running + api_server connected → 可用(绿,附原因);
  # 其余(gateway 停了/连不上)才是真红。
  st="$(jget "$base/health/detailed" "$key" "d.get('status','?')")"
  if [ "$st" = "ok" ]; then ok "/health/detailed status=ok"
  else
    usable="$(jget "$base/health/detailed" "$key" "'yes' if (d.get('status')=='degraded' and ((d.get('gateway_state')=='running') or (((((d.get('readiness') or {}).get('checks')) or {}).get('gateway') or {}).get('status')=='ok')) and ((((d.get('platforms') or {}).get('api_server')) or d.get('api_server') or {}).get('state')=='connected')) else 'no'")"
    reasons="$(jget "$base/health/detailed" "$key" "','.join(sorted(k for k,v in ((((d.get('readiness') or {}).get('checks')) or {}).items()) if isinstance(v,dict) and v.get('status') not in (None,'ok')))")"
    if [ "$usable" = "yes" ]; then ok "/health/detailed degraded 但网关可用(原因:${reasons:-未知},U-001 判据)"
    else bad "/health/detailed status=$st(原因:${reasons:-未知})"; fi
  fi

  local caps
  caps="$(jget "$base/v1/capabilities" "$key" "','.join(sorted(k for k,v in d.get('features',d).items() if v is True))")"
  if [ "$caps" = "__PARSE_ERROR__" ] || [ -z "$caps" ]; then
    bad "/v1/capabilities 不可达"
  else
    local missing=""
    IFS=',' read -ra NEED <<< "$need_caps"
    for c in "${NEED[@]}"; do
      [[ ",$caps," == *",$c,"* ]] || missing="$missing $c"
    done
    if [ -z "$missing" ]; then
      ok "capabilities 含:$need_caps"
    else
      bad "capabilities 缺:$missing"
    fi
  fi
}

echo "Hermes smoke $(date '+%F %T')(live=$LIVE)"
check_gateway "default"       "$DEFAULT_API" ""              "chat_completions"
check_gateway "scribe3 读"    "$READ_API"    "scribe3"       "responses_api"
check_gateway "scribe3 写"    "$WRITE_API"   "scribe3_write" "run_submission,run_approval_response"

echo "== scribe3 skills"
RKEY="$(key_for scribe3)"
SKILLS="$(jget "$READ_API/v1/skills" "$RKEY" "','.join(s.get('name','') for s in (d.get('data') or d.get('skills') or []))")"
if [[ ",$SKILLS," == *",scribe-novel-v2,"* ]]; then
  ok "scribe-novel-v2 已加载"
else
  bad "scribe-novel-v2 未在 /v1/skills(实际:${SKILLS:0:120})"
fi

echo "== cron(best-effort)"
if command -v hermes >/dev/null 2>&1; then
  if hermes -p scribe3 cron list 2>/dev/null | grep -q "scribe3"; then
    ok "hermes -p scribe3 cron list 有 scribe3 任务"
  else
    note "cron list 无 scribe3 任务或命令失败(不计失败)"
  fi
else
  note "hermes CLI 不在 PATH,跳过 cron 检查"
fi

if [ "$LIVE" = "1" ]; then
  echo "== live Responses(:8643,烧 1 笔)"
  TXT="$(curl -sS --max-time 120 "$READ_API/v1/responses" \
    -H "Authorization: Bearer $RKEY" -H "Content-Type: application/json" \
    -d '{"input":"只回两个字:体检","stream":false}' 2>/dev/null \
    | python3 -c "import json,sys
d=json.load(sys.stdin)
print(''.join(c.get('text','') for it in d.get('output',[]) if it.get('type')=='message' for c in it.get('content',[]))[:40])" 2>/dev/null)"
  if [ -n "$TXT" ]; then
    ok "Responses 出字:$TXT"
  else
    bad "Responses 无输出"
  fi
fi

# ---- P4(hermes 能力审查):模型兜底链配置存在性(三 profile;主模型单点=红)----
echo "— fallback 兜底链 —"
for cfg in "$HOME/.hermes/config.yaml" "$HOME/.hermes/profiles/scribe3/config.yaml" "$HOME/.hermes/profiles/scribe3_write/config.yaml"; do
  # 不依赖 python yaml(系统 python3 可能没装)——数顶层 fallback_providers 的 "- provider" 项;
  # n 必须是数字,取不出=红(防解析失败假绿,零降级)
  n=$(awk '/^fallback_providers:/{f=1;next} f&&/^[A-Za-z_]/{f=0} f&&/^[[:space:]]*- provider:/{c++} END{print c+0}' "$cfg" 2>/dev/null)
  label=$(basename "$(dirname "$cfg")")
  case "$n" in (''|*[!0-9]*) bad "$label: fallback 配置读取失败";; 
    (0) bad "$label: fallback 未配置(主模型单点)";; 
    (*) ok "$label: fallback 链 $n 级";; esac
done


echo
echo "结果:PASS=$PASS FAIL=$FAIL"
[ "$FAIL" = "0" ]
