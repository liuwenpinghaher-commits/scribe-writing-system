import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { WriteChat } from '../WriteChat'
import { api } from '../api'

const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'demo_work'),
  addIdea: vi.fn(),
  aiRunStatus: vi.fn(() => Promise.resolve({ run_id: 'run_1', status: 'requires_approval' })),
  aiRunEvents: vi.fn(() => ({ close: vi.fn() })),
  aiRunApproval: vi.fn(() => Promise.resolve({ status: 'resumed' })),
  runWrite: vi.fn((_msg, opts) => {
    opts.onDone?.()
    return { abort: vi.fn(), close: vi.fn() }
  }),
  chatWrite: vi.fn((_msg, opts) => {
    opts.onDone?.()
    return { abort: vi.fn() }
  }),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('WriteChat phase', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    apiMock.getWork.mockReturnValue('demo_work')
  })

  it('正文阶段传入 phase=final 时把 final phase 发给写作接口', async () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '继续写正文' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(api.chatWrite).toHaveBeenCalled())
    expect(api.chatWrite.mock.calls[0][0]).toBe('继续写正文')
    expect(api.chatWrite.mock.calls[0][1]).toMatchObject({
      chapter: 4,
      focalizer: '崔判',
      phase: 'final',
    })
    expect(api.runWrite).not.toHaveBeenCalled()
  })

  it('明确登记世界状态时走 Hermes Runs 而不是普通写作流', async () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '请登记伏笔: 铜炉会反噬持有人' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(api.runWrite).toHaveBeenCalled())
    expect(api.chatWrite).not.toHaveBeenCalled()
    expect(api.runWrite.mock.calls[0][0]).toContain('请登记伏笔')
    expect(api.runWrite.mock.calls[0][1]).toMatchObject({
      chapter: 4,
      phase: 'final',
      focalizer: '崔判',
    })
  })

  it('正文主编对话使用统一的单面板输入区', () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    expect(screen.getByTestId('chief-write-chat')).toBeTruthy()
    expect(screen.getByTestId('chief-chat-messages').className).toContain('bg-canvas')
    const composer = screen.getByTestId('chief-chat-composer')
    const textarea = screen.getByPlaceholderText(/提思路/)
    expect(composer.getAttribute('data-chief-composer')).toBe('true')
    expect(composer.className).toContain('chief-composer-panel')
    expect(composer.className).toContain('rounded-md')
    expect(composer.className).not.toContain('space-y-2')
    expect(textarea.className).toContain('border-0')
    expect(textarea.className).toContain('shadow-none')
    expect(textarea.className).toContain('focus:shadow-none')
    expect(textarea.className).toContain('focus:ring-0')
    expect(textarea.className).toContain('min-h-[36px]')
    expect(textarea.className).not.toContain('min-h-[72px]')
  })

  it('正文主编底部工具栏展示附件、语音和大发送按钮', () => {
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const toolbar = screen.getByTestId('chief-chat-toolbar')
    expect(screen.getByRole('button', { name: '添加附件' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '语音输入' })).toBeTruthy()
    const send = screen.getByRole('button', { name: '发送' })
    expect(send.textContent).toContain('发送')
    expect(send.className).toContain('min-w-')
    expect(toolbar.textContent).not.toContain('Enter 发送')
  })

  it('正文阶段收到 Hermes approval 事件时可批准', async () => {
    apiMock.runWrite.mockImplementation((_msg, opts) => {
      opts.onRun?.({ run_id: 'run_1' })
      opts.onApproval?.({ run_id: 'run_1', approval_id: 'ap_1', message: '允许写入伏笔?' })
      return { abort: vi.fn() }
    })
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '请登记伏笔' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(apiMock.chatWrite).not.toHaveBeenCalled()
    expect(await screen.findByText('允许写入伏笔?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '批准' }))

    await waitFor(() => expect(apiMock.aiRunApproval).toHaveBeenCalledWith('run_1', {
      approval_id: 'ap_1',
      decision: 'approve',
    }))
    expect(await screen.findByText('已批准')).toBeTruthy()
  })

  it('正文阶段审批超时显示已过期，不再显示批准按钮', async () => {
    let handlers
    apiMock.runWrite.mockImplementation((_msg, opts) => {
      handlers = opts
      opts.onRun?.({ run_id: 'run_expired' })
      opts.onApproval?.({ run_id: 'run_expired', approval_id: 'ap_expired', message: '允许写入伏笔?' })
      return { abort: vi.fn() }
    })
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    fireEvent.change(screen.getByPlaceholderText(/提思路/), { target: { value: '请登记伏笔' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))
    expect(await screen.findByText('允许写入伏笔?')).toBeTruthy()

    await act(async () => {
      handlers.onApprovalResolved?.({ run_id: 'run_expired', approval_id: 'ap_expired', decision: 'timeout' })
    })
    expect(await screen.findByText('审批已过期，请重新发起')).toBeTruthy()
    expect(screen.queryByRole('button', { name: '批准' })).toBeNull()
    expect(screen.queryByText('已拒绝')).toBeNull()
  })

  it('刷新后恢复正文阶段未决 Hermes approval 并可继续审批', async () => {
    let recoveredHandlers = null
    apiMock.runWrite.mockImplementation((_msg, opts) => {
      opts.onRun?.({ run_id: 'run_1' })
      opts.onApproval?.({ run_id: 'run_1', approval_id: 'ap_1', message: '允许写入伏笔?' })
      return { abort: vi.fn(), close: vi.fn() }
    })
    apiMock.aiRunEvents.mockImplementation((_runId, handlers) => {
      recoveredHandlers = handlers
      return { close: vi.fn() }
    })
    const first = render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '请登记伏笔' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('允许写入伏笔?')).toBeTruthy()
    expect(apiMock.aiRunEvents).not.toHaveBeenCalled()
    first.unmount()
    vi.clearAllMocks()
    apiMock.getWork.mockReturnValue('demo_work')
    apiMock.aiRunStatus.mockResolvedValue({ run_id: 'run_1', status: 'requires_approval' })
    apiMock.aiRunEvents.mockImplementation((_runId, handlers) => {
      recoveredHandlers = handlers
      return { close: vi.fn() }
    })

    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    expect(await screen.findByText('允许写入伏笔?')).toBeTruthy()
    await waitFor(() => expect(apiMock.aiRunStatus).toHaveBeenCalledWith('run_1'))
    await waitFor(() => expect(apiMock.aiRunEvents).toHaveBeenCalledWith('run_1', expect.any(Object)))
    fireEvent.click(screen.getByRole('button', { name: '批准' }))

    await waitFor(() => expect(apiMock.aiRunApproval).toHaveBeenCalledWith('run_1', {
      approval_id: 'ap_1',
      decision: 'approve',
    }))
    recoveredHandlers.onApprovalResolved?.({ run_id: 'run_1', approval_id: 'ap_1', decision: 'approve' })
    expect(await screen.findByText('已批准')).toBeTruthy()
  })

  it('正文阶段显示 Hermes 工具输出摘要', async () => {
    apiMock.chatWrite.mockImplementation((_msg, opts) => {
      opts.onTool?.('mcp_scribe3_read_s3_hybrid_recall')
      opts.onToolOutput?.({ snippets: ['铜炉曾在第二章出现'] }, 'call_2')
      opts.onDone?.()
      return { abort: vi.fn() }
    })
    render(<WriteChat chapter={4} focalizer="崔判" phase="final" />)

    const input = screen.getByPlaceholderText(/提思路/)
    fireEvent.change(input, { target: { value: '查铜炉素材' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText(/铜炉曾在第二章出现/)).toBeTruthy()
    expect(screen.getByText('hybrid_recall')).toBeTruthy()
  })
})
