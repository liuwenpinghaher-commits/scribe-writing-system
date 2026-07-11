# Context Tree UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已确认的 demo UI 落到真实二栏/三栏:二栏用分类树,三栏用分类总览或具体详情。

**Architecture:** 保持 FourPaneShell 的栏1/栏2/栏3/栏4边界不变。新增一份能力上下文树配置,由 `CapabilityDirectories.jsx` 负责二栏分类/条目输出,由 `CapabilityDetailPanes.jsx` 负责三栏分类总览;原伏笔/母题/演绎真实详情继续在具体条目节点上渲染。

**Tech Stack:** React, Vite, Vitest, Testing Library, Tailwind class utilities.

## Global Constraints

- 不改左侧 rail 能力集合。
- 不改素材库、设定库、手稿目录真实能力。
- 不 commit,不 push,不回退无关改动。
- 先写失败测试,再实现。

---

### Task 1: Lock Capability Group Overview Behavior

**Files:**
- Modify: `scribe3/web/src/layout/__tests__/directoryPane-capabilities.test.jsx`
- Modify: `scribe3/web/src/__tests__/detailPane-capabilities.test.jsx`

**Interfaces:**
- Produces: `capability_group` node contract: `{ id, type: 'capability_group', capability, label, meta, payload }`
- Produces: leaf nodes keep existing types such as `deduce_view`, `promise_view`, `motif_view`.

- [ ] **Step 1: Write failing directory test**

Add a test asserting that clicking a capability group sends `type: 'capability_group'` and clicking a child sends the existing leaf type.

- [ ] **Step 2: Write failing detail test**

Add a test asserting that `DetailPane` renders group overview for `capability_group`.

- [ ] **Step 3: Run focused tests and confirm failure**

Run: `cd scribe3/web && npm test -- src/layout/__tests__/directoryPane-capabilities.test.jsx src/__tests__/detailPane-capabilities.test.jsx --runInBand`

Expected: tests fail because `capability_group` is not implemented.

### Task 2: Implement Column 2 Context Tree

**Files:**
- Modify: `scribe3/web/src/layout/CapabilityDirectories.jsx`

**Interfaces:**
- Consumes: `DIRECTORY_CONFIG[capability].groups`.
- Produces: group buttons and child item buttons in a dense tree UI.

- [ ] **Step 1: Replace flat rows with groups**

Keep existing row ids/types, but organize them under groups. Clicking a group emits `capability_group`; clicking a child emits existing leaf node.

- [ ] **Step 2: Preserve legacy expectations**

Ensure row labels such as `场景真相`, `本章要收`, `本章触及` are still clickable by accessible name.

- [ ] **Step 3: Run directory test**

Run: `cd scribe3/web && npm test -- src/layout/__tests__/directoryPane-capabilities.test.jsx --runInBand`

Expected: pass.

### Task 3: Implement Column 3 Group Overview

**Files:**
- Modify: `scribe3/web/src/layout/CapabilityDetailPanes.jsx`
- Modify: `scribe3/web/src/DetailPane.jsx`

**Interfaces:**
- Consumes: `node.type === 'capability_group'`.
- Produces: group overview UI with title, path, constraint copy, related scope and actions.

- [ ] **Step 1: Add `CapabilityGroupDetailPane`**

Render the same UI language as the demo: path, category title, meaning, writing constraint, scope, related chips, and action row.

- [ ] **Step 2: Route `capability_group` in `DetailPane`**

Add a route before specific capability nodes.

- [ ] **Step 3: Run detail test**

Run: `cd scribe3/web && npm test -- src/__tests__/detailPane-capabilities.test.jsx --runInBand`

Expected: pass.

### Task 4: Verify App Surface

**Files:**
- Verify only unless fixes are required.

- [ ] **Step 1: Run focused tests**

Run: `cd scribe3/web && npm test -- src/layout/__tests__/directoryPane-capabilities.test.jsx src/__tests__/detailPane-capabilities.test.jsx --runInBand`

- [ ] **Step 2: Run build**

Run: `cd scribe3/web && npm run build`

- [ ] **Step 3: Browser smoke**

Open the running app, switch to 演绎/伏笔/母题, verify 二栏分类点击 changes 三栏 to group overview and leaf click opens detail.
