# scribe3 改造计划 · 以 Hermes + SurrealDB 为内核

> 详细改造计划 + 新旧版本隔离。落地《故事本体 v2》《写作台 v2》。
> 2026-06-22 · 依据 2 路源码级/文档级能力调研(Hermes hermes-agent 源码 + SurrealDB 3.x 官方文档,逐条带证)

---

## 0. 版本核实结论(实测,先做完才规划)

| 底座 | 装的版本 | 最新 | 结论 |
|---|---|---|---|
| **SurrealDB** | 3.1.5(:8001 运行中) | 3.1.x(3.1.0 于 2026-05 发) | **已是最前沿,无需升级**。surrealdb-py 2.0.0 正确匹配(需 Python≥3.10) |
| **Hermes Agent** | 0.17.0(:8642 运行中) | 落后上游 **267 commits** | **不宜盲目 `hermes update`**(见 §7.2):依赖全固定、provider 架构迁移、elicitation 依赖 mcp SDK≥1.11——会动到主编依赖的三个契约。先 pin + 隔离验证 + 备份再升 |

SurrealDB 3.x 官方定位 **"AI agent memory 底座"**,查询引擎重写后图查询快 8–22×——与"故事本体"诉求天然契合,选型被背书。

---

## 1. 内核定位纠偏(关键:纠正纵切片的偏差)

| 底座 | 正确职责 | 我纵切片里的偏差 → 本计划纠正 |
|---|---|---|
| **SurrealDB** | **持久层 + 知识层底座(唯一事实源)**:实体/事件/事实/知识边/三帧全落库;图遍历/向量/LIVE/CHANGEFEED | 切片用内存 dataclass `World` → **迁到 SurrealDB**(World 退为薄封装 Domain) |
| **Hermes** | **agent 平台底座**:主编 agentic(Responses)、工具(MCP)、技能(skill)、写待批(elicitation)、体检(cron)、分章并行(kanban)、模型路由 | 切片把 Hermes 仅当 LLM 网关 → **升为平台**:渲染/QC/写库全走 MCP 工具 + skill,写经 elicitation |

**三条不变量(全系统纪律,详见配套《开发标准》):**
1. **SurrealDB = 唯一真相**;世界状态只能经写门控 MCP 工具改(execute 单一落库点)。
2. **Hermes = 编排/计算/批准**;主编不直接碰库,只调 MCP 工具。
3. **渲染层只读**:渲染 = `fabula ∩ 知识帧` 投影,绝不回写世界。

---

## 2. 现状:scribe2 已对接 Hermes(重构是"深化"非"从零")

调研实测 `~/.hermes/config.yaml`:
- `mcp_servers.scribe2` 已挂(`scribe/.venv/bin/python -m scribe2.mcp`,`SURREAL_URL=ws://127.0.0.1:8001/rpc`)。
- `skills.external_dirs` 已挂 `scribe2/hermes_skills` + `写作/hermes-novel/skills`。
- 主模型 = 火山 doubao-seed-2.0-pro;无 fallback_model(风险);web 后端未配。

→ scribe2 当前 = **NS=`scribe` / DB=`main`**,MCP FastMCP 名 `scribe`(挂为 server_label `scribe2`),前端 3310 / 后端 3320。**这些是隔离的基准线(§6 全部错开)。**

---

## 3. 目标架构(Hermes + SurrealDB 为内核)

```
┌─────────────────────────── 前端 写作台 v2(端口 3311) ───────────────────────────┐
│  结构面/散文面/校验面;多视图(表/图/时间线)经 SurrealDB LIVE 订阅,改一处处处同步      │
└───────────┬───────────────────────────────────────────────┬───────────────────────┘
            │ 生成(SSE)                                      │ LIVE SELECT(WS 订阅)
            ▼                                                 ▼
┌─── Hermes :8642(agent 平台底座)───┐            ┌──── SurrealDB :8001(真相底座)────┐
│ /v1/responses 主编 agentic         │  MCP 工具   │ NS=scribe3 / DB=main             │
│   工具面来自 config(不是请求体!)   │ ──读/写──▶ │ 节点:character/event/proposition │
│ scribe3 MCP server(读工具放行/     │            │ 边:knows/causal/participates     │
│   写工具发 elicitation 待批)        │ ◀──数据──  │ 向量索引(HNSW)/全文(BM25)      │
│ scribe-novel-v2 skill(渐进披露)    │            │ DEFINE EVENT 触发器(写事件→边)  │
│ cron 体检 / kanban 分章并行         │            │ CHANGEFEED 审计 / 物化视图        │
│ 渲染走 completion(fabula∩帧→sjuzhet)│            └──────────────────────────────────┘
└────────────────────────────────────┘
```

**主编一次写章的数据流(全程不绕开两底座):**
1. 前端 POST `:8642/v1/responses`(`Authorization`+`X-Hermes-Session-Key`+`stream`+`instructions`=主编人格)。
2. 主编(skill 指引)调 scribe3 MCP **读工具**查世界:`get_author_intent`/`project_frame`(本场 focalizer 知识帧)/`list_foreshadows_status`。
3. 渲染:`render_scene`(工具内 `build_render_prompt` = fabula∩帧 → Hermes completion → sjuzhet)。
4. QC:`discipline_check`/`find_leaks`/`causal_complete`(只读判官,兜底)。
5. 落库:`ingest_chapter`/`record_knowledge`(**写工具 → 发 `elicitation/create` → 用户批准 → execute 单点落 SurrealDB**)。
6. 前端多视图经 LIVE SELECT 自动刷新(无需轮询)。

---

## 4. 本体 v2 → SurrealDB schema(可直接落库)

核心表 **SCHEMAFULL**(强约束防 LLM 写脏);可变元数据用 `FLEXIBLE TYPE object`。**双时态自建字段**(SurrealDB 原生 bitemporal 仅路线图,§7.3)。

```surrealql
-- ===== 持续体节点 =====
DEFINE TABLE character SCHEMAFULL;
DEFINE FIELD name      ON character TYPE string ASSERT string::len($value) > 0;
DEFINE FIELD aliases   ON character TYPE array<string> DEFAULT [];
DEFINE FIELD backstory ON character TYPE option<string>;     -- 冰山·私密前史
DEFINE FIELD metadata  ON character FLEXIBLE TYPE object;
DEFINE FIELD embedding ON character TYPE option<array<float>>;
DEFINE FIELD created   ON character TYPE datetime VALUE time::now() READONLY;
-- location / item / faction 同构

-- ===== 命题/事实(知识帧载体)=====
DEFINE TABLE proposition SCHEMAFULL;
DEFINE FIELD text        ON proposition TYPE string;
DEFINE FIELD secret      ON proposition TYPE bool DEFAULT false;       -- 私密(泄露=穿帮)
DEFINE FIELD leak_markers ON proposition TYPE array<string> DEFAULT [];
-- valid_time:故事内章(自建,稳)
DEFINE FIELD valid_from_chapter ON proposition TYPE int;
DEFINE FIELD valid_to_chapter   ON proposition TYPE option<int>;       -- null=惯性持续
DEFINE FIELD embedding   ON proposition TYPE option<array<float>>;

-- ===== 发生体节点(事件本体)=====
DEFINE TABLE event SCHEMAFULL;
DEFINE FIELD summary            ON event TYPE string;
DEFINE FIELD valid_from_chapter ON event TYPE int;
DEFINE FIELD motivated_by_goal  ON event TYPE option<string>;          -- IPOCL 硬约束
DEFINE FIELD draft_version      ON event TYPE int DEFAULT 1;           -- transaction_time(自建)
DEFINE FIELD tx_at              ON event TYPE datetime VALUE time::now();

-- ===== 知识边(RELATE,边上挂三帧元数据)=====
DEFINE TABLE knows        TYPE RELATION FROM character TO proposition SCHEMAFULL;
DEFINE FIELD polarity     ON knows TYPE bool DEFAULT true;             -- false=误信
DEFINE FIELD certainty    ON knows TYPE float DEFAULT 1.0;
DEFINE FIELD since_chapter ON knows TYPE int;
DEFINE FIELD acquired_via ON knows TYPE string DEFAULT "given";       -- saw/told/inferred
DEFINE TABLE causal       TYPE RELATION FROM event TO event SCHEMAFULL;
DEFINE FIELD ctype        ON causal TYPE string;                       -- physical/enabling/motivation/psychological
DEFINE TABLE participates TYPE RELATION FROM character TO event SCHEMAFULL;

-- ===== 向量(语义 RAG 召回设定,差异化)=====
DEFINE INDEX idx_prop_vec ON proposition FIELDS embedding HNSW DIMENSION 1024 DIST COSINE EFC 150 M 12;
-- ===== 全文(BM25)=====
DEFINE ANALYZER cn TOKENIZERS class FILTERS lowercase;
DEFINE INDEX idx_event_ft ON event FIELDS summary FULLTEXT ANALYZER cn BM25 HIGHLIGHTS;
-- ===== 触发器:写事件→自动建在场边(看见即知道的一半)=====
DEFINE EVENT on_event ON TABLE event WHEN $event="CREATE" THEN {
  -- 伪:对 participants 建 participates 边 + 给在场者发 knows 边
};
-- ===== CHANGEFEED:草稿审计/版本回放(transaction_time 的稳妥实现)=====
DEFINE TABLE manuscript CHANGEFEED 30d INCLUDE ORIGINAL;
```

**三帧 = 同一命题底座上按 knower 的查询(不建三个库):**
```surrealql
-- 第 N 章某角色知识帧(限知渲染的输入)
SELECT ->knows[WHERE since_chapter <= $n]->proposition.* AS known FROM character:老道;
-- 戏剧反讽 = 读者知 ∧ 视角不知(布尔投影)
-- 语义召回设定再追因果链(单库多模红利:向量 + 图)
SELECT id, summary, ->causal->event.summary AS effects
  FROM event WHERE embedding <|5,COSINE|> $q ORDER BY vector::distance::knn();
```

**递归图遍历**(3.x 杀手锏):`character:老道.{1..3}->knows->(?)`、最短路径 `event:a.{..+shortest=event:z}->causal->event`。

---

## 5. 写作流 / agentic → Hermes(吃透能力后的接法)

| 能力 | 怎么接(基于源码实测) |
|---|---|
| **主编 agentic** | `/v1/responses` + `stream` + `previous_response_id` 续接。**工具面来自 config 不是请求体**——scribe3 MCP 挂 config + 默认 `include_default_mcp_servers=True` → 工具自动可用 |
| **主编鲁棒性(白拿,别重造)** | 主编走 `AIAgent`(`run_agent.py` 5538 行,Responses 经 `api_server.py:1045 from run_agent import AIAgent` 调它):**streaming / Provider 容错 / 上下文压缩 / 用户打断 / Grace Call / 子 agent 委派 / 插件钩子全自带**——scribe3 别重造这些轮子(源码实测) |
| **技能自进化(主编越写越好)** | `skill_manage(patch)`(`skill_manager_tool.py:946` 六操作 create/patch/edit/write_file/remove_file/delete,patch 用 `fuzzy_match` 模糊匹配)让 `scribe-novel-v2` 成**活 playbook**:主编把 craft 发现自我沉淀(后台复盘 `run_agent.py:1445` 触发);**走审批 + `skills_guard` 扫描 + git 回滚;只沉淀流程、剧情事实进 SurrealDB;patch 小补丁非重写**。这把本会话手工挖的 gap1–13 等修法,变成主编可自维护的资产 |
| **工具系统** | scribe3 = FastMCP server;读工具 `readOnlyHint=true` 放行,写工具登记 WRITE_GATED |
| **写待批(核心)** | scribe3 写工具执行前发 MCP `elicitation/create`(form-mode)→ Hermes `ElicitationHandler` 弹批准(CLI/Telegram)→ accept 才落库,超时/decline=fail-closed。**取代自建 REST B3**(§7.1) |
| **skill** | `scribe-novel-v2/SKILL.md`(渐进披露:Tier1 名+述,Tier2 `skill_view` 全文,大规则拆 `references/`,上限~36k token) |
| **体检** | `hermes cron create "every 6h" "..." --skills novel-qc --script qc_fetch.py`:前置脚本从 SurrealDB 拉章节做机械统计→注入 prompt;agent 只判断+报告;`[SILENT]` 仅异常通知 |
| **分卷/分章并行** | Hermes **kanban**(`auto_decompose`)现成,别自建任务调度;`delegate_task` 子 agent 继承 scribe3 工具(`inherit_mcp_toolsets:true`) |
| **模型路由** | 主编=doubao;**auxiliary 小模型**配给 标题/压缩/QC判官 控成本;**启用 fallback_model**(当前无,doubao 限流即断) |
| **token 纪律** | prompt 缓存 5m TTL:稳定内容(世界观/skill)放头部、易变(本章状态)放尾部 |
| **记忆分工** | 世界观/章节/伏笔 → SurrealDB(Hermes memory 仅 2200 字符);Hermes memory 只放"作者偏好/项目元信息" |

---

## 6. 新旧版本隔离(scribe2 ↔ scribe3 共存,不串话/不丢工具)

**原则:scribe2 全程不动、novel 项目继续在它上面跑,直到 scribe3 达 parity 再切。** 五层全错开:

| 维度 | scribe2(旧,不动) | scribe3(新) | 为何这样隔离 |
|---|---|---|---|
| **SurrealDB** | 同实例 :8001 · **NS=scribe / DB=main** | 同实例 :8001 · **NS=scribe3 / DB=main** | 分 namespace=数据/ schema 完全隔离,同一 server,互不见 |
| **MCP 工具面** | FastMCP `scribe`,server_label `scribe2` | FastMCP `scribe3`,server_label `scribe3` | **关键防串话**:见下"工具不认识"解法 |
| **Hermes profile** | 默认 profile(挂 scribe2 + 旧 skill) | **`hermes --profile scribe3`**(只挂 scribe3 MCP + v2 skill) | 一个 profile 一套自洽工具,换 profile 换整套,**不在同一会话里同时见两套同名工具** |
| **skill** | `scribe-novel` | `scribe-novel-v2` | 名字不同,主编不混 playbook |
| **venv** | `scribe/.venv` | **`scribe3/.venv`(独立)** | scribe3 依赖变更/`hermes update` 不污染 scribe2 运行时 |
| **端口** | 前 3310 / 后 3320 | 前 **3311** / 后 **3321**(strictPort) | 可同时起,不抢端口 |

**"换了会话或工具不认识了"的根因与解法**:Hermes 主编工具面由 config 决定;若把 scribe2 和 scribe3 两个 MCP server 同时挂默认 profile,会出现**同名工具(create_work 等)冲突**→主编混乱。解法两道:
1. **首选 · profile 隔离**:scribe3 走独立 Hermes profile,主编做新系统时 `--profile scribe3` 只见 scribe3 工具;默认 profile 仍是 scribe2。换会话=换 profile,工具面始终自洽。
2. **加固 · 工具命名空间**:scribe3 所有工具名加前缀(如 `s3_create_work`),即便误同挂也不撞名。
> 数据迁移(S6):scribe2 的 NS=scribe 数据经一次性脚本投影到 scribe3 NS(实体→character、char_state→proposition+knows、foreshadow→promise…),CHANGEFEED/备份兜底,**不动原库**。

---

## 7. 关键架构决策(需拍板)

### 7.1 写待批:elicitation vs 自建 REST B3 —— 建议二选一
我在 `feat/surrealdb-knowledge-layer` 自建了 B3 待批 REST(commit 62e2f3e)。Hermes elicitation 功能重叠。**建议:scribe3 用 Hermes elicitation(少维护一套、天然多平台批准),自建 REST 待批不带进 scribe3**;前端批准 UI 可走 `mcp_serve.py` 的 `permissions_list_open`/`permissions_respond`。(若坚持前端 3311 完全自控批准,则保留 REST、不发 elicitation——但别两套并存。)

### 7.2 Hermes 升级:推迟 + 隔离验证(不盲升)
267 commits behind 但主编依赖三契约(Responses SSE event 名 / scribe MCP 挂载 / elicitation)。**建议:scribe3 先在当前 0.17.0 上建到 parity;升级单独立项**——`cp -r ~/.hermes ~/.hermes.backup-$(date +%F)` → pin 当前 commit → 隔离副本验证三契约 + mcp SDK≥1.11 不回退 → `hermes doctor` → 再升。config 已开 `pre_update_backup`。

### 7.3 双时态:自建字段(不等原生)
SurrealDB 原生 bitemporal 仅路线图;`VERSION` 时间旅行是 alpha 且绑 `versioned=true` 引擎。**决策:valid_time(章)+ transaction_time(draft_version)都自建字段(稳、可索引);审计回放用 CHANGEFEED(成熟)。** 这样 scribe3 可共用现成 :8001 实例(无需特殊引擎启动参数)。

---

## 8. 分阶段(增量,scribe2 不动;每段 TDD + 真机验证 + 提交)

| 段 | 目标 | 关键产出 | 验收 |
|---|---|---|---|
| **S0** | 隔离骨架 | scribe3/.venv;NS=scribe3 schema(§4 DEFINE 脚本);Hermes profile scribe3;端口 3311/3321 | schema 建成;两系统可同时跑不抢端口 |
| **S1** | 持久层迁移切片 | 内存 `World` → SurrealDB store(纵切片逻辑 project_frame/render/verify 不变,存储换 Surreal);焦三/老道场景落库重验 | 老道 prompt 仍不含「治眼」;find_leaks 清(真机) |
| **S2** | MCP 工具 + skill + elicitation | scribe3 FastMCP(读放行/写发 elicitation);scribe-novel-v2 skill;主编经 Responses 调通写一章 | 主编真机写一章,写操作弹批准、批准后落 NS=scribe3 |
| **S3** | 三帧 + 反讽 + 向量 RAG | reader 帧;反讽查询;proposition embedding + `<|K|>` 召回设定 | 反讽点可查;语义召回命中 |
| **S4** | cron 体检 + kanban | novel-qc cron(伏笔超期/声音/泄露扫描);kanban 分章并行 | cron 真机出体检札记;两章并行生成 |
| **S5** | 写作台 v2 双表面 + LIVE 多视图 | 前端 3311:结构面/散文面/校验面;表/图/时间线经 LIVE SELECT | 改一处三视图同步;每句回链结构 |
| **S6** | 数据迁移 + 切换 | scribe2 NS=scribe → scribe3 NS 投影脚本;parity 验收;切默认 profile | 乱世铜炉/拾骨记数据在 scribe3 可写可查;切换 |

---

## 9. 风险与反面教训
1. **请求体 tools 不生效**——主编工具必须固化进 config（`mcp_servers`/`platform_toolsets.api_server`），别指望运行时动态传。
2. **双时态非原生**——自建字段,别等官方;真·时间旅行是 alpha 风险。
3. **LIVE 仅单节点、无聚合**——聚合视图实时=对 `DEFINE TABLE AS SELECT` 物化视图再 LIVE;WS only。
4. **两套 MCP 同挂会撞名**——profile 隔离 + 工具命名空间。
5. **盲目 hermes update 会断主编**——隔离验证三契约再升。
6. **subagent_auto_approve=false**——多 agent 写流会被批准卡住,需为可信内部写设豁免路径。
7. **Hermes memory 太小(2200 字符)**——世界观只放 SurrealDB。
8. **纯模拟=流水账 / 限知靠查询非判官 / 渲染只读**——本体 v2 的铁律仍然成立(见本体文档)。

---

## 10. 一句话
**SurrealDB 3.1.5(已最新)做唯一真相底座——本体 v2 落成节点/RELATE 边/向量/全文/EVENT/CHANGEFEED,三帧是按 knower 的查询,双时态自建字段;Hermes 0.17.0(暂不盲升)做 agent 平台底座——主编走 Responses(工具来自 config)、技能走 skill、写操作走 elicitation 待批、体检走 cron、分章走 kanban、渲染走 completion;scribe3 用独立 NS/profile/venv/端口与 scribe2 彻底隔离(profile 切换防工具串话),scribe2 不动直到 parity 再切。配套《开发标准》保证后续能力都按这套长。**

---

### 附:来源(完整见两份调研原始报告)
**Hermes**:hermes-agent 源码 `gateway/platforms/api_server.py`(Responses/SSE)、`tools/mcp_tool.py`(ElicitationHandler)、`tools/approval.py`/`write_approval.py`、`cron/jobs.py`、`toolsets.py`、`hermes_cli/tools_config.py`(include_default_mcp_servers)、`~/.hermes/config.yaml`
**SurrealDB**:[3.0 发布](https://surrealdb.com/3.0) · [3.1 stability/DiskANN](https://surrealdb.com/blog/surrealdb-3-1-stability-diskann-and-a-new-release-process) · [graph](https://surrealdb.com/docs/surrealdb/models/graph) · [RELATE](https://surrealdb.com/docs/surrealql/statements/relate) · [datetimes/VERSION](https://surrealdb.com/docs/surrealql/statements/select) · [vector-indexes](https://surrealdb.com/docs/learn/data-models/vector-search/vector-indexes) · [LIVE](https://surrealdb.com/docs/surrealql/statements/live) · [DEFINE EVENT](https://surrealdb.com/docs/surrealql/statements/define/event) · [CHANGEFEED](https://surrealdb.com/docs/surrealql/statements/show) · [python sdk](https://surrealdb.com/docs/sdk/python)
