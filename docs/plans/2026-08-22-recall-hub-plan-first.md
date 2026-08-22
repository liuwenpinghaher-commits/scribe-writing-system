# 铜炉：先把该看见的找齐，草稿前先把账立住

| 项 | 值 |
|----|-----|
| **日期** | 2026-08-22 |
| **状态** | Draft · 审查改进稿（相对 Qoder「改造方案 v2」） |
| **取代** | 不覆盖 v1 笔记；**不取代** `docs/plans/2026-08-22-volume-scale-discipline.md`（体量纪律仍是写章主干）。本文管两件事：召回怎么统一、规划怎么先行。 |
| **输入** | Qoder「铜炉最强化改造方案 v2」；Noah 五设施审计结论；Mia 规划先行裁决；体量纪律 rev.3 |
| **不改** | 明喻 1/800、对白 15%、重合 15%；不 pad；不 curl `s3_add_*`；不对已部署万界书 force 重立责任 / overlay 卷纲 |

---

## 给作者看的人话

系统里其实有五座桥：设定卡片、事实图谱、语义相近、关键词、以及「这个人此刻知不知道」。修好了，但写章时各走各的。最忙的那条——把设定塞进写章嘱咐——还在用「标题里有没有这几个字」，不够就按字母序凑几条。所以同一条设定，对话路径看得见、写章路径可能看不见。

规划先行不是先写三百章剧本。先立的是**账**：全书要办哪些事、每卷一笔闭环、每章一句话谁在哪办成什么。戏和节拍按卷再铺。演绎、草稿仍一章一章写，因为它们咬着上一章的末态。

和已经定的体量纪律不打架：一卷仍是好几笔账，不是一章放大；写今晚看得见后面还没办的；后面可以挂着，不许今晚演完。细到场面的细纲仍然一卷一卷来，不许一次吐完全书节拍。

怎样算做完：

1. 同一条设定，写章路径和对话路径找回来的是同一批实体（预算裁完顺序仍一致）。
2. 新书能在系统里走完：设定与总纲 → 各卷纲 → 各章一句话账 → 进卷再铺戏；每步有人批。
3. 旗全关时，旧书行为与现在一致。万界已冻的第 1 章责任不重写。

---

## Overview

v2 的三点质问成立：①设施在、写路径没用满；②决定/召回/消费各灶；③规划被做成滚动辅助，不是草稿前先立账。

本改进稿**采纳**统一召回中枢与「账目全建、剧本按卷」。**收紧**三处，避免再把一卷收成一章、或用完成度格子挡写作：

1. 设定进检索只走「摘要命题化」，不给实体表另建一套向量（限知门不能裂）。
2. 规划先行的「全书」停在**一句话章账**；duty/play 仍按卷批跑，演绎草稿仍逐章。
3. 体量纪律 PR-1～4 先绿；召回影子可并行；规划批跑端点排在其后。完成度门只报告不 422。

---

## Background（对照现网，不是复述 Noah）

`scribe3/playbook/context.py` `playbook_codex_recall`（约 405–468 行）：`facts_at` 后用标题/焦点者子串匹配；命中不足 2 条则 **字母序取前 4 条凑数**；截断 `_CODEX_BUDGET = 800`。这不是「没有向量」，是写章设定槽没用向量。

`scribe3/codex_secret_bridge.py` 只镜像势力秘密字段。角色等其余类秘密进不了 `knows` 门，召回统一后会漏或误亮——所以通用 secret 桥必须和摘要命题化一起上。

`MemoryRetriever`（`memory_retrieval.py`）四通道只辖 `memory_item`。playbook `build_ctx` 的八个 guide 槽里没有记忆通道。同一本书的经验，对话开 envelope 全有、关 envelope 只剩 craft_rules、写章路径全无。

体量纪律文档已裁：写章主干仍是 `generate-stage → thicken_stage → run_stage`；缺的是邻章账。v2 不应再把 playbook 降级成可选。

---

## Goals & Non-Goals

**Goals**

- 一条 `RecallService.recall(...)` 出口，写章设定槽与对话设定段走同一底座、同一限知/时态门。
- 影子期并行计算、不改输出；差异稳定后再按旗翻主；原函数体保留降级。
- 草稿前可在系统内完成：设定+总纲 → 卷纲 → 章账（一句话）→ 进卷 duty→design。人批落库。
- 章 `outline_status=stale` 时挡住 deduce/draft（人话：纲改过还没核对）；duty/design 放行。缺字段的旧书不拦。

**Non-Goals**

- 实体表直加 embedding（第二套向量）。
- 一次生成全书节拍/duty/play/deduce/draft。
- 前置演绎、全书零稿流。
- 完成度 16 字段 / 实体数量基线当 422。
- 机器 422 挡人工卷纲。
- 改 1/800、对白 15%、重合 15%。
- 对已部署万界书 force 重立责任、overlay 卷纲、用 `persist=false` 冒充只读试跑 generate-stage。
- RecallService 接管 north_star / chapter_duty 等主键直取槽。

---

## Proposed Design

### 1. 统一召回（回应①②）

**D-R1（维持 v2）**：设定检索底座 = 实体摘要同步为 `proposition`（`attribute="codex_digest"`），一实体可多条（总摘 + 字段簇），`source_entity` + `field_group` 回指。定位实体后，渲染仍回源卡片、走三档门控。否决实体表自建 HNSW。

**RecallService**（`scribe3/recall_service.py`，按 work 隔离）：

```
recall(work, chapter, focalizer, intent, query, budget_tag) -> RecallPack
```

六段：结构直取（不参与抢预算）→ 语义 → BM25 → 图（含补建的人物/实体关系 ≤2 跳）→ 时态+限知 fail-closed → RRF + 预算档 + 溯源。

**接管**：playbook `codex_recall`；对话 `_codex_segments`（点名保底 + 语义并入，**不绕 iceberg 门**）；canonical 块**只改排序不改来源**；memory/material/lesson 对外只出 RecallService。

**不换**：其余 7 个 playbook guide 槽；brief/voice 等直查（本期）。

**删凑数**：`playbook_codex_recall` 字母序前 4 条在翻主后删除；命中空则如实空并打 skip 原因，禁止静默 `or "（无）"`。

**预算**：扩展 `context_budget.py` 登记档名。写章设定槽增量建议 ≤ +400 字/章，避免语义召回把嘱咐撑爆。对话档仍可更大，但**实体集合与裁剪顺序**与写章槽对照验收（R7）。

**影子**：`SCRIBE3_RECALL_SHADOW=1` 时并行算、只记 diff、输出不变。连续差异率低且抽查无劣化，再逐旗翻主。

### 2. 规划先行（回应③）——全建的是账，不是剧本

| 层 | 何时全建 | 落点 | 体量 |
|----|----------|------|------|
| 设定 | 草稿前 | 现有设定库 + thicken | 报告缺口，不 422 |
| 总纲 | 草稿前 | 现有 intent | 方向+红线 |
| 卷纲 | 草稿前 | `volume.intro` | **该卷每一章各办哪一件**，禁止一章一夜冒充一卷 |
| 章账 | 草稿前，**按卷** | `chapter.synopsis` 30–80 字：谁、在哪、办成什么、付什么 | 可把各卷跑完，但是逐卷人批，不是一枪 300 章 |
| 戏/契约 | **进该卷之后** 批跑 duty→design | 现有 generate-stage | 单卷循环；禁止进 deduce/draft |
| 演绎/草稿/正文 | 逐章 | 现有五层 | 演绎不前置 |

这与体量纪律的关系：

- 云端「禁止一次生成全书细纲」改为：**禁止一次生成全书节拍级以下**（duty/play/deduce/draft）。**账目级一句话章纲允许按卷批跑。** 实施时改 `volume-scale-discipline.md` §8 / KD-9 措辞，不另起炉灶。
- 台账（PR-1）吃的就是这些 synopsis。账齐了，近窗才不是「有啥显啥」。
- 法官仍问：今晚只办这一笔；后面可以挂着，不许演完。批跑节拍时靠这一问，防止把卷二的夜写进卷一。

**不要**把「完成度 16 字段、势力 3–6 个」写成写好的标准。那是缺口报告的尺子。作者签字才能进下一阶段。

### 3. 修纲状态（硬门，旧书零影响）

章 meta 增量：`outline_status`（frozen/stale）、`outline_rev`、`confidence`（high/low）。**缺字段 = 旧书，不拦。**

- 改卷 intro：同卷 `confidence=low` 的章标 stale；high 的进「待人判」清单，不自动标。
- 改章 synopsis：对已有戏/演绎/草稿只提示「账已变」，**不自动 force 责任卡**。
- 目标 stage 为 deduce/draft 且 stale → 422，人话：「这章的纲改过还没核对，先看章纲再写正文。」duty/design 不拦。
- 旗 `SCRIBE3_OUTLINE_STATUS_GATE` 登记且可关。已冻正文不因修纲自动返工。

### 4. 与体量纪律施工顺序

| 云端 | 本方案 |
|------|--------|
| PR-1 台账+3.2.3 | 先做。召回翻主只改 `codex_recall` 函数体，与 `volume_ledger` 槽不相交。 |
| PR-2/3 UI | 先做。规划批跑产物在这些页审读。 |
| PR-4 万界只读冒烟 | **硬依赖**：规划 MCP 与召回翻主排其后。 |
| PR-5/6 长篇 opt-in | 百万字书才需要单元表；3 卷 10 章不强迫。 |

P0 可与云端 PR-1 **并行**的只有：digest 同步、索引/关系遍历、RecallService **影子**、secret 桥、outline 字段（门禁可先关旗）。**不要**在 PR-4 前对万界书批跑 duty→design。

---

## Key Decisions

1. **五种设施用不满的根因是各灶召回，不是缺桥。** 证据：`playbook_codex_recall` 子串+字母序凑数。
2. **摘要命题化唯一底座（D-R1）。** 限知/时态跟 proposition 走；渲染回源实体。
3. **RecallService 是写路径相关性取数的唯一出口。** 直取槽不接管。
4. **影子先于翻主。** 原函数体保留。
5. **规划先行 = 账目全建 + 剧本按卷。** 不是全书节拍，不是前置演绎。
6. **体量纪律不废。** 只放宽「全书」一词到账目级 synopsis。
7. **完成度只报告。** 禁止把字段表当写作通过条件。
8. **stale 门只拦 deduce/draft。** 旧书缺字段不拦。已冻责任不自动 force。
9. **产品写只走 MCP 审批。** 新工具进 WRITE_GATED。REST 最多 GET。
10. **万界验收只读。** 禁止 generate-stage 打已部署该书。

---

## Alternatives Considered

- **实体表自建向量**：限知要重建，泄漏窗口大；召回只需定位实体。否决。
- **混合双底座**：融合去重+门不对称。否决。
- **全书零稿再修**：连续性错误比重写贵。否决。
- **只接线、不统一中枢**：回应不了「五种设施没用满」。否决为终态；影子期可以先并行。

---

## Security & Privacy

限知 fail-closed。digest 与实体 PATCH 同审批链。secret 桥按实体类分旗灰度。主编坞全知兜底。屏蔽计数进 trace。禁止检索结果绕 iceberg。

---

## Observability

影子 diff 记 trace（hits、通道、是否跳过）。digest 对账告警。召回空结果打 skip 原因。旗变更打日志。

---

## Rollout

1. P0：digest + 索引/关系图 + RecallService 影子 + secret 桥；outline 字段可落、门禁可先关。
2. 云端 PR-1～4 绿（邻章账、设计页认戏、卷侧栏、万界只读冒烟）。
3. P1：三路召回翻主（各旗独立）；规划四件套 MCP（`s3_plan_volumes` / `s3_plan_chapter_accounts` / `s3_refine_volume_outline` / `s3_batch_stage` 仅 duty→design、单卷）。
4. P2：完成度只读门、进度面、长尾注入收编、红线 blocking 默认关。

回滚：各旗独立。影子关即无计算。翻主旗=0 回原函数。门禁旗=0 旧书行为。不 force-push。

---

## Risks

| 风险 | 缓解 |
|------|------|
| 一次换两条设定路径回退 | 影子 7 天；逐旗翻主；原函数保留 |
| 语义召回稀释写章嘱咐 | 档位封顶 +400 字；空则注空 |
| digest 双写漂移 | 同链同步 + backfill + 对账 |
| 批跑被当成一键全书节拍 | `s3_batch_stage` 硬编码单卷且禁 deduce/draft；全书节拍 422 |
| stale 误拦 | 缺字段不拦；high 章不自动 stale |
| 与 PR-1 同改 `context.py` | 台账新槽 vs 只改 `playbook_codex_recall` 函数体；先合 PR-1 |

---

## Open Questions

无。下列已裁：底座用摘要命题化；规划先行停在账目+按卷戏；演绎不前置；完成度不 422；万界不 overlay。

若影子期两路实体集合对不齐，先查预算裁剪点是否同序，再翻主。

---

## PR Plan

**PR-A** digest 命题化 + backfill + 多摘要 + 别名进 digest  
文件：新 `scribe3/codex_digest.py`、migration、`tools/codex_digest_backfill.py`；PATCH 钩到审批落库。旗 `SCRIBE3_CODEX_DIGEST_SYNC` default=1。  
依赖：无。

**PR-B** chapter HNSW、lesson BM25、人物/实体关系 ≤2 跳  
文件：migrations；`store/recall.py`。旗 `SCRIBE3_GRAPH_RELATION_RECALL`。  
依赖：无。

**PR-C** RecallService 骨架 + 预算登记 + 影子挂 playbook 与对话  
文件：新 `scribe3/recall_service.py`；`context_budget.py`；`feature_flags.py`。输出零变化快照。  
依赖：A（digest 可空跑）、B 可后挂图通道。

**PR-D** 通用 secret 桥（角色等类分旗）  
文件：`codex_secret_bridge.py` 推广。依赖：A。主编坞可见；普通视角屏蔽夹具。

**PR-E** outline_status / confidence 字段 + 门禁（默认可关）  
文件：`chapter_meta_codec.py`、migration、`stage_generate.py` 前置。缺字段不拦。  
依赖：无。建议门禁旗先 0，批跑上线再开。

**PR-F**（云端已有）体量纪律 PR-1～4。本方案不重做。合入时 `codex_recall` 与 `volume_ledger` 函数级不相交。

**PR-G** 翻主：playbook 槽 / 对话设定 / canonical 排序，三旗独立；删字母序凑数。  
依赖：C 影子绿 + F 的 PR-4。

**PR-H** 规划 MCP 四件套 + 完成度只读报告。WRITE_GATED。`s3_batch_stage` 单卷 duty→design。  
依赖：F 的 PR-4；建议 E 字段已在。

不排期：实体表向量、全书节拍、前置演绎、卷纲法官 422、密疏字数格。

---

## References

- `scribe3/playbook/context.py` — `_CODEX_BUDGET`、`playbook_codex_recall` 子串与字母序凑数
- `scribe3/codex_secret_bridge.py` — 仅势力
- `scribe3/memory_retrieval.py` — MemoryRetriever
- `scribe3/store/recall.py` — `semantic_recall` / `hybrid_recall`
- `scribe3/api/services/write_assemble_blocks.py` — `_codex_segments` / bridge mirror
- `docs/plans/2026-08-22-volume-scale-discipline.md` — 体量纪律
- Qoder 方案 v2（本文件的输入）；Noah / Mia 卷只引用结论
