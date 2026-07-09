# 章关联与四栏交互修复设计

## 背景

当前章页顶栏仍叫“限知帧”，实际只覆盖 POV 知识帧、禁写、反讽与来源账本。用户要解决的是“我怎么知道这一章关联了哪些设定库、素材库的东西”，所以一级章页入口应升级为“关联”，覆盖章内设定、素材、伏笔、母题、限知和校验风险。

同时，V2 四栏路径丢失了旧三栏已有的边缘 tab 折叠/展开契约；手稿二栏也没有完全按 demo 的目录工作台模式落地，导致二栏像旧项目树，栏宽和详情联动都不够清晰。

## 目标

1. 章阶段一级 tab 文案改为“关联”，保留内部 key `frame` 以兼容已有 localStorage 与路由。
2. “关联”页能直接展示本章关联的设定、素材、伏笔、母题、限知、校验风险，并能跳转到三栏真实详情。
3. V2 四栏恢复二栏和四栏的拖拽、折叠、恢复与状态持久化。
4. 手稿二栏按 demo 模式实现：顶部当前章、工具区、卷章/场景目录、滚动列表，点击目录只更新栏3，栏2常驻。

## 非目标

1. 不重写素材库、设定库、伏笔、母题的详情页。
2. 不新增全知 secret 暴露开关。
3. 不把图谱、时间线、仪表盘移回左栏。
4. 本轮不自动 commit；实现验收后由用户决定是否提交。

## 信息架构

章阶段顶栏顺序保持：

`大纲 / 节拍 / 草稿 / 正文 / 简报 / 关联 / 北极星`

“关联”页内部采用“分组 -> 当前分类 -> 就地详情/跳转”的模式：

- 设定：本章涉及角色、命题、关系、事实或世界规则。点击后选中对应设定节点，栏3使用 `CodexDetail`。
- 素材：来自 `api.materialRefsByChapter(seq)`。点击后选中 `material` 节点，栏3使用 `MaterialDetail`。
- 伏笔：来自 `api.promisesLedger(work)`，筛出 setup/payoff/clue 命中当前章的行。点击后使用伏笔详情 pane。
- 母题：来自 `api.motifInstances(seq, work)`。点击后使用母题详情 pane。
- 限知：复用当前 `frame/irony` 数据，保留可写、禁写、反讽、盲区、来源。
- 校验：来自 `api.issues(seq)`。点击后使用校验 issue 详情 pane。

## 数据流

`ChapterStudio` 在 phase 为 `frame` 时渲染关联工作台：

```jsx
<FramePanel
  work={work}
  focalizer={meta?.focalizer || ''}
  focalizerOptions={meta?.chars || []}
  chapter={seq}
  meta={meta}
  onSelectNode={onSelectNode}
/>
```

`FramePanel` 继续负责章级关联画布，但增加关联数据聚合：

- `api.frame(focalizer, chapter)`
- `api.irony(focalizer, chapter)`
- `api.materialRefsByChapter(chapter)`
- `api.facts(chapter)`
- `api.characterRelations(chapter)`
- `api.promisesLedger(work)`
- `api.motifInstances(chapter, work)`
- `api.issues(chapter)`

任何接口失败时，该分组显示空态和降级提示，不把失败伪装成“没有关联”。

## 四栏折叠契约

V2 `FourPaneShell` 应复用旧三栏的行为模型：

- 栏2 `Panel` 增加 `panelRef`、`collapsible`、`collapsedSize="0%"`、`onResize`。
- 栏4 `Panel` 增加同样折叠契约。
- 点击左侧当前 active tab：折叠栏2；栏2已折叠时再次点击恢复。
- 点击右侧主编 rail 或恢复按钮：折叠/恢复栏4。
- 折叠状态按 work 隔离保存，避免不同作品串状态。
- 视图模式仍隐藏栏2；退出视图后按用户折叠状态恢复，而不是强制展开。

## 手稿二栏设计

`ManuscriptDirectory` 是栏2的权威手稿目录，不回退到旧 `ProjectTree`。它应展示：

- `DirectoryHeader`：标题“手稿”、当前章 badge、当前路径、跳章/过滤、上一章、同步。
- 书级工具：全书大纲、北极星、进度。
- 卷章区：卷、章、场景。卷可折叠，章和场景可选择。
- 长章节列表只在二栏内部滚动，不把栏3挤窄。

## 测试策略

1. `chapterStudio-topbar.test.jsx`：断言顶栏显示“关联”而非“限知帧”。
2. `framePanel.test.jsx`：断言关联页标题、设定/素材分组、点击素材/设定会调用 `onSelectNode`。
3. `fourPaneShell.test.jsx`：断言二栏和四栏可折叠/恢复，折叠状态持久化。
4. `directoryPane-manuscript.test.jsx`：断言手稿二栏 demo 结构、书级工具、卷章场景、点击章后目录仍常驻。
5. `npm run build`。
6. 浏览器验收：纸命 -> 第2章 -> 关联；检查设定、素材、限知分组；点击关联项跳三栏详情；折叠/恢复栏2和栏4；手稿二栏保持 demo 结构。

## 验收标准

1. 顶栏没有“限知帧”，只显示“关联”。
2. 关联页能看到本章设定和素材分组。
3. 点击素材或设定后，栏2不消失，栏3打开真实详情。
4. 二栏、四栏边缘 tab 和恢复按钮可用，刷新后状态不串书。
5. 手稿二栏符合 demo：工具区、卷章目录、当前章上下文齐全。
6. 旧三栏 flag 关闭路径不被破坏。
