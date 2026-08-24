import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AppRail, VIEWS } from '../AppRail'
import { PC_LAYOUT } from '../layout/tokens'

describe('AppRail 顶栏分组', () => {
  it('总纲是顶栏第一项，点击派发 synopsis', () => {
    const onView = vi.fn()
    expect(VIEWS[0]).toMatchObject({ key: 'synopsis', label: '总纲' })
    render(
      <AppRail
        current={{ slug: 'demo', title: '示例作品' }}
        view={null}
        onView={onView}
        onOpenLibrary={vi.fn()}
        theme="light"
        onTheme={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /总纲/ }))
    expect(onView).toHaveBeenCalledWith('synopsis')
  })

  // Task 7:章阶段撤出全局栏(插槽链 useTopbarSlot→App→BinderLayout→AppRail 已删)——
  // 即便上游误传 extra,AppRail 也不得渲染章阶段插槽;全局分区顺序保持:
  // 作品切换 → 全局视图 → 搜索 → 主题 → 系统状态。
  it('不再渲染章阶段插槽(传入 extra 也不生效)', () => {
    render(
      <AppRail
        current={{ slug: 'demo', title: '示例作品' }}
        view={null}
        onView={vi.fn()}
        onOpenLibrary={vi.fn()}
        theme="light"
        onTheme={vi.fn()}
        extra={<div data-testid="chapter-phase-topbar">章节阶段</div>}
      />,
    )

    expect(screen.queryByTestId('topbar-work-tabs')).toBeNull()
    expect(screen.queryByTestId('chapter-phase-topbar')).toBeNull()

    const separator = screen.getByTestId('topbar-view-separator')
    const globalViews = screen.getByTestId('topbar-global-views')
    const theme = screen.getByTestId('topbar-theme')
    expect(theme.className).toContain('ml-auto')
    expect(separator.compareDocumentPosition(globalViews) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(globalViews.compareDocumentPosition(theme) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  // Task 3 Step 4:全局栏收敛到 44px(取自 PC_LAYOUT.topbar,不得硬编码),
  // 并把「搜索触发」「系统状态」独立成区,区域顺序:全局视图 → 搜索 → 主题 → 系统状态。
  it('全局栏高度取自布局 token,并独立分出搜索触发与系统状态区', () => {
    render(
      <AppRail
        current={{ slug: 'demo', title: '示例作品' }}
        view={null}
        onView={vi.fn()}
        onOpenLibrary={vi.fn()}
        theme="light"
        onTheme={vi.fn()}
      />,
    )

    const rail = screen.getByTestId('app-rail')
    // 高度=token 值(44),证明未硬编码:与 PC_LAYOUT.topbar 同源
    expect(rail.style.height).toBe(`${PC_LAYOUT.topbar}px`)

    const globalViews = screen.getByTestId('topbar-global-views')
    const search = screen.getByTestId('topbar-search')
    const theme = screen.getByTestId('topbar-theme')
    const status = screen.getByTestId('topbar-status')

    // 搜索触发是可点击按钮
    expect(search.tagName).toBe('BUTTON')

    // 区域顺序:全局视图 → 搜索触发 → 主题 → 系统状态
    expect(globalViews.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(search.compareDocumentPosition(theme) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(theme.compareDocumentPosition(status) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  // Task 3 收尾①:搜索触发是真交互——传 onSearch 时点击必回调,
  // 不传时点击派发既有 s3-open-capability 事件(打开左轨「搜索」能力),二者取实现实际行为。
  it('点击搜索触发会回调 onSearch,缺省则派发 s3-open-capability', () => {
    const onSearch = vi.fn()
    const { rerender } = render(
      <AppRail current={{ slug: 'demo', title: '示例作品' }} view={null}
        onView={vi.fn()} onOpenLibrary={vi.fn()} theme="light" onTheme={vi.fn()} onSearch={onSearch} />,
    )
    fireEvent.click(screen.getByTestId('topbar-search'))
    expect(onSearch).toHaveBeenCalledTimes(1)

    // 缺省 onSearch:点击应派发 s3-open-capability(detail.capability === 'search',
    // Task 10:带 focus:true,SearchDirectory 收到后聚焦其唯一搜索框)
    const events = []
    const onCap = (e) => events.push(e.detail)
    window.addEventListener('s3-open-capability', onCap)
    rerender(
      <AppRail current={{ slug: 'demo', title: '示例作品' }} view={null}
        onView={vi.fn()} onOpenLibrary={vi.fn()} theme="light" onTheme={vi.fn()} />,
    )
    fireEvent.click(screen.getByTestId('topbar-search'))
    window.removeEventListener('s3-open-capability', onCap)
    expect(onSearch).toHaveBeenCalledTimes(1)   // 缺省路径不再碰旧回调
    expect(events).toContainEqual({ capability: 'search', focus: true })
  })

  // Task 3 收尾②(本计划信任修复核心):系统状态区不谎报——
  // 不传 status 时,状态区内绝不出现「在线/已连接/online」等虚假状态文案。
  it('不传 status 时系统状态区不谎报在线/已连接', () => {
    render(
      <AppRail current={{ slug: 'demo', title: '示例作品' }} view={null}
        onView={vi.fn()} onOpenLibrary={vi.fn()} theme="light" onTheme={vi.fn()} />,
    )
    const status = screen.getByTestId('topbar-status')
    expect(within(status).queryByText(/在线|已连接|online/i)).toBeNull()
    expect(status.textContent).not.toMatch(/在线|已连接|online/i)
  })
})
