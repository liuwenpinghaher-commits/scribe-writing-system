import { useId } from 'react'
import { Tabs } from '../ui/Tabs'

// 通用对象外框(spec §4 地基):任何对象套同一语义插槽——
//   顶栏 = 面包屑 › 对象名<h1> + 状态徽章(role=status) + 动作区 + 可选横向 tab;   中央 = 该对象详情(children)。
//
// 纯外部呈现接口:props 直传 breadcrumb/title/status/tabs/activeTab/onTab/actions/children,
// 不再自查注册表(呈现数据由 objectRegistry.presentationForNode 从节点算好后传入)。
// 详情组件由 DetailPane 业务路由决定并作为 children 注入,ObjectFrame 不关心其类型。
export function ObjectFrame({ breadcrumb, title, status, tabs = [], activeTab, onTab, actions, children }) {
  // useId 生成唯一标题 id:同页可能并挂多个 ObjectFrame(如 Task7 分栏),硬编码 id 会重复 → a11y 违规。
  // aria-labelledby 指向本框自己的 <h1>,让每个 region 都有唯一、正确的可访问名。
  const titleId = useId()
  return (
    <section className="flex h-full min-h-0 flex-col bg-canvas" aria-labelledby={titleId}>
      <header className="shrink-0 border-b border-line bg-surface px-4 py-3">
        {breadcrumb && <div className="mb-1 truncate text-meta text-muted">{breadcrumb}</div>}
        <div className="flex min-h-9 items-center gap-3">
          <h1 id={titleId} className="min-w-0 flex-1 truncate text-object-title font-semibold text-ink">{title}</h1>
          {status && <span role="status" className="text-meta text-muted">{status}</span>}
          {actions}
        </div>
        {tabs.length > 0 && <Tabs ariaLabel={`${title}页签`} value={activeTab} onValueChange={onTab} items={tabs} />}
      </header>
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  )
}
