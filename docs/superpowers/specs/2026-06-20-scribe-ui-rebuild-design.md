# Scribe 前端彻底重构 · 产品级 UX Spec

**日期**:2026-06-20
**范围**:前端整体 UX——顶层信息架构、视觉系统、组件、数据可视化、动效、状态/无障碍/性能/文案/表单/onboarding/移动端、规模化。
**后端**:关系图谱与质量趋势依赖配套后端增强(见 [后端 spec](2026-06-20-scribe-backend-data-enhancement-design.md)):关系丰富化、质量时序表、批量分析入口。除此之外不改后端 / 不破现有 72 个接口契约(增强均为新增字段/端点)。
**目标**:把"工程师 UI"重做成**面向完整产品(百万字小说 / 大量实体 / 随时间演化 / 长期使用)**、达到 Linear / iA Writer 级的成品体验。**整个体验做到成品级,不止"好看"。**

## 1. 根因(为何屡次重构仍差)

1. **无视觉系统**:颜色/间距/字号硬编码,白卡叠白底、灰字配白。
2. **inline style 散乱**:无组件原语 → 高度/对齐/间距/交互态不一致。
3. **为"当下数据稀疏"做优化,而非为成品设计**:数据面只剩裸数字、关系只剩文字列表、所有东西硬塞三栏。
4. **缺产品级体面**:无系统化状态/空/错、无 onboarding、无移动模型、无障碍与性能无预算、文案泄漏英文。

结论:**重做视觉层 + 重构顶层 IA(多视图)+ 补齐全部产品级维度。**

## 2. 已锁定方向(用户逐项确认)

- 地基:**shadcn/ui + Tailwind**(组件入仓库;主题 CSS 变量)
- 外壳:Linear 密度;正文:衬线(Source Serif 4 + 思源宋);配色:Notion 暖灰;强调:黛绿 `#3f6b58`
- **主题:浅 + 深均做到成品级**
- 数据可视化:shadcn `chart`(Recharts)+ **React Flow**;动效:**Framer Motion**(targeted)
- 规模化:虚拟化 + 游标分页 + 密度/溢出
- **顶层 IA:5 个顶层视图 + App 侧栏(放不下就分视图,不硬塞)**

## 3. 顶层信息架构(5 视图)

左侧 **App Rail**(图标 + 标签,折叠/展开)切换 5 个顶层视图。当前书在 Rail 顶部切换。

| 视图 | 内容 | 布局 |
|---|---|---|
| **写作台**(主) | 大纲树 · 编辑器/对话双模 · 轻量速查栏(当前章相关设定/伏笔/一致性) | 三栏 |
| **关系图谱** | React Flow 实体关系网络 + 角色弧光/事件时间线;按章过滤 | 全画布 |
| **质量仪表盘** | 质量/AI腔/伏笔/一致性/字数/成本 趋势·分布·排行 | 网格仪表盘 |
| **设定库** | 角色/设定/伏笔/素材 全量管理(表格/卡网格)+ 详情编辑 | 列表-详情 |
| **记忆与技能** | 跨会话记忆(按命名空间)+ 技能审批门 | 列表-详情 |

写作台保留"正文｜对话"双模;重数据/管理移到各自整屏视图。深链 `#/work/<id>/<view>[/...]`。

## 4. 接入(脚手架)

Vite + React + TS;无 Tailwind/别名,已有 `@types/node`。

1. Tailwind v4:`npm i -D tailwindcss @tailwindcss/vite`;vite 插件;`@import "tailwindcss"`。
2. Path alias `@/*`→`./src/*`(tsconfig ×2 + vite resolve.alias)。
3. `npx shadcn@latest init`(New York / neutral / CSS 变量)。
4. 依赖:shadcn 标配(Radix + cva + clsx + tailwind-merge)、`recharts`、`@xyflow/react`、`framer-motion`。

## 5. 主题令牌(浅 + 深,均成品级)

shadcn 变量约定承载暖灰 + 黛绿。**两套都精修并各自验对比度。**

浅色 `:root`:bg `#f6f5f2` · fg `#37352f` · card `#fffefb` · muted `#f1efe9`/`#7c7a73` · border `#e2ded4` · primary `#3f6b58`/`#fff` · accent `#e8efe9`/`#3f6b58` · ring `#3f6b58` · destructive `#b4503f` · radius `.6rem`。

深色 `.dark`(暖调,非简单反相):bg `#1b1a17` · fg `#ece8df` · card `#24221d` · muted `#2c2a24`/`#a39f93` · border `#38352d` · primary `#6fa087`(提亮保 AA)/`#10130f` · accent `#243029`/`#9cc4ad` · ring `#6fa087`。

补充:`--font-ui`(Inter+思源黑)、`--font-prose`(Source Serif 4+思源宋)、`--warn`/`--ok`、图表色板(黛绿主 + 暖中性多色,浅深各一套)。

## 6. 组件清单

**shadcn 现成**:`button card tabs dialog sheet input textarea select badge tooltip scroll-area separator sonner dropdown-menu chart skeleton`。ToastProvider→sonner。

**定制**:`AppRail`(视图切换)、`Segmented`(正文｜对话)、`Empty`、`StateBoundary`(§7)、`NorthStarBar`、各视图容器。

**交互状态矩阵(硬要求)**:每个交互元件覆盖 default / hover / active / focus-visible / disabled / loading / selected / error(适用者),由 shadcn + token 统一,人工逐一核。

## 7. 状态系统(统一)

`StateBoundary` 包裹每个异步面,四态 + 恢复:
- **loading**:skeleton(贴最终布局,非 spinner)
- **empty**:`Empty`——图标 + 一句话 + 主操作 CTA(治死白;每个空面都要引导)
- **error**:原因 + 恢复(重试/编辑/帮助);`useData` 对 404/网络抖动**自动重试 1 次**再报错(修瞬时「作品不存在」)
- **partial / offline**:局部失败不连坐;离线提示 + 降级

## 8. 数据可视化(成品级)

- **质量仪表盘**(shadcn `chart`/Recharts,主题走变量,懒加载):质量随章趋势(area/line)、每章 AI腔分布(bar)、最弱章排行(可跳章)、一致性/伏笔径向进度、成本随时间。图例/tooltip/空/skeleton/响应式/reduced-motion 静态/AA。
- **关系图谱**(React Flow,懒加载):节点=实体、边=关系;按章过滤、拖拽缩放聚焦;数十实体可读。
- **时间线**:按 `chapter_seq` 的角色状态/事件横向轨迹。

## 9. 动效(Framer Motion · targeted)

关键处用、统一时长缓动、全程 `useReducedMotion` 降级:视图切换方向过渡、模态/sheet spring(`AnimatePresence`)、卡片/消息入场 fade+上移、列表 stagger 30–50ms、AI 流式节奏、退出快于进入、不阻塞输入、可中断。

## 10. 规模化(百万字 / 大量实体)

虚拟化(大纲树/素材/札记/线程/记忆/对话流);游标分页(接口已支持 `?cursor=&limit=`)+ 触底加载;密度档 + line-clamp + tooltip 全文 + tabular-nums;卷/章折叠、⚠ 角标聚合。

## 11. 无障碍(系统化)

landmark/role(每视图 `<main>`/区域 role)、跨栏 Tab 顺序合理、`aria-live` 播报(流式增量节流播报、toast `polite`、表单错误 `assertive`)、模式/视图切换后焦点移到主区、skip-link、focus-visible 黛绿环、触达 ≥44px、对比 ≥AA(浅深各验)、键盘可达一切(含图表 tooltip/关系图节点)。

## 12. 性能预算

- 每个顶层视图 **路由级 code-split**(懒加载);Recharts/React Flow/Tiptap 仅在所属视图加载。
- 首屏(写作台)初始 JS gz **目标 < 200KB**;TTI < 2.5s(本地)。
- 交互/滚动 60fps;输入延迟 < 100ms;高频事件 debounce/throttle。
- 图片/字体 `display:swap` + 预连接;CLS < 0.1(异步区预留高度/skeleton)。

## 13. 文案 / 本地化体系

全中文、零英文泄漏、零占位符;类型/枚举集中映射(如设定 `item`→物品、状态机英文态→中文,见现有 `STATE_LABEL`/`SET_LABEL`,补全);语气一致(主编口吻);数字/日期本地化格式。建立 `src/labels.ts` 统一 copy 与枚举映射。

## 14. 表单 / 内联编辑

可见 label(非仅 placeholder)、必填标记、失焦校验、错误就近 + `aria`、提交 loading→成功/失败、乐观更新 + 失败回滚;长表单/正文自动存草稿(正文已有,北极星/设定补);破坏性操作二次确认 + undo toast。

## 15. 首次使用(Onboarding)

空书库 → 大图零状态 + "建第一本书" 主 CTA;建后引导设北极星(强提示:没北极星 AI 走均值)→ 建第一章 → 提示"让主编写这章 / 与主编对话"。每个视图首次进入有零状态引导,而非空白。

## 16. 移动端 / 响应式

App Rail → 移动底部 Tab(≤5);写作台移动单列:大纲/速查栏为抽屉(sheet),默认进"对话或正文";关系图谱/仪表盘移动简化(更少刻度、横向条);断点 375/768/1024/1440;`min-h-dvh`;无横向滚动;触达友好。

## 17. 工程做法

1. 脚手架(§4)→ build 空跑绿。
2. 顶层 IA 先落:`AppRail` + 视图路由 + 写作台迁移,再逐视图。
3. 逐文件 inline style → shadcn + Tailwind,每文件改完 `npm run build`。
4. **不动** api.ts 接口/后端/数据流/SSE/流式/diff/SegmentNode 逻辑。
5. 收尾:删旧硬编码样式;`labels.ts`;`useData` 自动重试。

## 18. 验收标准(硬清单,可执行)

逐项勾选才算成品级:
- [ ] `npm run build`(tsc -b + vite)绿
- [ ] 浅 + 深双主题:文本对比 ≥AA(各自实测),边框/状态在两主题都可辨
- [ ] 8px 间距节奏、发丝线 + 微阴影、黛绿强调、正文衬线全局一致
- [ ] 每个异步面四态齐(loading skeleton / empty+CTA / error+恢复 / partial)
- [ ] 每个交互元件交互态矩阵齐;无 inline style 残留硬编码
- [ ] 5 视图都有零状态引导;首次使用流程走通
- [ ] 图表/关系图主题一致、响应式、reduced-motion 静态、键盘可达
- [ ] 100+ 章 / 多实体压力下虚拟化/图谱/图表不崩
- [ ] 移动 375 单列可用(抽屉、底部 Tab、无横向滚动)
- [ ] 无英文泄漏 / 占位符;枚举全中文
- [ ] 首屏 JS gz < 200KB;关键视图懒加载
- [ ] 对照 ui-ux-pro-max Pre-Delivery Checklist 全过

## 19. 非目标(YAGNI)

- 后端仅按配套 spec 做 3 处定向增强(关系字段 / 质量时序 / 批量分析),其余不动、不破现有契约。
- 不引入 shadcn 之外的 UI 组件框架;不自研图引擎(用 React Flow);不上重型 BI(shadcn chart 够)。
- 不做协作/多人(单用户本地)。
