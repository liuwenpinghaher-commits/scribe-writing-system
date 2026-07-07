import { useState } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'
import { TopbarSlotProvider } from '../TopbarSlotContext'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../BriefPanel', () => ({ BriefPanel: ({ seq }) => <div data-testid="brief-panel">简报:{seq}</div> }))
vi.mock('../FramePanel', () => ({ FramePanel: ({ focalizer, chapter }) => <div data-testid="frame-panel">帧:{focalizer}:{chapter}</div> }))
vi.mock('../NorthStarPanel', () => ({ NorthStarPanel: ({ seq }) => <div data-testid="northstar-panel">北极星:{seq}</div> }))
vi.mock('../WriteLayout', () => ({ WriteLayout: () => <div data-testid="write-layout" /> }))
vi.mock('../DeduceStage', () => ({ DeduceStage: () => <div data-testid="deduce-stage" /> }))
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: () => <textarea aria-label="mock-editor" />,
  useUnsavedGuard: () => {},
}))

function Harness() {
  const [slot, setSlot] = useState(null)
  return (
    <TopbarSlotProvider onSlot={setSlot}>
      <div data-testid="topbar-slot">{slot}</div>
      <div data-testid="detail-body">
        <ChiefSlotProvider>
          <ChapterStudio work="demo" seq={3} initialPhase="outline" />
        </ChiefSlotProvider>
      </div>
    </TopbarSlotProvider>
  )
}

describe('ChapterStudio 顶栏阶段条', () => {
  beforeEach(() => {
    localStorage.clear()
    apiMock.chapter.mockResolvedValue({ title: '三', synopsis: '', beats: [], focalizer: 'role:小翠', prose: '', deductions: [], involved_characters: [] })
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
  })

  it('把章阶段切换条注册到外部顶栏并从栏3移除', async () => {
    render(<Harness />)

    const topbar = await screen.findByTestId('chapter-phase-topbar')
    expect(within(topbar).getByRole('button', { name: /大纲/ })).toBeTruthy()
    expect(within(topbar).getByRole('button', { name: /正文/ })).toBeTruthy()

    const detail = screen.getByTestId('detail-body')
    expect(within(detail).queryByRole('button', { name: /大纲/ })).toBeNull()
    expect(within(detail).queryByRole('button', { name: /简报/ })).toBeNull()

    fireEvent.click(within(topbar).getByRole('button', { name: /简报/ }))
    expect((await screen.findByTestId('brief-panel')).textContent).toBe('简报:3')
  })
})
