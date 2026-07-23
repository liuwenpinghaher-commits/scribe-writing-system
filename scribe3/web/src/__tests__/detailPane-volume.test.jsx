import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DetailPane } from '../DetailPane'

const apiMock = vi.hoisted(() => ({
  outline: vi.fn(),
  addVolume: vi.fn(),
  createChapter: vi.fn(),
  patchVolume: vi.fn(),
  reorderChapters: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../ui/Toast', () => ({
  showToast: vi.fn(),
  useToast: () => vi.fn(),
  ToastProvider: ({ children }) => children,
}))
vi.mock('../ChapterStudio', () => ({ ChapterStudio: () => <div data-testid="chapter-studio" /> }))
vi.mock('../CodexDetail', () => ({
  CodexDetail: ({ node }) => <div data-testid="codex-detail">{node.id}</div>,
  PropositionDetail: ({ node }) => <div data-testid="proposition-detail">{node.id}</div>,
}))
vi.mock('../CodexNew', () => ({ CodexNew: () => <div data-testid="codex-new" /> }))
vi.mock('../Materials', () => ({
  MaterialDetail: ({ node }) => <div data-testid="material-detail">{node.id}</div>,
  MaterialImportPane: () => <div data-testid="material-import-pane" />,
  MaterialNetworkPane: () => <div data-testid="material-network-pane" />,
  MaterialNew: () => <div data-testid="material-new" />,
}))
vi.mock('../views/AtlasView', () => ({ AtlasView: () => <div data-testid="view-atlas" /> }))
vi.mock('../views/InsightView', () => ({ InsightView: () => <div data-testid="view-insight" /> }))
vi.mock('../views/OverviewView', () => ({ OverviewView: () => <div data-testid="view-overview" /> }))
vi.mock('../views/TimelineView', () => ({ TimelineView: () => <div data-testid="view-timeline" /> }))
vi.mock('../ContainerOutline', () => ({ ContainerOutline: () => <div data-testid="container-outline" /> }))
vi.mock('../NorthStarPanel', () => ({ NorthStarPanel: () => <div data-testid="northstar-panel" /> }))

describe('DetailPane 卷工作台', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    apiMock.outline.mockResolvedValue({
      volumes: [
        { id: '1', title: '第一卷', intro: '旧卷纲', color: '#2f7563', sort_order: 1 },
      ],
      chapters: [
        { seq: 1, title: '入城', synopsis: '开局', volume: '1', word_count: 1200, label: 'draft' },
        { seq: 2, title: '借命契', synopsis: '立约', volume: '1', word_count: 1800, label: 'outline' },
        { seq: 3, title: '未分卷章', synopsis: '', volume: null, word_count: 600 },
      ],
    })
  })

  it('选中卷时渲染卷工作台只读卷纲并支持跳章', async () => {
    const onSelectNode = vi.fn()
    render(
      <DetailPane
        sel={{ mode: 'node', node: { id: 'vol:1', type: 'volume', ref: '1', label: '第一卷' } }}
        work="demo"
        onSelectNode={onSelectNode}
      />,
    )

    expect(await screen.findByRole('heading', { name: '第一卷' })).toBeTruthy()
    expect(screen.getByText(/2 章 · 3\.0k 字/)).toBeTruthy()
    expect(screen.getByTestId('volume-meta-readonly')).toBeTruthy()
    expect(screen.getByText('旧卷纲')).toBeTruthy()
    expect(screen.queryByRole('button', { name: '保存卷信息' })).toBeNull()
    expect(apiMock.patchVolume).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /1 入城/ }))
    expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({
      id: 'ch:1',
      type: 'chapter',
      ref: 1,
      label: '1 入城',
    }))
  })

  it('未分卷「让主编创建分卷」种子化,不 REST addVolume', async () => {
    apiMock.outline.mockResolvedValue({
      volumes: [],
      chapters: [
        { seq: 1, title: '入城', volume: null, word_count: 1200 },
        { seq: 2, title: '借命契', volume: null, word_count: 1800 },
      ],
    })
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))

    render(
      <DetailPane
        sel={{ mode: 'node', node: { id: 'vol:null', type: 'volume', ref: null, label: '未分卷' } }}
        work="demo"
      />,
    )

    expect(await screen.findByRole('heading', { name: '未分卷' })).toBeTruthy()
    fireEvent.change(screen.getByLabelText('新卷名'), { target: { value: '第一卷' } })
    fireEvent.change(screen.getByLabelText('新卷卷纲'), { target: { value: '主角入局,借命契成立。' } })
    fireEvent.click(screen.getByTestId('volume-create-from-unassigned'))

    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(seeds.join('\n')).toMatch(/s3_add_volume|第一卷/)
    expect(tabs).toContain('chief')
    expect(apiMock.addVolume).not.toHaveBeenCalled()
    expect(apiMock.reorderChapters).not.toHaveBeenCalled()
  })

  it('卷工作台「让主编新建章」种子化,不 REST createChapter', async () => {
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))

    render(
      <DetailPane
        sel={{ mode: 'node', node: { id: 'vol:1', type: 'volume', ref: '1', label: '第一卷' } }}
        work="demo"
      />,
    )

    expect(await screen.findByRole('heading', { name: '第一卷' })).toBeTruthy()
    fireEvent.click(screen.getByTestId('volume-create-chapter'))

    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(seeds.join('\n')).toMatch(/s3_add_chapter/)
    expect(tabs).toContain('chief')
    expect(apiMock.createChapter).not.toHaveBeenCalled()
  })
})
