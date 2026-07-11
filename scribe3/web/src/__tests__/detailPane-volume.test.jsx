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
    apiMock.addVolume.mockResolvedValue({ status: 'created', id: 'new-vol' })
    apiMock.createChapter.mockResolvedValue({ status: 'created', seq: 4, title: '第4章', volume: '1' })
    apiMock.patchVolume.mockResolvedValue({ status: 'updated', id: '1' })
    apiMock.reorderChapters.mockResolvedValue({ status: 'ok' })
  })

  it('选中卷时渲染卷工作台并保存卷纲', async () => {
    const onSelectNode = vi.fn()
    const onTreeChanged = vi.fn()
    render(
      <DetailPane
        sel={{ mode: 'node', node: { id: 'vol:1', type: 'volume', ref: '1', label: '第一卷' } }}
        work="demo"
        onSelectNode={onSelectNode}
        onTreeChanged={onTreeChanged}
      />,
    )

    expect(await screen.findByRole('heading', { name: '第一卷' })).toBeTruthy()
    expect(screen.getByText('2 章')).toBeTruthy()
    expect(screen.getAllByText('3.0k 字').length).toBeGreaterThan(0)

    const intro = screen.getByLabelText('卷纲')
    expect(intro.value).toBe('旧卷纲')
    fireEvent.change(intro, { target: { value: '新卷纲\n第二幕反转' } })
    fireEvent.click(screen.getByRole('button', { name: '保存卷信息' }))

    await waitFor(() => expect(apiMock.patchVolume).toHaveBeenCalledWith('1', expect.objectContaining({
      title: '第一卷',
      intro: '新卷纲\n第二幕反转',
      color: '#2f7563',
    })))
    expect(onTreeChanged).toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /1 入城/ }))
    expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({
      id: 'ch:1',
      type: 'chapter',
      ref: 1,
      label: '1 入城',
    }))
  })

  it('未分卷可以创建为正式分卷并收纳现有章节', async () => {
    apiMock.outline.mockResolvedValue({
      volumes: [],
      chapters: [
        { seq: 1, title: '入城', volume: null, word_count: 1200 },
        { seq: 2, title: '借命契', volume: null, word_count: 1800 },
      ],
    })
    const onSelectNode = vi.fn()
    const onTreeChanged = vi.fn()
    render(
      <DetailPane
        sel={{ mode: 'node', node: { id: 'vol:null', type: 'volume', ref: null, label: '未分卷' } }}
        work="demo"
        onSelectNode={onSelectNode}
        onTreeChanged={onTreeChanged}
      />,
    )

    expect(await screen.findByRole('heading', { name: '未分卷' })).toBeTruthy()
    fireEvent.change(screen.getByLabelText('新卷名'), { target: { value: '第一卷' } })
    fireEvent.change(screen.getByLabelText('新卷卷纲'), { target: { value: '主角入局,借命契成立。' } })
    fireEvent.click(screen.getByRole('button', { name: '创建分卷' }))

    await waitFor(() => expect(apiMock.addVolume).toHaveBeenCalledWith('第一卷', 1, null, '主角入局,借命契成立。'))
    expect(apiMock.reorderChapters).toHaveBeenCalledWith('new-vol', [1, 2])
    expect(onTreeChanged).toHaveBeenCalled()
    expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({
      id: 'vol:new-vol',
      type: 'volume',
      ref: 'new-vol',
      label: '第一卷',
    }))
  })

  it('卷工作台可以直接在当前卷中新建章节并选中新章', async () => {
    const onSelectNode = vi.fn()
    const onTreeChanged = vi.fn()
    render(
      <DetailPane
        sel={{ mode: 'node', node: { id: 'vol:1', type: 'volume', ref: '1', label: '第一卷' } }}
        work="demo"
        onSelectNode={onSelectNode}
        onTreeChanged={onTreeChanged}
      />,
    )

    expect(await screen.findByRole('heading', { name: '第一卷' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '新建章' }))

    await waitFor(() => expect(apiMock.createChapter).toHaveBeenCalledWith({ volume: '1' }))
    expect(onTreeChanged).toHaveBeenCalled()
    expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({
      id: 'ch:4',
      type: 'chapter',
      ref: 4,
      label: '4 第4章',
    }))
  })
})
