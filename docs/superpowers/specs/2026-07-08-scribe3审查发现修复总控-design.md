# Scribe3 审查发现修复总控 · 设计文档

日期: 2026-07-08

状态: 已批准方向后的总控 spec, 待用户确认后进入实施计划

## 1. 结论

采用 **可信性止血 -> 产品闭环补全 -> 架构生产化** 的三批修复方式。

本轮不做大爆炸重构,也不按单个 UI 表象零散修补。审查发现的共同根因不是某个按钮或某个组件坏了,而是多个能力在“入口、目录、详情、右栏、API、store、prompt、测试”之间没有形成一致闭环。修复必须用总控工程管理:每个修复包都要有明确业务目标、爆炸半径、涉及能力、验收命令、浏览器路径和禁止事项。

最高优先级是 **数据和状态可信**。只要系统会查看即写、删除无影响分析、导入吞错、失败显示为空态,用户就无法相信后续任何 UI 优化。因此第一批先关闭 P1 可信性问题;第二批再把左栏、二栏、三栏、右栏真正连成产品闭环;第三批做可扩展和长期维护。

## 2. 输入依据

本 spec 以这些审查产物为权威输入:

- `docs/audits/2026-07-08-scribe3全系统全维审查总报告.md`
- `docs/audits/2026-07-08-scribe3-wave-a-全局骨架全维审查.md`
- `docs/audits/2026-07-08-scribe3-wave-b-写作主链路全维审查.md`
- `docs/audits/2026-07-08-scribe3-wave-c-知识与素材全维审查.md`
- `docs/audits/2026-07-08-scribe3-wave-d-工艺与横切视图全维审查.md`
- `docs/audits/2026-07-08-scribe3-wave-e-横切风险全维审查.md`

总报告给出的当前判断是:整体 **M2 可用,但未到 M3 稳定闭环**。本 spec 的目标就是把核心能力从 M2 推到 M3。

## 3. 修复总原则

### 3.1 先保真,再变美

第一目标不是界面更顺眼,而是用户不会被系统误导:

- 失败不能显示成空结果。
- 部分成功不能显示成全成功。
- 查看动作不能隐式写数据。
- 删除动作必须说明影响范围。
- 主编写作必须使用正确 phase 和上下文。

### 3.2 保留真实能力,替换壳不替换能力

左栏、二栏、三栏重构时,不能用静态目录或占位详情替代旧面板里的真实能力。迁移规则是:

```text
旧真实面板能力 -> 新目录模型 -> 真实详情/工作台 -> 右栏上下文
```

任何新组件如果只能显示占位文案,不能接到生产路由。

### 3.3 每个修复包独立验收

每个修复包必须满足:

- 有后端或前端定点测试。
- 有浏览器走查路径。
- 有旧能力回归清单。
- 有明确不覆盖项。
- 不能依赖“全量 build 绿”替代业务验收。

### 3.4 写真实作品的测试默认禁止

普通回归只能跑只读或沙盒测试。会写真实《纸命》等用户作品的 e2e 必须单独命名、显式快照、finally 恢复、结束复核零残留。

## 4. 修复包总览

| 包 | 名称 | 批次 | 关闭问题 | 爆炸半径 |
|---|---|---|---|---|
| F0 | 回归分级与验收护栏 | 0 | e2e 安全边界、验收混乱 | R0 |
| F1 | 正文 final phase 写作链 | 1 | `WriteChat` 未传 `phase='final'` | R1 |
| F2 | 演绎查看只读化 | 1 | `DeduceTree` 打开即写 | R1/R2 |
| F3 | 对象 lifecycle 契约 | 1 | 角色/fact/material 删除不可信 | R0/R1 |
| F4 | 素材导入和素材网络可信化 | 1 | 导入吞错、边失败不可见 | R1/R2 |
| F5 | 统一错误态/degraded/retry | 1 | 失败被空态/加载态/console 吞掉 | R1/R2 |
| F6 | 左栏能力全书态和 work-scoped 偏好 | 2 | 未选章能力消失、跨书 active 误导 | R2 |
| F7 | 四栏生产路由闭环 | 2 | `EntryRail/DirectoryPane/DetailPane` 未真实接壳 | R1/R2 |
| F8 | 全局搜索产品化 | 2 | 搜索伪全局、无跳转、无详情 | R2 |
| F9 | 校验 issue 台账 | 2 | QC/张力/Pulse 未统一可修复闭环 | R1/R2 |
| F10 | 素材引用账本与素材性能 | 2/3 | 章级引用不可见、长列表风险 | R1/R2 |
| F11 | 横切视图跳转和对象聚焦 | 2/3 | 图谱/时间线/仪表盘发现不能回流 | R2 |
| F12 | 大文件拆分和 MCP 多书联查方案 | 3 | `studioDocks` 聚合、MCP 单 work 债 | R0/R2 |

F0 是实施治理包,必须先做。F1-F5 是第一批可信性止血。F6-F11 是产品闭环补全。F12 是生产化架构包,只在前两批稳定后做。

## 5. F0 回归分级与验收护栏

### 目标

建立修复期间的安全边界,避免“修复审查问题”时污染用户作品或用窄测试冒充全系统完成。

### 设计

新增或整理三个回归档位:

| 档位 | 命名 | 允许行为 | 默认运行 |
|---|---|---|---|
| 只读冒烟 | `e2e:readonly` | 打开、切换、搜索、查看;不写数据 | 是 |
| 写入带快照 | `e2e:writes-with-snapshot` | 写沙盒或真实作品前快照,finally 恢复,复核零残留 | 否 |
| 破坏性手工 | `e2e:destructive-manual` | 删除、导入提交、真实迁移、张力检查等高副作用路径 | 否 |

每个修复包的验收记录必须写明跑了哪个档位,没跑哪个档位,为什么。

### 验收

- `package.json` 或测试文档中能区分三个档位。
- 写真实作品的脚本不能被默认 test 命令调用。
- 总控计划中每包都有测试档位声明。

## 6. 第一批: 可信性止血

### F1 正文 final phase 写作链

**问题:** 正文阶段右栏 `WriteChat` 未传 `phase='final'`,导致后端 final prompt 和演绎块真实入口未触发。

**目标:** 正文写作入口必须触发 final phase,并用测试证明 prompt 包含 final 写作所需上下文。

**设计:**

- 前端正文阶段调用 `WriteChat` 时显式传 `phase='final'`。
- 后端保留 `phase='final'` 默认语义,不把 final 降级成 draft。
- 增加前端测试证明正文阶段传 phase。
- 增加后端 prompt 内容测试,断言 final phase 仍包含本章演绎/scene_truth/deductions 等关键片段。

**验收:**

- 定点前端测试通过。
- 后端 prompt 测试通过。
- 浏览器在正文阶段发送主编写作请求时,network payload 含 `phase:"final"`。

### F2 演绎查看只读化

**问题:** `DeduceTree` 打开后自动 `patchChapter(seq, { involved_characters })`。

**目标:** 查看演绎面板永远只读;同步角色必须是用户明确确认的写操作。

**设计:**

- 自动推断涉及角色只生成本地建议列表。
- UI 显示“检测到可能涉及角色: A/B/C”,提供“同步到本章”按钮。
- 点击同步前展示预览:新增哪些、保留哪些、会写入哪个 work/seq。
- 写入成功后 toast;失败保留建议并显示错误。
- 切章或切作品时建议失效,避免跨章写错。

**验收:**

- 挂载 `DeduceTree` 不调用 `api.patchChapter`。
- 点击同步才调用 `patchChapter`。
- 浏览器打开演绎后不产生 PATCH 请求;点击同步才产生。

### F3 对象 lifecycle 契约

**问题:** 角色/fact 删除直接 ok,material 删除不清引用/relates,对象回收语义不统一。

**目标:** 删除前可解释影响,不存在返回 404,有引用时返回 409 或要求明确确认;默认优先归档。

**设计:**

建立统一 lifecycle API 语义:

```text
GET /objects/{type}/{id}/impact
POST /objects/{type}/{id}/archive
DELETE /objects/{type}/{id}?confirm_impact_token=...
```

第一阶段不必一次覆盖所有对象,但必须覆盖:

- `role`
- `fact`
- `material`

素材删除必须作为第一阶段的显式对象处理,不能只删 `material` 行。删除前要展示它的 `material_reference`、`relates`、`about_entities`、召回索引和章级引用影响;执行后要清理或保留可解释 tombstone,避免素材库、素材网络和章工作台引用账本互相矛盾。

impact 返回:

```json
{
  "object": {"type": "fact", "id": "fact:xxx", "label": "..."},
  "references": [
    {"kind": "knowledge_edge", "count": 3},
    {"kind": "semantic_index", "count": 1},
    {"kind": "graph", "count": 2}
  ],
  "recommended_action": "archive|refuse|hard_delete_allowed",
  "confirm_impact_token": "..."
}
```

**验收:**

- 删除不存在 role/fact/material 返回 404。
- 删除有引用 fact 返回 impact 或 409,不能静默 ok。
- material 删除清理或标记 `material_reference`、`relates`、召回索引影响。
- UI 删除确认文案显示影响范围。

### F4 素材导入和素材网络可信化

**问题:** 导入 commit 单条失败被吞;素材网络边查询失败显示为空边;引用记录失败被吞。

**目标:** 素材导入、素材网络和素材引用必须表达部分成功和 degraded。

**设计:**

- `material_import_commit` 返回:

```json
{
  "created": 2,
  "ids": ["a", "b"],
  "failed": [
    {"index": 3, "title": "xxx", "reason": "非法分类 kind=..."}
  ],
  "warnings": [
    {"index": 1, "stage": "build_edges", "reason": "embedding unavailable"}
  ],
  "retry_job_id": "..."
}
```

- UI 显示“部分导入成功”,列出失败条目,允许保留并重试。
- `material_graph` 返回 `degraded_sources` 或 `edges_degraded`。
- 写作召回记录 `material_reference` 失败时不阻断写作,但进入 degraded/日志,并可在章素材账本里提示“引用记录可能不完整”。

**验收:**

- 模拟单条失败,UI 能看到失败项。
- 模拟 relates 不可用,素材网络显示“节点可用,联想边降级”。
- 后端测试覆盖 `failed/warnings/degraded` 字段。

### F5 统一错误态/degraded/retry

**问题:** 搜索、仪表盘、progress、实时护栏、卷操作等失败会被空态、加载态或 console 吞掉。

**目标:** 用户能区分 loading、empty、error、degraded、partial success,并知道下一步。

**设计:**

建立前端状态展示标准:

| 状态 | UI 文案 | 必须动作 |
|---|---|---|
| loading | 加载中 | 显示 spinner 或骨架 |
| empty | 没有数据 | 给创建/导入/选择下一步 |
| error | 加载失败 | 显示错误摘要和重试 |
| degraded | 部分数据不可用 | 显示可用部分和降级源 |
| partial | 部分成功 | 列成功/失败明细 |

优先覆盖:

- `InsightView` 的 `quality/progress`
- 左栏搜索
- 实时护栏
- 卷 add/rename/delete
- 素材列表和设定详情加载失败

**验收:**

- 对每个覆盖点有失败注入测试。
- 浏览器中模拟失败时能看到错误/重试。
- 不再只有 `console.error`。

## 7. 第二批: 产品闭环补全

### F6 左栏能力全书态和 work-scoped 偏好

**问题:** 未选章时演绎/伏笔/母题/检索/校验消失;左栏 active tab 跨书保留。

**目标:** 左栏一级能力常驻;未选章时进入全书态,选章后进入章态;偏好按 work 隔离。

**设计:**

左栏固定入口:

```text
手稿
设定库
素材库
演绎
伏笔
母题
搜索
校验
```

章态差异只发生在二栏内容:

| 能力 | 未选章 | 已选章 |
|---|---|---|
| 演绎 | 全书演绎目录,提示选择章 | 当前章场景真相/角色限知 |
| 伏笔 | 全书伏笔台账 | 本章相关 + 全书分组 |
| 母题 | 全书母题列表 | 本章触及证据 + 全书母题 |
| 搜索 | 全书搜索 | 搜索时默认加当前章上下文 |
| 校验 | 全书质量概览 | 当前章 QC + issue 台账 |

偏好键从 `s3.leftTab` 改为 work-scoped,例如 `s3.${work}.leftTab`。

**验收:**

- 未选章仍显示 8 个入口。
- 切书后 active 入口不继承上一书误导状态。
- 浏览器走查空书、4 章书、18 章书。

### F7 四栏生产路由闭环

**问题:** 新 `EntryRail/DirectoryPane/DetailPane` 未完整接入生产壳,旧真实面板和新静态目录并存。

**目标:** 生产路径统一为:

```text
EntryRail -> DirectoryPane -> DetailPane -> RightDock context
```

**设计:**

- `EntryRail` 只负责一级能力和 active entry。
- `DirectoryPane` 负责二栏目录,按 entry 分发:
  - 手稿 -> `ManuscriptDirectory/ContainerOutline`
  - 设定库 -> 真实设定分类和条目
  - 素材库 -> `MaterialList`
  - 演绎 -> 当前章/全书演绎目录
  - 伏笔 -> 真实 promise ledger
  - 母题 -> 真实 motif list/instances
  - 搜索 -> 搜索结果目录
  - 校验 -> issue list
- `DetailPane` 只负责三栏详情/工作台。
- `CapabilityDetailPanes` 中占位内容不得接入生产;要么替换成真实详情,要么移除生产路由。

**验收:**

- 点击每个左栏入口,二栏常驻且不被详情替换。
- 点击二栏条目只刷新三栏。
- 旧能力不丢:演绎/伏笔/母题/搜索/校验都能访问原真实数据。
- `DirectoryPane` 有真实生产调用方和回归测试。

### F8 全局搜索产品化

**问题:** 搜索被包装成全局能力,真实只是设定语义召回文本列表。

**目标:** 搜索成为跨对象导航入口,能返回类型、来源、得分、跳转目标和三栏详情。

**设计:**

搜索结果类型:

- 设定: role/fact/item/place/faction/term/rule
- 章节: chapter/prose/synopsis/beats
- 素材: material
- 伏笔: promise
- 母题: motif/motif_instance
- 事件/关系: event/relation

统一结果结构:

```json
{
  "id": "result:...",
  "type": "material|fact|chapter|promise|motif|event",
  "label": "...",
  "excerpt": "...",
  "source": "设定库|素材库|手稿|伏笔|母题",
  "chapter": 4,
  "score": 0.82,
  "target_node": {"type": "material", "ref": "abc"}
}
```

UI:

- 二栏显示分组结果和筛选。
- 三栏显示选中对象详情。
- 右栏主编上下文聚焦当前结果。
- 失败显示 error,无结果显示 empty。

**验收:**

- 搜索同一关键词能返回至少两类对象的测试数据。
- 点击结果进入三栏真实详情。
- 浏览器检索 `借命` 能看到类型、来源、跳转。

### F9 校验 issue 台账

**问题:** QC、张力检查、Pulse、post-check 分散,结果不能进入统一可修复闭环。

**目标:** 校验入口成为 issue ledger,每条问题可定位、理解、修复、复查。

**设计:**

Issue 统一结构:

```json
{
  "id": "issue:...",
  "source": "qc|tension|pulse|post_check|verify|causal",
  "severity": "info|warning|blocking",
  "chapter": 4,
  "range": [120, 180],
  "title": "...",
  "reason": "...",
  "suggested_action": "...",
  "status": "open|resolved|ignored",
  "degraded_sources": []
}
```

UI:

- 左栏校验进入二栏 issue list。
- 三栏显示 issue 详情、定位正文、建议操作。
- 张力检查结果写入临时或持久 issue ledger,不是按钮下方孤立文本。
- 复查后更新状态。

**验收:**

- QC issue 能跳到正文范围。
- 张力检查不直接污染真实作品;结果进入 issue list。
- 失败时显示 degraded 或 error。

### F10 素材引用账本与素材性能

**问题:** 素材写作召回和引用溯源后端闭环,但章工作台不可见;素材列表和网络全量渲染。

**目标:** 作者能看到“本章用了哪些素材、为什么用、来自哪里”,并保证素材量增长后仍可用。

**设计:**

章工作台新增素材引用区域:

```text
本章参考素材
- 《标题》 · 手法 · phase:final · 被引用原因
- 《标题》 · 情绪卡 · phase:deduce · 被引用原因
```

素材库:

- `/materials` 支持 `limit/cursor/kind/view/q`。
- 二栏列表使用虚拟化。
- `/materials/graph` 支持 `focus/limit/hop/truncated`。

**验收:**

- 章详情能显示 `/materials/refs-by-chapter`。
- 1000 条素材模拟下二栏滚动稳定。
- 素材网络默认不全量炸图,显示 truncated 状态。

### F11 横切视图跳转和对象聚焦

**问题:** 图谱/时间线/仪表盘能发现问题,但部分对象不能回到具体工作对象。

**目标:** 横切视图发现的节点、事件、弱章、伏笔、关系都能跳回三栏详情或章工作台。

**设计:**

- 图谱节点:
  - role -> 设定详情
  - fact -> 命题详情
  - relation -> 关系详情
- 时间线 item:
  - event -> 事件详情/章工作台
  - promise -> 伏笔详情
  - arc -> 角色弧光详情
- 仪表盘:
  - 弱章 -> 章工作台校验页
  - 伏笔超期 -> 伏笔详情
  - 进度点 -> 对应日期/章聚合说明

右栏主编同步聚焦当前对象。

**验收:**

- 每类横切对象至少一个浏览器跳转用例。
- 跳转后左栏、二栏、三栏选中态一致。

## 8. 第三批: 架构生产化

### F12 大文件拆分和 MCP 多书联查方案

**问题:** `studioDocks.jsx` 聚合多域逻辑;MCP 当前单进程单 work,非绑定作品无法联查。

**目标:** 降低维护成本,为后续扩展提供稳定边界。

**设计:**

拆分前端模块:

```text
layout/
  EntryRail.jsx
  DirectoryPane.jsx
  DetailPaneRoutes.jsx
capabilities/
  manuscript/
  codex/
  materials/
  deduce/
  promises/
  motifs/
  search/
  issues/
rightDock/
  ChiefDock.jsx
  PilotDock.jsx
  InboxDock.jsx
hooks/
  useWorkScopedPref.js
  useCapabilitySelection.js
  useIssueLedger.js
```

MCP 多书联查采用二选一:

1. per-work store cache:工具签名带 work,内部 LRU 管理 store。
2. per-work MCP profile:每本书启动独立工具 profile。

推荐先写架构 ADR,不在第一批实现 MCP 改造。

**验收:**

- `studioDocks.jsx` 不再承担所有能力目录和右栏逻辑。
- 拆分后每个能力有自己的 tests。
- MCP ADR 明确选择、风险和迁移路径。

## 9. 实施顺序

严格按下面顺序推进:

1. F0 回归分级与验收护栏。
2. F1 正文 final phase。
3. F2 演绎查看只读化。
4. F3 对象 lifecycle 第一版。
5. F4 素材导入和网络可信化。
6. F5 统一错误态。
7. 第一批浏览器回归和提交。
8. F6 左栏全书态。
9. F7 四栏生产路由。
10. F8 全局搜索。
11. F9 校验 issue 台账。
12. F10 素材引用账本与性能。
13. F11 横切视图回流。
14. 第二批浏览器回归和提交。
15. F12 架构生产化。

F1-F5 可以部分并行开发,但必须按顺序合并。F6-F11 共享四栏路由状态,不能多人同时改同一生产壳而无协调。

## 10. 验收矩阵

每批收尾必须跑:

```bash
cd "/Users/miaoma/Downloads/写作 3.0"
scribe3/.venv/bin/pytest -q scribe3/tests/test_security.py scribe3/tests/test_verify.py scribe3/tests/test_purpose_contract.py scribe3/tests/test_setting_system.py
scribe3/.venv/bin/pytest -q scribe3/tests/test_migrate.py scribe3/tests/test_transaction.py scribe3/tests/test_ingest_idempotency.py

cd "/Users/miaoma/Downloads/写作 3.0/scribe3/web"
npm test -- src/__tests__/materials-workbench.test.jsx src/layout/__tests__/directoryPane-manuscript.test.jsx src/layout/__tests__/fourPaneShell.test.jsx src/__tests__/detailPane-capabilities.test.jsx
```

第一批额外:

- prompt/final phase 定点测试。
- DeduceTree no-write 测试。
- lifecycle delete/impact 测试。
- material import partial failure 测试。
- error/degraded UI 测试。

第二批额外:

- EntryRail/DirectoryPane/DetailPane 真实路由测试。
- 搜索多类型结果测试。
- issue ledger 测试。
- material refs-by-chapter UI 测试。
- 图谱/时间线/仪表盘跳转测试。

浏览器回归至少覆盖:

| 路径 | 必须证明 |
|---|---|
| 作品库 -> `纸命` -> 未选章左栏 | 8 个能力入口都可见 |
| 选第 1 章 -> 正文 -> 主编写作 | payload 有 `phase=final` |
| 演绎入口 | 打开不 PATCH,点击同步才 PATCH |
| 素材库导入失败模拟 | 部分成功和失败项可见 |
| 搜索 `借命` | 多类型结果和三栏详情 |
| 校验入口 | issue list -> issue detail -> 定位 |
| 图谱/时间线/仪表盘 | 可跳回具体对象 |
| 切书 | 左栏 active 不串书 |

## 11. 提交策略

每个修复包独立提交。提交信息建议:

```text
fix: wire final phase writing context
fix: make deduce tree readonly until confirmed
fix: add object lifecycle impact checks
fix: report material import partial failures
fix: surface degraded and retry states
feat: keep capability rail available without chapter selection
feat: route directory pane to real capability details
feat: add typed global search results
feat: add unified issue ledger
feat: show chapter material references
refactor: split studio docks by capability
```

不把 mockup、zip、无关下载目录、旧试验文件混进提交。

## 12. 不做事项

本修复总控不做:

- 不重写整个前端。
- 不一次性替换所有旧面板。
- 不在第一批做 MCP 多书联查实现。
- 不把搜索做成 LLM 智能问答。
- 不把写真实作品的 e2e 放进默认回归。
- 不为了视觉统一删除旧真实能力。

## 13. 完成定义

当以下条件全部满足,可以认为审查发现修复闭环完成:

1. 总报告 P1 findings 全部关闭或有明确降级说明。
2. P2 中涉及失败误导、长列表性能和错误态的问题至少完成产品可见修复。
3. 左栏 8 个能力入口在未选章和已选章状态都可达。
4. 二栏常驻目录、三栏真实详情、右栏对象上下文形成稳定路由。
5. 删除、导入、演绎、主编写作不再产生不可解释数据变化。
6. 搜索和校验从“文本面板”升级为可跳转、可修复的对象工作流。
7. 图谱、时间线、仪表盘发现的问题能回流到具体对象。
8. 只读 e2e 和写入 e2e 分档完成。
9. 每批都有测试输出和浏览器证据。
10. 未覆盖项被明确记录,不存在“假绿”状态。
