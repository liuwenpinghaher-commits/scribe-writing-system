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

  it('卷叙事字段只读,让主编写入不调用 patchVolume', async () => {
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))

    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)

    expect(await screen.findByTestId('volume-meta-readonly')).toBeTruthy()
    expect(screen.getByText('卷纲正文')).toBeTruthy()
    fireEvent.click(screen.getByTestId('volume-ask-chief'))

    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(tabs).toContain('chief')
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
