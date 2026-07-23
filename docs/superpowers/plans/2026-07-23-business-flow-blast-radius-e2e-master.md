# 业务流 × 爆炸半径 × E2E 执行质量 · 总控计划

> **日期**：2026-07-23  
> **目标**：沿每一条完整作者业务流做爆炸半径分析，修闭环缺陷，并用分层 e2e 证明执行质量。  
> **真源**：`docs/CURRENT_ARCHITECTURE.md` · `docs/craft-first-verification-scheme-v3.md` · `docs/融合执行规程-真人验收×对话驱动改造.md` · `docs/真人作者全功能验收测试方案-v2.md`  
> **分支**：`feat/architecture-split-and-hardening`

---

## 0. 完成定义（旅程总 PASS）

```text
旅程总 PASS ⇔
  卫生 PASS (GATE-A ∧ ∀seq GATE-B ∧ C-Det)
  ∧ 质量 PASS (verify_content_quality + 专家读感无阻断)
  ∧ 无未关闭 P0/P1
  ∧ 禁止用 form_fill / 字数 / 入口触达 单独结案
```

`make e2e-real`（`full_journey.mjs`）**只算 Hermes 连通冒烟**，不得写入「质量验收 PASS」。

---

## 1. 完整业务流地图（作者主路径）

| ID | 业务流 | 入口 | 主干链路 | 爆炸半径（失败谁炸） |
|----|--------|------|----------|----------------------|
| **F1** | 世界写（设定/结构/意图/伏笔/素材） | UI「让主编…」种子 / Hermes Run | `chiefSeed` → `shouldUseHermesRun` → MCP `s3_*` → `_ask` → **`commit_if_approved`** → Surreal | 世界正典不落库；后续简报/限知/写作上下文陈旧；作者以为已写入 |
| **F2** | 正文生成与接受 | 写作槽 / 主编 prose 意图 | `POST /chat/write`（**只读 MCP**）→ 提案卡 → 接受 → `/save-chapter` → 自动 ingest | 无稿；存稿 craft 闸 409；知识账本落后 |
| **F3** | 章阶段脚手架 | 大纲/节拍/演绎 Tab | seed → `s3_patch_chapter_plan` 等 → GATE-B | 跳过阶段写正文 → GATE-B 红；旅程不得标完成 |
| **F4** | 限知与反哺 | 演绎 + 存稿后 ingest | `project_frame` / `find_leaks` / `/ingest` | 越知进 prompt；因果/伏笔台账断 |
| **F5** | Emergency REST 闸 | 默认关 | 世界写前缀 403；手稿/chat/ai 放行 | 残留表单直写必炸；测试钉开 ≠ 生产 |
| **F6** | 四栏布局 | phase / view | `layoutMode` + collapse + `sanitizeLayout` | 折叠空白、还原钮错位；**不**伤世界态 |
| **F7** | 横切看板 | 图谱/时间线/仪表盘 | view 模式隐藏目录；详情主舞台 | 导航错乱；决策无对象 |
| **F8** | 工艺门闩 | save / e2e | `verify_craft_compliance` · `/craft-gates` | 假绿结案（旧字数路径已作废） |

### 1.1 写通道分层（铁律）

```text
作者语义世界写 ──► Hermes + WRITE_GATED + commit_if_approved
正文/草稿       ──► /chat/write 提案 → save-chapter（非世界闸）
紧急运维 REST   ──► SCRIBE3_EMERGENCY_REST_WRITE=1（产品默认 0）
过程记忆        ──► memory_fabric（默认开）≠ 正典替代
```

### 1.2 WRITE_GATED 全集（须全员走 commit）

含：角色/事实/事件/知识/意图/伏笔/关系/卷章 meta/plan/素材 add·**patch·delete**/母题/结构运维等。  
**禁止** WRITE_GATED 名在闸内却手写 declined/written 绕过 `commit_if_approved`（`s3_register_purpose` 已收回）。

---

## 2. 爆炸半径矩阵（改一处先看谁）

| 改动面 | 必回归 |
|--------|--------|
| `mcp.py` / `commit_if_approved` | `test_mcp` · `test_p0_author_paths` · `test_gate_invariants` |
| emergency middleware | `test_emergency_rest_write` |
| chiefSeed / Codex / Materials / Binder | vitest readonly · chiefSeed · structure-dialogue-write · policy-dualwrite-ban |
| `/chat/write` · save · ingest | `test_app` 相关 + writeChat/WriteLayout 测 |
| layoutMode / FourPaneShell | layoutMode · sanitizeLayout · fourPaneShell 测 |
| craft 合规 | `test_craft_compliance_gates` · `craft_gate_cli` |
| 前端壳/选择器 | `make e2e-frontend` · author_decisions |

---

## 3. 缺陷台账（审计 2026-07-23）

| ID | 级 | 流 | 问题 | 处置 |
|----|----|----|------|------|
| R1 | P0 | F1/F5 | Materials **编辑/删** 走 REST，闸关 403 | **已修**：`s3_patch_material` / `s3_delete_material` + seed CTA |
| R2 | P1 | F1 | `s3_register_purpose` 绕过 commit | **已修**：统一 `commit_if_approved` |
| R3 | P1 | F8 | fused 无 `E2E_WORK` 仍 OK | **已修**：默认强制；仅 `E2E_SKIP_CRAFT_GATES=1` 可跳 |
| R4 | P1 | F1 | Intent 数字配额 `putIntent` 仍世界闸 | **已修**：`PUT /intent-goals` + 前端 putIntentGoals；叙事仍闸 |
| R5 | P1 | F2 | 自动+手动 ingest 双路径 / 多 worker | **已文档化**：单 worker 在途去重合同；多 worker 须跨进程锁（未实现） |
| R6 | P2 | F1 | `s3_save_chapter` / `s3_ingest` 无审批 | 设计旁路（手稿）；保持 + 文档标明 |
| R7 | P2 | F8 | `e2e-real` 弱路径心智假绿 | Makefile 注释澄清；总控禁止当质量 PASS |
| R8 | P3 | F6 | 旧 `FourPane.jsx` 占位 | 不挡主路径 |

---

## 4. 分层验证执行单（本机）

### L0 · 确定性（不烧网关）

```bash
make test-baseline
make test-author-paths
make test-craft
make e2e-det
cd scribe3/web && npm test -- \
  src/lib/chiefSeed.test.js \
  src/layout/__tests__/layoutMode.test.js \
  src/layout/__tests__/sanitizeLayout.test.js \
  src/layout/__tests__/fourPaneShell.test.jsx
```

### L1 · Craft 卫生（活库）

```bash
make e2e-craft-gates   # 反面书必须红
# 正面书：craft_gate_cli --work <slug> --seq 1
```

### L2 · 前端隔离冒烟（3311/3321 须空闲）

```bash
make e2e-frontend
```

### L3 · 工艺优先旅程（Hermes + 开发栈）

```bash
# 前后端已起 :3311/:3321；SCRIBE3_CRAFT_GATE=1；勿 E2E_ALLOW_API_SEED=1
cd scribe3/web && GOAL_SCRATCH=../../artifacts/e2e-$(date +%Y%m%d)-craft \
  E2E_BASE=http://127.0.0.1:3311 E2E_API=http://127.0.0.1:3321 \
  node e2e/craft_first_journey.mjs
```

### L4 · 质量轨 + 人工

```bash
# 旅程内嵌 ContentQuality；再人工读稿 → artifacts/.../09-author-verdict.md
# 仅当卫生+质量+无 P0/P1 → 旅程总 PASS
```

### 弱连通（不得结案）

```bash
make e2e-real   # full_journey：建书+一句话
```

---

## 5. 执行节奏（缺口即改）

```text
跑 L0 → 红则修 → 绿
跑 L1 反面 → 必须红
（可选）L2 隔离冒烟
L3 craft_first 1 章 → 红按 RC-* 修链路 → 同意图回归
扩展 3 章 / 返工剧本（v2 §5）
人工质量评审 → 总 PASS 或 打开未决 R*
```

---

## 6. 本轮已落地代码

- `scribe3/mcp.py`：`s3_patch_material` / `s3_delete_material`；`s3_register_purpose` → commit
- `chiefSeed.js` + `Materials.jsx`：编辑/归档/删除走种子
- `fused_author_journey.mjs`：强制 craft gates
- `Makefile`：`test-author-paths` / `test-craft` / `e2e-craft-gates`
- 单测：`test_p0_author_paths` / `chiefSeed.test.js`

---

## 7. 证据目录约定

```text
artifacts/e2e-YYYYMMDD-<work>/
  gates/gate-a.json
  gates/ch{N}-bc.json
  quality/ch{N}.json
  05-gap-research-log.md
  09-author-verdict.md
```

---

## 8. L3 真机执行记录（2026-07-23）

| 轮次 | work | 结果 | 发现 |
|------|------|------|------|
| r1 | book_2bff6f45 | GATE-A A3+A5 红；0 章 | 建书选择器已修；建章按钮只 seed 不发送 |
| r2 | book_7c49d708 | A5 红；0 章 | 工具名拆分后 A3 绿；stage 无章失败 |
| r3 | book_46a6ccfb | A5 红；s3_add_chapter 未落库 | chiefSay 建章仍 0 章（store 直写可绿） |
| r4 | book_d75a78f7 | 同 r3 | Hermes 可写 character/rule/promise/intent；**系统性不落库 motif+chapter** |

**已修产品缺口**：
- `craft_first` 建书路径对齐 `书名…` + Enter  
- 世界写 seed **自动发送**（`ChiefDock` seedIn）  
- Hermes instructions 补 motif/chapter/plan  

**阻塞旅程总 PASS 的 RC**：
| RC | 说明 | 下一步 |
|----|------|--------|
| RC-HERMES-STRUCTURE | Hermes Run 对 `s3_add_chapter` / `s3_add_motif` 不落库（store 与 MCP commit 单测绿） | 查 scribe3_write 工具面/审批/work 注入；重启 Hermes 重载 MCP |
| RC-REACT-KEY | 空书阶段 React duplicate key 刷屏 | 单独修列表 key |
| RC-SEED-NOSEND | （已修）seed 只填不发 | 回归按钮建章 |

证据目录：`artifacts/e2e-20260723-craft{,2,3,4}/`

---

## 专家团结果（计划层）

- **模式**：Feature team · Plan + Fix + Verify  
- **角色**：Architect（流图）· Implementer（R1–R4）· Tester（分层门闩 + L3）  
- **未决**：RC-HERMES-STRUCTURE（L3 主阻塞）；R5 多 worker 锁；L4 人工读感  
)
