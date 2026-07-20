import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { useEffect } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChiefDock } from '../ChiefDock'
import { ChiefSlotProvider, useChiefSlot } from '../ChiefSlotContext'

const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'demo_work'),
  chapterPulse: vi.fn(() => Promise.resolve({ dimensions: [] })),
  addIdea: vi.fn(),
  chatWrite: vi.fn(),
  chatStream: vi.fn(),
  aiRunStatus: vi.fn(() => Promise.resolve({ run_id: 'run_1', status: 'requires_approval' })),
  aiRunEvents: vi.fn(() => ({ close: vi.fn() })),
  aiRunApproval: vi.fn(() => Promise.resolve({ status: 'resumed' })),
  runWrite: vi.fn((_msg, opts) => {
    opts.onDone?.()
    return { abort: vi.fn(), close: vi.fn() }
  }),
  aiUsage: vi.fn(() => Promise.resolve({
    cap: { cap: 500, used_today: 12, remaining: 488, scope: 'shared' },
    tokens: { days: [{ day: '2026-07-10', total: { total_tokens: 34567 } }] },
  })),
}))

vi.mock('../api', () => ({ api: apiMock }))

const here = dirname(fileURLToPath(import.meta.url))

function PhaseSetter({ phase }) {
  const { setChapterPhase } = useChiefSlot()
  useEffect(() => { setChapterPhase(phase) }, [phase, setChapterPhase])
  return null
}

function Harness({ phase = 'outline' }) {
  return (
    <ChiefSlotProvider>
      <PhaseSetter phase={phase} />
      <ChiefDock
        chapterSel
        lastSeq={7}
        sel={{ mode: 'node', node: { id: 'ch:7', type: 'chapter', ref: 7, label: '7 铜炉认主' } }}
      />
    </ChiefSlotProvider>
  )
}

describe('ChiefDock UI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    apiMock.getWork.mockReturnValue('demo_work')
  })

  it('非正文阶段主编对话框使用统一上下文壳', async () => {
    render(<Harness phase="outline" />)

    const shell = await screen.findByTestId('chief-chat-shell')
    expect(shell.className).toContain('bg-surface')
    expect(screen.getByTestId('chief-chat-title').textContent).toBe('主编上下文')
    expect(screen.getByTestId('chief-ctx').textContent).toBe('第 7 章 · 大纲')
    expect(screen.getByTestId('chief-chat-messages')).toBeTruthy()
    expect(screen.getByTestId('chief-chat-composer')).toBeTruthy()
  })

  it('非正文阶段主编输入区使用单一输入面板, textarea 不再画独立大框', async () => {
    render(<Harness phase="outline" />)

    await screen.findByTestId('chief-chat-shell')
    const composer = screen.getByTestId('chief-chat-composer')
    const textarea = screen.getByPlaceholderText(/就当前内容问主编/)

    expect(composer.getAttribute('data-chief-composer')).toBe('true')
    expect(composer.className).toContain('chief-composer-panel')
    expect(composer.className).toContain('rounded-xl')
    expect(composer.className).not.toContain('space-y-2')
    expect(textarea.className).toContain('w-full')
    expect(textarea.className).toContain('border-0')
    expect(textarea.className).toContain('shadow-none')
    expect(textarea.className).toContain('focus:shadow-none')
    expect(textarea.className).toContain('focus:ring-0')
    expect(textarea.className).toContain('min-h-[36px]')
    expect(textarea.className).not.toContain('min-h-[72px]')
    expect(textarea.className).not.toContain('flex-1')
  })

  it('主编输入器局部覆盖全局 textarea focus 光晕', () => {
    const css = readFileSync(resolve(here, '../index.css'), 'utf8')

    expect(css).toContain('[data-chief-composer="true"] textarea:focus')
    expect(css).toContain('box-shadow: none')
  })

  it('非正文阶段主编底部工具栏展示附件、语音和大发送按钮', async () => {
    render(<Harness phase="outline" />)

    await screen.findByTestId('chief-chat-shell')
    const toolbar = screen.getByTestId('chief-chat-toolbar')

    expect(screen.getByRole('button', { name: '添加附件' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '语音输入' })).toBeTruthy()
    const send = screen.getByRole('button', { name: '发送' })
    expect(send.textContent).toContain('发送')
    expect(send.className).toContain('min-w-')
    expect(toolbar.textContent).not.toContain('Enter 发送')
  })

  it('收到 Hermes approval 事件时展示审批卡并可批准', async () => {
    apiMock.runWrite.mockImplementation((_msg, opts) => {
      opts.onRun?.({ run_id: 'run_1' })
      opts.onApproval?.({ run_id: 'run_1', approval_id: 'ap_1', message: '允许写入设定?' })
      return { abort: vi.fn() }
    })
    render(<Harness phase="outline" />)

    const input = screen.getByPlaceholderText(/就当前内容问主编/)
    fireEvent.change(input, { target: { value: '请登记这个设定' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(apiMock.chatWrite).not.toHaveBeenCalled()
    expect(await screen.findByText('允许写入设定?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '批准' }))

    await waitFor(() => expect(apiMock.aiRunApproval).toHaveBeenCalledWith('run_1', {
      approval_id: 'ap_1',
      decision: 'approve',
    }))
    expect(await screen.findByText('已批准')).toBeTruthy()
  })

  it('刷新后恢复非正文阶段未决 Hermes approval 并重连事件流', async () => {
    let recoveredHandlers = null
    apiMock.runWrite.mockImplementation((_msg, opts) => {
      opts.onRun?.({ run_id: 'run_1' })
      opts.onApproval?.({ run_id: 'run_1', approval_id: 'ap_1', message: '允许写入设定?' })
      return { abort: vi.fn(), close: vi.fn() }
    })
    apiMock.aiRunEvents.mockImplementation((_runId, handlers) => {
      recoveredHandlers = handlers
      return { close: vi.fn() }
    })
    const first = render(<Harness phase="outline" />)

    const input = await screen.findByPlaceholderText(/就当前内容问主编/)
    fireEvent.change(input, { target: { value: '请登记这个设定' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('允许写入设定?')).toBeTruthy()
    expect(apiMock.aiRunEvents).not.toHaveBeenCalled()
    first.unmount()
    vi.clearAllMocks()
    apiMock.getWork.mockReturnValue('demo_work')
    apiMock.chapterPulse.mockResolvedValue({ dimensions: [] })
    apiMock.aiRunStatus.mockResolvedValue({ run_id: 'run_1', status: 'requires_approval' })
    apiMock.aiRunEvents.mockImplementation((_runId, handlers) => {
      recoveredHandlers = handlers
      return { close: vi.fn() }
    })

    render(<Harness phase="outline" />)

    expect(await screen.findByText('允许写入设定?')).toBeTruthy()
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

  it('非正文阶段明确登记世界状态时走 Hermes Runs', async () => {
    render(<Harness phase="outline" />)

    const input = await screen.findByPlaceholderText(/就当前内容问主编/)
    fireEvent.change(input, { target: { value: '请新增角色: 柳怀玉的师父' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(apiMock.runWrite).toHaveBeenCalled())
    expect(apiMock.chatWrite).not.toHaveBeenCalled()
    expect(apiMock.runWrite.mock.calls[0][0]).toContain('请新增角色')
    expect(apiMock.runWrite.mock.calls[0][1]).toMatchObject({
      chapter: 7,
      phase: 'plan',
    })
  })

  it('显示 Hermes 工具输出摘要', async () => {
    apiMock.chatWrite.mockImplementation((_msg, opts) => {
      opts.onTool?.('mcp_scribe3_read_s3_get_chapter')
      opts.onToolOutput?.('{"title":"第二章","prose":"正文"}', 'call_1')
      opts.onDone?.()
      return { abort: vi.fn() }
    })
    render(<Harness phase="outline" />)

    const input = screen.getByPlaceholderText(/就当前内容问主编/)
    fireEvent.change(input, { target: { value: '查第二章' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText(/正文/)).toBeTruthy()
    expect(screen.getByText('get_chapter')).toBeTruthy()
  })

  it('头部显示全系统预算 chip(日帽笔数 + 今日 token)', async () => {
    render(<Harness phase="outline" />)

    const chip = await screen.findByTestId('chief-usage-chip')
    expect(chip.textContent).toContain('12/500 发')
    expect(chip.textContent).toContain('35k tok')   // 34567 → 四舍五入 35k
    expect(apiMock.aiUsage).toHaveBeenCalled()
  })

  it('无限用量时只显示今日已用和不限次数', async () => {
    apiMock.aiUsage.mockResolvedValueOnce({
      cap: { cap: 0, used_today: 12, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [{ day: '2026-07-10', total: { total_tokens: 34567 } }] },
    })
    render(<Harness phase="outline" />)

    const chip = await screen.findByTestId('chief-usage-chip')
    expect(chip.textContent).toContain('今日已用 12 发')
    expect(chip.textContent).toContain('不限次数')
    expect(chip.textContent).not.toMatch(/\/\s*0/)
    expect(chip.textContent).not.toContain('日帽 0')
  })
})
