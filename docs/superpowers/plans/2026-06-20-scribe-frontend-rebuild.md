# Scribe 前端产品级重构 Implementation Plan(Phase 0–1 + 路线图)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 shadcn/ui + Tailwind 地基上,把 Scribe 前端重做成产品级:5 顶层视图 + 暖灰/黛绿/衬线设计系统 + 复用最大化。本计划详写 **Phase 0(脚手架)+ Phase 1(地基:令牌/原语/AppRail/5视图骨架/写作台换皮)**;Phase 2–3 列路线图,地基落地后再细化。

**Architecture:** Vite + React + TS。引入 Tailwind v4 + shadcn/ui(组件入仓库,主题 CSS 变量)。保留现有数据层(`api.ts`/SSE/流式/diff/SegmentNode/Tiptap),只重做视觉与顶层 IA。前端验证 = `npm run build` 绿 + 浏览器逐栏视觉自审(无单元 TDD;组件正确性靠 build + 类型 + 视觉)。

**Tech Stack:** Vite、React、TypeScript、Tailwind v4(`@tailwindcss/vite`)、shadcn/ui(Radix + cva + clsx + tailwind-merge)、lucide-react。后续:recharts(shadcn chart)、@xyflow/react + elkjs、framer-motion。

---

### 前置(执行前必做)

- [ ] **暂存旧前端 WIP**:`git stash push -m "pre-rebuild dual-mode WIP" web-app/src/` 后确认 `git status` 工作树干净(WIP 可后续 `git stash list`/`pop` 找回)。
- 工作目录:`<repo-root>/scribe/web-app`
- 真源参考(不要照搬旧 UI,按 spec 重做):[前端 spec](../specs/2026-06-20-scribe-ui-rebuild-design.md)
- 设计令牌真值见 spec §5;后端新字段(关系 typed / quality history)已就位,可直接调。

---

## Phase 0 · 脚手架

### Task 0.1:接入 Tailwind v4 + path alias

**Files:**
- Modify: `web-app/package.json`(deps)
- Modify: `web-app/vite.config.ts`(plugin + alias)
- Modify: `web-app/tsconfig.json` 和 `web-app/tsconfig.app.json`(paths)
- Modify: `web-app/src/index.css`(顶部 `@import "tailwindcss"`)

- [ ] **Step 1:装依赖**

Run: `npm i -D tailwindcss @tailwindcss/vite` 与 `npm i tailwindcss-animate`(shadcn 动画基)。
Expected: 安装成功。

- [ ] **Step 2:vite.config.ts 加插件 + alias**

```ts
import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: { port: 3310, strictPort: true },
  preview: { port: 3310, strictPort: true },
})
```

- [ ] **Step 3:tsconfig 加 paths**

`tsconfig.json` 顶层 `compilerOptions` 增(若无该键则新建):
```json
"baseUrl": ".",
"paths": { "@/*": ["./src/*"] }
```
`tsconfig.app.json` 同样加 `baseUrl` + `paths`。

- [ ] **Step 4:index.css 顶部引入 Tailwind**

把现有字体 `@import url(...)` 保留在最上,其后加一行:
```css
@import "tailwindcss";
```

- [ ] **Step 5:验证 build**

Run: `npm run build`
Expected: tsc + vite 通过(此时 Tailwind 类可用,旧样式仍在)。

- [ ] **Step 6:提交**

```bash
git add web-app/package.json web-app/package-lock.json web-app/vite.config.ts web-app/tsconfig*.json web-app/src/index.css
git commit -m "chore(web): 接入 Tailwind v4 + @ path alias"
```

### Task 0.2:shadcn 初始化 + 主题令牌(暖灰/黛绿,浅+深)

**Files:**
- Create: `web-app/components.json`、`web-app/src/lib/utils.ts`(经 shadcn init)
- Modify: `web-app/src/index.css`(注入 shadcn CSS 变量主题)

- [ ] **Step 1:shadcn init**

Run: `npx shadcn@latest init`（选 New York 风格、base color neutral、CSS variables: yes、path alias 用 `@`）。
Expected: 生成 `components.json` + `src/lib/utils.ts`(含 `cn`)+ 在 index.css 注入 `:root`/`.dark` 变量与 `@theme`。

- [ ] **Step 2:把主题改成暖灰 + 黛绿(spec §5)**

在 index.css 的 `:root` 覆盖为(用 shadcn 变量名;OKLCH 或 hex 均可,这里用 hex):
```css
:root {
  --background:#f6f5f2; --foreground:#37352f;
  --card:#fffefb; --card-foreground:#37352f;
  --popover:#fffefb; --popover-foreground:#37352f;
  --primary:#3f6b58; --primary-foreground:#ffffff;
  --secondary:#f1efe9; --secondary-foreground:#37352f;
  --muted:#f1efe9; --muted-foreground:#7c7a73;
  --accent:#e8efe9; --accent-foreground:#3f6b58;
  --destructive:#b4503f; --destructive-foreground:#ffffff;
  --border:#e2ded4; --input:#e2ded4; --ring:#3f6b58;
  --radius:0.6rem;
}
.dark {
  --background:#1b1a17; --foreground:#ece8df;
  --card:#24221d; --card-foreground:#ece8df;
  --popover:#24221d; --popover-foreground:#ece8df;
  --primary:#6fa087; --primary-foreground:#10130f;
  --secondary:#2c2a24; --secondary-foreground:#ece8df;
  --muted:#2c2a24; --muted-foreground:#a39f93;
  --accent:#243029; --accent-foreground:#9cc4ad;
  --destructive:#d2715f; --destructive-foreground:#15100e;
  --border:#38352d; --input:#38352d; --ring:#6fa087;
}
```
并在 `@theme inline`(shadcn 注入的)里补两个字体族:`--font-ui` 与 `--font-prose`(值见 spec §5),映射到 Tailwind `font-ui`/`font-prose`。`body` 用 `font-ui`。

- [ ] **Step 3:验证 build + 主题切换**

Run: `npm run build`;并本地 `npm run dev` 切换 `<html class="dark">` 目测两套主题对比度。
Expected: build 绿;浅/深都协调。

- [ ] **Step 4:提交**

```bash
git add web-app/components.json web-app/src/lib/utils.ts web-app/src/index.css
git commit -m "feat(web): shadcn 初始化 + 暖灰/黛绿浅深双主题"
```

### Task 0.3:装核心 shadcn 原语

- [ ] **Step 1:add 组件**

Run: `npx shadcn@latest add button card tabs dialog sheet input textarea select badge tooltip scroll-area separator sonner dropdown-menu command skeleton`
Expected: 落在 `src/components/ui/`;build 仍绿(`npm run build`)。

- [ ] **Step 2:挂 Toaster**

在 `src/main.tsx` 渲染树外层加 `<Toaster />`(sonner)。

- [ ] **Step 3:提交**

```bash
git add web-app/src/components/ui web-app/src/main.tsx
git commit -m "feat(web): 装 shadcn 核心原语 + sonner Toaster"
```

---

## Phase 1 · 地基(AppRail + 5 视图骨架 + 写作台换皮)

> 说明:Phase 1 把"结构骨架 + 写作台"立起来并换皮;关系图谱/仪表盘/设定库/记忆 4 视图在 Phase 2 细化(先放占位空状态)。

### Task 1.1:视图路由 + 类型

**Files:**
- Create: `web-app/src/views.ts`(视图枚举 + 标签 + 图标名)
- Modify: `web-app/src/App.tsx`(顶层按 view 切换;深链 `#/work/<id>/<view>`)

- [ ] **Step 1:定义视图**

```ts
// src/views.ts
import { PenLine, Network, BarChart3, Library, Brain } from "lucide-react"
export const VIEWS = [
  { key: "write",   label: "写作台", icon: PenLine },
  { key: "atlas",   label: "关系图谱", icon: Network },
  { key: "insight", label: "质量仪表盘", icon: BarChart3 },
  { key: "codex",   label: "设定库", icon: Library },
  { key: "agent",   label: "记忆与技能", icon: Brain },
] as const
export type ViewKey = typeof VIEWS[number]["key"]
```

- [ ] **Step 2:App 顶层按 view 渲染 + 深链**

App 维护 `view` state(默认 `write`),hash 路由扩展为 `#/work/<id>/<view>[/ch/<seq>]`,解析/写回。各视图渲染先用占位(下个 Task 接 AppRail + 写作台)。

- [ ] **Step 3:验证**

Run: `npm run build` → 绿;`npm run dev` 改 hash 切 view 不报错。

- [ ] **Step 4:提交**

```bash
git add web-app/src/views.ts web-app/src/App.tsx
git commit -m "feat(web): 顶层 5 视图路由 + 深链"
```

### Task 1.2:AppRail(用 shadcn sidebar)

**Files:**
- Add: `npx shadcn@latest add sidebar`
- Create: `web-app/src/AppRail.tsx`
- Modify: `web-app/src/App.tsx`(挂 AppRail + 书切换)

- [ ] **Step 1:add sidebar 并实现 AppRail**

`AppRail` 用 shadcn `sidebar`:顶部书切换(dropdown-menu 列 works),中部 5 视图导航项(图标 + 标签,active 高亮 `bg-accent text-accent-foreground`),底部主题切换(Sun/Moon)。props:`works`、`current`、`view`、`onView`、`onSelectWork`、`theme`、`onTheme`。

- [ ] **Step 2:接进 App,替换旧左栏 Library 容器**

- [ ] **Step 3:验证**

Run: `npm run build` → 绿;dev 目测:Rail 切视图、切书、切主题可用,active 态清晰。

- [ ] **Step 4:提交**

```bash
git add web-app/src/AppRail.tsx web-app/src/App.tsx web-app/src/components/ui/sidebar.tsx
git commit -m "feat(web): App Rail(shadcn sidebar)5 视图 + 书切换 + 主题"
```

### Task 1.3:写作台三栏 + 换皮(Navigator/Center/Inspector)

**Files:**
- Modify: `web-app/src/Navigator.tsx`、`Center.tsx`、`Right.tsx`、`Editor.tsx`、`Conversation.tsx`(若 stash 后不存在则新建)
- Create: `web-app/src/components/Empty.tsx`、`Segmented.tsx`、`StateBoundary.tsx`(业务定制)

- [ ] **Step 1:定制 3 件套**

`Empty`(图标 + 文案 + 可选 CTA)、`Segmented`(正文｜对话,基于 button 组,active `bg-card text-primary shadow-sm`)、`StateBoundary`(loading→Skeleton / error→重试 / empty→Empty)。

- [ ] **Step 2:写作台三栏用 Tailwind 重排**

左 Navigator(大纲树:发丝线 `border-border`、活动项 `bg-accent`、状态点)、中 Center(NorthStarBar 黛绿左条 + Segmented + 正文衬线 `font-prose`/对话流)、右 Inspector(shadcn Tabs:设定速查/伏笔/一致性)。所有卡片换 shadcn `Card`;按钮换 shadcn `Button`;输入换 `Input`/`Textarea`。删除对应 inline style。

- [ ] **Step 3:验证(逐栏视觉自审)**

Run: `npm run build` → 绿。dev 目测对照 spec:8px 间距、发丝线+微阴影、黛绿强调、正文衬线、空状态不死白、四交互态。

- [ ] **Step 4:提交**

```bash
git add web-app/src
git commit -m "feat(web): 写作台三栏 shadcn 换皮(Navigator/Center/Inspector + Empty/Segmented/StateBoundary)"
```

---

## 路线图(Phase 2–3,地基落地后细化)

**Phase 2 · 四视图(各自整屏)**
- 关系图谱:`@xyflow/react` + `elkjs` 自动布局;节点按 `src_type` 上色、边按 `relation_category` 分类、`weight` 控粗细;按章过滤(`upto`)。数据用后端新 typed 字段。
- 质量仪表盘:shadcn `chart`(recharts);趋势(`GET /quality/history`)、每章分布、最弱章排行、径向分。
- 设定库:shadcn Data Table(TanStack)管理角色/设定/伏笔/素材 + 详情编辑。
- 记忆与技能:跨会话记忆 + 技能审批门(复用现有 Panels 逻辑,换 shadcn 皮)。

**Phase 3 · 横切打磨**
- 状态系统全覆盖(StateBoundary 落到每个异步面)+ `useData` 自动重试。
- 无障碍(landmark/aria-live/焦点管理/skip-link)。
- 性能(视图级 code-split:recharts/React Flow/Tiptap 懒加载;首屏 gz<200KB)。
- 动效(framer-motion:视图过渡/模态 spring/列表 stagger,reduced-motion 降级)。
- 移动端(Rail→底部 Tab;写作台抽屉化)。
- 文案体系(`src/labels.ts`,枚举全中文)。
- onboarding(空库/无北极星引导)。
- 验收:对照 spec §18 硬清单逐项勾选。

> Phase 2 每个视图、Phase 3 每个横切项,在 Phase 1 验收通过后,各自补一份细化的 bite-sized 任务清单(同本文件 Phase 0/1 粒度)再执行。

---

## Phase 2 · 四视图(细化)

> 前置:`npm run dev` 起 3310;后端 3320 已含新数据端点。每视图独立文件,装配进 App 的 view 分支。每 Task 后 `npm run build` 绿 + 目测。

### Task 2.0:api.ts 补后端新能力
- `Relation` 类型增 `src_type?/dst_type?/relation_category?/weight?/directed?`。
- 增 `QualitySnapshot` 类型(words/slop_density/consistency_score/foreshadow_payoff/vocab_richness/repetition_rate/cost_usd/created_at/scope/chapter_seq)。
- 增方法:`qualityHistory(w, scope="global") → GET /works/{w}/quality/history?scope=`;`analyzeWork(w) → POST /works/{w}/analyze`。
- commit:`feat(web): api 补 quality/history + analyze + 关系 typed 字段`

### Task 2.1:关系图谱视图(`src/views/AtlasView.tsx`)
- 装 `@xyflow/react elkjs`。
- 用 React Flow:`api.relations(w)` → 节点=实体(按 `src_type/dst_type` 上色:角色/地点/阵营/物品…)、边=关系(label=relation,粗细∝`weight`,有向看 `directed`)。
- elkjs 自动布局(force/layered),社区 `useAutoLayout` 模式。
- 顶部:按章过滤(slider/Select,`upto`)。空数据→`<Empty>` + "分析全书"按钮(`api.analyzeWork`,带 loading)。
- 装进 App 的 `atlas` 视图分支(整屏)。commit。

### Task 2.2:质量仪表盘视图(`src/views/InsightView.tsx`)
- `npx shadcn@latest add chart`(装 recharts)。
- 卡片网格:① 质量趋势(`api.qualityHistory`,area/line:slop/一致性/字数/成本随时间)② 每章 AI腔分布(bar,`api.quality().weakest_chapters` 或逐章)③ 最弱章排行(横向 bar,点击跳章)④ 一致性/伏笔回收 径向。
- 全部用 shadcn `ChartContainer` + recharts,主题走 CSS 变量;图例/tooltip/`<Empty>`/skeleton。空→"分析全书"。
- 装进 `insight` 视图。commit。

### Task 2.3:设定库视图(`src/views/CodexView.tsx`)
- `npx shadcn@latest add table` + `npm i @tanstack/react-table`。
- shadcn Data Table:Tab(角色/设定/伏笔/素材),可排序/筛选/分页;行点开详情编辑(复用现有 api.characters/settings/foreshadows/materials 的增改)。
- 装进 `codex` 视图。commit。

### Task 2.4:记忆与技能视图(`src/views/AgentView.tsx`)
- 复用现有 `Panels.tsx` 的 `AgentPanel` 逻辑(跨会话记忆按命名空间 + 技能审批门),整屏布局换 shadcn 皮(左右分栏:记忆列表 / 技能审批)。
- 装进 `agent` 视图。commit。

## Self-Review(规划者自检)

- **Spec 覆盖(Phase 0–1)**:Tailwind+shadcn 接入(spec §4)✓、暖灰/黛绿浅深主题(§5)✓、核心原语 + sidebar/command(§6)✓、5 视图 IA(§3)✓、写作台换皮 + Empty/Segmented/StateBoundary(§6/§9)✓。Phase 2–3 覆盖 §6 数据可视化/§7 动效/§8 规模/§11-16 横切——列为路线图,显式标注"地基后细化"。
- **无占位符**:Phase 0–1 每步有确切命令/代码;Phase 2–3 是声明的路线图(非伪任务),按计划在地基后展开。
- **类型一致**:`ViewKey`/`VIEWS` 在 1.1 定义,AppRail(1.2)、App 复用;`Empty`/`Segmented`/`StateBoundary` 在 1.3 定义并被写作台用。
- **风险**:shadcn init 会改 index.css(可能覆盖字体 import)——Task 0.2 显式要求保留字体 import 并覆盖变量;前端无单元 TDD,验证靠 build + 视觉自审(已在每 Task Step 写明)。
