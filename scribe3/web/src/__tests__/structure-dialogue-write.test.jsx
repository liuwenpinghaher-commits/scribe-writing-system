/**
 * 结构面(卷/章)主路径禁止 REST 直写世界结构;须种子主编走 s3_* 审批。
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VolumeDetailPane } from '../layout/VolumeDetailPane.jsx'

vi.mock('../api', () => ({
  api: {
    outline: vi.fn(),
    patchVolume: vi.fn(),
    createChapter: vi.fn(),
    addVolume: vi.fn(),
    reorderChapters: vi.fn(),
  },
}))
vi.mock('../ui/Toast', () => ({ showToast: vi.fn() }))

const { api } = await import('../api')

describe('structure dialogue-write (volume/chapter)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    api.outline.mockResolvedValue({
      volumes: [{ id: 'v1', title: '卷一', intro: '', color: '', sort_order: 0 }],
      chapters: [{ seq: 1, title: '开篇', volume: null, word_count: 0 }],
      unassigned_chapters: [1],
    })
  })

  it('未分卷「创建分卷」不调用 addVolume,只种子主编', async () => {
    const seeds = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    render(
      <VolumeDetailPane
        node={{ id: 'vol:null', type: 'volume', ref: null, label: '未分卷' }}
      />,
    )
    const title = await screen.findByLabelText('新卷名')
    fireEvent.change(title, { target: { value: '潮生卷' } })
    fireEvent.click(screen.getByTestId('volume-create-from-unassigned'))
    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(seeds.join('\n')).toMatch(/s3_add_volume/)
    expect(seeds.join('\n')).toMatch(/潮生卷/)
    expect(api.addVolume).not.toHaveBeenCalled()
    expect(api.reorderChapters).not.toHaveBeenCalled()
  })
})
