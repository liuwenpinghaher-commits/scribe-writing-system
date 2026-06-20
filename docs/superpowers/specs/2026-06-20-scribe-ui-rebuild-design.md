# Scribe 前端视觉彻底重构 · 设计 Spec

**日期**:2026-06-20
**范围**:仅前端视觉层与组件原语。不改后端、不改数据流、不改 72 个 REST 接口契约。
**目标**:把"工程师 UI(散乱 inline style、扁平白卡、灰字、死白)"重做成一套真正的 design system,达到 Linear/iA Writer 级别的成品观感。

## 1. 背景与根因

前几轮重构都在调信息架构(谁放左/中/右)与换 token(字体/图标/端口),从未建立视觉设计系统。"low / 按钮错位 / 交互乱"的根因有三:

1. **无视觉系统**:颜色/间距/字号硬编码、无层次与密度节奏,全是白卡叠白底、灰字配白。
2. **inline style 散乱**:每个元素手摆 `style={{…}}`,无统一组件原语 → 高度/对齐/间距/交互态不一致。
3. **死白**:无空状态设计与密度控制,界面显得空旷廉价。

结论:**结构保留(三栏 + 中栏双模已正确),推倒视觉层重做。**

## 2. 已锁定的视觉语言(用户确认)

- **外壳 / 密度 / 组件**:Linear 路线(发丝线 + 微阴影 + 紧凑密度 + 克制强调)
- **正文 / 阅读**:衬线(Source Serif 4 + 思源宋),用于章节正文、diff、对话气泡、设定名
- **配色基底**:Notion 暖灰中性
- **强调色**:黛绿 Sage `#3f6b58`
- **主题**:浅色优先(保留深色 token 结构,本轮只把浅色做到极致)

## 3. 设计令牌(`theme.css`)

所有视觉常量集中于 `:root`,组件只引用变量。

```
/* 表面 */
--bg:        #f6f5f2;   /* app 暖灰 */
--panel:     #fffefb;   /* 中栏/卡片 */
--panel-2:   #faf9f6;   /* 右栏 */
/* 文字 */
--ink:       #37352f;   /* 主 */
--ink-sub:   #7c7a73;   /* 次 */
--ink-faint: #9c998f;   /* 弱 */
/* 描边 */
--line:      #ebe8e1;
--line-2:    #e2ded4;
/* 强调 黛绿 */
--accent:    #3f6b58;
--accent-bg: #e8efe9;
--accent-ink:#ffffff;
/* 语义 */
--ok:#4f7a5b; --warn:#b9893f; --danger:#b4503f;
--warn-bg:#f6ecd9; --danger-bg:#f5e7e3;
/* 字体 */
--font-ui:    'Inter','Noto Sans SC',system-ui,sans-serif;
--font-prose: 'Source Serif 4','Noto Serif SC',Georgia,'Songti SC',serif;
/* 字阶(6 级) */ 11 / 12 / 13 / 15 / 20 / 28
/* 间距(8px 节奏,强制) */ --s1:4 --s2:8 --s3:12 --s4:16 --s6:24
/* 圆角 */ --r-sm:6 --r:9 --r-lg:13
/* 阴影 */
--sh-sm: 0 1px 2px rgba(40,34,25,.05);
--sh-lg: 0 10px 40px rgba(40,34,25,.12);
/* 密度 */ 行高 27–30px · 卡 padding 10–12px · 控件高 34px
```

深色变体(`:root[data-theme=dark]`)保留键位但本轮不精修。

## 4. 组件原语(`ui.tsx`) — 治本

把散落各处的 inline style 收敛为 8 个原语,**所有页面只拼这些**,不再手写 `style`。

| 原语 | 职责 | 取代 |
|---|---|---|
| `Button` | primary/ghost/danger + busy/disabled,统一高度与交互态 | 现有 Btn + 各处裸 `<button>` |
| `Card` | 面板卡,可选 `accent`/`tone` 左条 | 到处的 `.card` + 内联 borderLeft |
| `Field` | label + input/textarea,统一 34px 高、focus 黛绿环 | 各处 `.field`/裸 input |
| `Segmented` | 中栏「正文｜对话」分段控件 | 现 `.mode-switch` |
| `Tabs` | 右栏 Tab + 计数 badge | 现 `.tabs` |
| `Chip` / `Badge` | 状态/类型标签 | 现 `.badge`/`.dot` + 内联 |
| `Stack` / `Row` | 纵/横布局 + 间距 | 满屏 `style={{display:flex,gap}}` |
| `Empty` | 统一空状态(图标 + 文案 + 可选操作) | 现 `.empty` 死白 |

交互态统一:hover(微亮/底色)、active(scale .98)、disabled(opacity .45)、focus-visible(黛绿 2px 环)。

## 5. 版式与布局(结构不变,重做皮)

三栏 + 中栏双模保留,按新系统重排:

- **左 Navigator**:Scribe 字标 + 书切换 chip · 大纲树(发丝线、活动项黛绿浅底、状态点)· 想象页脚
- **中 Center**:北极星条(黛绿左条,sticky)→ 正文｜对话 Segmented → 内容
  - 正文模式:编辑器(正文衬线、16px、行宽 ≤72ch)
  - 对话模式:`Conversation`(主编札记卡 → 决策卡差异矩阵 → 气泡流(衬线)→ 置底输入 → 历史议题)
- **右 Inspector**:Tabs(设定圣经/伏笔/一致性/素材/脉络/记忆)+ 设定卡(名用衬线)+ 关系图行
- **全局**:`prefers-reduced-motion` 降级 · `:focus-visible` 黛绿环 · 触达 ≥44px · 文本对比 ≥ AA(4.5:1)

图标统一 Lucide 线性(上一轮已基本完成,本轮校全)。

## 6. 工程做法

1. 新增 `src/theme.css`(令牌)与 `src/ui.tsx`(原语);`index.css` 收敛为"仅令牌 + 原语 class",删除散落硬编码。
2. 逐组件把 inline style 换成原语 / class:`App` `Center` `Conversation` `Editor` `Right` `Navigator` `Panels` `Library`。一次一个文件,每个文件改完 `npm run build` 验证。
3. **不动**:`api.ts` 接口、后端、数据流、路由、SSE、流式、diff、SegmentNode。
4. 修瞬时「作品不存在」:`useData` 加一次自动重试(对 404/网络抖动)+ 友好兜底文案 + 重试按钮(已有)。

## 7. 验证

- `npm run build`(tsc -b + vite)必须绿。
- 浏览器逐栏自审,对照本 spec 的令牌:间距是否 8px 节奏、卡是否有发丝线 + 微阴影、强调色是否黛绿、正文是否衬线、空状态是否不再死白。
- 关键交互态(hover/active/disabled/focus)四态可见。
- 375 / 768 / 1024 / 1440 断点不破版。

## 8. 非目标(YAGNI)

- 不做深色精修(浅色优先)。
- 不做新功能 / 不改接口。
- 不做动画系统升级(沿用 150–300ms 过渡)。
- 不引入 UI 框架(Tailwind/shadcn)——纯 CSS 变量 + 轻量原语,保持零新依赖。
