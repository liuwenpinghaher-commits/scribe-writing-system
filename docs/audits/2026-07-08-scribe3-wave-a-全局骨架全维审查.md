# 功能域审查：Wave A 全局骨架和数据基线

**审查日期:** 2026-07-08  
**审查范围:** A1 作品库/work 切换/API base；A2 顶栏/左栏/二栏/三栏/右栏路由骨架；A3 `DetailPane` 路由表；A4 错误边界/toast/loading/empty/degraded。  
**爆炸半径:** R0/R2/R4。  
**审查性质:** 只读审查，未修产品代码，未回退工作区改动。  

## 结论

Wave A 当前属于 **可用但有产品级缺口**。

全局骨架的核心方向是成立的：`App` 持有 `sel` 单一真相源，`api.js` 默认给业务 API 加 `work`，四栏壳将“一级入口 / 二栏目录 / 三栏详情 / 右栏主编”分开，`DetailPane` 是三栏详情和横切视图的集中路由点。浏览器验证也证明图谱态可以切回素材库，作品切换会清空三栏选中和顶栏章阶段。

但 Wave A 还没有达到“全维成熟能力”：左栏能力在未选章时被隐藏，导致伏笔/母题/检索/校验等全书能力的发现性不足；左栏 active tab 使用全局偏好，跨作品保留上一个入口，切书后会落在另一本书的同名入口而不是一个中性初始态；若项目树加载失败，`reload()` 直接吞错，用户可能只看到空/旧界面而不知道数据源失败。

## 业务闭环

| 环节 | 当前状态 | 证据 | 缺口 |
|---|---|---|---|
| 目标 | 让用户从作品库进入一本书，并在顶栏、左栏、二栏、三栏、右栏间稳定完成导航。 | `App.jsx:17-18` 定义 `sel` 单一真相源；`FourPaneShell.jsx:16-24` 注释定义四栏职责。 | 业务目标成立，但左栏能力发现性受“是否已选章”影响。 |
| 进入 | 作品库可进入作品；顶栏作品按钮可回作品库。 | 浏览器：作品库显示 5 本书；进入 `铜炉试炼·三轮验证` 后顶栏显示图谱/时间线/仪表盘；点击作品按钮回作品库。 | 作品切换后左栏 active 保留上一作品入口，心智上不像“重新进入一本书”。 |
| 创建/读取 | 作品列表走 `/works`；业务 API 走 `?work=`；树通过 `api.projectTree()` 加命题分类。 | `api.js:22-34` 封装 `j/post/patch/del/put`；`api.js:47-54` 作品库端点不带 work；`BinderLayout.jsx:60-70` 拉 `projectTree` 和 `facts`。 | `BinderLayout.jsx:70` 对 `reload()` 失败 `catch(() => {})`，无 UI 降级状态。 |
| 使用 | 左栏切一级入口，二栏常驻目录，三栏详情，右栏主编。 | `FourPaneShell.jsx:65-103` 二栏与三栏拆开；`DetailPane.jsx:44-155` 集中路由详情。 | 未选章时左栏只显示内容库，工艺/检查能力隐藏。 |
| 反馈 | `ToastHost` 全局挂载，局部错误边界存在，部分 degraded 已表达。 | `App.jsx:65` 挂 `ToastHost`；`DetailPane.jsx:38-40` 包 `ErrorBoundary`；`WriteLayout.jsx:448-449` 展示检测降级。 | 项目树加载失败、卷 rename/delete/reorder 失败只 `console.error` 或吞错，用户反馈不足。 |
| 沉淀 | 布局宽度、折叠态、左栏 tab 有持久化。 | `BinderLayout.jsx:57-58` binder layout 持久化；`BinderLayout.jsx:166-172` 折叠态持久化；`studioDocks.jsx:27` 左 tab 走 `usePref('s3.leftTab')`。 | 左 tab 持久化未按 work 隔离，跨书延续入口状态。 |
| 回收 | 作品/卷删除有确认，危险动作部分走 dialog。 | `BinderLayout.jsx:197-205` 删除卷确认；`Library.jsx` 使用 `ConfirmDialog`。 | Wave A 未覆盖全部破坏性动作，留给 E2 数据生命周期继续审。 |

## 架构归属

| 层 | 当前职责 | 是否合理 | 证据 |
|---|---|---|---|
| 顶栏 | 作品切换、章阶段 slot、横切视图、主题。 | 基本合理。章阶段和横切视图分隔清楚。 | `AppRail.jsx:24-45`。浏览器：选章后顶栏为“大纲/节拍/草稿/正文/简报/限知帧/北极星 | 图谱/时间线/仪表盘”。 |
| 左栏 | 小 tab 轨，承载内容库和章级能力入口。 | 部分合理。能力入口只在有 `seq` 时出现，导致全书能力发现性不足。 | `studioDocks.jsx:64-75` 未选章直接返回 `base`；`studioDocks.jsx:83-94` 选章后才追加演绎/伏笔/母题/检索/校验。 |
| 二栏 | 目录或能力列表，视图态隐藏。 | 合理。常驻目录和三栏详情分开。 | `FourPaneShell.jsx:65-88`，`DirectoryPane.jsx:16-61`。 |
| 三栏 | 详情或横切视图。 | 基本合理。`DetailPane` 集中路由，未知类型有兜底。 | `DetailPane.jsx:44-155`。 |
| 右栏 | 主编/收件箱/存档/Pilot 等辅助上下文。 | 基本合理。章态和非章态文案区分存在。 | 浏览器：章详情时右栏显示“主编 · 写作”；素材库时右栏显示“主编 未选中...”。 |
| API | 统一 `work` 参数、错误抛出。 | 基本合理，但 `chatWrite` streaming 错误只回调字符串，和普通 `handle()` 错误结构不完全统一。 | `api.js:13-19`、`api.js:240-249`。 |
| store/backend | 作品、树、状态、degraded 来源。 | Wave A 仅确认入口，后续 E1/E2/E3 深审。 | `app.py:4686-4800` inbox degraded；`app.py:3186-3523` post-check degraded。 |
| LLM/ingest | 不属于 Wave A 主体。 | 留给 B4/C4/E1。 | 本轮未深审。 |

## 八维评分

| 维度 | 分数 | 理由 | 证据 |
|---|---:|---|---|
| 业务完善性 | 2 | 作品进入、导航、详情闭环成立；但全书能力入口未选章时隐藏，切书后保留旧左栏 active。 | 浏览器：进入作品未选章左栏只有“手稿/设定库/素材库”；选章后才有演绎/伏笔/母题/检索/校验。 |
| 逻辑闭环性 | 2 | 顶栏 view 和左栏切换可回流；但项目树加载失败无用户态反馈。 | `BinderLayout.jsx:70`、浏览器图谱 -> 素材库验证通过。 |
| 架构合理性 | 2 | 四栏职责大体成立；左栏能力是否章级/全书级未拆清，`usePref('s3.leftTab')` 跨书共享。 | `studioDocks.jsx:27`、`studioDocks.jsx:75`。 |
| 数据可信性 | 2 | 后端 work 测试通过；API 默认加 `work`；作品切换清空 `sel`。但左 tab 偏好跨 work，可能造成入口上下文误导。 | `api.js:11-34`、`App.jsx:36-37`。 |
| UI 友好性 | 2 | 顶栏分组清楚，四栏可用；但未选章时关键能力不可见，素材空态在二栏窄区信息密度偏高。 | 浏览器素材库二栏宽 113px，显示新建/导入/网络/分类等密集内容。 |
| 创作质量 | 1 | Wave A 只覆盖骨架，不能证明生成/校验质量。 | 留给 B4/C4/D1/D3/E1。 |
| 失败恢复 | 2 | Toast/Dialog/ErrorBoundary 存在，后端 degraded 定点测试通过；但 `reload()` 和部分卷操作失败只吞错或 console。 | `App.jsx:65`、`BinderLayout.jsx:70`、`BinderLayout.jsx:105-142`。 |
| 工程可维护性 | 2 | 定点测试和 build 通过；路由集中度较好。当前工作区有大量未提交改动，后续审查要继续区分前序改动与新发现。 | 测试命令见“验证”。 |

总分：15/24，判定为 **半成品到可用之间**。骨架方向成立，但发现性、失败反馈和跨作品 UI 状态需要产品级补齐。

## 用户旅程

**成功路径 1：作品库 -> 作品 -> 选章 -> 章工作台。**  
浏览器进入 `铜炉试炼·三轮验证` 后，默认显示顶栏全局视图、左栏内容库、二栏手稿目录、三栏空态、右栏主编；选第一章后，顶栏出现章阶段 tab，左栏出现演绎/伏笔/母题/检索/校验，三栏打开正文，右栏变成章写作主编。

**成功路径 2：章详情 -> 图谱 -> 素材库。**  
浏览器点击图谱后，二栏隐藏，三栏全画布显示知识图谱；再点击左栏素材库，二栏恢复素材库目录，三栏回到未选中空态，console error 为空。

**失败/空态路径：作品切换。**  
从 `铜炉试炼·三轮验证` 素材库回作品库，再进入 `纸命`：顶栏章阶段清空、三栏选中清空，说明 `sel` 清理有效；但左栏 active 仍停在素材库，二栏显示 `纸命` 的素材空态。这不是数据串书，但会让用户误以为新作品默认进入素材库。

**交互评价：**  
顶栏分组比之前清楚；四栏拆分符合钻取架构。主要问题是左栏能力“选章后才出现”的发现性，以及二栏窄宽下素材库操作和分类信息过密。

## Findings

### [P1][R2][业务完善性/架构合理性] 未选章时工艺/检查能力从左栏消失，弱化全书能力发现性

**证据:** `studioDocks.jsx:64-75` 在 `seq == null` 时直接 `return base`，只保留手稿/设定库/素材库；`studioDocks.jsx:83-94` 选章后才追加演绎、伏笔、母题、检索、校验。浏览器进入作品未选章时左栏文本为“手稿设定库素材库”；选第一章后才变成“手稿设定库素材库演绎伏笔母题检索10校验”。  
**复现:** 打开作品但不选章，查看左栏；再选第一章，对比左栏。  
**影响:** 伏笔、母题、检索、校验这类全书/跨章能力被隐式依赖“最近章”，用户会认为能力没了。它不是后端断链，而是产品闭环和信息架构断点。  
**建议:**  
- 最小止血：未选章时仍显示伏笔、母题、检索、校验入口，进入后展示全书视图或“选择章后可看章级切片”。  
- 产品补全：把能力拆成全书态和章态，左栏常驻全书态，章态使用最近章或显式章选择器。  
- 架构重构：`useLeftDockCapabilities` 不再用 `seq == null` 决定能力是否存在，而由每个 capability 声明 `scope: book|chapter|both`。  
**验收:** 浏览器进入作品未选章时，左栏仍可见伏笔/母题/检索/校验；点击后二栏有全书视图或明确章选择引导；选章后切为章级切片。

### [P2][R2][数据可信性/UI 友好性] 左栏 active tab 跨作品持久化，切书后入口上下文不重置

**证据:** `studioDocks.jsx:27` 使用 `usePref('s3.leftTab', 'tree')`，未按 work 维度隔离；`App.jsx:36-37` 只清空 `topbarExtra` 和 `sel`，没有清空左栏 tab。浏览器从 `铜炉试炼·三轮验证` 的素材库切回作品库，再进入 `纸命`，顶栏和三栏已清空，但左栏仍 active 素材库，二栏显示 `纸命` 素材库空态。  
**复现:** 在作品 A 选素材库 -> 顶栏作品按钮 -> 选作品 B。  
**影响:** 数据没有串书，但用户旅程会继承上一书的工作入口；对“打开一本书从手稿开始”的主流程不友好，容易被误解为状态污染。  
**建议:**  
- 最小止血：`open(w)` 时派发事件或 reset left tab 到手稿。  
- 产品补全：按 work 维度持久化左栏 tab，例如 `s3.leftTab.${work}`。  
- 架构重构：把 left tab 纳入 `BinderLayout` 的 work-scoped UI state，而不是全局 pref。  
**验收:** 从任一入口切书后，新作品默认进入手稿或该作品自己的上次入口；不同作品之间不会共享 active tab。

### [P2][R2][失败恢复] 项目树加载失败被吞掉，用户无法区分“空书”和“加载失败”

**证据:** `BinderLayout.jsx:60-70` 中 `reload()` 拉 `api.projectTree()` 和 `api.facts()`，最后 `.catch(() => {})`，无 toast、无 degraded、无 ErrorBoundary fallback 状态；`BinderLayout.jsx:84` 只对 live 断线有 toast。  
**复现:** 需要模拟 `/project-tree` 失败；源码路径已证明异常被吞。  
**影响:** 项目树或命题注入失败时，用户可能看到旧树、空白或不完整树，但没有“没查成/加载失败”的反馈；这和系统已有的 degraded 哲学不一致。  
**建议:**  
- 最小止血：`reload()` catch 设置 `treeLoadError` 并 toast 一次。  
- 产品补全：左栏/二栏提供“加载失败，重试”状态。  
- 架构重构：统一 API 错误状态模型，把 `degraded_sources` 思路扩展到前端基础数据源。  
**验收:** 模拟 `/project-tree` 500 时，左栏显示错误态和重试按钮，不能静默展示空态。

### [P2][R2][失败恢复/UI 友好性] 卷 rename/delete/reorder 失败只打 console，不反馈给用户

**证据:** `BinderLayout.jsx:105-142` 中 `handleVolumeRename`、`doVolumeDelete`、`handleReorder` 的 catch 都是 `console.error(e)`，没有 toast/dialog 恢复路径。  
**复现:** 模拟卷相关 API 失败。  
**影响:** 用户拖拽或删除卷失败后看不到原因，可能以为操作成功或数据丢失。虽然这不是 Wave A 主流程 P0，但会影响手稿目录闭环。  
**建议:**  
- 最小止血：catch 里 `showToast(e?.body?.detail || e?.message || '操作失败', { tone: 'danger' })`。  
- 产品补全：乐观更新失败时回滚并说明“未保存排序”。  
- 架构重构：为目录操作建立统一 mutation helper，包含 loading、success、error、reload。  
**验收:** 卷操作失败时用户看到明确错误，目录状态回到服务端真相。

## 爆炸半径

- **入口:** 顶栏作品按钮、顶栏横切视图、左栏手稿/设定库/素材库/演绎/伏笔/母题/检索/校验、右栏主编/收件箱。
- **前端组件:** `App.jsx`、`AppRail.jsx`、`BinderLayout.jsx`、`FourPaneShell.jsx`、`studioDocks.jsx`、`DetailPane.jsx`、`DirectoryPane.jsx`、`ui/Toast.jsx`、`ui/Dialog.jsx`、`ErrorBoundary.jsx`。
- **API:** `/works`、`/project-tree`、`/facts?chapter=100000`、`/live`、`/post-check`、`/inbox`。
- **状态:** `sel`、`topbarExtra`、`s3.leftTab`、`s3.leftCollapsed`、`s3.rightCollapsed`、panel layout。
- **测试:** `test_works.py`、`appRail-layout.test.jsx`、`entryRail.test.jsx`、`fourPaneShell.test.jsx`、`detailPane-capabilities.test.jsx`、`Toast.test.jsx`、`Dialog.test.jsx`、`test_pulse.py`、`test_pilot.py`、`test_app.py`。

## 验证

已运行：

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_works.py
# 5 passed in 5.06s
```

```bash
cd "/Users/miaoma/Downloads/写作 3.0/scribe3/web"
npm test -- src/__tests__/appRail-layout.test.jsx src/layout/__tests__/entryRail.test.jsx src/layout/__tests__/fourPaneShell.test.jsx src/__tests__/detailPane-capabilities.test.jsx src/ui/Toast.test.jsx src/ui/Dialog.test.jsx
# 6 test files passed, 27 tests passed
```

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_pulse.py::test_inbox_empty_book scribe3/tests/test_pilot.py::test_inbox_reports_degraded_sources scribe3/tests/test_app.py::test_post_check_degraded_when_find_leaks_raises scribe3/tests/test_app.py::test_post_check_degraded_when_validate_setting_raises
# 4 passed, 1 warning
```

```bash
cd "/Users/miaoma/Downloads/写作 3.0/scribe3/web"
npm run build
# built successfully; existing Vite large chunk warning
```

浏览器走查：

- `http://127.0.0.1:3311/` 作品库：顶栏无章阶段/全局视图，只有作品选择和主题。
- 进入 `铜炉试炼·三轮验证`：顶栏显示图谱/时间线/仪表盘；左栏未选章只显示手稿/设定库/素材库；二栏显示手稿目录；三栏为空态；右栏主编空态。
- 选第一章：顶栏显示章阶段；左栏能力补全；三栏打开正文；右栏切到章写作主编。
- 从章态点图谱：二栏隐藏，三栏全画布显示知识图谱。
- 从图谱点素材库：二栏恢复素材库目录，三栏回空态，console error 为空。
- 从作品 A 素材库切回作品库，再进入作品 B：顶栏章阶段和三栏选中清空，左栏 active 仍为素材库，console error 为空。

未运行：

- 未跑全量 `pytest -q scribe3/tests`，按计划留到 E4 最终回归矩阵。
- 未跑全量 `npm test`，本轮只跑 Wave A 定点前端测试；全量留到 E4。

## 未覆盖

- 未审查写作保存、dirty state、Pilot、素材召回、限知 prompt、图谱性能等业务深水区；这些分别属于 Wave B/C/D/E。
- 未模拟 `/project-tree` 失败的浏览器错误态，只依据源码确认 catch 吞错；后续修复前应补浏览器或测试复现。
- 未做窄屏/移动 viewport 检查；当前浏览器宽度约 742px，已经暴露二栏素材库较窄的信息密度问题，但不等价于完整响应式审查。

## 下一步

1. 进入 Wave B：手稿与章工作台主链路，重点查“切章/保存/dirty state/主编写作对话/Pilot 选择环”的业务闭环。
2. 在后续修复排期中优先处理 Wave A 的 P1：未选章时左栏工艺/检查能力隐藏。
3. 在 E4 汇总时把 Wave A 的四个 findings 纳入全局爆炸半径排序。
