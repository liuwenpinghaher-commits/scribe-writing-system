#!/usr/bin/env bash
# =============================================================================
# PR-10 · 小说质量模式 · Demo 冒烟 Runbook 脚本
#
# 做什么：
#   - 打印质量模式 env / 回滚 env
#   - 轻量公网 health/ready（可选）
#   - 初始化证据目录骨架
#   - 打印 铜炉新卷 2 章 冒烟勾选清单
#   - serialize 默认 dry-run（避免误跑重 LLM 连载）
#
# 不做什么：
#   - 默认不改 demo .env、不重启容器、不跑全量 serialize
#   - 不在 Grok 运行机拉起 Surreal / npm ci / 全量 pytest
#
# 用法：
#   ./scripts/nq_quality_smoke_runbook.sh help
#   ./scripts/nq_quality_smoke_runbook.sh health
#   ./scripts/nq_quality_smoke_runbook.sh print-env
#   ./scripts/nq_quality_smoke_runbook.sh print-rollback
#   ./scripts/nq_quality_smoke_runbook.sh checklist
#   ./scripts/nq_quality_smoke_runbook.sh init-evidence
#   ./scripts/nq_quality_smoke_runbook.sh migration-note
#   FORCE_SERIALIZE=1 ./scripts/nq_quality_smoke_runbook.sh serialize
#
# 环境变量：
#   BASE_URL          默认 https://tonglu.example.com
#   EVID_DIR          默认 <repo>/docs/evidence/nq-quality-smoke-20260810
#   FORCE_SERIALIZE   设为 1 才允许真正触发「后续连载提示」外的重路径
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${BASE_URL:-https://tonglu.example.com}"
EVID_DIR="${EVID_DIR:-$ROOT/docs/evidence/nq-quality-smoke-20260810}"
FRAG_Q="$ROOT/deploy/prod/env.quality-mode.fragment"
FRAG_R="$ROOT/deploy/prod/env.quality-mode-rollback.fragment"
RUNBOOK="$ROOT/docs/ops/nq-quality-mode-demo-runbook.md"
CMD="${1:-help}"

log() { printf '%s\n' "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

cmd_help() {
  sed -n '2,30p' "$0" | sed 's/^# \?//'
  log ""
  log "子命令: help | health | print-env | print-rollback | checklist | init-evidence | migration-note | serialize"
  log "手册: $RUNBOOK"
}

cmd_print_env() {
  log "==> 质量模式 env（PR-10 核心 + 设计完整）"
  if [[ -f "$FRAG_Q" ]]; then
    grep -E '^[A-Z0-9_]+=' "$FRAG_Q" || true
  else
    cat <<'EOF'
SCRIBE3_DRAMA_GATE=1
SCRIBE3_BEATS_SYNOPSIS_FALLBACK=0
SCRIBE3_CRAFT_NOVEL=1
SCRIBE3_PILOT_SOFT_PRESSURE=0
SCRIBE3_PILOT_SOFT_AI_GRADE=1
SCRIBE3_PARK_STROLL_BLOCKING=1
SCRIBE3_DRAMA_HARD_PRESSURE=4
SCRIBE3_BEATS_V2=1
SCRIBE3_DRAMA_GATE_COMPAT=0
SCRIBE3_PDC=1
SCRIBE3_PDC_BLOCKING=1
EOF
  fi
  log ""
  log "# export 形式（本地 shell 试验；demo 请写入 deploy/prod/.env 后重启 backend）"
  if [[ -f "$FRAG_Q" ]]; then
    grep -E '^[A-Z0-9_]+=' "$FRAG_Q" | sed 's/^/export /'
  fi
}

cmd_print_rollback() {
  log "==> 回滚到可达 soft"
  if [[ -f "$FRAG_R" ]]; then
    grep -E '^[A-Z0-9_]+=' "$FRAG_R" || true
  else
    cat <<'EOF'
SCRIBE3_PILOT_SOFT_PRESSURE=1
SCRIBE3_PILOT_SOFT_AI_GRADE=1
SCRIBE3_BEATS_SYNOPSIS_FALLBACK=1
SCRIBE3_DRAMA_GATE=0
SCRIBE3_DRAMA_GATE_COMPAT=1
SCRIBE3_CRAFT_NOVEL=0
SCRIBE3_PARK_STROLL_BLOCKING=0
SCRIBE3_PDC_BLOCKING=0
EOF
  fi
}

cmd_health() {
  local code body
  log "==> health  $BASE_URL/api/health"
  body="$(curl -sS --connect-timeout 10 --max-time 20 \
    -w '\n%{http_code}' "${BASE_URL%/}/api/health" || true)"
  code="$(printf '%s\n' "$body" | tail -n1)"
  body="$(printf '%s\n' "$body" | sed '$d')"
  log "  HTTP $code  $body"
  [[ "$code" == "200" ]] || die "health 非 200"

  log "==> ready   $BASE_URL/api/ready"
  body="$(curl -sS --connect-timeout 10 --max-time 20 \
    -w '\n%{http_code}' "${BASE_URL%/}/api/ready" || true)"
  code="$(printf '%s\n' "$body" | tail -n1)"
  body="$(printf '%s\n' "$body" | sed '$d')"
  log "  HTTP $code  $body"
  [[ "$code" == "200" ]] || die "ready 非 200"

  if [[ -d "$EVID_DIR" ]]; then
    {
      echo "stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo "base=$BASE_URL"
      echo "health=$body"
    } >"$EVID_DIR/06-health.txt" 2>/dev/null || true
    # rewrite with both endpoints
    {
      echo "stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo "base=$BASE_URL"
      echo -n "health: "
      curl -sS --connect-timeout 10 --max-time 20 "${BASE_URL%/}/api/health" || echo FAIL
      echo
      echo -n "ready: "
      curl -sS --connect-timeout 10 --max-time 20 "${BASE_URL%/}/api/ready" || echo FAIL
      echo
    } >"$EVID_DIR/06-health.txt"
    log "  wrote $EVID_DIR/06-health.txt"
  fi
  log "HEALTH_OK"
}

cmd_migration_note() {
  cat <<EOF
==> Migration 117_beats_meta（须在 demo 已部署栈应用）

文件: scribe3/migrations/117_beats_meta.surql
  DEFINE FIELD IF NOT EXISTS beats_meta ON chapter TYPE option<string>;

推荐:
  1) ./scripts/deploy_demo.sh hot   # 热更含 117 的代码
  2) 打开/新建作品 → backend _apply_schema_once 幂等应用
  3) 确认:
       SELECT meta::id(id) AS id FROM _migration
         WHERE meta::id(id) = '117_beats_meta';
       INFO FOR TABLE chapter;   # 应含 beats_meta

手动补打与证据字段见:
  $RUNBOOK
  $EVID_DIR/00-migration-117.md
EOF
}

cmd_checklist() {
  cat <<'EOF'
==> 铜炉新卷 2 章 · 质量模式冒烟勾选（PR-10）

对照书: book_013bcb3b（docs/evidence/v633-reval-20260810/）
样本:   铜炉同宇宙新卷（非无关新书）· 仅 2 章

前置
  [ ] PR-0…8 代码已热更 demo
  [ ] deploy/prod/.env 合并 env.quality-mode.fragment 并重启 backend
  [ ] migration 117_beats_meta 已应用（_migration + INFO FOR TABLE）
  [ ] curl /api/health 与 /api/ready = 200
  [ ] （可选）./scripts/smoke_s32.sh exit 0

质量旗生效（进程内）
  [ ] SCRIBE3_DRAMA_GATE=1
  [ ] SCRIBE3_BEATS_SYNOPSIS_FALLBACK=0
  [ ] SCRIBE3_CRAFT_NOVEL=1
  [ ] SCRIBE3_PILOT_SOFT_PRESSURE=0
  [ ] SCRIBE3_PILOT_SOFT_AI_GRADE=1
  [ ] SCRIBE3_PARK_STROLL_BLOCKING=1
  [ ] SCRIBE3_DRAMA_HARD_PRESSURE=4
  [ ] （推荐）BEATS_V2=1 · DRAMA_GATE_COMPAT=0 · PDC=1 · PDC_BLOCKING=1

连载 ch1–ch2（重；demo 机执行 · 勿 Grok 机默跑）
  [ ] 新书 slug 记入 03-book.md
  [ ] ch1 finalized 或可人读 prose → 04-serialize/ch01.md
  [ ] ch2 同上 → 04-serialize/ch02.md
  [ ] 每章 beats_meta.beats_source ≠ synopsis_segments
  [ ] 高压章 drama_validation 可审计
  [ ] E1 限知无帧外直说
  [ ] pressure soft 不再掩盖 blocking 终态

人读 / 人盲
  [ ] 戏剧推进中位 ≥4（对照基线）
  [ ] 比喻过多中位 ≤2
  [ ] 结果写入 05-human-read.md（真人；禁止 LLM 代填封顶）

收尾
  [ ] 99-status.md 写 PASS/FAIL + 缺口
  [ ] 若失败：合并 env.quality-mode-rollback.fragment 恢复可达
EOF
}

cmd_init_evidence() {
  mkdir -p "$EVID_DIR/04-serialize"
  # 骨架文件：已有则不覆盖正文
  [[ -f "$EVID_DIR/00-plan-link.md" ]] || cat >"$EVID_DIR/00-plan-link.md" <<'MD'
# 方案链接

- 设计：`docs/plans/2026-08-10-novel-quality-first-pipeline-optimization.md`（PR-10 · Rollout）
- 运维手册：`docs/ops/nq-quality-mode-demo-runbook.md`
- 对照证据：`docs/evidence/v633-reval-20260810/` · 书 `book_013bcb3b`
- 旗：`scribe3/novel_quality_flags.py` · `QUALITY_MODE_TARGETS`
MD
  [[ -f "$EVID_DIR/00-migration-117.md" ]] || cat >"$EVID_DIR/00-migration-117.md" <<'MD'
# Migration 117 · beats_meta

## 状态

- [ ] 未在 demo 确认
- [ ] 已确认 `_migration:117_beats_meta`
- [ ] 已确认 `INFO FOR TABLE chapter` 含 `beats_meta`

## 操作摘要（操作后填写）

| 项 | 值 |
|----|-----|
| 时间 | |
| 作品 slug | |
| 应用方式 | 自动 schema / 手动 DEFINE |
| 备注 | |

## 摘录（脱敏）

```text
# 粘贴 INFO FOR TABLE / _migration 行
```
MD
  [[ -f "$EVID_DIR/01-quality-env.md" ]] || cat >"$EVID_DIR/01-quality-env.md" <<'MD'
# 质量模式 env 快照

## 目标值（PR-10）

| Flag | 目标 |
|------|------|
| SCRIBE3_DRAMA_GATE | 1 |
| SCRIBE3_BEATS_SYNOPSIS_FALLBACK | 0 |
| SCRIBE3_CRAFT_NOVEL | 1 |
| SCRIBE3_PILOT_SOFT_PRESSURE | 0 |
| SCRIBE3_PILOT_SOFT_AI_GRADE | 1 |
| SCRIBE3_PARK_STROLL_BLOCKING | 1 |
| SCRIBE3_DRAMA_HARD_PRESSURE | 4 |
| SCRIBE3_BEATS_V2 | 1 |
| SCRIBE3_DRAMA_GATE_COMPAT | 0 |
| SCRIBE3_PDC | 1 |
| SCRIBE3_PDC_BLOCKING | 1 |

## Demo 生效确认

- [ ] 已写入 `/opt/scribe3/app/deploy/prod/.env`（备份 `.env.bak.*`）
- [ ] 已 `docker restart` / compose up backend
- [ ] 进程内快照（可选：容器 `novel_quality_flags_snapshot()` 或日志）

片段文件：`deploy/prod/env.quality-mode.fragment`
MD
  [[ -f "$EVID_DIR/02-smoke-checklist.md" ]] || {
    {
      echo "# 冒烟勾选（与脚本 checklist 同步）"
      echo ""
      echo "生成：\`./scripts/nq_quality_smoke_runbook.sh checklist\`"
      echo ""
      echo '```'
      "$0" checklist 2>/dev/null | sed '1d' || true
      echo '```'
    } >"$EVID_DIR/02-smoke-checklist.md"
  }
  [[ -f "$EVID_DIR/03-book.md" ]] || cat >"$EVID_DIR/03-book.md" <<'MD'
# 铜炉新卷（质量模式）

| 项 | 值 |
|----|-----|
| slug | （连载后填写） |
| title | 炉灰记·质量模式·PR10·… |
| base | https://tonglu.example.com |
| 对照 | book_013bcb3b |
| 章范围 | ch1–ch2 |
| 备注 | 同宇宙新卷 · 非无关作者新书 |
MD
  [[ -f "$EVID_DIR/05-human-read.md" ]] || cat >"$EVID_DIR/05-human-read.md" <<'MD'
# 人读 / 人盲（N4 · S3）

> 须真人填写。禁止 LLM 代评后宣称人盲通过。

| 章 | 戏剧推进(1–5) | 比喻过多(1–5↓) | 散步感 Y/N | 评者 | 备注 |
|----|---------------|----------------|------------|------|------|
| ch1 | | | | | |
| ch2 | | | | | |

## 结论

- 戏剧推进中位：
- 比喻过多中位：
- 对照 book_013bcb3b 主观差：
MD
  [[ -f "$EVID_DIR/99-status.md" ]] || cat >"$EVID_DIR/99-status.md" <<'MD'
# PR-10 证据总状态

| 项 | 状态 |
|----|------|
| 文档/env/runbook | **交付**（本 PR） |
| demo health 抽样 | 见 `06-health.txt`（若跑过 health） |
| migration 117 | **待操作员在 demo 确认** |
| 质量 env 上线 | **待操作员合并 fragment 并重启** |
| 2 章连载 | **未跑**（避免默认重路径；`FORCE_SERIALIZE=1` 后按手册） |
| 人读/人盲 | **待真人** |

## 下一步

1. `./scripts/deploy_demo.sh hot`（含 PR-0…8 + 117）  
2. 合并 `deploy/prod/env.quality-mode.fragment` → 重启 backend  
3. 确认 migration 117  
4. 铜炉新卷 2 章 pilot + 人读  
5. 更新本文件为 PASS/FAIL  
MD
  # serialize placeholders
  [[ -f "$EVID_DIR/04-serialize/ch01.md" ]] || echo "<!-- pending ch1 prose export -->" >"$EVID_DIR/04-serialize/ch01.md"
  [[ -f "$EVID_DIR/04-serialize/ch02.md" ]] || echo "<!-- pending ch2 prose export -->" >"$EVID_DIR/04-serialize/ch02.md"
  log "EVIDENCE_OK  $EVID_DIR"
  find "$EVID_DIR" -type f | sort | sed 's/^/  /'
}

cmd_serialize() {
  if [[ "${FORCE_SERIALIZE:-0}" != "1" ]]; then
    cat <<EOF
==> serialize · DRY-RUN（默认）

本子命令 **不会** 触发 LLM 全量连载。
完整 2 章请在 demo 可达环境按手册执行，并设：

  FORCE_SERIALIZE=1 $0 serialize

建议路径（任选其一，仍须人工盯）：
  - 见 docs/ops/nq-quality-mode-demo-runbook.md §3.3
  - 脚手架：python3 scripts/v633_change_revalidation.py --phase scaffold
  - 然后 pilot API 仅 from-seq=1 to-seq=2（勿一次 5 章）

证据目录: $EVID_DIR
手册:     $RUNBOOK
EOF
    return 0
  fi
  log "==> FORCE_SERIALIZE=1 · 仍不内置重 LLM 循环（防误炸）"
  log "请按手册在已配置凭证的环境执行 2 章 pilot，并把 prose/meta 写入："
  log "  $EVID_DIR/03-book.md"
  log "  $EVID_DIR/04-serialize/ch01.md"
  log "  $EVID_DIR/04-serialize/ch02.md"
  log "本脚本刻意不嵌入长连载，以免 PR-10 文档提交被重任务绑架。"
  log "SERIALIZE_HANDOFF"
}

case "$CMD" in
  help|-h|--help) cmd_help ;;
  health) cmd_health ;;
  print-env) cmd_print_env ;;
  print-rollback) cmd_print_rollback ;;
  checklist) cmd_checklist ;;
  init-evidence) cmd_init_evidence ;;
  migration-note) cmd_migration_note ;;
  serialize) cmd_serialize ;;
  *) die "未知子命令: $CMD（试 help）" ;;
esac
