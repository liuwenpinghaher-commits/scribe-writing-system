import '@testing-library/jest-dom/vitest'
import { useEffect } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { act, render, screen, waitFor, fireEvent } from '@testing-library/react'
import { ChiefDock } from '../ChiefDock'
import { ChiefSlotProvider, useChiefSlot } from '../ChiefSlotContext'

// Task 6:主编历史 = 一 work 一连续线程 + 每轮焦点标签。
// 三条语义:① 焦点切换不换线程(不重载消息);② 历史消息保留;③ 上下文标签跟随焦点。

const apiMock = vi.hoisted(() => ({
  getWork: vi.fn(() => 'demo_work'),
  chapterPulse: vi.fn(() => Promise.resolve({ dimensions: [] })),
  addIdea: vi.fn(),
  chatWrite: vi.fn(),
  chatStream: vi.fn(),
  runWrite: vi.fn(),
  threadMessages: vi.fn(),
  aiRunStatus: vi.fn(() => Promise.resolve({ status: 'completed' })),
  aiRunEvents: vi.fn(() => ({ close: vi.fn() })),
  aiUsage: vi.fn(() => Promise.resolve(null)),
}))
vi.mock('../api', () => ({ api: apiMock }))

// 用可变快照驱动 useContextSnapshot(Harness 每次 render 读当前值)。
let currentSnapshot = null
vi.mock('../context/ContextSnapshotContext', () => ({
  useContextSnapshot: () => ({
    snapshot: currentSnapshot,
    navigate: () => {},
    restoring: false,
    error: null,
    navigated: false,
    sessionId: currentSnapshot?.session_id ?? null,
  }),
}))

const H64 = 'a'.repeat(64)

function Harness() {
  return (
    <ChiefSlotProvider>
      <ChiefDock
        lastSeq={3}
        sel={{ mode: 'node', node: { id: 'role:甲', type: 'character', ref: 'role:甲', label: '甲' } }}
      />
    </ChiefSlotProvider>
  )
}

function PhaseSetter({ phase }) {
  const { setChapterPhase } = useChiefSlot()
  useEffect(() => { setChapterPhase(phase) }, [phase, setChapterPhase])
  return null
}

// 章节讨论 harness(phase=draft 走 chatWrite 路径,便于断言 send 时的 context 绑定)。
function ChapterHarness({ phase = 'draft' }) {
  return (
    <ChiefSlotProvider>
      <PhaseSetter phase={phase} />
      <ChiefDock
        chapterSel
        lastSeq={3}
        sel={{ mode: 'node', node: { id: 'ch:3', type: 'chapter', ref: 3, label: '3 章' } }}
      />
    </ChiefSlotProvider>
  )
}

describe('ChiefDock 线程连续性(Task 6)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    apiMock.getWork.mockReturnValue('demo_work')
    currentSnapshot = null
  })

  it('从角色甲切到伏笔乙仍保留同一线程消息', async () => {
    apiMock.threadMessages.mockResolvedValue([
      { id: 'm1', role: 'user', text: '先谈甲', context_revision: 2, focus: { id: 'role:甲' } },
    ])
    currentSnapshot = {
      work: 'demo_work', thread_id: 't1', session_id: 's1', revision: 2, context_hash: H64,
      focus: { type: 'character', id: 'role:甲', label: '甲' }, chapter: null, phase: null,
    }
    const view = render(<Harness />)

    // 历史消息载入(线程一次性拉取)
    expect(await screen.findByText('先谈甲')).toBeTruthy()
    // 上下文标签跟随角色焦点
    await waitFor(() => expect(screen.getByTestId('chief-ctx')).toHaveTextContent('角色'))

    // 焦点从 role:甲 → promise:乙(仅切焦点,线程 id 不变)
    currentSnapshot = {
      ...currentSnapshot, revision: 3,
      focus: { type: 'promise', id: 'promise:乙', label: '乙' },
    }
    view.rerender(<Harness />)

    // ① 线程不随焦点重载
    expect(apiMock.threadMessages).toHaveBeenCalledTimes(1)
    // ② 历史消息保留
    expect(screen.getByText('先谈甲')).toBeTruthy()
    // ③ 上下文标签跟随焦点(伏笔)
    await waitFor(() => expect(screen.getByTestId('chief-ctx')).toHaveTextContent('伏笔'))
  })

  it('带焦点的消息气泡标注 data-context-revision', async () => {
    apiMock.threadMessages.mockResolvedValue([
      { id: 'm1', role: 'user', text: '先谈甲', context_revision: 5, focus: { id: 'role:甲' } },
    ])
    currentSnapshot = {
      work: 'demo_work', thread_id: 't1', session_id: 's1', revision: 5, context_hash: H64,
      focus: { type: 'character', id: 'role:甲', label: '甲' },
    }
    render(<Harness />)
    const bubbleText = await screen.findByText('先谈甲')
    const bubble = bubbleText.closest('[data-context-revision]')
    expect(bubble).toBeTruthy()
    expect(bubble.getAttribute('data-context-revision')).toBe('5')
  })

  it('I-2:线程历史载入失败不卡死且可重试', async () => {
    apiMock.threadMessages
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce([{ id: 'm1', role: 'user', text: '恢复的消息' }])
    currentSnapshot = {
      work: 'demo_work', thread_id: 't1', session_id: 's1', revision: 1, context_hash: H64,
      focus: { type: 'character', id: 'role:甲', label: '甲' },
    }
    render(<Harness />)
    // 失败 → 错误横幅出现(组件未崩)
    expect(await screen.findByTestId('chief-thread-load-error')).toBeTruthy()
    // 点重试 → 第二次成功 → 消息出现,且确实重拉了一次
    fireEvent.click(screen.getByTestId('chief-thread-retry'))
    expect(await screen.findByText('恢复的消息')).toBeTruthy()
    expect(apiMock.threadMessages).toHaveBeenCalledTimes(2)
  })

  it('I-1:server 模式发送时请求体带上 context 绑定字段', async () => {
    apiMock.threadMessages.mockResolvedValue([])
    apiMock.chatWrite.mockImplementation((_m, opts) => { opts.onDone?.(); return { abort: vi.fn() } })
    currentSnapshot = {
      work: 'demo_work', thread_id: 't1', session_id: 's1', revision: 4, context_hash: H64,
      focus: { type: 'chapter', id: 'chapter:3', label: '第3章' }, chapter: 3, phase: 'draft',
    }
    render(<ChapterHarness phase="draft" />)
    const input = await screen.findByPlaceholderText(/就当前内容问主编/)
    fireEvent.change(input, { target: { value: '这段节奏怎么调' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(apiMock.chatWrite).toHaveBeenCalled())
    const opts = apiMock.chatWrite.mock.calls[0][1]
    expect(opts.context).toMatchObject({
      thread_id: 't1', context_session_id: 's1', context_revision: 4, context_hash: H64,
    })
    expect(opts.context.focus).toMatchObject({ id: 'chapter:3' })
  })

  it('历史空回填先完成后才收到 Run 审批时，保留本轮 Run 卡且不崩溃', async () => {
    let resolveHistory
    let runOptions
    apiMock.threadMessages.mockImplementation(() => new Promise((resolve) => { resolveHistory = resolve }))
    apiMock.runWrite.mockImplementation((_message, options) => {
      runOptions = options
      return { abort: vi.fn(), close: vi.fn() }
    })
    currentSnapshot = {
      work: 'demo_work', thread_id: 't1', session_id: 's1', revision: 4, context_hash: H64,
      focus: { type: 'chapter', id: 'chapter:3', label: '第3章' }, chapter: 3, phase: 'outline',
    }
    render(<ChapterHarness phase="outline" />)

    const input = await screen.findByPlaceholderText(/就当前内容问主编/)
    fireEvent.change(input, { target: { value: '请只调用 s3_add_chapter 新建第1章，需审批' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))
    expect(runOptions).toBeTruthy()

    // 真实竞态：首次线程历史的空结果先落地，随后网关才推送 Run/approval SSE。
    await act(async () => { resolveHistory([]) })
    await act(async () => {
      runOptions.onRun?.({ run_id: 'run_after_history', status: 'requires_approval' })
      runOptions.onApproval?.({
        run_id: 'run_after_history', approval_id: 'ap_after_history', message: '允许新建第1章？',
      })
      // 审计链回放与实时 SSE 可在临界窗口交叠；同一 approval 只能渲染一张作者裁决卡。
      runOptions.onApproval?.({
        run_id: 'run_after_history', approval_id: 'ap_after_history', message: '允许新建第1章？',
      })
    })

    expect(await screen.findByText('允许新建第1章？')).toBeTruthy()
    expect(screen.getAllByText('允许新建第1章？')).toHaveLength(1)
    expect(screen.getByTestId('chief-chat-shell')).toBeTruthy()
  })
})
