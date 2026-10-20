# 功能域审查：Wave B 写作主链路

**审查日期:** 2026-07-08  
**审查范围:** B1 手稿目录/卷章/章选择；B2 章工作台阶段 tab；B3 正文编辑/保存/切章/版本；B4 主编写作对话/选中文本讨论改写/prompt；B5 Pilot/收件箱/选择环。  
**爆炸半径:** R1/R2/R4。  
**审查性质:** 只读审查，未修产品代码，未回退工作区改动。  

## 结论

Wave B 当前是 **主链路可写、测试基础较强，但产品闭环仍有 P1 级断点**。

优点很明确：正文保存已经有 `dirtyRef`、切章前保存、卸载兜底保存、跨作品 work 钉死、本地暂存稿恢复；选择环有半盲候选、强制终选理由、终选后通知中区重拉；Pilot 和收件箱已经有右栏入口，不再只是后端 curl 能力；后端相关定点测试全部通过。

但还不能算“写作主链路闭环成熟”：四栏方案的 `DirectoryPane`/`EntryRail`/`ManuscriptDirectory` 没有接入真实 `FourPaneShell`，二栏仍由旧 `useLeftDockCapabilities`/`ProjectTree` 渲染；正文阶段右栏 `WriteChat` 没传 `phase='final'`，后端支持的 final 阶段角色与演绎块注入没有被真实正文主编入口触发；实时护栏和章加载失败仍存在静默失败/未 catch 路径；窄宽下顶栏章阶段与图谱/时间线/仪表盘重叠，三栏最小宽度还会把右栏挤窄到不可用。

## 业务闭环

| 环节 | 当前状态 | 证据 | 缺口 |
|---|---|---|---|
| 目标 | 作者可以从手稿选章，按大纲/节拍/草稿/正文推进，并由主编、护栏、选择环、Pilot 辅助落稿。 | `ChapterStudio.jsx:20-28` 定义阶段；`WriteLayout.jsx:68-128` 处理切章/卸载保存；`studioDocks.jsx:381-389` 右栏挂主编/选择环/存档/Pilot/收件箱。 | 二栏目录的真实实现没有用计划中的 `DirectoryPane`，主链路入口仍混旧架构。 |
| 进入 | 作品 -> 手稿 -> 章可达；选章后左栏出现演绎/伏笔/母题/检索/校验，右栏出现选择环/存档/Pilot。 | 浏览器：`纸命` 未选章左栏为手稿/设定库/素材库；选第 1 章后左栏为手稿/设定库/素材库/演绎/伏笔/母题/检索/校验，右栏为主编/选择环/存档/Pilot/收件箱。 | 未选章能力隐藏已在 Wave A 报；选章后可达，但窄宽下顶栏和右栏信息过挤。 |
| 创建/读取 | 大纲/节拍读写 `chapter.synopsis/beats`；草稿读写 draft；正文读写 `saveChapter`；版本/选择环走 version/finalize。 | `ChapterStudio.jsx:58-89`、`150-186`、`294-356`；`WriteLayout.jsx:465-541`；`SelectionPanel.jsx:73-113`。 | `WriteLayout` 对 `api.chapter/api.causal/api.qc` 加载失败没有统一错误态。 |
| 使用 | 正文编辑器、护栏、全量体检、反哺设定库、主编写作槽、选中段落改写均在正文台。 | `WriteLayout.jsx:636-854` 顶部工具；`WriteLayout.jsx:897-902` 编辑器；`WriteLayout.jsx:573-591` 区分讨论/改写。 | 实时护栏 `api.checkProse` 失败被吞，可能显示旧状态或无状态。 |
| 反馈 | 保存失败有 toast；自动保存失败有本地暂存；选择环失败分 422/404/网络；收件箱 degraded 可见。 | `WriteLayout.jsx:75-84`、`114-128`、`465-483`；`SelectionPanel.jsx:79-97`；`studioDocks.jsx:183-205`。 | Pilot 状态拉取失败被吞；章主数据加载失败无用户反馈；实时护栏失败无 degraded。 |
| 沉淀 | 存稿返回 QC/泄露；反哺设定库；选择环终选理由入 lesson；主编对话本地按 work+章持久化。 | `WriteLayout.jsx:543-572`；`SelectionPanel.jsx:100-108`；`WriteChat.jsx:78-80`；`useChatPersist.js:34-57`。 | 正文主编 prompt 没带 final phase，沉淀的演绎/限知成果不一定进真实写作入口。 |
| 回收 | 版本可恢复，恢复有确认并通知中区重拉；Pilot 可退出/解卡/暂停。 | `studioDocks.jsx:411-443`、`321-348`。 | 恢复会覆盖正文，虽然有确认；未存改动与恢复动作的联动仍需专项破坏性路径测试。 |

## 架构归属

| 层 | 当前职责 | 判断 | 证据 |
|---|---|---|---|
| 顶栏 | 章阶段 + 横切视图 + 作品切换。 | 职责方向正确，但响应式不足。 | `AppRail.jsx:24-31` 把 extra 和 views 放同一 flex 行；`ChapterStudio.jsx:559-568` 阶段 tab 可横滚但窄宽仍与视图区挤压。 |
| 左栏 | 一级能力小 tab。 | 选章后能力完整；未选章仍不完整。 | `studioDocks.jsx:64-95`。 |
| 二栏 | 目录/能力列表。 | 真实实现与计划不一致：`DirectoryPane` 未接入，仍直接渲染旧能力面板。 | `FourPaneShell.jsx:32-43` 直接调用 `useLeftDockCapabilities`；`FourPaneShell.jsx:82-83` 渲染 `active.render()`；`DirectoryPane.jsx` 当前无调用方。 |
| 三栏 | 章详情/正文/横切视图。 | 写作能力集中，保存链路较完整；但 `Shell` 的硬最小宽度破坏窄宽布局。 | `shell.jsx:45-49` `main` 固定 `min-w-[480px]`；浏览器 742px 时中栏实际 480px、右栏输入仅约 65px。 |
| 右栏 | 主编、选择环、存档、Pilot、收件箱。 | 能力入口完整；Pilot/收件箱闭环比旧版强，但部分状态失败静默。 | `studioDocks.jsx:381-389`；`studioDocks.jsx:282-303`。 |
| API | save/check/chat/select/pilot/inbox。 | 测试通过，契约较完整；`chatWrite` 支持 phase，但前端正文入口没有传。 | `api.js:240-245`；`WriteChat.jsx:140-142`。 |
| 后端/LLM | prompt 单源组装，phase 控制阶段角色和演绎块。 | 后端方向正确；前端未触发 final phase 是断链。 | `app.py:2276-2336`。 |

## 八维评分

| 维度 | 分数 | 理由 |
|---|---:|---|
| 业务完善性 | 2 | 选章、写正文、保存、版本、主编、选择环、Pilot 都可达；但二栏目录架构未真实落地，正文主编 prompt 不完整。 |
| 逻辑闭环性 | 2 | 保存/终选/恢复闭环较强；实时护栏和 Pilot 状态失败时闭环断开。 |
| 架构合理性 | 1 | `DirectoryPane`/`EntryRail` 存在但未接入真实壳；`studioDocks.jsx` 继续承载左右栏大量业务；写作 shell 的 `min-w` 与四栏布局冲突。 |
| 数据可信性 | 2 | work 钉死、暂存稿恢复、409/stale 防护有明确代码；但 final prompt 未带 phase，护栏失败会静默。 |
| UI 友好性 | 1 | 窄宽下顶栏重叠、右栏输入过窄、二栏按钮溢出，影响真实使用。 |
| 创作质量 | 2 | 后端 prompt 组装包含素材、演绎、限知、craft；但真实正文主编入口没传 final phase，创作质量打折。 |
| 失败恢复 | 2 | 保存失败和选择环失败处理较好；章加载、实时护栏、Pilot 状态拉取失败不够可见。 |
| 工程可维护性 | 2 | 定点测试强；但核心 UI 仍集中在 `studioDocks.jsx`/`WriteLayout.jsx` 大文件，未接入的新组件增加误判风险。 |

总分：14/24。主写作链路比骨架成熟，但存在 P1 级“能力写了但真实入口没用上/后端支持但前端没传参”的断链。

## 用户旅程证据

**成功路径：手稿 -> 第 1 章 -> 正文。**  
浏览器在 `http://127.0.0.1:3311/`，作品 `纸命`，点击左栏手稿后二栏展示 4 章；点击 `1 第1章` 后，顶栏显示大纲/节拍/草稿/正文/简报/限知帧/北极星，左栏能力补全，三栏正文显示 6551 字且状态为已存，右栏显示主编写作槽和选择环/存档/Pilot/收件箱入口。console error/warn 为空。

**空态/未选章路径。**  
未选章时三栏显示“从左侧项目树选一个章开始写”，右栏主编显示未选中讨论态；左栏仅手稿/设定库/素材库。该点已在 Wave A 作为全书能力发现性缺口记录。

**窄宽路径。**  
当前浏览器视口约 742x784。选章后，阶段 tab 与图谱/时间线/仪表盘都在顶栏同一行：阶段组宽约 315px，北极星按钮坐标约 x=593-671，全局时间线约 x=586-665，仪表盘约 x=669-748，存在重叠/挤压风险。三栏中 `Shell` 的 `min-w-[480px]` 使中区在实际 detail panel 约 406px 时仍强撑 480px，右栏主编输入区宽度被压到约 65px。

**浏览器限制。**  
逐阶段自动循环走查在浏览器控制会话中超时重置；已完成正文态、手稿态、章态、右栏入口和 console 证据。大纲/节拍/草稿/简报/限知帧/北极星的逐阶段视觉证据需要下一轮短事务补跑。

## Findings

### [P1][R1/R2][架构合理性/业务完善性] `DirectoryPane`/`EntryRail` 已实现但未接入真实四栏壳，二栏仍走旧 `ProjectTree`/能力面板

**证据:** `EntryRail.jsx:45-70` 定义了一级入口分组；`DirectoryPane.jsx:16-43` 定义了手稿/素材/设定/能力目录分发；但 `FourPaneShell.jsx:32-43` 直接调用 `useLeftDockCapabilities`，`FourPaneShell.jsx:82-83` 直接渲染 `active.render()`，没有使用 `EntryRail` 或 `DirectoryPane`。CodeGraph 显示 `DirectoryPane.jsx` 当前无调用方。浏览器手稿二栏展示的是旧项目树行“未分卷 / 第1章...”，没有 `ManuscriptDirectory.jsx:57-102` 中定义的“书级工具/DirectoryHeader”。  
**影响:** 用户要的“左栏一级入口 -> 二栏目录薄分发 -> 三栏详情”在真实页面没有完全成立；新写的目录组件和测试可能给出假安全感，但生产 UI 仍是旧能力面板。手稿、设定、素材、演绎、伏笔、母题、检索、校验都会受此架构漂移影响。  
**建议:**  
- 最小止血：在 `FourPaneShell` 内用 `EntryRail` 管 `entry`，用 `DirectoryPane` 渲染栏2；保留 `Rail` 仅作图标样式时也要让数据流走 entry/item 两级。  
- 产品补全：`EntryRail` 入口常驻手稿/设定库/素材库/演绎/伏笔/母题/搜索/校验，未选章时章级能力显示全书态或选章引导。  
- 架构重构：删除或收敛 `useLeftDockCapabilities` 在 V2 四栏里的目录职责，让它只服务旧三栏 flag 或拆成能力数据源。  
**验收:** 浏览器手稿二栏出现 `ManuscriptDirectory` 的目录头/书级工具；素材库、设定库、演绎等都由 `DirectoryPane` 分发；CodeGraph 显示 `DirectoryPane` 有真实调用方。

### [P1][R1][创作质量/数据可信性] 正文阶段右栏 `WriteChat` 没传 `phase='final'`，后端 final prompt/演绎块真实入口未触发

**证据:** `api.js:240-245` 支持把 `phase` 放入 `/chat/write` 请求体；`app.py:2308-2316` 只有 `phase in ("draft", "final")` 才注入 `_deduction_block`；`app.py:2071-2083` 只有 `final` 才给正文期编审角色提示。可是真实正文写作槽 `WriteLayout.jsx:913-926` 创建 `<WriteChat chapter={chapter} focalizer={focalizer} ... />`，没有传 phase；`WriteChat.jsx:54` props 也没有 phase，`WriteChat.jsx:140-142` 调 `api.chatWrite` 时只传 chapter/focalizer/images。  
**影响:** 大纲/节拍/草稿等讨论态通过 `ChiefDock.jsx:214-217`、`340-343` 映射 phase；但最核心的正文主编入口没有 final phase。用户在正文里让主编续写/改写时，后端虽然具备演绎、限知、final 编审注入能力，真实请求却可能走空 phase，导致“后端完整，前端最后一公里断链”。这会直接影响创作质量和限知/演绎一致性。  
**建议:**  
- 最小止血：给 `WriteChat` 增加 `phase="final"` prop，`WriteLayout` 正文槽固定传入。  
- 产品补全：把 `phase` 展示为可追踪调试信息或测试断言，避免未来阶段新增后再次漏传。  
- 架构重构：统一 `chatWrite` 调用封装，章阶段上下文由 `ChapterStudio/ChiefSlotContext` 单源提供，禁止各组件手写 phase。  
**验收:** 前端测试断言正文 `WriteChat` 请求体包含 `phase:"final"`；后端 prompt 内容测试覆盖 `final` 来自真实前端调用路径。

### [P1][R1][失败恢复/数据可信性] 实时护栏失败被吞，用户可能把“没查成”看成“没问题”

**证据:** `WriteLayout.jsx:263-279` 在 3 秒防抖后调用 `api.checkProse(chapter, prose, focalizer)`，失败时 `.catch(() => {})`；没有 `guardError/degraded` 状态，也没有清空或标灰护栏。护栏芯片渲染依赖 `guard` 旧值：`WriteLayout.jsx:661-672`。  
**影响:** 实时护栏是正文台的高信任信号。若 `/check` 网络失败、后端错误或当前章加载过程中 stale，UI 可能继续显示上一次 guard 状态或不提示失败。对限知泄露/QC 来说，“没查成”被误读成“安全”是产品级风险。  
**建议:**  
- 最小止血：`catch` 设置 `guardStatus='degraded'`，护栏 chip 显示“护栏降级/重试”。  
- 产品补全：护栏 popover 区分 `checking / clean / issues / degraded / off` 五态。  
- 架构重构：复用 `postCheck` 的 degraded 语义，让实时检查和全量体检共享状态词典。  
**验收:** 模拟 `/check` 500，护栏显示“检测失败/没查≠没病”，不能保留假绿。

### [P2][R1][失败恢复] 正文章主数据加载失败没有用户态错误，`api.chapter/api.causal/api.qc` 缺少 catch

**证据:** `WriteLayout.jsx:283-305` 同时调用 `api.entities()`、`api.motifs()`、`api.chapter(chapter)`、`api.causal(chapter)`、`api.qc(chapter)`；除 `entities/motifs` 外也没有 catch，`api.chapter` 失败时不设置错误态，`causal/qc` 失败也可能产生未处理 rejection。  
**影响:** 章正文、因果、QC 是写作台基础数据。失败时用户不知道是“章为空”“接口失败”还是“仍在加载”，可能继续在旧正文/空正文上操作。  
**建议:**  
- 最小止血：为章加载设置 `chapterLoadState`，失败时中区显示错误态和重试。  
- 产品补全：`causal/qc/entities/motifs` 分别降级，不阻断正文但明确显示“部分数据不可用”。  
- 架构重构：建立 `useChapterWorkspaceData(work, chapter)` hook，集中处理 loading/error/degraded。  
**验收:** 模拟 `/chapter?seq=1` 失败，正文台不渲染旧稿或空白，而是显示错误和重试。

### [P2][R2/R4][UI 友好性] 顶栏章阶段和全局视图在窄宽下重叠/挤压

**证据:** `AppRail.jsx:24-31` 将章阶段 `extra` 和图谱/时间线/仪表盘放在同一 flex 行；`ChapterStudio.jsx:559-568` 阶段 tabs 自身可横滚，但没有和全局 views 做整体响应式分配。浏览器 742px 下阶段组约 x=176-491，但阶段子按钮坐标延伸到北极星 x=593-671；全局时间线约 x=586-665、仪表盘约 x=669-748。  
**影响:** 用户在窄屏/分屏下难以区分“章阶段”和“全局视图”，按钮可能互相覆盖或造成点击误判。这正是用户此前问“大纲这一行能否放到仪表盘这一行”后持续出现的顶栏密度问题。  
**建议:**  
- 最小止血：`topbar-work-tabs` 设定可滚动区域并硬性 clip，global views 在空间不足时收进菜单或只显示图标。  
- 产品补全：章阶段左对齐、分隔线后全局视图右侧固定；小宽度下全局视图改 icon-only 带 tooltip。  
- 架构重构：`AppRail` 按 slot 分区，阶段 slot 和 global slot 各自有 `min/max/flex-basis`，而不是所有按钮自由挤压。  
**验收:** 742px、1024px、1440px 三档截图中阶段与全局视图不重叠，最长文案不裁到不可识别。

### [P2][R1/R4][UI 友好性/架构合理性] `Shell` 的 `min-w-[480px]` 与四栏 resizable 布局冲突，右栏被压到不可用

**证据:** `shell.jsx:45-49` 的 `main` 固定 `min-w-[480px]`；`FourPaneShell.jsx:91-113` detail/right 都是 resizable panel 百分比。浏览器 742px 下 detail 容器约 406px，但内部 `Shell` 实际撑到 480px，右栏主编输入区 textarea 宽约 65px，建议按钮也变成长竖条。  
**影响:** 三栏详情在窄屏时强撑，右栏主编虽然“常驻”，但实际不可用；这会让用户感知为“框太窄/信息很麻烦/二栏太宽”。  
**建议:**  
- 最小止血：V2 四栏中移除 `Shell` 的 `min-w-[480px]`，改成 `min-w-0`，编辑器正文容器用 max-width 而不是 main min-width。  
- 产品补全：低于阈值时右栏自动折叠成 rail，主编输入展开为 overlay 或底部抽屉。  
- 架构重构：让 `WriteLayout` 不再套旧 `Shell`，由 `DetailPane/FourPaneShell` 负责外层尺寸。  
**验收:** 742px 下中区不越界，右栏输入至少可用；拖动分隔条不会被内部 min-width 抵消。

### [P2][R1][逻辑闭环/失败恢复] Pilot 状态拉取失败被吞，状态机入口可能显示 stale/idle

**证据:** `studioDocks.jsx:282-303` 中 `api.pilotStatus(seq)` 和 `api.pilotRunStatus()` 的 catch 都是空操作；`refresh()` 也空 catch。  
**影响:** Pilot 是高成本、长时间、状态机型能力。若状态接口失败，用户可能看到旧 `st` 或默认 `idle`，无法判断是未启动、正在运行、停靠、卡住还是接口失败。  
**建议:**  
- 最小止血：增加 `statusError`，显示“Pilot 状态拉取失败，重试”。  
- 产品补全：状态卡区分 `loading/error/stale/running/parked/stalled/finalized`，显示最近更新时间。  
- 架构重构：Pilot/Inbox 共用轮询状态 helper，所有右栏状态型面板统一错误和 stale 语义。  
**验收:** 模拟 `/pilot/status` 失败时不显示 idle，显示错误和重试。

### [P2][R2][工程可维护性] `studioDocks.jsx` 继续承载左右栏、Pilot、收件箱、伏笔、母题、QC 等多域逻辑

**证据:** `studioDocks.jsx` 当前约 707 行，包含 `useLeftDockCapabilities`、`LeftDock`、`InboxPanel`、`DeliveryCard`、`PilotDock`、`RightDock`、`RightVersionPanel`、`PromisesPanel`、`MotifsPanel`、`TensionCheck`、`QCPanel` 等多个业务域。  
**影响:** 任何左栏/右栏交互调整都容易误伤 Pilot、收件箱、伏笔/母题/QC；用户连续反馈“修了一个地方丢了另一个能力”与这种聚合结构高度相关。  
**建议:**  
- 最小止血：不继续往 `studioDocks.jsx` 增加新业务，新增只做拆分。  
- 产品补全：按域拆为 `leftDockCapabilities`、`rightDockCapabilities`、`InboxPanel`、`PilotDock`、`NarrativeLedgerPanels`、`QualityPanel`。  
- 架构重构：把“能力注册表”和“面板实现”分离，每个能力声明 scope、入口、目录、详情、右栏关系。  
**验收:** 单个功能域变更能通过 import 边界和测试边界定位，不需要读完整 `studioDocks.jsx`。

## 爆炸半径

- **入口:** 手稿、章阶段、大纲/节拍/草稿/正文/简报/限知帧/北极星、主编、选择环、存档、Pilot、收件箱、左栏演绎/伏笔/母题/检索/校验。
- **前端组件:** `FourPaneShell.jsx`、`EntryRail.jsx`、`DirectoryPane.jsx`、`ManuscriptDirectory.jsx`、`ChapterStudio.jsx`、`WriteLayout.jsx`、`WriteChat.jsx`、`ChiefDock.jsx`、`studioDocks.jsx`、`shell.jsx`、`SelectionPanel.jsx`。
- **API:** `/chapter`、`/save-chapter`、`/check`、`/post-check`、`/chat/write`、`/chapter-brief`、`/north-star/chapter`、`/select/chapter`、`/select/finalize`、`/pilot/*`、`/inbox`、`/ingest`。
- **状态:** `sel`、`leftSeq`、`curSeq`、`chapterPhase`、`dirtyRef`、`saved`、`stash`、`guard`、`proposal`、`stageProposal`、`s3.chat.*`、`s3.rightTab`、Pilot state。
- **测试:** `test_manuscript.py`、`test_timeline.py`、`test_ingest.py`、`test_ingest_idempotency.py`、`test_chat_message.py`、`test_llm_stream.py`、`test_brief.py`、`test_pilot.py`、`test_selection.py`、`test_loop_endpoint.py`、`chapterStudio-topbar.test.jsx`、`appRail-layout.test.jsx`、`deduceStage-layout.test.jsx`、`directoryPane-manuscript.test.jsx`、editor tests。

## 修复分层

**最小止血批次:**

1. `WriteLayout` -> `WriteChat` 传 `phase="final"`，补前端测试。
2. `WriteLayout` 的 `/check`、`/chapter`、`/causal`、`/qc` 加错误/降级态。
3. Pilot 状态拉取失败显示错误和重试。
4. `Shell` 在 V2 四栏中移除 `min-w-[480px]`。
5. 顶栏窄宽下 global views 改 icon-only 或 overflow menu，确保不与阶段 tabs 重叠。

**产品补全批次:**

1. 真正接入 `EntryRail` + `DirectoryPane`，恢复“一级入口 -> 二栏目录 -> 三栏详情”的业务架构。
2. 未选章时保留全书态演绎/伏笔/母题/搜索/校验入口。
3. 章工作台每个阶段加入明确的“结果沉淀到哪里/下一步是什么”微反馈，不靠说明文堆叠。
4. Pilot/收件箱增加 stale 时间、错误态、重试态。

**架构重构批次:**

1. 建立能力注册表：`capability -> scope -> directory -> detail -> rightDock -> api -> tests`。
2. 拆分 `studioDocks.jsx`，防止一个文件牵动所有能力。
3. 把章工作台数据加载封装成 hook，统一 loading/error/degraded。
4. 统一 chat phase 上下文来源，不允许每个聊天入口手写 payload。

## 验证

已运行：

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_manuscript.py scribe3/tests/test_timeline.py scribe3/tests/test_ingest.py scribe3/tests/test_ingest_idempotency.py
# 85 passed, 1 warning
```

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_chat_message.py scribe3/tests/test_llm_stream.py scribe3/tests/test_brief.py scribe3/tests/test_pilot.py scribe3/tests/test_selection.py scribe3/tests/test_loop_endpoint.py
# 119 passed, 1 warning
```

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/layout/__tests__/directoryPane-manuscript.test.jsx src/__tests__/chapterStudio-topbar.test.jsx src/__tests__/appRail-layout.test.jsx src/__tests__/deduceStage-layout.test.jsx src/editor/markdown.test.js src/editor/guardIssues.test.js src/editor/applyProposal.test.js
# 7 test files passed, 31 tests passed
```

浏览器走查：

- `http://127.0.0.1:3311/`，作品 `纸命`。
- 未选章：左栏仅手稿/设定库/素材库，三栏空态，右栏主编未选中；console error/warn 为空。
- 手稿：二栏显示未分卷 4 章；点击第 1 章可进入正文。
- 章态：顶栏阶段可见，左栏能力补全，右栏选择环/存档/Pilot/收件箱可见；console error/warn 为空。
- 窄宽：发现顶栏按钮重叠风险、`Shell` 最小宽度压缩右栏。

未运行：

- 未触发“出 3 候选”“Pilot 推进一步/连写”“保存/存为正文”“反哺设定库”等写入或高成本生成动作。
- 未完成每个阶段 tab 的完整浏览器截图矩阵，自动循环因浏览器控制会话超时中断；需要后续短事务补跑。
- 未跑全量 `npm test`、全量 `pytest -q scribe3/tests`，按计划留到 E4 总回归。

## 下一步

1. 进入 Wave C：设定库、素材库、伏笔、母题、关系、弧光、素材召回/ingest，重点查“知识是否能从输入到写作召回再回流”。
2. Wave B 修复优先级最高的是两个 P1：真实接入 `DirectoryPane`，以及正文 `WriteChat` 传 `phase="final"`。
3. E4 汇总时把 Wave A/B findings 合并排序，形成“最小止血 / 产品补全 / 架构重构”三批修复清单。
