# Scribe3 Creative Context OS 与创作质量系统设计

**版本：** 3.0（以小说质量为第一性目标、以上下文组织为核心机制的深化版）

**日期：** 2026-07-19

**状态：** 等待作者复核；未进入实现

**权威性：** 本文件取代同路径1.0和2.0版本，作为后续实施计划、代码、测试和验收的唯一产品规格。

## 1. 第一性目标与成功定义

Scribe3 的第一性目标不是“生成更多文字”“检查更多问题”或“把所有字段填满”，而是：

> 在不削弱作者创作主权、作品独特性和写作心流的前提下，持续提高作品实现作者意图、产生目标阅读体验并维持长篇完整性的概率。

因此，系统优化的不是单一分数，而是六个不可互相替代的结果：

1. **意图实现：** 作品是否实现本书质量合同中的核心承诺、主题边界与阅读体验。
2. **读者效果：** 真人读者是否理解、投入、感受到目标情绪并愿意继续阅读。
3. **长篇完整性：** 事实、因果、人物、关系、时间、POV、伏笔和结构是否在五万字以上仍成立。
4. **艺术有效性：** 场景、语言、声音、主题、潜台词和形式选择是否必要且有效。
5. **作品独特性：** 参考作品提供可迁移机制，但不把作品压成参考对象或通用AI文本的复制品。
6. **作者主权与负担：** 作者能理解、质疑、拒绝、撤销所有机器建议，且反馈量不会淹没创作本身。

任何方案只要显著提高一项却破坏另一项，都不能称为最优。例如：更接近参考作品却降低原创性、发现更多问题却让作者无法继续写、逻辑全绿却失去情绪和声音，都属于失败。

系统能够提高写出高质量小说的概率，但不能保证任何作品必然成为名著或商业成功。

### 1.1 从第一性目标到核心机制

小说由持续数月、数万次相互依赖的创作决策构成。任何一次生成、人工写作、评价或修订，质量都受到当时可用信息的制约。因此本系统采用以下因果假设：

`小说质量提升概率 = 上下文适配度 × 创作决策质量 × 反馈学习能力 × 作者审美判断`

其中，上下文适配度是系统最可工程化、也最能贯穿全部能力的杠杆。Scribe3的核心产品形态因此深化为 **Creative Context OS**：在每一次创作决策发生前，提供正确、充分、及时、可追溯、不过载且不限制创造性的上下文；在决策之后记录结果、评价和作者选择，用于改进后续上下文。

上下文不是越多越好，也不是把数据库内容全部塞进提示词。每份上下文必须同时优化：

1. **相关性：** 只服务当前决策；
2. **正确性：** 不把推测、素材或旧状态冒充canon；
3. **权威性：** 冲突来源有明确优先级且不静默覆盖；
4. **时态性：** 区分系统记录时间、故事有效时间和角色/读者获知时间；
5. **视角合法性：** 只暴露当前POV或评价角色允许知道的内容；
6. **充分性：** 必需证据完整，缺失时阻断或明确降级；
7. **经济性：** 在满足任务的前提下控制token、延迟和注意力；
8. **可追溯性：** 每个结论能返回具体来源、版本和原文锚点；
9. **创造空间：** 无锚探索主动排除会导致固着的参考信息，不用“正确上下文”压灭意外和原创性。

上下文是核心操作系统，但不是全部。领域事实、正文版本、审批、评价、真人反馈和作者决定仍有各自权威；它们通过上下文进入决策，而不是被降格成提示词文本。

## 2. 规格审计结论

1.0版方向正确但不能直接实施，2.0版补齐了质量系统的工程边界；3.0进一步发现并解决上下文核心仍未闭环的问题：

| 级别 | 原规格问题 | 2.0处理 |
|---|---|---|
| P0 | `quality_context_compiler` 会与现有 `ContextSnapshot`、`ContextEnvelope`、`ContextAssembler` 形成双真相源 | 改为质量策略层，强制复用现有上下文内核 |
| P0 | 没有表、迁移、API、事件和文件落点 | 增加完整的持久化、接口、事件与仓库映射 |
| P0 | 场景是评价单位，但当前系统只有章级 `prose`，没有稳定场景边界 | 增加场景契约与版本绑定锚点，章正文仍为唯一权威 |
| P0 | 五万字评价没有冻结快照和成员定义 | 增加作品快照、章版本成员与不可变哈希 |
| P0 | 直接使用LLM自报置信度参与加权，无法校准 | 置信度改由上下文覆盖、证据有效性、校准可靠度、独立性和稳定性计算 |
| P0 | 加权平均容易把三方分歧隐藏成一个数字 | 改为三轴判断、分歧状态和仅供排序的决策指数；禁止小说总分 |
| P0 | “官方DeepSeek”没有对应当前调用边界、JSON空响应和上游并发语义 | 增加官方客户端、结构化输出、usage、429队列和供应商证明 |
| P1 | 六个新业务空间会破坏当前四栏信息架构 | 只新增“参考作品”入口，其余嵌入手稿、北极星、校验和设置中心 |
| P1 | 跨作品审美宪法没有全局持久化位置；2.0引入SQLite又形成新权威 | 改为同一SurrealDB实例的全局作者档案库，`USER.md`降为投影 |
| P1 | 参考指纹缺少分层生成、作者校正与相似性算法 | 增加章节/全书指纹、差异声明和多通道相似性检测 |
| P1 | LLM评价缺少位置偏差、自增强偏差和顺序偏差控制 | 增加证据提取/评分分离、盲评、顺序翻转和校准门 |
| P1 | 现有Pilot、NorthStar、QC、purpose和issue ignore如何接入不明确 | 给出复用、升级和迁移规则 |
| P1 | “所有字段验证”没有可生成的权威目录 | 增加字段目录、`data-field-path`和自动覆盖矩阵 |
| P1 | 质量建议没有注意力预算，会制造反馈过载 | 增加分层问题预算、聚类和心流静默规则 |
| P1 | 五万字质量验收样本、盲评和通过阈值不充分 | 增加固定验收数据、缺陷语料、30组盲评与真人门 |
| P0 | 2.0把质量系统放在中心，但没有说明所有创作能力如何共同服务一次决策 | 将Creative Context OS设为全系统核心机制，质量系统成为评价与学习子系统 |
| P0 | 2.0写成“扩展现有ContextPolicy”，但当前代码没有该模型 | 明确新增声明式`ContextPolicy`，保留`ContextAssembler`兼容门面 |
| P0 | 当前`ContextSnapshot`只冻结导航语义，不冻结实际内容来源 | 分离`NavigationSnapshot`、`ContextRequest`、`ContextManifest`和质量快照 |
| P0 | 当前`envelope_hash`不包含来源内容版本或摘要，同来源ID改内容后可能仍同哈希 | Manifest强制保存来源revision/content_digest，并计算`actual_input_hash` |
| P0 | 固定八块与固定预算无法表达生成、评价、参考、修订的不同必需和禁用来源 | 新增按任务声明的slot、预算、时态、POV、完整性和降级策略 |
| P1 | 召回结果与最终作品效果之间没有反馈链，无法证明“更好上下文”真的更好 | 增加Outcome Trace、上下文消融、盲评和作者决策反馈 |
| P1 | SurrealDB图、引用、事务和实时能力没有明确使用边界 | 用依赖边和事务实现一致性；明确snapshot isolation、write skew和实时事件限制 |
| P1 | Spectron设计思想有价值，但直接接入会形成第二套记忆和服务权威 | 仅吸收其来源优先、三时态、协调、分层检索和trace思想；不接入、不依赖、不预留适配器 |

## 3. 已确认的产品决策

### 3.1 产品形态

- 自适应多类型：固定十个核心质量维度，叠加可组合的类型观察包和作品自定义目标。
- 每部作品有独立质量合同；跨作品有作者审美宪法，本书可以覆盖或声明例外。
- 参考作品采用“全书指纹 + 分维度目标 + 模式 + 强度 + 反向约束”。
- 作者判断、系统判断和参考目标达成度分开保存；作者默认权重高于任一单独机器来源。
- 当前SurrealDB和现有领域模型是唯一持久化权威；不引入Spectron服务、SDK、Schema、适配器或旁路记忆库。
- 每个字段和功能必须通过“上下文贡献合同”证明它如何改善创作决策，否则删除、合并或降为内部观测。
- 内部按依赖分阶段实现，但只有统一验收后才算整体交付。

### 3.2 作者必须批准的动作

- 质量合同及重要例外；
- 大纲、人物重大转变和关键场景；
- AI候选正文进入作者正文；
- 创意假设晋升canon；
- 高影响修订应用；
- 硬风险覆盖或质量分歧裁决；
- 作品定稿；
- 单部作品观察晋升为长期审美偏好。

系统可以自动执行低风险整理、确定性检查、上下文编译、证据提取、候选生成和缓存失效。

## 4. 三套独立权威体系

### 4.1 故事事实

正式canon > 已批准时态状态 > 创意假设 > 素材或参考资料 > 模型推断。

模型推断永远不能冒充故事事实。创意假设只有独立批准后才能晋升canon。

### 4.2 创作意图

已批准作品质量合同 > 本书明确例外 > 作者审美宪法 > 参考目标配方 > 通用写作规则。

类型惯例和通用规则不能覆盖本书主动选择的反类型策略。

### 4.3 质量判断

硬风险单独处理；非硬风险同时显示作者判断、系统分析、参考目标达成度和真人读者反馈。作者拥有最终文本决定权，但系统必须先分析且所有原始意见永久保留。

### 4.4 上下文不是第四套权威

上下文只是一份针对特定任务的有界投影，不能反向成为事实源。`ContextManifest`保存“本次使用了什么”，不拥有canon、正文、合同、参考指纹或作者偏好。任何上下文内容都必须引用上述权威对象的不可变版本；模型输出只有经过相应审批才可能写回领域权威。

## 5. 仓库适配架构

### 5.1 必须复用的现有能力

| 目标能力 | 现有落点 | 2.0方案 |
|---|---|---|
| 动态上下文 | `context_models.py`、`context_service.py`、`context_assembler.py` | 新增声明式`ContextPolicy`并把现有组装器演化为统一门面；当前代码不存在可扩展的`ContextPolicy` |
| 写作提示单源 | `app.py::_assemble_write_instructions` | 继续作为写作生成总闸；质量合同通过现有envelope注入 |
| 主编身份与规则 | `app.py::_editor_system` | 保留身份层；不在各质量模块重复拼设定、角色和伏笔 |
| 章写作生命周期 | `pilot.py` | Pilot继续编排大纲、节拍、演绎、草稿、体检、交付和终选 |
| 确定性质量检查 | `/post-check`、`/issues`、`critique.py`、chapter QC | 作为确定性评价适配器接入，不重复实现 |
| 北极星和目的合同 | `intent`、`chapter_scorecard`、`purpose.py` | 升级为质量合同兼容投影，已有目的delta仍是唯一章目的源 |
| 版本和过期保护 | `chapter_version`、context revision/hash、`ai_run_trace` | 扩展为质量快照与任务绑定，不另造无关版本机制 |
| 素材导入与召回 | material import、BM25、向量、图召回、溯源 | 复用解析与索引基础设施，参考作品存储和检索空间独立 |
| 四栏界面 | `App → BinderLayout → FourPaneShell`、左轨能力组 | 只扩展现有入口和详情路由，不重做新应用壳 |
| 审批和事件 | Hermes Runs、`HermesEventAdapter`、Pilot approve | 复用事件语义和审批体验，质量只读任务使用自己的持久化作业 |

### 5.2 新增后端包

Creative Context OS新增以下通用内核文件：

- `scribe3/context_policy.py`：任务类型、slot、来源、时态、POV、预算、完整性和降级策略注册表；
- `scribe3/context_engine.py`：统一规划、检索、协调、装配和验证内核；
- `scribe3/context_store.py`：包装现有`SurrealStore`的Manifest、来源、冲突、依赖和Outcome窄读写接口，避免继续膨胀`store.py`；
- `scribe3/context_manifest.py`：来源清单、内容摘要、输入哈希、依赖边和可复现性合同；
- `scribe3/context_outcome.py`：输出、评价、作者决策、业务结果与上下文反馈；
- `scribe3/context_assembler.py`：保留现有公共接口，逐步改为调用`CreativeContextEngine`的兼容门面。

新增 `scribe3/quality/`，边界如下：

- `models.py`：Pydantic请求、响应、枚举和JSON Schema；
- `store.py`：`QualityStore`，包装现有 `SurrealStore` 的窄读写接口；
- `contract.py`：质量合同、类型包和旧 `intent` 投影；
- `references.py`：参考作品导入、分层指纹和相似性检测；
- `exploration.py`：创意假设、分支和canon晋升候选；
- `scenes.py`：场景契约、边界锚点和重绑定；
- `snapshots.py`：章、场景、卷、全书不可变质量快照；
- `rubrics.py`：固定十维、类型包、量表版本和评价提示模板；
- `evaluator.py`：证据提取、评分、反证、参考比较和分歧；
- `jobs.py`：持久化只读质量作业、分片、恢复和SSE事件；
- `revision.py`：修订问题、候选补丁、作者决策和复验；
- `api.py`：独立 `APIRouter`，由 `app.py` 只做一次挂载。

新增 `scribe3/deepseek_client.py` 作为官方API的可测试实现，`scribe3/llm.py` 仍是系统统一LLM出口并为旧字符串接口提供兼容包装。

不得继续把质量逻辑堆进已经过大的 `app.py` 或 `store.py`。

### 5.3 一个上下文内核，不是新的质量组装器

全系统只有一个 `CreativeContextEngine`。质量、参考、写作和修订只提供不同的 `ContextPolicy`，不得各自拼接一套提示词。现有 `ContextAssembler.assemble()` 保留为兼容入口，内部委托统一引擎；`_assemble_write_instructions`继续是生成总闸，但不再自行从十几个函数重复取数，而是消费已验证的 `ContextEnvelope`。

当前 `ContextSnapshot` 的真实语义是“导航快照”，3.0不强行让它承担内容冻结职责。兼容期保留类名和API，设计语义称为 `NavigationSnapshot`。它是 `ContextRequest` 的一个输入，不是完整上下文本身。

统一内核执行：

1. 读取导航快照和业务任务，构造 `ContextRequest`；
2. 解析任务对应的 `ContextPolicy`；
3. 先做确定性领域直查，再按需执行BM25、向量和图检索；
4. 按权威、三时态、POV、剧透边界和冲突规则协调候选；
5. 按slot优先级和预算装配，不允许可选块挤掉必需块；
6. 校验必需来源、内容版本、证据锚点和禁用来源；
7. 持久化 `ContextManifest`，生成 `actual_input_hash`；
8. 输出 `ContextEnvelope` 给DeepSeek、确定性检查器或UI；
9. 执行完成后写 `ContextOutcomeTrace`，把作者决策和业务效果反馈给后续检索评估。

任何质量模式不得回退到旧散点提示链。必需上下文缺失时应阻断并显示原因；现有普通写作路径只可在明确灰度期保留有信号的旧链回退，并统计每次回退，默认生产门要求回退为零。

### 5.4 核心对象合同

#### `ContextRequest`

描述“这一次为什么需要上下文”，至少包含：

`request_id`、`task_kind`、`target_ref`、`navigation_snapshot_id`、`work`、`chapter`、`scene_key`、`phase`、`actor_role`、`pov_character`、`story_time_window`、`knowledge_cutoff`、`author_intent_ref`、`quality_contract_revision`、`required_slots`、`forbidden_source_kinds`、`budget_profile`、`freshness_requirement`、`policy_version`。

`task_kind`使用受控枚举，至少包括：

`explore`、`outline`、`beats`、`deduce`、`draft`、`final`、`discuss`、`quality_scene`、`quality_chapter`、`quality_book`、`reference_fingerprint`、`reference_compare`、`revision_plan`、`revision_patch`、`canon_proposal`。

#### `ContextPolicy`

它是新增的声明式版本化合同，不是散落在Python条件分支里的隐式规则。每个slot声明：

- 是否必需、最少覆盖和最大token；
- 允许的领域表、对象类型和来源种类；
- 权威下限和冲突策略；
- 故事有效时间、获知时间、POV和剧透过滤；
- 允许的检索通道和最大扩展跳数；
- 截断、压缩、摘要和原文保留规则；
- 缺失时是 `block`、`degrade` 还是 `omit`；
- 是否允许进入模型提示、只进入审计清单或必须物理屏蔽。

Policy采用代码内声明式注册表作为初始权威，并同步保存 `policy_version + schema_hash`；作者可调的预算和偏好只能在Policy允许的范围内覆盖，不能通过设置解除canon、POV、剧透和审批红线。

#### `ContextPlan`

记录引擎准备从哪些领域对象、查询和检索通道取数，不包含最终模型正文。它用于估算成本、解释为什么要查询某项以及在执行前检测明显不可能满足的slot。

#### `ContextManifest`

这是实际输入的不可变证据清单。每个来源项至少保存：

`source_ref`、`source_kind`、`authority_class`、`revision`、`content_digest`、`anchor`、`system_time`、`valid_time`、`known_from`、`known_to`、`pov_visibility`、`retrieval_channels`、`channel_ranks`、`final_rank`、`included`、`reason`、`masked`、`token_estimate`。

Manifest不复制领域权威，也不把秘密原文写入日志。秘密或受屏蔽内容使用带服务端pepper的摘要参与版本身份；公开上下文使用规范化内容SHA-256。所有来源项的有序摘要、Policy版本、任务参数和最终渲染字节共同计算 `actual_input_hash`。

#### `ContextEnvelope`

扩展现有对象，增加：

`request_id`、`manifest_id`、`policy_version`、`required_missing`、`degraded_reasons`、`actual_input_hash`、`rendered_token_estimate`、`render_profile`。

现有 `envelope_hash`在兼容期保留，但不再作为可复现评价的充分证明；质量任务和审批必须绑定 `actual_input_hash`。

#### `ContextOutcomeTrace`

绑定 `request_id + manifest_id + actual_input_hash`，保存实际模型、usage、输出哈希、确定性结果、质量结果、作者接受/拒绝/修改、修订后的目标变化和副作用。它用于评价上下文策略，不自动改变canon或作者长期偏好。

### 5.5 权威协调与三时态

所有可召回内容统一映射为以下来源类，不要求复制到统一大表：

1. `canonical`：现有fact、proposition、event、promise、character、relation、timeline和已批准场景状态；
2. `intent`：质量合同、章目的、作者批准的本书例外和审美宪法投影；
3. `manuscript`：不可变chapter version、场景锚点和当前草稿；
4. `experiential`：对话、冷读、修订决定、质量判断和作者选择；
5. `reference`：素材、参考作品指纹和外部资料；
6. `uncertainty`：冲突、未确认推断、失效锚点和缺失信息。

协调规则不是last-write-wins：

- canonical与经验冲突时保留canonical，经验进入冲突或不确定项；
- 同一权威内的新版本通过显式supersedes链替代旧版本；
- 不同作品、不同角色知识范围或不同故事时间允许并存；
- 任何模型抽取的置信度不能自动覆盖作者批准的事实；
- 冲突未解决时，Policy决定阻断、并列展示或带降级继续，不能静默选择。

三时态统一为：

- `system_time`：记录何时进入系统及其版本历史；
- `valid_time`：事实在故事世界何时成立；
- `knowledge_time`：角色或读者从何章、何场或何事件开始知道，何时不再适用。

当前 `known_from / known_to`继续作为知识时态的章节投影；非线性叙事、倒叙和多POV使用事件/场景边界补充，不能只以章序近似。

### 5.6 分层检索与上下文预算

检索采用按成本逐级升级的路由：

1. **T0 必需直查：** 合同、目标正文、POV、章目的、canon和显式引用；
2. **T1 精确结构检索：** record link、实体、关系、时间和已知依赖；
3. **T2 混合召回：** BM25 + HNSW + 图召回，经RRF融合；
4. **T3 扩展召回：** 相邻场景、关系邻居、承诺链、主题链和反证；
5. **T4 有界全局：** 只有全书评价或低覆盖任务才读取分层全局摘要与必要原文证据。

`k`只控制返回数量，不得同时隐式控制内部候选池。生成任务禁止复用旧模型答案冒充新结果；只允许复用输入哈希完全一致的不可变Manifest、检索结果和确定性派生物。缓存命中必须重新验证来源head、Policy版本和依赖失效游标。

预算先保障硬约束和必需slot，再分配高价值证据，最后才放可选启发。固定八块预算改为兼容默认值，逐步迁移到按任务Policy。每个被排除来源都记录 `token_budget`、`authority_conflict`、`temporal_out_of_scope`、`pov_forbidden`、`spoiler_forbidden`、`duplicate`或`low_relevance`等明确原因。

### 5.7 不同任务的上下文隔离

- `explore`：读取核心意图、已知硬边界和作者主动给定素材；默认不读参考作品指纹和现成情节答案；
- `generation`：读取canon、合同、人物、章/场目的、相关历史、作者偏好和受控素材；禁止参考原文；
- `quality_scene`：读取冻结场景、场景契约、相关canon和有限前后文；
- `quality_chapter`：读取冻结章、章目的、相邻章证据、人物线和承诺；
- `quality_book`：读取分层证据包、全书合同、跨章结构和必要原文，不把五万字一次性塞入模型；
- `reference_fingerprint`：只读参考作品分片，不读取本书生成提示；
- `reference_compare`：读取冻结本书证据和已批准指纹，不执行生成写入；
- `revision_patch`：读取一个已确认问题、原文锚点、上层约束和副作用保护项，不加载无关全书建议。

生成模型和评价模型不得共享会泄露生成来源、生成提示、模型推理说明或作者预评分的上下文。相同底层事实可以从同一Manifest来源派生，但渲染Policy和可见字段必须隔离。

### 5.8 上下文贡献合同

每个领域字段和产品能力必须登记 `ContextContributionContract`：

`producer`、`authority_source`、`temporal_semantics`、`eligible_tasks`、`forbidden_tasks`、`context_slots`、`consumers`、`invalidation_sources`、`evidence_path`、`quality_hypothesis`、`acceptance_metric`。

它回答两个问题：

1. 该能力如何让某类创作决策获得更好的上下文？
2. 如何证明加入它以后，业务质量优于不加入或旧上下文？

只有存储和界面、却没有任何合法消费者的字段视为孤儿字段；只有注入模型、却没有来源、时态和排除规则的字段视为上下文泄漏；无法提出质量假设和验收指标的能力不得作为核心产品功能继续扩张。

### 5.9 Spectron采用边界

Spectron不进入运行时架构，不预留抽象适配层，也不复制其Schema。只吸收以下已被其文档体系验证、且能由当前SurrealDB原生实现的原则：来源优先、权威与经验分离、三时态、非静默协调、混合检索、分层成本、trace作为学习证据、状态差异和剧透安全。

任何Spectron命名、API、CLI、Context、服务角色、模型配置和部署方式都不是本系统合同。后续即使Spectron成熟，也必须作为一次全新的架构提案重新审计，不能借本规格预埋旁路。

## 6. 持久化模型与迁移

每部作品仍使用独立SurrealDB数据库；跨作品作者档案使用同一SurrealDB实例中的专用全局数据库。SurrealDB及现有领域对象是唯一持久化权威，不新增SQLite、Spectron或文件型第二真相源。

### 6.1 通用版本字段

关键对象统一具有：

`logical_id`、`revision`、`content_hash`、`supersedes`、`change_reason`、`changed_by`、`approved_by`、`created_at`、`effective_from`。

修订内容只增不改；单独的head记录通过CAS指向当前版本。异步结果绑定：

`work + snapshot_id + object_id + object_revision + content_hash + navigation_context_hash + context_manifest_id + actual_input_hash + rubric_version + model_profile_version`。

### 6.2 每部作品新增表

| 表 | 作用 | 关键字段 |
|---|---|---|
| `context_policy_snapshot` | 本次Manifest使用的Policy不可变审计投影 | `policy_key`、`version`、`schema_hash`、`payload`；代码注册表仍是Policy权威 |
| `context_manifest` | 一次实际上下文输入的不可变身份 | `request_id`、`task_kind`、`policy_version`、`actual_input_hash`、`required_missing`、`degraded_reasons` |
| `context_manifest_source` | Manifest逐来源清单 | `manifest_id`、`source_ref`、权威/时态/POV、`revision`、`content_digest`、召回通道、包含/排除原因 |
| `context_outcome_trace` | 上下文到输出、评价和作者决定的结果链 | `manifest_id`、`output_hash`、模型usage、质量变化、作者决定、`feedback_state` |
| `context_reconciliation_issue` | 未解决的来源冲突或缺失 | 冲突键、来源双方、权威、时态、处理状态和作者决定 |
| `context_dependency` | 全系统增量失效边 | `source_ref`、`dependent_ref`、`dependency_kind`、维度、版本和失效游标 |
| `quality_contract_revision` | 不可变作品合同 | `revision`、`status`、`payload`、`content_hash`、批准信息 |
| `quality_contract_head` | 当前合同CAS指针 | `current_revision`、`current_id`、`updated_at` |
| `reference_work` | 参考作品与导入状态 | `title`、`role`、`import_revision`、`status`、`source_hash` |
| `reference_chunk` | 参考章节/分片 | `reference_id`、`ordinal`、`text`、`text_hash`、`embedding` |
| `reference_fingerprint` | 章节/全书/维度指纹 | `scope`、`dimension`、`mechanisms`、`evidence`、`risk`、`revision` |
| `reference_target` | 本书分维度参考目标 | `dimension`、`target_mode`、`target_strength`、`target_band`、`negative_constraints` |
| `creative_hypothesis` | 创意方案当前对象 | `logical_id`、`state`、`head_revision`、`mutual_exclusions` |
| `creative_hypothesis_revision` | 创意方案历史 | `payload`、正反证据、试写片段、受影响对象 |
| `scene_contract_head` | 稳定场景身份和当前版本 | `scene_key`、`chapter_seq`、`ordinal`、`current_revision` |
| `scene_contract_revision` | 场景契约与正文锚点 | `contract`、`boundary_anchor`、`chapter_version_id`、`prose_hash` |
| `quality_snapshot` | 场景/章/卷/书冻结快照 | `scope`、`contract_revision`、`status`、`snapshot_hash` |
| `quality_snapshot_member` | 快照成员 | `snapshot_id`、`chapter_seq`、`chapter_version_id`、`range`、`text_hash` |
| `quality_job` | 持久化评价任务 | `state`、`snapshot_id`、模型与量表版本、进度、错误、费用估计 |
| `quality_job_shard` | 可恢复任务分片 | `job_id`、`unit`、`dimension_pack`、`attempt`、`state`、`lease_owner`、`lease_expires_at`、`heartbeat_at`、`result_hash` |
| `quality_job_event` | 可回放任务事件 | `job_id`、`sequence`、`event_type`、`payload`、`created_at` |
| `quality_evaluation` | 一次完整评价包 | `snapshot_id`、`job_id`、`status`、`coverage`、`degraded` |
| `quality_judgment` | 单位×维度×评价来源 | `unit`、`dimension`、`evaluator_kind`、`score`、`state`、`confidence` |
| `quality_evidence` | 原文证据与反证 | `judgment_id`、`polarity`、`anchor`、`quote`、`validation_state` |
| `cold_read` | 作者和真人读者冷读 | `snapshot_id`、`reader_kind`、`tags`、`notes`、可选分维度评分 |
| `revision_item` | 分层修订问题 | `layer`、`priority`、`evidence_ids`、`impact`、`status` |
| `revision_proposal` | 候选补丁或重构方案 | `revision_item_id`、`base_hash`、`patch`、`expected_effect` |
| `revision_decision` | 接受、拒绝、延期、覆盖 | `proposal_id`、`decision`、`reason`、`actor`、`created_at` |
| `issue_decision` | 可持久化忽略与豁免 | `issue_fingerprint`、`prose_hash`、`decision`、`reason`、`expires_at` |

复杂对象由Pydantic JSON Schema在API边界严格校验，SurrealDB保存结构化对象及索引字段。不得用“任意JSON串”绕开所有业务校验。

领域对象不批量复制进`context_manifest_source`。该表只保存稳定record引用、版本、摘要和本次使用决策；正文、canon、合同、素材、参考指纹和偏好的真实内容仍从各自领域表按不可变版本读取。对没有历史表的旧对象，迁移先补head/revision或内容摘要，再允许其进入强可复现上下文。

### 6.3 场景与章正文的权威关系

当前 `chapter.prose` 继续是唯一正式正文。场景对象不保存第二份正式正文，只保存：

- 稳定 `scene_key` 和章内顺序；
- 场景契约；
- 绑定某个 `chapter_version` 的范围、原文摘录、前后文指纹和UTF-16偏移；
- 锚点状态 `valid / relocated / needs_rebind / stale`。

直接编辑章正文后，系统先用摘录、前后文和段落指纹重定位。只有唯一匹配才能自动产生新场景契约版本；多解或无解必须由作者重绑。这样支持场景级设计与评价，又不破坏现有章编辑器。

所有文本锚点统一声明 `offset_encoding: utf16`，同时保存摘录、前缀、后缀和文本哈希，避免Python码点与浏览器UTF-16下标不一致。

### 6.4 冻结快照

创建质量快照时：

1. 为所有成员章创建或复用 `chapter_version(kind='quality_snapshot')`；
2. 为 `chapter_version` 增加 `content_hash`；
3. `quality_snapshot_member` 只引用不可变章版本和可选场景范围；
4. 全书快照哈希由有序成员哈希、合同版本、场景边界版本共同计算；
5. 任何评价只读快照，不读取后来变化的 `chapter.prose`。

### 6.5 跨作品审美档案

新增 `scribe3/author_profile_store.py`，复用现有SurrealDB连接和迁移机制，固定写入全局namespace/database，例如 `scribe3/author_profile`。作品数据库只保存所采用审美档案版本的record引用和本书覆盖，不复制档案正文。

表包括：`aesthetic_profile_revision`、`aesthetic_observation`、`aesthetic_decision`、`profile_projection_state`。

结构化SurrealDB记录是权威；现有 `USER.md` 内容首次导入为待确认候选，之后 `USER.md` 只由权威档案生成受控投影，不再直接追加成为事实源。全局数据库不可用时，跨作品偏好明确标记degraded，不允许悄悄回退到`USER.md`写入。

### 6.6 追加式迁移序列

从当前最高迁移089之后开始：

1. `090_chapter_version_quality_snapshot.surql`
2. `091_creative_context_core.surql`
3. `092_quality_contract.surql`
4. `093_reference_lab.surql`
5. `094_creative_scene.surql`
6. `095_quality_snapshot.surql`
7. `096_quality_job.surql`
8. `097_quality_evaluation.surql`
9. `098_revision_issue_decision.surql`
10. `099_context_dependency.surql`

全局作者档案数据库维护独立、同名可重入的`001_author_profile.surql`起始迁移，不与作品数据库的090序列混用；迁移执行器必须在回执中同时记录目标namespace/database，避免把全局表误建进某一本书。

迁移只增不删，先备份、预检和数量核对，再应用并生成回执。旧 `intent.reader_feeling`、`emotional_arc`、`red_lines` 投影到首个质量合同草稿；缺失项标记 `unknown`，不由模型伪造。

现有 `guardIssues.js` 的localStorage忽略记录不是长期权威。用户打开匹配正文时，前端可以把能够由“正文哈希+问题指纹”唯一匹配的旧记录一次性导入 `issue_decision`；无法唯一匹配的记录保留为仅本机旧记录，不伪造作者理由。迁移完成后服务器记录成为跨设备权威。

## 7. API与事件契约

所有作品级接口继续使用 `?work=`；作者档案和设置走全局raw接口。写接口使用 `expected_revision` 做CAS，创建类接口支持 `Idempotency-Key`。

### 7.1 核心接口

- 保留现有 `POST /context/sessions`、导航、快照和trace接口，兼容导航快照语义；
- `GET /context/policies`：返回可用任务Policy及版本，不暴露服务端秘密摘要pepper；
- `POST /context/compile`：按`ContextRequest`编译、校验并持久化Manifest；
- `GET /context/manifests/{id}`：上下文检查器读取来源、排除、降级和输入身份；
- `GET /context/manifests/{id}/sources`：分页读取逐来源证据；
- `GET /context/outcomes/{id}`：读取输出与作者决定的闭环trace；
- `POST /context/outcomes/{id}/feedback`：记录作者对本次上下文有用、缺失、错误或过载的判断；
- `GET /context/reconciliation-issues`、`POST /context/reconciliation-issues/{id}/decision`；
- `GET /context/dependencies/{source_ref}`：读取反向失效范围；
- `GET /quality/contract`
- `PUT /quality/contract`：保存新修订；批准动作单独调用
- `POST /quality/contract/{revision}/approve`
- `GET /quality/contract/revisions`
- `GET /references`、`POST /references`、`PATCH /references/{id}`
- `POST /references/import`、`GET /references/import/{job}/preview`、`POST /references/import/{job}/commit`
- `POST /references/{id}/fingerprints`、`GET /references/{id}/fingerprints`
- `GET /creative/hypotheses`、`POST /creative/hypotheses`
- `POST /creative/hypotheses/{id}/transition`
- `POST /creative/hypotheses/{id}/promote`：只生成canon写入提案，仍需现有审批门
- `GET /chapters/{seq}/scenes`、`POST /chapters/{seq}/scenes`
- `PUT /scenes/{scene_key}`、`POST /scenes/{scene_key}/rebind`
- `POST /quality/snapshots`
- `POST /quality/jobs/estimate`
- `POST /quality/jobs`、`GET /quality/jobs/{id}`
- `GET /quality/jobs/{id}/events`、`POST /quality/jobs/{id}/cancel`、`POST /quality/jobs/{id}/resume`
- `GET /quality/evaluations/{id}`
- `POST /quality/snapshots/{id}/cold-read`
- `GET /quality/revisions`、`POST /quality/revisions/{id}/proposals`
- `POST /quality/proposals/{id}/decision`
- `POST /quality/proposals/{id}/recheck`
- `GET /author-profile/aesthetic`、`PUT /author-profile/aesthetic`、`GET /author-profile/aesthetic/revisions`
- `GET /meta/field-catalog`

### 7.2 错误语义

- `409 stale_revision`：CAS或正文哈希不匹配；
- `409 stale_snapshot`：尝试把旧评价或补丁应用到新正文；
- `409 approval_required`：需要作者批准；
- `422 schema_invalid`：字段、量表或结构化模型输出无效；
- `422 evidence_invalid`：证据无法在冻结快照验证；
- `429 provider_concurrency`：官方供应商并发限制，任务保留在队列；
- `503 provider_unavailable`：官方DeepSeek不可用且没有静默替代；
- `503 required_context_missing`：必需上下文缺失；
- `409 context_source_stale`：Manifest引用的领域版本已变化；
- `422 context_policy_unsatisfied`：必需slot、权威、时态或POV合同不满足；
- `503 context_retrieval_unavailable`：某个Policy要求的检索通道不可用；
- `422 context_budget_exceeded`：必需证据在预算内无法完整提供。

错误响应统一返回 `code`、`message`、`retryable`、`degraded_reasons`、`expected`、`actual` 和 `recovery_action` 中适用字段。

### 7.3 质量作业事件

SSE事件统一为：

`quality.job.created`、`quality.job.started`、`quality.shard.started`、`quality.shard.completed`、`quality.shard.failed`、`quality.job.degraded`、`quality.job.stale`、`quality.job.completed`、`quality.job.cancelled`。

事件包含 `job_id`、`snapshot_id`、`progress`、`state`、`unit`、`dimension_pack`、`manifest_id`、`actual_input_hash`、`result_id` 和错误摘要；不在事件中发送完整正文。

事件先持久化再推送，`sequence` 在单个job内单调递增。SSE支持 `Last-Event-ID`，浏览器断线重连后从缺失事件继续，不能只看到当前状态而丢失中间失败或降级。

上下文编译本身不新建独立实时协议。质量任务通过上述job事件携带`manifest_id`；普通写作通过现有chat/run事件携带`request_id + manifest_id + actual_input_hash`。UI需要刷新上下文检查器时读取持久化Manifest，不能只依赖一次性内存事件。

## 8. 端到端创作闭环

流程可以回退、分支和循环，不是只能前进的流水线。

每一个需要模型或系统判断的步骤都执行同一小闭环：

`ContextRequest → ContextPolicy → ContextManifest → 创作/评价动作 → ContextOutcomeTrace → ContextDelta/依赖失效`

因此“完成一个功能”不仅要求动作有输出，还要求证明它使用了正确上下文、没有使用禁用上下文、输出绑定实际输入、作者结果被记录、后续受影响上下文已失效。纯人工编辑不强制先编译上下文，但保存后仍产生领域版本和`ContextDelta`，供后续任务使用。

1. **作品入驻：** 选择架构型、发现型或混合型工作方式；建立合同草稿、参考配方、维度权重和本书上下文边界。发现型作者可以先用最小合同，但深度评价和定稿前必须批准完整合同。
2. **无锚探索：** 使用`explore` Policy，默认隐藏参考作品、现成情节答案和不必要canon，系统提问、发散并提出方向正交的候选；所有内容保持非canon。
3. **反固着参考分析：** 导入喜欢和希望避开的作品，形成作者可校正的分层指纹、差异声明和禁用模式。
4. **动态规划：** 维护大纲、互斥假设和暂存碎片；偏离原计划不自动判错。
5. **场景设计：** 建立场景契约和正文边界，编译场景所需canon、人物状态、获知边界、目的delta与承诺触达；缺失项显式阻断或降级。
6. **心流写作：** 使用生成Policy，隐藏软评分，只显示确定性硬风险；系统候选进入候选区，不自动接受。作者可以查看本次Manifest，但系统不强迫持续打开检查器。
7. **里程碑冻结：** 场景、章、卷或全书完成一个阶段后创建不可变快照。
8. **作者冷读：** 在机器结论解锁前记录惊喜、无聊、困惑、不信、感动、太明显、想继续、声音不对及自由笔记。作者可以明确跳过，系统记录跳过而不是伪造冷读。
9. **独立评价：** 从冻结快照编译与生成隔离的评价Manifest，依次执行确定性检查、证据提取、十维评价、类型叠加、参考比较、原创性检测和反证复核。
10. **分歧裁决：** 显示三轴判断和真人反馈；作者处理冲突或明确覆盖硬风险。
11. **分层修订：** 按全书主题、人物关系、结构因果、章节目的、场景、段落、对话潜台词、句子意象、校对顺序修订。
12. **复验：** 每个已应用高影响修订绑定修改前后快照和Manifest，检查目标维度是否改善、是否产生副作用，以及改善来自正文变化还是上下文变化。
13. **定稿与canon反馈：** 定稿和canon写回是两个独立批准动作。
14. **审美学习：** 单次选择只形成观察；满足证据门后才建议晋升长期偏好。

Pilot继续负责章写作生命周期。其 `full_check` 使用快速确定性检查；深度质量评价作为快照作业运行。`finalize` 前必须存在当前快照的质量结果，或由作者提供带理由的显式覆盖。

## 9. 质量合同与量表

### 9.1 合同字段

质量合同至少包含：

- 作品类型：一个主类型、零至三个叠加类型、自定义类型说明；
- 目标读者与阅读情境；
- 一句话核心承诺；
- 目标阅读体验与情绪轨迹；
- 主题问题、允许的歧义和禁止的说教方式；
- 人物、关系、结构、语言、原创性的成功标准；
- 不可破坏项和允许取舍项；
- 十维重要性权重；
- 作者、系统和参考判断权重；
- 参考目标配方；
- 评价里程碑、注意力预算和完稿标准。

### 9.2 十个固定维度

1. 连贯性与因果；
2. 人物真实性；
3. 场景必要性；
4. 结构与节奏；
5. 悬念与兑现；
6. 情绪效力；
7. 阅读体验；
8. 语言与声音；
9. 主题与潜台词；
10. 原创性。

阅读体验拆分为叙事理解、注意力集中、情感投入和叙事临场感。LLM只能预测这些效果，不能冒充真人阅读体验。

### 9.3 单位专属量表

场景、章节、分卷和全书使用同一维度名称，但观察项不同，禁止把场景均分冒充全书质量。例如：

- 场景必要性在场景层检查进入状态、策略变化、转折、代价和退出状态；
- 结构与节奏在章节层检查章目的、信息释放和场景顺序；
- 结构与节奏在全书层检查主线、支线、转折间距和篇幅分配；
- 主题与潜台词在场景层检查选择与留白，在全书层检查反复、变化和最终立场张力。

`rubrics.py` 使用声明式注册表，固定 `rubric_version`。初始类型包至少覆盖：推理、爱情、恐怖、惊悚、幻想、科幻、历史、冒险、喜剧、文学、网文连载和青少年。类型包只增加观察项，不覆盖核心维度；多个类型包可以组合，本书可增加自定义观察项。

### 9.4 五级锚点

1. 明显损害合同目标；
2. 局部成立但存在实质缺口；
3. 完成基本功能；
4. 有效且存在清晰证据；
5. 高度有效并产生不可轻易替代的作品效果。

五分必须说明效果、机制、原文证据和删除或替换后的损失。评价状态为 `not_applicable / insufficient / degraded / conflicted / evaluable`，只有 `evaluable` 可产生分数。

## 10. 评价引擎与偏差控制

### 10.1 评价流水线

每个单位执行六个隔离步骤：

1. 确定性硬风险；
2. 按维度检索候选证据；
3. 验证证据锚点并形成证据包；
4. 在不知道作者评分、生成来源和其他评价结果的条件下评分；
5. 独立反证审阅，寻找评分不成立的证据；
6. 合并为带覆盖率、置信度和分歧状态的判断。

同一模型生成和评价时，评价请求不得看到生成提示、推理说明或“这是AI文本”的标记。高影响判断至少执行两次独立上下文评价；成对比较必须交换文本顺序以检测位置偏差。

### 10.2 置信度不是模型自报概率

LLM只能输出不确定原因，不能给自己设置最终数值置信度。系统置信度由以下可观测信号计算：

- `context_coverage`：合同要求的必需上下文覆盖率；
- `evidence_validity`：证据锚点验证通过率；
- `calibration_reliability`：当前模型、提示、量表版本在校准集上的可靠度；
- `independence_factor`：不同模型为1.0、同供应商不同模型为0.8、同模型独立上下文为0.6；
- `stability_factor`：重复评价的一致性。

最终置信度为这些信号的保守组合，并保存各分量。任一必需证据无效时，该判断不能标记为高置信。

### 10.3 三轴判断与权重

每个维度分别显示：

- `A`：作者满足度；
- `S`：系统工艺与效果判断；
- `R`：参考目标达成度。

三者不是同一种真理。只有作者完成该维度评分时，系统才可生成决策支持指数：

`D = A×wA + S×wS×Cs + R×wR×Cr`

默认 `wA=0.50`、`wS=0.30`、`wR=0.20`，本书可逐维修改，但必须满足 `wA > wS` 且 `wA > wR`。作者缺席时只显示机器临时判断，不重新归一化成仿佛已经完成的决策。

`D` 只用于同一维度内的修订排序，不能跨维度相加，也不能生成小说总分。

以下任一情况产生 `conflicted`：作者与系统相差两档以上；作者指出高优先级问题而系统判优；高强度参考目标未达成；原创性风险与参考接近目标冲突；两次高影响评价结论相反。

硬风险不能被加权平均抵消。作者可以覆盖，但必须确认原文证据并填写理由。

### 10.4 修订优先级

`作者关注度 × 证据强度 × 影响范围 × 合同重要性 × 下游依赖数 / 预计修订成本`

该结果只排序问题，不自动生成或应用补丁。全书和结构问题可以只给重构方案，不强行伪造字符级补丁。

## 11. 参考作品系统

### 11.1 分层分析

参考作品导入复用现有解析、切分、向量和进度基础设施，但使用独立表和检索命名空间。分析顺序：

1. 章节或稳定分片的局部机制与证据；
2. 人物、关系、承诺、结构、主题和语言的跨章聚合；
3. 全书指纹；
4. 作者校正、批准和差异声明。

指纹不是模型摘要，必须包含证据、反证、可迁移机制、不可复制要素和适用范围。

### 11.2 目标模式

- `close`：在作者定义的目标带内接近；
- `inspired`：机制相似但表达、人物配置和情节保持距离；
- `contrast`：主动形成相反机制或效果；
- `avoid`：避免指定模式。

`R` 评价的是目标模式达成度，不是“越像越高”。原创性维度始终独立，不能被参考目标抵消。

### 11.3 反固着与相似性检测

- 无锚探索完成前，生成模型看不到参考作品及其指纹；
- 生成模型只读取作者批准的抽象机制和差异声明，不读取参考原文；
- 参考文本按数据边界封装，文本中的指令不得成为模型指令；
- 确定性字符/词组n-gram检测近复制；
- 段落向量检测语义近似；
- LLM只辅助判断结构、人物配置和情节组合风险；
- 每个风险必须指向本书和参考作品的对应证据。

## 12. 场景设计、写作与修订

### 12.1 场景契约

字段包括POV、时间、地点、入场状态、欲望、阻力、风险、策略变化、转折、代价、事实变化、人物知识变化、读者信息变化、情绪变化、关系变化、承诺触达、退出状态、下一场驱动力和主动保留的未解决项。

现有 `chapter.purpose_text` 与 `deltas` 仍是章节目的权威源；场景契约只说明本场如何贡献，不重复登记章目的。

### 12.2 心流规则

- 起草时不持续显示十维评分；
- 确定性硬风险可以后台提示，但不自动改文；
- 软问题只在作者主动检查或里程碑快照后出现；
- AI默认给二至四个方向正交的候选，并说明差异，不给一个“标准答案”；
- 接受候选必须生成基于正文哈希的显式补丁或插入动作；
- 正文变化后旧候选变为stale，不能自动应用。

### 12.3 分层修订

固定顺序为：

1. 全书意图、主题和结局；
2. 人物弧、关系和关键选择；
3. 结构、因果、悬念和兑现；
4. 卷与章节目的；
5. 场景必要性与转折；
6. 段落、信息释放和留白；
7. 对话、声音和潜台词；
8. 句子、意象和节奏；
9. 校对和格式。

下层修订不能在上层仍可能重写时大规模执行。作者可以跳层，但系统显示可能浪费的修订成本。

### 12.4 注意力预算

每层默认只展开：所有blocking问题、最多5个major问题和最多10个普通建议。其余按根因、证据和影响对象聚类折叠，作者可以查看全部。

系统不得为了显得有用而重复报告同一根因。被拒绝或豁免的问题进入持久化 `issue_decision`，只有正文哈希、量表或合同变化使理由失效时才重新出现。

## 13. 作者审美宪法

审美学习区分：本书选择、情境偏好、长期偏好和硬禁忌。

- 一次选择只生成 `observation`；
- 同一偏好至少有三次独立选择、覆盖至少两部作品，且检查过反例后，才能建议晋升为跨作品偏好；
- 只在一部作品反复出现的选择可以成为本书规则，不能直接跨书；
- 作者批准后生成新 `aesthetic_profile_revision`；
- 每条偏好保存支持证据、反例、适用类型、置信度、复核日期和撤销历史；
- 本书质量合同与偏好冲突时，本书合同优先；
- `USER.md` 只呈现已批准偏好的紧凑投影。

## 14. 四栏界面落点

不新增六套平行工作区，不改变 `App → BinderLayout → FourPaneShell`。

### 14.1 左轨

- 保留 `manuscript`、`codex`、`materials`；
- 内容组只新增 `references`（参考作品）；
- 保留现有 `northstar` key，面板升级并改名为“目标/合同”，避免用户偏好和路由失效；
- 保留现有 `review` key，将“校验”升级为质量审阅与修订目录；
- `frame`、`deduce`、`promise`、`motif` 和 `search` 不复制。

### 14.2 手稿目录

- 手稿根增加“创意实验室”容器；
- 每章可以展开场景契约子项；
- 章仍进入现有编辑器；场景项进入场景契约详情并可定位正文；
- 快照、评价、修订问题都通过 `targetNavigation` 返回章或场景。

### 14.3 中间详情区

- 目标/合同：合同字段、版本、批准和旧 `intent` 映射；
- 参考作品：导入、分片进度、指纹、作者校正和目标配方；
- 创意实验室：分支、互斥方案、试写和状态迁移；
- 质量审阅：冷读锁、三轴判断、证据、反证、分歧和降级；
- 修订工作台：分层队列、前后版本、候选补丁、决策和复验。

### 14.4 右栏与设置

- 右栏新增当前对象作用域的“修订建议”，不新增另一个聊天系统；
- 升级现有上下文检查器，而不是新建平行界面：显示当前`ContextRequest`、Policy、必需slot、Manifest来源、排除原因、冲突、降级、token和`actual_input_hash`；默认折叠，只在失败、作者主动查看或验收模式下展开；
- 每个来源可以定位现有领域详情或冻结正文锚点；检查器只能解释和反馈上下文，不能直接编辑canon或把被排除来源强塞进当前已执行请求；
- 设置中心 `PrefsSection` 升级为作者审美宪法；
- LLM设置显示生成、评价和参考模型配置、供应商证明、实际token和无限/有限调用策略；
- 当前 NorthStar 文案“裁决在人”改为“系统先分析，作者拥有更高决策权；原始意见均保留”。

## 15. 官方DeepSeek与模型职责

### 15.1 模型配置

将单一 `llm.model` 升级为：

- `llm.provider = deepseek_official`；
- `llm.generation_model`；
- `llm.evaluation_model`；
- `llm.reference_model`；
- `SCRIBE3_DAILY_CALL_CAP`，默认0表示不设产品级日帽；
- `llm.max_concurrency`，用于本地队列保护，不冒充供应商配额。

旧 `llm.model` 在迁移时作为三个模型的初始值，随后仅保留兼容读取。模型名来自设置和官方能力，不在业务代码硬编码。

### 15.2 调用边界

- 纯生成、参考分析和质量评价直接调用官方DeepSeek；
- 官方客户端提供 `complete_text`、`complete_json` 和 `stream_text`，统一返回 `LLMResult`；
- `LLMResult` 包含文本、解析对象、模型、供应商、必有的本地 `client_request_id`、可选的 `provider_request_id`、usage、缓存命中token、耗时和重试记录；
- 现有 `hermes_complete` 等旧接口通过兼容包装返回字符串；
- 需要工具和审批的Hermes路径必须记录实际推理供应商。若不是官方DeepSeek，界面标记不符合本书模型策略，不能静默宣称官方调用。

### 15.3 JSON输出

评价调用使用官方 `response_format={"type":"json_object"}`，提示中明确包含JSON和目标示例，并设置足够 `max_tokens`。官方文档说明JSON模式可能偶发空内容，因此：

1. 空内容视为失败，不补假对象；
2. 最多执行两次有记录的格式修复或重试；
3. 结果必须通过Pydantic Schema和证据锚点验证；
4. 仍失败则分片失败或任务partial，不能用默认分数补齐。

### 15.4 无500次产品上限

当前 `SCRIBE3_DAILY_CALL_CAP` 默认500。迁移后0表示无限，`_tick_daily()` 在0时只记usage不阻断，`daily_remaining()` 返回 `None`，用量API返回 `unlimited:true`，前端不再渲染500分母。

这不取消官方供应商的并发限制。官方429进入持久化队列并退避重试；不形成无限热循环。用户仍可主动设置有限日帽作为成本保险丝。

### 15.5 提示与缓存

官方DeepSeek缓存依赖完整公共前缀。提示顺序固定为：稳定系统协议、量表、合同、上下文清单、可变证据和本次任务。记录 `prompt_cache_hit_tokens` 与 `prompt_cache_miss_tokens`，但缓存是best-effort，不能作为正确性依赖。

API密钥只能从注册的secret设置或环境读取，不能写入源码、业务数据库、日志、提示词、测试夹具或Git。这是基础安全边界，不建设额外隐私或版权产品功能。

## 16. 任务、失败、并发与恢复

### 16.1 状态机

`queued → running → succeeded | partial | degraded | failed | cancelled | stale | superseded`

状态必须持久化。进程重启后，`running`分片转为可恢复队列，已经成功且哈希匹配的分片不重算。

### 16.2 作业执行与租约

质量任务由独立 `python -m scribe3.quality.worker` 进程消费，避免长篇评价阻塞Uvicorn请求线程。worker通过原子更新领取分片并设置短租约，运行中定期写心跳；进程死亡或租约过期后，其他worker可以重新领取。

分片采用at-least-once执行语义，并以 `job_id + unit + dimension_pack + input_hash + evaluator_version` 唯一键保证结果幂等。供应商请求可能已经完成但结果尚未来得及落库时允许重做；重复结果只能命中同一幂等键，不能生成两套互相竞争的当前评价。

### 16.3 分片原则

- 确定性检查按章；
- LLM评价按场景或章与维度包分片；
- 全书评价读取低层已验证证据包和必要原文摘录，不直接把五万字塞进一个请求；
- 高影响维度使用第二次独立评价；
- 参考比较独立分片，失败不污染系统工艺判断。

### 16.4 并发安全

每个任务绑定快照、合同、量表、参考指纹和模型配置版本。作者编辑正文不会取消旧任务，但任务完成时标记stale，结果只能查看，不能应用。

正文和canon使用现有乐观并发与审批边界。候选补丁携带 `base_hash`；不匹配时返回409，不自动三方合并。

### 16.5 降级规则

- 关键canon、冻结正文、质量合同或场景边界缺失：阻断对应评价；
- 次要参考或相邻章缺失：允许degraded并说明受影响维度；
- 评价模型与生成模型相同：标记模型不独立并降低置信度；
- 某维度失败：保存其他合法结果，但整体为partial；
- 任何mock、备用模型或旧提示链都不能作为真实验收中的静默降级。

## 17. 长篇性能与增量失效

### 17.1 分层评价

`场景原文证据 → 章节判断 → 分卷关系 → 全书判断`

每层都保留回到原文的证据，摘要不能成为最终证据。相关证据在上下文开头和结尾合理分布，并通过分片检索避免“长上下文中部遗失”。

### 17.2 依赖失效

修改场景后，只失效：

- 该场景和所属章；
- 涉及人物、关系、承诺、主题或事件的相关聚合；
- 依赖这些聚合的分卷和全书维度。

`context_dependency`以SurrealDB record link或relation表达从领域对象到Manifest、评价、修订候选和聚合结果的依赖。失效从发生变化的record revision反向遍历，生成可审计`ContextDelta`，不得通过“全书缓存全部清空”掩盖依赖模型缺失。

没有依赖边的维度可以继续复用旧结果，但复用前必须验证`actual_input_hash`、所有来源revision/content_digest、合同版本、Policy、量表、模型配置和失效游标。发现一个已使用来源没有依赖边时，结果标记`dependency_incomplete`，不得作为当前结论。

### 17.3 可观测预算

- 创建任务和返回估算不等待模型；
- 上下文编译内部耗时p95目标低于2秒，不含供应商推理；
- 取消请求5秒内停止派发新分片；
- 进程重启60秒内恢复队列状态；
- token估算与实际usage偏差目标不超过20%；
- 全书运行前显示分片数、token区间、费用区间和可能降级项；
- “快速、标准、深度”只改变证据广度、重复评价次数和成本，不改变量表定义。

上下文还必须记录：各slot候选数、选入数、排除数、必需覆盖率、来源新鲜度、检索通道贡献、冲突数、POV/剧透拦截数、实际token占比和最终作者反馈。不能只观测总token和延迟。

### 17.4 SurrealDB能力与正确性边界

- 领域对象、上下文Manifest、来源引用、依赖边、任务和结果尽量在一次短事务中原子写入；
- SurrealDB的snapshot isolation能阻止同一record的丢失更新，但不能自动防止跨record write skew；canon晋升、任务租约、唯一当前head等不变量必须触碰共享guard/head记录并处理事务冲突重试；
- 数据库`ASYNC EVENT`不处于原写事务内，不承担正确性关键的Manifest、失效和审批写入，只可触发可重建后台工作；
- `LIVE SELECT`只用于已提交变化的即时UI提示，不能作为唯一任务队列或可靠重放源；持久事件表和`Last-Event-ID`仍是恢复权威；
- record references和graph relation用于反向依赖与关系遍历，删除行为必须显式声明，关键历史对象不得默认级联删除；
- 是否把Python RRF迁移到`search::rrf()`、是否使用新索引类型，必须先对实际运行二进制执行version命令和真实查询探针；文档出现能力不等于当前部署已经支持；
- 中文检索继续用jieba生成可审计tokens，并用`search::analyze()`探针验证索引与查询分词一致。

## 18. 所有字段与功能的可证明覆盖

新增 `scribe3/field_catalog.py` 作为验收目录，合并Pydantic Schema、现有codex声明和人工登记的旧字段。`GET /meta/field-catalog` 返回：

`field_path`、`object_type`、`label`、`kind`、`editable`、`required_when`、`ui_route`、`read_api`、`write_api`、`storage_path`、`authority_source`、`temporal_semantics`、`eligible_tasks`、`forbidden_tasks`、`context_slots`、`context_consumers`、`invalidation_sources`、`quality_hypothesis`、`acceptance_metric`、`export_path`、`fixture_value`。

所有前端输入控件必须带稳定 `data-field-path`。CI生成并核对“字段—界面—API—存储—上下文—导出”矩阵：

- 用户可编辑字段必须验证创建、读取、修改、版本、撤销和导出；
- 机器派生字段必须验证来源、刷新、过期和降级；
- 适用字段填写率100%；不适用、未知和延期分别使用 `not_applicable`、`unknown`、`deferred`；
- 新增字段没有目录项或目录项没有消费者时，测试失败；
- 字段被填写但从未参与任何流程时，不算功能完成。
- 字段进入某个Manifest但没有来源版本、合法任务或排除规则时，判定为上下文泄漏；
- 字段有消费者但不能提出与小说质量相关的可检验假设时，不得以“以后可能有用”保留为核心用户字段。

功能目录以“用户操作 → HTTP/SSE → 后端服务 → 存储变化 → 上下文贡献 → 界面反馈 → 业务目标”七段证据为单位。只证明按钮可点、接口200或数据已进入提示词都不算通过。

## 19. 测试与质量校准

### 19.1 自动化层

- 单元：量表、权重、置信度、状态机、锚点、缓存失效和相似性算法；
- Schema：所有请求、响应、DeepSeek JSON和SurrealDB写入；
- 集成：真实SurrealDB作品库与全局作者档案库、官方DeepSeek测试账户和恢复队列；
- 契约：旧API、现有四栏、Pilot、NorthStar、导出和设置兼容；
- 浏览器：真实界面填写、冷读锁、证据定位、冲突、重启、恢复和导出；
- 故障注入：超时、空JSON、429、5xx、进程中止、过期正文、锚点失效和部分分片失败。

### 19.2 评价校准集

建立版本化语料，包括：

- 植入事实、时间、POV、因果、人物、伏笔和重复缺陷的文本；
- 明确无缺陷的对照文本；
- 每个软质量维度的高、中、低锚点样本；
- 有意重复、排比、误导和留白等容易误报的反例；
- 近复制、机制借鉴、主动对照和完全独立的参考对比样本；
- 包含emoji和生僻Unicode字符的锚点样本。

上线门：

- 确定性植入硬缺陷召回率100%，对固定无缺陷对照零误报；
- 所有展示证据的锚点有效率100%；
- 软维度证据相关性经人工抽样达到85%以上，抽样不少于100条或覆盖该版本全部证据（不足100条时）；
- 同一冻结文本重复评价，90%以上维度保持在一档以内；
- 至少100组成对样本执行输入顺序翻转，无证据反转比例不得超过5%；
- 校准失败的模型、提示或量表版本不能进入默认生产配置。

### 19.3 上下文系统校准集

上下文正确性与文学评价分开验收。建立至少覆盖以下情况的版本化gold set：当前/历史canon冲突、倒叙、跨章秘密、多POV获知差异、同名实体、旧章改写、参考固着、无锚探索、过量素材、缺失章目的、失效场景锚点和同来源不同revision。

硬门：

- 必需结构化来源召回率100%；
- Manifest来源revision/content digest和原文锚点覆盖率100%；
- 跨作品、POV、剧透、禁用参考原文和过期revision泄漏为0；
- 被明确禁用或超出时态的来源选入数为0；
- 旧`actual_input_hash`接受、旧补丁应用和不完整依赖复用为0；
- 同一不可变输入、Policy和模型配置必须生成相同Manifest与渲染字节；
- 检索p95、token预算和必需slot覆盖达到第17节门槛。

软价值门采用上下文消融：在相同冻结任务、模型、参数和随机策略下，对比“3.0上下文”“旧组装链”“移除目标slot”“加入干扰上下文”四组输出。匿名随机盲评必须证明3.0在目标合同维度上优于旧链和消融组，且提升不是来自更长输出、更多token或泄漏未来事实。

## 20. 五万字真实端到端验收

### 20.1 主验收作品

创建一部不少于50,000个非空白正文字符、至少20章和60个场景契约的完整测试小说。使用真实浏览器、真实数据库和官方DeepSeek，从空白走通：

质量合同、上下文Policy、无锚探索、四种参考目标、分支大纲、人物与世界、场景设计、章目的、连续写作、canon、POV、知识边界、故事时间、关系、伏笔、素材、上下文Manifest、冲突协调、冻结快照、作者冷读、十维评价、类型叠加、参考对比、原创性、分歧、九层修订、复验、ContextDelta、审美观察、定稿、重启恢复和导出。

全部可适用字段由真实界面填写并经过读回、修改和流程消费；不允许直接灌库代替真人路径。另用小型专项作品覆盖全部初始类型包。

### 20.2 后端流程证据

每一步保存：`ContextRequest`、Policy、Plan、逐来源Manifest、包含/排除理由、必需覆盖、版本与content digest、`actual_input_hash`、最终渲染字节哈希、模型与usage、原始结构化输出、领域存储变化、依赖边、UI结果、失败或降级、作者决策、Outcome Trace和复验结果。

专项验证：并发编辑、跨record write skew防护、旧Manifest和旧补丁拒绝、任务取消、进程重启、SSE断线回放、429排队、空JSON、部分失败、参考导入恢复、场景锚点重绑定、POV/剧透隔离、冲突不静默覆盖、精准依赖失效、无限调用设置和旧作品迁移。

### 20.3 业务质量验证

建立系统介入前的冻结基线。对至少30组高影响修订进行匿名、随机顺序的修改前后对比；评价者包括作者和至少两名独立真人读者。

另外选取不少于60个真实上下文敏感任务，覆盖探索、大纲、演绎、正文、讨论、评价、参考比较和修订。在相同模型、参数、目标正文与随机策略下，对“3.0上下文”和“旧组装链/关键slot消融/干扰上下文”进行匿名比较。评审者不知道哪份输出来自哪套上下文。

通过条件：

- 至少70%的已应用高影响修订在目标维度上获得多数真人偏好；
- 至少70%的上下文对照任务在预注册目标维度上多数偏好3.0输出，且任何POV、剧透、canon和参考原文红线零退步；
- 人工抽检不少于100份Manifest，选入来源与当前任务直接相关的比例至少90%，必需来源漏失为0；
- 质量提升不能仅由平均输出长度或token增长解释；token增长超过25%的任务必须证明相应质量收益或重新优化Policy；
- 任何合同定义为“不可退步”的高权重维度都没有未批准下降；
- 作者与两名独立读者的多数盲评在至少一个合同核心阅读指标上偏好修订版；任何“不可退步”指标都不得出现多数人判断退步；
- 没有未处理的硬完整性错误，作者覆盖项有明确理由；
- 近复制测试全部识别，机制借鉴和主动对照样本不被误判为抄近；
- 作者确认系统帮助作品更接近本书合同，而非只让文本更像通用好文；
- 两名真人读者的意见、系统判断和作者判断全部保留，不用一个平均分抹平。

Codex或LLM模拟作者只能用于流程压力测试，不能替代作者冷读和真人读者质量门。

### 20.4 验收报告

每一步标记 `PASS / PARTIAL / FAIL / BLOCKED`，附原始结果、上下文证据、分析、问题、修复和复验。只有字段矩阵、功能矩阵、上下文正确性与消融、五万字闭环、后端一致性、旧功能回归和业务质量全部通过，才能宣称整体完成。

## 21. 实施顺序与退出门

### 阶段0：基线与可测性

完成字段目录、Context Contribution目录、现状旧组装链基线、上下文gold set、消融实验骨架、50k验收脚本骨架和质量校准集。退出门：现有字段、功能、注入点、孤儿字段、上下文泄漏和未接线能力能够诚实列出。

### 阶段1：Creative Context OS内核

完成`ContextRequest`、Policy、Plan、Manifest、Outcome Trace、三时态、权威协调、分层检索、内容身份、依赖边和现有Assembler兼容门面。退出门：第19.3节硬门通过，所有生产写作入口能证明只走统一内核，旧链回退为0。

### 阶段2：模型、快照与任务基础设施

完成官方DeepSeek客户端、无限日帽语义、质量数据迁移、不可变快照、持久任务、SSE回放和全局SurrealDB作者档案。退出门：真实provider、CAS、write-skew guard、重启恢复、空JSON和429测试通过。

### 阶段3：创作前系统

完成质量合同、参考实验室、创意假设和场景契约。退出门：参考原文不进入生成Manifest、无锚探索不受参考固着、场景锚点可重绑、旧intent和purpose无双写分歧。

### 阶段4：质量决策

完成十维、类型包、证据、置信度、参考比较、原创性和分歧。退出门：校准集达到第19节门槛。

### 阶段5：修订与审美

完成冷读锁、注意力预算、修订队列、补丁、复验、issue决策和审美宪法。退出门：正文不被自动覆盖，所有决策可撤销和追踪。

### 阶段6：界面、迁移与总验收

完成四栏接入、Context Inspector、旧数据迁移、全字段矩阵、上下文消融、五万字闭环和真人质量验证。退出门：第20节全部通过。

本文件是系统级主规格，不对应一个不可审查的巨型代码批次。每个阶段必须形成独立实施计划、迁移边界、回滚策略和验收回执；前一阶段退出门通过后才能让后一阶段依赖其合同。各阶段可以独立提交和审查，但不能单独宣称满足第一性目标。

## 22. 明确不在范围内

- 保证作品成为名著或商业成功；
- 用AI替代作者的主题、审美和最终文本决定；
- 自动出版、营销、版权交易或商业发行；
- 新建隐私与版权管理产品功能；
- 接入或预留Spectron服务、SDK、Schema、CLI、适配器或旁路记忆库；
- 引入第二个领域权威、用Manifest复制领域真相或把模型上下文反写成canon；
- 把“上下文组织”等同于无限扩大提示词、一次性塞入全书或持续打断作者心流；
- 与高质量小说目标无关的社交、运营或通用协作功能；
- 为字段全绿制造不适用数据；
- 用小说总分或测试全绿证明文学质量。

## 23. 完成定义

只有同时满足以下条件才算完成：

- 所有本规格模块进入真实四栏界面且不存在平行假入口；
- 迁移、API、事件、上下文、快照、任务和模型调用符合本规格；
- 所有模型和系统判断都绑定可复现Manifest与`actual_input_hash`，不存在未登记的散点提示注入；
- 所有核心字段都有Context Contribution Contract，孤儿字段和上下文泄漏为0；
- SurrealDB是作品与跨作品作者档案的唯一持久化权威，不存在SQLite、文件或外部记忆服务双写；
- 现有作品、Pilot、QC、目的合同、素材、canon和导出没有破坏性回归；
- 全部可适用字段完成真实读写、修改、追踪、消费和导出验证；
- 所有核心生成、参考分析和评价使用官方DeepSeek并具有供应商证据；
- 产品级500次日帽已改为默认无限，供应商并发和费用仍可观测；
- 五万字作品完成从空白到定稿、重启恢复和导出的真实闭环；
- 评价通过校准集、偏差测试、参考测试和真人盲评；
- 上下文系统通过gold set、POV/剧透/跨书隔离、依赖失效、消融和真人盲评；
- 所有范围内验收问题完成复现、根因修复和全链路复验；
- 交付代码、迁移、测试、字段/功能矩阵、使用说明和逐步骤验收报告；
- 任何未通过项明确标记，不得宣称整体完成。

## 24. 设计依据

- [Flower 与 Hayes 的认知过程写作模型](https://doi.org/10.58680/ccc198115885)：写作是规划、表达和复核之间的递归过程。
- [Kellogg 等关于写作与工作记忆的研究](https://doi.org/10.17239/JOWR-2013.05.02.1)：长篇写作需要外部化状态和分层处理。
- [Writing Excuses：混合型大纲与发现式写作](https://writingexcuses.com/12-22-hybrid-outlining-and-discovery-writing/)与[修订实践](https://writingexcuses.com/15-04-revision-with-patrick-rothfuss/)：系统同时支持多种工作流，并把修订视为独立创作阶段。
- [Brandon Sanderson 对大纲型与发现型写作的说明](https://faq.brandonsanderson.com/knowledge-base/are-you-an-outliner-or-a-discovery-writer/)：工作流必须适应作者和作品。
- [Smith、Ward 与 Schumacher 关于示例固着的研究](https://doi.org/10.3758/BF03202751)：先看到示例会造成无意趋同。
- [Doshi 与 Hauser 关于生成式AI和短篇创作的研究](https://doi.org/10.1126/sciadv.adn5290)：AI可能提高单篇结果，却降低作品之间的多样性。
- [Busselle 与 Bilandzic 的叙事投入量表](https://doi.org/10.1080/15213260903287259)：阅读体验应拆分为理解、注意、情绪投入和临场感。
- [CoAuthor](https://arxiv.org/abs/2201.06796) 与 [Wordcraft](https://doi.org/10.1145/3490099.3511105)：人机共写应保留候选、采纳、拒绝、修改历史和作者所有权。
- [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685)：LLM评价存在位置、冗长、自增强和推理偏差，必须校准和盲评。
- [G-Eval](https://arxiv.org/abs/2303.16634)：结构化量表和分步评价能改善人类对应度，但评价器可能偏爱LLM文本。
- [Lost in the Middle](https://arxiv.org/abs/2307.03172)：长上下文中的中部证据容易被模型忽略，支持分片与证据检索设计。
- [SurrealDB Transactions and Isolation](https://surrealdb.com/docs/transactions-and-isolation)：事务使用snapshot isolation并检测同record写冲突，但应用仍需防止跨record write skew。
- [SurrealDB Hybrid Search](https://surrealdb.com/docs/learn/data-models/vector-search/hybrid-search)：全文、向量和RRF可以在同一多模型数据库内组合；采用前仍需真实版本探针。
- [SurrealDB Graph Model](https://surrealdb.com/docs/learn/data-models/graph/overview)与[Record References](https://surrealdb.com/docs/reference/query-language/language-primitives/record-references)：支持显式依赖边、反向引用和删除行为建模。
- [SurrealDB Live Queries](https://surrealdb.com/docs/learn/querying/real-time/live-queries)：适合已提交变化的实时通知，但不替代持久事件和可靠重放。
- [SurrealDB Analyzers and Tokenizers](https://surrealdb.com/docs/learn/data-models/full-text-search/analyzers-and-tokenizers)：索引前应使用`search::analyze()`验证实际分词，中文仍保留已验证的jieba路径。
- [Spectron Principles and Goals](https://surrealdb.com/docs/spectron/architecture/principles-and-goals)、[Tri-temporal Model](https://surrealdb.com/docs/spectron/architecture/tri-temporal-model)、[Coherence and Retrieval Tiers](https://surrealdb.com/docs/spectron/architecture/coherence-retrieval-and-tiers)与[Spoiler-safe Narrative Memory](https://surrealdb.com/docs/spectron/cookbooks/patterns/spoiler-safe-narrative-memory)：仅作为来源优先、三时态、非静默协调、分层检索、trace和剧透安全的设计参考；本系统不接入或预留Spectron。
- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode)：结构化输出需要JSON模式、合理max tokens和空结果处理。
- [DeepSeek Context Caching](https://api-docs.deepseek.com/guides/kv_cache)：缓存依赖完整公共前缀且仅best-effort。
- [DeepSeek Rate Limit & Isolation](https://api-docs.deepseek.com/quick_start/rate_limit)：供应商并发、429和keep-alive必须与产品调用次数限制分开处理。

本地 `surrealdb-docs-cache` 是调研缓存，不是运行时或版本权威。由于本次审计发现429正文和少量URL/正文错配，实施时只采用路径、标题、正文相互一致且能由实时官方页面或真实二进制探针复核的能力；缓存摘要中的“成功”不能代替语义正确性检查。
