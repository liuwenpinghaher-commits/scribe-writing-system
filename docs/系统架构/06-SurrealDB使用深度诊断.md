# 06 · SurrealDB 使用深度诊断

> 对象:**scribe3** 对 SurrealDB 的使用现状、深度、未用能力,以及含两组件协同的综合改进方案。
> 取证基于 `surreal version` 二进制实测 + 9 个迁移 + `store.py`/`live.py`/`embed.py`,精确到 `文件:行号`/表名/字段名。
> 配套 [01](./01-系统架构总览.md)–[05](./05-HermesAgent使用深度诊断.md)。

---

## 0. 环境基线

| 项 | 实测值 |
|---|---|
| SurrealDB 版本 | **3.1.5 for macos on aarch64**(`~/.surrealdb/surreal version`,当前最新线) |
| 连接 | `ws://127.0.0.1:8001/rpc`(`store.py:34/103`),WebSocket RPC |
| 命名空间 | NS=`scribe3`(与 scribe2 的 NS=scribe 物理隔离) |
| 库划分 | **一书一 DB**(`db=<slug>`),注册表 `db=_reg`,默认主书 `db=main` |
| 凭证 | **root/root 明文硬编码**(`store.py:40/105`、`live.py:22`) |
| 全库索引 | **仅 1 个**:HNSW 向量(`003_vector.surql`);无其他 DEFINE INDEX |

---

## 2.1 SurrealDB 核心能力使用清单

> 深度档:**深**/**中**/**浅**/**无**。SurrealDB 3.x 的卖点是"图+文档+向量+实时单库",下表看 scribe3 兑现了几成。

| 能力模块 | 是否使用 | 使用位置 | 使用深度 | 备注 |
|---|---|---|---|---|
| 文档模型 | ✅ 是 | 全部 13 表 | 深 | 每表本质文档行 |
| 关系模型(普通字段存 ID 手动匹配) | ✅ 是(**反模式重度依赖**) | `proposition.entity`(`001:18`)、`reader_knows.proposition`(`002:5`)、`voice_sample.character`(`009:3`) | 深(但错) | 跨表引用全退化成 `TYPE string`,读侧 Python 内存手动匹配,无 JOIN |
| 图模型:Record Links(单向引用) | ❌ 否 | — | 无 | 全库无 `record<…>` 类型 |
| 图模型:Record References(双向) | ❌ 否 | — | 无 | 全库无 `REFERENCE` |
| 图模型:Graph Edges + RELATE(带元数据边) | ✅ 是(**仅 1 条**) | `knows`(`001:36` `TYPE RELATION FROM character TO proposition`),边属性 since/until/polarity/acquired_via | 中 | 唯一图边,建模正确;但见下"递归遍历"——建了不遍历 |
| 递归图遍历(无限深度) | ❌ 否 | — | 无 | `knows` 只 `SELECT … FROM knows` 平铺读(`store.py:431`),**零 `->` 箭头遍历**。图边当普通边表用 |
| 向量索引(HNSW) | ✅ 是 | `003:4` `idx_prop_vec … HNSW DIMENSION 512 DIST COSINE` | 深 | **用得最到位的特性** |
| 向量相似度查询(KNN) | ✅ 是 | `store.py:243` `embedding <|{k},COSINE|> $qv` | 深 | 原生 KNN 算子,非外部向量库 |
| 混合检索(全文+向量 RRF) | ❌ 否 | — | 无 | 仅单路向量召回 |
| Graph RAG(图遍历+向量单查询) | ❌ 否 | `semantic_recall`(`store.py:236`) | 无 | 纯向量,召回后不拼图谱(见 §4.4 改造) |
| 全文索引(FTS + BM25) | ❌ 否 | — | 无 | 无 `DEFINE ANALYZER`/`SEARCH`/`@@` |
| Live Queries(实时订阅) | ✅ 是 | `live.py:25` `c.live(table)`,订阅 9 表 | 中 | 转 SSE 推前端;每表一连接 |
| Table Events(DEFINE EVENT) | ❌ 否 | — | 无 | 全库无 `DEFINE EVENT`;变更反应全在应用层 |
| Async Events | ❌ 否 | — | 无 | 同上 |
| 版本时态表(原生 VERSION) | ❌ 否 | — | 无 | 双时态**手工自建**(valid_from/since_chapter,`001:21`),非原生 |
| 预聚合视图(DEFINE TABLE AS SELECT) | ❌ 否 | — | 无 | `stats()` 把全表 prose 拉进 Python 数字数(`store.py:383`),未用 DB 聚合 |
| Schemafull 模式 | ✅ 是 | 9 SCHEMAFULL / 4 SCHEMALESS | 中 | 核心本体强约束 |
| Table Constraints(ASSERT) | ⚠️ 几乎否(仅 2 处) | `001:8/14`(`name len>0`) | 浅 | status/kind/polarity/acquired_via 等枚举**全无 ASSERT**,只靠注释 |
| Record ID Ranges(时序 ID) | ❌ 否 | — | 无 | ID 是语义自定义(`fact:k{seq}-{i}`),非时序范围 |
| Custom Functions(fn::) | ❌ 否 | — | 无 | 逻辑全在 Python `store.py` |
| JavaScript Functions | ❌ 否 | — | 无 | — |
| WebAssembly 插件 | ❌ 否 | — | 无 | — |
| SurrealML(内置 ML) | ❌ 否 | — | 无 | 向量嵌入用外部 fastembed(`embed.py`) |
| File Storage Buckets | ❌ 否 | — | 无 | 正文存 `chapter.prose` string 字段 |
| Multi-tenancy(NS/DB 隔离) | ✅ 是(库级) | NS=scribe3,一书一 DB(`store.py:37-95`) | 中 | 物理分库;但身份层零隔离(见 2.5) |
| Row-level Permissions | ❌ 否 | — | 无 | 全库无 `PERMISSIONS` |
| Record Access(DEFINE SCOPE/ACCESS) | ❌ 否 | — | 无 | 无应用级用户/JWT;全 root |
| Custom HTTP API(DEFINE API) | ❌ 否 | — | 无 | HTTP 走 FastAPI |
| GraphQL 自动生成 | ❌ 否 | — | 无 | — |
| WebSocket 实时连接 | ✅ 是 | `ws://…:8001/rpc`(`store.py:34`) | 中 | LIVE 依赖 |
| LangChain Integration | ❌ 否 | — | 无 | — |
| MCP Server(官方 DB-MCP) | ❌ 否 | — | 无 | scribe3 用自家 `mcp.py`,非 SurrealDB 官方 MCP(见 §3.1) |
| OpenTelemetry | ❌ 否 | — | 无 | — |
| Surrealist UI(可视化) | ⚠️ 需人工确认 | — | — | 开发期可能用过看图,不在代码;非运行依赖 |

**统计**:34 项里**实质用了 7 项**(文档/关系字段/Graph Edge/HNSW/KNN/LIVE/NS-DB/WS),其余 ~27 项未用。**SurrealDB 选型的"图+向量+文档+实时"四卖点,只兑现了向量;图能力建了一条边却不遍历,实时只做了 LIVE 不做 Event。**

---

## 2.2 Schema 设计质量审查

### 全表清单

| 表 | 模式 | 字段数 | 关键约束/备注 |
|---|---|---|---|
| `character` | SCHEMAFULL | 4 | `name ASSERT len>0`;`created` READONLY;`aliases array DEFAULT[]` — `001:7-11` |
| `place` | SCHEMAFULL | 1 | `name ASSERT len>0` — `001:13-14` |
| `proposition` | SCHEMAFULL | 8(+embedding) | 双时态 valid_from/to;secret;leak_markers;embedding option — `001:17-25`+`003:3` |
| `event` | SCHEMAFULL | 5 | ⚠️ **participants/effects/preconditions/location/causal_in 无字段** — `001:28-33` |
| `knows` | SCHEMAFULL **RELATION** | 4 | `FROM character TO proposition`;边属性 since/until/polarity/acquired_via — `001:36-40` |
| `reader_knows` | SCHEMAFULL | 2 | `proposition string`(应 record link)、since_chapter — `002:4-6` |
| `chapter` | SCHEMAFULL | 5 | ⚠️ `seq` 无 unique index — `004:3-8` |
| `promise` | SCHEMAFULL | 5 | ⚠️ status/kind 无 ASSERT — `005:3-8` |
| `motif` | SCHEMAFULL | 4 | — `006:3-7` |
| `intent` | **SCHEMALESS** | 0 声明 | 单例;reader_feeling 等字段未在 schema 声明 — `007:3` |
| `craft_rule` | **SCHEMALESS** | 3 | — `008:3-6` |
| `voice_sample` | **SCHEMALESS** | 4 | — `009:2-6` |
| `voice_evolution_flag` | **SCHEMALESS** | 4 | ⚠️ status 无 ASSERT;`done` 是死值 — `009:9-13` |
| `work`(@`_reg`) | **SCHEMALESS** | 0 声明 | 运行时建表,字段全无声明(`store.py:42`) |

### 关系建模方式评估

| # | 关系 | 当前建模 | 最优? | 建议 |
|---|---|---|---|---|
| 1 | character →知道→ proposition | ✅ Graph Edge `knows` | **正确**(有元数据需边),但从不遍历 | 保持 + 增多跳遍历查询(§4.4) |
| 2 | `proposition.entity` → character/place | ❌ 裸字符串(`001:18`) | ❌ 直接跳转,该用 link | 🔴 **升 Record Link** `record<character\|place>` |
| 3 | `reader_knows.proposition` → proposition | ❌ 裸字符串(`002:5`) | ❌ | 🔴 **升 Record Link** `record<proposition>` |
| 4 | `voice_sample.character` → character | ❌ 裸字符串(`009:3`) | ❌ | 🟡 **升 Record Link** `record<character>` |
| 5 | `voice_evolution_flag.character` → character | ❌ 裸字符串(`009:10`) | ❌ | 🟡 升 Record Link |
| 6 | **Event → 参与者 character** | ❌ **持久层整片丢失**(`event` 表无 participants;`add_event` `store.py:177` 不写) | 🔴 **数据蒸发** | 🔴 **建 Graph Edge** `RELATE event->involves->character SET role`(多对多+角色元数据+需遍历) |
| 7 | **Event → 效果 proposition(effects)** | ❌ **持久层丢失**(因果来源蒸发) | 🔴 | 🔴 **建 Record Link** `proposition.caused_by record<event>` 或 `RELATE event->causes->proposition` |
| 8 | Event → 因果 Event(causal_in) | ❌ 持久层丢失 | 🔴 verify.causal_complete 无数据可依 | 🔴 **Graph Edge** `RELATE event->causal->event SET ctype` |
| 9 | promise ↔ 角色/事件 | ❌ 无任何关联(`005`) | ⚠️ 伏笔与触发事件脱钩 | 🟡 视需求 `promise.setup_event record<event>` |
| 10 | `chapter.focalizer` → character | ❌ 裸字符串 option(`004:6`) | ❌ | 🟡 升 `option<record<character>>` |

**根因**:`store.py:19-30` 的 `ONT2TBL/_split/_join` 在 Python 层手工做 oid↔record 映射,把本可由 SurrealDB record link 原生表达的引用全降级成字符串,丧失引用完整性、级联与图查询能力。**唯一正确建模的 `knows` 边又从不被遍历**——SurrealDB 图能力基本闲置。

**其他 schema 问题**:① ASSERT 严重不足(13 表仅 2 处);② `chapter.seq`/`promise`/`motif` 无 unique index,重复 ingest 产重复行;③ SCHEMALESS 表(intent/work)字段无声明,违背"建 schema 防漂移"初衷;④ HNSW DIMENSION 512 硬编码,与 `embed.py` 的 bge-small-zh(512 维)耦合,换模型维度不匹配会运行时炸。

---

## 2.3 向量与检索能力使用评估

- **存储**:embedding 存 `proposition.embedding`,类型 `option<array<float>>`(`003:3`)。**只覆盖命题,`chapter.prose` 正文未向量化**——章节级语义检索缺失。
- **HNSW 索引**:`003:4` `DIMENSION 512 DIST COSINE`。512 对应 `BAAI/bge-small-zh-v1.5`(512 维,`embed.py:2`)——**匹配,合理**;COSINE 对 bge 归一化句向量**正确**。⚠️ 未显式设 HNSW 的 `EFC`/`M` 调参(用默认),小数据可接受,规模化需关注。
- **查询**:`semantic_recall`(`store.py:236-245`)`SELECT …, vector::distance::knn() AS dist FROM proposition WHERE embedding <|{k},COSINE|> $qv ORDER BY dist`——**语法正确**,k 经 `int(k)` 防注入。
- **原生 vs 外部**:✅ **100% SurrealDB 原生**,无 pgvector/Pinecone/Qdrant 外部库。**无迁移必要**(这是当前最该保持的特性)。
- **Graph RAG**:❌ 未用(召回后不沿 knows/entity 拼图谱)。
- **Hybrid Search/RRF**:❌ 未用(无全文 BM25 路)。

> 评估:向量检索是 scribe3 用得最对的一块——原生、参数合理、语法正确。**升级空间在"从纯向量 → Graph RAG + Hybrid"**(§4.4),而非换库。

---

## 2.4 实时能力使用评估

- **LIVE SELECT 用在**:`live.py:25` `c.live(table)`+`subscribe_live`,订阅 9 表(`character,place,proposition,event,knows,reader_knows,promise,motif,chapter`,`app.py:611`)→ 转 SSE 推前端"哪张表变了",前端 `tick++` 重取。**架构:每表一条独立 WS 连接**(`live.py:20-31`,9 表=9 连接,注释称避免单连接多订阅不确定性)。
- **Table Events / Async Events**:❌ **完全未用**(无 `DEFINE EVENT`)。所有"变更反应"靠客户端 LIVE 拉取,无服务端触发。
- **该用实时/事件却没用的场景**:
  1. 🔴 **ingest 级联**:render→存→ingest→知识态更新(`ingest.py:1-5`)本可 `DEFINE EVENT ON chapter WHEN $event="CREATE" THEN …` 在 DB 层触发,现在全应用层手工编排。
  2. 🟡 **voice_evolution_flag 自动标记**(`store.py:340`)可由 `DEFINE EVENT ON proposition` 触发。
  3. 🟡 **promise 超期告警**(`005:2`)是典型 event/聚合视图场景,现靠 cron 主动扫(且 cron 当前坏,见文档05 R1)。
  4. ⚠️ LIVE 仅单节点(`live.py:4` 自承);多节点部署实时不可用。

---

## 2.5 多租户与权限设计

| 维度 | 现状 |
|---|---|
| NS/DB 隔离 | ✅ **库级物理隔离**:NS=scribe3,一书一 DB(`db=<slug>`),注册表 `db=_reg`;建书给独立 DB 建全套 schema,删书 `REMOVE DATABASE IF EXISTS {slug}`(主书保护 + slug alnum 白名单,`store.py:62-65`) |
| Row-level Permissions | ❌ **零**(全库无 `PERMISSIONS`) |
| DEFINE SCOPE/Record Access | ❌ **零**(无应用级用户/JWT/登录态) |
| 凭证 | 🔴 **全程 root/root 明文硬编码**(`store.py:40/102/105`、`live.py:22`、`conftest.py:35`) |
| 多用户隔离在 DB 层 | 🔴 **未实现**:隔离止于"一书一 DB",但所有书共用同一 root 账户,DB 层无法表达"用户 A 只能访问自己的书";租户隔离完全靠应用层(FastAPI)自律,DB 裸奔 |

> 结论:多租户在"**内容分库**"维度做到了,在"**身份/权限**"维度**零实现**。本地单用户语境可接受;**生产化/多用户前必须引入 DEFINE ACCESS(RECORD/JWT)+ PERMISSIONS,并把 root 凭证移出代码**(呼应文档03 P01/P08)。

---

## 3. 两组件协同诊断

### 3.1 Hermes Agent ↔ SurrealDB 集成方式

- **Hermes 如何查 SurrealDB**:**不直连**。链路是 `Hermes 主编(:8643)→ scribe3 自家 MCP(mcp.py 的 s3_ 工具)→ SurrealStore(store.py)→ SurrealDB(:8001)`。即 Hermes 经 **scribe3 应用层 MCP** 间接访问,工具内部调 `store.project_frame`/`store.semantic_recall` 等(`mcp.py:67-162`)。
- **SurrealDB 官方 MCP 是否接入**:❌ 否。scribe3 用的是**自己实现的应用层 MCP**(语义工具如 `s3_project_frame` 返回限知投影),**不是** SurrealDB 官方 DB-MCP(后者会暴露裸 SurrealQL)。**这是有意且更优的选择**——应用层 MCP 封装了限知语义,比让主编直接写 SurrealQL 安全得多(主编无法绕过 project_frame 拿到帧外私密)。**无需接官方 DB-MCP**。
- **Hermes Memory 与 SurrealDB 的关系**:
  - Hermes 原生 FTS5 记忆:❌ scribe3 **未使用**(`memory_enabled:true` 平台开着,应用没接,见文档05)。
  - SurrealDB 作持久记忆后端:**部分意义上是**——scribe3 的"世界事实账本"(proposition/knows)就是主编的长期记忆,但它是**领域数据**不是"Hermes memory 抽象"。
  - 会话/长期/用户模型三层映射:❌ **未映射**。会话上下文靠 `_editor_system` 每次现拼(`app.py:317`),长期记忆=SurrealDB 世界状态(但非 Hermes memory 接口),用户模型层完全无。

### 3.2 Agent 上下文注入方式

- **当前注入方式**:**结构化查询 → 自然语言文本拼接**(混合,非图检索)。两条路:
  1. **速答/写作**:`_editor_system(st)`(`app.py:317-340`)从 SurrealDB 查北极星(intent)+ 角色 + 已确立设定 + open 伏笔,**拼成自然语言** instructions 注入(主编全知,含 secret)。
  2. **联查实证**:主编 agentic 自调 `s3_project_frame` 等工具,拿**结构化 JSON**(限知帧),据此推进。
- **上下文窗口管理**:靠 Hermes `compression.enabled:true`(threshold 0.5,文档05)被动压缩;scribe3 代码侧无主动截断策略,`_editor_system` 全量拼装有膨胀风险(书越大、角色越多,instructions 越长)。
- **是否用 Graph RAG**:❌ 否。`s3_semantic_recall` 是纯向量;`s3_project_frame` 是按 (focalizer,chapter) 取整帧,非图遍历(无"查与 A 相关的 B 的 C")。**这是上下文精准度的最大升级空间**(§4.4)。

---

## 4. 综合改进方案

### 4.1 优先级最高的 10 项改进

| 序号 | 改进项 | 涉及组件 | 当前状态 | 改进描述 | 预期收益 | 工作量 |
|---|---|---|---|---|---|---|
| 1 | 修体检 cron 路径 | Hermes | 🔴 持续失败 | 改 `jobs.json` script 为绝对路径(文档05 R1) | 恢复伏笔/连贯护城河告警 | 极小(10 分钟) |
| 2 | 补数据库索引 | SurrealDB | 仅 HNSW | `proposition(valid_from)`/`knows`/`voice_sample(character)`/`chapter(seq unique)` 加 DEFINE INDEX | 限知投影热路径提速 | 小(<1 天) |
| 3 | 验证 skill 加载 | Hermes | 🟡 未确认 | 确认 `scribe-novel-v2` 真注入 :8643(文档05 R2) | 写作纪律/自进化回路成立 | 小 |
| 4 | 持久化 Event 参与者/效果 | SurrealDB | 🔴 数据蒸发 | `event` 补字段 + `RELATE event->involves->character`/`->causes->proposition` | 修限知裂口(see_event 真库生效) | 中(2-4 天) |
| 5 | `proposition.entity` 升 Record Link | SurrealDB | 裸字符串 | `TYPE record<character\|place>` + 索引 | 引用完整性 + 消除 `_split` + 可 `SELECT entity.name` | 中 |
| 6 | 补枚举 ASSERT | SurrealDB | 仅 2 处 | status/kind/polarity/acquired_via 加 `ASSERT $value IN [...]` | 挡 LLM 写脏值(呼应文档04) | 小 |
| 7 | Graph RAG 改造 semantic_recall | 协同 | 纯向量 | 向量召回 + 沿 knows/entity 遍历拼上下文(§4.4) | 主编上下文从"相似事实"→"相关知识子图" | 中-大 |
| 8 | root 凭证外置 + 起步权限 | SurrealDB | 🔴 全 root 明文 | 凭证移 env;规划 DEFINE ACCESS(生产前) | 安全(文档03 P08) | 小(外置)/大(权限) |
| 9 | ingest 级联用 DEFINE EVENT | SurrealDB | 应用层手工 | `DEFINE EVENT ON chapter` 触发回写/校验 | 减应用层编排,DB 层保证 | 中 |
| 10 | Skills 工序化补全 | Hermes | 仅 1 skill | 新建 5 个工序 skill(文档05 §1.4) | 主编少重推,流程固化 | 中 |

### 4.2 SurrealDB Schema 升级建议(3 个最重要的表)

**① `proposition`(核心本体,升 Record Link + 补因果 + 补索引)**
```surql
DEFINE TABLE proposition SCHEMAFULL;
DEFINE FIELD entity       ON proposition TYPE record<character | place>   -- 升级:裸字符串→link
    ASSERT $value != NONE;
DEFINE FIELD attribute    ON proposition TYPE string;
DEFINE FIELD value        ON proposition TYPE string;
DEFINE FIELD valid_from   ON proposition TYPE int ASSERT $value >= 1;
DEFINE FIELD valid_to     ON proposition TYPE option<int>;
DEFINE FIELD secret       ON proposition TYPE bool DEFAULT false;
DEFINE FIELD leak_markers ON proposition TYPE array<string> DEFAULT [];
DEFINE FIELD embedding    ON proposition TYPE option<array<float>>;
DEFINE FIELD caused_by    ON proposition TYPE option<record<event>>;       -- 新增:补因果来源
DEFINE INDEX idx_prop_vec    ON proposition FIELDS embedding HNSW DIMENSION 512 DIST COSINE;
DEFINE INDEX idx_prop_entity ON proposition FIELDS entity;                  -- 新增:加速主体反查
DEFINE INDEX idx_prop_time   ON proposition FIELDS valid_from, valid_to;    -- 新增:时间门索引
```

**② `event`(补回蒸发的参与者/效果/因果,改用图边)**
```surql
DEFINE TABLE event SCHEMAFULL;
DEFINE FIELD etype             ON event TYPE string;
DEFINE FIELD story_chapter     ON event TYPE int ASSERT $value >= 1;        -- 统一命名(原 valid_from)
DEFINE FIELD location          ON event TYPE option<record<place>>;          -- 补 location link
DEFINE FIELD motivated_by_goal ON event TYPE option<string>;
-- 参与者:多对多 + 角色元数据 → 图边(补回 store.py:177 丢失的 participants)
DEFINE TABLE involves TYPE RELATION FROM event TO character SCHEMAFULL;
DEFINE FIELD role ON involves TYPE string ASSERT $value IN ['SUBJ','OBJ','WITNESS'];
-- 效果:事件初始化的命题 → 图边(支撑"看见即知道")
DEFINE TABLE causes   TYPE RELATION FROM event TO proposition SCHEMAFULL;
-- 因果链:事件→事件
DEFINE TABLE causal   TYPE RELATION FROM event TO event SCHEMAFULL;
DEFINE FIELD ctype ON causal TYPE string;
```
写入示例(替代当前丢字段的 `add_event`):
```surql
CREATE event:对峙 SET etype = '对峙', story_chapter = 1, location = place:乱岗;
RELATE event:对峙 -> involves -> character:老道 SET role = 'SUBJ';
RELATE event:对峙 -> involves -> character:焦三 SET role = 'OBJ';
```

**③ `knows`(已是正确图边,补唯一约束 + 启用遍历)**
```surql
DEFINE TABLE knows TYPE RELATION FROM character TO proposition SCHEMAFULL;
DEFINE FIELD since_chapter ON knows TYPE int ASSERT $value >= 1;
DEFINE FIELD until_chapter ON knows TYPE option<int>;
DEFINE FIELD polarity      ON knows TYPE bool DEFAULT true;
DEFINE FIELD acquired_via  ON knows TYPE string
    ASSERT $value IN ['saw','told','inferred','given','learned'];           -- 补全 learned(文档04)
DEFINE INDEX idx_knows_since ON knows FIELDS since_chapter;                  -- 时间门索引
```

### 4.3 Hermes Skills 补全计划

> 完整清单见 [05-HermesAgent使用深度诊断.md §1.4](./05-HermesAgent使用深度诊断.md)。摘要:建议新建 5 个工序 skill(限知守门 / 伏笔台账 / 声音一致 / 回写校验 / 修订工序),把现散在 SKILL.md 一篇的"写一章 9 步环"拆成可独立触发的工序卡,减少主编重推。**前提:先修文档05 R2(确认 skill 真加载)**。

### 4.4 Graph RAG 改造方案

**现状**(纯向量,`store.py:236-245` `semantic_recall`):
```surql
-- 只按向量相似召回命题,召回后是孤立事实,不带关系上下文
SELECT *, vector::distance::knn() AS dist
FROM proposition
WHERE embedding <|5,COSINE|> $qv
ORDER BY dist;
```

**改造为 Graph RAG**(向量召回种子 + 图遍历拼知识子图,单次查询)。前提是先做 §4.2 的 Record Link + involves/causes 图边:
```surql
-- 「焦三现在处境」类查询:向量找种子命题 → 沿图边拼出"主体/知情者/相关事件"上下文
SELECT
    value,
    attribute,
    valid_from,
    entity.name                              AS 主体,        -- record link 直接取名(原需 _split+二次查)
    <-knows<-character.name                  AS 知情角色,    -- 反向遍历 knows:谁知道这条命题
    <-causes<-event.etype                    AS 来源事件,    -- 反向遍历 causes:哪个事件产生了它
    ->involves->character.name               AS 同场角色,    -- 经事件再跳到同场参与者
    vector::distance::knn()                  AS dist
FROM proposition
WHERE embedding <|5,COSINE|> $qv             -- 向量召回种子
  AND valid_from <= $chapter                  -- 叠加时间门(限知)
ORDER BY dist;
```
**收益**:一次查询同时拿到"语义相关的事实 + 谁知道它 + 它从哪个事件来 + 涉及哪些角色"——主编上下文从"5 条孤立相似事实"升级为"5 个事实各自的知识子图",这是纯向量或纯图都做不到的,正是 SurrealDB"图+向量单库"的杀手锏。可包成新 MCP 工具 `s3_graph_recall` 供主编调用。

> ⚠️ 上述图遍历语法(`<-knows<-character`、`->involves->character`)依赖 §4.2 的图边落地;当前 `knows` 是 character→proposition,反向遍历 `<-knows<-character` 取"知道某命题的角色"语法成立。`involves`/`causes` 边需先按 §4.2 建立。

### 4.5 分阶段实施路线

| 阶段 | 时间 | 核心目标 | 关键任务 | 验收标准 |
|---|---|---|---|---|
| **立即(本周)** | 1-3 天 | 修运行时缺陷 + 补基础约束 | ① 修 cron 路径(R1)② 验 skill 加载(R2)③ 查 :8642 健康(R4)④ 补 DEFINE INDEX(索引)⑤ 补枚举 ASSERT ⑥ root 凭证移 env | cron 转绿;索引生效;脏枚举值被 DB 拒;凭证不落明文 |
| **短期(本月)** | 2-4 周 | 激活闲置图能力 + 补限知裂口 | ① `proposition.entity` 升 Record Link ② `event` 补 involves/causes 图边(修 see_event 真库失效)③ ingest 级联用 DEFINE EVENT ④ 补 5 个工序 skill ⑤ ingest 幂等(文档03 P07) | 真库 see_event 生效;删角色可级联;主编按工序 skill 工作 |
| **中期(本季度)** | 1-3 月 | Graph RAG + 生产化权限 | ① `s3_graph_recall` 上线(§4.4)② Hybrid Search(补全文 BM25 + RRF)③ DEFINE ACCESS + PERMISSIONS(多用户)④ chapter.prose 向量化(章节级语义检索)⑤ 评估 Hermes memory 三层接入(文档05) | 主编上下文用图检索;DB 层身份隔离;章节级 RAG 可用 |

---

> **总判定**:scribe3 对两个组件都是"**选型对、用一半**"。Hermes 用对了最该用的(MCP+elicitation),但 cron/skill/网关三处运行时有缺口;SurrealDB 选了"图+向量+文档+实时"四能一体的库,却只兑现了向量——图边建了不遍历、关系降级成字符串、Event 结构落库即蒸发。**两者最高 ROI 的共同方向是"把图用起来":持久化事件关系 + Record Link 化引用 + Graph RAG 上下文注入**,这一条线同时修复限知持久化裂口(文档03 P03)、本体关系建模缺失(文档04 §3)、和上下文精准度,是贯穿全部诊断的总枢纽。
>
> 本分析基于只读扫描,未改任何代码、未打印任何 secret。需人工确认项:HNSW 实际召回质量(需跑数据)、`intent`/`work` SCHEMALESS 表运行时字段集、Hermes skill/delegate 的 runtime 实际触发、:8642 当前是否可服务。
