# 小说业务审计 · 铜炉 / scribe3

| 项 | 值 |
|----|----|
| 角色 | 小说编辑 + 产品架构（只审业务是否服务小说） |
| 仓库 | `/home/admin/projects/scribe-writing-system` |
| 北极星 | 人话、有戏、可续的长篇 |
| 对标 | 《乱世铜炉》引子 + 前几章 + 第十六章（除夕） |
| 日期 | 2026-08-13 |
| 纪律 | 禁止把工程绿灯当小说质量；禁止再加一个 Agent；禁止 human-blind≥9.5 |
| 已知已证实（本文只升级，不当新发现） | 合同未进 assemble；D1–D7 词表代理冲突；product-mainline / write-path 已有设计未落地；对标差在人间秩序/群像机关/笑闹切异变/说书人，不在更碎短句 |

**一句话总判**：产品会写「戏核表」和「齐套灯」，不会写「先有日子再出事」。作者在写作台看见的完成，是材料字数和机判；书要的完成，是人间还在过、事变落了痕、下章日子被改过。五阶段、四套合同、限知工位、词表打分，是在逼刷脚手架。

---

### F-N01 五阶段时钟逼刷脚手架，不服务「先有日子再出事」

- 角度：小说
- 严重度：P0
- 现状：章工作台硬钉五阶段时钟：大纲→节拍→演绎→草稿→正文（`ChapterStudio.jsx` PHASES；`chapter_stage.py` 同源）。大纲 duty 一上来就是「谁、想干什么、会付出什么代价」；节拍 duty 是「冲突怎么升级、怎么收」；中间强制插入「场景真相 + 每人知道什么」。开写前材料清单把 synopsis≥80、节拍≥3、scene_truth≥80 标成 error，「还不齐 · 不建议开写」；齐了就亮「材料够了，可以开写」。standard 长文存正文走 GATE-B：缺大纲/节拍/演绎 → HTTP 409「章级脚手架未齐套，禁止接受正文」。
- 不合理：《乱世铜炉》引子先写婚宴、劝酒、面子、更梆、祖宗牌位——日子坐实了，才「嘎啦」一声切异变。第十六章题为（除夕），先写供桌冷火、婴儿暖被、子时入年，再写厢房夺丹。产品时钟把「日子」当成可跳过的闲笔，把「出事」拆成西式节拍卡，还要先填认知账本才能动笔。作者不是在过这一章，是在通关。
- 更合理：章的主时钟应是「日子（人间还在转）→事变（有人改了钱/命/面子）→余烬（下章必须接着过）」。大纲只写「这章村里在过什么、谁被卷进去」；节拍最多记必须发生的动作，不规定条数；演绎不是开写门票。脚手架诊断可折叠，不得挡正文。
- 不改的代价：每章开场都会像「任务简报」而不是话本；铜炉式岁时铺垫在产品里没有合法工位，模型只会从「目标/冲突」起笔。
- 证据：
  - `scribe3/web/src/ChapterStudio.jsx` L37–45 五阶段 duty
  - `scribe3/web/src/ChapterMetaPane.jsx` L249–318「开写前要齐的材料」/「材料够了，可以开写」
  - `scribe3/web/src/lib/chapterContractGate.js` L11–17、L111–157：80 字 / 3 拍 / scene_truth 为 error
  - `scribe3/chapter_stage.py` L7、L43–53：顺序 +1 的阶段机
  - `scribe3/verify_craft_compliance.py` L1090–1106：GATE-B 拦存稿
  - `乱世铜炉.md` 引子 L5–81（贺客笑闹 → 子时更梆 → 见鬼）；第十六章 L1801–1823（除夕日子 → 雪地脚步）

---

### F-N02 完成态至少九盏灯，作者只会认工程灯

- 角度：小说
- 严重度：P0
- 现状：同一章上同时存在多套「完成」：
  1. 五阶段 / `StageBoard`（推进到下一阶段）
  2. 章标 `label`：想法/节拍/草稿/修订/完成（`ChapterMetaPane` LABEL_OPTIONS）
  3. 开写材料灯：「材料够了，可以开写」
  4. dual-lamp 脚手架 chip：「可开写」
  5. dual-lamp 读者灯：「可读：机判过关，请通读确认」+ toast「机判可读」
  6. `may_claim_scaffold` / GATE-A/B/C/D 顶层 `ok` / `journey_pass` / `mvp_pass`
  7. `may_claim_story`（demo 宣称已切叙事；前端几乎不展示这个词）
  8. 草稿「采用为正文」+ 存稿 200 + QC 合计
  9. 评分卡 D1–D7 / NorthStar / purpose deltas achieved
  后端 `story_complete` 的黄灯要人 ack note≥10；前端 `readerReadyGate` **忽略** `lamps.reader.label="故事"`，只映射 phase，把 yellow 写成「机判过关」。`narrative_contract` 在 `scribe3/web` **零引用**。作者看不见合同四字段，只看见材料灯和机判灯。
- 不合理：小说作者认的完成只有一盏——「这章能给人看，下章日子被改了」。九盏灯里最亮的是脚手架。宣称公式已切 story，产品表面仍在教作者刷齐套。
- 更合理：产品只留一盏人灯：「本章戏是否成立」（人读完写一句话）。其余全部降为诊断，且不得用「过关/可开写/PASS」。材料灯、机判灯、阶段机、章标「完成」、旅程 PASS 必须从主路径消失。
- 不改的代价：作者会为绿灯填满 80 字大纲和 3 条带「拦/逼/拒」的节拍，然后以为章写完了；书仍是空的。
- 证据：
  - `scribe3/web/src/lib/readerReadyGate.js` L6–21、L28–41
  - `scribe3/web/src/WriteLayout.jsx` L543–548、L1092–1113
  - `scribe3/story_complete.py` L153–165、L207–211
  - `scribe3/reader_ready.py` L167–177（story 路径仍发 scaffold「可开写」）
  - 前端 grep `narrative_contract`：0 命中
  - 设计已写 Kill List，**未落地**（`docs/plans/2026-08-13-narrative-engine-product-mainline.md` §4）

---

### F-N03 合同四字段会把话本写成西方 beat sheet；且约束的是出口语不是场面

- 角度：小说
- 严重度：P0
- 现状：叙事合同字段是欲望 / 阻力 / 回合 / 代价（`desire/obstacle/turn/cost`），claim 还要求至少一条 `CONFLICT_LEX` 命中的 conflict_beat。节拍工位另有 GCD 五格：目标/冲突/转折/代价/钩子。`narrative_drive` 再要引爆/对立/期限/章末钩。`drama_beats` 再要 goal/conflict/turn/cost。同一套好莱坞场次语法复制了至少四次。校验是字数≥8 + 冲突词表，不是「场上是否发生过一件改日子的事」。`format_contract_block` 把「欲望：拒交铜匙」原文推进去——设计已承认这会让角色把条款念出口；assemble **至今未接**，但已接的 `event_drive` / `drama_contract` 是同一套西式标签。
- 不合理：《乱世铜炉》章法不是「主角欲望→阻力→中点反转→代价」。引子的欲望说不清（新郎只想散席），事变是牛泪见阴、面子酒桌；除夕章先过年，再夺丹。用 desire/obstacle/turn/cost 填铜炉，会把「除夕家里冷了」判成 no_conflict_clue，把「拦/讨/逼/拒」填进村口寒暄。
- 更合理：合同只约束**场面必须发生什么**和**必须留下什么痕迹**（钥匙没交、账上勾了半笔、人死了、年没过成）。禁止约束出口语、禁止英文字段名进嘴、禁止词表当戏。西式四格若保留，只能当作者私房备忘，不得当 claim 充分条件，不得当节拍每格必填。
- 不改的代价：书会越写越像英文大纲的中译：每章一个对峙动词，没有岁时，没有笑闹，没有说书人停下来评一句。
- 证据：
  - `scribe3/narrative_contract.py` L16–22 CONFLICT_LEX；L32 `_FIELD_KEYS`；L173–176 字段过短即 error；L51–80 beat_shape 无冲突词则 fail
  - `scribe3/web/src/ChapterStudio.jsx` L311–317、L480 GCD 五格
  - `scribe3/narrative_drive.py` L79–111 引爆/对立/期限
  - `scribe3/drama_beats.py` L1–28
  - `scribe3/narrative_contract.py` L234–248 `format_contract_block` 原文四行
  - `scribe3/api/services/write_assemble_v1.py` L230–260：只 `_push` event_drive / drama_contract，无 narrative_contract（已知，升级：UI 也没有合同）

---

### F-N04 戏核对象叠了四套半，作者不知道该填哪张表

- 角度：小说
- 严重度：P0
- 现状：章上同时活着：`narrative_contract`、`narrative_drive`、`pressure_drive`（PDC/PSC + irreversible.evidence）、`drama_beats` GCD、`purpose` deltas（knowledge/promise/fact/heat）、chapter.beats 文本、synopsis 里的 `stakes:/赌注:` 标签。migrate/project 函数在合同与 drive 之间互译，说明作者本不该面对两套。claim 认合同；注入认 drive/drama；存稿认 GATE-B 大纲节拍演绎；评分认 CONFLICT_LEX / TURN_COST。
- 不合理：小说只要一张「本章必须发生」和一本「世上已经发生」。四套半表是工程迭代残骸当产品。作者填完仍不知道戏在哪。
- 更合理：收敛成一个场面对象（人话：这章要出事的那一下 + 留下的痕）。drive/PDC/drama/purpose 降为内部投影或删除产品入口。禁止再为「对齐旧旗」保留第五张表。
- 不改的代价：任何改合同的努力都会被另一张表在 prompt 里盖掉；产品会继续长出第六套「真正的戏核」。
- 证据：
  - `scribe3/story_complete.py` L56–68：无合同则 migrate from drive
  - `scribe3/narrative_contract.py` L190–231 双向投影
  - `scribe3/pressure_drive.py` L1–6、L827 不可逆证据另库
  - `scribe3/purpose.py` L1–26、L218–251 又一套章目的
  - `scribe3/web/src/lib/chapterContractGate.js` L62–67 大纲里用英文 `stakes:` 标签

---

### F-N05 限知/演绎过重：把说书人工位收成了认知会计

- 角度：小说
- 严重度：P1（对铜炉声口是 P0）
- 现状：产品自我定义为「限知渲染：角色不知道的事，物理上进不了其 prompt」（`docs/CURRENT_ARCHITECTURE.md` §1）。演绎是五阶段第三拍，工位是 scene_truth + 每人一页投影，Run 走受限工具+审批，可并行多焦点，超时 6 分钟。草稿有「演绎未齐」条；契约把 scene_truth 空/短当 error。写作 banner 是「叙事贴焦点者所知所感」。2016-06-22 设计曾写明：铜炉是全知说书人，应标记私密、不得扣留；当晚改成 `project_frame` 物理扣留，后续文档未对账。
- 不合理：引子说书人直接告诉读者祖魂一直在家里喝酒、时闻盂从此做了神汉发了财——这不是焦点者限知，是说书人站在村口评点。第十六章夹叙术界戒律、杀妖取丹的江湖规矩，是叙述者全知。把这些先做成「场景真相 80 字 + 每人知道什么」，既慢又会把评点裁掉。限知该管的是**角色嘴里不能知道的**，不是叙述者不能说的。
- 更合理：演绎降为可选辅面（写破再说）。默认说书位 = 全知可评点；角色对白/心思走知识边。物理扣留只在作者钉了焦点章时启用，且不得当开写门票。
- 不改的代价：长篇会失去铜炉最值钱的嗓音（评点、报应、村社规矩），只剩摄像机跟一个 POV 走，戏变薄。
- 证据：
  - `docs/CURRENT_ARCHITECTURE.md` L11、L74–86
  - `scribe3/web/src/ChapterStudio.jsx` L43、L179–199
  - `scribe3/web/src/DeduceStage.jsx` L22–23、L13–16 GENERATE_TIMEOUT_MS=360000
  - `scribe3/epistemic_guard.py` L30–37 写作限知横幅
  - `设计文档/2026-07-04-本体论改造溯源审计.md`（标记式 vs 扣留式同日反转）
  - `乱世铜炉.md` L95–103 说书收束；L1835–1838 术界戒律评点

---

### F-N06 章间不可逆没有进入下一章的「日子」

- 角度：小说
- 严重度：P0
- 现状：不可逆散落在三处，互不接力成下一章生活：
  - PDC `irreversible.evidence_must_show`：本章正文是否出现某关键词（`pressure_metrics.irreversible_anchored`）
  - `purpose.settle_purpose`：未兑现 delta 复制到下一章合同（若下一章已存在），进 brief 必达清单
  - `ingest`：抽事件/知识边/关系触碰，理论上改世界，供下章限知帧
  续写仪式 `continue_snapshot` 只塞承诺、开环、焦点状态、文尾 200 字，**不**把「钱路改了/人死了/年没过成」写成下一章必须过的日子。写路径设计要的 `prior_consequences` **未接线**。
- 不合理：铜炉可续，是因为牛泪不可逆（时闻盂做神汉）、除夕家里人没了（婴儿还要喂）、钥匙/账/命会改村社秩序。产品验的是「本章有没有写出那个词」，不是「下一章开门是否还活在那个后果里」。ingest 是后台抽取，作者不当它是戏；PDC 证据是刷词；purpose 是另一套待办。
- 更合理：每章落笔后只收 1–3 条人话余烬（谁的日子改了、改成什么样），作为下一章大纲的默认第一行。关键词证据只做诊断。没有余烬，不得宣称章完成。
- 不改的代价：百万字会章章重置情绪，像连载任务本；读者不记得上章改过什么，因为下章也不记得。
- 证据：
  - `scribe3/pressure_metrics.py` L113–128 关键词命中即 anchored
  - `scribe3/purpose.py` L218–251 滚的是 deltas 待办，不是人间后果
  - `scribe3/experience/continue_rite.py` L56–95 快照字段
  - `scribe3/ingest.py` L1–4 闭合循环在知识账本，不在下一章场面
  - write-path §A 规定 prior_consequences 注入：代码未实现

---

### F-N07 岁时 / 群像改钱路 / 笑闹切异变 / 说书 / 事变章题——业务残缺，不是克制

- 角度：小说
- 严重度：P0
- 现状：
  - **岁时**：无节气/红白喜事/年节对象。除夕在对标里是章的主层；产品里最多当设定条目（`extract_settings` 里「每年六时节气入谷」是世界设定，不是写章时钟）。大纲/节拍/合同都不问「这章村里在过什么日子」。
  - **群像改钱路**：上下文组装**主动防止**群像污染北极星（只钉 protagonist+major）。关系触碰有冲突/靠近/决裂/亏欠/协作，但没有「账、债、香火、面子钱」作为戏核。群像是噪声，不是机关。
  - **笑闹切异变**：无声调对象。craft 注入的是压迫感身体句和温度曲线，把笑闹当「闲笔配额」。引子那种灌酒喷饭 → 门外折断声，产品无法表达。
  - **说书**：见 F-N05。默认扣留。
  - **事变章题**：铜炉是「第十六章（除夕）沧桑自古人间事」——括弧里是事变/岁时，联语是评点。产品 title 是自由文本，label 是 idea/draft/done。没有「章题=这章出了什么事」的业务。
- 不合理：这五项不是风格插件，是话本长篇的骨架。缺它们，系统只会优化对峙短句。这不是克制（克制是少做技法处方），这是残缺。
- 更合理：若只加业务，加在场面合同上即可——「本章日子」（岁时/场面）、「谁的钱/面子被改」（群像机关）、「何处由闹入异」（切变点）、「章题四个字」。不要新 Agent，不要新阶段。
- 不改的代价：对标会永远输在「不够文学」，团队会继续加短句引擎，越修越不像铜炉。
- 证据：
  - `scribe3/context_assembler.py` L711–717 防群像污染
  - `scribe3/craft.py` L27–33、L117「被关在笼子里」压迫感
  - `scribe3/structure_style.py` L30–36「长短交错」
  - `乱世铜炉.md` 章题 L5、L106、L1801 等；引子笑闹切变 L50–81
  - 写路径设计 L171 已点名这五项；产品对象未对应

---

### F-N08 D1–D7 词表把「有戏」定义成「出现对峙字」（已知升级）

- 角度：小说
- 严重度：P1
- 现状：`scripts/score_narrative_chapter.py` D1=CONF_LEX 种类数+对白条数；D2=TURN_COST 词（抵账/勾账/拒交…）+合同字段加分；D3=对白占比+身体动词−冷静模板；D4=beat_shape；D5=先验关键词（匙/炉/灰狸…铜炉书钉死）；D6=anti_meta+长度；D7=感官词+代价词。composite 均值当质量。停环看 Δ。这是写作协议，却被当验收。
- 不合理：引子高潮是「堂屋正中空空如也」+「天干物燥——小心火烛」，CONF_LEX 几乎不加分；除夕前半「过年」会低分。代理会往对白里塞「拦/逼/拒」和「——」急转刷 D1/D3。已知冲突，这里升级为：**评分在定义什么叫小说**，定义错了。
- 更合理：D1–D7 退出产品完成与停环。人读戏。最多用「余烬是否进了下一章」做结构检查。
- 不改的代价：机刷收敛到一张铜炉皮的网文对峙稿；人一看就假。
- 证据：`scripts/score_narrative_chapter.py` L27–49、L83–181；D5 默认 prior 钉死炉巷专名 L154–156

---

### F-N09 模型看见技法处方，看不见「必须发生的场面」（已知升级）

- 角度：小说
- 严重度：P0
- 现状：assemble 真主路径注入 prefix（含长短交错）、event_drive、drama_contract、envelope、craft 八引擎（身体先行/温度曲线/闲笔≥3/比喻 2–4/潜台词/感官/浸泡/留白）、phase_role。合同块未 `_push`，也未进 `generation_physical_order_names`。UI 主编种子把 GATE-B B1/B2/B3 字数条数写进对话。结果已见：冷短句、对白中句「——」、合同账房词进嘴。
- 不合理：小说模型应先看见「这章除夕家里人没了，雪地有人来夺丹」，不应先看见「每 500 字温度变化 1 次」。技法处方在教模型演「文学」，不教模型演人间。
- 更合理：写路径只见场面人话 + 限知（角色嘴）+ 声口禁令 + 上章余烬。craft/GATE/D1 名从 instructions 消失。此即 write-path 已审设计，**未开工**。
- 不改的代价：接上 `format_contract_block` 原文只会更糟（角色念欲望行）。必须按 write-path 的「禁止节」接，不能按 product-mainline §9 原文落地。
- 证据：
  - `scribe3/api/services/write_assemble_v1.py` L229–308
  - `scribe3/craft.py` L20–80
  - `scribe3/structure_style.py` L30–36
  - `scribe3/web/src/lib/chiefSeed.js` L155–176、L234–277
  - `docs/plans/2026-08-13-write-path-story-constraints.md` Background 表 1–10

---

### F-N10 存稿硬闸把「先写日子」判非法

- 角度：小说
- 严重度：P1
- 现状：standard 长 prose：GATE-B 未齐 → 409。短稿放行。explore 可 soft。`skip_craft_gate` 仍在。`danger_draft` 只旁路 finalize，不旁路 GATE-B。`GATE_SAVE_MODE` 仅存在于 8/13 设计，代码未注册。作者若先写婚宴再补大纲，正式存会被拦。
- 不合理：话本常是写着才知道章题。先日子后出事，材料必然后补。硬闸逼人先填 80 字起因转折结果，再写——这是剧本软件，不是长篇手稿。
- 更合理：存稿永不因材料未齐失败。材料诊断可见。宣称另走人 ack。finalize 只拦极端验收腔/崩坏，不拦「节拍不足 3」。
- 不改的代价：所有「先有日子」的正当写法在产品里是违规操作。
- 证据：`scribe3/verify_craft_compliance.py` L1028–1106；WriteLayout 409 toast；product-mainline §4.2 仍是设计

---

### F-N11 节拍≥3 + 每拍 GCD，把一章切成三场西式戏

- 角度：小说
- 严重度：P2
- 现状：MIN_BEAT_TEXTS=3 为 error；高压章还要 stakes 标签。每拍可展开目标/冲突/转折/代价/钩子。claim 的 conflict_beats 至少 1 条 shape_ok。scene_cover 用节拍关键词覆盖正文 2/3 才「场面覆盖」。
- 不合理：铜炉一章常常是一场日子里的一个变故，不是三场升级。用 3 拍去套「除夕」，会把安顿婴儿、做梦、夺丹拆成三个 beat，再要求每拍都有冲突词。scene_cover 会逼正文重复节拍摘要字面。
- 更合理：节拍是可选备忘。1 条够。禁止条数当完成。禁止关键词覆盖当可读。
- 不改的代价：章会变「三局对打」，岁时主层被拆碎。
- 证据：`chapterContractGate.js` L11–12、L131–137；`reader_ready.py` L71–107 scene_cover；`ChapterStudio.jsx` BeatsTab

---

### F-N12 修订默认整章再生，已改过的人话被丢掉

- 角度：小说
- 严重度：P2
- 现状：正文有「改这段」，仍走 `/chat/write` 全量 assemble。`scope=chapter` 列协议第一位。已知设计要把默认收到 `/revise-span` 预览，未落地。
- 不合理：长篇定稿是逐句换词。整章再生等于每次打磨都可能把已通的笑闹段换成冷短句。
- 更合理：默认改选区；整章重写二次确认。不新增 Agent。
- 不改的代价：人越改，人话越少。
- 证据：write-path Background §3；`ChapterStudio.jsx` 草稿/正文 selEdit 仍 seed 主编全量写

---

### F-N13 辅助面上的「分」在和正文抢定义权

- 角度：小说
- 严重度：P2
- 现状：AUX 有评分卡（NorthStar）、经验复盘、简报必达。QC 产品键合计 repetition/purple/ai_tics/god_view…。Pulse/QC 下划线。这些自称参考，但占主视觉，且与 D1–D7、GATE 一起形成「写给机器看」的反馈环。
- 不合理：作者会为少一个 purple、多一个冲突词改稿。小说不靠合计键绿。
- 更合理：评分卡/QC 进折叠，默认关。主反馈是人读一句「这章日子改了没有」。
- 不改的代价：人话被改成反 AI 检测器喜欢的样子——往往更假。
- 证据：`ChapterStudio.jsx` L48–53 AUX_ENTRIES；`qc_product_keys.py` L11–21

---

### F-N14 设计已看见主线，产品仍跑工程表面（已知升级）

- 角度：小说
- 严重度：P0
- 现状：2026-08-13 两份设计已共识：叙事=唯一完成；工程表面 Kill List；写路径只见故事约束。代码：宣称旗可开，表面/注入/存稿/IA **均未做**。审计时不得把「有设计」当成「业务已服务小说」。
- 不合理：继续按设计叠 PR 而不砍对象，会变成「合同主栏 + 旧五阶段 + 旧双灯 + 旧 GCD」五灯并存。
- 更合理：落地时以**删灯、删表、删阶段完成语义**为验收，不以「又接了一个 JSON 键」为验收。
- 不改的代价：第三份设计出现。作者仍在刷 80 字。
- 证据：两份 plan 文首「待人审签执行」；`GATE_SAVE_MODE` 仅文档；web 无 narrative_contract

---

### F-N15 若只留 5 个业务对象：名单与必须降级删除

- 角度：小说
- 严重度：P0（收敛令）
- 现状：见下节「七问」第 7 条。此处只钉原则：留下的必须是作者写长篇时手摸得着的东西；其余可留代码当基建，但必须从完成、主灯、开写门票、主编种子话术里消失。
- 不合理：对象多不是能力，是作者注意力税。
- 更合理：五对象见「七问」第 7 条。禁止用新 Agent 代替删对象。
- 不改的代价：永远在「再做一个真正的戏核」。
- 证据：本报告 F-N02、F-N04 对象清单

---

## 七问逐条答

### 1. 五阶段（大纲→节拍→演绎→草稿→正文）是否服务「先有日子再出事」，还是逼刷脚手架？

**逼刷脚手架。** 名义上大纲问代价、节拍问冲突，像在服务戏；实际上时钟强制「先齐材料再准写」，材料标准是字数、条数、场景真相，不是日子。中间插进演绎工位，把「出事」推迟到认知账本之后。存稿 409 把先写日子判非法。对照铜炉：日子是主层，事变是切一刀——产品把切一刀拆成三拍 GCD，把日子降成闲笔配额。阶段机 + 契约 banner + chief GATE 话术是同一套通关游戏。

### 2. 完成态有几套？作者会认哪盏？哪些必须从产品消失？

**至少九套**（F-N02）。作者会认的只有他看得见、并且会挡住他的：

- 主认：「材料够了，可以开写」+「可读：机判过关」+ 存稿是否 409 + 草稿是否已采用为正文。
- 几乎不认：`may_claim_story`（JSON/嵌套）、story-ack note≥10（toast 仍说「确认给读者」，不像认戏）。

**必须从产品消失的完成语义**（代码可留诊断）：

- 「材料够了，可以开写」/ scaffold「可开写」主 chip
- 「可读：机判过关」及 toast「机判可读」
- `may_claim_scaffold`、`craft-gates` 顶层 `ok`、`journey_pass`、`mvp_pass`、GATE-B 当完成
- 五阶段「推进完成」、章标 label=`done` 当故事完成
- D1–D7 composite / 停环 / NorthStar 当完成
- scene_cover、beats≥3、synopsis/truth≥80 当充分
- `skip_craft_gate` 当验收通过

**唯一可留的人灯**：人读完写一句，本章日子是否被改过（现 story-ack 可改口，但文案不能再叫机判/给读者）。

### 3. 合同四字段会不会把话本写成西方 beat sheet？该约束场面还是出口语？

**会。已经在写。** desire/obstacle/turn/cost + 每拍 GCD + drive 引爆对立 + CONFLICT_LEX，就是中译 beat sheet。铜炉不是每章一个主角欲望弧。

**只约束场面，绝不约束出口语。** 场面=必须发生的动作与留下的痕（钥匙还在谁手里、账勾没勾、人还在不在、年过没过）。出口语、账房词、英文字段名、冲突词表，一律不得进角色嘴，也不得当 shape_ok 的充分条件。四字段原文若进 prompt，必须另附「禁止念条款」；更好是改成「必须发生 / 必须留下」两行人话。

### 4. 限知/演绎是否过重？

**过重。** 对铜炉是方向错误，不只是剂量问题。限知应约束角色不能说破的私密；叙述者需要全知评点（报应、村社规矩、戒律、数日后才揭的因果）。演绎作为必经阶段 + scene_truth 80 字门票 + 6 分钟审批 Run，是在写知识库，不是在写章。保留知识边和投影作可选工具；从时钟、契约 error、开写建议里拿掉。

### 5. 章间不可逆如何进入下一章？

**现在进不去「日子」，只进得去账本和词表。**

- ingest → 下章限知帧（后台，作者不当戏）
- purpose carried → 下章待办清单（验做没做，不验日子）
- PDC evidence → 本章关键词（不进下一章）
- continue_snapshot → 承诺/文尾（太弱）

**应走的路**：章完成 = 收下 1–3 条余烬人话，自动成为下一章默认「日子还在过什么」。开门先活在后果里，再出事。不要新 Agent；不要通用不可逆动词表。

### 6. 岁时/群像改钱路/笑闹切异变/说书/事变章题——业务有无对应？克制还是残缺？

| 项 | 有无对应 | 判定 |
|----|----------|------|
| 岁时 | 无写章对象；仅有世界设定边角 | **残缺** |
| 群像改钱路 | 群像被当噪声裁掉；无账/债/面子钱戏核 | **残缺**（有反向机制） |
| 笑闹切异变 | 无；craft 推压迫感与温度曲线 | **残缺** |
| 说书 | 有限知扣留，与说书相反 | **残缺且反向** |
| 事变章题 | title 自由文本；label 是工程状态 | **残缺** |

不是克制。克制应砍技法处方和灯。这五项是话本骨架，砍它们等于不写这种书。

### 7. 「若只保留 5 个业务对象」的名单 + 必须降级删除的对象

**保留（作者手摸得着）：**

1. **手稿正文** — 唯一绿。存得下、改得了选区、给人读。
2. **场面** — 本章日子是什么、必须发生哪一下、留下哪一痕。人话。不是 desire 四格，不是 3 拍 GCD。
3. **余烬（世界已发生）** — 事实/事件/伤情/钱债/面子。章间接力用。ingest 可作实现，不得当完成灯。
4. **说书位与声口** — 默认全知可评点；角色嘴受知识边约束；禁对白中句「——」、禁念条款。
5. **章题（事变）** — 四个字说这章出了什么事（贺客/怪墓/除夕），不是 idea/draft/done。

**必须降级（可留代码，禁完成/主灯/门票/种子话术）：**

- 五阶段时钟与 `StageBoard` 完成感
- GATE-A/B/C/D、`craft-gates.ok`、`journey_pass`、`mvp_pass`、`may_claim_scaffold`
- dual-lamp「可开写 / 机判过关」
- `chapterContractGate` 80 字 / 3 拍 / scene_truth 门票
- `narrative_drive`、`pressure_drive`、`drama_beats`、`purpose` deltas 作为产品表（收进场面+余烬）
- 演绎必经阶段、并行限知工位
- D1–D7、NorthStar、QC 合计、scene_cover
- craft 八引擎 / 长短交错进写作 prompt
- 章标 label 五态、评分卡主入口
- CONFLICT_LEX / TURN_COST 当戏

**禁止**：再加一个 Agent、再加第六张戏核表、用 human-blind≥9.5 证明质量。

---

## 验收（若改，只认这些）

- 作者可以不填节拍、不演绎，先写一章婚宴再存——不 409。
- 写作台主表面不再出现「可开写」「机判过关」「材料够了」。
- 起草模型 instructions 看不见 GATE/D1/长短交错；看得见「必须发生 / 必须留下 / 上章余烬」。
- 下一章开门能读到上章余烬人话，而不是只读到冲突词表。
- 章题可以是（除夕），且不被判成无冲突。

以上任一条仍失败，工程绿灯不算小说业务过关。
