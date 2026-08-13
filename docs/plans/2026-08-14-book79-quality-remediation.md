# book_79c0d45e 排序改造方案

状态：**分析方案，未实现。** 不重开宣称公式，不改 `GATE_SAVE_MODE=soft`，不把 skip_finalize 说成质控通过。  
对照评注：`docs/evidence/v634-true-chat-20260814/14-quality-findings.md`  
问题全表：`docs/evidence/v634-true-chat-20260814/14-problem-table.md`  
观测账本设计（未落地）：`docs/plans/2026-08-14-pipeline-analysis-log.md`

杠杆原则：**先修挡读者的脏稿通道和假绿，再修装段空合同（这是提纲腔的上游），再修声口与跨章单真。**

---

## 不做

- 不重写五章当本目标交付（除非后续单独 goal）。
- 不关 soft 宣称、不宣称人盲 ≥9.5、不把 31614 说成可读定稿。
- 不在 Grok 机全量测 / 本机 Surreal / 第二套库。
- 不为「再验一次」另起平行书。
- 不把 141 `pipeline_log` 假装已经在现网。

---

## P0 · 挡读者 / 假绿（先做）

### R1 存稿围栏：只落散文，禁止提案帧

**改什么**：`save-chapter` / extract 入口。若正文匹配 `{'scope':` / `"fallback": True` / `⟦提案` / 尾部 Python dict，**拒绝入库**或剥到纯 `prose` 字段再存。对 `write_stream` 的 fallback：只把 `prose_body` 交给客户端标记，**永远不要**把 JSON 对象 `str()` 进累积缓冲。

**验收（已部署 demo）**：对现网第 1–4 章做一次「剥尾重存」或新书一章：`GET /api/chapter` 的 `prose` 不含 `fallback`；post-check `dup_n` 不再接近「整章×2」。

**对应**：S1 S2 T1。

### R2 禁元词表补导演腔与机器尾

**改什么**：`anti_meta` / 退化检测增加：`开写前`、`正文如下`、`先理一条线`、`## 第X章` 出现在章首 200 字、`fallback': True`。命中 = claim_blocking，finalize **不得**靠 skip 默默过。

**验收**：把第 2 章原文丢进现网 `POST /api/post-check`，`anti_meta.hits` 非空；今天是空数组。

**对应**：S10 T2。

### R3 skip / 定稿门必须在链上可见

**改什么**：`save.finalize_gate` span 写 `actual_reason=skipped_by_flag`（或 blocked）；chain.notes 打戳。`headline_from_spans` **删除**默认「对照齐全」，改成「定稿门跳过 · 可读未宣称」这类人话。

**验收**：再 skip 一次，`GET /debug/pipeline-traces` 的该 save 链 headline 含「跳过」或「未过质控」，不是绿「对照齐全」。

**对应**：S3 S4。不改 soft 公式，只改观测诚实。

### R4 可读灯未绿禁止当成功定稿 UI

**改什么**：作者章页 / save 回包：`may_claim_readable=false` 时主按钮文案是「已存草稿（不可宣称可读）」，不是「已定稿」。脚手架灯保持可开写。

**验收**：五章现态即可对照——脚手架绿、可读红必须同时看见。

**对应**：S4。

---

## P0.5 · 空合同（提纲腔与跑题的上游）

### R5 戏剧合同：slogan beats 也要能注入「必须发生」

**现状**：`format_drama_block` 无 GCD/钩子 → 空串。点批 beats 只有 `{text}`。

**改什么**（二选一，推荐 A+B）：

- **A（快）**：`format_drama_block` 在无 GCD 时降级注入「〔必须发生〕」+ 三条 `text` + 限知免责，**禁止空串**（章上有任何非空 beat）。
- **B（正）**：结构点批/MCP apply 把 synopsis 拆成带 `goal/conflict/turn` 的 beats.v2，并写 `beats_meta.chapter_hook`。

**验收**：新写一章，span `assemble.seg.drama_contract` `actual=present` 且 chars>0。

**对应**：S5 T3。

### R6 大纲步空注必须 fail-loud

**现状**：`expected=has_outline_src` 但 `actual=empty`。

**改什么**：`_outline_block` 空返回时 span 记 `why`（get_chapter 空？synopsis 被 clip 光？异常？）。有 synopsis 或 beats 仍空 = 单测红 + 链 notes。修 rebind/章视图直到现网 span chars>0。

**验收**：对 `book_79c0d45e` 再打一次 write（可 danger_draft），`assemble.seg.outline` 不再 empty。

**对应**：S6 T2 T7。

### R7 对照卡与 span 同一套 actual

**改什么**：`contrast_summary.rows` 必须读 span 落盘后的 `actual/chars`，禁止并行再算一遍导致「span 说 codex 702 字、对照说 empty」。

**验收**：同一 `trace_id` 上同名段 span.actual === contrast.row.actual。

**对应**：S7。

### R8 失败链写 exception

**改什么**：assemble/rebind 异常进 `chain.notes` + 末 span `output.error={type,summary}`（无堆栈密钥）。

**验收**：人为触发一处已知 fail-soft 之外的 NameError，链上能读到类名。

**对应**：S8 S17。

---

## P1 · 限知 / 单真 / 节拍可覆盖

### R9 侧门（A7）进 secret_guard，不只条幅

**改什么**：设定「仅老桂知侧门开法」落 secret；限知章（阿绣）写路径 `secret_guard` 必 present；出口扫描「铜签/锁眼/拨锁/门轴」+ 非知情人 POV = leak。

**验收**：用第 4 章摘录打 post-check / epistemic，`leaks` 非空。今天 `leaks=[]`。

**对应**：T6。

### R10 物件单真：断刀鞘

**改什么**：A2 写死一条现行真（推荐：霍三刀之物，沈拾灯暂扣，还到炉前）。写前注入「现行真 + 禁改来历」。supersede 才允许改。

**验收**：新写涉及鞘的段落不得出现「爹的东西」「郭家三刀」「霍不知谁拾」三选二。

**对应**：T5 T8。

### R11 炉契禁令进揭示纪律

**改什么**：第 1 章 synopsis 已有「不能揭破炉契全文」——把这类禁令收成章级 `reveal_secret_ids` / 揭示纪律，而不是指望模型自己记得。

**对应**：T7 T9。

### R12 节拍可被 scene_cover 打中

**改什么**：点批模板改成场面名词（缺页灯册、封炉、挡炉）而非整句口号；或 `scene_cover` 对 slogan 抽 2–4 个实质词（封炉/缺页/刀鞘）做命中。**不要**为了绿灯改阈值到 0。

**验收**：第 3 章这种「戏其实在」的正文，`valid` 至少 2/3。

**对应**：S11 T12。

### R13 人物怎知（T4）

**改什么**：阿绣点破「军中人命」须有 deduction / 已揭示事实；否则 epistemic 记 leak。不要靠换 POV 逃避。

---

## P2 · 声口与观测账本

### R14 声口锚变成真约束

30 字 unexpected 锚改为：本书过程偏好（铜腥/炉灰、禁系统流）+ 焦点者口吻各 1 句。缺锚 = 不注，而不是注空壳还红。

### R15 章名生成

结构 apply 后若 title 匹配 `^第\d+章$`，用 synopsis 前 8 字或作者点名补上。

### R16 可见字剥污染

wordcount / visible 先跑 R1 同类剥离，再计数。31614 不得继续当「可读 3 万字」。

### R17 落地 141 分析账本

按已评审 `docs/plans/2026-08-14-pipeline-analysis-log.md`：**逐步中文日志、步骤身份、消费边、7 天 TTL**。本分析 **不实现**。没有它，下次质量分析仍只能做对照卡考古。

### R18 设定分词噪声

「炉火」「拾灯」不当 unknown_name。P2，勿让它挡住 P0。

---

## 建议施工顺序（可进后续 execute）

| 序 | 项 | 预估 | 依赖 |
|----|----|------|------|
| 1 | R1 存稿围栏 | 0.5–1 PR | 无 |
| 2 | R2 禁元词表 | 同 PR 或紧随 | R1 |
| 3 | R3 headline / skip 戳 | 小 PR | 无 |
| 4 | R4 存稿文案 | 前端小 PR | R3 |
| 5 | R5+R6 戏剧/大纲不再空 | 装段 PR | 单测不启 Surreal |
| 6 | R7 对照=span | 观测小 PR | 无 |
| 7 | R8 失败摘要 | 顺手 | 无 |
| 8 | R9–R13 限知/单真/覆盖 | 设定+守卫 | 不重开公式 |
| 9 | R17 141 | 已有设计 | 单独 goal |
| 10 | 可选：洗 `book_79c0d45e` 1–4 章脏尾 | 运维向 | R1 先合；须用户点头 |

**第一刀只做 R1+R2**：现网读者立刻不再看见 JSON 和「开写前先理一条线」。其余都是让下一本不要再写成这样。

---

## 与宣称 / soft 的边界

- `GATE_SAVE_MODE=soft` 保持：工程可存危险草稿。
- soft **不等于** UI/headline 说「定稿/对照齐全/可读」。
- 体验总通过、人盲分：本方案零触及。
