import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DraftCard } from './DraftCard'

describe('DraftCard', () => {
  it('把作者实际可见的章节提案正文暴露为稳定的验收语义', () => {
    render(
      <DraftCard
        proposal={{ scope: 'chapter', prose: '退潮露出礁脊，他借湿木板横过缺口。' }}
        candidates={[]}
        streaming={false}
        onAccept={vi.fn()}
        onReject={vi.fn()}
      />,
    )

    expect(screen.getByTestId('draft-card')).toBeTruthy()
    expect(screen.getByTestId('draft-proposal-text').textContent).toContain('退潮露出礁脊')
  })

  it('把作者实际可见的选区候选正文暴露为稳定的验收语义', () => {
    render(
      <DraftCard
        proposal={null}
        candidates={['退潮露出礁脊，他借湿木板横过缺口。']}
        streaming={false}
        onAccept={vi.fn()}
        onReject={vi.fn()}
        onAcceptCandidate={vi.fn()}
      />,
    )

    expect(screen.getByTestId('draft-candidate-text').textContent).toContain('退潮露出礁脊')
  })
})
