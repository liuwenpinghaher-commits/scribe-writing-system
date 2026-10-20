# 功能域审查：Wave D 工艺能力与横切视图

**审查日期:** 2026-07-08  
**审查范围:** D1 演绎；D2 搜索/语义召回；D3 校验、质量、护栏、Pulse、张力检查；D4 图谱、时间线、仪表盘。  
**爆炸半径:** R1/R2/R4。  
**审查性质:** 只读审查。未修产品代码，未回退工作区改动；未触发演绎生成、张力检查、主编生成、导入提交、删除等写入或高成本动作。  

## 结论

Wave D 的底座强弱分化明显：**图谱和时间线已经接近可承诺的横切视图，演绎与校验处于可用但需要收口的状态，搜索仍是 M1 级能力，仪表盘在失败恢复上不达标。**

图谱、时间线、仪表盘从顶栏进入后，没有再锁死 view mode。真实浏览器走查证明，打开 `图谱`、`时间线`、`仪表盘` 后，点击左栏 `素材库` 都能切回二栏目录；章态下左栏 `检索` 能返回语义召回结果，`校验` 能显示 QC 计数。后端的 `/graph`、`/timeline`、`/quality`、`/progress`、`/post-check`、`/tension-check` 也有较多 pytest 覆盖。

但按全方位产品审查标准，关键问题不是“能不能点开”，而是“是否闭环、是否可信、是否不会隐式伤害数据”。演绎树当前在打开时会根据章 synopsis/beats 自动 `patchChapter` 写入 `involved_characters`，这属于查看即写数据，违反用户心智和审查只读边界。搜索入口写着语义召回，但生产实现只返回设定命题的 attribute/value 文本，失败被吞成空态，结果不能跳转对象；新 `CapabilityDirectory` 又声称全书/设定/正文/素材四类结果，和真实能力不一致。仪表盘的 `/quality` 或 `/progress` 失败会和加载态混在一起，用户无法区分慢、空、坏。

当前成熟度判定：

| 功能域 | 成熟度 | 判断 |
|---|---|---|
| 演绎 | M2 可用 | `DeduceStage` 保存/生成链路较稳，三栏宽度已改善；但 `DeduceTree` 打开即自动写章角色，且二栏目录还不是显式、可解释的演绎任务模型。 |
| 搜索/语义召回 | M1 可见 | 能输入 query 并返回命题文本；但不是全局搜索，失败无错态，结果无类型、无跳转、无三栏详情。 |
| 校验/QC/Pulse | M2 可用 | 确定性 QC、post-check、Pulse、张力检查后端较完整；左栏 QC 能显示命中，但错误态无直接重试，问题定位主要还在正文编辑器内。 |
| 图谱 | M3- 闭环接近完整 | ego 子图、节点详情、中心展开、错误重试和限知私密遮蔽都有；前端真实组件测试偏薄。 |
| 时间线 | M3- 闭环接近完整 | vis-timeline 虚拟化、泳道、双轴、详情、双击跳章成立；错误叠层缺就地重试说明。 |
| 仪表盘/进度 | M2 可用 | 质量、伏笔台账、进度图表信息丰富；但质量和进度拉取失败会伪装成长期加载。 |

## 业务闭环

| 功能域 | 当前闭环 | 缺口 |
|---|---|---|
| 演绎 | 章态左栏进入；二栏可选场景真相/角色；三栏 `DeduceStage` 编辑和生成；失焦、切换、卸载有保存兜底；生成走 `phase='deduce'`。 | 打开左栏会自动补写涉及角色；用户没有确认、预览和撤销；演绎结果未明确进入校验或正文应用链。 |
| 搜索 | 左栏检索输入 query；`/recall` 返回语义相近设定；浏览器实测 query `借命` 返回多条命题命中。 | 搜索范围实际窄于 UI 文案；失败等于空；结果不能点开对象、不能保留上下文、不能进入三栏详情。 |
| 校验/QC | 左栏校验显示确定性 QC；正文保存和 post-check 也有质量/泄露/纪律/设置/孤儿边等检查；张力检查按钮独立触发。 | QC 失败只能“切走再切回”；张力检查是按钮级结果，不进入问题台账；左栏 QC 和正文护栏的归属需要更清晰。 |
| 图谱 | 顶栏打开；默认中心角色 ego 子图；节点详情；角色可展开；私密命题遮蔽；错误态可重试；左栏可切回功能入口。 | 节点详情只能聚焦主编，不能直接跳到设定详情；前端缺真实组件回归测试。 |
| 时间线 | 顶栏打开；按事件/伏笔/弧光/关系泳道展示；详情面板；双击/按钮跳章；左栏可切回功能入口。 | 错误叠层只有错误文本，虽顶栏有刷新但错误态没有就地行动提示；仪表盘弱章列表不能点击跳章。 |
| 仪表盘/进度 | 顶栏打开；质量、伏笔、QC、进度、热力图、弱章诊断可见；`progress` 入口可聚焦码字进度。 | `/quality` 失败一直显示“加载中”；`/progress` 失败也显示“进度数据加载中”；用户不知道是空书、慢请求还是接口坏。 |

## 架构归属

| 层 | 当前职责 | 判断 |
|---|---|---|
| 顶栏 | 横切视图入口：图谱、时间线、仪表盘。 | 方向正确；浏览器实测不会吞掉左栏入口。 |
| 左栏 | 作品/章入口和章级能力：手稿、设定库、素材库、演绎、伏笔、母题、检索、校验。 | 真实能力仍主要在 `useLeftDockCapabilities`，不是新 `EntryRail + DirectoryPane` 的完整生产链。 |
| 二栏 | 当前在旧壳中承载能力面板；新 `CapabilityDirectory` 提供静态目录雏形。 | 静态目录不能替代真实能力，否则搜索/校验/伏笔/母题会变成假计数和占位详情。 |
| 三栏 | `DetailPane` 承载横切全画布、章工作台、条目详情、演绎详情。 | 横切视图路由清楚；搜索/QC 的三栏详情还停留在占位层。 |
| 右栏 | 主编对当前视图或对象聚焦；横切视图会给视图级话术。 | 图谱/时间线选中会更新主编 focus；检索结果和 QC 问题未形成对象级主编上下文。 |
| 后端/store | `/graph`、`/timeline`、`/quality`、`/progress`、`/post-check`、`/tension-check`。 | 横切视图端点较成熟；搜索端点实际是 facts semantic recall，不是全局 search contract。 |

## 八维评分

| 维度 | 分数 | 理由 |
|---|---:|---|
| 业务完善性 | 2 | 图谱/时间线/校验能服务写作复盘；搜索不是全局闭环，演绎结果未形成应用/复盘台账。 |
| 逻辑闭环性 | 2 | 多数成功路径成立；搜索、仪表盘失败态和演绎隐式写入破坏闭环可信性。 |
| 架构合理性 | 2 | 顶栏横切、三栏详情方向正确；但旧 `studioDocks.jsx` 和静态 `CapabilityDirectory` 仍在并存。 |
| 数据可信性 | 1 | 演绎打开即写 `involved_characters` 是本波最大可信性问题；检索失败吞空也会误导用户。 |
| UI 友好性 | 2 | 图谱/时间线体验较完整；搜索结果和 QC 错误恢复仍不够可操作。 |
| 创作质量 | 2 | `phase='deduce'`、post-check、Pulse、张力检查进入创作质量链；搜索和仪表盘偏展示，未形成可修复闭环。 |
| 失败恢复 | 1 | 仪表盘、搜索、QC 多处缺直接 retry 或错误解释。 |
| 工程可维护性 | 2 | 后端测试覆盖较强；前端横切视图真实组件测试少，能力面板仍集中在大文件。 |

总分：14/24。当前不是“功能不存在”，而是“部分能力已强，产品闭环和失败恢复没有统一到同一套钻取架构里”。

## 用户旅程证据

**横切视图切回左栏。**  
浏览器打开 `http://127.0.0.1:3311/`，进入作品 `纸命`。依次点击顶栏 `图谱`、`时间线`、`仪表盘`，三栏分别显示 `知识图谱`、`时间线`、`质量仪表盘`。每次再点击左栏 `素材库`，二栏都切回素材库目录，三栏回到未选中空态；console 没有应用 error，只有 WebGL `ReadPixels` 性能 warning。

**章态检索。**  
进入 `纸命` 第 1 章后，左栏显示 `演绎 / 伏笔 / 母题 / 检索 / 校验`。点击 `检索`，输入 `借命` 并搜索，二栏返回多条语义命中，例如“获知:借命契背面写着他的名字”“行动:收下借命契称要想想”等。结果是文本列表，没有对象类型、得分、来源章、跳转按钮或三栏详情。

**章态校验。**  
进入 `纸命` 第 1 章后点击 `校验`，二栏显示 `确定性 QC · 本章正文`，计数为复读 10、跨章复读 0、整句重复 1、排比句式 4、情感直说 0、辞藻升华 1、AI 腔 1、过饱和 0，并显示 `叙事张力检查` 按钮。未点击张力检查。

**演绎走查限制。**  
本轮没有在浏览器里点击演绎树，因为源码证明 `DeduceTree` 打开后可能自动 `patchChapter` 写 `involved_characters`。为保持只读审查边界，这个行为直接列为 P1 finding。

## Findings

### [P1][R1/R2][数据可信性/逻辑闭环] 演绎树打开即自动写 `involved_characters`

**证据:** `DeduceTree` 挂载后会拉 `api.chapter(seq)` 和 `api.entities()`，随后如果 `ch.involved_characters` 为空，就把 synopsis/beats 中命中的角色 id 自动 `api.patchChapter(seq, { involved_characters: hit })`，见 `scribe3/web/src/DeduceTree.jsx:20-28`。这不是用户点击“同步”或“确认”，而是查看面板的副作用。  
**影响:** 用户只是打开演绎能力，章数据就可能被修改；自动匹配基于文本包含，误判角色后会污染演绎目录、主编上下文、图谱/时间线相关推导和后续写作 prompt。审查、演示、只读浏览也会意外产生写入。  
**建议:**  
- 最小止血：移除自动 patch，改为显示“检测到可能涉及角色”预览和手动 `同步涉及角色` 按钮。  
- 产品补全：同步前展示候选来源片段，支持勾选、撤销、忽略本章。  
- 架构重构：把“角色发现”作为只读 derived suggestion，不写入章正典；只有用户确认后才落库，并记录来源。  
**验收:** 打开演绎面板不会发 PATCH；点击同步才写入；误匹配候选可取消；测试断言 DeduceTree 初次挂载只 GET 不 PATCH。

### [P1][R2][业务完善性/架构合理性] 搜索被包装成全局能力，但真实实现只是设定语义召回文本列表

**证据:** 生产左栏 `RecallPanel` 只调用 `api.recall(q.trim(), 8)`，失败时 `catch(() => setHits([]))`，结果只渲染 `attribute:value`，见 `scribe3/web/src/studioDocks.jsx:143-163`。后端 `/recall` 直接返回 `_store_for(work).semantic_recall(q, k)` 的 facts，见 `scribe3/app.py:350-352`。新 `CapabilityDirectory` 的搜索目录却写了 `全书 / 设定 / 正文 / 素材` chips 和 `设定命中 / 正文命中 / 素材命中` rows，见 `scribe3/web/src/layout/CapabilityDirectories.jsx:51-64`。  
**影响:** 用户以为这是全局搜索，实际只搜设定语义命中；正文、素材、伏笔、母题没有同一结果契约。网络或后端失败时显示为空，用户会误以为没有命中。结果无法跳到三栏对象，也不能保持当前章上下文。  
**建议:**  
- 最小止血：把文案改为“设定语义召回”，失败显示错误和重试，不再用空态掩盖失败。  
- 产品补全：定义统一 `SearchResult {type,id,label,excerpt,source,score,targetNode}`，按设定/正文/素材/伏笔/母题分组，点击结果进入三栏详情或对应章。  
- 架构重构：建立 `/search` 聚合端点或前端 search service，统一 facts、chapters、materials、promises、motifs 的查询、权限、排序、跳转。  
**验收:** 搜索 `借命` 时每条结果显示来源类型和跳转目标；模拟 `/recall` 500 时显示错误态；正文/素材结果不会在 UI 中伪装已支持。

### [P1][R2][架构合理性/UI 友好性] 新能力详情仍是占位文案，不能作为搜索/校验/伏笔/母题的真实三栏详情

**证据:** `CapabilityDetailPanes.jsx` 对 `promise_view`、`motif_view`、`recall_result`、`review_issue` 只渲染“这里承载...”的说明文案，见 `scribe3/web/src/layout/CapabilityDetailPanes.jsx:1-18`、`20-40`、`82-87`。`CapabilityDirectory` 的搜索/校验目录使用硬编码计数和静态 rows，见 `scribe3/web/src/layout/CapabilityDirectories.jsx:51-84`。  
**影响:** 现在线上真实能力还在旧二栏面板，所以用户能看到真实检索和 QC。一旦为了“二栏目录 + 三栏详情”把静态目录接成生产路径，用户会从真实功能退化到占位说明，复现此前“能力被修没了”的问题。  
**建议:**  
- 最小止血：在代码/测试层明确这些 detail panes 是 mock/spec demo，不作为业务通过依据。  
- 产品补全：把 `RecallPanel`、`QCPanel` 的真实数据拆成目录数据源，三栏详情展示命中上下文、定位、修复建议和跳转。  
- 架构重构：每个 capability 注册 `directoryQuery`、`detailQuery`、`selectToNode`、`rightContext` 和测试清单，禁止硬编码业务计数。  
**验收:** 搜索结果、QC issue、伏笔、母题在三栏显示真实对象详情；无任何“这里承载...”类占位文案出现在生产壳。

### [P2][R2][失败恢复/数据可信性] 仪表盘和进度接口失败会伪装成长期加载

**证据:** `InsightView` 调用 `api.quality().then(setQ)` 没有 `catch`，`q` 为 null 时只显示“加载中…”，见 `scribe3/web/src/views/InsightView.jsx:747-758`。`ProgressPanel` 拉 `api.progress(win).then(setProg).catch(() => setProg(null))`，`prog` 为 null 时也只显示“进度数据加载中…”，见 `scribe3/web/src/views/InsightView.jsx:429-443`。  
**影响:** `/quality` 或 `/progress` 失败时，用户无法判断是空书、慢请求、网络断开还是后端错误；仪表盘作为全局判断入口，会把系统不可用伪装成“还在加载”。  
**建议:**  
- 最小止血：给 quality/progress 分别维护 `loading/error/data`，错误态显示重试按钮和错误摘要。  
- 产品补全：质量失败时仍显示可用的进度或反之，分区降级，不让整个仪表盘卡死。  
- 架构重构：统一横切视图的数据加载 hook，输出 `loading/error/empty/degraded/stale`，保留上次成功数据。  
**验收:** mock `/quality` 500 时仪表盘显示“质量加载失败，重试”；mock `/progress` 500 时仅进度区错误，不影响伏笔/QC图表。

### [P2][R2/R4][失败恢复/UI 友好性] QC 失败和张力检查结果没有进入统一问题台账

**证据:** `QCPanel` 失败时显示“QC 加载失败,切走再切回可重试”，没有就地重试按钮，见 `scribe3/web/src/studioDocks.jsx:682-703`。`TensionCheck` 有 loading、error、rubric_failed 和 no_prose 状态，见 `scribe3/web/src/studioDocks.jsx:641-680`，但结果只在按钮下方临时展示，没有进入 `review_issue` 详情或正文定位。  
**影响:** 用户可以看到 QC 数量，但失败恢复不顺手；张力检查即使给出 8 项结果，也不能沉淀为可筛选、可定位、可交给主编修复的问题清单。  
**建议:**  
- 最小止血：QC 失败态加“重试”按钮；张力检查失败保留上一次结果并标记 stale。  
- 产品补全：张力检查结果进入校验目录，按 `pass=false` 自动生成 issue，可点进三栏看解释和修复建议。  
- 架构重构：统一 `post-check`、`qc`、`tension-check` 的 issue contract，把确定性和 LLM rubric 都转成同一类可定位问题。  
**验收:** 断网后 QC 可一键重试；张力检查不通过项出现在校验目录，可点开三栏详情并发送主编。

### [P2][R2/R4][UI 友好性] 时间线错误态有刷新能力但错误叠层没有就地重试提示

**证据:** `TimelineView` 顶栏有刷新按钮，见 `scribe3/web/src/views/TimelineView.jsx:550-554`；但主体错误态只显示错误文本，没有“重试”按钮或提示刷新位置，见 `scribe3/web/src/views/TimelineView.jsx:561-564`。图谱错误态则有明确 `重试` 按钮，见 `scribe3/web/src/views/AtlasView.jsx:333-340`。  
**影响:** 时间线本身能力强，但失败时用户会看到孤立红框，不知道顶栏小图标可以恢复；和图谱的失败恢复体验不一致。  
**建议:** 复用图谱错误态模式，在错误叠层里加重试按钮，并保留当前 lane/axis 状态。  
**验收:** mock `/timeline` 500 时主体显示错误、原因和重试；点击重试再次调用 `/timeline`。

### [P3][R2][工程可维护性] 横切视图缺少真实前端组件回归测试

**证据:** `AppRail`、`DetailPane`、`DirectoryPane` 有路由和布局测试；`AtlasView`、`TimelineView`、`InsightView` 在这些测试里被 mock 掉，见 `scribe3/web/src/__tests__/detailPane-routing.test.jsx` 和 `scribe3/web/src/layout/__tests__/directoryPane-tools.test.jsx`。CodeGraph 对 `AtlasView`、`InsightView` 也提示未找到覆盖测试。  
**影响:** 图谱和时间线大量依赖 canvas/WebGL/vis-timeline，容易被样式、容器高度、路由 key、数据 shape 变更影响。现在主要靠浏览器手测和后端 pytest，前端回归网不够。  
**建议:**  
- 增加轻量组件测试：错误态、空态、loading、refresh、DetailPanel 跳章。  
- 增加 Playwright 冒烟：打开图谱非空、时间线非空、仪表盘非加载，左栏可切回。  
**验收:** 修改横切视图路由或容器后，至少有一组前端测试能捕获空白画布、无限加载和 view mode 锁死。

## 爆炸半径

- **入口:** 顶栏图谱/时间线/仪表盘；左栏演绎、检索、校验；章内正文护栏；右栏主编上下文。
- **前端组件:** `AppRail.jsx`、`DetailPane.jsx`、`DeduceTree.jsx`、`DeduceStage.jsx`、`studioDocks.jsx`、`CapabilityDirectories.jsx`、`CapabilityDetailPanes.jsx`、`AtlasView.jsx`、`TimelineView.jsx`、`InsightView.jsx`、`WriteLayout.jsx`、`PulseBar.jsx`。
- **API:** `/recall`、`/graph`、`/timeline`、`/quality`、`/progress`、`/qc`、`/check`、`/post-check`、`/chapter-pulse`、`/tension-check`、`/chat/write`。
- **后端/store:** `semantic_recall`、`graph`、`timeline`、`progress`、`quality_flags`、`quality_issues`、`find_leaks`、`chapter_pulse`、`tension_deterministic`、`parse_tension_report`。
- **状态:** `sel.mode/viewKey`、`s3.leftTab`、`DeduceProvider selected`、`workRef.dirty`、`selectionContext focus`、QC loading/error、timeline lane/axis、atlas focus/hop。
- **测试:** `test_qd.py`、`test_causal_directives.py`、`test_hybrid_recall.py`、`test_semantic.py`、`test_indexes.py`、`test_verify.py`、`test_critique.py`、`test_qc_fix.py`、`test_event_graph.py`、`test_timeline.py`、`test_pulse.py`、`test_app.py` quality/progress/post-check/tension-check 节点、`deduceStage-layout.test.jsx`、`appRail-layout.test.jsx`、`detailPane-routing.test.jsx`、`directoryPane-tools.test.jsx`、`guardIssues.test.js`、`GuardDecoration.test.js`。

## 修复分层

**最小止血批次:**

1. 移除 `DeduceTree` 打开即自动 patch，改成手动同步候选。
2. 搜索失败态从空结果改成错误 + 重试；文案改成“设定语义召回”直到全局搜索真正完成。
3. 仪表盘 quality/progress 分离 loading/error/empty，避免无限“加载中”。
4. QC 失败态加重试按钮；时间线错误态加就地重试。
5. 给 `CapabilityDirectory` 和占位详情加生产禁用边界，避免静态目录替换真实面板。

**产品补全批次:**

1. 统一搜索结果模型，覆盖设定、正文、素材、伏笔、母题，结果可进入三栏详情或跳章。
2. 校验目录真实化：QC、post-check、张力检查统一进入 issue 列表，三栏显示上下文和修复建议。
3. 演绎目录任务化：场景真相、角色限知、冲突误判、公开信息都来自真实章数据和用户确认。
4. 仪表盘弱章列表可点击跳章，伏笔/质量项可跳到对应台账或校验详情。

**架构重构批次:**

1. 建立 capability 注册表：`entry -> directoryData -> detailNode -> detailRenderer -> rightContext -> tests`。
2. 把 `RecallPanel`、`QCPanel`、`TensionCheck` 从 `studioDocks.jsx` 拆出，和三栏详情共享同一数据契约。
3. 横切视图统一加载状态和降级语义，支持保留上次成功数据。
4. 搜索聚合端点统一全文、向量、BM25、素材召回和对象跳转，不让 UI 拼接多个不一致结果源。

## 验证

已运行：

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_qd.py scribe3/tests/test_causal_directives.py
# 18 passed, 1 warning
```

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_hybrid_recall.py scribe3/tests/test_semantic.py scribe3/tests/test_indexes.py
# 11 passed
```

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_verify.py scribe3/tests/test_critique.py scribe3/tests/test_qc_fix.py
# 200 passed
```

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_timeline.py scribe3/tests/test_pulse.py \
  scribe3/tests/test_app.py::test_quality_endpoint \
  scribe3/tests/test_app.py::test_progress_endpoint_basic \
  scribe3/tests/test_app.py::test_post_check_degraded_when_find_leaks_raises \
  scribe3/tests/test_app.py::test_post_check_degraded_when_validate_setting_raises
# 30 passed, 1 warning
```

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q \
  scribe3/tests/test_app.py::test_tension_deterministic_items \
  scribe3/tests/test_app.py::test_tension_check_no_prose \
  scribe3/tests/test_app.py::test_tension_check_full_items_with_mocked_rubric \
  scribe3/tests/test_app.py::test_tension_check_rubric_failed_when_llm_junk \
  scribe3/tests/test_app.py::test_tension_check_survives_llm_exception \
  scribe3/tests/test_app.py::test_tension_check_rubric_type_error_degrades \
  scribe3/tests/test_app.py::test_tension_check_micro_tension_empty_deserts_shows_none \
  scribe3/tests/test_app.py::test_tension_check_micro_tension_with_deserts
# 8 passed, 1 warning
```

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_event_graph.py
# 4 passed
```

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/deduceStage-layout.test.jsx src/__tests__/appRail-layout.test.jsx src/__tests__/detailPane-routing.test.jsx src/layout/__tests__/directoryPane-tools.test.jsx
# 4 test files passed, 6 tests passed
```

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/editor/guardIssues.test.js src/editor/GuardDecoration.test.js
# 2 test files passed, 15 tests passed
```

浏览器走查：

- `图谱`：能打开，显示 `知识图谱`、默认中心角色、跳数选择、角色/命题/私密图例；点击左栏 `素材库` 可切回二栏素材目录。
- `时间线`：能打开，显示事件/伏笔/弧光/关系计数、泳道、故事/叙事轴、全览和刷新；点击左栏 `素材库` 可切回。
- `仪表盘`：能打开，显示质量仪表盘、码字进度、热力图、伏笔台账、弱章诊断；点击左栏 `素材库` 可切回。
- `检索`：第 1 章章态下输入 `借命` 返回语义命中；console error/warn 为空。
- `校验`：第 1 章章态下显示 QC 分类计数和张力检查按钮；console error/warn 为空。

未运行：

- 未点击演绎左栏树，因源码证明存在打开即 patch 的写入副作用。
- 未点击张力检查按钮，避免真实 LLM rubric 调用。
- 未触发演绎生成、主编生成、保存、删除、导入提交等写入或高成本动作。
- 未跑全量 `npm test`、全量 `pytest -q scribe3/tests`，按计划留到最终总回归。

## 下一步

1. 进入 Wave E：限知/secret、数据生命周期、失败恢复统一、性能、测试体系、文档一致性。
2. 最终总报告要把 Wave A-D 的 P1 聚合成“最小止血批次”，其中演绎隐式写入、素材删除生命周期、正文 phase 缺口、真实 `DirectoryPane` 未接入应排在前列。
