# scribe3 TipTap 编辑器 + 交互质感重构方案(2026-06-23)

来源:① 彻底分析老版 scribe2 web-app 交互 ② 全网搜 TipTap v3 + 顶级写作 App 最佳实践(官方一手核实)③ ui-ux-pro-max 设计系统/UX 规则。

## 诊断:为什么"质感不如老版"

scribe3 颜色 token 已不错(墨 #37352f 非纯黑、暖纸 #f6f5f2 非纯白、暗底 #15140f 非纯黑——都符合"显高级"标准)。**差距在交互层与正文编辑面**:

| 缺口 | 老版有 | scribe3 现状 | 级别 |
|---|---|---|---|
| 正文是 **textarea** | TipTap 富文本 | `<textarea>` 裸控件 | 头号 |
| **全局 `:focus-visible`** | 2px 黛绿环 + 2px offset | **无**(键盘焦点不可见) | a11y CRITICAL |
| **`::selection` / `caret-color`** | — | 系统默认蓝(显廉价) | 高 |
| **过渡基准 token** | `--t:160ms` 统一 | 散用 150/200ms | 中 |
| **input/textarea focus** | 黛绿边 + 18% 光晕 | 仅 border 变色 | 中 |
| **Skeleton 骨架屏** | StateBoundary | 文字"加载中…" | 中 |
| **防丢草稿** | 3s localStorage + 恢复卡 | 无 | 中 |
| 正文排版 | Source Serif 4 / 行高 1.95 / 72ch | manuscript 有(但未用于编辑) | — |

## 决策(基于官方核实)

### A. TipTap 编辑器(头号交付)—— `ProseEditor.jsx` 替换 textarea
- **栈**:TipTap **v3**,菜单从 `@tiptap/react/menus` 导(v3 改路径,已本地核实);Floating UI(`@floating-ui/dom` 已随装)。
- **扩展**:`StarterKit`(含 Undo/Redo、Dropcursor、Gapcursor、TrailingNode)+ `Placeholder` + `CharacterCount` + `Focus`(段落级聚焦)+ 自定义 `SceneBreak`(`***`→居中 `* * *`,小说场景分隔)。**不引** Typography(避免智能标点干扰中文)。
- **BubbleMenu(划词)**:`options={{placement:'top',offset:8}}`(v3 默认 placement=right 必须改)、显式 `shouldShow`(空选区/节点选择/不可编辑时不显)。动作克制:**加粗 / 斜体 / 复制选区 + 选区字数**(小说正文 marks 少用,保持轻)。
- **专注模式**:Focus 扩展 `mode:'deepest'` + CSS 把非 `.has-focus` 段落降到 ~40% opacity;顶栏开关(iA Writer 式,仅起草用)。
- **CJK 关键**(官方核实):`CharacterCount.characters()`=字数(中文惯例;`words()` 对中文无意义,弃用);CSS `line-height:1.9 / text-indent:2em / word-break:normal / overflow-wrap:break-word`(**绝不 break-all**)/ `line-break:strict`(标点不顶行首);IME 合成期不改文档(加 compositionstart/end 守卫)。
- **性能**(写长篇必须):`spellcheck:false`(最大收益)、`getJSON` 非 `getHTML`、`shouldRerenderOnTransaction:false` + `useEditorState` 订阅 BubbleMenu active 态、`immediatelyRender:false`。
- **防丢草稿**:停输入 1s 防抖存 localStorage(`s3-draft-<work>-<ch>`),载章时若有比落库更新的草稿→顶部恢复卡(恢复/丢弃)。
- **流式**:render 仍走现有 SSE,渲染完 `setContent` 灌入编辑器。

### B. 全局交互打磨(`index.css` + `ui.jsx`)
- **过渡 token**:`@theme` 加 `--ease-standard:cubic-bezier(.4,0,.2,1)`;统一 hover 150ms ease-out / 入场 200ms。
- **`:focus-visible`**:全局 `outline:2px solid var(--color-brand); outline-offset:2px`(仅键盘,不破鼠标);圆角元素用 ring。
- **input/textarea/contenteditable focus**:黛绿边 + `box-shadow:0 0 0 3px color-mix(brand 18%)` 光晕。
- **`::selection`**:`background:color-mix(brand 20%); color:inherit`(取代系统蓝)。
- **`caret-color: var(--color-brand)`**(编辑器内)。
- **Skeleton 组件**(ui.jsx):`animate-pulse` 占位条,替换"加载中…"。
- **层叠阴影**:`--shadow-card` 多层低 alpha(取代生硬单层),用于卡片 hover/模态。
- **按压**:Btn 已 `active:scale-[.98]` ✓;给可点卡片加 hover `-translate-y-0.5` + 阴影升级。
- **reduced-motion**:`@media (prefers-reduced-motion)` 关动效。

### C. 不做(克制 / 收益边际)
- ❌ Slash `/` 命令(老版也无;命令面板 ⌘K 已覆盖;场景分隔用 `***` input rule 即可)。
- ❌ 打字机居中滚动(可后续;先做段落聚焦)。
- ❌ AI/人工段落着色 SegmentNode(scribe3 是整章 render,非逐段来源;暂不需要)。
- ❌ framer-motion(Tailwind transition + CSS 足够,官方核实老版也没用)。

## 验证口径
- `npm run build` 绿;后端 pytest 全绿。
- 真机逐视图冒烟:写作台(TipTap 输入/占位/字数/场景分隔/专注/划词/防丢草稿)、主编速答+联查实证、设定库 CRUD、图谱、仪表盘。
- 交互核验:键盘 Tab 焦点环可见、选区黛绿、光标黛绿、骨架屏、hover/按压反馈、reduced-motion。
- 输出质量:限知 render 仍不泄密(编辑器不破坏限知);中文排版正确(首行缩进/不切英文单词/标点不顶行首)。
