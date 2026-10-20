---
title: 铜炉写作系统最优化改造完整Spec
date: 2026-08-23
shortname: tonglu-opt-20260823
ssot: true
source: Qoder IDE / 21份深度审查报告
---

> 本文件为本仓库工作 SSOT。编号项台账见同目录 `2026-08-23-tonglu-opt-ledger.md`。

# 铜炉写作系统最优化改造完整Spec

## 1. 概述

### 1.1 审查范围

本Spec基于2026-08-23对铜炉写作系统（Scribe3）进行的**21份深度审查报告**，覆盖系统全部12个业务板块、40+核心模块、200+API端点、6个前端视图体系。审查由三组研究员（Sam/Jack/Tina）分别从架构闭环、业务完整性、跨域协同三个维度执行，另有写作专家（Lena）和架构师（Marco）对第十三轮迭代进行双视角评审。

### 1.2 方法论

* **六维度审查法**：CRUD对称性 / 正典闭环 / 写作注入 / 限知一致性 / Schema透传 / 健康度门闸

* **五层架构拆解**：状态合成 / 能力编排 / 经验压力 / API路由 / Pilot执行体

* **四维信息追踪**：输入来源 / 输出去向 / 异常分支 / 信号断点

* **对抗性双视角**：架构师视角（工程闭环）+ 一线作家视角（叙事有效性）

### 1.3 发现总量统计

| 严重度    | 数量   | 说明            |
| ------ | ---- | ------------- |
| **P0** | 约35项 | 阻断性/数据损坏/安全风险 |
| **P1** | 约85项 | 功能缺陷/体验显著受损   |
| **P2** | 约80项 | 改善建议/维护性/死路径  |
| **P3** | 约15项 | 远期优化/低优先级     |

去重合并后全量优化项约**215项**，分布于12个板块 + 跨板块链路 + 第十三轮迭代遗留。

***

## 2. 系统性问题模式

以下为跨板块反复出现的共性问题，每个模式列出所有涉及板块和具体表现。

### 2.1 SSE实时更新未接入（s3-live事件总线断头）

**模式描述**：后端通过changefeed → SSE `/live` 推送变更事件，`BinderLayout` 接收并 dispatch `s3-live` 事件，但多个前端面板未订阅该事件，导致数据修改后需手动刷新。

| 板块              | 具体表现                                                                    |
| --------------- | ----------------------------------------------------------------------- |
| 仪表盘(Insight)    | InsightView 所有面板（质量/进度/伏笔台账）未订阅 s3-live，存稿后显示旧数据                        |
| 主编(Director)    | faction/item/term/world\_rule 四表SSE无前端设定库监听；s3-chapter-phase-hint 无前端消费 |
| 主编(Director)    | SSE /live 端点零测试覆盖                                                       |
| 主编(Director)    | /live SSE断连后重连无补偿机制（丢失期间变更）                                             |
| 系统中心(SystemHub) | Gateway restart后无轮询探活，前端仅fetch一次                                        |

### 2.2 级联删除不完整（孤儿数据积累）

**模式描述**：实体删除时仅删除主表记录，不清理关联表（proposition/knows/relation/material/canon\_candidate等），导致孤儿数据被语义召回注入prompt。

| 板块            | 具体表现                                                                                                     |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| 图谱(Atlas)     | 势力删除无lifecycle保护，桥接命题成孤儿；角色删除不级联清理命题                                                                     |
| 设定库(Codex)    | faction/item/term/world\_rule删除无级联清理（proposition/knows/relation成孤儿）；`_cleanup_record_refs`仅处理role/fact前缀 |
| 素材库(Material) | 删除codex实体不清理material.about\_entities；delete\_material不发cache invalidation                                |
| 设定库(Codex)    | character删除时canon\_candidate不清理；codex\_digest命题不随实体删除清理                                                  |

### 2.3 正典Apply后同步断裂

**模式描述**：正典审批通过（apply\_change\_pack）后，不触发digest同步、不触发secret\_bridge同步、不触发语义索引，导致新入库设定在召回和限知体系中不可见。

| 板块         | 具体表现                                                      |
| ---------- | --------------------------------------------------------- |
| 设定库(Codex) | Apply后不触发sync\_entity\_digests（S2-1）                      |
| 设定库(Codex) | Apply后不触发codex\_secret\_bridge同步（S2-2）                    |
| 设定库(Codex) | Apply后新入库非fact实体不触发语义索引（S2-3）                             |
| 图谱(Atlas)  | 正典Apply不触发限知桥（canon\_apply\_store缺sync\_faction\_secrets） |
| 演绎(Deduce) | apply\_change\_pack无回滚机制，部分生效导致不一致                        |

### 2.4 并发安全缺失

**模式描述**：多个关键写路径缺乏章节锁、分布式锁或CAS保护，多Worker/多章并行时存在竞态。

| 板块             | 具体表现                                             |
| -------------- | ------------------------------------------------ |
| 演绎(Deduce)     | chat\_write路径无章节锁，并发写入覆写丢失                       |
| 演绎(Deduce)     | Playbook run\_stage无内置章节锁                        |
| 主编(Director)   | \_pilot\_inflight/run\_state进程私有，多Worker同章双跑竞态   |
| 伏笔(Promise)    | advance\_promise无CAS/事务包裹；promise\_touch无唯一约束防重复 |
| 演绎(Deduce)     | ingest apply\_delta无事务保护，中途崩溃知识图残缺               |
| 仪表盘(Dashboard) | set\_intent使用MERGE无CAS（低风险）                      |

### 2.5 章间连续性断裂风险

**模式描述**：chapter\_state抽取失败后无自动恢复路径，下一章prev\_state=None导致叙事衔接断裂。

| 板块           | 具体表现                                          |
| ------------ | --------------------------------------------- |
| 演绎(Deduce)   | chapter\_state抽取失败needs\_human无自动恢复           |
| 演绎(Deduce)   | Frozen Artifact丢失致Pilot永久卡死                   |
| 主编(Director) | letter诊断/scene\_grid信息不注入下一章prompt（经验层→写路径断链） |

### 2.6 无主动告警机制

**模式描述**：系统完全依赖被动观测（Grafana + stdout日志），无webhook/邮件/主动推送，异常发现延迟取决于人工巡检。

| 板块              | 具体表现                               |
| --------------- | ---------------------------------- |
| 系统中心(SystemHub) | 无任何主动告警集成（webhook/email/push）      |
| 伏笔(Promise)     | overdue伏笔无主动告警链路，仅被动查询             |
| 演绎(Deduce)      | LLM抽取失败时正典链路静默降级无告警                |
| 演绎(Deduce)      | recall影子模式threshold\_ok=False无自动切换 |

### 2.7 Schema-Driven承诺未兑现

**模式描述**：codex\_schema.py声称的schema-driven架构仅在前端表单和faction store白名单两处实现，实际新增字段需修改7-8处。

| 板块         | 具体表现                                        |
| ---------- | ------------------------------------------- |
| 设定库(Codex) | codex\_generate prompt不读schema字段列表（S1-1）    |
| 设定库(Codex) | codex\_digest硬编码\_KIND\_GROUPS引用不存在字段（S1-2） |
| 设定库(Codex) | store patch\_\*白名单硬编码，新增字段被静默丢弃（S1-3）       |
| 设定库(Codex) | canon\_extract LLM prompt不含schema字段列表（S3-1） |

***

## 3. 分板块优化清单

### 3.1 系统中心 (SystemHub)

#### SYS-01 | Admin危险操作缺二次确认 | P0

* **问题描述**：Admin转让书籍归属(`AdminConsole.jsx:255-266`)、重置密码/强制下线(`AdminConsole.jsx:191-217`)直接执行不可逆操作无前置确认弹窗

* **影响范围**：所有admin操作用户，误操作不可恢复

* **修复方案**：统一接入已有ConfirmDialog组件，危险操作前弹出确认

* **预估改动量**：低

* **优先级**：P0

#### SYS-02 | settings/admin板块零toast反馈 | P0

* **问题描述**：全部写入操作仅用内联小字/alert，与写作区showToast体验割裂。`SettingField.jsx:12-14`、`AdminConsole.jsx`全文无showToast

* **影响范围**：系统中心所有设置修改操作

* **修复方案**：统一接入showToast组件，成功/失败均给明确反馈

* **预估改动量**：低

* **优先级**：P0

#### SYS-03 | story-moves propose/review无审计日志 | P1

* **问题描述**：`settings_gateway.py:771-798`操作不留痕，无法事后追溯谁提议/审批了什么招式

* **影响范围**：招式系统审计能力

* **修复方案**：补audit\_rows写入，记录actor/action/payload

* **预估改动量**：低

* **优先级**：P1

#### SYS-04 | PUT /gateway/files无结构化审计 | P1

* **问题描述**：仅有`.bak`备份无谁改了什么的记录。`gateway_files.py`管理员修改网关配置无法追溯到操作者

* **影响范围**：网关配置变更可追溯性

* **修复方案**：write\_file后追加审计日志（actor+变更摘要）

* **预估改动量**：低

* **优先级**：P1

#### SYS-05 | 无主动告警机制 | P1

* **问题描述**：系统完全依赖被动观测（日志+Dashboard），无主动告警能力。日帽触顶/服务宕机只能靠人工发现

* **影响范围**：全系统运维可见性

* **修复方案**：接入webhook/Grafana alerting，关键事件（日帽触顶/DB断连/LLM超时）主动推送

* **预估改动量**：中

* **优先级**：P1

#### SYS-06 | FastEmbed嵌入服务未探活 | P1

* **问题描述**：ObserveStrip仅探SurrealDB/Hermes/LLM，FastEmbed故障时用户无感知（向量检索依赖）

* **影响范围**：语义召回可用性监控

* **修复方案**：补/embedding/health端点或首次向量检索延迟检测

* **预估改动量**：低

* **优先级**：P1

#### SYS-07 | /settings/audit无admin门禁 | P2

* **问题描述**：任何已认证用户可查看审计日志（含设置变更历史），`settings_gateway.py:128-131`无admin检查

* **影响范围**：审计数据可见性

* **修复方案**：添加`_require_admin_api()`检查或按产品决策保留（记录在案）

* **预估改动量**：1行

* **优先级**：P2

#### SYS-08 | 技法/招式列表空态无兜底文案 | P2

* **问题描述**：`SystemHub.jsx:470-498`新书场景显示空白`<ul>`无empty检查

* **影响范围**：新书初始化体验

* **修复方案**：加empty placeholder提示"暂无技法/招式，可通过XX添加"

* **预估改动量**：低

* **优先级**：P2

#### SYS-09 | Gateway restart后无轮询探活 | P2

* **问题描述**：`GatewaySection.jsx:291-293`前端仅fetch一次，网关启动中时用户看到假"离线"

* **影响范围**：重启后用户体验

* **修复方案**：加3次2s间隔retry fetch轮询

* **预估改动量**：低

* **优先级**：P2

#### SYS-10 | secret输入缺autocomplete="off" | P2

* **问题描述**：`SettingField.jsx:40`密钥输入框无autocomplete属性，浏览器可能自动填充

* **影响范围**：密钥输入安全性

* **修复方案**：加一行属性`autoComplete="off"`

* **预估改动量**：1行

* **优先级**：P2

#### SYS-11 | 幽灵配置SCRIBE3\_DESIGN\_BOOK | P3

* **问题描述**：`settings.py:382`声明在REGISTRY但无运行时消费（`feature_flags.py:118`仅列在FLAG列表）

* **影响范围**：配置管理清洁度

* **修复方案**：接线到章设计校验逻辑或从REGISTRY移除/标记deprecated

* **预估改动量**：低

* **优先级**：P3

#### SYS-12 | 幽灵配置SCRIBE3\_STORYLINE\_UI | P3

* **问题描述**：`settings.py:409`仅feature\_flags列表登记+测试断言存在，无运行时消费

* **影响范围**：配置管理清洁度

* **修复方案**：实现前端Gantt/情绪曲线入口的flag门控或标记deferred

* **预估改动量**：低

* **优先级**：P3

#### SYS-13 | SCRIBE3\_DEFAULT\_WORK裸environ绕过 | P3

* **问题描述**：`api/app_impl.py:92`直接os.environ读取，未纳入REGISTRY或FLAG\_EXEMPT

* **影响范围**：配置治理完整性

* **修复方案**：纳入REGISTRY或FLAG\_EXEMPT.md

* **预估改动量**：1行

* **优先级**：P3

#### SYS-14 | MCP catalog gate字段为展示型非运行时门控 | P3

* **问题描述**：`mcp_catalog_build.py`的gate字段是声明式目录，Hermes运行时物理门控走Profile+WRITE\_GATED，需文档澄清

* **影响范围**：开发者理解成本

* **修复方案**：文档明确标注"gate字段为能力说明书，非运行时门控"

* **预估改动量**：低

* **优先级**：P3

***

### 3.2 仪表盘 (Insight/Dashboard)

#### DSH-01 | totalGoal=0时前端除零 | P0

* **问题描述**：后端`set_intent`允许0值落库。前端`InsightView.jsx:336,340`中`totalGoal=0`时`Math.round((totalWords/0)*100)`=Infinity，进度条显示100%误导用户

* **影响范围**：所有设置目标为0的用户

* **修复方案**：改为`const totalGoal = prog.total_word_goal || 100000`（0走fallback），或计算前`if (totalGoal <= 0) totalGoal = 100000`

* **预估改动量**：1行

* **优先级**：P0

#### DSH-02 | InsightView不监听s3-live事件 | P1

* **问题描述**：`InsightView.jsx`所有面板（质量/进度/伏笔台账）未订阅s3-live事件，数据仅挂载时拉取一次。存稿后切到仪表盘看到旧数据。（多报告提及）

* **影响范围**：所有使用仪表盘的用户

* **修复方案**：添加`window.addEventListener('s3-live', ...)`监听，在chapter/promise/daily\_progress表变更时递增对应key

* **预估改动量**：中

* **优先级**：P1

#### DSH-03 | 连胜计算用服务器时区非用户时区 | P1

* **问题描述**：`store/connection.py:371`和`progress_stats.py:64`使用服务器进程时区。UTC部署+UTC+8用户=跨午夜连胜可能被错误打断

* **影响范围**：跨时区用户的连胜统计准确性

* **修复方案**：接受前端传入的timezone或today参数；API层从请求头获取用户时区

* **预估改动量**：中

* **优先级**：P1

#### DSH-04 | /quality端点无TTL缓存但每次全查SurrealDB | P1

* **问题描述**：每次请求调outline()+list\_promises()+get\_intent()全查DB，200+章时性能可能成为瓶颈

* **影响范围**：大规模作品的仪表盘响应速度

* **修复方案**：添加短TTL服务端缓存（如5s），或增量查询策略

* **预估改动量**：中

* **优先级**：P1

#### DSH-05 | PromiseLedger加载失败时静默消失 | P2

* **问题描述**：`InsightView.jsx:209`的`.catch(() => setLed(null))`导致伏笔台账直接不渲染，用户无从知晓是加载失败还是无数据

* **影响范围**：伏笔台账可用性

* **修复方案**：catch中设置error状态并渲染ErrorState组件

* **预估改动量**：低

* **优先级**：P2

#### DSH-06 | 伏笔setup章被删后UI仍显示可点击 | P2

* **问题描述**：删章不级联修改伏笔setup\_chapter，PromiseOpenBar仍渲染指向已删章的跨度条，"跳到第X章"按钮跳到不存在的章

* **影响范围**：伏笔台账展示准确性

* **修复方案**：前端跳章前校验章是否存在；或store层archive\_chapter时标记关联伏笔

* **预估改动量**：低

* **优先级**：P2

#### DSH-07 | 200+章/100+伏笔时无分页无虚拟列表 | P2

* **问题描述**：图表200+数据点XAxis标签重叠；100+伏笔时LedgerColumn全量渲染DOM节点过多

* **影响范围**：大规模数据的渲染性能

* **修复方案**：图表加interval/tickCount限制；伏笔台账加虚拟列表或折叠

* **预估改动量**：中

* **优先级**：P2

#### DSH-08 | set\_intent无乐观锁并发写同字段丢失 | P2

* **问题描述**：`store/intent.py:82`使用UPSERT MERGE，两tab同时修改同字段后写者覆盖

* **影响范围**：多tab并发编辑目标场景（低频）

* **修复方案**：对用户体感影响低的配额字段可接受；如需严格可加IF-CHECK条件更新

* **预估改动量**：低

* **优先级**：P2

#### DSH-09 | 跨视图切换时数据刷新依赖组件卸载/重挂载 | P2

* **问题描述**：React路由切视图时若InsightView不unmount（如keep-alive），useEffect不重触发

* **影响范围**：特定路由配置下的数据更新

* **修复方案**：增加跨视图切换时自动递增key的逻辑

* **预估改动量**：低

* **优先级**：P2

***

### 3.3 设定库 (Codex/Canon)

#### CDX-01 | store patch白名单硬编码，新增schema字段被静默丢弃 | P0

* **问题描述**：`codex_ext.py:150-152,194-196,238-239`对item/term/world\_rule的patch手写`if k in (...)`，新增字段数据静默丢失，作者以为保存了实际丢失

* **影响范围**：所有设定库schema扩展场景

* **修复方案**：改为`allowed = set(_codex_all_storage_keys(kind))`，与faction一致

* **预估改动量**：低

* **优先级**：P0

#### CDX-02 | codex\_digest字段名错误（item用了不存在的字段） | P0

* **问题描述**：`codex_digest.py:33-35`使用"function"/"origin"而非实际字段"description"/"current\_owner"，item摘要命题内容为空/错误

* **影响范围**：item类设定的语义召回完全失效

* **修复方案**：改为从codex\_schema动态生成或对齐实际字段名

* **预估改动量**：1行

* **优先级**：P0

#### CDX-03 | codex\_generate prompt不读schema字段列表 | P0

* **问题描述**：`codex_generate.py:spec_ask()`的`_CHAR_HEADS/_ITEM_HEADS/_RULE_HEADS`全硬编码，新增字段LLM永远不主动生成

* **影响范围**：设定自动生成的字段覆盖率

* **修复方案**：改prompt构造为动态遍历`fields_for(kind)`

* **预估改动量**：中

* **优先级**：P0

#### CDX-04 | Apply后不触发sync\_entity\_digests | P1

* **问题描述**：`canon_apply_store.py`无codex\_digest引用，审批通过的设定在语义召回中不可见。（多报告提及）

* **影响范围**：正典审批后设定的召回可达性

* **修复方案**：在\_apply\_one成功后调sync\_entity\_digests

* **预估改动量**：低

* **优先级**：P1

#### CDX-05 | Apply后不触发codex\_secret\_bridge同步 | P1

* **问题描述**：`canon_apply_store._apply_faction`无sync\_faction\_secrets调用，限知链断裂。（多报告提及）

* **影响范围**：正典审批后限知信息同步

* **修复方案**：\_apply\_faction/\_apply\_character末尾补sync\_faction\_secrets/sync\_role\_secrets

* **预估改动量**：低

* **优先级**：P1

#### CDX-06 | Apply后非fact实体不触发语义索引 | P1

* **问题描述**：character/faction/item/term写入不含embedding更新，在语义召回中不可见

* **影响范围**：新入库设定的语义检索

* **修复方案**：补semantic\_index或通过digest→fact间接触发

* **预估改动量**：中

* **优先级**：P1

#### CDX-07 | Reject不学习，下次抽取反复提同样噪声 | P1

* **问题描述**：`_persist_pack_items`只预查pending不查rejected，被拒绝的候选下次仍会被重复提交

* **影响范围**：正典审核体验（运营噪声循环）

* **修复方案**：预取rejected键集合作去重

* **预估改动量**：低

* **优先级**：P1

#### CDX-08 | faction/item/term/world\_rule删除无级联清理 | P1

* **问题描述**：`_cleanup_record_refs`仅处理role/fact前缀，faction/item/term跳过。删除后proposition/knows/relation成孤儿被语义召回

* **影响范围**：数据一致性，孤儿数据积累

* **修复方案**：仿`_cleanup_record_refs`补各类型级联逻辑

* **预估改动量**：中

* **优先级**：P1

#### CDX-09 | faction删除不走lifecycle | P1

* **问题描述**：`del_faction`直接调store.delete\_faction无影响评估，不对齐character/fact的lifecycle路径

* **影响范围**：势力删除后的数据完整性

* **修复方案**：对齐character/fact的lifecycle保护路径

* **预估改动量**：中

* **优先级**：P1

#### CDX-10 | MCP s3\_delete\_codex不走lifecycle | P1

* **问题描述**：直接硬删无影响评估，绕过了lifecycle保护

* **影响范围**：通过MCP删除设定时的数据安全

* **修复方案**：复用lifecycle路径

* **预估改动量**：低

* **优先级**：P1

#### CDX-11 | character secret bridge默认关闭 | P1

* **问题描述**：`SCRIBE3_SECRET_BRIDGE_ROLES`默认False，角色backstory不进入统一限知链

* **影响范围**：角色秘密的限知防护覆盖

* **修复方案**：评估开启的影响，默认开启或在文档中明确说明

* **预估改动量**：低

* **优先级**：P1

#### CDX-12 | codex\_health与iceberg evaluate\_codex\_ready标准不一致 | P2

* **问题描述**：codex\_ext.py硬编码三字段判sparse vs iceberg完整评估，两套判定标准可能给出矛盾结论

* **影响范围**：设定完备性判定一致性

* **修复方案**：统一判定源或明确语义差异

* **预估改动量**：低

* **优先级**：P2

#### CDX-13 | canon\_extract LLM prompt不含schema字段列表 | P2

* **问题描述**：新增字段不被自动抽取（S3-1）

* **影响范围**：正典自动抽取的字段覆盖率

* **修复方案**：prompt中注入schema字段列表

* **预估改动量**：低

* **优先级**：P2

#### CDX-14 | SurrealDB SCHEMAFULL表需手写migration | P2

* **问题描述**：无自动生成migration工具（S3-2）

* **影响范围**：schema变更的开发效率

* **修复方案**：基于codex\_schema差异自动生成migration脚本

* **预估改动量**：高

* **优先级**：P2

#### CDX-15 | motif/promise仅MCP可达，前端无REST路由 | P2

* **问题描述**：`api/routers/codex.py`无motif/promise路由，仅AI可操作

* **影响范围**：用户直接管理母题/伏笔的能力

* **修复方案**：补REST或确认"仅AI操作"设计意图并文档化

* **预估改动量**：中

* **优先级**：P2

#### CDX-16 | world\_rule无REST PATCH端点 | P2

* **问题描述**：前端编辑世界规则无对应后端路由（S3-13）

* **影响范围**：世界规则编辑能力

* **修复方案**：补PATCH /world-rules/{id}端点

* **预估改动量**：低

* **优先级**：P2

#### CDX-17 | SCRIBE3\_CODEX\_THICKEN\_GATE=0绕过门闸时无审计日志 | P2

* **问题描述**：绕过设定完备性门闸时无审计记录（S3-5）

* **影响范围**：门闸绕过可追溯性

* **修复方案**：补审计日志记录绕过操作

* **预估改动量**：低

* **优先级**：P2

***

### 3.4 素材库 (Material)

#### MAT-01 | emotion\_module双重注入导致token浪费 | P0

* **问题描述**：`store/recall.py:580-642`无kind过滤，`brief.py:923-924`独立召回emotion\_module，同一素材可被注入两次，挤占token预算。

* **影响范围**：每章写入均可能触发；其他素材被裁剪

* **修复方案**：material\_recall增加kind过滤排除已被其他通道独立召回的kind；或统一召回入口去重

* **预估改动量**：低

* **优先级**：P0

#### MAT-02 | motif\_instance evidence无可溯源验证 | P0

* **问题描述**：`ingest.py:216-217`明确豁免motif类evidence的grep\_back\_verify；evidence\_acceptable仅检查长度≥2。LLM可任意声称"已回应母题"

* **影响范围**：母题闭环彻底失效——无法区分真正回应与幻觉声称，heat调度数据污染

* **修复方案**：对motif evidence增加正文子串匹配或语义相似度≥阈值校验；不通过标记unverified不计入heat

* **预估改动量**：中

* **优先级**：P0

#### MAT-03 | 删除codex实体不清理material.about\_entities | P0

* **问题描述**：`store/connection.py:422-431` `_cleanup_record_refs`不涉及material表。删除角色/地点后素材的about\_entities仍引用已删实体ID

* **影响范围**：素材记忆网络BFS遍历返回脏数据或空节点

* **修复方案**：`_cleanup_record_refs`增加`UPDATE material SET about_entities -= $deleted_id WHERE about_entities CONTAINS $deleted_id`

* **预估改动量**：低

* **优先级**：P0

#### MAT-04 | delete\_material不发cache invalidation | P0

* **问题描述**：`store/materials.py:169-172`delete无广播 vs `193-208`update有广播。删除后其他节点缓存仍持有已删素材

* **影响范围**：分布式部署下已删素材可被recall返回注入写路径

* **修复方案**：delete\_material末尾追加`await self._emit_cache_invalidation("material", material_id)`

* **预估改动量**：1行

* **优先级**：P0

#### MAT-05 | origin=manual/session\_clip路径缺build\_material\_edges | P1

* **问题描述**：手动创建和session\_clip路径不调build\_material\_edges，导致这些素材无图边和about\_entities，记忆网络不可达

* **影响范围**：手动录入素材的图遍历召回失效

* **修复方案**：POST /materials和session\_clip commit后追加build\_material\_edges

* **预估改动量**：低

* **优先级**：P1

#### MAT-06 | material\_reference溯源语义错误 | P1

* **问题描述**：记录"被注入"而非"被借鉴"，溯源链语义不准确

* **影响范围**：素材使用追溯可靠性

* **修复方案**：明确reference类型语义（injection vs inspiration）

* **预估改动量**：低

* **优先级**：P1

#### MAT-07 | 素材搜索无语义检索（仅BM25文本匹配） | P1

* **问题描述**：前端搜索仅走BM25，无向量语义检索通道

* **影响范围**：素材检索召回率

* **修复方案**：搜索API增加hybrid模式（BM25+向量）

* **预估改动量**：中

* **优先级**：P1

#### MAT-08 | 素材kind分类无层级/无自定义扩展 | P2

* **问题描述**：kind为固定枚举，用户无法自定义素材类型

* **影响范围**：素材分类灵活性

* **修复方案**：允许用户创建自定义kind标签

* **预估改动量**：中

* **优先级**：P2

***

### 3.5 图谱 (Atlas)

#### ATL-01 | 归档角色泄入写作prompt | P0

* **问题描述**：`store/characters.py`的`characters()`查询无archived过滤。归档角色设定仍被`_codex_segments()`注入LLM prompt影响生成

* **影响范围**：所有归档角色的设定泄露到写作

* **修复方案**：characters() SELECT加`WHERE archived = NONE OR archived != true`

* **预估改动量**：1行

* **优先级**：P0

#### ATL-02 | 势力删除无lifecycle保护 | P0

* **问题描述**：`del_faction`硬删不经影响评估，桥接命题成幽灵数据被语义召回。（多报告提及）

* **影响范围**：删除势力后prompt可能引用不存在势力

* **修复方案**：走`_delete_object_with_lifecycle`路径，或清理proposition+调用\_cleanup\_record\_refs。物品/术语同理

* **预估改动量**：中

* **优先级**：P0

#### ATL-03 | 正典Apply不触发限知桥同步 | P0

* **问题描述**：`canon_apply_store._apply_faction()`写入faction secret字段时不调sync\_faction\_secrets()，限知链断裂。（多报告提及）

* **影响范围**：通过正典流程修改的secret字段限知门控失效

* **修复方案**：\_apply\_faction/\_apply\_character末尾追加sync\_faction\_secrets/sync\_role\_secrets

* **预估改动量**：低

* **优先级**：P0

#### ATL-04 | 因果根编辑端点前端零接触 | P0

* **问题描述**：`world_read.py:779`注册PATCH /events/{eid}/causal-root但前端api.js无wrapper、组件无调用路径。因果链编辑能力完全断线

* **影响范围**：作者无法修正AI推断错误的因果关系

* **修复方案**：api.js添加wrapper + TimelineView或事件详情面板添加因果根编辑入口

* **预估改动量**：中

* **优先级**：P0

#### ATL-05 | 角色删除不级联清理命题 | P1

* **问题描述**：`_cleanup_record_refs`只删knows/involves边不删命题行。孤儿命题仍被semantic\_recall召回

* **影响范围**：已删角色信息泄入prompt

* **修复方案**：补`DELETE proposition WHERE entity_id = $oid`

* **预估改动量**：低

* **优先级**：P1

#### ATL-06 | 势力known\_members与角色实体无动态同步 | P1

* **问题描述**：`_faction_prompt_block`注入静态known\_members字段，角色退出/死亡后faction.known\_members未自动更新

* **影响范围**：prompt中显示过时势力成员

* **修复方案**：known\_members改为动态查询或在角色状态变更时自动同步

* **预估改动量**：中

* **优先级**：P1

#### ATL-07 | 物品state\_history无时间线展示 | P1

* **问题描述**：item有state\_history字段但前端无对应时间线组件

* **影响范围**：物品流转追踪可见性

* **修复方案**：在物品详情面板添加state\_history时间线展示

* **预估改动量**：中

* **优先级**：P1

#### ATL-08 | 关系图无权重/无方向标注 | P1

* **问题描述**：角色关系图仅显示关系存在，不展示关系强度/方向/变化

* **影响范围**：关系复杂度可视化

* **修复方案**：关系边增加权重/方向属性和视觉标注

* **预估改动量**：中

* **优先级**：P1

#### ATL-09 | 事件无批量导入/导出 | P2

* **问题描述**：时间线事件只能逐条创建，无批量操作

* **影响范围**：大型世界观构建效率

* **修复方案**：增加CSV/JSON批量导入API

* **预估改动量**：中

* **优先级**：P2

***

### 3.6 伏笔 (Promise)

#### PRM-01 | Overdue无硬闸阻止力 | P0

* **问题描述**：overdue从未作为hard gate阻止save\_chapter/loop\_chapter/chat\_write执行。超期伏笔可永远被忽略。`health.py:43`超期只产出列表；`promise_touch_soft.py:101`明确blocking:False

* **影响范围**：伏笔治理机制失效，可永远不兑现

* **修复方案**：在check\_finalize\_for\_save或run\_chapter\_loop起始处增overdue数量阈值硬闸（如overdue>=3时拒绝写新章）

* **预估改动量**：中

* **优先级**：P0

#### PRM-02 | 并发写入安全缺失 | P0

* **问题描述**：`advance_promise`模式为SELECT+UPDATE无CAS/事务；`add_promise_touch`无唯一约束可重复写入。多章并行ingest时promise\_touch可重复

* **影响范围**：伏笔状态数据一致性

* **修复方案**：1) advance增WHERE status='open'条件; 2) promise\_touch增唯一约束(promise\_id,chapter,ingest\_seq)

* **预估改动量**：低

* **优先级**：P0

#### PRM-03 | Resolution校验绕过口 | P1

* **问题描述**：`canon_apply_store._apply_promise`调store.plant\_promise不传resolution，store层无strict校验，可绕过tier=book的resolution必填约束

* **影响范围**：正典流程创建的伏笔可能缺失resolution

* **修复方案**：store层plant\_promise增可选strict模式或\_apply\_promise补tier级校验

* **预估改动量**：低

* **优先级**：P1

#### PRM-04 | Canon advance不产生fact/proposition | P1

* **问题描述**：advance\_promise在canon路径内只改status=closed+payoff\_chapter，不产生知识图条目。"伏笔兑现"不进入知识图谱

* **影响范围**：限知帧无法利用"谁知道伏笔已兑现"信息

* **修复方案**：advance后自动生成proposition"伏笔X已兑现于第Y章"+为在场角色建knows边

* **预估改动量**：中

* **优先级**：P1

#### PRM-05 | 伏笔超期无主动告警链路 | P1

* **问题描述**：promise\_ledger只是查询时聚合，无定时扫描+主动推送。（多报告提及）

* **影响范围**：依赖作者手动查阅或被动问诊发现

* **修复方案**：agent\_crons增check\_overdue\_promises定时任务+nudge级压力信号注入experience\_state

* **预估改动量**：中

* **优先级**：P1

#### PRM-06 | Seed→Promise衔接丢失上下文 | P1

* **问题描述**：`promote_seed_payload`只复制text\[:120]和seq，seed的reason/evidence未迁移到promise

* **影响范围**：升格后的伏笔缺失创意来源上下文

* **修复方案**：promote时将seed的reason/evidence写入promise的resolution或clues\[0]

* **预估改动量**：低

* **优先级**：P1

#### PRM-07 | 伏笔-角色绑定缺失 | P1

* **问题描述**：promise表无character\_id字段，无法追踪"谁的伏笔"

* **影响范围**：角色弧光与伏笔的关联分析

* **修复方案**：增加optional的involved\_characters字段

* **预估改动量**：中

* **优先级**：P1

#### PRM-08 | 伏笔间依赖网络缺失 | P2

* **问题描述**：伏笔之间无"A依赖B先兑现"的关系建模

* **影响范围**：复杂伏笔网络的编排能力

* **修复方案**：增加promise\_dependency表或depends\_on字段

* **预估改动量**：中

* **优先级**：P2

#### PRM-09 | Legacy数据tier可能被误判 | P2

* **问题描述**：旧行tier=None回退为"chapter"产生过窄窗口(±1-3而非±5-15)

* **影响范围**：极旧数据的overdue判定准确性

* **修复方案**：执行一次性批量迁移脚本补正确tier值

* **预估改动量**：低

* **优先级**：P2

***

### 3.7 母题 (Motif)

#### MOT-01 | echo\_terms未参与ingest反哺链路 | P1

* **问题描述**：`critique/rules_parts/05_prompts.py:132-138`仅传motif\_names不传echo\_terms。LLM抽取prompt中无echo\_terms信息，隐性回声（用"炉火"呼应"灯与债"但未显式提名）100%丢失

* **影响范围**：母题回响追踪的查全率严重不足

* **修复方案**：ingest prompt中注入每个母题的echo\_terms作为辅助匹配关键词；或\_resolve\_motif增加echo\_terms模糊匹配

* **预估改动量**：中

* **优先级**：P1

#### MOT-02 | phase无自动推进逻辑 | P1

* **问题描述**：MOTIF\_PHASES定义5态(seed/echo/turn/payoff/rest)但全代码零auto-advance逻辑。除rest外四态行为完全无区别——纯展示标签

* **影响范围**：母题生命周期管理无系统化推进

* **修复方案**：基于motif\_instance累计count+叙事进度自动推进phase（如触碰>5次进turn，正文含转折词进payoff）

* **预估改动量**：中

* **优先级**：P1

#### MOT-03 | tier/scope后端调度完全忽略 | P1

* **问题描述**：`motif_craft.py:121-173` schedule\_motifs完全不区分tier，所有母题一锅调度。前端按tier过滤但后端heat算法对book-tier和chapter-tier等同处理

* **影响范围**：长线母题和短线母题节奏混乱

* **修复方案**：schedule\_motifs按tier分组调度，book-tier母题允许更长gap，chapter-tier要求更频繁触碰

* **预估改动量**：中

* **优先级**：P1

#### MOT-04 | motif\_instance evidence无溯源验证 | P1

* **问题描述**：`ingest.py:216-217`豁免motif evidence的grep\_back\_verify，LLM可编造回应声称。（与MAT-02同源，多报告提及）

* **影响范围**：母题heat调度数据可能被幻觉污染

* **修复方案**：增加正文子串匹配或语义相似度校验

* **预估改动量**：中

* **优先级**：P1

#### MOT-05 | 母题回响无"过度重复"阈值告警 | P1

* **问题描述**：motif\_instance记录触及但无上限检测，同一母题被无节制反复触碰（anti\_meta仅检测文本面"母题SEO腔"）

* **影响范围**：母题过度使用影响文学质量

* **修复方案**：motif\_heat增加"过热告警"阈值（如streak>=5产blocking级advisory）

* **预估改动量**：低

* **优先级**：P1

#### MOT-06 | 创建闭环无"降级自动填占位"路径 | P2

* **问题描述**：作者拒绝motif\_seed\_proposal后系统只能反复催（循环产blocker），无自动降级写入占位母题的机制

* **影响范围**：圣经阶段的母题门槛阻塞体验

* **修复方案**：连续N次拒绝后降级为"通用母题占位"+弱化GATE-A门槛

* **预估改动量**：中

* **优先级**：P2

#### MOT-07 | 过热抑制依赖LLM遵循指令无硬保证 | P2

* **问题描述**：avoid\_overuse指令为自然语言建议，若LLM不遵循且ingest误识别为触及则heat不回落

* **影响范围**：过热抑制机制可靠性

* **修复方案**：过热母题在post\_check中增加专项检测（正文含过热母题名/echo\_terms时标advisory）

* **预估改动量**：中

* **优先级**：P2

***

### 3.8 时间线 (Timeline)

#### TML-01 | 时间线不订阅SSE s3-live事件 | P2

* **问题描述**：TimelineView不订阅SSE事件，写新章后时间线不实时更新，唯一更新路径为手动点刷新

* **影响范围**：时间线数据实时性

* **修复方案**：mount effect中addEventListener('s3-live', handler)，涉及event/promise/char\_state/relation表时refetch当前range

* **预估改动量**：低

* **优先级**：P2

#### TML-02 | 因果弧线SVG未实现 | P2

* **问题描述**：store层已返回causal\_in\_rich结构，注释承诺"供前端SVG因果弧线"，但前端零渲染代码

* **影响范围**：因果链追踪可视化缺失

* **修复方案**：vis-timeline afterDraw钩子中基于两端chapter绘制SVG箭头连线

* **预估改动量**：中

* **优先级**：P2

#### TML-03 | 时间线选中伏笔后无操作入口 | P2

* **问题描述**：DetailPanel的promise分支只展示只读字段+跳章按钮，无兑现/弃置操作

* **影响范围**：伏笔就地操作能力

* **修复方案**：DetailPanel增加快捷操作按钮（兑现/弃置/标障眼法）

* **预估改动量**：中

* **优先级**：P2

#### TML-04 | 记忆否认未与canon事实交叉 | P2

* **问题描述**：memory\_denial的known\_markers仅来自伏笔文本片段，未利用canon已确立事实，查全率偏低

* **影响范围**：记忆否认检测精度

* **修复方案**：调用前从facts\_at(seq)拉取可知事实value前16字作为补充markers

* **预估改动量**：低

* **优先级**：P2

#### TML-05 | 全表查无WHERE（story轴模式） | P2

* **问题描述**：`_all_events_bulk()`执行SELECT无条件，千事件级别时DB→Python传输成瓶颈。Python侧四全表遍历

* **影响范围**：大规模作品的时间线性能

* **修复方案**：story轴改用WHERE story\_chapter BETWEEN；promises/char\_states同样加章号条件

* **预估改动量**：中

* **优先级**：P2

#### TML-06 | 缺少"跳到第N章"直达能力 | P2

* **问题描述**：仅有拖动+缩放+全览三种定位方式，长篇找特定章需反复操作

* **影响范围**：长篇作品导航效率

* **修复方案**：顶栏添加章号输入框，输入→tl.setWindow(chToDate(N-5), chToDate(N+5))

* **预估改动量**：低

* **优先级**：P2

#### TML-07 | 选中联动不传播因果链/弧光 | P2

* **问题描述**：选中事件后仅单条高亮，causal\_in前驱事件、同角色弧光均无联动标记

* **影响范围**：因果追踪的可视化价值

* **修复方案**：select回调中根据\_raw\.refs.causal\_in给前驱item添加vis-highlighted className

* **预估改动量**：低

* **优先级**：P2

#### TML-08 | faction.timeline字段前端零消费 | P3

* **问题描述**：083迁移预留字段但全栈未消费

* **影响范围**：势力时间线展示缺失

* **修复方案**：前端泳道增加势力事件展示或标记字段为deprecated

* **预估改动量**：中

* **优先级**：P3

***

### 3.9 旅程 (Journey)

#### JNY-01 | Pilot可绕过旅程门槛直接开写 | P1

* **问题描述**：Pilot的step()/approve()无任何旅程站位校验。用户可跳过旅程门槛直接开写——无北极星/角色/母题保护

* **影响范围**：写作质量（无约束开写导致偏离）

* **修复方案**：/pilot/step入口增可选旅程前置校验（feature flag控制），intent未设或motif不足时返回409+引导

* **预估改动量**：中

* **优先级**：P1

#### JNY-02 | 质量熔断状态对作者不可见 | P1

* **问题描述**：`build_workflow_snapshot()`的pilot\_status不区分"正常drafting"与"质量循环熔断后卡住"。作者在旅程界面只看"草稿中"无法识别卡死

* **影响范围**：用户等待体验

* **修复方案**：snapshot章状态增quality\_stalled:bool字段，前端对stalled章展示警告标记

* **预估改动量**：低

* **优先级**：P1

#### JNY-03 | ledger站为空壳，全书完成后胶囊消失 | P1

* **问题描述**：ledger站无实质逻辑（仅占位），全部章finalized后旅程胶囊从DOM消失，作者体验为"突然没了"无仪式闭环

* **影响范围**：完成体验

* **修复方案**：ledger站实现最小可用内容（完成统计+质量总评+"恭喜完成"）；serialize站增"焦点章"概念

* **预估改动量**：中

* **优先级**：P1

#### JNY-04 | 8个pilot状态压缩为5个，需审批状态被隐藏 | P2

* **问题描述**：outline\_proposed和beats\_ready在UI上合并为"规划中"，作者无法区分"等待审批"vs"AI处理中"

* **影响范围**：进度感知精度

* **修复方案**：需作者操作的状态增加"等待你审批"视觉差异

* **预估改动量**：低

* **优先级**：P2

#### JNY-05 | 前三站"继续"依赖NLU匹配精准度弱 | P2

* **问题描述**：WorkflowCapsule前三站(intent/world/structure)的"继续"按钮domainHint=null，依赖正则匹配fallback可能分配错误工作包

* **影响范围**：引导准确性

* **修复方案**：从snapshot的next\_step.id映射更多domain

* **预估改动量**：低

* **优先级**：P2

#### JNY-06 | WorkflowCapsule轮询无backoff，消失无解释 | P2

* **问题描述**：12s定时轮询网络错误时setSnap(null)→胶囊消失无解释，无exponential backoff

* **影响范围**：网络韧性和用户理解

* **修复方案**：catch中保留旧snap+isStale=true灰化展示；连续失败backoff(12→24→48s)

* **预估改动量**：低

* **优先级**：P2

#### JNY-07 | 章被打回无事件通知 | P2

* **问题描述**：snapshot只展示当前态不告知作者"刚才从checked被退回了"，需主动对比前后发现

* **影响范围**：状态变更感知

* **修复方案**：snapshot增recent\_transitions\[]字段+前端展示toast通知

* **预估改动量**：低

* **优先级**：P2

#### JNY-08 | 停滞检测无分级 | P2

* **问题描述**：仅二值（卡住/未卡住），无分级；parked（主动暂停）与被动卡住未区分

* **影响范围**：告警精度

* **修复方案**：stalled分级(warning 30min / critical 2h)；parked态独立展示

* **预估改动量**：低

* **优先级**：P2

***

### 3.10 主编 (Director)

#### DIR-01 | Proposal审批缺乏持久化 | P0

* **问题描述**：`api/routers/director.py:666-671` execute=False分支仅返回JSON标记awaiting\_hermes\_approval，不写入任何持久化存储。proposal对象仅存在于单次HTTP响应中，页面刷新即丢失。（多报告提及）

* **影响范围**：所有生产路径的proposal审批

* **修复方案**：proposal持久化到DB（如write\_proposal表）并生成唯一ID；Hermes审批结果通过该ID回写状态

* **预估改动量**：高

* **优先级**：P0

#### DIR-02 | 多Worker部署下同章双跑竞态 | P0

* **问题描述**：`app_impl.py:1625,1675`的\_pilot\_inflight(threading.Lock)和\_pilot\_run\_state(dict)均为进程私有。gunicorn多worker时两worker可同时对同章执行pilot step

* **影响范围**：章数据损坏、状态不一致

* **修复方案**：引入DB级advisory lock或Redis分布式锁；或限制pilot路由单worker处理

* **预估改动量**：高

* **优先级**：P0

#### DIR-03 | Frozen Artifact丢失致Pilot不可自愈卡死 | P0

* **问题描述**：`pilot.py:128-133`的run\_stage需前置冻结产物缺失时反复报stage\_not\_ready。reset-step只清parked标记不回退状态，dismiss丢失所有进度

* **影响范围**：Pilot生命周期永久阻塞

* **修复方案**：reset-step增force\_rollback参数允许回退到指定状态并清除对应frozen artifact

* **预估改动量**：中

* **优先级**：P0

#### DIR-04 | SSE /live端点零测试覆盖 | P0

* **问题描述**：`pilot_inbox.py` /live端点+`live.py`。SSE是前端实时反馈唯一通道，无测试意味着changefeed路由变更无法被CI拦截

* **影响范围**：前端状态不同步风险

* **修复方案**：新增pytest + httpx AsyncClient SSE mock测试，验证chapter\_update/approval/pilot\_state事件结构

* **预估改动量**：中

* **优先级**：P0

#### DIR-05 | Blocker双向闭环零测试 | P0

* **问题描述**：blocker是写路径核心闸控，仅有"产生"侧覆盖，完全缺失"解除后允许写入"的双向闭环测试

* **影响范围**：blocker误锁时CI无法检测

* **修复方案**：test\_director\_workflow新增：零母题→seed→blocker消失、超期伏笔→advance→blocker消失

* **预估改动量**：中

* **优先级**：P0

#### DIR-06 | s3-chapter-phase-hint事件无前端消费 | P1

* **问题描述**：`ui_target.py:367`产出soft focus事件但前端无监听

* **影响范围**：章节焦点引导失效

* **修复方案**：前端uiDirective.js增加handler

* **预估改动量**：低

* **优先级**：P1

#### DIR-07 | faction/item/term/world\_rule四表SSE无设定库监听 | P1

* **问题描述**：`app_impl.py:1703`产出SSE事件但前端设定库面板无监听

* **影响范围**：设定库实时更新

* **修复方案**：设定库面板增加s3-live监听

* **预估改动量**：低

* **优先级**：P1

#### DIR-08 | needs\_human收件箱无dismiss/消除出口 | P1

* **问题描述**：`pilot_inbox.py:298-304`收件箱项无dismiss/消除机制，积累后无法清理

* **影响范围**：收件箱积压体验

* **修复方案**：增加/inbox/dismiss端点

* **预估改动量**：低

* **优先级**：P1

#### DIR-09 | lesson/pulse/digest收件箱无标记完成 | P1

* **问题描述**：`pilot_inbox.py:305-427`收件箱项无acknowledge状态字段

* **影响范围**：收件箱状态管理

* **修复方案**：增加dismiss/acknowledge状态字段

* **预估改动量**：低

* **优先级**：P1

#### DIR-10 | /live SSE断连后重连无补偿 | P1

* **问题描述**：`live.py`+`api.js:747`断连后重连仅收新事件，丢失期间变更无reconcile

* **影响范围**：网络波动后状态不同步

* **修复方案**：重连后触发全量pull

* **预估改动量**：低

* **优先级**：P1

#### DIR-11 | pulse\_decision项无dismiss机制 | P1

* **问题描述**：`pilot_inbox.py:376-391`无dismiss/acknowledge路径

* **影响范围**：脉搏决策项积压

* **修复方案**：增加dismiss端点

* **预估改动量**：低

* **优先级**：P1

#### DIR-12 | letter诊断结果不注入下一章prompt | P1

* **问题描述**：`experience/letter.py`→`build_ctx`传导断链。letter诊断结果不注入下一章prompt

* **影响范围**：经验层"诊后不治"，AI不记得已诊断的问题

* **修复方案**：build\_ctx增revision\_letter\_digest slot

* **预估改动量**：中

* **优先级**：P1

#### DIR-13 | scene\_grid信息不注入生成prompt | P1

* **问题描述**：`experience/scene_grid.py`→`build_ctx`传导断链。场景网格六格信息不注入生成prompt

* **影响范围**：场景结构诊断无法驱动改进

* **修复方案**：build\_ctx增scene\_grid slot

* **预估改动量**：中

* **优先级**：P1

#### DIR-14 | MAX\_QUALITY\_ROUNDS全失败后草稿未落库 | P1

* **问题描述**：`pipeline.py:203,876`8轮熔断后无降级产出

* **影响范围**：质量循环卡死时工作完全丢失

* **修复方案**：8轮熔断时保留最佳候选（分数最高的一轮产出）

* **预估改动量**：中

* **优先级**：P1

#### DIR-15 | checked态下full\_check永远blocking无法修复 | P1

* **问题描述**：`pilot_inbox.py:236-242`无回退路径

* **影响范围**：Pilot状态卡死

* **修复方案**：增加force\_rollback参数

* **预估改动量**：低

* **优先级**：P1

#### DIR-16 | Proposal reject无审计日志 | P2

* **问题描述**：无法事后复盘拒绝原因

* **影响范围**：决策可追溯性

* **修复方案**：reject时记录审计日志

* **预估改动量**：低

* **优先级**：P2

#### DIR-17 | idea路由LLM失败静默降级为unclear | P2

* **问题描述**：用户无感知LLM处理失败

* **影响范围**：错误诊断透明度

* **修复方案**：降级时toast提示"AI处理异常，已降级为通用回答"

* **预估改动量**：低

* **优先级**：P2

#### DIR-18 | live onGiveUp后永久停止无探活恢复 | P2

* **问题描述**：SSE放弃后永久停止，无定时探活尝试恢复

* **影响范围**：长时间连接中断后需手动刷新

* **修复方案**：onGiveUp后启动定时探活(30s)，恢复后自动重连

* **预估改动量**：低

* **优先级**：P2

***

### 3.11 手稿 (Manuscript)

#### MAN-01 | chapter\_version表无容量上限/无清理策略/无分页 | P0

* **问题描述**：`store/chapters.py:346-358` list\_chapter\_versions无LIMIT。每次save/loop候选/选择环都CREATE chapter\_version含完整prose。200章×50次=10000+条确定性膨胀

* **影响范围**：数据库存储线性增长，API响应体积膨胀

* **修复方案**：1) list加分页LIMIT+OFFSET; 2) 引入清理策略：保留最近N个+里程碑+引用版本; 3) candidate/draft设更短保留期

* **预估改动量**：中

* **优先级**：P0

#### MAN-02 | 无并发编辑冲突检测（last-write-wins） | P1

* **问题描述**：`store/chapters.py:241-271`save\_chapter纯UPSERT覆盖写，无version/ETag。多tab/多设备编辑后保存者无条件覆盖

* **影响范围**：数据静默丢失（当前单用户形态下风险可控）

* **修复方案**：chapter增version字段；save带expected\_version，不匹配返回409

* **预估改动量**：中

* **优先级**：P1

#### MAN-03 | 永久删除未级联清理canon\_candidate | P1

* **问题描述**：`delete_chapter_permanent`清理15+关联表但遗漏canon\_candidate WHERE seq=$seq

* **影响范围**：孤儿正典候选指向不存在的章节

* **修复方案**：追加DELETE canon\_candidate WHERE seq=$seq

* **预估改动量**：1行

* **优先级**：P1

#### MAN-04 | 归档未处理未决正典候选 | P1

* **问题描述**：`archive_chapter`仅设archived=true，未处理pending canon\_candidate

* **影响范围**：归档后候选列表仍有该章待审条目

* **修复方案**：归档时将该章pending的canon\_candidate批量设为dismissed

* **预估改动量**：低

* **优先级**：P1

#### MAN-05 | 大纲/节拍/演绎无版本记录 | P2

* **问题描述**：`update_chapter_meta`直接UPDATE无快照，修改后旧版本不可恢复

* **影响范围**：设计阶段产物的可恢复性

* **修复方案**：对synopsis/scene\_truth/deductions关键字段变更时追加轻量快照

* **预估改动量**：中

* **优先级**：P2

#### MAN-06 | chatWrite SSE无超时且无重连 | P2

* **问题描述**：`web/src/api.js:772-821`AbortController无timeout，流断开无重连

* **影响范围**：LLM长时间未响应时前端无限等待

* **修复方案**：添加可配置超时(180s)；断流时如已收proposal\_start触发partial recovery

* **预估改动量**：中

* **优先级**：P2

#### MAN-07 | Ingest Worker无自动重试 | P2

* **问题描述**：BackgroundTasks一次性执行失败标failed仅靠用户手动重试

* **影响范围**：LLM超时导致章节ingest永久failed

* **修复方案**：增有限重试(max 2-3次指数退避)或cron扫描failed自动重跑

* **预估改动量**：中

* **优先级**：P2

#### MAN-08 | postCheck结果不落库且无hash失效检查 | P2

* **问题描述**：`write.py:720`注释"不落库"；结果存useState切章即丢。正文编辑后旧体检结果仍在展示

* **影响范围**：质量判断误导

* **修复方案**：前端postCheckResult附proseHash，渲染时比对当前hash不匹配标"已过期"

* **预估改动量**：低

* **优先级**：P2

#### MAN-09 | 选择环终选来源未持久化 | P2

* **问题描述**：`select_finalize`调save\_chapter不带来源字段，无法直接判断正文源自哪次选择环

* **影响范围**：正文溯源能力

* **修复方案**：chapter表增source\_selection\_id/source\_version\_id字段

* **预估改动量**：低

* **优先级**：P2

#### MAN-10 | 切章自动保存fire-and-forget无重试 | P2

* **问题描述**：`WriteLayout.jsx:70-111`切章flush失败仅localStorage stash+toast无重试队列

* **影响范围**：快速切章时数据可能留在localStorage

* **修复方案**：进入章节时自动检测同章stash并重试上传

* **预估改动量**：低

* **优先级**：P2

#### MAN-11 | 章节重排乐观更新无回滚 | P2

* **问题描述**：重排走主编审批流，乐观UI更新后审批拒绝不回滚

* **影响范围**：用户看到新顺序但实际被否决

* **修复方案**：审批拒绝/超时后自动reload outline

* **预估改动量**：低

* **优先级**：P2

***

### 3.12 演绎 (Deduce/Playbook)

#### DED-01 | chat\_write路径无章节锁 | P0

* **问题描述**：`write.py:384-424`同一章同时触发两次写会竞态写入save\_chapter\_prose，chapter\_lock.py有完整acquire/release API但chat\_write未引入

* **影响范围**：并发写入时正文覆写丢失

* **修复方案**：chat\_write入口处调acquire\_chapter\_lock+try/finally release+busy检测返回409

* **预估改动量**：低

* **优先级**：P0

#### DED-02 | Playbook run\_stage无内置章节锁 | P0

* **问题描述**：完全依赖上层加锁，直接API/脚本调用thicken\_stage存在并发风险。（多报告提及）

* **影响范围**：MCP外调用方并发时产物覆写

* **修复方案**：pipeline.py的run\_stage入口处增acquire\_chapter\_lock(kind="run")

* **预估改动量**：低

* **优先级**：P0

#### DED-03 | ingest apply\_delta无事务保护 | P0

* **问题描述**：`ingest.py:258-400`purge\_ingest(seq)清除后逐条写入，中途崩溃知识图永久残缺。同稿指纹匹配跳过不自愈。（多报告提及）

* **影响范围**：章知识丢失不可自愈

* **修复方案**：SurrealDB事务包裹(BEGIN...COMMIT)或两阶段提交+ingest\_integrity\_check启动扫描

* **预估改动量**：中

* **优先级**：P0

#### DED-04 | apply\_change\_pack无回滚机制 | P0

* **问题描述**：`canon_loop.py:427-554`逐条apply某条失败记rejected但已apply不回滚，部分生效导致设定不一致。（多报告提及）

* **影响范围**：设定库原子性

* **修复方案**：引入预检模式dry\_run+applied\_items日志+逆操作undo；或pending标签批量confirm

* **预估改动量**：高

* **优先级**：P0

#### DED-05 | leak\_markers依赖人工标注 | P0

* **问题描述**：`codex_secret_bridge.py:40-46`明确"leak\_markers留空"且全仓无自动提取。bridge创建的secret命题仅靠recall visible\_to单道防线。（多报告提及）

* **影响范围**：限知泄露风险（知情POV倒灌）

* **修复方案**：sync\_\*中基于target+field自动生成基础leak\_markers；增auto\_generate\_leak\_markers函数

* **预估改动量**：中

* **优先级**：P0

#### DED-06 | 卷纲→章纲无自动细化闭环 | P0

* **问题描述**：synopsis留空时duty\_generate收到"本章责：（无）"无约束生成偏离卷纲

* **影响范围**：新书开写时叙事偏离

* **修复方案**：短期：synopsis空时硬阻断返回{ok:False}; 中期：增suggest\_chapter\_synopsis工具

* **预估改动量**：低(短期)/中(中期)

* **优先级**：P0

#### DED-07 | build\_ctx与ContextAssembler两套并行上下文系统 | P0

* **问题描述**：`playbook/context.py:730-760`和context\_assembler.py数据源重叠但取数逻辑独立无共享缓存，同一轮写作中可能不一致

* **影响范围**：playbook规划与写路径数据一致性

* **修复方案**：短期引入ContextSnapshotCache(per-request)；中期build\_ctx委托给Assembler底层

* **预估改动量**：中(短期)/高(中期)

* **优先级**：P0

#### DED-08 | chapter\_state抽取失败无自动恢复 | P0

* **问题描述**：LLM多次失败返回{ok:False}，章间连续性数据断裂，下一章prev\_state=None。（多报告提及）

* **影响范围**：连续性断裂导致下章叙事衔接失败

* **修复方案**：增降级state机制+下章build\_ctx检测needs\_human触发re-extract+state\_recovery\_cron

* **预估改动量**：中

* **优先级**：P0

#### DED-09 | Discussion路径无质量检查 | P1

* **问题描述**：讨论产出的建议/分析完全无质量门控，模型可能幻觉设定细节

* **影响范围**：作者收到错误建议

* **修复方案**：Discussion输出后异步validate\_discussion\_claims，检测到与正典矛盾时追加提示

* **预估改动量**：中

* **优先级**：P1

#### DED-10 | \_quality\_loop计数器逻辑缺陷 | P1

* **问题描述**：ParseError时quality不递增只continue，理论上可超长循环

* **影响范围**：潜在超预期LLM调用量

* **修复方案**：ParseError时同时递增quality和infra\_fails；或增total\_attempts总计数器

* **预估改动量**：1行

* **优先级**：P1

#### DED-11 | advisory分支正文悬空 | P1

* **问题描述**：`loop.py:491-493`verdict=advisory时正文未落库未ingest，需人工触发save-chapter。前端无引导/无超时。（多报告提及）

* **影响范围**：章稿永远不落库

* **修复方案**：增advisory\_ttl(72h)+前端"待确认"标注+accept\_advisory一键接受API

* **预估改动量**：中

* **优先级**：P1

#### DED-12 | 三套质量体系无统一聚合视图 | P1

* **问题描述**：playbook判官/post\_check/review三套体系无合一判定展示（多报告提及）

* **影响范围**：章节真实健康状态不透明

* **修复方案**：增ChapterHealthReport聚合模型+章节详情API暴露+前端红黄绿展示

* **预估改动量**：中

* **优先级**：P1

#### DED-13 | canon\_candidate无自动过期/清理 | P1

* **问题描述**：pending候选堆积无上限无过期。（多报告提及）

* **影响范围**：候选表膨胀，审核负担

* **修复方案**：增candidate\_ttl(30天)+audit\_maintenance定时扫描+UI按过期排序

* **预估改动量**：中

* **优先级**：P1

#### DED-14 | fact supersede无跨章广播 | P1

* **问题描述**：关闭旧态写新态不通知缓存的下游，同session可能读到旧态

* **影响范围**：极端情况下叙事引用过期事实

* **修复方案**：supersede\_fact后调\_emit\_cache\_invalidation("fact", work)

* **预估改动量**：低

* **优先级**：P1

#### DED-15 | build\_ctx soft\_fail静默降级 | P1

* **问题描述**：codex\_recall为空时仍会生成（可能瞎编设定），只记日志不阻断

* **影响范围**：设定召回失败时LLM编造

* **修复方案**：关键slot失败时注入"⚠️不编造"限制指令+metadata标注degraded\_slots

* **预估改动量**：低

* **优先级**：P1

#### DED-16 | volume\_ledger flag默认关 | P1

* **问题描述**：SCRIBE3\_VOLUME\_LEDGER未显式开启时卷台账完全静默失效

* **影响范围**：运维不知功能未生效

* **修复方案**：\_guide\_fail中记录flag未开状态；或默认开启

* **预估改动量**：低

* **优先级**：P1

#### DED-17 | recall\_service图通道默认关闭 | P1

* **问题描述**：SCRIBE3\_GRAPH\_RELATION\_RECALL需单独开启，默认关时角色关系网络不被召回。（多报告提及）

* **影响范围**：关系图信息缺失影响叙事一致性

* **修复方案**：评估性能后默认开启或自适应策略(角色数>5时启用)

* **预估改动量**：低

* **优先级**：P1

#### DED-18 | draft冻结成功但state失败时上层误判 | P1

* **问题描述**：\_run\_draft将state抽取失败映射为整个draft的ok=False，但draft已冻结，上层可能决定重做

* **影响范围**：不必要的draft重生成浪费

* **修复方案**：返回值增细分{ok:True, state\_ok:False}，上层仅在draft层自身问题时重做

* **预估改动量**：低

* **优先级**：P1

#### DED-19 | craft\_skills无自动选择 | P1

* **问题描述**：完全依赖LLM自主判断何时读取哪个技法。（多报告提及）

* **影响范围**：关键技法可能被忽略（如限知章不调"限知视角"）

* **修复方案**：增场景检测→强制注入逻辑；关键技法设trigger条件

* **预估改动量**：中

* **优先级**：P1

#### DED-20 | scene\_grid诊断注入路径不完整 | P1

* **问题描述**：diagnose\_scene\_grid输出需外部显式传入build\_revision\_letter。（多报告提及）

* **影响范围**：问诊信不含场景动能诊断

* **修复方案**：build\_revision\_letter内部自动调diagnose\_scene\_grid或从experience\_state读取

* **预估改动量**：低

* **优先级**：P1

#### DED-21 | LLM抽取失败静默降级无告警 | P2

* **问题描述**：canon\_extract LLM失败只返回标记结果，无告警通知用户本章设定抽取不完整

* **影响范围**：正典抽取覆盖率不透明

* **修复方案**：增加告警通知机制（收件箱item或toast）

* **预估改动量**：低

* **优先级**：P2

#### DED-22 | ingest grep\_back\_verify标注"未明确"仍写入 | P2

* **问题描述**：核对不到原文的事实只标注annotated但仍apply到store，可能引入幻觉事实

* **影响范围**：知识图可靠性

* **修复方案**：未验证事实标unverified+不计入写路径正典注入

* **预估改动量**：中

* **优先级**：P2

#### DED-23 | chat\_write与Playbook路径质量标准不同 | P2

* **问题描述**：同一章可能通过两条路径产出不同质量标准正文，用户无法感知差异

* **影响范围**：产出质量不一致

* **修复方案**：文档+UI标注"对话式产出（未经五层审查）"

* **预估改动量**：低

* **优先级**：P2

#### DED-24 | recent\_duty\_summary只看3章硬编码 | P2

* **问题描述**：长卷时LLM对早期duty无感知，信息衰减

* **影响范围**：长卷叙事连续性

* **修复方案**：改为动态窗口（基于卷边界或N=min(5,卷内章数)）

* **预估改动量**：低

* **优先级**：P2

***

## 4. 跨板块链路优化清单

### CRS-01 | 质量闭环统一聚合

* **涉及板块**：演绎 + 主编 + 仪表盘

* **问题**：playbook判官、post\_check检测器族、review/runner三套质量体系各自独立，无统一的"章节总体健康度"聚合视图

* **修复方案**：引入ChapterHealthReport聚合模型（playbook\_status/post\_check\_verdict/review\_coverage/overall\_grade），暴露API+前端展示

* **优先级**：P1

### CRS-02 | 正典回写→全局同步链

* **涉及板块**：设定库 + 图谱 + 演绎 + 素材库

* **问题**：正典Apply后三处同步断裂（digest/secret\_bridge/语义索引），导致审批通过≠全局生效

* **修复方案**：apply\_change\_pack成功后统一触发sync\_entity\_digests + sync\_\*\_secrets + semantic\_index更新

* **优先级**：P0/P1

### CRS-03 | 记忆召回统一中枢完善

* **涉及板块**：演绎 + 素材库 + 设定库

* **问题**：图通道默认关闭、影子模式无自动切换、emotion\_module双重注入

* **修复方案**：默认开启图通道+影子模式连续N次失败自动切换+统一recall入口去重

* **优先级**：P1

### CRS-04 | 经验压力→写路径注入闭环

* **涉及板块**：主编 + 演绎

* **问题**：letter诊断和scene\_grid信息仅供展示，AI生成时完全"不记得"系统已诊断的问题

* **修复方案**：build\_ctx增revision\_letter\_digest和scene\_grid slot；experience产出自动注入写prompt

* **优先级**：P1

### CRS-05 | 限知门控全链路加固

* **涉及板块**：图谱 + 设定库 + 演绎 + 伏笔

* **问题**：leak\_markers空、character secret bridge默认关、正典Apply不触发限知桥、伏笔兑现不进知识图

* **修复方案**：auto\_generate\_leak\_markers + 默认开启role bridge + apply尾部补sync + advance后生成proposition

* **优先级**：P0/P1

### CRS-06 | 级联删除统一治理

* **涉及板块**：设定库 + 图谱 + 素材库 + 手稿

* **问题**：多类实体删除不经lifecycle/不级联清理，孤儿数据可被召回

* **修复方案**：统一lifecycle保护路径，覆盖faction/item/term/world\_rule/material级联

* **优先级**：P1

### CRS-07 | SSE实时更新全面接入

* **涉及板块**：仪表盘 + 时间线 + 系统中心 + 主编

* **问题**：多个前端面板未订阅已有的s3-live事件总线

* **修复方案**：InsightView/TimelineView/SystemHub统一接入s3-live事件监听

* **优先级**：P1

***

## 5. 第十三轮迭代遗留项

### T13-01 | T04红测试未修复（裸入库）

* **问题**：`test_discussion_instructions_contain_pulse` FAILED。fake\_stream.\_\_name\_\_不含"hermes"导致GAP-12门闸拦截

* **修复方案**：`monkeypatch.setenv("SCRIBE3_HERMES_ONLY_LLM", "0")`（1行）或`fake_stream.__name__ = "hermes_complete_stream"`

* **优先级**：P0（阻断统一度100%声称）

### T13-02 | xfail-ledger标"已修复"与事实不符

* **问题**：`xfail-ledger.md:17`标注已修复但实际仍FAILED

* **修复方案**：回退为"续挂/受阻于GAP-12"

* **优先级**：P0（文档诚实度）

### T13-03 | round13-debts声称"无代码遗留"

* **问题**：遗漏T04残余项

* **修复方案**：补登T04残余行

* **优先级**：P0（文档诚实度）

### T13-04 | shadow\_equal三层比对缺负面用例

* **问题**：可能误判True导致legacy回退被跳过

* **修复方案**：新增2-3个负面断言（删段落/换顺序必须返回False）

* **优先级**：P1

### T13-05 | test\_recall\_unity白名单维护风险

* **问题**：白名单需人工维护，新文件若未加入可漏报

* **修复方案**：改为动态发现非允许文件（排除法）

* **优先级**：P1

### T13-06 | deploy\_check.sh macOS不可用

* **问题**：systemd-analyze verify在非Linux环境不可用，`|| true`兜底使检查永不失败

* **修复方案**：加`command -v systemd-analyze`前置判断或标注仅限Linux

* **优先级**：P1

### T13-07 | test\_epistemic\_100用inspect.getsource源码断言

* **问题**：重构方法名即失效

* **修复方案**：改为调用级验证（用mock store实际跑一次recall）

* **优先级**：P2

### T13-08 | budget\_overrun阈值硬编码1.05

* **问题**：未走设置中心，长文作者context域波动大5%略紧

* **修复方案**：改为设置项或分级（>10% warning, >5% info）

* **优先级**：P2

***

## 6. 实施路线图

### Stage 0：止血（P0全修，预计1-2天）

**目标**：消除所有阻断性/数据损坏/安全风险

| 批次  | 修复项                                                                               | 预估   |
| --- | --------------------------------------------------------------------------------- | ---- |
| 0.1 | T13-01/02/03（台账诚实度+T04 fixture，3×1行）                                              | 0.5h |
| 0.2 | DSH-01（除零保护，1行）+ ATL-01（归档过滤，1行）+ CDX-02（字段名修正，1行）+ MAT-04（cache invalidation，1行） | 1h   |
| 0.3 | CDX-01（patch白名单动态化）+ CDX-03（prompt动态schema）                                       | 2h   |
| 0.4 | DED-01/02（章节锁补全）+ DED-06短期（synopsis空阻断）                                           | 2h   |
| 0.5 | SYS-01/02（admin确认弹窗+toast）                                                        | 1h   |
| 0.6 | MAN-01（版本表分页+清理策略）                                                                | 4h   |
| 0.7 | PRM-01（overdue硬闸）+ PRM-02（并发安全）                                                   | 3h   |

### Stage 1：系统性模式修复（SSE接入/级联完整性/同步断裂，预计3-5天）

**目标**：修复跨板块反复出现的共性问题模式

| 批次  | 修复项                                                        | 预估   |
| --- | ---------------------------------------------------------- | ---- |
| 1.1 | SSE全面接入：DSH-02 + TML-01 + DIR-06/07 + SYS-09               | 1d   |
| 1.2 | 正典Apply同步链：CDX-04/05/06 + ATL-03 + CRS-02                  | 1d   |
| 1.3 | 级联删除治理：CDX-08/09 + ATL-02/05 + MAT-03 + MAN-03/04 + CRS-06 | 1.5d |
| 1.4 | leak\_markers自动化：DED-05 + CDX-11                           | 0.5d |

### Stage 2：并发安全与持久化（分布式锁/Proposal持久化/事务保护，预计3-5天）

**目标**：解决多Worker部署安全和数据原子性

| 批次  | 修复项                                   | 预估   |
| --- | ------------------------------------- | ---- |
| 2.1 | DIR-01（Proposal持久化到DB）                | 1.5d |
| 2.2 | DIR-02（Pilot分布式锁）                     | 1d   |
| 2.3 | DED-03（ingest事务保护）+ DED-04（apply回滚机制） | 2d   |
| 2.4 | DED-07短期（ContextSnapshotCache）        | 0.5d |
| 2.5 | MAN-02（并发编辑冲突检测）                      | 0.5d |

### Stage 3：功能补全（死路径激活/UI反馈完善/缺失闭环补齐，预计5-7天）

**目标**：激活死路径、补齐闭环、增强UI反馈

| 批次  | 修复项                                          | 预估   |
| --- | -------------------------------------------- | ---- |
| 3.1 | 经验层注入：DIR-12/13 + DED-20 + CRS-04            | 1d   |
| 3.2 | 收件箱闭环：DIR-08/09/10/11 + DED-11(advisory TTL) | 1d   |
| 3.3 | 因果根激活：ATL-04 + TML-02/07                     | 1d   |
| 3.4 | 母题改进：MOT-01/02/03/04/05                      | 1.5d |
| 3.5 | 旅程补全：JNY-01/02/03                            | 1d   |
| 3.6 | 召回完善：DED-17 + DED-19 + MAT-01 + CRS-03       | 1d   |

### Stage 4：质量加固（测试覆盖/CI守卫/文档闭环，预计3-5天）

**目标**：提升测试覆盖率和CI可靠性

| 批次  | 修复项                                                 | 预估   |
| --- | --------------------------------------------------- | ---- |
| 4.1 | DIR-04/05（SSE+Blocker测试）+ T13-04/05/06              | 1.5d |
| 4.2 | DED-08（chapter\_state自动恢复）+ DIR-03（force\_rollback） | 1d   |
| 4.3 | DED-12（质量聚合视图）+ CRS-01                              | 1d   |
| 4.4 | DED-13/14/15/16/18（各项P1修复）                          | 1d   |

### Stage 5：性能与体验优化（信息过载治理/懒加载/分页，预计2-3天）

**目标**：优化大规模数据场景的性能和用户体验

| 批次  | 修复项                                       | 预估   |
| --- | ----------------------------------------- | ---- |
| 5.1 | DSH-07（分页/虚拟列表）+ TML-05（全表查优化）            | 1d   |
| 5.2 | DSH-03（时区）+ JNY-04/05/06/07/08            | 0.5d |
| 5.3 | 体验优化：SYS-08/10 + MAN-06/10/11 + DIR-17/18 | 1d   |

***

## 7. 优先级矩阵

| 编号     | 板块        | 问题标题                      | 影响面 | 修复成本   | 优先级 |
| ------ | --------- | ------------------------- | --- | ------ | --- |
| T13-01 | 迭代        | T04红测试裸入库                 | 低   | 极低(1行) | P0  |
| DSH-01 | 仪表盘       | totalGoal=0除零             | 低   | 极低(1行) | P0  |
| ATL-01 | 图谱        | 归档角色泄入prompt              | 高   | 极低(1行) | P0  |
| CDX-02 | 设定库       | digest字段名错误               | 高   | 极低(1行) | P0  |
| MAT-04 | 素材库       | delete无cache invalidation | 高   | 极低(1行) | P0  |
| CDX-01 | 设定库       | patch白名单硬编码               | 高   | 低      | P0  |
| DED-01 | 演绎        | chat\_write无章节锁           | 高   | 低      | P0  |
| DED-02 | 演绎        | run\_stage无章节锁            | 高   | 低      | P0  |
| DED-06 | 演绎        | 卷纲章纲无闭环(短期)               | 中   | 低      | P0  |
| SYS-01 | SystemHub | 危险操作缺确认                   | 中   | 低      | P0  |
| SYS-02 | SystemHub | 零toast反馈                  | 中   | 低      | P0  |
| PRM-01 | 伏笔        | Overdue无硬闸                | 高   | 中      | P0  |
| PRM-02 | 伏笔        | 并发写入无安全                   | 高   | 低      | P0  |
| ATL-02 | 图谱        | 势力删除无lifecycle            | 高   | 中      | P0  |
| ATL-03 | 图谱        | Apply不触发限知桥               | 高   | 低      | P0  |
| ATL-04 | 图谱        | 因果根端点断线                   | 中   | 中      | P0  |
| MAT-01 | 素材库       | emotion双重注入               | 高   | 低      | P0  |
| MAT-02 | 素材库       | evidence无溯源验证             | 高   | 中      | P0  |
| MAT-03 | 素材库       | 删codex不清material          | 高   | 低      | P0  |
| MAN-01 | 手稿        | 版本表无限膨胀                   | 高   | 中      | P0  |
| DIR-01 | 主编        | Proposal无持久化              | 高   | 高      | P0  |
| DIR-02 | 主编        | 多Worker竞态                 | 高   | 高      | P0  |
| DIR-03 | 主编        | Artifact丢失卡死              | 高   | 中      | P0  |
| DIR-04 | 主编        | SSE零测试                    | 中   | 中      | P0  |
| DIR-05 | 主编        | Blocker零测试                | 中   | 中      | P0  |
| DED-03 | 演绎        | ingest无事务                 | 高   | 中      | P0  |
| DED-04 | 演绎        | apply无回滚                  | 高   | 高      | P0  |
| DED-05 | 演绎        | leak\_markers空            | 高   | 中      | P0  |
| DED-07 | 演绎        | 两套上下文系统                   | 高   | 中      | P0  |
| DED-08 | 演绎        | state恢复缺失                 | 高   | 中      | P0  |
| CDX-03 | 设定库       | prompt不读schema            | 中   | 中      | P0  |

***

## 8. 验收标准

### Stage 0 完成条件

* [ ] CI全绿（含T04修复后）

* [ ] 所有P0项已合并main

* [ ] 除零/归档/白名单/章节锁/版本分页等单行修复项通过回归测试

* [ ] admin危险操作均有ConfirmDialog保护

* [ ] xfail-ledger/round13-debts准确反映事实

### Stage 1 完成条件

* [ ] InsightView/TimelineView/SystemHub接入s3-live后，存稿→切面板<2s自动刷新

* [ ] 正典Apply后新设定在<5s内可被语义召回

* [ ] 删除faction/item/term后无孤儿proposition被召回（测试验证）

* [ ] codex\_secret\_bridge创建的命题含非空leak\_markers

### Stage 2 完成条件

* [ ] Proposal持久化后页面刷新可恢复pending proposal

* [ ] 多Worker压测：同章并行pilot step无数据损坏

* [ ] ingest中途kill进程后重启可自愈（integrity\_check通过）

* [ ] apply\_change\_pack部分失败可回滚已apply项

### Stage 3 完成条件

* [ ] letter/scene\_grid诊断注入写路径prompt（通过prompt内容断言验证）

* [ ] 因果根编辑前端可达（E2E测试）

* [ ] 母题echo\_terms参与ingest匹配（隐性回声可被识别）

* [ ] 旅程门槛软闸生效（无intent开写返回409）

### Stage 4 完成条件

* [ ] SSE端点有≥3个集成测试

* [ ] Blocker双向闭环有≥2个测试用例

* [ ] chapter\_state抽取失败后下一章仍能获得降级state

* [ ] ChapterHealthReport API返回三体系聚合状态

### Stage 5 完成条件

* [ ] 200+章仪表盘首次加载<1s

* [ ] 时间线story轴1000事件无性能退化

* [ ] 连胜统计使用用户时区

***

## 9. 风险与依赖

### 关键依赖关系

| 修复项              | 依赖                     | 说明                                 |
| ---------------- | ---------------------- | ---------------------------------- |
| DED-03（ingest事务） | SurrealDB事务能力          | 需评估SurrealDB BEGIN/COMMIT在当前版本的完整性 |
| DIR-02（分布式锁）     | Redis或DB advisory lock | 需引入新基础设施或评估SurrealDB锁能力            |
| DED-04（apply回滚）  | 逆操作可行性评估               | supersede\_fact等操作的逆操作需设计          |
| Stage 1.2（正典同步链） | Stage 0.3完成            | 需先修复patch白名单才能正确同步                 |
| Stage 3.4（母题改进）  | echo\_terms数据质量        | 需确保现有母题echo\_terms字段已填充            |

### 风险登记册

| 风险              | 级别 | 缓解措施                             |
| --------------- | -- | -------------------------------- |
| SurrealDB事务限制   | 中  | 备选方案：两阶段提交+integrity\_check      |
| 分布式锁引入复杂度       | 中  | 可先用单Worker限制pilot路由              |
| 正典回滚的不可逆操作      | 高  | 改为pending→confirm两阶段而非write→undo |
| echo\_terms数据稀疏 | 低  | 先从现有motif定义自动生成初始echo\_terms     |
| Stage间依赖导致阻塞    | 中  | 各Stage内批次可并行；Stage间串行依赖已最小化      |
| 多Worker压测环境     | 低  | 可用docker-compose模拟多worker        |

***

## 10. 附录：源报告索引

### 21份深度审查报告完整路径

| #  | 报告名称                   | 路径                                                                        |
| -- | ---------------------- | ------------------------------------------------------------------------- |
| 1  | 系统中心六层深度审查结论           | `<vault>/01-项目/tonglu/2026-08-23-系统中心深度审查结论.md`        |
| 2  | SystemHub双层功能闭环与设置幽灵审计 | `<vault>/00-收件箱/2026-08-23-铜炉系统中心SystemHub双层审计报告.md`   |
| 3  | SystemHub第三层与第四层审计     | `<vault>/00-收件箱/2026-08-23-SystemHub-L3-L4-深度审计报告.md`  |
| 4  | 仪表盘深度审查报告（六维度）         | `<vault>/01-项目/铜炉/2026-08-23-仪表盘深度审查报告.md`             |
| 5  | 仪表盘维度B+C审计             | `<vault>/00-收件箱/2026-08-23-铜炉仪表盘维度BC审计报告.md`           |
| 6  | 设定库业务闭环深度审查            | `<vault>/01-项目/tonglu/2026-08-23-设定库业务闭环深度审查报告.md`     |
| 7  | 素材库板块深度闭环审计            | `<vault>/01-项目/tonglu/2026-08-23-素材库板块深度闭环审计报告.md`     |
| 8  | 图谱业务板块深度闭环审查           | `<vault>/01-项目/tonglu/2026-08-23-图谱业务板块深度闭环审查报告.md`    |
| 9  | 伏笔模块深度审查与改进Spec        | `<vault>/01-项目/tonglu/2026-08-23-伏笔模块深度审查报告与改进Spec.md` |
| 10 | 母题板块深度审查               | `<vault>/01-项目/tonglu/2026-08-23-母题板块深度审查报告.md`        |
| 11 | 时间线板块深度审查              | `<vault>/01-项目/tonglu/2026-08-23-时间线板块深度审查报告.md`       |
| 12 | 旅程业务健康度审查              | `<vault>/01-项目/tonglu/2026-08-23-旅程业务健康度审查报告.md`       |
| 13 | 主编业务板块深度闭环审查           | `<vault>/01-项目/tonglu/2026-08-23-主编业务板块深度闭环审查报告.md`    |
| 14 | 手稿业务板块深度审查             | `<vault>/01-项目/tonglu/2026-08-23-手稿业务板块深度审查报告.md`      |
| 15 | 演绎板块深度审查（全景链路+缺口分析）    | `<vault>/01-项目/tonglu/2026-08-23-铜炉演绎板块深度审查报告.md`      |
| 16 | 演绎板块质量闭环与正典回写链路深度审查    | `<vault>/00-收件箱/2026-08-23-铜炉演绎板块质量闭环与正典回写链路深度审查.md`   |
| 17 | 记忆状态链路与经验压力编排层深度审查     | `<vault>/00-收件箱/2026-08-23-铜炉记忆状态链路与经验压力编排层深度审查报告.md`  |
| 18 | 第十三轮盘点报告               | `<vault>/00-收件箱/2026-08-23-铜炉第十三轮盘点报告.md`              |
| 19 | 第十三轮写作专家评审（Lena）       | `<vault>/00-收件箱/2026-08-23-铜炉第十三轮写作专家评审-Lena.md`       |
| 20 | 第十三轮架构师评审（Marco）       | `<vault>/00-收件箱/2026-08-23-铜炉第十三轮架构师评审-Marco.md`       |
| 21 | 第十三轮双视角评审报告            | `<vault>/01-项目/tonglu/2026-08-23-铜炉第十三轮双视角评审报告.md`     |

### 参考文档

| 文档       | 路径                                                                      |
| -------- | ----------------------------------------------------------------------- |
| 昨日终极改造方案 | `<vault>/01-项目/tonglu/2026-08-22-铜炉终极改造方案-三专家整合版.md` |

***

*文档生成时间：2026-08-23 | 基于21份深度审查报告综合编写 | 全量优化项约215项*
