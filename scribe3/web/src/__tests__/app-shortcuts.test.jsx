import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

// cmdk 依赖 ResizeObserver 与 Element.scrollIntoView(jsdom 均无)——每文件补桩
beforeAll(() => {
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
  if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => {}
})

// App 顶层键盘层(⌘K / ⇧⌘K)专项。只 mock 重型子树,保留真实 AppRail 与真实
// CommandPalette —— 这样「视图」组的 {cur && …} 依赖是真跑,不是复刻。
const apiMock = vi.hoisted(() => ({
  works: vi.fn(() => Promise.resolve([{ slug: 'demo', title: 'Demo 书' }])),
  setWork: vi.fn(),
}))
vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../BinderLayout', () => ({ BinderLayout: ({ work }) => <div data-testid="binder" data-work={work} /> }))
vi.mock('../Library', () => ({
  // 点一下就"打开 demo 书"(App.open → setCur),把 App 推进作品内态
  Library: ({ onSelect }) => (
    <button type="button" onClick={() => onSelect({ slug: 'demo', title: 'Demo 书' })}>open-demo</button>
  ),
}))
vi.mock('../ui/Toast', () => ({ ToastHost: () => null }))

const PALETTE_PLACEHOLDER = '跳视图 / 切书 / 作品库…'
const key = (opts) => fireEvent.keyDown(window, { key: 'k', ...opts })

async function enterWork() {
  fireEvent.click(screen.getByText('open-demo'))
  await screen.findByTestId('binder')   // cur 已置 → 进入作品内态
}

describe('App 全局快捷键 ⌘K / ⇧⌘K', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    apiMock.works.mockResolvedValue([{ slug: 'demo', title: 'Demo 书' }])
  })

  it('作品库(无 cur)⌘K 打开命令面板,且不出「视图」组', async () => {
    render(<App />)
    await screen.findByText('open-demo')
    expect(screen.queryByPlaceholderText(PALETTE_PLACEHOLDER)).toBeNull()

    key({ metaKey: true })

    expect(await screen.findByPlaceholderText(PALETTE_PLACEHOLDER)).toBeTruthy()
    // 无 cur:命令面板只出「作品」组,不出「视图」组
    expect(screen.getByText('作品')).toBeTruthy()
    expect(screen.queryByText('视图')).toBeNull()
  })

  it('刷新后从本地记录恢复仍存在的当前作品，而非退回作品库丢失章节上下文', async () => {
    localStorage.setItem('s3-active-work', 'demo')
    render(<App />)

    const binder = await screen.findByTestId('binder')
    expect(binder.getAttribute('data-work')).toBe('demo')
    expect(apiMock.setWork).toHaveBeenCalledWith('demo')
  })

  it('作品内 ⌘K 派发 s3-open-capability{search,focus:true},不开命令面板', async () => {
    render(<App />)
    await screen.findByText('open-demo')
    await enterWork()

    const events = []
    const onCap = (e) => events.push(e.detail)
    window.addEventListener('s3-open-capability', onCap)
    key({ metaKey: true })
    window.removeEventListener('s3-open-capability', onCap)

    expect(events).toContainEqual({ capability: 'search', focus: true })
    // ⌘K 让位给搜索:命令面板不弹
    expect(screen.queryByPlaceholderText(PALETTE_PLACEHOLDER)).toBeNull()
  })

  it('作品内 ⇧⌘K 打开命令面板,「视图」组可达并能跳视图', async () => {
    render(<App />)
    await screen.findByText('open-demo')
    await enterWork()

    // ⇧⌘K 不派发搜索事件,而是开命令面板
    const events = []
    const onCap = (e) => events.push(e.detail)
    window.addEventListener('s3-open-capability', onCap)
    key({ metaKey: true, shiftKey: true })
    window.removeEventListener('s3-open-capability', onCap)
    expect(events).toHaveLength(0)

    const input = await screen.findByPlaceholderText(PALETTE_PLACEHOLDER)
    // 命令面板根(cmdk-root),把断言/点击限定在面板内 —— 顶栏 AppRail 也渲 VIEWS,'图谱'重名
    const palette = within(input.closest('[cmdk-root]'))
    // cur 存在 → 「视图」组渲染,VIEWS 里的「图谱」可点跳转(读真实 cur 依赖)
    expect(palette.getByText('视图')).toBeTruthy()
    const atlas = palette.getByText('图谱')
    expect(atlas).toBeTruthy()
    fireEvent.click(atlas)
    // 跳视图后面板关闭(act(onView) → onClose),证明命令项真的执行了
    await waitFor(() => expect(screen.queryByPlaceholderText(PALETTE_PLACEHOLDER)).toBeNull())
  })
})
