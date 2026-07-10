import { useState } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'
import { TopbarSlotProvider } from '../TopbarSlotContext'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  archiveChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../BriefPanel', () => ({ BriefPanel: ({ seq }) => <div data-testid="brief-panel">简报:{seq}</div> }))
vi.mock('../FramePanel', () => ({ FramePanel: ({ focalizer, chapter }) => <div data-testid="frame-panel">关联:{focalizer}:{chapter}</div> }))
vi.mock('../NorthStarPanel', () => ({ NorthStarPanel: ({ seq }) => <div data-testid="northstar-panel">北极星:{seq}</div> }))
vi.mock('../NorthStarBar', () => ({ NorthStarBar: () => <div data-testid="northstar-bar" /> }))
vi.mock('../WriteLayout', () => ({ WriteLayout: () => <div data-testid="write-layout" /> }))
vi.mock('../DeduceStage', () => ({ DeduceStage: () => <div data-testid="deduce-stage" /> }))
vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: () => <textarea aria-label="mock-editor" />,
  useUnsavedGuard: () => {},
}))

function StudioHarness({ onArchived } = {}) {
  const [slot, setSlot] = useState(null)
  return (
    <TopbarSlotProvider onSlot={setSlot}>
      <div data-testid="topbar-slot">{slot}</div>
      <ChiefSlotProvider>
        <ChapterStudio work="demo" seq={3} initialPhase="outline" onArchived={onArchived} />
      </ChiefSlotProvider>
    </TopbarSlotProvider>
  )
}

function renderStudio(props) {
  return render(
    <StudioHarness {...props} />,
  )
}

describe('ChapterStudio 章工作台归位', () => {
  beforeEach(() => {
    localStorage.clear()
    apiMock.chapter.mockResolvedValue({ title: '三', synopsis: '', beats: [], focalizer: 'role:小翠', prose: '', deductions: [], involved_characters: [] })
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.latestDraft.mockResolvedValue({ prose: '', summary: '' })
    apiMock.archiveChapter.mockResolvedValue({ status: 'archived', seq: 3 })
  })

  it('章工作台提供简报、关联、北极星页签并渲染对应面板', async () => {
    renderStudio()

    fireEvent.click(await screen.findByRole('button', { name: /简报/ }))
    expect((await screen.findByTestId('brief-panel')).textContent).toBe('简报:3')

    fireEvent.click(screen.getByRole('button', { name: /关联/ }))
    expect((await screen.findByTestId('frame-panel')).textContent).toBe('关联:role:小翠:3')

    fireEvent.click(screen.getByRole('button', { name: /北极星/ }))
    expect((await screen.findByTestId('northstar-panel')).textContent).toBe('北极星:3')
  })

  it('章工作台提供归档章节入口,确认后调用章节归档并通知外层刷新', async () => {
    const onArchived = vi.fn()
    renderStudio({ onArchived })

    fireEvent.click(await screen.findByRole('button', { name: '归档章节' }))
    fireEvent.click(screen.getByRole('button', { name: '归档' }))

    expect(apiMock.archiveChapter).toHaveBeenCalledWith(3, '')
    await waitFor(() => expect(onArchived).toHaveBeenCalledWith(3))
  })
})
