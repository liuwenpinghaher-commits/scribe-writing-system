import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'

const toast = vi.hoisted(() => vi.fn())
const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  chapters: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  saveDraft: vi.fn(),
  saveChapter: vi.fn(),
  materialRefsByChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../ui/Toast.jsx', () => ({ useToast: () => toast }))
vi.mock('../WriteLayout', async () => {
  const React = await import('react')
  return {
    WriteLayout: () => <div data-testid="write-layout" />,
    RestoreContext: React.createContext(0),
  }
})
vi.mock('../DeduceStage', () => ({ DeduceStage: () => <div data-testid="deduce-stage" /> }))
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: ({ value, onChange, ariaLabel }) => (
    <textarea aria-label={ariaLabel} value={value || ''} onChange={(event) => onChange?.(event.target.value)} />
  ),
  useUnsavedGuard: () => {},
}))

function renderStudio() {
  return render(
    <ChiefSlotProvider>
      <ChapterStudio work="demo" seq={1} initialPhase="draft" />
    </ChiefSlotProvider>,
  )
}

describe('ChapterStudio 草稿采用正文事务', () => {
  beforeEach(() => {
    localStorage.clear()
    toast.mockReset()
    apiMock.chapter.mockResolvedValue({
      title: '质量闭环正文', synopsis: '本章大纲', beats: ['节拍'], focalizer: 'role:林雾',
      prose: '', scene_truth: '码头涨潮', scene_truth_revision: 1,
      deductions: [{ character_id: 'role:林雾', prose: '林雾只知道涨潮', based_on_truth_rev: 1 }],
      involved_characters: ['role:林雾'],
    })
    apiMock.chapters.mockResolvedValue([{ seq: 1 }])
    apiMock.entities.mockResolvedValue([{ id: 'role:林雾', kind: 'character', name: '林雾' }])
    apiMock.latestDraft.mockResolvedValue({ prose: '潮水越过木桩，林雾没有回头。', summary: '悬念草稿' })
    apiMock.materialRefsByChapter.mockResolvedValue([])
    apiMock.saveDraft.mockResolvedValue({ ok: true })
  })

  it('工艺门拒绝采用时保留草稿且不虚报正文已采用', async () => {
    apiMock.saveChapter.mockRejectedValue(Object.assign(new Error('HTTP 409'), {
      body: {
        detail: {
          message: '工艺门阻止采用：缺少已确认的章节节拍',
          blocking: ['GATE-A'],
          root_causes: ['beats_missing'],
        },
      },
    }))
    renderStudio()

    await screen.findByTestId('chapter-workbench-shell')
    expect(screen.getByRole('textbox', { name: '草稿正文' }).value).toContain('林雾没有回头')
    fireEvent.click(screen.getByRole('button', { name: '采用为正文' }))

    await waitFor(() => expect(apiMock.saveChapter).toHaveBeenCalledWith(
      1, '潮水越过木桩，林雾没有回头。', '质量闭环正文', 'role:林雾',
    ))
    await waitFor(() => expect(toast).toHaveBeenCalled())

    expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('draft')
    expect(screen.getByRole('textbox', { name: '草稿正文' }).value).toContain('林雾没有回头')
    const messages = toast.mock.calls.map(([message]) => String(message)).join('\n')
    expect(messages).toContain('工艺门阻止采用：缺少已确认的章节节拍')
    expect(messages).not.toContain('已采用为正文')
    expect(messages).not.toContain('[object Object]')
  })
})
