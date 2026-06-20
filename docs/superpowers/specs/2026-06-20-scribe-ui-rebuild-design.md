# Scribe 前端视觉彻底重构 · 设计 Spec(成品级)

**日期**:2026-06-20
**范围**:前端视觉层、组件体系、数据可视化、动效、规模化。不改后端、不改数据流、不改 72 个 REST 接口契约。
**目标**:把"工程师 UI"重做成**面向完整产品(百万字小说 / 大量实体 / 随时间演化)**的设计系统,达到 Linear / iA Writer 级成品观感。

## 1. 背景与根因

前几轮重构只调信息架构与换 token,从未建立视觉系统;且**一直为"当下数据稀疏"做优化,而非为完整产品设计**。"low / 按钮错位 / 交互乱"的根因:

1. **无视觉系统**:颜色/间距/字号硬编码,白卡叠白底、灰字配白。
2. **inline style 散乱**:无组件原语 → 高度/对齐/间距/交互态不一致。
3. **死白 + 短视**:无空状态、无密度控制;数据面只剩裸数字、关系只剩文字列表——没按"成品会有大量数据"设计。

结论:**结构保留(三栏 + 中栏双模已正确),用 shadcn/ui 重做视觉层,并按完整产品补足数据可视化 / 动效 / 规模化。**

## 2. 已锁定的方向(用户确认)

- **组件地基**:**shadcn/ui + Tailwind**(组件源码入仓库;主题走 CSS 变量)
- **外壳 / 密度**:Linear(发丝线 + 微阴影 + 紧凑密度 + 克制强调)
- **正文 / 阅读**:衬线(Source Serif 4 + 思源宋)
- **配色基底**:Notion 暖灰中性;**强调色**:黛绿 Sage `#3f6b58`;**主题**:浅色优先
- **数据可视化**:shadcn `chart`(Recharts)做趋势/分布;**React Flow** 做关系网络
- **动效**:**Framer Motion**(targeted,尊重 reduced-motion)
- **规模化**:虚拟化 + 密度/溢出策略,从一开始为百万字设计

## 3. 接入(一次性脚手架)

Vite + React + TS;无 Tailwind、无 path alias、已有 `@types/node`。

1. **Tailwind v4**:`npm i -D tailwindcss @tailwindcss/vite`;`vite.config.ts` 加插件;`index.css` 顶部 `@import "tailwindcss"`。
2. **Path alias** `@/*` → `./src/*`:`tsconfig.json` + `tsconfig.app.json` + `vite.config.ts` resolve.alias。
3. **shadcn init**:`npx shadcn@latest init`(New York 风格、neutral 基色、CSS 变量主题)→ `components.json` + `src/lib/utils.ts`(`cn`)。
4. **依赖**(都是各自领域事实标准,贴合 shadcn):
   - shadcn 标配:Radix 基元 + `class-variance-authority` + `clsx` + `tailwind-merge`
   - `recharts`(shadcn `chart` 底层)
   - `@xyflow/react`(React Flow,关系网络)
   - `framer-motion`(动效)

## 4. 主题令牌(shadcn CSS 变量)

`src/index.css` 的 `:root` 用 shadcn 变量约定承载暖灰 + 黛绿:

| shadcn 变量 | 取值(浅色) | 含义 |
|---|---|---|
| `--background` | `#f6f5f2` | app 暖灰底 |
| `--foreground` | `#37352f` | 墨色主文字 |
| `--card` | `#fffefb` | 卡/中栏面板 |
| `--muted` / `--muted-foreground` | `#f1efe9` / `#7c7a73` | 次级面/次文字 |
| `--border` / `--input` | `#e2ded4` | 暖灰发丝线 |
| `--primary` / `--primary-foreground` | `#3f6b58` / `#fff` | **黛绿强调** |
| `--accent` / `--accent-foreground` | `#e8efe9` / `#3f6b58` | 浅黛绿底/选中态 |
| `--ring` | `#3f6b58` | focus 环 |
| `--destructive` | `#b4503f` | 砖红 |
| `--radius` | `0.6rem` | 圆角基准 |

补充(Tailwind `theme.extend`):`--font-ui`(Inter+思源黑)、`--font-prose`(Source Serif 4+思源宋,→ `font-prose`)、`--warn` `#b9893f`、`--ok` `#4f7a5b`、图表色板(黛绿主 + 暖中性多色,见 §6)。深色 `:root.dark` 保留键位,本轮不精修。

## 5. 组件清单(shadcn 现成 + 定制)

**shadcn 现成原语**(`add`):`button` `card` `tabs` `dialog` `input` `textarea` `badge` `tooltip` `scroll-area` `separator` `sonner`(toast)`dropdown-menu` `chart`。→ 统一交互态(hover/active/disabled/focus 环)、间距、高度。ToastProvider → sonner。

**定制**(Tailwind + 基元拼):`Segmented`(正文｜对话)、`Empty`(统一空状态,治死白)、`NorthStarBar`、三栏 `Workspace`、`Conversation` 流、`Editor`、`Inspector`。

## 6. 数据可视化(成品级)

为"成品会有大量数据"设计,数据少时优雅降级、数据多时不崩。

- **脉络/质量计分卡 → 仪表盘**(shadcn `chart` / Recharts,主题走 CSS 变量):
  - 质量随章**趋势**(area/line):AI腔密度、一致性分、字数累计、成本随时间
  - 每章 AI腔密度**分布**(bar)、最弱章**排行**(横向 bar,可跳章)
  - 一致性分 / 伏笔回收率 **径向进度**(radial)
  - 全部:图例、tooltip、空状态、loading skeleton、`prefers-reduced-motion` 时静态、AA 对比、响应式
- **实体关系图 → 网络图**(React Flow):节点=实体,边=关系标签;支持按章过滤(`upto`)、拖拽、缩放、聚焦;数十实体可读。取代现文字列表。
- **角色状态轨迹 / 时间线 → 横向时间线**:按 `chapter_seq` 铺开的事件/状态轨迹(自定义轻组件或 Recharts scatter)。

## 7. 动效(Framer Motion · targeted)

只在质感关键处用,统一时长/缓动,全程 `useReducedMotion` 降级:
- 模态/抽屉/sheet:spring 弹入弹出(`AnimatePresence`)
- 中栏 正文↔对话:方向性过渡 / crossfade
- 卡片 / 消息 / 札记入场:fade + 上移,列表 **stagger**(30–50ms)
- AI 流式:节奏感光标/渐显
- 退出快于进入(~60–70%);不阻塞输入;可中断

## 8. 规模化(百万字 / 大量实体)

- **虚拟化**:大纲树(已用 `@tanstack/react-virtual`,强化)、长列表(素材/札记/线程/记忆)、对话流
- **分页**:接口已支持 `?cursor=&limit=`(章节/素材/时间线),前端接游标分页 + 触底加载
- **密度与溢出**:统一密度档;长文本 line-clamp + tooltip 全文;数字 tabular-nums
- **大纲树**:卷/章折叠、状态点、⚠ 角标按章聚合,百章可用

## 9. 版式与布局(结构不变,重做皮)

三栏 + 中栏双模保留:
- **左 Navigator**:Scribe 字标 + 书切换(dropdown)· 大纲树(发丝线、活动项浅黛绿底)· 想象页脚
- **中 Center**:北极星条(黛绿左条,sticky)→ 正文｜对话 Segmented →(正文:衬线编辑器 ≤72ch / 对话:`Conversation` 流)
- **右 Inspector**:Tabs(设定圣经/伏笔/一致性/素材/脉络/记忆)+ 设定卡(名衬线)+ 关系图入口
- **全局**:reduced-motion 降级 · focus-visible 黛绿环 · 触达 ≥44px · 对比 ≥ AA · 图标统一 Lucide

## 10. 工程做法

1. 脚手架(§3)一次到位,`npm run build` 空跑绿。
2. 逐文件迁移 inline style → shadcn + Tailwind:`Library → Navigator → Center/NorthStar → Conversation → Editor → Right/Panels(含图表/关系图)→ App`,每文件改完即 build。
3. **不动**:`api.ts` 接口、后端、数据流、SSE、流式、diff、SegmentNode 逻辑(仅换外层样式)。
4. 收尾:删旧 `index.css` 硬编码;ToastProvider → sonner;`useData` 加一次自动重试(修瞬时「作品不存在」)。

## 11. 验证

- `npm run build`(tsc -b + vite)绿。
- 逐栏自审:8px 间距节奏、发丝线 + 微阴影、黛绿强调、正文衬线、空状态不死白、四交互态、图表/关系图主题一致且响应式、reduced-motion 下静态可读。
- 数据压力:造 100+ 章 / 多实体,验证虚拟化、关系图、图表不崩。
- 375 / 768 / 1024 / 1440 断点不破版。

## 12. 非目标(YAGNI)

- 不做深色精修(浅色优先;仅保留变量键位)。
- 不做新后端功能 / 不改接口契约。
- 不引入 shadcn 之外的 UI 组件框架。
- 不自研图引擎(用 React Flow);不上重型 BI(用 shadcn chart 即够)。
