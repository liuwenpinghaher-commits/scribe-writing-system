import { useEffect } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChiefDock } from '../ChiefDock'
import { ChiefSlotProvider, useChiefSlot } from '../ChiefSlotContext'

// Task 13:主编 run 审批命中"发起时上下文已过期"时,ChiefDock 展示发起时/当前焦点 + 已过期,
// 并按 409 code 分流:changed=作废(不放行);stale=二次确认后带 approve_stale=true 重批。
const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'book-a'),
  chapterPulse: vi.fn(() => Promise.resolve({ checks: [] })),
  addIdea: vi.fn(),
  chatWrite: vi.fn(),
  chatStream: vi.fn(),
  aiRunStatus: vi.fn(() => Promise.resolve({ run_id: 'run_1', status: 'requires_approval' })),
  aiRunEvents: vi.fn(() => ({ close: vi.fn() })),
  aiRunApproval: vi.fn(() => Promise.resolve({ status: 'resumed' })),
  aiUsage: vi.fn(() => Promise.resolve({ cap: null })),
  runWrite: vi.fn((_msg, opts) => {
    opts.onRun?.({ run_id: 'run_1' })
    opts.onApproval?.({ run_id: 'run_1', approval_id: 'ap_1', message: '允许写入第 9 章设定?' })
    return { abort: vi.fn(), close: vi.fn() }
  }),
}))

vi.mock('../api', () => ({ api: apiMock }))

function PhaseSetter({ phase }) {
  const { setChapterPhase } = useChiefSlot()
  useEffect(() => { setChapterPhase(phase) }, [phase, setChapterPhase])
  return null
}

function Harness() {
  return (
    <ChiefSlotProvider>
      <PhaseSetter phase="outline" />
      <ChiefDock
        chapterSel
        lastSeq={9}
        sel={{ mode: 'node', node: { id: 'ch:9', type: 'chapter', ref: 9, label: '9 铜炉认主' } }}
      />
    </ChiefSlotProvider>
  )
}

function err409(detail) {
  return Object.assign(new Error('HTTP 409'), { status: 409, body: { detail } })
}

async function triggerRunApproval() {
  render(<Harness />)
  const input = await screen.findByPlaceholderText(/就当前内容问主编/)
  fireEvent.change(input, { target: { value: '请新增角色:柳怀玉的师父' } })
  fireEvent.click(screen.getByRole('button', { name: '发送' }))
  await screen.findByText('允许写入第 9 章设定?')
}

describe('ChiefDock run 上下文过期审批', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    apiMock.getWork.mockReturnValue('book-a')
    apiMock.chapterPulse.mockResolvedValue({ checks: [] })
  })

  it('影响当前章(run_context_changed)→ 展示已过期/发起时/当前焦点并作废,不放行', async () => {
    apiMock.aiRunApproval.mockRejectedValueOnce(err409({
      code: 'run_context_changed',
      origin_focus: { type: 'chapter', id: 'chapter:9', label: '第 8 章(发起时)' },
      current_focus: { type: 'chapter', id: 'chapter:9', label: '第 9 章(当前)' },
      origin_context_revision: 8,
      current_context_revision: 9,
    }))
    await triggerRunApproval()

    fireEvent.click(screen.getByRole('button', { name: '批准' }))

    expect(await screen.findByTestId('run-context-stale')).toBeTruthy()
    expect(screen.getByTestId('run-context-expired').textContent).toContain('已过期')
    expect(screen.getByTestId('run-origin-focus').textContent).toBe('第 8 章(发起时)')
    expect(screen.getByTestId('run-current-focus').textContent).toBe('第 9 章(当前)')
    expect(screen.getByTestId('run-context-voided')).toBeTruthy()
    // 作废态没有"仍要批准"入口;审批只被调用一次(第一次即 409)
    expect(screen.queryByTestId('run-approve-stale')).toBeNull()
    expect(apiMock.aiRunApproval).toHaveBeenCalledTimes(1)
  })

  it('无关焦点(run_context_stale)→ 二次确认带 approve_stale=true 重批后已批准', async () => {
    apiMock.aiRunApproval
      .mockRejectedValueOnce(err409({
        code: 'run_context_stale',
        origin_focus: { type: 'chapter', id: 'chapter:9', label: '第 9 章' },
        current_focus: { type: 'chapter', id: 'chapter:3', label: '第 3 章' },
        origin_context_revision: 8,
        current_context_revision: 9,
      }))
      .mockResolvedValueOnce({ status: 'resumed' })
    await triggerRunApproval()

    fireEvent.click(screen.getByRole('button', { name: '批准' }))

    const stale = await screen.findByTestId('run-approve-stale')
    expect(screen.getByTestId('run-origin-focus').textContent).toBe('第 9 章')
    expect(screen.getByTestId('run-current-focus').textContent).toBe('第 3 章')
    expect(screen.queryByTestId('run-context-voided')).toBeNull()

    fireEvent.click(stale)

    await waitFor(() => expect(apiMock.aiRunApproval).toHaveBeenCalledTimes(2))
    expect(apiMock.aiRunApproval.mock.calls[1][1]).toEqual(expect.objectContaining({
      approval_id: 'ap_1',
      decision: 'approve',
      approve_stale: true,
    }))
    expect(await screen.findByText('已批准')).toBeTruthy()
  })
})
