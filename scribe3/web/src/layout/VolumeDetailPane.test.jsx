import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VolumeDetailPane } from './VolumeDetailPane'

vi.mock('../api', () => ({
  api: { outline: vi.fn(), patchVolume: vi.fn(), createChapter: vi.fn(), addVolume: vi.fn(), reorderChapters: vi.fn() },
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
})
