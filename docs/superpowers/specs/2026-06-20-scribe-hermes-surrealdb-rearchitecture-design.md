# Scribe 底座重构 · 设计 Spec(Hermes 为大脑 + SurrealDB 为数据层)

**日期**:2026-06-20
**性质**:架构级重构。把 Scribe 从"自造一切的单体"改成"**Hermes(agent 大脑)+ SurrealDB(关系+向量+图 一体的数据层)+ Scribe 领域/MCP 层 + Web UI**"四层。
**前置**:本 spec 取代/吸收先前的「后端数据增强」spec(关系/质量时序等改到 SurrealDB),与「前端产品级重构」spec 并行(UI 大体保留,数据与 AI 后端换底座)。

## 0. 一句话

> 让 Hermes 当真正的 agent 大脑(运行/记忆/技能/调度/模型),让 SurrealDB 当真正联动的数据底座(关系+向量+图+全文一句话查),Scribe 退成"小说领域逻辑 + 一套干净的 MCP 工具 + 编辑器/视图",二者经 MCP 连接。

**核心原则 · Clean Slate**:在新底座上**干净重写**,旧实现整体退役删除——**改造后不得残留任何 SQLite/sqlite-vec/orchestrator/proactive/直连火山/双轨逻辑**,杜绝遗留代码造成干扰。不做渐进绞杀、不先做 spike。

## 1. 现状根因(已查证)

1. **Hermes 几乎没用上**:网页主路径 `_volc_complete` **直连火山 doubao,绕过 Hermes**;`/chat` 走 Hermes 也只是裸补全。Hermes 的 runs/sessions/memory/skills/cron 全没用。
2. **本地复刻了一堆 Hermes 已有的东西**:`agent_memory`/`agent_skills` 表、`orchestrator.py` 状态机、`proactive_review` 后台 ticker、`llm.py` ledger —— 都是 Hermes 原生能力的劣质再造。
3. **数据是"死的"**:27 张表里只有 `segments`(正文)被向量化;设定/人物/伏笔/素材/记忆/关系等 11+ 张内容表**从不被语义召回**,数据躺着发霉;向量用手搓的 `sqlite-vec` + 三路 RRF。
4. **三套能力割裂**:关系(SQLite)、向量(sqlite-vec)、图(entity_relations 边表)各存各的,没有统一联动。

## 2. 目标架构

```
┌─ Web UI :3310 ─────────────────────────────────────────────────────────────┐
│  编辑器/版本/diff · 北极星 · 五视图 · 关系图/仪表盘 · 主编对话(run 驱动)      │
└───────────┬───────────────────────────────────────────────┬────────────────┘
            │ 领域读写(REST,瘦)                              │ 主编对话:/v1/runs + SSE + /approval
            ▼                                                 ▼
┌─ Scribe 领域/MCP 层 :3320 ────────────────┐       ┌─ Hermes :8642(大脑/底座)──────────────┐
│  · 小说领域逻辑(校验/工作流/diff/版本)    │       │  runs(异步 agent + SSE 事件 + 审批门)    │
│  · 一套干净 MCP 工具(读/写/检索,写=需审批)│◄─MCP─►│  sessions(有状态 + fork)               │
│  · 把 SurrealDB 能力封装成领域语义工具      │       │  memory(会话作用域) · skills(自创+审计) │
└───────────┬───────────────────────────────┘       │  cron(主动体检) · 模型路由 + 用量        │
            │ SurrealQL                              └────────────┬───────────────────────────┘
            ▼                                                     │ 也可直接挂 SurrealMCP(只读检索)
┌─ SurrealDB(数据底座 · 嵌入/本地进程)────────────────────────────┘
│  关系 + 文档 + 图(->relates->) + 向量 + 全文,ACID,一句 SurrealQL 联动        │
│  canonical 真相源:works/章/设定/人物/伏笔/版本… + 图边 + 每实体的 embedding   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**四层职责**
- **SurrealDB** = 唯一数据底座(关系结构 + 版本 + 图 + 向量 + 全文,ACID)。取代 SQLite + sqlite-vec + 手搓 RRF + 图边表割裂。
- **Scribe 领域/MCP 层** = 小说领域逻辑 + 一套 MCP 工具(把 SurrealDB 封成"建章/改设定/查知识/推伏笔"等领域语义),写操作标记需审批。
- **Hermes** = agent 大脑:runs/sessions/memory/skills/cron/模型路由。取代本地复刻件。
- **Web UI** = 编辑器/视图保留;主编对话改 run 驱动(看主编思考+工具调用+审批)。

## 3. 数据层 · SurrealDB(关系 + 向量 + 图 一体)

### 3.1 为什么 SurrealDB
- 一个引擎原生 文档/关系/图/向量/全文,**一句 SurrealQL 同时跑 图遍历 + 向量相似 + 标量过滤 + 时序**([多模](https://surrealdb.com/docs/what-is-surrealdb) · [AI context layer](https://surrealdb.com/use-cases/ai-agents))。
- **官方 MCP server(SurrealMCP)**:查询/遍历/向量检索/事务皆标准 MCP 工具 → Hermes 即插([SurrealMCP](https://surrealdb.com/mcp))。
- 嵌入/本地进程跑(单二进制 + Python SDK),契合 Scribe 本地架构([embedded](https://surrealdb.com/solutions/embedded-application))。
- ACID → 版本树/章序/精确查询有保障(纯向量库做不到)。

### 3.2 数据模型(SurrealQL schema)
- **结构/真相**:`work`、`volume`、`chapter`、`snapshot`(版本,带 `version`/`locked`)、`segment`、`setting`、`character`、`foreshadow`、`consistency_flag`、`author_intent`、`option_set`、`material`、`style_exemplar`、`imagination`、`feedback`、`preference_signal`、`taste_model`、`quality_snapshot`。结构/外键用 SurrealDB record links(`chapter.work` 指向 `work`)。
- **图**:实体间关系用 SurrealDB **graph edges**(`RELATE character:沈舟 -> holds -> item:断魂剑 SET valid_from=1, weight=2, category='从属'`),取代 `entity_relations` 表;时间线、角色状态轨迹同样用边或带时序字段的记录。`->?->` 遍历替代递归 CTE。
- **向量 + 全文**:每个内容实体加 `embedding`(向量索引 HNSW)+ 文本字段挂 **FTS 索引**。覆盖**全部内容**(正文/设定/人物/伏笔/素材/记忆/范本),不再只有正文。
- **派生/信号**:质量快照、偏好信号、品味模型作为时序记录,反哺检索与生成(不再死存)。

### 3.3 统一知识检索(联动回路,一句话)
核心检索 = 一条 SurrealQL:`对 query 做向量+全文混合 → 命中实体 → 沿图扩展关联 → 带回 canonical 详情`。封装成领域 MCP 工具 `search_knowledge(query, types?, k, upto?)`,主编写作/对话时自动汇聚全书相关知识。**这就是"让死数据活起来 + 真正联动"。**

### 3.4 嵌入与同步
- 嵌入提供方可插拔(本地 fastembed / 远程 embedding API);写入实体时在同一事务里算 + 存 embedding(或异步队列补)。
- `/reindex` 幂等:从 canonical 重建所有 embedding/FTS,坏了能重建。
- 嵌入/向量是 SurrealDB 内的派生字段(同库,无跨库同步问题)。

## 4. 大脑层 · Hermes(替代本地复刻)

| Scribe 现在本地造 | → Hermes 原生替代 | 接口 |
|---|---|---|
| `agent_memory` 表 | **Hermes memory**(`X-Hermes-Session-Key`=owner/书 作用域) | session headers |
| `agent_skills` 表 + 自造审批 | **Hermes skills**(自动创建/审计)+ **run approval** | skills hub / `/v1/runs/{id}/approval` |
| `orchestrator.py` 状态机 | **Hermes run 多步编排** + 工具调用 | `/v1/runs` |
| `proactive_review` 后台 ticker | **Hermes cron**(定时跑"体检"run) | cron/scheduler |
| `llm.py` 直连火山 + ledger | **Hermes 模型路由 + 用量** | 经 Hermes 调用;Scribe 只读展示 |
| `/chat` 裸补全 | **`/v1/runs` agentic + 工具 + 审批** | runs + SSE events |

**已查证 Hermes 暴露**:`POST /v1/runs`(异步,返回 run_id)、`GET /v1/runs/{id}/events`(SSE 生命周期/工具事件)、`POST /v1/runs/{id}/approval`(人审批)、`/stop`;`/api/sessions`(持久 + **fork**);`/v1/chat/completions` 与 `/v1/responses` 支持会话/记忆头。

## 5. MCP 工具层(领域工具 + 审批门)

- **扩充** `scribe_mcp/server.py`(现 28 工具)到覆盖全部领域动作:`read_*`(读)、`search_knowledge`/`traverse`(检索/图)、`create_chapter`/`save_prose`/`update_setting`/`advance_foreshadow`/`run_critique`/`set_intent` 等(写)。
- **写工具标记 `requires_approval`**:Hermes run 命中写工具 → 暂停 emit 审批事件 → 前端弹卡 → 用户批准 → 执行(最佳实践:[会改状态的工具默认要人审批](https://open-techstack.com/blog/how-to-use-openai-agents-sdk-with-mcp-and-approvals-2026/))。
- **一套干净的 MCP server**,不拆成多个([one clean MCP server](https://www.morphllm.com/ai-agent-framework))。可选:把 **SurrealMCP** 也挂给 Hermes 做只读高级检索,但**写一律走 Scribe 领域工具**(领域校验/工作流/审批集中一处)。

## 6. 主编 = 工具 agent(能力延展 + 审批)

主编对话改 **run 驱动**:发消息 → Scribe `/chat` 转 `POST Hermes /v1/runs`(挂 scribe MCP、session-key=书、system=主编人格)→ 前端订阅 SSE:流式显示主编思考 + 工具调用("要新建第10章"/"读了沈舟的关系")→ 写操作弹**审批卡**(复用现有"决策/差异矩阵"UI)→ 批准 → 工具执行 → 数据落 SurrealDB → 记忆/技能自动沉淀进 Hermes。
**延展能力**:跨会话记得偏好、从复杂任务自创技能(待批)、会话 fork(A/B 走向)、spawn 子 agent 并行(同时体检多章)。

## 7. 保留不动(领域身体,Hermes/SurrealDB 都替不了的)

编辑器(Tiptap)、版本树/diff、北极星、五视图、关系图/质量仪表盘(数据改从 SurrealDB 来)。**领域数据留在你自己的 SurrealDB 实例 = 不被 Hermes 锁定。**

## 8. 数据流示例

**写第 N 章**:用户「让主编写这章」→ run → 主编调 `search_knowledge`(SurrealQL 混合检索 + 图扩展,汇聚相关设定/旧正文/伏笔/记忆)→ 生成草稿(经 Hermes 模型路由)→ 调 `save_prose`(写工具)→ 弹审批 diff → 批准 → 落 SurrealDB(新 snapshot + 重嵌入)→ 触发一致性检查工具。

## 9. 策略:Clean Rebuild(干净重写,零遗留)

**不做绞杀式渐进、不先做 spike**。在新底座上**重写后端**,旧实现**整体退役删除**,不与新系统并存,避免遗留代码/逻辑造成干扰。

### 9.1 新建(clean)
- **新后端包** `scribe/`(新 `app/` 或新包名),从零基于 **SurrealDB + Hermes** 写:领域模型(SurrealQL schema)、领域服务、一套干净 MCP 工具、Hermes run 集成、领域 REST(供前端)。
- 老 Python 包 `scribe_mcp/`(SQLite/vec/orchestrator/proactive/llm/server 旧版)与 `schema.sql`、旧 `tests/` **整体删除**(原仓内重建,旧代码靠 git 历史可查,不留 `legacy/`、不留双轨)。
- **数据(已定)**:**全新干净 SurrealDB 库,不迁**。现有 SQLite 作品与那堆测试/重复书一并弃用,不写迁移脚本。

### 9.2 保留(已是干净产物)
- **前端**(刚重建的 shadcn 五视图/编辑器):保留,但**清掉自身遗留**——删 `index.css` 残留旧类、未用的 `Library.tsx`、半迁移的 `Panels.tsx` 等,统一到 shadcn。
- 领域**概念/提示词/业务价值**(每个功能要做什么)沿用,代码重写。

### 9.3 退役清单(改造后不得残留)
`scribe_mcp/db.py`(SQLite)、`vec.py`(sqlite-vec)、`retrieval.py`(手搓 RRF)、`orchestrator.py`、`metrics.py` 旧版、`llm.py`(直连火山 + ledger)、`agent_memory`/`agent_skills` 表与相关端点、`proactive_review` 后台 ticker、`server.py` 旧 MCP(由新 MCP 工具取代)、`schema.sql`、`scribe.db`、旧 `tests/`。**一律删除(git 历史可查),不留 dead code、不留双轨、不留 `legacy/`。**

### 9.4 构建顺序(降风险靠"先建地基",非靠 spike 门)
1. SurrealDB 数据层 + 领域模型 + `search_knowledge`(最不确定,先建)
2. 一套干净 MCP 工具(读/写/检索,写=需审批)
3. Hermes run 集成 + 主编对话 run 驱动 + 审批 UI
4. 记忆/技能/cron 全部走 Hermes
5. 生成全经 Hermes;前端清遗留 + 接新 REST
> 不确定点(Hermes runs schema、SurrealDB 嵌入)在第 1/3 步**边建边证**,不单设 spike 阶段。出问题就地解决,不回退到旧底座。

## 10. 最佳实践对照(全网)
- MCP 作 AI 原生适配层包装领域能力([MCP vs API](https://atlan.com/know/when-to-use-mcp-vs-api/));一个干净 MCP server。
- 有状态会话用 Responses/sessions,Assistants 已弃([OpenAI 生态](https://www.speakeasy.com/mcp/openai-ecosystem))。
- 改状态工具默认人审批,read→analyze→prepare→pause→approve([approvals](https://open-techstack.com/blog/how-to-use-openai-agents-sdk-with-mcp-and-approvals-2026/))。
- 多模一体库做 AI context layer([SurrealDB AI agents](https://surrealdb.com/use-cases/ai-agents))。

## 11. 风险与缓解
- **工作量极大且无回退底座**(clean rebuild,双底座一次性替换):用户明确接受"不先验证、彻底重构"。缓解 = **构建顺序先建最不确定的地基**(SurrealDB 数据层、Hermes run 集成)边建边证;新系统跑通前不删可参考的旧代码(归档到 `legacy/`,跑通后清除)。
- **Hermes `/v1/runs` 工具/审批 schema 不确定**:第 3 步集成时就地实测对齐(已知它暴露 runs/events/approval)。
- **SurrealDB 嵌入/Python/SurrealMCP 成熟度**:第 1 步建数据层时验证;若嵌入 Python 不顺,退化为"SurrealDB 本地进程(`surreal start`)+ HTTP/SDK",仍属 clean(无旧底座残留)。
- **SurrealQL 学习成本**:领域逻辑集中在新 db/服务层,封装后上层无感。
- **外部依赖(Hermes/SurrealDB)**:领域数据在自有 SurrealDB 实例;Hermes 只做大脑,数据可移植。
- **开发期数据**:默认全新干净库;需保留现有作品则一次性迁移脚本,迁完即弃。

## 12. 非目标(YAGNI)
- 不引第二个图/向量库(SurrealDB 一把全要)。
- 不做多人协作/云同步(单用户本地)。
- 不在本轮重做编辑器/五视图(它们读 SurrealDB 即可)。
- 不强求紧凿逐字生成也走完整 run(可保留经 Hermes 的 session 补全)。

## 13. 开放问题(P0 spike 解决)
1. Hermes `/v1/runs` 能否每请求挂指定 MCP server + 拿到结构化工具/审批事件?
2. SurrealDB 嵌入式 Python 写作工作负载下的版本/事务表现?SurrealMCP 对本地实例?
3. 嵌入提供方(本地 fastembed vs 远程)在 SurrealDB 向量索引下的延迟/质量?
