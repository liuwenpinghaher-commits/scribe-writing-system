# D · 本体规范化(地基枢纽)

> 对象:**scribe3**。本枢纽把混乱的命名/枚举/分类规范化,是其他枢纽(尤其 **B 图枢纽**、**E 性能与索引**)的**地基**:命名与枚举统一后,B 才能在干净基础上建图边、升 RecordLink,否则在漂移的字段名上建图是返工。
> 聚合诊断:[04-本体论实现分析与改进方案](../系统架构/04-本体论实现分析与改进方案.md)(§4 分类体系、§5 语义一致性、§8.1 统一词汇表、§8.2 目标 Schema)+ P32(SCHEMALESS 收紧)。
> 生成日期:2026-06-24。本文是**方案文档**,不真改代码;所有引用为 `文件:行号`,基于全库只读扫描。

---

## 1. 概述

### 1.1 本枢纽聚合的问题

scribe3 的本体论被诊断判为 **L2.5**(关联数据→显式语义之间),最薄弱的一环正是"语义一致性"(`04` §5,判定 L1)与"属性约束"(`04` §4.2,判定 L1.5)。本枢纽聚合以下五类问题:

| 编号 | 问题 | 诊断证据 |
|---|---|---|
| **D-枚举** | **全库零正式枚举**:无 Python `Enum`/`typing.Literal`、无 SurrealDB `ASSERT $value IN [...]`。所有枚举域只活在注释与默认值里。 | `04` §4.2;`ontology.py:20,52`、`001:29,40` |
| **D-命名** | **命名极度不一致**:① "第N章"整数语义散成 **12 个字段名**;② `kind` 一名五义;③ 标识符/角色多名;④ 同一对象跨表/类/路径/UI 四名。 | `04` §5.1-5.3 |
| **D-死值** | **死值/越界值**:`acquired_via` 漏 `learned`(实际在写)、`craft_rule.kind` 的 `cover_action`(零产出)、`voice_evolution_flag.status` 的 `done`(无写入路径)。 | `04` §5.4;`ingest.py:31`、`008:4`、`store.py:342` |
| **D-P32** | **SCHEMALESS 收紧**:007/008/009(intent/craft_rule/voice)最该受约束却最松——表级 `SCHEMALESS`。 | P32;`007:4`、`008:3`、`009:3,17` |
| **D-taxonomy** | **分类全扁平**:`Entity.kind` 无子类型、`Event.type` 完全自由字符串,无受控域、无层级。 | `04` §4.1,§4.3 |

### 1.2 目标

一句话:**给地基浇钢筋**——用三件事把"高立意、欠地基"中的地基补齐。

1. **统一词汇表(Glossary)**:一处一名。每个概念有唯一规范代码名 + 定义 + 明令禁用的错名,覆盖"章时间 / 标识符 / 角色 / 文本 / kind"五组。
2. **枚举受控**:补 Python `Enum`(`EntityKind`/`AcquiredVia`/`PromiseKind`/`PromiseStatus`/`VoiceKind`/`FlagStatus` 等)+ 对应 SurrealDB `ASSERT $value IN [...]`,让 DB 在落库层直接拒绝脏值(不再依赖 LLM 自觉)。
3. **命名一致 + 死值清理**:把 `story_time`/`etype`/`entity_id` 等跨层换名收敛到规范名;`learned` 正式入枚举,`cover_action`/`done` 标"需人工确认"。

> **范围红线**:本枢纽**只做**"命名 / 枚举 / 分类"的规范化与约束。它**不做** Event 持久化、RecordLink 升级、角色关系图、Graph RAG——那些属于 **B 图枢纽**,本枢纽是其前置。本枢纽的 SurrealDB 改动**不动** `_execute_write` 单一落库点(开发标准不变量1),只在迁移层加 `ASSERT`/`DEFINE FIELD`。

---

## 2. 背景与动机

### 2.1 诊断 L2.5 判定与本枢纽的关系

`04` 的分维度判定(§1)把本枢纽涉及的两维打到最低:

| 维度 | 诊断层次 | 关键证据 |
|---|---|---|
| 属性约束 | **L1.5** | 核心表有 `TYPE`/`ASSERT len>0`,但**全库零枚举约束**(`04` §1 雷达) |
| 语义一致性 | **L1** | 命名极度混乱:同概念多名(章=12 名)、同名多义(`kind`×5)、跨层四名(`04` §5) |
| 分类层级 | **L1** | grep `parent/subtype/extends/is_a` 零命中,全扁平(`04` §4.1) |

诊断的**总判定原文**(`04` 文末):"scribe3 的本体论是**高立意、欠地基**……零枚举、命名混乱、单一图边、事件持久化失效四块短板,让它实际停在 L2.5。**第一阶段(统一词汇表 + 补枚举约束 + 引用完整性)是 ROI 最高的本体投资**——小工作量即可把高立意从被地基侵蚀中解救出来。" 本枢纽正是这"第一阶段"中**命名 + 枚举**两块(引用完整性 RecordLink 划归 B)。

### 2.2 为何命名/枚举是其他枢纽的地基

地基性体现在三处具体依赖,均可在代码中验证:

1. **B 图枢纽要在字段上建图边,而字段名此刻是漂移的。**
   - 例:事件发生章此刻有三个名字——`Event.story_time`(`ontology.py:63`)、DB 字段 `valid_from`(`001:30`、`store.py:178,419`)、API 输出 `chapter`(`04` §5.1)。B 若要建 `Event -[involves]-> character` 边并按发生章过滤,必须先确定"发生章"到底叫什么。若 D 不先收敛,B 会在 `story_time`/`valid_from`/`chapter` 之间反复手工桥接,每加一条边重复一次映射,改一处漏一处(B4 风险)。
   - 例:`Fact.entity_id`(`ontology.py:31`)在 DB 是裸 `string` 字段 `entity`(`001:18`)。B 要把它升为 record link,第一步就是确定规范名是 `entity` 还是 `entity_id`(此刻 store.py:154 用 `entity=$entity` 把 `f.entity_id` 写进 `entity` 列,正是跨层换名的现场)。

2. **B/C 要靠枚举做结构校验,而枚举此刻是注释。**
   - C 知识账本一致性要校验 ingest 写入的 `acquired_via` 合法,但此刻 `learned`(`ingest.py:31`)已越界在用(声明域是 `saw/told/inferred/given`,`001:40` 注释)。若 D 不先把 `learned` 正式入枚举并加 `ASSERT`,C 无从判断哪些值是合法、哪些是脏。
   - B 要约束 `Event.event_type` 才能"按类型施加结构规则"(如 `04` §4.3 设想的"所有死亡类事件须关联伏笔"),但此刻 etype 完全自由(`001:29`),无受控域可依。

3. **多 agent 通信靠共享词汇,而此刻各 agent 各叫各的。**
   - `04` §8.4 指出:统一 Schema 后,主编/校验/ingest 各 agent 通过同一套受控枚举与命名通信,消除"who 是名字还是 oid"(B1)、"章号叫哪个字段"(B4)这类 agent 间误解。词汇表是这套共享通信的字典。

> **因果链**:命名漂移 → B 在漂移上建图 = 返工;枚举是注释 → B/C 无法做结构校验。故 **D 必须先行**,这也是总纲 §4.1 依赖图 `D → B`、`D → E` 的根据。

---

## 3. 详细设计

本节四部分:**统一词汇表** → **Python Enum + SurrealDB ASSERT** → **命名重构映射** → **SCHEMALESS→SCHEMAFULL** → **死值处理**。

### 3.1 统一词汇表(Glossary)

> 在 `04` §8.1 基础上**补全**为五组(章时间 / 标识符 / 角色 / 文本 / kind),每条给"中文名 / 规范代码名 / 定义 / 禁用错名"。规范名落地后写入 `scribe3/GLOSSARY.md`(单一事实源),所有新代码、迁移注释、MCP 工具签名、前端术语以此为准。

#### 组一:章时间(整数,故事内第 N 章)

诊断证据:单一"第N章"语义散成 `valid_from/valid_to/since_chapter/until_chapter/story_time/setup_chapter/payoff_chapter/seq/story_at/frame_at/upto_chapter/chapter` **12 个名**(`04` §5.1)。规范化原则:**区分语义角色**——是"单点发生章"、"有效区间端点"、"知识获取区间端点"、还是"渲染层时间参数",分别保留,但消除同一语义的多名。

| 中文名 | 规范代码名 | 定义 | 禁用错名 |
|---|---|---|---|
| 事件发生章 | `story_chapter` | 事件占用的故事时刻(单点,第 N 章) | ~~`story_time`(Python)/ `valid_from`(event 表)/ `chapter`(API)~~ — event 借用 `valid_from` 是误用(事件非区间) |
| 事实生效起点 | `valid_from` | 事实(quality)有效区间的起章 | (保留:语义确是区间起点) |
| 事实失效点 | `valid_to` | 事实有效区间的终章;`None`=惯性持续 | (保留) |
| 获知起章 | `since_chapter` | 知识边时态:knower 从第几章起知道 | (保留:语义是知识获取区间起点) |
| 获知止章 | `until_chapter` | 知识边时态:知道到第几章为止 | (保留) |
| 伏笔埋设章 | `setup_chapter` | promise 被开启的章 | (保留:语义明确) |
| 伏笔回收章 | `payoff_chapter` | promise 被闭合的章;`None`=未回收 | (保留) |
| 章序号(叙述层) | `seq` | manuscript/chapter 表主键序号(叙述顺序) | (保留**仅** chapter 表;`voice_flag.seq` 误用——见命名重构 §3.3) |
| 声音版本生效章 | `since_chapter` | voice_sample 该版本从第几章起适用(时间门) | (与知识边 `since_chapter` 同名同义,可接受:都是"从第 N 章起") |
| 渲染故事时间 | `story_at` | 渲染参数:选哪个故事时刻的事件(非线性闪回) | (保留:渲染层显式参数,语义=要渲染的 `story_chapter`,注明) |
| 渲染帧时间 | `frame_at` | 渲染参数:投影哪一章的知识帧(沉浸式闪回 ≤story_at) | (保留:语义明确,注明=投影用章号) |
| 渲染上限章 | `upto_chapter` | 取声音/craft 时"不剧透未来"的上限章 | (保留;`store.py:328` 已用) |

> **关键收敛点**:`story_time`(Python `Event`)与 `valid_from`(event 表)→ 统一规范名 **`story_chapter`**。这是本组唯一的实质重构(其余多为"保留+注明语义角色")。理由:事件是发生体(占单一时刻),借用 quality 的区间字段 `valid_from` 是本体类型混淆(`04` §5.1 指出"event 表无 story_time 字段,排查时找错字段")。

#### 组二:标识符(oid / 内部 id / 局部名)

诊断证据:`oid/pid/mid/rid/fid/local` 多名(`04` §8.1)。store.py 现状:`_split` 返回 `(table, local)`、变量混用 `oid/pid/rid/mid/fid/_l`(`store.py:24,257-297`)。

| 中文名 | 规范代码名 | 定义 | 禁用错名 |
|---|---|---|---|
| 本体标识符 | `<entity>_id`(如 `character_id`/`fact_id`/`event_id`) | 带前缀 oid,如 `role:焦三`、`fact:治眼`、`ev:对峙3` | ~~泛称 `oid`~~ 作参数名时统一 `<entity>_id`;裸 `pid/mid/rid/fid` 一律改 `promise_id/motif_id/craft_rule_id/fact_id` |
| 局部名 | `<entity>_local` 或统一 `local` | oid 去前缀后的 SurrealDB record 局部部分 | ~~`_l`/`_local` 混用~~ 统一 `local` |
| 前缀↔表映射 | `ONT2TBL`/`TBL2ONT`(保留) | 本体 id 前缀 ↔ SurrealDB 表名 | (保留;`store.py:19-20`) |

> 说明:这组改动**面小**(多为 store.py 内部局部变量重命名,不跨进程边界),但提升可读性。MCP 工具/REST 的对外参数名应统一为 `<entity>_id`(如 `s3_*` 工具的 `pid` → `promise_id`)。

#### 组三:角色(指代"人物"这一对象的多个词)

诊断证据:`focalizer/knower/character/who` 多名(`04` §5.3),"role:/character/entity 三词"。

| 中文名 | 规范代码名 | 定义 | 禁用错名 |
|---|---|---|---|
| 角色(实体) | `character`(表/类别)/ `character_id`(标识) | `kind=character` 的 Entity | ~~`role`/`entity`/`who`~~ 作"角色"统称时一律 `character`(oid 前缀 `role:` 保留,但概念名是 character) |
| 视角角色 | `focalizer` | 当前渲染章的 POV 角色,**值是 `character_id`** | (保留:语义明确;但注明 =`character_id`) |
| 知识持有者 | `knower` / `knower_id` | 知识边的主体(可为 `character_id`、`reader`、`world`) | (保留:语义是"belief base 持有者",比 character 宽——含 reader/world) |
| 事件参与者名 | `who` → `character_id` | ingest delta 里的参与者引用 | ~~`who`(裸名字)~~ ingest 应解析为 `character_id`(`ingest.py:13` `_ensure_char` 现状是裸名字,关联 C/B1 幻觉问题) |

> 说明:`focalizer`/`knower` **保留**(语义比 character 精确:focalizer=POV、knower=belief 持有者含 reader/world)。要消除的是**作"角色统称"时**的 `role/entity/who` 三词混用。`who` 是裸名字这一点关联 B1 幻觉角色(`04` §7),其"解析为 character_id"的实现属 C 枢纽,D 只在词汇表定调。

#### 组四:文本(长正文 vs 短文本 vs 注记)

诊断证据:`04` §8.1 "明确二分,不再混用 value/note 指正文"。

| 中文名 | 规范代码名 | 定义 | 禁用错名 |
|---|---|---|---|
| 章节正文 | `prose` | 章的长正文(渲染产物) | ~~`text`/`value`~~ 指长正文时统一 `prose`(`chapter.prose` 已规范,`004:8`) |
| 短文本字段 | `text` | promise/voice_sample 的短文本载荷 | (保留:语义是"短文本",`005:6`、`009:9`) |
| 事实取值 | `value` | Fact 的 attribute 取值(短) | (保留;`001:20`) |
| 注记 | `note` | craft_rule 的可选说明 | (保留;不得用来装正文,`008:6`) |

> 说明:本组现状基本规范(`prose`/`text`/`value`/`note` 各司其职),词汇表的作用是**固定边界**,防止后续新代码用 `text` 装长正文或 `value` 装注释。**面极小**(无重构,仅约束)。

#### 组五:kind(一名五义,最需拆分)

诊断证据:`kind` 一个字段名,五套互斥语义(`04` §5.2)——`Entity.kind`(本体类别)/`craft_rule.kind`(规则类型)/`voice_sample.kind`(语域)/`promise.kind`(伏笔性质)/critique 与 proposal 内部 dict 键。`PromIn.kind`/`VoiceIn.kind` 同名加剧(`app.py:198,247`)。

| 中文名 | 规范代码名 | 定义 | 禁用错名 |
|---|---|---|---|
| 实体本体类别 | `entity_kind`(DB 可保留 `kind`,但 Python/API 用 `entity_kind`) | character/item/place/faction | ~~泛 `kind`~~ 在 Entity 上下文用 `entity_kind`,枚举 `EntityKind` |
| 题材规则类型 | `craft_rule_kind` | purple_regex/artifact_craft/… | ~~泛 `kind`~~ 枚举 `CraftRuleKind` |
| 声音语域 | `voice_kind` | free/pressure/relation/narration | ~~泛 `kind`~~ 枚举 `VoiceKind` |
| 伏笔性质 | `promise_kind` | promise/red_herring | ~~泛 `kind`~~ 枚举 `PromiseKind` |

> **拆分策略(务实)**:DB **表内列名** `kind` 在各表内部不歧义(`craft_rule.kind` 在 craft_rule 表里只有一义),**可保留列名 `kind`** 以避免大规模迁移;真正要消除的是**跨表/跨层的裸 `kind` 传参与 Pydantic 同名**(`PromIn.kind`/`VoiceIn.kind`)——这些应改用语义化名(`promise_kind`/`voice_kind`)。即:**列名容忍同名(有表上下文消歧),Python/API 参数名必须语义化**。这把改动面控制在 Python 边界,不触发全表迁移。

---

### 3.2 Python Enum + SurrealDB ASSERT

> 双层防护:**Python `Enum`**(进程内类型安全,IDE/类型检查器可查)+ **SurrealDB `ASSERT $value IN [...]`**(落库层硬拒,LLM 经 MCP 写脏值时 DB 直接报错)。两层都要,因为 MCP/REST 写入不一定经 Python Enum 验证,DB ASSERT 是最后防线。

#### 3.2.1 Python Enum 定义(新增 `scribe3/enums.py`)

```python
"""scribe3 受控枚举 · 单一事实源(替换全库裸字符串 + 注释式枚举域)。

设计:全部 (str, Enum) 以便 JSON 序列化与 == 字符串比较直接可用。
DB 侧对应 ASSERT $value IN [...](migrations);两层防护——Python 进程内 + DB 落库层。
"""
from __future__ import annotations

from enum import Enum


class EntityKind(str, Enum):
    """实体本体类别。诊断:声明 4 种但 store 仅落 2 种(item/faction 静默丢,store.py:139-147)。
    本枚举正式登记 4 种;item/faction 的落库实现属 B 枢纽(本枢纽只定枚举)。"""
    character = "character"
    item = "item"
    place = "place"
    faction = "faction"


class AcquiredVia(str, Enum):
    """知识边获取方式。诊断:声明 saw/told/inferred/given,实际还在写 learned(ingest.py:31 越界)。
    本枚举正式纳入 learned(死值处理 §3.5)。told/inferred 当前无写入路径——保留(语义有效、未来会用),
    但标注'声明未用',与 learned'已用未声明'相反,不视为废弃。"""
    saw = "saw"
    told = "told"
    inferred = "inferred"
    given = "given"
    learned = "learned"   # ← 补全:ingest.py:31 实际在写,此前越界无校验


class PromiseKind(str, Enum):
    """伏笔性质。005:8 字面量 promise/red_herring。"""
    promise = "promise"
    red_herring = "red_herring"


class PromiseStatus(str, Enum):
    """伏笔状态。store.py:353,364 字面量 open/closed。"""
    open = "open"
    closed = "closed"


class VoiceKind(str, Enum):
    """声音语域。render.py:69 dict 白名单是唯一对齐良好处,以此为准。"""
    free = "free"
    pressure = "pressure"
    relation = "relation"
    narration = "narration"


class FlagStatus(str, Enum):
    """声音进化标记状态。009 注释声明 open/done,但 done 无写入路径(store.py:342 永写 open)。
    done 是死值(§3.5)——本枚举暂保留 done 但标'需人工确认',待产品确认补写入路径或删除。"""
    open = "open"
    done = "done"          # ← 需人工确认:是未完成(缺写入路径)还是废弃


class CraftRuleKind(str, Enum):
    """题材规则类型。008:4 注释声明 purple_regex/artifact_craft/cover_action;
    store.py:301,311-313 仅产出 purple_regex/artifact_craft,cover_action 零产出(死值 §3.5)。"""
    purple_regex = "purple_regex"
    artifact_craft = "artifact_craft"
    cover_action = "cover_action"   # ← 需人工确认:计划启用还是废弃(当前零产出零消费)
```

> **保留 `Event.event_type` 为自由字符串(暂不枚举)**:诊断 §4.3 指出事件类型自由化的代价,但小说事件类型本质开放(对峙/取丹/逃/拜师……不可穷举)。强行枚举会**阻塞主编创作**。本枢纽对 `event_type` 的处理是:**保留自由字符串但收敛命名**(`etype`→`event_type`,见 §3.3),**受控枚举留给 B 枢纽**结合 taxonomy 需求决定(轻量分类 vs 完全自由)。这里**标"需人工确认 event_type 是否需要受控枚举"**——属 taxonomy 决策(§3.6)。

#### 3.2.2 SurrealDB ASSERT(迁移层,落库硬拒)

新增迁移 `010_enums.surql`,对已有枚举字段**追加 ASSERT**(用 `OVERWRITE` 或先 `REMOVE FIELD` 再 `DEFINE`——见下方幂等说明)。SurrealQL 语法:`DEFINE FIELD ... ASSERT $value IN [...]`。

```sql
-- scribe3 · 受控枚举 ASSERT(落库层硬拒脏值;对应 Python scribe3/enums.py)
-- 幂等策略:DEFINE FIELD ... OVERWRITE 重定义(SurrealDB 3.x 支持 OVERWRITE 覆盖已有定义)。
-- 不动 _execute_write 单写点;仅在 schema 层加约束。

-- ── 知识边 acquired_via:补 learned 入域(此前 ingest.py:31 越界无校验)──
DEFINE FIELD OVERWRITE acquired_via ON knows TYPE string
  ASSERT $value IN ['saw', 'told', 'inferred', 'given', 'learned'] DEFAULT 'given';

-- ── 伏笔 promise.kind / status ──
DEFINE FIELD OVERWRITE kind ON promise TYPE string
  ASSERT $value IN ['promise', 'red_herring'] DEFAULT 'promise';
DEFINE FIELD OVERWRITE status ON promise TYPE string
  ASSERT $value IN ['open', 'closed'] DEFAULT 'open';

-- ── 声音语域 voice_sample.kind(009 此前 SCHEMALESS,见 §3.4 一并收紧)──
DEFINE FIELD OVERWRITE kind ON voice_sample TYPE string
  ASSERT $value IN ['free', 'pressure', 'relation', 'narration'];

-- ── 声音进化标记 status:done 暂留枚举但需人工确认(§3.5)──
DEFINE FIELD OVERWRITE status ON voice_evolution_flag TYPE string
  ASSERT $value IN ['open', 'done'] DEFAULT 'open';

-- ── 题材规则 craft_rule.kind:cover_action 暂留但需人工确认(§3.5)──
DEFINE FIELD OVERWRITE kind ON craft_rule TYPE string
  ASSERT $value IN ['purple_regex', 'artifact_craft', 'cover_action'];

-- ── 实体类别:character/place 表此前无 kind 字段(kind 是 Python 侧分派,store.py:139)──
-- Entity.kind 的 character/item/place/faction 受控,落到 DB 是"表即类别"(character 表/place 表),
-- item/faction 尚无表(B 枢纽补)。故此处不在 DB 加 kind ASSERT——kind 由表名隐含 + Python EntityKind 守。
-- (说明:留作注释,避免误加无意义的 ASSERT。)
```

> **幂等与现有数据的兼容(关键风险点)**:
> - `DEFINE FIELD OVERWRITE` 是 SurrealDB 3.x 重定义已有字段的方式(替代"先 REMOVE 再 DEFINE")。**需人工确认本地 SurrealDB 版本支持 `OVERWRITE` 关键字**(`surreal version`;若不支持则改用 `REMOVE FIELD IF EXISTS` + `DEFINE FIELD`,但 REMOVE 字段不删数据、只删定义,安全)。
> - **加 ASSERT 前必须先清洗存量越界值**,否则新约束会让后续对老行的 UPDATE 失败。TDD 计划(§4)把"扫存量脏值 → 清洗/确认 → 加 ASSERT"列为前置步骤。已知存量越界:`acquired_via='learned'`(ingest 已写入,但 learned 这次正式入域,故不算脏)。需扫 craft_rule/voice_flag 确认有无 `cover_action`/`done` 实例(预期为零,诊断称零产出/无写入路径)。

---

### 3.3 命名重构映射

> "现名 → 规范名"对照,逐条标注**涉及的 migration + store 映射 + 测试改动面**。按改动面从大到小排,**每条都是独立可回滚的小步**(配合 §4 TDD 的"加新名兼容→迁移→删旧名"三段式)。

| # | 现名(位置) | 规范名 | 涉及 migration | 涉及 store/代码 | 测试改动面 |
|---|---|---|---|---|---|
| N1 | event 表字段 `etype`(`001:29`) | `event_type` | `001`(或新增 `011_rename` 加列迁移);DEFINE FIELD `event_type` | `store.py:178`(写 `etype=$t`)、`store.py:424`(读 `etype`)、`426`(`r["etype"]`) | `test_store.py`(event 往返)、`test_ontology.py:48`(see_event)、`test_app.py`(若 API 透出);**限知守护不直接涉及**(etype 不进知识帧) |
| N2 | `Event.story_time`(`ontology.py:63`)+ event 表 `valid_from`(`001:30`) | `story_chapter`(Python 字段 + DB 列统一) | `001`/`011`:event 表 `valid_from`→`story_chapter` | `ontology.py:63`、`store.py:178`(`vf=$ev.story_time`)、`419-420`(`max_chapter` 读 `valid_from`)、`424-426`(`events_at` 读 `valid_from`) | `test_store.py`、`test_ontology.py`、`test_health.py`(`max_chapter` 体检);**注意**:proposition 表的 `valid_from` 是事实区间起点,**不改**——只改 event 表那个被误用的 `valid_from` |
| N3 | proposition 表 `entity`(`001:18`)↔ `Fact.entity_id`(`ontology.py:31`) | `entity_id`(DB 列 + Python 字段统一) | `001`/`011`:proposition `entity`→`entity_id` | `store.py:152-154`(写 `entity=$entity` ← `f.entity_id`)、`201,206`(读 `entity`)、`211,214`、`241,244`、`408`(graph 节点) | `test_store.py`、`test_semantic.py`(`semantic_recall` 选 `entity`)、`test_irony.py`(投影);**限知守护涉及**:`test_focalizer_frame_excludes_others_secret` 经 project_frame 用 fact.entity_id → **必须不破** |
| N4 | `voice_evolution_flag.seq`(`009:11`,实为触发章) | `since_chapter`(语义=触发章,与 chapter 序号区分) | `009`/`011`:`seq`→`since_chapter`(或 `trigger_chapter`,**需人工确认**该 seq 究竟是章号还是序号) | `store.py:340-343`(`add_voice_flag` 写 `seq=$s`)、`345-348`(`list_voice_flags` 读 `seq`) | `test_voice.py`;**需先确认语义**(诊断 §5.1 称"实为章号",但变量名是 seq——人工确认后定规范名) |
| N5 | Pydantic `PromIn.kind`/`VoiceIn.kind`(`app.py:198,247`) | `promise_kind` / `voice_kind`(参数名语义化;DB 列名保留 `kind`) | 无(纯 API/Pydantic 层) | `app.py:198,247`(模型字段)、对应端点解包处 | `test_app.py`(promise/voice 端点);**面小**(进程内) |
| N6 | render 参数语义注明(`story_at`/`frame_at`,`render.py:34`) | 保留名,补 docstring 注明 =`story_chapter`/帧投影章 | 无 | `render.py:34,38-42,96,99`(已有 docstring,补"=story_chapter"一句) | `test_render.py`(不改逻辑,仅注释);**零行为改动** |
| N7 | store 局部变量 `pid/mid/rid/_l`(`store.py:257-297,363`) | `promise_id/motif_id/craft_rule_id/local` | 无 | `store.py:257-297`(`_update_by`/`_delete_by`/`update_promise` 等局部名) | 无(纯内部重命名,行为不变) |

> **重构总原则**:
> - **DB 列改名是最重的一档**(N1/N2/N3/N4):涉及迁移 + store 读写两侧 + 数据搬迁。用三段式(§4):先加新列并双写 → 回填老数据 → 切读到新列 → 删老列。每段后跑全测试(尤其限知守护)。
> - **API/Pydantic 改名是中档**(N5):改参数名 + 前端对应字段,前后端同 PR。
> - **内部变量改名是轻档**(N6/N7):纯重命名,行为不变,一次到位。
> - **跨进程边界的名(MCP 工具签名、REST 字段)改动需同步前端**——本枢纽列出但其前端落地与 H 枢纽协调(H 管前端健壮性)。

---

### 3.4 SCHEMALESS → SCHEMAFULL(P32)

> 诊断 P32:007/008/009 最该约束却最松(表级 `SCHEMALESS`)。给三表补 `SCHEMAFULL` + `DEFINE FIELD`。**注意 intent(007)是 SCHEMALESS 单例**——它的字段(reader_feeling/emotional_arc/red_lines)语义稳定,可安全 SCHEMAFULL;但需确认无其他动态字段在用。

新增迁移 `011_schemafull.surql`(或并入 `010`):

```sql
-- scribe3 · 收紧 007/008/009 SCHEMALESS → SCHEMAFULL(P32)
-- 幂等:DEFINE TABLE OVERWRITE;字段用 DEFINE FIELD IF NOT EXISTS(已存在的字段定义不动)。

-- ── 007 intent(单例 intent:main;store.py:391-401 已固定三字段)──
DEFINE TABLE OVERWRITE intent SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS reader_feeling ON intent TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS emotional_arc  ON intent TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS red_lines      ON intent TYPE string DEFAULT '';

-- ── 008 craft_rule(kind 已在 010_enums 加 ASSERT)──
DEFINE TABLE OVERWRITE craft_rule SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS kind    ON craft_rule TYPE string
  ASSERT $value IN ['purple_regex', 'artifact_craft', 'cover_action'];
DEFINE FIELD IF NOT EXISTS pattern ON craft_rule TYPE string;
DEFINE FIELD IF NOT EXISTS note    ON craft_rule TYPE option<string>;

-- ── 009 voice_sample + voice_evolution_flag ──
DEFINE TABLE OVERWRITE voice_sample SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS character     ON voice_sample TYPE string;
DEFINE FIELD IF NOT EXISTS kind          ON voice_sample TYPE string
  ASSERT $value IN ['free', 'pressure', 'relation', 'narration'];
DEFINE FIELD IF NOT EXISTS text          ON voice_sample TYPE string;
DEFINE FIELD IF NOT EXISTS since_chapter ON voice_sample TYPE int;

DEFINE TABLE OVERWRITE voice_evolution_flag SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS character     ON voice_evolution_flag TYPE string;
-- seq 改名问题见 N4:此处暂留 seq,改名在 N4 步骤独立处理(避免两件事耦合)
DEFINE FIELD IF NOT EXISTS seq           ON voice_evolution_flag TYPE int;
DEFINE FIELD IF NOT EXISTS reason        ON voice_evolution_flag TYPE string;
DEFINE FIELD IF NOT EXISTS status        ON voice_evolution_flag TYPE string
  ASSERT $value IN ['open', 'done'] DEFAULT 'open';
```

> **风险**:`SCHEMAFULL` 后,任何未声明字段的写入会被 DB 拒。**前置**:扫三表现有数据的全部字段名(`SELECT * ... LIMIT` 抽样 + 比对声明集),确认无"在用但未声明"的字段。`craft_rule` 的 `seed_craft_rules`(`store.py:303-315`)只写 kind/pattern/note,`add_voice_sample`(`319`)只写 4 字段,`add_voice_flag`(`341`)只写 4 字段——代码侧已对齐,但存量数据需抽样验证(TDD 前置)。**需人工确认 intent 单例无业务用到的额外动态字段**(SCHEMALESS 期间可能被临时塞过字段)。

---

### 3.5 死值处理

> 三个死值/越界值,逐一给"判定 + 动作"。原则:**能确定的直接处理,不能确定产品意图的标"需人工确认"**(诊断 §8 文末也把后两者列为需结合产品意图确认)。

| 死值 | 位置 | 诊断判定 | 本枢纽动作 |
|---|---|---|---|
| `acquired_via='learned'` | `ingest.py:31`(实写)vs `001:40` 注释域 `saw/told/inferred/given` | **越界值**(在用但未声明) | **直接处理**:`learned` 正式入 `AcquiredVia` 枚举 + `010_enums.surql` 的 `ASSERT IN [...,'learned']`。这是"已用未声明"→ 补声明,无需人工确认(代码已在写,语义清晰="通过学习/钻研获知")。 |
| `craft_rule.kind='cover_action'` | `008:4` 注释声明 vs `store.py:301,311-313` 零产出 | **死值**(声明但永不可达) | **需人工确认**:是"计划启用的角色覆盖动作规则,尚未实现写入"还是"已废弃的设计残留"。① 若计划启用 → 保留枚举值 + 补 `add_craft_rule(kind='cover_action',...)` 的产出路径(属功能开发,非本枢纽);② 若废弃 → 从枚举与 ASSERT 移除、删 `008` 注释。**本枢纽暂保留枚举值并加注释标记 `# 需人工确认`**,不擅自删(删枚举值是破坏性的)。 |
| `voice_evolution_flag.status='done'` | `009` 注释声明 vs `store.py:342` 永写 `'open'`、无置 done 路径 | **死值**(flag 永远 open,无法置 done) | **需人工确认**:是"标记完成功能未实现(缺 `mark_flag_done` 写入路径)"还是"废弃(flag 设计为只增不结)"。① 若未实现 → 补 `update_voice_flag_status(flag_id, 'done')` 写入路径(功能开发);② 若废弃 → 从枚举移除 done、改 status 为常量或删字段。**本枢纽暂保留枚举值并加注释标记 `# 需人工确认`**。 |

> **`acquired_via` 默认值漂移(顺带修)**:诊断 §5.4 指出同字段三处默认不同——`ontology.py:52`=`given`、`mcp.py:233`=`saw`、`001:40` DB DEFAULT=`given`。这不是死值但是不一致。本枢纽建议**统一默认为 `given`**(中性"被给予/公开告知",最不武断),把 `mcp.py:233` 的 `acquired_via: str = "saw"` 改为 `acquired_via: AcquiredVia = AcquiredVia.given`。**需人工确认**:`mcp.py` 默认 `saw` 是否是有意的(MCP 工具语境下"看见"更常见)——若有意则保留并在词汇表注明"MCP 入口默认 saw 是刻意的领域选择"。

---

### 3.6 taxonomy 处理(分类层级)

> 诊断 §4:`Entity.kind` 无子类型、`Event.type` 完全自由。本枢纽的 taxonomy 处理**克制**——只做"受控枚举"这一层,**不引入继承/父子层级**(那属 B/未来枢纽,且诊断 §4.3 的角色子类继承是更大的设计决策)。

| 字段 | 现状 | 本枢纽动作 |
|---|---|---|
| `Entity.kind` | character/item/place/faction 平级,仅 2 落库 | **给受控枚举**(`EntityKind`,§3.2.1)。**不加**"主角/配角/反派"子类型——那是新建模需求,**标"需人工确认是否需要角色重要度子类"**(诊断 §4.3 列为业务问题,但属新功能)。 |
| `Event.type` | 完全自由字符串 | **保留自由字符串 + 收敛命名为 `event_type`**(§3.3 N1)。**不强制枚举**(小说事件类型本质开放,枚举会阻塞创作)。**标"需人工确认是否给轻量受控枚举"**——若产品要"按类型统计/施加结构规则"(诊断 §4.3),可在 B 枢纽引入"事件大类枚举(冲突/转折/日常…)+ 自由子类型"的两层结构。本枢纽不决策,只把命名收敛干净,为 B 留接口。 |

> **结论**:taxonomy 本枢纽**只交付"枚举受控"这一最务实层**;"子类型/层级/继承"是更大的建模决策,统一标"需人工确认 + 划归 B/未来",避免本地基枢纽越界引入未验证的层级模型。

---

## 4. TDD 实施计划

> 严格 **先测后改**(superpowers:test-driven-development)。每个枚举约束:**先写"写脏值被拒"的测试(红)→ 加 `ASSERT`(绿)→ 验证**。每个命名重构:**加新名兼容(双写/双读)→ 迁移数据 → 切读 → 删旧名**,**每一步后跑全测试,限知守护测试(`test_*_does_not_break_pov`、`test_focalizer_frame_excludes_others_secret`、`test_render_prompt_cannot_contain_others_secret`、`test_dramatic_irony_*`)必须全程绿**。
>
> 不变量贯穿:`_execute_write` 单写点不动;命名/枚举改动必配迁移;不 commit(交付方案与代码,提交由人决定)。

### 阶段 D0 · 前置:存量脏值普查(动手前必做)

| 步 | 任务 | 验收 |
|---|---|---|
| D0.1 | 写普查脚本/查询:`SELECT acquired_via FROM knows GROUP BY acquired_via`、对 promise/craft_rule/voice_sample/voice_flag 同样按枚举字段聚合,列出所有实际取值 | 产出"实际值 vs 声明域"差异表;确认 `learned` 在 knows、`cover_action`/`done` 是否有实例(预期零) |
| D0.2 | 写三表(intent/craft_rule/voice)`SELECT *` 抽样,列全部字段名,比对 SCHEMAFULL 将声明的字段集 | 确认无"在用未声明"字段;若有,先决定保留(加 DEFINE FIELD)还是清理 |
| D0.3 | 跑一次全量测试基线(`pytest scribe3/tests/`),记录绿数 | 得到改动前的绿基线(尤其限知守护组),后续每步对照 |

> D0 是**安全闸门**:加 ASSERT/SCHEMAFULL 前若库里有越界值或未声明字段,新约束会让既有写入失败。普查清楚才能区分"清洗存量"还是"补声明"。

### 阶段 D1 · 枚举约束(每个枚举:脏值测试→ASSERT→验证)

> 模板(对每个枚举字段重复):

1. **写红测试**——`test_enum_assert.py` 新增,如:
   ```python
   def test_acquired_via_rejects_dirty_value(store):
       # 写一个不在 [saw,told,inferred,given,learned] 的值,DB 应拒
       import pytest
       from surrealdb import ... # 触发写入越界 acquired_via='telepathy'
       with pytest.raises(Exception):   # SurrealDB ASSERT 失败抛错
           store._db.query(
               "RELATE character:甲->knows->proposition:乙 "
               "SET since_chapter=1, acquired_via='telepathy'")

   def test_acquired_via_accepts_learned(store):
       # learned 必须被接受(此前越界,现入域)
       store._db.query(
           "RELATE character:甲->knows->proposition:乙 "
           "SET since_chapter=1, acquired_via='learned'")  # 不抛错即通过
   ```
   先跑 → **红**(当前无 ASSERT,脏值能写进去,`pytest.raises` 不触发 → 测试失败)。
2. **加 ASSERT**——把该字段的 `DEFINE FIELD ... ASSERT $value IN [...]` 写进 `010_enums.surql`,`apply_schema` 重放。
3. **再跑 → 绿**:脏值被拒(`raises` 命中)、`learned`/合法值通过。
4. **回归**:跑全测试,确认 `add_knowledge`/`add_voice_sample`/`plant_promise` 等既有写入(都写合法值)不被新 ASSERT 误伤。

逐字段顺序(独立小步,各自 红→绿):
| 步 | 枚举字段 | 红测试要点 |
|---|---|---|
| D1.1 | `knows.acquired_via` | 拒 `telepathy`;**接受 `learned`**(关键:验证越界值正式入域) |
| D1.2 | `promise.kind` | 拒 `foreshadow`;接受 `promise`/`red_herring` |
| D1.3 | `promise.status` | 拒 `pending`;接受 `open`/`closed` |
| D1.4 | `voice_sample.kind` | 拒 `monologue`;接受四语域(先做 §3.4 的 voice_sample SCHEMAFULL) |
| D1.5 | `voice_flag.status` | 拒 `archived`;接受 `open`/`done`(done 暂留,标人工确认) |
| D1.6 | `craft_rule.kind` | 拒 `random`;接受三值(cover_action 暂留,标人工确认) |
| D1.7 | Python `enums.py` | 单测:每个 Enum 的成员集合 == 期望集合(防漂移);`AcquiredVia.learned` 存在 |

### 阶段 D2 · SCHEMALESS→SCHEMAFULL(P32)

| 步 | 任务 | 测试守护 |
|---|---|---|
| D2.1 | 写红测试:`test_schemafull.py`——向 intent/craft_rule/voice_sample 写一个**未声明字段**(如 `craft_rule SET kind='purple_regex', pattern='x', bogus_field=1`),SCHEMAFULL 后应拒 | 当前 SCHEMALESS 不拒 → 红 |
| D2.2 | 写 `011_schemafull.surql`(§3.4),`apply_schema` 重放 | — |
| D2.3 | 再跑 → 绿(未声明字段被拒);**回归**:`set_intent`/`add_craft_rule`/`seed_craft_rules`/`add_voice_sample`/`add_voice_flag` 全部仍能写(它们只写声明字段) | `test_craft_rule.py`、`test_voice.py`、`test_app.py`(intent 端点)全绿 |

### 阶段 D3 · 命名重构(三段式:加新名兼容→迁移→删旧名)

> 每条 N(§3.3)按三段式,每段后跑全测试 + 限知守护。以 **N3(proposition `entity`→`entity_id`)** 为范例(改动面最敏感,涉及限知投影):

**N3 三段式**:
1. **加新名兼容**(双写+双读):
   - 迁移:`DEFINE FIELD IF NOT EXISTS entity_id ON proposition TYPE string`(新列与旧 `entity` 并存)。
   - store 写:`add_fact` 同时 `SET entity=$e, entity_id=$e`(双写)。
   - store 读:读取处优先 `entity_id`,回退 `entity`(`r.get("entity_id") or r["entity"]`)。
   - **跑全测试**:`test_store.py`/`test_irony.py`/`test_focalizer_frame_excludes_others_secret`/`test_render_prompt_cannot_contain_others_secret` → 必须全绿(行为未变)。
2. **迁移数据**:
   - 回填:`UPDATE proposition SET entity_id = entity WHERE entity_id = NONE`。
   - 验证:`SELECT count() FROM proposition WHERE entity_id = NONE`(应为 0)。
3. **删旧名**:
   - store 读写只用 `entity_id`;迁移 `REMOVE FIELD entity ON proposition`(REMOVE 删定义,数据列随之失效——**确认回填完成后**)。
   - **跑全测试 + 限知守护** → 全绿。
   - Python `Fact.entity_id` 字段名本就叫 `entity_id`(`ontology.py:31`),故 Python 侧无需改——本重构是让**DB 列名追上 Python**,消除 `store.py:154` 的 `entity=$entity` 跨层换名。

**N1/N2/N4 同法**(各自独立 PR/分支步,不耦合):
- **N1 `etype`→`event_type`**:加 `event_type` 列双写双读 → 回填 → 删 `etype`。守护:`test_store.py`/`test_ontology.py:48`(see_event 不破)。
- **N2 event 表 `valid_from`→`story_chapter`**:加 `story_chapter` 列 → 回填 → 删 event 的 `valid_from`。**务必只改 event 表**,proposition 表 `valid_from`(事实区间)不动。守护:`test_health.py`(`max_chapter`)、`test_store.py`(`events_at`)。
- **N4 `voice_flag.seq`→规范名**:**先人工确认语义**(章号 or 序号),再三段式。守护:`test_voice.py`。

**N5/N6/N7(轻档,一次到位)**:
- N5(Pydantic 参数名):改 `PromIn.kind`→`promise_kind`、`VoiceIn.kind`→`voice_kind` + 端点解包 + 前端字段(与 H 协调)。守护:`test_app.py`。
- N6(render docstring 注明):纯注释,守护 `test_render.py` 全绿(零行为改动)。
- N7(store 局部变量):纯重命名,守护全测试绿。

### 阶段 D4 · 死值落地

| 步 | 任务 |
|---|---|
| D4.1 | `learned` 已在 D1.1 入枚举+ASSERT,此处确认 `ingest.py:31` 写入仍通过(回归) |
| D4.2 | `acquired_via` 默认值统一:`mcp.py:233` `"saw"`→`AcquiredVia.given`(**或经人工确认保留 saw**)。守护 `test_mcp.py` |
| D4.3 | `cover_action`/`done`:在 `enums.py` 与 surql 注释标 `# 需人工确认:未完成 or 废弃`;**产出待产品决策的 issue**(不在本枢纽擅自删/补) |

### 阶段 D5 · 词汇表落地

| 步 | 任务 |
|---|---|
| D5.1 | 写 `scribe3/GLOSSARY.md`(§3.1 五组表),作为单一事实源 |
| D5.2 | 各迁移文件注释、`enums.py` docstring 引用 GLOSSARY 规范名;render.py docstring 注明 story_at=story_chapter |

> **每阶段结束的统一验收动作**:`pytest scribe3/tests/` 全绿,**特别核对限知守护组**(`test_focalizer_frame_excludes_others_secret`、`test_render_prompt_cannot_contain_others_secret`、`test_craft_does_not_break_limited_pov`、`test_voice_does_not_break_pov`、`test_dramatic_irony_point`、`test_dramatic_irony_on_store`)与改前基线一致。任一守护变红 = 立即回滚该步,排查(systematic-debugging)。

---

## 5. 验收标准

| # | 验收项 | 度量方式 |
|---|---|---|
| AC1 | **脏枚举值被 DB 拒** | 对每个枚举字段,写一个越界值,DB 抛 ASSERT 错(`test_enum_assert.py` 全绿;脏值 `raises`、合法值通过) |
| AC2 | **`learned` 正式合法** | `acquired_via='learned'` 写入通过(`test_acquired_via_accepts_learned` 绿);`ingest.py:31` 既有写入回归通过 |
| AC3 | **词汇表落地** | `scribe3/GLOSSARY.md` 存在,覆盖五组(章时间/标识符/角色/文本/kind),每条有中文名/代码名/定义/禁用错名 |
| AC4 | **命名一处一名** | N1-N4 的旧 DB 列名(`etype`、event 的 `valid_from`、proposition 的 `entity`)已删除;`grep -rn "etype" scribe3/` 仅剩历史迁移注释,无活代码读写;Python `Event.story_time` 重命名为 `story_chapter`(或 store 映射收敛到单一规范名) |
| AC5 | **SCHEMAFULL 生效** | 向 intent/craft_rule/voice_sample 写未声明字段被拒(`test_schemafull.py` 绿) |
| AC6 | **无死值(或已确认)** | `cover_action`/`done` 在代码中带 `# 需人工确认` 标注 + 已开 issue;`acquired_via` 默认值跨三处一致(或人工确认保留差异并记录) |
| AC7 | **限知不破(地基红线)** | 限知守护组(§4 列举的 6 个测试)全程绿,与改前基线一致 |
| AC8 | **枚举 Python+DB 双层** | `enums.py` 每个 Enum 有单测(成员集合断言);DB 侧 `ASSERT IN` 与 Enum 成员一一对应(`test_enum_parity`:Python 枚举值集 == surql ASSERT 域,防两层漂移) |

> **AC8 的"双层对账测试"是防回归的关键**:它守护"Python Enum 改了但忘改 surql ASSERT"(反之亦然)这类漂移,呼应 scribe3 既有的"守护 WRITE_GATED 与 dispatch 不漂移"测试范式(见近期 commit `9a1a0e5`)。

---

## 6. 风险与依赖

### 6.1 依赖

- **前置:无**。本枢纽是**地基**,不依赖任何其他枢纽,可立即启动(总纲 §4.2 第一阶段含 D 子集)。
- **被依赖:B、E**。
  - **B 图枢纽**依赖本枢纽:B 要升 `proposition.entity`→RecordLink、建 `Event` 图边、加角色关系表,必须在 D 收敛 `entity`/`entity_id`(N3)、`etype`/`event_type`(N1)、`story_time`/`valid_from`/`story_chapter`(N2)之后,否则在漂移名上建图是返工(总纲 §4.1 关键路径 `D→B`)。
  - **E 性能与索引**依赖本枢纽:E 要在字段上建 `DEFINE INDEX`,字段名须先稳定(总纲 §4.1 `D→E`)。
- **协调:H(前端)**。N5(Pydantic 参数名)、任何 REST/MCP 对外字段改名,需前端同步——与 H 枢纽协调,同 PR 改前后端。

### 6.2 风险

| 风险 | 等级 | 缓解 |
|---|---|---|
| **命名重构是广改动面,回归风险高** | **高** | ① 严格三段式(加新名→迁移→删旧名),每段独立可回滚;② 每步后跑全测试,**限知守护组**(`test_*_does_not_break_pov` 等 6 个)是 load-bearing 断言,任一变红立即停;③ 一条 N 一个改动步,绝不批量改名;④ 先做最敏感的 N3(涉及投影)并以它验证三段式可行,再推其余 |
| **加 ASSERT/SCHEMAFULL 让存量越界写入失败** | 中 | D0 前置普查必做;先清洗/确认存量再加约束;`learned` 这次正式入域故不算越界 |
| **`OVERWRITE` 关键字版本兼容** | 中 | 动手前 `surreal version` 确认 3.x 支持 `DEFINE FIELD/TABLE OVERWRITE`;不支持则降级用 `REMOVE FIELD IF EXISTS`+`DEFINE`(REMOVE 字段只删定义不删数据,安全) |
| **`cover_action`/`done`/`voice_flag.seq` 语义未定** | 低 | 不擅自删/改;标 `# 需人工确认` + 开 issue,枚举值暂保留(保留比误删安全) |
| **删 DB 旧列误删未回填数据** | 中 | 三段式第 2 段"回填后验证 `count WHERE new=NONE` 为 0"是删列的前置硬条件;`REMOVE FIELD` 前必过此关 |
| **两层枚举漂移**(Python 改了 surql 没改) | 低 | AC8 双层对账测试(`test_enum_parity`)守护 |

### 6.3 不变量(贯穿全枢纽)

- `_execute_write` 单一落库点**不动**:本枢纽所有 DB 改动在 schema 层(`DEFINE FIELD ASSERT`/`SCHEMAFULL`),不新增落库路径。
- 命名/枚举改动**必配迁移**:无裸改 store 读写而不动 schema 的情况。
- **不 commit**:交付方案 + 可执行 TDD 步骤,提交由人决定(当前 `feat/surrealdb-knowledge-layer` 分支,工作区有会话前无关改动,绝不 `-A`)。

---

## 7. 闭环问题清单(逐项对账)

> 证明 §1.1 聚合的五类问题全部有处理动作,与 `04` 诊断逐项对齐。

| 诊断条目 | 证据位置 | 本枢纽处理 | 落点 |
|---|---|---|---|
| **零正式枚举**(无 Enum/Literal) | `04` §4.2 | 新增 `scribe3/enums.py`:EntityKind/AcquiredVia/PromiseKind/PromiseStatus/VoiceKind/FlagStatus/CraftRuleKind | §3.2.1 |
| **零 `ASSERT IN`** | `04` §4.2;`001:40` | `010_enums.surql` 给 acquired_via/promise.kind/promise.status/voice.kind/voice_flag.status/craft_rule.kind 加 `ASSERT $value IN [...]` | §3.2.2、D1 |
| **章时间 12 名** | `04` §5.1 | 词汇表组一收敛:event 的 `story_time`/`valid_from`→`story_chapter`(N2);其余按语义角色保留+注明 | §3.1 组一、N2 |
| **`kind` 一名五义** | `04` §5.2 | 词汇表组五:DB 列名容忍(有表上下文)、Python/API 参数语义化(`PromIn.kind`→`promise_kind` 等);各 kind 配独立 Enum | §3.1 组五、N5 |
| **标识符多名**(oid/pid/rid/fid/local) | `04` §5.3,§8.1 | 词汇表组二:对外 `<entity>_id`、内部 `local` 统一 | §3.1 组二、N7 |
| **角色多名**(focalizer/knower/character/who) | `04` §5.3 | 词汇表组三:统称用 `character`;focalizer/knower 保留(语义更精确)+注明 | §3.1 组三 |
| **跨层四名**(proposition/Fact/facts;etype/type;valid_from/story_time) | `04` §5.3 | N1(etype→event_type)、N2(story_time/valid_from→story_chapter)、N3(entity→entity_id);proposition↔Fact 跨层名差异记入词汇表(表名 proposition、对外 fact) | §3.3 N1/N2/N3、§3.1 |
| **死值 `learned`**(越界在用) | `04` §5.4;`ingest.py:31` | **直接处理**:入 `AcquiredVia` 枚举 + ASSERT 域 | §3.5、D1.1 |
| **死值 `cover_action`**(零产出) | `04` §5.4;`008:4` | **需人工确认**:枚举暂留 + `# 需人工确认` + 开 issue | §3.5、D4.3 |
| **死值 `done`**(无写入路径) | `04` §5.4;`store.py:342` | **需人工确认**:枚举暂留 + `# 需人工确认` + 开 issue | §3.5、D4.3 |
| **`acquired_via` 默认值漂移**(given/saw/given) | `04` §5.4;`ontology.py:52`/`mcp.py:233` | 统一为 `given`(或人工确认保留 mcp 的 saw 并记录) | §3.5、D4.2 |
| **P32 SCHEMALESS**(007/008/009 最松) | P32;`007:4`/`008:3`/`009:3,17` | `011_schemafull.surql`:三表 `SCHEMAFULL`+`DEFINE FIELD` | §3.4、D2 |
| **taxonomy 全扁平**(Entity.kind 无子类、Event.type 自由) | `04` §4.1,§4.3 | Entity.kind→受控枚举(交付);角色子类型/event_type 受控枚举/层级继承→**需人工确认 + 划归 B/未来**(本枢纽不引入未验证层级) | §3.6 |

**对账结论**:§1.1 五类(D-枚举 / D-命名 / D-死值 / D-P32 / D-taxonomy)逐项落到 §3 设计 + §4 TDD 步骤;直接处理项(枚举约束、learned、命名收敛、SCHEMAFULL)有明确实现;不擅决项(cover_action/done/角色子类/event_type 枚举)统一标"需人工确认"并开 issue,**不在地基枢纽越界做未验证的建模决策**。

---

> **总结**:D 是浇地基。它**只做**命名收敛 + 枚举受控 + SCHEMAFULL + 死值清理这四件"小工作量、高 ROI"的事(诊断认定为本体投资 ROI 最高的第一阶段),**不碰** Event 持久化/RecordLink/角色关系图/Graph RAG(那是 B 的活,本枢纽是其前置)。最大风险在命名重构的广改动面,缓解全押在"三段式小步 + 限知守护测试全程绿"上。完成后,B/E 可在一处一名、枚举受控的干净地基上施工。
