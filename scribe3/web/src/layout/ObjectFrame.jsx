import { useId } from 'react'
import { Tabs } from '../ui/Tabs'

// 通用对象外框(spec §4 地基):任何对象套同一语义插槽——
//   顶栏 = 面包屑 › 对象名<h1> + 状态徽章(role=status) + 动作区 + 可选横向 tab;   中央 = 该对象详情(children)。
//
// 纯外部呈现接口:props 直传 breadcrumb/title/status/tabs/activeTab/onTab/actions/children,
// 不再自查注册表(呈现数据由 objectRegistry.presentationForNode 从节点算好后传入)。
// 详情组件由 DetailPane 业务路由决定并作为 children 注入,ObjectFrame 不关心其类型。
//
// compact(可选,默认 false):紧凑头部——面包屑与标题合并为一行「面包屑 › 标题」,
// 头部从三行(面包屑/标题+动作/tabs)压成两行。章工作台(ChapterStudio)启用;
// 其余调用方(DetailPane withFrame 的 character/material)不传,默认布局零变化。
// 面包屑保持在 <h1> 之外:aria-labelledby 指向的可访问名仍只含对象名,不掺路径。
export function ObjectFrame({ breadcrumb, title, status, tabs = [], activeTab, onTab, actions, children, compact = false }) {
  // useId 生成唯一标题 id:同页可能并挂多个 ObjectFrame(如 Task7 分栏),硬编码 id 会重复 → a11y 违规。
  // aria-labelledby 指向本框自己的 <h1>,让每个 region 都有唯一、正确的可访问名。
  const titleId = useId()
  return (
    <section className="flex h-full min-h-0 flex-col bg-canvas" aria-labelledby={titleId}>
      <header className="shrink-0 border-b border-line/40 px-5 py-2.5">
        {!compact && breadcrumb && <div className="mb-0.5 truncate text-meta text-muted">{breadcrumb}</div>}
        <div className="flex min-h-8 items-center gap-3" data-testid={compact ? 'object-frame-titlerow-compact' : undefined}>
          {compact && breadcrumb && (
            <span className="shrink-0 inline-flex items-center gap-1.5 text-meta text-muted">
              {breadcrumb}
              <span aria-hidden="true">›</span>
            </span>
          )}
          <h1 id={titleId} className="min-w-0 flex-1 truncate text-object-title font-semibold tracking-tight text-ink">{title}</h1>
          {status && <span role="status" className="text-meta text-muted">{status}</span>}
          {actions}
        </div>
        {tabs.length > 0 && (
          <div className="mt-2.5">
            <Tabs ariaLabel={`${title}页签`} value={activeTab} onValueChange={onTab} items={tabs} />
          </div>
        )}
      </header>
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  )
}
