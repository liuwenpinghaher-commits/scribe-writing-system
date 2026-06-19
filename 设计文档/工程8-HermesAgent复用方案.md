# 工程8 · Hermes Agent 复用方案

> **上游**:[00-总纲与数据模型 §2.5](00-总纲与数据模型.md)、[内核0-主编智能体](内核0-主编智能体.md)。
> **方针**:Scribe 不自建 Agent 框架。领域逻辑实现为 Hermes Agent 之上的「SKILL.md + 轻量插件 + MCP 工具」,最大化复用、最小化自写代码。自建仅限真正的业务层(稿件版本、设定/伏笔 schema、账号体系、前端编辑器)。
> **设计基线** 2026 年 6 月。

---

## 1. 在回路中的位置与职责

Hermes Agent 是**整个 Scribe 的运行底座**。它扮演「操作系统」的角色——提供调度主循环、工具发现、记忆后端、子 Agent 编排、定时任务、MCP 接入——而 Scribe 的领域逻辑(品味、写章流程、伏笔校验、多方案生成)作为插件与技能运行于其上。

```
┌──────────────────────────────────────────────────────────────┐
│  Scribe 业务层(自建 Python)                                   │
│   schemas / account / editor frontend / DB migrations         │
├──────────────────────────────────────────────────────────────┤
│  Scribe 技能层(SKILL.md × N)                                  │
│   写章流程 / 卷尾钩子 / 多方案 / 品味注入 / 主动体检 …          │
├──────────────────────────────────────────────────────────────┤
│  Scribe 插件层(~/.hermes/plugins/<name>/)                     │
│   scribe-draft / scribe-bible / scribe-memory / scribe-taste  │
├──────────────────────────────────────────────────────────────┤
│  Hermes Agent 底座(开箱即用)                                   │
│   AIAgent 主循环 / 工具自注册 / SKILL.md 引擎                  │
│   delegate_task(子Agent) / Cron / MCP 客户/服务端             │
│   记忆后端(MEMORY.md + state.db + 外部 Provider)              │
│   7 层安全 / 6 后端 / 6 入口                                   │
└──────────────────────────────────────────────────────────────┘
         ↓ MCP                           ↓ delegate_task
   PostgreSQL/pgvector              并行子 Agent
   (Scribe DB)                      (调研/批量章/评审)
```

---

## 2. 设计目标与百万字挑战

| 目标 | Hermes 提供的答案 | 剩余风险 |
|---|---|---|
| 统一人格的编排主循环 | `AIAgent` 同步编排;三层提示词护 prefix cache | 百万字不能塞上下文,靠工具+检索(见内核0 §3.1) |
| 工具按需扩展 | `tools/*.py` 自注册,`registry.register()` | 工具多了需 schema 按需检索,不能一次全塞 |
| 跨会话记忆 | MEMORY.md 冻结注入 + state.db SQLite FTS5 + 8 种外部 Provider(单选) | 单选 Provider 是硬约束;MEMORY.md 2200 字符硬上限 |
| 并行子 Agent | `delegate_task(goal,context,toolsets,max_iterations)` / tasks=[...] | 上下文完全隔离只回传摘要,设计时须明确接口 |
| 定时全文体检 | Cron jobs.json 60s tick,每 job 隔离新 AIAgent | 需设计 `[SILENT]` 归档 vs 推送逻辑 |
| MCP 接入 Scribe DB | MCP 客户端(config.yaml mcp_servers,stdio/HTTP+OAuth2.1) | 自建 MCP Server for PostgreSQL/pgvector |
| 技能自生长 | SKILL.md 自主创建(约每 15 次反思,`skill_manage`),可人审批 | 写作场景要强制 `skills.write_approval=true` |
| 安全隔离 | 7 层安全(容器/白名单/危险命令审批/SSRF 防护…) | Desktop 仍 preview;供应链扫描需校验 |

---

## 3. 详细设计

### 3.1 借用 vs 自建 总映射表

表中「层」列对应 00 §2 同心层。

| Scribe 能力 | 层 | Hermes 状态 | 具体落法(映射到哪个原语) |
|---|---|---|---|
| **主编智能体编排主循环** | 中枢 | ✅ 开箱即用 | `AIAgent` 主循环;prompt 三层(stable=主编人格+北极星+品味/context=当前章/volatile=当次任务) |
| **对话式评议(DiscussionThread)** | 内核1 | ✅ 开箱即用 | 主编对话流;`DiscussionThread` 存进 state.db / pgvector via MCP |
| **主动引擎(ProactiveInsight)** | 内核1 | ✅ 开箱即用 | Cron job:每 N 章/每日触发隔离 AIAgent 全文体检,产出 `ProactiveInsight`,`[SILENT]` 存档,前端拉取显示 |
| **品味模型注入(TasteModel)** | 内核2 | 🔧 需插件 | 插件 `scribe-taste`:Hook `pre_llm_call` 注入 `StyleExemplar` + 负向黑名单 few-shot;Hook `post_tool_call(propose_options)` 附品味权重 |
| **反平庸/反同质化** | 内核3 | 🔧 需插件+技能 | 技能 `写章流程` 内嵌多样性约束指令;`scribe-taste` 插件注入对比样本(「不是你风格」反例);Hermes 本身不含写作美学逻辑 |
| **多方案生成(OptionSet)** | 内核1 | 🔧 需技能 | SKILL.md `多方案决策`:调用 `propose_options(decision_point)` 工具,产出 `OptionSet`,写入 Scribe DB via MCP |
| **分层规划(Volume/Chapter大纲)** | 实现1 | 🔧 需技能 | SKILL.md `分层规划`:按 Volume→Chapter→Outline 层序递进;调用 `search_book` 避免结构冲突 |
| **正文生成(写章)** | 实现2 | 🔧 需技能 | SKILL.md `写章流程`:检索 ContextBundle → 注入品味 → 生成 → 写入 `Segment`/`Snapshot` via MCP 工具 |
| **编排引擎(任务调度)** | 实现3 | ✅ 开箱即用 | `AIAgent` 主循环;子 Agent 派发见实现3 |
| **记忆与检索(AgentMemory/MemoryEntry)** | 实现4 | 🔧 需配置+插件 | 记忆 Provider 选 **Hindsight**(知识图谱,关系推理强)或 Mem0;Scribe DB 全文/向量检索通过 MCP Server(自建)暴露为工具 `search_book` / `search_materials` |
| **连贯性校验(ConsistencyFlag)** | 门槛1 | 🔧 需插件 | 插件 `scribe-bible`:工具 `check_consistency(scope)` / `scan_foreshadow(scope)` 调用 Scribe 校验服务,结果写 `ConsistencyFlag` |
| **设定圣经(SettingItem/Character)** | 门槛2 | 🔧 需插件 | 插件 `scribe-bible`:工具 `lookup_setting(entity)` / `upsert_setting(entity,data)`,CRUD via MCP PostgreSQL |
| **素材库(Material)** | 原料 | 🔧 需插件 | 插件 `scribe-draft`:工具 `search_materials(query)` 向量检索 Material;`ingest_material(url/text)` |
| **稿件版本(Snapshot/Branch)** | 工程4 | 🏗 需自建 | 自建(Hermes 无版本分支概念);插件 `scribe-draft` 包装 `create_snapshot` / `diff_snapshots` 工具 |
| **LLM 成本路由** | 工程3 | 🔧 需配置 | Hermes `delegate_task` 可 `model=` 指定;重活→子 Agent 用 Claude Opus;批量生成→本地 Hermes 4;规划/摘要→快模型 |
| **API Server(工程5)** | 工程5 | ✅ 开箱即用 | Hermes OpenAI 兼容 API Server(`hermes serve`);前端编辑器对接此接口 |
| **质量度量(工程6)** | 工程6 | 🏗 需自建 | 度量逻辑自建(Hermes 不含写作美学度量);通过工具/Cron 触发;结果写 Scribe DB |
| **前端编辑器(工程2)** | 工程2 | 🏗 需自建 | React 编辑器调 Hermes API Server;Hermes Desktop(Electron)仍 preview,生产不依赖 |
| **账号/多用户隔离** | 工程1 | 🏗 需自建 | Hermes 无多租户;per-user Hermes 实例或自建 auth 层路由 |
| **Cron 全文体检** | 工程7 | ✅ 开箱即用 | jobs.json 配置;`context_from` 链式;`[SILENT]` 归档 |
| **子 Agent:并行调研** | 内核0 §3.9 | ✅ 开箱即用 | `delegate_task(role="researcher",goal=...,toolsets=["web"])` 多任务并行 |
| **子 Agent:批量章节** | 内核0 §3.9 | ✅ 开箱即用 | tasks=[...] 并行;每子 Agent 隔离上下文,只回传章节摘要 |
| **子 Agent:多视角评审** | 内核0 §3.9 | ✅ 开箱即用 | 派「读者视角」「逻辑视角」「文风视角」三子 Agent 并行评审同一章 |
| **技能自生长(AgentSkill)** | 内核0 §3.6 | ✅ 开箱即用 | 启用 `skills.write_approval=true`;`propose_skill` 触发 → 人审批 → `AgentSkill` 状态机 |
| **Web 搜索工具** | 工具 | ⚠️ 依赖订阅 | 高质量搜索依赖 Nous Portal 订阅;备选:自配 Tavily/Brave API key 注入 |

**图例**:✅ 开箱即用 / 🔧 需插件或配置 / 🏗 需自建 / ⚠️ 有外部依赖

---

### 3.2 Scribe 落在 Hermes 上的具体形态

#### 3.2.1 SKILL.md 技能(agentskills.io 开放标准)

每个技能一个目录(`skills/<name>/SKILL.md`),YAML frontmatter + When to Use / Procedure / Pitfalls / Verification。

| 技能名 | 触发场景 | 核心步骤 | requires_toolsets |
|---|---|---|---|
| `写章流程` | 人指令"写第N章" | ①检索 ContextBundle(search_book+recall_memory) ②注入品味(scribe-taste hook) ③生成 Segment ④写入 Snapshot via MCP ⑤触发 ConsistencyFlag 检查 | scribe,mcp_scribedb |
| `分层规划` | 新建 Volume/Chapter 大纲 | ①读 AuthorIntent+北极星 ②结构规划 Volume beats ③细化 Chapter outline ④产出 OptionSet 供人选 | scribe,mcp_scribedb |
| `多方案决策` | 情节走向/人物抉择/关键场景 | ①识别 decision_point ②生成 2–4 个差异化方案+各自代价 ③写入 OptionSet ④等待人选 | scribe |
| `卷尾钩子专项` | 每卷末章前触发 | ①扫描本卷伏笔状态 ②生成 3 种钩子方案(悬念型/反转型/情感型) ③与北极星比对 ④产出 OptionSet | scribe,mcp_scribedb |
| `品味对话` | 人提供范本/否定某段 | ①提取风格描述符 ②更新 TasteModel ③调用 scribe-taste 插件刷新注入策略 | scribe |
| `全文主动体检` | Cron 触发(每 N 章/每日) | ①scan_foreshadow(global) ②check_consistency(global) ③比对北极星 ④产出 ProactiveInsight 列表 ⑤[SILENT]存档 | scribe,mcp_scribedb |
| `意见重做` | 人提交 FeedbackNote | ①解析 nl_critique→parsed_directive ②检索受影响 Segment ③重写 ④产新 Snapshot ⑤链接 FeedbackNote | scribe,mcp_scribedb |

#### 3.2.2 插件(~/.hermes/plugins/<name>/)

每个插件含 `plugin.yaml + __init__.py(register) + schemas.py + tools.py`。

| 插件名 | 职责 | 关键 Hook / 工具 |
|---|---|---|
| `scribe-draft` | 稿件正文 CRUD、Snapshot 版本、Segment 写入 | 工具:create_snapshot / commit_segment / diff_snapshots / list_versions |
| `scribe-bible` | 设定圣经 + 连贯性校验 | 工具:lookup_setting / upsert_setting / check_consistency / scan_foreshadow;Hook:post_tool_call(写章完成后自动触发轻量校验) |
| `scribe-memory` | Scribe 五层记忆命名空间管理 + 跨作品隔离 | Hook:on_session_start(注入 AgentMemory working/session);on_session_end(压缩归档 episodic);工具:recall_memory / write_memory |
| `scribe-taste` | 品味注入 + 反同质化 | Hook:pre_llm_call(注入 StyleExemplar few-shot + 负向黑名单);Hook:post_tool_call(propose_options 附品味权重);工具:update_taste_model |

> **文件大小公约**(00 §2.6):每个 `tools.py` / `__init__.py` 软上限 400 行,硬上限 600 行;超出按职责拆 `tools_draft.py` / `tools_review.py` 等。

#### 3.2.3 MCP 工具(Hermes 作客户端)

```yaml
# config.yaml mcp_servers 段
mcp_servers:
  scribedb:
    transport: stdio
    command: python
    args: ["-m", "scribe_mcp.server"]   # 自建 MCP Server
    tool_prefix: mcp_scribedb_
    whitelist:
      - search_book
      - search_materials
      - upsert_imagination
      - upsert_chapter
      - upsert_segment
      - upsert_setting
      - read_author_intent
      - write_consistency_flag
      - write_proactive_insight
```

`scribe_mcp/server.py` 对接 PostgreSQL + pgvector:全文检索走 `tsvector`,语义检索走 `pgvector cosine`,混合 RRF 融合。这是 Scribe **自建范围最核心的一件事**。

#### 3.2.4 delegate_task 子 Agent 使用场景

```python
# 并行多线索调研(资料收集不阻塞主编)
results = await agent.delegate_task(
    tasks=[
        {"goal": "调研「记忆宫殿」叙事技法", "toolsets": ["web"]},
        {"goal": "核查第12章历史细节", "toolsets": ["web"]},
        {"goal": "搜集类似设定的反例", "toolsets": ["web"]},
    ]
)

# 批量独立章节(可并行的初稿)
chapters = await agent.delegate_task(
    tasks=[{"goal": f"起草第{n}章", "context": ctx[n], "toolsets": ["scribe"]}
           for n in range(c_start, c_end)],
    max_concurrent_children=3,   # 默认值
)

# 多视角评审(同一章三视角并行)
reviews = await agent.delegate_task(
    tasks=[
        {"goal": "读者视角评审:节奏与代入感", "model": "fast"},
        {"goal": "逻辑视角评审:因果与时间线一致性", "model": "fast"},
        {"goal": "文风视角评审:是否偏离作者品味", "model": "fast"},
    ]
)
```

**铁律(同内核0 §3.9)**:默认主编单体;仅任务能真正并行才拆。串行/强依赖任务不派子 Agent。

#### 3.2.5 Cron 定时任务

```jsonc
// jobs.json
[
  {
    "name": "scribe_proactive_review",
    "schedule": "0 3 * * *",          // 每天凌晨3点
    "goal": "对 work_id=${WORK_ID} 执行全文主动体检,产出 ProactiveInsight",
    "skill": "全文主动体检",
    "context_from": "last_session",
    "flags": ["[SILENT]"]              // 仅存档,前端轮询读取
  },
  {
    "name": "scribe_foreshadow_scan",
    "schedule": "after_chapter_commit", // 事件触发(自定义 Hook)
    "goal": "扫描受影响伏笔链",
    "toolsets": ["scribe"],
    "flags": ["[SILENT]"]
  }
]
```

#### 3.2.6 记忆 Provider 选型

推荐优先级:**Hindsight**(知识图谱,关系推理强,适合人物/伏笔/设定关系网络)> Mem0(生产成熟,API 稳定)> 默认 state.db(仅 MVP 阶段足够)。

| Provider | 优势 | 劣势 | 适用阶段 |
|---|---|---|---|
| state.db (默认) | 零配置,SQLite FTS5 | 无向量/图;百万字后性能瓶颈 | MVP |
| **Hindsight** | 知识图谱;人物-伏笔-设定关系推理 | 需单独部署;API 稳定性待核实 | 增强版 |
| **Mem0** | 生产成熟;API 稳定;自托管可选 | 无图推理 | 增强版备选 |

> **注**:Hermes 外部 memory provider **单选**,是硬约束。切换 provider 需迁移。MVP 阶段用 state.db + Scribe MCP 自建检索,无需绑定外部 provider。

---

### 3.3 autonovel 复用评估

**autonovel**(Nous 官方,github.com/NousResearch/autonovel)pipeline:世界观→大纲→分章起草→自动修订→LaTeX 排版→插图→有声书。

| autonovel 模块 | Scribe 态度 | 理由 |
|---|---|---|
| 世界观→大纲→分章 pipeline | 🔧 **参考架构,不直接用** | autonovel 是全自动流水线(无人协作回路);Scribe 核心是人机共创,需大量人的判断/选项/意见驱动 |
| 自动修订(revision loop) | ✅ **可借用思路** | 内核3 反平庸的迭代改稿可参考其 revision prompt 设计 |
| LaTeX 排版 / 有声书 | 🔧 **后期可选接入** | 当 Scribe 需要导出功能时 fork 或包装为工具 |
| Hermes 工具调用范式 | ✅ **直接参考** | autonovel 的工具 schema、错误处理、上下文管理方式是真实 Hermes 用法示例 |

**结论**:fork autonovel 作为**技术验证沙盒**——用它快速验证 Hermes 工具链、prompt 三层架构、子 Agent 并行的实际行为;不直接用其业务流程。

---

## 4. 数据契约(引用 00 §4)

工程8 不新增实体。相关实体已登记于 00 §4:

- `AgentMemory` / `AgentSkill`:内核0 §4
- `DiscussionThread` / `ProactiveInsight`:内核0 §4
- `Snapshot`:版本层(00 §4.4)
- `ConsistencyFlag`:门槛层(00 §4.3)
- `TasteModel` / `PreferenceSignal`:内核2(00 §4.1)

**MCP Server 暴露的视图**(非新实体,查询层):

```python
# scribe_mcp/server.py 暴露的工具签名(供 Hermes 调用)
search_book(query: str, scope: Literal["chapter","volume","global"],
            work_id: UUID, top_k: int = 8) -> list[SearchResult]

search_materials(query: str, work_id: UUID,
                 types: list[str] | None = None, top_k: int = 5) -> list[Material]

upsert_segment(chapter_id: UUID, seq: int, text: str,
               created_by: Literal["ai","human"]) -> Segment

write_consistency_flag(chapter_id: UUID, error_class: str,
                       severity: str, detail: str,
                       evidence_refs: list[dict]) -> ConsistencyFlag

write_proactive_insight(work_id: UUID, kind: str, summary: str,
                        evidence_refs: list[dict], confidence: float,
                        severity: str, suggested_action: str) -> ProactiveInsight
```

---

## 5. 对外接口

| 接口 | 方向 | 说明 |
|---|---|---|
| `hermes serve` (OpenAI 兼容 API) | 前端→Hermes | 前端编辑器通过 `/v1/chat/completions` 与主编对话 |
| `hermes mcp serve` | 外部 Agent→Hermes | 将 Scribe 主编能力暴露为 MCP 工具(可供 Claude Code / Cursor 调用) |
| MCP `scribedb` server | Hermes→PostgreSQL | Hermes 通过 stdio MCP 工具读写 Scribe DB |
| Cron jobs.json | Hermes→定时任务 | 全文体检 / 伏笔扫描定时触发 |
| Plugin Hooks | Scribe 插件↔Hermes | pre/post_llm_call 注入品味;on_session_end 压缩记忆 |

---

## 6. 失败模式与缓解

| 风险 | 场景 | 缓解 |
|---|---|---|
| **单 memory provider 锁定** | 切换 Hindsight→Mem0 需全量迁移 | MVP 阶段用 state.db 延迟绑定;选定后写迁移脚本并版本化;保留 Scribe MCP 作独立检索不依赖 provider |
| **MEMORY.md 2200 字符硬上限** | 长篇积累后品味/北极星注入被截断 | 关键信息(北极星/品味摘要)走 SKILL.md stable 层注入,不放 MEMORY.md;MEMORY.md 只放当前任务短暂上下文 |
| **SKILL.md 自主创建失控** | 主编产生不合预期的流程改动 | 强制 `skills.write_approval=true`;AgentSkill 状态机人审批门(内核0 §3.6) |
| **Desktop / preview 不成熟** | Hermes Desktop 仍 preview,UI 不可依赖 | Scribe 自建 React 编辑器,对接 `hermes serve` OpenAI API;不依赖 Desktop |
| **Nous Portal 搜索订阅依赖** | Tool Gateway 高质量搜索需订阅 | 自配 Tavily 或 Brave API key 注入 Hermes 工具注册;非订阅锁定 |
| **delegate 异步刚上线** | 子 Agent 异步 API 可能不稳定 | MVP 阶段子 Agent 用同步调用;异步 delegate 作增强版功能,充分测试后上线 |
| **供应链扫描** | 插件/MCP server 注入风险 | Hermes 7 层安全含 Context 文件注入扫描;MCP 凭证过滤;插件代码自审 |
| **子 Agent 上下文隔离** | 只回传摘要可能丢失细节 | 明确定义每个 delegate 的输出 schema;批量章节子 Agent 须返回结构化 `ChapterDraft` 而非自由文本摘要 |

---

## 7. MVP vs 完整版

### MVP(目标:2–4 周跑通最小协作回路)

**最短路径**:

```
1. 安装 Hermes Agent(uv add hermes-agent)
2. 配置 config.yaml:model=claude-opus-4(或 claude-sonnet-4-5)
3. 自建 scribe_mcp/server.py:PostgreSQL+pgvector,暴露 search_book / upsert_segment / write_proactive_insight 等核心工具
4. config.yaml mcp_servers 注入 scribedb
5. 编写 SKILL.md「写章流程」(最小版:检索→生成→存稿)
6. 编写 SKILL.md「多方案决策」
7. 安装插件 scribe-draft(最小:commit_segment / create_snapshot)
8. 用 hermes serve 起 API Server
9. 前端编辑器(最简 React 页面)对接 /v1/chat/completions
10. 跑通:输入一段想象→主编评议→产出 OptionSet→人选→写章→存 Snapshot
```

MVP **不上**:Cron 全文体检、子 Agent、scribe-taste 插件、外部 memory provider、自我优化、Hermes Desktop。

MVP 记忆:state.db(SQLite)足够;Scribe DB 检索走 MCP。

### 增强版(MVP 验证后)

- 上 `scribe-taste` 插件(品味注入)+ `scribe-bible` 插件(连贯性校验)
- 上 Cron 全文体检 → ProactiveInsight
- 子 Agent:并行调研、多视角评审
- 外部 memory provider(Hindsight 或 Mem0)
- Hermes 4 本地部署 + LoRA 个性化起步

### 完整版

- 自我优化闭环(propose_skill + 人审批 AgentSkill 状态机)
- 图记忆(Hindsight 知识图谱成熟后)
- 多模型成本路由(Opus/Sonnet/Hermes4/fast 按任务路由)
- 反同质化全套(对比样本 DPO 数据累积 → 薄 LoRA)
- autonovel 导出 pipeline(排版/有声书)

---

## 8. 证据与引用

**Hermes Agent 核心事实【已核实】**:
- 官网 [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com)
- GitHub [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- autonovel [NousResearch/autonovel](https://github.com/NousResearch/autonovel)
- agentskills.io 开放标准(SKILL.md 跨 Claude Code/Cursor 互通)

**架构方针来源【已核实】**:
- 并行+81%/串行−39~−70%:Google《Scaling Agent Systems》[来源](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)
- 默认单 LLM+检索:Anthropic《Building Effective Agents》[来源](https://www.anthropic.com/research/building-effective-agents)
- 工具质量比 prompt 更重要:Anthropic《Writing Tools for Agents》[来源](https://www.anthropic.com/engineering/writing-tools-for-agents)
- Write/Select/Compress/Isolate 上下文工程:mem0 [来源](https://mem0.ai/blog/context-engineering-ai-agents-guide)
- 全自主风险警告:[arXiv 2502.02649](https://arxiv.org/pdf/2502.02649)

**【需复核】**:
- Hindsight、Mem0 等外部 provider 的 Hermes 集成文档稳定性,使用前查官方最新 changelog
- delegate 异步 API 刚上线,行为细节以实际版本为准
- Hermes Agent 的 star 数/社区活跃度,MVP 前重新核实

**【设计决策】**:
- 「MVP 用 state.db 延迟绑定 memory provider」:经评估 pgvector MCP 已覆盖检索需求,外部 provider 的关系图谱价值需增强版验证
- 「scribe_mcp/server.py 自建而非用现成 PostgreSQL MCP」:需保证 Scribe 专属工具 schema(search_book 的 scope/work_id 语义等)精确可控

---

## 9. 开放问题

1. **MCP Server 稳定性 spike**:自建 `scribe_mcp/server.py` 接入 Hermes 的最大未知。MVP 前须验证:工具 schema 注册、stdio 通信稳定性、并发写入时的 PostgreSQL 连接池行为。

2. **memory provider 迁移成本**:单选约束意味着「先用 state.db,后迁 Hindsight」须完整迁移脚本。MVP 阶段就设计好迁移接口,避免锁死。

3. **SKILL.md 与插件的边界**:当「写章流程」技能需要调用 `scribe-draft` 插件工具时,技能的 `requires_toolsets` 与插件注册的 toolset 命名须对齐——需在 MVP 阶段建立命名约定。

4. **子 Agent 输出 schema**:批量章节子 Agent 只回传摘要,但「足够的摘要」对主编继续编排至关重要。需在 MVP 增强期定义标准化 `ChapterDraftSummary` 结构。

5. **Hermes 版本锁定策略**:Hermes Agent 仍在快速迭代。建议 lockfile 固定版本(`uv.lock`),升级前跑 Scribe 集成测试套件。

6. **多用户/多作品隔离**:Hermes 无原生多租户。方案 A:per-user Hermes 进程(隔离彻底,资源重);方案 B:单进程 + work_id/owner_id 全面过滤(轻量,需防串味)。MVP 阶段单用户跳过,增强版前决策。

---

## 核实更新:向量存储 与 Chat UI 进一步复用(2026-06,联网核实)

> 以下两条**修订**前文的"自建清单"与"MVP 路径",进一步减少自写代码。

### A. 向量存储:MVP 用 SQLite + sqlite-vec,不自建 PostgreSQL+pgvector

**已核实事实:**
- Hermes 内置 `state.db` = SQLite + **FTS5 关键词**,**无向量**;8 个记忆 Provider 中**本地的(Holographic/ByteRover/OpenViking)都不是真向量检索**,真向量的(Mem0/RetainDB/Supermemory/Honcho)**全是云端需 API key**。[memory-providers](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers)
- **sqlite-vec**(Alex Garcia,MIT/Apache,零依赖,SQL 虚拟表做向量 KNN;现 alpha,仅暴力扫描无 ANN,**<10万向量适用**)。[sqlite-vec](https://github.com/asg017/sqlite-vec)
- **Hermes 的 `qmd` 技能已原生用 SQLite+FTS5+sqlite-vec 做本地混合检索(BM25+向量+LLM rerank)**——有现成路径。[OpenClaw local-first RAG](https://www.pingcap.com/blog/local-first-rag-using-sqlite-ai-agent-memory-openclaw/)

**修订决策:**
- **MVP 存储 = 单个 SQLite**(承载稿件/版本/设定/伏笔等关系数据)**+ sqlite-vec(向量)**,优先**复用 Hermes `qmd` 技能**做检索,不再单独起 PostgreSQL/pgvector,**也免去 MVP 自建向量 MCP Server**。
- **迁移门槛(切 pgvector)**:向量 >~50万、需多租户并发写/细粒度权限、单文件并发瓶颈出现时。届时 embedding 生成逻辑不变,只换存储后端——**实现4 检索的接口契约保持不变**。
- 影响:[实现4-记忆与检索](实现4-记忆与检索.md) 的"PG 关系表落地双图"在 MVP 降级为"SQLite 表 + sqlite-vec";门槛/版本同库。

| | SQLite + sqlite-vec(MVP) | PostgreSQL + pgvector(规模化) |
|---|---|---|
| 部署 | 单文件零服务 | 独立进程 |
| 向量 | 暴力 KNN,<10万 | HNSW/IVF ANN,百万级 |
| 多租户 | 弱 | 强 |
| 与 Hermes | 原生(qmd) | 需自建 Provider |

### B. Chat UI:复用现成,只自建小说专用面板

**已核实事实:** Hermes 有 **Desktop(Electron v0.16 正式版)、Web Dashboard、CLI/TUI、OpenAI 兼容 API(`:8642/v1`)+ 官方一键 `setup_open_webui.sh`**,可接 Open WebUI / LobeChat / LibreChat / ChatBox。[Open WebUI 接入](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/open-webui)

**修订决策:**
- **对话核心(会话管理/流式/多模型切换)= 复用现成**,不自建。
- **小说专用面板(大纲树/正文编辑器+diff/设定圣经/校验·伏笔·主编札记侧栏/OptionSet 卡)= 必须自建**——无任何现成 chat UI 自带([工程2](工程2-交互与编辑器.md) 仍有效)。
- **两条复用路线**:① **LobeChat standalone 插件**——把小说面板做成 React 组件嵌入,复用整个对话核心,改造成本最低;② 当小说面板占比 >60% 时,**轻前端(Next.js)直连 Hermes OpenAI API** 自建布局,比侵入式改 LobeChat 更省。
- **MVP 建议**:纯对话先用 **Hermes Desktop / Open WebUI(一键)** 跑通主编对话回路;小说编辑器作为 Phase 1 后段并行开发(走路线①或②,届时定)。

### C. 据此更新"自建最小清单"

| 原列为自建 | 修订 |
|---|---|
| 向量 MCP Server(pgvector) | **MVP 取消**,改用 qmd/sqlite-vec;规模化再建 |
| Chat UI | **取消自建对话核心**;仅自建小说专用面板 |
| 仍需自建 | 稿件版本/设定·伏笔 schema(SQLite)、**多本书/作品库逻辑**、小说编辑器面板、少量领域工具/技能。**账号/鉴权你自建,系统不做账号体系**(只消费 owner_id) |
