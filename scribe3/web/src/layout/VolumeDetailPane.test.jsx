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
    api.outline.mockResolvedValue({
      volumes: [{ id: 'vol-2', title: '第二卷', intro: '卷纲', color: '#123456', sort_order: 2 }],
      chapters: [],
    })
    api.patchVolume.mockResolvedValue({ status: 'updated' })
  })

  it('让作者编辑卷排序并随卷信息一起保存', async () => {
    render(<VolumeDetailPane node={{ id: 'vol:vol-2', type: 'volume', ref: 'vol-2', label: '第二卷' }} />)

    await screen.findByDisplayValue('第二卷')
    fireEvent.change(screen.getByLabelText('卷排序'), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: '保存卷信息' }))

    await waitFor(() => expect(api.patchVolume).toHaveBeenCalledWith('vol-2', {
      title: '第二卷', intro: '卷纲', color: '#123456', sort_order: 5,
    }))
  })
})
