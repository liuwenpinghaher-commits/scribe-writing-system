import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DeduceStage } from '../DeduceStage'

vi.mock('../api', () => ({
  api: {
    patchChapter: vi.fn(() => Promise.resolve({})),
    chapter: vi.fn(() => Promise.resolve({ deductions: [] })),
    chatWrite: vi.fn(),
  },
}))

vi.mock('../editor/RichEditor.jsx', () => ({
  RichEditor: ({ className }) => <div data-testid="rich-editor" className={className} />,
  useUnsavedGuard: vi.fn(),
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
  it('在三栏详情中使用宽工作台容器,不沿用普通阶段窄文稿宽度', () => {
    render(<DeduceStage seq={1} meta={{ chars: [], deductions: [] }} work="demo" />)

    const stage = screen.getByTestId('deduce-stage')
    expect(stage.className).toContain('w-full')
    expect(stage.className).toContain('max-w-[min(1120px,calc(100%-48px))]')
    expect(stage.className).not.toContain('max-w-[48rem]')
    expect(screen.getByTestId('rich-editor').className).toContain('w-full')
  })
})
