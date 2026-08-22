import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ChiefDock } from '../ChiefDock'
import { ChiefSlotProvider } from '../ChiefSlotContext'
import { Rail } from '../shell'
import { useRightDockController } from '../studioDocks'

const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'demo'),
  chapterPulse: vi.fn(() => Promise.resolve({ checks: [] })),
  inbox: vi.fn(() => Promise.resolve({ items: [], count: 0 })),
  chapterVersions: vi.fn(() => Promise.resolve([])),
  selectLightLatest: vi.fn(() => Promise.resolve(null)),
  selectLatest: vi.fn(() => Promise.resolve(null)),
  selectLight: vi.fn(),
  selectChapter: vi.fn(),
  pilotStatus: vi.fn(() => Promise.resolve({ state: 'idle', can_step: true, pipeline: [] })),
  pilotRunStatus: vi.fn(() => Promise.resolve({ running: false })),
  threadMessages: vi.fn(),
  chatStream: vi.fn(),
  chatWrite: vi.fn(),
  aiUsage: vi.fn(() => Promise.resolve(null)),
}))

vi.mock('../api', () => ({ api: apiMock }))

function DockHarness() {
  const controller = useRightDockController({
    sel: { mode: 'node', node: { type: 'chapter', ref: 3, id: 'ch:3', label: '3' } },
    chapterSel: true,
    seq: 3,
    lastSeq: 3,
  })
  return (
    <>
      <Rail
        side="left"
        caps={[]}
        active=""
        onActive={() => {}}
        secondaryCaps={controller.caps}
        secondaryActive={controller.activeKey}
        onSecondaryClick={controller.activate}
      />
      <div data-testid="dock">{controller.activeKey}</div>
    </>
  )
}

function ChatHarness() {
  return (
    <ChiefSlotProvider>
      <ChiefDock
        chapterSel
        lastSeq={3}
        sel={{ mode: 'node', node: { id: 'ch:3', type: 'chapter', ref: 3, label: '3 铜炉' } }}
      />
    </ChiefSlotProvider>
  )
}

describe('主编模式融合', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    apiMock.inbox.mockResolvedValue({ items: [], count: 0 })
  })

  it('右栏不再有选择环/主编驾驶 tab', () => {
    render(
      <ChiefSlotProvider>
        <DockHarness />
      </ChiefSlotProvider>,
    )
    expect(screen.getByRole('button', { name: '主编' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /选择环/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /主编驾驶/ })).toBeNull()
    expect(screen.getByRole('button', { name: '存档' })).toBeTruthy()
  })

  it('s3-right-tab=selection 仍打开主编 tab', () => {
    render(
      <ChiefSlotProvider>
        <DockHarness />
      </ChiefSlotProvider>,
    )
    fireEvent(window, new CustomEvent('s3-right-tab', { detail: 'selection' }))
    expect(screen.getByTestId('dock').textContent).toBe('chief')
  })

  it('切选择模式不卸对话壳，并挂上选择条', async () => {
    render(<ChatHarness />)
    expect(await screen.findByTestId('chief-mode-bar')).toBeTruthy()
    expect(screen.getByTestId('chief-chat-shell')).toBeTruthy()
    fireEvent.click(screen.getByTestId('chief-mode-select'))
    expect(await screen.findByTestId('selection-panel')).toBeTruthy()
    expect(screen.getByTestId('chief-chat-shell')).toBeTruthy()
  })

  it('切驾驶模式挂驾驶条且对话仍在', async () => {
    render(<ChatHarness />)
    fireEvent.click(screen.getByTestId('chief-mode-pilot'))
    await waitFor(() => expect(screen.getByTestId('chief-pilot-strip')).toBeTruthy())
    expect(screen.getByTestId('chief-chat-shell')).toBeTruthy()
  })
})
