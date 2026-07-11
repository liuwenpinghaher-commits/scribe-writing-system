---
name: scribe-novel-v2
title: Scribe 主编 v2 · 故事本体驱动的限知写作
description: "用 scribe3 MCP 工具按【设计fabula→冻结知识帧→渲染sjuzhet→校验→待批落库】写长篇。限知靠知识帧投影、不靠判官;读自动答,写经 elicitation 待批。"
version: 0.1.0
author: scribe3
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Writing, Novel, Ontology, POV, Knowledge, SurrealDB, Scribe3]
    mcp_server: scribe3
---

# Scribe 主编 v2 · 故事本体驱动的限知写作

> 本 skill 是**按需查阅的写作工序参考**(fabula→知识帧→sjuzhet→校验→待批落库),讲"这道工序怎么做"。
> 强制纪律不在此,由三层承载:①恒定纪律(剧情事实只进 SurrealDB、不进 Hermes memory;s3_ 必带
> work;写入必待批)在 profile SOUL.md;②讨论/动稿围栏协议、限知宪法等强制纪律 prompt 内嵌
> (每轮 instructions);③结构性兜底(网关 work-scoped MCP、只暴露 s3_ 只读工具、写入走 elicitation)。
> 下面只沉淀**做法**,不重复"必须遵守"的约束。

工序的两条方法论支柱(是做法,不是这里执行的纪律):
1. **SurrealDB 是剧情真相的数据源**(NS=scribe3):世界/事件/事实/知识都在库里,读写都经 s3_ 工具。
2. **限知靠知识帧投影、不靠判官**:渲染某视角前,先投影出该角色的知识帧,只把帧内事实喂生成——他不知道的,物理上写不进去。判官只兜底。

## 工具(scribe3 MCP,均 s3_ 前缀)
- **读(自动用)**:`s3_project_frame`(某 focalizer 截至某章知道什么=渲染输入)、`s3_render_scene`(限知视角渲染本章,只读)、`s3_find_leaks`(兜底 POV 判官)、`s3_causal_complete`(连贯性查询)、`s3_dramatic_irony`(反讽点:读者知而视角不知)、`s3_semantic_recall`(语义召回相关设定,非字面)、`s3_hybrid_recall`(RRF 混合召回)、`s3_graph_recall`(GraphRAG 知识子图)、`s3_chapter_recall`(章节语义召回)、`s3_setting_completeness`(设定完整性检查)、`s3_list_world_rules`(世界规则)、`s3_list_factions`(势力)、`s3_character_state`(角色弧光状态快照)、`s3_character_timeline`(角色弧光时间线)、`s3_relations_at`(角色关系图)
- **写(经 elicitation 待批)**: `s3_add_character` `s3_add_fact` `s3_add_event` `s3_record_knowledge` `s3_add_character_relation` `s3_add_world_rule` `s3_add_faction` `s3_add_char_state`——执行前会弹批准给作者,accept 才落库(拒绝/超时=不写)
  - **Pitfall**: `s3_add_fact` REQUIRES the `oid` field, not just `entity`. Both are needed and must match. Omit `oid` and you'll get a validation error: "Field required".

## 写一章(必走的环)
0. **设定完整性检查(开写前)**:调 `s3_setting_completeness` 看缺什么。若缺世界规则/势力/角色深描,主动提出 2-3 个选项让作者决策(不是让作者填表,而是主编引导:"你的魔法体系有什么代价?""这个势力的公开面目和私下运作是什么?")。作者确认后用 `s3_add_world_rule`/`s3_add_faction` 落库。
1. **设计 fabula**:把本章要发生的事建成 `s3_add_event`(挂 motivated_by_goal);相关状态建 `s3_add_fact`(私密底细置 `secret=true`)。
2. **冻结知识帧**:选本场 **focalizer**(一场一 POV,不 head-hop)→ `s3_project_frame(focalizer, 章)` 看他此刻知道什么。这就是渲染能用的全部事实。
2.5. **取前文已用措辞(防跨章复读·开写前必调)**:调 `s3_recent_phrases(章)` 拿前 3 章的独特措辞/意象清单(`avoid`)。**本章生成时逐字避开**这些句式与意象——单遍长程生成的"复读病"是模型跨章复用自己偏爱的招式(实测第2章逐字搬运第1章「胡不为惨叫一声」「嗡鸣声越来越响」「要从嗓子眼里蹦出来」等 14 处),逐章 QC 查不到。同一个意思,本章另寻表达(换感官、换喻体、换节奏),别原样重打。
3. **渲染 sjuzhet**:`s3_render_scene(focalizer, 章)`——只吃知识帧,帧外私密绝不出现;并避开 2.5 的 `avoid` 清单。直接出正文,不要元叙述。
4. **存稿**:`s3_save_chapter`(草稿,直接存,不待批)。
5. **QC 闸(按序)**:`s3_qc_chapter`(确定性:复读/排比/升华→定向删)→ `s3_cross_repetition(章)`(**跨章逐字复读**:逐章 QC 的盲区;count>0 即调 `s3_dedup_cross(章)` 确定性定向改写犯规句,拿回 prose 用 `s3_save_chapter` 存回——实测最严重章 30→8、↓73%,比 prompt 预防可靠)→ `s3_discipline_check`(LLM 判官:双高潮/声音崩/解说倾泻,确定性盲区;违规且复发点靠后→截到 cut_after,太早则交回重写)→ `s3_find_leaks`(兜底扫 POV 泄露)。
6. **落库世界(待批)**:章内新发生的事实/知识用 `s3_add_fact`/`s3_record_knowledge` 记(看见即知道:在场者才获知)；埋/收伏笔用 `s3_plant_promise`/`s3_advance_promise`——均弹批准。
7. **回写闭环**: `s3_ingest_chapter`(客观回写,已**不待批**;后端存稿时也会自动后台跑同一逻辑)——读定稿抽"各角色新知道什么/做了什么且谁看见"→更新知识账本。**下一章限知渲染据此反映新知**(谁这章知道了什么,下章他就能用、别人仍不知)。
  - **Pitfall**: If `s3_ingest_chapter` fails with "Couldn't coerce value... Expected `int` but found `NONE`", this indicates a voice profile or character state record is missing a required chapter anchor. The save still succeeded; the background auto-ingest will typically retry successfully later.
8. **后台综合体检(delegate,不阻塞)**:存稿后可 `delegate_task(background=true, prompt="对第N章做综合体检:依次 s3_qc_chapter / s3_discipline_check / s3_find_leaks / s3_causal_complete,综合判断哪些是真问题(别堆噪声),写一份精炼体检报告")`——后台 subagent 自主跑多步,你**立刻继续写,不等**。报告下次取。(确定性回写已由第7步/后端自动管;这里 delegate 的是需要多步判断的体检。)
9. **章成自检(自进化)**:本章有没有摸出一条**可复用修法**(某类坑的解/某腔调的立法/某道 QC 序列)?有 → `skill_manage(action="patch")` 追加进本 skill 对应段(见下"技能自进化")。只沉淀**流程/craft**,不沉淀剧情事实(事实进 SurrealDB)。

## 写作纪律(craft · 引擎层题材无关,渲染端已程序化注入 `scribe3/craft.py`)
渲染前先**浸泡**(`soak`):以 focalizer 身份过一遍本场,定情感曲线+种子词。落笔守七引擎:
- **身体先行**:情感经 身体→行动→沉默→语言;不命名情感;L3 失控全卷≤3 次;叙述者 95% 闭嘴。
- **温度曲线**:每 500 字一震,冷/暖/锐/杂,全章温差≥2 级;压抑≠恒温。
- **闲笔**每章≥3(豁免契诃夫之枪);**潜台词**每章≥1;**认知比喻**来自角色领域、后不跟解释;**感官锚定**每场≥1 非视觉感官。
- 需要某情感的身体信号时查 `s3_emotion_palette`(选 2-3 个编织,勿堆砌)。
- show 不 tell;冷笔动作收尾,不喊升华口号;单一戏剧主线,不双高潮、不偷跑后续章;用了力量必付代价。
- 本书题材规则(升华句/法器写法)见 `s3_craft_rule_list`;负面禁令由 `s3_qc_chapter` 后置兜底,不必写时分心。

## 设定动静结合(世界观基石 vs 剧情演变)
设定分两层:**静态基石**(世界规则/角色核心性格/势力意识形态——不变)和**动态演变**(角色能力成长/关系变化/势力兴衰——随剧情变)。
- **静态基石**用 `s3_add_world_rule`(Sanderson 式:源头/能力/代价/限制/例外)和角色 `traits`/`motivation` 固化。
- **动态演变**用 `s3_add_char_state` 记录弧光质变点(能力突破/关系升级/性格转折),带章锚点。查某章状态用 `s3_character_state`(合并所有 CharState 到该章的快照)。
- **关系演变**:`s3_add_character_relation` 带 `since_chapter`;关系变化时旧的设 `until_chapter`,新建一条。查某章关系用 `s3_relations_at`。
- **主编引导**:每写新章前,若发现角色经历了质变(绝境共战/重大背叛/能力突破),主动提示"这个角色这章发生了弧光变化,要不要记录?"——用 `s3_add_char_state` 落库。
每当你摸索出一条**可复用的写作修法**(某类坑的解、某个腔调的立法、某道 QC 序列),用 `skill_manage(action="patch", ...)` **小补丁**把它追加进本 skill 对应位置——下次自动用上。规矩:
- **只沉淀【流程/craft】,不沉淀【剧情事实】**(事实进 SurrealDB,不进 skill)。
- **patch 往对应 anchor 段**:craft/腔调修法 → 「写作纪律」段;流程/QC 序列修法 → 「写一章的环」对应步。patch 小补丁、非重写;创建/删除前确认作者意图;受 skills_guard 安全扫描。
- 这把手工挖的修法变成可审查、可回滚(git)、可分发的资产。

## 工序前提(架构约束,供参考)
SurrealDB 是真相源 / Hermes 是平台(主编只调工具不碰库)/ 渲染只读(投影 fabula∩知识帧,绝不回写)。这三条是本工序运转的架构前提,详见 `docs/superpowers/plans/2026-06-22-scribe3-开发标准.md`。
