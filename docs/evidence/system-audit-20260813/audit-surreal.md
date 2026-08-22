# 图/文档库架构审计 · Surreal 正典·时间·图·检索·一书一库

- 仓库：`/home/admin/projects/scribe-writing-system`
- 产品：`scribe3/`
- 角色：图/文档库架构师（只读；不改代码、不 push、不起第二套库）
- 北极星：写出前后一致的好小说，不是把 Surreal 功能清单勾满
- 入口：`docs/CURRENT_ARCHITECTURE.md` §3–5；方案：`docs/plans/2026-08-08-surrealdb-3.2.4-optimization-plan.md`
- 抽查：`scribe3/store/{connection,chapters,events,recall}.py`、`live.py`、`migrations/`、`ingest_policy.py`、`context_assembler.py`、`feature_flags.py` / `surreal_flags.py`、`graph_recall` / `hybrid_recall` / 向量 / FTS / LIVE
- **已知已证实、本文不刷篇幅**：`narrative_contract` 列已落库；assemble **未**注入合同。
- **明确否决**：再起一套库；把正典迁出 Surreal（Spectron / Hermes memory / 第二真相库）。

图例：每条写清 **没用上** vs **不该用硬用了**。

---

### F-S01 一书一 `db` 被平台 SQLite / `_reg` / Hermes 切成多面，正典面仍在书库

- 角度：Surreal
- 严重度：P2
- 现状：架构铁律是「一书一 `db=<work slug>`，NS=`scribe3`，Surreal = 世界正典唯一真相源」。实现上还有平行面：
  - 用户/会话：`scribe3/auth/users.py` → `SCRIBE3_AUTH_DB`（默认 `~/.scribe2-surreal/scribe3_auth.sqlite3`）
  - 产品旗标/检索权重：`settings_store.py` → `SCRIBE3_SETTINGS_DB`
  - LLM 日帽：`usage.py` → `SCRIBE3_LLM_LEDGER`
  - 作品注册表：独立 Surreal DB `_reg`（`store/core_preamble.py` `DEFINE TABLE work SCHEMALESS`），`owner_user_id` 在此，不在书库
  - Hermes：`store=True` + `previous_response_id` / 网关 `state.db`（`tools/backfill_editorial_chat.py` 证明对话曾只活在 Hermes）
  - 配置文件：`gateway_files.py` 读写 `~/.hermes/profiles/{scribe3,scribe3_write}/`
  - 正文/命题/事件/知识边/素材/过程记忆：在书库（`004_manuscript` `chapter.prose`、`001` 本体、`078` `memory_item`）
- 不合理：把「一书一库」理解成「整台产品只有一个文件」会误判。真正的多真相风险不在 auth 台账，而在：(1) 书级行为开关不随书走；(2) Hermes 会话若被当剧情回忆；(3) `_reg` 与书库对同一 slug 的元数据可能漂移。
- 更合理：
  - **不该用硬用了**：不要把 auth / 会话 / 全站日帽硬塞进书库（L1 规格就是单 Surreal 进程 + 逻辑隔离，用户表不属于故事本体）。
  - **没用上**：书级「写作/检索合同」（hybrid 开关、memory 权重、ingest 策略快照）没有作为书库一等对象随书备份/导出。
- 不改的代价：换机/导出一本书时，正典在 Surreal、作者能否登录在 SQLite、检索权重在另一份 SQLite、对话尾巴可能在 Hermes `state.db`。故事正文不会丢，但「这本书当时怎么被检索/反哺」不可复现。
- 证据：`docs/CURRENT_ARCHITECTURE.md` §3；`store/connection.py` `db_name=work`；`auth/users.py` `_db_path`；`settings_store.py`；`usage.py`；`store/core_preamble.py` `_reg_conn` / `list_works`；`hermes_runtime.py` `store`/`previous_response_id`；`tools/backfill_editorial_chat.py`。

---

### F-S02 该在书库的是「书级检索与时间门策略」，不是用户表

- 角度：Surreal
- 严重度：P2
- 现状：`memory.weight_*` / `half_life_*`、`SCRIBE3_HYBRID_SEARCH_NATIVE`、`SCRIBE3_INGEST_POLICY` 走设置中心 SQLite（`settings.py` + `settings_store`）。ingest hold 已部分落在 `chapter`（`ingest_policy.py` 读写 `ingest_hold_*`）。
- 不合理：同一套权重作用于所有书。武侠密谋书与群像限知书共用 RRF/半衰期，等于没有「一书一检索合同」。
- 更合理：平台旗标留 SQLite；**书级**召回权重、时间门默认、ingest 策略版本写入该书 `db`（SCHEMAFULL 小表或 `work_policy` 记录）。**不要**把用户密码迁进 Surreal。
- 不改的代价：A 书调参污染 B 书；备份书库无法复现当时写作召回面。
- 证据：`scribe3/settings.py` `SCRIBE3_HYBRID_SEARCH_NATIVE` / `SCRIBE3_CHANGEFEED_CACHE`；`memory_retrieval.py` `channel_weights()` / `half_life_days()`；`ingest_policy.py` `policy_mode()`。

---

### F-S03 图写路径：MCP `add_event` 是真写；长篇主路径仍是 ingest 事后补，且常缺 `effects`

- 角度：Surreal
- 严重度：P1
- 现状：
  - `store/events.py` `add_event`：事务内写 `event` + `involves` + `causes` + `causal`；**有 `effects` 才** `see_event` → `knows(acquired_via=saw)`。同槽多人 `iter_participants` 支持 `WITNESS: list`。
  - MCP `s3_add_event`（`mcp/tools_write.py`）走同一函数，是正典写门（待批）。
  - 定稿主路径是存稿 → ingest：`did` 会合成事件并挂 `effects`，因而会发 `knows`；`delta.events` 抽取（`ingest.py` ~456–514）**通常不传 `effects`**，只落类型/参与者/因果，**不触发看见即知道**。
  - `add_event` 失败时 `did` 回退手写 `knows`（图边与知识边分叉）。
- 不合理：架构文写「生产：`add_event` 带 effects 时自动 see_event」。产品上大部分事件来自抽正文，不是主编当场 `s3_add_event`。图的「谁在场看见了什么」对抽取事件经常是空的。
- 更合理：
  - **该用**：写时（大纲/节拍/主编工具）就落带 `participants`+`effects` 的事件，而不是等 ingest 猜。
  - **没用上**：抽取 `events` 未强制 effects / 目击者，时间门图是半空的。
  - **不该用硬用了**：不要为「图好看」在 ingest 里用启发式给每个器物/地点造 WITNESS（代码已刻意不把非人物登记成角色）。
- 不改的代价：限知帧只靠 `learned`/`did` 的直写边；多目击者、戏剧反讽、`graph_recall` 的 `source_events`/`co_present` 在真书上稀疏。下一章「谁不该知道」只能靠 dump 命题，不能靠图。
- 证据：`store/events.py:8-54`；`knowledge.py` `see_event` / `iter_participants`；`ingest.py:299-321` vs `505-508`（后者无 `effects=`）；`mcp/tools_write.py` `s3_add_event`。

---

### F-S04 图读（knows 时间门 / 因果链 / 多跳）未进写作 assemble，只 MCP/面板/探针

- 角度：Surreal
- 严重度：P0
- 现状：
  - `graph_recall`：HNSW 种子 + `<-knows` / `<-causes<-event`；`knowers` 用 Python 按 `since/until` 再滤（SQL FETCH 无时间门）。
  - `causal_chain`：`->causal(..depth)->event` 递归，失败退 1 跳。
  - `fn::knowledge_frame`（122）+ `project_frame`：**已**进 assemble 限知裁剪。
  - `graph()`（`store/structure.py`）尊重 `until_chapter`。
  - `SCRIBE3_MULTI_HOP_GRAPH` 默认开，但 `event_graph.py` 是 **Python 邻接表**，不是 Surreal 多跳；消费面是 `novel_first_surface` / HTTP，**assemble / `write_assemble*` 零引用** `graph_recall` / `causal_chain` / `hybrid_recall`。
  - assemble 正典：`facts_at(chapter)[:40]` + `open_promises()[:8]` + `events_at(ch-1)[:6]`（`context_assembler.py` `_canonical_from_store`）。有 MemoryRetriever 时 structured 通道仍是 **全表时间门 dump**，不是查询相关图。
- 不合理：图为一致性准备的能力（谁知道、谁在场、因果链）在写下一句时用不上。模型若碰巧调 `s3_graph_recall` 才看得到；`run_stage_policy` 的 deduce/plan **甚至不保证**这些工具在写阶段强制调用。
- 更合理：assemble 的 canonical/focus 用「本章 query + 时间门 graph 子图」替代无序 dump。限知继续走 `project_frame`（已接，保持）。**不要**把全图塞进 prompt。
- 不改的代价：前后不一致（已忘的仇、不在场的目击、断因果）靠事后 QC，不靠物理上下文。书越长，`[:40]` 越稀释关键事实。
- 证据：`store/recall.py` `graph_recall` / `causal_chain` / `list_knowers_for_proposition`；`context_assembler.py:843-871`；对 `scribe3/api/services` 搜 `hybrid_recall|graph_recall` **无命中**；`mcp/tools_recall.py`；`run_tool_filter.py` 仅白名单。

---

### F-S05 正典 FTS+向量+混合是旁路；写路径混的是 `memory_item`，不是命题库

- 角度：Surreal
- 严重度：P0
- 现状：
  - 命题：`003` HNSW、`119` `tokens` + FULLTEXT BM25；`semantic_index` 写 embedding+tokens；`hybrid_recall` 单程 SurQL + `search::rrf`（`SCRIBE3_HYBRID_SEARCH_NATIVE` 默认开），失败 Python RRF；时间门 **后过滤**（避开 KNN×WHERE）。
  - 素材：`070` 三通道 `material_recall` → 写作闸 `_material_recall_block`（参考非事实，已接）。
  - 过程记忆：`078` FTS+HNSW；`MemoryRetriever` 四通道 = `facts_at` dump + `memory_bm25` + `memory_vector` + `memory_relation` 一跳。**不是** `hybrid_recall(proposition)`。
  - 写路径：`write_stream._get_write_retriever` 挂 `MemoryRetriever`；query 用种子词/作者话/synopsis。
- 不合理：3.2.4 上已校准的「命题混合检索」只服务 MCP / `probe_s32_hotpath` / `surreal_engineering_smoke`。写作 envelope 的「正典」是时间门全量切片，与本章要写什么无关。
- 更合理：
  - **该用未用**：`hybrid_recall(query, chapter)` 进 canonical 块（再经 `project_frame` 裁）。
  - **不该用硬用了**：不要把 `memory_item` 的 BM25/向量结果标成 canonical（当前 kind 分离是对的）。
- 不改的代价：相关旧设定召不回、无关旧设定占满 40 条；混合检索绿探针 ≠ 小说更一致。
- 证据：`store/recall.py:50-241`；`memory_retrieval.py:1-14,328-393`；`api/services/write_stream.py:410-447`；`context_assembler.py` 无 `hybrid_recall`。

---

### F-S06 SCHEMAFULL 核心表在，叙事合同/节拍/驱动是 `option<string>` JSON 袋；RECORD 链接半死

- 角度：Surreal
- 严重度：P2
- 现状：
  - 真 SCHEMAFULL：`character` / `proposition` / `event` / `knows` / `involves` / `causes` / `causal` / `memory_item`（001/013/019/078）。
  - JSON 袋：`134_narrative_contract.surql` `chapter.narrative_contract option<string>`；同型 `118 narrative_drive`、`117 beats_meta`、`114 pressure_drive`（注释写明绕嵌套 object）。
  - 半迁移：`014` `entity_id` 与 `001` `entity` 并存；`026 entity_link option<record<character|place>>` 文档自承 **死字段**，`graph_recall` 读 `entity_id` 字符串。
  - SCHEMALESS 袋：`_reg.work`、`ingest_lease`、`chapter_reader_ack`、`cache_watch`。
- 不合理：合同/节拍本应可查询「本章欲望/障碍/代价」，却不能 `WHERE narrative_contract.desire CONTAINS …`，也不能用 TYPE 挡住缺字段。这是 schema 问题，不是「列没建」（列已在）。
- 更合理：合同四元组升成可查询字段或 `FLEXIBLE object` + ASSERT；`entity_link` 要么补写路径当 RECORD 完整性，要么 REMOVE。**不要**一次全库 SCHEMAFULL。
- 不改的代价：一致性检查只能在 Python `json.loads`；脏 JSON 静默；图无法 `RELATE` 到合同对象。
- 证据：`migrations/001_ontology.surql`；`013_event_graph.surql`；`026_record_links.surql` 头注释；`040_naming_collapse.surql`；`118`/`134`。

---

### F-S07 LIVE/changefeed：前端有 SSE，但仍大量轮询；CDC 只打缓存不打写路径

- 角度：Surreal
- 严重度：P2
- 现状：
  - `live.py`：后端 `c.live(table)` → SSE；`SCRIBE3_LIVE_GRANULAR` 带 action+id；`LIVE SELECT WHERE` **DEFERRED**，用输出侧 `live_id_allowed`。
  - 前端：`BinderLayout` 单路 `api.live` 广播 `s3-live`；Brief/Version/Deduce/Pulse 等按表刷新。
  - 仍轮询：`studioDocks.jsx` Pilot 3.5s；`CodexDirectory` 收件箱债 8s；`WorkflowCapsule` 12s **叠加** live；`QualityReview` 1s。
  - Changefeed：表建时 `CHANGEFEED 1h`；`ChangefeedCacheWorker` `SHOW CHANGES` → `context_cache` 失效。**不**驱动写作/ingest。
- 不合理：LIVE 配额有限（`_LIVE_MAX`，默认 5，超则 429）。轮询与 SSE 双烧。原生条件 LIVE 没用上。
- 更合理：热面板只信 `s3-live`；轮询仅作断线兜底。CDC 继续只做缓存（**不要**用 changefeed 自动改正典）。
- 不改的代价：多标签页打满 LIVE；树/债面板 stale 或空转；与「写出好小说」弱相关，但是书库实时面的诚实度问题。
- 证据：`live.py:34-41,113-114`；`web/src/BinderLayout.jsx:79-90`；`web/src/studioDocks.jsx:407`；`web/src/layout/CodexDirectory.jsx:105`；`changefeed_consumer.py`；`migrations/120`/`125`。

---

### F-S08 `memory_fabric` vs 正典：边界写在纸上，压制缺键时过程记忆会进写作 recent

- 角度：Surreal
- 严重度：P1
- 现状：
  - 宪法：`memory_item` 只存经验五类；正典不复制进 fabric；高风险断言进 `pending_authority_claim`（`memory_capture.py`）。
  - 产品默认 `SCRIBE3_MEMORY_FABRIC_V1` 开；写路径 capture + retrieve 对称。
  - 正典压制依赖候选 `provenance` 的 `(entity, attribute)`。捕获模块**诚实声明**：生产 episodic **不**写精确 attribute（怕误压制），故 `unconflictable_count` 仍 >0。
  - assembler：episodic/working → **recent** 块（「近期事件/决策」文案），与章尾 prose 并列进写作 prompt。
- 不合理：没有冲突键就无法「正典盖过经验」。对话里的猜测/摘要会以「近期」身份出现在写路径，读者/角色可能当成已发生剧情。
- 更合理：
  - **该用**：pending → 审批 → `add_fact`（已有 `/memory/pending-claims`）。
  - **没用上**：无键 episodic 应降级 reference/uncertainty 或不进 write envelope。
  - **不该用硬用了**：不要为了压制率用启发式硬凑 attribute（捕获注释已否决，保持）。
- 不改的代价：过程记忆冒充剧情；限知门只挡 `known_from`，挡不住「口吻像事实的经验句」。
- 证据：`memory_capture.py:29-45,7-15`；`memory_retrieval.py:116-135`；`context_assembler.py:11-21,408-441`；`CURRENT_ARCHITECTURE.md` §5b。

---

### F-S09 3.2.4 对「前后一致」杠杆最大却没接到写路径（1/3）：命题 `hybrid_recall`（HNSW+FTS+`search::rrf`+章门）

- 角度：Surreal
- 严重度：P0
- 现状：引擎能力已落地且有探针；写作 assemble **不用**它选正典（见 F-S05）。
- 不合理：长篇一致性的核心是「此刻相关的、此时已成立的事实」，不是「时间门内任意 40 条」。
- 更合理：写路径 query（种子词/节拍/障碍）→ `hybrid_recall` → 限知裁剪 → canonical。素材混合可继续仅作参考。
- 不改的代价：3.2.4 检索升级只惠及主编手查与工程冒烟。
- 证据：`119_hybrid_search_config.surql`；`store/recall.py` `_hybrid_recall_native`；`surreal_flags.hybrid_search_native`；assemble 无调用。

---

### F-S10 3.2.4 杠杆（2/3）：时间门图 RAG + 原生递归因果（`graph_recall` / `causal_chain`），不是 Python 邻接表

- 角度：Surreal
- 严重度：P0
- 现状：`knows.since/until`、`involves` 多目击者、`causal` 递归语法、`fn::knowledge_frame` 均在库侧。后三者除 knowledge_frame 外不进 assemble。`MULTI_HOP_GRAPH` 走内存图，HTTP 表面。
- 不合理：好小说的「不该知道 / 因果必还」是图查询，却在写时退化成 6 条近事件字符串。
- 更合理：本章焦点事件为种子，注入：知情者集合、同场角色、向前/向后 2–3 跳因果。继续用章门后过滤。
- 不改的代价：断链、目击穿帮、仇怨遗忘只能事后扫。
- 证据：`store/recall.py:243-307,435-485`；`migrations/122_knowledge_frame_fn.surql`；`event_graph.py`；`novel_first_surface.py`。

---

### F-S11 3.2.4 杠杆（3/3）：章级 HNSW（`016`）与 RECORD 完整性未服务「回忆/回指」

- 角度：Surreal
- 严重度：P1
- 现状：`save_chapter` 尽力写 `chapter.embedding`；`chapter_recall` 仅 MCP。`entity_link` RECORD 未成为写真相。双时态是自建 `int` 章号，不是 Surreal `TIME`/`VALID` 类型（可接受），但查询未组合「故事时 × 叙事时」（`narrative_position` 已有字段，assemble 不用）。
- 不合理：回指前章意象/伏笔应走章向量+时间门，而不是靠 recent 截断或 Hermes 会话。
- 更合理：续写/回指用 `chapter_recall`（排除未来章）进 recent/canonical 辅块；写命题时填 `entity_link` 防悬空主体。
- 不改的代价：跨章呼应靠模型记性；改名/删角色后命题字符串仍指向幽灵。
- 证据：`migrations/016_chapter_vector.surql`；`store/chapters.py` `chapter_recall` / save embedding fail-soft；`026_record_links.surql`；`mcp/tools_write.py` `narrative_position` 注释。

---

## 七问逐条答

### 1. 一书一 db 是否被 SQLite（auth/ledger/settings）、文件、Hermes `state.db` 拆成多真相？哪些该在 Surreal 却不在？

**部分拆了，但正典面没有被迁走。**

| 面 | 存哪 | 是否多真相 | 该不该进书库 |
|----|------|------------|--------------|
| 命题/事件/knows/章正文/素材 | 书库 Surreal | 否，这是正典 | 已在 |
| 过程记忆 `memory_item` | 同书库，别表 | 设计分离 | 应在同库、不得替代正典 |
| 作品目录/归属 | `_reg` SCHEMALESS | 元数据第二库 | 可留 `_reg`，不要再引入第三注册表 |
| 用户/会话 | SQLite auth | 平台身份 | **不该**进书库 |
| 全站设置/日帽 | SQLite | 运维面 | 全站可留；**书级检索/ingest 策略该在书库（F-S02）** |
| Hermes `state.db` / `store=True` | 网关过程 | 对话曾丢过，靠回填脚本 | 剧情不得以 Hermes 为准；`chat_message` 才是产品对话正本 |
| Hermes 配置文件 | 磁盘白名单 | 人格/密钥 | **不该**当故事库 |

**没用上**：书级策略随书走。  
**不该用硬用了**：把 auth/ledger 并进 Surreal，或再起一套剧情库。

### 2. 图（knows / see_event / 时间门 / 多目击者）写路径是否真用，还是只 ingest 事后补？

**两条写路径都存在，长篇主路径是 ingest 事后补，且补得不全。**

- **真用**：`s3_add_event` / `store.add_event` 在带 `effects` 时自动 `see_event`；`did` 抽取走这条。
- **事后补**：定稿 ingest 的 `events` 列表常无 `effects` → 无目击者边。
- **读侧时间门真用**：`project_frame` / `fn::knowledge_frame` / `knowers_at_chapter` / `graph()`。
- **写下一章时图没用上**：assemble 不读 `graph_recall`。

### 3. FTS+向量+混合是否进写作 assemble，还是只旁路？

**正典混合 = 旁路。过程记忆混合 = 已进 assemble。素材混合 = 写作闸参考段。**

- 进写作：`MemoryRetriever`（`memory_item` FTS+向量+联想边）+ `facts_at` dump + `material_recall`。
- 不进写作：`hybrid_recall` / `semantic_recall` / `graph_recall` / `chapter_recall`（MCP、探针、演绎白名单）。

### 4. SCHEMAFULL/迁移：`narrative_contract` 等是否一等字段？有没有该 DEFINE 却塞进无 schema 袋？

- 本体核心表是 SCHEMAFULL + RELATE，合格。
- `narrative_contract`：**有列**，但是 `option<string>` JSON 袋，不是可查询的 desire/obstacle/turn/cost 字段（assemble 不注入属已知事实，此处只判 schema 等级）。
- 同类袋：`narrative_drive` / `beats_meta` / `pressure_drive`。
- 该 DEFINE 却半死：`entity_link` RECORD。
- 故意 SCHEMALESS：`_reg.work`、lease/ack/cache_watch（工程表，可接受）。

### 5. LIVE/changefeed 前端用了还是轮询？

**LIVE 用了，不是纯轮询；也不是纯推送。**

- 主壳一条 `/live` SSE，面板订阅 `s3-live`。
- Pilot/Codex 债/部分质量页仍 `setInterval`。
- Changefeed 给缓存失效，不给 UI、不给写路径。
- 原生 `LIVE SELECT … WHERE` 未用（输出侧过滤）。

### 6. `memory_fabric` vs 正典有没有过程记忆冒充剧情？

**有风险，机制未关死。**

- 设计：canonical 不进 `memory_item`；冲突 episodic 应 omitted。
- 缺口：生产捕获不写 `(entity,attribute)` → 压制经常空转 → episodic 进 **recent**，文案像「近期事件」。
- 高风险句进 pending 是对的；低风险口吻像事实的句子会漏。
- **不该用硬用了**：把 fabric 当第二正典，或为压制率乱填 attribute。

### 7. 3.2.4 里对「前后一致的好小说」帮助最大却没接到写路径的 3 个能力？

1. **命题 `hybrid_recall`**（HNSW + tokens BM25 + `search::rrf` + `valid_from/to` 章门）— F-S09  
2. **时间门图 RAG + 递归 `causal`**（`graph_recall` / `causal_chain` / 多目击者）— F-S10  
3. **章 HNSW 回指 + RECORD 主体完整性**（`chapter_recall` / `entity_link`）— F-S11  

已接到、应保持：`project_frame`/`fn::knowledge_frame`、一书一 db、ingest+`see_event` 事务、素材三通道（参考非事实）、fabric 与正典分表。

**否决重申**：不要为上述三项再起平行 Surreal/SQLite 剧情库；不要把正典迁去 Hermes memory。缺的是 **接到 `/chat/write` assemble**，不是新底座。

---

## 分类汇总

| 类别 | 条目 |
|------|------|
| 该用未用（对一致性有杠杆） | F-S04 图读、F-S05/F-S09 正典混合检索、F-S10 因果/目击者、F-S11 章向量/RECORD、F-S02 书级策略 |
| 不该用硬用了 / 误用风险 | F-S08 无键 episodic 进 recent；把 auth/Hermes 当剧情源；ingest 给非人物造目击者 |
| 半接（工程面，弱于北极星） | F-S07 LIVE+轮询；changefeed 仅缓存；`MULTI_HOP` 内存图 |
| 保持 | 一书一 db；正典在 Surreal；限知投影；fabric 分表；禁止第二真相库 |
