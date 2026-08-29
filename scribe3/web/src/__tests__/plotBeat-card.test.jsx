import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChapterCard } from '../ChapterCard.jsx'
import { cardColorVar } from '../outlineColors'
import { ACTION_TOKEN, plotBeat } from '../plotBeat'

vi.mock('@dnd-kit/sortable', () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: () => {},
    transform: null,
    transition: null,
    isDragging: false,
  }),
}))

describe('ChapterCard plot beat', () => {
  it('shows four cells: 视角 动作 输赢 关系', () => {
    render(
      <ChapterCard
        chapter={{
          seq: 12,
          title: '差一步',
          synopsis: '柳岸青付零点五度，交易接口只差一步没合上。',
          focalizer: 'role:柳岸青',
          word_count: 0,
        }}
        colorMode="plot"
      />,
    )
    const strip = screen.getByTestId('plot-beat')
    const t = strip.textContent || ''
    expect(t).toContain('柳岸青')
    expect(t).toContain('买')
    expect(t).toContain('半成')
    expect(t).toContain('未变')
  })

  it('plot color mode uses action token so 买 chapters share a stripe', () => {
    const a = { synopsis: '付零点五度买三息' }
    const b = { synopsis: '付腕内零点四度买验锁三息，交差被锁' }
    expect(plotBeat(a).action).toBe('买')
    expect(plotBeat(b).action).toBe('买')
    expect(cardColorVar(a, 'plot')).toBe(`var(--color-${ACTION_TOKEN.买})`)
    expect(cardColorVar(b, 'plot')).toBe(cardColorVar(a, 'plot'))
  })
})
