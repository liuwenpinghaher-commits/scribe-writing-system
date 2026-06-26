# 05 · Hermes Agent 使用深度诊断

> 对象:**scribe3** 对 Hermes Agent 的使用现状、深度、未用能力与改进方案。
> 取证基于 `hermes --version` 二进制实测 + `~/.hermes/` 配置 + scribe3 集成代码,精确到 `文件:行号`/配置键。
> **安全说明**:扫描 `~/.hermes/.env` 与 config 时**未读取/未打印任何 secret 值**,仅取字段名。配套 [01](./01-系统架构总览.md)–[04](./04-本体论实现分析与改进方案.md)、[06-SurrealDB使用深度诊断.md](./06-SurrealDB使用深度诊断.md)。

---

## 0. 环境基线(二进制实测)

| 项 | 实测值 |
|---|---|
| Hermes 版本 | **v0.17.0 (2026.6.19)**,upstream `bb7ff7dc`,**落后上游 434 commits**(`hermes --version`) |
| 运行时 | Python 3.11.15,OpenAI SDK 2.32.0 |
| default 网关 :8642 | `gateway_state: running`,但 **`api_server.state: disconnected`**(`~/.hermes/gateway_state.json`,06-24 03:13) |
| scribe3 网关 :8643 | `gateway_state: running`,**`api_server.state: connected`**(pid 50534,`profiles/scribe3/gateway_state.json`) |
| 模型 | doubao-seed-2.0-pro(火山 ark,`profiles/scribe3/config.yaml:5`) |

> ⚠️ scribe3 的速答/渲染/纪律判官/ingest **全部依赖 :8642**(`llm.py:12`),而它当前报 `disconnected`——需人工确认是否仍可服务(见 §3 R4)。

---

## 1.1 Hermes v0.17.0 核心能力使用清单

> 深度档:**深**(核心依赖)/**中**(在用非核心)/**浅**(配置开但应用未接/仅文档)/**无**(未用)。

### 🧠 核心代理与记忆

| 能力 | 是否使用 | 使用位置 | 使用深度 | 备注 |
|---|---|---|---|---|
| SOUL.md 全局人格定义 | ❌ 否 | `~/.hermes/SOUL.md` | 无 | 内容 = Hermes 出厂默认("You are Hermes Agent…"),scribe3 未定制;主编人格全靠 `app.py:317-340` `_editor_system` 运行时注入 |
| Context Files(分模块上下文) | ❌ 否 | — | 无 | profile 无 context file 配置;`context_file_max_chars: null`;上下文走代码侧动态拼装 |
| 上下文截断阈值(context_truncation_threshold) | ⚠️ 部分 | `profiles/scribe3/config.yaml` compression 段 | 浅 | **该确切键名不存在**;最接近是 `compression.threshold:0.5` + `tool_output.max_bytes:50000` + `file_read_max_chars:100000`。**需人工确认**指哪个 |
| Skills System | ✅ 是 | `scribe3/hermes_skills/scribe-novel-v2/SKILL.md`;`config.yaml:397-398` `external_dirs` | 中(配置)/**待验证**(runtime) | 已注册,但 :8643 网关 skills 快照含 92 个 builtin 包**无 scribe-novel-v2**,快照早于 SKILL.md 最后编辑 → runtime 是否注入无证据(R2) |
| Skills 自动生成(闭合学习回路) | ⚠️ 配置存在 | `SKILL.md:34,46-49`(指示 `skill_manage(action="patch")`) | 浅 | 仅 SKILL.md 文字指令;`skills.write_approval:false`+`guard_agent_created:false`(不另设审批);**runtime 未验证有补丁写入** |
| Skills Hub / agentskills.io | ❌ 否 | — | 无 | 未引入社区技能 |
| Skill Bundles | ❌ 否 | — | 无 | 无 bundle 配置 |
| 技能中心多枢纽接入 | ❌ 否 | — | 无 | — |
| 技能管理器 curator | ⚠️ 默认 | `config.yaml` auxiliary.curator | 浅 | `provider: auto`(跟随主模型),scribe3 未定制;非主动使用 |
| 内存系统三层(会话/持久/用户模型) | ⚠️ 平台开,应用未接 | `config.yaml:371-377` `memory_enabled:true`/`user_profile_enabled:true`/`provider:novel` | 浅 | **全局默认开着,scribe3 代码零 memory 读写**——主编上下文每次从 SurrealDB 现拼(`_editor_system`),未用 Hermes 内存 |
| 内存原子化批量操作 | ❌ 否 | — | 无 | scribe3 不用 Hermes memory |
| FTS5 全文检索记忆召回 | ❌ 否 | — | 无 | scribe3 自有 SurrealDB 向量召回(见文档06),不用 Hermes FTS5 记忆 |
| Honcho 用户建模 | ❌ 否 | `config.yaml:415` `honcho:{}` | 无 | 空配 |
| 会话压缩与摘要时间锚点 | ✅ 是 | `config.yaml:113-120` `compression.enabled:true`/threshold 0.5/target 0.2 | 中 | 平台级,长会话自动压缩;scribe3 被动受益 |
| 内存/技能写入审批开关 | ✅ 设了 | `config.yaml` `memory.write_approval:false`、`skills.write_approval:false` | 中 | 显式关闭(配合 skill_manage 自进化无门) |

### 🤖 多代理与任务调度

| 能力 | 是否使用 | 使用位置 | 使用深度 | 备注 |
|---|---|---|---|---|
| Subagent 并行委托(delegate_task) | ⚠️ 仅文档 | `SKILL.md:33`(第8步) | 浅 | **scribe3 源码零调用**(全仓 grep `delegate_task` 仅命中 SKILL.md);是给主编 agent 的运行时建议,非 app 驱动 |
| 后台异步子代理(background=true)[v0.17] | ⚠️ 仅文档 | `SKILL.md:33` `delegate_task(background=true,…)` | 浅 | 同上;`delegation.orchestrator_enabled:true`/`max_async_children:3`/`subagent_auto_approve:false`,但 runtime 是否触发**需人工确认** |
| 子代理自定义端点池 | ❌ 否 | — | 无 | — |
| 子代理实时活动监视面板 | ❌ 否 | — | 无 | — |
| Programmatic Tool Calling(execute_code) | ❌ 否 | `config.yaml:500` `code_execution.mode:project`(开着) | 无 | 配置开但 scribe3 源码无 execute_code 调用;工具走标准 MCP function_call |
| 看板(Kanban)多代理平台 | ❌ 否 | — | 无 | — |
| 全局单例调度锁 | ⚠️ 默认 | — | 浅 | 平台默认,scribe3 未主动用 |
| 定时任务(Cron) | ✅ 是(**当前失败**) | `profiles/scribe3/cron/jobs.json`「scribe3-体检」每 360 分钟 | 中(配置)/🔴坏(runtime) | `last_status:error`,路径多拼 `profiles/scribe3/scripts/` 前缀 → `Script not found`(R1) |
| 自动化蓝图(Automation Blueprints)[v0.17] | ❌ 否 | — | 无 | 自动化只有那个(坏的)cron |
| Chronos 托管定时(缩容到零)[v0.17] | ❌ 否 | `config.yaml` `cron.provider:''`/`chronos.callback_url:''` | 无 | 用本地 interval cron,非 chronos |
| background notify_on_complete | ❌ 否 | — | 无 | — |

### 🔌 MCP 与工具集成

| 能力 | 是否使用 | 使用位置 | 使用深度 | 备注 |
|---|---|---|---|---|
| MCP Integration(外部工具服务器) | ✅ 是 | `mcp.py:20` FastMCP("scribe3") 19 工具;`config.yaml:575-578` 挂 `run_mcp.sh` | **深(核心)** | scribe3 的 agentic 写作命脉:主编经 :8643 自调 19 个 `s3_` 工具 |
| MCP 工具过滤配置 | ⚠️ 默认 | `config.yaml` `tool_search.enabled:auto` | 浅 | 未定制过滤;19 工具量级未触发过滤需求 |
| MCP 可疑配置拦截 | ✅ 默认开 | `config.yaml` `security.tirith_enabled:true`(fail_open) | 中 | 平台级安全扫描 |
| MCP 工具调用中途确认 [v0.17] | ✅ 是 | `mcp.py:48-59` `_ask`→`ctx.elicit`;`approvals.mode:manual` | **深(核心)** | scribe3 的「写待批」就是此机制:写工具触发 elicitation 弹窗,fail-closed(§4) |
| 回合间动态新增工具 [v0.17] | ❌ 否 | — | 无 | 工具表在 `mcp.py` server 启动时定死,无运行时增删 |
| SurrealDB MCP 服务器接入 | ❌ 否 | — | 无 | scribe3 用**自己的** `mcp.py`(应用层 MCP),非 SurrealDB 官方 DB-MCP(见文档06 §3.1) |
| 官方 Unreal Engine 5.8 MCP [v0.17] | ❌ 否 | — | 无 | 与本项目无关 |
| 图像生成工具(image_generate) | ❌ 否 | — | 无 | scribe3 只**消费**图片输入(`app.py:484-490` input_image),不生成 |
| 图生图编辑 [v0.17] | ❌ 否 | — | 无 | 同上 |

### 📡 消息平台网关

| 能力 | 是否使用 | 使用位置 | 使用深度 | 备注 |
|---|---|---|---|---|
| 钉钉 / 飞书 / Telegram / Discord / Slack / WhatsApp(Baileys/Cloud)/ iMessage / Raft / SimpleX / 微信 | ❌ 全否 | — | 无 | config 各平台段全默认空配,无 token/channel 绑定。**scribe3 唯一入口是自家 FastAPI(:3321)+ :8643 HTTP,不经任何 IM**。这类能力**与本项目定位无关**,非"该用未用" |

### 🖥️ 桌面端与仪表盘

| 能力 | 是否使用 | 使用位置 | 使用深度 | 备注 |
|---|---|---|---|---|
| 桌面应用(v0.17 生产级) | ❌ 否 | — | 无 | scribe3 用自家 React 前端(:3311) |
| 仪表盘档案构建器 [v0.17] | ❌ 否 | `config.yaml` dashboard.* 全空 | 无 | — |
| 多档案管理 + 全局切换器 [v0.17] | ⚠️ 部分 | default + scribe3 两 profile | 浅 | 有两档案,但靠 `hermes -p scribe3` 命令切,非 dashboard 切换器 |
| /model 热切换 | ❌ 否 | — | 无 | scribe3 代码固定模型(`llm.py:31`) |
| /fast 快速模式 | ❌ 否 | — | 无 | — |
| xAI Grok 直调 [v0.17] | ❌ 否 | — | 无 | 用豆包 |
| Voice Mode(TTS/STT) | ❌ 否 | — | 无 | 无语音交互 |
| Langfuse 可观测性 | ❌ 否 | — | 无 | 仅本地文件日志(`config.yaml:507-511`) |

### 🚀 部署与安全

| 能力 | 是否使用 | 使用位置 | 使用深度 | 备注 |
|---|---|---|---|---|
| Docker 部署 | ❌ 否 | — | 无 | 无 Dockerfile(见文档03 P12) |
| SSH/Daytona/Modal 远程执行 | ❌ 否 | — | 无 | 本地执行 |
| Nix flake 安装 | ⚠️ 需人工确认 | — | — | Hermes 自身安装方式,scribe3 不涉及 |
| 网关中继(0-3 阶段)[v0.17] | ❌ 否 | — | 无 | — |
| 托管作用域(管理员根目录全局配置)[v0.17] | ❌ 否 | — | 无 | — |
| 单网关进程复用多档案 [v0.17] | ❌ 否 | — | 无 | scribe3 用**独立进程** :8643(`--replace`) |
| Atropos RL 强化反馈 | ❌ 否 | — | 无 | — |
| OpenTelemetry 遥测 | ❌ 否 | — | 无 | — |

---

## 1.2 使用深度总评

**scribe3 把 Hermes 当作"agentic 写作的 MCP 宿主 + LLM 网关",用深了 2 条线、用浅了 3 条线、放弃了其余整片平台能力——这是恰当的克制,但 3 条"浅线"里藏着真问题。**

- **用得深(核心依赖,2 条)**:① **MCP 集成 + elicitation 写门控**——19 个 `s3_` 工具挂 :8643,主编自调查限知数据,写操作经 `ctx.elicit` 待批,这是 scribe3 区别于"裸 LLM 写作"的命脉(`mcp.py`)。② **双网关 LLM 调用**——:8642 速答/渲染、:8643 agentic Responses,职责清晰(`llm.py`)。
- **用得浅(配置开/仅文档,藏雷,3 条)**:① **Skills + skill_manage 自进化**——SKILL.md 写得很完整,但 runtime 未确认加载(R2)。② **Cron 体检**——配了,但路径 bug 持续失败(R1)。③ **delegate_task 后台子代理**——只在 SKILL.md 出现,代码零驱动,是否被主编触发未知。
- **放弃(与定位无关或暂不需要)**:memory 三层/honcho/IM 网关/dashboard/voice/chronos/blueprints/programmatic tool calling/observability——对"单机单用户小说写作工具"是合理取舍,**不建议盲目接入**。其中 **memory 三层是平台开着、应用没接**(`memory_enabled:true` 但 scribe3 零 memory 读写),值得评估是否接(§5)。

> **判定:Hermes 使用深度 = 核心精准、外围克制,但运行时健康度有缺口**。设计选型对(MCP+elicitation 是 v0.17 最该用的能力,scribe3 用对了),但 cron/skill/网关三处 runtime 状态需要修复与验证才能说"真的在工作"。

---

## 1.3 Runtime 问题清单(取证发现的真问题,优先修)

| 编号 | 级别 | 问题 | 证据 | 影响 |
|---|---|---|---|---|
| **R1** | 🔴 高 | **体检 cron 持续失败** | `profiles/scribe3/cron/jobs.json` `last_status:error`,`last_error:"Script not found: …/profiles/scribe3/scripts/scribe3_qc.sh"`——脚本实际在 `~/.hermes/scripts/`,cron 解析多拼了 `profiles/scribe3/` 段 | 伏笔超期/因果连贯的护城河告警 06-24 起不生效;下次 12:34 仍失败 |
| **R2** | 🟡 中 | **自进化 skill 未确认加载** | `scribe-novel-v2` 不在 :8643 skills 快照(92 builtin 中 grep=0),`.bundled_manifest` 无 scribe;snapshot 时间戳早于 SKILL.md 最后编辑 | "主编自进化技能"回路属"已配未验证";SKILL.md 的写作纪律可能没真正注入主编 prompt |
| **R3** | 🟡 中 | **agentic 端写工具实际写不进** | 非交互上下文 elicitation fail-closed(`mcp.py:57-58`),`AGENTIC_SETUP.md:53` + `app.py:374` 自承 | 主编在 :8643 只能读、不能落库;"主编自调写工具进化世界"当前是断的,只有 REST 直编 + 草稿/ingest 豁免能写 |
| **R4** | 🟡 中 | **default :8642 报 disconnected** | `~/.hermes/gateway_state.json` `api_server.state:disconnected`(06-24 03:13) | 速答/渲染/judge/ingest 全依赖 :8642,**需人工确认是否仍可服务**(可能已掉) |
| **R5** | ⚪ 低 | **明文 ark api_key 落盘** | `~/.hermes/config.yaml` 与 `profiles/scribe3/config.yaml` 第 4 行 `model.api_key` 明文(值已 redact 未打印) | 凭证明文落盘 2 处;`security.redact_secrets:true` 只管日志不管配置文件 |
| **R6** | ⚪ 低 | **Hermes 落后上游 434 commits** | `hermes --version` | 记忆已记"不盲升"(0.17.0→新版需评估破坏性),非紧急但需规划 |

---

## 1.4 Hermes Skills 补全计划

> 现状:仅 1 个 skill(`scribe-novel-v2`,且 runtime 加载待验证 R2)。下列为"建议立即新建"的 skill 文档(每个把一段反复推理沉淀成可复用流程,减少主编每次重推)。

| Skill 名称 | 触发场景 | 需要的工具/MCP | 预期节省的推理次数 |
|---|---|---|---|
| `scribe-limited-pov-guard`(限知守门) | 主编每次动稿前,自检"本段是否只用了 focalizer 知道的事实" | `s3_project_frame` + `s3_find_leaks` | 每章 2-3 次(把"取帧→比对→改写"流程固化) |
| `scribe-foreshadow-tracker`(伏笔台账) | 开新章/收尾时检查 open 伏笔是否该回收 | `s3_list_promises` + `s3_advance_promise` | 每章 1-2 次(替代主编每次重新通读判断超期) |
| `scribe-voice-consistency`(声音一致) | 写某角色对白前,拉取其 4 类声音样本对齐 | `s3_*`(需新增 `s3_list_voice`,见文档06)+ voice 时间门 | 每场景 1 次(防 OOC,固化"取声音样本→对齐语域") |
| `scribe-ingest-verify`(回写校验) | 存稿后,校验 ingest 抽取的 learned/did 是否含幻觉角色 | `s3_get_chapter` + `s3_project_frame` | 每章 1 次(把文档03 P18 幻觉角色校验固化为流程) |
| `scribe-revision-pass`(修订工序) | 章成后的确定性 QC + 纪律判官两道 pass | `s3_qc_chapter` + `s3_discipline_check` + `s3_find_leaks` | 每章 1 次(固化"三道闸"顺序,避免漏跑) |

> 收益逻辑:这 5 个 skill 把目前散在 SKILL.md 一篇里的"写一章 9 步环"拆成**可独立触发的工序卡**,主编在对应场景直接调用对应 skill,而非每次从整篇 SKILL.md 重新推导该做什么——这正是 v0.17 Skills System 的设计意图。**前提是先修复 R2(确认 skill 真被加载)**。

---

## 1.5 Hermes 侧改进建议(优先级)

1. **修 R1 cron 路径**(立即,10 分钟):把 `jobs.json` 的 script 路径改为绝对路径 `~/.hermes/scripts/scribe3_qc.sh`,或排查 cron 为何多拼 profile 段。恢复护城河告警。
2. **验 R2 skill 加载**(立即):起一个 :8643 会话,检查 system prompt 是否含 `scribe-novel-v2` 内容;若无,排查 `external_dirs` 是否需要 `hermes` 重载/重启网关。这是"自进化"成立的前提。
3. **查 R4 :8642 健康**(立即):确认 default 网关是否真可服务;若掉了,scribe3 全部 LLM 功能(除 agentic)受影响。
4. **R3 设计澄清**(短期):明确"agentic 主编是否应该能写世界"。当前 fail-closed 让 agentic 写工具形同摆设——要么提供"交互式批准通道"让主编写能落地,要么文档明确"agentic 只读、写一律走 REST 直编",消除"配了写工具却写不进"的认知错位。
5. **评估 memory 三层是否接入**(短期):平台 `memory_enabled:true` 开着但 scribe3 没接。可评估把"主编对某书的跨会话记忆"(如写作风格偏好、已确立的隐性设定)放进 Hermes memory,减少每次 `_editor_system` 全量重拼。**需权衡**:scribe3 的"真相唯一在 SurrealDB"原则下,Hermes memory 只宜存"过程性偏好"不宜存"世界事实",避免双真相源。
6. **R5 凭证外置**(短期):ark key 移环境变量,config 不落明文。
7. **Skills 补全**(短期,见 §1.4):先修 R2,再逐个落地 5 个工序 skill。
8. **R6 升级评估**(中期):跟踪 Hermes 新版破坏性变更,规划 0.17.0 → 新版的升级窗口(记忆已记"不盲升")。
