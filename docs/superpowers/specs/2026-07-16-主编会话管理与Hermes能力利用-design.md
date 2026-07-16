# 主编会话管理 + Hermes 能力充分利用 · 设计 Spec

日期:2026-07-16
来源:作者四问——"历史会话要不要折叠 / 要不要历史会话·新建会话 / Hermes 没有这些能力吗能不能直接用 / 会话记忆和系统深度契合吗",追加"充分利用 Hermes 这块的能力,能利用的都利用上"。

---

## 1. 背景与结论先行

### 1.1 现状痛点
- 主编对话**一打开一大堆**:一 work 恒一条连续线程(store.py `get_or_create_editorial_thread`,"最早 active 稳定不漂"),前端 ChiefDock 一次性全量加载该线程消息(`threadMessages`,limit=500)全部渲染。
- **无历史会话/新建会话**:后端 `editorial_thread` 表 + `GET /chat/threads` + `POST /chat/threads/{id}/fork` 能力齐全,但前端零调用(无任何 jsx 使用 `api.threads()`/`api.forkThread()`)。

### 1.2 Hermes 能不能直接用(核心判断)
**不能用 Hermes 替代会话层,能用它做增量**:
- `hermes sessions` 管的是 CLI/telegram 等**平台会话**(SQLite state.db),不是 per-work 小说线程;
- Responses 层 `conversation`/`previous_response_id` 是**服务端 LRU 100,掉链常态**(hermes_runtime.py:87 注释明确),只配当"续接锚";
- 主编会话记忆**与系统深度契合**(四层 Hermes 给不了):限知过滤、UCM/设定耦合(s3_ 工具实时联查)、结构化留痕(可列/可 fork/可审计)、多会话管理语义。
- 结论:**会话存储权威源 = scribe3 `editorial_thread` + `chat_message`**;Hermes 提供续接锚(已在用)+ 本方案新增的四个增量能力(skills/cron/memory/导出范式)。

### 1.3 Hermes v0.18.2 能力盘点(实测 `hermes --help` 及子命令)
| 能力 | 实测 | 本方案用法 | 不用的理由 |
|---|---|---|---|
| Responses/Runs/MCP/approval | 已在用(:8642/:8643/:8644 三 profile) | 维持 | — |
| skills(browse/install/渐进披露) | ✅ | **P1**:通用写作技法按需披露 | — |
| cron(create/pause/run/tick) | ✅ | **P2**:夜间摘要兜底 + 每日创作摘报 | — |
| memory(内置 MEMORY.md/USER.md 层) | ✅ | **P3**:跨书作者偏好 | — |
| sessions(export/archive/rename) | ✅ | 借鉴范式给 editorial_thread(P0b 导出) | 存储层不搬(平台会话≠小说线程) |
| insights(token/成本分析) | ✅ | 不用 | 与 scribe3 `/ai/usage` 台账重叠 |
| memory-graph/learning/journey | ✅ | 不用 | agent 通用学习图谱,与 UCM(小说设定记忆)重叠 |

---

## 2. 深度审核记录(第一批设计的修正,防实施踩坑)

| # | 审出的问题 | 严重度 | 修正 |
|---|---|---|---|
| 1 | "后端八成现成"高估:`/chat/stream`、`/chat/agentic-stream`、`/chat/write` **均不收 thread_id**,恒经 `_editor_turn_context`→最早 active 线程。前端就算做了切换,消息仍全落最早线程 | 🔴 | thread_id 参数贯通三端点(+runs 留痕对齐);**不传回落 active 线程,字节兼容** |
| 2 | 会话切换 × UCM 快照绑定漂移:前端 threadMode 来源是 `snapshot.thread_id`,context session 创建绑 active 线程;只改 dock 本地状态会导致 bind 与实际线程漂移=串台 | 🔴 | `create_context_session` 增可选 thread_id;**切会话=重建 context session** 绑新线程 |
| 3 | 摘要挂 cron 滞后一天 | 🟠 | **每轮后台增量摘要**(阈值触发,`_bg_ingest` 范式);cron 只兜底 |
| 4 | fork 不继承父摘要=失忆分支 | 🟠 | fork 拷贝父 summary 入子线程 |
| 5 | 生成中切会话静默中止在途流 | 🟡 | busy 时切会话弹确认;部分稿 `_ChatTurnLog` 已落库不丢 |
| 6 | 归档唯一 active 线程后 get_or_create 静默再造;"当前会话"选择权未定 | 🟡 | localStorage `s3.thread.current.<work>`;fallback:localStorage→active→新建 |
| 7 | 新会话都叫"主编讨论"无法辨认 | 🟡 | 首条用户消息自动命名(截 24 字,可改名),零 LLM |
| 8 | 多会话引入新失效模式:跨线程历史串台 | 🟠 | e2e 矩阵⑥扩**线程隔离对抗测试**(B 线程 `llm_stub.last_history` 绝不含 A 内容) |
| 9 | 导出带工具输出扩大泄密面 | 🟡 | 导出只含 role+content+ts |

---

## 3. 架构(4 层,P0 基座)

```
P0  会话管理基座(editorial_thread 权威源 + dock 下拉 + 折叠)
 ├── P1  skills:通用写作技法渐进披露(挂 agentic 层)
 ├── P2  cron:夜间摘要兜底 + 每日创作摘报(喂 P0 摘要;摘报进决策收件箱)
 └── P3  memory:USER.md 跨书作者偏好(注入会话 instructions)
```
依赖:P0 先行;P1/P2/P3 相互独立。分期:**P0a → P0b → P2 → P1 → P3**。

---

## 4. P0a 多会话骨架(独立可上线)

### 4.1 后端
- **thread_id 贯通**:`GET /chat/stream`、`GET /chat/agentic-stream`、`GET|POST /chat/write` 增可选 `thread` 参数。**传了必须有效**:不存在/已归档 → 404,跨 work(`_assert_work_binding`)→ 409,**绝不静默回落 active 线程**(回落=串台掩盖器)。不传(旧调用方)= active 线程——显式文档化的参数默认(同 `work="main"`),非降级;新前端一律显式传 thread。runs 路径留痕归属按 `test_all_chat_sse_endpoints_persist_or_are_exempt` 现状对齐,若 runs 留痕未挂线程则把 thread_id 传入 run trace。
- **`POST /chat/threads`**:显式新建(title 可选,默认"主编讨论·N");返回完整线程行。
- **`PATCH /chat/threads/{id}`**:rename(title ≤60 字)+ archive(status→archived)。归档"当前"线程由前端 fallback 链接管。
- **fork 补继承**:`fork_editorial_thread` 拷贝父 summary(分支不失忆)。
- **`create_context_session` 增可选 thread_id**(校验 work 绑定);不传=现行为。
- **自动命名**:`_ChatTurnLog` 落首条 user 消息时,若线程 title 仍是默认值→置为消息前 24 字。

### 4.2 前端
- **dock 顶部会话下拉**(已定 UI):当前会话名 ▾ → 列表(active 高亮/最近更新排序/归档区折叠)+「+ 新建会话」+「管理」(改名/归档/导出/从当前分支)。
- **切换流程**:busy 先弹确认(中止本轮)→ 重建 context session(带 thread_id)→ threadId 变化触发现有 loadedThreadRef 效应重拉消息 → localStorage 记 `s3.thread.current.<work>`。
- **当前线程解析链**:localStorage → 后端 active → 新建。**每次向下切换必须可见**:localStorage 指向的线程已归档/不存在 → toast 明示「原会话已归档/删除,已切到默认会话」,绝不静默换线程。

### 4.3 测试(TDD)
- store:create/rename/archive/fork 继承 summary;
- 端点:thread 参数落对线程、跨 work 409、不传参回落 active(兼容);
- **e2e 对抗**:线程隔离(A/B 两线程,B 轮 `llm_stub.last_history` 无 A 内容);切换后 context session 绑定一致。

---

## 5. P0b 摘要折叠 + 导出(独立可上线)

### 5.1 注入层折叠(prompt)
- `_thread_history_for_prompt` 改**"summary(早期)+ 近 N 轮全文"**,替代现行"超预算丢最旧";summary 块明确标注「主编讨论早期摘要」。
- **每轮后台增量摘要**:turn 结束后若未摘要消息数>阈值(默认 40)→ BackgroundTasks 调 LLM(默认网关 :8642,无工具)增量压缩至 summary(≤1500 字),记 `summarized_upto_ts`。失败 log.error + 下轮重试;**连续失败必须前端可见**:线程行记 `summary_error`,摘要卡红字「早期摘要未更新(上次生成失败)」——不允许只躺在后端日志里。

### 5.2 显示层折叠(前端)
- `list_thread_messages` 增 `before_ts` 分页;dock 默认渲染近 N 轮(默认 30 条),顶部「载入更早」;更早区折叠为**摘要卡**(内容=thread.summary),点开可继续翻页。

### 5.3 导出
- `GET /chat/threads/{id}/export?format=md|jsonl`(借鉴 hermes sessions export);只含 role+content+ts;前端「管理」菜单触发下载。

---

## 6. P1 skills 写作技法渐进披露

- **边界**:题材无关**通用技法**(限知视角写法/对话潜台词/场景转换/节奏)→ Hermes skills;**本书专属** craft_rule → 留 DB 走现有 assembler(呼应"题材规则拆引擎层+题材层")。
- **形态**:技法写成 SKILL.md 装进 scribe3 profile;prompt 只带一行索引,触及才加载全文。
- **⚠ 实施首步=实测定案(二选一,无运行时降级)**:实测 Hermes 原生 skills 注入在 api_server(:8643 Responses)路径是否生效(CLI/chat 路径确定支持)。生效→方案A(原生注入);不生效→方案B(instructions 嵌技法索引每条一行 + `s3_skill_read(name)` 只读工具按需取全文)。**定案后即唯一路径,不做 A 失败切 B 的运行时降级**;运行期失败就报错可见。
- **provisioning**:技法文件进 git `deploy/hermes/skills/`,`provision_hermes.py` 安装(U-007 纪律)。

## 7. P2 cron 定时主编任务(两个 job)

| job | 频率 | 做什么 | 结果落哪 |
|---|---|---|---|
| 摘要兜底 | 每夜 | curl `POST /maintenance/summarize-threads`(压缩漏摘要长线程,幂等) | editorial_thread.summary |
| 创作摘报 | 每日 | 汇总伏笔超期(pulse 信号)/昨日字数 vs 目标/待批积压 | digest 行 → 决策收件箱新 kind=`daily_digest` |

- 失败可见:job 失败写 digest 行带 error 字段;收件箱 `degraded_sources` 范式显示,不静默。
- cron 定义进 git `deploy/hermes/crons.yaml`,provision 布署;`hermes cron status` 纳入启动守卫检查项(可选)。

## 8. P3 memory 跨书作者偏好

- **事实源 = Hermes `USER.md`**(天生跨书,hermes CLI/desktop 原生可见),内容限**作者层偏好**(偏短句/不煽情/叙事距离)。
- **注入路径唯一**:scribe3 读 USER.md 拼进 `_editor_system` instructions,这是**唯一依赖的注入路径**(不是兜底)。实施时验证网关是否也原生注入 USER.md——若是则关其一,防同内容双份;读文件失败直接抛(fail-loud),不静默无偏好。
- **写路径过待批**:主编识别稳定偏好 → elicitation 待批 → 作者批准才写入。
- **红线**(捕获点限知红线延续):偏好≠正典;书内设定/人物/世界观一律不进 USER.md;拿不准→不写。

---

## 9. 横切纪律

- **fail-loud(本方案零降级逻辑)**:线程列表失败=AsyncState error(已有);切换失败=danger toast;无效 thread 参数=404/409 抛,绝不回落 active;解析链向下切换=toast 可见;摘要失败=log.error+重试+**摘要卡红字**;cron 失败=digest error 字段+收件箱如实显示;USER.md 读失败=抛。禁止任何"静默回落旧线程/空历史/空偏好"。
- **可复现部署**:skills/crons/USER.md 模板全进 `deploy/hermes/`,provision_hermes.py 单命令布署。
- **测试**:每期 TDD;多会话防串台对抗测试为 P0a 验收硬门。

## 10. 验收标准

1. P0a:下拉可列/建/切/改名/归档/分支;消息落对线程(端点测试);线程隔离对抗测试绿;不传 thread 参数的旧调用行为字节不变(回归绿)。
2. P0b:长线程打开默认只见近 N 轮+摘要卡;「载入更早」可翻页;prompt 注入=summary+近窗(测试断言);导出 md/jsonl 可下载。
3. P1:讨论触及技法时主编能引用技法全文(真机验证);prompt 常驻部分只含索引行;craft_rule 注入路径回归绿。
4. P2:两 job 在 `hermes cron list` 可见且当夜/当日产出;收件箱见 daily_digest;job 失败时收件箱如实显示 error。
5. P3:两本书的主编都遵循同一偏好(真机);USER.md 写入全部经待批;红线测试(书内设定不入)。

## 11. 风险

- P1 网关 skills 注入行为未证实 → 实施首步实测定案(A/B 二选一),定案后无运行时降级路径。
- 多会话让"主编失忆"表象更易被误报(新会话本来就空)→ UI 新会话空态文案明示"全新会话,不带历史"。
- cron 依赖 Hermes 常驻(nohup 后台+轮询,既有运维事实)→ 启动守卫可选检查 cron scheduler 状态。
- 摘要质量影响掉链重建与折叠体验 → 摘要 prompt 要求保留:未决决策/作者偏好表态/伏笔承诺三类信息优先。
