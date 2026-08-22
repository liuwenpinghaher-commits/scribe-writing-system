import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { PulseBar } from '../PulseBar'

const apiMock = vi.hoisted(() => ({
  chapterPulse: vi.fn(),
  getWork: vi.fn(() => 'demo'),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('PulseBar 灯位', () => {
  beforeEach(() => {
    apiMock.chapterPulse.mockResolvedValue({
      dimensions: [
        { dimension: 'promise', severity: 'info', items: [] },
        { dimension: 'arc', severity: 'nudge', items: [{ message: '弧有缺口' }] },
        { dimension: 'quality', severity: 'decision', items: [{ message: '需决' }] },
      ],
    })
  })

  it('只渲色点，不把伏笔/弧光等字贴在意图旁', async () => {
    render(<PulseBar seq={1} />)
    const bar = await screen.findByTestId('pulse-bar')
    expect(bar.textContent).not.toContain('伏笔')
    expect(bar.textContent).not.toContain('弧光')
    expect(screen.getByTestId('pulse-promise').getAttribute('aria-label')).toContain('伏笔')
    expect(screen.getByTestId('pulse-arc').getAttribute('title')).toContain('弧光')
  })

  it('详情浮层 portal 到 body，fixed + 高层级，不被正文叠住', async () => {
    render(<PulseBar seq={1} />)
    fireEvent.click(await screen.findByTestId('pulse-arc'))
    const pop = await screen.findByTestId('pulse-popover')
    await waitFor(() => expect(pop.className).toContain('fixed'))
    expect(pop.className).toContain('z-[80]')
    expect(pop.parentElement).toBe(document.body)
    expect(pop.textContent).toContain('弧有缺口')
  })
})
