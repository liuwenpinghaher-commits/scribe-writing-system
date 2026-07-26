import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  chapters: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  archiveChapter: vi.fn(),
  materialRefsByChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../WriteLayout', async () => {
  const React = await import('react')
  return {
    WriteLayout: () => <div data-testid="write-layout" />,
    RestoreContext: React.createContext(0),
  }
})
vi.mock('../DeduceStage', () => ({ DeduceStage: ({ seq }) => <div data-testid="deduce-stage">演绎:{seq}</div> }))
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: () => <textarea aria-label="mock-editor" />,
  useUnsavedGuard: () => {},
}))

function renderStudio(props = {}) {
  return render(
    <ChiefSlotProvider>
      <ChapterStudio work="demo" seq={3} initialPhase="outline" {...props} />
    </ChiefSlotProvider>,
  )
}

describe('演绎软门 + 生产入口', () => {
  beforeEach(() => {
    localStorage.clear()
    apiMock.chapters.mockResolvedValue([{ seq: 1 }, { seq: 2 }, { seq: 3 }])
    apiMock.entities.mockResolvedValue([
      { id: 'role:哑姑', kind: 'character', name: '哑姑' },
      { id: 'role:老范', kind: 'character', name: '老范' },
    ])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
    apiMock.archiveChapter.mockResolvedValue({ status: 'archived', seq: 3 })
    apiMock.materialRefsByChapter.mockResolvedValue([])
  })

  it('切到草稿时 missing/stale 显示 deduce-soft-gate 条，不阻断草稿壳', async () => {
    apiMock.chapter.mockResolvedValue({
      title: '三',
      synopsis: '大纲',
      beats: [],
      focalizer: 'role:哑姑',
      prose: '',
      scene_truth: '井边有人',
      scene_truth_revision: 2,
      involved_characters: ['role:哑姑', 'role:老范'],
      deductions: [
        { character_id: 'role:哑姑', prose: '旧投影', based_on_truth_rev: 1 },
      ],
    })
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')
    fireEvent.click(await screen.findByRole('tab', { name: '草稿' }))
    const gate = await screen.findByTestId('deduce-soft-gate')
    expect(gate.textContent).toMatch(/未齐|未演绎|过期/)
    expect(screen.getByTestId('deduce-soft-gate-go')).toBeTruthy()
    // 草稿壳仍在（软门不硬卡）
    expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('draft')
  })

  it('点「去补演绎」回到演绎阶段', async () => {
    apiMock.chapter.mockResolvedValue({
      title: '三',
      synopsis: '',
      beats: [],
      scene_truth: 't',
      scene_truth_revision: 1,
      involved_characters: ['role:哑姑'],
      deductions: [],
    })
    renderStudio()
    fireEvent.click(await screen.findByRole('tab', { name: '草稿' }))
    fireEvent.click(await screen.findByTestId('deduce-soft-gate-go'))
    await waitFor(() => expect(screen.getByTestId('deduce-stage')).toBeTruthy())
  })

  it('演绎齐备时不显示 soft-gate', async () => {
    apiMock.chapter.mockResolvedValue({
      title: '三',
      synopsis: '',
      beats: [],
      scene_truth: '真相',
      scene_truth_revision: 1,
      involved_characters: ['role:哑姑'],
      deductions: [
        { character_id: 'role:哑姑', prose: '完整投影', based_on_truth_rev: 1 },
      ],
    })
    renderStudio()
    fireEvent.click(await screen.findByRole('tab', { name: '草稿' }))
    await screen.findByTestId('chapter-workbench-shell')
    expect(screen.queryByTestId('deduce-soft-gate')).toBeNull()
  })

  it('生产章工作台不挂载遗留 DeducePanel', async () => {
    apiMock.chapter.mockResolvedValue({
      title: '三', synopsis: '', beats: [], scene_truth: '', deductions: [], involved_characters: [],
    })
    renderStudio()
    await screen.findByTestId('chapter-workbench-shell')
    fireEvent.click(await screen.findByRole('tab', { name: '演绎' }))
    expect(await screen.findByTestId('deduce-stage')).toBeTruthy()
    expect(screen.queryByText(/演绎某角色/)).toBeNull()
    expect(document.querySelector('[data-testid="deduce-panel"]')).toBeNull()
  })
})
