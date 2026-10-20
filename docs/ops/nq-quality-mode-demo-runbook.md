# 小说质量第一 · Demo 质量模式运维与冒烟手册（PR-10）

| 项 | 值 |
|----|-----|
| **日期** | 2026-08-10 |
| **PR** | PR-10 · demo 质量 env + 铜炉新卷 2 章人读/人盲小样 |
| **设计真源** | [`docs/plans/2026-08-10-novel-quality-first-pipeline-optimization.md`](../plans/2026-08-10-novel-quality-first-pipeline-optimization.md) §Rollout / PR Plan |
| **验收环境** | 已部署 demo `https://www.example.com`（`203.0.113.10` · `/opt/scribe3/app`） |
| **对照书** | `book_013bcb3b`（炉灰记·v6.3.3 · ch1–5 · soft-pass 基线） |
| **证据根** | [`docs/evidence/nq-quality-smoke-20260810/`](../evidence/nq-quality-smoke-20260810/) |
| **脚本** | `scripts/nq_quality_smoke_runbook.sh` |

> **强制**：验证 = 打已部署栈；**禁止**为验收再起平行 Surreal / 第二 compose。  
> **本 PR 交付**：env 片段 + 手册 + 可延后执行的 runbook；**不**在 Grok 运行机全量连载。

---

## 0. 目标与边界

### 目标

1. 在 demo **显式**打开「质量模式」env（代码默认仍为可达 soft）。  
2. 应用 migration **`117_beats_meta`**，保证 `chapter.beats_meta` 可写。  
3. **铜炉新卷（同宇宙）** 连载 **2 章**，人读 / 人盲对照 `book_013bcb3b`。  
4. 验收 N1–N3 + E1 +（有人时）N4/S3；证据落盘。

### 非目标（本 runbook 默认不做）

- 全量 5 章+ serialize、长旅程、Grok 机 `npm ci` / 本机 Surreal。  
- 改代码默认旗（质量模式 **仅** demo env 翻转）。  
- 把人盲问卷结果 LLM 代填后宣称 ≥9.5。

---

## 1. 质量模式 env

### 1.1 片段文件

| 文件 | 用途 |
|------|------|
| [`deploy/prod/env.quality-mode.fragment`](../../deploy/prod/env.quality-mode.fragment) | 质量模式合并进 `deploy/prod/.env` |
| [`deploy/prod/env.quality-mode-rollback.fragment`](../../deploy/prod/env.quality-mode-rollback.fragment) | 回滚到可达 soft |

### 1.2 PR-10 核心清单（必须）

```bash
SCRIBE3_DRAMA_GATE=1
SCRIBE3_BEATS_SYNOPSIS_FALLBACK=0
SCRIBE3_CRAFT_NOVEL=1
SCRIBE3_PILOT_SOFT_PRESSURE=0
SCRIBE3_PILOT_SOFT_AI_GRADE=1
SCRIBE3_PARK_STROLL_BLOCKING=1
SCRIBE3_DRAMA_HARD_PRESSURE=4
```

### 1.3 完整质量模式（推荐一并）

```bash
SCRIBE3_BEATS_V2=1
SCRIBE3_DRAMA_GATE_COMPAT=0
SCRIBE3_PDC=1
SCRIBE3_PDC_BLOCKING=1
```

与 `scribe3.novel_quality_flags.QUALITY_MODE_TARGETS` / `QUALITY_MODE_EXTERNAL_ENV` 对齐。

### 1.4 在 demo 应用（操作员）

```bash
# SSH: ubuntu@203.0.113.10 ，密钥 ~/.ssh/id_tencent_lh
ssh -i ~/.ssh/id_tencent_lh ubuntu@203.0.113.10
cd /opt/scribe3/app

# 1) 备份
cp -a deploy/prod/.env "deploy/prod/.env.bak.$(date +%Y%m%d-%H%M%S)"

# 2) 合并质量片段（人工审阅后；避免重复 KEY 时以片段为准改旧行）
#    推荐：编辑器打开 .env，按 fragment 改值；或：
#    grep -v '^#' deploy/prod/env.quality-mode.fragment | grep -v '^$' >> deploy/prod/.env
#    随后去重（后写覆盖前写需自行保证）

# 3) 热更代码（含 117 migration + PR-0…8 行为）
# 在开发机：
#   ./scripts/deploy_demo.sh hot
# 若本机已是最新 tree 在服务器 git：
#   ./scripts/deploy_demo.sh server-git   # 按仓库约定

# 4) 重启 backend 读 env（compose env_file = deploy/prod/.env）
docker compose -f deploy/prod/docker-compose.yml --env-file deploy/prod/.env up -d backend
# 或：docker restart prod-backend-1

# 5) 存活
curl -fsS https://www.example.com/api/health
curl -fsS https://www.example.com/api/ready
```

### 1.5 回滚

合并 `env.quality-mode-rollback.fragment` → 重启 backend → `smoke_s32` 或至少 health + 一章 pilot soft 可达。

**口令**：恢复可达 = `SCRIBE3_PILOT_SOFT_PRESSURE=1` + fallback=1 + `DRAMA_GATE=0`。

---

## 2. Migration · `117_beats_meta.surql`（必做）

### 2.1 内容

```surql
-- scribe3/migrations/117_beats_meta.surql
DEFINE FIELD IF NOT EXISTS beats_meta ON chapter TYPE option<string>;
```

SCHEMAFULL：`beats_meta` 未 DEFINE 时写入会静默丢弃/报错（定案 A · KD-NQ-13）。

### 2.2 推荐路径（应用启动自动）

1. 部署含 `scribe3/migrations/117_beats_meta.surql` 的 backend。  
2. 打开任意作品时 `store.connection._apply_schema_once` 会按 `_migration` 表幂等应用。  
3. 对新书：建书/首连即触发；对旧书：首次打开 work 触发。

### 2.3 手动确认 / 补打（demo 机）

```bash
# 容器名以现网为准（常见 prod-surreal-1 / prod-backend-1）
SURREAL=prod-surreal-1
# 读 root 凭证：deploy/prod/.env 的 SURREAL_USER/PASS（勿回显到日志仓）

# 对目标作品 DB（例：新卷 slug 或 _reg 探测）
docker exec -i "$SURREAL" /surreal sql \
  --endpoint http://127.0.0.1:8000 \
  -u "$SURREAL_USER" -p "$SURREAL_PASS" \
  --ns scribe3 --db '<work_slug>' <<'SQL'
INFO FOR TABLE chapter;
SELECT meta::id(id) AS id, applied_at FROM _migration WHERE meta::id(id) = '117_beats_meta';
SQL

# 若无 117 记录且代码已挂载 migration，可触发一次打开作品，或：
docker exec -i "$SURREAL" /surreal sql \
  --endpoint http://127.0.0.1:8000 \
  -u "$SURREAL_USER" -p "$SURREAL_PASS" \
  --ns scribe3 --db '<work_slug>' <<'SQL'
DEFINE FIELD IF NOT EXISTS beats_meta ON chapter TYPE option<string>;
UPSERT type::record('_migration', '117_beats_meta') SET applied_at = time::now();
SQL
```

### 2.4 验收

| # | 检查 | 通过 |
|---|------|------|
| M1 | `_migration` 含 `117_beats_meta` | 有 applied_at |
| M2 | `INFO FOR TABLE chapter` 含 `beats_meta` | option\<string\> |
| M3 | expand_beats / 章 meta 可写 `beats_meta` JSON | 非空 schema/beats_source |

证据建议：`docs/evidence/nq-quality-smoke-20260810/00-migration-117.md` 粘贴 INFO 摘要（脱敏）。

---

## 3. 铜炉新卷 · 2 章冒烟清单

### 3.1 书与对照

| 项 | 值 |
|----|-----|
| 样本策略 | **铜炉同宇宙新卷**（非无关作者新书）· KD-NQ-17 |
| 对照 | `book_013bcb3b` ch1–5 · `docs/evidence/v633-reval-20260810/` |
| 章数 | **2**（PR-10 最小人读包；可后续加章） |
| 标题模板 | `炉灰记·质量模式·PR10·YYYYMMDD` |
| API | `API_BASE=https://www.example.com` |

### 3.2 前置

- [ ] 代码 PR-0…8 已热更到 demo  
- [ ] §1 质量 env 已写入并 **重启 backend**  
- [ ] §2 migration 117 已应用（新书打开后确认）  
- [ ] `curl` health/ready = ok  
- [ ] 可选：`./scripts/smoke_s32.sh` exit 0  

### 3.3 连载（重；在 demo 机或能打公网 API 的环境执行）

**不要在 Grok 运行机跑全量 LLM 连载。** 推荐：

```bash
# 开发机/demo 机（凭证勿提交）
export API_BASE=https://www.example.com
export SCRIBE3_BOOTSTRAP_USERS='user:pass'   # 或 BOOT_FILE
export EVID_DIR=docs/evidence/nq-quality-smoke-20260810

# 仅打印清单 / 轻量 health（本仓库脚本）：
./scripts/nq_quality_smoke_runbook.sh health
./scripts/nq_quality_smoke_runbook.sh print-env
./scripts/nq_quality_smoke_runbook.sh checklist

# 完整 2 章：见脚本 serialize 子命令（默认 dry-run；需 FORCE_SERIALIZE=1）
# 或复用 v633 / pilot 脚本脚手架后人工/pilot 两章：
#   python3 scripts/v633_change_revalidation.py --phase scaffold
#   # 再 pilot 仅 ch1–2（禁止默认可一次 5 章）
```

连载通过标准（每章）：

| # | 标准 | 证据 |
|---|------|------|
| C1 | pilot 至 finalized 或可人读 prose | `04-serialize/ch0N.md` |
| C2 | `beats_meta.beats_source` ≠ `synopsis_segments`（质量模式） | 章 meta JSON 摘录 |
| C3 | 高压章（pressure≥4）`drama_validation` 可审计 | beats_meta 摘录 |
| C4 | 限知：无帧外直说（E1） | 人读或 review 摘要 |
| C5 | soft-pass：pressure 相关不应再「软放行终态」掩盖 blocking | full_check / deliver 卡 |

### 3.4 人读 / 人盲（N4 · S3）

| 维 | 量表 | 通过参考 |
|----|------|----------|
| 戏剧推进 | 1–5 | 中位 ≥4（对照 ch1–5 基线） |
| 比喻过多 | 1–5（越低越好） | 中位 ≤2 |
| 公园散步感 | Y/N + 简述 | 高压章不应为终态散步 |

模板可参考 `docs/plans/human-blind-memory-quality-protocol.md`（量表维度可裁剪为戏剧/比喻）。  
结果写入 `docs/evidence/nq-quality-smoke-20260810/05-human-read.md`（人填；禁止 LLM 代评封顶）。

### 3.5 验收矩阵（设计 Acceptance 子集）

| ID | 内容 | 测法 |
|----|------|------|
| N1 | 高压章 scene beat 含 goal+conflict+turn | beats_meta / 人读 |
| N2 | 正文代价/不可逆或 turn 落地 | 人读 + pressure 指标 |
| N3 | 连续地点句无推力 ≥3 不得高压终态 | park_stroll / spatial |
| N5 | finalized ≠ synopsis_segments 源 | beats_source |
| E1 | 限知不破 | 人读 / review |
| E4 | 代码默认可达；质量模式仅 env | 回滚片段可恢复 |
| E5 | beats_source 可审计 | meta JSON |
| N4/S3 | 人盲（可选本窗口） | 问卷 |

---

## 4. 证据目录布局

```text
docs/evidence/nq-quality-smoke-20260810/
  00-plan-link.md
  00-migration-117.md          # 迁移确认（操作后填）
  01-quality-env.md            # 生效旗快照（脱敏）
  02-smoke-checklist.md        # 勾选状态
  03-book.md                   # 新卷 slug/title
  04-serialize/                # ch01.md ch02.md（连载后）
  05-human-read.md             # 人读/人盲
  06-health.txt                # 可选 curl 摘录
  99-status.md                 # 总状态
```

---

## 5. 脚本速查

```bash
./scripts/nq_quality_smoke_runbook.sh help
./scripts/nq_quality_smoke_runbook.sh health          # 仅公网 health/ready
./scripts/nq_quality_smoke_runbook.sh print-env       # 打印 export 块
./scripts/nq_quality_smoke_runbook.sh checklist       # 打印勾选清单
./scripts/nq_quality_smoke_runbook.sh init-evidence   # 确保证据目录骨架
./scripts/nq_quality_smoke_runbook.sh serialize       # 默认 dry-run；FORCE_SERIALIZE=1 才真跑
```

---

## 6. 相关

- 设计 Rollout：`docs/plans/2026-08-10-novel-quality-first-pipeline-optimization.md`  
- 旗读辅助：`scribe3/novel_quality_flags.py`  
- 发版冒烟：`docs/ops/release-smoke-checklist.md` · `scripts/smoke_s32.sh`  
- 对照证据：`docs/evidence/v633-reval-20260810/`  
- 部署：`./scripts/deploy_demo.sh`  
