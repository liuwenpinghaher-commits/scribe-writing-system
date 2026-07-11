import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DeduceTree } from '../DeduceTree'
import { api } from '../api'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  entities: vi.fn(),
  patchChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../deduceContext', () => ({
  useDeduceSel: () => ({ selected: 'truth', setSelected: vi.fn() }),
}))
vi.mock('../selectionContext', () => ({
  useSelection: () => ({ setFocus: vi.fn() }),
}))

const baseChapter = {
  title: '四',
  synopsis: '崔判在纸命契前停下。',
  beats: [{ text: '纸灯忽明忽暗。' }],
  scene_truth: '',
  involved_characters: [],
  deductions: [],
}

const syncedChapter = {
  ...baseChapter,
  involved_characters: ['role:崔判'],
}

const characters = [
  { id: 'role:崔判', kind: 'character', name: '崔判' },
  { id: 'role:苏纸鸢', kind: 'character', name: '苏纸鸢' },
]

const tick = () => new Promise((resolve) => setTimeout(resolve, 20))

describe('DeduceTree read-only inference', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.chapter.mockResolvedValue(baseChapter)
    apiMock.entities.mockResolvedValue(characters)
    apiMock.patchChapter.mockResolvedValue({})
  })

  it('打开演绎树只显示涉及角色建议,不自动 patch 本章', async () => {
    render(<DeduceTree seq={4} />)

    await waitFor(() => expect(api.chapter).toHaveBeenCalledWith(4))
    await waitFor(() => expect(api.entities).toHaveBeenCalled())
    await tick()

    expect(api.patchChapter).not.toHaveBeenCalled()
    const suggestion = await screen.findByRole('status')
    expect(within(suggestion).getByText(/检测到可能涉及角色/)).toBeTruthy()
    expect(within(suggestion).getByText(/崔判/)).toBeTruthy()
  })

  it('点击同步到本章后才写 involved_characters', async () => {
    apiMock.chapter
      .mockResolvedValueOnce(baseChapter)
      .mockResolvedValueOnce(syncedChapter)

    render(<DeduceTree seq={4} />)

    fireEvent.click(await screen.findByRole('button', { name: /同步到本章/ }))

    await waitFor(() => expect(api.patchChapter).toHaveBeenCalledWith(4, {
      involved_characters: ['role:崔判'],
    }))
    await waitFor(() => expect(api.chapter).toHaveBeenCalledTimes(2))
  })
})
