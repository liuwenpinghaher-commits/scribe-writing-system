# Director 五站全链路 · 约 5 万字真实连载验收方案

| 项 | 值 |
|----|-----|
| **版本** | **3.0**（作废 1.0 / 2.x 执行 PASS；方案骨架保留并收紧） |
| **日期** | 2026-08-06 |
| **状态** | **已重定 · 全量最优真路径执行中** |
| **产品** | scribe3 |
| **环境** | **仅 demo 已部署栈**（`www.qing.blue`）；禁止 Grok 机起 Surreal/全量 monorepo |
| **进度台账** | [`设计文档/2026-08-06-旅程5万字-进度.md`](../设计文档/2026-08-06-旅程5万字-进度.md) |

---

## 0. 为何再重定（v3）

### 0.1 作废的「完成」

| 轮次 | 做法 | 否决原因 |
|------|------|----------|
| v1 | `EMERGENCY_REST` 灌设定 + 模板扩写 `save-chapter` + skip 门 | 假路径；Web 空/误导 |
| v2 | 离线 `prose_pure/*.txt` 批量 `save-chapter`（no skip）+ 事后装饰 pilot；`07-director-trace` 同微秒 8 态伪造 | **正文不是 pilot 链产物**；导演线造假；七线 TOTAL 不诚实 |
| v2 证据 | 宣称 45285 字 PASS | skeptic 三轮 refuted：pilot 装饰、trace 剧场、PNG 非 SPA |

**v2 库内数据（审计 2026-08-06，book_2524fd8a）仍在，但不得作为验收 PASS：**

| 观察 | 含义 |
|------|------|
| API `word_count=45285`，ch1–10 `prose` 有文学正文 | **库有字**，不等于真路径完成 |
| 角色 4 个但 **backstory/性格等字段全空** | Web 设定面板「像没写设定」 |
| `workflow/snapshot` **旅程卡在「世界底座」** | 产品 bug：`_char_count` 只认 `list_characters`，生产 Store 只有 `characters()` → 永远 0 |
| 旅程 structure/serialize 显示 todo | 与「10 章已成」矛盾 → 作者体感「空书/未完成」 |
| 当前章车道停在 ch11 附录 pilot 烟测 | 干扰主书阅读焦点 |
| pilot 单次 draft 常 ~1.3–1.6k 字 | 未修 token/驱动前无法靠真链稳达 5k×10 |

### 0.2 用户可见问题（必须当 P0）

作者在 **Web** 打开时：

1. 若默认进错书 / 旅程永远停世界 → **像空书或没进度**  
2. 角色只有名字 → **设定像没有**  
3. 即便点开 ch1 有离线灌的散文 → **也不是验收要求的 pilot 真写路径**  

**v3 不以「API 字数够」为完成；以 Web 旅程+设定+正文+真路径证据一致为完成。**

### 0.3 v3 一句话

先 **最优修产品根因**（旅程角色计数、章稿生成上限、设定丰满度），再在 **新 slug** 上用 **对话/编排批准 + pilot/step(+approve) + restore 采纳 pilot 稿** 串行写出约 5 万字；**禁止** 离线 `prose_pure` 灌库作证据；**禁止** 同时间戳伪 multi-state；结案闸 `EMERGENCY=0` / `SOFT=0`。

---

## 1. 完成定义与七线（更严）

```text
旅程总 PASS
  ⇔ Web可见  ∧  导演  ∧  真路径  ∧  工艺  ∧  质量  ∧  规模  ∧  缺陷
```

| 线 | PASS 条件 |
|----|-----------|
| **Web 可见** | 登录 SPA → 书库见主书章数/字数 → 目录 10 章 → 打开 1/5/10 章可见 **pilot 源** 正文；设定面板角色 **非空字段**；旅程在结构/连载合理推进（不永卡世界） |
| **导演** | `07-director-trace.jsonl` **append-only、时间序、间隔合理**；≥5 种 **真实** `pilot_state`；每行来自 live step/approve/restore，禁止批造 |
| **真路径** | `EMERGENCY_REST=0`；世界写经 orch **approve** 或 Hermes 审批；**禁止** 主证据为 REST 静默灌正典 |
| **工艺** | 成稿 `skip_craft=false` 且 `skip_finalize=false`；GATE 绿或单次书面 P0 逃生并关闭 |
| **质量** | 文学正文；pad 标记（条N存档/换位完成/观察条/勒紧半指等）=0；读感可过 |
| **规模** | 已接受正文合计 **[45000, 55000]**；Web 与 API 一致 |
| **缺陷** | 无开放 P0/P1；临时逃生已关 |

### 1.1 正文唯一合法源（v3 硬条）

```text
accepted_prose(seq)
  := 经 live pilot/step（含 draft_loop）生成的版本
     → /chapters/{seq}/restore-version 采纳
     → 后续 full_check / deliver / /pilot/approve 定稿
     的 chapter.prose

禁止:
  - 读 prose_pure/*.txt / gen_literary_prose 结果 POST /save-chapter 作为主证据
  - 短 pilot 稿不够长时用磁盘长文「补齐」
  - 伪造 07-trace 多状态
```

若单次 draft 仍短：最优路径是 **产品侧** 提高 loop `max_tokens` + 驱动语字数目标，再 **同章 re-steer + 再 draft_loop**（可多次），**不是** 离线扩写灌入。

### 1.2 明确禁止

| 禁止 | 最优替代 |
|------|----------|
| 离线长文 bulk `save-chapter` 冒充连载 | pilot 链 + restore + approve |
| 伪造 director multi-state | live append-only tape |
| `EMERGENCY_REST` 灌设定 | orch proposal/apply approve |
| `skip_*_gate` 默认 | 修门闩 / 脚手架 |
| 七线假绿 | score_closure 只读 tape + API 实读 |
| 把 v2 book_2524fd8a 当 PASS | 归档为反面教材；主证据用 **新 slug** |

---

## 2. 拍板（v3）

| # | 决定 |
|---|------|
| D1 | 新验收书：`《旅程五站·v3·YYYYMMDD》` **新 slug**；v2 书改名/归档标注「离线灌稿·不作 PASS」 |
| D2 | 10 章 × 约 4.5–5.5k，合计 4.5–5.5 万；质量优先，禁止注水凑数 |
| D3 | 题材：限知志怪（纸灯/债契线可延续设定骨架，但 **正文必须重产**） |
| D4 | 串行驱动：`v2_serial_pilot.py`（名沿用实现文件）为 **唯一** 证据序列路径 |
| D5 | 世界：intent + ≥4 角色（含性格/目标/恐惧等可见字段）+ 卷 + 章 synopsis + 伏笔，均经 **approve** |
| D6 | 结案：`SCHEMA_SOFT=0` `EMERGENCY_REST=0` |
| D7 | Web 证据：API prose head **必须** + 尽量 SPA 真截图；禁止把合成 PNG 当 SPA |

---

## 3. 阶段 0 · 根因最优修复（先修后写）

| ID | 问题 | 最优方案 | 状态 |
|----|------|----------|------|
| R0.1 | 旅程永卡「世界」 | `director._char_count` 兼容 `characters()` | **已修（代码）** |
| R0.2 | pilot 稿 ~1.5k | `loop_chapter` `max_tokens=8192` + draft_loop 字数驱动 | **已修（代码）** |
| R0.3 | 角色设定空壳 | 批准路径写满 codex 字段，非仅 name | 执行期 |
| R0.4 | 空壳/干扰书 | 归档空书；v2 书标题加「不作PASS」 | 执行期 |
| R0.5 | 假证据脚本 | 隔离 `v2_upload_pure` / `build_pure_final` 等为 **NON-EVIDENCE** | 执行期 |
| R1 | 建书 Surreal 2.1 | 已有迁移修复；SOFT=0 建书 | 回归 |
| R2 | 世界写闸 | 保持 EMERGENCY=0；orch approve | 执行期 |
| R3 | pilot 停靠/restore | dismiss→step→approve 大纲→…→draft park→restore 最长稿→继续 | 驱动实现 |
| R5 | 部署 | push main → GHA → demo 冒烟 | 执行期 |

**阶段 0 出口：** 修复已部署；`workflow/snapshot` 在有角色后 **current ≥ structure/serialize**；新建书 SOFT=0 成功。

---

## 4. 真路径合同

```text
【世界】主编意图 → orch proposal ops → decision=approve execute
         → GET /intent /entities /volumes /promises 回读非空字段

【正文】每章:
  dismiss(清僵尸态) → steer(字数+质量) → step/approve 直至 drafting
  draft_loop 产 version → 若 parked advisory:
      GET /chapter-versions → 取最长 prose 的 version_id
      POST /chapters/{seq}/restore-version
  step → full_check → deliver → /pilot/approve 终选
  若 cn_len(prose) < 4500: 不灌盘；再 steer 扩写 / 清 prose 重 draft（产品帽已提高后）
  每步 append 07-director-trace.jsonl（真实 ts）

【禁止】prose_pure → save-chapter；同 ts 伪状态；skip 默认
```

---

## 5. 五站执行摘要

| 站 | 硬门 |
|----|------|
| 0 基线 | env 审计；部署 R0；证据目录；归档 v2 |
| 1 intent | 批准写北极星；Web/API 可见 |
| 2 world | ≥4 丰满角色 + 规则/伏笔；旅程离开「世界」 |
| 3 structure | 3 卷 + 10 章 synopsis |
| 4 serialize | 10× pilot 真链正文 ≥45k |
| 5 ledger | 字数 rollup + 诚实七线 + 缺陷关闭 |

章循环 SOP 同 v2 §5.1（S1–S9），**不得**用 save-chapter 替换 S3–S6。

---

## 6. 证据包

```text
artifacts/e2e-journey-5w-v3-YYYYMMDD-<slug>/
  00-runtime-baseline.md
  00-rootcause-fixes.md
  01-intent.md … 06-defect-ledger.md
  07-director-trace.jsonl   # live only
  08-wordcount-rollup.md    # 从 API 实读
  09-final-closure.md       # score_closure(tape) 诚实绿/红
  10-env-lockdown.md
  screenshots/              # prose heads 必须；SPA 尽量
```

**score_closure 规则：** 导演 PASS 仅当 tape 内 **≥5 不同 pilot_state 且时间跨度 >10s**；规模/质量从 API 正文实算；任何一票否决则 TOTAL 不得 PASS。

---

## 7. 工期（诚实）

| 段 | 估计 |
|----|------|
| 根因部署 + 新书脚手架 | 0.5–1 日 |
| 10 章真 pilot（含 LLM 时延与停靠处理） | 数小时–数日（视网关） |
| 结案与 Web 验收 | 0.5 日 |

**不做「最快灌库」；卡点就修产品再同路径回归。**

---

## 8. 修订记录

| 版本 | 说明 |
|------|------|
| 1.0 | 假路径冲字（作废） |
| 2.0 | 真路径方案对；执行仍 offline 灌稿 + 假 trace（执行作废） |
| **3.0** | **根因修复 + 正文唯一源=pilot；新书；诚实 scorer；全量最优执行** |
