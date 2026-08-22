import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { NorthStarBar } from '../NorthStarBar'

const apiMock = vi.hoisted(() => ({
  intent: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('NorthStarBar 收起/展开', () => {
  beforeEach(() => {
    apiMock.intent.mockResolvedValue({
      reader_feeling: '压抑中见微光',
      emotional_arc: '由怯到决',
      red_lines: '不写超自然',
    })
  })

  it('默认一行截断，不展开三格', async () => {
    render(<NorthStarBar />)
    const summary = await screen.findByTestId('northstar-summary')
    expect(summary.className).toContain('truncate')
    expect(screen.queryByTestId('northstar-readonly')).toBeNull()
    expect(screen.getByRole('button', { expanded: false })).toBeTruthy()
  })

  it('点击后展开三格，字号跟顶栏一致', async () => {
    render(<NorthStarBar />)
    await screen.findByTestId('northstar-summary')
    fireEvent.click(screen.getByTestId('northstar-bar').querySelector('button'))
    const panel = await screen.findByTestId('northstar-readonly')
    expect(panel.textContent).toContain('读者感受')
    expect(panel.textContent).toContain('压抑中见微光')
    expect(panel.className).not.toContain('type-stage')
    await waitFor(() => {
      expect(screen.getByRole('button', { expanded: true })).toBeTruthy()
    })
  })
})
