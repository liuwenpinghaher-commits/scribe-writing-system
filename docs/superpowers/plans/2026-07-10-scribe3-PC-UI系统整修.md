# Scribe3 PC UI 系统整修 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不搬迁现有业务功能和 API 的前提下，将 Scribe3 PC 界面整修为统一、可信、可访问的专业写作工作台，并消除重复章节导航、阶段语义混乱、四栏状态分叉和静态假数据。

**Architecture:** 保留 `AppRail → BinderLayout → FourPaneShell → DirectoryPane / DetailPane / RightDock` 生产路径。先建立兼容式 Token 与共享组件，再整修四栏与状态投影，随后接入视觉版 `ObjectFrame`、收敛章节工作台，最后逐页迁移并完成 PC 运行时验证；不建立完整 URL 路由和全量对象注册表。

**Tech Stack:** React、Vite、Tailwind CSS、Vitest、Testing Library、Playwright、`react-resizable-panels`、Lucide React。

## Global Constraints

- 仅支持 PC；最低完整视口 1280×720，主要验收视口 1440×900 和 1600×900。
- 保留现有四栏、八个一级入口、业务功能、API 和 `s3.layout.v2` 回退路径。
- 不做手机 / 平板 Drawer，不做完整 URL / 深链接，不做全量对象注册表重构。
- `ContextSnapshot`、`NavigationIntent`、Context Memory 和编辑线程是当前在途改动；实施前先核对最新 diff 和相关测试，不覆盖、不重建。
- 设定库与素材库名称和语义必须继续区分。
- 所有代码理解先用 CodeGraph；工具版本只通过二进制版本命令查询。
- 每项改动先写失败测试，再实现，再运行专项测试。
- `npm run build` 通过不代表运行时正确；结构任务必须完成真实 PC 浏览器验证。
- 未经用户单独授权，不 commit、不 push；每个任务结束只报告 checkpoint 和精确 diff。
- 不修改与本计划无关的工作区现有改动。

---

## File Map

### 设计系统

- Modify: `scribe3/web/src/index.css` — 语义颜色、字体、间距、焦点、动效和兼容别名。
- Modify: `scribe3/web/src/ui.jsx` — 兼容现有调用的 Button / Input / Textarea 基础原语。
- Modify: `scribe3/web/src/ui/Chip.jsx` — 统一紧凑组件尺寸和状态。
- Modify: `scribe3/web/src/ui/Dialog.jsx` — 保持焦点陷阱、Escape 和焦点恢复。
- Modify: `scribe3/web/src/ui/Toast.jsx` — 状态与 `aria-live`。
- Create: `scribe3/web/src/ui/Field.jsx` — Label / Description / Error 组合。
- Create: `scribe3/web/src/ui/Tabs.jsx` — 键盘可操作 Tabs。
- Create: `scribe3/web/src/ui/AsyncState.jsx` — loading / empty / error / degraded。
- Create: `scribe3/web/src/ui/designTokens.test.js` — CSS Token 与对比度合同。
- Create: `scribe3/web/src/ui/primitives.test.jsx` — 共享组件状态与语义。

### 主框架与状态

- Modify: `scribe3/web/src/AppRail.jsx` — 纯全局职责。
- Modify: `scribe3/web/src/App.jsx` — 删除章节顶栏插槽状态，保留全局视图与搜索入口。
- Modify: `scribe3/web/src/BinderLayout.jsx` — 删除阶段 Slot Provider，保留 Context / Selection / Chief / Deduce Provider。
- Modify: `scribe3/web/src/shell.jsx` — 入口分组、32px 点击区、12px 最小标签。
- Modify: `scribe3/web/src/studioDocks.jsx` — capability 分组与右栏作用域。
- Modify: `scribe3/web/src/layout/FourPaneShell.jsx` — 作品级布局偏好和统一选择投影。
- Modify: `scribe3/web/src/layout/DirectoryHeader.jsx` — 统一目录头。
- Modify: `scribe3/web/src/layout/DirectoryPane.jsx` — 为各入口提供一致外框。
- Create: `scribe3/web/src/layout/contextSelection.js` — `ContextSnapshot` 到 UI selection 的纯投影。
- Create: `scribe3/web/src/layout/contextSelection.test.js` — 投影合同。
- Modify: `scribe3/web/src/layout/__tests__/fourPane-context-atomic.test.jsx` — 内容级 revision 原子性。

### 对象与章节

- Modify: `scribe3/web/src/layout/ObjectFrame.jsx` — 视觉外框，支持外部标题 / 状态 / Tabs / Actions。
- Modify: `scribe3/web/src/layout/objectRegistry.js` — 仅维护章、角色、素材的呈现描述。
- Modify: `scribe3/web/src/DetailPane.jsx` — 接入对象视觉外框。
- Modify: `scribe3/web/src/ChapterStudio.jsx` — 五阶段、单一章导航、章节对象框架。
- Modify: `scribe3/web/src/WriteLayout.jsx` — 移除第二套章导航和重复横条。
- Create: `scribe3/web/src/ChapterAuxPanel.jsx` — 简报 / 关联 / 北极星组合辅助页。
- Modify: `scribe3/web/src/__tests__/chapterStudio-routing.test.jsx` — 五阶段与演绎接入。
- Modify: `scribe3/web/src/__tests__/chapterStudio-topbar.test.jsx` — 顶栏不再承载阶段。
- Modify: `scribe3/web/src/__tests__/writeLayout-phase.test.jsx` — 只有一套章导航。
- Modify: `scribe3/web/src/layout/__tests__/objectFrame.test.jsx` — 新呈现接口。
- Create: `scribe3/web/src/layout/__tests__/objectFrame-integration.test.jsx` — 章 / 角色 / 素材生产接入。

### 页面与验证

- Modify: `scribe3/web/src/Library.jsx`
- Modify: `scribe3/web/src/CodexNew.jsx`
- Modify: `scribe3/web/src/CodexDetail.jsx`
- Modify: `scribe3/web/src/Materials.jsx`
- Modify: `scribe3/web/src/MaterialNetwork.jsx`
- Modify: `scribe3/web/src/layout/CapabilityDirectories.jsx`
- Modify: `scribe3/web/src/layout/CapabilityDetailPanes.jsx`
- Modify: `scribe3/web/src/capabilities/search/SearchDirectory.jsx`
- Modify: `scribe3/web/src/capabilities/search/SearchDetail.jsx`
- Modify: `scribe3/web/src/capabilities/issues/IssueDirectory.jsx`
- Modify: `scribe3/web/src/capabilities/issues/IssueDetail.jsx`
- Modify: `scribe3/web/src/views/AtlasView.jsx`
- Modify: `scribe3/web/src/views/TimelineView.jsx`
- Modify: `scribe3/web/src/views/InsightView.jsx`
- Modify: `scribe3/web/pw_layout.mjs` — 当前 DOM、三种 PC 视口、浅色 / 深色和只读拦截。
- Create: `scribe3/web/src/__tests__/pc-ui-static-contract.test.js` — 字号、Emoji、伪按钮新增守卫。

---

### Task 1: 建立 PC Design Token 合同

**Files:**
- Modify: `scribe3/web/src/index.css`
- Modify: `scribe3/web/src/layout/tokens.js`
- Create: `scribe3/web/src/ui/designTokens.test.js`

**Interfaces:**
- Produces: CSS 变量 `--color-canvas|surface|raised|ink|muted|faint|line|brand|brandfg|ok|warn|danger`。
- Produces: 语义字号 `--text-meta|helper|body|object-title|section-title|page-title`。
- Produces: `PC_LAYOUT`，供全局栏、入口栏和四栏默认宽度共用。
- Consumes: 现有 Tailwind `@theme` 和 `dark` class 主题切换。

- [ ] **Step 1: 写 Token 存在性和对比度失败测试**

```javascript
import { describe, expect, it } from 'vitest'
import fs from 'node:fs'

const css = fs.readFileSync(new URL('../index.css', import.meta.url), 'utf8')
const hex = (name, block) => {
  const match = block.match(new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`))
  if (!match) throw new Error(`missing color token: ${name}`)
  return match[1]
}
const lum = (value) => {
  const channels = value.match(/[0-9a-f]{2}/gi).map((part) => parseInt(part, 16) / 255)
    .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}
const contrast = (a, b) => (Math.max(lum(a), lum(b)) + 0.05) / (Math.min(lum(a), lum(b)) + 0.05)

describe('PC UI color tokens', () => {
  it('keeps every normal text token at 4.5:1 on canvas', () => {
    const light = css.match(/:root\s*\{([\s\S]*?)\}/)[1]
    for (const name of ['ink', 'muted', 'faint', 'brand', 'ok', 'warn', 'danger']) {
      expect(contrast(hex(name, light), hex('canvas', light)), name).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('keeps dark theme normal text tokens at 4.5:1 on canvas', () => {
    const dark = css.match(/\.dark\s*\{([\s\S]*?)\}/)[1]
    for (const name of ['ink', 'muted', 'faint', 'brand', 'ok', 'warn', 'danger']) {
      expect(contrast(hex(name, dark), hex('canvas', dark)), name).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('defines semantic type roles and never maps them below 12px', () => {
    for (const name of ['meta', 'helper', 'body', 'object-title', 'section-title', 'page-title']) {
      const match = css.match(new RegExp(`--text-${name}:\\s*([0-9.]+)px`))
      expect(match, name).not.toBeNull()
      expect(Number(match[1]), name).toBeGreaterThanOrEqual(12)
    }
  })
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/ui/designTokens.test.js`

Expected: FAIL，现有 CSS 缺少 `raised`、`muted` 和语义字号 Token，且部分颜色组合低于 4.5:1。

- [ ] **Step 3: 在 `index.css` 增加兼容式语义 Token**

```css
:root {
  --color-canvas: #f3f1ec;
  --color-surface: #fbfaf7;
  --color-raised: #ffffff;
  --color-ink: #1d2420;
  --color-muted: #5f6963;
  --color-faint: #65706a;
  --color-line: #d8d4cb;
  --color-brand: #2f6b5d;
  --color-brandfg: #ffffff;
  --color-ok: #2f6b4f;
  --color-warn: #825615;
  --color-danger: #9d3838;
  --text-meta: 12px;
  --text-helper: 13px;
  --text-body: 14px;
  --text-object-title: 16px;
  --text-section-title: 20px;
  --text-page-title: 24px;
}

.dark {
  --color-canvas: #141816;
  --color-surface: #1b211e;
  --color-raised: #222925;
  --color-ink: #eef1ed;
  --color-muted: #b7c0ba;
  --color-faint: #8f9a93;
  --color-line: #38423d;
  --color-brand: #74b29e;
  --color-brandfg: #102019;
  --color-ok: #78c49b;
  --color-warn: #e8b768;
  --color-danger: #f08b8b;
}
```

保留现有 Token 名作为兼容别名；不要在 Task 1 删除仍被页面引用的 `text-f10` / `text-f11`，清理放到 Task 11。

把 `layout/tokens.js` 改成真实被布局消费的尺寸合同：

```javascript
export const PC_LAYOUT = Object.freeze({
  topbar: 44,
  rail: 56,
  directory: { min: 240, ideal: 264, max: 320 },
  detail: { min: 600 },
  right: { min: 300, ideal: 336, max: 380 },
})
```

Task 3 的 `AppRail` / `Rail` 与 Task 4 的 `FourPaneShell` 必须导入该合同，避免 CSS、JS 和测试各写一套尺寸。

- [ ] **Step 4: 运行 Token 测试和现有基础测试**

Run: `cd scribe3/web && npx vitest run src/ui/designTokens.test.js src/__tests__/basic.test.js`

Expected: PASS；关键文本色对画布不低于 4.5:1。

- [ ] **Step 5: Checkpoint**

Run: `git diff --check -- scribe3/web/src/index.css scribe3/web/src/layout/tokens.js scribe3/web/src/ui/designTokens.test.js`

Expected: 无输出。报告变更，不 commit。

---

### Task 2: 重建共享 PC 控件与状态组件

**Files:**
- Modify: `scribe3/web/src/ui.jsx`
- Modify: `scribe3/web/src/ui/Chip.jsx`
- Modify: `scribe3/web/src/ui/Dialog.jsx`
- Modify: `scribe3/web/src/ui/Toast.jsx`
- Create: `scribe3/web/src/ui/Field.jsx`
- Create: `scribe3/web/src/ui/Tabs.jsx`
- Create: `scribe3/web/src/ui/AsyncState.jsx`
- Create: `scribe3/web/src/ui/primitives.test.jsx`

**Interfaces:**
- Preserves: `Btn`, `Input`, `Textarea`, `Card`, `Skeleton`, `SectionTitle`, `Empty`, `Row`, `Tag` exports。
- Produces: `Field({ label, description, error, required, children })`。
- Produces: `Tabs({ value, onValueChange, items, ariaLabel })`。
- Produces: `AsyncState({ state, title, message, onRetry, children })`。

- [ ] **Step 1: 写共享语义和键盘失败测试**

```jsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Btn } from '../ui.jsx'
import { Field } from './Field.jsx'
import { Tabs } from './Tabs.jsx'
import { AsyncState } from './AsyncState.jsx'

describe('PC UI primitives', () => {
  it('associates field label, description and error', () => {
    render(<Field label="标题" description="用于目录显示" error="不能为空" required><input /></Field>)
    const input = screen.getByRole('textbox', { name: /标题/ })
    expect(input).toHaveAccessibleDescription('用于目录显示 不能为空')
  })

  it('moves tabs with arrow keys', () => {
    const onChange = vi.fn()
    render(<Tabs ariaLabel="章节阶段" value="outline" onValueChange={onChange}
      items={[{ value: 'outline', label: '大纲' }, { value: 'beats', label: '节拍' }]} />)
    fireEvent.keyDown(screen.getByRole('tab', { name: '大纲' }), { key: 'ArrowRight' })
    expect(onChange).toHaveBeenCalledWith('beats')
  })

  it('uses status and alert semantics', () => {
    const { rerender } = render(<AsyncState state="loading" title="加载目录" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    rerender(<AsyncState state="error" title="目录加载失败" onRetry={() => {}} />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('keeps icon buttons accessible', () => {
    render(<Btn icon aria-label="展开目录" />)
    expect(screen.getByRole('button', { name: '展开目录' })).toHaveClass('h-8', 'w-8')
  })
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/ui/primitives.test.jsx`

Expected: FAIL，三个新组件尚不存在，`Btn` 仍有 24 / 28px 尺寸。

- [ ] **Step 3: 实现兼容式尺寸与新组件**

`Btn` 尺寸合同：

```jsx
const sizes = icon
  ? { xs: 'h-8 w-8 rounded-md', sm: 'h-8 w-8', md: 'h-9 w-9' }
  : { xs: 'h-[30px] px-2.5 text-meta', sm: 'h-[34px] px-3 text-helper', md: 'h-9 px-3.5 text-body' }
```

`Tabs` 导出合同：

```jsx
export function Tabs({ value, onValueChange, items, ariaLabel }) {
  const move = (index, delta) => {
    const next = items[(index + delta + items.length) % items.length]
    onValueChange(next.value)
  }
  return <div role="tablist" aria-label={ariaLabel} className="inline-flex items-center gap-1 rounded-lg bg-soft p-1">
    {items.map((item, index) => <button key={item.value} role="tab" aria-selected={item.value === value}
      tabIndex={item.value === value ? 0 : -1}
      onClick={() => onValueChange(item.value)}
      onKeyDown={(event) => {
        if (event.key === 'ArrowRight') { event.preventDefault(); move(index, 1) }
        if (event.key === 'ArrowLeft') { event.preventDefault(); move(index, -1) }
      }}
      className="h-8 rounded-md px-3 text-helper text-faint aria-selected:bg-surface aria-selected:text-brand aria-selected:ring-1 aria-selected:ring-line">
      {item.label}
    </button>)}
  </div>
}
```

`Field.jsx` 合同：

```jsx
import { cloneElement, useId } from 'react'

export function Field({ label, description, error, required = false, children }) {
  const id = useId()
  const descriptionId = description ? `${id}-description` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [descriptionId, errorId].filter(Boolean).join(' ') || undefined
  return <div className="space-y-1.5">
    <label htmlFor={id} className="block text-helper font-medium text-ink">{label}{required && <span aria-hidden="true"> *</span>}</label>
    {cloneElement(children, { id, required, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })}
    {description && <div id={descriptionId} className="text-meta text-muted">{description}</div>}
    {error && <div id={errorId} role="alert" className="text-meta text-danger">{error}</div>}
  </div>
}
```

`AsyncState.jsx` 合同：

```jsx
import { Btn } from '../ui.jsx'

export function AsyncState({ state, title, message, onRetry, children }) {
  if (state === 'ready') return children
  const role = state === 'error' ? 'alert' : 'status'
  return <div role={role} className="rounded-lg border border-line bg-surface p-4 text-helper">
    <div className="font-medium text-ink">{title}</div>
    {message && <div className="mt-1 text-muted">{message}</div>}
    {state === 'error' && onRetry && <Btn className="mt-3" onClick={onRetry}>重试</Btn>}
  </div>
}
```

- [ ] **Step 4: 运行共享 UI 测试**

Run: `cd scribe3/web && npx vitest run src/ui/primitives.test.jsx src/ui/Dialog.test.jsx src/ui/Toast.test.jsx`

Expected: PASS。

- [ ] **Step 5: Checkpoint**

Run: `git diff --check -- scribe3/web/src/ui.jsx scribe3/web/src/ui`

Expected: 无输出。报告变更，不 commit。

---

### Task 3: 入口分组与全局栏职责

**Files:**
- Modify: `scribe3/web/src/shell.jsx`
- Modify: `scribe3/web/src/studioDocks.jsx`
- Modify: `scribe3/web/src/AppRail.jsx`
- Modify: `scribe3/web/src/layout/__tests__/fourPaneShell.test.jsx`
- Modify: `scribe3/web/src/__tests__/appRail-layout.test.jsx`

**Interfaces:**
- Extends capability: `{ key, icon, label, group: 'content'|'craft'|'inspect', badge, render }`。
- Preserves: `Rail({ side, caps, active, onActive })`。
- Preserves temporarily: `AppRail.extra`，Task 7 移除章节阶段后再删除。

- [ ] **Step 1: 写入口分组失败测试**

```jsx
it('groups all eight PC entries without deleting capabilities', () => {
  render(<FourPaneShell {...props} />)
  expect(screen.getByRole('group', { name: '内容' })).toBeInTheDocument()
  expect(screen.getByRole('group', { name: '工艺' })).toBeInTheDocument()
  expect(screen.getByRole('group', { name: '检查' })).toBeInTheDocument()
  for (const name of ['手稿', '设定库', '素材库', '演绎 · 角色限知', '伏笔', '母题', '搜索', '校验']) {
    expect(screen.getByRole('button', { name })).toBeInTheDocument()
  }
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/fourPaneShell.test.jsx src/__tests__/appRail-layout.test.jsx`

Expected: FAIL，`Rail` 尚未输出三个命名组。

- [ ] **Step 3: 为 capability 添加组并按组渲染**

```jsx
const GROUPS = [
  { key: 'content', label: '内容' },
  { key: 'craft', label: '工艺' },
  { key: 'inspect', label: '检查' },
]

export function Rail({ side, caps, active, onActive }) {
  if (side === 'right') return <div className="w-[56px] shrink-0 border-l border-line bg-surface px-1 py-2">
    {caps.map((cap) => <RailBtn key={cap.key} cap={cap} label={shortLabel(cap)} badge={cap.badge}
      on={active === cap.key} onClick={() => onActive(active === cap.key ? '' : cap.key)} />)}
  </div>
  return <div className="w-[56px] shrink-0 border-r border-line bg-surface px-1 py-2">
    {GROUPS.map((group) => <div key={group.key} role="group" aria-label={group.label} className="mb-2 border-b border-line pb-2 last:mb-0 last:border-0 last:pb-0">
      {caps.filter((cap) => cap.group === group.key).map((cap) => <RailBtn key={cap.key} cap={cap}
        label={shortLabel(cap)} badge={cap.badge} on={active === cap.key}
        onClick={() => onActive(active === cap.key ? '' : cap.key)} />)}
    </div>)}
  </div>
}
```

在 `useLeftDockCapabilities` 中给手稿 / 设定 / 素材标记 `content`，演绎 / 伏笔 / 母题标记 `craft`，搜索 / 校验标记 `inspect`。

- [ ] **Step 4: 收敛全局栏视觉，但暂保留阶段插槽兼容**

将 `AppRail` 高度改为 44px；作品、全局视图、搜索触发、主题和系统状态按区域分隔。Task 7 前 `extra` 仍能渲染，但不新增第二套阶段。

- [ ] **Step 5: 运行专项测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/fourPaneShell.test.jsx src/__tests__/appRail-layout.test.jsx`

Expected: PASS；八个入口全部存在，且三个组可被辅助技术识别。

- [ ] **Step 6: Checkpoint**

Run: `git diff --check -- scribe3/web/src/shell.jsx scribe3/web/src/studioDocks.jsx scribe3/web/src/AppRail.jsx`

Expected: 无输出。报告变更，不 commit。

---

### Task 4: 统一目录头与作品级布局偏好

**Files:**
- Modify: `scribe3/web/src/layout/DirectoryHeader.jsx`
- Modify: `scribe3/web/src/layout/DirectoryPane.jsx`
- Modify: `scribe3/web/src/layout/CapabilityDirectories.jsx`
- Modify: `scribe3/web/src/layout/FourPaneShell.jsx`
- Modify: `scribe3/web/src/layout/__tests__/directoryPane-tools.test.jsx`
- Modify: `scribe3/web/src/layout/__tests__/directoryPane-manuscript.test.jsx`
- Modify: `scribe3/web/src/layout/__tests__/fourPaneShell.test.jsx`

**Interfaces:**
- Produces: `DirectoryHeader({ title, count, query, onQueryChange, searchLabel, primaryAction, secondaryActions, status })`。
- Preserves: 各目录现有业务组件和 `onSelectItem`。
- Produces: work-scoped panel layout id `${FOUR_PANE_LAYOUT_ID}:${work || 'main'}`。

(2026-07-10 修正:布局 id 保留现常量 FOUR_PANE_LAYOUT_ID 前缀，换名会作废用户既有栏宽偏好)

- [ ] **Step 1: 写目录头和作品隔离失败测试**

> 注:这两个测试文件不用 jest-dom（全仓惯例用 `toBeTruthy()` / `toBeNull()`），照惯例写。

```jsx
it('uses one semantic directory header without fake controls', () => {
  render(<CapabilityDirectory capability="promise" seq={3} onSelectItem={() => {}} />)
  expect(screen.getByRole('heading')).toBeTruthy()
  expect(screen.queryByText('固定')).toBeNull()
  expect(screen.queryByRole('button', { name: '同步' })).toBeNull()
  expect(screen.queryByRole('button', { name: '范围' })).toBeNull()
})

it('scopes panel layout by work', () => {
  render(<FourPaneShell {...props} work="book-a" />)
  expect(mockUseDefaultLayout).toHaveBeenCalledWith(expect.objectContaining({ id: 's3.fourPane.layout.v2:book-a' }))
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/directoryPane-tools.test.jsx src/layout/__tests__/directoryPane-manuscript.test.jsx src/layout/__tests__/fourPaneShell.test.jsx`

Expected: FAIL，目录头仍含静态“固定 / 同步 / 范围”，面板 id 未按作品隔离。

- [ ] **Step 3: 改造 `DirectoryHeader` 为受控组件**

```jsx
export function DirectoryHeader({ title, count, query = '', onQueryChange, searchLabel, primaryAction, secondaryActions = [], status }) {
  return <header className="shrink-0 border-b border-line bg-surface px-3 py-3">
    <div className="mb-2 flex min-h-8 items-center gap-2">
      <h2 className="min-w-0 flex-1 truncate text-object-title font-semibold text-ink">{title}</h2>
      {Number.isFinite(count) && <span className="text-meta tabular-nums text-muted">{count}</span>}
      {status}
    </div>
    <div className="flex items-center gap-2">
      {onQueryChange && <input type="search" aria-label={searchLabel || `${title}筛选`} value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-canvas px-3 text-helper text-ink" />}
      {secondaryActions.map((action) => <Btn key={action.label} size="xs" onClick={action.onClick}>{action.label}</Btn>)}
      {primaryAction && <Btn variant="primary" size="sm" onClick={primaryAction.onClick}>{primaryAction.label}</Btn>}
    </div>
  </header>
}
```

在 `DirectoryHeader.jsx` 导入 `Btn`，同时把 `CapabilityDirectories.jsx` 的旧 `badge/current/subtitle/primaryAction/secondaryAction/chips` 调用改成新合同。没有真实 handler 时不传按钮；没有 live 数量时不传 `count`。

- [ ] **Step 4: 按作品隔离布局 id 和偏好**

```jsx
const layoutId = `${FOUR_PANE_LAYOUT_ID}:${work || 'main'}`
const { defaultLayout, onLayoutChanged } = useDefaultLayout({ id: layoutId })
```

保持当前 `readCollapsed` / `writeCollapsed` 的作品级行为；不要迁移或清空现有本地偏好。

- [ ] **Step 5: 运行专项测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/directoryPane-tools.test.jsx src/layout/__tests__/directoryPane-manuscript.test.jsx src/layout/__tests__/fourPaneShell.test.jsx`

Expected: PASS。

- [ ] **Step 6: Checkpoint**

Run: `git diff --check -- scribe3/web/src/layout/DirectoryHeader.jsx scribe3/web/src/layout/DirectoryPane.jsx scribe3/web/src/layout/CapabilityDirectories.jsx scribe3/web/src/layout/FourPaneShell.jsx`

Expected: 无输出。报告变更，不 commit。

---

### Task 5: 让 ContextSnapshot 真正投影到四栏内容

**Files:**
- Create: `scribe3/web/src/layout/contextSelection.js`
- Create: `scribe3/web/src/layout/contextSelection.test.js`
- Modify: `scribe3/web/src/layout/FourPaneShell.jsx`
- Modify: `scribe3/web/src/layout/__tests__/fourPane-context-atomic.test.jsx`

**Interfaces:**
- Consumes: `ContextSnapshot { entry, focus, detail_route, chapter, phase, revision }`。
- Produces: `selectionFromSnapshot(snapshot, fallbackSel)`。
- Preserves: `handleSelectItem` 和 `targetNodeToSelection` 本地导航路径。

- [ ] **Step 1: 先运行现有 Context 测试作为保护门**

Run: `cd scribe3/web && npx vitest run src/context/contextSnapshot.test.js src/layout/__tests__/fourPane-context-atomic.test.jsx`

Expected: PASS。若失败，停止 UI 计划并报告当前在途 Context 改动状态。

- [ ] **Step 2: 写内容投影失败测试**

```javascript
import { describe, expect, it } from 'vitest'
import { selectionFromSnapshot } from './contextSelection.js'

describe('selectionFromSnapshot', () => {
  it('projects a chapter including its phase', () => {
    expect(selectionFromSnapshot({ detail_route: 'chapter:7', chapter: 7, phase: 'deduce', focus: { type: 'chapter', id: 'chapter:7', label: '第七章' } }, null)).toEqual({
      mode: 'node',
      node: { id: 'ch:7', type: 'chapter', ref: 7, label: '第七章', phase: 'deduce' },
    })
  })

  it('keeps a richer local selection when routes match', () => {
    const local = { mode: 'node', node: { id: 'material:abc', type: 'material', ref: 'material:abc', label: '原始标题', meta: { kind: 'note' } } }
    expect(selectionFromSnapshot({ detail_route: 'material:abc', focus: { type: 'material', id: 'material:abc', label: '标题' } }, local)).toBe(local)
  })
})
```

- [ ] **Step 3: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/layout/contextSelection.test.js`

Expected: FAIL，投影模块尚不存在。

（2026-07-10 修正：原示例的 `ref: snapshot.focus.id` 用全限定 id 会打穿 CodexDetail/PropositionDetail/MaterialDetail 的本地 id 约定（ref 须是去前缀本地 id，如 `'甲'` 而非 `'character:甲'`）；章节判据应以 `focus.type` 为准而非 `snapshot.chapter != null`（否则带 ambient chapter 的角色 focus 被误投成章节）。裁决：实测约定优先于文档示例——条目节点一律委托 `targetNodeToSelection`（本地导航的权威节点构造器）产出同形节点。）

- [ ] **Step 4: 实现最小安全投影**

```javascript
import { targetNodeToSelection } from './targetNavigation'

// 后端 FocusType → targetNodeToSelection 能识别的 hint type：review_issue 走 'issue'
// 触发 issueNode（补 payload/target_node）；promise/motif 产出 promise_view/motif_view。
const DELEGATE_TYPE = { character: 'character', material: 'material', promise: 'promise', motif: 'motif', fact: 'fact', review_issue: 'issue' }

const routeOf = (sel) => {
  const node = sel?.node
  if (!node) return sel?.mode === 'view' ? `view:${sel.viewKey}` : 'empty'
  if (node.type === 'chapter' || node.type === 'scene') return `chapter:${node.type === 'scene' ? node.ref?.seq : node.ref}`
  return String(node.id || node.type)
}

// 从 focus.id 剥掉首段 `前缀:`，得去前缀本地 id
const localRef = (id) => String(id || '').replace(/^[^:]+:/, '')

export function selectionFromSnapshot(snapshot, fallbackSel) {
  if (!snapshot?.focus) return fallbackSel
  if (routeOf(fallbackSel) === snapshot.detail_route) return fallbackSel
  const focus = snapshot.focus
  if (focus.type === 'view') {
    const viewKey = String(focus.id || '').replace(/^view:/, '')
    return viewKey && viewKey !== 'empty' ? { mode: 'view', viewKey } : fallbackSel
  }
  // 章/场景判据以 focus.type 为准（不用 snapshot.chapter != null）
  if (focus.type === 'chapter' || focus.type === 'scene') {
    const seq = Number(snapshot.chapter ?? String(snapshot.detail_route || '').split(':')[1])
    if (!Number.isFinite(seq)) return fallbackSel
    return { mode: 'node', node: { id: `ch:${seq}`, type: 'chapter', ref: seq, label: focus.label || `${seq}`, phase: snapshot.phase || undefined } }
  }
  // 其余条目类：委托 targetNodeToSelection 产出同形节点（ref = 去前缀本地 id）
  const hint = DELEGATE_TYPE[focus.type]
  if (!hint) return fallbackSel
  const target = { type: hint, id: focus.id, label: focus.label || focus.id }
  if (hint !== 'issue') target.ref = localRef(focus.id)   // review_issue 章号由 issueNode 推
  const selected = targetNodeToSelection(target)
  return selected?.node ? { mode: 'node', node: selected.node } : fallbackSel
}
```

- [ ] **Step 5: 四栏共同使用 `effectiveSel`**

```jsx
const effectiveSel = navigated ? selectionFromSnapshot(snapshot, sel) : sel
// DetailPane、RightDock、当前目录选中态全部传 effectiveSel；事件处理仍更新原 onSelectNode。
// isView 也读 effectiveSel（而非本地 sel）：栏2 显隐 / 栏3 minSize / 目录折叠 effect 与内容同源，
// 跨 node↔view 边界对齐时布局与内容不再自相矛盾。
```

扩展 `fourPane-context-atomic.test.jsx`：模拟 409 latest 从角色 A 切到章节 7，断言 `data-context-revision` 相同且详情、右栏都收到章节 7。

- [ ] **Step 6: 运行 Context 与四栏测试**

Run: `cd scribe3/web && npx vitest run src/context/contextSnapshot.test.js src/layout/contextSelection.test.js src/layout/__tests__/fourPane-context-atomic.test.jsx src/layout/__tests__/targetNavigation.test.js`

Expected: PASS。

- [ ] **Step 7: Checkpoint**

Run: `git diff --check -- scribe3/web/src/layout/contextSelection.js scribe3/web/src/layout/contextSelection.test.js scribe3/web/src/layout/FourPaneShell.jsx scribe3/web/src/layout/__tests__/fourPane-context-atomic.test.jsx`

Expected: 无输出。报告变更，不 commit。

---

### Task 6: 将 ObjectFrame 接入真实详情路径

**Files:**
- Modify: `scribe3/web/src/layout/ObjectFrame.jsx`
- Modify: `scribe3/web/src/layout/objectRegistry.js`
- Modify: `scribe3/web/src/DetailPane.jsx`
- Modify: `scribe3/web/src/layout/__tests__/objectFrame.test.jsx`
- Create: `scribe3/web/src/layout/__tests__/objectFrame-integration.test.jsx`

**Interfaces:**
- Produces: `ObjectFrame({ breadcrumb, title, status, tabs, activeTab, onTab, actions, children })`。
- Produces: `presentationForNode(node)`，仅为 chapter / character / material 返回基础呈现数据。
- Preserves: `DetailPane` 业务路由和各 Detail Component props。

- [ ] **Step 1: 写视觉外框与生产接入失败测试**

```jsx
it('renders a semantic object header', () => {
  render(<ObjectFrame breadcrumb="设定库 / 角色" title="柳三更" status="已保存" actions={<button>更多</button>}><div>详情</div></ObjectFrame>)
  expect(screen.getByRole('heading', { name: '柳三更' })).toBeInTheDocument()
  expect(screen.getByText('设定库 / 角色')).toBeInTheDocument()
  expect(screen.getByText('已保存')).toHaveAttribute('role', 'status')
})

// (2026-07-10 修正:ref 用去前缀本地 id,见 Task 5 修正说明)
// 权威构造器 layout/targetNavigation.js:codexNode/targetNodeToSelection 产出的 character/material 节点
// ref 是去前缀本地 id('a'),node.id 才带类型前缀;CodexDetail.jsx:53 pickRow 与 Materials.jsx:136 MaterialDetail 均按此约定匹配。
it.each([
  [{ mode: 'node', node: { id: 'character:a', type: 'character', ref: 'a', label: '柳三更' } }, '柳三更'],
  [{ mode: 'node', node: { id: 'material:a', type: 'material', ref: 'a', label: '铃铛资料' } }, '铃铛资料'],
])('frames production detail %j', (sel, title) => {
  render(<DetailPane sel={sel} work="book-a" />)
  expect(screen.getByRole('heading', { name: title })).toBeInTheDocument()
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/objectFrame.test.jsx src/layout/__tests__/objectFrame-integration.test.jsx`

Expected: FAIL，当前 `ObjectFrame` 依赖未完成 registry，`DetailPane` 未使用它。

- [ ] **Step 3: 改造 ObjectFrame 为外部呈现接口**

```jsx
// (2026-07-10 修正:硬编码 id="object-title" 在同页挂两个 ObjectFrame 时会重复(a11y 违规),
//  改用 useId() 生成唯一 id 并让 aria-labelledby 指向它。)
export function ObjectFrame({ breadcrumb, title, status, tabs = [], activeTab, onTab, actions, children }) {
  const titleId = useId()
  return <section className="flex h-full min-h-0 flex-col bg-canvas" aria-labelledby={titleId}>
    <header className="shrink-0 border-b border-line bg-surface px-4 py-3">
      <div className="mb-1 truncate text-meta text-muted">{breadcrumb}</div>
      <div className="flex min-h-9 items-center gap-3">
        <h1 id={titleId} className="min-w-0 flex-1 truncate text-object-title font-semibold text-ink">{title}</h1>
        {status && <span role="status" className="text-meta text-muted">{status}</span>}
        {actions}
      </div>
      {tabs.length > 0 && <Tabs ariaLabel={`${title}页签`} value={activeTab} onValueChange={onTab} items={tabs} />}
    </header>
    <div className="min-h-0 flex-1 overflow-auto">{children}</div>
  </section>
}
```

- [ ] **Step 4: 在 DetailPane 仅包装角色和素材；章节留给 Task 7**

使用 `presentationForNode(node)` 返回 breadcrumb / title；保持 `renderDetail` 的现有组件调用，不改变 API。容器、全局视图、创建表单暂不包对象框架。

- [ ] **Step 5: 运行对象路由测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/objectFrame.test.jsx src/layout/__tests__/objectFrame-integration.test.jsx src/__tests__/detailPane-routing.test.jsx src/__tests__/detailPane-capabilities.test.jsx`

Expected: PASS。

- [ ] **Step 6: Checkpoint**

Run: `git diff --check -- scribe3/web/src/layout/ObjectFrame.jsx scribe3/web/src/layout/objectRegistry.js scribe3/web/src/DetailPane.jsx`

Expected: 无输出。报告变更，不 commit。

---

### Task 7: 章节五阶段与单一章导航

**Files:**
- Modify: `scribe3/web/src/ChapterStudio.jsx`
- Modify: `scribe3/web/src/WriteLayout.jsx`
- Modify: `scribe3/web/src/AppRail.jsx`
- Modify: `scribe3/web/src/App.jsx`
- Modify: `scribe3/web/src/BinderLayout.jsx`
- Create: `scribe3/web/src/ChapterAuxPanel.jsx`
- Modify: `scribe3/web/src/studioDocks.jsx`
- Modify: `scribe3/web/src/__tests__/chapterStudio-routing.test.jsx`
- Modify: `scribe3/web/src/__tests__/chapterStudio-topbar.test.jsx`
- Modify: `scribe3/web/src/__tests__/writeLayout-phase.test.jsx`
- Modify: `scribe3/web/src/__tests__/appRail-layout.test.jsx`

(2026-07-11 修正:appRail-layout 第一条用例断言 extra 渲染,与 Step 1 矛盾,须由本任务改写)

**Interfaces:**
- Produces: `PHASES = outline|beats|deduce|draft|final`。
- Produces: `ChapterAuxPanel({ seq })`，内部页签 brief / frame / northstar。(2026-07-11 修正:work 是死参,RightDock 无 work 形参,面板走全局 WORK)
- Consumes: `DeduceStage({ seq, meta, onSaved, work })`。
- Preserves: `WriteLayout` 保存、未保存暂存、护栏、QC、主编 Portal。

- [ ] **Step 1: 写五阶段、顶栏和单导航失败测试**

```jsx
it('shows exactly five semantic stages', () => {
  render(<ChapterStudio work="book-a" seq={1} />)
  const tabs = screen.getAllByRole('tab')
  expect(tabs.map((tab) => tab.textContent)).toEqual(['大纲', '节拍', '演绎', '草稿', '正文'])
  expect(screen.queryByRole('tab', { name: '简报' })).not.toBeInTheDocument()
  expect(screen.queryByRole('tab', { name: '关联' })).not.toBeInTheDocument()
  expect(screen.queryByRole('tab', { name: '北极星' })).not.toBeInTheDocument()
})

it('renders one chapter navigation set', () => {
  render(<ChapterStudio work="book-a" seq={2} onSeqChange={() => {}} />)
  expect(screen.getAllByRole('button', { name: '上一章' })).toHaveLength(1)
  expect(screen.getAllByRole('button', { name: '下一章' })).toHaveLength(1)
})

it('does not inject phases into AppRail', () => {
  render(<AppRail current={{ title: '书' }} extra={<div>章节阶段</div>} />)
  expect(screen.queryByTestId('topbar-work-tabs')).not.toBeInTheDocument()
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/__tests__/chapterStudio-routing.test.jsx src/__tests__/chapterStudio-topbar.test.jsx src/__tests__/writeLayout-phase.test.jsx`

Expected: FAIL，当前有七个阶段项、阶段仍注入 AppRail，正文包含第二套章导航。

- [ ] **Step 3: 收敛阶段常量并直接渲染 DeduceStage**

```jsx
const PHASES = [
  { key: 'outline', label: '大纲', icon: AlignLeft },
  { key: 'beats', label: '节拍', icon: ListChecks },
  { key: 'deduce', label: '演绎', icon: Sparkles },
  { key: 'draft', label: '草稿', icon: FileEdit },
  { key: 'final', label: '正文', icon: BookText },
]
const META_PHASES = new Set(['outline', 'beats', 'deduce', 'draft'])
```

删除 `setPhaseP` 中派发 `s3-open-capability` 的 deduce 特例；在渲染分支中加入：

```jsx
phase === 'deduce'
  ? <DeduceStage seq={seq} meta={meta} work={work} onSaved={() => setRefresh((value) => value + 1)} />
  : null
```

- [ ] **Step 4: 用 ObjectFrame 承载章节标题、导航和阶段**

`ChapterStudio` 直接渲染 `ObjectFrame`，actions 中放上一章 / 下一章 / 更多；tabs 传五阶段。把真实末章读取从 `WriteLayout` 上移：

```jsx
const [maxSeq, setMaxSeq] = useState(seq)
useEffect(() => {
  let alive = true
  api.chapters().then((chapters) => {
    if (!alive) return
    const values = Array.isArray(chapters) ? chapters.map((chapter) => Number(chapter.seq)).filter(Number.isFinite) : []
    setMaxSeq(values.length ? Math.max(...values) : seq)
  }).catch(() => { if (alive) setMaxSeq(seq) })
  return () => { alive = false }
}, [work, seq])
```

上一章使用 `Math.max(1, seq - 1)`；下一章按钮在 `seq >= maxSeq` 时禁用。归档进入更多菜单。

- [ ] **Step 5: 将简报 / 关联 / 北极星放入一个右栏辅助页**

```jsx
export function ChapterAuxPanel({ seq }) {
  const [tab, setTab] = useState('brief')
  const items = [
    { value: 'brief', label: '简报' },
    { value: 'frame', label: '关联' },
    { value: 'northstar', label: '北极星' },
  ]
  return <div className="flex h-full min-h-0 flex-col p-3">
    <Tabs ariaLabel="章节辅助" value={tab} onValueChange={setTab} items={items} />
    <div className="min-h-0 flex-1 overflow-auto pt-3">
      {tab === 'brief' && <BriefPanel seq={seq} />}
      {tab === 'frame' && <FramePanel chapter={seq} />}
      {tab === 'northstar' && <NorthStarPanel seq={seq} />}
    </div>
  </div>
}
```

(2026-07-11 修正:RightDock 无 work 形参,面板走全局 WORK 惯例,避免碰在途 FourPaneShell)

在 `RightDock` 仅当 `seq != null` 时增加一个 `context` capability。

- [ ] **Step 6: 移除 WriteLayout 内第二套章导航和 AppRail 阶段插槽**

保留 `WriteLayout` 的 `chapter` 同步和未保存保护；删除只为内部上一章 / 下一章按钮服务的 UI 与死状态。删除 `ChapterStudio.useTopbarSlot` 与 import；`App.jsx` 删除 `topbarExtra` state 和 `extra` prop；`BinderLayout` 删除 `onTopbarSlot` prop 以及 `TopbarSlotProvider` 包裹；`AppRail` 删除 `extra` 参数和渲染。`TopbarSlotContext.jsx` 暂不删除，待 Task 11 用 `rg` 确认零调用后再决定是否清理。

- [ ] **Step 7: 运行章节专项测试**

Run: `cd scribe3/web && npx vitest run src/__tests__/chapterStudio-routing.test.jsx src/__tests__/chapterStudio-topbar.test.jsx src/__tests__/writeLayout-phase.test.jsx src/__tests__/deduceStage-layout.test.jsx src/__tests__/writeChat-phase.test.jsx`

Expected: PASS；五阶段可达，演绎复用同一 `DeduceStage`，DOM 只有一套章节导航。

- [ ] **Step 8: Checkpoint**

Run: `git diff --check -- scribe3/web/src/ChapterStudio.jsx scribe3/web/src/WriteLayout.jsx scribe3/web/src/AppRail.jsx scribe3/web/src/App.jsx scribe3/web/src/BinderLayout.jsx scribe3/web/src/ChapterAuxPanel.jsx scribe3/web/src/studioDocks.jsx`

Expected: 无输出。报告变更，不 commit。

(后续任务:prev/next 应取章列表相邻项而非 ±1,规避归档 seq 空洞;maxSeq 已拉全量列表可复用)

---

### Task 8: 右栏作用域、真实 Badge 与统一异步状态

**Files:**
- Modify: `scribe3/web/src/studioDocks.jsx`
- Modify: `scribe3/web/src/ChiefDock.jsx`
- Modify: `scribe3/web/src/__tests__/chiefDock-ui.test.jsx`
- Modify: `scribe3/web/src/__tests__/chiefDock-thread-continuity.test.jsx`
- Create: `scribe3/web/src/__tests__/rightDock-scope.test.jsx`

**Interfaces:**
- Extends right capability: `{ scope: 'object'|'chapter'|'global' }`。
- Preserves: chief / selection / versions / pilot / inbox keys and existing APIs。
- Adds: context key from Task 7。

- [ ] **Step 1: 写作用域和 Badge 失败测试**

```jsx
it('separates object tools from global inbox', async () => {
  render(<RightDock sel={{ mode: 'node', node: { type: 'chapter', ref: 1 } }} seq={1} />)
  expect(screen.getByRole('group', { name: '当前对象' })).toBeInTheDocument()
  expect(screen.getByRole('group', { name: '全局' })).toContainElement(screen.getByRole('button', { name: /收件箱/ }))
})

it('does not turn inbox request failure into zero pending items', async () => {
  api.inbox.mockRejectedValue(new Error('offline'))
  render(<RightDock seq={1} />)
  expect(await screen.findByLabelText('收件箱状态未知')).toBeInTheDocument()
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/__tests__/rightDock-scope.test.jsx src/__tests__/chiefDock-ui.test.jsx src/__tests__/chiefDock-thread-continuity.test.jsx`

Expected: FAIL，右栏没有作用域组，失败被静默成无 Badge。

- [ ] **Step 3: 实现作用域和未知状态**

将 `inboxCount` 初值改为 `undefined`，失败改为 `null`；`null` 显示状态未知图标和可访问名称，不显示数字 0。右侧 `Rail` 按 object / chapter / global 渲染分隔组，但保留原 key，防止偏好失效。

- [ ] **Step 4: 迁移 Pilot / Versions / Inbox 的 loading 与 error 到 AsyncState**

只迁移展示层，不改轮询、恢复和 API 调用；错误给出重试，危险恢复继续使用 `ConfirmDialog`。

- [ ] **Step 5: 运行右栏测试**

Run: `cd scribe3/web && npx vitest run src/__tests__/rightDock-scope.test.jsx src/__tests__/chiefDock-ui.test.jsx src/__tests__/chiefDock-thread-continuity.test.jsx src/ui/Dialog.test.jsx`

Expected: PASS。

- [ ] **Step 6: Checkpoint**

Run: `git diff --check -- scribe3/web/src/studioDocks.jsx scribe3/web/src/ChiefDock.jsx scribe3/web/src/__tests__/rightDock-scope.test.jsx`

Expected: 无输出。报告变更，不 commit。

---

### Task 9: 作品库、设定库和素材库统一组件

**Files:**
- Modify: `scribe3/web/src/Library.jsx`
- Modify: `scribe3/web/src/CodexNew.jsx`
- Modify: `scribe3/web/src/CodexDetail.jsx`
- Modify: `scribe3/web/src/Materials.jsx`
- Modify: `scribe3/web/src/MaterialNetwork.jsx`
- Create: `scribe3/web/src/__tests__/library-accessibility.test.jsx`
- Modify: `scribe3/web/src/__tests__/codex-lifecycle-delete.test.jsx`
- Modify: `scribe3/web/src/__tests__/materials-workbench.test.jsx`
- Modify: `scribe3/web/src/__tests__/material-import-trust.test.jsx`

**Interfaces:**
- Consumes: Button / Field / Dialog / AsyncState / ObjectFrame。
- Preserves: 作品、设定、素材 CRUD 和 provenance API。
- Preserves names: 设定库 / 素材库。

- [ ] **Step 1: 写作品卡与字段语义失败测试**

```jsx
it('does not nest delete interaction inside the open-work button', () => {
  render(<Library works={[{ slug: 'book-a', title: '书 A' }]} reload={() => Promise.resolve()} onSelect={() => {}} />)
  const open = screen.getByRole('button', { name: /打开书 A/ })
  const remove = screen.getByRole('button', { name: /删除书 A/ })
  expect(open.contains(remove)).toBe(false)
})

it('associates codex field labels with inputs', () => {
  render(<CodexNew catType="character" label="角色" />)
  expect(screen.getByRole('textbox', { name: '名称' })).toBeInTheDocument()
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/__tests__/library-accessibility.test.jsx src/__tests__/codex-lifecycle-delete.test.jsx src/__tests__/materials-workbench.test.jsx src/__tests__/material-import-trust.test.jsx`

Expected: FAIL，作品卡仍有嵌套交互，部分字段 Label 未关联。

- [ ] **Step 3: 迁移作品库**

将作品卡拆成主打开按钮与独立更多菜单；加载失败显示重试，空库显示“新建第一部作品”。1280 / 1440 / 1600 使用稳定网格，不把内容限制在左上角窄列。

- [ ] **Step 4: 迁移设定表单**

用 `Field` 包装所有 Input / Textarea；只读值用语义文本，进入编辑用明确按钮。保存显示 saving / saved / error，不把请求失败解释为“可能已删除”。

- [ ] **Step 5: 迁移素材工作台**

保持素材为非正典材料；统一来源、类型、引用和“用在哪”的元数据节奏。素材网络保留 degraded 提示并增加列表入口，不改图数据 API。

- [ ] **Step 6: 运行页面专项测试**

Run: `cd scribe3/web && npx vitest run src/__tests__/library-accessibility.test.jsx src/__tests__/codex-lifecycle-delete.test.jsx src/__tests__/materials-workbench.test.jsx src/__tests__/material-import-trust.test.jsx`

Expected: PASS。

- [ ] **Step 7: Checkpoint**

Run: `git diff --check -- scribe3/web/src/Library.jsx scribe3/web/src/CodexNew.jsx scribe3/web/src/CodexDetail.jsx scribe3/web/src/Materials.jsx scribe3/web/src/MaterialNetwork.jsx`

Expected: 无输出。报告变更，不 commit。

---

### Task 10: 工艺目录、搜索和校验只展示真实状态

**Files:**
- Modify: `scribe3/web/src/layout/capabilityTree.js`
- Modify: `scribe3/web/src/layout/CapabilityDirectories.jsx`
- Modify: `scribe3/web/src/layout/CapabilityDetailPanes.jsx`
- Modify: `scribe3/web/src/capabilities/search/SearchDirectory.jsx`
- Modify: `scribe3/web/src/capabilities/search/SearchDetail.jsx`
- Modify: `scribe3/web/src/capabilities/issues/IssueDirectory.jsx`
- Modify: `scribe3/web/src/capabilities/issues/IssueDetail.jsx`
- Modify: `scribe3/web/src/layout/__tests__/directoryPane-capabilities.test.jsx`
- Modify: `scribe3/web/src/__tests__/global-search.test.jsx`
- Modify: `scribe3/web/src/__tests__/issue-ledger.test.jsx`

**Interfaces:**
- Keeps: capability group labels, meanings and constraints as structural copy。
- Removes: hard-coded business counts, fake rows and action arrays without handlers。
- Produces: live count or `undefined`; never substitutes demo numbers。

- [ ] **Step 1: 写无假数据失败测试**

```jsx
it('does not show configured demo counts as live data', () => {
  render(<CapabilityDirectory capability="promise" seq={3} onSelectItem={() => {}} />)
  expect(screen.queryByText(/超期 4/)).not.toBeInTheDocument()
  expect(screen.queryByText(/已回收 19/)).not.toBeInTheDocument()
})

it('does not render action buttons without handlers', () => {
  render(<CapabilityGroupDetailPane node={{ capability: 'promise', ref: { group: 'open' }, label: '待回收' }} />)
  expect(screen.queryByRole('button', { name: '查看全部命中正文' })).not.toBeInTheDocument()
})
```

- [ ] **Step 2: 运行失败测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/directoryPane-capabilities.test.jsx src/__tests__/global-search.test.jsx src/__tests__/issue-ledger.test.jsx`

Expected: FAIL，静态配置仍进入业务数量和动作 UI。

- [ ] **Step 3: 分离结构配置和 live payload**

`capabilityTree.js` 只保留 group id / label / meaning / constraint / scope。数量、rows、related 和 actions 必须由 API payload 提供；值不存在时不渲染数量和按钮。

- [ ] **Step 4: 顶部搜索统一触发左侧搜索工作区**

复用 `s3-open-capability`，顶部搜索与 `⌘K` 发送 `{ capability: 'search', focus: true }`；`SearchDirectory` 接收事件后聚焦其唯一搜索框。不创建第二份结果 store。

- [ ] **Step 5: 校验定位失败给出真实恢复路径**

`IssueDetail` 定位失败时显示“正文已变化，重新检查后再定位”，提供 `onRecheck`；不能静默或定位到错误范围。

- [ ] **Step 6: 运行工艺 / 搜索 / 校验测试**

Run: `cd scribe3/web && npx vitest run src/layout/__tests__/directoryPane-capabilities.test.jsx src/__tests__/global-search.test.jsx src/__tests__/issue-ledger.test.jsx src/editor/GuardDecoration.test.js`

Expected: PASS。

- [ ] **Step 7: Checkpoint**

Run: `git diff --check -- scribe3/web/src/layout/capabilityTree.js scribe3/web/src/layout/CapabilityDirectories.jsx scribe3/web/src/layout/CapabilityDetailPanes.jsx scribe3/web/src/capabilities`

Expected: 无输出。报告变更，不 commit。

---

### Task 11: 全局视图的键盘等价路径与 UI 静态清理

**Files:**
- Modify: `scribe3/web/src/views/AtlasView.jsx`
- Modify: `scribe3/web/src/views/TimelineView.jsx`
- Modify: `scribe3/web/src/views/InsightView.jsx`
- Modify: `scribe3/web/src/MaterialNetwork.jsx`
- Create: `scribe3/web/src/__tests__/global-view-accessibility.test.jsx`
- Create: `scribe3/web/src/__tests__/pc-ui-static-contract.test.js`

**Interfaces:**
- Produces: 每个 Canvas / WebGL 视图旁的命名列表或文本摘要。
- Preserves: 原图谱、时间线、洞察数据和节点点击 API。
- Enforces: 不新增 10 / 11px、不新增结构性 Emoji、不新增无键盘路径的 `div onClick`。

- [ ] **Step 1: 写全局视图等价路径失败测试**

```jsx
it.each([
  ['图谱对象列表', <AtlasView />],
  ['时间线事件列表', <TimelineView />],
  ['洞察数据摘要', <InsightView />],
])('exposes %s beside the visual canvas', (name, view) => {
  render(view)
  expect(screen.getByRole('region', { name })).toBeInTheDocument()
})
```

- [ ] **Step 2: 写静态合同测试**

```javascript
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const files = []
const walk = (dir) => {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name)
    const stat = fs.statSync(full)
    if (stat.isDirectory() && name !== '__tests__') walk(full)
    if (stat.isFile() && /\.(jsx|js)$/.test(name) && !/\.test\./.test(name)) files.push(full)
  }
}
walk(root)

describe('PC UI static contract', () => {
  it('contains no 10px or 11px utility in production JSX', () => {
    const bad = files.filter((file) => /text-f10|text-f11/.test(fs.readFileSync(file, 'utf8')))
    expect(bad).toEqual([])
  })
  it('contains no structural emoji', () => {
    const bad = files.filter((file) => /[🔒📍🔥⚠✕×]/u.test(fs.readFileSync(file, 'utf8')))
    expect(bad).toEqual([])
  })
})
```

- [ ] **Step 3: 运行失败测试并记录剩余清单**

Run: `cd scribe3/web && npx vitest run src/__tests__/global-view-accessibility.test.jsx src/__tests__/pc-ui-static-contract.test.js`

Expected: FAIL，并列出仍含 10 / 11px 或结构性 Emoji 的生产文件。

- [ ] **Step 4: 为视图增加列表 / 摘要**

列表使用与 Canvas 同一数据数组；选择列表项调用与图形节点相同的 `onNavigateToObject`。热力图提供文本摘要，不能只依赖颜色和不可聚焦 `title`。

- [ ] **Step 5: 机械清理剩余小字、Emoji 和伪按钮**

- `text-f10` → `text-meta`。
- `text-f11` → `text-meta` 或 `text-helper`，按信息重要度选择。
- 结构性 Emoji → Lucide 图标 + 可见文字。
- `div onClick` → `button`；如果容器仍需布局，按钮使用 `w-full text-left`。
- JS 平滑滚动和图谱动画读取 `matchMedia('(prefers-reduced-motion: reduce)')`。

- [ ] **Step 6: 运行视图、静态和相关页面测试**

Run: `cd scribe3/web && npx vitest run src/__tests__/global-view-accessibility.test.jsx src/__tests__/pc-ui-static-contract.test.js src/__tests__/cross-view-navigation.test.jsx src/__tests__/cross-view-real-views.test.jsx src/__tests__/insightView-error.test.jsx`

Expected: PASS。

- [ ] **Step 7: Checkpoint**

Run: `git diff --check -- scribe3/web/src/views scribe3/web/src/MaterialNetwork.jsx scribe3/web/src/__tests__/global-view-accessibility.test.jsx scribe3/web/src/__tests__/pc-ui-static-contract.test.js`

Expected: 无输出。报告变更，不 commit。

---

### Task 12: 全量测试、构建与真实 PC 浏览器验收

**Files:**
- Modify: `scribe3/web/pw_layout.mjs`
- Modify: `docs/superpowers/specs/2026-07-10-scribe3-PC-UI系统整修-design.md` — 仅在实现事实与规格需同步时更新状态，不改设计边界。

**Interfaces:**
- Produces: 只读 PC 运行时报告，覆盖 1280×720、1440×900、1600×900，浅色和深色。
- Preserves: 浏览器测试阻断 POST / PATCH / DELETE；不得修改真实作品数据。

- [ ] **Step 1: 先修复过期 Playwright 选择器**

将旧 `[data-testid="entry-rail"]` 改为 `[data-testid="left-entry-rail"]`；入口按钮通过 `role=button` 和 `aria-label` 定位，不依赖可见短文字。

- [ ] **Step 2: 为三种 PC 视口和双主题添加断言**

```javascript
import fs from 'node:fs'

const VIEWPORTS = [
  { name: '1280x720', width: 1280, height: 720 },
  { name: '1440x900', width: 1440, height: 900 },
  { name: '1600x900', width: 1600, height: 900 },
]
const THEMES = ['light', 'dark']

fs.mkdirSync('artifacts', { recursive: true })

for (const viewport of VIEWPORTS) {
  for (const theme of THEMES) {
    await p.setViewportSize({ width: viewport.width, height: viewport.height })
    await p.evaluate((value) => localStorage.setItem('s3-theme', value), theme)
    await p.reload()
    await p.locator('[data-testid="four-col"]').waitFor()
    const detail = await p.locator('[data-testid="detail-panel"]').boundingBox()
    const right = await p.locator('[data-testid="right-panel"]').boundingBox()
    if (!detail || detail.width < 600) throw new Error(`${viewport.name}/${theme}: detail too narrow`)
    if (!right || right.x < detail.x + detail.width - 1) throw new Error(`${viewport.name}/${theme}: panels overlap`)
    await p.screenshot({ path: `artifacts/pc-ui-${viewport.name}-${theme}.png`, fullPage: true })
  }
}
```

在首次 `goto` 前安装只读拦截：

```javascript
await p.route('**/api/**', async (route) => {
  const method = route.request().method()
  if (['GET', 'HEAD', 'OPTIONS'].includes(method)) await route.continue()
  else await route.abort('blockedbyclient')
})
```

- [ ] **Step 3: 运行全部前端测试**

Run: `cd scribe3/web && npm run test`

Expected: Vitest exit 0，0 failed。

- [ ] **Step 4: 运行前端构建**

Run: `cd scribe3/web && npm run build`

Expected: Vite exit 0，无 unresolved import、TDZ 或 CSS 编译错误。

- [ ] **Step 5: 运行只读端到端检查**

Run: `cd scribe3/web && npm run e2e:readonly`

Expected: exit 0；无写请求、无控制台 error。

- [ ] **Step 6: 运行 PC 四栏浏览器验收**

Run: `cd scribe3/web && node pw_layout.mjs v2`

Expected:

- 三种 PC 视口、双主题均完成。
- 目录点击后仍常驻。
- 详情宽度不低于 600px，右栏与详情不重叠。
- DOM 只有一套章节导航和五个阶段。
- 图谱 / 时间线 / 洞察返回后恢复原选择。
- 浏览器控制台无 error。
- 所有非 GET / HEAD / OPTIONS 请求在只读验收中被阻断。

- [ ] **Step 7: 手工键盘验收**

按顺序验证：全局栏 → 入口 → 目录 → 详情 → 右栏；Tabs 方向键；Dialog Escape 与焦点恢复；`⌘K` 搜索；`⌘S` 保存；200% 缩放下收起目录 / 右栏后关键功能仍可达。

- [ ] **Step 8: 最终范围与 diff 审计**

Run: `git diff --check`

Expected: 无输出。

Run: `git status --short`

Expected: 只包含本计划文件、已确认 UI 文件，以及实施开始前已经存在且未被覆盖的 Context Memory 在途文件。

- [ ] **Step 9: 报告 checkpoint**

报告：改动文件、专项测试、全量测试、构建、浏览器视口 / 主题、失败与未完成项。未经用户明确授权，不 commit、不 push。

---

## Execution Order and Stop Conditions

严格按 Task 1 → 12 顺序执行。以下任一情况立即停止当前任务并报告：

- Context Memory 在途测试在 Task 5 前不是绿色。
- 需要覆盖或回退用户未提交改动。
- 需要新增后端 API 才能显示某个数量；默认隐藏该数量。
- 专项测试、全量测试、构建或真实浏览器验证失败。
- 1280×720 出现正文 / 工具栏 / 右栏重叠。
- 浅色或深色关键文字低于 4.5:1。
- 写作、素材、主编、选择环、版本、Pilot 或收件箱真实流程回归。

## Implementation Completion Evidence

实施完成时必须同时提供：

1. Task 1–12 checklist 状态。
2. `npm run test` 的当次通过数量和 0 failed 证据。
3. `npm run build` exit 0 证据。
4. `npm run e2e:readonly` exit 0 证据。
5. 1280 / 1440 / 1600、浅色 / 深色六张运行时截图路径。
6. 键盘与 200% 缩放验收结果。
7. `git diff --check` 无输出。
8. 未修改的用户在途文件清单。
9. 尚未 commit / push 的明确说明，除非用户另行授权。
