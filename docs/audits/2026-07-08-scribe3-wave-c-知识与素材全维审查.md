# 功能域审查：Wave C 知识与素材

**审查日期:** 2026-07-08  
**审查范围:** C1 设定库；C2 伏笔、母题、关系、弧光、声音演变；C3 素材库；C4 ingest、material recall、embedding、BM25、relates 图。  
**爆炸半径:** R1/R2/R3。  
**审查性质:** 只读审查，未修产品代码，未回退工作区改动。  

## 结论

Wave C 不是“能力丢失”，而是 **后端和旧面板能力较完整，新四栏钻取架构仍未把这些能力产品化收束**。

设定库、素材库、伏笔、母题、弧光、声音演变的业务底座是有的：后端 CRUD、命题时态、伏笔生命周期、母题实例、角色弧光、声音 flags、素材导入、素材召回、素材网络、写作注入和溯源都有实现，并且定点测试通过。真实浏览器也证明素材库的搜索/新建/导入/网络入口可达，章态下演绎/伏笔/母题/检索/校验左栏入口可达，点击伏笔或母题条目可以打开三栏详情。

但按“业务完善性、逻辑闭环性、架构合理性、UI 交互友好性”审，Wave C 仍有明显断点：素材写作召回和引用溯源在后端闭环，但用户在章工作台看不到“本章参考了哪些素材”；素材删除文案说“只影响素材库”，但后端已有 `material_reference` 和 `relates`，删除没有清理这些关系，存在孤儿引用风险；导入 commit 对单条失败静默 `pass`，用户只能看到 created 数量，不能知道哪条失败；新 `CapabilityDirectory` 是静态计数和占位详情，不能作为真实伏笔/母题/搜索/校验目录接入，否则会把现在旧面板里的真实能力换成假目录。

当前成熟度判定：

| 功能域 | 成熟度 | 判断 |
|---|---|---|
| 设定库 | M2 可用 | 正典对象和特化详情较完整，但加载失败和“未找到”混淆，目录仍走旧树。 |
| 伏笔 | M3- 闭环接近完整 | 旧面板有章级台账，详情有埋/收/线索；但全书态发现性依赖选章，静态新目录不能接。 |
| 母题 | M2 可用 | 章级证据和设定详情可达；但目录/详情闭环仍依赖旧面板，加载失败只弱提示。 |
| 角色弧光/声音 | M2 可用 | 有独立锚、里程碑、声音折叠；但声音 profile 无 GET，失败时容易显示为空。 |
| 素材库 | M2 可用 | 新建/导入/搜索/网络/写作注入存在；但用户可见溯源、删除一致性、导入失败反馈不足。 |
| 素材召回/ingest | M3- 闭环接近完整 | 后端三通道召回、注入、引用记录测试通过；前端章工作台没有显性引用账本。 |

## 业务闭环

| 功能域 | 当前闭环 | 缺口 |
|---|---|---|
| 设定库 | 目录列角色/势力/物件/术语/规则/伏笔/母题/命题；点叶子进 `CodexDetail`；详情可保存、删除；命题支持超越/遗忘。 | 分类加载失败常退化为空或“未找到”，用户不知道是接口失败还是数据不存在。 |
| 伏笔 | 左栏章态显示埋/收台账；点击条目进入详情；详情支持标记回收、增删线索、编辑删除。 | 未选章不可见；如果新 `CapabilityDirectory` 接入，会被静态目录和占位详情替换。 |
| 母题 | 左栏章态显示本章触及证据和全书母题；点击母题进入详情；右栏主编上下文随母题更新。 | 章态证据强，但未选章没有全书入口；失败态仅“切走再切回”。 |
| 素材库 | 二栏有搜索、新建、导入、网络、智能视图、分类；三栏有新建/导入/网络/详情；后端写作时召回素材并记录引用。 | “本章引用了哪些素材”没有在章工作台可见；素材删除没有清理引用/关系；导入部分失败不可见。 |

## 架构归属

| 层 | 当前职责 | 判断 |
|---|---|---|
| 左栏 | 入口轨：手稿/设定库/素材库；选章后追加演绎/伏笔/母题/检索/校验。 | 真实能力仍在旧 `useLeftDockCapabilities`，不是新 `EntryRail + DirectoryPane`。未选章隐藏全书能力的问题沿用 Wave A。 |
| 二栏 | 旧能力面板：项目树、素材工作台、伏笔台账、母题证据、语义召回、QC。 | 生产数据真实，但职责过重；新 `CapabilityDirectory` 还不能替代它。 |
| 三栏 | `DetailPane` 分发 `CodexDetail`、`MaterialDetail`、`MaterialImport`、`MaterialNetwork`、章工作台等。 | 详情复用方向正确；但左栏能力点击后，三栏不一定进入能力详情，多数保留正文，只有点具体条目才钻取。 |
| 右栏 | 主编上下文随 `sel` 变化；素材/伏笔/母题条目会给讨论建议。 | 条目级上下文有效；目录级和网络/导入上下文仍偏泛化。 |
| 后端/store | 设定、伏笔、母题、素材、导入、召回、引用记录、图边。 | 能力底座强；删除/导入失败/前端可见性需要补产品契约。 |

## 八维评分

| 维度 | 分数 | 理由 |
|---|---:|---|
| 业务完善性 | 2 | 多数能力有 CRUD 和真实入口；素材召回、引用溯源、全书态能力仍缺用户可见闭环。 |
| 逻辑闭环性 | 2 | 伏笔和母题条目能进详情；素材导入到召回后端闭环强，但失败/删除/引用账本断点明显。 |
| 架构合理性 | 1 | 生产壳仍走旧 `active.render()`；新能力目录是静态占位，存在“接入即降级”风险。 |
| 数据可信性 | 2 | work 流和测试较强；但素材删除不清理引用、导入单条失败静默，影响数据真实性。 |
| UI 友好性 | 2 | 素材库入口比之前完整；二栏 196px 内信息密度仍高，错误态/重试态不足。 |
| 创作质量 | 2 | 素材召回进入写作总闸，伏笔/母题/弧光进入主编上下文；但用户看不到召回依据和使用记录。 |
| 失败恢复 | 1 | 多处 catch 退为空或“未找到”，素材列表无重试，导入 commit 单条失败不可追。 |
| 工程可维护性 | 2 | 测试覆盖较好；但 `studioDocks.jsx` 聚合多域逻辑，新旧目录并存增加误判风险。 |

总分：14/24。底座比 UI 成熟；最大风险不是“没有功能”，而是“真实功能散在旧面板和后端，新架构一接就可能把真能力替换成假壳”。

## 用户旅程证据

**素材库未选章路径。**  
浏览器进入 `纸命` 后，未选章左栏只有手稿/设定库/素材库。点击素材库后，二栏显示 `素材库 0/0`、搜索框、`新建/导入/网络`、智能视图、分类和空态；三栏仍是未选中空态；console error/warn 为空。二栏宽约 196px。

**素材库三栏路径。**  
点击 `新建` 后三栏显示新建素材表单；点击 `导入` 后三栏显示文件/粘贴文本/网址导入；点击 `网络` 后三栏显示记忆网络空态。二栏目录保持素材库，没有被三栏详情替换。

**章态能力路径。**  
选 `纸命` 第 1 章后，左栏出现 `手稿 / 设定库 / 素材库 / 演绎 / 伏笔 / 母题 / 检索 / 校验`，校验 badge 为 17。点击演绎后，二栏显示场景真相和涉及角色，三栏显示演绎编辑面。点击伏笔后二栏显示本章埋下的 8 条伏笔，点第一条后，三栏进入伏笔详情并显示生命周期和 5 条线索。点击母题后二栏显示本章触及的 7 个母题，点第一条后，三栏进入母题详情。点击检索后，二栏显示语义召回表单；点击校验后，二栏显示 QC 计数和张力检查按钮。

## Findings

### [P1][R1/R2][数据可信性/逻辑闭环] 素材删除不清理引用和联想关系，且确认文案误导为“只影响素材库”

**证据:** `MaterialDetail` 删除确认文案写的是“素材不参与正文/图谱,删除只影响素材库”，见 `scribe3/web/src/Materials.jsx:200-204`。但后端已有素材引用和联想图：`store.add_material_reference()` 会写 `material_reference` 并增加 `recall_count`，见 `scribe3/store.py:1284-1293`；`material_refs_by_chapter` 和 `material_refs_by_material` 提供双向溯源，见 `scribe3/app.py:1209-1218`；`material_graph()` 会读 `relates`，见 `scribe3/store.py:1402-1416`。删除实现只 `_delete_by("material", material_id)`，见 `scribe3/store.py:1262-1267`，没有清理 `material_reference` 或 `relates`。  
**影响:** 用户删除素材时会被告知“只影响素材库”，但实际上会影响召回、网络和引用账本；反向溯源可能留下指向已删除素材的孤儿记录。  
**建议:**  
- 最小止血：改确认文案，明确会影响召回、网络和历史引用显示；删除后重拉引用/网络。  
- 产品补全：删除前展示该素材被哪些章参考过，要求二次确认；提供“归档/停用召回”优先于硬删除。  
- 架构重构：后端删除事务同时清理 `material_reference`、`relates`，或改成 `archived=true` 的软删除。  
**验收:** 新测试覆盖“有引用素材删除后 refs-by-chapter 不返回孤儿 id”；浏览器删除确认能显示引用影响。

### [P1][R1/R2][业务完善性/UI 友好性] 素材写作召回和引用溯源后端闭环，但章工作台没有用户可见账本

**证据:** 写作总闸 `_material_recall_block()` 会从草稿提取 query、召回素材、LLM 重排、渲染参考块并写 `material_reference`，见 `scribe3/app.py:2233-2270`；`_assemble_write_instructions()` 每次写作指令都拼接素材召回块，见 `scribe3/app.py:2276-2305`。前端 API 暴露 `materialRefsByChapter`，见 `scribe3/web/src/api.js:161-164`，但 CodeGraph 显示 `materialRefsByChapter` 无调用方。当前前端只在选中单条素材时展示正向引用，见 `scribe3/web/src/Materials.jsx:105-112`、`187-198`。  
**影响:** 作者不知道本章主编写作时参考了哪些素材，也不知道某个建议为什么出现；素材作为“参考记忆”的价值只在后端 prompt 中发生，产品上不可解释。  
**建议:**  
- 最小止血：在章工作台或右栏加“本章参考素材”只读区，调用 `/materials/refs-by-chapter`。  
- 产品补全：主编输出后显示“本次参考了哪些素材/为什么参考”，可一键打开素材详情。  
- 架构重构：把素材引用账本纳入 `ChapterWorkspaceData`，和伏笔/母题/QC 一样成为章级辅助上下文。  
**验收:** 触发一次带素材召回的写作后，章工作台可看到本章素材引用；点击引用可进入素材详情。

### [P1][R2][架构合理性] 新 `CapabilityDirectory` 是静态计数和占位详情，不能替代真实伏笔/母题/搜索/校验面板

**证据:** `CapabilityDirectories.jsx` 的伏笔、母题、搜索、校验目录均为静态 `rows` 和硬编码 `meta` 计数，见 `scribe3/web/src/layout/CapabilityDirectories.jsx:3-86`；`CapabilityDetailPanes.jsx` 对 `promise_view`、`motif_view`、`recall_result`、`review_issue` 只渲染说明性占位文案，见 `scribe3/web/src/layout/CapabilityDetailPanes.jsx:1-18`、`20-40`。生产 `FourPaneShell` 没有使用 `DirectoryPane`，而是继续调用 `useLeftDockCapabilities` 并渲染 `active.render()`，见 `scribe3/web/src/layout/FourPaneShell.jsx:32-43`、`82-83`。  
**影响:** 现在真实能力还在旧二栏，所以用户能看到真实伏笔台账、母题证据、语义召回、QC。如果后续为了“二栏目录”直接接入 `CapabilityDirectory`，会把真实数据换成假计数和占位详情。  
**建议:**  
- 最小止血：给 `CapabilityDirectory` 标注未接入/禁止生产替换，测试不要把静态目录视为业务通过。  
- 产品补全：用现有 `PromisesPanel`、`MotifsPanel`、`RecallPanel`、`QCPanel` 的真实数据源改造成目录数据源。  
- 架构重构：建立能力注册表，每个 capability 声明 `scope`、`directoryData`、`detailRenderer`、`rightContext`、`tests`，禁止静态 meta。  
**验收:** 真实 `FourPaneShell` 接入二栏目录后，伏笔/母题/检索/校验计数来自 API，点击项进入真实详情，不出现占位说明。

### [P1][R2][失败恢复/数据可信性] 素材导入提交逐条失败被静默吞掉，用户不知道哪些素材没落库

**证据:** 后端 commit 循环中单条失败直接 `except Exception: pass`，见 `scribe3/app.py:1183-1192`；前端只读 `created` 并 toast “已导入 N 条素材”，见 `scribe3/web/src/MaterialImport.jsx:174-180`。  
**影响:** 用户在预览阶段编辑了多条素材，提交后如果某些条目因非法分类、embedding、数据库错误失败，只会看到较小的导入数量，无法知道哪条失败、为什么失败，也无法重试失败条。  
**建议:**  
- 最小止血：后端返回 `{created, ids, failed:[{index,title,error}]}`，前端 toast 改成“成功 N 条，失败 M 条”并保留失败项。  
- 产品补全：提交后显示导入报告，失败项可回到预览继续编辑重试。  
- 架构重构：导入 job 保留状态，commit 变成幂等任务，支持断点重试。  
**验收:** 构造一条失败 item，前端能显示失败条目并允许修改重提；测试断言不会静默丢失。

### [P2][R2][失败恢复/UI 友好性] 素材列表和设定详情多处把加载失败退化成空态或“未找到”

**证据:** 素材列表失败只显示“素材加载失败。”且无重试，见 `scribe3/web/src/Materials.jsx:261-299`。素材详情加载失败时 `catch` 后 `row=null`，最终显示“未找到该素材(可能已删除)”，见 `scribe3/web/src/Materials.jsx:115-134`。设定详情 `loadRows()` 多个分类接口 `.catch(() => [])`，见 `scribe3/web/src/CodexDetail.jsx:24-36`；`CodexDetail.reload()` catch 后显示“未找到该条目”，见 `scribe3/web/src/CodexDetail.jsx:599-610`。命题详情 `api.facts()` 失败也显示“未找到该命题(可能已被超越或删除)”，见 `scribe3/web/src/CodexDetail.jsx:399-447`。  
**影响:** 用户会把网络/后端失败理解为素材不存在、命题被超越、设定已删除，容易做出错误操作或误判系统状态。  
**建议:**  
- 最小止血：把 error 和 missing 分成两个状态，错误态显示“加载失败，重试”。  
- 产品补全：详情页保留上一次可用数据并标记 stale，避免失败时瞬间变空。  
- 架构重构：统一数据加载 hook，输出 `loading/error/empty/stale`，不要在每个组件里 catch 成空数组。  
**验收:** 模拟 `/materials`、`/facts`、`/motifs` 500 时，UI 不显示“未找到/暂无”，而是明确失败和重试。

### [P2][R2/R4][UI 友好性] 素材库入口完整但二栏信息密度仍偏高，错误态和空态缺少下一步层级

**证据:** 浏览器实测素材库二栏宽约 196px，首屏同时放搜索、新建/导入/网络、智能视图、分类、空态。`MaterialList` 结构见 `scribe3/web/src/Materials.jsx:244-405`。空态只有“新建一条”，没有把“导入”和“网络”作为同级下一步；错误态没有重试按钮，见 `scribe3/web/src/Materials.jsx:298`、`371-374`。  
**影响:** 能力没有丢，但二栏仍像小工作台而不是轻目录。素材多时可扫，素材空时用户不一定理解“新建/导入/网络”的优先级。  
**建议:**  
- 最小止血：错误态加重试；空态提供“新建/导入”两个主动作。  
- 产品补全：二栏只保留搜索、三主动作、筛选和列表；导入/网络详情完全交给三栏，减少二栏解释文本。  
- 架构重构：素材库二栏拆成 `MaterialDirectoryData` 和 `MaterialDirectoryView`，和能力注册表对齐。  
**验收:** 196px、240px、320px 三档二栏下搜索和动作不挤压；空态能直接选择新建或导入。

## 爆炸半径

- **入口:** 左栏设定库、素材库、伏笔、母题、检索、校验；三栏素材详情/导入/网络/设定详情；右栏主编上下文。
- **前端组件:** `Materials.jsx`、`MaterialImport.jsx`、`MaterialNetwork.jsx`、`CodexDetail.jsx`、`ContainerOutline.jsx`、`studioDocks.jsx`、`DirectoryPane.jsx`、`CapabilityDirectories.jsx`、`CapabilityDetailPanes.jsx`、`DetailPane.jsx`。
- **API:** `/materials`、`/materials/import/*`、`/materials/recall`、`/materials/graph`、`/materials/{mid}/refs`、`/materials/refs-by-chapter`、`/promises*`、`/motifs*`、`/character-relations*`、`/arc-beats`、`/voice-flags*`、`/facts*`。
- **后端/store:** `store.add_material`、`update_material`、`delete_material`、`add_material_reference`、`material_recall`、`material_graph`、`build_material_edges`、`_material_recall_block`。
- **测试:** `test_setting_system.py`、`test_ontology.py`、`test_ontology_complete.py`、`test_promise.py`、`test_pulse.py`、`test_voice.py`、`test_material_import.py`、`test_material_recall.py`、`test_material_memory.py`、`test_material_consume.py`、`test_hybrid_recall.py`、`test_material_bm25_probe.py`、`materials-workbench.test.jsx`、`directoryPane-capabilities.test.jsx`。

## 修复分层

**最小止血批次:**

1. 修素材删除文案，并禁止把“只影响素材库”作为确认提示。
2. 后端素材删除改软删除或清理 `material_reference`/`relates`，补测试。
3. 素材导入 commit 返回失败列表，前端展示成功/失败明细。
4. 素材列表、素材详情、设定详情区分 error 和 missing，给重试入口。

**产品补全批次:**

1. 章工作台加入“本章参考素材”账本，调用 `/materials/refs-by-chapter`。
2. 主编写作结果显示本次参考素材和理由，可跳转素材详情。
3. 伏笔/母题未选章时显示全书态，选章后显示章级切片。
4. 素材库空态把“新建 / 导入”作为同级主动作，网络作为探索入口。

**架构重构批次:**

1. 用真实数据源重建 `CapabilityDirectory`，替换静态 meta 和占位详情。
2. 把 `PromisesPanel`、`MotifsPanel`、`RecallPanel`、`QCPanel` 从 `studioDocks.jsx` 拆成独立能力模块。
3. 建立 `capability -> scope -> directory -> detail -> rightDock -> api -> tests` 注册表。
4. 素材引用、召回、网络、删除统一进素材数据生命周期服务，避免 UI 和 store 各自解释。

## 验证

已运行：

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_setting_system.py scribe3/tests/test_ontology.py scribe3/tests/test_ontology_complete.py
# 26 passed
```

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_promise.py scribe3/tests/test_pulse.py scribe3/tests/test_voice.py
# 21 passed, 1 warning
```

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/python -m pytest -q scribe3/tests/test_material_import.py scribe3/tests/test_material_recall.py scribe3/tests/test_material_memory.py scribe3/tests/test_material_consume.py scribe3/tests/test_hybrid_recall.py scribe3/tests/test_material_bm25_probe.py
# 33 passed, 1 warning
```

```bash
cd "/Users/miaoma/Downloads/写作 3.0/scribe3/web"
npm test -- src/__tests__/materials-workbench.test.jsx src/layout/__tests__/directoryPane-capabilities.test.jsx
# 2 test files passed, 8 tests passed
```

浏览器走查：

- 作品库 -> `纸命`：未选章左栏只有手稿/设定库/素材库。
- 素材库：搜索、新建、导入、网络入口可见；点击新建/导入/网络后，二栏保留目录，三栏切换对应工作台；console error/warn 为空。
- 选第 1 章：左栏出现演绎/伏笔/母题/检索/校验，校验 badge 为 17。
- 伏笔：二栏显示本章 8 条埋设伏笔；点击第一条后，三栏显示伏笔详情、生命周期、回收章、5 条线索和新增线索入口。
- 母题：二栏显示本章触及 7 个母题；点击第一条后，三栏显示母题详情；右栏主编上下文切为该母题。
- 检索：二栏显示语义召回设定搜索框；未执行实际搜索写入。
- 校验：二栏显示 QC 命中计数和张力检查按钮；未触发 LLM 张力检查。

未运行：

- 未执行真实素材导入提交、删除素材、张力检查、主编生成、反哺设定等写入或高成本动作。
- 未跑全量 `npm test`、全量 `pytest -q scribe3/tests`，按计划留到 E4 总回归。
- 未对大量素材、超长设定树做性能压测；留给 E3。

## 下一步

1. 进入 Wave D：演绎、搜索、校验/Pulse、图谱、时间线、仪表盘。重点查“能力面板点击后是否真正钻取到三栏详情”和“横切视图是否能回到左栏能力”。
2. Wave C 修复优先级最高的是素材删除生命周期、素材引用账本、导入失败明细，以及禁止静态 `CapabilityDirectory` 替代真实能力。
3. E4 汇总时把 Wave A/B/C findings 合并，形成 P0/P1/P2/P3 总排序和三批修复路线。
