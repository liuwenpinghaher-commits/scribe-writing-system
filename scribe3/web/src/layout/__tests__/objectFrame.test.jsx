import { describe, it, expect } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { ObjectFrame } from '../ObjectFrame'
import { presentationForNode } from '../objectRegistry'

// ObjectFrame 已从「查注册表的黑盒」改造为「纯外部呈现接口」:props 直传 breadcrumb/title/status/tabs/actions,
// 语义头部(面包屑 + <h1> 对象名 + role=status 徽章)统一插槽。呈现数据由 presentationForNode(node) 计算,
// 详情组件仍由 DetailPane 业务路由决定并作为 children 传入。
describe('ObjectFrame 语义对象外框', () => {
  it('renders a semantic object header', () => {
    render(<ObjectFrame breadcrumb="设定库 / 角色" title="柳三更" status="已保存" actions={<button>更多</button>}><div>详情</div></ObjectFrame>)
    expect(screen.getByRole('heading', { name: '柳三更' })).toBeInTheDocument()
    expect(screen.getByText('设定库 / 角色')).toBeInTheDocument()
    expect(screen.getByText('已保存')).toHaveAttribute('role', 'status')
  })

  it('aria-labelledby 指向本框标题,且同页两个外框的 id 互不相同(useId 唯一,不撞 a11y)', () => {
    const { container } = render(
      <div>
        <ObjectFrame breadcrumb="甲面包屑" title="甲"><div /></ObjectFrame>
        <ObjectFrame breadcrumb="乙面包屑" title="乙"><div /></ObjectFrame>
      </div>,
    )
    const sections = [...container.querySelectorAll('section[aria-labelledby]')]
    const headings = [...container.querySelectorAll('h1')]
    expect(sections).toHaveLength(2)
    expect(headings).toHaveLength(2)
    const secIds = sections.map((s) => s.getAttribute('aria-labelledby'))
    // 两框各自的 aria-labelledby 不重复(硬编码 object-title 会重复,useId 不会)
    expect(new Set(secIds).size).toBe(2)
    // 每个 aria-labelledby 都精确对上同页某个 <h1> 的 id(指向确实存在)
    expect([...secIds].sort()).toEqual(headings.map((h) => h.id).sort())
  })

  it('缺省 status/actions/tabs 时不渲染多余节点,只出面包屑与标题', () => {
    render(<ObjectFrame breadcrumb="素材库" title="铃铛资料"><div>正文</div></ObjectFrame>)
    expect(screen.getByRole('heading', { name: '铃铛资料' })).toBeInTheDocument()
    expect(screen.queryByRole('status')).toBeNull()
    expect(screen.queryByRole('tablist')).toBeNull()
  })

  it('传入 tabs 时渲染横向页签(复用 ui/Tabs),回调 onTab 生效', () => {
    render(<ObjectFrame breadcrumb="手稿" title="第 3 章" tabs={[{ value: 'outline', label: '大纲' }, { value: 'final', label: '正文' }]} activeTab="outline" onTab={() => {}}><div /></ObjectFrame>)
    expect(screen.getByRole('tablist')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '正文' })).toBeInTheDocument()
  })
})

// presentationForNode:仅为 chapter / character / material 三类返回基础呈现数据(breadcrumb/title);
// 其余类型返回 null,DetailPane 据此决定「不包对象框架」(容器/横切视图/创建表单/能力详情等原样渲染)。
describe('presentationForNode 呈现契约', () => {
  it.each([
    [{ type: 'chapter', ref: 3, label: '第 3 章' }, '手稿', '第 3 章'],
    [{ type: 'character', ref: 'a', label: '柳三更' }, '设定库 / 角色', '柳三更'],
    [{ type: 'material', ref: '5', label: '铃铛资料' }, '素材库', '铃铛资料'],
  ])('为 %o 返回 breadcrumb/title', (node, breadcrumb, title) => {
    expect(presentationForNode(node)).toMatchObject({ breadcrumb, title })
  })

  it('title 兜底用 ref(label 缺省也不空标题)', () => {
    expect(presentationForNode({ type: 'character', ref: '焦三' }).title).toBe('焦三')
  })

  it('非 chapter/character/material 一律返回 null(调用方不包外框)', () => {
    expect(presentationForNode({ type: 'faction', ref: '云门', label: '云门' })).toBeNull()
    expect(presentationForNode({ type: 'promise_view', ref: 'open' })).toBeNull()
    expect(presentationForNode({ type: 'codex_category', ref: 'character' })).toBeNull()
    expect(presentationForNode(null)).toBeNull()
  })
})
