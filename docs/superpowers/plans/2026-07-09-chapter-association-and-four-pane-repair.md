# Chapter Association And Four Pane Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把章页“限知帧”升级为“关联”，补齐章级本章设定/本章素材，并恢复 V2 四栏缩放折叠与手稿二栏 demo 结构。

**Architecture:** `ChapterStudio` 只改阶段入口与 props 传递；`FramePanel` 保持内部组件但承担章级关联工作台；`FourPaneShell` 恢复 `react-resizable-panels` 的 collapsible/ref 契约；`ManuscriptDirectory` 作为栏2手稿目录的唯一生产实现。

**Tech Stack:** React 18, Vite, Vitest, Testing Library, `react-resizable-panels`, existing scribe3 REST API.

## Global Constraints

- 所有交互说明、文档和最终回复使用简体中文。
- 本轮不自动 commit；实现验收后由用户决定是否提交。
- 不回退已提交基线，不改与本任务无关的功能。
- 生产代码先写失败测试，再实现。
- 旧三栏 flag 关闭路径必须保持可用。

---

### Task 1: 章页入口改名为“关联”

**Files:**
- Modify: `scribe3/web/src/ChapterStudio.jsx`
- Modify: `scribe3/web/src/__tests__/chapterStudio-topbar.test.jsx`
- Modify: `scribe3/web/src/__tests__/framePanel.test.jsx`

**Interfaces:**
- Consumes: existing phase key `frame`
- Produces: visible label `关联`, unchanged key `frame`

- [ ] **Step 1: Write failing tests**

Add assertions:

```jsx
expect(screen.getByRole('button', { name: '关联' })).toBeTruthy()
expect(screen.queryByRole('button', { name: '限知帧' })).toBeNull()
```

In `framePanel.test.jsx`, expect page title:

```jsx
expect(screen.getByText('第 3 章关联树')).toBeTruthy()
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- src/__tests__/chapterStudio-topbar.test.jsx src/__tests__/framePanel.test.jsx
```

Expected: FAIL because current UI still renders `限知帧` and `限知帧树`.

- [ ] **Step 3: Implement**

Change only display labels:

```jsx
{ key: 'frame', label: '关联', icon: Eye }
```

In `FramePanel`, update visible heading to `第 {chapter} 章关联树`; keep aria labels for backward compatibility only where tests or screen readers need it.

- [ ] **Step 4: Verify GREEN**

Run the same test command. Expected: PASS.

### Task 2: 关联页补齐章级设定与素材

**Files:**
- Modify: `scribe3/web/src/ChapterStudio.jsx`
- Modify: `scribe3/web/src/FramePanel.jsx`
- Modify: `scribe3/web/src/__tests__/framePanel.test.jsx`

**Interfaces:**
- Consumes: `api.materialRefsByChapter(chapter)`, `api.facts(chapter)`, `api.characterRelations(chapter)`, `api.motifInstances(chapter, work)`, `api.promisesLedger(work)`, `api.issues(chapter)`
- Produces: `onSelectNode(node)` calls for `material`, `character`, `proposition`, `promise_view`, `motif_view`, `review_issue`

- [ ] **Step 1: Write failing tests**

Mock the new API calls in `framePanel.test.jsx`:

```jsx
apiMock.materialRefsByChapter.mockResolvedValue([
  { material_id: 'm1', title: '铜炉制度', kind: 'worldbuilding', phase: 'outline' },
])
apiMock.facts.mockResolvedValue([
  { id: 'p1', entity: 'role:柳怀玉', attribute: '身份', value: '纸扎匠', chapter: 3 },
])
apiMock.characterRelations.mockResolvedValue([])
apiMock.motifInstances.mockResolvedValue([{ id: 'motif:命纸:3', motif_id: '命纸', title: '命与纸', chapter: 3 }])
apiMock.promisesLedger.mockResolvedValue({ open: [], closed: [], red_herring: [] })
apiMock.issues.mockResolvedValue({ issues: [] })
```

Assert:

```jsx
expect(screen.getByRole('button', { name: /本章设定/ })).toBeTruthy()
expect(screen.getByRole('button', { name: /本章素材/ })).toBeTruthy()
fireEvent.click(screen.getByRole('button', { name: /本章素材/ }))
fireEvent.click(screen.getByRole('button', { name: /铜炉制度/ }))
expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({ type: 'material', ref: 'm1' }))
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- src/__tests__/framePanel.test.jsx
```

Expected: FAIL because current `FramePanel` has no `本章设定`/`本章素材`.

- [ ] **Step 3: Implement**

Pass `work`, `meta`, and `onSelectNode` from `ChapterStudio` to `FramePanel`.

Inside `FramePanel`:

- fetch the new association sources in effects keyed by `work/chapter`
- derive sections `codex`, `materials`, `promise`, `motif`, `review`, plus existing limit-knowledge sections
- build nodes:

```js
{ id: `material:${id}`, type: 'material', ref: id, label: title, meta: { kind } }
{ id: `character:${name}`, type: 'character', ref: name, label: name }
{ id: `proposition:${id}`, type: 'proposition', ref: id, label }
```

Use `onSelectNode(node)` for external detail jumps; use existing inline detail for limit facts.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- src/__tests__/framePanel.test.jsx
```

Expected: PASS.

### Task 3: V2 四栏恢复二栏/四栏折叠缩放

**Files:**
- Modify: `scribe3/web/src/layout/FourPaneShell.jsx`
- Modify: `scribe3/web/src/layout/__tests__/fourPaneShell.test.jsx`

**Interfaces:**
- Consumes: existing `Rail` active toggle behavior
- Produces: `data-testid="directory-restore-button"`, `data-testid="right-restore-button"`, collapsible directory/right panels

- [ ] **Step 1: Write failing tests**

Add tests:

```jsx
fireEvent.click(screen.getByRole('button', { name: '手稿' }))
expect(screen.queryByTestId('col-directory')).toBeNull()
fireEvent.click(screen.getByTestId('directory-restore-button'))
expect(screen.getByTestId('col-directory')).toBeTruthy()
```

For right panel:

```jsx
fireEvent.click(screen.getByTestId('right-collapse-button'))
expect(screen.queryByTestId('chief')).toBeNull()
fireEvent.click(screen.getByTestId('right-restore-button'))
expect(screen.getByTestId('chief')).toBeTruthy()
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- src/layout/__tests__/fourPaneShell.test.jsx
```

Expected: FAIL because V2 panels are not collapsible.

- [ ] **Step 3: Implement**

Add `usePanelRef` refs in `FourPaneShell`. Add state:

```js
const [directoryCollapsed, setDirectoryCollapsed] = useState(false)
const [rightCollapsed, setRightCollapsed] = useState(false)
```

Use `collapsible collapsedSize="0%" panelRef={directoryRef}` and `panelRef={rightRef}`. Persist under:

```js
`s3.${work || 'default'}.directoryCollapsed`
`s3.${work || 'default'}.rightCollapsed`
```

Render restore buttons inside detail panel when collapsed.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- src/layout/__tests__/fourPaneShell.test.jsx
```

Expected: PASS.

### Task 4: 手稿二栏按 demo 结构补齐

**Files:**
- Modify: `scribe3/web/src/layout/ManuscriptDirectory.jsx`
- Modify: `scribe3/web/src/layout/__tests__/directoryPane-manuscript.test.jsx`

**Interfaces:**
- Consumes: `entry.source` manuscript tree, `sel`, `seq`, `onSelectItem`, `onJumpChapter`
- Produces: stable `data-testid` values for header, tools, volume list, current chapter

- [ ] **Step 1: Write failing tests**

Assert:

```jsx
expect(screen.getByTestId('manuscript-directory')).toBeTruthy()
expect(screen.getByTestId('manuscript-current-card').textContent).toContain('当前')
expect(screen.getByTestId('manuscript-book-tools').textContent).toContain('全书大纲')
expect(screen.getByTestId('manuscript-volume-list').textContent).toContain('第一卷')
```

After clicking chapter:

```jsx
expect(screen.getByTestId('directory-sticky-header')).toBeTruthy()
expect(screen.getByTestId('manuscript-volume-list')).toBeTruthy()
```

- [ ] **Step 2: Verify RED**

Run:

```bash
npm test -- src/layout/__tests__/directoryPane-manuscript.test.jsx
```

Expected: FAIL for missing test ids and current-card structure.

- [ ] **Step 3: Implement**

Wrap `ManuscriptDirectory` with:

```jsx
<div data-testid="manuscript-directory" className="h-full min-h-0 flex flex-col">
```

Expose current card and book tools with test ids. Keep visual style close to demo: sticky header, compact chips, internal scroll, no nested cards.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm test -- src/layout/__tests__/directoryPane-manuscript.test.jsx
```

Expected: PASS.

### Task 5: Regression And Browser Verification

**Files:**
- No production source expected unless earlier tasks reveal integration failures.

**Interfaces:**
- Verifies complete behavior across chapter topbar, frame/association, four pane shell, manuscript directory.

- [ ] **Step 1: Run focused tests**

```bash
npm test -- src/__tests__/framePanel.test.jsx src/__tests__/chapterStudio-topbar.test.jsx src/layout/__tests__/fourPaneShell.test.jsx src/layout/__tests__/directoryPane-manuscript.test.jsx
```

Expected: all PASS.

- [ ] **Step 2: Run build**

```bash
npm run build
```

Expected: build succeeds; existing large chunk warning is acceptable.

- [ ] **Step 3: Browser smoke**

Open `http://127.0.0.1:3311/`, choose `纸命`, open chapter 2.

Verify:

- Topbar shows `关联`, not `限知帧`
- `关联` page has `本章设定` and `本章素材`
- Clicking material opens material detail in栏3 while栏2 remains
- Clicking left active tab collapses/restores栏2
- Right dock can collapse/restore
- Hand manuscript directory still shows demo header/tools/volume list

- [ ] **Step 4: Update CodeGraph**

```bash
codegraph sync .
codegraph status .
```

Expected: `Index is up to date`.

## Self-Review

- Spec coverage: tasks cover tab rename, chapter settings/materials, V2 collapse, manuscript demo directory, regression/browser verification.
- 占位扫描: 没有未展开的实施步骤。
- Type consistency: node shapes match current `DetailPane` routing: `material`, `character`, `proposition`, `promise_view`, `motif_view`, `review_issue`.
