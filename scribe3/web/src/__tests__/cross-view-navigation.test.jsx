import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { useState } from 'react'
import { FourPaneShell } from '../layout/FourPaneShell'

vi.mock('../DetailPane', () => ({
  DetailPane: ({ sel, onNavigateToObject }) => (
    <div data-testid="detail-content">
      {sel?.mode === 'view' ? `view:${sel.viewKey}` : `node:${sel?.node?.id || 'empty'}`}
      <button type="button" onClick={() => onNavigateToObject?.({ type: 'weak_chapter', chapter: 4, title: '第 4 章弱章诊断' })}>
        模拟仪表盘弱章
      </button>
      <button type="button" onClick={() => onNavigateToObject?.({ type: 'character', id: 'role:小翠', label: '小翠' })}>
        模拟图谱角色
      </button>
      <button type="button" onClick={() => onNavigateToObject?.({ type: 'promise', id: 'promise:p1', label: '铜炉要回收', chapter: 4 })}>
        模拟时间线伏笔
      </button>
    </div>
  ),
}))

vi.mock('../api', () => ({
  api: {
    promisesLedger: vi.fn(() => Promise.resolve({ open: [], closed: [], red_herring: [] })),
    motifs: vi.fn(() => Promise.resolve([])),
    qc: vi.fn(() => Promise.resolve({ repeated: [] })),
    search: vi.fn(() => Promise.resolve({ results: [] })),
    issues: vi.fn(() => Promise.resolve({ issues: [], degraded_sources: [] })),
    chapter: vi.fn(() => Promise.resolve({ title: '第七章', scene_truth: '', deductions: [], involved_characters: [] })),
    entities: vi.fn(() => Promise.resolve([])),
  },
}))

vi.mock('../ProjectTree', () => ({
  ProjectTree: ({ tree }) => (
    <div data-testid="project-tree">
      <div>{tree?.manuscript?.label}</div>
      <div>{tree?.codex?.label}</div>
      <div>{tree?.materials?.label}</div>
    </div>
  ),
}))

vi.mock('../DeduceTree', () => ({
  DeduceTree: () => <div data-testid="deduce-tree">演绎目录</div>,
}))

vi.mock('../DeduceStage', () => ({
  DeduceStage: ({ seq }) => <div data-testid="deduce-stage">演绎详情:{seq}</div>,
}))

vi.mock('../studioDocks', async () => {
  const actual = await vi.importActual('../studioDocks')
  return {
    ...actual,
    RightDock: ({ sel, lastSeq }) => (
      <aside data-testid="chief">{`${sel?.mode || 'none'}:${lastSeq ?? ''}`}</aside>
    ),
  }
})

vi.mock('../ContainerOutline', () => ({
  ContainerOutline: ({ node }) => <div data-testid="container-outline">{node?.id}</div>,
}))

vi.mock('../Materials', () => ({
  MaterialList: ({ node }) => <div data-testid="material-list">{node?.id}</div>,
}))

const tree = {
  manuscript: { id: 'manuscript_root', type: 'manuscript_root', label: '手稿', children: [] },
  codex: {
    id: 'codex_root',
    type: 'codex_root',
    label: '设定库',
    children: [{ id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色' }],
  },
  materials: { id: 'material_root', type: 'material_root', label: '素材库' },
}

function Harness({ viewKey }) {
  const [sel, setSel] = useState({ mode: 'view', viewKey })
  const onSelectNode = (node) => {
    if (!node) { setSel({ mode: 'node', node: null }); return }
    if (node.type === 'view') setSel({ mode: 'view', viewKey: node.id.split(':')[1] })
    else setSel({ mode: 'node', node })
  }
  return <FourPaneShell tree={tree} sel={sel} onSelectNode={onSelectNode} work="demo" leftSeq={4} />
}

describe('横切视图对象回跳四栏', () => {
  beforeAll(() => {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    globalThis.ResizeObserver = ResizeObserverMock
  })

  beforeEach(() => {
    localStorage.clear()
  })

  it('仪表盘弱章回到校验入口并打开 issue 详情', async () => {
    render(<Harness viewKey="insight" />)

    expect(screen.queryByTestId('col-directory')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '模拟仪表盘弱章' }))

    await waitFor(() => expect(screen.getByTestId('detail-content').textContent).toContain('node:issue:weak:4'))
    expect(screen.getByRole('button', { name: '校验' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('col-directory')).toBeTruthy()
  })

  it('图谱角色回到设定库入口并打开角色详情', async () => {
    render(<Harness viewKey="atlas" />)

    fireEvent.click(screen.getByRole('button', { name: '模拟图谱角色' }))

    await waitFor(() => expect(screen.getByTestId('detail-content').textContent).toContain('node:character:小翠'))
    expect(screen.getByRole('button', { name: '设定库' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('时间线伏笔回到伏笔入口并打开伏笔详情', async () => {
    render(<Harness viewKey="timeline" />)

    fireEvent.click(screen.getByRole('button', { name: '模拟时间线伏笔' }))

    await waitFor(() => expect(screen.getByTestId('detail-content').textContent).toContain('node:promise:p1'))
    expect(screen.getByRole('button', { name: '伏笔' })).toHaveAttribute('aria-pressed', 'true')
  })
})
