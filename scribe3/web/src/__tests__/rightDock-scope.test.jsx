import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { Rail } from '../shell'
import { RightDock, useRightDockController } from '../studioDocks'
import { ChiefSlotProvider } from '../ChiefSlotContext'

// Task 8:右栏作用域分组(当前对象/章节/全局)+ 收件箱 badge 不谎报 + 面板异步态统一 AsyncState。
// mock api.inbox(RightDock 挂载时唯一的常驻拉取)与 chapterVersions(存档 tab 懒加载)。
const apiMock = vi.hoisted(() => ({
  inbox: vi.fn(() => Promise.resolve({ items: [], count: 0 })),
  chapterVersions: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../api', () => ({ api: apiMock }))
// ChiefDock 是在途重度改写文件,且默认 tab 就渲染它——桩掉,本套件只测右栏结构/badge,
// 主编本体行为由 chiefDock-ui / chiefDock-thread-continuity 两套保护门覆盖。
vi.mock('../ChiefDock', () => ({ ChiefDock: () => <div data-testid="chief-stub" /> }))

function Harness(props) {
  const controller = useRightDockController(props)
  return (
    <ChiefSlotProvider>
      <Rail side="left" caps={[]} active="" onActive={() => {}}
        secondaryCaps={controller.caps}
        secondaryActive={controller.activeKey}
        onSecondaryClick={controller.activate} />
      <RightDock active={controller.active} seq={props.seq} />
    </ChiefSlotProvider>
  )
}

describe('RightDock 作用域与真实 badge(Task 8)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    apiMock.inbox.mockResolvedValue({ items: [], count: 0 })
  })

  it('separates object tools from global inbox', async () => {
    render(<Harness sel={{ mode: 'node', node: { type: 'chapter', ref: 1 } }} seq={1} />)
    // 对象组:主编（选择环已收进主编模式条）
    expect(screen.getByRole('group', { name: '当前对象' })).toBeTruthy()
    // 全局组内含收件箱按钮(不随章/选中变)
    const globalGroup = screen.getByRole('group', { name: '全局' })
    expect(within(globalGroup).getByRole('button', { name: /收件箱/ })).toBeTruthy()
    // 章节组:存档(选中章才有意义;驾驶已收进主编模式条)
    const chapterGroup = screen.getByRole('group', { name: '章节' })
    expect(within(chapterGroup).getByRole('button', { name: '存档' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Pilot/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /选择环/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /主编驾驶/ })).toBeNull()
  })

  it('does not turn inbox request failure into zero pending items', async () => {
    apiMock.inbox.mockRejectedValue(new Error('offline'))
    render(<Harness seq={1} />)
    // 失败 → 显式「状态未知」,而不是静默无 badge(看起来像 0 待办)
    expect(await screen.findByLabelText('收件箱状态未知')).toBeTruthy()
    const inboxBtn = screen.getByRole('button', { name: /收件箱/ })
    expect(within(inboxBtn).queryByText('0')).toBeNull()
    // 面板端同真相:切到收件箱 tab → error 走 AsyncState(role=alert)+ 重试
    fireEvent.click(inboxBtn)
    expect(await screen.findByRole('alert')).toBeTruthy()
    apiMock.inbox.mockResolvedValue({ items: [], count: 0 })
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    expect(await screen.findByTestId('inbox-empty')).toBeTruthy()
    expect(screen.getByText(/这页没有等你的事项/)).toBeTruthy()
    expect(screen.queryByText(/一切有账/)).toBeNull()
    // 重试成功后未知标记撤下(count=0 → 无 badge 也无「?」)
    expect(screen.queryByLabelText('收件箱状态未知')).toBeNull()
  })

  it('does not disguise archive load failure as "no archives yet"', async () => {
    // 旧行为:chapterVersions 失败 → 空数组 → 渲成「还没有存档点」(假空态)
    apiMock.chapterVersions
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce([])
    render(<Harness seq={1} />)
    fireEvent.click(screen.getByRole('button', { name: '存档' }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('存档列表加载失败')
    expect(screen.queryByText(/还没有存档点/)).toBeNull()
    // 重试 → 第二次成功(真空列表)→ 这才允许显示空态文案
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    expect(await screen.findByText(/还没有存档点/)).toBeTruthy()
  })

  it('shows the real pending count once inbox loads', async () => {
    apiMock.inbox.mockResolvedValue({ items: [{}, {}, {}], count: 3 })
    render(<Harness seq={1} />)
    const inboxBtn = screen.getByRole('button', { name: /收件箱/ })
    expect(await within(inboxBtn).findByText('3')).toBeTruthy()
    // 有真实数字时不得同时挂「状态未知」
    expect(screen.queryByLabelText('收件箱状态未知')).toBeNull()
  })

  // ── 收尾补测(双审后):scope 归属逐项锁死 + 空组不渲染 + 存量偏好不失效 ──

  it('scopes chief and selection to the object group; aux panel is gone from the right dock', () => {
    render(<Harness sel={{ mode: 'node', node: { type: 'chapter', ref: 1 } }} seq={1} />)
    // 裁决:chief/selection='object'(随选中对象变)
    const objectGroup = screen.getByRole('group', { name: '当前对象' })
    expect(within(objectGroup).getByRole('button', { name: '主编' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /选择环/ })).toBeNull()
    // 2026-07-12 裁决:「章节辅助」capability 移出栏4(入口在章工作台头部,点击全宽层)——
    // 右栏任何分组都不得再出现此入口,栏4 专属主编对话等章节工具。
    expect(screen.queryByRole('button', { name: '章节辅助' })).toBeNull()
    // 章节组仍在(存档/Pilot),不因迁出章节辅助而整组消失
    expect(within(screen.getByRole('group', { name: '章节' })).getByRole('button', { name: '存档' })).toBeTruthy()
  })

  it('falls back stored s3.rightTab=context preference to chief after the aux capability removal', async () => {
    // 存量用户偏好停在已移除的 context tab → 失效回退效应收敛到主编,不白屏不悬空
    localStorage.setItem('s3.rightTab', 'context')
    render(<Harness sel={{ mode: 'node', node: { type: 'chapter', ref: 1 } }} seq={1} />)
    await screen.findByTestId('chief-stub')
    expect(screen.getByRole('button', { name: '主编' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('renders no chapter group when no chapter is selected', () => {
    // 未选章(seq=null)→ context/versions/pilot 三个 cap 不产生 → 章节组整组不渲染(空组无边框)
    render(<Harness sel={{ mode: 'empty' }} />)
    expect(screen.queryByRole('group', { name: '章节' })).toBeNull()
    // 对象/全局组不受影响:主编与收件箱常驻
    expect(within(screen.getByRole('group', { name: '当前对象' })).getByRole('button', { name: '主编' })).toBeTruthy()
    expect(within(screen.getByRole('group', { name: '全局' })).getByRole('button', { name: /收件箱/ })).toBeTruthy()
  })

  it('keeps the stored s3.rightTab=versions preference active after grouping', async () => {
    // key 全保留是分组的硬前提:存量偏好在分组渲染后仍应命中并高亮,不回落 chief
    localStorage.setItem('s3.rightTab', 'versions')
    render(<Harness seq={1} />)
    expect(screen.getByRole('button', { name: '存档' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: '主编' }).getAttribute('aria-pressed')).toBe('false')
    // 面板真的按偏好挂上(chapterVersions 默认解析空列表 → 空态文案)
    expect(await screen.findByText(/还没有存档点/)).toBeTruthy()
  })

  it('未知入口不会留下分裂活动态，而是回退主编', async () => {
    localStorage.setItem('s3.rightTab', 'unknown-capability')
    render(<Harness seq={1} />)
    expect(await screen.findByTestId('chief-stub')).toBeTruthy()
    expect(screen.getByRole('button', { name: '主编' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('离开章节时活动的章节能力消失并回退主编', async () => {
    localStorage.setItem('s3.rightTab', 'versions')
    const view = render(<Harness seq={1} />)
    expect(screen.getByRole('button', { name: '存档' }).getAttribute('aria-pressed')).toBe('true')
    view.rerender(<Harness />)
    expect(await screen.findByTestId('chief-stub')).toBeTruthy()
    expect(screen.getByRole('button', { name: '主编' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.queryByRole('group', { name: '章节' })).toBeNull()
  })
})
