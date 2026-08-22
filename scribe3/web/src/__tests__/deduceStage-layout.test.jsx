import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DeduceStage, GENERATE_TIMEOUT_MS } from '../DeduceStage'

vi.mock('../api', () => ({
  api: {
    patchChapter: vi.fn(() => Promise.resolve({})),
    chapter: vi.fn(() => Promise.resolve({ deductions: [] })),
    chatWrite: vi.fn(),
    aiRunPendingApproval: vi.fn(() => Promise.resolve({ runs: [] })),
  },
}))

vi.mock('../deduceContext', () => ({
  useDeduceSel: () => ({ selected: 'truth', setSelected: vi.fn() }),
}))

vi.mock('../context/ContextSnapshotContext', () => ({
  useContextSnapshot: () => ({ snapshot: null }),
}))

vi.mock('../ChiefSlotContext', () => ({
  ProposalBar: () => <div data-testid="proposal-bar" />,
  useStageProposal: () => ({ pending: null, clear: vi.fn() }),
  useChiefSlot: () => ({ setChiefIntent: vi.fn() }),
}))

vi.mock('../ui/Toast.jsx', () => ({
  useToast: () => vi.fn(),
}))

describe('DeduceStage 布局', () => {
  it('为真实 TokenPlan 长推理保留六分钟窗口，不在模型完成前自动取消', () => {
    expect(GENERATE_TIMEOUT_MS).toBe(360000)
  })

  it('在三栏详情中使用宽工作台容器,不沿用普通阶段窄文稿宽度', () => {
    render(<DeduceStage seq={1} meta={{ chars: [], deductions: [] }} work="demo" />)

    const stage = screen.getByTestId('deduce-stage')
    expect(stage.className).toContain('w-full')
    expect(stage.className).toContain('max-w-[min(1120px,calc(100%-24px))]')
    expect(stage.className).not.toContain('max-w-[48rem]')
    expect(screen.getByTestId('deduce-readonly').className).toContain('flex-1')
    const panel = screen.getByTestId('parallel-deduce-panel')
    expect(panel.tagName).toBe('DETAILS')
    expect(panel.open).toBe(false)
  })

  it('未绑定章节时不渲染可写编辑器，避免把内容保存到 /chapters/undefined', () => {
    render(<DeduceStage seq={undefined} meta={{ chars: [], deductions: [] }} work="demo" />)

    expect(screen.getByTestId('deduce-stage-missing-chapter')).toBeTruthy()
    expect(screen.queryByTestId('deduce-readonly')).toBeNull()
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})
