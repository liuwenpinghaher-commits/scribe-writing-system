# 铜炉写作系统 5万字全程验收方案

| 项 | 值 |
|----|-----|
| **标题** | Linux CLI + Playwright · 5万字 / 15–20章 端到端验收 |
| **版本** | v1.0 · 2026-08-12 |
| **产品** | 铜炉 / tonglu · 代码 `scribe3/` |
| **仓库** | `scribe-writing-system`（开发：`/home/admin/projects/scribe-writing-system`；部署常见：`/opt/scribe3/app`） |
| **实现入口** | `scripts/run_50k_acceptance.sh` · `scribe3/web/e2e/acceptance_50k/` |
| **主验收协议对照** | v6.3.4 体验总 PASS 仍要求真人 SPA；**本方案 = 可重复自动化长程验收 / 工程回归**，可支撑 PARTIAL 与门闩证据，**不得单独宣称 v6.3.4 总 PASS**（缺 `author_human=true`） |
| **状态** | 可执行脚手架已入库 |

---

## 1. 概述

### 1.1 目标

通过**真实 Playwright 浏览器自动化**，在**已部署**前后端 + Hermes + Surreal 上：

1. 从零建书（或 `--resume` 续跑）；
2. 对话 + 点批写入北极星、角色、势力、规则、物品、术语、母题、伏笔；
3. GATE-A / WCG 全绿后进入连载；
4. 完成 **≥15 章、目标 18 章、全书 ≥50,000 字**；
5. 每章：脚手架（大纲→节拍→演绎）→ 写作槽提案卡 → 采用正文 → `verify_content_quality`；
6. 验证正典 / 限知 / 记忆 / 伏笔；
7. 终审 GATE-A/B/C/D 通过率 + 定稿门只读裁决 + 十维代理分；
8. 产物落入 `artifacts/e2e-50k-{date}-{work}/`。

### 1.2 范围

| 在范围内 | 不在范围内 |
|----------|------------|
| MUST M1–M12、SHOULD S1–S5、COULD C1–C2 | 真人盲测 ≥9.5 宣称 |
| 已部署 demo/验收栈（3311/3321） | Grok 运行机全量 `npm ci` / 本机临时 Surreal |
| UI → Hermes Run → MCP 审批写路径 | REST 灌正文 / 表单直填正典 |
| 内容质量轨（`verify_content_quality`） | 把 craft gate 绿当作质量 PASS |
| 断点续传 | 脚本 `POST /save-chapter` 静默落库 |

### 1.3 前提条件

- Docker Compose（或等价）已部署：**前端 :3311、后端 :3321、Surreal（demo 常映射 :8001）、Hermes :8642/:8643/:8644**
- Node.js + 仓库内 Playwright（`scribe3/web` 已装依赖的环境，通常是 **demo 机**）
- 真实 LLM（非 mock）；单章超时默认 480s
- 显式 `E2E_ALLOW_DEPLOYED=1`

### 1.4 铁律（与代码护栏一致）

1. **禁止 API 灌库正文/设定**（`E2E_ALLOW_API_SEED` 默认关；本方案主路径不用）。
2. **禁止表单直填正典**；设定/脚手架走 `chiefSay` → MCP → `run-approve`。
3. **闸绿 ≠ 质量通过**：每章必须 `qualityReview`。
4. **安全**：未设 `E2E_ALLOW_DEPLOYED=1` 拒绝运行；默认拒绝把 `E2E_WORK` 指到「纸命/印迹」等黑名单。
5. **真实 LLM**：`E2E_CHAPTER_MAX_MS=480000`，全程 ≤6h（`E2E_TOTAL_MAX_MS`）。

### 1.5 与现有脚本关系

| 现有 | 角色 |
|------|------|
| `e2e/lib.mjs` | `withPage` / `openBook` / `closeBrowserWithin` |
| `e2e/author_decisions.mjs` | `chiefSay` / `approveAllPending` / `acceptDraftProposal` / `adoptDraftAsFinal` |
| `e2e/craft_gates.mjs` | `fetchCraftGates` / `assertCraftGatesOrExit` |
| `e2e/craft_first_journey.mjs` | 1 章工艺优先参考（本方案 Phase1–4 扩写） |
| `e2e/hq_wordcount_push.mjs` | 5 万字补齐参考（本方案集成门闩+质量+断点） |
| `e2e/full_author_acceptance.mjs` | 短旅程矩阵总控（本方案是长程 monobook） |
| `scripts/v4_world_complete_gate.py` | WCG SSOT（可人工对照；自动化侧以 `/craft-gates` GATE-A 为主） |
| **`e2e/acceptance_50k/*`** | **本方案可执行实现** |

---

## 2. 环境准备

### 2.1 服务检查

```bash
# 容器（路径按机器调整）
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -40

# 端口探活
curl -sf http://127.0.0.1:3321/health | head -c 400; echo
curl -sf http://127.0.0.1:3321/ready | head -c 400; echo
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3311/
for p in 8642 8643 8644; do
  curl -sf -o /dev/null -w "hermes :$p %{http_code}\n" "http://127.0.0.1:$p/health" || echo "hermes :$p down"
done
```

期望：

- `/health` → 200
- 前端 `/` → 200
- 至少一个 Hermes 网关可达（否则 `chiefSay` 会在审批/Run 上超时）

### 2.2 Playwright 安装验证

```bash
cd /path/to/scribe-writing-system/scribe3/web
node -e "import('playwright').then(m=>console.log('playwright ok',!!m.chromium)).catch(e=>{console.error(e);process.exit(1)})"
# 若缺浏览器：
# npx playwright install chromium
```

> **资源警告**：勿在 Grok 运行机（约 1.6Gi 内存）执行 `npm ci` / 全量安装。在 **demo 部署机** 已有 `node_modules` 的树里跑。

### 2.3 环境变量清单

| 变量 | 默认 | 说明 |
|------|------|------|
| `E2E_BASE` | `http://127.0.0.1:3311` | 前端 |
| `E2E_API` | `http://127.0.0.1:3321` | 后端 API |
| `E2E_ALLOW_DEPLOYED` | shell 入口默认 `1` | 允许写已部署栈 |
| `E2E_BOOK_TITLE` | `50k全程验收·{stamp}` | 书名（建书/恢复） |
| `E2E_WORK` | （空） | 已有 slug 则跳过建书 |
| `E2E_WORD_TARGET` | `50000` | 全书字数 |
| `E2E_TARGET_CHAPTERS` | `18` | 目标章数（≥15） |
| `E2E_MIN_PROSE` | `2500` | 单章净文目标 |
| `E2E_MIN_CHAPTER_HARD` | `1200` | 单章硬底线 |
| `E2E_CHAPTER_MAX_MS` | `480000` | 单次 chiefSay 上限 |
| `E2E_TOTAL_MAX_MS` | `21600000` | 全程 6h |
| `E2E_QUALITY_REPAIR_ROUNDS` | `2` | 质量修订轮数 |
| `E2E_ART` | `artifacts/e2e-50k-…` | 产物目录 |
| `E2E_RESUME` / `--resume` | off | 断点续传 |
| `E2E_REFUSE_TITLES` | 默认含纸命/印迹 | 禁止作为 `E2E_WORK` |
| `E2E_PYTHON` | `scribe3/.venv/bin/python` | 质量桥 Python |
| `SCRIBE3_SURREAL_URL` | 可选 | 质量桥直连 Surreal；不可用则 HTTP 回退 |
| `E2E_HERMES_PORTS` | `8642,8643,8644` | 探活列表 |

### 2.4 仓库路径约定

```text
# 开发工作区
/home/admin/projects/scribe-writing-system

# demo 常见部署
/opt/scribe3/app   # 或 /opt/scribe3
# 以实际 `docker compose` 工作目录与 git checkout 为准
```

---

## 3. 验收脚本架构

### 3.1 文件结构

```text
scripts/
  run_50k_acceptance.sh                 # Bash 一键入口

scribe3/web/e2e/
  lib.mjs                               # 复用：withPage / openBook
  author_decisions.mjs                  # 复用：chiefSay / 批准 / 提案
  craft_gates.mjs                       # 复用：门闩查询
  acceptance_50k/
    run_50k_acceptance.mjs              # 主编排
    env_guard.mjs                       # 安全与健康检查
    checkpoint.mjs                      # 断点续传
    log.mjs                             # ISO 日志
    api_read.mjs                        # 只读 API
    quality_bridge.mjs                  # verify_content_quality + 十维映射
    ui_helpers.mjs                      # 选章/建章/Tab
    novel_bible.mjs                     # 18 章叙事圣经与提示词
    phases.mjs                          # Phase1–6 实现
```

### 3.2 模块依赖

```text
run_50k_acceptance.mjs
  ├─ env_guard.mjs
  ├─ checkpoint.mjs / log.mjs
  ├─ lib.mjs (withPage)
  └─ phases.mjs
        ├─ author_decisions.mjs
        ├─ api_read.mjs
        ├─ quality_bridge.mjs
        ├─ ui_helpers.mjs
        └─ novel_bible.mjs
```

### 3.3 入口命令

```bash
cd /path/to/scribe-writing-system

# 一键（推荐）
./scripts/run_50k_acceptance.sh

# 续跑
./scripts/run_50k_acceptance.sh --resume

# 显式环境
E2E_ALLOW_DEPLOYED=1 \
E2E_BASE=http://127.0.0.1:3311 \
E2E_API=http://127.0.0.1:3321 \
E2E_BOOK_TITLE='50k全程验收·灰契' \
E2E_WORD_TARGET=50000 \
E2E_TARGET_CHAPTERS=18 \
./scripts/run_50k_acceptance.sh
```

或直接 Node：

```bash
cd scribe3/web
E2E_ALLOW_DEPLOYED=1 E2E_RESUME=1 \
  node e2e/acceptance_50k/run_50k_acceptance.mjs
```

### 3.4 交互通道（实现真相）

| 通道 | UI | 网络 | 落库 |
|------|-----|------|------|
| **world_write** | 主编 `chiefComposer` → `chiefSay` | `POST /ai/runs` + 审批卡 | MCP `s3_*` 经批准 |
| **prose_write** | 写作槽 `writeComposer` `preferWrite:true` | `POST /chat/write` | 提案卡 → 填入 → **采用为正文** → `POST /save-chapter`（**仅由点击触发**） |
| **discuss** | 闲聊 | `/chat/stream`（agentic 写死 false） | 不直接写 L1 |

Run 终态：`completed | completed_unverified | remote_completed_pending_audit | failed | stopped`（见 `isTerminalHermesRunStatus`）。

### 3.5 关键选择器

```javascript
// 与 author_decisions.DECISION_SELECTORS + 建书 UI 一致
const SELECTORS = {
  bookNameInput: 'input[placeholder="书名…"], input[aria-label="书名"]',
  createButton: 'button:has-text("建")', // getByRole exact「建」
  fourCol: '[data-testid="four-col"]',
  chiefComposer: 'textarea[placeholder^="就当前内容问主编"]',
  writeComposer: 'textarea[placeholder^="提思路"]',
  runApprove: '[data-testid="run-approve"]',
  runApproveStale: '[data-testid="run-approve-stale"]',
  draftAccept: '[data-testid="draft-accept"]',
  draftUseCandidate: '[data-testid="draft-use-candidate"]',
  stageFill: '[data-testid="stage-fill"]',
  stageAppend: '[data-testid="stage-append"]',
  manuscriptDir: '[data-testid="manuscript-directory"]',
}
```

---

## 4. Phase 1: 建书与设定（估 20–40min）

### 4.1 步骤

1. `goto(E2E_BASE)` → 填书名 → 点「建」→ 等待 `POST /works` → `[data-testid="four-col"]`
2. 解析 `work` slug（精确标题 `resolveWorkSlugByExactTitle`）
3. `chiefSay` + 批准：
   - `s3_set_intent`（M2）
   - `s3_add_character` ×3 + `s3_add_character_relation`（M3）
   - `s3_add_world_rule` + `s3_add_faction`
   - item / term / `s3_add_motif`
   - `s3_plant_promise` ×3（M10 种植）
4. 只读回查：`/intent`、`/entities`、`/factions`、`/world-rules`、`/items`、`/terms`、`/motifs`、`/promises`

### 4.2 PASS

| ID | 条件 |
|----|------|
| M1 | work 非空 + four-col |
| M2 | intent 三字段非空 |
| M3 | 角色/势力/规则/母题/伏笔 list ≥1（item/term 尽力） |

### 4.3 实现位置

`phases.mjs` → `phase1Bootstrap`（完整可运行，无占位）。

叙事默认值见 `novel_bible.mjs`（灰契线，与 `craft_first_journey` 质量探针兼容）。

---

## 5. Phase 2: 世界完整度门闩（估 10–20min）

### 5.1 步骤

1. `GET /craft-gates?work=` → `gate_a`
2. 若 `blocking` 非空：按 A1–A7 修复 prompt 循环最多 3 轮（**仅 MCP 对话，不 REST 灌库**）
3. 落盘 `quality/craft_gates_phase2.json`

### 5.2 PASS

| ID | 条件 |
|----|------|
| M4 | `gate_a.ok && blocking=[]` |

### 5.3 对照 WCG SSOT

人工/并行可跑：

```bash
export API_BASE=http://127.0.0.1:3321   # 或 https://tonglu.example.com
export SCRIBE3_BOOTSTRAP_USERS=admin:****
python3 scripts/v4_world_complete_gate.py --slug book_xxx \
  --out artifacts/e2e-50k-.../quality/wcg.json
```

自动化主路径以 **`/craft-gates` GATE-A** 为硬门（与 `craft_gates.mjs` / `verify_craft_compliance.gate_a` 同源）。

---

## 6. Phase 3: 章脚手架循环（估 60–90min，与 Phase4 交织）

每章在写作前执行：

1. `s3_add_chapter`（或 UI「+ 章节」+ 批准）
2. 选章 → Tab 大纲 / 节拍 / 演绎
3. `s3_patch_chapter_plan`（`stagePrompt`）
4. 演绎后 `missingDeductionProjections` 回读；缺口再 MCP 修

### 6.1 PASS（M5）

- 已写章中多数具备 synopsis / beats / scene_truth（见 `chapters/chXX.json` 的 `plan`）
- 实现汇总：`must.M5.ok`（≥80% 有硬底正文的章计入）

---

## 7. Phase 4: 连载写作（估 4–5h）

### 7.1 章循环（实现：`writeChapterCycle`）

```text
for seq in startChapter..TARGET_CHAPTERS:
  openBook(work)                          # 防 UI 漂移
  ensure chapter exists (MCP/UI)
  selectChapter(seq)
  stages: 大纲→节拍→演绎 (chiefSay MCP)
  ensureWriteComposer
  chiefSay(prosePrompt, preferWrite=true, maxMs=480000)
  acceptDraftProposal
  if stage: adoptDraftAsFinal + wait POST /save-chapter (UI 触发)
  qualityReview → 最多 2 轮 repairPrompt
  fetchCraftGates(work, seq)
  save chapters/chXX.json + .txt
  saveCheckpoint
```

### 7.2 断点续传

```javascript
// checkpoint.mjs
const STATE_FILE = `${ART_DIR}/checkpoint.json`
// 字段：phase, work, book, lastCompletedChapter, run_ids, must, chapter_results, started_at
// --resume / E2E_RESUME=1 → loadCheckpoint，从 lastCompletedChapter+1 继续
```

### 7.3 质量监控

```javascript
// quality_bridge.mjs — 优先 SurrealStore + review_chapter_quality
// 失败则 HTTP GET /chapter + 规则回退（仍区分 quality_pass）
// mapTenDimensions → quality/models 十维 key 代理分
```

### 7.4 错误恢复

| 故障 | 策略 |
|------|------|
| 浏览器崩溃 | `withPage` 关闭；`--resume` 新 session |
| Hermes 超时 | `maxMs`；章记 errors，checkpoint 前进（可配置停） |
| 审批卡死 | `approveAllPending` 12×500ms；另点 stale |
| UI 漂移 | 每章 `openBook` |
| 提案未落库 | `s3_save_chapter` **经 chiefSay 审批**（非 REST） |

### 7.5 PASS（M6）

- `works.word_count ≥ 50000`
- `chapter_count ≥ 15`
- 单章硬底 ≥1200 净文；目标均长 ≥2500

---

## 8. Phase 5: 高级功能验证（估 30–45min）

| ID | 做法 | PASS |
|----|------|------|
| **M7 正典** | 对话触发 canon 抽取；`GET /canon/candidates` | 端点可回读；候选数记证 |
| **M8 限知** | 抽样 `GET /frame?focalizer=` | 无显式泄漏标记 |
| **M9 记忆** | `GET /recall` + 对话 semantic/hybrid | ≥1 命中或回复含前文引用 |
| **M10 伏笔** | plant（P1）+ track/resolve 对话 | 列表非空；尽量 hasClosed |
| **S2 Director** | 对话要建议 | 回复长度 >20 |
| **S3 返工** | 改已写章 | prose 回读前后可对比 |
| **C1 Storyline** | DOM 探测 | 有相关节点则记 |
| **C2 多 POV** | 圣经 沈砚/老道/陆晚 | ≥3 焦点 |

---

## 9. Phase 6: 质量终审

### 9.1 数值标准

| 项 | 阈值 |
|----|------|
| 全书字数 | ≥ 50,000 |
| 章数 | ≥ 15 |
| 单章平均（目标） | ≥ 2,500 |
| 最短章 | ≥ 1,200 |
| 十维单维 | ≥ 3.0（代理分） |
| 十维均分 | ≥ 3.5 |
| 任维 ≤2.0 | 该章 hardFail |
| GATE-A | 全绿 |
| GATE-B | ≥80% 章 |
| GATE-C | ≥90% 章 |
| GATE-D | ≥70%（SHOULD） |
| 限知泄漏 | 0（抽样） |
| 单章 E2E | ≤ 8 min 目标（软） |
| 全程 | ≤ 6 h |

### 9.2 十维 key（`scribe3/quality/models.py`）

```text
coherence_causality, character_truth, scene_necessity, structure_pacing,
suspense_payoff, emotional_effect, reading_experience, language_voice,
theme_subtext, originality
```

本方案用 `verify_content_quality` 的 scores + 启发式映射到十维（HTTP 回退同样输出）。  
**诚实边界**：非完整人工/LLM 十维盲评；S4 记入 SHOULD。

### 9.3 定稿门（M12）

- 无单一稳定 `GET /finalize-gate` 时：合成 `evaluateFinalizeGateReadOnly`  
  = GATE-A + 字数目标 + quality 仪表盘摘要  
- 与运行时 `finalize_gate.evaluate_finalize_gate`（写路径 post-check）正交；终审产物 `quality/finalize.json`

### 9.4 总 PASS 公式（本自动化方案）

```text
ok ⇔ ∀ id ∈ M1..M12: must[id].ok === true
```

SHOULD/COULD 失败只写入 `summary.json`，不单独阻断（除非你在后处理脚本加严）。

---

## 10. 执行命令与 CLI 集成

### 10.1 一键启动

```bash
#!/usr/bin/env bash
# 已实现：scripts/run_50k_acceptance.sh
./scripts/run_50k_acceptance.sh
./scripts/run_50k_acceptance.sh --resume
```

### 10.2 超时与重试

| 参数 | 值 |
|------|-----|
| 单次 `chiefSay` | 300–480s |
| `acceptDraftProposal` | 300s |
| `adoptDraftAsFinal` | 120s |
| 质量修订 | 2 轮 |
| GATE-A 修复 | 3 轮 |
| 全程墙钟 | 6h |

### 10.3 退出码

| code | 含义 |
|------|------|
| 0 | `summary.ok === true` |
| 1 | MUST 未全过或 withPage 失败 |
| 2 | 致命异常（启动/环境） |

### 10.4 与 CI 关系

- **不要**把本脚本接到默认 PR CI（真 LLM、长时、写 demo 库）。
- 适合：demo 机 nightly / 手动 workflow / 发版前长程。
- 确定性前端冒烟仍用 `scripts/e2e_ci.sh`（临时 Surreal，**占用 3311/3321 会拒绝**——与本方案互斥）。

---

## 11. 产物归档

```text
artifacts/e2e-50k-{YYYYMMDD}-{work_slug}/
├── checkpoint.json
├── journey.log
├── journey-meta.json
├── summary.json
│   ├── ok, word_count, chapter_count
│   ├── quality_scores, gate_results
│   ├── duration_minutes, run_ids
│   ├── must / should / could
├── chapters/
│   ├── ch01.json
│   ├── ch01.txt
│   └── ...
├── quality/
│   ├── craft_gates.json
│   ├── craft_gates_phase2.json
│   ├── rubric_scores.json
│   ├── quality_dashboard.json
│   ├── finalize.json
│   └── settings_counts.json
├── evidence/
│   ├── screenshot-*.png / phase1-four-col.png
│   ├── canon-candidates.json
│   ├── epistemic-samples.json
│   ├── promises.json
│   ├── memory-recalls/recall.json
│   └── run-traces/          # 可后续用 /ai/runs/{id}/trace 补
└── errors/
    ├── withpage.json
    └── fail-chN-*.png
```

归档命令示例：

```bash
ART=artifacts/e2e-50k-20260812-book_xxx
tar -C artifacts -czf "artifacts/$(basename "$ART").tgz" "$(basename "$ART")"
```

---

## 12. 故障排除

| 现象 | 原因 | 处理 |
|------|------|------|
| `E2E_ALLOW_DEPLOYED` 拒绝 | 安全护栏 | 确认目标确为验收栈后 export `=1` |
| 后端 health 失败 | compose 未起 | `docker compose ps` / `deploy_demo.sh` |
| `resolveComposer` 失败 | 右坞折叠 | `ensureChiefVisible`；查 `rightCollapsed` localStorage |
| 一直审批超时 | Hermes/MCP elicitation | 查 :8642–8644；看 run trace |
| 建章不落库 | 未批准 seed Run | `approveAllPending`；改走 `s3_add_chapter` |
| 提案卡不出现 | 写在了主编闲聊槽 | `preferWrite: true` + 正文/草稿 Tab |
| `采用为正文` 不可用 | 未 stage-fill | 先 `acceptDraftProposal`；再 adopt |
| quality 全 skip | 本机无 Surreal 直连 | 依赖 HTTP 回退；或在 demo 机设 `SCRIBE3_SURREAL_URL` |
| 字数达标但 M11 红 | 脚手架/检测未过 | 续跑单章 repair；勿 API 灌绿 |
| 与 e2e_ci 冲突 | 端口互斥哲学相反 | 长程用已部署；CI 用临时栈，勿混跑 |
| OOM on Grok 机 | 内存不足 | **只在 demo 机跑 Playwright** |

### 12.1 手动恢复

```bash
# 1) 找到 art 与 work
ls -lt artifacts/e2e-50k-* | head
cat artifacts/e2e-50k-*/checkpoint.json | head -40

# 2) 续跑
E2E_ART=/abs/path/to/art E2E_WORK=book_xxx E2E_BOOK_TITLE='原标题' \
  ./scripts/run_50k_acceptance.sh --resume

# 3) 单章人工：打开 SPA，选章，对话修订后把 lastCompletedChapter 手改 checkpoint
```

---

## 13. 功能矩阵速查

### MUST

| ID | 功能 | 实现锚点 |
|----|------|----------|
| M1 | 对话驱动建书 | `phase1Bootstrap` POST /works |
| M2 | 北极星 | `s3_set_intent` + GET /intent |
| M3 | 设定全类型 | MCP + list 端点 |
| M4 | WCG/GATE-A | `phase2Wcg` |
| M5 | 章脚手架 | `s3_patch_chapter_plan` |
| M6 | 15–20 章 ≥5 万字 | `phase34WriteAll` |
| M7 | 正典闭环 | `phase5` canon candidates |
| M8 | 限知 | `/frame` 抽样 |
| M9 | 记忆 | `/recall` + 对话 |
| M10 | 伏笔 | plant + track/resolve |
| M11 | GATE A/B/C/D 率 | `phase6FinalAudit` |
| M12 | 定稿门 | `evaluateFinalizeGateReadOnly` |

### SHOULD / COULD

S1 explore · S2 Director · S3 返工 · S4 十维/DTW 代理 · S5 结构多样性（仪表盘/注入侧）  
C1 Storyline DOM · C2 多 POV · C3 秘密时序（可扩展 `frame` 跨章 diff）

---

## 14. 验收标准判定示例（summary.json）

```json
{
  "ok": true,
  "protocol": "50k-cli-playwright-acceptance-v1",
  "work": "book_xxxxxxxx",
  "word_count": 51234,
  "chapter_count": 18,
  "ten_dim_avg": 3.72,
  "gate_results": {
    "A": { "ok": true, "pass_rate": 1 },
    "B": { "pass_rate": 0.89 },
    "C": { "pass_rate": 0.94 },
    "D": { "pass_rate": 0.78 }
  },
  "must_all": true,
  "duration_minutes": 287
}
```

---

## 15. 代码完整性声明

下列文件为**完整可运行实现**（非文档内伪代码）：

- `scripts/run_50k_acceptance.sh`
- `scribe3/web/e2e/acceptance_50k/run_50k_acceptance.mjs`
- `scribe3/web/e2e/acceptance_50k/env_guard.mjs`
- `scribe3/web/e2e/acceptance_50k/checkpoint.mjs`
- `scribe3/web/e2e/acceptance_50k/log.mjs`
- `scribe3/web/e2e/acceptance_50k/api_read.mjs`
- `scribe3/web/e2e/acceptance_50k/quality_bridge.mjs`
- `scribe3/web/e2e/acceptance_50k/ui_helpers.mjs`
- `scribe3/web/e2e/acceptance_50k/novel_bible.mjs`
- `scribe3/web/e2e/acceptance_50k/phases.mjs`

复用且禁止改坏的共享库：

- `scribe3/web/e2e/lib.mjs`
- `scribe3/web/e2e/author_decisions.mjs`
- `scribe3/web/e2e/craft_gates.mjs`

---

## 16. 建议执行顺序（demo 机）

```bash
# 0. SSH 到 demo，进入应用 git 树
cd /opt/scribe3/app   # 或同步后的 scribe-writing-system

# 1. 确认栈
curl -sf http://127.0.0.1:3321/health && curl -sf http://127.0.0.1:3311/ >/dev/null

# 2. 热更（若刚推代码）
# ./scripts/deploy_demo.sh   # 按仓库既有流程

# 3. 跑验收（screen/tmux 建议）
tmux new -s s50k
./scripts/run_50k_acceptance.sh
# 断线后续：
./scripts/run_50k_acceptance.sh --resume

# 4. 看结果
python3 -c "import json;print(json.load(open('artifacts/.../summary.json'))['ok'])"
```

---

## Revision

| rev | 日期 | 说明 |
|-----|------|------|
| 1.0 | 2026-08-12 | 初版：方案 + `acceptance_50k` 可执行脚手架入库 |
