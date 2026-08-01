import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ProposalBar } from '../ChiefSlotContext'

describe('ProposalBar', () => {
  it('草稿阶段的“填入草稿框”也暴露稳定的作者接受标识', () => {
    render(
      <ProposalBar
        text="主编生成了草稿"
        actions={[{ label: '填入草稿框', onClick: vi.fn() }]}
      />,
    )

    expect(screen.getByTestId('stage-fill').textContent).toContain('填入草稿框')
  })
})
