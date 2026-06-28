# 05 · 声音指纹、角色弧光与 craft 引擎层

> 本文档讲清 scribe3 让"每个角色声音可辨、人物随情节变、文字有工艺"的三套子系统:
> **声音指纹(voice fingerprint)**、**角色弧光(character arc)**、**craft 引擎层**。
> 每一节先讲现状(读代码)、再对照专业写作工艺、最后给改进方案。
>
> 代码基线:`feat/business-audit-fixes` 分支(本会话把审计标"死"的字段接活后)。
> 关键文件:`scribe3/store.py`、`scribe3/app.py`、`scribe3/craft.py`、`scribe3/critique.py`、`scribe3/ingest.py`。
> 关联审计:`docs/audits/2026-06-28-数据字段业务合理性审计.md`(C5 声音弧光、C4 craft、主题 D"卖点空心化")、
> `docs/audits/2026-06-28-写作主链路分析与改进.md`。

---

## 0. 一张图看懂三套系统怎么咬合

```
                ┌─────────────────── 写作主链路(/chat/write)─────────────────────┐
                │  _editor_write_system  系统提示(主编人格 + 北极星 intent)       │
                │      + _voice_anchor_block   ← 声音指纹(焦点者声音锚 + 对白速记) │
                │      + _arc_state_block      ← 角色弧光(char_state_at 时点快照)  │
                │      + _motif_block          ← 母题(主动编织)                    │
                │      + _frame_block          ← 限知帧(只能写他知道的)            │
                │      + build_craft_block     ← craft 引擎层(8 引擎 + 题材规则)   │
                │                          ↓                                        │
                │                    Hermes 生成正文                                │
                └──────────────────────────┬──────────────────────────────────────┘
                                           ↓ 定稿
        ┌──────────────────────── ingest_chapter(读回正文抽知识)─────────────────┐
        │  build_knowledge_extract_prompt → LLM → parse_knowledge_delta            │
        │    learned/did → 知识账本(谁知道什么)                                   │
        │    voice_shift → add_voice_flag      ← 声音随情节演变(标记)             │
        │    arc         → add_char_state       ← 自动长出弧光(反哺下一章)        │
        └─────────────────────────────────────────────────────────────────────────┘
                                           ↓ 半自动消化
        fold_voice_flags(角色)  ← LLM 把 open flag 折叠进 voice_profile,闭环
```

三套系统共享同一个**事件溯源 + 双时态**底座:角色不是一张静态卡片,而是"事件流叠加出来的时点快照"。
声音会变、能力会变、关系会变,系统的任务是让**写第 N 章时,生成器看到的是该角色在第 N 章那一刻的样子**,而不是设定库里那个永恒不变的版本。

---

## 1. 声音指纹系统(Voice Fingerprint)

### 1.1 现状:voice_profile 9 节结构

每个角色一条 `voice_profile` 记录(表名 `voice_profile`,record id = 角色 local id)。
写入口 `store.set_voice_profile(character_id, profile)`(`store.py` 约 1192 行),读 `get_voice_profile`。
9 节字段如下表——这是"角色怎么说话"的全部维度:

| # | 字段 | 类型 | 含义 | 进续写 prompt? | 备注 |
|---|------|------|------|:---:|------|
| 1 | `style_summary` | str | 一句话声音概述(如"冷峭、爱用反问、不肯把话说满") | ✅ 主锚 | 叙述+内心独白都贴它 |
| 2 | `catchphrases` | list | 口头禅/标志性措辞 | ✅ | 注入为"口头禅:…" |
| 3 | `tone_rules` | list | 语气规则(如"对长辈用敬语、急时省主语") | ✅ | 注入为"语气规则:…" |
| 4 | `reference_lines` | dict/list | 参考语感样句(该角色说过的、对味的句子) | ✅ 取前 2 条 | 兼容 dict/list 两种形状 |
| 5 | `ooc_signals` | list[dict] | **出戏信号**:{description, severity, detection_method} | ❌(事后校验用) | 喂 `check_ooc` |
| 6 | `sentence_patterns` | dict | 句式偏好(如 {长短:多短句, 标点:少感叹号}) | ✅(本会话接活) | 曾是"死字段" |
| 7 | `vocabulary_profile` | dict | 词汇倾向(行业黑话/方言/避用词) | ✅(本会话接活) | 曾是"死字段" |
| 8 | `internal_monologue_style` | str | 内心独白专属风格 | ✅(本会话接活) | 曾是"死字段" |
| 9 | `version` | int | 声音版本号(演变后递增) | — | 折叠时滚动 |

**本会话的关键修复**:审计 C5 #2 指出第 6/7/8 三节(`sentence_patterns` / `vocabulary_profile` /
`internal_monologue_style`)**零消费**——存了没人读,是 YAGNI 过度设计。讽刺点在于:prompt 锚的明明是
"叙述与**内心独白**",用的却是泛泛的 `style_summary`,而专门的 `internal_monologue_style` 躺着没人理。
本会话在 `_voice_anchor_block`(`app.py:930`)把这 3 节全部接进续写 prompt(代码标注 `# P3-d: 注入3个此前未用的声音节点`),9 节里如今 8 节有真实消费链。

### 1.2 哪些进续写 prompt:`_voice_anchor_block`

`app.py:930` 的 `_voice_anchor_block(st, focalizer)` 是声音进生成的唯一入口,产出两部分:

1. **焦点者声音锚**(叙述/内心独白贴这个声音):
   - 主锚 `style_summary` → "叙述与内心独白贴「焦三」的声音:…"
   - 依次追加 `catchphrases`(口头禅)、`tone_rules`(语气规则)、`internal_monologue_style`(内心独白风格)、
     `sentence_patterns`(句式)、`vocabulary_profile`(词汇倾向)、`reference_lines`(参考语感,取前 2)。
   - **声音待演变提示**:若该焦点者有 open 的 `voice_evolution_flag`,附加一段
     "{角色} 因下列情节声音正在转变,行文可体现这种变化:{reasons}"——让生成时就带上转变的苗头。

2. **登场角色对白声音速记**(各自在声,别串味):
   `list_voice_profiles()` 取所有角色的 `{character_id, style_summary, ...}`,每个截 30 字摘要,
   拼成 "焦三—冷峭爱反问;阿菱—絮叨好引俗谚",防止多角色同场时对白"一个腔调"。

> **设计要点**:声音是**生成时锚定(in voice)**,不是事后纠正。`check_ooc` 是兜底,不是主力。
> 物理上把声音特征喂进 prompt,让模型在"已经是这个角色"的状态下落笔。

### 1.3 事后校验:`check_ooc` + `validate_setting`

`store.check_ooc(character_id, dialogue)`(`store.py:1223`)对照 `ooc_signals` 规则扫描一段对话,
返回违规列表 `[{signal, line, severity}]`。当前是**确定性规则匹配**(`detection_method="rule"`):

- "长句"信号:`dialogue.split("。")` 后统计 >25 字的句子,>3 句则报"连续 N 句长句"。
- "感叹号"信号:`！` 出现 >2 次报警。
- "情感词/直接说"信号:命中 `["很高兴","我爱你","感谢","很开心","太好了"]` 任一则报"直接情感词"——
  这条精确对应 craft 引擎"身体先行/不命名情感"的禁令。

`validate_setting`(`store.py:1358`)把 `check_ooc` 编进设定校验大流程:对每个有 voice_profile 的角色,
抽出正文里含其名字的句子当对话,跑 OOC 检测,违规产出 `type:"personality_ooc"` 线索。

> **局限**:目前只有 3 类硬编码规则(长句/感叹号/情感词),`detection_method` 字段预留了非 rule 方法但未实现;
> "含角色名的句子≈该角色的对话"是粗糙近似(旁白提到角色名也会被当对话扫)。

### 1.4 声音随情节演变:flag → fold 闭环(本会话接通)

**审计 C5 #1 原文**:"弧光→声音演变全链路断裂——`affects_voice` 零消费、`voice_evolution_flag.status`
从不关闭(永远 open 的待办 inbox)、voice_sample 无生产者。三表名义协作,实则各自悬空。"

本会话把这条断链补成闭环,三段如下:

**① 触发(生产 flag)** — 两条路:
- 自动:`ingest.py:116` 读回正文时,LLM 抽 `voice_shift`(谁这章经历了创伤/背叛/身份剧变),
  对每条调 `store.add_voice_flag(who, seq, reason)`。
- 联动:`add_char_state(..., affects_voice=True)` 时(`store.py:1113`)自动 `add_voice_flag`——
  弧光质变若影响声音,自动挂一面"该更新声音了"的旗。

**② 标记存活** — `voice_evolution_flag` 表:`{character, trigger_chapter, reason, status='open'}`。
`list_voice_flags("open")` 取未消化的。注意 `trigger_chapter` 是命名收口后的唯一真源(旧库的 `seq` 已废,
见 commit 1595691 修的 schema drift)。

**③ 折叠进 profile(消费 flag)** — `store.fold_voice_flags(character_id, complete_fn)`(`store.py:700`),
半自动声音演变消化,流程:
1. 取该角色 open flags,无则直接返回 `{folded:0}`。
2. 取当前 `voice_profile`(可为 None)。
3. `build_voice_fold_prompt`(`critique.py:301`)把"当前指纹 + 各章演变信号"喂 LLM,
   要求输出**更新后**的指纹 JSON(必含 `style_summary`,选填 `tone_rules`/`catchphrases`)。
4. `parse_voice_profile_from_fold` 解析:坏 JSON 或缺 `style_summary` → 返回 None → **fail-soft 不改旧 profile**,
   返回 `{folded:0, degraded:True}`。
5. 成功:与旧 profile 合并(新值覆盖旧值)→ `set_voice_profile` → 对每条 flag 调 `resolve_voice_flag`(status→done)。

REST 出口:`POST /voice-flags/fold`(`app.py:596`),body 传 `character_id`,内部用 `hermes_complete`。
`resolve_voice_flag`(`store.py:694`)把 status 从 open 改 done——审计指出的"flag 从不关闭"问题就此解决。

> **闭环全貌**:情节发生 → ingest 抽 voice_shift / arc 的 affects_voice → 挂 flag → 续写时"声音待演变提示"
> 让转变苗头先渗进文字 → 攒够了人工(或定时)触发 fold → LLM 折叠进指纹 → flag 关闭、version 递增。
> 这是一条"边写边演变"的半自动管线,人保留最终触发权(不全自动改角色声音)。

---

## 2. 角色弧光系统(Character Arc)

### 2.1 事件溯源模型:角色是"事件叠加出来的"

scribe3 不把角色状态存成一张可变的卡片,而是存成一串**不可变的质变点(char_state)**,
读取时**累积合成**出某一时刻的快照。这就是事件溯源(event sourcing):状态 = 初始 + Σ 事件。

`char_state` 表一行 = 一个弧光质变点(`store.add_char_state`,`store.py:1094`):

| 字段 | 含义 |
|------|------|
| `character_id` | 哪个角色 |
| `chapter` | 哪一章发生(时间轴坐标) |
| `change_type` | 变化类型:`ability`(能力) / `relation`(关系) / `personality`(性格) / `composite`(复合) |
| `summary` | 一句话摘要 |
| `before_state` / `after_state` | 变化前/后快照(dict);after 按 change_type 归入对应键 |
| `trigger_event` | 触发事件 |
| `arc_phase` | 弧光阶段标签(如"觉醒前/试炼/质变") |
| `affects_voice` | 是否影响声音(True 则自动挂 voice flag) |
| `confidence` | `confirmed`(手动种)/ `inferred`(ingest 自动抽) |
| `ingest_seq` | ingest 回写时记,供 `purge_ingest` 幂等清理 |

`after_state` 的归口约定(`ingest.py:134`):
- `ability` → `{"ability_snapshot": {技能:状态}}`
- `relation` → `{"relation_snapshot": {对象角色:关系描述}}`
- `personality` → `{"personality_snapshot": "字符串描述"}`
- `composite` → 整个 dict 直接进

### 2.2 时点快照合成:`char_state_at`

`store.char_state_at(character_id, chapter)`(`store.py:1116`)是事件溯源的"读模型":
拉该角色 `chapter <= N` 的全部质变点,按章升序逐条叠加,合成出该时刻的完整状态:

```python
char_state_at("role:焦三", 7) →
{
  "character_id": "role:焦三",
  "as_of_chapter": 7,
  "abilities":  {"炼器": "入门→小成", "辨煞": "新得"},   # 历章 ability_snapshot 累积 update
  "relations":  {"role:云阳真人": "师徒→决裂"},          # 历章 relation_snapshot 累积 update
  "personality": "由怯转狠,信物不信人",                 # 取最后一次 personality_snapshot
  "arc_phases": [
     {"chapter": 3, "phase": "试炼",   "summary": "初下奈何谷"},
     {"chapter": 7, "phase": "质变",   "summary": "亲手毁了镇煞钉"}
  ]
}
```

合成规则:`abilities`/`relations` 用 `dict.update` 累积(后章覆盖前章同键),`personality` 取最后一次,
`arc_phases` 收集全部带 `arc_phase` 的记录(末项即"当前阶段")。
无任何记录时返回空骨架(空 dict + 空 list),不报错。

`list_char_states(character_id)`(`store.py:1143`)则是完整演进史(含 before/after/trigger),给前端"弧光时间线"视图看。

### 2.3 自动长出弧光:ingest 抽 char_state(本会话新加)

**审计前**:`char_state` 只能手动种,`char_state_at` 只被"手动查询框"和 mcp 消费,续写 prompt 不注入(C5 #3)。

**本会话(G4)**:`ingest.py:120` 让弧光"边写边长出来":
- `build_knowledge_extract_prompt`(`critique.py:359`)在原有 learned/did/voice_shift 三抽之外,新增 **arc 抽取**:
  "哪些角色本章经历了可量化的弧光质变——能力获得/丧失、重要关系建立/破裂、性格明显转折",
  每条列 `{who, change_type, summary, snapshot}`。
- `apply_delta` 遍历 `delta["arc"]`,过滤合法 change_type,`_resolve_char` 解析角色,
  `snapshot` 按 change_type 归入 `after_state`,调 `add_char_state(confidence="inferred", ingest_seq=seq)`。
- `parse_knowledge_delta` 对 `arc` 字段**向后兼容**:旧模型不返回 arc 时默认空列表,不破坏老调用。

于是:**写第 N 章 → 定稿 ingest 抽出弧光 → 写第 N+1 章时 `_arc_state_block` 把它喂回去**,弧光自反哺。

### 2.4 弧光注入续写:`_arc_state_block`(本会话接活)

`app.py:904` 的 `_arc_state_block(st, focalizer, chapter)`(审计 C5 #3 的修复):
取 `char_state_at(focalizer, chapter)`,把能力/关系/性格/当前阶段拼成约束块注入 prompt:

```
## 本章焦点者弧光状态(写作须贴合)
焦三:能力:炼器=入门→小成、辨煞=新得;关系:role:云阳真人=师徒→决裂;性格:由怯转狠;当前阶段:质变
```

意义:写第 7 章时,生成器**看得到**焦三此刻已经会炼器、已与师父决裂、性格已转狠——
不会再写出他还像第 1 章那样怯懦,也不会让他用一项他还没习得的能力。弧光成了写作的硬约束,而非摆设。

---

## 3. craft 引擎层(Craft Engine)

### 3.1 现状:8 个 ENGINES(题材无关写作引擎)

`craft.py` 是从 hermes-novel craft wiki 萃取、清洗掉科幻残留后的**纯常量/纯函数**模块
(无 DB/无网络,可离线单测)。核心是 `ENGINES` 字典,8 条题材无关的写作引擎:

| 引擎 | 中文名 | 一句话精髓 | 可量化判据 |
|------|--------|-----------|-----------|
| `body` | 身体先行 | 情感展示顺序永远是 身体→行动→沉默→语言;叙述者不命名情感 | L1微动作>L2覆盖动作>L3身体失控(全卷≤3次);叙述者 95% 闭嘴 |
| `temperature` | 温度曲线 | 每 500 字情绪温度至少变 1 次;四色(冷/暖/锐/杂) | 全章温度差≥2 级,不全冷不全锐 |
| `idle` | 闲笔 | 每章≥3 个与剧情无关但让世界/角色有温度的具体细节 | 至少 1 世界级 + 1 角色级;豁免契诃夫之枪 |
| `metaphor` | 认知比喻 | 每个比喻须让读者懂一件之前不懂的事,且来自角色专业领域 | 每章 2-4 个;三问筛(删了少懂啥/来自领域吗/后面有解释吗) |
| `subtext` | 潜台词 | 每章≥1 处"实际说的≠真正想说的",不在叙述里解释 | 三模式:屏障对话/转移话题/物理替代 |
| `sensory` | 感官锚定 | 每个关键场景≥1 个非视觉感官;环境承载情感 | 2-3 精准>5 泛泛;反复场景要有稳定"感官签名" |
| `soak` | 浸泡(贯穿) | 始终保持 POV 角色的声音——不是你在写,是角色在经历 | 环境/他人/情感全经该角色感知过滤 |
| `restraint` | 留白/减法 | 该不写的不写比写满更有力 | 信息冰山(只露 1/8)/情绪不解释/删装饰/冷笔收尾/一段一焦点 |

逐引擎细解:

- **身体先行(body)**:禁"他感到悲伤"。三层防御机制——L1 无意识微动作(最强,角色自己都不知道)>
  L2 覆盖动作(用另一行为盖住情绪,暴露防御)> L3 身体失控(想控制却失败,全卷≤3 次)。
  叙述者 95% 闭嘴,5% 例外仅用于"打破读者认知框架"的一句洞察,每章最多 1 句。
- **温度曲线(temperature)**:压抑≠恒温——表面平静时内部仍有微震(手指频率变了/呼吸变了)。
  三工具:节奏切换(长短句)、叙事距离跳跃(特写↔远景)、闲笔插入(高压后给读者一口气)。
- **闲笔(idle)**:必须具体到能画出来,不解释,放那里就好。豁免契诃夫之枪——闲笔不为推动剧情,是让世界活着。
- **认知比喻(metaphor)**:来自角色的专业领域(思维惯性冒出来,不是在"用修辞")。三问筛:
  ①删了它读者少理解什么?"没什么"→删(装饰比喻);②来自角色领域吗?否→重写;③后面跟解释句吗?有→删解释。
- **潜台词(subtext)**:三模式——屏障对话(心知肚明不说破)、转移话题(避真正想说的、谈无关日常)、
  物理替代(用一个动作替代该说的话)。角色避真话时往往谈论无关的日常事物。
- **感官锚定(sensory)**:每个关键场景至少 1 个非视觉感官(听/触/嗅/温度/本体感觉)。
  反复出场的场景应有稳定"感官签名"(读者闻到那股气味就知道身在何处)。
- **浸泡(soak)**:贯穿全程的 POV 一致性——与声音指纹的"叙述贴焦点者声音"是同一件事的两面。
- **留白(restraint)**:五条——①信息冰山(前史/设定只露 1/8);②情绪不解释(给身体/场景,
  不给"这意味着/他明白了");③删装饰;④克制收尾(章末冷笔定格,不升华不总结);⑤一段一焦点。

另:`craft.py` 还带一本 `PALETTE` 情感词典——15 种情绪(压抑的悲伤/被压住的恐惧/内疚/愤怒…),
每种给 `body`(身体信号)+ `inner`(内部感觉)具体清单,是"身体先行"引擎的弹药库(已删科幻词)。

### 3.2 接入续写:`build_craft_block`(本会话接活)

**审计 C4 #1 原文**:"craft 引擎层基本死——`build_craft_block`(把工艺规则注入渲染 prompt 的唯一入口)
**零生产调用,仅测试用**。"

本会话把它接进主链路:`build_craft_block(rules)`(`craft.py:147`)组装引导块——
8 引擎逐条列出(中文名 + 全文),再叠加本书题材规则。在 `chat_write` / `chat_write_post`
(`app.py:1116` / `1206`)调 `build_craft_block(st.list_craft_rules() or None)` 拼进 instructions。craft 引擎层从"展示性死表"变成真正进生成 prompt 的工艺约束。

### 3.3 题材规则:`craft_rule`(per-work 正则)

引擎层是题材无关的;**题材特化**放在 per-work 的 `craft_rule` 表(`store.add_craft_rule(kind, pattern, note)`):

- `kind="purple_regex"`:本书"升华句/翻译腔"黑名单正则。`purple_patterns()` 把它喂
  `critique.find_purple_prose` 的 `extra_patterns`,做事后 QC。`seed_craft_rules()` 给乱世铜炉系种了 8 条
  实证升华句正则(如 `天地为炉|万物为铜`、`原来.{0,30}(就|早就|从一开始)`、`从.{1,18}那一刻起`)。
- `kind="artifact_craft"`:法器/法术首次出场须"四件套"(专名+工艺工序+术数+义理,至少齐 3 项)。
- `kind="cover_action"`:(枚举预留)

> **审计遗留**:`artifact_craft` / `cover_action` 两枚举**目前仍无消费者**——seed 了数据也只是进
> `build_craft_block` 的"本书题材规则"文字段落,没有专门的校验逻辑去验证"四件套齐没齐"。
> 唯一有闭环的题材规则是 `purple_regex`(反向喂 QC)。这是下一步要补的(见 §4)。

### 3.4 母题:motif(贯穿编织 + 防误删白名单)

`motif` 表 `{name, theme, echoes, unfolding}`(`store.add_motif`):

- `name`:母题名(如"炉/铜""老槐树""回不去的故乡")。
- `theme`:它承载的主题。
- `echoes`:历次回声/复现点。
- `unfolding`:展开计划。

**两条用途**:
1. **主动编织(本会话接活)**:`_motif_block`(`app.py:1002`)把 `name:theme（回声:echoes）` 列进续写 prompt,
   标题"## 贯穿母题(可主动编织)",上限 5 条。这是审计后新增——此前母题**不进任何 prompt**(C4),
   `theme/echoes/unfolding` 全是死字段,母题只靠 `name` 做被动防误删。
2. **防误删白名单**:`motif_terms()`(`store.py:829`)把母题名各部分(≥2 字)+ 少量物名/地名/书名
   (镇煞钉、奈何谷、大元炼真经、清潭派…)收进白名单,跨章复读检测时**放行**——
   乱世铜炉式母题本应复现,只揪"动作/句式偷懒重打",不误伤刻意复现的母题。

### 3.5 北极星:intent(reader_feeling / emotional_arc / red_lines)

`intent` 是单例记录 `intent:main`(`store.get_intent` / `set_intent`,`store.py:854`):

| 字段 | 含义 |
|------|------|
| `reader_feeling` | 想让读者产生什么感受(最高目标) |
| `emotional_arc` | 全书情感弧线 |
| `red_lines` | 绝不背叛的红线(角色/主题底线) |
| `overdue_threshold` | (可选)伏笔逾期阈值,覆盖模块默认 `OVERDUE_SLACK` |

**注入点**:`_editor_system`(`app.py:683`)把三项拼进主编系统提示——
"【北极星·作品意图】读者感受:…;情感弧:…;绝不背叛的红线:…"。

> **关键局限**:北极星**只进主编对话/写作系统提示**(`_editor_system` → `_editor_write_system`),
> 而 `_voice_anchor_block` / `_arc_state_block` / `_motif_block` 那条逐章渲染链路里**没有单独的北极星块**。
> 因为 `chat_write` 的 instructions 是 `_editor_write_system(st)` 起头(已含 intent),逐章写作能间接看到;
> 但 intent 在这条链路里是"埋在系统人格里的一句话",没有像母题/弧光那样被提成显式、可被模型反复对照的约束块。

---

## 4. 全网工艺调研 + 差距与改进

> 本节对照专业写作工艺评估三套系统,并给逐条改进方案。工艺要点来自对作家教学资源的检索
> (Writers Helping Writers / K.M. Weiland / Reedsy / Jane Friedman / The Write Practice 等,见文末出处)。

### 4.0 工艺调研提炼(四大主题)

**A. 角色声音可辨(distinct voice)** — 来源:Helping Writers Become Authors、Ellen Brock。
1. 专属**词汇库 + 拒用词**:每人一套独占高频词 + 一套绝不会说的词(教育/阶层/世代标记)。
2. **句法节奏分层**:声音真相不在单个用词,而在节奏与构造——啰嗦角色流水长句,寡言角色顿挫短句/碎片。
3. **比喻取材锚定身份**:角色打的比方来自其职业/地域/心理世界(工程师用技术黑话,水手用航海词)。
4. **五维身份决定说话方式**:出身/教育/职业/世界观/世代,共同决定词汇复杂度、语法、文化梗、俚语。
5. **沉默与回避也是声音**:用"不说什么"、犹豫、对特定话题拒谈来塑形;整体话量多少本身是区分项。
> 核心硬指标——**遮名测试**:删掉所有"X 说"和人名,读者能否仅凭用词/句式/节奏认出谁在说话?

**B. 对话潜台词(subtext)** — 来源:K.M. Weiland、Jerry Jenkins、Inside Creative Writing。
1. **去 on-the-nose**:先明确真正想传达的点,然后绝不直白说出——侧面切入/说反话/动作暗示。
2. **意外回应/闪避**:对直接提问不给显而易见的答案(误解/反讽/撒谎/岔开/答非所问)。
3. **谈第三件事(The Third Thing)**:两人不直谈彼此情绪,而谈一个"第三物"(天气/家具/一道菜)作隐喻。
4. **物理替代(action beats)**:用动作/对物体的处理代替说不出口的情绪(反复擦杯子、摘下又戴上戒指)。
5. **冰山五载体**:台词(说反话)/肢体(假笑回避)/生理(口干手抖,不受控)/内心独白(与台词反讽对照)/声音线索(音量音高失控)。
> 判定:**目标对撞**——给每个说话者一个"此刻想要的"+一个"绝不肯承认的",张力自动生成潜台词;
> 台词与肢体/生理/内心若存在可检出的**矛盾**,矛盾即潜台词信号。

**C. 人物弧光 want vs need + lie/ghost/truth** — 来源:K.M. Weiland(character-arcs-2/3)。
- **Ghost(创伤)**:过去一个**具体事件**,催生了角色相信的谎言。
- **The Lie(谎言)**:一句话可陈述的核心错误信念(关于自我/他人/世界),是所有缺陷的根因,开篇甚至看着像优点。
- **The Truth(真相)**:谎言的正反面,高潮处角色必须接受并据此行动。
- **Want**:外在/具体情节目标(钱/权/爱/生还),谎言驱动的虚假解药,与情节绑定。
- **Need = 真相**:无形普世的领悟("我值得""人可信"),与弧光和主题绑定。
- **高潮二选一(苦甜时刻)**:角色通常须**牺牲 Want 才能得到 Need**。
```
Ghost → The Lie ←对立→ The Truth → Need(内在)
                │派生
            症状(恐惧/羞耻/秘密)→ Want(外在目标,虚假解药)
                                        ↓
                       高潮:被迫在 Want 与 Need 间二选一
```

**D. 母题(motif)与主题(theme)主动编织** — 来源:NY Book Editors、Jericho Writers、YourDictionary。
1. **母题 ≠ 主题**:主题=抽象单一的整体意义;母题=具体可触、反复出现的元素。**母题是重复的证据,主题是重复的意义**。
2. **先锚主题再选母题**:母题服务主题,不是装饰。
3. **变其形不变其义**:同一母题可换形态(钟/表/沙漏=同一个"时间"母题)。
4. **复现中深化(多义生长)**:好母题每次出现都让含义加深/转向(火:净化→情欲火花→被扼杀的创造力)。
5. **明显即败笔(organic)**:绝不直白点破象征,靠累积让读者潜移默化通向主题;有意复现 **3-4 次**、落点对齐关键情节。

### 4.1 对照评估:本系统的领先与差距

**领先的设计**(优于多数 AI 写作工具):
- **声音是生成时锚定 + 事后校验双保险**:`_voice_anchor_block` 在生成时把声音特征喂进 prompt(in voice),
  `check_ooc` 事后兜底——比纯靠 prompt 一句话"保持角色性格"扎实得多。
- **声音随情节演变有闭环**:`voice_shift → flag → fold → version++` 是一条罕见的"角色声音会成长"的管线;
  多数系统的角色声音是静态卡片,从第 1 章到第 100 章一个腔调。
- **弧光是事件溯源、时点合成**:`char_state_at` 让"写第 N 章看到第 N 章的角色"成立,且能自动从正文抽取(G4)。
- **声音速记防串味**:"登场角色对白声音"速记直接对应工艺 A 的"逐角色编辑/声音速记卡"。

**对照工艺的六处差距**(逐条改进):

#### 改进① 对白潜台词:从"引导"到"结构化支持 + 校验" ★★★
- **现状**:craft 的 `subtext` 引擎只是一段文字引导(每章≥1 处、三模式),无任何结构化支持、无校验。
- **工艺**(主题 B):潜台词的核心是"台词与肢体/生理/内心的**可检出矛盾**"+"目标对撞(想要的 vs 不肯承认的)"
  +"谈第三件事"。这些都是可操作、可检测的具体手法,不只是"写得含蓄点"。
- **改法**:
  1. 给场景级注入一个**潜台词支架**:在续写 prompt 里,对"本场两个主要角色"各填一行
     "此刻明面想要 X / 绝不肯承认 Y",让模型据对撞自动生成潜台词(而非空喊"加潜台词")。
     数据可从 char_state 的当前 relations + 角色 `surface_goal`/`deep_need` 派生(见改进②)。
  2. 做一个**轻量潜台词校验**(`critique.py` 加 `find_on_the_nose`):正则扫"直陈情绪/意图"句式
     (如"他想说……""她心里其实……""我很生气/我爱你"等直白宣告),作为低 severity 提示——
     命中即"这里 on-the-nose 了,考虑改成动作/第三物"。可复用 `check_ooc` 已有的"直接情感词"清单扩充。
  3. craft 引擎的 `subtext` 文字补一句**矛盾载体**口诀:让台词与至少一个非台词通道(肢体/生理/内心)相左。
- **优先级**:★★★(潜台词是"文学感"的命门,且当前几乎只有一句引导)。

#### 改进② 弧光维度:补 want-vs-need / lie / ghost(其实地基已在,只差接线) ★★★
- **关键发现**:`character` 表**已经有** want-vs-need 的字段地基——
  `surface_goal`(想要/表层目标)、`deep_need`(需要/深层需求)、`internal_conflict`(内在冲突)、`fear`(恐惧),
  在字段白名单(`store.py:109`)、CRUD 端点(`app.py:251-254`)、前端 CodexView 表单里都齐了。
  **但这四个字段当前只被读出来当 API 响应序列化(`app.py:177-180`),从不注入任何写作 prompt**——
  存了、能编辑,却进不了生成。这正是审计"主题 D 卖点空心化"的同型病:字段看得见,不落地。
- **工艺**(主题 C):want(surface_goal)= 谎言驱动的虚假解药;need(deep_need)= 真相;
  二者在高潮处对撞。还缺两个 Weiland 框架的关键件:**the lie(一句话核心错误信念)** 和
  **the ghost(催生谎言的具体过去事件)**——这两个目前 character 表没有。
- **改法**:
  1. **接线(零建表,立即可做)**:在 `_arc_state_block` 旁加一个 `_motivation_block`,把焦点者的
     `surface_goal`/`deep_need`/`internal_conflict`/`fear` 拼成"## 焦点者驱动力(写作贴合)
     表层想要:…;深层需要:…;内在冲突:…;恐惧:…"注入续写 prompt。一行接线,激活已有四字段。
  2. **补两字段(小建模)**:character 表加 `the_lie`(一句话错误信念)+ `the_ghost`(催生谎言的具体往事),
     与 surface_goal/deep_need 一起构成完整 Weiland 弧光地基。
  3. **弧光阶段校验**:`char_state.arc_phase` 已存在但无校验——可加一条"高潮章是否出现 want 让位于 need 的抉择"
     的体检提示(对照 intent.emotional_arc 的高潮章号)。
- **优先级**:★★★(地基已建好,接线成本极低,收益是"角色有内在驱动")。

#### 改进③ 北极星只进主编、不进逐章渲染块 ★★
- **现状**:`intent`(reader_feeling/emotional_arc/red_lines)只在 `_editor_system` 拼进**主编系统人格**;
  逐章渲染链(voice/arc/motif/frame/craft)里没有独立的、可被模型反复对照的北极星块。
- **工艺**:主题 D 的"先锚主题再选母题/写每一段都对齐核心信息"要求**主题在每一处落笔时可见**,
  而不是埋在系统人格的一句话里。
- **改法**:加 `_intent_block(st)` 注入续写 instructions,用显式标题
  "## 北极星(每段落笔都对齐)读者感受:…;情感弧此刻位置:…;红线(绝不触碰):…"——
  与母题块并列,让 emotional_arc 能按当前章定位(配合改进②的高潮抉择校验)。
- **优先级**:★★(低成本,显著提升"全书一口气"的一致性)。

#### 改进④ 母题只做"防误删 + 提示出现",没"主动编织/复现追踪" ★★
- **现状**:`_motif_block` 已把 name/theme/echoes 注入(本会话接活,已是进步),`motif_terms` 做防误删白名单。
  但系统不知道某母题"已复现几次、上次在哪章、这次该不该深化"——只是被动提示"可主动编织"。
- **工艺**(主题 D):编织 = 有意复现 3-4 次 + 每次变形守义 + 每次深化转义 + 不点破。
  `unfolding` 字段(展开计划)正是为此设计,却仍未消费。
- **改法**:
  1. **复现追踪**:ingest 抽取时识别母题命中(用 `motif_terms` 比对正文),记 `motif_occurrence{motif, chapter}`;
     `_motif_block` 注入时附"本母题已现于第 X、Y 章,这次宜深化为 Z"(读 `unfolding` 计划)。
  2. **密度检查**:体检加"某母题埋了 setup 但 N 章未复现"的提醒(类比伏笔 overdue 逻辑),防母题断更。
  3. 让 `echoes` 字段在每次复现后由 ingest 自动追加,形成母题的"回声史"。
- **优先级**:★★。

#### 改进⑤ 声音可辨度无量化(遮名测试缺失) ★★
- **现状**:有生成时锚 + check_ooc,但没有"角色间声音区分度"的任何度量——无法回答"焦三和阿菱说话像不像"。
- **工艺**(主题 A):核心硬指标是**遮名测试**——删人名后能否认出谁在说。这可半自动化。
- **改法**:加一个声音区分度体检 `voice_distinctiveness`:对一章里两个角色的对白集,
  抽句长分布 + 标志词命中 + 标点习惯,算一个简单距离;过近则提示"两角色对白同质化,检查声音锚是否在生效"。
  进阶可用 embedding 算对白向量的角色间距离。同时把"遮名测试"写进 craft 的 soak/voice 引导。
- **优先级**:★★。

#### 改进⑥ fold 触发时机:纯人工,易积压 ★
- **现状**:`fold_voice_flags` 只能人工触发(`POST /voice-flags/fold`)。open flag 可能长期不消化,
  "声音待演变提示"会一直挂着(虽然 fail-soft 不出错,但演变迟迟不落地)。
- **改法**:加触发策略——(a)某角色 open flag 数 ≥ 阈值(如 3 条)时,在体检/写作前提示"建议消化声音演变";
  (b)Hermes 有 cron/skills 能力,可挂一个定时巡检 job 自动 fold(保留人工复核)。注意 fold 改的是角色声音,
  应保留人最终确认权,不宜全自动。
- **优先级**:★(体验优化,非正确性问题)。

> **关于 voice_sample**:审计 C5 提到的 `voice_sample` 表(及 `latest_voice_samples` 时间门)在当前代码中
> **已不存在**——职责与 `voice_profile.reference_lines` 重叠,已被移除。本文不再将其列为待办;
> 若未来要做"从正文自动回灌真实台词样本",应直接进 `reference_lines`,不重建独立表。

---

## 5. 改进方案总表(按优先级)

| # | 维度 | 现状 | 工艺缺口 | 改法 | 优先级 |
|---|------|------|---------|------|:---:|
| 1 | 对白潜台词 | craft 有 subtext 引擎(纯文字引导) | 无结构化支持、无校验 | 见 §4 改进①:潜台词标注 + 校验 | ★★★ |
| 2 | 弧光维度 | char_state 记 ability/relation/personality;character 表已有 surface_goal/deep_need/internal_conflict/fear 但**从不进 prompt** | 缺 lie/ghost;已有 want/need 未接线 | 见 §4 改进②:接线已有四字段(零建表)+ 补 the_lie/the_ghost | ★★★ |
| 3 | 北极星渲染 | intent 只进主编系统提示 | 逐章渲染无显式北极星块 | 见 §4 改进③:加 `_intent_block` 进逐章链 | ★★ |
| 4 | 母题编织 | _motif_block 已注入 | 只"提示出现",无"复现密度/进展"校验 | 见 §4 改进④:motif 编织追踪 + 密度检查 | ★★ |
| 5 | 声音可辨度 | 生成时锚 + check_ooc | 无"角色间声音区分度"量化 | 见 §4 改进⑤:声音区分度指标 | ★★ |
| 6 | fold 触发时机 | 纯人工触发 /voice-flags/fold | 攒了 flag 可能长期不消化 | 见 §4 改进⑥:fold 触发策略 | ★ |
| 7 | 题材规则校验 | artifact_craft/cover_action 无消费者 | 只进文字、不验证 | 把"四件套齐 3 项"做成确定性校验喂 QC | ★ |

---

## 附录 A · 9 节声音指纹速查表

(见 §1.1 表)

## 附录 B · 8 craft 引擎速查表

(见 §3.1 表)

## 附录 C · 弧光时点快照示例

(见 §2.2 代码块)

## 附录 D · 关键文件与函数索引

| 功能 | 文件:函数 |
|------|-----------|
| 声音指纹存取 | `store.py: set_voice_profile / get_voice_profile / list_voice_profiles` |
| 声音事后校验 | `store.py: check_ooc / validate_setting` |
| 声音演变 flag | `store.py: add_voice_flag / list_voice_flags / resolve_voice_flag` |
| 声音折叠闭环 | `store.py: fold_voice_flags` + `critique.py: build_voice_fold_prompt / parse_voice_profile_from_fold` |
| 声音注入续写 | `app.py: _voice_anchor_block` |
| 声音演变 REST | `app.py: POST /voice-flags/fold` |
| 弧光质变点 | `store.py: add_char_state / char_state_at / list_char_states` |
| 弧光自动抽取 | `ingest.py: apply_delta` (arc 段) + `critique.py: build_knowledge_extract_prompt` |
| 弧光注入续写 | `app.py: _arc_state_block` |
| craft 引擎 | `craft.py: ENGINES / PALETTE / build_craft_block` |
| 题材规则 | `store.py: add_craft_rule / purple_patterns / seed_craft_rules` |
| 母题 | `store.py: add_motif / list_motifs / motif_terms` + `app.py: _motif_block` |
| 北极星 | `store.py: get_intent / set_intent` + `app.py: _editor_system` |

## 附录 E · 工艺调研出处

**声音可辨**:Helping Writers Become Authors《Top 14 Tips for Unique Character Voices》
https://www.helpingwritersbecomeauthors.com/character-voices/ ·
Ellen Brock《Distinct Character Voices》https://ellenbrockediting.com/2016/07/25/how-to-write-dialogue-with-distinct-character-voices-novel-boot-camp-15/ ·
知乎 https://www.zhihu.com/question/20355902

**对话潜台词**:K.M. Weiland《How to Write Subtext in Dialogue》
https://www.helpingwritersbecomeauthors.com/subtext-in-dialogue/ ·
Jerry Jenkins《Subtext Examples》(冰山五载体)https://jerryjenkins.com/subtext-examples/ ·
Inside Creative Writing《The Third Thing》https://insidecreativewriting.com/character-development/writing-subtext-in-dialogue/

**人物弧光(want vs need / lie-ghost-truth)**:K.M. Weiland《Character Arcs Pt.2 — The Lie》
https://www.helpingwritersbecomeauthors.com/character-arcs-2/ ·《Pt.3 — Want vs Need》
https://www.helpingwritersbecomeauthors.com/character-arcs-3/ ·
The Novel Smithy https://thenovelsmithy.com/want-versus-need-storytelling/ ·知乎 https://zhuanlan.zhihu.com/p/56127397

**母题与主题**:NY Book Editors《How to Use Motifs》
https://nybookeditors.com/2020/02/motifs-in-storytelling-how-to-use-this-literary-element-to-weave-a-stronger-story/ ·
Jericho Writers《How to Incorporate Motifs》https://jerichowriters.com/how-to-incorporate-motifs-in-your-writing/ ·
YourDictionary《Theme vs Motif》https://www.yourdictionary.com/articles/theme-motif-differences-connections ·
知乎 https://zhuanlan.zhihu.com/p/515939125
