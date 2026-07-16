import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ContextSnapshotProvider, useContextSnapshot, DEFAULT_CAPABILITIES } from './ContextSnapshotContext'

// Task 16-B:前端能力以后端 /capabilities 为准(不靠 localStorage 开服务端能力)。
const apiMock = vi.hoisted(() => ({
  getWork: () => 'demo',
  createContextSession: vi.fn(() => Promise.reject(new Error('降级'))),   // 走本地直通,不影响能力拉取
  fetchCapabilities: vi.fn(),
}))
vi.mock('../api', () => ({ api: apiMock }))

function Probe() {
  const { capabilities } = useContextSnapshot()
  return <div data-testid="caps">{JSON.stringify(capabilities.flags)}</div>
}

describe('ContextSnapshotProvider capabilities', () => {
  it('后端开启的开关下发到前端,未列出的保持默认全关', async () => {
    apiMock.fetchCapabilities.mockResolvedValueOnce({
      flags: { context_inspector_v1: true },   // 只列一个开的
      versions: { retrieval_policy: '1' },
    })
    render(<ContextSnapshotProvider work="demo"><Probe /></ContextSnapshotProvider>)
    await waitFor(() => {
      const flags = JSON.parse(screen.getByTestId('caps').textContent)
      expect(flags.context_inspector_v1).toBe(true)
      expect(flags.memory_fabric_v1).toBe(false)      // 未列出 → 默认全关
      expect(flags.snapshot_v1).toBe(false)
    })
  })

  it('拉取失败时保持默认全关(fail-soft,前端不越权开启)', async () => {
    apiMock.fetchCapabilities.mockRejectedValueOnce(new Error('网络错误'))
    render(<ContextSnapshotProvider work="demo"><Probe /></ContextSnapshotProvider>)
    await waitFor(() => {
      const flags = JSON.parse(screen.getByTestId('caps').textContent)
      expect(flags).toEqual(DEFAULT_CAPABILITIES.flags)
    })
  })
})

// ---- P0a 多会话:switchThread + 当前线程解析链(零降级:每次向下切换必须可见)----
import { fireEvent } from '@testing-library/react'
import { showToast } from '../ui/Toast.jsx'

vi.mock('../ui/Toast.jsx', () => ({ showToast: vi.fn() }))

function ThreadProbe() {
  const { snapshot, switchThread } = useContextSnapshot()
  return (
    <div>
      <div data-testid="tid">{snapshot?.thread_id || 'none'}</div>
      <button onClick={() => switchThread('t2')}>switch</button>
    </div>
  )
}

const SNAP = (tid) => ({ session_id: 's-' + tid, thread_id: tid, revision: 0 })

describe('P0a switchThread 与解析链', () => {
  it('switchThread 成功:snapshot 换绑新线程 + localStorage 记忆', async () => {
    localStorage.clear()
    apiMock.createContextSession.mockResolvedValueOnce(SNAP('t1'))   // 挂载
    apiMock.createContextSession.mockResolvedValueOnce(SNAP('t2'))   // 切换
    render(<ContextSnapshotProvider work="demo"><ThreadProbe /></ContextSnapshotProvider>)
    await waitFor(() => expect(screen.getByTestId('tid').textContent).toBe('t1'))
    fireEvent.click(screen.getByText('switch'))
    await waitFor(() => expect(screen.getByTestId('tid').textContent).toBe('t2'))
    expect(localStorage.getItem('s3.thread.current.demo')).toBe('t2')
  })

  it('localStorage 指向失效线程:toast 可见 + 清键 + 回默认(绝不静默)', async () => {
    localStorage.clear()
    localStorage.setItem('s3.thread.current.demo', 'ethread:demo:dead')
    apiMock.createContextSession.mockClear()   // mock.calls 跨测试累积,先清再断言首调
    apiMock.createContextSession
      .mockRejectedValueOnce(Object.assign(new Error('HTTP 404'), { status: 404 }))
      .mockResolvedValueOnce(SNAP('t-default'))
    render(<ContextSnapshotProvider work="demo"><ThreadProbe /></ContextSnapshotProvider>)
    await waitFor(() => expect(screen.getByTestId('tid').textContent).toBe('t-default'))
    expect(showToast).toHaveBeenCalledWith(
      expect.stringContaining('已切到默认会话'), expect.anything())
    expect(localStorage.getItem('s3.thread.current.demo')).toBeNull()
    // 挂载时带了偏好线程 → 首次调用 body 含 thread_id
    expect(apiMock.createContextSession.mock.calls[0][0]).toMatchObject(
      { thread_id: 'ethread:demo:dead' })
  })

  it('switchThread 失败:danger toast 且当前状态不变(零降级)', async () => {
    localStorage.clear()
    apiMock.createContextSession.mockResolvedValueOnce(SNAP('t1'))
    apiMock.createContextSession.mockRejectedValueOnce(new Error('网关 down'))
    render(<ContextSnapshotProvider work="demo"><ThreadProbe /></ContextSnapshotProvider>)
    await waitFor(() => expect(screen.getByTestId('tid').textContent).toBe('t1'))
    fireEvent.click(screen.getByText('switch'))
    await waitFor(() => expect(showToast).toHaveBeenCalledWith(
      expect.stringContaining('切换会话失败'), expect.objectContaining({ tone: 'danger' })))
    expect(screen.getByTestId('tid').textContent).toBe('t1')   // 状态不变
    expect(localStorage.getItem('s3.thread.current.demo')).toBeNull()
  })
})
