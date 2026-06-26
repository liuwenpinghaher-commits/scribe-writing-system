# B · 图枢纽(总枢纽)

> 对象:**scribe3**。本枢纽是贯穿三篇诊断的**总枢纽**——
> **限知裂口 P03 = 本体关系缺失(文档04 §3)= SurrealDB Event 蒸发(文档06 §2.2)是同一件事的三个视角**。
> scribe3 选了「图 + 向量 + 文档 + 实时」四能一体的 SurrealDB,却**只兑现了向量**:唯一图边 `knows` 建了从不遍历,关系大多降级成裸字符串,Event 的 participants/effects/causal 落库即蒸发。本枢纽把图能力真正用起来。
> 生成日期:2026-06-24。配套 [00 总纲](./00-系统改进方案总纲.md) / 诊断 [03](../系统架构/03-问题诊断与整改方案.md) [04](../系统架构/04-本体论实现分析与改进方案.md) [06](../系统架构/06-SurrealDB使用深度诊断.md)。
> 本文是**方案文档,不真改代码**;所有引用精确到 `文件:行号`/表名/字段名。

---

## 1. 概述

### 1.1 聚合的问题

| 来源 | 问题 | 精确定位 |
|---|---|---|
| **P03** | `add_event` 丢弃 participants/effects/causal/location/preconditions,真库 `see_event` 失效 | `store.py:175-180`(写)、`store.py:422-427`(读 `events_at`)、`knowledge.py:53-61`(`see_event`)、`ontology.py:55-68`(内存 Event 字段) |
| **关系 RecordLink 化**(文档06 §2.2 #2-5,#10) | proposition.entity / reader_knows.proposition / voice_sample.character / voice_evolution_flag.character / chapter.focalizer 全是裸 `TYPE string` | `001:18`、`002:5`、`009:3`、`009:10`、`004:6` |
| **Event 图边**(文档06 §2.2 #6-8) | Event→character(参与)/ Event→proposition(效果)/ Event→Event(因果)均无持久建模 | `event` 表 `001:28-33` 无相关字段 |
| **角色关系**(文档04 §3.2 M3 / B3) | Entity→Entity(盟友/敌对/亲属/师徒)**根本无表无字段** | grep `parent/relates` 全库零命中(文档04 §4.1) |
| **P38** | 无引用完整性,删角色不级联,留孤儿知识边 | `store.py:264-273`(`_delete_by`/`delete_record`) |
| **Graph RAG**(文档06 §4.4) | `semantic_recall` 纯向量召回,召回后是孤立事实,不拼知识子图 | `store.py:236-245` |

### 1.2 目标(一句话)

把 scribe3 从「图建了不用」推进到「图真正承载语义」——**Event 持久化**(participants/effects/causal 落库,`see_event` 真库生效)+ **引用 RecordLink 化**(裸字符串升 `record<…>`,获引用完整性与级联)+ **角色关系图**(新增 `character_relation` 边)+ **Graph RAG**(向量召回种子 + 沿 `knows`/`involves`/`causes` 图遍历拼知识子图,包成新 MCP 工具 `s3_graph_recall`)。

> 这一条线同时修复 **P03 限知裂口**、**文档04 §3 本体关系缺失**、**文档06 图能力闲置**——故称总枢纽,ROI 最高(见 §2)。

---

## 2. 背景与动机:三视角是同一件事

### 2.1 同一裂口的三个名字

三篇诊断从不同维度指向**同一处结构缺失**:

```
        ┌──────────────────────────────────────────────────────────┐
        │  内存 ontology.py: Event 有 participants/effects/causal_in  │
        │                    (ontology.py:55-68,完整建模)            │
        └──────────────────────────────┬───────────────────────────┘
                                        │  add_event 落库时只取 3 字段
                                        ▼  (store.py:177-179)
   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
   │ 文档03 P03            │   │ 文档04 §3 / B2·B3     │   │ 文档06 §2.2           │
   │ 「限知持久化裂口」     │ = │ 「本体关系缺失」       │ = │ 「Event 结构蒸发」     │
   │ see_event 真库失效     │   │ Event→Fact 边缺失      │   │ event 表无 participants │
   │ (knowledge.py:53)      │   │ Entity→Entity 无表     │   │ /effects/causal 字段    │
   └───────────────────────┘   └───────────────────────┘   └───────────────────────┘
                                        │
                                        ▼
                    限知范式从「结构化保证」退化为「概率保证」
                    (事件自动发知识边 → 改靠 ingest LLM 抽,漏抽即穿帮)
```

- **限知视角(文档03 P03)**:`see_event`(`knowledge.py:53-61`)依赖 `event.effects` + `event.participants` 给在场目击者发知识边(「看见即知道」)。但 `add_event`(`store.py:175-180`)只写 `etype/valid_from/motivated_by_goal`,`events_at`(`store.py:422-427`)也只读这 3 个 → 真库上 Event 的 `effects=[]`、`participants={}`,`see_event` **形同空操作**。内存测试 `test_see_event_grants_knowledge_to_witnesses_only`(`test_ontology.py:48-57`)通过,但它跑在 `World` 内存 dataclass 上,**与真库行为已分叉**。
- **本体视角(文档04 §3.2 / B2·B3)**:Event→Fact(effects)、Event→Event(causal_in)持久层缺失;Entity→Entity(角色关系)**根本无建模**。文档04 §6 判定知识图谱完整度仅 ~55%,首因正是「图边单一(只 `knows`)」+「持久层丢事件结构」。
- **DB 视角(文档06 §2.2 #6-8)**:`event` 表(`001:28-33`)无 participants/effects/causal_in 字段,直接标注「🔴 数据蒸发」;唯一正确建模的 `knows` 边又「建了不遍历」(`store.py:431` 只 `SELECT … FROM knows` 平铺读,零 `->` 箭头遍历,文档06 §2.1)。

### 2.2 为何这是 ROI 最高的总枢纽

1. **一改修三处**:Event 补字段 + 建图边,同时关掉文档03/04/06 各自记的同一笔账。按 P 编号逐条改会把这一处缝合拆到三个工单。
2. **限知是 scribe3 的命脉**:`see_event` 让「在场即知道」由**事件结构自动派生知识边**,这是限知范式区别于「全知扁平注入」的核心(`scenario.py` 复刻的焦三/老道泄露场景正赖此)。真库失效意味着这条护城河只在内存测试里成立,真机写作靠 ingest LLM 概率补——漏抽则后续章限知帧不演进 → 穿帮(文档04 B2)。
3. **图是 SurrealDB 选型的本钱**:34 项能力只实质用了 7 项,「图 + 向量 + 文档 + 实时」四卖点只兑现向量(文档06 §2.1 统计)。Graph RAG(§3.4)是「图 + 向量单库」的杀手锏——一次查询拿到「语义相关事实 + 谁知道它 + 它从哪个事件来 + 涉及哪些角色」,纯向量或纯图都做不到。不用图,等于为图库付费却只当文档库使。
4. **下游解锁**:C 知识账本一致性修复「看见即知道」依赖本枢纽的 Event 持久化(总纲 §4.1 关键路径 `D→B→C`)。

---

## 3. 详细设计

> **红线**:所有写经 `_execute_write` 单一落库点(`store.py:121-123`);SurrealQL 用正确语法(`RELATE`/`->`/`record<…>`/`DEFINE`,不用 SQL 代替);RELATE 箭头位不接受内联函数,用 `RecordID` 绑参(沿用 `add_knowledge` 既有范式 `store.py:166-172`)。
> **前置**:本枢纽依赖 **D 本体规范化**先行——命名(event 发生章统一 `story_chapter`,文档04 §8.1)与枚举(`acquired_via` 补 `learned`、`role` 槽位受控)须先统一,否则在裸字符串混乱命名上建图边是返工(总纲 §4.1)。

### 3.1 Event 持久化 + 图边

#### 3.1.1 新迁移 `010_event_graph.surql`

> 设计取舍:**参与者/因果是「多对多 + 带关系属性 + 需遍历」→ 用图边(RELATE)**;**效果(effects)用图边 `causes`**(便于 Graph RAG 反向遍历 `<-causes<-event`,文档06 §4.4);location 是「单值直接跳转」→ 用 **Record Link**。事件**发生章**字段沿 D 的统一命名升为 `story_chapter`(原 `valid_from`,文档04 §8.1 / 文档06 §4.2 ②)。

```surql
-- scribe3 · 010 事件图边(补回 store.py:177 蒸发的 participants/effects/causal)
-- 全部 IF NOT EXISTS,幂等可重复 apply(SurrealDB 3.x DEFINE 默认不幂等)。
-- 依赖 D:event.story_chapter 命名统一(原 valid_from);role/ctype 枚举受控。

-- ① event 表补字段(location 用 Record Link;发生章统一 story_chapter)
DEFINE FIELD IF NOT EXISTS location  ON event TYPE option<record<place>>;       -- 补 location link
DEFINE FIELD IF NOT EXISTS preconditions ON event TYPE array<string> DEFAULT []; -- 前置(对齐内存 ontology.py:64)

-- ② 参与者:多对多 + 角色槽位元数据 → 图边(补回 participants)
DEFINE TABLE IF NOT EXISTS involves TYPE RELATION FROM event TO character SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS role ON involves TYPE string
    ASSERT $value IN ['SUBJ','OBJ','WITNESS'];                                   -- 槽位受控(原 scenario.py:33 裸 dict 键)

-- ③ 效果:事件初始化的命题 → 图边(支撑 see_event「看见即知道」)
DEFINE TABLE IF NOT EXISTS causes TYPE RELATION FROM event TO proposition SCHEMAFULL;

-- ④ 因果链:事件→事件(对齐内存 causal_in,verify.causal_complete 据此查)
DEFINE TABLE IF NOT EXISTS causal TYPE RELATION FROM event TO event SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS ctype ON causal TYPE string;                          -- 因果类型(enables/motivates/…)

-- ⑤ 遍历用索引(图边读热路径;配合 E 性能枢纽)
DEFINE INDEX IF NOT EXISTS idx_involves_role ON involves FIELDS role;
```

> ⚠️ **需人工确认**:`event.story_chapter` 的改名属 D 本体规范化范畴。若 D 尚未落地、本枢纽需独立可跑,则迁移内 `story_chapter` 暂留 `valid_from`,待 D 统一时一次性改名 + 数据迁移(见 §6 风险)。本文按「D 先行」假设书写。

#### 3.1.2 写入示例(RELATE 语法)

```surql
-- 创建事件本体 + 用图边接参与者/效果/因果(替代当前丢字段的单条 CREATE)
CREATE event:对峙 SET etype = '对峙', story_chapter = 1,
                     location = place:乱岗, motivated_by_goal = 'goal:老道索丹';

-- 参与者(SET role 是边属性)
RELATE event:对峙 -> involves -> character:老道 SET role = 'SUBJ';
RELATE event:对峙 -> involves -> character:焦三 SET role = 'OBJ';

-- 效果(事件初始化的命题 → 供 see_event 给在场者发边)
RELATE event:取丹 -> causes -> proposition:取丹;

-- 因果链(SET ctype 是边属性)
RELATE event:取丹 -> causal -> event:对峙 SET ctype = 'enables';
```

#### 3.1.3 `store.add_event` 改造伪码

> 不变量:仍全经 `_execute_write`(`store.py:121`)。`_split("ev:对峙")` → `("event","对峙")`(`ONT2TBL` `store.py:19`);RELATE 用 `RecordID("event", local)` 绑参(沿用 `add_knowledge` `store.py:167-172`)。

```python
def add_event(self, ev: Event) -> Event:
    _, local = _split(ev.id)                         # "ev:对峙" -> ("event","对峙")
    ev_rid = RecordID("event", local)

    # ① 事件本体(location 升 record link:仅当 ev.location 非空)
    loc_local = _split(ev.location)[1] if ev.location else None
    self._execute_write(
        "CREATE type::record('event',$local) SET etype=$t, story_chapter=$sc, "
        "motivated_by_goal=$g, location=$loc, preconditions=$pre",
        {"local": local, "t": ev.type, "sc": ev.story_time, "g": ev.motivated_by_goal,
         "loc": RecordID("place", loc_local) if loc_local else None,
         "pre": ev.preconditions})

    # ② participants:dict{slot: entity_oid} -> involves 边(SET role=slot)
    for slot, ent_oid in ev.participants.items():
        if not ent_oid:
            continue
        ctbl, clocal = _split(ent_oid)               # 仅 character 入 involves(类型安全)
        self._execute_write(
            "RELATE $e->involves->$c SET role=$role",
            {"e": ev_rid, "c": RecordID("character", clocal), "role": slot})

    # ③ effects:list[fact_oid] -> causes 边(供 see_event 真库发边)
    for fid in ev.effects:
        _, flocal = _split(fid)
        self._execute_write(
            "RELATE $e->causes->$p",
            {"e": ev_rid, "p": RecordID("proposition", flocal)})

    # ④ causal_in:list[(event_oid, ctype)] -> causal 边
    for src_oid, ctype in ev.causal_in:
        _, slocal = _split(src_oid)
        self._execute_write(
            "RELATE $e->causal->$src SET ctype=$ct",
            {"e": ev_rid, "src": RecordID("event", slocal), "ct": ctype})
    return ev
```

#### 3.1.4 `events_at` 读回完整 Event(让 `see_event` 吃真库)

> 现状 `events_at`(`store.py:422-427`)只回 etype/valid_from/goal,故真库 Event 的 `participants`/`effects` 恒空。改造:读回时**沿图边补回** participants(`->involves->`,SET role 作 dict key)与 effects(`->causes->`)。这是 `see_event`「真库生效」的关键——`witnesses_of(event)`(`knowledge.py:48-50`)读 `event.participants.values()`,`see_event`(`knowledge.py:56`)读 `event.effects`。

```python
def events_at(self, chapter: int) -> list[Event]:
    rows = self._query(
        "SELECT meta::id(id) AS local, etype, story_chapter, motivated_by_goal, "
        # 反向沿图边把参与者/效果在同一查询取回(图遍历,非 N+1)
        "  (SELECT meta::id(out) AS clocal, role FROM ->involves) AS parts, "
        "  (SELECT meta::id(out) AS plocal FROM ->causes)         AS effs "
        "FROM event WHERE story_chapter = $ch", {"ch": chapter})
    out = []
    for r in rows:
        participants = {p["role"]: f"role:{p['clocal']}" for p in (r.get("parts") or [])}
        effects = [f"fact:{e['plocal']}" for e in (r.get("effs") or [])]
        out.append(Event(f"ev:{r['local']}", r["etype"], participants=participants,
                         story_time=r["story_chapter"], effects=effects,
                         motivated_by_goal=r.get("motivated_by_goal")))
    return out
```

> 这样 `see_event(store, ev)`(`knowledge.py:53`)在真库取到的 `ev` 已带 participants/effects,与内存 `World` 行为对齐——**「看见即知道」从内存独有变成真库也成立**(验收 §5)。

#### 3.1.5 `s3_add_event` MCP 工具扩参(可选,守红线)

当前 `s3_add_event`(`mcp.py:194-201`)只收 `oid/etype/valid_from/motivated_by_goal`,无法传 participants/effects。可扩参(仍走 `commit_if_approved` 待批 + `_store.add_event` 单点):

```python
@mcp.tool(annotations=_RW)
async def s3_add_event(ctx, oid: str, etype: str, valid_from: int,
                       participants: dict[str, str] | None = None,   # {slot: role_oid}
                       effects: list[str] | None = None,             # [fact_oid]
                       motivated_by_goal: str | None = None) -> dict:
    """新增事件(写,待批)。participants/effects 落图边,供 see_event 真库发知识边。"""
    ok = await _ask(ctx, f"新增事件 {oid}:{etype}(参与{list((participants or {}).values())})")
    return commit_if_approved("s3_add_event", ok,
        lambda: _store.add_event(Event(oid, etype, story_time=valid_from,
                                       participants=participants or {}, effects=effects or [],
                                       motivated_by_goal=motivated_by_goal)))
```

> `s3_add_event` 仍在 `WRITE_GATED`(`mcp.py:30-32`),门控不变。

### 3.2 RecordLink 升级

#### 3.2.1 各表字段升 `TYPE record<…>`(新迁移 `011_record_links.surql`)

> 文档06 §2.2 关系建模表逐项给出了目标类型。升级后:获引用完整性、可 `SELECT entity.name`(省 `_split` + 二次查)、删角色可级联。

```surql
-- scribe3 · 011 引用 RecordLink 化(裸字符串 -> record link)
-- ⚠️ SCHEMAFULL 表改字段 TYPE 须先迁移存量数据(见 §3.2.2),否则旧裸字符串行校验失败。
-- 故本迁移须在「数据转换脚本」之后 apply(或转换脚本内联在同一事务)。

-- ① proposition.entity:裸 string -> record<character|place>(文档06 #2,🔴 最高优先)
DEFINE FIELD IF NOT EXISTS entity ON proposition TYPE record<character | place>
    ASSERT $value != NONE;
DEFINE INDEX IF NOT EXISTS idx_prop_entity ON proposition FIELDS entity;          -- 加速主体反查

-- ② reader_knows.proposition:裸 string -> record<proposition>(文档06 #3)
DEFINE FIELD IF NOT EXISTS proposition ON reader_knows TYPE record<proposition>;

-- ③ voice_sample.character:裸 string -> record<character>(文档06 #4)
DEFINE FIELD IF NOT EXISTS character ON voice_sample TYPE record<character>;

-- ④ voice_evolution_flag.character:裸 string -> record<character>(文档06 #5)
DEFINE FIELD IF NOT EXISTS character ON voice_evolution_flag TYPE record<character>;

-- ⑤ chapter.focalizer:裸 option<string> -> option<record<character>>(文档06 #10)
DEFINE FIELD IF NOT EXISTS focalizer ON chapter TYPE option<record<character>>;
```

> 注:`knows` 已是正确 RELATION(`001:36`),无需升级,仅 D 补 `acquired_via` 的 `ASSERT IN [...,'learned']`(文档06 §4.2 ③),不在本枢纽改。

#### 3.2.2 数据迁移注意(裸字符串 → record link 的迁移脚本思路)

存量库里 `proposition.entity` 是 `'role:焦三'` 形态的裸字符串(本体 oid),而 record link 要求 `character:焦三`。**直接改 TYPE 会让旧行校验失败**——必须先转换数据,再 apply 新 schema:

```surql
-- 转换脚本(在 apply 011 之前跑,或与之同一事务):
-- 把 proposition.entity 的本体 oid 字符串就地转成 record link。
-- 'role:X' -> character:X ; 'place:X' -> place:X(对齐 ONT2TBL store.py:19)。
BEGIN TRANSACTION;
UPDATE proposition SET entity = type::record('character', string::slice(entity, 5))
    WHERE type::is::string(entity) AND string::starts_with(entity, 'role:');
UPDATE proposition SET entity = type::record('place', string::slice(entity, 6))
    WHERE type::is::string(entity) AND string::starts_with(entity, 'place:');
-- reader_knows.proposition:'fact:X' -> proposition:X
UPDATE reader_knows SET proposition = type::record('proposition', string::slice(proposition, 5))
    WHERE type::is::string(proposition) AND string::starts_with(proposition, 'fact:');
-- voice_sample / voice_evolution_flag .character:'role:X' -> character:X
UPDATE voice_sample SET character = type::record('character', string::slice(character, 5))
    WHERE type::is::string(character) AND string::starts_with(character, 'role:');
UPDATE voice_evolution_flag SET character = type::record('character', string::slice(character, 5))
    WHERE type::is::string(character) AND string::starts_with(character, 'role:');
COMMIT TRANSACTION;
```

> **迁移协议(三步,见 §6 风险)**:① `surreal export` dump 全库做物理备份;② 跑上面的转换脚本(幂等:`type::is::string` 守卫确保已转的 record link 不被二次切片);③ apply `011`,跑校验查询确认零裸字符串残留(`SELECT count() FROM proposition WHERE type::is::string(entity)` 应为 0)。
> **存量切片标识符不规范的兜底**:迁移数据的 entity 串「可能无标准前缀」(`store.py:189` 既有注释已承认),转换脚本须对不匹配 `role:`/`place:` 前缀的行**单独列出人工核对**,不静默丢。
> **读侧适配**:升级后 `fact()`/`facts_at()`(`store.py:198-216`)读 `entity` 拿到的是 `RecordID` 而非字符串,需 `_join(table, meta::id)` 还原本体 oid(或查询里 `SELECT type::string(entity) AS entity` 保持字符串契约,渐进迁移更稳)。

#### 3.2.3 P38 引用完整性收益

升 record link 后,删角色不再留孤儿。删除路径 `delete_record`→`_delete_by`(`store.py:264-273`)可改为级联或先查引用:

```surql
-- 删角色前查谁还在引用它(record link 使引用可被图查询发现)
SELECT count() FROM proposition WHERE entity = character:焦三;       -- 它的事实
SELECT count() FROM ->involves WHERE out = character:焦三;            -- 它参与的事件
-- 级联策略(二选一,按产品意图):
--   A. 硬删 + 级联清理:DELETE 角色后,DELETE 其 proposition / involves 边
--   B. 软删:角色加 deleted=true,投影时过滤(保留历史,推荐长篇)
```

> 具体级联 vs 软删策略属 C/G 范畴;本枢纽只**提供 record link 这个前提**(无 link 则孤儿不可发现,文档04 B6)。

### 3.3 角色关系新边 `character_relation`

> 填文档04 §3.2 M3 / B3 缺失:Entity→Entity 盟友/敌对/亲属/师徒**根本无表**。新增带关系属性(`since_chapter`)的图边。

#### 3.3.1 迁移 `012_character_relation.surql`

```surql
-- scribe3 · 012 角色关系图(填文档04 §3.2 缺失,修 B3)
-- 角色间盟友/敌对/亲属/师徒/恋人,带 since_chapter 关系属性(何章建立)。
DEFINE TABLE IF NOT EXISTS character_relation TYPE RELATION
    FROM character TO character SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS relation      ON character_relation TYPE string
    ASSERT $value IN ['ally','enemy','kin','master_disciple','lover'];           -- 受控枚举(对齐文档04 CharacterRelationType)
DEFINE FIELD IF NOT EXISTS since_chapter ON character_relation TYPE int
    ASSERT $value >= 1;                                                          -- 关系属性:何时建立
DEFINE FIELD IF NOT EXISTS note          ON character_relation TYPE option<string>;
DEFINE INDEX IF NOT EXISTS idx_charrel_since ON character_relation FIELDS since_chapter;
```

#### 3.3.2 RELATE 写入示例 + store 方法

```surql
RELATE character:焦三 -> character_relation -> character:阿萤
    SET relation = 'ally', since_chapter = 1, note = '乱岗结识';
RELATE character:老道 -> character_relation -> character:焦三
    SET relation = 'enemy', since_chapter = 1;
```

```python
# store.py 新增(走 _execute_write 单点;RecordID 绑参)
def add_character_relation(self, src_oid: str, dst_oid: str, relation: str,
                           since_chapter: int, note: str | None = None) -> None:
    _, sl = _split(src_oid); _, dl = _split(dst_oid)
    self._execute_write(
        "RELATE $s->character_relation->$d SET relation=$r, since_chapter=$sc, note=$n",
        {"s": RecordID("character", sl), "d": RecordID("character", dl),
         "r": relation, "sc": since_chapter, "n": note})

def relations_at(self, chapter: int) -> list[dict]:
    """某章已建立的角色关系(限知时间门:since_chapter <= chapter)。"""
    return self._query(
        "SELECT meta::id(in) AS src, meta::id(out) AS dst, relation, since_chapter, note "
        "FROM character_relation WHERE since_chapter <= $ch", {"ch": chapter})
```

> 配套 MCP 写工具 `s3_add_character_relation` 须加入 `WRITE_GATED`(`mcp.py:30-32`),走 `commit_if_approved` 待批(守门控红线)。

### 3.4 Graph RAG:`semantic_recall` → 知识子图

> 现状 `semantic_recall`(`store.py:236-245`)纯向量召回,召回后是孤立事实。升级为「向量召回种子 + 沿图边拼知识子图」(单次查询),参考文档06 §4.4。**前提**:§3.1(`involves`/`causes` 边)+ §3.2(`proposition.entity` 升 record link)已落地。

#### 3.4.1 可直接用的 SurrealQL(向量召回种子 + 图遍历)

```surql
-- 「焦三现在处境」类查询:向量找种子命题 -> 沿图边拼出「主体/知情者/来源事件/同场角色」
-- 反向遍历 <-knows<-character:谁知道这条命题(knows 是 character->proposition,反向取知情者)
-- 反向遍历 <-causes<-event :哪个事件产生了它(causes 是 event->proposition)
-- 经事件再跳 ->involves->character:同场参与者
SELECT
    meta::id(id)                          AS local,
    value,
    attribute,
    valid_from,
    entity.name                           AS 主体,        -- record link 直接取名(升级后省 _split+二次查)
    <-knows<-character.name               AS 知情角色,    -- 反向遍历 knows
    <-causes<-event.etype                 AS 来源事件,    -- 反向遍历 causes
    <-causes<-event->involves->character.name AS 同场角色, -- 经事件再跳同场参与者
    vector::distance::knn()               AS dist
FROM proposition
WHERE embedding <|5,COSINE|> $qv          -- 向量召回种子(HNSW,沿用 store.py:243 语法)
  AND valid_from <= $chapter               -- 叠加时间门(限知:不召回未来事实)
ORDER BY dist;
```

> 收益:一次查询同时拿到「语义相关的事实 + 谁知道它 + 它从哪个事件来 + 涉及哪些角色」——主编上下文从「5 条孤立相似事实」升级为「5 个事实各自的知识子图」(文档06 §4.4)。`<-knows<-character` 反向遍历语法成立(`knows` 是 character→proposition,文档06 §4.4 末已确认);`involves`/`causes` 依赖 §3.1 落地。

#### 3.4.2 `store.graph_recall` 方法 + `s3_graph_recall` MCP 工具签名

```python
# store.py 新增(只读,不走 _execute_write)
def graph_recall(self, query: str, chapter: int, k: int = 5) -> list[dict]:
    """Graph RAG:向量召回种子命题 + 沿 knows/causes/involves 图遍历拼知识子图。
    返回每条种子事实 + {主体, 知情角色, 来源事件, 同场角色}。叠加 chapter 时间门(限知)。"""
    from scribe3.embed import embed
    qv = embed([query])[0]
    return self._query(
        f"SELECT meta::id(id) AS local, value, attribute, valid_from, "
        f"  entity.name AS subject, <-knows<-character.name AS knowers, "
        f"  <-causes<-event.etype AS source_events, "
        f"  <-causes<-event->involves->character.name AS co_present, "
        f"  vector::distance::knn() AS dist "
        f"FROM proposition WHERE embedding <|{int(k)},COSINE|> $qv "
        f"  AND valid_from <= $ch ORDER BY dist", {"qv": qv, "ch": chapter})
```

```python
# mcp.py 新增(读工具,放行 _RO;与 s3_semantic_recall mcp.py:93-97 并列)
@mcp.tool(annotations=_RO)
def s3_graph_recall(query: str, chapter: int, k: int = 5) -> list[dict]:
    """Graph RAG 召回:语义相关命题 + 其知识子图(谁知道/来源事件/同场角色),叠加章时间门。
    比 s3_semantic_recall(纯向量孤立事实)多返回关系上下文,主编据此做结构化+语义查询。"""
    return _store.graph_recall(query, chapter, k)
```

> ⚠️ **限知守护**:`s3_graph_recall` 的 `知情角色` 字段揭示「谁知道这条命题」,是**全知元数据**——它供主编(全知通道,`app.py:317` `_editor_system` 本就全知含 secret)做联查,**不喂限知渲染**。限知渲染仍只走 `project_frame`(`knowledge.py:24`)/`build_render_prompt`。本工具不绕过 `project_frame`,故不破限知(见 §5/§6)。`s3_graph_recall` 与 `s3_semantic_recall` 同为 `_RO` 读工具,不入 `WRITE_GATED`,不改写门控。

---

## 4. TDD 实施计划

> bite-sized,每步「写测试 → 实现 → 验收 → commit」。复用 conftest 的临时内存 SurrealDB 夹具(`tests/conftest.py:28-54`,`store` fixture)。
> **限知 load-bearing 守护(每步必跑且不破)**:`test_persisted_paradigm_holds`(`test_store.py:36-44`,真库老道帧不含「治眼」)、`test_focalizer_frame_excludes_others_secret` + `test_see_event_grants_knowledge_to_witnesses_only`(`test_ontology.py:38-57`)。新增守护测试统一命名 `test_*_does_not_break_pov`,断言「升级后老道视角 prompt 仍不含焦三私密」。

### 步骤 ① Event 持久化 + 图边(迁移 010 + add_event/events_at 改造)

- **先写测试**(`test_store.py` 增):
  - `test_event_participants_roundtrip`:`add_event(Event("ev:对峙","对峙", participants={"SUBJ":"role:老道","OBJ":"role:焦三"}, story_time=1))` → `events_at(1)` 取回的 Event,其 `participants == {"SUBJ":"role:老道","OBJ":"role:焦三"}`(**往返不丢**,直接证 P03 修复)。
  - `test_event_effects_roundtrip`:effects 列表往返不丢。
  - `test_event_causal_roundtrip`:`causal_in=[("ev:对峙","enables")]` 往返不丢。
  - `test_event_graph_does_not_break_pov`:落 canonical 场景(`luanshi_leak_world(store)`)后,`build_render_prompt(store,1,"role:老道")` 仍 `"治眼" not in p`。
- **实现**:迁移 `010_event_graph.surql`(§3.1.1)+ `add_event` 改造(§3.1.3)+ `events_at` 沿图边读回(§3.1.4)。
- **验收**:四测试绿;`test_persisted_paradigm_holds`/`test_causal_complete_runs_against_store`(`test_store.py:47-51`)不破。

### 步骤 ② `see_event` 真库生效(事件→知识边自动生成)

- **先写测试**(`test_store.py` 增,真库版,对照内存 `test_ontology.py:48-57`):
  - `test_see_event_grants_knowledge_in_real_db`:真库落角色 + `fact:取丹` + `Event("ev:取丹", participants={"SUBJ":"role:焦三","WITNESS":"role:老道"}, story_time=2, effects=["fact:取丹"])` → 调 `see_event(store, store.events_at(2)[0])` → `project_frame(store,"role:老道",2).knows("fact:取丹")` 为真(**在场目击者真库获知**),`project_frame(store,"role:阿萤",2).knows("fact:取丹")` 为假(**不在场者不获知**)。
  - `test_see_event_does_not_break_pov`:`see_event` 只给在场者发边,老道仍不获知他没目击的 `fact:治眼`。
- **实现**:依赖步骤①的 `events_at` 已带 participants/effects(`see_event` `knowledge.py:53` 不改一行,直接吃真库 Event)。若需在 ingest/save 链触发,加 `store.see_event_for(chapter)` 薄封装走 `add_knowledge` 单点。
- **验收**:真库 `see_event` 与内存 `World` 行为对齐(知识边自动生成);限知守护不破。

### 步骤 ③ RecordLink 迁移(删角色级联,无孤儿)

- **先写测试**(`test_store.py` 增):
  - `test_proposition_entity_is_record_link`:`add_fact` 后查 `SELECT type::is::record(entity) FROM proposition` 为真。
  - `test_delete_character_no_orphan`:建角色 + 其 fact,`delete_record("role:X")`(按选定级联策略)后,`SELECT count() FROM proposition WHERE entity = character:X` 为 0(**无孤儿**,证 P38)。
  - `test_record_link_migration_does_not_break_pov`:对存量裸字符串场景跑转换脚本(§3.2.2)+ apply 011 后,`test_persisted_paradigm_holds` 等价断言仍成立(老道帧不含治眼)。
- **实现**:迁移 `011_record_links.surql`(§3.2.1)+ 转换脚本(§3.2.2)+ 读侧 `_join` 适配(§3.2.2 末)。
- **验收**:存量 dump→转换→校验零裸字符串残留;删角色无孤儿;限知守护不破。

### 步骤 ④ `s3_graph_recall`(召回带知识子图)

- **先写测试**(`test_semantic.py` 或新 `test_graph_recall.py`):
  - `test_graph_recall_returns_subgraph`:落「fact + 知道它的角色(knows 边)+ 产生它的事件(causes 边)+ 同场角色(involves 边)」后,`graph_recall("处境", chapter=2)` 返回的首条含非空 `subject`/`knowers`/`source_events`/`co_present`(**召回带图子结构**,而非孤立事实)。
  - `test_graph_recall_respects_time_gate`:`valid_from > chapter` 的未来事实不被召回(限知时间门)。
  - `test_graph_recall_does_not_break_pov`:`graph_recall` 是只读联查,不调用即不影响 `project_frame`;断言它不写库(`knowledge` 边数前后不变)、且限知渲染路径(`build_render_prompt`)不受其影响。
- **实现**:`store.graph_recall`(§3.4.2)+ `s3_graph_recall` MCP 工具(§3.4.2,`_RO`,不入 `WRITE_GATED`)。
- **验收**:召回结果含图子结构;时间门生效;限知守护不破;`s3_graph_recall` 未出现在 `WRITE_GATED`(`mcp.py:30-32`)。

### 步骤 ⑤(可选)角色关系 `character_relation`

- **先写测试**:`test_character_relation_roundtrip`(RELATE 往返 + `since_chapter` 时间门 `relations_at` 不返未来关系)、`test_add_character_relation_is_write_gated`(`s3_add_character_relation` ∈ `WRITE_GATED`)。
- **实现**:迁移 `012`(§3.3.1)+ `add_character_relation`/`relations_at`(§3.3.2)+ MCP 写工具入门控。
- **验收**:关系往返不丢;时间门生效;写工具走待批。

---

## 5. 验收标准

| # | 标准 | 度量(可执行断言) |
|---|---|---|
| AC1 | **真库 `see_event` 生效** | 真库落事件(带 participants+effects)→ `see_event` 后在场目击者 `project_frame.knows(effect)` 为真、不在场者为假(步骤②测试绿) |
| AC2 | **participants/effects 不蒸发** | `add_event` 后 `events_at` 取回的 Event,participants/effects/causal_in 与写入完全一致(步骤①往返测试绿) |
| AC3 | **删角色无孤儿** | `proposition.entity` 等已升 record link;删角色后 `SELECT count() FROM proposition WHERE entity=<删除角色>` 为 0,无悬挂 `involves`/`knows` 边(步骤③测试绿) |
| AC4 | **`s3_graph_recall` 返回图子结构** | 召回结果每条含 `subject`/`knowers`/`source_events`/`co_present` 关系上下文(非孤立事实),叠加章时间门(步骤④测试绿) |
| AC5 | **限知正确性守护不破** | `test_persisted_paradigm_holds`(`test_store.py:36`)+ `test_focalizer_frame_excludes_others_secret`/`test_see_event_grants_knowledge_to_witnesses_only`(`test_ontology.py:38-57`)+ 全部新增 `test_*_does_not_break_pov` 全绿;老道视角 prompt 始终不含「治眼」 |
| AC6 | **不变量守护** | 所有新写经 `_execute_write`(`store.py:121`);新写 MCP 工具(`s3_add_character_relation` 及扩参 `s3_add_event`)在 `WRITE_GATED`(`mcp.py:30`);`s3_graph_recall` 为只读不入门控 |
| AC7 | **迁移幂等可回放** | `010`-`012` 全 `IF NOT EXISTS`,重复 `apply_schema`(`store.py:115-118`)不报错、不重复建边 |

---

## 6. 风险与依赖

### 6.1 依赖

- **🔴 强依赖 D 本体规范化先行**(总纲 §4.1 关键路径 `D→B→C`):
  - **命名**:event 发生章须先统一 `story_chapter`(原 `valid_from`,文档04 §8.1 / §5.1 列出 story_time/valid_from/chapter 三名)。在未统一的混乱命名上建图边 = 返工。
  - **枚举**:`involves.role`(SUBJ/OBJ/WITNESS)、`causal.ctype`、`character_relation.relation`、`knows.acquired_via` 补 `learned`——D 统一枚举域后本枢纽的 `ASSERT IN [...]` 才与全库一致。
  - 缓解:若需独立推进,§3.1.1 已标注 `story_chapter` 可暂留 `valid_from`,待 D 落地一次性改名 + 数据迁移。
- **下游**:C 知识账本一致性依赖本枢纽的 Event 持久化修复「看见即知道」(总纲 §4.1)。
- **协同**:`involves`/`causal` 边落地后,`verify.causal_complete`(`mcp.py:88-90` 调用)从「无数据可依」变为真库可查(文档06 §2.2 #8),C/G 可据此收紧连贯校验。

### 6.2 最大风险:迁移(裸字符串 → record link 的存量数据转换)

这是本枢纽**最高风险项**:`proposition.entity` 等 SCHEMAFULL 字段改 `TYPE record<…>`,旧裸字符串行**直接 apply 会校验失败**。

- **风险点**:
  1. 存量切片 entity 串「可能无标准前缀」(`store.py:189` 既有注释承认)→ 转换脚本匹配 `role:`/`place:` 前缀时,不匹配的行须**单独列出人工核对**,不静默丢。
  2. 转换非幂等会二次切片(`string::slice` 重复跑会截坏已转的 link)→ §3.2.2 用 `type::is::string()` 守卫,确保已是 record link 的行跳过。
  3. 读侧契约变化:升级后 `fact.entity_id` 从字符串变 `RecordID`(`store.py:206`)→ 须 `_join` 还原或查询里 `type::string()` 保字符串契约(渐进迁移更稳)。
- **迁移协议(三步,强制)**:
  1. **dump**:`surreal export` 全库物理备份(回滚兜底)。
  2. **转换 + 校验**:跑 §3.2.2 转换脚本(BEGIN/COMMIT 事务包裹)→ 跑校验查询 `SELECT count() FROM proposition WHERE type::is::string(entity)` 应为 0;不匹配前缀的残留行人工核对。
  3. **apply + 回归**:apply `011` → 跑全测试套(尤其 AC5 限知守护)。
  - 🔴 红线:`surreal export` / 转换脚本含 `UPDATE`,属数据变更——**执行前须人工批准**(用户全局红线:未经批准不运行 `drop/truncate/delete`、`db reset` 类操作;本枢纽转换脚本无破坏性 DELETE,但 dump+备份是前置)。本文是方案文档,**不真改代码、不真跑迁移**。

### 6.3 限知正确性必须守护(贯穿)

- 每步 TDD 必跑 AC5 的限知 load-bearing 测试,任一步骤破「老道帧含治眼」即回退。
- **`s3_graph_recall` 的 `knowers` 字段是全知元数据**(揭示谁知道某命题),仅供主编全知联查通道(`app.py:317` `_editor_system` 本就全知),**绝不喂限知渲染**——限知渲染唯一入口仍是 `project_frame`(`knowledge.py:24`)。本工具不绕过 `project_frame`,不破限知。
- `events_at` 沿图边读回 participants 后,须警惕文档03 P33(渲染「事件块」`render.py:60-66` 列全部 participants 不经 focalizer 帧过滤)——本枢纽**让 participants 真库可读**,P33 的「事件块限知门控」由 C 枢纽收口;本枢纽测试须确认「读回 participants 不等于把隐藏参与者喂进限知 prompt」。

### 6.4 其他风险

- **HNSW 维度耦合**:Graph RAG 仍用 `embedding <|k,COSINE|>`(`store.py:243`),DIMENSION 512 与 bge-small-zh 耦合(文档06 §2.2 ④),换嵌入模型须同步;本枢纽不动嵌入,无新增风险。
- **图遍历性能**:`<-knows<-character`/`->involves->` 多跳遍历无索引会慢;§3.1.1/§3.3.1 已加 `idx_involves_role`/`idx_charrel_since`,knows 时间门索引由 E 枢纽补(文档06 §4.2 ③ `idx_knows_since`)。
- **`reader_knows.proposition` 升 link 的两端类型**:reader 帧因类型安全单独建表(`002` 注释、文档04 §3.2),升 `record<proposition>` 只约束 out 端,不影响「reader 不走 character→knows 边」的设计。

---

## 7. 闭环问题清单(对账)

> 证明本枢纽覆盖总纲 §3 分配给 B 的全部条目,逐项给修复手段 + 验收锚点。

| 编号/条目 | 来源 | 修复手段(本枢纽) | 验收锚点 |
|---|---|---|---|
| **P03** Event 蒸发 / 限知裂口 | 文档03 §2 | §3.1 event 补字段 + involves/causes/causal 图边 + add_event/events_at 改造 → see_event 真库生效 | AC1 / AC2(步骤①②) |
| **P38** 引用完整性(删角色孤儿) | 文档03 P38 | §3.2 proposition.entity 等升 record link → 删角色可级联/可发现引用 | AC3(步骤③) |
| **关系 RecordLink 化** proposition.entity | 文档06 §2.2 #2 | §3.2.1 ① `record<character\|place>` + idx_prop_entity | AC3 / 步骤③ |
| **关系 RecordLink 化** reader_knows.proposition | 文档06 §2.2 #3 | §3.2.1 ② `record<proposition>` | 步骤③ |
| **关系 RecordLink 化** voice_sample.character | 文档06 §2.2 #4 | §3.2.1 ③ `record<character>` | 步骤③ |
| **关系 RecordLink 化** voice_evolution_flag.character | 文档06 §2.2 #5 | §3.2.1 ④ `record<character>` | 步骤③ |
| **关系 RecordLink 化** chapter.focalizer | 文档06 §2.2 #10 | §3.2.1 ⑤ `option<record<character>>` | 步骤③ |
| **Event 图边** involves(event→character) | 文档06 §2.2 #6 | §3.1.1 ② `RELATE event->involves->character SET role` | AC2(步骤①) |
| **Event 图边** causes(event→proposition) | 文档06 §2.2 #7 | §3.1.1 ③ `RELATE event->causes->proposition` | AC1/AC2(步骤①②) |
| **Event 图边** causal(event→event) | 文档06 §2.2 #8 | §3.1.1 ④ `RELATE event->causal->event SET ctype` | AC2(步骤①) |
| **角色关系** character_relation | 文档04 §3.2 M3 / B3 | §3.3 `RELATE character->character_relation->character`(ally/enemy/kin/master_disciple/lover + since_chapter) | 步骤⑤ |
| **Graph RAG** s3_graph_recall | 文档06 §4.4 | §3.4 向量召回种子 + `<-knows<-character`/`<-causes<-event`/`->involves->character` 遍历 → s3_graph_recall | AC4(步骤④) |

**对账结论**:总纲 §3 列给 B 的 P03、P38、5 项 RecordLink、3 项 Event 图边、角色关系、Graph RAG **共 12 条目全部覆盖**,无遗漏。P33(事件块限知门控)在本枢纽让 participants 真库可读后,门控收口移交 C 枢纽(§6.3 已标注边界,避免与 C 重复主归属)。

---

> 本方案基于 2026-06-24 只读扫描的代码事实(`store.py`/`ontology.py`/`knowledge.py`/`mcp.py`/`migrations/*.surql`/`tests/*`)与三篇诊断,未改任何代码、未跑任何迁移、未打印任何 secret。
> **需人工确认项**:① `event.story_chapter` 改名时机(随 D 落地 vs 本枢纽暂留 valid_from);② 删角色级联 vs 软删策略(产品意图,§3.2.3);③ 存量库中 `proposition.entity` 无标准前缀行的人工核对清单(§6.2)。
