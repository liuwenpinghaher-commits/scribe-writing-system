# Gate C/D：字段—功能—上下文—质量价值矩阵

> 状态：执行中。本文是 Gate C/D 的验收台账，不是“功能已完成”的声明。
>
> 真源：`docs/CURRENT_ARCHITECTURE.md`、当前运行代码与真实 UI/MCP/SurrealDB 证据。

## 已完成的前置门槛

| Gate | 结论 | 真实证据 |
| --- | --- | --- |
| Gate A | PASS（运行基线） | React :3311 → FastAPI :3321 → SurrealDB；Hermes `0.18.2`。 |
| Gate B | PASS（2026-07-27） | `book_dafb9436`：预览 Run `run_c4c6351afd3148df81e1fd43f9112b8c`；受限写入 Run `run_172a53bf783044aea8db7ffd8c4e309f`；真实 UI 刷新后批准、`s3_patch_chapter_plan`、SurrealDB/UI 回读、trace `completed`。 |

Gate B 的回归修复：Run 事件现在由服务端唯一 collector 消费；浏览器 SSE 仅订阅。作者在待审批时刷新或断开，不能丢失 `tool.completed` / `run.completed` 审计尾部。

## 判定规则

每个条目都必须具备下列六项，缺任一项即不是 PASS：

1. 作者可达的 UI 输入或可解释的“让主编写入”入口；
2. MCP 审批边界正确（正典写入不可走 REST 旁路）；
3. SurrealDB 回读、刷新回读、跨会话/跨章影响符合语义；
4. 能证明它实际进入了正确的上下文、检索、质量判断或写作控制点；
5. 输出按固定质量维度评估，且能给作者具体决策价值；
6. 失败、冲突、缺失、超预算、跨书隔离等反例经过验证。

证据等级：A=真实 UI+Provider+MCP+DB+刷新；B=真实服务链但少 UI；C=自动化；D=仅代码；E=未知。

## 字段总清单：Codex 注册表

当前 `scribe3.codex_schema.KINDS` 注册了 64 个顶层字段；嵌套对象字段须随其父字段一并填充和验收。`private_operation` 标记为 deprecated，不得为了“填满”而填造内容；应验证迁移提示和替代字段。

| 类型 | 顶层字段数 | 字段 | Gate C 状态 |
| --- | ---: | --- | --- |
| faction | 28 | `name,status,ideology,leader,known_members,public_face,first_mention_chapter,artifact_operation,external_manipulation,acceleration_methods,origin,internal_factions,structure,key_figures,artifacts,scale,recruitment,symbols,motto,goals,world_rule_affinity,aliases,timeline,headquarters,communication,rituals,secret_agenda,private_operation` | **27 个活跃字段及嵌套字段写入/回读 A 级通过；`private_operation` 已废弃，不填造内容；上下文消费仍被 Provider 阻断。** `book_759ab1db`：真实 UI → Hermes → `s3_add_faction` → 作者点击批准；Run `run_e0555a86a4e44719930a6587bc591da3` 为 `completed`，有 `s3_add_faction` 的 `written` 输出。公开视图掩码五个私密字段，作者授权详情返回原值；刷新后从“设定库 → 势力”可见「潮汐会」，且不显示 chief-only 私密议程。 |
| character | 14 | `name,aliases,appearance,personality_detail,personality_tags,backstory,surface_goal,deep_need,fear,internal_conflict,abilities,weaknesses,importance,first_appearance` | **写入/回读 A 级通过；上下文消费未闭环**。`codex_complete_profile_approval.mjs` 在隔离作品经真实 UI → Hermes → `s3_add_character` → 作者点击批准；公共列表正确掩码私密前史，作者解锁详情可回读原值，刷新后仍正确。2026-07-27 在 `book_ec6ad992` 复验中，角色后续经 `s3_add_chapter` 真实审批创建“设定消费章”。草稿请求已真实到达 `/chat/write`，但 DeepSeek 官方 Provider 返回 HTTP 401，未形成 assistant/Manifest，故不得声称字段已被写作消费。 |
| item | 7 | `name,category,description,symbolic_state,current_owner,first_chapter,special_properties` | **写入/回读 A 级通过；上下文消费被 Provider 阻断。** `book_9fd36852`：真实 UI → Hermes → `s3_add_item` → 浏览器批准 → DB/刷新回读；Run `run_f8d709d516654a45a200725f7246206c` 为 `completed` 且有 `written` 输出。 |
| term | 5 | `name,category,definition,aliases,first_mention_chapter` | **写入/回读 A 级通过；上下文消费被 Provider 阻断。** `book_c178d3b5`：真实 UI → Hermes → `s3_add_term` → 浏览器批准 → DB/刷新回读；Run `run_b34c90bd75f147fba38e13bdae65cc6f` 为 `completed` 且有 `written` 输出。 |
| world_rule | 10 | `name,category,source,cost,scope,established_chapter,limitations,exceptions,capabilities,note` | **写入/回读 A 级通过；上下文消费被 Provider 阻断。** `book_d1962048`：真实 UI → Hermes → `s3_add_world_rule` → 浏览器批准 → DB/刷新回读；Run `run_d165eed0df9f43418f14e86f61ab8997` 为 `completed` 且有 `written` 输出。 |

## 功能域执行矩阵

| 域 | 质量价值 | 上下文/权威路径 | 本轮要验证的反例 | 当前证据 |
| --- | --- | --- | --- | --- |
| 作者意图、题材、读者、主题、全书目标 | 为每次生成与评价提供可审计的“作品合同” | `s3_set_intent` → Surreal 正典 → 写作 envelope / 北极星 | 空泛意图、目标冲突、作者修改后旧上下文残留 | 未执行 |
| 人物与关系 | 保证欲望、恐惧、行动、弧光与关系张力可进入场景 | Codex character / relation / anchors / states → chapter brief / recall | 同名角色、限知泄漏、角色字段未进入 prompt | 未执行 |
| 世界规则、势力、物件、术语 | 使代价、限制、信物、权力关系约束剧情，而非静态百科 | Codex → world/graph/brief/context | 例外未声明、规则无代价、秘密字段误入生成 | 未执行 |
| 事实、事件、知识边、时间线 | 保护因果、时序、目击与读者信息差 | proposition/event/knows → project_frame / graph_recall | 时序倒退、角色知道不该知道的事、跨书泄漏 | 未执行 |
| 卷章结构、节拍、场景真相与限知演绎 | 让长篇结构真实约束正文，并允许作者逐步裁决 | chapter/brief/deduce → 受限 stage profile | 预览污染正典、拒绝仍写入、刷新失去审批 | Gate B: A；其余未执行 |
| 正文、版本、选择环、修订 | 将质量诊断落实为可比较、可回滚的稿件改进 | `_assemble_write_instructions` / version / outcome | 半成品假成功、版本错章、选择结果不进正文 | 未执行 |
| 素材、记忆、召回与上下文检查器 | 在预算内选取正确证据，区分素材、正典、作者偏好与过程记忆 | material recall / memory fabric / ContextInspector | 过期记忆、来源不明、参考材料污染正典、超预算静默截断 | 未执行 |
| 参考作品技法卡 | 以可迁移机制帮助结构与节奏，不复刻受版权保护表达 | reference import → fingerprint → author approval → quality judgment | 原文泄漏、近似改写、未批准指纹进入建议 | 未执行 |
| 固定维度质量判断 | 在作者判断前给出证据化诊断与优先级建议 | quality evaluation / author judgment / trace binding | 空泛评分、证据与正文不对应、作者否决被覆盖 | 未执行 |
| Pilot、收件箱、审批与恢复 | 把建议变为作者可理解、可拒绝、可追溯的决策 | run trace / inbox / pending claims | 后端存在但 UI 不可达、刷新丢状态、已失败显示完成 | Gate B: A；其余未执行 |

## Gate D 固定质量维度及验收输出

每次章节评价必须同时产出：评级/置信度、正文或正典证据定位、反证、修改建议、作者采纳状态、修订后复测。维度为：

1. 叙事目标与冲突；
2. 因果、揭示、悬念与兑现；
3. 人物欲望、行动、关系张力与弧光；
4. 场景目标、阻力、转折、余波；
5. 世界规则与代价兑现；
6. 时间线、空间、物件、伤病、知识连续性；
7. 视角、叙述距离、时态、语体；
8. 节奏、信息密度、重复与拖沓；
9. 对话角色化、潜台词与冲突；
10. 感官细节、动作、意象与情绪呈现；
11. 主题、母题与全书回响；
12. 原创性、陈词滥调与不当模仿风险；
13. 目标读者体验与题材承诺；
14. 与经作者批准的参考作品“技法层”对照。

## 后续执行顺序

1. 在新的隔离作品中以 MCP 审批填入所有可达 Codex 字段及嵌套字段；
2. 对每个字段回读存储、刷新 UI，并从 ContextInspector / manifest / 输出证据验证真正消费；
3. 完成事实—事件—知识—时间线与多书隔离反例；
4. 完成材料/记忆/参考作品/质量判断的真实 Provider 验收；
5. 只有所有关键项达到 A/B 级，才进入 50,000 字原创长篇闭环。

## 2026-07-27 运行时增量证据（未改变总判定）

- 已修复作品级 Run 刷新恢复：服务端 `GET /ai/runs/pending-approvals` 现可在不传章节 scope 时只返回本书的作品级待审批 Run；前端从审计链重建审批卡，再继续 trace/SSE 恢复。真实浏览器已在旧的 `s3_add_chapter` Run 上重新显示“批准”按钮。
- 已修复 Hermes 审批载荷：服务端会把具体 `approval_id` 与 `choice` 一并传给 Hermes，避免作者裁决无法绑定到对应 MCP elicitation。修复后新隔离书 `book_ec6ad992` 的章节已经真实批准并落库。
- 不将上述恢复卡的旧 Run 记为端到端通过：该 Run 在服务重启后的长时间等待中已被 Hermes 以 `declined` 结束，且事件流有 404；它只证明“恢复卡可达”，不证明“恢复后批准写入成功”。
- 草稿阶段实际入口是右栏 `DiscussionDock`（不是 final 阶段才使用的 `WriteChat` portal）；已修正 E2E 对真实入口的选择。此前的 DeepSeek HTTP 401 已失效：当前运行态为阿里云 TokenPlan（Qwen 兼容接口、`qwen3.8-max-preview`），真实 `/chat/write` 已在上下文绑定门控后成功完成。**这只解除 Provider 阻断，不等于字段上下文消费和 Gate D 质量闭环已经通过；二者仍需分别取证。**
- 审批恢复新增真实反例修复：`approval_failed` 且 Hermes 已明确返回 `approval_not_active` 的 Run，旧版仍会因历史 `approval.requested` 在刷新后显示为待批准；现已在 `/ai/runs/pending-approvals` 排除。回归测试覆盖“失效审批隐藏”与两类有效审批恢复（3 passed），完整 `test_ai_runs.py` 为 **22 passed**；重启后的真实 API 对 `book_157f4d0a` 返回空待审批列表，真实浏览器进入并刷新该书后 `run-approve` 数为 0。该修复只隐藏已明确失效的审批，其他 transport 错误仍保留可重试入口。
- 势力全字段增量：`book_759ab1db` 的 `run_e0555a86a4e44719930a6587bc591da3` 是可用 A 级写入证据。工具为 `s3_add_faction`，审计状态 `completed`，工具输出 `written`；作者授权回读覆盖所有活跃字段与嵌套对象。公共详情中 `artifact_operation`、`external_manipulation`、`acceleration_methods`、`origin`、`secret_agenda` 均为 `🔒 私密`，刷新后真实浏览器进入“设定库 → 势力”可见该条目且不含 chief-only 议程原文。对应可复跑脚本为 `scribe3/web/e2e/codex_complete_faction_approval.mjs`；脚本的首次真实运行在对象深比较时暴露了键序误判，已改为 `deepStrictEqual`，该断言问题不影响已完成的写入与正典证据。
- 物件/术语/世界规则全字段增量：新增可复跑脚本 `scribe3/web/e2e/codex_complete_simple_registry_approval.mjs`，用 `E2E_KIND=item|term|world_rule` 逐类验证。三次真实浏览器运行均完成 UI 输入、Hermes Run、审批点击、正典回读、审计 `written` 与刷新回读：item=`book_9fd36852`/`run_f8d709d516654a45a200725f7246206c`；term=`book_c178d3b5`/`run_b34c90bd75f147fba38e13bdae65cc6f`；world_rule=`book_d1962048`/`run_d165eed0df9f43418f14e86f61ab8997`。三个 Run 均为 `completed`，不包含 Provider 生成链证据，故不外推为上下文或质量闭环通过。
- 运行配置增量：用户此前要求取消调用上限；当前运行时曾显示 `cap=100000`，与该要求不一致。已通过设置接口将 `SCRIBE3_DAILY_CALL_CAP` 写为 `0`（热生效）；实时 `/ai/usage` 回读为 `unlimited=true`、`remaining=null`。该项不属于小说正典写入，未绕过 MCP 世界状态边界。

## 2026-07-27 Run 生命周期与多书初始化增量（未改变总判定）

- **创建后未订阅 SSE 的 Run 不再遗失**：`POST /ai/runs` 在持久化 trace、阶段策略和发起时上下文绑定后，立即启动服务端唯一 collector；浏览器 SSE 仅作为订阅者。回归 `test_ai_run_creation_starts_server_collector_without_sse_subscription` 先以 `queued` 失败，修复后与完整 `test_ai_runs.py` 一起为 **23 passed**。真实无浏览器 SSE 探测：`book_collector_preview_e2e_1785131502992` / `run_be07f08301bf4f3eb22b9e0bb9690969`，Trace 为 `completed`，持久化了 6 次只读工具调用及对应输出、无策略违规。
- **首次打开同一作品的 API/MCP schema 竞态已修复**：此前 API 与 Hermes MCP 独立进程同时初始化新 `work` 时，SurrealDB 会返回可重试的 transaction conflict，旧实现又以 `CREATE` 写 `_migration` 标记，造成 `_migration:<name> 已存在` 并阻断正常读取。现在迁移标记改为幂等 `UPSERT`，`apply_schema` 对可重试事务冲突有限重试。并发回归 `test_apply_schema_concurrent_initializers_share_one_migration_record` 及相邻 migration 回归共 **3 passed**。重启 `scribe3_deduce`/`scribe3_deduce_preview` profile 后，新的真实隔离作品预览读取已不再出现 migration 冲突。
- **边界说明**：上述 preview Run 是运行时与多书初始化证据，不是正文质量验收。它没有生成或写入正典；当前 Provider 已切到可用的阿里云 TokenPlan，但 Gate C 的字段上下文消费与 Gate D 的真实质量闭环仍待逐项验证。

## 2026-07-27 图谱审批全链路增量（未改变总判定）

- `graph_semantics_approval.mjs` 在隔离作品 `book_01888fac` 以唯一 case=`ms2vmh1m` 依次完成 `s3_add_character`、`s3_add_fact`、`s3_add_event`、`s3_add_character_relation`、`s3_record_knowledge`。五个 Run（`run_78b885e80ae245c5922a6168a201a818`、`run_f54ddc2f689141c8bab747c88ffc7bb5`、`run_e6848ccf937e40af876bd38bc8743642`、`run_8f5db047267f41c59288d456bf073ff7`、`run_85058aa4b3ad43ef869a0d596ca3a54e`）均为 `completed`，目标工具输出均为 `written` 且作者决议为 `approve`。
- 真实浏览器执行“主编输入 → 审批卡点击 → 刷新回读”；API 图谱回读到 `role:许棹ms2vmh1m -> knows -> fact:潮纹船票归属_ms2vmh1m` 与 `role:林雾 -> 盟友 -> role:许棹ms2vmh1m`，时间线回读到 `ev:船票交付_ms2vmh1m`。刷新后再点击浏览器“图谱”“时间线”，均显示本轮节点/事件。
- 本轮修复两项验收/审计缺陷：关系读模型返回裸角色名，E2E 不再误期待 `role:` 前缀；当 `run.completed` 与审批事件乱序时，未决写审批 fail-closed 为 `timeout/declined`，但已决或随后真实批准会回填为 `approve/written`，不再把真实批准倒灌为超时。新增四条存储回归覆盖这三种顺序与晚到批准。
- 这只让“事实—事件—关系—知识—图谱/时间线”功能域达到 A 级写入与回读证据；它尚未证明这些信息已影响生成正文，也未完成跨书隔离反例或 Gate D 质量闭环。
