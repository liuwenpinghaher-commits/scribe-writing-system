# scribe3 · 全系统彻底审查 Prompt(对抗验证版 v2,2026-07-06 修订)

> v1→v2:注入 2026-07-05/06 两轮大改造(北极星三环、遗留处置三批、断头修复批、主编主动化 P0+P1)的全部实战教训。v1 时代的 29 项审计、22 断头、D-001~D-032 台账问题**已全修**,列入去重清单;新增四条铁律(前端最后一厘米/运行时活性/B-3 同型/stub 完整性)与三个新审查面(北极星三环、Chapter Pilot、脉搏与时机引擎)。
> 用法:多 agent 并行按维审查 → 对抗验证 → 运行时验证 → 汇总。基准 commit 审查开始时记录(当前 7f08a7f)。

## 系统速写(供审查者定向,2026-07-06 现状)

中文长篇小说 AI 写作引擎:SurrealDB 3.1.5(每书一 DB,ns=scribe3,:8001,生产文件 ~/.scribe2-surreal/data.db)+ FastAPI(:3321,~120 端点)+ React/Vite(:3311)+ Hermes 0.18 网关(:8643 scribe3 profile,唯一 LLM 出口 llm.py,日调用帽单点)+ MCP 工具层(mcp.py,s3_ 前缀,elicitation 门控写)。

核心域(★=v2 新面):
- 五阶段写作流(大纲/节拍/演绎/草稿/正文)+ 限知引擎(project_frame/dramatic_irony/find_leaks)+ ingest 反哺(幂等 purge)+ 伏笔生命周期(tier 窗口/touch/salience/refresh_count)+ 弧光(锚+lie_belief)+ 章前简报(brief.py)+ 确定性检测管线(critique.py,含时间线检测器/filter-words 未做)+ 素材库隔离 + 主编双模对话。
- ★**北极星三环**:修复环(POST /loop/chapter:triage 四判据①leaks②degeneration blocking③ai_grade heavy④S1→regenerate≤2轮→needs_human;S1=纪律判×确定性共振三刹车[降档/共振表 kind 收窄/熔断>30%];advisory 永不自动重写)、沉淀环(chat→distill lesson[增量]→brief 反哺;升格待批)、选择环(关键章 3 候选→过滤→全循环赛 rubric→半盲终选)。
- ★**Chapter Pilot**(pilot.py+app.py Pilot 段):状态机 idle→outline_proposed→beats_ready→deduced→drafting→checked→delivered→finalized;授权 auto/propose/approve,宪法锚 finalize 硬编码;跳步协议(字段已有不覆盖);停靠协议(pilot_park/needs_human/advisory 如实停);连写 /pilot/run(交付即续,终选留人);想法收件箱 /ideas(#想法 前缀,五类路由,setting/revise 永远待批);_pilot_inflight 与 _loop_inflight 双锁体系。
- ★**脉搏与时机引擎**:/chapter-pulse 六维(decision 全源确定性信号,无总分)、PulseBar、/inbox 五源、进章开场白/落稿摘要/卡文探测/讨论 digest 注入(seq→lastSeq 传递链)、防烦协议(每章每维一次/静音/带依据,localStorage 记账)。

### 铁律(违反任何一条,该发现作废)

1. **运行时真相优先**。能力以 app.py 实际路由与实际接线为准;文档/旧审计/注释/记忆只当线索。实证史:4 检测器实现且测试绿但零接线;限流熔断死代码;/health 曾纯桩。
2. **测试绿 ≠ 生产可达**。pytest 直连 store;生产要走端点→store→DB 真链与 work 参数;前端 `tsc --noEmit` 假绿(真检查 `npm run build`)。
3. **fail-safe 是掩盖器**。审降级:有没有信号、降级后语义对不对、会不会掩盖上游真错。
4. **每个发现要证据**:file:line+触发条件+失败场景+复现方式;CONFIRMED/PLAUSIBLE 分标。
5. **区分缺陷与设计决策**(对照有意设计清单);挑战设计须论证权衡已变。
6. **与已知清单去重**(文末);已知问题的新变体/新影响面算新发现,须写明差异。
7. **自我反驳 pass**:每条做反向论证并写进条目。
8. ★**前端最后一厘米**(本系统最高发缺陷形态,22 断头实证)。凡功能类发现必须**追信号链到终点**:UI 入口存在→回调真被绑定→状态真变化→请求真发出→端点存在且被这个前端调→响应被消费渲染。任何一环断=「断在半路」并指明断点。原型案例:Rail 折叠信号在源头发出、被中间一行 `k || active.key` 吞掉;/draft-check 后端+测试全绿两天、前端零调用。判定三档:闭环/断在半路(断点 file:line)/未做。
9. ★**build 绿 ≠ 运行时活**。esbuild 不查 TDZ/运行时引用(实证:renderCheckupCard 定义在调用点之后,build 绿页面崩,ErrorBoundary 吞掉连 pageerror 都没有——中区静默变"界面出错了")。前端发现的验证优先级:Playwright(pw_pilot_smoke.mjs 已入库可扩)>浏览器手测>纯静态推理(必须标 PLAUSIBLE)。查 ErrorBoundary fallback 是否吞过崩溃:真机各主视图走一遍看有无"界面出错了"。
10. ★**B-3 同型防**(prompt 注入类专用)。"指令说『据 X 写』但 X 从未进 prompt"在本系统已三次复发(大纲注入/演绎 scene_truth/时机C digest)。凡审 prompt 组装:断言**具体内容**在最终 prompt 里,不是段标题在;凡新增注入:查所有调用方是否都传了触发参数(phase/seq)。
11. ★**测试 stub 完整性**。`set_complete_fn` 只覆盖 `_complete_fn` 通道;`hermes_complete/hermes_complete_stream/hermes_responses_events` 直连处必须 patch scribe3.llm 模块属性(实证:pilot 测试首跑烧真网关生成整章)。审测试时查:stub 是否拦了被测代码的**全部** LLM 出口;stub 判据是否会被 system prompt 内容误触(实证:"纪律"字样判据被写作链 system 误吞)。
12. ★**检测器误报纪律**。新检测器/新阈值上线前必须真章标定(实证:时间线检测器 9 达标章首跑 7/7 误报——跨夜顺行/比喻追述/人名"柳三更"三类根因;密度标定发现切片判档整体不稳)。审任何检测器:找它的标定证据;无标定=PLAUSIBLE 顶格。

### 执行阶段

- **阶段 0 · 盘点**:路由全量(grep `@app\.`)/迁移终态(001-069)/api.js 消费点/mcp.py 工具/env 开关(SCRIBE3_*)/检测器清单及消费方/prompt 组装点清单(_editor_system/_editor_write_system/_assemble_write_instructions/_pulse_digest/_pilot_llm_gen/build_*_prompt 族)。
- **阶段 1 · 分维并行审查**(十维,见下)。
- **阶段 2 · 对抗验证**:复核/复现/反驳/去重/定级。
- **阶段 3 · 运行时验证**:pytest 全量基线(仓库根跑!cd scribe3 会被 mcp.py 遮蔽);npm run build;**pw_pilot_smoke.mjs**;对 :3321 只读判别实验;读后端日志逐条归因。红线:不重启在跑后端、不写真实书(book_c256380e/book_bfd18b78)、写实验只用 loop-qa/pilot-qa 或临时 work 且用后删、门级全量 pytest 期间冻结 scribe3/*.py(inspect 伪影)。
- **阶段 4 · 汇总分级输出**(格式文末)。

### 十个审查维度

**A · 架构与分层**:store `_execute_write` 唯一写入纪律;llm.py 唯一 LLM 出口(grep httpx/requests 绕行)+日帽覆盖三出口;prompt 组装点第二套逻辑漂移;双表示一致性(promise 窗口三口径/检测器 flags vs issues);_store_for LRU;★pilot executor 是否绕过既有链自造生成逻辑(宪法:只编排)。

**B · 业务旅程端到端**(每步五问:前置谁保证/失败去哪/幂等吗/并发进来怎样/**UI 有入口吗**):
①建书→设定 ②五阶段逐章 ③存正文→ingest→限知帧更新 ④伏笔全生命周期 ⑤弧光/关系 ⑥主编双模+stageProposal ⑦质检环 ⑧素材 ⑨多书隔离 ⑩版本恢复 ⑪横切视图 ★⑫修复环全链(loop 三分流/回炉约束/journal+result.json)★⑬选择环(候选/过滤/rubric/终选理由入 lesson)★⑭Pilot 旅程(#想法→路由→step/run→停靠→收件箱→放行→终选;僵尸态 dismiss;advisory 停靠后作者怎么走)★⑮时机引擎(六维变色/开场白/落稿摘要/卡文/静音)。

**C · 数据生命周期**:31+表逐表账本(生产/存储/消费/演化/删除);五类病(孤儿字段/幽灵读/双写发散/断链/无限增长——promise_touch/motif_instance/char_state/reader_knows/**idea/pilot journal/localStorage 记账键** 有 retention 吗);书稿安全(哪些路径可能覆盖 prose——pilot 跳步协议保护面完整吗)。

**D · 一致性与不变量**:既有八不变量+★新增:⑨advisory 永不自动放行(pilot 停靠协议)⑩终选/升格/动圣经/伏笔弃置永远 approve ⑪pulse 无总分、decision 全源确定性 ⑫S1 仅共振升格且熔断可暂停 ⑬跳步协议不覆盖人工内容 ⑭连写不产终选背书版。
**公理对撞矩阵**(v1 的 H1-H15 之外新增):H16 跳步"字段已有=产物在"×作者故意清空重写流;H17 _pilot_inflight×_loop_inflight 双锁次序与死锁面;H18 steer 追加 2000 字帽×多想法尾部截断丢失;H19 连写循环×LLM 日帽×预算可见性;H20 pulse decision←promise_directives 语义漂移(directives 措辞变化会不会改变 severity 映射);H21 pilot_state SCHEMAFULL 字段×get_chapter 显式列(实证坑:读不到,已修 read_state 直查——查还有没有同类"新字段没进显式 SELECT");H22 sessionStorage seed 单槽×连续两次「聊这个」覆盖;H23 localStorage 记账键(s3.spoke.*)×多书同 seq 串扰(键含 work 吗——逐个验)。

**E · 降级与失败路径账本**:全部 except/fallback/catch 逐处记录五元组;重点:LLM 失败链、embedding 失败(已 fail-soft,查信号)、_resolve_* 静默、前端 persist catch(暂存机制已建,查覆盖面)、SSE 断连、后台任务、★pilot parked 的可发现性(收件箱之外还有信号吗)、★连写异常停靠后 run-status 的残留语义。

**F · 秘密与注入**:secret 屏蔽全链(存储→帧→prompt 双模→图谱→日志→MCP);★新注入面:pilot_steer/idea.text/低置信段自审输出 内插 prompt 的伪造指令面;★pilot_card/交付卡会不会带 secret;凭据面(SurrealDB root/Hermes key);破坏性端点确认面(dismiss/reset-step/ideas/resolve 的误触)。

**G · 并发与时序**:后台任务矩阵(_bg_ingest/★_pilot_run_bg)×请求线程×LRU×SSE;★连写期间作者操作面(step/approve/save/dedup/loop 六路互斥闭合吗——run 循环间隙窗口);前端竞态(dirtyRef/stageProposal/suppress/busy);幂等清单(POST 双击面,★/ideas 双发、★/pilot/run 双开 TOCTOU 已知记录在案查修复);ws 单连接交错。

**H · 观测与运维**:静默失败信号面;日志三查(缺/噪/泄);★pilot journal 完整性(每 action 都留痕吗;journal 文件按章覆盖还是追加);★时机引擎记账可审计性(开口≤4/章有脚本可验吗);运维脚本真跑(migrate/qc_scan[已多书]/health);备份面(数据文件路径+丢失面)。

**I · 前后端契约**:api.js×端点 shape 逐对;错误语义一致性;★新契约:pulse dimensions/inbox items(五源 kind 枚举前端全认吗——pilot_outline/pilot_delivered/pilot_parked/idea_*/needs_human/promotable_lesson/pulse_decision)/pilot status/run-status/交付卡 JSON;★前端死数据新查(后端产出 UI 永不显示:idea.note?pilot_card.promises?curve?)。

**J ·(新)LLM 链路质量与成本**:每个 LLM 调用点的 {prompt 规模, 频次, 触发方, 失败重试, 日帽覆盖};★pilot 单章全链调用账(大纲1+节拍1+真相1+投影N+loop≤3×[生成+纪律]+体检1+自审1≈10-15 发)——连写 10 章的成本可见性;★pulse/inbox 的查询放大(单次 pulse≈11-13 查询含 2 次全书扫描,三消费方各自拉);stub 完整性抽查(铁律11)。

### 方法与工具

- codegraph 优先结构理解;"零消费"判死刑前 grep 复核。
- 验证:仓库根 `scribe3/.venv/bin/python -m pytest scribe3/tests -q`(基线 1154 绿);`cd scribe3/web && npm run build`;`node pw_pilot_smoke.mjs`;curl :3321 只读。
- **红线**:不重启在跑后端;不写 book_c256380e/book_bfd18b78;写实验只用 loop-qa 或临时 work;全量 pytest 期间冻结 scribe3/*.py。

### 有意设计清单(不要当 bug 报)

v1 全部条目仍有效(唯一写入点/fail-safe ingest/素材隔离/每书一DB/限知双模/检测器确定性优先/草稿版本化/merge-latest/单机无 auth)+ v2 新增:
- **宪法全集**:不造总分;rubric/fulfillment 永不进 blocking;advisory 永不自动重写**且不替作者放行**;蒸馏升格永不自动生效;regenerate 复用完整组装链;停机判据只挂确定性项;终选/升格/动圣经/伏笔弃置永远 approve;S1 三刹车(单判恒S2/共振表收窄/熔断);pilot 只编排不造生成逻辑。
- 跳步协议(字段已有→skipped 不覆盖)是防覆盖人工编辑的**设计**,不是"pilot 不干活";想重提案=清空字段或未来 revise 通道。
- 连写不等终选即写下一章(loop pass 已 ingest,知识不断档;终选是背书不是数据依赖)。
- pilot 用独立 _pilot_inflight(预登记 _loop_inflight 会撞 loop 自身互斥)。
- 熔断进程内不落库(保护不是账本);时机记账 localStorage(轻;丢了重提醒一次可接受)。
- pulse 弱指纹缓存(跨章一致性扫 (count,Σ字数),同字数改动漏检可容——advisory 级)。
- 自定口径集(标定前提下可改不算 bug):S1 熔断 30%/短文本 500 字/共振表 3 条/刷新耗尽 3 次/弧光跳变 15/steer 帽 2000/digest 600。

### 已知问题清单(报出即 DUPLICATE_KNOWN)

**已全修(2026-07-05/06,勿再报)**:v1 的审计 29 项(P0-1~P2-16)与各块遗留;22 断头(D-029);北极星三轮审查 39 项(D-015/018/020);遗留处置三批(D-021~028:S1 接线/池A2/短文本/增量蒸馏/HNSW EF/时间线检测器/Hermes 0.18);主编主动化两轮审查 16 项(D-030~032:时机C 死线/seed 丢失/refresh 泄漏/跳变分档/卡文闭包/QC 死分支/needs_human 滞留/live 风暴/badge 死指标/advisory 假交付/并发背书/覆盖手写/ideas 脏值/审计链/体检消费/收件箱出口)。
**已知未做(裁决在案,不作为发现)**:工艺引擎 P1/P2 自排期 13 条(关系四轴/场景卡/MRU/情感曲线等,评测裁"不做/等触发",台账可查);M7.1 filter words 与 M9 卡文诊断话术已并入主动化(卡文=时机D);pilot P2(自治升级环/盲评节律)挂"真实连写≥10章"触发;authz book 级配置未接入(接入时须同步 gate==approve 停靠防御,D-032 钉住);pilot 崩溃窗口非原子(loop 互斥+版本库兜底,D-032 记录可接受);/pilot/run TOCTOU 已知记录;idea unclear 无收件箱承载(D-032);金标③纸命第5章=作者参与项。

### 重点怀疑区(v2 线索,须重新验证后才算发现)

1. pilot 全链成本与失败恢复的**真实长跑**面:连写 5+ 章会暴露什么(state 残留/journal 膨胀/steer 累积语义)。
2. pulse/inbox 查询放大在 50+ 章书的延迟(三消费方各自拉全书扫描)。
3. 交付卡 promises 字段/curve 数据的前端消费(刚加的字段有没有 UI 出口——铁律8 自查)。
4. 时机引擎 localStorage 键膨胀与多书串扰(H23)。
5. advisory 停靠后作者的实际操作闭环(收件箱提示"手动保存该稿后 reset"——这条路 UI 真走得通吗)。
6. 069 迁移在**生产库**(已有 chapter 行)上的字段回填语义;pilot_state 对旧章的 idle 默认。
7. loop journal 目录无 retention(pilot_ch*.json 每章一份+loop 每次一份+result.json——量级账)。
8. 讨论 digest 的 lastSeq 语义:作者看视图时聊"全书",digest 却注入最近章——语境错配面。
9. DiscussionDock agentic 模式(chatStream agentic:true 路径)有没有消费方;/chat/agentic-stream 的 seq 注入零调用方(P0 审查发现,修的是 stream 路径——agentic 路径现在有人用吗)。
10. WriteChat 会话持久化(useChatPersist)×pilot 交付卡话术的键空间。

### 输出格式

1. **执行摘要**:十维各一句话+计数。
2. **发现清单**:`{P0-P3, CONFIRMED/PLAUSIBLE, 维度, 标题, file:line, 失败场景, 复现, 根因, 修复草案, 影响面, 反驳与回应}`。
3. **覆盖证明**:维度×模块矩阵(没有它,"没发现"≠"没问题")。
4. **不建议做清单**。
5. **方法自评**:未到达区域/低置信区/下轮建议。
