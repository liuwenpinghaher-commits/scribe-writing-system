import { useState } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ChapterStudio } from '../ChapterStudio'
import { ChiefSlotProvider } from '../ChiefSlotContext'
import { TopbarSlotProvider } from '../TopbarSlotContext'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  entities: vi.fn(),
  latestDraft: vi.fn(),
  materialRefsByChapter: vi.fn(),
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

function HarnessWithoutInitialPhase() {
  const [slot, setSlot] = useState(null)
  return (
    <TopbarSlotProvider onSlot={setSlot}>
      <div data-testid="topbar-slot">{slot}</div>
      <div data-testid="detail-body">
        <ChiefSlotProvider>
          <ChapterStudio work="demo" seq={3} />
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
    apiMock.materialRefsByChapter.mockResolvedValue({ refs: [] })
  })

  it('把章阶段切换条注册到外部顶栏并从栏3移除', async () => {
    render(<Harness />)

    const topbar = await screen.findByTestId('chapter-phase-topbar')
    expect(within(topbar).getByRole('button', { name: /大纲/ })).toBeTruthy()
    expect(within(topbar).getByRole('button', { name: /正文/ })).toBeTruthy()
    expect(within(topbar).queryByRole('button', { name: /演绎/ })).toBeNull()

    const detail = screen.getByTestId('detail-body')
    expect(within(detail).queryByRole('button', { name: /大纲/ })).toBeNull()
    expect(within(detail).queryByRole('button', { name: /简报/ })).toBeNull()

    fireEvent.click(within(topbar).getByRole('button', { name: /简报/ }))
    expect((await screen.findByTestId('brief-panel')).textContent).toBe('简报:3')
  })

  it('旧持久化 deduce 阶段不会把演绎带回顶栏或栏3', async () => {
    localStorage.setItem('s3.chapter.phase', 'deduce')

    render(<HarnessWithoutInitialPhase />)

    const topbar = await screen.findByTestId('chapter-phase-topbar')
    expect(within(topbar).queryByRole('button', { name: /演绎/ })).toBeNull()
    expect(screen.queryByTestId('deduce-stage')).toBeNull()
    expect(screen.getByTestId('write-layout')).toBeTruthy()
  })

  it('大纲到草稿阶段在栏3共享统一章工作台骨架', async () => {
    render(<Harness />)

    const shell = await screen.findByTestId('chapter-workbench-shell')
    expect(shell.getAttribute('data-phase')).toBe('outline')
    expect(within(shell).getByTestId('chapter-stage-heading').textContent).toBe('大纲')
    expect(within(shell).getByTestId('chapter-stage-meta')).toBeTruthy()
    expect(shell.className).toContain('bg-canvas')

    const topbar = await screen.findByTestId('chapter-phase-topbar')
    fireEvent.click(within(topbar).getByRole('button', { name: /节拍/ }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('beats'))
    expect(screen.getByTestId('chapter-stage-heading').textContent).toBe('节拍')

    fireEvent.click(within(topbar).getByRole('button', { name: /草稿/ }))
    await waitFor(() => expect(screen.getByTestId('chapter-workbench-shell').getAttribute('data-phase')).toBe('draft'))
    expect(screen.getByTestId('chapter-stage-heading').textContent).toBe('草稿')
  })

  it('简报、限知帧、北极星保留原面板结构,不套统一章工作台外壳', async () => {
    render(<Harness />)

    const topbar = await screen.findByTestId('chapter-phase-topbar')
    fireEvent.click(within(topbar).getByRole('button', { name: /简报/ }))
    await screen.findByTestId('brief-panel')
    await waitFor(() => expect(screen.queryByTestId('chapter-workbench-shell')).toBeNull())

    fireEvent.click(within(topbar).getByRole('button', { name: /限知帧/ }))
    await screen.findByTestId('frame-panel')
    await waitFor(() => expect(screen.queryByTestId('chapter-workbench-shell')).toBeNull())

    fireEvent.click(within(topbar).getByRole('button', { name: /北极星/ }))
    await screen.findByTestId('northstar-panel')
    await waitFor(() => expect(screen.queryByTestId('chapter-workbench-shell')).toBeNull())
  })
})
