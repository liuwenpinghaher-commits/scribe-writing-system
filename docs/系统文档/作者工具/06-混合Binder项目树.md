# 作者工具 · 06 混合 Binder 项目树(ProjectTree + DetailPane)

> **本文是 `00`–`05` 这一批作者工具的「导航容器框架」。** 01–05 设计的是一个个**视图/工具**(大纲卷章树、时间线、伏笔台账、进度统计、护栏定位);本文设计的是**装这些工具的壳**——把当前「5 个平行 Rail 视图」升级为「左侧统一项目树 + 中间栏按节点路由的详情/卡片墙/大纲表」。这是 Scrivener Binder 模型的 scribe3 本地化落地。
>
> **与 01 的关系**:01「大纲与卷章树」设计的手稿树(`volume` 表 + `chapter.synopsis/volume/sort_order/label` + `GET /outline`)就是本文项目树的**「手稿支」**。本文不重新设计手稿树,直接把 01 的产物挂进来,并补上另一支(素材支)和一层统一抽象(`GET /project-tree`)。
>
> 代码基线:main(2026-06-28)。后端 `scribe3/`,前端 `scribe3/web/src/`。
> 目标读者:照此实现的前端工程师。性质:**设计文档,不改代码**,所有代码示例为待实现草案。

---

## 0 · 一句话定位

scribe3 现在是 **5 个互不相干的全屏视图**,顶栏 tab 一次只能看一个:写作台、设定库、图谱、仪表盘(+ 作品库)。手稿(章)和素材(角色/势力/物件…)分属两个视图,作者**没有一个「全书一览」的入口**;而 Scrivener 用一棵 Binder 树把草稿和研究素材统一在左侧,点任一节点就在中间栏加载对应内容。

本文交付:**混合 Binder**——左侧一棵 `ProjectTree`(📖 手稿支:卷→章→场景;📚 素材支:分类→具体项)常驻,中间 `DetailPane` 按选中节点类型**路由渲染**(章→写作台中间栏 / 设定项→详情卡 / 容器→卡片墙或大纲表);而图谱/时间线/台账/仪表盘这类**跨节点聚合视图**不挂在树上,走**顶栏一排 tab**(AppRail 保留为横切入口)并存。「混合」即指此:**树管「有详情的实体」,横切视图走顶栏 tab**。

> **两个已拍板决策(本文据此定稿)**:
> 1. **写作台嵌入 = 方案 B**:把写作台**左栏(大纲/结构/母题/联查)完全并入左侧项目树**,中间栏只留【对话 + 正文 + 护栏(含本章结构面板)】。这是更干净统一的方案——左侧不再出现「项目树 + 写作台自带左栏」双栏并列;代价是要迁移/下线 `WriteLayout` 自带的左栏渲染器(`renderOutline/renderStructure/renderMotifs/renderRecall`)。详见 §4.1、§4.5。
> 2. **横切视图入口 = 顶栏 tab 保留**:图谱/时间线/伏笔台账/仪表盘走**顶栏一排 tab**(`AppRail` 不彻底清空,渐进式收编)。**不设树底「视图」区**;窄屏同样靠顶栏。

---

## 1 · 现状与缺口(代码实证)

### 1.1 现在是「5 个平行 Rail 视图」

顶层编排在 `App.jsx`:`view` 状态只有 4 个值 + 作品库(`App.jsx:16` `useState('write')`;`App.jsx:39–43` 用 `if/else` 硬切):

```jsx
if (!cur) body = <Library .../>                       // App.jsx:39
else if (view === 'codex')   body = <CodexView .../>   // App.jsx:40
else if (view === 'atlas')   body = <AtlasView .../>   // App.jsx:41
else if (view === 'insight') body = <InsightView .../> // App.jsx:42
else body = <WriteLayout .../>                         // App.jsx:43(write 默认)
```

切视图靠顶栏 `AppRail`(`AppRail.jsx:3–8` 定义 `VIEWS = [write, codex, atlas, insight]`,`AppRail.jsx:26–34` 渲染成一排 tab 按钮)。**一次只能看一个视图,视图之间无共享上下文**:在设定库点了「焦三」,切回写作台不会带过去;在写作台第 5 章,切到图谱再回来,得重新找章。

### 1.2 手稿导航是「扁平按钮列」

写作台 `WriteLayout.jsx` 的章导航有两处,都**没有层级**:

- **顶栏步进器**(`WriteLayout.jsx:208–212`):`◂ 第 N 章 ▸`,纯 `setChapter(c±1)`。
- **左栏「素材→大纲」**(`WriteLayout.jsx:355–366`,`renderOutline()`):`chapters.map` 出一列纯文本按钮,点了 `setChapter(c.seq)`。数据来自 `api.chapters()`(只回 `seq,title`)。无卷、无梗概、无场景、无字数角标。

> 01 已经针对这块设计了 OutlineView(卷章树 + 卡片墙)。本文把它从「写作台左栏的一个 cap」/「第 5 个全屏 tab」**提升为整个应用的左侧常驻树的一支**。

### 1.3 素材导航是「11 分类 tab + 中区列表/表格」

设定库 `CodexView.jsx`:左栏 Rail 是 11 个分类 cap(`CodexView.jsx:8–20` `TABS`:概览/角色/设定命题/世界规则/势力/物品/术语/伏笔/母题/弧光/关系);`CodexView.jsx:703–725` 把每个分类渲染成左栏可展开的条目列表,点条目 `setSelected({type, row})`;中区 `DetailView`(`CodexView.jsx:380`)按 type inline 编辑(角色档案多字段 + 私密锁 `backstory_secret` + 弧光录入 `DynamicTimeline` + 关系 `DynamicRelations`)。

**关键观察**:设定库**已经是一个局部的「树→详情」模式**了(左栏分类→条目列表,点条目→中区详情卡)。它缺的只是:① 跟手稿统一在同一棵树里;② 用统一的节点抽象而非 `CodexView` 私有的 `TABS`/`selected` 状态。

### 1.4 图谱/仪表盘是「跨节点聚合」,本质不属于树

- `AtlasView.jsx`:读 `api.graph()`(`AtlasView.jsx:105`),把**全书**角色 + 命题 + 关系边用 ELK 布局画成一张图。它是**跨所有角色/命题的聚合**,没有「单个节点」可挂。
- `InsightView.jsx`:读 `api.quality()`(`InsightView.jsx:19`),按章铺字数/QC 曲线 + 弱章诊断。也是**跨全书章节的聚合**。
- 01 的伏笔台账、02 的时间线同理——都是横切。

### 1.5 现状 vs Scrivener 对照图

```
现状(scribe3 · 5 平行视图)                     Scrivener(统一 Binder)
┌─ AppRail: [写作台][设定库][图谱][仪表盘] ─┐    ┌─ Binder(左,常驻)──┬─ Editor / Corkboard / Outliner ─┐
│  一次只能看一个,互不共享上下文           │    │ ▾ Draft(草稿)      │  点节点 → 中间栏加载            │
│                                          │    │   ▾ 第一卷          │   · 文档 → Editor 写            │
│ write   → WriteLayout(章=扁平按钮列)     │    │     · 第1章         │   · 容器 → Corkboard 卡片墙     │
│ codex   → CodexView(11 分类 tab→详情)    │    │     · 第2章         │   · 容器 → Outliner 大纲表      │
│ atlas   → AtlasView(全书图谱,无单节点)  │    │ ▾ Research(研究)   │                                │
│ insight → InsightView(全书质量曲线)      │    │   · 角色档案        │  草稿 + 研究素材同一棵树        │
│                                          │    │   · 地点/参考       │  在任一视图拖拽重排 → 三处同步  │
│ 手稿 / 素材分属两视图,无「全书一览」     │    │                    │                                │
└──────────────────────────────────────────┘    └─────────────────────┴─────────────────────────────────┘
```

> Scrivener 的三视图(Binder / Corkboard / Outliner)**始终联动**:Binder 里文本的顺序对应 Corkboard 索引卡顺序、对应 Outliner 行顺序;在任一处重排,另两处同步([Literature & Latte — Integrating Binder, Corkboard, Outliner](https://www.literatureandlatte.com/blog/integrating-scriveners-binder-corkboard-and-outliner))。

---

## 2 · 概念:为什么是「混合」Binder

### 2.1 纯树塞不下横切视图

最朴素的想法是「万物皆树节点」。但 scribe3 有两类根本不同的东西:

1. **有「单一详情」的实体**:一个章有它的正文/对话/护栏;一个角色有它的档案。这类**天然是树节点**——点它,中间栏出它的详情,一对一。
2. **跨多个实体的聚合视图**:图谱是「所有角色 × 所有命题」的关系网;时间线是「所有事件沿章号横铺」;仪表盘是「所有章的质量曲线」;伏笔台账是「所有伏笔的 setup→payoff 审计」。这类**没有「一个节点」能代表它**——硬塞进树只能塞成一个孤立的叶子(「图谱」节点),点了它中间栏出全图,这和「节点=它的详情」的语义自相矛盾,且树里会冒出一堆没有子节点、只是「入口」的伪节点。

所以采用**混合**:树只装第 1 类;第 2 类作为 DetailPane 的特殊 mode,从**顶栏一排 tab**进入(决策②:横切入口锁定顶栏,不设树底「视图」区)。这正是 Scrivener 的做法——Binder 装草稿+研究(都是有详情的文档),而「全书统计 / 编译 / 项目搜索」这类聚合操作在菜单/工具栏,不在 Binder 里当节点。World Anvil 也类似:Content Tree 装文章(有详情),而 Maps / Timelines 是侧栏里独立的入口而非树节点([World Anvil — Content Trees](https://blog.worldanvil.com/worldanvil/tutorials/content-trees-to-organize-your-worldbuilding/))。

### 2.2 「进树 vs 横切视图」归类表(本文核心结论)

| 东西 | 进树? | 类型 | 点击/进入后中间栏出什么 | 数据源 | 现状对应 |
|---|---|---|---|---|---|
| **卷 volume** | ✅ 树·手稿支容器 | `volume` | 卡片墙(本卷各章卡)/ 大纲表 | 01 的 `volume` 表 | 01 设计,未实现 |
| **章 chapter** | ✅ 树·手稿支叶 | `chapter` | **完整写作台**(对话+草稿卡+正文+护栏) | `chapter` 表 | `WriteLayout` |
| **场景 scene** | ✅ 树·手稿支叶(章下) | `scene` | 写作台 + 定位正文到该场景段落 | `prose` 按 `* * *` 切分(01 §3.1) | 无(`SceneBreak.js` 推断) |
| **设定分类**(角色/势力/物件/术语/规则) | ✅ 树·素材支容器 | `codex_category` | 该分类卡片墙 / 表格(同 CodexView 列表) | 各设定表 | `CodexView` 的 `TABS` |
| **角色** | ✅ 树·素材支叶 | `character` | 角色详情卡(档案+私密锁+弧光+关系) | `character`/`entities` | `CodexView` DetailView(chars) |
| **势力 / 物件 / 术语 / 世界规则** | ✅ 树·素材支叶 | `faction`/`item`/`term`/`world_rule` | 对应详情卡 | `factions`/`items`/`terms`/`world-rules` | `CodexView` DetailView(通用) |
| **伏笔 / 母题** | ⚠️ 二象性(见 §2.3) | `promise`/`motif` | 详情卡(进树时) | `promises`/`motifs` | `CodexView` 表格 |
| **图谱(Atlas)** | ❌ 横切 | mode `atlas` | 全书知识图(ELK) | `api.graph()` | `AtlasView` |
| **时间线(Timeline)** | ❌ 横切 | mode `timeline` | 事件按章号横铺泳道 | 02 的 `GET /timeline` | 02 设计,未实现 |
| **伏笔台账(Promise Dashboard)** | ❌ 横切 | mode `promises` | 三栏台账 + setup→payoff 审计 | 03 的 `GET /promises*` | 03 设计,未实现 |
| **质量仪表盘(Insight)** | ❌ 横切 | mode `insight` | 字数/QC 曲线 + 弱章 | `api.quality()` | `InsightView` |
| **进度统计(Progress)** | ❌ 横切 | mode `progress` | 码字日历 + 连胜 + 目标 | 04 的 `GET /progress` | 04 设计,未实现 |
| **概览(Overview)** | ❌ 横切 | mode `overview` | 设定完整度统计 | `setting-completeness` | `CodexView` overview tab |

> **归类判据(一句话)**:**「这个东西有没有一份属于它自己的详情?」有 → 进树(点它出详情);没有、它是「跨一堆东西的聚合」→ 横切视图(从顶栏进)。**

### 2.3 伏笔/母题的二象性(给决策的小坑)

伏笔(promise)和母题(motif)**两边都沾**:单条伏笔有自己的字段(可当树叶→详情卡),但「伏笔台账」(03)是跨全书的 setup→payoff 聚合(横切)。建议:**素材支里给一个「伏笔」「母题」分类容器(点容器=表格列表,点单条=详情卡)**,同时**横切区保留「伏笔台账」mode**(03 的三栏审计视图)。二者数据同源、视角不同——正如 Plottr 的 Outline 是从 Timeline 同一份数据自动生成的另一种视角([Plottr — Outline Overview](https://docs.plottr.com/article/68-outline-overview))。这不是重复,是「列表管理 vs 全局审计」两种需求。

---

## 3 · 树的结构设计

### 3.1 顶层两支 + 横切入口区

```
ProjectTree(左侧常驻)
│
├─ 📖 手稿(MANUSCRIPT)              ← 复用 01 的 GET /outline
│   ├─ ▾ 第一卷 · 镇煞   (volume)
│   │   ├─ ● 1 楔子      (chapter)
│   │   ├─ ▾ 3 炼真      (chapter, 可展开)
│   │   │   ├─ · 地窖前的犹豫  (scene)
│   │   │   ├─ · 炼钉          (scene)
│   │   │   └─ · 灼伤与代价    (scene)
│   │   └─ ● 2 入派      (chapter)
│   ├─ ▾ 第二卷 · 出谷   (volume)
│   └─ ▾ 未分卷          (volume:null 兜底组)
│
├─ 📚 素材(CODEX)                  ← 复用现有设定表
│   ├─ ▾ 角色            (codex_category: character)
│   │   ├─ · 焦三        (character)
│   │   └─ · 沈青梧      (character)
│   ├─ ▸ 势力            (codex_category: faction)
│   ├─ ▸ 物件            (codex_category: item)
│   ├─ ▸ 术语            (codex_category: term)
│   ├─ ▸ 世界规则        (codex_category: world_rule)
│   ├─ ▸ 伏笔            (codex_category: promise)  ← §2.3 二象性
│   └─ ▸ 母题            (codex_category: motif,迁自写作台左栏「母题」cap,见 §4.5)

横切视图(概览/图谱/时间线/伏笔台账/仪表盘/进度)**不在树里**——
走顶栏一排 tab(AppRail),点 = 切 DetailPane 的 view mode。(决策②,见 §4.4)
```

> **横切入口锁定为顶栏 tab**(决策②):图谱/时间线/伏笔台账/仪表盘这类聚合视图从顶栏 `AppRail` 进入,**不在项目树里当节点、也不设树底「视图」区**。理由:它们没有「单一详情」可挂(§2.1),做成树底入口会与「树节点=它的详情」语义打架;顶栏一排 tab 是现状已有的形态,渐进收编代价最小。窄屏同样靠顶栏。

### 3.2 树节点的统一抽象

不管是卷、章、场景,还是角色、势力分类,前端都归一为同一个节点形状,由 `GET /project-tree` 一把返回:

```ts
type TreeNode = {
  id: string            // 全局唯一,如 "vol:1" / "ch:3" / "ch:3#scene:1" / "cat:character" / "character:焦三"
  type: 'manuscript_root' | 'volume' | 'chapter' | 'scene'
       | 'codex_root' | 'codex_category' | 'character' | 'faction' | 'item' | 'term' | 'world_rule' | 'promise' | 'motif'
  label: string         // 显示名,如 "第 3 章 炼真" / "焦三"
  ref?: string|number   // 跳详情用的原始键:chapter→seq;scene→{seq,idx};codex→local id
  children?: TreeNode[]  // 容器才有;叶子省略
  badges?: TreeBadge[]   // 角标:QC/字数/伏笔/私密/超期 等
  meta?: Record<string, any>  // 透传:focalizer、volume id、importance、secret 等
}
type TreeBadge = { kind: 'wc'|'qc'|'promise'|'pov'|'secret'|'overdue'|'count', value?: string|number, tone?: 'ok'|'warn'|'danger'|'fore'|'faint' }
```

设计要点:
- **`id` 全局唯一**:用 `type:ref` 前缀,避免「章 3」和「分类第 3 项」撞键。展开/选中态都用 `id`。
- **`ref` 是回原数据的钥匙**:点章 → 用 `ref`(=seq)调 `api.chapter(seq)`;点角色 → 用 `ref`(=local id)进详情卡。**树本身不搬运详情数据**,只搬「身份 + 角标」,详情按需懒加载(对齐 VS Code:TreeItem 只给 label/icon,内容点开才加载)([VS Code — Tree View API](https://code.visualstudio.com/api/extension-guides/tree-view))。
- **`children` 懒展开**:素材支的分类节点 `children` MVP 可一次性带回(条目通常几十条);手稿支场景 `children` 由后端切 `* * *` 得到。

### 3.3 后端聚合端点 `GET /project-tree`

合并 01 的手稿树(`/outline`)+ 设定分类树,一把返回左树渲染所需的**身份 + 角标**(不回正文、不回详情字段)。沿用 `?work=` 多书约定。

**响应示例**:

```json
{
  "manuscript": {
    "id": "manuscript_root", "type": "manuscript_root", "label": "手稿",
    "children": [
      {
        "id": "vol:1", "type": "volume", "label": "第一卷 · 镇煞", "ref": "1",
        "badges": [{ "kind": "count", "value": 3 }, { "kind": "wc", "value": "9.8k" }],
        "children": [
          {
            "id": "ch:1", "type": "chapter", "label": "1 楔子", "ref": 1,
            "meta": { "focalizer": "焦三", "label": "done" },
            "badges": [{ "kind": "wc", "value": "1.2k" }, { "kind": "pov", "value": "焦三" }, { "kind": "qc", "value": 0, "tone": "ok" }]
          },
          {
            "id": "ch:3", "type": "chapter", "label": "3 炼真", "ref": 3,
            "meta": { "focalizer": "焦三", "label": "revise" },
            "badges": [{ "kind": "wc", "value": "3.1k" }, { "kind": "pov", "value": "焦三" }, { "kind": "qc", "value": 1, "tone": "warn" }, { "kind": "promise", "value": 2 }],
            "children": [
              { "id": "ch:3#scene:0", "type": "scene", "label": "地窖前的犹豫", "ref": { "seq": 3, "idx": 0 }, "badges": [{ "kind": "wc", "value": "980" }] },
              { "id": "ch:3#scene:1", "type": "scene", "label": "炼钉",         "ref": { "seq": 3, "idx": 1 }, "badges": [{ "kind": "wc", "value": "1.3k" }] },
              { "id": "ch:3#scene:2", "type": "scene", "label": "灼伤与代价",   "ref": { "seq": 3, "idx": 2 }, "badges": [{ "kind": "wc", "value": "800" }] }
            ]
          }
        ]
      },
      { "id": "vol:null", "type": "volume", "label": "未分卷", "ref": null,
        "children": [ { "id": "ch:5", "type": "chapter", "label": "5 …", "ref": 5, "badges": [] } ] }
    ]
  },
  "codex": {
    "id": "codex_root", "type": "codex_root", "label": "素材",
    "children": [
      { "id": "cat:character", "type": "codex_category", "label": "角色", "ref": "character",
        "badges": [{ "kind": "count", "value": 8 }],
        "children": [
          { "id": "character:焦三",   "type": "character", "label": "焦三",   "ref": "焦三",   "meta": { "importance": "protagonist" }, "badges": [{ "kind": "secret", "tone": "faint" }] },
          { "id": "character:沈青梧", "type": "character", "label": "沈青梧", "ref": "沈青梧", "meta": { "importance": "major" } }
        ]
      },
      { "id": "cat:faction",    "type": "codex_category", "label": "势力",   "ref": "faction",    "badges": [{ "kind": "count", "value": 3 }], "children": [ /* … */ ] },
      { "id": "cat:item",       "type": "codex_category", "label": "物件",   "ref": "item",       "badges": [{ "kind": "count", "value": 5 }], "children": [] },
      { "id": "cat:term",       "type": "codex_category", "label": "术语",   "ref": "term",       "badges": [{ "kind": "count", "value": 12 }], "children": [] },
      { "id": "cat:world_rule", "type": "codex_category", "label": "世界规则", "ref": "world_rule", "badges": [{ "kind": "count", "value": 6 }], "children": [] },
      { "id": "cat:promise",    "type": "codex_category", "label": "伏笔",   "ref": "promise",    "badges": [{ "kind": "count", "value": 9 }, { "kind": "overdue", "value": 2, "tone": "danger" }], "children": [] },
      { "id": "cat:motif",      "type": "codex_category", "label": "母题",   "ref": "motif",      "badges": [{ "kind": "count", "value": 4 }], "children": [] }
    ]
  },
  "views": [
    { "id": "view:overview",  "type": "view", "label": "概览" },
    { "id": "view:atlas",     "type": "view", "label": "图谱" },
    { "id": "view:timeline",  "type": "view", "label": "时间线" },
    { "id": "view:promises",  "type": "view", "label": "伏笔台账", "badges": [{ "kind": "overdue", "value": 2, "tone": "danger" }] },
    { "id": "view:insight",   "type": "view", "label": "仪表盘" },
    { "id": "view:progress",  "type": "view", "label": "进度" }
  ]
}
```

**实现策略(后端,`store.py`)**:`project_tree()` 内部**复用而非另造**——
- `manuscript` 支:直接调 01 设计的 `self.outline()`(卷+章+场景+角标),映射成 `TreeNode` 形状(把 `volumes`/`chapters`/`scenes` 摊成嵌套 children)。01 没落地前,MVP 可退化为 `list_chapters()`(扁平章,无卷)套一个「全部章」伪卷。
- `codex` 支:对每个分类调已有读路径(`entities()` 过滤 character / `_query factions/items/terms/world-rules` / `promises()` / `motifs()`),每条只取 `id/name/label/几个 meta 字段 + 角标计数`(**不取全字段**,详情懒加载)。这些读方法 `CodexView.reload()`(`CodexView.jsx:545–560`)已经在前端拼了——后端把这一坨拼装下沉成一个端点即可。
- `views` 支:静态清单 + 少量横切角标(如 promise overdue 数,复用 03 的单源 overdue)。

> **不新造存储**:树是手稿表 + 设定表的**只读统一投影**。没有「tree」表、没有「node」表。增删改仍走各自的现有/01 设计的写端点(`save_chapter`/`reorder_chapters`/`editChar`/…),写完前端 `refetch project-tree`(或乐观局部更新)。

### 3.4 节点 → 中间栏(DetailPane)映射表

| 选中节点 type | 中间栏渲染 | 复用/新建 | 右栏(辅助) |
|---|---|---|---|
| `chapter` | **写作台中间栏**:主编对话 + 草稿卡 + ProseEditor 正文 + 护栏芯片 + 本章结构面板 | `WriteLayout` 瘦身版(接 `seq` prop;左栏 cap 已并入项目树,见 §4.5) | 写作台自带的**右** cap(主编对话/校验/伏笔/在场/演绎)+ 留下的左 cap(帧/意图、存档)继续在 DetailPane 内部 |
| `scene` | 写作台 + 进入后滚动/定位正文到该场景段落(`* * *` 第 idx 段) | `WriteLayout` + 新增 `scrollToScene(idx)` | 同上 |
| `volume` / `manuscript_root` | **卡片墙(Corkboard)** 或 **大纲表(Outliner)**,容器多模式(§3.5) | 01 的 `Corkboard`/`Outliner` | 无 / 卷简介编辑 |
| `codex_category` | 该分类**卡片墙/表格**(角色出卡,其余出表) | `CodexView` 的列表/表格区(`CodexView.jsx:633–694`) | 主编对话(设定向) |
| `character` | **角色详情卡**(档案 + 私密锁 + 弧光 `DynamicTimeline` + 关系 `DynamicRelations`) | `CodexView` 的 `DetailView(type='chars')` | 主编对话 |
| `faction`/`item`/`term`/`world_rule`/`promise`/`motif` | 对应**详情卡**(通用字段表) | `CodexView` 的 `DetailView`(通用分支) | 主编对话 |
| `view:*`(横切) | 对应横切视图(全屏占满中间栏) | `AtlasView`/`InsightView`/02/03/04 的视图 | 视图自带或无 |

> **容器节点的「多模式」**:点卷/分类这类容器,中间栏不是单一详情,而是「**这个容器里所有子项的某种排布**」,且可在卡片墙 ↔ 大纲表间切(顶部 segmented)。这正是 Scrivener 的容器行为——选中一个文件夹(容器),Editor 区按当前 Group Mode 显示成 Corkboard 或 Outliner;选中单个文档则显示其正文([Literature & Latte — Organize with the Corkboard](https://www.literatureandlatte.com/blog/organize-your-scrivener-project-with-the-corkboard))。

---

## 4 · 前端架构

### 4.1 新骨架:ProjectTree 常驻 + DetailPane 路由

```
App(顶层)
├─ AppRail(降级:书切换 + 横切视图 mode 入口 + 主题,见 §4.4)
└─ BinderLayout(新顶层布局,替代 App.jsx:39–43 的 if/else)
   ├─ ProjectTree(左,常驻,可拖宽/折叠,复用 shell.jsx 的 Resizer/宽度持久化)
   │   ├─ TreeSection 📖 手稿  → TreeNode 递归
   │   ├─ TreeSection 📚 素材  → TreeNode 递归
   │   └─ TreeSection 🔭 视图  → 横切入口(点=切 mode)
   └─ DetailPane(中,按 selected/mode 路由)
       ├─ mode==='node' & node.type==='chapter'/'scene'  → <WriteLayout seq=… />
       ├─ mode==='node' & node.type 容器                  → <ContainerView node=… />(卡片墙/大纲表切换)
       ├─ mode==='node' & node.type 素材叶               → <CodexDetail type ref=… />
       └─ mode==='view'                                   → <AtlasView/> | <InsightView/> | <Timeline/> | <PromiseDashboard/> | …
```

注意:**WriteLayout 内部已经是一套完整 Shell(左 cap + 中正文 + 右 cap)**(`WriteLayout.jsx:595–598`)。所以章节点的 DetailPane = 把这套 Shell 嵌进 BinderLayout 的中间栏。

**已拍板:采用方案 B(写作台左栏完全并入项目树)。**

- **方案 B(锁定)**:把 `WriteLayout` **自带的左栏 cap「素材 · 大纲/结构/母题/检索」**(`WriteLayout.jsx:542–562` 的 `leftCaps`,内部四个分段 `renderOutline/renderStructure/renderMotifs/renderRecall`)**拆解并入左侧项目树**——大纲并进手稿支、母题进素材支、检索(联查 Recall)归横切工具、结构留中间栏(逐项去向见 §4.5)。写作台瘦身为**「章节点的中间栏渲染器」**:只剩【主编对话 + 草稿卡 + 正文(ProseEditor)+ 护栏(NorthStarBar/护栏芯片)+ 本章结构面板】,左侧不再有第二根栏。这样整屏只有**一根**导航栏(项目树),视觉统一、心智一致。
- **代价**:要动 `WriteLayout` 的左栏渲染器——四个 `render*` 函数各有去向(下线/搬家),`leftCaps` 数组里的「素材」cap 移除,`Shell` 的 `left` 入参随之删掉。其余两个左 cap(帧/意图 `FramePanel`、存档 `VersionPanel`)和全部右 cap(主编对话/校验/演绎)**保持不动**,仍在写作台内。这比「A:整体嵌入、左栏留着」多了一道「拆左栏」的活,故迁移按 §5 分期摊开风险。
- **(被否的方案 A,仅存档)** 曾考虑「WriteLayout 整体嵌入、自带左右 cap 全留,只在最外层再加一根项目树」。否决理由:左侧会出现「项目树 + 写作台『素材』cap」**两根导航栏并列**(大纲在两处重复),违背 Binder「单一左侧导航」的初衷。故选 B。

### 4.2 ASCII 布局草图(章节点选中态)

```
┌─ AppRail ────────────────────────────────────────────────────────────────────────────┐
│ SCRIBE3   乱世铜炉 ▾ │   🔭 概览 图谱 时间线 伏笔台账 仪表盘 进度        ☾          │
├──────────────────────┬─────────────────────────────────────────────────┬──────────────┤
│ ProjectTree (常驻)   │  DetailPane(中间栏)= 章节点 → 写作台            │  写作台右栏  │
│ (可拖宽/折叠)        │                                                 │  (WriteLayout│
│                      │  ┌ 第 3 章 炼真 │ 视角:焦三 ▾ │ 护栏✓ 3.1k 保存▾ ┐│   自带 cap)  │
│ 📖 手稿              │  ├───────────────────────────────────────────────┤│  ┌─────────┐ │
│ ▾ 第一卷 · 镇煞      │  │ [草稿卡 DraftCard: 主编流式输出的提案]        ││  │主编对话  │ │
│   ● 1 楔子   1.2k✓   │  │                                               ││  │ WriteChat│ │
│   ▾ 3 炼真   3.1k⚠1  │  │ 焦三蹲在地窖口,火折子在指间…(ProseEditor)   ││  │          │ │
│     · 地窖前的犹豫   │  │ 正文可选中→改写按钮条→灌 seedQuote            ││  ├─────────┤ │
│     · 炼钉          │  │                                               ││  │校验/伏笔 │ │
│     · 灼伤与代价     │  │                                               ││  │/在场/演绎│ │
│   ● 2 入派   2.1k    │  └───────────────────────────────────────────────┘│  └─────────┘ │
│ ▾ 第二卷 · 出谷      │                                                 │              │
│ ▾ 未分卷            │   (WriteLayout 整体嵌入,对话+正文+护栏不退化)  │              │
│                      │                                                 │              │
│ 📚 素材              │                                                 │              │
│ ▾ 角色  8            │                                                 │              │
│   · 焦三  🔒         │                                                 │              │
│   · 沈青梧          │                                                 │              │
│ ▸ 势力  3            │                                                 │              │
│ ▸ 物件 ▸ 术语 ▸ 规则 │                                                 │              │
│ ▸ 伏笔  9 ⚑2超期    │                                                 │              │
│ ▸ 母题  4            │                                                 │              │
│ ──────────────────── │                                                 │              │
│ 🔭 视图              │                                                 │              │
│  概览 图谱 时间线    │                                                 │              │
│  伏笔台账 仪表盘 进度 │                                                 │              │
└──────────────────────┴─────────────────────────────────────────────────┴──────────────┘
```

容器节点(卷/分类)选中态——中间栏出卡片墙,顶部多模式切换:

```
├──────────────────────┬─────────────────────────────────────────────────────────────────┤
│ 📖 手稿              │  第一卷 · 镇煞   [卡片墙] 大纲表          筛选:全部▾ POV▾ 状态▾   │
│ ▾[第一卷·镇煞]◀选中  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                         │
│   ● 1 楔子          │  │■1 楔子   │ │■2 入派   │ │■3 炼真    │  ← 01 的 ChapterCard      │
│   …                 │  │焦三夜行… │ │拜师清潭…  │ │地窖炼钉… │     synopsis+字数+QC+POV  │
│                      │  │1.2k✓done│ │2.1k⚠1   │ │3.1k done⚑2│   点卡→选中该 chapter 节点 │
└──────────────────────┴──└──────────┘─└──────────┘─└──────────┘─────────────────────────────┘
```

### 4.3 状态管理(选中节点 → 中间栏)

顶层只加**两个**状态(其余沿用):

```jsx
// App.jsx / BinderLayout
const [tree, setTree] = useState(null)          // GET /project-tree 结果
const [sel, setSel] = useState({ mode: 'node', node: null })
// mode: 'node'(选中树节点)| 'view'(横切视图);node: TreeNode | null;viewKey: 'atlas'|...
const [expanded, setExpanded] = useState(() => new Set(['manuscript_root','codex_root']))  // 展开态

// 点树节点
const onSelectNode = (node) => {
  if (node.type === 'view') { setSel({ mode: 'view', viewKey: node.id.split(':')[1] }); return }
  if (CONTAINER_TYPES.has(node.type)) toggleExpand(node.id)  // 容器:展开 + 也可选中出卡片墙
  setSel({ mode: 'node', node })
}
```

- **选中态单一真相源**`sel`:DetailPane 纯由它路由,无隐藏耦合。跨视图上下文天然保持(从图谱回来 `sel` 还在第 3 章)。
- **持久化**:`sel.node?.id` + `expanded` 存 `localStorage`(按 work 隔离),刷新回到上次位置。对齐 Notion「侧栏即导航主轴、保留路径」的心智([Notion — Navigate with the sidebar](https://www.notion.com/help/navigate-with-the-sidebar))。
- **乐观更新**:详情里改了(存章/编辑设定/重排),局部 patch `tree` 对应节点的 badge,不必每次全量 refetch;重大结构变更(建卷/删角色)再 refetch。
- **无需 Redux/Zustand**:维持现有「`useState` + props 下传」风格(06 §1.1)。`sel`/`tree` 提到 `BinderLayout` 即可,深层组件经 props/回调。

### 4.4 AppRail 的去向

**决策②:AppRail 保留为横切入口(顶栏一排 tab),不彻底清空。** 降级为「**书切换 + 横切视图 tab + 主题**」:
- **保留**:字标、`当前书 ▾`(回作品库)、主题切换(`AppRail.jsx:39–45` 原样)。
- **改造**:原 `VIEWS = [write, codex, atlas, insight]`(`AppRail.jsx:3–8`)的 `write/codex` **删掉**(它们变成左树两支,不再是顶栏 tab);保留并扩充**横切视图 tab**(概览/图谱/时间线/伏笔台账/仪表盘/进度),作为顶栏一排 tab——点了 = `setSel({mode:'view', viewKey})`。
- **横切入口只在顶栏**:不设树底「视图」区(决策②)。一排顶栏 tab 是现状已有形态,渐进收编、风险最小;窄屏同样靠顶栏。这与树「只装有详情的实体」的语义一致——聚合视图不混进树。

### 4.5 写作台左栏功能 → 新家(方案 B 的核心细节)

方案 B 要拆 `WriteLayout` 自带的左栏 cap「素材 · 大纲/结构/母题/检索」(`WriteLayout.jsx:542–562`,内部四段 `renderOutline/renderStructure/renderMotifs/renderRecall`)。逐项去向、理由、迁移动作如下(代码锚点均为实读):

| 原左栏功能(实读) | 渲染什么 / 数据源 | 新家 | 为什么 | 迁移动作 |
|---|---|---|---|---|
| **大纲**(`renderOutline` `:355–366`) | `chapters.map` 出纯文本章按钮,点 `setChapter(c.seq)`;数据 `api.chapters()`(只回 `seq,title`) | 项目树 **手稿支**(卷→章→场景) | 章是「可导航实体」,正是树的本职;且 01 的卷章树本就该当手稿支,扁平按钮列被树取代 | **下线** `renderOutline`;选章逻辑从 `setChapter` 改为项目树 `onSelectNode(chapter)` 驱动(写作台接 `seq` prop) |
| **母题**(`renderMotifs` `:380–391`) | 母题列表(name/theme/unfolding),数据 `api.motifs()` | 项目树 **素材支** 的「母题」分类(`codex_category: motif`),与角色/势力等并列 | 母题是「带字段的库记录」,与素材支其它分类同构,点单条出详情卡;§2.3 已为它在素材支留了分类容器 | **下线** `renderMotifs`;母题数据进 `GET /project-tree` 的 `codex.children`(已在 §3.3 列出);单条详情走 `CodexDetail` |
| **结构 · 本章事件/事实**(`renderStructure` `:367–379`) | 本章 `events`(类型/目标缺失)+ `facts`(属性:值,私密锁),数据 `api.events(chapter)` / `api.facts(chapter)` | **留中间栏写作台内**(瘦身后 WriteLayout 的一个面板,跟随选中章) | 它是**「当前章的」伴随上下文**——随章切换而变,不是可独立导航的实体,进树会变成「跟着选中章漂移的伪节点」,与「树节点=稳定身份」冲突。**推荐留中间栏**(护栏区旁的「本章结构」面板) | **保留** `renderStructure` 函数,但从 `leftCaps` 移到 WriteLayout 中间栏(并入护栏/校验区,或作中间栏底部一格);不进树、不进 `GET /project-tree` |
| **检索 · 联查 Recall**(`renderRecall` `:392–403`) | 语义召回设定的搜索框 + 命中(`runRecall` → `api.recall(q,8)`) | **横切工具 / 命令面板**(顶栏或命令面板入口) | Recall 是「跨设定查证」的**搜索/工具**,不是某个节点的详情,也不是某个章的伴随上下文——它对全书设定做向量召回。归横切工具最合身:不进树、不算节点详情 | **搬家**:`renderRecall` 抽成独立「联查」工具组件,挂顶栏「联查」入口或命令面板;`api.recall` 不变。MVP 期可先暂留写作台内(见 §8) |
| **帧/意图**(`FramePanel`,`leftCaps` `:555–557`) | `FramePanel focalizer chapter`(当前章的帧/意图) | **留中间栏写作台内**(不动) | 当前章的伴随上下文,非可导航实体;且非「素材」cap 的一部分,本就独立 | **不动**(仍是写作台左/右 cap,或并入中间栏伴随区) |
| **存档**(`VersionPanel`,`leftCaps` `:558–561`) | 当前章存档点列表 + 恢复 | **留中间栏写作台内**(不动) | 当前章的版本历史,伴随选中章 | **不动** |
| **北极星条**(`NorthStarBar`,`center` 内 `:328`) | 全书意图条,喂主编当写作纲领 | **留中间栏写作台内**(不动) | 已在中间栏 `center` 顶部,伴随当前写作 | **不动** |
| **护栏芯片 + 体检**(`topbarMid` 护栏 Chip `:229–282` / `renderVerify` 等) | 限知泄露 / 五类 QC / 因果 / 生成后体检 | **留中间栏写作台内**(不动) | 当前章的质量护栏,伴随正文 | **不动**(护栏芯片在中间栏顶栏,校验在右 cap) |

> **一句话**:大纲、母题是「可导航实体」→ 进树;结构、帧、存档、北极星、护栏是「**当前章的伴随上下文**」→ 留中间栏写作台内;联查 Recall 是「**跨设定查证工具**」→ 归横切工具/命令面板。三类判据清晰,无歧义。
> **结构面板与联查的拍板**:结构面板**留中间栏**(它是当前章的上下文,不是可导航实体,进树会漂移);联查 Recall **归横切工具/命令面板**(它是搜索工具,不是节点详情)。

---

## 5 · 与现有 5 视图的迁移路径(渐进式,不推倒重来)

逐个落位,**每步都能独立上线、可回退**:

| 现视图 | 落到新架构 | 阶段 |
|---|---|---|
| `write`(WriteLayout) | **拆分**(方案 B):① 把「当前章」来源从 `useState(1)` 改成接 `seq` prop(01 §3.3 已设计 `initialSeq`);② **拆左栏**——`leftCaps` 里的「素材 · 大纲/结构/母题/检索」cap 按 §4.5 解体:`renderOutline` 下线(职能归手稿支)、`renderMotifs` 下线(母题进素材支)、`renderRecall` 搬去横切工具、`renderStructure` 移进中间栏面板。WriteLayout 瘦身为「章节点的中间栏渲染器」(对话+正文+护栏+本章结构面板),左侧不再有第二根栏;帧/意图、存档两个左 cap 保留。 | MVP(接 seq + 大纲下线)→ 进阶(母题/联查/结构拆净) |
| `codex`(CodexView) | 拆成两半:① **分类列表**(`TABS` + 条目)→ 上移成 ProjectTree 素材支;② **DetailView**(`CodexView.jsx:380` 详情卡)→ 素材叶节点的 DetailPane 渲染器。`reload()` 的多端点拼装(`CodexView.jsx:545`)下沉进 `GET /project-tree`。概览/弧光/关系这类非「单条详情」的子 tab 归横切区或容器卡片墙。 | MVP(列表上树)→ 进阶(详情拆出) |
| `atlas`(AtlasView) | 原样变 `view:atlas` 横切 mode。**零改**,只换挂载点(从 `App.jsx:41` 的全屏 if 分支 → DetailPane 的 view 分支)。 | MVP(暂留 Rail)→ 收编 |
| `insight`(InsightView) | 同上,变 `view:insight`。**零改**。 | MVP→收编 |
| (01 OutlineView) | **不单独存在**——它的卷章树就是手稿支,卡片墙/大纲表就是容器节点的 DetailPane。01 与本文**合并落地**:01 出后端(`/outline`/`reorder`/卷 CRUD)+ Corkboard/Outliner 组件,本文出树容器 + 路由。 | MVP/进阶 |
| (02 时间线 / 03 台账 / 04 进度) | 新增 `view:timeline`/`view:promises`/`view:progress` 横切 mode,各自按 02/03/04 实现。 | 进阶/完整 |

**渐进顺序(关键,方案 B + 顶栏 tab)**:
1. **先树 + 手稿 + 拆大纲**:ProjectTree 渲手稿支(复用 `list_chapters` 或 01 的 `/outline`),点章 → WriteLayout(接 `seq`);同步**下线 WriteLayout 的 `renderOutline`**(大纲职能交给手稿支),其余左栏块(结构/母题/检索)**暂留写作台内**不动。横切视图仍走 AppRail 顶栏 tab。此步已能「一屏看骨架 + 点章即写」,且左侧大纲不再两处重复。
2. **再并素材支 + 搬母题**:ProjectTree 加 codex 支(含母题分类),点设定项/母题 → CodexDetail;**下线 `renderMotifs`**。设定库旧全屏视图可下线。
3. **拆净写作台左栏**:`renderRecall` 搬成横切「联查」工具(顶栏/命令面板)、`renderStructure` 移进中间栏面板;`leftCaps` 的「素材」cap 整体移除,WriteLayout 完成瘦身。横切视图(atlas/insight/timeline/promises/progress)从旧 tab 收编为 DetailPane 的 view mode,仍由**顶栏 tab** 触发,AppRail 完成降级(保留为横切入口,不清空)。

---

## 6 · 实现任务分解(有序,含改哪些文件 + TDD/验证要点)

> TDD:先写失败测试再实现到绿。后端测试 `scribe3/tests/`,前端 `web/src/__tests__/`(vitest + RTL)。真类型检查用 `npm run build`(MEMORY「假绿」坑:`tsc --noEmit` 是空操作)。

### T1 · 后端 `GET /project-tree`(只读投影)
- **文件**:`store.py` 加 `project_tree()`(内部复用 `outline()`/`entities()`/`factions`/`items`/`terms`/`world-rules`/`promises()`/`motifs()` + 角标计数,映射成 TreeNode);`app.py` 加 `@app.get("/project-tree")`。01 未落地时手稿支退化为 `list_chapters()` 套「全部章」伪卷。
- **TDD**(`tests/test_store.py` / `test_app.py`):种 1 卷 2 章 + 2 角色 + 1 势力 → 断言 `manuscript.children` 卷/章嵌套正确、`codex.children` 分类计数对、章节点带 `wc/qc/pov` badge、`views` 静态项齐。`TestClient` GET 200 + 结构断言。

### T2 · `api.js` + ProjectTree 组件(只读树)
- **文件**:`api.js` 加 `projectTree: () => j('/project-tree')`;新建 `ProjectTree.jsx`(递归 TreeNode + 展开/选中 + badge 渲染,复用 `shell.jsx` 的宽度持久化 `useNumPref` + `Resizer`);新建 `BinderLayout.jsx`(左树 + DetailPane 容器)。
- **TDD**:mock `projectTree()` → 断言渲两支 + 分类计数文本 + 章 badge;点节点 → `onSelectNode(node)` 以正确 node 调用;展开/收起切 `children` 可见性。

### T3 · DetailPane 路由 + 章节点接写作台 + 拆大纲 cap
- **文件**:新建 `DetailPane.jsx`(按 `sel.mode`/`node.type` 路由,§4.1);`WriteLayout.jsx` 把 `chapter` 来源从 `useState(1)` 改为接 `seq` prop(`useEffect` 同步,复用 01 `initialSeq` 设计,保留 focalizer/title 恢复 `WriteLayout.jsx:112–113`);**(方案 B)下线 `renderOutline`(`:355–366`)**——`matSeg` 去掉「大纲」段,选章改由项目树 `onSelectNode` 驱动;`App.jsx` 用 `BinderLayout` 替换 `:39–43` 的 if/else,提 `sel`/`tree` 状态。
- **验证**:点章节点 → 中间栏出**写作台**(对话+草稿卡+正文+护栏齐全,**未退化为纯文本编辑器**——硬约束①);左侧只有项目树一根栏(大纲不再在写作台内重复);切到别的节点再回来,章不丢。

### T3b · 拆 WriteLayout 左栏剩余块(方案 B,进阶)
- **文件**:`WriteLayout.jsx`——`renderMotifs`(`:380–391`)**下线**(母题改由素材支节点 → CodexDetail 承载);`renderRecall`(`:392–403`)**抽成独立「联查」工具组件**,挂顶栏/命令面板入口(`api.recall` 不变);`renderStructure`(`:367–379`)**从 `leftCaps` 移进中间栏**(并入护栏/校验区或作中间栏「本章结构」面板,跟随 `chapter`);最终从 `leftCaps`(`:542–562`)移除「素材」cap,`Shell` 的 `left` 入参随之精简(只剩帧/意图、存档两个 cap,或全收进中间栏)。
- **TDD**:断言写作台不再渲染「素材→大纲/母题/检索」cap;母题点击走 CodexDetail;联查入口可独立打开并召回;本章结构面板随选中章刷新(`events`/`facts`)。**约束①不回归**(对话+正文+护栏仍全)。

### T4 · 素材叶 → CodexDetail(详情卡拆出)
- **文件**:把 `CodexView.jsx` 的 `DetailView`(`:380`)抽成独立 `CodexDetail.jsx`(接 `{type, ref}`,内部懒加载该条全字段 + 弧光/关系子组件);DetailPane 素材叶分支渲染它。
- **TDD**:点角色节点 → 渲档案字段 + 私密锁 + `DynamicTimeline`;点势力/物件 → 通用字段表;编辑某字段 → 调对应 `editChar/post` + 乐观更新 tree badge。

### T5 · 容器节点多模式(卡片墙/大纲表)
- **文件**:新建 `ContainerView.jsx`(顶部 segmented 切 卡片墙/大纲表;卷→复用 01 的 `Corkboard`/`Outliner`;分类→复用 CodexView 列表/表格区);点卡片/行 → `onSelectNode` 选中对应叶节点。
- **TDD**:卷容器渲卡片墙、各卡 synopsis/字数/QC;切大纲表同源;点卡 → 选中该 chapter 节点(中间栏切到写作台)。

### T6 · 横切视图收编 + AppRail 降级(顶栏 tab,决策②)
- **文件**:DetailPane 加 `mode==='view'` 分支挂 `AtlasView`/`InsightView`(零改)+ 02/03/04 视图;`AppRail.jsx` 删 write/codex tab、把横切入口(概览/图谱/时间线/伏笔台账/仪表盘/进度)保留为**顶栏一排 tab**,点击 = `setSel({mode:'view',…})`。**不设树底「视图」区**(决策②)。
- **验证**:顶栏点图谱 → 中间栏出全图,树选中态不变;窄屏靠顶栏入口;AppRail 仍在(降级为横切入口,未清空)。

### T7 · 场景级(完整)
- **文件**:后端 `project_tree()` 手稿支带 `scene` children(01 的 `* * *` 切分);`WriteLayout` 加 `scrollToScene(idx)`;点 scene 节点 → 写作台 + 定位正文段落。
- **TDD**:`_split_scenes` 已在 01 单测;点场景 → 正文滚动到第 idx 段(`SceneBreak` 锚)。

### T8 · 拖拽重排(完整,接 01)
- **文件**:ProjectTree 手稿支接 `@dnd-kit`,拖章重排 → `api.reorderChapters`(01 §3.2,**只改 sort_order 不动 seq**);首次重排守卫提示「重排只改阅读顺序,章号不变」。
- **TDD**:`computeReorder` 纯函数单测;模拟拖拽 → 调 `reorderChapters` 的 `order` 正确;断言请求体不含 seq 变更。

### T9 · 文档对齐
- 更新 `06-前端与交互.md`(标记 5 视图收编为 Binder)+ `00-作者工具总索引.md`(加本文为第 6 篇/容器框架)。

---

## 7 · 验收标准(可勾选)

**后端**
- [ ] `GET /project-tree` 返回 `{manuscript, codex, views}`,均为 TreeNode 形状;手稿支卷→章(→场景)嵌套;素材支分类→条目;不回正文/详情全字段。
- [ ] 章节点带 `word_count/qc/pov` 角标;分类节点带 `count`;伏笔分类/伏笔台账带 `overdue` 角标(复用 03 单源 overdue)。
- [ ] `project_tree()` **复用**现有读路径,**不新建 tree/node 表**;现有测试不回归(`pytest scribe3/tests`)。

**前端 · 硬约束**
- [ ] **(约束①)** 点【章】节点 → 中间栏出**完整写作台**(主编对话 + 草稿卡 + 正文编辑 + 护栏),**未退化为纯文本编辑器**。
- [ ] **(约束②)** 图谱/时间线/伏笔台账/仪表盘**不在树里当节点**,而是横切 mode,走**顶栏 tab**进入(决策②;不设树底「视图」区)。
- [ ] **(约束⑥,方案 B)** 点【章】后**左侧只有项目树一根导航栏**,写作台不再渲染自带的「素材 · 大纲/结构/母题/检索」左 cap;大纲在手稿支、母题在素材支、联查在横切工具、结构在中间栏面板(各居其位、无重复)。
- [ ] **(约束③)** 拖拽重排只改 `sort_order`,`chapter.seq` 始终不变;首次重排有守卫提示。
- [ ] **(约束④)** 手稿支复用 01 的 `volume` + `chapter.synopsis/volume/sort_order/label`;素材支复用现有设定表;无新造存储。
- [ ] **(约束⑤)** 素材叶点击出**结构化详情卡**(非文档编辑器);文档已说明 scribe3「素材=带字段的库记录」与 Scrivener「自由文档/PDF」的差异。

**前端 · 功能**
- [ ] ProjectTree 常驻左侧,可拖宽/折叠/展开收起;选中态/展开态按 work 持久化,刷新恢复。
- [ ] DetailPane 由单一 `sel` 路由:章→写作台 / 场景→定位段落 / 设定项→详情卡 / 容器→卡片墙(可切大纲表)/ view→横切视图。
- [ ] 跨视图上下文保持(从图谱回来仍在原章)。
- [ ] AppRail 降级为书切换 + 横切入口(顶栏一排 tab)+ 主题;原 write/codex tab 移除,AppRail 不彻底清空(决策②)。
- [ ] 前端测试全绿;`npm run build` 通过。

---

## 8 · 分期

> **「拆左栏」按分期摊风险(方案 B 的关键策略)**:方案 B 要解体 WriteLayout 的「素材」左 cap,但**不必一次拆完**。MVP 只拆**大纲**一段(下线 `renderOutline`,职能交手稿支),**其余三块(结构/母题/检索)暂留写作台内**——此时左侧已是「项目树 + 写作台残留『素材』cap(只剩结构/母题/检索三段)」,可接受的过渡态;到完整期再把母题搬素材支、联查归命令面板、结构移中间栏,最终移除整个左 cap。这样把「拆左栏」的回归风险分摊到三期,每期都能独立上线、可回退。

### MVP — 看见全书 + 点章即写(大纲先并树)
- **范围**:T1(手稿支可退化版)+ T2 + T3 + T4。左树渲**手稿卷章**(01 落地则带卷/场景,否则扁平章套伪卷)+ **素材分类→条目**;点章 → 写作台(对话+正文+护栏)+ 进入接 `seq`;点设定项 → 详情卡。**横切视图(图谱/仪表盘)暂留 AppRail 顶栏 tab,不收编**(决策②)。
- **写作台左栏处置(本期)**:只**下线 `renderOutline`**(大纲并入手稿支,避免两处重复);**结构(`renderStructure`)、母题(`renderMotifs`)、检索(`renderRecall`)三块暂留写作台「素材」cap 内不动**——本期不强拆,把拆左栏的风险后置到进阶/完整期。帧/意图、存档、护栏、北极星全留中间栏写作台内。
- **价值**:作者第一次有「全书一览 + 一键点到任意章/任意设定」的统一入口,手稿/素材不再割裂,且大纲不再两处重复。是 01–05 所有工具的落脚壳。

### 进阶 — 容器多模式 + 详情拆净 + 母题搬素材支
- **范围**:T5(卷/分类卡片墙 ↔ 大纲表)+ CodexView 详情完全拆成 DetailPane 渲染器,旧设定库全屏视图下线;**T3b 起步:`renderMotifs` 下线**,母题归素材支「母题」分类(点单条 → CodexDetail)。
- **价值**:容器节点像 Scrivener 一样可在「树/卡片/表」间切;母题从写作台左栏移出,左栏只剩结构/检索两段。

### 完整 — 横切收编 + 拆净左栏 + 场景级 + 拖拽
- **范围**:T6(atlas/insight/timeline/promises/progress 全部收编为 view mode,由**顶栏 tab** 触发,AppRail 完成降级、不清空)+ **T3b 收尾:`renderRecall` 搬成横切「联查」工具(顶栏/命令面板)、`renderStructure` 移进中间栏「本章结构」面板,`leftCaps` 的「素材」cap 整体移除** + T7(场景节点 + 正文定位)+ T8(`@dnd-kit` 拖拽重排,接 01,守卫提示)。
- **价值**:单一外壳容纳全部工具,5 个平行视图彻底统一为「一棵树 + 一个按节点路由的中间栏(写作台只剩对话+正文+护栏+本章结构)+ 顶栏横切 tab」;写作台左侧不再有第二根栏(方案 B 落地完成)。

---

## 附 A · 全网工艺锚(统一树 + 中间详情 + 多展示模式,带出处)

1. **Scrivener — Binder/Corkboard/Outliner 三视图始终联动,容器选中切模式**:Binder 是左侧把草稿(Draft)与研究素材(Research)**统一在一棵树**的层级导航;选中容器(文件夹),Editor 区按 Group Mode 显示为 Corkboard(索引卡墙,卡正面是 synopsis)或 Outliner(可定制列的表格);选中单个文档则显示其正文。三视图共享同一份数据与顺序,任一处拖拽重排,另两处同步。→ **scribe3 落地**:树节点点击驱动中间栏;容器节点多模式(卡片墙/大纲表);章=文档→写作台。([Literature & Latte — Integrating Binder, Corkboard, Outliner](https://www.literatureandlatte.com/blog/integrating-scriveners-binder-corkboard-and-outliner)、[Organize with the Corkboard](https://www.literatureandlatte.com/blog/organize-your-scrivener-project-with-the-corkboard))

2. **Plottr — 多视图同源,Outline 由 Timeline 数据自动生成**:Timeline(章×情节线网格)、Outline(线性大纲)、Plan(Kanban)是**同一份数据的不同视角**——Outline「automatically generated using the content and structure of your Timeline」;颜色编码(情节线色/POV 色)跨视图一致,移动卡片仍能看出归属。→ **scribe3 落地**:伏笔分类(列表/详情)与伏笔台账(全局审计)同源不同视角(§2.3);横切视图与树节点共享底层表。([Plottr Docs — Outline Overview](https://docs.plottr.com/article/68-outline-overview)、[Timeline Overview](https://docs.plottr.com/article/54-timeline-overview))

3. **VS Code — Activity Bar(容器入口)+ Sidebar 树 + Editor + Panel 四区分工,TreeItem 懒加载**:Explorer 在 Primary Sidebar 显示文件树,点节点在 Editor 区打开内容;Activity Bar 的每个 item 是一个「View Container」,切换不同侧栏树;Panel(终端/问题/输出)是另一类「跨文件聚合」区,**不混进文件树**。Tree View API 的 TreeItem 只给 label/icon,内容点开才加载。→ **scribe3 落地**:树搬「身份 + 角标」、详情懒加载(§3.2);横切视图类比 Panel,不进树(§2.1)。([VS Code — UX Guidelines · Sidebars](https://code.visualstudio.com/api/ux-guidelines/sidebars)、[Tree View API](https://code.visualstudio.com/api/extension-guides/tree-view))

4. **World Anvil — Content Tree 装异构文章,Maps/Timelines 是独立侧栏入口而非树节点**:Content Tree 可把**任意类型文章**(角色/地点/物种/魔法系统/历史事件/组织)放进一棵自定义层级树;而 Maps、Timelines 是导航侧栏里**独立的入口**,不当成树节点。印证「有详情的实体进树、聚合视图另设入口」的混合范式,以及「异构节点统一抽象」的可行性。→ **scribe3 落地**:素材支把角色/势力/物件/术语/规则等异构记录统一为 TreeNode;图谱/时间线另设入口(§2.1、§3.2)。([World Anvil — Content Trees](https://blog.worldanvil.com/worldanvil/tutorials/content-trees-to-organize-your-worldbuilding/)、[Campfire vs World Anvil 对比](https://kindlepreneur.com/campfire-vs-world-anvil/))

5. **Notion / Obsidian — 侧栏即导航主轴,选节点→主面板加载,保留路径**:Notion 左侧栏把整个工作区的页面/子页面层级化,点条目主区加载该页;顶栏面包屑保留来路便于回退。Obsidian 文件树 + 面板同理(树选文件、面板显内容)。→ **scribe3 落地**:`sel` 单一真相源驱动 DetailPane,选中态/展开态持久化、刷新恢复(§4.3)。([Notion — Navigate with the sidebar](https://www.notion.com/help/navigate-with-the-sidebar))

6. **中文网文工具(橙瓜码字/番茄作家助手)— 「卷 + 章 + 大纲」是中文长篇标配骨架**:网文动辄数百章,无「卷」层级无法管理。印证手稿支必须三层(卷→章→场景),不能是扁平章列表。(承 01 §2.1 出处)

> **本地化差异点(写进文档以提醒实现者)**:Scrivener / World Anvil 的「研究素材」是**自由文档/图片/PDF**(任意富文本);scribe3 的「素材支」是**结构化库记录**(角色/势力/物件…都是带固定字段的记录,见 `CodexView` 的 `fieldMap`)。因此素材叶点击 →**结构化详情卡**(字段表 + 私密锁 + 弧光/关系子表),**不是文档编辑器**。这是 scribe3 把 Binder 模型本地化的关键取舍(硬约束⑤)。

## 附 B · 关键代码锚点速查

| 关注点 | 位置 |
|---|---|
| 顶层视图编排(if/else 切 5 视图) | `scribe3/web/src/App.jsx:39–43` |
| 视图清单 / 顶栏 tab | `scribe3/web/src/AppRail.jsx:3`、`:26` |
| Shell + Rail/Resizer/宽度持久化(树可复用) | `scribe3/web/src/shell.jsx:5`(useNumPref)、`:32`(Resizer)、`:51`(Shell) |
| 写作台(章=DetailPane 渲染器) | `scribe3/web/src/WriteLayout.jsx:26`、扁平章导航 `:208`/`:355` |
| 设定库 11 分类 / 详情卡 / reload 多端点拼装 | `scribe3/web/src/views/CodexView.jsx:8`(TABS)、`:380`(DetailView)、`:545`(reload) |
| 图谱(横切,变 view mode) | `scribe3/web/src/views/AtlasView.jsx:96`、`api.graph` |
| 仪表盘(横切,变 view mode) | `scribe3/web/src/views/InsightView.jsx:18`、`api.quality` |
| 手稿树后端契约(本文手稿支复用) | `docs/系统文档/作者工具/01-大纲与卷章树.md` §3.2 `GET /outline` |
| 章标签格式化(树 label 复用) | `scribe3/web/src/chapterLabel.js` |
| api 客户端(加 projectTree) | `scribe3/web/src/api.js` |

## 出处

- [Literature & Latte — Integrating Binder, Corkboard, Outliner](https://www.literatureandlatte.com/blog/integrating-scriveners-binder-corkboard-and-outliner)
- [Literature & Latte — Organize Your Project with the Corkboard](https://www.literatureandlatte.com/blog/organize-your-scrivener-project-with-the-corkboard)
- [Plottr Docs — Outline Overview](https://docs.plottr.com/article/68-outline-overview) · [Plottr Docs — Timeline Overview](https://docs.plottr.com/article/54-timeline-overview)
- [VS Code — UX Guidelines · Sidebars](https://code.visualstudio.com/api/ux-guidelines/sidebars) · [VS Code — Tree View API](https://code.visualstudio.com/api/extension-guides/tree-view)
- [World Anvil — Content Trees to Organize your Worldbuilding](https://blog.worldanvil.com/worldanvil/tutorials/content-trees-to-organize-your-worldbuilding/) · [Kindlepreneur — Campfire vs World Anvil](https://kindlepreneur.com/campfire-vs-world-anvil/)
- [Notion — Navigate with the sidebar](https://www.notion.com/help/navigate-with-the-sidebar)
- [橙瓜码字官网](https://www.chenggua.com/) · [番茄作家助手](https://www.32r.com/app/122865.html)(承 01)
