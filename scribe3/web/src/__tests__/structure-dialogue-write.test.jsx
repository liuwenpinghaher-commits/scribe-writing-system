import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VolumeDetailPane } from '../layout/VolumeDetailPane.jsx'

/**
 * 卷/章结构创建与叙事元数据均禁止作者 REST 直写世界结构:
 * 主路径种子主编走 s3_add_volume / s3_add_chapter 审批。
 */
const apiMock = vi.hoisted(() => ({
  outline: vi.fn(),
  patchVolume: vi.fn(),
  createChapter: vi.fn(),
  addVolume: vi.fn(),
  reorderChapters: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../ui/Toast', () => ({ showToast: vi.fn() }))

describe('structure dialogue-write (volume/chapter)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    apiMock.outline.mockResolvedValue({
      volumes: [],
      chapters: [{ seq: 1, title: '开篇', volume: null, word_count: 0 }],
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
    expect(apiMock.addVolume).not.toHaveBeenCalled()
    expect(apiMock.reorderChapters).not.toHaveBeenCalled()
  })
})
