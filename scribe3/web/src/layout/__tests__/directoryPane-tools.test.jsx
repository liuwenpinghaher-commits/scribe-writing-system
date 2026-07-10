import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DirectoryPane } from '../DirectoryPane'
import { DetailPane } from '../../DetailPane'

vi.mock('../../ContainerOutline', () => ({
  ContainerOutline: ({ node }) => <div data-testid="container-outline">{node.id}</div>,
}))
vi.mock('../../Materials', () => ({
  MaterialList: () => <div data-testid="material-list" />,
  MaterialDetail: () => <div data-testid="material-detail" />,
  MaterialNew: () => <div data-testid="material-new" />,
}))
vi.mock('../../ChapterStudio', () => ({ ChapterStudio: () => <div data-testid="chapter-studio" /> }))
vi.mock('../../CodexDetail', () => ({
  CodexDetail: () => <div data-testid="codex-detail" />,
  PropositionDetail: () => <div data-testid="proposition-detail" />,
}))
vi.mock('../../CodexNew', () => ({ CodexNew: () => <div data-testid="codex-new" /> }))
vi.mock('../../NorthStarPanel', () => ({ NorthStarPanel: ({ scope }) => <div data-testid="northstar-panel">{scope}</div> }))
vi.mock('../../views/AtlasView', () => ({ AtlasView: () => <div data-testid="view-atlas" /> }))
vi.mock('../../views/InsightView', () => ({ InsightView: ({ focus }) => <div data-testid="view-insight">{focus || ''}</div> }))
vi.mock('../../views/OverviewView', () => ({ OverviewView: () => <div data-testid="view-overview" /> }))
vi.mock('../../views/TimelineView', () => ({ TimelineView: () => <div data-testid="view-timeline" /> }))

describe('DirectoryPane 手稿书级工具', () => {
  it('手稿根目录不再在卷章上方显示全书大纲、北极星、进度入口', () => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={{ id: 'manuscript_root', type: 'manuscript_root', label: '手稿' }} onSelectItem={onSelectItem} />)

    expect(screen.queryByRole('button', { name: '全书大纲' })).toBeNull()
    expect(screen.queryByRole('button', { name: '北极星' })).toBeNull()
    expect(screen.queryByRole('button', { name: '进度' })).toBeNull()
    expect(screen.getByText('卷章')).toBeTruthy()
    expect(onSelectItem).not.toHaveBeenCalled()
  })

  it('书级工具节点在栏3渲染对应工作台', () => {
    const { rerender } = render(<DetailPane sel={{ mode: 'node', node: { id: 'book:outline', type: 'book_outline', label: '全书大纲' } }} />)
    expect(screen.getByTestId('container-outline').textContent).toBe('manuscript_root')

    rerender(<DetailPane sel={{ mode: 'node', node: { id: 'book:northstar', type: 'book_northstar', label: '北极星' } }} />)
    expect(screen.getByTestId('northstar-panel').textContent).toBe('book')
  })
})
