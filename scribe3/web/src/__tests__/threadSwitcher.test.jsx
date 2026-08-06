// P0a:会话下拉——列表/切换/新建/失败红字。零降级:加载失败绝不装"没有会话"。
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const switchThread = vi.fn(() => Promise.resolve({ revision: 1, session_id: 's' }))
const apiMock = vi.hoisted(() => ({
  threads: vi.fn(),
  createThread: vi.fn(),
  patchThread: vi.fn(() => Promise.resolve({})),
  forkThread: vi.fn(() => Promise.resolve({ thread_id: 't4' })),
  exportThreadUrl: vi.fn(() => '#export'),   // P0b:导出链接
}))
vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../context/ContextSnapshotContext', () => ({
  useContextSnapshot: () => ({ snapshot: { thread_id: 't1' }, switchThread }),
}))
const showToast = vi.hoisted(() => vi.fn())
vi.mock('../ui/Toast.jsx', () => ({ showToast }))
import { ThreadSwitcher } from '../ThreadSwitcher'

const LIST = { threads: [
  { thread_id: 't1', title: '主编讨论', status: 'active', updated_at: '2024-01-01T00:00:00Z' },
  { thread_id: 't2', title: '门派支线', status: 'active', updated_at: '2024-06-01T00:00:00Z' },
  { thread_id: 't3', title: '旧支线', status: 'archived', updated_at: '2025-01-01T00:00:00Z' },
] }

beforeEach(() => {
  switchThread.mockClear()
  switchThread.mockImplementation(() => Promise.resolve({ revision: 1, session_id: 's' }))
  apiMock.threads.mockReset()
  apiMock.createThread.mockReset()
  apiMock.forkThread.mockReset()
  apiMock.forkThread.mockResolvedValue({ thread_id: 't4' })
  apiMock.patchThread.mockReset()
  apiMock.patchThread.mockResolvedValue({})
  showToast.mockClear()
})

describe('ThreadSwitcher', () => {
  it('打开列出会话,当前项打勾;点其他项调 switchThread;归档区可见', async () => {
    apiMock.threads.mockResolvedValue(LIST)
    render(<ThreadSwitcher busy={false} />)
    fireEvent.click(screen.getByText('主编讨论'))
    await waitFor(() => screen.getByText(/门派支线/))
    expect(screen.getByText(/✓ 主编讨论/)).toBeTruthy()
    expect(screen.getByText(/已归档 1/)).toBeTruthy()
    fireEvent.click(screen.getByText(/门派支线/))
    expect(switchThread).toHaveBeenCalledWith('t2')
  })

  it('新建会话(默认延续):走 fork(带 parent+title=新会话)后切换——不是失忆', async () => {
    apiMock.threads.mockResolvedValue(LIST)
    apiMock.forkThread.mockResolvedValue({ thread_id: 't8', title: '新会话', status: 'active' })
    render(<ThreadSwitcher busy={false} />)
    fireEvent.click(screen.getByText('主编讨论'))
    await waitFor(() => screen.getByText('新建会话(延续当前上下文)'))
    fireEvent.click(screen.getByText('新建会话(延续当前上下文)'))
    await waitFor(() => expect(apiMock.forkThread).toHaveBeenCalledWith('t1', { title: '新会话' }))
    await waitFor(() => expect(switchThread).toHaveBeenCalledWith('t8'))
    expect(apiMock.createThread).not.toHaveBeenCalled()
  })

  it('全新会话(手动不带历史):走 createThread', async () => {
    apiMock.threads.mockResolvedValue(LIST)
    apiMock.createThread.mockResolvedValue({ thread_id: 't9', title: '新会话', status: 'active' })
    render(<ThreadSwitcher busy={false} />)
    fireEvent.click(screen.getByText('主编讨论'))
    await waitFor(() => screen.getByText('全新会话(不带历史)'))
    fireEvent.click(screen.getByText('全新会话(不带历史)'))
    await waitFor(() => expect(apiMock.createThread).toHaveBeenCalled())
    await waitFor(() => expect(switchThread).toHaveBeenCalledWith('t9'))
  })

  it('单飞:创建进行中连点不会二次 fork', async () => {
    apiMock.threads.mockResolvedValue(LIST)
    let resolveFork
    apiMock.forkThread.mockImplementation(() => new Promise((r) => { resolveFork = r }))
    render(<ThreadSwitcher busy={false} />)
    fireEvent.click(screen.getByText('主编讨论'))
    await waitFor(() => screen.getByTestId('thread-new-continue'))
    fireEvent.click(screen.getByTestId('thread-new-continue'))
    fireEvent.click(screen.getByTestId('thread-new-continue'))
    fireEvent.click(screen.getByTestId('thread-new-continue'))
    expect(apiMock.forkThread).toHaveBeenCalledTimes(1)
    resolveFork({ thread_id: 't-only', title: '新会话', status: 'active' })
    await waitFor(() => expect(switchThread).toHaveBeenCalledWith('t-only'))
  })

  it('绑定失败后展示重试且重试仍用同一 thread_id 不再 create', async () => {
    apiMock.threads.mockResolvedValue(LIST)
    apiMock.forkThread.mockResolvedValue({ thread_id: 't-orphan', title: '新会话', status: 'active' })
    switchThread
      .mockRejectedValueOnce(new Error('bind fail'))
      .mockResolvedValueOnce({ revision: 2, session_id: 's2', thread_id: 't-orphan' })
    render(<ThreadSwitcher busy={false} />)
    fireEvent.click(screen.getByText('主编讨论'))
    await waitFor(() => screen.getByTestId('thread-new-continue'))
    fireEvent.click(screen.getByTestId('thread-new-continue'))
    await waitFor(() => screen.getByTestId('thread-bind-retry'))
    expect(apiMock.forkThread).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByTestId('thread-bind-retry-btn'))
    await waitFor(() => expect(switchThread).toHaveBeenCalledTimes(2))
    expect(switchThread).toHaveBeenLastCalledWith('t-orphan')
    expect(apiMock.forkThread).toHaveBeenCalledTimes(1)
  })

  it('归档当前会话切到 updated_at 最新的其它 active', async () => {
    apiMock.threads
      .mockResolvedValueOnce(LIST)
      .mockResolvedValueOnce({
        threads: [
          { thread_id: 't2', title: '门派支线', status: 'active', updated_at: '2024-06-01T00:00:00Z' },
          { thread_id: 't1', title: '主编讨论', status: 'archived', updated_at: '2024-07-01T00:00:00Z' },
          { thread_id: 't0', title: '更早但更新', status: 'active', updated_at: '2024-08-01T00:00:00Z', created_at: '2020-01-01T00:00:00Z' },
        ],
      })
    render(<ThreadSwitcher busy={false} />)
    fireEvent.click(screen.getByText('主编讨论'))
    await waitFor(() => screen.getByText(/✓ 主编讨论/))
    // 归档按钮在 group-hover；直接点 title=归档
    const archiveBtns = screen.getAllByTitle('归档')
    fireEvent.click(archiveBtns[0]) // 当前 t1 行
    await waitFor(() => expect(apiMock.patchThread).toHaveBeenCalledWith('t1', { status: 'archived' }))
    await waitFor(() => expect(switchThread).toHaveBeenCalledWith('t0'))
  })

  it('列表加载失败:红字「不代表没有会话」,不装没事', async () => {
    apiMock.threads.mockRejectedValue(new Error('down'))
    render(<ThreadSwitcher busy={false} />)
    fireEvent.click(screen.getByText('主编讨论'))
    await waitFor(() => screen.getByText(/不代表没有会话/))
  })

  it('非线程模式(无 snapshot.thread_id)渲染 null', async () => {
    const mod = await import('../context/ContextSnapshotContext')
    vi.spyOn(mod, 'useContextSnapshot').mockReturnValue({ snapshot: null, switchThread })
    const { container } = render(<ThreadSwitcher busy={false} />)
    expect(container.innerHTML).toBe('')
  })
})
