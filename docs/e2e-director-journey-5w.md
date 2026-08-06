# Director 五站全链路 · 约 5 万字真实连载验收方案

| 项 | 值 |
|----|-----|
| **版本** | **5.0（真正完善版）** |
| **日期** | 2026-08-07 |
| **状态** | **已定稿 · 待按本版从零执行** |
| **产品** | scribe3 |
| **环境** | **仅 demo 已部署栈**（`www.qing.blue` / `ubuntu@82.157.130.140`） |
| **进度** | [`设计文档/2026-08-06-旅程5万字-进度.md`](../设计文档/2026-08-06-旅程5万字-进度.md) |
| **融合规程** | [`docs/融合执行规程-真人验收×对话驱动改造.md`](./融合执行规程-真人验收×对话驱动改造.md)（强制） |

---

## 0. 一句话

**先把设定做满并 Web 可见，再结构对齐，再按 pilot 状态机一章一章：大纲→节拍→演绎→草稿→体检→交付→定稿；任何一步假路径/脚手架/假证据都不算 PASS。**

---

## 1. 历史作废（不可再引用为 PASS）

| 轮次 | 书 | 致命捷径 |
|------|-----|----------|
| v1 | `book_d3052625` 等 | EMERGENCY 灌设定；模板扩写；skip 门 |
| v2 | `book_2524fd8a` | 离线 `prose_pure`→save-chapter；伪 07-trace；合成截图 |
| v3 | `book_887bb8e8` | **设定未齐就开写**；接地失败 **safe_beats/假演绎**；orch API 代替 Playwright；API 证明代替 SPA；full_check AI 味 soft-pass 当质量绿；scorer 曾硬编码 |

标题处置：

- v2 → `…离线灌稿·不作PASS`
- v3 → `…设定未齐即开写·不作PASS`

---

## 2. 完成定义（八线全绿）

```text
总 PASS ⇔ 设定 ∧ Web ∧ 导演 ∧ 真路径 ∧ 工艺 ∧ 质量 ∧ 规模 ∧ 缺陷
```

| 线 | PASS |
|----|------|
| **设定** | WCG 全绿（§4）；且 **先于** 任何验收正文 |
| **Web** | SPA：书库主书正确章数字数；设定 Codex 可见；目录 10 章；ch1/5/10 正文可见；**真截图或等价录像** |
| **导演** | `07-director-trace.jsonl` append-only；≥5 种 live `pilot_state`；时间跨度 >10s；**无**同微秒批造 |
| **真路径** | `EMERGENCY=0`；设定经 **对话意图→提案→批准**（融合：优先 Playwright 点批准；API apply 仅作工程过渡且须在结案前换成 UI 或书面 P1）；正文 **完整 pilot 链** |
| **工艺** | 无默认 `skip_craft`/`skip_finalize`；GATE 报告或等价可审计；**无** tape 中 safe_scaffold 相位 |
| **质量** | 无公式注水；读感过；正文可回指设定；AI 味 heavy 若产品 soft-pass → **不得**自动记质量 PASS，须读感说明或改稿再检 |
| **规模** | 已接受正文合计 **[45000, 55000]**；Web=API |
| **缺陷** | 无开放 P0/P1；`06-defect-ledger.md` 齐 |

---

## 3. 铁律（违反即本轮 FAIL）

| # | 铁律 |
|---|------|
| T1 | **未过 WCG → 禁止 draft_loop / 定稿作证据** |
| T2 | **章内必须** `idle→大纲→(approve)→节拍→演绎→草稿→(restore)→体检→交付→(approve)终选`；禁止跳步 |
| T3 | **禁止** `patch_chapter_meta` 灌 safe_beats / 假 scene_truth / 假 deductions 跳过接地 |
| T4 | **禁止** 离线长文 / prose_pure → save-chapter 作主证据 |
| T5 | **禁止** 伪造 multi-state director tape |
| T6 | **禁止** 默认 skip 门闩；禁止 EMERGENCY 灌正典作主路径 |
| T7 | **禁止** 用 API 静默代替「作者接受正文」当唯一路径（restore 须对应 advisory 真稿 + 可审计） |
| T8 | 接地/批准/Web 撞墙 → **STOP → 修产品或设定 → 同路径回归 → 再续**；禁止换捷径过关 |
| T9 | 结案文档与 SESSION/进度 **不得** 与事实矛盾 |

驱动已落实：`scripts/v2_serial_pilot.py` 遇接地 **`GROUNDING_STOP` 退出**；短稿用尽重试 **`SHORT_DRAFT_STOP`**；serialize 前强制 `v4_world_complete_gate.py`。

---

## 4. 设定完成门闩 WCG

命令：

```bash
python3 scripts/v4_world_complete_gate.py --slug <slug> \
  --out artifacts/e2e-journey-5w-v5-YYYYMMDD-<slug>/00-world-complete-gate.json
# 必须 exit 0
```

| 域 | 最低要求 |
|----|----------|
| intent | feeling / arc / ≥3 红线 / word_goal∈[4e4,6e4] |
| 角色 ≥4 | 每角色：appearance, personality_detail, surface_goal, deep_need, fear, **backstory**；含 protagonist |
| 关系 | ≥3 条角色关系（可回读） |
| 规则/事实 | ≥3 世界规则 + ≥5 可引用事实（真工具写入，非仅 ingest 噪声） |
| 势力/物件/术语 | 至少覆盖两类且计数达标（faction≥1 或 item≥2+term≥2 等，以 gate 脚本为准） |
| 伏笔 | ≥3 条 promise，含 setup/payoff 窗口 |
| 结构 | 3 卷 + 10 章；synopsis≥40 字；≥8 章 synopsis 点名已建角色；focalizer 指向角色 |

**WCG 未绿 → 不得进入 §6 串行。**

---

## 5. 阶段总览（固定顺序）

```text
Phase 0  环境与根因锁（EMERGENCY=0, SOFT=0；空壳书归档；Hermes 可用）
Phase A  建书 + intent（对话/orch 批准 → Web 可见）
Phase B  世界设定至 WCG 绿（可多日；撞墙修产品）
Phase C  结构对齐（卷章 synopsis 与设定互证）
Phase D  串行 10 章完整 pilot 链（仅此时开写）
Phase E  账本 + 读感 + 八线结案 + env 锁
```

---

## 6. 章循环 SOP（与 `scribe3/pilot.py` 一致）

```text
S0  章已存在且 synopsis 来自 Phase C（结构站）
S1  idle → propose_outline → outline_proposed
S2  /pilot/approve 放行大纲（品味检查点）
S3  expand_beats → beats_ready   【真 LLM；接地失败 → GROUNDING_STOP】
S4  deduce → deduced             【真场景真相+限知；接地失败 → STOP】
S5  draft_loop → drafting        【版本库；advisory → restore 最长合格稿】
S6  full_check → checked         【blocking 非软过则改稿或 STOP；见 §7.3】
S7  deliver → delivered
S8  /pilot/approve 终选 → finalized
S9  journal + tape + 字数；Web 打开本章抽样
```

**不允许：** 无大纲直接草稿；无演绎直接正文；restore 磁盘 prose_pure；短稿定稿充数。

---

## 7. 真路径细节

### 7.1 设定写入

```text
作者意图（对话或明确提案文案）
  → orch proposal: s3_set_intent / s3_add_character / s3_patch_character /
    s3_add_character_relation / s3_add_world_rule / s3_add_fact /
    s3_add_faction / s3_add_item / s3_add_term / s3_plant_promise / …
  → 批准：优先 Playwright 点「批准」；过渡期 API apply 须记入 06 并排期 UI 回归
  → GET 回读 + Web Codex/账本
```

### 7.2 正文写入

```text
仅 pilot/step + approve + restore-version
驱动语每步绑定：POV、设定实体、规则、本章 synopsis、应触伏笔
```

### 7.3 质量门（诚实）

| 情况 | 正确做法 |
|------|----------|
| pad 公式尾 | 禁止；出现即 FAIL |
| full_check 限知/退化 blocking | STOP 改稿，禁止 soft |
| full_check **仅** AI 味 heavy | 产品可记 quality_warn；**质量线须人工/代理读感**，不得自动 TOTAL 绿 |
| 字数不足 | 同链 re-draft（【强制重写】）；禁止磁盘灌入 |

### 7.4 批准 UI（融合 M7）

| 决策 | 设计 | v5 要求 |
|------|------|---------|
| Hermes/提案批准 | Playwright 点击 | **目标路径**；demo 装/跑 e2e 点批 |
| 大纲放行 / 终选 | SPA 或等价 | tape 记录；目标为 UI 点击 |
| API apply | 工程后门 | 仅过渡；结案须声明是否仍依赖 |

---

## 8. 工具与脚本

| 工具 | 用途 |
|------|------|
| `scripts/v4_world_complete_gate.py` | WCG 审计；exit≠0 禁写 |
| `scripts/v2_serial_pilot.py` | serialize **强制 WCG**；**接地 STOP**；短稿 STOP；score 从 tape 推导 |
| 禁止 | `v2_upload_pure` / `gen_literary_prose` 作证据；`--force-skip-world-gate` 验收禁用 |

---

## 9. 证据包

```text
artifacts/e2e-journey-5w-v5-YYYYMMDD-<slug>/
  00-runtime-baseline.md
  00-rootcause-fixes.md
  00-world-complete-gate.json      # WCG 机器结果
  00-shortcut-ban.md               # 本版禁止捷径清单勾选
  01-intent.md
  02-world.md                      # 丰满设定 live 实读
  03-structure.md
  04-serialize/ch01.md … ch10.md   # 每章 S1–S8 路径摘要
  05-ledger.md
  06-defect-ledger.md
  07-director-trace.jsonl          # live only
  08-wordcount-rollup.md
  09-final-closure.md              # 八线 + true_path/craft 信号
  10-env-lockdown.md
  screenshots/                     # SPA 或诚实说明+API heads
```

`09` 中若 tape 含 `grounding_safe_*` / `prose_pure` / `skip_craft` → **真路径/工艺 FAIL**。

---

## 10. 执行检查单（开工顺序）

1. [ ] 读本文件 v5 + 融合规程 M1–M7  
2. [ ] demo health；`EMERGENCY=0` `SOFT=0`；归档 v2/v3 干扰书  
3. [ ] **新建** `《旅程五站·v5·YYYYMMDD》`  
4. [ ] Phase A intent → Web  
5. [ ] Phase B 设定直到 **WCG exit 0**（证据 `00-world-complete-gate.json`）  
6. [ ] Phase C 结构对齐  
7. [ ] Phase D 逐章完整 pilot（无脚手架）  
8. [ ] Phase E 八线结案；SESSION/进度一致  

---

## 11. 工期（诚实）

| 段 | 估计 |
|----|------|
| WCG 设定（含可能修工具/字段/关系 API） | 1–4 日 |
| 结构 | 0.5 日 |
| 10 章真链 | 数小时–数日（接地/LLM 时延） |
| Playwright 批准链若未通 | 额外 0.5–2 日修 UI/e2e |
| 结案 | 0.5 日 |

---

## 12. 修订记录

| 版本 | 说明 |
|------|------|
| 1–2 | 假路径 / 离线灌稿（作废） |
| 3 | pilot 产文但设定未齐 + 脚手架（作废） |
| 4 | 设定门闩优先（骨架） |
| **5.0** | **完善版：八线 + 全捷径黑名单 + 真状态机 + 接地 STOP + 证据/融合/质量诚实规则** |
