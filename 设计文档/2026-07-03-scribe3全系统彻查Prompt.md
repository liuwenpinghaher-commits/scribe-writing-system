# scribe3 · 全系统彻底审查 Prompt(对抗验证版 v1)

> 适配自「专访 1.0 全系统彻查 Prompt」。用法:多 agent 并行按维审查 → 对抗验证 → 运行时验证 → 汇总。
> 与 2026-07-03 的《全系统架构与业务闭环审计》(29 问题/44 断链)方法论互补:那次是"字段级生产-消费闭环";本次编码的是**抓真 bug 的纪律**——生产可达性验证、判别实验、不变量审计、公理对撞——并把误报坑(信文档不信运行时、"零消费"误报、旧报告过时)写成铁律。
>
> **基准**:审查开始时的 HEAD commit(记录之)。在途事实:工艺引擎 P0 的 T8-T11 未实施、审计修复批A-E 未启动、块四b 未做——**已知未完成事项不作为发现**;app.py 写作注入区与 ContainerOutline/NorthStar 区可能有并行 agent 在途改动,发现须以复核时的实际代码为准并注明。

## 系统速写(供审查者定向)

中文长篇小说 AI 写作引擎:SurrealDB(每书一 DB,ns=scribe3)权威库 + FastAPI(:3321,~100 端点)+ React/Vite 前端(:3311)+ Hermes LLM 网关(唯一 LLM 出口,llm.py)+ MCP 工具层(tools/mcp.py,48 工具,门控写)。核心域:五阶段写作流(大纲/节拍/演绎/草稿/正文)、限知视角引擎(knowledge.py:proposition/knows/reader_knows/project_frame/dramatic_irony)、ingest 反哺(定稿→LLM 抽 learned/did/arc/voice_shift/motif/promise_touch/belief→购幂等 purge 重写)、伏笔生命周期(tier/窗口/触及/salience)、弧光(锚五要素+lie_belief)、章前组装器(brief.py)、确定性检测管线(critique.py)、素材库(非正典,物理隔离)、主编对话(讨论/写作双模,⟦PROPOSAL⟧ 围栏,stageProposal 通道)、选中总线(selectionContext/focusTalk)。

### 铁律(违反任何一条,该发现作废)

1. **运行时真相优先**。系统能力以 `scribe3/app.py` 实际注册的路由(`@app.get/post/patch/delete`)与实际接线为准;设计文档/旧审计/注释/记忆只当线索。本项目实证:4 个检测器实现且测试绿但产品零接线;README 级能力(限流/熔断)是死代码;promise 窗口函数曾零消费方。**能力存在 ≠ 生产可达。**
2. **测试绿 ≠ 生产可达**。pytest 直连 store 内部对象;生产要经过端点→store→SurrealDB 的真实链路与 work 参数;前端 `tsc --noEmit` 是假绿(真检查是 `npm run build` + vitest)。必须验证"生产路径真的走到":端点有没有人调(grep api.js/mcp.py)、UI 有没有入口、注入块有没有拼进最终 prompt(读 `_editor_system`/`_editor_write_system` 的实际拼接)。
3. **fail-safe 是掩盖器**。scribe3 到处是 non-fatal try/except(ingest 各循环、embedding、_resolve_* 静默跳过、后台 ingest 只 warning)。审它们的不是"存在与否"(单机可用性取舍是设计),而是:降级发生时**有没有信号**、降级后**语义还对不对**、会不会掩盖上游真错(实证:apply_schema 把失败迁移标已应用 → schema 漂移不可自愈)。
4. **每个发现要证据**:file:line + 触发条件 + 具体失败场景(什么输入/状态 → 什么错误结果)+ 复现方式(pytest/curl/UI 步骤)。能复现标 `CONFIRMED`,仅静态推理标 `PLAUSIBLE` 并说明缺什么证据。
5. **区分缺陷与设计决策**。对照文末「有意设计清单」;挑战设计须论证"当初的代价权衡已变化",不许直接当 bug 报。
6. **与已知问题去重**。文末「已知问题清单」(29 项审计 + 各块遗留清单)已排入修复批A-E;重复报出记 `DUPLICATE_KNOWN` 剔除。**但已知问题的新变体/新影响面/新根因算新发现**(须写明与已知条目的差异)。
7. **自我反驳 pass**。定稿前对每条做"如何证明它不是问题"的反向论证,反驳与回应写进条目。

### 执行阶段

- **阶段 0 · 盘点(以实际为准)**:产出"系统真实能力地图"——(a) 全部路由(grep `@app\.` scribe3/app.py);(b) 数据实体(migrations/001-055 累积终态 × store.py CREATE/UPDATE 反推隐式字段);(c) 前端 API 调用点(web/src/api.js 每方法的消费组件);(d) MCP 工具清单与门控(tools/mcp.py);(e) env/开关(grep SCRIBE3_/环境变量);(f) 检测器清单(critique.py 全部 find_*/quality_* 及各自消费方);(g) prompt 组装点清单(所有拼 LLM prompt 的函数)。
- **阶段 1 · 分维并行审查**(九维,独立、只读、产候选)。
- **阶段 2 · 对抗验证**:逐条复核 file:line、写复现、做反驳、与已知清单去重、定级。
- **阶段 3 · 运行时验证**(与阶段 1 可并行):pytest 全量基线;`npm run build`+vitest;对 :3321 跑只读判别实验(GET 端点全扫、/quality、/chapter-brief、/promises/ledger、跨端点口径对撞);**通读可得的后端输出/日志**,每条 warn/error 归因。红线:不重启在跑的后端、不对真实书(book_c256380e)做任何写、写实验一律用临时 work 且用后删。
- **阶段 4 · 汇总分级输出**(格式见文末)。

### 九个审查维度(每维给"怎么查")

**A · 架构与分层**
- 分层契约:store.py(`_execute_write` 唯一写入点纪律——grep `_db.query` 找绕过者)/ knowledge.py(限知投影)/ critique.py(确定性检测,唯一例外 tension rubric)/ ingest.py(反哺)/ brief.py(章前组装)/ llm.py(唯一 LLM 出口——grep requests/httpx 找绕过 Hermes 的外呼)/ app.py(路由,不该手搓状态)/ tools/(MCP)/ web(前端)。查穿透与双头真相。
- 双表示一致性:promise 的存储窗口(payoff_min/max)×计算态(promise_window_state)×_overdue_flag 三处口径;synopsis 的书级/章级;narrative_position 双时态(story_chapter vs narrative_position);检测器的 flags 版 vs issues 带 offset 版。
- 全局机制完备性:**所有** LLM 调用点都走 hermes_complete/_stream 吗?超时/重试口径一致吗?prompt 组装点(阶段0-g)有没有第二套注入逻辑漂移(GET/POST 注入不对称是已知,查还有没有同类)?
- 包装器/工厂:_store_for 的 LRU 语义;_client 测试与生产的差异面。

**B · 业务流程(以作者旅程端到端走查)**
旅程清单:①建书→立设定/角色/锚 ②五阶段逐章(大纲→节拍→演绎→草稿→正文,含阶段间数据流转) ③存为正文→checkpoint→ingest→下章限知帧反映新知 ④伏笔全生命周期(plant→touch→窗口→advance/展期/abandon→ledger/quality 呈现) ⑤母题/弧光(锚→belief→里程碑)/关系 ⑥主编对话全模式(讨论/chatWrite/围栏/多候选/stageProposal 落地/聚焦话术/chiefIntent) ⑦质检环(/quality、/post-check、/tension-check、draft 检测)→修订 ⑧素材库(建→搜→插入草稿→聚焦) ⑨多书(建第二本→隔离验证→切换) ⑩版本/checkpoint(落版→恢复→对比) ⑪横切视图消费(时间线/图谱/仪表盘/体检 cron)。
每步五问:前置条件谁保证?失败分支去哪(用户看到什么)?幂等吗(双击/重试重放)?并发另一写进来会怎样?**UI 有入口吗**(存在但无入口 = 死功能)?
- 状态机 producer/consumer 矩阵:promise.status×resolution×kind×tier、chapter 的阶段字段(synopsis/beats/scene_truth/deductions/draft/prose)、char_state.change_type 六值、motif、material.kind、ingest_unverified、voice_evolution_flag、chapter_version.kind——每个值谁写谁读、有没有写而无读/读而永不出现、非法迁移有没有拦。

**C · 数据生命周期(核心维度,逐实体建账本)**
31 表逐表:生产(谁建、字段完整性、id 规则)/ 存储(surql 约束×store 写入一致?typed 字段与灵活 dict 有没有影子真相?)/ 消费(谁读?secret/限知门控在每条消费路径口径一致吗——域层过滤 vs SQL WHERE vs 前端展示?)/ 演化(更新会不会覆盖作者手工确认?ingest 重跑 purge 幂等对每类 ingest 产物都成立吗——proposition/knows/reader_knows/char_state/motif_instance/promise_touch 逐个验)/ 删除(级联完整吗?删章/删角色/删书的联动;删除后重引入会悬空吗——learned 跨章复用保护是先例,查同类)。
- 五类病:孤儿字段、幽灵读、双写发散、断链、无限增长表(chapter_version 已知,查还有:promise_touch/motif_instance/char_state/daily_progress/reader_knows 有 retention 吗)。
- 书稿数据安全(单机版"隐私"):哪些路径可能覆盖/丢失作者正文(prose)?checkpoint 恢复的覆盖面?e2e 脚本的快照恢复纪律有没有产品级等价物?

**D · 一致性与不变量**
- scribe3 不变量清单并查缺口:①角色只能知道其知识帧内命题(写作产出层谁保证?);②reader_knows 随叙述单调递增(purge 会破块吗——purge 后 reader 边被清,读者"忘了"已读内容,语义对吗?);③synopsis 单一真相源;④max_chapter 口径单源(chapter∪event);⑤_overdue_flag 单源;⑥窗口边界 next_ch==payoff_min 属 in_window;⑦每书一 DB 物理隔离;⑧素材不进任何分析管线。
- **设计公理对撞矩阵**:列全全局假设(H1 每书一DB隔离、H2 ingest purge 幂等、H3 learned 跨章复用保护、H4 保存即后台 ingest、H5 checkpoint(final) 也 ingest、H6 markdown 序列化往返无损、H7 focalizer 空=作者全知、H8 演绎 merge-latest、H9 suppress 一次性标记、H10 busy 冻结 fKey、H11 stageProposal 单槽 last-wins、H12 每保存落 final 版本、H13 store LRU=8 驱逐、H14 检测器纯确定性、H15 MCP 固定 SCRIBE3_WORK……),**两两对撞**找碰撞场景。已实证 H4×H5 碰撞 = 双 ingest 竞态(P0-1)、H1×H15 = 串书(P0-2)——同类碰撞大概率不止两处(候选:H2×H3 复用命题的边被他章 purge 波及?H6×生成内容含 `*`/`#` 字面量?H12×H13 驱逐时后台任务持旧连接?H9×H10 聚焦与镜像交错?)。
- revision/版本链:chapter_version 的 kind 语义、恢复路径(restore 谁调)、恢复后 ingest 状态与知识账本还一致吗(恢复旧正文但 knows 边是新的——有没有"恢复即重 ingest"或至少警告?)。

**E · 降级与失败路径账本**
grep 全部 `except`/`fallback`/`warning`/`fail.?safe`/`降级`/`兜底`(py)与 `catch`/`console.warn`(jsx),每处记录:{触发条件, 降级行为, 可观测信号, 降级后语义是否仍正确, 会否掩盖上游真错}。重点:LLM 失败/超时/parse_failed 重试耗尽、embedding 失败(语义召回静默缺块)、_resolve_char/motif/promise 静默跳过的累积面、前端 persist .catch(块一修过演绎,查其余——**静默丢作者文字最优先**)、SSE/live 断连、后台任务异常。

**F · 秘密与注入(scribe3 版安全)**
- secret 命题屏蔽全链:存储(secret 标记)→限知帧(masked)→主编 prompt(全知模式显式含私密 vs 限知模式屏蔽——分支口径)→图谱打码→时间线/仪表盘→**日志**(secret value 有没有进过 logging?)→MCP 只读工具(s3_ 系列会不会把 secret 吐给未门控调用方?)。
- 凭据:SurrealDB root/root 默认凭据、Hermes key 的读取/日志/错误响应泄漏面;.env/config 有没有进 git。
- prompt 注入面:书稿文本/素材/母题名/伏笔文本内插进 system prompt(brief.py 已做换行清洗,查其余内插点:_codex_block、voice、craft_rule.pattern——作者可控文本能不能伪造指令段头)。
- 破坏性端点:purge/delete 类端点的误触面(前端有没有确认;MCP 写门控覆盖全吗)。

**G · 并发与时序**
- 后台任务矩阵:BackgroundTasks(_bg_ingest)× 请求线程 × _stores LRU 驱逐 × SSE live——交错语义逐对推演(已知 P0-1/P2-2/P2-3,查新变体)。
- 前端:dirtyRef flush × 切换 × 服务端回读(块一修过主路径,遗留双 PATCH 竞序在案);stageProposal 单槽覆盖;suppress 标记 × 多导航源;busy 冻结 × 切章 abort。
- 幂等清单:全部 POST 重放一遍的语义(双击面)——plant_promise 重复埋?ingest 重跑?checkpoint 连点(已知)?arc-beats 重复建?
- SurrealDB 单 ws 连接的请求交错(P2-3 已知,查具体高危对:transaction 收集期间另一线程写入会怎样?)。

**H · 观测与运维**
- 静默失败信号:ingest 失败(已知 P1-6)之外——embedding 失败后语义检索缺块有信号吗?migration 失败(已知 P1-7)?体检 cron 只查 main(已知 P2-9)?
- 日志三查:关键路径缺日志/噪声日志/书稿内容与 secret 入日志。
- 运维真实可用性:migrate.py/qc_scan.py/health.py 真跑一遍(dry-run,只读档);备份/导出能力存在吗(若无,列为观察而非 bug——单机 SurrealDB 文件即备份,但要确认数据文件路径与丢失面)。

**I · 前后端契约**
- api.js 每方法 × 端点响应 shape 逐对;错误语义(404/409/422/500)前后端一致吗;端点改了 shape 前端跟了吗(近期 promise 行加 tier/window 字段——PromisesPanel/ledger 消费到了吗,还是拿旧字段?)。
- 前端状态覆盖:空态/加载/错误/成功;后端产出但 UI 永不展示的死数据(voice/craft_rule 已知,查新增:promises_with_lifecycle 的 window 态、brief sections、tension-check items 有前端消费吗——**注:T10 未实施,brief/tension 无前端属已知未完成,不报**,但查"已有前端的面板拿不拿新字段")。
- markdown 往返:块一的 md↔tiptap 转换在四阶段真实数据形态下的损耗尾巴(已知 Minor 清单在案,查新形态:LLM 生成的表格/有序列表嵌套/长破折号)。

### 方法与工具

- 结构理解 codegraph(`codegraph explore/node`)优先;但"零消费"判死刑前必须文本 grep 复核(codegraph 有过未消费误报)。
- 验证:`scribe3/.venv/bin/python -m pytest scribe3/tests -q`(全量基线应全绿,~10min);`cd scribe3/web && npm run build && npx vitest run`;e2e 参考 `scribe3/web/e2e/`(快照/恢复纪律)。
- 判别实验:curl :3321(在跑的后端;只读 GET 随意;写实验只对临时 work,用后删)。无 body 的 POST 注意 FastAPI 422 面。
- **红线**:不重启在跑的后端;不对 book_c256380e 做任何写;不跑会改真实书稿的 e2e(除非先快照后恢复且注明)。

### 有意设计清单(不要当 bug 报)

- `_execute_write` 唯一写入点 + 事务收集拼单条 surql(SDK 不支持跨调用事务的绕法)
- fail-safe ingest:抽取失败不阻断存稿、_resolve_* 匹配不到不建实体(防幻觉污染)、non-fatal 循环
- 素材库物理隔离(不 ingest/不进图谱/不进分析)是规格;素材插入草稿走 stageProposal 而非直写是规格
- 每书一 DB;work 参数贯穿 REST;MCP 固定 SCRIBE3_WORK 是**已知缺陷**(P0-2)非设计
- 限知全知双模:focalizer 空 = 作者全知(含私密)是有意;主编全知注入"(私密/伏线)"标记是有意
- 检测器管线确定性优先(不跑 LLM;tension rubric 是显式例外)
- 草稿保存 = 版本化落库(无失焦自动存是取舍);演绎 merge-latest;markdown 零依赖转换(不引 tiptap-markdown 包)
- e2e 真机脚本要求快照/恢复纪律是项目规范
- demo/种子:bt_seed.py 存在;测试用独立内存 SurrealDB(conftest 每测试一实例)
- 平静接受:单机单用户无 auth、SurrealDB 本地 root 凭据(列观察不列 bug,除非有远程暴露面)

### 已知问题清单(去重用;报出即 DUPLICATE_KNOWN)

审计29项:P0-1 双ingest竞态;P0-2 MCP串书;P1-3 promise_kind↔kind漂移;P1-4 命题/secret无UI生产入口;P1-5 事件图断链因果假绿;P1-6 ingest失败静默;P1-7 apply_schema失败标已应用;P1-8 world_rule.scope枚举漂移;P1-9 物品状态双断链;P1-10 四检测器零接线;P1-11 声音后半环UI黑洞;P1-12 限流熔断死代码;P1-13 MCP文档断链;P2-1 自动final版本刷屏;P2-2 /works全量开store+LRU驱逐竞态;P2-3 ws连接跨线程;P2-4 GET/POST注入不对称;P2-5/6/7 [已规划A线];P2-8 motif_terms跨书;P2-9 cron口径漂移;P2-10 死端点;P2-11 半成品旋钮;P2-12 set_intent整体替换;P2-13 跨章一致性全量扫;P2-14 051缺号;P2-15 死字段死代码合集;P2-16 切章自动保存烧LLM。
各块遗留(设计文档《写作台二轮》§七.5):双PATCH竞序、A→B→A过期加载、markdown Minor 群(`- - -`漂移/ul吃星号行/docToMd无单测/setChars重渲)、useDirtySave 待提炼、素材树拉body/kind白名单5处散落/focus枚举未收口、聚焦payload未结构化传后端。
A线P0在途:T1-T7 已落地(伏笔窗口/触及/弧光锚/lie_belief/brief.py/端点注入),T8三态注入、T9张力检查、T10前端露出、T11端到端**未实施**——缺这些不是发现。

### 重点怀疑区(线索,须重新验证后才算发现)

- WriteLayout/ChiefDock 巨型组件的状态机与竞态残面(块一二三修了大头,查残余)
- 限知引擎边界:knows 边的 until_chapter/polarity 消费面;project_frame 对"忘知""误信"的语义;dramatic_irony 的口径
- ingest learned 去重(_find_existing_learned_prop 的包含匹配)误合并面:两个不同事实互为子串?
- purge 幂等 × learned 复用保护的边界(重 ingest A 章后 B 章复用命题的 reader_knows 边)
- 语义检索链(semantic_index/embedding→召回)的实际接线与失败面
- 时间线双时态(narrative_position 回退 story_chapter)的消费一致性
- brief 组装 N+1 与注入总长在真实规模下的账(已裁定可接受,查规模临界点)
- checkpoint 恢复 × 知识账本一致性(恢复旧正文后 knows/char_state 是新的)
- Hermes 网关双模(chat 速答 vs agentic 联查)与 s3_ 工具的门控一致性
- ContainerOutline/项目树在 100+ 章书的量级(outline 停拉全文的既有优化还成立吗)

### 输出格式

1. **执行摘要**:九维各一句话结论 + 问题计数(按严重度)。
2. **发现清单**(最严重在前),每条:`{P0-P3, CONFIRMED/PLAUSIBLE, 维度, 标题, file:line, 失败场景, 复现方式, 根因, 修复方案草案, 影响面, 反驳与回应}`。
3. **覆盖证明**:已审且无问题的区域清单(维度×模块矩阵,注明验证方式)——没有这个,"没发现"≠"没问题"。
4. **不建议做清单**:看似问题但修复代价 > 收益,或属有意设计。
5. **方法自评**:哪些区域没到达、置信度低,下一轮建议。
