#!/usr/bin/env bash
# =============================================================================
# SurrealDB 3.2.4 demo 备份：按 namespace/database export 为 .surql
#
# 在 **demo 机** 上执行（需 docker + prod-surreal-1）。
# 不修改数据；导出到 BACKUP_DIR（默认 /opt/scribe3/backups/surreal/YYYYMMDD-HHMMSS）。
#
# 用法：
#   ./scripts/backup_surreal_demo.sh
#   NS=scribe3 DBS="main,_reg,demo_s32b" ./scripts/backup_surreal_demo.sh
#
# 恢复（旁路新卷，勿直接覆盖生产未备份目录）:
#   docker exec -i prod-surreal-1 /surreal import \
#     --endpoint http://127.0.0.1:8000 -u "$SURREAL_USER" -p "$SURREAL_PASS" \
#     --namespace scribe3 --database main /tmp/main.surql
# =============================================================================
set -euo pipefail

CONTAINER="${SURREAL_CONTAINER:-prod-surreal-1}"
NS="${NS:-scribe3}"
# 默认导出注册库 + 常见作品；可用 DBS 覆盖（空格/逗号分隔）
DBS_RAW="${DBS:-_reg main}"
DBS_RAW="${DBS_RAW//,/ }"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-/opt/scribe3/backups/surreal/${STAMP}}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "容器未运行: $CONTAINER" >&2
  exit 1
fi

# 无权限写 /opt 时回退到用户目录
if ! mkdir -p "$BACKUP_DIR" 2>/dev/null; then
  BACKUP_DIR="${HOME}/scribe3-backups/surreal/${STAMP}"
  mkdir -p "$BACKUP_DIR"
  echo "NOTE: 使用可写目录 BACKUP_DIR=$BACKUP_DIR"
fi

# 凭证：优先环境，否则 compose .env
USER_NAME="${SURREAL_USER:-}"
PASS_WORD="${SURREAL_PASS:-}"
if [[ -z "$USER_NAME" || -z "$PASS_WORD" ]]; then
  ENV_FILE="${SURREAL_ENV_FILE:-/opt/scribe3/app/deploy/prod/.env}"
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a
    # 只取需要的键，避免 source 整个文件副作用
    USER_NAME="$(grep -E '^SURREAL_USER=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
    PASS_WORD="$(grep -E '^SURREAL_PASS=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
    set +a
  fi
fi
USER_NAME="${USER_NAME:-root}"
if [[ -z "$PASS_WORD" ]]; then
  echo "缺少 SURREAL_PASS（env 或 $ENV_FILE）" >&2
  exit 2
fi

META="$BACKUP_DIR/META.txt"
{
  echo "stamp=$STAMP"
  echo "container=$CONTAINER"
  docker exec "$CONTAINER" /surreal version 2>/dev/null | head -1 || true
  docker inspect "$CONTAINER" --format 'image={{.Config.Image}}' 2>/dev/null || true
  echo "ns=$NS"
  echo "dbs=$DBS_RAW"
} | tee "$META"

for db in $DBS_RAW; do
  [[ -n "$db" ]] || continue
  out="$BACKUP_DIR/${NS}__${db}.surql"
  echo "==> export ns=$NS db=$db -> $out"
  # 导出到容器内再 docker cp，避免权限问题
  remote="/tmp/export_${NS}_${db}_$$.surql"
  # 写入容器内固定路径再 docker cp（勿用 stdout：会混入 tracing INFO 导致 import 失败）
  remote="/data/export_${NS}_${db}.surql"
  if docker exec "$CONTAINER" /surreal export \
    --endpoint http://127.0.0.1:8000 \
    -u "$USER_NAME" -p "$PASS_WORD" \
    --namespace "$NS" --database "$db" \
    "$remote" 2>"$BACKUP_DIR/${db}.export.log"; then
    docker cp "$CONTAINER:$remote" "$out"
    # 去掉文件头可能误入的非 SurQL 行（防御）
    if head -1 "$out" 2>/dev/null | grep -qE '^[0-9]{4}-|INFO |ERROR '; then
      grep -vE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T| INFO | ERROR ' "$out" >"${out}.clean" || true
      mv "${out}.clean" "$out"
    fi
    if [[ ! -s "$out" ]]; then
      echo "WARN export empty db=$db" | tee -a "$META"
    else
      ls -lh "$out" | tee -a "$META"
    fi
  else
    echo "WARN export failed db=$db (see ${db}.export.log)" | tee -a "$META"
    rm -f "$out"
  fi
done

# 可选：打包数据目录快照提示（不自动停库拷贝，避免误操作）
echo "NOTE: 逻辑备份为 .surql；物理卷 ${SCRIBE3_DATA_DIR:-/opt/scribe3/data}/surreal 需停库+文件系统快照另做。" | tee -a "$META"
echo "BACKUP_DIR=$BACKUP_DIR"
echo "DONE"
