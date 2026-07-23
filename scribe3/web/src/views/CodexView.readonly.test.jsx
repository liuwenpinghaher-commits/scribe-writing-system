import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act, cleanup } from '@testing-library/react'
import { DetailView, seedChiefCodexWrite } from './CodexView.jsx'

vi.mock('../api', () => {
  const api = new Proxy({}, {
    get: () => vi.fn(() => Promise.resolve([])),
  })
  return { api }
})

vi.mock('../ui/Toast', () => ({ showToast: vi.fn() }))

/** 冲掉 DynamicTimeline / DynamicRelations 的微任务 setState，避免 act 警告 */
async function flushEffects() {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
    await new Promise((r) => setTimeout(r, 0))
  })
}

describe('Codex DetailView 只读（禁表单直填）', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })
  afterEach(() => {
    cleanup()
  })

  it('已有角色：只读横幅 + 让主编写入，无编辑入口', async () => {
    render(
      <DetailView
        type="chars"
        isNew={false}
        row={{ id: 'role:沈砚', name: '沈砚', appearance: '右手茧', personality_tags: ['克制'] }}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    await flushEffects()
    expect(screen.getByTestId('codex-readonly-banner')).toBeTruthy()
    expect(screen.getByTestId('codex-ask-chief').textContent).toMatch(/让主编写入/)
    expect(screen.queryByLabelText(/编辑外貌/)).toBeNull()
    expect(screen.getByText('右手茧')).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByTestId('codex-readonly-banner')).toBeTruthy()
    })
  })

  it('让主编写入写入 sessionStorage 种子', async () => {
    render(
      <DetailView
        type="chars"
        isNew={false}
        row={{ id: 'role:沈砚', name: '沈砚', appearance: '右手茧' }}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    await flushEffects()
    await act(async () => {
      fireEvent.click(screen.getByTestId('codex-ask-chief'))
    })
    const seed = sessionStorage.getItem('s3.chief.seed') || ''
    expect(seed).toMatch(/沈砚/)
    expect(seed).toMatch(/s3_patch_character/)
  })

  it('新建角色仍可直填（immediate）', async () => {
    render(
      <DetailView
        type="chars"
        isNew
        row={{ name: '', appearance: '' }}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    await flushEffects()
    expect(screen.queryByTestId('codex-readonly-banner')).toBeNull()
  })

  it('seedChiefCodexWrite 导出可单测', () => {
    const t = seedChiefCodexWrite('chars', { name: '季棠' })
    expect(t).toMatch(/季棠/)
    expect(t).toMatch(/s3_patch_character/)
  })

  it('已有角色后挂区：无直填入口，有主编种子 CTA', async () => {
    render(
      <DetailView
        type="chars"
        isNew={false}
        row={{ id: 'role:沈砚', name: '沈砚', appearance: '右手茧' }}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    await flushEffects()
    expect(screen.queryByText('+ 记录质变')).toBeNull()
    expect(screen.queryByText('建立关系')).toBeNull()
    expect(screen.getByTestId('timeline-ask-chief').textContent).toMatch(/主编/)
    expect(screen.getByTestId('relations-ask-chief').textContent).toMatch(/主编/)
  })

  it('后挂 CTA 写入带 hint 的主编种子', async () => {
    render(
      <DetailView
        type="chars"
        isNew={false}
        row={{ id: 'role:沈砚', name: '沈砚' }}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    await flushEffects()
    await act(async () => {
      fireEvent.click(screen.getByTestId('timeline-ask-chief'))
    })
    const seed = sessionStorage.getItem('s3.chief.seed') || ''
    expect(seed).toMatch(/弧光质变/)
  })

  it('只读值无边框假输入盒', async () => {
    const { container } = render(
      <DetailView
        type="chars"
        isNew={false}
        row={{ id: 'role:沈砚', name: '沈砚', appearance: '右手茧' }}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    await flushEffects()
    const val = screen.getByText('右手茧')
    expect(val.className).not.toMatch(/border-line/)
    // 只读值节点本身不应是 bordered box
    expect(val.closest('.border-line.bg-surface')).toBeNull()
    expect(container.querySelector('[data-testid="codex-detail-chars"]')).toBeTruthy()
  })
})
