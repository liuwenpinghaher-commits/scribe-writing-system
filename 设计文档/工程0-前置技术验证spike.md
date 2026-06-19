# 工程0 · 前置技术验证 Spike(动手第一张工单)

> **目的**:在投入全功能建设前,用最小成本验证"**基于 Hermes Agent 底座 + SQLite/sqlite-vec + 复用 Chat UI**"这条架构路真实可行。
> **产出**:一个 **Go / No-Go 决策** + 已验证的最小骨架(可直接长成 Batch 1)。
> **不是 MVP**(00 §3 原则 11):这是建设的第 0 步(Batch 0),只为消除技术不确定性,不交付用户功能。
> 上游:[工程8 复用方案](工程8-HermesAgent复用方案.md)、[工程1 架构](工程1-架构与技术栈.md)、[00 §2.5/§2.7](00-总纲与数据模型.md)。

---

## 0. 验证清单总览(每项独立可判定)

| # | 验证项 | 通过即证明 | 失败回退 |
|---|---|---|---|
| S1 | Hermes Agent 安装并起服 | 底座可用、OpenAI 兼容 API 可调 | 评估自建 FastAPI 编排 |
| S2 | 自建领域 MCP Server(SQLite) | 领域数据/工具可被 Hermes 调用 | 用 Hermes 插件而非 MCP |
| S3 | qmd / sqlite-vec 向量检索 | 不需 pgvector 即有语义召回 | 评估外部 memory provider 或 pgvector |
| S4 | 复用 Chat UI(Open WebUI) | 对话核心零自建 | 轻前端直连 OpenAI API |
| S5 | 最小协作回路(想象→出稿→意见→重做) | 内核1 可落在 Hermes 上 | 拆解哪一环需自建 |
| S6 | 多本书隔离(Profile / work_id) | 多本书模型可行、不串味 | 定 per-user 进程方案 |
| S7 | 子 Agent 并行(delegate_task) | 可并行重活 | 串行降级 |
| S8 | Hook 埋点 → OTel → Phoenix | 可观测零侵入(工程10) | 自建日志中间件 |

**总判定**:S1–S5 全过 = 架构 **Go**(全押 Hermes 底座);S1/S2/S5 任一不过 = 触发回退评审。

---

## 1. 环境前提(人工准备,系统外)

- Python 3.11 + `uv`;一台 Mac/Linux(本地即可)。
- **至少一个 LLM API key**(前沿模型用于评议/写作;Hermes 模型可后置)。
- Docker(S7 沙箱/可选)。
- 这些是你提供的外部资源;Spike 脚本不代为申请。

---

## 2. 逐项验证(目标 / 步骤 / 通过标准 / 记录)

### S1 · Hermes Agent 起服
- **步骤**:按官方 `install.sh` 安装;`hermes` 起 CLI 跑通一轮对话;`hermes serve`(或等价)起 OpenAI 兼容 API(`http://127.0.0.1:8642/v1`)。
- **通过标准**:`curl :8642/v1/chat/completions` 返回正常补全;CLI 多轮对话与工具调用可见。
- **记录**:版本号(锁 `uv.lock`)、起服命令、端口。

### S2 · 自建领域 MCP Server(SQLite)
- **目标**:验证 Scribe 领域数据(稿件/设定/伏笔)以 MCP 工具暴露给 Hermes。
- **步骤**:写最小 `scribe_mcp`(stdio MCP server),建 SQLite,暴露 2–3 个工具:`save_chapter(work_id,seq,text)`、`get_chapter(work_id,seq)`、`upsert_setting(work_id,type,name,content)`;在 `~/.hermes/config.yaml` 的 `mcp_servers` 注册;对话中让主编调用。
- **通过标准**:Hermes 成功调用这些工具(工具名前缀 `mcp_scribe_*`),数据正确落 SQLite 并可读回。
- **记录**:stdio 稳定性、并发表现、错误传播是否被 Hermes 转为工具结果(不崩主循环)。

### S3 · qmd / sqlite-vec 向量检索
- **目标**:不起 PostgreSQL/pgvector 即有语义召回。
- **步骤**:启用 Hermes `qmd` 技能(或在 `scribe_mcp` 内集成 `sqlite-vec`);灌入 ~200 段示例正文 embedding;按"语义 query"召回 top-k;对比 FTS5 关键词召回。
- **通过标准**:语义 query 能召回**关键词不命中但语义相关**的段落;延迟可接受(本地、数千段 < 数百 ms)。
- **记录**:sqlite-vec 版本(alpha,仅暴力扫描)、向量量级上限观察、是否需 rerank。

### S4 · 复用 Chat UI(Open WebUI)
- **步骤**:跑官方 `setup_open_webui.sh`(或手动指向 `:8642/v1`);在 Open WebUI 中与主编对话。
- **通过标准**:对话/流式/多模型切换全部由 Open WebUI 提供,零自建;能看到工具调用。
- **记录**:能否嵌入自定义面板的限制(印证"小说面板需自建",对齐工程2b);评估 LobeChat 插件路线是否更适合。

### S5 · 最小协作回路(核心)
- **目标**:把内核1 的"想象→出稿→意见→重做"跑在 Hermes 上。
- **步骤**:写 2 个最小 `SKILL.md`(`capture-imagination`、`rewrite-on-feedback`)+ 用 `scribe_mcp` 存 `Imagination/Chapter/Snapshot/FeedbackNote`。对话中:① 抛一个想象 → ② 主编据此出一段大纲/正文 → ③ 提一句自然语言意见("更狠") → ④ 主编**定向重写**产新 Snapshot。
- **通过标准**:四步贯通;FeedbackNote 被解析为指令并**只改指出处**(非整章重生成);版本链(parent_id)正确;全过程数据在 SQLite 可追溯。
- **记录**:解析意见的可靠性、定向重写质量、回路时延。

### S6 · 多本书隔离
- **步骤**:建两本书(两个 Hermes Profile,或单进程 + work_id 过滤);在 A 书写设定,到 B 书生成。
- **通过标准**:**B 书生成绝不出现 A 书设定**(防串味);owner 级品味/素材可跨书可见(若已接 S5)。
- **记录**:Profile 方案 vs work_id 过滤的取舍(回填 00 §2.7 / 工程8 开放问题)。

### S7 · 子 Agent 并行(可选,降风险)
- **步骤**:`delegate_task(tasks=[...])` 派 2–3 个并行子任务(如"查三条线索资料")。
- **通过标准**:并行执行、上下文隔离、仅回传摘要;父中断子取消。
- **记录**:异步子 Agent 稳定性(较新功能)。

### S8 · Hook 埋点 → OTel → Phoenix(可选,对齐工程10)
- **步骤**:注册 `pre/post_tool_call`、`pre/post_llm_call` Hook,发 OTel span;本地起 Phoenix(`pip install arize-phoenix`)查看 trace。
- **通过标准**:一次对话的 LLM/工具调用在 Phoenix 中形成正确的 span 层级(invoke_agent→chat→execute_tool)。
- **记录**:Hook 是否足以覆盖所需埋点;token/成本字段是否可得。

---

## 3. 决策门(Spike 出口)

完成后填写:

```
S1 Hermes 起服        : Pass / Fail  备注:
S2 领域 MCP(SQLite)  : Pass / Fail  备注:
S3 qmd/sqlite-vec     : Pass / Fail  备注:
S4 Open WebUI         : Pass / Fail  备注:
S5 最小协作回路        : Pass / Fail  备注:
S6 多本书隔离          : Pass / Fail  备注:
S7 子Agent 并行        : Pass / Fail  备注:
S8 OTel/Phoenix       : Pass / Fail  备注:
```

- **Go(S1–S5 全 Pass)**:确认"Hermes 底座 + SQLite/sqlite-vec + 复用 UI"架构,进入 [工程7](工程7-工程化与路线图.md) Batch 1。
- **部分 Pass**:按上表"失败回退"逐项决策(如 S2 失败→改用 Hermes 插件;S3 失败→评估 pgvector;S4 失败→轻前端直连)。
- **No-Go(S1/S5 失败)**:重审"是否自建编排框架",回到工程8 开放问题。

---

## 4. 交付物

- 已起服的 Hermes + 最小 `scribe_mcp`(SQLite)+ 2 个 SKILL.md + Open WebUI 接通 + (可选)Phoenix。
- 一份填好的决策门表 + 各项记录。
- 这套骨架**直接长成 Batch 1**(非一次性 demo)。
