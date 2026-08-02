import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DetailPane } from '../DetailPane'

vi.mock('../ChapterStudio', () => ({ ChapterStudio: () => <div data-testid="chapter-studio" /> }))
vi.mock('../CodexDetail', () => ({
  CodexDetail: ({ node }) => <div data-testid="codex-detail">{node.id}</div>,
  PropositionDetail: ({ node }) => <div data-testid="proposition-detail">{node.id}</div>,
}))
vi.mock('../CodexNew', () => ({ CodexNew: () => <div data-testid="codex-new" /> }))
vi.mock('../Materials', () => ({
  MaterialDetail: ({ node }) => <div data-testid="material-detail">{node.id}</div>,
  MaterialList: ({ node }) => <div data-testid="material-list">{node.id}</div>,
  MaterialNew: () => <div data-testid="material-new" />,
}))
vi.mock('../views/AtlasView', () => ({ AtlasView: () => <div data-testid="view-atlas" /> }))
vi.mock('../views/InsightView', () => ({ InsightView: () => <div data-testid="view-insight" /> }))
vi.mock('../views/OverviewView', () => ({ OverviewView: () => <div data-testid="view-overview" /> }))
vi.mock('../views/TimelineView', () => ({ TimelineView: () => <div data-testid="view-timeline" /> }))
vi.mock('../ContainerOutline', () => ({ ContainerOutline: () => <div data-testid="container-outline" /> }))

describe('DetailPane 路由', () => {
  it('栏3只渲染条目详情:容器节点不再就地展开列表', () => {
    render(<DetailPane sel={{ mode: 'node', node: { id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色' } }} />)

    expect(screen.queryByTestId('container-outline')).toBeNull()
    expect(screen.queryByTestId('material-list')).toBeNull()
    expect(screen.getByText(/选择目录条目/)).toBeTruthy()
  })

  it('条目节点仍进入详情,横切 view 仍进入全画布视图', async () => {
    const { rerender } = render(<DetailPane sel={{ mode: 'node', node: { id: 'motif:1', type: 'motif', ref: 1, label: '回声' } }} />)
    expect((await screen.findByTestId('codex-detail')).textContent).toBe('motif:1')

    rerender(<DetailPane sel={{ mode: 'view', viewKey: 'atlas' }} />)
    expect(await screen.findByTestId('view-atlas')).toBeTruthy()
  })
})
