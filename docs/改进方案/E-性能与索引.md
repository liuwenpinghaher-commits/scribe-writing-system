# 枢纽 E · 性能与索引

> 对象:**scribe3**(AI 小说写作系统,根目录 `<repo-root>`)。
> 本枢纽聚合"性能与索引"相关问题,补齐 DEFINE INDEX、预聚合视图、DEFINE EVENT 级联、章节级 RAG、Hybrid Search。
> 取证基于 `surreal version` 实测(**3.1.5 for macos on aarch64**)+ `scribe3/migrations/*.surql`(9 个迁移)+ `scribe3/store.py` + `scribe3/app.py` + `scribe3/embed.py`,精确到 `文件:行号`/表名/字段名。
> 配套诊断:[03-问题诊断与整改方案.md](../系统架构/03-问题诊断与整改方案.md) §4、[06-SurrealDB使用深度诊断.md](../系统架构/06-SurrealDB使用深度诊断.md) §2.1/§2.3/§2.4/§4.2/§4.4/§4.5。
>
> **本文是方案文档,不真改代码、不 commit。** 所有写操作仍须经 `store.py:121` 的 `_execute_write` 单一落库点;限知投影语义不破坏。无法对 SurrealDB 3.1.5 确认的语法显式标注"**需人工确认**"。

---

## 1. 概述

scribe3 选了 SurrealDB(图+文档+向量+实时四能一体),但**性能维度只兑现了向量召回一项**:全库 13 张表里**除 `003_vector.surql:4` 的 HNSW 向量索引外,零 DEFINE INDEX**(06§0 "全库索引:仅 1 个";03§4 P05)。而**限知投影是每次渲染的热路径**(03§4 引言),其底层查询——`facts_at`(`store.py:209`)、`events_at`(`store.py:422`)、`latest_voice_samples`(`store.py:328`)、`knowledge`(`store.py:429`)——**全部走全表扫描的时间门过滤**。长篇放大效应显著(数百命题 × 数十角色 × 数百知识边)。

本枢纽的目标是把"性能压在渲染热路径"这一结构性短板系统性补齐,分五条线:

1. **DEFINE INDEX(零风险,第一阶段)**——给所有时间门/等值查询字段加索引,让 `facts_at`/`events_at`/`knows`/`voice_sample` 走索引而非全表扫;并用 `chapter.seq` / `promise` 唯一索引挡重复 ingest。
2. **预聚合(DB 侧聚合)**——`stats()`(`store.py:383`)当前把全表 `prose` 拉进 Python 数字数;改为 DB 侧聚合(`DEFINE TABLE … AS SELECT` 物化视图,或事件维护的增量计数表)。
3. **/quality QC 结果随存稿缓存(章级)**——`app.py:274` 逐章重跑 `quality_flags`+`causal_complete`,无缓存/分页(03§4 P29);改为存稿时算一次、`/quality` 读缓存聚合。
4. **DEFINE EVENT 级联(中期)**——ingest 级联/voice 标记/promise 超期,现全在应用层手工编排(06§2.4);可由表事件在 DB 层触发。
5. **章节级 RAG + Hybrid Search(中期)**——embedding 只覆盖 `proposition`(`003:3`),`chapter.prose` 未向量化 → 章节语义检索缺失(06§2.3);并补全文 BM25 + RRF 融合,从纯单路向量升级为混合召回。

> 红线复述:索引/视图/事件不改变限知语义——时间门(`valid_from <= ch AND (valid_to = NONE OR valid_to > ch)`)是**索引谓词**,投影屏蔽逻辑不动;新增的 `chapter` 向量索引服务于"作者侧检索",仍受 MCP 工具层限知封装约束(06§3.1)。

---

## 2. 背景与动机

### 2.1 性能压在渲染热路径

03§4 开宗明义:"**限知投影是每次渲染的热路径**,性能问题直接拖慢核心体验。长篇(数百命题 × 数十角色 × 数百知识边)放大效应显著。"渲染一章 prose,要先投影该 (focalizer, chapter) 的知识帧——这条链路上的每个 store 读方法都带时间门:

| 热查询方法 | 位置 | 谓词字段 | 当前索引 | 全表扫? |
|---|---|---|---|---|
| `facts_at(chapter)` | `store.py:209-216` | `proposition.valid_from`、`valid_to` | 无 | 🔴 是 |
| `events_at(chapter)` | `store.py:422-427` | `event.valid_from`(`= $ch`) | 无 | 🔴 是 |
| `latest_voice_samples` | `store.py:328-337` | `voice_sample.character`(等值)+ `since_chapter`(≤) | 无 | 🔴 是 |
| `knowledge`(@property) | `store.py:429-441` | `knows` 全表 + `reader_knows` 全表 | 无 | 🔴 是,且每访问跑 2 条全表查询(03§4 P04) |
| `open_promises` | `store.py:356-361` | `promise.status`(Python 端过滤) | 无 | 🔴 是(先全拉再 Python filter) |
| `semantic_recall` | `store.py:236-245` | `proposition.embedding` | ✅ HNSW(`003:4`) | 否(唯一已索引路径) |

`facts_at` 的 surql(`store.py:210-213`):

```sql
SELECT meta::id(id) AS local, entity, attribute, value, valid_from, valid_to,
       secret, leak_markers FROM proposition
WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch)
```

`proposition` 上 `valid_from`/`valid_to` 无索引(`001:21-22` 只声明 `TYPE int` / `option<int>`,无 DEFINE INDEX),这是一次**全表顺序扫 + 行级谓词求值**。命题表随着写作单调增长(每章 ingest 追加 `fact:k{seq}-{i}`,03§3 P07),到数百章时全表扫成本线性膨胀。

### 2.2 长篇放大,且复合在一起

更糟的是这些方法被**反复、嵌套**调用:

- `graph()`(`store.py:403-415`)先调 `facts_at(ch)`(全表扫命题),再遍历 `self.knowledge`(@property,触发 2 条全表扫)——**三次全表扫**产一个 Atlas 视图。
- `dramatic_irony` 类逻辑两次 `project_frame` = 知识边全扫 2 遍(03§4 P04)。
- `/quality`(`app.py:280-289`)对**每一章**循环 `get_chapter` + `quality_flags`(确定性 QC 扫描)+ `causal_complete`,N 章 = N 次重活,无缓存无分页(03§4 P29);`st.max_chapter()`(`store.py:417`)又一次全表扫 `event`。

### 2.3 SurrealDB 的能力被闲置

06§2.1 统计:SurrealDB 34 项能力 scribe3 **实质用了 7 项**,本枢纽相关的**全部未用**:

- **预聚合视图(DEFINE TABLE AS SELECT)**:❌ 未用——`stats()` 把全表 prose 拉进 Python 数字数(06§2.1 表 + `store.py:383-387`)。
- **Table Events(DEFINE EVENT)**:❌ 完全未用(06§2.4)——所有"变更反应"靠客户端 LIVE 拉取,无服务端触发。
- **混合检索(全文 + 向量 RRF)**:❌ 未用(06§2.3)——仅单路向量召回,无 `DEFINE ANALYZER`/`SEARCH`/`@@`。
- **章节正文向量化**:❌ embedding 只覆盖命题,`chapter.prose` 正文未向量化(06§2.3)。

> 一句话动机:**scribe3 的性能瓶颈不是算法问题,是"该建的索引没建、该让 DB 干的聚合搬到了 Python、该用事件触发的级联在应用层手抄"。** 这五条线全部是低改动、可分阶段、与限知范式正交的补强。其中 DEFINE INDEX 是 03§8 与 06§4.1 共同认定的 **ROI 最高、零逻辑风险**的第一刀。

---

## 3. 详细设计

> 所有 surql 针对 SurrealDB **3.1.5**。索引/事件采用 `IF NOT EXISTS` 与现有迁移一致(`001:4` "启动可重复 apply 幂等")。落库点不变:DDL(DEFINE)走 `apply_schema`(`store.py:115-118`,逐迁移 `_db.query`);DML 写仍经 `_execute_write`(`store.py:121`)。
>
> **依赖提示**:本节字段名沿用当前迁移现状(`event.valid_from`、`proposition.entity` 裸字符串等)。**枢纽 D(命名统一)落地后**,若 `event.valid_from` 改名 `story_chapter`、`entity` 升 `record<…>`,本节索引字段名须同步——见 §6。

### 3.1 ① DEFINE INDEX 清单(第一阶段,零逻辑风险)

新增迁移 `010_indexes.surql`(纯 DDL,无 DML,可独立 apply、可重复)。下表逐条对账到热查询:

```sql
-- scribe3 · 010_indexes.surql · 性能索引(枢纽 E §3.1)
-- 全部 IF NOT EXISTS:与现有迁移一致,启动可重复 apply 幂等(对照 001:4)。
-- 仅补常规字段索引;HNSW 向量索引已在 003_vector.surql,不重复。

-- (1) 命题时间门:facts_at 的 valid_from<=ch AND (valid_to=NONE OR valid_to>ch)(store.py:213)
--     复合索引覆盖范围谓词的两个字段。
DEFINE INDEX IF NOT EXISTS idx_prop_valid   ON proposition FIELDS valid_from, valid_to;

-- (2) 命题主体反查:proposition.entity 等值(graph/限知按主体聚合;06§4.2 建议)
DEFINE INDEX IF NOT EXISTS idx_prop_entity  ON proposition FIELDS entity;

-- (3) 知识边时间门:knowledge / project_frame 按 since_chapter 过滤(store.py:433)
DEFINE INDEX IF NOT EXISTS idx_knows_since   ON knows FIELDS since_chapter;

-- (4) reader 帧时间门:reader_knows.since_chapter(store.py:438 并入 reader 帧)
DEFINE INDEX IF NOT EXISTS idx_rknows_since  ON reader_knows FIELDS since_chapter;

-- (5) 事件时间门:events_at 的 valid_from = $ch(store.py:425)+ max_chapter ORDER BY(store.py:419)
DEFINE INDEX IF NOT EXISTS idx_event_chapter ON event FIELDS valid_from;

-- (6) 声音库:latest_voice_samples 的 character 等值 + since_chapter 排序(store.py:332)
DEFINE INDEX IF NOT EXISTS idx_voice_char    ON voice_sample FIELDS character, since_chapter;

-- (7) 声音进化标记:list_voice_flags 按 status 过滤(store.py:348)
DEFINE INDEX IF NOT EXISTS idx_vflag_status  ON voice_evolution_flag FIELDS status;

-- (8) 伏笔状态:open_promises 当前 Python 端过滤(store.py:360-361),建索引后可下推 WHERE status='open'
DEFINE INDEX IF NOT EXISTS idx_promise_status ON promise FIELDS status;

-- (9) 章节唯一:chapter.seq 当前无 unique(004:4 仅 TYPE int;06§2.2 标注"seq 无 unique index")
--     UPSERT 落库用 record id = seq(store.py:371),但 seq 字段本身可重复写;唯一索引锁死一章一行。
DEFINE INDEX IF NOT EXISTS idx_chapter_seq   ON chapter FIELDS seq UNIQUE;

-- (10) 母题去重:重复 ingest 防重(06§2.2 "motif 无 unique index 重复 ingest 产重复行")
DEFINE INDEX IF NOT EXISTS idx_motif_name    ON motif FIELDS name UNIQUE;
```

**逐项依据与对账**:

| 索引 | 服务的查询 | 谓词来源 | 收益 |
|---|---|---|---|
| `idx_prop_valid` | `facts_at` | `store.py:213` | 时间门从全表扫 → 范围索引扫 |
| `idx_prop_entity` | `graph`/主体反查 | 06§4.2 | 按主体聚合命题加速 |
| `idx_knows_since` | `knowledge`/帧投影 | `store.py:433` | 知识边时间门走索引 |
| `idx_rknows_since` | reader 帧 | `store.py:438` | reader 帧时间门走索引 |
| `idx_event_chapter` | `events_at`/`max_chapter` | `store.py:419/425` | 等值 + 排序均走索引 |
| `idx_voice_char` | `latest_voice_samples` | `store.py:332` | 复合(等值+排序)免全表 + 免排序 |
| `idx_vflag_status` | `list_voice_flags` | `store.py:348` | status 等值走索引 |
| `idx_promise_status` | `open_promises` | `store.py:360` | 可把 Python filter 下推为 `WHERE status='open'` |
| `idx_chapter_seq` UNIQUE | 防重复章 | `004:4`、06§2.2 | 一章一行强约束 |
| `idx_motif_name` UNIQUE | 防重复母题 | 06§2.2 | 重复 ingest 不产重复行 |

> ⚠️ **唯一索引上线前置检查(需人工确认)**:`idx_chapter_seq UNIQUE` / `idx_motif_name UNIQUE` 在**已有重复数据**的库上 `DEFINE INDEX … UNIQUE` 会因唯一约束冲突而**报错**。上线前须先 `SELECT seq, count() FROM chapter GROUP BY seq`(及 motif name)确认无重复,有则先清理。本地主书 `main` 数据量小,人工核一次即可。
>
> ⚠️ `open_promises`(`store.py:356-361`)当前是"`list_promises` 全拉 + Python `if status=='open'`"。加 `idx_promise_status` 后**还需改 store 代码**把谓词下推到 SQL(`WHERE status='open'`)索引才真正生效——**纯加索引不改查询,这条索引不被用到**。这是本枢纽里唯一"索引 + 改查询"配套项;其余 9 条索引现有 SQL 已带对应 WHERE/ORDER BY,加索引即生效。

### 3.2 ② /quality QC 结果随存稿缓存(章级)

**现状**(`app.py:274-297`):`/quality` 对每章循环 `get_chapter` → `quality_flags(prose)`(确定性扫描:排比/结构/升华)→ `causal_complete(st, seq)`;N 章 N 次全量重算,无缓存。`quality_flags` 是纯函数(吃 prose 出 flags),**结果只随 prose 变化**——天然可缓存。

**设计**:存稿是唯一改变 prose 的入口(`save_chapter`,`store.py:368-373`),在存稿后把该章 QC 结果算一次并随章落库;`/quality` 改为读缓存聚合。

迁移 `004` 的 `chapter` 表补缓存字段(新增迁移 `011_chapter_qc.surql`,只加字段、向后兼容):

```sql
-- scribe3 · 011_chapter_qc.surql · 章级 QC 缓存(枢纽 E §3.2)
DEFINE FIELD IF NOT EXISTS qc_word_count ON chapter TYPE option<int>;
DEFINE FIELD IF NOT EXISTS qc_issues     ON chapter TYPE option<int>;     -- repetition+structural+purple 计数
DEFINE FIELD IF NOT EXISTS qc_causal     ON chapter TYPE option<int>;     -- causal_complete 违规计数
DEFINE FIELD IF NOT EXISTS qc_at         ON chapter TYPE option<datetime>; -- 缓存生成时刻(判新鲜)
```

`save_chapter` 落库时同写缓存(仍经 `_execute_write`,UPSERT 一条 surql 覆盖正文 + QC;示意,真实接线在 §4):

```sql
-- 存稿即缓存:prose 与 QC 计数在同一次 UPSERT 落库(一致、不漂移)
UPSERT type::record('chapter', $seq) SET
    seq = $seq, title = $title, focalizer = $foc, prose = $prose,
    qc_word_count = $wc, qc_issues = $issues, qc_causal = $causal, qc_at = time::now();
```

`/quality` 读缓存版(替代 `app.py:280-289` 的逐章重算循环):

```sql
-- 直接读已缓存的章级 QC(无重算);仅在 qc_at=NONE(旧章未回填)时回退现算
SELECT seq, title, qc_word_count, qc_issues, qc_causal, qc_at
FROM chapter ORDER BY seq;
```

> 设计取舍:缓存字段用 `option<…>`,旧章 `qc_at=NONE` → `/quality` 对这部分回退到现算并顺手回填(惰性迁移),不需一次性 backfill 全书。`causal_complete` 依赖知识图谱状态(非纯 prose 函数),严格说"存稿后图谱再变可能让 `qc_causal` 过期"——但因果违规检测的输入(事件/命题)主要在 ingest 阶段定型,章级缓存对仪表盘足够;若要绝对新鲜,可在 ingest 完成的 DEFINE EVENT(§3.3)里顺带重算该章 `qc_causal`。**`qc_at` 字段正是为"判断缓存是否比最近一次图谱变更旧"预留**。

### 3.3 ③ DEFINE EVENT 示例(ON chapter / ON proposition / ON promise)

**现状**(06§2.4):ingest 级联("render → 存 → ingest → 知识态更新")、voice 标记、promise 超期全在应用层手工编排(`app.py:587` `background.add_task(_bg_ingest)`)。SurrealDB 的 `DEFINE EVENT` 可把部分级联下沉到 DB 层。

> **SurrealDB 3.x 事件变量(需人工确认精确名)**:`DEFINE EVENT` 体内可用 `$event`(操作类型 CREATE/UPDATE/DELETE)、`$after`(新行)、`$before`(旧行)、`$value`(= `$after`)。下列示例按此约定书写;**3.1.5 上 `$before`/`$after` 的可用性与 `$event` 取值集合须以实测为准**,标"需人工确认"。

**(a) ON chapter:存稿后回写"该章已落"标记 + 触发轻量校验**

把"存稿后需要的纯 DB 级副作用"放进事件(重活如 LLM ingest 仍留应用层,事件只做 DB 内可完成的回写/校验):

```sql
-- scribe3 · DEFINE EVENT 示例(枢纽 E §3.3a)· 需人工确认 $after/$event 语义
DEFINE EVENT IF NOT EXISTS ev_chapter_saved ON TABLE chapter
    WHEN $event = "CREATE" OR $event = "UPDATE"
    THEN {
        -- 回写一个"manuscript 进度"单例(供仪表盘读最大章,免 max_chapter 全表扫 event)
        UPSERT meta:manuscript SET
            last_saved_seq = $after.seq,
            last_saved_at  = time::now();
    };
```

**(b) ON proposition:命题写入后,按规则标记声音进化**

`store.py:340` 的 `add_voice_flag` 当前由应用层在 ingest 检测重大事件时手工调用;可由 `DEFINE EVENT ON proposition` 在满足条件时自动写标记(06§2.4 场景 2)。条件示例:命题 `attribute` 命中"重大转变"类:

```sql
-- scribe3 · DEFINE EVENT 示例(枢纽 E §3.3b)· 需人工确认
DEFINE EVENT IF NOT EXISTS ev_prop_voice_flag ON TABLE proposition
    WHEN $event = "CREATE" AND $after.attribute IN ['转变', '创伤', '决意']
    THEN {
        CREATE voice_evolution_flag SET
            character = $after.entity,        -- 注:entity 当前是裸字符串(001:18);D 升 record 后改 $after.entity（保持本表 character 字段类型）
            seq       = $after.valid_from,
            reason    = string::concat('命题触发:', $after.attribute, '=', $after.value),
            status    = 'open';
    };
```

**(c) ON promise:伏笔超期由"事件 + 聚合"替代坏掉的 cron**

06§2.4 场景 3 与文档05 R1:promise 超期告警现靠 cron 主动扫,**且 cron 当前坏**。超期是 `setup_chapter + N < 当前最大章` 的纯派生量,可用预聚合视图(§3.4)直接暴露 open-overdue 计数,不必依赖 cron。事件侧补一个"伏笔状态变更审计"作为可观测性:

```sql
-- scribe3 · DEFINE EVENT 示例(枢纽 E §3.3c)· 审计伏笔闭合,可观测
DEFINE EVENT IF NOT EXISTS ev_promise_closed ON TABLE promise
    WHEN $event = "UPDATE" AND $before.status = 'open' AND $after.status = 'closed'
    THEN {
        CREATE promise_audit SET
            promise   = $after.id,
            setup     = $after.setup_chapter,
            payoff    = $after.payoff_chapter,
            closed_at = time::now();
    };
```

> 事件落地的边界(给 §6 风险):**DEFINE EVENT 在 DB 层执行,绕过应用层的 `_execute_write` 审计与限知校验**。因此事件只承担"纯 DB 内、不涉及私密/限知判断的回写与审计"(进度标记、状态审计、派生计数);**任何会改变"谁知道什么"(knows 边)的级联仍须留在应用层** ingest 流程,以保持限知不变量与单一写点的可审计性。`ev_prop_voice_flag` 只写"提示标记"(`voice_evolution_flag` 本就"只提示不自动生成独白",`009:8`),不发知识边,属安全范围。

### 3.4 ④ 预聚合(DEFINE TABLE AS SELECT 或增量计数)

**现状**(06§2.1 + `store.py:383-387`):`stats()` 把全表 `prose` 拉进 Python 数字数:

```python
def stats(self) -> dict:
    rows = self._query("SELECT prose FROM chapter")          # 全表拉正文(可能很大)
    wc = sum(len("".join((r.get("prose") or "").split())) for r in rows)
    return {"chapter_count": len(rows), "word_count": wc}
```

**问题**:把整本书的 prose 字符串全部传到 Python 只为数字数,数据传输量 = 全书字数。

**方案 A:DB 侧聚合查询(最小改动,先做)**——配合 §3.2 的 `qc_word_count` 缓存字段,字数已在 DB 内,直接聚合:

```sql
-- 字数在 DB 侧求和,不回传 prose(依赖 §3.2 的 qc_word_count 缓存)
SELECT count() AS chapter_count, math::sum(qc_word_count) AS word_count
FROM chapter GROUP ALL;
```

> 若不引入缓存字段、要纯 SQL 在库内数字数:SurrealDB 3.x 有 `string::len()`(`001:8` 已用),理论可 `math::sum(string::len(prose))` 在库内算——但 `string::len` 数的是含空白的字符数,与 Python 端 `"".join(prose.split())` 去空白口径不同(**需人工确认**是否有等价的"去空白长度"字符串函数,如 `string::replace` 去空白后取 len)。**推荐走方案 A 缓存字段**,口径与现有 `word_count` 一致且只回传整数。

**方案 B:物化预聚合视图(DEFINE TABLE … AS SELECT)**——SurrealDB 的预聚合视图,DB 自动随基表变更维护(06§2.1 称此能力"未用"):

```sql
-- scribe3 · 预聚合视图(枢纽 E §3.4 方案 B)· 需人工确认 3.1.5 物化视图语法/触发时机
DEFINE TABLE IF NOT EXISTS word_stats AS
    SELECT
        count()                  AS chapter_count,
        math::sum(qc_word_count) AS word_count
    FROM chapter
    GROUP ALL;
-- 读:SELECT * FROM word_stats;(DB 维护,免每次聚合)
```

> ⚠️ **需人工确认**:① SurrealDB 3.1.5 的 `DEFINE TABLE … AS SELECT` 物化视图是否随基表写入实时维护、`GROUP ALL` 在视图定义中的支持;② 视图维护的性能代价(每次 chapter 写都更新聚合)。**保守建议:第一阶段先落方案 A(一条聚合 SELECT,零新概念、确定可用),方案 B 作为中期"预聚合视图"的探索项**,确认语法后再上。

**伏笔超期预聚合**(替代坏 cron,呼应 §3.3c):

```sql
-- open + 超期伏笔计数,供仪表盘/告警直接读(/quality 的 foreshadow 块,app.py:292-296)
-- $mc = 当前最大章(可由 §3.3a 的 meta:manuscript.last_saved_seq 提供,免 max_chapter 全表扫)
SELECT
    count()                                              AS open_count,
    count(setup_chapter + 3 < $mc)                       AS overdue_count
FROM promise WHERE status = 'open';
```

> 注:`count(<布尔表达式>)` 在 SurrealDB 里对真值计数的确切写法**需人工确认**(可能需 `count(IF setup_chapter+3 < $mc THEN 1 END)` 或 `math::sum(...)` 形式);逻辑意图明确即可,落地时按实测语法定稿。`app.py:295` 现有 Python 实现 `p["setup_chapter"] + 3 < mc` 是口径来源("超过 3 章未收"=超期)。

### 3.5 ⑤ chapter.prose 向量化 + HNSW(章节级 RAG)

**现状**(06§2.3):embedding 只存 `proposition.embedding`(`003:3`),**`chapter.prose` 正文未向量化** → "查与某段语义相近的章节正文"做不到。`semantic_recall`(`store.py:236`)只能召回**命题**(结构化事实),召回不到**叙述文本**。

**设计**:给 `chapter` 加 `embedding` 字段 + HNSW 索引,与 `proposition` 同维同距(512 / COSINE,匹配 `embed.py` 的 bge-small-zh-v1.5):

```sql
-- scribe3 · 012_chapter_vector.surql · 章节级 RAG(枢纽 E §3.5)
DEFINE FIELD IF NOT EXISTS embedding ON chapter TYPE option<array<float>>;
-- 与 003_vector.surql 的 idx_prop_vec 同参:512 维 = bge-small-zh-v1.5,COSINE
DEFINE INDEX IF NOT EXISTS idx_chapter_vec ON chapter
    FIELDS embedding HNSW DIMENSION 512 DIST COSINE;
```

写入:存稿后对 prose embed 一次(章节较长,**需人工确认**是否需分段/截断 embed——bge-small-zh 有输入长度上限,整章可能超长;可取"章摘要"或分段后取均值/首段,落地时定策略):

```sql
-- 存稿后写章向量(仍经 _execute_write;向量由 embed.py 在应用侧算好绑参 $v)
UPDATE type::record('chapter', $seq) SET embedding = $v;
```

章节级语义召回(与 `semantic_recall` 同构,KNN 算子 `<|k,COSINE|>`):

```sql
-- 章节语义检索:给定查询向量 $qv,召回最相似的 k 章正文
SELECT seq, title, vector::distance::knn() AS dist
FROM chapter
WHERE embedding <|5,COSINE|> $qv
ORDER BY dist;
```

> ⚠️ **HNSW EFC/M 调参(需人工确认)**:`003:4` 与本索引均未显式设 `EFC`/`M`(用默认)。06§2.3 注:"小数据可接受,规模化需关注"。章数远少于命题数(数百章 vs 数千命题),默认参数大概率够用;若召回质量不足,再调 `EFC`(构建期精度)/`M`(图连接度)。
> ⚠️ **维度耦合**:512 硬编码与 `embed.py` 的 bge-small-zh(512 维)耦合(06§2.2 ④)。换 embedding 模型须同步改 `DIMENSION`,否则运行时炸。章向量与命题向量**必须同模型同维**,否则不可跨表混排。

### 3.6 ⑥ Hybrid Search:DEFINE ANALYZER + SEARCH BM25 + RRF 融合

**现状**(06§2.3 / §3.1):纯单路向量召回(`semantic_recall`),无全文 BM25 路,无 RRF 融合。向量召回擅长"语义相近",但对**专名/罕用词精确匹配**(法器名、人名)弱;全文 BM25 正好互补。Hybrid = 两路召回 + RRF(Reciprocal Rank Fusion)融合排名。

**步骤 1:定义分析器(中文分词)**

```sql
-- scribe3 · DEFINE ANALYZER(枢纽 E §3.6)· 需人工确认 3.1.5 中文分词器可用项
-- SurrealDB 内置 tokenizer/filter;中文需确认是否有 ngram/中文友好分词。
DEFINE ANALYZER IF NOT EXISTS zh_analyzer
    TOKENIZERS class
    FILTERS lowercase;
```

> ⚠️ **需人工确认(中文分词关键)**:SurrealDB 的内置 tokenizer(`blank`/`camel`/`class`/`punct`)对**中文**支持有限——中文无空格,`blank` 分不开,`class` 按字符类粗分。常见做法是 `FILTERS ngram(1,2)` 或 `edgengram` 做 N-gram 切分以支持中文子串匹配。**3.1.5 是否提供 ngram filter、对中文的实际召回质量须实测**;若内置分词对中文不可用,全文路可能需要外部分词预处理(与"100% SurrealDB 原生"目标冲突,需权衡)。这是本枢纽 **不确定性最高的一项**。

**步骤 2:全文索引(在 chapter.prose 与 proposition.value 上)**

```sql
-- 章节正文全文索引(BM25 打分)
DEFINE INDEX IF NOT EXISTS idx_chapter_fts ON chapter
    FIELDS prose SEARCH ANALYZER zh_analyzer BM25 HIGHLIGHTS;
-- 命题值全文索引
DEFINE INDEX IF NOT EXISTS idx_prop_fts ON proposition
    FIELDS value SEARCH ANALYZER zh_analyzer BM25;
```

**步骤 3:全文查询(`@@` 匹配 + `search::score`)**

```sql
-- 单路全文:@N@ 绑定第 N 个匹配算子,search::score(N) 取 BM25 分
SELECT seq, title, search::score(0) AS score
FROM chapter
WHERE prose @0@ $q
ORDER BY score DESC LIMIT 20;
```

**步骤 4:RRF 融合(向量路 + 全文路)**

RRF 公式:每个文档的融合分 = Σ over 各路 `1 / (k_rrf + rank_in_that_path)`(`k_rrf` 常取 60)。SurrealDB 单条 SQL 内做完整 RRF 较复杂(需两个有序召回再按 record 合并打分);务实做法是**两路各召回 top-N,在 store 应用层做 RRF 合并**,或用子查询拼。示意(应用层 RRF,最稳):

```sql
-- 路 A:向量召回 top-K(返回有序 record id 列表)
SELECT id, seq FROM chapter WHERE embedding <|20,COSINE|> $qv ORDER BY vector::distance::knn();
-- 路 B:全文召回 top-K
SELECT id, seq, search::score(0) AS s FROM chapter WHERE prose @0@ $q ORDER BY s DESC LIMIT 20;
-- 融合:store 侧对两个有序列表算 RRF = Σ 1/(60 + rank),按融合分重排,取 top-k 返回
```

> ⚠️ **需人工确认**:① `@@`/`@N@` 匹配语法与 `search::score(N)` 的 N 索引绑定规则在 3.1.5 的确切形式;② 能否在**单条 SurrealQL** 内用 `math::` / 子查询表达完整 RRF(若可,则免应用层合并)。**保守路线:RRF 融合放 store 应用层(纯算法,确定可实现),DB 只负责两路召回**——这与 06§4.4 "可包成新 MCP 工具 `s3_graph_recall`"的封装思路一致,Hybrid 可作为 `s3_hybrid_recall`。
> ⚠️ Hybrid 与枢纽 B 的 Graph RAG(06§4.4)**共享同一向量基础**(同 HNSW、同 embed 模型);三者(章节 RAG / Hybrid / Graph RAG)是同一向量底座上的三种召回策略,应协同设计,不重复建向量。

---

## 4. TDD 实施计划(bite-sized)

> 测试基线:scribe3 后端 24 测试,核心模块几乎全覆盖(03§9),`conftest.py` 已有真库 fixture(03§5 提及 `conftest.py:35`)。索引/事件/缓存均可在真库 fixture 上验证。下列每条都是可独立提交的小步。

### 阶段一:索引(加 DEFINE INDEX → 验证走索引)

> 索引类不写"功能测试",而是"**加 DEFINE INDEX → 用查询计划/耗时对比验证走索引**"。SurrealDB 用 `EXPLAIN`(**需人工确认 3.1.5 的查询计划命令是 `EXPLAIN <query>` 还是其他**)看是否命中索引(operation: Iterate Index vs Iterate Table)。

1. **建基准**:在 apply `010_indexes.surql` **前**,对 `facts_at` 的 SQL 跑 `EXPLAIN`,记录"全表扫"(Iterate Table)与耗时(可造 N 条命题数据放大差异)。
2. **加 `idx_prop_valid` → 验证**:apply 后同一 `EXPLAIN` 应显示命中 `idx_prop_valid`(Iterate Index);耗时对比应下降。**断言**:计划里出现索引名 / 不再是全表扫。
3. 逐条同法验证 `idx_knows_since`(`knowledge`)、`idx_event_chapter`(`events_at`)、`idx_voice_char`(`latest_voice_samples`)走对应索引。
4. **唯一索引行为测试**:`idx_chapter_seq UNIQUE` —— 对同一 `seq` 两次 `CREATE`(非 UPSERT)应被 DB 拒(断言抛唯一冲突);UPSERT 同 seq 仍正常覆盖(`store.py:371` 路径不破)。`idx_motif_name UNIQUE` 同理。
5. **上线前置守护**:写一条测试"库内 `SELECT seq, count() FROM chapter GROUP BY seq` 无 >1"作为加唯一索引的前置断言(防在脏数据上 apply 失败)。
6. **`open_promises` 下推**:改 `store.py:360` 为 `WHERE status='open'` 后,测试"`open_promises` 结果不变"(行为等价)+ `EXPLAIN` 命中 `idx_promise_status`。

### 阶段二:/quality 章级缓存(写测试:命中)

7. **缓存写入**:`save_chapter` 后,`get_chapter(seq)` 应带 `qc_word_count`/`qc_issues`/`qc_causal`/`qc_at` 非空。**断言**:存稿即缓存,数值 == 现算 `quality_flags` 结果(缓存与重算一致)。
8. **缓存命中**:`/quality` 读已缓存章**不调用** `quality_flags`(用 mock/spy 断言 `quality_flags` 未被调用,或断言耗时 ~O(章数) 而非 O(全量扫描))。
9. **惰性回填**:对 `qc_at=NONE` 的旧章,`/quality` 回退现算并回写;第二次 `/quality` 该章走缓存(spy 断言第二次不重算)。
10. **缓存失效语义**:改 prose(再 `save_chapter`)后 `qc_at` 更新、`qc_*` 随新 prose 变化(断言缓存随存稿刷新,不陈旧)。

### 阶段三:DEFINE EVENT(写测试:触发后副作用)

11. **ON chapter 触发**:apply `ev_chapter_saved` 后,`CREATE`/`UPDATE` 一章 → 查 `meta:manuscript.last_saved_seq` == 该章 seq(**断言事件副作用发生**)。
12. **ON proposition 触发**:`CREATE` 一条 `attribute='转变'` 的命题 → 查 `voice_evolution_flag` 多出一条对应 `character`/`seq`(断言);`attribute` 不在触发集时**不**产标记(断言负例)。
13. **ON promise 审计**:把一条 promise 从 `open` `UPDATE` 为 `closed` → `promise_audit` 多一条(断言);`open`→`open` 不产审计(负例)。
14. **事件不破限知**:断言事件副作用**不写 `knows` 边**(防 DB 层绕过限知发知识边)——查事件触发前后 `knows` 行数不变。

### 阶段四:章节 RAG + Hybrid(中期)

15. **章向量写入**:存稿后 `chapter.embedding` 非空、长度 == 512(断言维度匹配 `idx_chapter_vec`)。
16. **章节语义召回**:造两章语义差异明显的 prose,用其一的近义查询召回,断言 top-1 是对的那章(`<|k,COSINE|>` 召回正确)。
17. **全文召回**:造含特定专名的章,全文 `@@` 查该专名,断言命中(BM25 路工作)——**前置:确认 `zh_analyzer` 中文分词可用**(§3.6 风险)。
18. **RRF 融合**:构造"向量近但无关键词" vs "有关键词但语义远"两章,断言 RRF 后两者都进 top-k(融合优于单路)。

---

## 5. 验收标准

| # | 标准 | 验证方式 |
|---|---|---|
| AC-1 | **时间门查询走索引** | `facts_at`/`events_at`/`knows`/`voice_sample` 的 `EXPLAIN` 显示 Iterate Index(命中 `010_indexes.surql` 对应索引),非全表扫 |
| AC-2 | **唯一约束生效** | `chapter.seq` / `motif.name` 重复写被 DB 拒;UPSERT 路径不破(`store.py:371` 正常) |
| AC-3 | **/quality 读缓存** | `/quality` 不再逐章重跑 `quality_flags`(spy 断言);章级 `qc_*` 字段随存稿落库且与现算一致 |
| AC-4 | **stats 不回传全文** | `stats()` 用 DB 侧聚合(方案 A),不再 `SELECT prose FROM chapter` 全表拉正文 |
| AC-5 | **事件触发生效** | `ON chapter`/`ON proposition`/`ON promise` 事件副作用可观测(`meta:manuscript`/`voice_evolution_flag`/`promise_audit` 被写);且不写 `knows` 边(限知不破) |
| AC-6 | **prose 可语义检索** | `chapter.embedding` 写入(512 维)+ `idx_chapter_vec` HNSW;章节语义召回返回正确章 |
| AC-7 | **Hybrid 可用(中期)** | 全文 `@@`/`search::score` 召回 + RRF 融合返回结果,融合优于单路(前提:中文分词确认可用) |
| AC-8 | **限知不破 / 单点不破** | 全程改世界状态写仍经 `_execute_write`(`store.py:121`);新增索引/事件不改投影屏蔽逻辑;现有 24 测试全绿 |

---

## 6. 风险与依赖

### 6.1 分阶段与风险等级

| 项 | 阶段 | 风险 | 说明 |
|---|---|---|---|
| **DEFINE INDEX(§3.1)** | **第一阶段(可早做)** | 🟢 几乎零风险 | 03§8 / 06§4.1 共同认定"几行 surql,零逻辑风险,ROI 最高"。**唯一注意**:UNIQUE 索引须先核无重复数据(§3.1 前置检查),否则 apply 报错 |
| /quality 缓存(§3.2) | 第一/二阶段 | 🟢 低 | 加 `option` 字段向后兼容;惰性回填免 backfill;`qc_causal` 新鲜度有弱假设(§3.2 已述) |
| 预聚合方案 A(§3.4) | 第一阶段 | 🟢 低 | 一条聚合 SELECT,确定可用 |
| 预聚合方案 B 物化视图(§3.4) | 中期 | 🟡 中 | 3.1.5 物化视图语法/维护代价**需人工确认** |
| DEFINE EVENT(§3.3) | 中期 | 🟡 中 | `$before`/`$after`/`$event` 语义**需人工确认**;**红线**:事件绕过 `_execute_write` 审计,只可做纯 DB 副作用,**不可发 `knows` 边**(否则破限知单点) |
| 章节 RAG(§3.5) | 中期 | 🟡 中 | 整章超 embed 长度上限的分段策略**需人工确认**;维度与 `embed.py` 耦合 |
| Hybrid / 中文分词(§3.6) | 中期 | 🟠 偏高 | **本枢纽最不确定项**:SurrealDB 内置分词对中文支持**需实测**;若不可用,全文路或需外部分词(与"100% 原生"冲突) |

### 6.2 依赖关系

- **依赖枢纽 D(命名统一)**:本枢纽索引字段名沿用当前迁移现状(`event.valid_from`、`proposition.entity` 裸字符串、`voice_sample.character` 裸字符串)。**D 落地后字段名才稳定**——若 D 把 `event.valid_from` 改名 `story_chapter`(06§4.2 建议)、`entity` 升 `record<character|place>`,则 §3.1 的 `idx_event_chapter`/`idx_prop_entity` 字段名、§3.3b 的 `$after.entity` 须同步改。**建议:DEFINE INDEX 这一刀可在 D 之前先落"字段名当前稳定"的那部分(`valid_from`/`valid_to`/`since_chapter`/`status`/`seq`/`name`),涉及会被 D 改名/改类型的字段(`entity`)的索引留到 D 之后**,避免返工。
- **与枢纽 B(Graph RAG)协同**:章节 RAG(§3.5)、Hybrid(§3.6)、B 的 Graph RAG(06§4.4)**共享同一向量底座**(同 HNSW、同 bge-small-zh-512、同 COSINE)。三者是同一基础上的不同召回策略,**必须协同设计、不重复建向量**;建议统一封装为 `s3_*_recall` 系列 MCP 工具(06§4.4 已为 Graph RAG 提此模式)。
- **依赖 §3.2 缓存字段**:预聚合方案 A(§3.4)的 `math::sum(qc_word_count)` 依赖 §3.2 先落 `qc_word_count` 字段;若不做缓存,退回"全表聚合 prose 长度"(口径差异见 §3.4)。
- **embed 模型耦合**:§3.5 章向量维度(512)硬耦合 `embed.py` 的 bge-small-zh(06§2.2 ④);换模型须同步改所有 `DIMENSION`。
- **环境**:SurrealDB **3.1.5**(实测,本文基线);Python `surrealdb` 客户端(`store.py:14`)。**不盲升 SurrealDB**(MEMORY:3.1.5 是最新线;Hermes 落后另议)。

### 6.3 安全/不变量红线复述

- 所有改世界状态写经 `_execute_write`(`store.py:121`)——索引/字段是 DDL(走 `apply_schema`),DML 写不新增旁路。
- **DEFINE EVENT 是 DB 层执行、绕过应用审计**:严格限制其只做"纯 DB 内、不涉私密/限知"的副作用;改变"谁知道什么"的级联**仍留应用层 ingest**(§3.3 边界)。
- 限知投影屏蔽逻辑不改;新增 `chapter.embedding`/全文索引服务作者侧检索,仍受 MCP 工具层限知封装(06§3.1)。
- 不做破坏性操作;唯一索引上线前**先只读核查重复数据**,不在脏数据上强 apply。

---

## 7. 闭环问题清单(对账)

| 来源编号/项 | 描述 | 本枢纽对应章节 | 闭环? |
|---|---|---|---|
| **P05** 🔴(03§4) | 除 HNSW 外零索引,所有时间门全表扫(`proposition.valid_from/to`、`knows.since_chapter`、`voice_sample.character`、`event.valid_from`、`promise.status`) | §3.1 全部 10 条 DEFINE INDEX + §4 阶段一查询计划验证 | ✓ |
| **P29**(03§4) | /quality 逐章重活、无缓存/分页(`app.py:274-289`) | §3.2 章级 QC 缓存 + §4 阶段二缓存命中测试 | ✓ |
| **P04**(03§4,关联) | `knowledge` @property 每访问 2 条全表查询(`store.py:429`) | §3.1 `idx_knows_since`/`idx_rknows_since`(P04 的"改显式方法 + 缓存"属枢纽 A/重构,本枢纽补其索引侧) | ◐ 索引侧闭环;@property 改方法见他枢纽 |
| **DEFINE EVENT 未用**(06§2.4) | ingest 级联/voice 标记/promise 超期全应用层手工 | §3.3 三个事件示例 + §4 阶段三触发测试 | ✓(给方案;voice 标记/promise 超期可下沉,ingest 知识级联因限知红线仍留应用层——已说明) |
| **预聚合视图未用**(06§2.1) | `stats()` 全表拉 prose 数字数(`store.py:383`) | §3.4 方案 A(聚合 SELECT)+ 方案 B(物化视图,需确认) | ✓(方案 A 确定;方案 B 标需确认) |
| **章节级 RAG 缺失**(06§2.3) | embedding 只覆盖 proposition,`chapter.prose` 未向量化 | §3.5 chapter.embedding + HNSW + 章节语义召回 | ✓ |
| **Hybrid Search/RRF 未用**(06§2.3) | 纯单路向量,无全文 BM25 + RRF | §3.6 DEFINE ANALYZER + SEARCH BM25 + RRF | ◐ 给完整方案,但中文分词可用性**需实测**(最高不确定项) |
| **chapter.seq 无 unique**(06§2.2) | 重复 ingest 产重复章行 | §3.1 `idx_chapter_seq UNIQUE` | ✓ |
| **motif 无 unique**(06§2.2) | 重复 ingest 产重复母题 | §3.1 `idx_motif_name UNIQUE` | ✓ |

**对账小结**:P05 ✓、P29 ✓ 两个点名问题完全闭环;DEFINE EVENT / 预聚合 / 章节 RAG 三项给出确定可落地方案;Hybrid 给完整设计但中文分词留实测验证;P04 的索引侧在本枢纽闭环、其 @property 重构归他枢纽。

---

> **自评(SurrealQL 语法)**:
> - **高置信(确定可用,有库内既有用法佐证)**:`DEFINE INDEX … FIELDS …`(常规/UNIQUE)、`DEFINE INDEX … HNSW DIMENSION 512 DIST COSINE`(照搬 `003:4` 实测可用)、`<|k,COSINE|>` KNN 算子(`store.py:243` 实测可用)、`vector::distance::knn()`、`DEFINE FIELD … TYPE option<…>`、聚合 `count()`/`math::sum()`/`GROUP ALL`、`string::len()`(`001:8` 实测可用)、`UPSERT … SET …` + `type::record()`(store 实测)。
> - **中置信(语法按 SurrealDB 3.x 通行写法,但 3.1.5 细节标了"需人工确认")**:`DEFINE EVENT … WHEN … THEN { … }` 及 `$event`/`$before`/`$after` 变量名与取值;`DEFINE TABLE … AS SELECT` 物化视图的维护时机;`count(<布尔>)` 对真值计数的确切形式。
> - **低置信(已显式标"需人工确认",落地前必实测)**:`DEFINE ANALYZER` 对**中文**的分词(tokenizer/ngram filter 可用性)——**本文最大不确定项**;`@@`/`@N@` + `search::score(N)` 全文匹配语法;`EXPLAIN` 查询计划命令的确切形式;HNSW `EFC`/`M` 调参值;整章超长 prose 的 embed 分段策略。
> - **限知/单点**:全程未引入绕过 `_execute_write` 的 DML 写路径;DEFINE EVENT 显式限定不发 `knows` 边、不碰私密判断,限知不变量保持。
>
> 本文为只读分析产出的方案文档,未改任何代码、未 commit、未打印任何 secret。
