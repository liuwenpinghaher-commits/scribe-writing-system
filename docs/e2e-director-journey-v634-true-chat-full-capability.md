# 铜炉验证方案 · v6.3.4 · 真书 · 对话驱动 + 点批/工作台裁决 · 全能力可验

| 项 | 值 |
|----|-----|
| **文档标题** | 铜炉 Director 旅程验收协议 · 全面更新（全能力 · 真书 · 对话驱动+点批） |
| **版本** | **v6.3.4 rev.13.4.1**（写章内核 play-contract 五层 + story-state 跨章连续性 + 叙事人称一致性 + 句子层装腔闸。**冻稿正文=定稿**；对白口径为引号行字数比。**WCG、SPA 不改**；总 PASS 维持 Wave C） |
| **作者** | Grok Design（待人类审定） |
| **日期** | 2026-08-20 |
| **状态** | **Draft rev.13.4.1** · 写章验收按新五层冻结。本轮同 slug `book_8777aad8` 第一章。宣称 / WCG / SPA **不改** |
| **产品** | 铜炉 / tonglu · 代码 `scribe3/` · 仓库 `/home/admin/projects/scribe-writing-system` |
| **验收环境** | **仅 demo 已部署栈**（公网主入口 **`https://tonglu.qing.blue`**；`www.qing.blue` / `qing.blue` 301 → 主域） |
| **禁止** | Grok 运行机全量 `npm ci` / 本机 Surreal / 第二验收栈 / 脚本灌章冒充体验 PASS |
| **WCG SSOT** | **`scripts/v4_world_complete_gate.py`**（exit 0 前禁止验收向连载） |
| **耐久落库建议路径** | `docs/e2e-director-journey-v634-true-chat-full-capability.md` |
| **摘要** | `/tmp/grok-1000/grok-design-summary-adfa3bbb.md` |

---

## 命名与前序关系

| 版本 | 角色 | 与本版关系 |
|------|------|------------|
| **v6.2** · `docs/e2e-director-journey-5w.md` | 纪律底本：遇障同路、正典全类型闭环、**WCG 以 gate 脚本为准**、约 5 万字 | **纪律与闭环实现真相仍有效**；规模主轴以本版覆盖 |
| **v6.3 / 6.3.1** · `docs/e2e-director-journey-2w-memory.md` | 约 2 万字；记忆主轴 M0–M6；D1–D7 | **记忆子集附录**；**总 PASS 以本版为准**（见 PR-Doc-2 指针） |
| **v6.3.2** · 同上 §2.4 | 真 chat 铁律；`v632_true_chat_journey.py` | **路径纪律继承**；落库方式须对齐 **SPA 三通道**（§SPA 作者通道真相），不得仅脚本 ChangePack 冒充 SPA |
| **v6.3.3** · `docs/plans/2026-08-10-v633-revalidation-quality-delta.md` | 变更复验 F1–F12 | **能力清单吸收**；**禁止**作体验总 PASS |
| **捷径禁令** · `docs/e2e-journey-5w-v5-shortcut-ban.md` | 黑名单 | 全文继承 + 本版追加 |
| **记忆质量 / 人盲** | to-9.5 · human-blind protocol | 诚实边界强制 |
| **校验 / 台账 / 做厚 / SESSION** | 08-10～08-11 plans | 映射矩阵 V/Q/H 等 |
| **v6.3.4 rev.3** · 本文 | 吸收 08-14 已上线：冰山地板、防洪水注入、设定库生成链、飞行记录仪、主编聊/选择/驾驶、决策收件箱含选择+Hermes、左栏「校验」不再日常入口 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.4** · 本文 | 吸收 08-14～08-15 写章实跑病灶：草稿读路径、节拍 UI 裁切、persist/focalizer/余烬、四仪与 drama 槽、usage/headline、recall/causal 回退。钉 **OpSeq 操作顺序**（大纲→节拍→演绎→排演 persist=true→latest-draft→定稿→save-chapter）。**不**另开总 PASS 公式 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.5** · 本文 | 章纲 SSOT 换为 `chapter_spine.v1` 13 短槽；Ice1/Ice2 改线索密度闸。demo 旧炉灰记已清。当时验收书 `book_bdfdcdc4`（**rev.6 起退役**）。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.6** · 本文 | **故事宇宙换锚**：《万界概率战争》V7.0。A1–A7 / 书名 / 金样 / 证据模板全部改绑。产品闸、OpSeq、SPA、WCG **一字不改门槛**。新旅程必须新建 slug。宇宙 SSOT：`docs/worlds/wanjie-probability-war-v7.md`。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.7** · 本文 | 吸收 fate-dearer rev.7：Ice3/4/6 **字数不再作通过条件**（结构 Should；旗 on 才 Must）。S2 必写 `who_pays`/`axis_terms`/`clock_start`/`clock_end`。OpSeq 大纲必填章钟 `span`/`delta` 与地点 `name`/`delta`。跨章禁止同物件同动作卡住；`delta=0` 只许冻一章。**不改** WCG 数字、SPA、宣称、GATE-B 80、`GATE_SAVE_MODE`。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.8** · 本文 | 吸收 fate-dearer rev.8：`cast_role_frozen` / `world_fact_*` / extra=`evaluate_write_contract`；默认 WAVE-2。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.9** · 本文 | WAVE-1 增 `goal_off_world`；ASK 末尾【世界合同】压过 extra；`SCRIBE3_PIPELINE_RECORDER` 默认开；F3b/c 分批硬闸标为历史。当时验收书 `book_83584141`（**rev.10 起不再当本轮验收书**）。禁 overlay `book_e415dfeb` / `book_61a7935e`。**不改** WCG 数字、SPA、宣称、GATE-B 80、`GATE_SAVE_MODE`。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.10** · 本文 | 本轮验收条：必须 **新建 slug** 连写 **第 1–3 章**；每章 OpSeq 一层 `persist=true`（outline→beats→deduce→draft→final）；`SCRIBE3_WORLD_SURFACE=on` 下定稿付清 goal/hook 组（`surface_claim_unpaid` / `claim_paid_by_paraphrase`）；extra 命令语气 → `extra_authors`；ch2 起 `gesture_echo`。质量验收读阶段文 + 记录仪，**HTTP 200 / 字段非空 / 闸绿 ≠ 完全按方案**。禁 overlay `book_83584141` / `book_e415dfeb` / `book_61a7935e` / `book_bdfdcdc4` / `wanjie-fate-r7`。**不改** WCG 数字、SPA、宣称、GATE-B 80、`GATE_SAVE_MODE`。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.11** · 本文 | **史。** 当时 OpSeq 步数因 design 合并减少。旗 `SCRIBE3_CHAPTER_DESIGN`、旧 design=outline+beats **已不存在**（rev.12 作废）。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.12** · 本文 | **吸收 play-contract 系统换代：** 旧写章五层（outline/beats/deductions/scene_truth/draft）与 Fate/水面闸全部删除；OpSeq、冰山表、Ice/Fate 矩阵行、KD-25/26 重写。当时总 PASS 公式、WCG、SPA、宣称不改。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.13** · 本文 | **协议优化：** 收尾 rev.12 漏改；Gate 0 部署冒烟；窗口版本冻结；traces×冻结对账；产物质量 Wave C 进总 PASS；playbook.2 对抗用例。WCG / SPA / ShouldRate 0.80 **不改**。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.13.1** · 本文 | **跨章连续性进验收：** 章末态（`chapter_state`）入新五层验收锚；Wave C 补连续性四判据；对抗用例 D9–D12；playbook.3 指针。WCG / SPA / ShouldRate 0.80 **不改**。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.13.2** · 本文 | **人称一致进验收：** state.narrative_pov 确立与传承；C-Must 补人称行；对抗 D13–D14；Gate 0 三闸升四闸；state/duty 读端点入验收对账；窗口冻结硬化（git tag）。WCG / SPA / ShouldRate 0.80 **不改**。不追溯修旧书人称。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.13.3** · 本文 | **保真精修：** C-Must「冻稿正文」澄清为定稿；对白行注明口径（引号行字数比）；state 锚句 final 后校正；契约 quote 禁编辑；run-card fail_reasons；冒烟书 slug 保留。WCG / SPA / ShouldRate 0.80 **不改**。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.13.4** · 本文 | **句子层：** 叙述装腔闸 `syntax_tics`（≥2 处「不是 A 是 B」/毒句式才拦，对白不计）；节奏三个数字只记账；定稿法官改成念开头 + 有没有在使劲（仍八问）；playbook.3.2。**不改** 明喻 1/800、对白 15%、重复率 15%、WCG、SPA、ShouldRate 0.80。不 overlay `book_20bab124`。 | **不替换** SPA 三通道与 WCG 脚本 |
| **v6.3.4 rev.13.4.1** · 本文 | **糙稿提示：** 字数不够与跟戏太像交替时合着说，门槛数字不动。装腔硬拦只留定稿，糙稿只点名原句。卡住的卡片写出原因，重发关掉上一张空白进行中。验收同 slug `book_8777aad8` 第一章。不 overlay `book_20bab124`。 | **不替换** SPA 三通道与 WCG 脚本 |

**系统换代声明（rev.12 必读，rev.13 / rev.13.1 / rev.13.2 / rev.13.3 / rev.13.4 仍准）：** 2026-08-18 起，写章内核换成 play-contract。旧 `stage=outline/beats`、`chapter_spine` / `beats` / Fate / 水面 422 码 **全部作废**。拿 rev.11 条款去验收会误伤 410 或假绿。本文从本节起按新五层验收。

**为何叫 v6.3.4 而非 v6.4：** 仍是 6.3 家族（对话驱动 · 记忆 · 真书），相对 6.3.3 是「补全能力矩阵 + 拉回 SPA 体验主路径」的修订号。仓库与结案字段钉 **v6.3.4**。rev.12 换写章验收内核；rev.13 **只加** Wave C 与开跑前置，**不改** WCG 门槛数字、SPA 三通道、ShouldRate 0.80。rev.13.1 **只加** 跨章连续性维度，**不改** rev.13 全部已有判据阈值。rev.13.2 **只加** 人称闸、对白硬闸、清洗器与读端点，**不改** 已有阈值、WCG、SPA。rev.13.3 **只加** 保真精修。rev.13.4 **只加** 句子层装腔闸与节奏记账，**不改** 已有数字门槛、WCG、SPA。rev.13.4.1 **只改** 糙稿重写提示与装腔拦的层、卡片原因，**不改** 门槛数字。**

```text
6.2 成功 ≈ 对话+点批 → 约 5 万可读好书 + 正典闭环
6.3.x 成功 ≈ 同上路径 → 约 2 万字 + 记忆真有用
6.3.3 做到 ≈ 变更探针 + 常工程/pilot（≠ SPA 体验 PASS）
6.3.4 成功 ≈ 作者打开旅程 + 主编对话驱动 + 点批/工作台裁决
           → 写完一本真书（可见字约 2 万；结构壳满足 WCG）
           → 全能力矩阵在真实写章阶段被触达并留证
           → 可复述「我聊了天、点了批/放行，没用脚本灌章」
```

**v6.3.2 记忆子集地位：** 仍可用于「只关心记忆线」的工程对照或附录探针；**不得**单独宣称铜炉 v6.3.4 **总 PASS**。总 PASS 协议 = 本文。

---

## Overview

2026-08-09～08-11 合入章节 lease、卷章 IA、弧光、校验 hybrid、QC 扩维、knowers×leaks、做厚 H1–H11、System Hub、图谱抽屉、TurnBind 等。v6.3.2 钉真 chat；v6.3.3 做变更复验但缺 `00-author-path`，**不能**当体验总 PASS。

本版 **v6.3.4 rev.4** 目标（rev.2 / rev.3 全部保留，并加上写章操作纪律）：

1. **全能力可验**（Must/Should/Could + 分波）；以代码与 **WCG 脚本** 为 SSOT。  
2. **真书**新 slug；真实连载。  
3. **主编对话驱动 + 点批/工作台裁决**（非「禁止点工作台」）；禁止表单直写正典与脚本灌章。  
4. **真实写作流程**，能力嵌在 **写章 S7** 内，非章后演示点一点。  
5. 证据可拆穿；**不宣称** 人盲 ≥9.5。  
6. **写章质量可分析**：五层冻结真过审、契约原文引用对得上、注入防洪水可回放、设定库生成链可验、飞行记录仪能打开真实工件；不是「字段非空 / HTTP 200」即绿。水面「付清」改由定稿法官 + 人评，**不再有词匹配 422 硬闸**。

**工期诚实（rev.2 仍准）：** 真人 SPA 全量（Wave A+B）估 **3–5+ 人日**；非 1.5–3 人日。可分波：仅 Wave A → 最高 **PARTIAL**，两波齐才总 PASS。

**rev.3 增量工期：** 走完冰山链 + 打开运行分析卷宗，每章额外约 0.5–1 人时（含 LLM 等）。不改变 Wave A+B 总公式。

**rev.4 增量：** 不改工期公式。每章必须按 OpSeq **一层验收完再进下一层**；禁止并行两层、禁止 persist=false 开新层。续写已有书时从第一层未厚处接着走，已厚层 SKIP。

---

## Background & Motivation

### 痛点

| 痛点 | 事实 |
|------|------|
| 验收碎片化 | 多 plan 无「一书内全触达」 |
| v6.3.3 假绿路径 | `docs/evidence/v633-reval-20260810/` **无** `00-author-path.md` |
| v632 ≠ SPA | 脚本显式 `change-pack(use_llm)`；浏览器主路径更偏 **resolve→world_write 审批** |
| WCG 硬 | `v4_world_complete_gate.py`：**≥3 卷、≥10 章、母题≥3、承诺≥3、丰满角色…** |
| 讨论非 agentic | `ChiefDock.jsx` **`agentic: false` 写死**（防跨书串库） |

### 为何必须更新 6.3

不更新 → 继续用工程复验或错误「1 卷」规格撞 WCG 红；不写 SPA 三通道 → 执行者「只口述等 ChangePack」设定落不进 L1。

---

## Goals & Non-Goals

### Goals

1. **全能力可验**（矩阵 + 分波）。  
2. **真书**新 `book_*`（创建时间 ∈ 证据窗）。  
3. **对话驱动 + 点批/工作台裁决**（§路径内 UI 白名单）；意图/设定/结构/开写/改稿/中程变更/记忆探针进主编线程或可追溯种子。  
4. **真实写作流程**；能力在 S7 写章内触达。  
5. **WCG SSOT = gate 脚本** exit 0 先于连载验收。  
6. 证据可审计；诚实质量边界。

### Non-Goals

- 不宣称人盲 **≥9.5**。  
- 不把 v632/v633/pilot/serial 当体验总 PASS。  
- 不默认打开 DRAMA/EVENT_DRIVE/STAGE_HARD/PARK 硬门 / EMERGENCY。  
- 不在 Grok 机全量 npm / 本机 Surreal。  
- 不穷尽调用 94 个 MCP 工具（验能力面与路径）。  
- **不**要求 SPA 默认开启 `/chat/agentic-stream`（当前禁用）。

---

## SPA 作者通道真相（产品实现 · 强制阅读）

> 代码锚：`scribe3/web/src/ChiefDock.jsx`、`lib/orchestrateSend.js`、`WriteChat.jsx`、`DeduceStage.jsx`；后端 `api/routers/director.py`、`canon_loop.py`、`misc_routes.py`。

### 三通道

| 通道 | 触发 | 实现 | 作者可见 | 正典/正文落库 |
|------|------|------|----------|----------------|
| **discuss** | 主编坞闲聊/讨论意图 | `GET /chat/stream`；**`agentic: false` 写死** | 对话气泡 | **不直接写 L1**；可附 orch proposal / 可选 change_pack 载荷 |
| **world_write** | `/orchestration/resolve` 命中写世界，或种子点名 `s3_add_*` | **`api.runWrite`**（Hermes 全写 + **工具审批卡**） | 审批卡批准/拒绝 | **主设定落地路径之一**：批准后 MCP `s3_*` → Surreal |
| **prose_write** | 章阶段写稿 | **`/chat/write`** + stageProposal 落中区 | 提案卡/用此版 | 正文/草稿进章字段 |

### 合法设定落地（C1 多选一 · 须可追溯 chat/种子）

| 路径 | 说明 | 体验 PASS |
|------|------|-----------|
| **(a) ChangePack** | 讨论原文 → `POST /canon/change-pack`（`use_llm`/`source=discussion`）→ 待确认/收件箱点批 → apply | ✅ 若 SPA 或明确作者触发；v632 脚本对照 ≠ 单独 SPA PASS |
| **(b) world_write 审批** | 对话/「让主编…」种子 → resolve → runWrite → **审批卡点批** `s3_*` | ✅ **SPA 主路径之一** |
| **(c) 定稿候选** | finalize → PostFinalize / pending-claims → 点批 | ✅ 定稿反哺 |
| **禁止** | 无 chat/种子的批量 `proposal/apply` 拼 ops；表单失焦改正典；EMERGENCY REST | ❌ |

### agentic 辨析（勿混淆）

| 概念 | 是否 SPA 默认 | 本版矩阵 |
|------|----------------|----------|
| **`/chat/agentic-stream`** | **禁用**（ChiefDock `agentic:false`） | Ch3 = **Could**（若将来开启） |
| **world_write + Hermes 审批写世界** | **常用主路径** | **设定 Must 的落地方式 (b)**，**不是**「可选 agentic」 |
| 讨论附带 change_pack | API 存在；**前端几乎无一键主按钮** | 工程/部分 orch 路径；不得假设「只聊自动出包」 |

### 浏览器如何触发 world_write（S3 执行要点）

1. 旅程「继续」/ 章前契约 **「让主编写…」**（`focusChiefWithSeed`，文案常含 `s3_add_*` 提示）。  
2. 作者在主编坞发送意图明确的设定指令（角色/母题/卷章结构）。  
3. 观察是否出现 **审批卡** → **批准**；Codex/目录回读确认。  
4. 打开 **设定收件箱 / 待确认设定**（CanonInbox / PendingClaims）处理候选。  
5. 若仅 discuss 无审批、设定未落库 → **继续发 world_write 向指令或种子**，禁止 curl 代 `s3_add_*` 冒充作者。

---

## 2026-08-14 已上线能力（rev.3 强制阅读；rev.4 操作顺序见上节 OpSeq）

> 本节只登记 **demo 已部署、作者旅程会碰到** 的能力。  
> **不改** 上文 SPA 三通道，**不改** `scripts/v4_world_complete_gate.py` 为结构 SSOT。  
> 工程对照：`docs/plans/2026-08-14-iceberg-complete.md`、`2026-08-14-antiflood-blast-radius.md`、`2026-08-14-codex-generation-chain.md`、`2026-08-14-pipeline-runtime-analysis.md`、`2026-08-14-chief-mode-fusion.md`。

### 新五层产物与验收锚（rev.12 · 替代旧写章冰山；rev.13.1 加章末态）

第 N 章金样 = `duty_card` + `chapter_play` + `contract` + `deduce` + `draft` + **`chapter_state`**（+ `prose` / `end_hook`）。`chapter_state` 是冻结糙稿（或定稿若与糙稿实质不同）的抽取副产品，不是第六生产层。每条人物/物件状态必须带正文锚句（`quote` 字面 ∈ 冻稿）。

| 层 | 产物（146 五表 + 148 章末态） | 验收锚（Must） | 作者动作 |
|----|------------------|----------------|----------|
| duty 责任卡 | `duty_card` | 法官 PASS + 结构闸；ch≥2 时 `bite_from_prev` == 上章 contract `hook.quote` | `POST /generate-stage stage=duty persist=true` |
| design 戏+契约 | `chapter_play` + `chapter_contract` | 所有 quote ∈ play（`quote_in_play`）；`stages_choice=true` 恰 1 场；法官 PASS 才冻结 | `stage=design persist=true`；`GET /chapters/{seq}/play` 与 `/contract` 回读 |
| deduce 演绎 | `chapter_deduce` | 法官 PASS；不得与 final prose 合并 | `stage=deduce persist=true` |
| draft 排演 | `chapter_draft` | 法官 PASS；`GET /latest-draft` 非空 | `stage=draft persist=true` |
| 章末态（抽取） | `chapter_state` | 冻结；每条人物/物件 `quote` ∈ 冻稿（`state_quote`）；供下一章 `prev_state` | draft 冻结后自动抽取；失败不静默 |
| final 定稿 | `prose` + `narrative_drive.end_hook` | 法官 PASS（含账是否付了）→「用此版」/ `/save-chapter` | `stage=final persist=true` |

**过渡：** 凡 playbook.2 老书续跑，首跑章的上一章 state 必须补登，补登产物标 `backfill=true`。不补则下一章 `prev_state` 为空，跨章连续性无从验收。不要求回填全书历史。

**层序铁律：** 上一层未冻结 → 409 `stage_not_ready`。旧 stage 名（outline / beats / chapter_design / plan）→ **410 Gone**，不得当产品 bug 上报。`s3_patch_chapter_plan` 已废，改 `s3_generate_stage` 或人工 `s3_patch_play` / `s3_patch_contract`（仍需法官复审才能冻结）。

**纪律：** 生成必须走 LLM。已冻结层默认跳过；`force=1` 只重跑本层、不动上游冻结戏。`rewrite=1` 只许 design：新戏版本，旧戏与下游作废。契约抽三次不过 → `needs_human`，**戏保持冻结**。宣称公式 **本版不改**。

### Fate / 水面闸（已删）

**Fate/水面闸已随 play-contract 删除。** `SCRIBE3_FATE_DEARER` / `SCRIBE3_FATE_WAVE` / `SCRIBE3_WORLD_SURFACE` 及 `fate_blocked` / `surface_claim_unpaid` / `claim_paid_by_paraphrase` / `gesture_echo` / `goal_off_world` / `world_fact_*` / `cast_role_frozen` 422 码均已不存在。唯一存活的旧闸是 `extra_authors`（命令语气 422）。水面「付清」改由 final 法官（账链路，LLM 判）+ 人评承担，**不再是词匹配硬闸**。

### rev.12 本轮：按新五层写章（替代 rev.11「只跑 design」）

本轮 **不是** 续写旧验收书。必须新建 slug。每章按新 OpSeq **走全五层**，每层 `persist=true` + 法官冻结后再进下一层。只跑 design 一层只算工程探针，不算体验验收。

| 条 | Must |
|----|------|
| 新书 | slug ∉ `{book_83584141, book_e415dfeb, book_61a7935e, book_bdfdcdc4, wanjie-fate-r7, book_718fe88f, book_680ab75f}`。任何 generate persist 之前先 `s3_set_intent` 并种可绑的 `promise:` / `storyline:` id |
| 每章五层 | `duty → design → deduce → draft → final`，每层 persist=true。design 后 `GET play` + `GET contract`：quote 全在戏里、抉择恰一场、hook.quote 非空 |
| 跨章 | ch≥2 的 `duty_bite`：`bite_from_prev` **字面等于**上章 contract `hook.quote`（机器硬闸，不是人工点名四字） |
| 冻结 | 不改宣称 / WCG / SPA。质量读阶段文 + 飞行记录仪；闸绿单独不算「完全按方案」 |

开书 S2：先 `s3_set_intent(who_pays, axis_terms, clock_start, clock_end)`（纪律，**缺了不会 422**）。设定库用 `add_term` / `add_item`。不 overlay 上表黑名单 slug。

质量验收（本目标增量，非 Wave A 总 PASS 替代）：读戏/契约/演绎/排演/正文 + 飞行记录仪，判 **连贯 / 演绎≠正文合并 / 注水 / 空壳 / 账是否付了**，不得只报「字段非空」。水面付清靠法官 + 人评。

### rev.12 操作顺序（OpSeq · 强制，一层完再进下一层）

> 写章顺序写错仍会空稿、断余烬。rev.12 按 play-contract 钉死。  
> **不改** SPA 三通道、**不改** WCG、**不改** 宣称。

对每一章，**严格按层、禁止乱序、禁止并行两层、禁止跳过未冻结层**：

```text
0.  开书 S2（每书一次）：s3_set_intent(who_pays, axis_terms, clock_start, clock_end,
    red_lines, total_word_goal) + 种 promise:/storyline: id
0b. 新章：s3_add_chapter → GET /chapters 确认壳
1. POST /generate-stage stage=duty   persist=true
   → ch≥2 验 duty_bite：bite_from_prev == 上章 contract hook.quote
2. POST /generate-stage stage=design persist=true
   → GET play：戏非空；GET contract：quote 全 ∈ play、stages_choice 恰 1、
     hook.quote 非空
3. POST /generate-stage stage=deduce persist=true → chapter_deduce 冻结
4. POST /generate-stage stage=draft  persist=true → GET /latest-draft 非空
5. POST /generate-stage stage=final  persist=true → 法官 PASS → /save-chapter
   → GET chapter.prose 非空；narrative_drive.end_hook 非空
6. 下一章开写前：确认上章 contract hook.quote 在库（duty_bite 的咬源）
禁止：乱序/并行两层/未冻结层开新层（409）/persist=false 当验收/
      只报 HTTP 200 与字段非空/把 410 旧 stage 当 bug。
```

| 已冻结层 | 处理 |
|----------|------|
| 该层 status=frozen | **SKIP** 重跑，从第一层未冻结处接着走 |
| 排演未冻结 / 正文未存 | **必须** 从该层继续，不得跳到更下层 |
| 只重抽契约 | `force=1` 只重跑本层，不动上游冻结戏 |
| 整章重拍戏 | 仅 design 允许 `rewrite=1`：新戏版本，旧戏与下游作废 |

**禁止（rev.12 操作 FAIL，即使 HTTP 200）：**

- 新章或未冻结层用 `persist=false` 当验收
- `generate-stage` 不传 `focalizer`（记录仪 POV 空/错）
- 跳过排演直接 final；跳过 `/save-chapter` 直接开下一章
- 并行生成两层；乱序（先排演后责任卡）
- 验收只报 generate-stage 返回值 / HTTP 200 / 字段非空
- 把 410 旧 stage 当产品 bug
- 把「已冻结层 skip」用到新章

### 前四章病灶 → 操作纪律（必须吸收）

| # | 病灶 | 现象（炉灰记 book_c14585d8） | 根因 | rev.4 纪律 |
|---|------|------------------------------|------|------------|
| F1 | 草稿 Tab 空 | ch1–3 `chapter.draft` 有万字，UI 读 `/latest-draft` 只认 `chapter_version` | 读路径不回退 | **产品已修** `resolve_latest_draft`。操作：draft 后必须 `GET /latest-draft` 验非空 |
| F2 | 长文框裁切 | 长稿被矮框裁掉，误判「没生成完」 | CSS | **产品已修** 为全文 `pre-wrap`。操作：戏/契约/排演验收读全文，不看框高 |
| F3 | persist=false 无正文 | ch4 大纲/节拍/演绎已厚，`draft=0 prose=0 hook 空` | 加厚脚本把 persist=false 用到未落库层 | **新层一律 persist=true**。ch4 从 draft 补起，不得重开书 |
| F4 | 忘传 focalizer | 记录仪 POV 空；注入用错视角 | 脚本未传 / generate-stage 默认 `""` | **每层必传** 本章主视角（本书 `role:柳岸青` / 落库 id） |
| F5 | 上章无 hook → 下章 ember 空 | 未 `/save-chapter` 则 `narrative_drive.end_hook` 不进余烬 | persist=false 或只写 draft | 定稿后必须 save-chapter，再 GET 验 hook，**再**开下一章 |
| F8 | usage=0 | 只统计 proposal fence | `_collect_write` | **产品已修** raw_delta。记录仪须有非零 usage |
| F9 | recall/causal 空 | 书无 fact/event 图 | C3 章台账回退 | 空则记缺陷，**不得因此停写**；回退须能看见上章因果 |
| F10 | 已冻结层再跑 skip | 续写当新章重跑 duty/design | 冻结层 skip | **跳过已冻结层**，从第一未冻结层顺序往下 |
| F11 | 排演读路径空 | persist 只写 `chapter_draft` 表，UI 只认旧 `chapter.draft` | 读路径未接新表 | **产品须** `GET /latest-draft` 回落冻结 `chapter_draft`。验收仍以该接口非空为准 |

**续写裁定（rev.9）：** 炉灰记 / `book_bdfdcdc4` / `wanjie-fate-r7` / `book_e415dfeb` / `book_61a7935e` **不得续写当本版总 PASS**。新旅程必须 **新建 slug**，从 S1 起按 OpSeq 走。旧书只作考古对照（ch8/9 红闸是证据，不是待办）。

### 防洪水（Antiflood · 注入层）

写请求组装时的六层刀 + `soft_activation`。作者不直接点「防洪水」。验收看飞行记录仪：进模型的段、被丢掉的段、帽。禁止把 `NOVEL_PROMPT_HARD` 调到 96k 当修法。demo 代码默认 48k、现网可 96k，**本版不改帽**。

### 设定库生成链

`POST /generate-codex` / `POST /generate-codex-batch` / Hermes `s3_generate_codex*`：**只生成不落 L1**。`include_secret` REST 拒绝；Hermes 走 `scribe3_write.include` 真边界。做厚种类 LLM-only。落地仍走 C1(a|b) 点批。

### 飞行记录仪 / 运行分析

`pipeline_chain`/`span`（140）+ `pipeline_event`/`pipeline_artifact`（142）。作者入口：**运行时·数据 → 运行分析**（一书一库；禁止再埋进「运维·危险」）。`SCRIBE3_PIPELINE_TRACE` 默认开；`SCRIBE3_PIPELINE_RECORDER` **设置/代码默认开**（仅显式 `0/false` 关）。7 日 TTL。查询：`GET /debug/pipeline-traces?work=`，单链 `include=events,artifacts`。

**全部信息 ≠ 全部字节**：允许窄红名单（密钥 / Cookie / secret 值）。禁止再用这句话砍掉 `end_hook`、戏/契约/演绎/排演正文、丢掉的段、编译段。

**红名单（rev.13）：** 密钥 / Cookie / secret 值。**禁止**再用旧 Fate/水面词项当红名单。新增必须进卷宗的两类质量事故：**章边界词入文**（上一章/这一章/下一章/本章）、**draft 对 play 高重复**（8 字窗 >15%，钩子豁免段除外）。

### 主编附属模式（聊 / 选择 / 驾驶）

右栏不再常驻「选择环」「主编驾驶」两个 tab。能力收进主编坞 **模式条**：聊（默认）/ 选择 / 驾驶。切模式 **不换 `thread_id`、不卸对话槽**。作业进行中 `jobBusy` 禁同章发送。REST `/select/*` `/pilot/*` **语义不变**。结果在模式条展示，不伪造聊天气泡。

### 决策收件箱

决策收件箱须能看见：待批设定、驾驶待放行、**选择环 pending（L1/L2/失败）**、**Hermes 待审批**。点选 / 终选须 `mark_select_result_verdict` 后从队列消失。设定收件箱（CanonInbox）仍是正典点批，不与决策收件箱混成一个列表。

### 「校验」不再是左栏日常入口

`GET /issues` 确定性台账仍在（护栏、全量体检、深链 `leftTab=review`）。**左栏入口组不再放「校验」tab**（`review` cap `hidden: true`）。日常看 **护栏灯 + 全量体检**。本版 **禁止** 把「校验」加回左栏当日常入口来凑 Q1 截图——Q1 改从护栏空态或全量体检覆盖诚实截图。

---

## 路径内 UI 控件白名单（Issue 15）

| 允许（路径内） | 禁止（体验 FAIL） |
|----------------|-------------------|
| 作品库 **新建** | 旧书改名 / 复用脏 slug |
| **旅程看板** 站位/WCG/字数/债 | serial pilot 无 chat 灌章 |
| **主编坞** 发送（discuss / 触发 world_write） | 表单失焦批量改正典 |
| **主编模式条** 聊 / 选择 / 驾驶（不换会话） | 把选择/驾驶再拆成右栏常驻 tab |
| **审批卡** 批准/拒绝/过期 | EMERGENCY 世界写 |
| **层法官放行**（duty / design / deduce / draft / final 各层独立放行态）/ 用此版 / 终选 / advisory 接受 | safe_beats / prose_pure / 离线 prose 灌库 |
| **待确认设定 / 决策收件箱 / pending-claims 点批** | 无 chat 脚本拼 ops |
| **章工作台** 阶段切换、play/contract 页、戏/契约/演绎点批；五层冻结 | 后台 seed 假记忆；切句充数当戏 |
| **Issue「让主编处理」** 种子后再聊 | curl **代聊** |
| **护栏 / 全量体检**（日常质检） | 把左栏「校验」当日常入口 |
| **运行时·数据 → 运行分析** | 只报 HTTP 200 / 字段非空当质量 PASS |
| **只读** Codex/目录/正文/Inspector/图谱 | 只 curl 绿当 UI Must PASS |
| System Hub **≤5 分钟只读**（不改危险设置） | 为凑绿关 fabric / 开 emergency |

**表述修正：** 「唯一合法作者路径」= **对话驱动生产意图 + 白名单 UI 裁决**，**不是**「禁止点击工作台」。

---

## 强制路径（不可协商）

### Gate 0 · 部署冒烟（开跑前必过）

验收开跑前必须完成 Gate 0：在 **已部署 demo** 跑 `python3 -m scribe3.tools.v634_smoke --mode live`（或 `scripts/v634_smoke.py --mode live`）。

假书一章五层全链须同时满足：

- 每层冻结产物存在  
- 该章 trace 状态为 `ok`（或 `ok` 且笔记写明「链异常但产物已落库」）  
- 法官 verdict ∈ {pass, fail}（不得默认盖章）  
- draft–play 8 字重复率 ≤15%（钩子豁免）  
- 正文无章边界词（上一章/这一章/下一章/本章）
- **chapter_state 产物生成** ∧ 每条 quote 保真 ∧ `gender_pronoun` / `state_quote` / `simile_density` / `pov_consistency` / `syntax_tics` **五闸**在岗（各注入一次对抗样本断言拦截，含 D13 人称翻转、D14 删像残渣、D15 叙述装腔）。冒烟书的 state 归档进 `00-smoke-result.md`
- **硬冻结：** Gate 0 PASS 后立即 `git tag gate0-YYYYMMDD`；跑批启动脚本校验 `HEAD==tag` 否则拒跑（容器内用 `SCRIBE3_GATE0_SHA`）。窗口内检测到新提交 → 该批次标「作废」，协议免责。连续三批跨版本混账（rev.12 热修窗、playbook.3 双进程、本批进程 A/B 横跨）后此项由纪律升级为工具强制。

**Gate 0 不过，验收不许开跑。** 产物归档为证据包 `00-smoke-result.md`。部署入口级 `--mode imports` 可作热更钩子，**不能**替代本条 live 全链。

### 会话铁律

0. **窗口版本冻结。** 开跑时记录后端指纹：`GET /health` 的 `changefeed.started_at`（或等价）+ 部署 commit。**窗口内任何热修/重启 → 已跑章节全部作废，从热修后重跑。** 禁止边修边跑边认账。Gate 0 PASS 后立即 `git tag gate0-YYYYMMDD`；跑批启动脚本校验 `HEAD==tag` 否则拒跑。窗口内新提交 → 该批次标「作废」，协议免责。连续三批跨版本混账后此项由纪律升级为工具强制。  
1. `GET /api/chat/threads?work=<slug>` 有线程；建议作者可见轮次 **≥60** 或覆盖阶段清单（开书/设定/结构/每章开写/探针/中程/改稿）。**数量不是充分条件**——禁止闲聊垫数。  
2. **硬门（主编线）：每章定稿章（1–5）≥1 条「开写」user message**，thread 导出可对 **seq / 时间戳**；缺任一章 → **主编线 FAIL**。  
3. 正典落库须可追溯到 **chat 原文或 UI 种子**（world_write 审批或 ChangePack `source=discussion` 等）；禁止无追溯 ops。  
4. `00-author-path.md` 诚实；脚本主写 → 主编线 FAIL。  
5. `GET https://tonglu.qing.blue/api/capabilities`：`memory_fabric_v1=true`，`emergency_rest_write=false`。  
6. chat/种子时间 **早于** 对应 apply / finalize。  
7. **每章 ≥1 次 UI 点批截图**（戏/契约冻结放行 **或** 终选 **或** 候选批准之一）；纯 pilot step+approve 无截图 → 最高 **PARTIAL**，不得体验总 PASS。  
8. **slug 必须本次新建**：`works.created_at`（或等价）∈ 证据时间窗；禁止旧书改名。旧验收 slug 黑名单示例：`book_7b918ca0`、`book_013bcb3b`、`book_aa57f17e`、`book_052a2adb`、`book_79c0d45e`、`book_b2a72ccb`、`obs-scratch`、`book_qe_live5`、`book_c14585d8`、`book_bdfdcdc4`、`wanjie-fate-r7`——**充分条件是时间窗，名单非穷尽**。

### `00-author-path.md` 模板

```markdown
# 00-author-path · v6.3.4
- slug / 书名 / 新建时间（须 ∈ 证据窗）
- 宇宙：万界概率战争 V7.0（不得填炉灰记）
- 作者是否真人坐浏览器：是 / 否（否 → 最高 engineering PARTIAL）
- 通道使用：discuss / world_write 审批 / prose_write / ChangePack / generate-stage（勾选实际用过的）
- 五层：每章 duty/design/deduce/draft/final 冻结状态 + contract quote 核验结果
- 运行分析：至少 1 条链 `include=events,artifacts` 路径
- 是否仅对话+白名单 UI：是 / 否（列例外）
- v632/v633/pilot：用途（禁止/对照）
- 每章开写 chat：seq → message_id 或时间戳（1..5 全填）
- 每章 UI 点批截图路径：ch01..ch05
- EMERGENCY / safe_beats / 离线灌库：0 次
```

---

## 真书规格（WCG SSOT）

### 原则

| 项 | 规格 |
|----|------|
| **结构/设定完成门** | **`python3 scripts/v4_world_complete_gate.py --slug <book>` → exit 0** 为唯一 WCG SSOT |
| **可见定稿字数** | **[18000, 24000]** 去空白（~2 万）；**不**回到 5 万门禁 |
| **intent.total_word_goal** | **40000–60000** 整数（脚本硬检；推荐 **45000**） |
| **本轮定稿章** | **第 1–5 章** finalize；第 6–10 为结构壳（有 synopsis，可不写正文） |
| **卷** | **≥3 卷**（gate：`volumes.ge3`）——**不是 1 卷** |
| **章壳** | **≥10 章** + 每章 synopsis 去空白 **≥40**；≥8 章 synopsis 提及角色名 |
| **书名模板** | `万界概率战争·v6.3.4·真chat全能力·YYYYMMDD-HHMM`；**新 slug** |
| **故事宇宙** | **KD-15：默认《万界概率战争》V7.0**（A1–A7 见下节 + `docs/worlds/wanjie-probability-war-v7.md`）。炉灰记锚退役，不得再当本版总 PASS 宇宙 |

**禁止：** 协议私自写「1 卷即可 WCG 绿」而不改 gate / 不部署 `--profile`。若未来降 WCG，须 **先改脚本并 demo 部署**，再改协议。

### 验收宇宙（rev.6 · 强制）

完整实体/金样/红线见 [`docs/worlds/wanjie-probability-war-v7.md`](./worlds/wanjie-probability-war-v7.md)。执行者不得再用灰七/香债/侧门当默认锚。

| 工作名 | 角色 |
|--------|------|
| 柳岸青 | 主角 · 双权柄 · 移动成核点 |
| 沈烛 | 守火人档案员 |
| 赫斯 | 神权祭司 / 天龙座买办 |
| 兰因 | 普罗米修斯同盟相位锚工程师 |

**三卷：** 囚笼 / 泄露 / 第三条路。**1–5 定稿题：** 华山成核 → 四十二度 → 金縢裂纹 → 灭活边缘 → 牧场主出价。6–10 壳见宇宙 SSOT。

**第 1 章金样 = 新五层锚（可改字，不可改形状）：** `duty_card` + `chapter_play` + contract 五字段（goal / choice / decision / cost / hook）+ deduce 五层 + draft + prose/`end_hook`。choice 仍是「交碎片给沈烛换活 **vs** 自己按回裂口暴露双权柄」。`lines` 绑已有 promise/storyline id；钩须可被第 2 章 `duty_bite` 字面对上。禁止 13 槽旧载体，禁止把炉灰记「假铜挡眼皮」搬进本章戏。

### WCG 可勾选表（与 `v4_world_complete_gate.py` 对齐）

| check 名 | 条件 | 作者侧怎么做（对话+审批） |
|----------|------|---------------------------|
| `intent.reader_feeling` | 去空白 ≥10 | chat 口述读者感受 |
| `intent.emotional_arc` | ≥4 | 情绪弧 |
| `intent.red_lines` | ≥3 行或长度≥20 | 红线 |
| `intent.total_word_goal` | int ∈ [40k,60k] | 规划字数 |
| `characters.count>=4` | ≥4 角色 | 设定 |
| `characters.codex_full(...)` | **≥4** 角色含 appearance/personality_detail/surface_goal/deep_need/fear/backstory | 丰满字段，勿只给名字 |
| `characters.has_protagonist` | importance=protagonist | 标明主角 |
| `relations.ge3_or_graph_edges` | ≥3 | 合法关系边 |
| `world_rules_or_propositions.ge3` | ≥3 | 规则/命题 |
| `facts.ge5_or_graph` | facts≥5 或图命题节点≥5 | 事实/命题 |
| `faction_item_term.two_categories` | faction/item/term 至少两类有实体 | 势力/物件/术语 |
| `promises.ge3` | **伏笔/承诺 ≥3** | `s3_plant_promise` 等 |
| `motifs.ge3` | **具名母题 ≥3** | `s3_add_motif` 等 |
| `volumes.ge3` | **≥3 卷** | 结构 chat / world_write |
| `chapters.ge10` | **≥10 章** | 结构壳 |
| `synopsis.ge40chars.ge10` | 1–10 章各 synopsis ≥40 字 | 梗概 |
| `synopsis.mentions_character.ge8` | ≥8 章梗概含角色名 | 写梗概时带名 |

**审计命令（只读证据，不代写）：**

```bash
export API_BASE=https://tonglu.qing.blue
python3 scripts/v4_world_complete_gate.py --slug book_xxx --out .../00-world-complete-gate.json
# 必须 pass=true / exit 0
```

### 脚手架其它纪律（继承 6.3.1）

- 关系词表合法（禁「债主/债权人」等）。  
- 物件：`artifact` vs **`state`**；A6 只 supersede `state`。  
- 禁止为 WCG 灌非法边/短梗概/双真。

---

## 真实写作流程阶段图（rev.2 重排）

### 总览：能力嵌写章，S11 仅补漏

```mermaid
flowchart TB
  S0[S0 环境锁与登录] --> S1[S1 新建真书 · 时间窗]
  S1 --> S2[S2 开书意图 chat · A5]
  S2 --> S3[S3 设定 · world_write/ChangePack · A1-A4 A7 · 母题承诺]
  S3 --> S4[S4 结构 ≥3卷≥10章 · WCG exit 0]
  S4 --> S5[S5 卷章 IA · 章前契约]
  S5 --> S6["S6 M0+M1 硬门 · 未过不得结案记忆PASS"]
  S6 --> S7[S7 章循环 1..5 · 内嵌能力]
  S7 --> S8[S8 中程 M4 · 设定债]
  S8 --> S7
  S7 --> S9[S9 定稿反哺 M6 · ingest lease]
  S9 --> S10[S10 护栏+全量体检 · 运行分析卷宗]
  S10 --> S11[S11 补漏巡视 · SystemHub/全局图谱]
  S11 --> S12[S12 Wave B Should 收口]
  S12 --> S13[S13 字数 · 矩阵 · 十线]
  S13 --> S14[S14 结案证据包]
```

### S7 单章（每章强制嵌能力）

```mermaid
sequenceDiagram
  participant A as 作者
  participant C as 主编坞
  participant W as 章工作台
  participant DB as Surreal

  A->>C: 开写 user message（硬门）
  A->>W: duty 责任卡冻结
  A->>W: design（play + contract）冻结
  A->>W: deduce 演绎冻结
  A->>W: draft 排演冻结
  A->>W: final 定稿
  Note over A,W: 五层流 duty→design(play+contract)→deduce→draft→final
  Note over A,W: ch≥3：M3；限知章：M5；弧光/图谱可同章打开
  W->>DB: finalize → post_finalize / ingest lease
```

| 阶段 | 作者动作 | 系统期望 |
|------|----------|----------|
| S0 | 登录 tonglu | health/capabilities |
| S1 | 新建 | 新 slug + 时间窗 |
| S2 | 意图+A5+命运坐标 | 线程+intent 批；`who_pays`/`axis_terms`/`clock_start`/`clock_end` 非空 |
| S3 | 设定全类型+母题+承诺+丰满角色 | world_write 审批和/或 ChangePack；收件箱点批 |
| S4 | 「三卷十章壳，本轮写 1–5…」 | **WCG 脚本 exit 0** |
| S5 | 契约页 | 齐套 soft |
| S6 | M0+M1 | **硬门：未过 M1 不得宣称过程记忆并进入结案记忆 PASS** |
| S7 | 每章开写+点批+内嵌 IA/Stage/可选 parallel/弧光/Inspector | 全链；禁 safe_beats |
| S8 | A6 变更 | supersede 单真 |
| S9 | 批候选 | M6；ingest status |
| S10 | 护栏 / 全量体检 / 运行分析 | coverage 诚实；QC 扩维；打开本章飞行记录仪（事件+工件） |
| S11 | Hub≤5min；全局图谱补漏 | 不改危险设置 |
| S12–S14 | Wave B + 结案 | 矩阵 schema |

---

## 完成定义与分波

### 总 PASS 公式

```text
总 PASS ⇔ Wave A ∧ Wave B ∧ Wave C
Wave A ⇔ 旅程 ∧ 主编(每章开写+UI点批) ∧ 设定(WCG exit0) ∧ 正典闭环
        ∧ 真路径 ∧ 工艺 ∧ 质量底线 ∧ 规模 ∧ 缺陷
        ∧ 记忆(M1∧M3∧M5 且 ≥5/7) ∧ 矩阵 Must 全绿（含 Must-if 规则）
Wave B ⇔ Should 计分 ≥80%（见下）∧ 证据 schema 合法
Wave C ⇔ C-Must（机器可测，全过）∧ C-人评（三身份通读，无红旗）
仅 Wave A → 最高 PARTIAL（可写「Must 旅程完成」），不得总 PASS
仅 Wave A∧B、Wave C 不过 → 机制绿、书不及格，不得总 PASS
```

### Wave C · 产物质量（rev.13；rev.13.1 补跨章连续性；rev.13.2 补人称/对白硬闸；rev.13.4 补句子层装腔闸）

机制 PASS ≠ 小说高质量。Wave A/B 验「层序/quote/409/410 是否运转」；Wave C 验「打开书像不像一章小说」。rev.13.1 补一句：**章章合格 ≠ 成书合格**。

#### C-Must（机器，全过才算）

| 指标 | 判据 | book_7331087b 基线 | book_3b6d91bd 基线 | book_be4343e4 基线 |
|------|------|--------------------|--------------------|---------------------|
| play→draft 8 字重复率 | 每章 ≤15%（hook 承接段豁免） | 23% / 57% / 98.92% | 15.04% / 2.69% / 5.76% | 15.0% / 8.7% / 11.2% |
| 章边界词入正文 | 0 处 | 4 处 | — | 0 |
| contract.fields.cost 非空 | 每章非空 | 0/3 | — | — |
| stages_choice 拍 conflict | 每章非空 | 0/3 | — | — |
| 第二有意志在场者 | 每章 ≥1（duty 卡 who≥2） | 0/3 | — | — |
| 对白占比 | 每章 ≥15%。**口径=引号行字数比**（一行里有「」『』“”"则整行计入），不是对白字符占全文比。由 `dialogue_floor` 硬闸执行（playbook.3.1 入链）；孤场景低对话走人工 override，override 记录进 `06-defect-ledger.md`。闸不猜「这一章该不该少说话」 | 0–8% | — | 8% / 20% / 19%（ch1 未愈） |
| 明喻密度 | ≤1 个/800 字（1/800）。已由系统闸 `simile_density` 硬拦（draft/final 落库）；本行作为协议兜底复测 | ~1/160 字 | 1/96～1/206 | 0 / 0 / 0 |
| draft 字数 | ≥2000（防压缩式伪 draft） | ch2 曾压缩 | — | — |
| 主角代词跨章一致 | 每章 `gender_pronoun` 闸零冲突（角色名±30 字窗口代词与 `state.characters[].gender` 一致率 100%） | — | ch3 翻转：他×101→她×64 | 他×97 她×0 |
| 叙事人称跨章一致 | 每章 `pov_consistency` 闸零冲突（剥对白后叙述层「我」密度与 `state.narrative_pov` 一致；ch1 确立、后续章传承）。判定不进法官 | — | ch2 翻成第一人称 | **人称 ch1 三→ch2 一→ch3 三（翻转实证）**；ch2 我×45 叙述层 |
| 关键物件位置连续 | 相邻章 `chapter_state` 对账零矛盾（同名物件 `objects[].location`/`state` 跳变须有本章新锚句） | — | 断指 ch2 末腕内 → ch3 开篇地上 | 承接链零断点 |
| 到期 open_loops 回响 | `state.open_loops` 中 `due_seq` ≤ 本章的条目不得仍挂在本章清单（回响后从清单删掉） | — | 锁扣钩子 ch2 零回响；「没有门」ch3 零交代 | — |
| chapter_state 产物存在且保真 | 每章 frozen ∧ 每条人物/物件 quote ∈ **定稿正文**（「冻稿正文」= final / `chapter.prose`，不是糙稿。机器闸 `state_quote`；定稿落库后须重校验，对不上的条用定稿原句原位替换） | 产物类型尚不存在 | 产物类型尚不存在 | 有产物；须经 `GET /chapters/{seq}/state` 直读归档 |
| 叙述装腔句 | 叙述层「不是 A 是 B」/毒句式 **<2 处**（对白不计）。闸 `syntax_tics`；1 处不拦、原句交给定稿法官。排比、短句率 **不** 硬拦 | — | — | `book_20bab124` 多处「不是明火，是碳粉」（对照，不 overlay） |

测量必须调用已上线函数（`draft_play_overlap` / `scan_anti_meta` / 契约字段 / `check_gender_pronoun` / `check_chapter_state_struct` / `check_pov_consistency` / `dialogue_ratio` / `check_syntax_tics` / `sentence_rhythm`），禁止另写一套对照实现。cost 非空是**验收尺子**，不改系统 schema（戏里没写仍可留空；play 层纪律须先写出可引用的付账场面）。节奏三个数字进证据包，**不当 C-Must 及格线**。

**语义判不进 C-Must：** 意象域一致性、新设定与前章事实矛盾——这两条是法官语义判，归 C-人评与层法官。C-Must 只收机器全量可测项。

#### C-人评（机器全绿不豁免）

三身份通读，每身份一章一票，红旗即 Wave C 不过：

- **作家**：想不想翻页（对话/对手/变化感）  
- **作家 · 连续性回读**：每章读完翻回上一章末段，核对三件事：人称代词没换、东西还在原处、上章结尾的悬念这章有着落（或明说搁置）。红旗即 Wave C 不过。性别翻转与物件瞬移在单章通读中都不显眼（章内自洽），只有回读才暴露。  
- **写模型的人**：有没有模板指纹（同位同招/比喻套路/复述痕迹）  
- **架构**：契约五字段在正文有没有落点  

「单句还行、整章不像小说」只有人读得出。「单章 8 分、拼起来不是一本书」只有回读读得出。

### Should 计分（KD-13）

\[
\text{ShouldRate} = \frac{\#\{\text{Should: PASS}\}}{\#\{\text{Should: PASS}\} + \#\{\text{Should: FAIL}\}}
\]

- **SKIP 不入分母**。  
- 总 PASS 要求 ShouldRate **≥ 0.80**。  
- **允许 SKIP 的环境条件**（须写 `skip_reason`）：

| 条件 | 可 SKIP 的示例 ID |
|------|-------------------|
| Hermes 演绎网关不可用/超时且记入 runtime-baseline | H1, H2, H3 |
| 端点 404 未部署 | H6, H9, 部分 debug |
| 非 admin 且项需 admin | SH4 |
| 本旅程未触发该故障 | Ch4（已是 Could）、Drm2 用 vacuous |
| 功能旗默认关且协议不要求打开 | H5, 硬门类 |

- Hermes/网关类 **失败 → FAIL 计入分母**（吃 20% 额度）；**仅当 baseline 声明网关不可用** 才可 SKIP（不得既声称网关正常又 SKIP）。

### 工期

| 模式 | 估计 |
|------|------|
| Wave A only（PARTIAL） | ~2–3 人日 |
| Wave A+B 总 PASS | **3–5+ 人日**（含 LLM 不稳重试） |
| 工程对照 v632 | 不计体验 PASS |

### 条件优先级语义

| 标记 | 含义 |
|------|------|
| **Must** | 总 PASS 硬门 |
| **Must-if-triggered** | 触发则硬门；**未触发 → PASS-vacuous（N/A）不挡**，须在 matrix 记 `status=N/A` + 说明 |
| **Should** | 入 ShouldRate |
| **Could** | 不入总 PASS 公式；有则记 |

---

## 全能力验证矩阵

> **证据类型：** `UI` = 必须截图/屏幕录制；`API` = 只读审计可；`UI+API` = 两者。标 **UI** 的 Must **无截图不得 PASS**。

### A. 旅程 / 建书 / 意图

| ID | 能力 | 优先级 | 阶段 | 证据 | 作者动作 | 期望 | PASS | 假绿禁令 |
|----|------|--------|------|------|----------|------|------|----------|
| J1 | 登录健康 | Must | S0 | API | 浏览器登录 | 进作品库 | `https://tonglu.qing.blue/api/health` 200 | 假 health |
| J2 | 新建真书 | Must | S1 | UI+API | 点新建 | 新 slug∈时间窗 | `01-book.md` | 旧书改名 |
| J3 | 旅程看板 | Must | S1–S13 | UI | 打开旅程 | 站位可见 | 截图 | 只 curl |
| J4 | 开书意图 | Must | S2 | UI | chat 主题/红线/2 万可见字 + who_pays/轴/书钟 | 线程有意图；GET /intent 四命运字段非空 | 非空 chat + intent 四字段 | 无 chat set_intent 脚本；只写 reader_feeling |
| J5 | 字数目标 | Must | S2–S4 | API | 规划 45k | goal∈[40k,60k] | WCG intent 项 | 混淆可见字与 goal |

### B. 正典闭环

| ID | 能力 | 优先级 | 阶段 | 证据 | 期望 | PASS | 假绿禁令 |
|----|------|--------|------|------|------|------|----------|
| C1 | 设定合法落地 | Must | S3 | UI+API | **(a) ChangePack discussion 点批 或 (b) world_write 审批落库**，可追溯 chat/种子 | Codex 有实体 | 无追溯 ops；假设只聊自动出包 |
| C2 | 待确认/收件箱点批 | Must | S3/S9 | UI | 人批 L1 | 截图点批 | 静默 L1 |
| C3 | 全类型≥4 类 | Must | S3–S9 | UI+API | 人物/规则/物件/关系/母题/承诺等 | ≥4 类 | 仅人物 |
| C4 | 中程改设定 | Must | S8 | UI+API | 聊天+批后再生效 | 与 M4 | 说说就算 |
| C5 | PostFinalize | Must | S9 | API+UI | ≥2 章候选路径 | body json | 仅 unit |
| C6 | 设定债 | Should | S4/S8 | API | debt 诚实 | 非 5xx | 假无债 |
| C7 | 收件箱 UI | Should | S3/S9 | UI | 可点批 | 截图 | API 批当 UI PASS |
| C8 | supersede 单真 | Must | S8 | API | 无双真注入 | prefetch | 双真 |

### C. 记忆（继承 6.3 · 硬门语言恢复）

#### 锚 A1–A7 → `01-memory-anchors.md`

| 锚 | 类型 | 《万界》V7.0 | 站 |
|----|------|--------------|-----|
| A1 | 专名 | 柳岸青 | 设定 |
| A2 | 物件 | 场核碎片 + 金縢之箱 | 设定 |
| A3 | 规则 | 无场核碎片不得肉身穿越融合点；大遮蔽内禁集体烛照 | 设定 |
| A4 | 关系 | 沈烛监控/护持柳岸青（合法边） | 设定 |
| A5 | 过程偏好 | 指针态/退相干/冗余；禁系统流；身体账 42°C | intent |
| A6 | 中程 | 金縢封印完整 → 箱壁裂纹 | ch2 后 |
| A7 | 限知 | 仅沈烛知场核方位；赫斯不知成核点 | 设定+POV |

| ID | 探针 | 优先级 | 阶段 | 证据 | PASS 要点 | 假绿禁令 |
|----|------|--------|------|------|-----------|----------|
| M0 | fabric | Must | S0/S6 | API | fabric true | 关 fabric |
| M1 | 跨话轮 | Must | **S6 硬门** | UI | 隔≥3 轮命中 A5 | 后台 seed |
| M2 | 正典 Codex | Must | S3 | UI+API | A1–A4 可见 | 只库有 |
| M3 | 跨章正文 | Must | **S7 ch≥3** | UI | 正文自然回指 | 作者复述锚 |
| M4 | 变更单真 | Must | S8 | API+UI | 新值+无双真 | 双真 |
| M5 | 限知 | Must | **S7 限知章** | UI | 定稿不泄 | 换 POV 逃避 |
| M6 | 定稿复用 | Must | S9→下章 | UI+API | 存+批+用 | 只存不批 |

**记忆线：** PASS ⇔ M1∧M3∧M5 且 M0–M6 中 ≥5 PASS。  
**硬门：** **未完成 M1 → 不得宣称过程记忆可用，且结案记忆线不得 PASS**（可继续写章记缺陷，但总 PASS 失败）。  
**未完成 M3 → 不得宣称跨章记忆可用。**

#### D1–D7 → `12-quality-d1-7.md`（地板；≥9 须人盲）

同 6.3.1 七维；结案 **记忆四问** 强制。

### D. 卷章 IA

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| I1 章前契约 | Must | **S5/S7 每章** | UI | 齐套 soft 截图 |
| I2 让主编种子 | Must | S5/S7 | UI | 种子后须有后续 chat/审批 |
| I3 volume_intro | Should | S4 | UI | 有或空说明诚实 |
| I4 focus | Should | S7 | API | 可观测 |
| I5 final soft banner | Should | S7 | UI | soft 不硬拦 |
| I6 结构 | Must | S4 | UI | 话术：**「三卷十章壳，本轮定稿 1–5」**；WCG 脚本绿 |

### E. 戏剧 / 契约拍 / 压力

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| Drm1 契约拍 | Must | S7 | API | contract beats ≥3 且 stages_choice 恰 1（机器硬闸）；戏/契约冻结后再演绎（与 PB3 同验） |
| Drm2 接地失败纪律 | **Must-if-triggered** | S7 | UI+日志 | **未触发 → N/A + 声明**；触发 → STOP 同路径、**禁 safe_beats** |
| Drm3 演绎分列 | Must | S7 | API | chapter_deduce 内容不得与 final prose 合并 |
| Drm4 压力 | Should | S7/S10 | API | findings 路径 |
| Drm5 戏剧真空 | Could | S7 | API | 触发即验 |

### F. 做厚（嵌 S7 + 补漏）

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| H1 parallel plan | Should | **S7 至少 1 章** | UI | plan 200 |
| H2 parallel preview | Should | **S7** | UI+API | stub∉ok_count；网关挂→SKIP+baseline |
| H3 full deduce | Could | S7 | UI | 显式 mode=deduce |
| H4 StageBoard | Should | **S5/S7** | UI | 双真源不静默盖 |
| H5 EVENT_LED | Could | S10 | API | soft only |
| H6 budget-probe | Could | S11 | API | 未部署 SKIP |
| H7 Cron 诚实 | Could | S11 | UI | timer≠开关 |
| H8 Benchmark | Could | S11 | UI | 可达 |
| H9 /debug/locks | Could | S11 | API | 未部署 SKIP |
| H10 Inspector 八块 | Should | **S6/S7** | UI | 非假 0 |
| H11 soft 非 403 | Must | S7/S11 | API | stage GET 200；parallel 非世界写 403；**禁开 EMERGENCY 绕** |

### G. QC / 台账

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| Q1 coverage | Must | S10 | UI | 诚实空态截图 |
| Q2 PRODUCT_QC | Must | S10 | API | total==sum 扩维键 |
| Q3 post-check | Must | S7/S10 | UI+API | degraded 诚实 |
| Q4 review det | Should | S10 | API | skipped 含 llm |
| Q5 degen 可见 | Should | S10 | UI | 进 issues |
| Q6 skipped chips | Should | S10 | UI | 未合入则 SKIP |
| Q7 让主编处理 | Must | S10 | UI | seed 截图 |
| Q8 faction 全书 | Could | S10 | UI | 非第 0 章 |
| Q9 日常质检入口 | Must | S7/S10 | UI | **护栏灯 + 全量体检**；左栏无「校验」日常入口。Q1 截图可从护栏空态或全量体检取 |

SSOT：`scribe3/qc_product_keys.py`。深链 `leftTab=review` 仍可达 IssueDirectory，**不**算日常入口。

### H. 限知 / knowers

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| K1 A7 叙事 | Must | S7 | UI | =M5 |
| K2 knowers API | Should | S9 | API | 可构造 |
| K3 leaks×knowers | Should | S10 | API | degraded 非丢 |
| K4 真相史 | Should | S8 | UI | 演变可读 |
| K5 命题树 | Should | S5 | UI | 滤噪 |
| K6 fact source | Should | S9 | API | 有 source |

### I. 管线 / ingest

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| P1 finalize 门 | Must | S7 | UI+API | 非无检灌 |
| P2 ingest 调度 | Must | S9 | API | status 可理解 |
| P3 lease | Should | S9 | API | capabilities 字段 |
| P4 advisory hold | Could | S7 | API | 触发即验 |
| P5 craft gate | Should | S7 | 日志 | blocking 不落 |
| P6 accept 未校验 | Could | — | 声明 | 未滥用 |

### J. 主编 / Hermes

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| Ch1 讨论流 | Must | 全程 | UI | stream 落线程；覆盖阶段 |
| Ch2 写作流 | Must | S7 | UI | prose_write 有正文 |
| Ch3 agentic-stream | Could | — | API | SPA 默认禁用；开启才验 |
| Ch4 审批过期 | Could | 触发 | API | expired≠declined（**触发即验**，不故意超时也可 N/A） |
| Ch5 能力说明 | Should | S11 | UI | Hub 模块可读 |
| Ch6 模式条 | Must | S7 | UI | 主编坞可见 聊/选择/驾驶；默认聊；切模式不换线程、对话槽仍在 |
| Ch7 选择附属 | Should | S7 至少 1 章 | UI | 模式=选择；L1 轻选或 L2 终选后草稿/lesson 可见；点选后决策收件箱该项消失 |
| Ch8 驾驶附属 | Should | S7 | UI | 模式=驾驶；推进/放行不卸对话；收件箱「在主编里打开驾驶」切到驾驶模式 |
| Ch9 作业锁 | Must-if-triggered | S7 | UI | L2/连写进行中同章发送禁用；未触发 → N/A |

**注意：** world_write 审批 **不是** Ch3；设定走 C1(b)。选择/驾驶 **不是** 第三条写章主时钟。

### K. System Hub

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| SH1 总览 | Must | S11 | UI | **≤5 分钟只读巡视**；截图总览；**禁止改 connection/gateway/emergency** |
| SH2 MCP catalog | Should | S11 | UI+API | ~94 tools |
| SH3 data health | Should | S11 | API | ok |
| SH4 RBAC | Could | S11 | API | 非 admin 403 |
| SH5 craft-skills | Could | S11 | API | 200 |

### L. 图谱 / 弧光（写章内优先）

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| G1 节点抽屉 | Should | **S7 或 S11** | UI | 可打开 |
| G2 图谱种子 | Should | S7 | UI | 后续聊 |
| G3 弧光锚 | Should | S3/S7 | UI | lie 或冷启动诚实 |
| G4 arc beat | Could | S7 | UI | 待批增删 |
| G5 pulse/brief | Should | S7 | API | 非「未见跳变=健康」 |

### M. 上下文

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| X1 Inspector | Must | S6/S7 | UI | 八块截图 |
| X2 TurnBind | Should | S3 | API | 有 bind |
| X3 prefetch | Should | M1/M4 | API | 辅助 |
| X4 pending-claims | Should | S3/S9 | UI | 可达 |

### N. 校验 hybrid（吸收 v633 F）

| ID | 旧 F | 优先级 | 阶段 | 要点 |
|----|------|--------|------|------|
| V1 | F1–2 | Must | S10 | coverage 诚实 |
| V2 | F3–4 | Should | S10 | deterministic |
| V3 | F5 | Should | S10 | degen 语义 |
| V4 | F6 | Should | S7/S10 | timeline label |
| V5 | F10 | Should | S10 | causal 三态 |
| V6 | F11 | Must | S0 | health |
| V7 | F12 | Should | S9 | lease 不 500 |

### O. 好书与规模

| ID | 优先级 | 要点 |
|----|--------|------|
| QL1 好书底线 | Must | 人读 checklist |
| QL2 字数带 | Must | [18k,24k] |
| QL3 无 pad | Must | 人判 |
| QL4 人盲 | Could | 不挡总 PASS |

### P. play-contract 五层 / 注入 / 设定生成 / 飞行记录仪（rev.13）

| ID | 优先级 | 阶段 | 证据 | 要点 |
|----|--------|------|------|------|
| PB1 duty 法官+咬钩 | Must | S7 每章 | API | duty_card 冻结；ch≥2 `duty_bite` 过闸 |
| PB2 quote 保真 | Must | S7 | API | contract 全部 quote `quote_in_play` 通过 |
| PB3 抉择唯一 | Must | S7 | API | `stages_choice=true` 恰 1 场（纯函数结构闸） |
| PB4 层序 409 | Must-if-triggered | S7 | API | 未冻结下层请求 → 409 `stage_not_ready`；触发即验 |
| PB5 四态/needs_human | Should | S7 | API | 冻结四态可见；三抽不过 → needs_human 不毁 Play |
| PB6 extra_authors | Must-if-triggered | S7 | API | 命令语气 extra → 422 `extra_authors` |
| PB7 deduce≠prose | Must | S7 | API | chapter_deduce 与 final prose 不合并 |
| PB8 法官留痕 | Should | S7 ≥1 章 | API | 飞行记录仪可见法官结论（T=0、先引原文再判） |
| Ice7 落库与余烬 | Must | S7 每新定稿章 | API | `persist=true`；`GET /latest-draft` 非空；定稿后 `narrative_drive.end_hook` 非空；每层带 focalizer。违反 = 该章 FAIL（即使 HTTP 200） |
| Af1 注入可回放 | Should | S7 ≥1 章 | API | 飞行记录仪能打开进模型段 / drop 段；禁止只报 digest |
| Cx1 设定生成不落库 | Must | S3 | API | `/generate-codex` 200 且 L1 未因本次生成新增实体；落地仍 C1 |
| Cx2 secret 边界 | Must | S3 | API | REST `include_secret` → 4xx |
| Rec1 运行分析入口 | Must | S7/S11 | UI | **运行时·数据** 可见本书链；非运维·危险 |
| Rec2 卷宗正文 | Should | S7 ≥1 章 | API | `GET /debug/pipeline-traces/{id}?include=events,artifacts` 有真实工件；单链须返回非空 `item` |
| Rec3 traces×冻结对账 | Must | S7 每章 | API | 证据 `07-trace-reconciliation.md`：每层 trace 状态 × 冻结产物 × 法官 verdict；不一致 → Wave A 不过 |
| Ice8 latest-draft 同源 | Must | S7 每章 | API | `GET /latest-draft?work=&seq=` 的 `source` ∈ {`chapter_version`,`chapter_draft`}；**三章同一条路径**；混路径视为 B2 窗口冻结被违反 |
| Inb1 选择进收件箱 | Should | S7 若跑选择 | UI+API | pending L1/L2 在决策收件箱 |
| Inb2 Hermes 进收件箱 | Should | S3 若有审批卡 | UI | hermes_approval 项可见 |
| D1 draft 抄戏 | Must | S7 | API | 故意提交与 play 重复率 >15% 的 draft → `check_draft_struct` 挡，code=`draft_copy_play` |
| D2 章边界词 | Must | S7 | API | 正文写「上一章他……」→ M8 挡稿（非 advisory） |
| D3 法官畸形 | Must | S7 | API | 畸形 verdict 且无 evidence → 归一化为 `needs_human`，冻结挂起 |
| D4 单人责任卡 | Should | S7 | API | duty `who` 只填焦点者 → 法官第 6 问 fail（不改 schema 必填人数） |
| D5 戏无对手/账 | Should | S7 | API | play 通篇无第二人交互 → play 法官拦；戏里有账而 contract.cost 空 → contract_judge 第 3 问 fail |
| D6 定稿须有契约 | Must | S7 | API | 无冻结 `chapter_contract` 的 final 必被挡（`no_chapter_contract`）；empty_drama_contract 跳过已死 |
| D7 playbook.3.2 | Must | S0 | API | `/health` 或代码断言 `playbook_version = playbook.3.2` |
| D8 Gate 0 归档 | Must | S0 | 文件 | `00-smoke-result.md` 进证据包；冒烟书 slug 保留不删，证据包须能打开 |
| D9 代词翻转 | Must | S7 | API | 前章 state 记「男」，本章正文该角色窗口内出现「她」多于「他」→ `gender_pronoun` 闸拦 |
| D10 状态造假 | Must | S7 | API | 提交带虚构 quote（不在冻稿正文）的 chapter_state → `state_quote` 保真闸拦 |
| D11 悬念超期 | Should | S7 | API | open_loop `due_seq` 到期未回响（仍挂在本章 open_loops）→ play 法官 fail 或 run-card 警告 |
| D12 意象域断裂 | Should | S7 | API | duty 的意象域与 `intent.imagery` 冲突且无桥接意象 → duty 法官 fail |
| D13 人称翻转 | Must | S7 | API | 前章 state 记 `third`，本章 draft 叙述层「我」≥10 且 >他÷3 → `pov_consistency` 闸拦，fail 原因含 `pov` |
| D14 删像残渣 | Must | S7 | API | draft 含残渣模式（`不似乎`/`，又[烧冻碎压]`/三连叠字）→ 清洗后校验拦，该句回退局部重写，禁止机械删直接落库 |
| D15 叙述装腔 | Must | S7 | API | 定稿叙述层两处及以上「不是 A 是 B」或毒句式 → `syntax_tics` 硬拦；糙稿只点名原句不硬拦；对白里同样句式不拦；一处不拦。定稿冻住后 `craft_diagnostic` 记下短句率/长句率/连击段数，`blocking=False` |

---

## 中程变更与设定债

1. A6：讨论 → 合法落地 (a|b) → **人批** → supersede **state** → 下章。  
2. 禁双真 condition。  
3. 债：debt API/旅程可观察。  
4. 绑定 M4/D4。

---

## 证据包结构

```text
docs/evidence/v634-true-chat-<YYYYMMDD>-<slug>/
  或 artifacts/e2e-journey-v634-true-chat-<YYYYMMDD>-<slug>/
```

### 必填

| 文件 | 谁写 | 说明 |
|------|------|------|
| `00-runtime-baseline.md` | 执行者 | **完整 URL 样例见下** |
| `00-env-lockdown.md` | 执行者 | fabric/emergency/网关可用性 |
| `00-author-path.md` | 作者 | 硬门 |
| `00-stop-log.md` | 遇障 | STOP |
| `00-world-complete-gate.json` | **gate 脚本输出** | pass=true |
| `01-book.md` | 执行者 | slug+**created 时间** |
| `01-memory-anchors.md` | 作者 | A1–A7 |
| `01-intent.md` | 摘录 | |
| **`02-feature-matrix.json`** | 执行者 | **见 schema** |
| `03-structure.md` | 摘录 | 3 卷 10 章 |
| `04-serialize/ch01…ch05.md` | 导出 | |
| `05-ledger.md` | 结案 | 十线+分波 |
| `06-defect-ledger.md` | 全程 | |
| `00-smoke-result.md` | Gate 0 | live 冒烟输出；不过则不许开跑。须含冒烟书 slug（保留不删）与 chapter_state 全文；路径须可访问 |
| `07-trace-reconciliation.md` | 每章 | 每层：trace 状态 × 冻结产物 × 法官 verdict（流程对账） |
| `08-wordcount-rollup.md` | 结案 | |
| `08-chapter-states.md` | 执行者 | 三章 state 产物全文归档（含 quote 锚句）——连续性的审计依据。**state 须经 API 端点直读（GET /chapters/{seq}/state）归档，禁止 DB 直查替代——端点缺失本身即验收阻断项（观测面完整性进验收）** |
| `09-state-reconciliation.md` | 执行者 | 相邻章 state 对账表（每对相邻章一节：characters/objects/open_loops 逐项 一致/变化/新增/关闭）——事实对账，与 B3 traces 对账表同构 |
| `09-final-closure.md` | 结案 | 四问+总裁决 |
| `11-canon-loop-chat.json` | 审计 | |
| `11-canon-loop-body-ch*.json` | 审计 | |
| `12-memory-*` / scorecard / d1-7 | 探针 | |
| `13-capability-audit/` | 摘录 | issues/post-check/hub… |
| `screenshots/` | 作者 | **最低集见下** |
| `99-summary.md` | 结案 | |

### `00-runtime-baseline.md` 强制样例字段

```markdown
# runtime baseline
- entry: https://tonglu.qing.blue
- GET https://tonglu.qing.blue/api/health → { ... 贴关键字段 ok/status ... }
- GET https://tonglu.qing.blue/api/ready → ...
- GET https://tonglu.qing.blue/api/capabilities → flags.memory_fabric_v1,
  flags.emergency_rest_write, flags.ingest_lease, flags.context_inspector_v1, ...
- demo env / 设置：SCRIBE3_PIPELINE_TRACE=1；SCRIBE3_PIPELINE_RECORDER=1（记录仪默认开）
- Hermes deduce preview/full 可达性：ok / degraded / unavailable（影响 H* SKIP）
- 证据窗起止 UTC
- deploy 备注（hot 时间可选）
```

### 截图最低集（与 Must 绑定）

| 截图 | 绑定 |
|------|------|
| 旅程站位 | J3 |
| 新建书/书名 | J2 |
| 每章开写气泡（1–5） | 主编硬门 |
| 每章 UI 点批（1–5） | 主编硬门 |
| 收件箱或审批卡点批 | C1/C2 |
| 章前契约至少 1 章 | I1 |
| 章工作台 play/contract 页 | PB2 |
| Issue coverage | Q1 |
| Context Inspector | X1 |
| SystemHub 总览 | SH1 |
| M1 追问回复 | M1 |
| 主编模式条（聊/选择/驾驶） | Ch6 |
| 运行分析卷宗（一书） | Rec1 |

### `02-feature-matrix.json` schema（PR-Doc-3 / PR-Script-0）

```json
{
  "version": "v6.3.4",
  "slug": "book_xxx",
  "wave": "A|B|all",
  "items": [
    {
      "id": "M1",
      "priority": "Must",
      "status": "PASS|FAIL|SKIP|N/A",
      "evidence_type": "UI|API|UI+API",
      "evidence_path": ["screenshots/m1.png", "12-memory-m1.md"],
      "skip_reason": "",
      "notes": ""
    }
  ],
  "should_rate": 0.0,
  "must_failed": [],
  "author_human": true
}
```

**checklist 脚本最低校验（内容级，非仅存在）：**

- 每个 Must：`status` ∈ {PASS, N/A}（N/A 仅 Must-if 且未触发）；无 FAIL；`evidence_path` 非空。  
- `author_human === true` 与 `00-author-path` 含「真人=是」。  
- `08-wordcount` 合计 ∈ [18000,24000]。  
- WCG json `pass===true`。  
- 空文件 / 空 status → 脚本非 0。

---

## 与工程脚本边界

| 工具 | 允许 | 体验 PASS | 推荐 |
|------|------|-----------|------|
| 浏览器对话+白名单 UI | 写书 | **唯一总 PASS** | 主路径 |
| 只读 curl / WCG 脚本 | 证据 | 否 | 鼓励 |
| v632 | 对照 | **否** | engineering PARTIAL |
| v633 / v63_memory | 回归 | **否** | 禁止总 PASS |
| pilot 在开写 chat 后 | 辅助 | **无每章 UI 点批截图 → PARTIAL** | 慎用 |
| serial / 灌库 / EMERGENCY | — | 否 | 禁止 |

---

## 人评 / 人盲

| 层 | 强制 | 关系 |
|----|------|------|
| 路径诚实+UI 截图 | 总 PASS | author-path |
| 好书底线 | 总 PASS | closure |
| Wave C 三身份通读 | 总 PASS | C-人评：作家 / 写模型的人 / 架构；红旗即 Wave C 不过；机器全绿不豁免 |
| 记忆四问 | 记忆 PASS | |
| 人盲 ≥9.5 | 仅质量冲刺 | 不挡本版总 PASS |

---

## 失败与回滚纪律

同 6.2：STOP → 真路径修 → 同路径回归。Must 红阻塞总 PASS。禁止改旧证据造绿。

---

## Alternatives Considered

### Alt-1 全 API 自动化（v633 极端）

可重复但假绿；**否决为总 PASS**。

### Alt-2 全人手无清单

不可审计；**否决**。

### Alt-3 Hybrid 一次跑满（本版主方案）

真人 SPA + 矩阵 + 只读证据；工期 **3–5+ 人日**；分波见 Alt-5。

### Alt-4 五万字再叠全能力

成本高边际低；**不作为门禁**。

### Alt-5 分波：Wave A Must 旅程 + Wave B Should 附录（**采纳为执行策略**）

| | 说明 |
|--|------|
| **做法** | Wave A 先出 PARTIAL（Must+记忆+WCG+5 章）；Wave B 补 Should≥80% 与 Hub/parallel 等 |
| **利** | 可执行；避免一天内假绿跳项 |
| **弊** | 总 PASS 变慢 |
| **与「一次总 PASS 才算数」** | **产品结案仍要求 A∧B∧C**；分波是 **执行节奏**，不是三个独立「总 PASS」。禁止只交付 Wave A 对外宣传总 PASS |
| **否决「永久只做 Wave A」** | 会退化回能力不触达 |

---

## Security & Privacy

密钥不进证据包；Hub 只读；emergency 关；限知审计脱敏；一书一库。

---

## Observability

threads、capabilities、ingest/lease、coverage、tool_trace_status、Inspector、字数。

**rev.3 飞行记录仪：** `GET /debug/pipeline-traces?work=<slug>&chapter=N` 列链；单链 `GET /debug/pipeline-traces/{id}?include=events,artifacts` 须返回非空 `item`，打开事件流与工件正文。作者 UI：运行时·数据 → 运行分析。分析质量时必须读阶段文 **和** 卷宗，禁止只数 `ok`。

**rev.13 对账表：** 每章每层一行：trace 状态 × 冻结产物存在性 × 法官 verdict。两者不一致即 Wave A 不通过（不管产物在不在）。归档 `07-trace-reconciliation.md`。

---

## Rollout Plan

1. 审定 → `docs/e2e-director-journey-v634-true-chat-full-capability.md`  
2. PR-Doc-2 指针（模板见下）+ **SESSION「主验收协议」= v6.3.4** + docs/README 挂链  
3. 证据模板 + matrix schema  
4. 可选 checklist 脚本（内容校验）  
5. demo 开跑 Wave A → B → 结案  
6. 缺陷回流产品 PR  

### PR-Doc-2 文首标准指针（5 行模板）

```markdown
> **总 PASS 协议（现行）**：[v6.3.4 真书·对话驱动·全能力](./e2e-director-journey-v634-true-chat-full-capability.md)  
> 本文档降为：**记忆子集 / 纪律附录**，单独跑完 **不得** 宣称铜炉 v6.3.4 总 PASS。  
> WCG SSOT：`scripts/v4_world_complete_gate.py`  
> 体验路径：SPA 对话 + 点批/工作台；禁止脚本灌章冒充。  
> 工程对照：`scripts/v632_true_chat_journey.py` ≠ SPA PASS。
```

适用于：`e2e-director-journey-2w-memory.md`、`e2e-director-journey-5w.md`（规模附录说明）、`plans/2026-08-10-v633-revalidation-quality-delta.md`。

---

## Risks

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| 按旧「1 卷」做 S4 | 高 | WCG 脚本 SSOT 表 |
| 只 discuss 不 world_write | 高 | §SPA 通道 + C1(a\|b) |
| 工期低估跳 Should | 高 | 3–5+ 日；分波；Should 计分 |
| 一句开写+全 auto pilot | 高 | 每章 UI 点批截图 |
| 人盲/9.5 误宣传 | 高 | Non-Goals |
| 矩阵空文件 | 中 | schema 内容校验 |

---

## Open Questions

| ID | 问题 | rev.2 状态 |
|----|------|------------|
| OQ1 宇宙 | 沿锚 vs 新 | **闭合 → KD-15 默认《万界》V7.0** |
| OQ2 字数 | 18–24k？ | **闭合：是** |
| OQ3 点批 UI | 路径内？ | **闭合：是 + 白名单** |
| OQ4 agentic | | **闭合：agentic-stream=Could；world_write=设定主路径** |
| OQ5 无真人 | | **闭合：不得总 PASS** |
| OQ6 SH1 Must | | **闭合：Must 但 ≤5min 只读** |
| OQ7 并行故障 | | **闭合 → KD-13** |
| OQ8 对外 v6.4 名 | 可选宣传 | 仓库仍 v6.3.4 |
| OQ9 08-14 能力 | 矩阵是否吸收 | **闭合 → KD-20…24** |

---

## Key Decisions

| ID | 决策 | 理由 |
|----|------|------|
| KD-1 | 版本 v6.3.4 | 6.3 家族修订 |
| KD-2 | 体验总 PASS = 真书 + 对话驱动 + 白名单 UI 裁决 | 北极星；非禁止工作台 |
| KD-3 | 可见字 ~2 万 / 定稿 5 章；结构壳满足 WCG | 能力可负担 |
| KD-4 | Must/Should/Could + 分波 A/B | 可执行 |
| KD-5 | 只读 API 仅证据 | 防代聊 |
| KD-6 | 不宣称人盲 9.5 | to-9.5 |
| KD-7 | v632 非主执行器 | SPA |
| KD-8 | demo only | 资源规则 |
| KD-9 | 点批/审批卡/工作台 ∈ 路径；表单改正典 ∉ | 对话驱动 |
| KD-10 | 遇障同路 | 6.2 |
| KD-11 | MCP 不穷尽调用 | 作者不可见 |
| KD-12 | 无 author-path/截图硬门 → 不得总 PASS | 可拆穿 |
| **KD-13** | ShouldRate=PASS/(PASS+FAIL)，SKIP 不入分母；网关类按 baseline SKIP 或 FAIL | Issue 3/7/OQ7 |
| **KD-14** | **WCG SSOT = `scripts/v4_world_complete_gate.py`**；协议不私自降级 | Issue 1 |
| **KD-15** | 默认《万界概率战争》V7.0 锚；炉灰记退役；另换宇宙须重写 A1–A7 与 `docs/worlds/` | OQ1 |
| **KD-16** | 每章开写 user message + 每章 UI 点批截图为主编硬门 | Issue 6/7 |
| **KD-17** | 条件 Must → Must-if-triggered / N/A | Issue 5 |
| **KD-18** | S7 内嵌 IA/Stage/parallel/弧光；S11 补漏 | Issue 4 |
| **KD-19** | 合法设定落地 = ChangePack **或** world_write 审批（可追溯） | Issue 2 |
| **KD-20** | 写章 S7 质量门 = PB1–PB8（duty 咬钩、quote 保真、抉择唯一、层序 409、四态、extra_authors、演绎≠正文、法官留痕）；生成必须 LLM；不改宣称 | 08-19 play-contract |
| **KD-21** | 防洪水是注入层，不是生成链；验收看记录仪工件 | 08-14 antiflood |
| **KD-22** | 设定库 generate 只生成不落 L1；secret fail-closed | 08-14 codex chain |
| **KD-23** | 选择/驾驶 = 主编附属模式；REST 语义不变；切模式不换会话 | 08-14 chief fusion |
| **KD-24** | 左栏「校验」非日常入口；日常 = 护栏 + 全量体检；决策收件箱含选择+Hermes | 08-14 inbox / rail |
| **KD-25** | 写章 OpSeq = duty→design→deduce→draft→final，每层生成→法官→结构闸→冻结，persist=true；层序 409；旧 stage 410 | 08-19 play-contract |
| **KD-26** | 保真唯一机制 = Contract quote 字面包含（`quote_in_play`）；语义判断只由法官做；词匹配硬闸（密度/fate/水面）全部退役 | 08-19 play-contract |

---

## PR Plan

| PR | 内容 |
|----|------|
| **PR-Doc-1** | 本文 → `docs/e2e-director-journey-v634-true-chat-full-capability.md` |
| **PR-Doc-2** | 旧文文首 5 行指针；**SESSION 主验收协议=v6.3.4**；docs/README 挂链；6.3.2=记忆附录 |
| **PR-Doc-3** | `docs/evidence/v634-true-chat-TEMPLATE/`：matrix 预填全部 ID、author-path、runtime-baseline |
| **PR-Script-0** | `scripts/v634_evidence_checklist.py`：schema/Must/字数/WCG/真人字段；**不写书** |
| **PR-Prod-*** | 旅程暴露 Must 缺口再开 |

---

## 捷径黑名单（继承 + 追加）

继承 v5 ban 与 6.3 §11，并追加：

- [ ] v633 证据或旧 slug 冒充 v6.3.4 总 PASS  
- [ ] 矩阵绿无正文/无线程/无每章开写 id  
- [ ] Must(UI) 只 curl 无截图  
- [ ] 一句开写 + 全 auto pilot 无点批截图  
- [ ] 关 fabric / coverage 刷绿  
- [ ] stub 计入 ok_count  
- [ ] 开 EMERGENCY 再关毁迹  
- [ ] 旧书改名进时间窗作假  
- [ ] 只 Wave A 宣传总 PASS  
- [ ] 协议写 1 卷绕过 WCG 脚本  
- [ ] 续写炉灰记 / `book_bdfdcdc4` / `wanjie-fate-r7` / `book_e415dfeb` / `book_61a7935e` / 灰七香债冒充本版总 PASS  


---

## 执行清单（监考）

```text
Wave A
□ S0  health + capabilities 贴 baseline（完整 URL）
□ S1  新书时间窗
□ S2  意图 + A5 + who_pays / axis_terms / clock_start / clock_end
□ S3  设定：world_write 审批和/或 ChangePack；母题≥3；承诺≥3；≥4 丰满角色；收件箱点批
□ S4  三卷十章壳 + WCG 脚本 exit 0
□ S5  契约页截图
□ S6  M0+M1 硬门
□ S7  五章：每章开写 chat id + UI 点批截图
      内嵌：契约/StageBoard/可选 parallel/Inspector/弧光或图谱
      ch≥3 M3；限知章 M5；禁 safe_beats
□ S8  M4 单真
□ S9  PostFinalize≥2 + M6 + ingest
□ S10 Q1–Q3 Q7 Q9 V1（护栏/全量体检，非左栏校验 tab）
□ S7 PB1-3 + PB7 + latest-draft 非空 + end_hook 非空；≥1 章打开 Rec2 卷宗做质量分析（非仅有输出）
□ Ch6 模式条可见；若用选择/驾驶则 Inb1/Ch7/Ch8
□ 记忆 scorecard + 四问草稿
□ 字数带检查

Wave B
□ Should 补齐（H* G* 等）至 rate≥80%
□ S11 SH1 ≤5min + 补漏
□ 02-feature-matrix.json schema 合法
□ checklist 脚本绿
□ 09 结案总 PASS 公式
```

---

## References

- `scripts/v4_world_complete_gate.py` — **WCG SSOT**  
- `docs/e2e-director-journey-5w.md` · `docs/e2e-director-journey-2w-memory.md`  
- `docs/plans/2026-08-10-v633-revalidation-quality-delta.md`  
- `docs/e2e-journey-5w-v5-shortcut-ban.md`  
- `docs/plans/2026-08-09-memory-quality-to-9.5-system-design.md`  
- `docs/plans/human-blind-memory-quality-protocol.md`  
- `docs/plans/2026-08-10-verification-capability-audit-and-llm-first-optimization.md`  
- `docs/plans/2026-08-11-tonglu-complete-wiring.md` · `docs/plans/2026-08-11-thicken-residual-optimal.md`  
- `docs/CURRENT_ARCHITECTURE.md` · `docs/SESSION.md`  
- `docs/guides/2026-08-11-writing-context-injection-and-data-generation-full-flow.md`  
- `scribe3/web/src/ChiefDock.jsx` · `lib/orchestrateSend.js` · `lib/chiefMode.js` · `system/SystemHub.jsx` · `ChapterMetaPane.jsx`  
- `scribe3/mcp_catalog_build.py` · `qc_product_keys.py` · `ingest_lease.py` · `arc_signals.py` · `parallel_deduce.py`  
- `scribe3/web/src/DeduceStage.jsx`（存在，533 行）  
- `scribe3/stage_generate.py` — 约 206 行 facade（旧 outline/beats 链已删）  
- `scribe3/playbook/` — `stages.py` / `pipeline.py` / `structural.py` / `quote.py` / `judge.py` / `prompts.py`  
- `scribe3/migrations/146_play_contract.surql` · `147_drop_old_design.surql`  
- `docs/playbook/playbook.1.md`  
- `scribe3/codex_generate.py` · `pipeline_recorder.py` · `inbox.py`  
- `docs/plans/2026-08-14-antiflood-blast-radius.md` · `2026-08-14-codex-generation-chain.md` · `2026-08-14-pipeline-runtime-analysis.md` · `2026-08-14-chief-mode-fusion.md`  
- `docs/worlds/wanjie-probability-war-v7.md` — **验收宇宙 SSOT**  
- `scripts/v632_true_chat_journey.py` · `scripts/v633_change_revalidation.py`  

---

## Revision Summary（设计文档）

| 版本 | 说明 |
|------|------|
| v6.3.4 Draft rev.1 | 首版全能力矩阵 |
| **v6.3.4 Draft rev.2** | 审查修订：WCG SSOT 全表；SPA 三通道与 C1(a\|b)；Should 计分/分波/工期；S7 内嵌能力；Must-if；每章开写+UI 点批硬门；证据 schema；KD-13…19；Alt-5；路径白名单表述；指针模板 |
| **v6.3.4 Draft rev.3** | 吸收 2026-08-14 已上线能力：冰山地板 Ice1–6、防洪水 Af1、设定生成 Cx1–2、飞行记录仪 Rec1–2、主编模式条 Ch6–9、收件箱 Inb1–2、Q9 校验不再日常入口。SPA 三通道与 WCG 脚本不变。质量分析须读阶段文+卷宗。KD-20…24。 |
| **v6.3.4 Draft rev.4** | 吸收 08-14～08-15 写章实跑：F1–F11（草稿读路径、节拍框、persist/focalizer/hook、四仪/drama、usage、recall 回退）。钉 OpSeq 与 Ice7。KD-25。**不**另开总 PASS，**不**改 SPA / WCG / 宣称。 |
| **v6.3.4 Draft rev.5** | 章纲 13 槽 + 线索密度闸；当时验收书 `book_bdfdcdc4`（rev.6 退役）。 |
| **v6.3.4 Draft rev.6** | 写作素材换锚《万界概率战争》V7.0：书名、A1–A7、三卷十章壳、第 1 章 13 槽金样、证据模板、宇宙 SSOT。**不改** SPA / WCG / 宣称 / OpSeq / 密度闸数字。新 slug；禁续写炉灰记冒充本版总 PASS。 |
| **v6.3.4 Draft rev.7** | 吸收 fate-dearer：Ice3/4/6 字数 Must 改为结构 Should（旗 on 才 Must）；S2/OpSeq 写入 who_pays、书钟、章钟/地点；卡住与冻钟/冻地。**不改** WCG 数字、SPA、宣称、GATE-B、`GATE_SAVE_MODE`。黑名单加 `wanjie-fate-r7`。 |
| **v6.3.4 Draft rev.8** | 词表 `WORLD_*`、`cast_role_frozen`、`world_fact_*`、extra=`evaluate_write_contract`、默认 WAVE-2。当时验收书 `book_61a7935e`（rev.9 退役）。 |
| **v6.3.4 Draft rev.9** | `goal_off_world` + 【世界合同】压 extra；记录仪默认开；F3b/c 标历史。新 slug。禁 overlay 旧万界书。**不改** SPA / WCG / 宣称 / GATE-B / `GATE_SAVE_MODE`。 |
| **v6.3.4 Draft rev.10** | 三章水面验收条（史）。词匹配硬闸现已退役。 |
| **v6.3.4 Draft rev.11** | 当时 OpSeq 合并为 design 一层（史）。旗与旧 design 语义已不存在。 |
| **v6.3.4 Draft rev.12** | 写章内核换代 play-contract：新五层 OpSeq、PB 矩阵、quote 保真、咬钩硬闸。Fate/水面/outline/beats 条款作废。总 PASS / WCG / SPA 不改。 |
| **v6.3.4 Draft rev.12.1** | 漏改收口：Drm1、第 1 章契约金样、万界宇宙字段、白名单/记录仪措辞。 |
| **v6.3.4 Draft rev.13** | Gate 0 冒烟；窗口版本冻结；traces×冻结对账；Wave C 产物质量进总 PASS；playbook.2 对抗 D1–D8。WCG / SPA / ShouldRate 0.80 不改。 |
| **v6.3.4 Draft rev.13.1** | 跨章连续性：`chapter_state` 验收锚；C-Must 四行；C-人评连续性回读；D9–D12；Gate 0 三闸对抗；证据 08/09 状态对账；playbook.3。**不改** rev.13 已有阈值、WCG、SPA、ShouldRate 0.80。 |
| **v6.3.4 Draft rev.13.2** | 人称一致：state.narrative_pov、pov_consistency 闸、C-Must 人称行、D13；删像残渣校验 D14；state/duty 读端点对账；窗口硬冻结 tag；对白闸入链+override 留痕；playbook.3.1。**不改** rev.13/13.1 已有阈值、WCG、SPA、ShouldRate 0.80。不追溯修旧书人称。 |
| **v6.3.4 Draft rev.13.3** | 保真精修：冻稿正文=定稿；对白口径=引号行字数比；state 锚句 final 后校正；契约 quote 禁编辑；run-card fail_reasons；冒烟书 slug 保留。**不改** 已有阈值、WCG、SPA、ShouldRate 0.80。 |
| **v6.3.4 Draft rev.13.4** | 句子层：`syntax_tics`、节奏记账进证据、定稿法官念开头+在使劲、playbook.3.2。**不改** 1/800、对白 15%、重复率 15%、WCG、SPA、ShouldRate 0.80。不 overlay `book_20bab124`。 |
| **v6.3.4 Draft rev.13.4.1** | 糙稿提示合写「写够 / 别搬戏」；装腔硬拦只留定稿；卡住卡片写出原因。验收 `book_8777aad8` 第一章。**不改** 门槛数字。不 overlay `book_20bab124`。 |

---

*完 · rev.13.4.1。宇宙 SSOT：`docs/worlds/wanjie-probability-war-v7.md`。写章 SSOT：`scribe3/playbook/`（playbook.3.2）。旧验收书 slug 不 overlay。*
