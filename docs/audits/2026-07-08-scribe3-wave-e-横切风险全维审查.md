# 功能域审查：Wave E 横切风险、生产化和测试边界

**范围:** 限知/secret、REST/MCP 权限边界、删除/导入/迁移/回填、长篇性能、错误降级、测试体系和 e2e 安全边界。  
**审查方式:** 只读源码 + CodeGraph + 定点 pytest + 前端定点测试 + 应用内浏览器只读抽样。未执行会写真实作品的 e2e、删除、导入提交、张力检查和演绎面板。

## 结论

Wave E 的核心结论是：Scribe3 的限知和 work 隔离底座已经接近可承诺能力，迁移/事务/观测性也有明确工程纪律；但数据生命周期和生产化契约还没有达到同一标准。尤其是角色/命题删除仍是“直接删并返回 ok”，素材导入提交会吞掉单条失败，素材网络和素材列表没有分页/虚拟化边界，部分 e2e 虽标注会恢复，但本质会改真实《纸命》数据，不能作为普通回归直接运行。

这不是“代码是否能跑”的问题，而是产品承诺问题：用户在设定库、素材库、仪表盘或主编里看到的数据，必须能解释来源、失败、删除影响、部分成功和恢复路径。当前后端多处 fail-soft 能保护主写作链不中断，但 UI 和 API 契约没有把“降级/部分失败”表达给用户，容易把“没查到/没建边/没落库”误读成“确实没有”。

| 横切能力 | 成熟度 | 判断 |
|---|---|---|
| 限知/secret 屏蔽 | M3 闭环 | REST 默认打码、写作 prompt 物理投影、图谱私密遮蔽、MCP 默认掩码均成立；全知解锁边界需要 UI/调用方更明确。 |
| work 隔离和 MCP 绑定 | M3- 闭环接近完整 | REST `?work=` 和 MCP `SCRIBE3_WORK` 护栏明确；多书全知联查仍是后续架构问题。 |
| 迁移/事务/回填纪律 | M3 闭环 | 迁移失败不标记、事务聚合、已有 dry-run 回填脚本模式清楚。 |
| 删除/归档生命周期 | M1 可见 | 部分对象有 404，角色/命题仍直接硬删；引用影响、预览、级联/阻止、归档语义不一致。 |
| 素材导入与素材网络 | M2 可用 | 多格式导入、预览、召回、溯源存在；提交部分失败、边构建失败和网络空态不可解释。 |
| 长篇性能 | M2 可用 | 图谱、时间线、quality/progress 已有限流或缓存；素材列表/素材网络仍全量拉取和全量渲染。 |
| e2e 回归安全 | M2 可用 | 多数脚本有快照/恢复纪律；但写真实作品的脚本必须显式分级，不能混入普通只读回归。 |

## 业务闭环

| 环节 | 当前状态 | 证据 | 缺口 |
|---|---|---|---|
| 目标 | 保证所有作品、视角、数据写入和测试在长期使用中可信、可解释、可恢复。 | `api.js:9-11` 对业务请求统一加 `work`；`app.py:119-126` 仅给 MCP 绑定作品挂工具。 | 删除、导入、素材网络错误仍没有统一“影响预览/部分成功/可恢复”契约。 |
| 进入 | 用户从设定库、素材库、图谱、时间线、仪表盘、主编、MCP 工具和 e2e 脚本进入横切能力。 | 浏览器抽样：`乱世铜炉·设定参照` 可打开手稿、素材库、图谱、时间线、仪表盘，console 无 error/warn。 | 未选章时仍只显示手稿/设定库/素材库，全书级工艺能力不可见，已在 Wave A 报。 |
| 创建/读取 | 限知帧、素材召回、图谱、时间线、进度都是只读或可解释聚合；素材导入先预览再提交。 | `app.py:1335-1425`、`app.py:1889-1914`、`app.py:1178-1194`。 | 导入提交单条失败 `except Exception: pass`，只返回 created/ids。 |
| 使用 | 写作 prompt、主编、图谱、时间线、仪表盘使用设定/素材/伏笔/进度聚合。 | `app.py:2256-2270` 素材召回后记录引用；`store.py:1284-1293` 写 material_reference 并递增 recall_count。 | 引用写入失败被吞；章工作台没有显性素材引用账本，见 Wave C。 |
| 反馈 | 迁移失败会上抛；部分 UI 有错误态；素材列表有“素材加载失败”。 | `store.py:362-392` 迁移失败不标记；`Materials.jsx:298-299` 有加载失败。 | `material_graph` 边查询失败返回空边，角色/命题删除不存在也返回 ok，用户无法区分无数据和失败。 |
| 沉淀 | daily_progress、material_reference、relates、knowledge、reader_knows 等长期表承载沉淀。 | `store.py:1284-1303`、`store.py:1305-1323`、`store.py:2144-2185`。 | 删除对象时沉淀关系如何处理没有统一策略，素材删除不清引用/relates，角色/命题删除不查引用。 |
| 回收 | 有 promise/material/volume 等局部 404 或确认；迁移/回填已有 dry-run 先例。 | `app.py:1077-1082` material 删除 404；`scripts/backfill_voice_flags.py` 是 dry-run 模式先例。 | 角色/fact 删除未对齐，e2e 写真实作品依赖脚本自行恢复。 |

## 架构归属

| 层 | 当前职责 | 判断 |
|---|---|---|
| REST/API | `work` 参数、错误抛出、聚合端点、素材导入、删除。 | 读路径较稳，写/删路径契约不一致。角色/fact 删除比 material/promise 弱。 |
| MCP | 固定绑定 `SCRIBE3_WORK`，默认掩码 secret，写工具待批。 | 边界清楚，但多作品全知联查还未产品化。 |
| Store | 事实、知识边、素材引用、relates、进度、事务、迁移。 | 内核强；删除影响和引用清理未形成统一 lifecycle 层。 |
| UI | 左栏入口、二栏目录、三栏详情、仪表盘、素材工作台。 | 横切错误态不统一。长列表和全量素材网络缺生产化保护。 |
| 测试 | pytest/vitest/e2e 混合。 | 单元/集成覆盖较强；会写真实作品的 e2e 需要独立“带快照写入回归”档位。 |

## 八维评分

| 维度 | 分数 | 理由 |
|---|---:|---|
| 业务完善性 | 2 | 限知、work、迁移、图谱/时间线/进度能支撑业务；删除/导入/素材网络仍缺完整产品承诺。 |
| 逻辑闭环性 | 2 | 主要成功链成立；部分成功、引用清理、降级表达断开。 |
| 架构合理性 | 2 | REST/MCP/store 边界大体清楚；对象 lifecycle 没有统一层。 |
| 数据可信性 | 2 | secret/work 较强；硬删除、静默失败、边失败吞空仍伤害可信性。 |
| UI 友好性 | 2 | 浏览器抽样可用；错误、空态、长列表和全书能力发现性仍弱。 |
| 创作质量 | 2 | 素材/限知/伏笔进入写作链；但失败被吞会让主编依据不可解释。 |
| 失败恢复 | 1 | 多处 fail-soft 保护主链路，但用户和 API 调用方无法恢复或重试具体失败项。 |
| 工程可维护性 | 2 | 测试和迁移纪律不错；e2e 安全分层、性能契约和 lifecycle 仍需补。 |

## 用户旅程证据

浏览器打开 `http://127.0.0.1:3311/`，进入 `乱世铜炉·设定参照`，作品库显示 18 章、37,958 字。未选章时左栏只有 `手稿 / 设定库 / 素材库`，二栏一次列出 18 章，三栏为空态“从左侧项目树选一个章开始写”。console error/warn 为空。

点击左栏 `素材库` 后，二栏显示 `素材库 0/0`、`新建 / 导入 / 网络`、智能视图和分类；三栏仍是未选中空态。点击顶栏 `图谱` 显示知识图谱，包含 `6 角色 · 110 命题 · 129 边` 和 `🔒 私密` 图例；再点左栏 `素材库` 可回到素材库。点击 `时间线` 显示 `89事件·10伏笔·28弧光·10关系 · 共18章`。点击 `仪表盘` 显示质量仪表盘、码字进度、伏笔台账和质检问题。全程 console error/warn 为空。

## Findings

### [P1][R0/R1][数据可信性/逻辑闭环] 角色和命题硬删除无存在性、引用影响和 404 契约

**证据:** `app.py:500-503` 删除角色直接 `_store_for(work).delete_record(f"role:{local}")` 并返回 `{"ok": True}`；`app.py:547-550` 删除命题同样直接删除并返回 ok。`store.py:1130-1138` 已有 `exists()`，但 `delete_record()` 在 `store.py:1150-1152` 不返回是否存在，也不检查引用。  
**影响:** 用户删除不存在对象、被知识边引用的命题、被图谱/搜索/限知使用的角色时，都可能得到成功反馈。后续图谱、搜索、reader_knows、prompt 和校验可能留下孤儿引用或语义索引漂移。  
**建议:** 建立统一 lifecycle contract：先 `GET /impact` 或 dry-run 返回引用影响；删除不存在返回 404；默认归档优先于硬删；硬删必须清理/阻止知识边、reader_knows、语义索引、关系、弧光、素材 about_entities。  
**验收:** 删除不存在角色/fact 返回 404；删除被引用 fact 返回 409 或 impact 预览；确认硬删后 graph/recall/frame/verify 不出现孤儿。

### [P1][R1/R2][失败恢复/数据可信性] 素材导入提交逐条失败仍被吞，部分成功无法复盘

**证据:** `app.py:1178-1194` 的 `material_import_commit_ep()` 对每条素材 `try add_material/build_material_edges`，异常只 `pass`，最后 pop job 并返回 `{created, ids}`。  
**影响:** 作者确认导入后，如果某几条因分类、embedding、建边或数据库异常失败，UI 只能看到创建数量变少，不能知道哪条失败、为什么失败、是否可重试；job 也被删除，失去恢复上下文。  
**建议:** 返回 `created_ids`、`failed_items[{index,title,reason}]`、`warnings`；有失败时保留 job 或生成 retry token；UI 显示“部分导入成功”并允许重试失败项。  
**验收:** 注入一条非法 kind 或模拟 `build_material_edges` 失败，前端显示失败条目，成功条目保留，失败条目可修正重试。

### [P2][R2][数据可信性/失败恢复] 素材网络和引用沉淀失败会静默退化为空或缺证据

**证据:** `store.py:1402-1416` 的 `material_graph()` 全量 `list_materials()` 后查询 `relates`，异常时 `edges = []`；`app.py:2256-2270` 写作素材召回记录 `material_reference`，单条 `add_material_reference` 异常被吞。  
**影响:** 用户看到“没有联想边”或素材没有引用记录时，不知道是确实没有关系，还是建边/引用记录失败。素材库作为“参考记忆”的可信度下降。  
**建议:** `material_graph()` 返回 `degraded_sources` 或 `edges_degraded=true`；写作引用记录失败进入后端日志和前端 degraded 汇总，不阻断写作但要可见。  
**验收:** 模拟 relates 表不可用时，素材网络显示“节点可用、联想边降级”，而不是无声空边。

### [P2][R2/R4][性能/架构合理性] 素材列表和素材网络缺分页、虚拟化和 limit 契约

**证据:** `app.py:1054-1057` `/materials` 直接返回 `store.list_materials(kind)`；`store.py:1227-1234` `list_materials()` 无 limit/offset；`Materials.jsx:260-276` 拉全量或召回结果，`Materials.jsx:378-399` 直接 `.map(filtered)` 渲染；`store.py:1402-1416` 素材网络全量节点和全量 `relates`。相比之下，`app.py:295-326` `/timeline` 有 `limit/truncated`，`app.py:1249-1258` `/graph` 有 `limit/hop`，`store.py:2278-2342` 有 ego 子图和硬上限。  
**影响:** 素材量上百上千时，二栏会变慢，网络图可能一次拉取过重；用户无法判断被截断还是全量。  
**建议:** `/materials` 增加 `limit/cursor/query/kind/view`；二栏列表虚拟化；`/materials/graph` 增加 `limit/focus/hop/truncated`，默认只显示重要节点或最近/置顶/已引用。  
**验收:** 1000 条素材下二栏滚动稳定，网络默认小子图，接口明确返回 `truncated`。

### [P2][R2][失败恢复/UI 友好性] 卷操作失败仍只打 console，和全局 toast 纪律不一致

**证据:** `ContainerOutline.jsx:213-220` 新建卷失败 `console.error('addVolume failed', err)`；`ContainerOutline.jsx:224-230` 重命名失败只 console；`ContainerOutline.jsx:242-249` 删除卷失败只 console。  
**影响:** 卷是手稿目录的高频结构对象，失败时用户不知道是网络问题、权限问题、还是后端拒绝。  
**建议:** 与 `patchSynopsis`、`patchLabel`、`reorder` 对齐，失败时 rollback/reload + toast。  
**验收:** 模拟 `/volumes` 500，用户看到失败 toast，目录状态回滚。

### [P2][R0][测试体系/数据安全] 会写真实作品的 e2e 必须从普通回归中隔离

**证据:** `scribe3/web/e2e/qa_b4b.mjs:2-8` 标注会编辑《纸命》ch1 并 finally 恢复；`scribe3/web/e2e/qa_t10.mjs:3-5` 覆盖张力检查等，并对《纸命》写锚、arc-beats、测试伏笔后清理；`scribe3/web/e2e/qa_batchE.mjs:1-9` 是纯前端只读、零残留脚本。  
**影响:** 如果把写真实作品的 e2e 混进普通“build 绿/真机绿”，失败或中断可能留下测试数据，破坏用户作品。  
**建议:** e2e 分三档：`readonly`、`writes-with-snapshot`、`destructive-manual`；CI/日常只跑 readonly；写入档必须先快照、finally 恢复、结束后校验零残留，并在命令名上显式标注。  
**验收:** `npm run e2e:readonly` 不写 API；`npm run e2e:writes` 失败也执行恢复并输出残留检查。

### [P3][R1][权限边界] 全知解锁能力存在，但 UI/调用链需要更明确标注“不能进入限知续写”

**证据:** REST `facts` 默认 `reveal_secret=False`，见 `app.py:252-267`；MCP `s3_semantic_recall`、`s3_hybrid_recall`、`s3_graph_recall` 默认掩码，注释明确 `reveal_secret=True` 仅供主编全知联查，不能喂限知章续写，见 `mcp.py:104-149`。  
**影响:** 代码层防线清楚，但产品层如果未来让 UI 暴露 reveal 开关，必须防止用户或 agent 把全知结果带回限知写作 prompt。  
**建议:** UI/日志/工具调用都用明确标签区分“作者全知讨论”和“限知写作输入”；全知结果进入写作前必须走 frame 投影或手动确认。  
**验收:** 全知联查结果在 UI 中带标签；正文限知写作 prompt 测试断言不含帧外 secret 明文。

### [P3][R2][工程可维护性] MCP 单进程单 work 护栏有效，但多书工具联查仍是未来架构债

**证据:** `app.py:119-126` 仅当 `work == SCRIBE3_WORK` 才挂 s3 工具；`mcp.py:817-832` `setup_store()` 启动时固定绑定一个 db，并在注释里列出中期方案。  
**影响:** 当前不会串书，但非绑定作品降级为纯对话，主编无法联查该书。  
**建议:** 后续做 per-work MCP store cache 或每书独立 profile；这属于 R0 架构改造，不应夹在 UI 修补里。  
**验收:** 切到任意作品，主编工具联查的是当前作品；跨书切换不需要重启 MCP，或 UI 清楚显示该书不可用工具。

## 爆炸半径

| 问题 | 爆炸半径 | 影响入口 |
|---|---|---|
| 角色/fact 删除 lifecycle | R0/R1 | 设定库、图谱、搜索、限知、prompt、校验、MCP |
| 素材导入部分失败 | R1/R2 | 素材库、写作召回、主编、素材网络 |
| 素材网络降级不可见 | R2 | 素材库、主编证据、引用溯源 |
| 素材长列表性能 | R2/R4 | 素材库二栏、素材网络、导入后刷新 |
| e2e 写真实作品 | R0 | 开发流程、回归可信性、用户作品数据 |

## 修复分层

**第一批：数据可信止血**

- 角色/fact 删除先补 404 和 impact dry-run，不急着自动级联。
- 导入 commit 返回失败条目，不再吞错并删除 job。
- `material_graph`、`material_reference` 写入失败返回/记录 degraded。

**第二批：生产化补全**

- 素材列表加分页/虚拟化，网络图加 `limit/focus/hop/truncated`。
- 卷操作失败接 toast/rollback。
- e2e 分档并新增只读 smoke 命令。

**第三批：架构级闭环**

- 建统一对象 lifecycle 层，覆盖角色、fact、material、promise、motif、arc、relation。
- MCP 多书联查做 per-work profile/cache。
- 全知讨论结果和限知写作结果建立不可混用的类型/标签契约。

## 验证

```bash
cd "<repo-root>"
scribe3/.venv/bin/pytest -q scribe3/tests/test_security.py scribe3/tests/test_verify.py scribe3/tests/test_purpose_contract.py scribe3/tests/test_setting_system.py
# 35 passed, 1 warning

scribe3/.venv/bin/pytest -q scribe3/tests/test_migrate.py scribe3/tests/test_transaction.py scribe3/tests/test_ingest_idempotency.py
# 15 passed

scribe3/.venv/bin/pytest -q scribe3/tests/test_soak.py scribe3/tests/test_observability.py
# 9 passed

cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/materials-workbench.test.jsx src/layout/__tests__/directoryPane-manuscript.test.jsx src/layout/__tests__/fourPaneShell.test.jsx src/__tests__/detailPane-capabilities.test.jsx
# 4 test files passed, 21 tests passed
```

补充说明：裸 `pytest` 在当前 shell 中不可用，已改用项目 venv 的 `scribe3/.venv/bin/pytest`。本轮未跑会写真实作品的 e2e。

## 浏览器证据

- 服务：`http://127.0.0.1:3311/` 返回 200，`/api/works` 返回 5 本作品。
- 作品：`乱世铜炉·设定参照`，18 章，37,958 字。
- 走查：手稿目录、素材库、图谱、素材库回流、时间线、仪表盘。
- console：error/warn 为空。
- 未触发：删除、导入提交、演绎、张力检查、写入 e2e。

## 未覆盖

- 未跑全量 `pytest -q scribe3/tests`。
- 未跑全量 `npm test` 和 `npm run build`。
- 未跑写入型 e2e。
- 未做 1000 条素材量级压测。
- 未验证 `reveal_secret=true` 从 UI 暴露时的完整防误用链。

## 下一步

Wave E 的发现应和 Wave C/D 合并排序。优先级最高的是数据可信性：删除 lifecycle、导入部分失败、查看即写数据、final prompt 未传 phase。这些问题会影响用户是否能相信系统，而不只是影响局部体验。
