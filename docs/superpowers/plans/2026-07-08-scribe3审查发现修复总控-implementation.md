# Scribe3 审查发现修复总控 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 2026-07-08 全系统审查总报告中的 P1 可信性问题关闭,并把左栏能力、二栏目录、三栏详情、右栏上下文补成可验证的生产闭环。

**Architecture:** 先建立测试分档和验收护栏,再按 `EntryRail -> DirectoryPane -> DetailPane -> RightDock context` 的生产路由修复能力闭环。所有会改变数据可信性的修复先从后端契约和前端失败态开始,所有 UI 迁移必须复用旧真实面板能力,不能用静态占位替换旧能力。

**Tech Stack:** FastAPI/Pydantic + SurrealStore, React 18/Vite/Vitest/Testing Library, Playwright e2e, CodeGraph indexed repo.

## Global Constraints

- 全部交互说明和交付总结使用简体中文;代码标识符和文件路径保留原文。
- 不回退、不清理工作区中已有的无关改动。
- 不自动 commit/push/建分支;每批完成后只报告可提交范围,除非用户明确要求提交。
- 写真实作品的 e2e 不能进入默认 `npm test`;必须显式 snapshot/restore 并复核零残留。
- 查看动作不能隐式写数据;删除、导入、主编写作必须能解释实际副作用。
- 新四栏壳只能接真实能力,不能用 mockup 或静态占位替代原系统功能。
- 每个修复包至少有定点测试;批次收尾必须跑对应后端、前端和浏览器验收。

---

## File Structure

- Modify: `scribe3/web/package.json`  
  负责声明 e2e 分档脚本,保持 `npm test` 只跑 vitest。
- Create: `scribe3/web/e2e/README.md`  
  负责说明只读、写入带快照、破坏性手工三档验收边界和运行顺序。
- Modify: `scribe3/web/src/WriteChat.jsx`  
  负责接收 `phase` prop 并传给 `api.chatWrite`。
- Modify: `scribe3/web/src/WriteLayout.jsx`  
  负责正文阶段把 `phase="final"` 传给 `WriteChat`,并补错误态入口。
- Create: `scribe3/web/src/__tests__/writeChat-phase.test.jsx`  
  负责证明主编写作请求 payload 带 `phase: "final"`。
- Modify: `scribe3/tests/test_pulse.py` 或 `scribe3/tests/test_purpose_contract.py`  
  负责证明后端 final prompt 保留演绎/scene_truth/deductions 上下文。
- Modify: `scribe3/web/src/DeduceTree.jsx`  
  负责把打开即写改成本地建议 + 显式同步。
- Create: `scribe3/web/src/__tests__/deduceTree-readonly.test.jsx`  
  负责证明挂载不 PATCH,点击同步才 PATCH。
- Modify: `scribe3/store.py`  
  负责对象存在性、impact 计数、素材引用和关系清理/归档支持。
- Modify: `scribe3/app.py`  
  负责对象 lifecycle API、素材导入部分失败返回、素材网络 degraded 返回。
- Create: `scribe3/tests/test_object_lifecycle.py`  
  负责 role/fact/material 删除 impact/404/409 契约。
- Modify: `scribe3/tests/test_app.py` 或 Create: `scribe3/tests/test_material_import_trust.py`  
  负责素材导入 failed/warnings/degraded 契约。
- Modify: `scribe3/web/src/Materials.jsx`  
  负责素材导入部分成功、失败项、网络降级、素材引用账本和列表性能。
- Modify: `scribe3/web/src/ContainerOutline.jsx`  
  负责卷 add/rename/delete 错误态和 retry。
- Modify: `scribe3/web/src/views/InsightView.jsx`  
  负责 quality/progress 的 loading/empty/error/degraded 状态。
- Modify: `scribe3/web/src/AppRail.jsx`, `scribe3/web/src/layout/EntryRail.jsx`, `scribe3/web/src/layout/DirectoryPane.jsx`, `scribe3/web/src/layout/FourPaneShell.jsx`, `scribe3/web/src/layout/CapabilityDirectories.jsx`, `scribe3/web/src/layout/CapabilityDetailPanes.jsx`, `scribe3/web/src/DetailPane.jsx`, `scribe3/web/src/studioDocks.jsx`  
  负责八个左栏能力常驻、work-scoped 偏好、二栏目录和三栏真实详情路由。
- Create: `scribe3/web/src/hooks/useWorkScopedPref.js`  
  负责按 work 隔离 left/right/capability active 偏好。
- Create: `scribe3/web/src/hooks/useCapabilitySelection.js`  
  负责统一 entry/item/target selection 结构。
- Create: `scribe3/web/src/hooks/useIssueLedger.js`  
  负责校验 issue 归一化。
- Modify: `scribe3/web/src/__tests__/*.test.jsx`, `scribe3/web/src/layout/__tests__/*.test.jsx`  
  负责每个能力入口、路由、错误态、搜索、issue、素材引用和横切跳转回归。
- Create: `docs/adr/2026-07-08-scribe3-mcp-multi-work.md`  
  负责 F12 多书联查架构决策。

---

### Task 0: 回归分级与验收护栏

**Files:**
- Modify: `scribe3/web/package.json`
- Create: `scribe3/web/e2e/README.md`

**Interfaces:**
- Consumes: existing e2e scripts under `scribe3/web/e2e/*.mjs`.
- Produces: package scripts `e2e:readonly`, `e2e:writes-with-snapshot`, `e2e:destructive-manual`, and a documented test policy.

- [ ] **Step 1: Write the guardrail documentation first**

Create `scribe3/web/e2e/README.md` with these concrete sections:

```markdown
# Scribe3 Web E2E 分档

## e2e:readonly

只允许打开、切换、查看、搜索、读 network payload,不得创建、编辑、删除、导入提交或保存真实作品。

运行命令:

```bash
npm run e2e:readonly
```

## e2e:writes-with-snapshot

允许写入 `book_c256380e` 第 4 章前提是先运行快照、脚本 finally 恢复、结束后复核章正文、草稿和临时测试数据零残留。

运行命令:

```bash
npm run e2e:writes-with-snapshot
```

## e2e:destructive-manual

删除、导入提交、迁移、真实张力写入和会影响多对象引用的脚本只允许人工单独运行。运行前必须记录目标 work、快照文件、恢复命令和复核命令。

运行命令:

```bash
npm run e2e:destructive-manual
```
```

- [ ] **Step 2: Add package scripts**

Update `scribe3/web/package.json` scripts to include:

```json
{
  "e2e:readonly": "node e2e/qa_batchE.mjs",
  "e2e:writes-with-snapshot": "node e2e/snapshot_ch4.mjs b2 && node e2e/qa_b2.mjs; node e2e/qa_b2_restore.mjs",
  "e2e:destructive-manual": "node -e \"console.error('destructive e2e requires an explicit script name and manual snapshot/restore note'); process.exit(2)\""
}
```

- [ ] **Step 3: Verify script separation**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- --runInBand
npm run e2e:destructive-manual
```

Expected:
- `npm test` still invokes vitest only.
- `e2e:destructive-manual` exits non-zero with the explicit refusal message.

---

### Task 1: 正文 final phase 写作链

**Files:**
- Modify: `scribe3/web/src/WriteChat.jsx`
- Modify: `scribe3/web/src/WriteLayout.jsx`
- Create: `scribe3/web/src/__tests__/writeChat-phase.test.jsx`
- Modify: `scribe3/tests/test_pulse.py` or `scribe3/tests/test_purpose_contract.py`

**Interfaces:**
- Consumes: `api.chatWrite(msg, options)` where `options.phase` is already supported by `scribe3/web/src/api.js`.
- Produces: `WriteChat({ phase })` and `WriteLayout` passing `phase="final"`.

- [ ] **Step 1: Write the failing frontend test**

Create `scribe3/web/src/__tests__/writeChat-phase.test.jsx`:

```jsx
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WriteChat } from '../WriteChat.jsx'
import { api } from '../api.js'

vi.mock('../api.js', () => ({
  api: {
    chatWrite: vi.fn((_msg, opts) => {
      opts.onDone?.()
      return { abort: vi.fn() }
    }),
  },
}))

describe('WriteChat phase', () => {
  it('sends final phase when正文阶段 passes phase=final', async () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const input = screen.getByPlaceholderText(/就当前内容问主编/)
    fireEvent.change(input, { target: { value: '继续写正文' } })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

    await waitFor(() => expect(api.chatWrite).toHaveBeenCalled())
    expect(api.chatWrite.mock.calls[0][1]).toMatchObject({
      chapter: 4,
      focalizer: '崔判',
      phase: 'final',
    })
  })
})
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/writeChat-phase.test.jsx
```

Expected: FAIL because `WriteChat` ignores the `phase` prop or never passes it to `api.chatWrite`.

- [ ] **Step 3: Implement minimal frontend code**

Change `WriteChat` signature and `api.chatWrite` call:

```jsx
export function WriteChat({ chapter, focalizer, seedQuote, phase = '', onProposal, onProposalStart, onProposalChunk }) {
  // ...
  api.chatWrite(finalMsg, {
    chapter,
    focalizer,
    images,
    phase,
    onDelta,
    onTool,
    onProposalStart,
    onProposalChunk,
    onProposal,
    onDone,
    onError,
  })
}
```

Change `WriteLayout` render:

```jsx
<WriteChat
  chapter={chapter}
  focalizer={focalizer}
  seedQuote={seedQuote}
  phase="final"
  onProposal={handleProposal}
  onProposalStart={handleProposalStart}
  onProposalChunk={handleProposalChunk}
/>
```

- [ ] **Step 4: Add backend final prompt assertion**

Add or extend a backend test so it creates a chapter with `scene_truth` and `deductions`, calls the prompt assembly path with `phase="final"`, and asserts the final prompt includes final-phase context names:

```python
def test_final_phase_prompt_keeps_deduction_context(client):
    # Arrange data with scene_truth and one deduction.
    # Act through /chat/write request assembly or the narrow prompt helper used by existing tests.
    # Assert "scene_truth" or the Chinese scene truth label, the deduction character id, and final phase marker are present.
    assert "final" in prompt or "正文" in prompt
    assert "scene_truth" in prompt or "场景真相" in prompt
    assert "role:崔判" in prompt or "崔判" in prompt
```

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/writeChat-phase.test.jsx

cd "<repo-root>"
scribe3/.venv/bin/pytest -q scribe3/tests/test_pulse.py scribe3/tests/test_purpose_contract.py
```

Expected: frontend test passes; backend prompt tests pass.

---

### Task 2: 演绎查看只读化

**Files:**
- Modify: `scribe3/web/src/DeduceTree.jsx`
- Create: `scribe3/web/src/__tests__/deduceTree-readonly.test.jsx`

**Interfaces:**
- Consumes: `api.chapter(seq)`, `api.entities()`, `api.patchChapter(seq, body)`.
- Produces: local inferred suggestions and explicit sync button.

- [ ] **Step 1: Write RED tests**

Create `scribe3/web/src/__tests__/deduceTree-readonly.test.jsx` with two cases:

```jsx
it('does not patch involved_characters on mount', async () => {
  mockChapter({ involved_characters: [], synopsis: '崔判入场' })
  mockEntities([{ id: 'role:崔判', name: '崔判' }])
  render(<DeduceTree seq={4} />)
  await screen.findByText(/检测到可能涉及角色/)
  expect(api.patchChapter).not.toHaveBeenCalled()
})

it('patches involved_characters only after explicit sync', async () => {
  mockChapter({ involved_characters: [], synopsis: '崔判入场' })
  mockEntities([{ id: 'role:崔判', name: '崔判' }])
  render(<DeduceTree seq={4} />)
  fireEvent.click(await screen.findByRole('button', { name: /同步到本章/ }))
  await waitFor(() => expect(api.patchChapter).toHaveBeenCalledWith(4, { involved_characters: ['role:崔判'] }))
})
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/deduceTree-readonly.test.jsx
```

Expected: first test fails because mount currently calls `api.patchChapter`.

- [ ] **Step 3: Implement local suggestion state**

Replace the auto-write effect with:

```jsx
const [inferredInvolved, setInferredInvolved] = useState([])
const [syncingInferred, setSyncingInferred] = useState(false)
const [syncError, setSyncError] = useState('')

useEffect(() => {
  if (!ch || (ch.involved_characters || []).length > 0 || chars.length === 0) {
    setInferredInvolved([])
    return
  }
  const text = `${ch.synopsis || ''}\n${(ch.beats || []).map((b) => b.text || '').join('\n')}\n${ch.scene_truth || ''}`
  const hit = chars.filter((c) => c.name && text.includes(c.name)).map((c) => c.id)
  setInferredInvolved(hit)
  setSyncError('')
}, [ch, chars, seq])

const syncInferred = async () => {
  if (!inferredInvolved.length || syncingInferred) return
  setSyncingInferred(true)
  setSyncError('')
  try {
    await api.patchChapter(seq, { involved_characters: inferredInvolved })
    const next = await api.chapter(seq)
    setCh(next)
    setInferredInvolved([])
  } catch (e) {
    setSyncError(e?.message || '同步失败')
  } finally {
    setSyncingInferred(false)
  }
}
```

Render a compact suggestion row:

```jsx
{inferredInvolved.length > 0 && (
  <div role="status">
    <span>检测到可能涉及角色: {inferredInvolved.map(labelFor).join('、')}</span>
    <button onClick={syncInferred} disabled={syncingInferred}>同步到本章</button>
    {syncError && <span role="alert">{syncError}</span>}
  </div>
)}
```

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/deduceTree-readonly.test.jsx
```

Expected: both tests pass.

---

### Task 3: 对象 lifecycle 第一版

**Files:**
- Modify: `scribe3/store.py`
- Modify: `scribe3/app.py`
- Modify: `scribe3/web/src/api.js`
- Modify: object delete UI in `scribe3/web/src/DetailPane.jsx`, `scribe3/web/src/Materials.jsx`, and setting/fact panels where delete buttons live.
- Create: `scribe3/tests/test_object_lifecycle.py`

**Interfaces:**
- Produces:
  - `GET /objects/{object_type}/{object_id}/impact`
  - `POST /objects/{object_type}/{object_id}/archive`
  - `DELETE /objects/{object_type}/{object_id}?confirm_impact_token=...`
  - `api.objectImpact(type, id)`, `api.archiveObject(type, id)`, `api.deleteObject(type, id, token)`

- [ ] **Step 1: Write backend contract tests**

Create tests for these concrete behaviors:

```python
def test_delete_missing_material_returns_404(client):
    r = client.delete('/objects/material/not-exist?work=main')
    assert r.status_code == 404

def test_material_impact_lists_references_and_relates(client):
    # create material, add material_reference and relates edge through store helpers
    r = client.get(f'/objects/material/{mid}/impact?work=main')
    assert r.status_code == 200
    body = r.json()
    assert body['object']['type'] == 'material'
    assert any(ref['kind'] == 'material_reference' for ref in body['references'])
    assert any(ref['kind'] == 'graph' for ref in body['references'])

def test_delete_referenced_material_requires_confirm_token(client):
    r = client.delete(f'/objects/material/{mid}?work=main')
    assert r.status_code == 409
    assert r.json()['confirm_impact_token']
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd "<repo-root>"
scribe3/.venv/bin/pytest -q scribe3/tests/test_object_lifecycle.py
```

Expected: FAIL because lifecycle endpoints do not exist.

- [ ] **Step 3: Implement store impact helpers**

Add helpers in `SurrealStore`:

```python
def material_impact(self, material_id: str) -> dict:
    refs = self.material_refs(material_id)
    edges = self.relates_for(material_id)
    return {
        "material_reference": len(refs),
        "graph": len(edges),
        "semantic_index": 1 if self._material_exists(material_id) else 0,
    }
```

Add equivalent minimal `record_impact(oid)` for `role:*` and `fact:*` by counting known relation/knowledge rows available in current store methods.

- [ ] **Step 4: Implement endpoints**

Add FastAPI endpoints returning:

```json
{
  "object": {"type": "material", "id": "abc", "label": "标题"},
  "references": [{"kind": "material_reference", "count": 2}],
  "recommended_action": "archive",
  "confirm_impact_token": "material:abc:<hash>"
}
```

Delete without token returns 409 when references exist; delete missing returns 404.

- [ ] **Step 5: Wire frontend delete confirmation**

When user clicks delete:
1. Call `api.objectImpact(type, id)`.
2. Show references counts in the confirm dialog.
3. Archive by default when recommended action is `archive`.
4. Only hard delete with token after explicit confirm.

- [ ] **Step 6: Run GREEN**

Run:

```bash
cd "<repo-root>"
scribe3/.venv/bin/pytest -q scribe3/tests/test_object_lifecycle.py scribe3/tests/test_consistency.py
```

---

### Task 4: 素材导入和素材网络可信化

**Files:**
- Modify: `scribe3/app.py`
- Modify: `scribe3/store.py`
- Modify: `scribe3/web/src/Materials.jsx`
- Modify: `scribe3/web/src/__tests__/materials-workbench.test.jsx`
- Create: `scribe3/tests/test_material_import_trust.py`

**Interfaces:**
- Produces `material_import_commit` response with `created`, `ids`, `failed`, `warnings`, optional `retry_job_id`.
- Produces `material_graph` response with `nodes`, `edges`, `degraded_sources`, `edges_degraded`, `truncated`.

- [ ] **Step 1: Write backend RED tests**

```python
def test_material_import_commit_reports_failed_item(client, monkeypatch):
    # one item succeeds, second store.add_material raises ValueError("非法分类 kind=bad")
    r = client.post(f'/materials/import/{job_id}/commit?work=main', json={'items': items})
    assert r.status_code == 200
    body = r.json()
    assert body['created'] == 1
    assert body['failed'][0]['index'] == 1
    assert '非法分类' in body['failed'][0]['reason']

def test_material_graph_reports_edge_degraded(client, monkeypatch):
    # force relates query failure
    r = client.get('/materials/graph?work=main')
    assert r.status_code == 200
    assert r.json()['edges_degraded'] is True
    assert r.json()['degraded_sources']
```

- [ ] **Step 2: Write frontend RED test**

Extend `materials-workbench.test.jsx`:

```jsx
it('shows partial import failures instead of full success', async () => {
  mockApi.materialImportCommit.mockResolvedValue({
    created: 1,
    ids: ['m1'],
    failed: [{ index: 1, title: '坏素材', reason: '非法分类 kind=bad' }],
    warnings: [],
  })
  // complete preview and commit flow
  expect(await screen.findByText(/部分导入成功/)).toBeInTheDocument()
  expect(screen.getByText(/坏素材/)).toBeInTheDocument()
  expect(screen.getByText(/非法分类/)).toBeInTheDocument()
})
```

- [ ] **Step 3: Run RED**

Run:

```bash
cd "<repo-root>"
scribe3/.venv/bin/pytest -q scribe3/tests/test_material_import_trust.py

cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/materials-workbench.test.jsx
```

- [ ] **Step 4: Implement fail-soft with visible failures**

Change import commit loop to append `failed` and `warnings`; never `pass` silently:

```python
failed = []
warnings = []
for idx, it in enumerate(req.items):
    title = (it.get("title") or "").strip()
    if not title:
        failed.append({"index": idx, "title": "", "reason": "标题为空"})
        continue
    try:
        mid = st.add_material(...)
        try:
            st.build_material_edges(mid)
        except Exception as e:
            warnings.append({"index": idx, "stage": "build_edges", "reason": str(e)})
        ids.append(mid)
    except Exception as e:
        failed.append({"index": idx, "title": title, "reason": str(e)})
return {"created": len(ids), "ids": ids, "failed": failed, "warnings": warnings}
```

- [ ] **Step 5: Implement degraded graph response**

Wrap edge collection with explicit degraded flags:

```python
return {"nodes": nodes, "edges": edges, "edges_degraded": bool(degraded), "degraded_sources": degraded, "truncated": truncated}
```

- [ ] **Step 6: Run GREEN**

Run the same backend/frontend tests from Step 3.

---

### Task 5: 统一错误态、degraded 和 retry

**Files:**
- Modify: `scribe3/web/src/views/InsightView.jsx`
- Modify: `scribe3/web/src/ContainerOutline.jsx`
- Modify: `scribe3/web/src/WriteLayout.jsx`
- Modify: `scribe3/web/src/Materials.jsx`
- Create or Modify: focused frontend tests in `scribe3/web/src/__tests__/`

**Interfaces:**
- Produces visible states: loading, empty, error, degraded, partial.

- [ ] **Step 1: Add frontend failing tests**

Add tests that mock rejected promises and assert visible UI:

```jsx
expect(await screen.findByRole('alert')).toHaveTextContent(/加载失败/)
expect(screen.getByRole('button', { name: /重试/ })).toBeInTheDocument()
```

Cover:
- `InsightView` quality/progress failure.
- `ContainerOutline` add/rename/delete volume failure.
- `Materials` list and graph degraded.
- `WriteLayout` live guard failure visible as degraded instead of silent catch.

- [ ] **Step 2: Run RED**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/insightView-error.test.jsx src/__tests__/containerOutline-errors.test.jsx src/__tests__/materials-workbench.test.jsx
```

- [ ] **Step 3: Implement reusable visible states without a large design-system rewrite**

Use existing local UI primitives and add compact state blocks:

```jsx
function ErrorState({ message, onRetry }) {
  return (
    <div role="alert" className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      <div>{message}</div>
      {onRetry && <button onClick={onRetry}>重试</button>}
    </div>
  )
}
```

- [ ] **Step 4: Replace silent catches**

For each covered point:
- keep usable partial data when present;
- show degraded warning when a degraded field exists;
- show error + retry when request fails;
- keep console logging only as secondary debugging, never as sole user feedback.

- [ ] **Step 5: Run GREEN**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/materials-workbench.test.jsx
npm run build
```

---

### Task 6: 左栏能力全书态和 work-scoped 偏好

**Files:**
- Modify: `scribe3/web/src/AppRail.jsx`
- Modify: `scribe3/web/src/layout/EntryRail.jsx`
- Modify: `scribe3/web/src/layout/FourPaneShell.jsx`
- Create: `scribe3/web/src/hooks/useWorkScopedPref.js`
- Modify: `scribe3/web/src/layout/__tests__/entryRail.test.jsx`
- Modify: `scribe3/web/src/layout/__tests__/fourPaneShell.test.jsx`

**Interfaces:**
- Produces fixed entries: `manuscript`, `codex`, `materials`, `deduce`, `promises`, `motifs`, `search`, `issues`.
- Produces `useWorkScopedPref(work, key, initialValue)` storing `s3.${work}.${key}`.

- [ ] **Step 1: Write tests for no-chapter state and work-scoped active**

```jsx
expect(screen.getByRole('button', { name: '手稿' })).toBeVisible()
expect(screen.getByRole('button', { name: '演绎' })).toBeVisible()
expect(screen.getByRole('button', { name: '校验' })).toBeVisible()
```

Switch work from `book_a` to `book_b` and assert active entry reads `s3.book_b.leftEntry`, not `s3.leftTab`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/layout/__tests__/entryRail.test.jsx src/layout/__tests__/fourPaneShell.test.jsx
```

- [ ] **Step 3: Implement the hook and entry list**

```jsx
const CAPABILITY_ENTRIES = [
  { id: 'manuscript', label: '手稿' },
  { id: 'codex', label: '设定库' },
  { id: 'materials', label: '素材库' },
  { id: 'deduce', label: '演绎' },
  { id: 'promises', label: '伏笔' },
  { id: 'motifs', label: '母题' },
  { id: 'search', label: '搜索' },
  { id: 'issues', label: '校验' },
]
```

- [ ] **Step 4: Run GREEN and browser smoke**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/layout/__tests__/entryRail.test.jsx src/layout/__tests__/fourPaneShell.test.jsx
npm run build
```

Browser path: open `http://127.0.0.1:3311/`, choose `纸命`, clear selected chapter if supported, verify 8 entries remain visible.

---

### Task 7: 四栏生产路由闭环

**Files:**
- Modify: `scribe3/web/src/layout/DirectoryPane.jsx`
- Modify: `scribe3/web/src/layout/CapabilityDirectories.jsx`
- Modify: `scribe3/web/src/layout/CapabilityDetailPanes.jsx`
- Modify: `scribe3/web/src/DetailPane.jsx`
- Modify: `scribe3/web/src/studioDocks.jsx`
- Modify: `scribe3/web/src/layout/__tests__/directoryPane-capabilities.test.jsx`
- Modify: `scribe3/web/src/__tests__/detailPane-capabilities.test.jsx`

**Interfaces:**
- Produces `selection = { entry, itemType, itemId, chapter, payload }`.
- `DirectoryPane` owns item selection; `DetailPane` renders real workbench/detail for selected item.

- [ ] **Step 1: Write route tests for all 8 entries**

For each entry, assert:
- two-column directory stays visible;
- selecting a directory row updates third pane;
- no placeholder copy such as “即将接入” is rendered on production route.

- [ ] **Step 2: Run RED**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/layout/__tests__/directoryPane-capabilities.test.jsx src/__tests__/detailPane-capabilities.test.jsx
```

- [ ] **Step 3: Replace placeholders with real panels**

Map:
- `manuscript` -> `ManuscriptDirectory` + `WriteLayout/ChapterStudio`.
- `codex` -> original setting/category list + existing codex detail components.
- `materials` -> `MaterialList` + existing material detail/workbench.
- `deduce` -> `DeduceTree`/deduce chapter detail.
- `promises` -> existing promises ledger/detail.
- `motifs` -> existing motifs list/detail with `onSelect`.
- `search` -> Task 8 search directory/detail.
- `issues` -> Task 9 issue ledger/detail.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/layout/__tests__/directoryPane-capabilities.test.jsx src/__tests__/detailPane-capabilities.test.jsx
```

---

### Task 8: 全局搜索产品化

**Files:**
- Modify: `scribe3/app.py`
- Modify: `scribe3/store.py`
- Modify: `scribe3/web/src/api.js`
- Create: `scribe3/web/src/capabilities/search/SearchDirectory.jsx`
- Create: `scribe3/web/src/capabilities/search/SearchDetail.jsx`
- Create: `scribe3/tests/test_global_search.py`
- Create: `scribe3/web/src/__tests__/global-search.test.jsx`

**Interfaces:**
- Produces `GET /search?q=...` returning typed result objects with `id`, `type`, `label`, `excerpt`, `source`, `chapter`, `score`, `target_node`.
- Produces `api.search(q)`.

- [ ] **Step 1: Backend RED**

Test query returning at least chapter + material or fact:

```python
assert {r['type'] for r in body['results']} >= {'chapter', 'material'}
assert all('target_node' in r for r in body['results'])
```

- [ ] **Step 2: Frontend RED**

Search `借命`, assert grouped result source labels and clicking a result renders third-pane detail.

- [ ] **Step 3: Implement typed backend aggregation**

Aggregate current store capabilities:
- chapters from outline/prose snippets;
- codex facts/entities from existing lists;
- materials from material recall/list;
- promises/motifs/events from existing endpoints/store methods.

- [ ] **Step 4: Implement UI directory/detail**

Second pane: query input, type filters, grouped results. Third pane: reuse target object detail renderer by `target_node`.

- [ ] **Step 5: Verify**

Run:

```bash
scribe3/.venv/bin/pytest -q scribe3/tests/test_global_search.py
cd "<repo-root>/scribe3/web" && npm test -- src/__tests__/global-search.test.jsx
```

---

### Task 9: 校验 issue 台账

**Files:**
- Modify: `scribe3/app.py`
- Modify: `scribe3/web/src/api.js`
- Create: `scribe3/web/src/hooks/useIssueLedger.js`
- Create: `scribe3/web/src/capabilities/issues/IssueDirectory.jsx`
- Create: `scribe3/web/src/capabilities/issues/IssueDetail.jsx`
- Create: `scribe3/tests/test_issue_ledger.py`
- Create: `scribe3/web/src/__tests__/issue-ledger.test.jsx`

**Interfaces:**
- Produces `GET /issues?chapter=...` returning normalized issue objects.
- Produces optional `POST /issues/{id}/resolve`, `POST /issues/{id}/ignore` for sources that support state.

- [ ] **Step 1: Backend RED**

Assert QC, causal, pulse/post-check data normalize to:

```json
{"id":"issue:...","source":"qc","severity":"warning","chapter":4,"range":[120,180],"status":"open"}
```

- [ ] **Step 2: Frontend RED**

Click 校验 entry, assert issue list appears, clicking issue opens detail, detail exposes locate/fix/recheck controls.

- [ ] **Step 3: Implement ledger normalization**

Normalize existing `quality`, `qc`, `causal`, `postCheck`, `tensionCheck`, `inbox/pulse` outputs without changing their legacy endpoints.

- [ ] **Step 4: Implement directory/detail**

Second pane groups by severity/source/status. Third pane shows title, reason, range, suggested action, degraded sources, and action buttons.

- [ ] **Step 5: Verify**

Run:

```bash
scribe3/.venv/bin/pytest -q scribe3/tests/test_issue_ledger.py
cd "<repo-root>/scribe3/web" && npm test -- src/__tests__/issue-ledger.test.jsx
```

---

### Task 10: 素材引用账本与素材性能

**Files:**
- Modify: `scribe3/app.py`
- Modify: `scribe3/store.py`
- Modify: `scribe3/web/src/Materials.jsx`
- Modify: `scribe3/web/src/DetailPane.jsx` or chapter workbench component.
- Modify: `scribe3/web/src/__tests__/materials-workbench.test.jsx`
- Create: `scribe3/tests/test_material_refs_and_paging.py`

**Interfaces:**
- Extends `GET /materials` with `limit`, `cursor`, `kind`, `view`, `q`.
- Extends `GET /materials/graph` with `focus`, `limit`, `hop`, `truncated`.
- Reuses `GET /materials/refs-by-chapter?chapter=...`.

- [ ] **Step 1: RED tests**

Backend:

```python
assert 'next_cursor' in client.get('/materials?limit=50').json()
assert client.get('/materials/graph?limit=20').json()['truncated'] in (True, False)
```

Frontend:

```jsx
expect(await screen.findByText(/本章参考素材/)).toBeInTheDocument()
expect(screen.getByText(/phase:final/)).toBeInTheDocument()
```

- [ ] **Step 2: Implement paging and graph limits**

Return `{items, next_cursor}` while keeping legacy array compatibility in frontend by normalizing both shapes.

- [ ] **Step 3: Implement chapter refs panel**

In chapter detail/workbench, show title, kind, phase, reason/excerpt and link to material detail.

- [ ] **Step 4: Verify**

Run:

```bash
scribe3/.venv/bin/pytest -q scribe3/tests/test_material_refs_and_paging.py
cd "<repo-root>/scribe3/web" && npm test -- src/__tests__/materials-workbench.test.jsx
```

---

### Task 11: 横切视图跳转和对象聚焦

**Files:**
- Modify: graph, timeline, dashboard view components under `scribe3/web/src/views/`
- Modify: `scribe3/web/src/layout/FourPaneShell.jsx`
- Modify: `scribe3/web/src/DetailPane.jsx`
- Create: `scribe3/web/src/__tests__/cross-view-navigation.test.jsx`

**Interfaces:**
- Produces `navigateToObject(target_node)` dispatching selection to left entry, directory item, detail pane, and right dock context.

- [ ] **Step 1: RED tests**

For graph node, timeline item and dashboard weak chapter:

```jsx
fireEvent.click(screen.getByRole('button', { name: /弱章/ }))
expect(screen.getByRole('button', { name: '校验' })).toHaveAttribute('aria-selected', 'true')
expect(screen.getByTestId('detail')).toHaveTextContent(/第 4 章/)
```

- [ ] **Step 2: Implement target mapping**

Map:
- role/fact/relation -> `codex`
- event/chapter -> `manuscript`
- material -> `materials`
- promise -> `promises`
- motif -> `motifs`
- issue/weak chapter -> `issues`

- [ ] **Step 3: Verify**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/cross-view-navigation.test.jsx src/layout/__tests__/fourPaneShell.test.jsx
```

---

### Task 12: 大文件拆分和 MCP 多书联查 ADR

**Files:**
- Create: `docs/adr/2026-07-08-scribe3-mcp-multi-work.md`
- Refactor only after Task 6-11 are green:
  - `scribe3/web/src/capabilities/*`
  - `scribe3/web/src/rightDock/*`
  - `scribe3/web/src/hooks/*`
  - `scribe3/web/src/studioDocks.jsx`

**Interfaces:**
- Produces clear ADR choice: per-work store cache first, per-work MCP profile deferred.

- [ ] **Step 1: Write ADR**

ADR must include:
- current single-work limitation;
- two options;
- selected option;
- migration path;
- risk controls;
- tests required before MCP implementation.

- [ ] **Step 2: Split only stable code**

Move already-tested capability route code into domain folders without behavior changes. Run tests after each move.

- [ ] **Step 3: Verify**

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/layout/__tests__/fourPaneShell.test.jsx src/layout/__tests__/directoryPane-capabilities.test.jsx src/__tests__/detailPane-capabilities.test.jsx
npm run build
```

---

## Batch Verification

### 第一批 F0-F5

Run:

```bash
cd "<repo-root>"
scribe3/.venv/bin/pytest -q scribe3/tests/test_security.py scribe3/tests/test_verify.py scribe3/tests/test_purpose_contract.py scribe3/tests/test_setting_system.py
scribe3/.venv/bin/pytest -q scribe3/tests/test_migrate.py scribe3/tests/test_transaction.py scribe3/tests/test_ingest_idempotency.py
scribe3/.venv/bin/pytest -q scribe3/tests/test_object_lifecycle.py scribe3/tests/test_material_import_trust.py

cd "<repo-root>/scribe3/web"
npm test -- src/__tests__/writeChat-phase.test.jsx src/__tests__/deduceTree-readonly.test.jsx src/__tests__/materials-workbench.test.jsx
npm run build
```

Browser evidence:
- 正文主编写作 network payload contains `phase:"final"`.
- 演绎打开无 PATCH;点击同步才 PATCH。
- 素材导入部分失败显示 failed rows。
- 仪表盘或素材网络失败显示 error/degraded + retry。

### 第二批 F6-F11

Run:

```bash
cd "<repo-root>/scribe3/web"
npm test -- src/layout/__tests__/entryRail.test.jsx src/layout/__tests__/directoryPane-capabilities.test.jsx src/layout/__tests__/fourPaneShell.test.jsx src/__tests__/detailPane-capabilities.test.jsx src/__tests__/global-search.test.jsx src/__tests__/issue-ledger.test.jsx src/__tests__/cross-view-navigation.test.jsx
npm run build
```

Browser evidence:
- 未选章和已选章都能看到 8 个左栏入口。
- 每个入口点击后二栏常驻,三栏显示真实详情。
- 搜索 `借命` 返回多类型结果并能跳转详情。
- 校验 issue 能定位到章详情。
- 图谱、时间线、仪表盘能回流具体对象。

### 第三批 F12

Run:

```bash
cd "<repo-root>"
scribe3/.venv/bin/pytest -q scribe3/tests/test_security.py scribe3/tests/test_verify.py scribe3/tests/test_purpose_contract.py scribe3/tests/test_setting_system.py scribe3/tests/test_migrate.py scribe3/tests/test_transaction.py scribe3/tests/test_ingest_idempotency.py

cd "<repo-root>/scribe3/web"
npm test
npm run build
```

---

## Self-Review

- Spec coverage: F0-F12 均有任务、文件、接口、测试和验收命令。
- Placeholder scan: 本计划不使用 TBD/TODO/implement later/fill in details。
- Type consistency: plan uses `entry`, `itemType`, `itemId`, `target_node`, `phase`, `degraded_sources`, `confirm_impact_token` consistently with the approved spec.
- Commit policy: spec 中的提交建议被降级为“完成后报告可提交范围”,符合当前用户规则“未经要求不 commit”。
