# Scribe3 Hermes Agent 全量官方证据库与能力利用审计设计

**版本：** 1.0  
**日期：** 2026-07-19  
**状态：** 已确认方案 C，待实施计划  
**第一性目标：** 只吸收能够提高小说创作质量、上下文组织质量、工作流可靠性或评价可信度的 Hermes 能力；不因 Hermes 自带某项能力就接入。

**关联规格：** `2026-07-19-scribe3-hermes-surrealdb-latest-upgrade-design.md`。官方证据库先冻结升级前后合同；升级规格负责运行时变更、数据安全、兼容验证和回滚。两者必须按同一固定版本快照执行。

## 1. 背景与结论

Scribe3 已经把 Hermes Agent 用作模型执行、Responses/Runs、MCP 工具、审批、会话连续、技能和运行时网关，但过去的能力判断同时受到三类证据漂移影响：

1. 本地缓存只是 2026-07-09 的官网快照，共 360 页；2026-07-19 官网 Sitemap 已有 365 页。
2. 本机二进制报告为 `Hermes Agent v0.18.2 (2026.7.7.2)`，同时报告上游已有大量新提交；官网最新文档不能直接当成本机合同。
3. 官方仓库除官网页面外还有核心工程文档、插件文档、协议说明、发布资料以及大量官方技能文档。只抓官网会漏证据，只抓仓库主干又会把未来能力误当成当前能力。

本设计采用已确认的方案 C：建立**全量、分层、版本化的 Hermes 官方证据库**，再把每项官方能力与本机运行时、Scribe3 当前代码路径和 Creative Context OS 第一性约束逐项对照。

最终产物不是“功能清单”，而是能够回答以下问题的证据系统：

- 这项能力在哪份官方证据中出现？
- 它属于当前发布版、官方最新主干，还是仅属于技能/示例语料？
- 本机 v0.18.2 是否真实支持，真实事件和参数是什么？
- Scribe3 是否已经配置、是否有业务消费者、是否端到端生效？
- 它如何改善一次具体的小说创作决策或上下文闭环？
- 接入后是否制造第二套事实、记忆、会话、任务或上下文权威？
- 应当采纳、局部借鉴、暂缓还是明确拒绝？如何验证？

## 2. 不可违背的架构边界

### 2.1 权威边界

- 当前 SurrealDB 和 Scribe3 现有领域模型继续是小说业务数据的唯一持久化权威。
- `CreativeContextEngine` 是业务上下文规划、检索、协调、装配和验证的唯一内核。
- Hermes 是模型执行与工具编排平面，不拥有 canon、正文、参考作品指纹、质量合同、作者审美偏好或上下文 Manifest。
- Hermes session、memory、context engine、goal、trajectory 和 skill 不得成为平行业务数据库。
- Hermes 官方文档缓存是工程证据，不是运行时权威，也不进入小说业务召回空间。

### 2.2 质量贡献门

每一项候选能力必须登记上下文贡献合同：

`能力 → 合法消费者 → 改善的创作决策 → 输入/输出证据 → 质量假设 → 对照实验 → 副作用 → 采用决定`

没有合法消费者、不能提出质量假设、无法设计验证或只增加界面复杂度的能力，不进入核心产品。

### 2.3 版本事实优先级

当不同证据冲突时，按以下顺序裁决：

1. 本机真实 API、CLI、SSE、工具发现和端到端行为；
2. 本机实际安装版本对应的官方发布标签和合同；
3. 官方最新主干源码中的文档与合同；
4. 官方文档网站当前页面；
5. 官方技能、指南和示例；
6. 旧项目文档和历史审计结论。

低层证据可以提出候选能力，不能覆盖高层运行时事实。旧审计只能作为回归种子，不能作为当前验证。

## 3. 当前事实基线

### 3.1 本机版本

必须只用二进制命令确定版本。本轮已记录：

```text
Hermes Agent v0.18.2 (2026.7.7.2) · upstream 36f2a966
Install directory: /Users/miaoma/.hermes/hermes-agent
Install method: git
Python: 3.11.15
OpenAI SDK: 2.24.0
```

本地安装目录的 Git HEAD 另为 `bd740f203b44237dbc5c27a2de4d86ef32af4dde`，工作区为 dirty。`upstream` 字段会随远端 fetch 更新，表示已知上游锚而不是当前安装源码身份；它在本轮首次探测时曾显示旧的 `ef9e0c98`，执行 `hermes update --check` 拉取远端后变为 `36f2a966`。因此版本号、上游锚和本地HEAD必须作为三个独立观测值保存，能力合同仍需通过运行时探测确认。

缓存与审计阶段不得执行 `hermes update`，避免一边取证一边改变被审计对象。

### 3.2 现有缓存

现有目录：`docs/external/hermes-agent-docs/`。

- 大小约 7.6 MB；
- 旧 Sitemap URL 360 个，成功 360，失败 0；
- 360 个清单文件均存在，来源 URL 一致；
- 未发现相同正文哈希；
- `/docs/search` 是动态搜索壳，正文异常短，不能作为有效内容页；
- 当前 Sitemap 新增 5 个 URL，旧缓存没有覆盖。

现有抓取器正确使用返回结果自身的 `result.url`，避免了按请求顺序错误配对的已知批抓陷阱；但还缺少版本快照、内容哈希、软 404、标题语义、MIME、最终 URL、重定向和跨版本完整性验证。

### 3.3 官方仓库规模快照

2026-07-19 只读发现结果：

- 官方主干快照 SHA：`36f2a966c7f9f69987494b867c3dcf96b69a5766`；
- 主干约 1436 个 Markdown/MDX 文件，约 19.1 MB；
- `v2026.7.7.2` 发布标签落点：`9de9c25f620ff7f1ce0fd5457d596052d5159596`；
- 发布版约 1415 个 Markdown/MDX 文件，约 18.8 MB；
- 发布版到主干至少有 21 个文档文件新增、91 个文档文件变化。

这些数字属于本次发现快照。实施时必须重新发现并把实际 SHA、数量和字节数写入 Manifest，不能硬编码为永恒事实。

## 4. “全部官方文档”的精确定义

### 4.1 官方来源白名单

只允许以下权威来源进入官方证据库：

1. `https://hermes-agent.nousresearch.com/docs/` 及其官方 Sitemap；
2. `https://github.com/NousResearch/hermes-agent` 官方仓库；
3. 该仓库的官方 tags、releases 和 Git objects/API；
4. 官方文档直接链接、且归属于同一官方仓库的附件，如 PDF。

第三方博客、论坛、转载、搜索摘要、个人仓库和旧 `vendor/` 快照不进入官方缓存。它们若未来用于外部实践调研，必须进入独立的第三方证据空间，不能标记为 Hermes 官方合同。

### 4.2 纳入内容

方案 C 包含：

- 官网 Sitemap 可发现的全部文档页面；
- 官方仓库全部 `.md`、`.mdx`、`.rst`、`.adoc` 文档；
- `docs/` 下的 PDF 和其他明确文档附件；
- 根目录 README、CONTRIBUTING、SECURITY、AGENTS、变更与迁移说明；
- `website/docs/` 英文源文档；
- 官方中文本地化文档，保留其语言和源路径；
- `skills/` 与 `optional-skills/` 下全部技能正文和引用资料；
- 插件、Gateway、Desktop、TUI、MCP 和其他子系统的 README/设计文档；
- 官方 release 元数据、发布说明和标签指向；
- 与公开能力合同直接相关的配置示例、JSON Schema、OpenAPI、manifest schema 和命令参考。

### 4.3 不纳入内容

- 完整业务源代码镜像；
- 测试夹具、构建产物、依赖目录、二进制可执行文件；
- issues、PR 评论和讨论区；
- 含 secret、token、凭证或本机配置值的内容；
- 仅因为扩展名是文本而存在、但不具备文档或合同语义的文件。

当文档不足以确定运行时合同，可以在审计报告中引用官方源码的文件、符号、提交 SHA 和行锚，但不把整个源码仓库复制进文档缓存。

## 5. 证据库分层

### 5.1 `website-current`

保存抓取时官方 Sitemap 的全部页面及抓取元数据。它回答“官网现在怎么说”，不自动代表本机支持。

### 5.2 `release-v2026.7.7.2`

保存当前二进制报告版本对应发布标签的全量官方文档。它是当前版本文档合同的主要候选，但仍低于真实运行时。

### 5.3 `main-current`

保存实施时发现的官方主干固定 SHA 全量文档。目录名必须包含完整或足够唯一的 SHA，禁止使用会漂移的裸 `main/` 作为唯一快照身份。

### 5.4 `skills-corpus`

技能文档同时属于发布/主干快照，但在索引中单独标记：

- `procedural_knowledge=true`；
- `runtime_contract=false`，除非另有核心文档或运行时证据；
- 可用于发现写作方法、工具编排和评测实践；
- 不得作为 canon、作者偏好或作品参考内容自动注入生成上下文。

### 5.5 `runtime-observed`

只保存去敏后的实际观测：

- `hermes --version`；
- `hermes --help` 与相关子命令帮助；
- 三个 profile 的 `/health/detailed`、`/v1/capabilities`；
- 工具集名称和数量，不保存凭证或完整敏感配置；
- Responses/Runs/SSE/Approval 的去敏契约样本；
- Memory Provider、Hooks、Sessions 等生命周期探针结果；
- 实际模型与供应商证明；
- 抓取和探测时间、进程启动版本与服务地址类别。

运行时样本不得包含用户正文、完整提示词、API key、Authorization header、`.env`、cookie 或真实隐私数据。

### 5.6 `release-diff`

生成以下差异：

- 官网旧快照到新快照；
- 当前发布标签到最新主干；
- 本机已观测能力到官网/主干声明能力；
- 当前 Scribe3 使用面到官方可用面。

每个差异项标记 `added`、`changed`、`removed`、`renamed`、`future_only`、`runtime_confirmed` 或 `runtime_contradicted`。

## 6. 目录与文件设计

沿用现有根目录，避免制造第二个 Hermes 文档缓存：

```text
docs/external/hermes-agent-docs/
  README.md
  manifests/
    discovery-<timestamp>.json
    website-<timestamp>.json
    upstream-v2026.7.7.2.json
    upstream-main-<sha>.json
    runtime-observed-<timestamp>.json
    integrity-<timestamp>.json
  snapshots/
    website/<timestamp>/pages/...
    upstream/v2026.7.7.2/...
    upstream/main-<sha>/...
  reports/
    coverage-<timestamp>.md
    release-diff-<timestamp>.md
    capability-matrix-<timestamp>.md
  current.json
  urls.txt
  _crawl_hermes_agent_docs.py
```

设计原则：

- 每个快照不可变；刷新产生新快照，不覆盖历史证据。
- `current.json` 只保存当前推荐快照指针和哈希，不使用易失真的目录软链接。
- 两个 Git 快照保留原始逻辑路径，支持 `rg`、CodeGraph外的全文检索和人工检查。
- Git 自身负责跨快照内容压缩；不引入难以人工浏览的哈希对象仓库。
- 旧 `pages/` 在迁移验收前保留；新快照验证通过后再决定兼容索引，不直接删除。
- `__pycache__` 等可重建产物不属于缓存交付物。

## 7. Manifest 合同

### 7.1 快照级字段

每个快照 Manifest 至少包含：

- `snapshot_id`；
- `source_kind`：`website|release|main|runtime`；
- `source_origin`；
- `requested_ref`；
- `resolved_sha` 或 `release_tag`；
- `fetched_at`；
- `crawler_version`；
- `document_count`；
- `total_bytes`；
- `success_count`、`failed_count`、`excluded_count`；
- `manifest_sha256`；
- `completeness_status`；
- `previous_snapshot_id`；
- `notes`。

### 7.2 文档级字段

每个文档至少包含：

- `document_id`；
- `requested_url`；
- `final_url`；
- `repo_path`；
- `output_path`；
- `language`；
- `category`；
- `mime_type`；
- `http_status`；
- `title`、`h1`；
- `content_sha256`；
- `byte_length`、`text_length`；
- `source_commit` 或 `website_snapshot_id`；
- `is_skill`、`is_runtime_contract`；
- `semantic_status`；
- `excluded_reason` 或 `error`；
- `supersedes_document_id`。

### 7.3 能力证据字段

能力矩阵中的每项能力至少保存：

- `capability_id`、`name`、`category`；
- `official_evidence_refs`；
- `documented_in_release`、`documented_in_main`；
- `runtime_advertised`、`runtime_probed`；
- `current_scribe_config_refs`、`current_scribe_consumer_refs`；
- `current_state`：`used|partial|configured_only|unused|incompatible|unknown`；
- `first_principle_contribution`；
- `authority_risk`；
- `quality_hypothesis`；
- `decision`：`adopt|optimize|borrow_design|defer|reject`；
- `verification_plan`；
- `rollback_boundary`；
- `evidence_confidence`。

## 8. 抓取与发现流程

### 8.1 官网发现

1. 请求官方 Sitemap；
2. 校验 XML、host、路径前缀和 URL 唯一性；
3. 保存原始 URL 清单和 Sitemap 哈希；
4. 对动态目录页、搜索页和普通正文页分类；
5. 分批抓取，每个返回结果按 `result.url` 和 `final_url` 绑定，绝不按数组位置配对；
6. 主选择器失败或正文过短时，用 `main` 选择器回退；
7. 回退仍异常时记录失败，不把导航壳当正文；
8. 对 429/5xx 做有限、带抖动重试；
9. 每批增量写 Manifest，进程中断后可恢复；
10. 全部完成后执行集合相等和语义完整性检查。

### 8.2 官方仓库发现

1. 通过官方 Git ref 解析发布标签和主干为不可变 commit SHA；
2. 获取对应 Git tree，确认 `truncated=false`；
3. 按明确纳入规则筛选文档和合同附件；
4. 下载原始 blob，不抓 GitHub HTML 展示页；
5. 保留仓库原始路径、文件字节和 blob SHA；
6. 对 LFS 指针、子模块、超大附件单独标记；
7. 对相同路径不同版本保存两份逻辑快照；
8. 生成发布版与主干的新增、修改、删除清单。

### 8.3 限流与恢复

- 遵守官方服务响应头和重试提示；
- 并发数配置化，默认保守；
- 不设置“失败也无限重试”；
- 已通过内容哈希验证的文件支持断点续传；
- 单页失败不终止全批，但最终完整性状态必须为失败；
- 没有失败清单和重试记录的批次不能验收。

## 9. 完整性与真实性门

### G0 来源门

所有条目必须来自白名单官方来源。发生跨域重定向时默认失败，除非是官方仓库明确引用且纳入白名单的附件。

### G1 集合覆盖门

官网：`Sitemap URL 集合 = 成功文档集合 ∪ 明确排除集合`，且失败集合为空才可标记完整。

仓库：`筛选规则命中文档集合 = 成功保存集合 ∪ 明确排除集合`，Git tree 不得截断。

### G2 内容身份门

每份文件必须有 SHA-256；Manifest 自身也计算稳定哈希。相同 URL 内容变化必须产生新文档身份。

### G3 语义门

检查：

- 标题/H1 与 URL 路径明显不符；
- 正文过短；
- 软 404、登录页、错误页、反爬页；
- 大量导航重复、正文为空；
- 不同 URL 正文完全相同；
- Markdown 只有链接壳；
- MIME 与扩展名不符；
- 内部链接指向未缓存官方文档。

动态搜索页可以保存为 `navigation_only`，但不计入有效正文页。

### G4 版本隔离门

任何能力结论必须明确来自 release、main、website 还是 runtime。没有本机探测证明的主干能力只能标为 `future_only` 或 `unverified`。

### G5 去敏门

缓存和报告不得出现 secret、token、Authorization、`.env` 内容、用户正文或真实敏感提示词。发现疑似 secret 时中止对应文件入库并报告路径，不输出其值。

### G6 可复现门

相同固定 ref、相同筛选规则再次执行，应得到相同文档集合和内容哈希；官网随时间变化则产生新快照，不覆盖旧快照。

## 10. 全量能力审计方法

### 10.1 能力域

能力矩阵至少覆盖：

1. CLI、配置、profiles、provider、credential pool、fallback；
2. Chat Completions、Responses、Runs、SSE、Approval、停止和恢复；
3. Sessions、存储、检查点、trajectory、usage；
4. Prompt assembly、context files、context compression、prompt caching；
5. Context Engine Plugin、Memory Provider、Honcho 等记忆机制；
6. MCP、toolsets、工具过滤、Tool Search、工具审批；
7. Skills、plugins、plugin LLM access、curator；
8. Hooks、cron、batch、persistent goals、delegation、Mixture of Agents；
9. Gateway、API Server、multi-profile、Dashboard/observability；
10. security、backup、doctor、升级和兼容性；
11. 与创作相关的官方技能、反低质文本、创意发散、研究和评测实践。

### 10.2 四层验证

每项能力依次经过：

1. **文档层：** 官方如何定义；
2. **版本层：** 当前发布版和主干分别是否包含；
3. **运行时层：** 本机是否暴露、参数与事件是否一致；
4. **业务层：** Scribe3 是否有真实消费者，是否改善第一性目标。

仅“配置文件出现”不算已用；仅“Capabilities 声明”不算端到端可用；仅“测试通过”不算创作质量得到改善。

### 10.3 当前代码映射

使用 CodeGraph 先定位并追踪：

- `scribe3/hermes_runtime.py`；
- `scribe3/llm.py`；
- `scribe3/app.py` 的 Responses/Runs/Approval 路径；
- `scribe3/mcp.py` 与读写工具集；
- `scribe3/hermes_plugins/scribe3-memory/`；
- `scribe3/context_*` 与 `_assemble_write_instructions`；
- `scribe3/scripts/provision_hermes.py`、smoke 和备份脚本；
- 前端 Runs 恢复、审批和 trace 消费路径；
- 对应测试、规格和历史审计。

每项能力区分：

- 配置存在；
- 运行时已加载；
- 代码已调用；
- UI/业务已消费；
- 真人任务已验证；
- 质量提升已通过对照实验。

## 11. 与 Creative Context OS 的采用原则

### 11.1 Context Engine Plugin

可以参考或用于传递 Scribe3 已编译的 `ContextEnvelope`，但不得让 Hermes 自己形成第二套 canon 检索、时态协调、POV裁剪或质量上下文权威。

候选最优边界：

- Scribe3 生成 `ContextRequest → Policy → Manifest → Envelope`；
- Hermes 只接收已验证 Envelope 和最小任务指令；
- Hermes 插件若参与，只负责生命周期适配、token窗口管理和回传观测；
- 插件不直接写业务数据库，不自行决定必需slot，不覆盖 Scribe3 的排除原因。

是否真正使用插件必须与“继续直接通过 Responses/Runs 传 Envelope”做对照；如果插件只增加一层不可观测封装，则拒绝接入。

### 11.2 Memory Provider

允许保存会话连续、工作摘要和经过授权的作者经验，不允许保存剧情事实副本。

必须验证当前 `Scribe3MemoryProvider` 的：

- 实际加载；
- `initialize`；
- `prefetch`；
- `sync_turn`；
- `on_pre_compress`；
- `on_session_end`；
- 只读工具 schema；
- 故障降级和事件可观测性。

当前 best-effort 静默吞错策略要审查：它可以保护主流程，但如果没有计数、trace和告警，会把“记忆长期未工作”伪装为正常。

### 11.3 Prompt assembly 与 compression

- 稳定身份、业务协议、动态 Envelope 和任务指令分层；
- canon、POV、时态、硬约束和质量合同不得交给通用摘要器任意压缩；
- Hermes 的会话压缩只处理会话历史，不能替代 Scribe3 工作摘要和 Manifest；
- 压缩前后必须记录来源覆盖变化；
- 如果必需上下文因压缩丢失，应阻断或重新编译，而不是静默继续。

### 11.4 Hooks 与 trajectory

优先审查其作为观测和评测基础设施的价值：

- 捕获运行开始、模型切换、工具调用、审批、压缩和结束；
- 绑定 `request_id + manifest_id + actual_input_hash`；
- 形成可重放的去敏任务轨迹；
- 为上下文消融、失败分类和质量回归提供数据。

Hooks 不得自动写 canon；trajectory 不得保存未去敏正文或隐式推理内容。

### 11.5 Tool Search

当前读/写 profile 约有 32/56 个工具，存在工具 schema token 成本。Tool Search 是候选优化，但不能仅凭官方宣传启用。

必须比较：

- 固定工具面 token；
- 冷工具额外模型轮次；
- 工具发现成功率；
- 选错工具率；
- 写审批工具的可发现性；
- 延迟和费用；
- DeepSeek 对工具检索桥的实际表现。

只有写作和主编真实任务在成功率不下降的前提下明显节省上下文，才允许灰度启用。

### 11.6 Batch、Goals、Delegation 与 MoA

这些能力只能作为执行策略候选：

- Scribe3 作业、章节状态、质量快照和审批仍是业务权威；
- Persistent Goal 不能替代作品目标、北极星或章节目的合同；
- Batch 可用于无状态或冻结快照任务，不能跳过持久化队列和重试语义；
- Delegation 可用于独立证据提取、反证或候选审阅，但输入必须来自隔离的 Manifest；
- MoA 只有在盲评证明质量收益、成本可控且不破坏生成/评价隔离时才考虑；默认不启用。

### 11.7 Skills

官方技能只提供程序性方法，不拥有作品内容。候选价值包括：

- 创意发散和反固着；
- 人类化与反低质文本模式；
- 研究、资料处理和证据组织；
- 评测、反证和复盘方法。

任何技能进入 Scribe3 前必须提炼为版本化、可测试的仓内能力，并声明使用场景、禁用场景和质量假设；不能运行时从最新 Hub 静默漂移。

### 11.8 Provider 与 fallback

每次质量关键任务必须记录实际 provider、model、usage和fallback历史。

- 官方 DeepSeek 策略与“模型名称包含 DeepSeek”不是同一件事；
- 非官方端点、其他模型或fallback一旦发生，必须显式标记策略不符合；
- 生成和评价的模型策略分别配置；
- fallback 提高可用性，但不能让不等价模型输出静默进入质量验收；
- 对严格任务可以排队等待官方 DeepSeek，而不是自动换模型。

## 12. 审计输出

实施后至少交付：

1. 全量官方证据缓存；
2. 抓取与刷新脚本；
3. URL、Git tree、文件和哈希 Manifest；
4. 完整性报告；
5. 发布版/主干/官网差异报告；
6. Hermes 全能力矩阵；
7. Scribe3 当前使用、部分使用、只配置未消费、未使用和不兼容清单；
8. 按第一性目标排序的优化建议；
9. 每项建议的收益假设、改动边界、验证和回滚；
10. 对 Creative Context OS 3.0 规格的必要修订提案。

审计结论不得使用“全部支持”“最佳使用”之类总括表述，除非每项能力都有对应证据。未完成真人业务质量验证的能力只能标记工程可用或待验收。

## 13. 实施阶段

### 阶段 A：冻结基线

- 保存当前 Git 状态；
- 记录旧缓存摘要；
- 用二进制记录 Hermes 版本；
- 记录官方 refs 和当前 Sitemap；
- 证据缓存阶段不修改 Hermes 安装、不重启服务；运行时升级进入关联升级规格后单独执行。

### 阶段 B：重构抓取器

- 把现有单一网站抓取器扩展为多来源、可恢复、可校验的证据抓取器；
- 先写失败测试，再实现 URL 配对、软404、哈希、Manifest和Git tree下载；
- 保留现有脚本入口兼容性或提供明确迁移命令。

### 阶段 C：生成三套固定快照

- 官网当前快照；
- v2026.7.7.2 发布版快照；
- 官方主干固定 SHA 快照；
- 生成技能分类和语言分类索引。

### 阶段 D：完整性验收

- 执行 G0-G6；
- 修复全部可修复抓取问题；
- 无法抓取项保留证据并使总状态失败，不假绿。

### 阶段 E：代码与运行时映射

- 用 CodeGraph 映射当前集成；
- 用只读运行时探针验证能力；
- 对 Responses/Runs/SSE/Approval/Memory 生命周期做去敏契约测试；
- 不做业务代码修改。

### 阶段 F：第一性能力审计

- 完成全能力矩阵；
- 重新审查历史采纳和否决结论；
- 把“有功能”转化为“是否改善上下文和小说质量”；
- 输出按 P0/P1/P2 排序的落地建议。

### 阶段 G：规格深化

- 只把证据充分、边界清晰的结论合入 Creative Context OS 3.0；
- 需要代码实现的部分另写实施计划；
- 未经确认不执行 Hermes update、不部署新插件、不改变 provider、不启动新增服务。

## 14. 测试设计

### 14.1 单元测试

- URL 规范化、去重和 host 白名单；
- URL 到输出路径映射；
- 请求URL与返回URL绑定；
- Git ref 固定化；
- 文件筛选和分类；
- 标题/H1提取；
- 正文规范化与 SHA-256；
- 软404、短页和动态壳识别；
- Manifest稳定序列化；
- secret模式拦截；
- 版本差异分类。

### 14.2 集成测试

- 官网小样本：普通页、目录页、动态搜索页、重定向页；
- GitHub小样本：Markdown、MDX、PDF、技能引用、中文文档；
- 模拟 429、5xx、超时和中断恢复；
- 模拟批量结果乱序，证明不会串页；
- 固定 ref 两次运行哈希一致。

### 14.3 全量验收

- 当前 Sitemap 全覆盖；
- 两个 Git tree 全覆盖；
- 零未解释失败；
- 零来源错配；
- 零疑似 secret 入库；
- 重复和异常短文档全部解释；
- Manifest 可重建每个逻辑快照；
- 能力矩阵每项至少有一条官方证据和一条当前代码/运行时判断。

## 15. Git 与交付边界

- 本设计规格单独提交。
- 后续缓存实施使用现有分支，不创建额外分支，除非用户另行要求。
- 现有未跟踪的 `cache_surrealdb_docs.py` 和 `surrealdb-docs-cache/` 属于用户数据，完全不触碰、不暂存、不提交。
- Hermes 缓存、脚本、Manifest和审计报告在实施验收后作为一个或多个有意图的提交交付。
- 不执行 push，除非用户明确要求。
- 大体积缓存提交前先报告实际文件数、工作区大小和 Git 增量。

## 16. 完成定义

只有同时满足以下条件，才能称为“已缓存并全量参考”：

1. 官网、当前发布标签和主干固定 SHA 三类证据均已缓存；
2. 官方技能语料已单独分类但没有被误当运行时合同；
3. Manifest、哈希、集合覆盖和语义检查全部通过；
4. 本机能力与最新能力已明确分离；
5. 当前 Scribe3 每条 Hermes 使用路径已映射到代码和真实运行时；
6. 全能力矩阵没有未解释空项；
7. 所有采用建议都能说明如何改善上下文或小说质量；
8. 所有权威冲突和双重状态风险都有明确处理；
9. 未经真人创作质量对照验证的能力没有被宣称为质量提升已成立；
10. Creative Context OS 的修订建议与现有 SurrealDB/领域模型唯一权威保持一致。

达到以上定义，只表示文档证据和设计审计闭环。后续功能实现仍须经过测试、运行时验证、五万字工作流和业务质量验收，不能把“文档审计完成”替代为“小说质量目标已实现”。
