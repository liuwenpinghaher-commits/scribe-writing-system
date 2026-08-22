import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VolumeDetailPane } from './VolumeDetailPane'

vi.mock('../api', () => ({
  api: { outline: vi.fn(), patchVolume: vi.fn(), createChapter: vi.fn(), addVolume: vi.fn(), reorderChapters: vi.fn(), codexCompleteness: vi.fn(), volumeReview: vi.fn() },
}))
vi.mock('../ui/Toast', () => ({ showToast: vi.fn() }))

const { api } = await import('../api')

describe('VolumeDetailPane', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    api.outline.mockResolvedValue({
      volumes: [{ id: 'vol-2', title: '第二卷', intro: '卷纲正文', color: '#123456', sort_order: 2 }],
      chapters: [],
    })
    api.codexCompleteness.mockResolvedValue({ advisory: true, blocks_write: false, report: { missing_dimensions: [], char_issues: [] } })
    api.volumeReview.mockResolvedValue(null)
  })

  it('正式卷草稿缓冲 + 让主编写入点名 s3_patch_volume，不调用 patchVolume REST', async () => {
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))

    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)

    expect(await screen.findByTestId('volume-meta-draft')).toBeTruthy()
    expect(screen.getByTestId('volume-draft-intro').value).toContain('卷纲正文')
    fireEvent.change(screen.getByTestId('volume-draft-intro'), {
      target: { value: '草稿改后的卷纲' },
    })
    expect(await screen.findByTestId('volume-draft-dirty')).toBeTruthy()
    fireEvent.click(screen.getByTestId('volume-ask-chief'))

    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(tabs).toContain('chief')
    expect(seeds[0]).toMatch(/s3_patch_volume/)
    expect(seeds[0]).toMatch(/volume_id=vol-2/)
    expect(seeds[0]).toMatch(/草稿改后的卷纲/)
    expect(api.patchVolume).not.toHaveBeenCalled()
  })

  it('新建章走主编种子,不调用 createChapter REST', async () => {
    const seeds = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)
    expect(await screen.findByTestId('volume-create-chapter')).toBeTruthy()
    fireEvent.click(screen.getByTestId('volume-create-chapter'))
    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(seeds[0]).toMatch(/s3_add_chapter/)
    expect(api.createChapter).not.toHaveBeenCalled()
  })

  it('侧栏列出本卷还没办的几笔，章下展示梗概', async () => {
    api.outline.mockResolvedValue({
      volumes: [{ id: 'vol-2', title: '第二卷', intro: '只写了华山那一夜', color: '#123456', sort_order: 2 }],
      chapters: [
        { seq: 1, title: '华山成核', volume: 'vol-2', synopsis: '按碎片', has_prose: true, word_count: 1900, label: '定稿' },
        { seq: 2, title: '四十二度', volume: 'vol-2', synopsis: '体温标价', has_prose: false, word_count: 0, label: '未设' },
        { seq: 3, title: '金縢裂纹', volume: 'vol-2', synopsis: '', has_prose: false, word_count: 0 },
      ],
    })
    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)
    expect(await screen.findByText('体温标价')).toBeTruthy()
    expect(screen.getByText('这章还没立要办的事')).toBeTruthy()
    const later = await screen.findByTestId('volume-remaining-later')
    expect(later.textContent).toMatch(/四十二度/)
    expect(later.textContent).toMatch(/金縢裂纹/)
    expect(later.textContent).not.toMatch(/华山成核/)
    expect(await screen.findByTestId('volume-intro-one-night')).toBeTruthy()
  })

  it('章下列出定稿记下的那句话', async () => {
    api.outline.mockResolvedValue({
      volumes: [{ id: 'vol-2', title: '第二卷', intro: '华山成核 / 四十二度', color: '#123456', sort_order: 2 }],
      chapters: [
        { seq: 1, title: '华山成核', volume: 'vol-2', synopsis: '按碎片', has_prose: true, word_count: 1900, settled_note: '第1章办成了：把碎片按回裂口' },
      ],
    })
    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)
    expect(await screen.findByTestId('chapter-settled-note')).toHaveTextContent('把碎片按回裂口')
  })

  it('侧栏列出纲改过还没核完的章', async () => {
    api.outline.mockResolvedValue({
      volumes: [{ id: 'vol-2', title: '第二卷', intro: '华山成核 / 四十二度', color: '#123456', sort_order: 2 }],
      chapters: [
        { seq: 1, title: '华山成核', volume: 'vol-2', synopsis: '按碎片', outline_status: 'stale' },
        { seq: 2, title: '四十二度', volume: 'vol-2', synopsis: '体温标价', outline_status: 'review' },
        { seq: 3, title: '金縢裂纹', volume: 'vol-2', synopsis: '裂纹', outline_status: 'frozen' },
      ],
    })
    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)
    const box = await screen.findByTestId('volume-pending-human')
    expect(box.textContent).toMatch(/华山成核/)
    expect(box.textContent).toMatch(/还没冻回去/)
    expect(box.textContent).toMatch(/冻回去/)
    expect(box.textContent).toMatch(/四十二度/)
    expect(box.textContent).toMatch(/看一眼对不对/)
    expect(box.textContent).toMatch(/逃生口/)
    expect(box.textContent).not.toMatch(/金縢裂纹/)
  })

  it('侧栏列出设定还缺什么，不挡写', async () => {
    api.codexCompleteness.mockResolvedValue({
      advisory: true,
      blocks_write: false,
      report: {
        missing_dimensions: ['世界规则(魔法体系/物理法则/社会制度)'],
        char_issues: [{ name: '柳岸青', issues: ['缺他要什么'] }],
      },
    })
    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)
    const box = await screen.findByTestId('volume-setting-gaps')
    expect(box.textContent).toMatch(/世界规则/)
    expect(box.textContent).toMatch(/柳岸青/)
    expect(box.textContent).toMatch(/缺他要什么/)
  })
})
