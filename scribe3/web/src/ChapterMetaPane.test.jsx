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
    sessionStorage.clear()
    api.chapter.mockResolvedValue({ title: '第1章', label: '', volume: null })
    api.listVolumes.mockResolvedValue([{ id: 'vol:one', title: '第一卷·退潮之名' }])
  })

  it('章节信息只读,让主编写入不调用 patchChapter', async () => {
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))

    render(<ChapterMetaPane seq={1} work="book-test" onClose={vi.fn()} />)

    expect(await screen.findByTestId('chapter-meta-pane')).toBeTruthy()
    expect(screen.getByText('第1章')).toBeTruthy()
    fireEvent.click(screen.getByTestId('chapter-meta-ask-chief'))

    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(tabs).toContain('chief')
    expect(api.patchChapter).not.toHaveBeenCalled()
  })
})
