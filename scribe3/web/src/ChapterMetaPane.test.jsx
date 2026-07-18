import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChapterMetaPane } from './ChapterMetaPane'

vi.mock('./api', () => ({
  api: { chapter: vi.fn(), listVolumes: vi.fn(), patchChapter: vi.fn() },
}))
vi.mock('./ui/Toast.jsx', () => ({ useToast: () => vi.fn() }))

const { api } = await import('./api')

describe('ChapterMetaPane', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.chapter.mockResolvedValue({ title: '第1章', label: '', volume: null })
    api.listVolumes.mockResolvedValue([{ id: 'vol:one', title: '第一卷·退潮之名' }])
    api.patchChapter.mockResolvedValue({ ok: true })
  })

  it('让作者从界面编辑章节标题、标签和所属卷', async () => {
    const onSaved = vi.fn()
    render(<ChapterMetaPane seq={1} work="book-test" onSaved={onSaved} />)

    await screen.findByDisplayValue('第1章')
    fireEvent.change(screen.getByLabelText('章节标题'), { target: { value: '闸底刻名' } })
    fireEvent.change(screen.getByLabelText('章节标签'), { target: { value: 'draft' } })
    fireEvent.change(screen.getByLabelText('所属卷'), { target: { value: 'vol:one' } })
    fireEvent.click(screen.getByRole('button', { name: '保存章节信息' }))

    await waitFor(() => expect(api.patchChapter).toHaveBeenCalledWith(1, {
      title: '闸底刻名', label: 'draft', volume: 'vol:one',
    }, 'book-test'))
    expect(onSaved).toHaveBeenCalledWith({ title: '闸底刻名', label: 'draft', volume: 'vol:one' })
  })
})
