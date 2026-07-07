import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { useState } from 'react'
import { FourPaneShell } from '../FourPaneShell'

vi.mock('../../DetailPane', () => ({
  DetailPane: ({ sel }) => (
    <div data-testid="detail-content">{sel?.mode === 'view' ? `view:${sel.viewKey}` : `node:${sel?.node?.id || 'empty'}`}</div>
  ),
}))

vi.mock('../../studioDocks', () => ({
  RightDock: ({ sel, lastSeq }) => (
    <aside data-testid="chief">{`${sel?.mode || 'none'}:${lastSeq ?? ''}`}</aside>
  ),
}))

vi.mock('../../ContainerOutline', () => ({
  ContainerOutline: ({ node, onOpenChapter, onSelect }) => (
    <div data-testid="container-outline" data-node={node.id}>
      <button onClick={() => onSelect?.(node.children?.[0])}>打开条目</button>
      <button onClick={() => onOpenChapter?.({ seq: 7, title: '第七章' })}>打开章节</button>
    </div>
  ),
}))

vi.mock('../../Materials', () => ({
  MaterialList: ({ node, onSelect }) => (
    <div data-testid="material-list" data-node={node.id}>
      <button onClick={() => onSelect?.({ id: 'material:1', type: 'material', ref: 1, label: '素材一' })}>素材一</button>
    </div>
  ),
}))

const tree = {
  manuscript: { id: 'manuscript_root', type: 'manuscript_root', label: '手稿', children: [] },
  codex: {
    id: 'codex_root',
    type: 'codex_root',
    label: '设定',
    children: [
      { id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色', children: [{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }] },
    ],
  },
  materials: { id: 'material_root', type: 'material_root', label: '素材库' },
}

function Harness({ initialSel = { mode: 'node', node: null } }) {
  const [sel, setSel] = useState(initialSel)
  const onSelectNode = (node) => {
    if (node.type === 'view') setSel({ mode: 'view', viewKey: node.id.split(':')[1] })
    else setSel({ mode: 'node', node })
  }
  return <FourPaneShell tree={tree} sel={sel} onSelectNode={onSelectNode} work="demo" leftSeq={3} />
}

describe('FourPaneShell 四栏钻取', () => {
  it('入口只切换栏2目录,目录条目才切换栏3详情,且栏2常驻', () => {
    render(<Harness />)

    fireEvent.click(screen.getByRole('button', { name: '角色' }))
    expect(screen.getByTestId('col-directory')).toBeTruthy()
    expect(screen.getByTestId('container-outline').getAttribute('data-node')).toBe('cat:character')
    expect(screen.getByTestId('detail-content').textContent).toBe('node:empty')

    fireEvent.click(within(screen.getByTestId('col-directory')).getByRole('button', { name: '打开条目' }))
    expect(screen.getByTestId('col-directory')).toBeTruthy()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:character:小翠')
  })

  it('横切视图不再作为栏1入口', () => {
    render(<Harness />)

    expect(screen.queryByRole('button', { name: '图谱' })).toBeNull()
    expect(screen.queryByRole('button', { name: '时间线' })).toBeNull()
    expect(screen.queryByRole('button', { name: '仪表盘' })).toBeNull()
  })

  it('外层顶栏切入视图时隐藏栏2,栏3全画布渲染 view', () => {
    render(<Harness initialSel={{ mode: 'view', viewKey: 'atlas' }} />)

    expect(screen.queryByTestId('col-directory')).toBeNull()
    expect(screen.getByTestId('detail-content').textContent).toBe('view:atlas')
  })
})
