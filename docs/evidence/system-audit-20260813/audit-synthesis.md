# 四方审计整合裁定

| 项 | 值 |
|----|-----|
| 日期 | 2026-08-13 |
| 输入 | `audit-hermes.md` / `audit-surreal.md` / `audit-novel.md` / `audit-ux.md` |
| 挂靠（禁止第三套 SSOT） | `docs/plans/2026-08-13-narrative-engine-product-mainline.md`（完成/宣称/Kill List） |
|  | `docs/plans/2026-08-13-write-path-story-constraints.md`（写路径载荷 / W1–W7） |
| 北极星 | 人话、有戏、可续的长篇。主编是持工具的编辑，不是被喂技法的续写机。 |
| 纪律 | 不改代码；不另起完成公式；不把工程绿灯当小说质量 |

---

## 一句话

四方审的是同一条主路径：作者被齐套灯领进五阶段，落笔时官方补全吃的是技法圣经和 `facts_at` 切片，不查这场必须发生什么、上章日子改成什么样——产品在通关，书不在过。

---

## P0（≤7）

只保留「不改就写不出话本」的改造。每条都能开工，且挂已有 W* / product-mainline P*；不新开完成公式。

| ID | 标题 | 来源发现（留最硬证据） | 挂靠设计 | 为什么是第一性 |
|----|------|------------------------|----------|----------------|
| **SYN-1** | 写路径换燃料：模型只见场面，不见技法门 | **F-H03 / F-H15**（`chat_write_post` → `_stream_write(with_tools=False)`；`_assemble_write_instructions_v1` 恒 `_push` craft / anti_slop / structure_diversity，合同从未 `_push`）压过同主题的 F-N09、F-S05。F-S04/S09 作为「正典从哪来」并入本条，不单独立项。 | **W1**（`format_story_constraint_block` + 物理序在 `event_drive` 前）+ **W2**（源头去长短句/压迫感/chief GATE 话术）。`load_chapter_story_inputs` **扩** `hybrid_recall(query, chapter)` + 时间门图子图，**替换** `facts_at[:40]` dump。禁止 `_push(format_contract_block)` 原文。 | 小说是这一次 complete 写出来的。先看见「除夕家里人没了，雪地有人来夺丹」，才会有戏；先看见「每 500 字温度变化」，只会演文学。 |
| **SYN-2** | 改一句禁止开章级生产线 | **F-U04**（「改这段」仍 `POST /chat/write` 整章 assemble；协议默认 `scope=chapter`；接受即整章覆盖）压过 F-H11、F-N12、F-U10。 | **W3**（`discussSel` → `POST /revise-span` 只预览；禁 `apply=true`；整章走二次确认） | 长篇定稿是逐句换词。整章再生把已通的笑闹段换成冷短句，人话越改越少。 |
| **SYN-3** | 灭灯：主表面只留「这章日子改了没有」 | **F-N02**（至少九套完成；`narrative_contract` 前端零引用；`readerReadyGate` 把 yellow 写成「机判过关」）+ **F-U03**（假完成 / 假按钮「确认给读者」全仓不存在 / 假阻塞「不建议开写」）。F-U02 主钮语义并入本条验收。 | **W4a**（= P6a 文案束）+ **W4b**（= P3：`may_claim_scaffold` / `craft-gates.ok` / `journey_pass` 诊断化）。Kill List 去完成语义，不删基建。 | 作者认灯不认戏。灯在，就会为 80 字大纲和「拦/逼/拒」填表，书仍是空的。 |
| **SYN-4** | 先写日子必须合法 | **F-N01**（五阶段 + GATE-B 409 把婚宴当非法）+ **F-N10**（standard 长文材料未齐 → 409；`GATE_SAVE_MODE` 仅文档）+ **F-U08**（大纲禁止手写，只能「让主编」审批）。F-U01/U09 是同一闸的点击面。 | **W5**（= P5 / product-mainline §4.2 存稿 soft，不重写真值表）+ 最小 IA：`ManuscriptDirectory` 点章打开稿纸（勿写死 `phase:'outline'`）；大纲格允许作者打字。审批只拦改别人的章/世界。 | 话本是日子坐实了才切异变。系统把日子判成闲笔、把出事拆成通关，铜炉式开场在产品里没有合法工位。 |
| **SYN-5** | 一份场面纸，不是第十张戏核表 | **F-N03 / F-N04**（desire/obstacle/turn/cost × drive × PDC × GCD × purpose = 四套半；claim 认词表，注入认 drive，存稿认 GATE-B）+ **F-U05**（页签 / 章节信息 / SoftCards 三套表）。 | **W6**（= P7）**按本裁定的产品口实施**：稿纸页眉一行「本章日子 / 必须发生哪一下 / 留下哪一痕」。五阶段页签、章节信息复述、StageBoard 进折叠。**不**再铺好莱坞四格当主栏完成条件。对象仍是已有 `narrative_contract`，不新建表。 | 小说只要「这场要出事的那一下 + 世上已经发生」。表一多，任何改合同的努力都会被另一张表在 prompt 里盖掉。 |
| **SYN-6** | 讨论默认只读联查 | **F-H04 / F-H14**（`ChiefDock.send` `agentic:false` → `/chat/stream` → `hermes_complete_stream` 灌 discussion envelope；`chat_agentic_stream` `:8643` + `s3_*` 已实现未接）。F-H05 双灌作为本条的 instructions 瘦身约束。 | **无独立 W***。挂产品铁律「主编 = 持工具的编辑」，**不新开 SSOT**。开工 = UI 默认 `agentic:true`；有工具时 instructions 只留身份 + 本轮问题 + 取数优先级（世界由 `s3_*` 取）。纯寒暄再降级 complete。世界写保持 Runs。 | 核对「这人此刻知道什么 / 伏笔开着几条」是编辑本职。背 prompt 像读过书，一超窗就胡编。 |
| **SYN-7** | 余烬进下一章日子 | **F-N06**（`prior_consequences` 写路径已规定、代码未接；`continue_snapshot` 只有承诺/文尾；PDC 验关键词；purpose 滚待办）+ **F-S03**（定稿 ingest `delta.events` 常不传 `effects` → 无 `see_event` / 目击者）。 | **W1** 已列 `prior_consequences` 注入；本条把它升级为验收牙齿，并补 ingest：抽取事件带 `participants`+`effects` 才走 `add_event` 真图。无 1–3 条人话余烬，不得点亮人灯（**不是**新 GATE、不进 `may_claim_story` 机判）。 | 可续 = 下一章开门还活在后果里（年没过成、人没了、账勾了半笔）。章章重置情绪的连载任务本，不是长篇。 |

**刻意未进 P0 的硬发现**（真、但不是「写出好小说」这一厘米）：W4c/P3b cover 原子、Hermes 函数名骗过 GAP-12（F-H02）、`store=True`/压缩进 `state.db`（F-H07）、LIVE+轮询（F-S07）、合同 JSON 袋不可 SQL（F-S06）、D1–D7 停环（F-N08 → 已有 **W7b**，作 P1）、破折号检测（**W7a**）。

---

## 矛盾裁定

只裁会让实现者走叉的冲突。未列入的「四方同指一件事」见上表合并，不在此复述。

### 裁 1 · 合同四字段会不会把话本写成 beat sheet？

| 方 | 主张 |
|----|------|
| product-mainline | `narrative_contract` 四字段 + `conflict_beats.ok` = 宣称 SSOT；P7 做合同主栏 |
| write-path | 继承该公式（KD-W7）；**载荷**改为 `format_story_constraint_block`（四义行原文 +「禁止念条款」+ 痕迹），禁止 `_push(format_contract_block)` |
| 小说 | 四字段 + CONFLICT_LEX + 每拍 GCD **已经在写**中译 beat sheet；只约束场面和痕迹；词表不得当 shape_ok 充分条件 |

**裁定：不改 `may_claim_story` 公式（防第三套 SSOT），改载荷和表面。**  
对象继续是 `chapter.narrative_contract`。进模型的必须是 write-path 的「必须发生 / 必须留下 / 上章余烬」，不是 §9 原文四行、不是 CONFLICT_LEX、不是英文字段名。W6 页眉用日子/事变/痕迹的人话，欲望/阻力只作作者可展开的私房备忘，**不得**当主灯、不得当开写门票。`conflict_beats.ok` 本轮仍留在宣称链（product-mainline 已 ship），但 **W6/W7 禁止把词表当戏**；真完成仍是人 ack。禁止再长第五张戏核表去「修正」四字段。

### 裁 2 · 限知物理扣留 vs 说书全知

| 方 | 主张 |
|----|------|
| 架构 / Surreal / write-path | `project_frame` 已进 assemble；写路径注入限知横幅 |
| 小说 F-N05 | 铜炉是全知说书人；扣留说书评点是方向错误；演绎当门票过重 |
| Hermes | 限知靠投影，不靠把全书塞进 prompt（与「别灌」一致，与「叙述者闭嘴」不是一件事） |

**裁定：能力留、默认改口、门票撤。**  
`project_frame` / `fn::knowledge_frame` **不拆**（Surreal 已接对的部分）。默认叙述位 = 全知可评点；角色对白/心思走知识边。物理扣留仅当作者钉了焦点章。演绎、`scene_truth≥80`、6 分钟审批 Run **退出时钟 / 契约 error / 开写建议**（并入 SYN-4/5）。write-path 限知句改写成「角色嘴里不能知道的」，禁止写成「叙述者不能说的」。

### 裁 3 · 落笔关工具灌约束 vs 主编持 `s3_*` 取世界

| 方 | 主张 |
|----|------|
| Hermes F-H03/H13 | 正文仍可用无工具补全，但输入应是本 span 约束；讨论必须挂只读工具 |
| write-path | 编排注入约束后 complete；不把 `/chat/write` 改成 agent loop |
| Surreal | 图/混合检索应进 assemble，不是再灌 40 条 |

**裁定：散文继续 complete；取数在编排层；讨论走只读 agent。**  
SYN-1 = `load_chapter_story_inputs` 先取（合同 + 余烬 + hybrid/图子图 + 限知帧），再短补全。SYN-6 = 讨论默认 `:8643`。**本轮不把动稿改成全量写 Run**（避免工具回合抢散文；也遵守小说「禁止再加一个 Agent」）。F-H08「draft include 补 recall」**不做**——故事联查由 assemble IO 做，不靠给草稿 agent 加玩具。

### 裁 4 · P7「合同主栏」vs UX「一份纸」vs 小说「不要西式四格产品化」

**裁定：W6 开工，但验收改口。**  
交付物是稿纸页眉那一张纸，不是章节信息里再复制四字段。若做出「合同主栏 + 旧五阶段 + 旧双灯 + 旧 GCD」并存，判 **P7 失败**（小说 F-N14 已预警）。product-mainline §6.2 IA 树保留为深编折叠，不进第一眼。

### 裁 5 · 图 RAG 进 assemble vs 「禁止把全书塞进 prompt」

**裁定：用查询，不用倾倒。**  
F-S04/S09/S10 并入 SYN-1：本章 query + 时间门子图（知情者 / 同场 / 2–3 跳因果），经 `project_frame` 再进 canonical。禁止全图、禁止再叠一份工具说明书（F-H05）。`memory_item` 不得标成正典（F-S05/S08 保持分离；无键 episodic **不准**再进 writing `recent`）。

### 裁 6 · 其它硬冲突（一次性钉死）

| 冲突 | 裁定 |
|------|------|
| 小说五对象 vs product 合同+节拍+ack | **映射不新造**：手稿=`save-chapter`；场面=`narrative_contract` 的 write-path 载荷；余烬=`prior_consequences`+带 effects 的 event；说书/声口=默认全知+角色嘴知识边；章题=现有 title（事变四字），`label=done` 不当故事完成。drive/PDC/drama/purpose **留代码、滚出表面**。 |
| 小说「无余烬不得宣称完成」vs `may_claim_story` 不含余烬 | 余烬走人灯文案与 SYN-7 验收，**不**塞进宣称公式机判（防又一张词表）。 |
| Hermes「draft 补 intent/motifs/recall」vs 小说「禁止新 Agent」 | **本轮不扩 draft 工具面**。见裁 3。 |
| product「叙事引擎=完成 SSOT」vs 小说「人读一句才是完成」 | 公式链保留；**产品绿的观感**以人 ack 为准（W4a）。机判永不说「过关」。 |

---

## 明确不做

看起来高级、能开新设计、与「先把这场戏写对人话」无关——本轮明确不做。

**运行时 / 底座**

- 换默认模型供应商；把剧情迁进 Hermes memory；EMERGENCY REST 当默认写通道
- 再起一套 Surreal / SQLite 剧情库；正典迁出书库；auth / 日帽并进书库
- 为「图好看」在 ingest 里给器物/地点造 WITNESS
- 用 changefeed 自动改正典；原生 `LIVE SELECT WHERE` / 轮询改造当主线
- 全库 SCHEMAFULL；把合同 JSON 袋升字段当本周 P0
- 再为每个 UI 按钮加 Hermes profile / 端口
- 启用或修补 `scribe-novel-v2` skill（含不存在的 `s3_render_scene` / `skill_manage`）
- 扫全量 `s3_*` 求「工具目录完整」；把 draft/final Run 加成全能 agent

**业务 / 完成 / 评分**

- 第六张戏核表、新 Agent、新阶段、岁时/笑闹/群像的独立工位（这五项若做，只写进场面纸字段，见 F-N07）
- human-blind ≥9.5 / LLM 文学分当产品门
- D1–D7 composite、停环、NorthStar、QC 合计、scene_cover 当完成（W7b 只降级 D1 读序，不当 P0）
- 破折号进 `may_claim_story` hard（W7a 可随后，NG2）
- 通用不可逆动词表替代篇章余烬（NG5）
- 删除 `verify_craft_compliance` / 关掉 Surreal / 拆 `save-chapter`
- 把 `DEGEN_IN_STORY_CLAIM`、H9、`may_claim_serializable` 产品化

**交互炫技**

- 旅程胶囊「继续」自动编导、四栏工艺、系统活地图、Pilot、收件箱当第一眼
- 为「高级感」重做图谱/时间线/仪表盘
- 大纲继续禁止手写、靠「让主编提案供批准」当主路径（这是反模式，SYN-4 要拆，不是要增强）

---

## 分面结论

### Hermes

三网关当能力隔离仍然对：零工具 / 只读 Responses / 写 Runs + 阶段 profile。现网偏差不在拓扑，在**主笔和讨论都没走该走的面**——动稿关工具灌技法，讨论走名为 Hermes 的官方 complete，真 agentic 被 UI 钉死。`hermes_complete*` 顶着 Hermes 名骗过 GAP-12，是假账，但修命名救不了小说；杠杆是 SYN-1 的调用形状和 SYN-6 的默认联查。SOUL「剧情不得进 memory」只有 markdown，压缩 + `store=True` 已在 `state.db` 留尾巴——本轮不迁剧情进 Hermes，产品主路应尽快 `store=false` / 只存指针，但不占 P0 名额。

### Surreal

正典面没有被迁走：一书一 `db`、`project_frame`、带 `effects` 的 `add_event` 事务、素材三通道参考、fabric 分表，这些是对的，保持。3.2.4 上对「前后一致」杠杆最大的三件——命题 `hybrid_recall`、时间门图 RAG / `causal_chain`、章向量回指——**写路径零引用**；写作混的是 `memory_item` 和 `facts_at` 倾倒。缺的不是新底座，是 SYN-1 把查询接到 `load_chapter_story_inputs`，以及 SYN-7 让抽取事件带目击者。书级检索合同、LIVE 配额、合同列升 SCHEMAFULL，与写出下一句无关。

### 小说业务

产品会写戏核表和齐套灯，不会写「先有日子再出事」。五阶段、四套半合同、限知工位、词表打分，是在逼刷脚手架；岁时、群像钱路、笑闹切异变、说书评点、事变章题不是风格插件，是话本骨架，但补法是写进场面纸，不是新时钟。设计（product-mainline / write-path）已经看见主线，**审计时不得把「有设计」当成业务已服务小说**——落地验收是删灯、删表、删阶段完成语义，不是又接一个 JSON 键。D1–D7 在定义什么叫小说，定义错了；退出完成与停环即可，不必本周重做评分学。

### 交互

主路径像工艺验收台：点第五章先进大纲门（>4 次才改得成一句），主按钮是「让主编 / 过门 / 存为正文」，大纲格子不能打字，「改这段」仍开章级生产线，灯说「可开写」时人已经在写，toast 叫人点一个不存在的「确认给读者」。旅程/四栏/系统图是注意力税，进高级即可，不必重做壳。UX 的 P0 不是换皮肤，是 SYN-3/4/5：灯灭、日子可先写、一份纸、改一句只改一句。

---

## 建议开工顺序

仍是建议。用户未要求写代码。排期挂已有 W*，把四方 P0 嵌进去，避免第三张 PR 表。

```text
第 0 步（已有设计，勿再开文档 PR 当交付）
  W0 指针已写清：P2/P3/P3b/P4/P5/P6a/P7 实施以 W* 为准
  本裁定只约束验收口（SYN-5 一份纸、SYN-1 扩取数、SYN-6 无新 SSOT）

第 1 步 · 换燃料 + 灭最亮的假灯（作者第二天就能感觉到）
  W1 = SYN-1 + SYN-7 的注入牙齿
      · format_story_constraint_block + 物理序
      · load_chapter_story_inputs：hybrid_recall + 图子图 + prior_consequences
      · 单测锁 order_indices，禁止 import format_contract_block
  W4a = SYN-3 文案束（无「机判过关 / 可以开写」）
  顺手：点章默认稿纸（F-U01，改动面极小，不必等 W6）

第 2 步 · 停灌处方 + 主编开始查书
  W2 = 源头去长短句/压迫感/chief GATE；allowlist 剥回潮
  SYN-6 = ChiefDock 默认 agentic:true + 瘦 instructions（可与 W2 同批）

第 3 步 · 改字不再毁章
  W3 = SYN-2 revise-span 预览
  目录/大纲可手写（SYN-4 的 F-U08）可插在此步，不依赖 W6 整页 IA

第 4 步 · 让「先写婚宴」合法，并收敛成一张纸
  W5 = SYN-4 存稿 soft（规格只引用 product-mainline §4.2）
  W6 = SYN-5 页眉场面纸（验收：不得五灯并存）
  ingest events 补 effects（SYN-7 图边）随 W5/W1 收口

第 5 步 · 工程表面收尾（防回归，不是小说增量）
  W4b / W4c / W7a / W7b 按原设计
  Hermes 主路 store=false、GAP-12 认 transport 不认函数名：随手还债
```

**验收只认这些（任一条失败，工程绿灯不算过）：**

1. 起草 instructions 看得见「必须发生 / 必须留下 / 上章余烬」，看不见 GATE / D1 / 长短交错 / 温度曲线。
2. 「改这段」200 预览、只脏选区；误点不会整章覆盖。
3. 写作台主表面不再出现「可开写」「机判过关」「材料够了」。
4. 不填节拍、不演绎，先写婚宴再存 —— 不 409。
5. 作者能在本章意图里打字，不必先批准主编提案。
6. 右栏问「他此刻知道什么」会打 `s3_*`，不是只背 envelope。
7. 下一章页眉能读到上章余烬人话。

---

## 现在最不合理的是哪一层？

四件事是一条因果链，不是四选一。业务把完成定义成齐套灯和西式节拍，交互就只能演验收台；主笔入口再把技法圣经灌进关工具的官方补全，主编就不可能是持工具的编辑；图和混合检索再深也没人在那一次调用里问库。若硬要钉「此刻最不合理的一处」，是 **Hermes 主笔调用形状用错**——小说是在 `chat_write_post → complete` 里写出来的，这里把编辑做成续写机，北极星当场落空；业务偏了决定喂什么，交互演戏决定作者点哪里，Surreal 用浅是前两者的后果而不是根因。先换 SYN-1 的燃料，灯和闸才值得拆。
