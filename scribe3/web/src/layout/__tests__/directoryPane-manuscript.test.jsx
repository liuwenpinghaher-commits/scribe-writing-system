import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DirectoryPane } from '../DirectoryPane'

vi.mock('../../api', () => ({
  api: {
    archivedChapters: vi.fn(),
    restoreChapter: vi.fn(),
    chapterImpact: vi.fn(),
    deleteChapter: vi.fn(),
  },
}))
vi.mock('../../ui/Toast', () => ({
  showToast: vi.fn(),
}))

vi.mock('../../ContainerOutline', () => ({
  ContainerOutline: ({ node }) => <div data-testid="legacy-container-outline">{node.id}</div>,
}))
vi.mock('../../Materials', () => ({
  MaterialList: () => <div data-testid="material-list" />,
}))

const { api } = await import('../../api')

const manuscript = {
  id: 'manuscript_root',
  type: 'manuscript_root',
  label: '手稿',
  children: [
    {
      id: 'vol:1',
      type: 'volume',
      ref: '1',
      label: '第一卷',
      children: [
        { id: 'ch:1', type: 'chapter', ref: 1, label: '第 1 章 入城' },
        {
          id: 'ch:2',
          type: 'chapter',
          ref: 2,
          label: '第 2 章 借命契',
          children: [
            { id: 'scene:2:1', type: 'scene', ref: { seq: 2, idx: 1 }, label: '场景 1 炉灰' },
          ],
        },
      ],
    },
  ],
}

const entry = { id: 'entry:manuscript', type: 'entry_capability', capability: 'manuscript', label: '手稿', source: manuscript }

describe('DirectoryPane 手稿目录', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.archivedChapters.mockResolvedValue([])
    api.restoreChapter.mockResolvedValue({ status: 'restored', seq: 9 })
    api.chapterImpact.mockResolvedValue({
      object: { type: 'chapter', id: 9, label: '旧线' },
      references: [{ kind: '正文', count: 12 }, { kind: '版本', count: 2 }],
      confirm_impact_token: 'impact-token-9',
    })
    api.deleteChapter.mockResolvedValue({ status: 'deleted', seq: 9 })
  })

  it('手稿二栏不再显示卷章上方的当前卡片和书级工具', () => {
    render(<DirectoryPane entry={entry} seq={2} sel={{ node: { type: 'chapter', ref: 2 } }} onSelectItem={() => {}} />)

    expect(screen.getByTestId('manuscript-directory')).toBeTruthy()
    expect(screen.queryByTestId('directory-sticky-header')).toBeNull()
    expect(screen.queryByTestId('manuscript-current-card')).toBeNull()
    expect(screen.queryByTestId('manuscript-book-tools')).toBeNull()
    expect(screen.queryByText('书级')).toBeNull()
    expect(screen.queryByRole('button', { name: '全书大纲' })).toBeNull()
    expect(screen.queryByRole('button', { name: '北极星' })).toBeNull()
    expect(screen.getByText('卷章')).toBeTruthy()
    expect(screen.getByTestId('manuscript-volume-list').textContent).toContain('第一卷')
    expect(screen.getByText('第一卷').closest('button')).toBeTruthy()
    expect(screen.getByRole('button', { name: /第 2 章/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /场景 1 炉灰/ })).toBeTruthy()
  })

  it('空手稿提供新建第一章和新建卷入口', () => {
    const onCreateChapter = vi.fn()
    const onAddVolume = vi.fn()
    const emptyEntry = {
      ...entry,
      source: { ...manuscript, children: [] },
    }

    render(
      <DirectoryPane
        entry={emptyEntry}
        onSelectItem={() => {}}
        onCreateChapter={onCreateChapter}
        onAddVolume={onAddVolume}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '新建未分卷章节' }))
    fireEvent.click(screen.getByRole('button', { name: '新建卷' }))

    expect(onCreateChapter).toHaveBeenCalledWith(null)
    expect(onAddVolume).toHaveBeenCalledTimes(1)
  })

  it('点击章只传出章节节点,并保留卷章列表', () => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry} seq={2} onSelectItem={onSelectItem} />)

    fireEvent.click(screen.getByRole('button', { name: /第 1 章/ }))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      id: 'ch:1',
      type: 'chapter',
      ref: 1,
    }))
    expect(screen.queryByTestId('directory-sticky-header')).toBeNull()
    expect(screen.getByTestId('manuscript-volume-list')).toBeTruthy()
  })

  it('点击卷传出卷节点,用于在三栏填写卷纲', () => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry} seq={2} onSelectItem={onSelectItem} />)

    fireEvent.click(screen.getByText('第一卷').closest('button'))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      id: 'vol:1',
      type: 'volume',
      ref: '1',
      label: '第一卷',
    }))
    expect(onSelectItem).not.toHaveBeenCalledWith(expect.objectContaining({
      type: 'chapter',
    }))
  })

  it('卷行提供新建章入口,并把目标卷传给外层', () => {
    const onCreateChapter = vi.fn()
    render(
      <DirectoryPane
        entry={entry}
        seq={2}
        sel={{ node: { id: 'vol:1', type: 'volume', ref: '1', label: '第一卷' } }}
        onSelectItem={() => {}}
        onCreateChapter={onCreateChapter}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '在第一卷中新建章' }))
    expect(onCreateChapter).toHaveBeenCalledWith('1')
  })

  it('归档箱列出归档章节,恢复后刷新目录并选中该章', async () => {
    api.archivedChapters.mockResolvedValueOnce([
      { seq: 9, title: '旧线', archived_at: '2026-07-09T10:00:00Z', archive_reason: '支线暂缓' },
    ])
    const onSelectItem = vi.fn()
    const onArchivedChanged = vi.fn()
    render(
      <DirectoryPane
        entry={entry}
        seq={1}
        onSelectItem={onSelectItem}
        onArchivedChanged={onArchivedChanged}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /归档箱/ }))

    expect(await screen.findByText('第 9 章 旧线')).toBeTruthy()
    expect(screen.getByText('支线暂缓')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '恢复第 9 章 旧线' }))

    await waitFor(() => expect(api.restoreChapter).toHaveBeenCalledWith(9))
    expect(onArchivedChanged).toHaveBeenCalled()
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      id: 'ch:9',
      type: 'chapter',
      ref: 9,
    }))
  })

  it('归档箱永久删除章节必须先确认影响清单 token', async () => {
    api.archivedChapters.mockResolvedValueOnce([
      { seq: 9, title: '旧线', archived_at: '2026-07-09T10:00:00Z', archive_reason: '' },
    ])
    const onArchivedChanged = vi.fn()
    render(
      <DirectoryPane
        entry={entry}
        seq={1}
        onSelectItem={() => {}}
        onArchivedChanged={onArchivedChanged}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /归档箱/ }))
    expect(await screen.findByText('第 9 章 旧线')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '永久删除第 9 章 旧线' }))
    await waitFor(() => expect(api.chapterImpact).toHaveBeenCalledWith(9))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText(/正文 12/)).toBeTruthy()
    expect(within(dialog).getByText(/版本 2/)).toBeTruthy()

    fireEvent.click(within(dialog).getByRole('button', { name: '永久删除' }))

    await waitFor(() => expect(api.deleteChapter).toHaveBeenCalledWith(9, 'impact-token-9'))
    expect(onArchivedChanged).toHaveBeenCalled()
  })
})
