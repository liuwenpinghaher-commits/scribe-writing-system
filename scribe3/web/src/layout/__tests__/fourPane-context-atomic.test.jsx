import { beforeAll, beforeEach, describe, it, expect, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { FourPaneShell } from '../FourPaneShell'
import { ContextSnapshotProvider } from '../../context/ContextSnapshotContext'

// 服务端会话初始快照(与 store.create_context_session 返回形状对齐)
const baseSnap = {
  session_id: 'ctx:1',
  work: 'demo',
  revision: 3,
  thread_id: 'thread:demo_default',
  entry: 'manuscript',
  directory_path: [],
  focus: { type: 'entry', id: 'entry:manuscript', label: '' },
  detail_route: 'entry:manuscript',
  chapter: null,
  phase: null,
  focalizer: null,
  previous_revision: 2,
  navigation_id: 'init',
  context_hash: 'h3',
}

function err409(latest) {
  return Object.assign(new Error('HTTP 409'), {
    status: 409,
    body: { detail: { code: 'stale_context', expected: 3, actual: latest.revision, latest } },
  })
}

const apiMock = vi.hoisted(() => ({
  getWork: () => 'demo',
  promisesLedger: vi.fn(() => Promise.resolve({ open: [], closed: [], red_herring: [] })),
  motifs: vi.fn(() => Promise.resolve([])),
  qc: vi.fn(() => Promise.resolve({})),
  chapter: vi.fn(() => Promise.resolve({ title: '第七章', scene_truth: '', deductions: [], involved_characters: [] })),
  entities: vi.fn(() => Promise.resolve([])),
  createContextSession: vi.fn(),
  contextSession: vi.fn(),
  navigateContext: vi.fn(),
  contextSnapshot: vi.fn(),
}))

vi.mock('../../api', () => ({ api: apiMock }))

vi.mock('../../DetailPane', () => ({
  DetailPane: ({ sel }) => (
    <div data-testid="detail-content">{sel?.mode === 'view' ? `view:${sel.viewKey}` : `node:${sel?.node?.id || 'empty'}`}</div>
  ),
}))

vi.mock('../../ProjectTree', () => ({
  ProjectTree: () => <div data-testid="project-tree" />,
}))

vi.mock('../../DeduceTree', () => ({ DeduceTree: () => <div /> }))

// Materials 链会拉进 sigma(WebGL),jsdom 下必须掐断
vi.mock('../../Materials', () => ({ MaterialList: () => <div data-testid="material-list" /> }))

// 栏2 手稿目录:409 对齐后 UI 跟随服务端 entry 的可见凭据
vi.mock('../ManuscriptDirectory', () => ({
  ManuscriptDirectory: () => <div data-testid="manuscript-directory" />,
}))

// 栏2 设定库目录:两个可点条目,走 onSelectItem 生产路由
vi.mock('../CodexDirectory', () => ({
  CodexDirectory: ({ onSelectItem }) => (
    <div data-testid="codex-directory">
      <button onClick={() => onSelectItem({ id: 'character:甲', type: 'character', ref: '甲', label: '甲' })}>甲</button>
      <button onClick={() => onSelectItem({ id: 'character:乙', type: 'character', ref: '乙', label: '乙' })}>乙</button>
    </div>
  ),
}))

vi.mock('../../studioDocks', async () => {
  const actual = await vi.importActual('../../studioDocks')
  return {
    ...actual,
    useRightDockController: ({ sel }) => {
      const active = {
        key: 'chief',
        label: '主编',
        scope: 'object',
        render: () => <aside data-testid="chief">{sel?.node?.id || 'none'}</aside>,
      }
      return { caps: [active], active, activeKey: active.key, activate: () => {} }
    },
    RightDock: ({ active }) => active.render(),
  }
})

const tree = {
  manuscript: {
    id: 'manuscript_root', type: 'manuscript_root', label: '手稿',
    children: [{ id: 'vol:1', type: 'volume', ref: '1', label: '第一卷', children: [] }],
  },
  codex: {
    id: 'codex_root', type: 'codex_root', label: '设定库',
    children: [{ id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色', children: [{ id: 'character:甲', type: 'character', ref: '甲', label: '甲' }] }],
  },
  materials: { id: 'material_root', type: 'material_root', label: '素材库' },
}

function Harness({ work = 'demo' }) {
  const [sel, setSel] = useState({ mode: 'node', node: null })
  const onSelectNode = (node) => {
    if (!node) { setSel({ mode: 'node', node: null }); return }
    if (node.type === 'view') setSel({ mode: 'view', viewKey: node.id.split(':')[1] })
    else setSel({ mode: 'node', node })
  }
  return (
    <ContextSnapshotProvider work={work}>
      {/* App 层旁路入口(I-2 复现):顶栏横切视图 / 时间线跳章都在 FourPaneShell 之外
          直改 sel(App.onView / App.handleJumpChapter),不经 handleSelectItem 的 navigate */}
      <button onClick={() => setSel({ mode: 'view', viewKey: 'atlas' })}>顶栏图谱</button>
      <button onClick={() => setSel({ mode: 'node', node: { id: 'ch:5', type: 'chapter', ref: 5, label: '5' } })}>跳到第5章</button>
      <FourPaneShell tree={tree} sel={sel} onSelectNode={onSelectNode} work={work} leftSeq={3} reload={() => {}} />
    </ContextSnapshotProvider>
  )
}

// 栏3 详情容器:react-resizable-panels 会把 Panel 的 id 自动写成 data-testid,
// 与内层 detail 容器撞名——取不带 data-panel 的那只(真正挂 revision 的容器)。
function detailEl() {
  return screen.getAllByTestId('detail').find((el) => !el.hasAttribute('data-panel'))
}

// 等 Provider 完成会话建立(服务端快照 revision=3 已投影到栏3容器)
async function renderReady() {
  const view = render(<Harness />)
  await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('3'))
  return view
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

describe('四栏上下文原子性(单一 ContextSnapshot reducer)', () => {
  beforeAll(() => {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    globalThis.ResizeObserver = ResizeObserverMock
  })

  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    apiMock.createContextSession = vi.fn(() => Promise.resolve({ ...baseSnap }))
    apiMock.navigateContext = vi.fn((id, intent) => Promise.resolve({
      ...baseSnap,
      ...intent,
      revision: intent.expected_revision + 1,
      previous_revision: intent.expected_revision,
      context_hash: `h${intent.expected_revision + 1}`,
    }))
  })

  it('切换入口只发一个完整 NavigationIntent', async () => {
    await renderReady()

    fireEvent.click(screen.getByRole('button', { name: '设定库' }))

    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)
    expect(apiMock.navigateContext).toHaveBeenCalledWith('ctx:1', expect.objectContaining({
      navigation_id: expect.any(String),
      expected_revision: 3,
      entry: 'codex',
      directory_path: ['codex'],
      focus: expect.objectContaining({ type: 'entry', id: 'entry:codex' }),
      detail_route: 'entry:codex',
      reason: 'entry',
    }))
  })

  it('目录选中后详情与主编共享同一 revision', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()

    fireEvent.click(screen.getByRole('button', { name: '甲' }))

    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)
    expect(apiMock.navigateContext).toHaveBeenCalledWith('ctx:1', expect.objectContaining({
      expected_revision: 3,
      focus: expect.objectContaining({ type: 'character', id: 'character:甲' }),
      detail_route: 'character:甲',
      reason: 'item',
    }))
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('4'))
    expect(screen.getByTestId('right-dock').getAttribute('data-context-revision')).toBe('4')
    // 既有 sel 链路不被 intent 化破坏:详情栏同步收到条目
    expect(screen.getByTestId('detail-content').textContent).toBe('node:character:甲')
  })

  it('409 时服务端 latest 赢:整体替换、leftTab 跟随对齐、不反向调用(请求收敛)', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()
    // latest.entry='manuscript' ≠ 本地 leftTab='codex' —— I-1 打架场景
    apiMock.navigateContext.mockImplementationOnce(() =>
      Promise.reject(err409({ ...baseSnap, revision: 9, context_hash: 'h9', navigation_id: 'nav-other' })))

    fireEvent.click(screen.getByRole('button', { name: '甲' }))

    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('9'))
    expect(screen.getByTestId('right-dock').getAttribute('data-context-revision')).toBe('9')
    // 本窗口 UI 跟随服务端 latest.entry:栏2 切到手稿目录,leftTab 偏好同步落库
    // (落库在 useWorkScopedPref 的 effect 里,比目录切换晚两个渲染周期,须 waitFor)
    await waitFor(() => {
      expect(screen.getByTestId('manuscript-directory')).toBeTruthy()
      expect(localStorage.getItem('s3.demo.leftTab')).toBe('manuscript')
    })
    // 请求循环消灭:补记 effect 不把旧 leftTab 反向写回服务端,总次数收敛在 1
    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)
  })

  it('在途确认串行化:后续意图进单槽 pending,以已确认 revision 为 CAS 基线(I-3①乱序)', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()
    const d1 = deferred()
    apiMock.navigateContext.mockImplementationOnce(() => d1.promise)

    fireEvent.click(screen.getByRole('button', { name: '甲' }))
    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)
    expect(detailEl().getAttribute('data-context-revision')).toBe('4')   // 乐观即时

    fireEvent.click(screen.getByRole('button', { name: '乙' }))
    // 在途:不并发直发,乙 进 pending 槽
    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)
    expect(detailEl().getAttribute('data-context-revision')).toBe('5')

    // 甲 的确认晚到:seq 守卫丢弃可见覆盖(不回滚到 甲),只推进 CAS 基线
    await act(async () => {
      d1.resolve({ ...baseSnap, revision: 4, focus: { type: 'character', id: 'character:甲', label: '甲' }, detail_route: 'character:甲', context_hash: 'h4' })
      await d1.promise
    })
    await waitFor(() => expect(apiMock.navigateContext).toHaveBeenCalledTimes(2))
    const [, wireA] = apiMock.navigateContext.mock.calls[0]
    const [, wireB] = apiMock.navigateContext.mock.calls[1]
    expect(wireA.expected_revision).toBe(3)
    // 乙 用服务端最新【已确认】revision(4)做基线,而非乐观值 5
    expect(wireB.expected_revision).toBe(4)
    expect(wireB.focus).toEqual(expect.objectContaining({ id: 'character:乙' }))
    expect(wireB.navigation_id).not.toBe(wireA.navigation_id)
    // 最终对齐 乙 的确认(rev 5),中途从未闪回 甲
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('5'))
    expect(screen.getByTestId('detail-content').textContent).toBe('node:character:乙')
  })

  it('409 到达时用户已再导航:latest 不回滚用户最新操作,只作为重试基线(I-3②)', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()
    const d1 = deferred()
    apiMock.navigateContext.mockImplementationOnce(() => d1.promise)

    fireEvent.click(screen.getByRole('button', { name: '甲' }))
    fireEvent.click(screen.getByRole('button', { name: '乙' }))
    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)

    // 甲 的 409 晚到,latest.entry='manuscript':用户已在 乙 → latest 被丢弃不上屏
    await act(async () => {
      d1.reject(err409({ ...baseSnap, revision: 9, context_hash: 'h9', navigation_id: 'nav-other' }))
      await d1.promise.catch(() => {})
    })
    await waitFor(() => expect(apiMock.navigateContext).toHaveBeenCalledTimes(2))
    const [, wireB] = apiMock.navigateContext.mock.calls[1]
    // 乙 以 latest 的 revision 为新基线重试,语义仍是用户最新操作(codex/乙)
    expect(wireB.expected_revision).toBe(9)
    expect(wireB.entry).toBe('codex')
    expect(wireB.focus).toEqual(expect.objectContaining({ id: 'character:乙' }))
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('10'))
    // UI 未被 latest 回滚:仍在设定库目录,没有闪回手稿
    expect(screen.queryByTestId('manuscript-directory')).toBeNull()
    expect(screen.getByTestId('codex-directory')).toBeTruthy()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:character:乙')
  })

  it('会话建立前本地导航:建成后以 restore 补发一次当前语义状态(I-3③)', async () => {
    const dc = deferred()
    apiMock.createContextSession = vi.fn(() => dc.promise)
    localStorage.setItem('s3.demo.leftTab', 'codex')
    render(<Harness />)

    // 会话未建成:本地直通,revision 本地自增,不发请求
    fireEvent.click(screen.getByRole('button', { name: '甲' }))
    expect(apiMock.navigateContext).not.toHaveBeenCalled()
    expect(detailEl().getAttribute('data-context-revision')).toBe('1')

    await act(async () => {
      dc.resolve({ ...baseSnap })
      await dc.promise
    })
    // 建成:不用服务端初始快照覆盖用户位置,而是补发一次 restore
    await waitFor(() => expect(apiMock.navigateContext).toHaveBeenCalledTimes(1))
    expect(apiMock.navigateContext).toHaveBeenCalledWith('ctx:1', expect.objectContaining({
      reason: 'restore',
      expected_revision: 3,
      entry: 'codex',
      focus: expect.objectContaining({ id: 'character:甲' }),
    }))
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('4'))
    expect(screen.getByTestId('detail-content').textContent).toBe('node:character:甲')
  })

  it('work 切换废弃在途确认:旧会话的确认/基线不再污染新会话(I-3④)', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    apiMock.createContextSession = vi.fn((body) => Promise.resolve(
      body?.work === 'book_b'
        ? { ...baseSnap, session_id: 'ctx:2', work: 'book_b', revision: 0, context_hash: 'g0' }
        : { ...baseSnap },
    ))
    const view = render(<Harness />)
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('3'))
    const d1 = deferred()
    apiMock.navigateContext.mockImplementationOnce(() => d1.promise)

    fireEvent.click(screen.getByRole('button', { name: '甲' }))
    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)

    view.rerender(<Harness work="book_b" />)
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('0'))

    // 旧 work 的确认晚到:代际守卫整体作废,不覆盖新会话快照、不触发续发
    await act(async () => {
      d1.resolve({ ...baseSnap, revision: 4, context_hash: 'h4' })
      await d1.promise
    })
    expect(detailEl().getAttribute('data-context-revision')).toBe('0')
    expect(apiMock.navigateContext).toHaveBeenCalledTimes(1)
  })

  it('context API 缺席时优雅降级:本地 reducer 直通,revision 本地自增', async () => {
    apiMock.createContextSession = undefined
    localStorage.setItem('s3.demo.leftTab', 'codex')
    render(<Harness />)

    fireEvent.click(screen.getByRole('button', { name: '甲' }))

    expect(apiMock.navigateContext).not.toHaveBeenCalled()
    expect(detailEl().getAttribute('data-context-revision')).toBe('1')
    expect(screen.getByTestId('right-dock').getAttribute('data-context-revision')).toBe('1')
    expect(screen.getByTestId('detail-content').textContent).toBe('node:character:甲')
  })

  // Task 5:快照不仅盖 revision,更要把内容投影进四栏。409 latest 把语义从"角色甲"
  // 换成"章节 7"后,详情与主编必须同帧收到章节 7(而非停在用户点的角色甲),
  // 且两栏共享同一 revision——原子性 + 内容一致,缺一即撕裂。
  it('409 latest 内容投影:从角色甲切到章节 7,详情与主编同帧共收章节 7', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()
    // latest 指向章节 7(manuscript 入口),detail_route/chapter/phase/focus 完整
    apiMock.navigateContext.mockImplementationOnce(() =>
      Promise.reject(err409({
        ...baseSnap,
        revision: 9,
        context_hash: 'h9',
        navigation_id: 'nav-other',
        entry: 'manuscript',
        chapter: 7,
        phase: 'deduce',
        focus: { type: 'chapter', id: 'chapter:7', label: '第七章' },
        detail_route: 'chapter:7',
      })))

    fireEvent.click(screen.getByRole('button', { name: '甲' }))

    // 同一 revision(9)同帧盖到栏3/栏4:原子性凭据
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('9'))
    expect(screen.getByTestId('right-dock').getAttribute('data-context-revision')).toBe('9')
    // 内容投影:详情与主编都收到章节 7(id=ch:7),而非用户点的角色甲
    expect(screen.getByTestId('detail-content').textContent).toBe('node:ch:7')
    expect(screen.getByTestId('chief').textContent).toBe('ch:7')
  })

  // I-2:isView 读 effectiveSel。跨 node↔view 边界对齐时,布局(栏2 显隐)与内容
  // (栏3 渲染 view)必须同源同帧;若 isView 仍读本地 sel 则会持续撕裂(投影不回写 sel)。
  it('node↔view 跨边界对齐:409 latest 是横切视图时栏2隐藏、栏3渲染 view(I-2)', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()
    // 用户在设定库点角色甲(本地 sel=node),但服务端 latest 是横切视图 atlas
    apiMock.navigateContext.mockImplementationOnce(() =>
      Promise.reject(err409({
        ...baseSnap,
        revision: 9,
        context_hash: 'h9',
        navigation_id: 'nav-other',
        entry: 'manuscript',
        focus: { type: 'view', id: 'view:atlas', label: '图谱' },
        detail_route: 'view:atlas',
        chapter: null,
      })))

    fireEvent.click(screen.getByRole('button', { name: '甲' }))

    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('9'))
    // isView 由 effectiveSel 驱动:栏2 目录整体隐藏,栏3 全画布渲染视图
    await waitFor(() => expect(screen.queryByTestId('col-directory')).toBeNull())
    expect(screen.getByTestId('detail-content').textContent).toBe('view:atlas')
  })

  it('I-2 顶栏切横切视图(App 层旁路):不被章/条目快照投影盖回,并补记一次 view 语义导航', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()
    // 进入条目(=进手稿后 navigated=true 的等价态):快照 focus 停在 character:甲
    fireEvent.click(screen.getByRole('button', { name: '甲' }))
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('4'))

    // 顶栏点图谱:App 层直改 sel,不经 FourPaneShell 回调
    fireEvent.click(screen.getByRole('button', { name: '顶栏图谱' }))

    // 栏3 必须渲染视图(而不是被投影盖回 character:甲)
    await waitFor(() => expect(screen.getByTestId('detail-content').textContent).toBe('view:atlas'))
    // 本地旁路先动 → 补记语义导航进快照(与 I-1 entry 对齐同型),快照保持唯一事实源
    expect(apiMock.navigateContext).toHaveBeenLastCalledWith('ctx:1', expect.objectContaining({
      focus: expect.objectContaining({ type: 'view', id: 'view:atlas' }),
      detail_route: 'view:atlas',
      reason: 'view',
    }))
  })

  it('I-2 时间线跳章(App 层直改 sel):不被旧条目快照投影盖回,补记 item 语义导航', async () => {
    localStorage.setItem('s3.demo.leftTab', 'codex')
    await renderReady()
    fireEvent.click(screen.getByRole('button', { name: '甲' }))
    await waitFor(() => expect(detailEl().getAttribute('data-context-revision')).toBe('4'))

    fireEvent.click(screen.getByRole('button', { name: '跳到第5章' }))

    await waitFor(() => expect(screen.getByTestId('detail-content').textContent).toBe('node:ch:5'))
    expect(apiMock.navigateContext).toHaveBeenLastCalledWith('ctx:1', expect.objectContaining({
      focus: expect.objectContaining({ type: 'chapter', id: 'chapter:5' }),
      detail_route: 'chapter:5',
      chapter: 5,
      reason: 'item',
    }))
  })
})
