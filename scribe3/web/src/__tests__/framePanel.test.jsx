import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { FramePanel } from '../FramePanel'
import { SelectionProvider } from '../selectionContext'

const apiMock = vi.hoisted(() => ({
  frame: vi.fn(),
  irony: vi.fn(),
  intent: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

function renderFrame() {
  return render(
    <SelectionProvider>
      <FramePanel focalizer="role:小翠" chapter={3} />
    </SelectionProvider>,
  )
}

describe('FramePanel 限知帧决策面板', () => {
  beforeEach(() => {
    apiMock.frame.mockResolvedValue([
      { id: 'f1', entity: '柳怀玉', attribute: '知道', value: '借命契存在', chapter: 1 },
      { id: 'f2', entity: '柳怀玉', attribute: '秘密', value: null, chapter: 2 },
    ])
    apiMock.irony.mockResolvedValue([
      { id: 'i1', entity: '读者', attribute: '真相', value: '续命者为空', chapter: 1 },
    ])
    apiMock.intent.mockResolvedValue({})
  })

  it('显示摘要和可写/禁写/反讽/来源分段', async () => {
    renderFrame()

    await waitFor(() => expect(screen.getByText('可写事实')).toBeTruthy())
    expect(screen.getByText('禁写风险')).toBeTruthy()
    expect(screen.getByText('反讽张力')).toBeTruthy()

    expect(screen.getByRole('button', { name: '可写入正文' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '禁止泄露' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '戏剧反讽' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '来源账本' })).toBeTruthy()

    expect(screen.getByText(/借命契存在/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '禁止泄露' }))
    expect(screen.getByText(/柳怀玉 · 秘密/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '戏剧反讽' }))
    expect(screen.getByText(/续命者为空/)).toBeTruthy()
  })
})
