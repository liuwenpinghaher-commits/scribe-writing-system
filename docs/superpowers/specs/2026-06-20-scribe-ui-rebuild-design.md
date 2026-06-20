# Scribe 前端视觉彻底重构 · 设计 Spec

**日期**:2026-06-20
**范围**:仅前端视觉层与组件体系。不改后端、不改数据流、不改 72 个 REST 接口契约。
**目标**:把"工程师 UI(散乱 inline style、扁平白卡、灰字、死白)"重做成一套真正的 design system,达到 Linear/iA Writer 级别的成品观感。

## 1. 背景与根因

前几轮重构都在调信息架构(谁放左/中/右)与换 token(字体/图标/端口),从未建立视觉设计系统。"low / 按钮错位 / 交互乱"的根因有三:

1. **无视觉系统**:颜色/间距/字号硬编码、无层次与密度节奏,全是白卡叠白底、灰字配白。
2. **inline style 散乱**:每个元素手摆 `style={{…}}`,无统一组件原语 → 高度/对齐/间距/交互态不一致。
3. **死白**:无空状态设计与密度控制,界面显得空旷廉价。

**关键反思**:手搓 CSS 本身就是 4 次"low"的原因。再手搓原语,质量仍赌在 CSS 手艺上。故本轮改用专业组件库托底。

结论:**结构保留(三栏 + 中栏双模已正确),用 shadcn/ui 重做视觉层。**

## 2. 已锁定的方向(用户确认)

- **组件地基**:**shadcn/ui + Tailwind**(组件源码 copy 进仓库;主题走 CSS 变量)
- **外壳 / 密度**:Linear 路线(发丝线 + 微阴影 + 紧凑密度 + 克制强调)
- **正文 / 阅读**:衬线(Source Serif 4 + 思源宋),用于章节正文、diff、对话气泡、设定名
- **配色基底**:Notion 暖灰中性
- **强调色**:黛绿 Sage `#3f6b58`
- **主题**:浅色优先(保留深色变量结构,本轮只精修浅色)

## 3. 接入(一次性脚手架)

Vite + React + TS 现状:无 Tailwind、无 path alias、已有 `@types/node`。

1. **Tailwind v4**:`npm i -D tailwindcss @tailwindcss/vite`,在 `vite.config.ts` 加 `@tailwindcss/vite` 插件;`index.css` 顶部 `@import "tailwindcss"`。
2. **Path alias**:`tsconfig.json` + `tsconfig.app.json` 加 `"paths": { "@/*": ["./src/*"] }`;`vite.config.ts` 加 `resolve.alias` `@ → /src`。
3. **shadcn 初始化**:`npx shadcn@latest init`(选 New York 风格、基色 neutral、CSS 变量主题)生成 `components.json` + `src/lib/utils.ts`(`cn()`)。
4. 按需 `npx shadcn@latest add <component>`(见 §5),组件落在 `src/components/ui/`。
5. **零黑盒**:shadcn 组件是源码,可改;依赖仅新增 `tailwindcss` + Radix 基元 + `class-variance-authority`/`clsx`/`tailwind-merge`(shadcn 标配)。

## 4. 主题令牌(shadcn CSS 变量)

用 shadcn 的变量约定承载我们的暖灰 + 黛绿,组件自动套用。`src/index.css` 的 `:root`:

| shadcn 变量 | 取值(浅色) | 含义 |
|---|---|---|
| `--background` | `#f6f5f2` | app 暖灰底 |
| `--foreground` | `#37352f` | 墨色主文字 |
| `--card` | `#fffefb` | 卡/中栏面板 |
| `--muted` | `#f1efe9` | 次级面板/底纹 |
| `--muted-foreground` | `#7c7a73` | 次级文字 |
| `--border` / `--input` | `#e2ded4` | 暖灰发丝线 |
| `--primary` | `#3f6b58` | **黛绿强调** |
| `--primary-foreground` | `#ffffff` | 强调反白 |
| `--accent` / `--accent-foreground` | `#e8efe9` / `#3f6b58` | 浅黛绿底/选中态 |
| `--ring` | `#3f6b58` | focus 环 |
| `--destructive` | `#b4503f` | 砖红 |
| `--radius` | `0.6rem` | 圆角基准(派生 sm/md/lg) |

补充自定义(Tailwind `theme.extend` 映射):
- `--font-ui` = Inter + 思源黑;`--font-prose` = Source Serif 4 + 思源宋 → Tailwind `font-prose` 工具类
- 语义:`--warn` `#b9893f`、`--ok` `#4f7a5b`(及对应浅底)
- 字阶沿用 Tailwind 默认(text-xs…2xl 已是克制阶);间距用 Tailwind 4/8px 体系
- 深色 `:root.dark` 保留键位,本轮不精修

## 5. 组件清单(shadcn 现成 + 少量定制)

**shadcn 现成原语(`add`)**,取代散落 inline style:
`button` · `card` · `tabs` · `dialog` · `input` · `textarea` · `badge` · `tooltip` · `scroll-area` · `separator` · `sonner`(toast)· `dropdown-menu`

→ 直接解决:按钮高度/对齐/交互态(hover/active/disabled/focus)不一致、间距随机。`Toast` 用 sonner 替换现有自写 ToastProvider。

**定制(用 Tailwind + shadcn 基元拼,工作台特有)**:
- `Segmented`(中栏 正文｜对话)——基于 Tabs 或自定义 toggle
- `Empty`(统一空状态:图标 + 文案 + 操作)——治死白
- `NorthStarBar`、三栏 `Workspace` 布局、`Conversation` 流、`Editor`、`Inspector` —— 业务组件,用上述原语 + Tailwind 排版

## 6. 版式与布局(结构不变,重做皮)

三栏 + 中栏双模保留,用新体系重排:

- **左 Navigator**:Scribe 字标 + 书切换(dropdown-menu)· 大纲树(发丝线、活动项浅黛绿底、状态点)· 想象页脚
- **中 Center**:北极星条(黛绿左条,sticky)→ 正文｜对话 Segmented → 内容
  - 正文模式:编辑器(`font-prose` 衬线、16px、行宽 ≤72ch)
  - 对话模式:`Conversation`(主编札记 Card → 决策卡差异矩阵 → 气泡流(衬线)→ 置底输入 → 历史议题)
- **右 Inspector**:Tabs(设定圣经/伏笔/一致性/素材/脉络/记忆)+ 设定 Card(名用衬线)+ 关系图行
- **全局**:`prefers-reduced-motion` 降级 · focus-visible 黛绿环(shadcn `--ring`)· 触达 ≥44px · 文本对比 ≥ AA;图标统一 Lucide

## 7. 工程做法

1. 脚手架(§3)一次到位,`npm run build` 验证空跑绿。
2. 逐组件迁移:把 inline style 换成 shadcn 组件 + Tailwind 工具类。一次一个文件,改完即 `npm run build`:
   `Library → Navigator → Center/NorthStar → Conversation → Editor → Right/Panels → App`。
3. **不动**:`api.ts` 接口、后端、数据流、路由、SSE、流式、diff、SegmentNode 逻辑(仅换其外层样式)。
4. 收尾:删除旧 `index.css` 中被 Tailwind/shadcn 取代的硬编码样式;ToastProvider → sonner。
5. 修瞬时「作品不存在」:`useData` 加一次自动重试(404/网络抖动)+ 友好兜底 + 重试。

## 8. 验证

- `npm run build`(tsc -b + vite)必须绿。
- 浏览器逐栏自审:间距是否 8px 节奏、卡是否发丝线 + 微阴影、强调色是否黛绿、正文是否衬线、空状态是否不再死白、四交互态可见。
- 375 / 768 / 1024 / 1440 断点不破版。

## 9. 非目标(YAGNI)

- 不做深色精修(浅色优先)。
- 不做新功能 / 不改接口。
- 不引入 shadcn 之外的 UI 框架;不上动画库(沿用 Tailwind transition 150–300ms)。
- 不做整套图表库(脉络/质量沿用现有轻量渲染)。
