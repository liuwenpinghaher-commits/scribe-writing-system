import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { WriteChat } from '../WriteChat'
import { api } from '../api'

// Task 13 I-1:章内写作槽发起的 approval 型 run 也必须绑发起时上下文,让审批重校验对它生效
// (否则 WriteChat 的 RunStaleCard 是死代码=假象)。此处验证:有统一快照时 runWrite 带 context。
const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'book-a'),
  addIdea: vi.fn(),
  aiRunStatus: vi.fn(() => Promise.resolve({ run_id: 'run_1', status: 'requires_approval' })),
  aiRunEvents: vi.fn(() => ({ close: vi.fn() })),
  aiRunApproval: vi.fn(() => Promise.resolve({ status: 'resumed' })),
  aiRunTrace: vi.fn(() => Promise.resolve({})),
  runWrite: vi.fn((_msg, opts) => {
    opts.onRun?.({ run_id: 'run_1' })
    opts.onApproval?.({ run_id: 'run_1', approval_id: 'ap_1', message: '允许写入伏笔?' })
    return { abort: vi.fn(), close: vi.fn() }
  }),
  chatWrite: vi.fn((_msg, opts) => { opts.onDone?.(); return { abort: vi.fn() } }),
}))

vi.mock('../api', () => ({ api: apiMock }))

// 注入统一快照(模拟四栏 ContextSnapshotProvider 已建会话):session_id + revision + focus。
vi.mock('../context/ContextSnapshotContext', () => ({
  useContextSnapshot: () => ({
    snapshot: {
      session_id: 'sess-ctx-1',
      revision: 8,
      context_hash: 'a'.repeat(64),
      thread_id: 'ethread:book-a',
      focus: { type: 'chapter', id: 'chapter:9', label: '第 9 章' },
    },
  }),
}))

describe('WriteChat 章内 run 绑发起时上下文(I-1a)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    apiMock.getWork.mockReturnValue('book-a')
  })

  it('登记世界状态走 Hermes Run 时把发起时 session/revision 绑进 create', async () => {
    render(<WriteChat chapter={9} focalizer="崔判" phase="final" />)
    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '请登记伏笔: 铜炉会反噬持有人' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(api.runWrite).toHaveBeenCalled())
    expect(api.runWrite.mock.calls[0][1].context).toEqual({
      context_session_id: 'sess-ctx-1',
      context_revision: 8,
    })
  })

  it('直接写正文即使提到人物推进也走写作流，而不是世界状态 Run', async () => {
    render(<WriteChat chapter={9} focalizer="崔判" phase="final" />)
    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, {
      target: { value: '直接写本章完整正文，以具体动作、感官和对话推进人物关系。' },
    })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(api.chatWrite).toHaveBeenCalled())
    expect(api.runWrite).not.toHaveBeenCalled()
    expect(api.chatWrite.mock.calls[0][1].context).toEqual({
      context_session_id: 'sess-ctx-1',
      context_revision: 8,
      context_hash: 'a'.repeat(64),
    })
  })

  it('过期焦点审批(run_context_changed)在章内槽也展示已过期并作废', async () => {
    apiMock.aiRunApproval.mockRejectedValueOnce(Object.assign(new Error('HTTP 409'), {
      status: 409,
      body: { detail: {
        code: 'run_context_changed',
        origin_focus: { label: '第 9 章(发起时)' },
        current_focus: { label: '第 20 章(当前)' },
      } },
    }))
    render(<WriteChat chapter={9} focalizer="崔判" phase="final" />)
    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '请登记伏笔' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('允许写入伏笔?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '批准' }))

    expect(await screen.findByTestId('run-context-stale')).toBeTruthy()
    expect(screen.getByTestId('run-origin-focus').textContent).toBe('第 9 章(发起时)')
    expect(screen.getByTestId('run-current-focus').textContent).toBe('第 20 章(当前)')
    expect(screen.getByTestId('run-context-voided')).toBeTruthy()
  })
})
