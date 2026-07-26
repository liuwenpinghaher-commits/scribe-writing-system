import { render, screen, waitFor } from '@testing-library/react'
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

describe('DeduceTree stale badge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.entities.mockResolvedValue([
      { id: 'role:哑姑', kind: 'character', name: '哑姑' },
    ])
    apiMock.patchChapter.mockResolvedValue({})
  })

  it('真相 revision 高于投影 based_on 时显示过期', async () => {
    apiMock.chapter.mockResolvedValue({
      title: '四',
      synopsis: '哑姑在井边',
      beats: [],
      scene_truth: '新真相',
      scene_truth_revision: 3,
      involved_characters: ['role:哑姑'],
      deductions: [{ character_id: 'role:哑姑', prose: '旧投影', based_on_truth_rev: 1 }],
    })
    render(<DeduceTree seq={4} />)
    await waitFor(() => expect(api.chapter).toHaveBeenCalledWith(4))
    expect(await screen.findByTestId('deduce-stale-badge')).toBeTruthy()
    expect(screen.getByTestId('deduce-stale-badge').textContent).toMatch(/过期/)
  })
})
