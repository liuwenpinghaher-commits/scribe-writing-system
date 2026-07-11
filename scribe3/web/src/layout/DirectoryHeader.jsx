import { Btn } from '../ui.jsx'

// 受控语义目录头(Task 4 统一版):一个标题 heading + 可选实时数量/状态/搜索/动作。
// 关键约束——只在传入真实 handler 时才渲染对应控件:没有 onQueryChange 不出搜索框,
// 没有 primaryAction/secondaryActions 不出按钮,没有 live count 不出数字。这样彻底删掉了旧版
// "当前:xxx 固定"卡片和无 handler 的"同步/范围"假控件(点了什么都不发生,只是骗眼睛)。
// 保留 data-testid="directory-sticky-header":能力二级目录仍以它作为目录头锚点。
export function DirectoryHeader({
  title,
  count,
  query = '',
  onQueryChange,
  searchLabel,
  primaryAction,
  secondaryActions = [],
  status,
}) {
  // 有无第二行控件决定首行是否留下边距:只传 title 的能力目录不该有 8px 死边距 + 空控件行。
  const hasControls = onQueryChange || secondaryActions.length > 0 || primaryAction
  return (
    <header
      data-testid="directory-sticky-header"
      className="shrink-0 border-b border-line bg-surface px-3 py-3"
    >
      <div className={`flex min-h-8 items-center gap-2${hasControls ? ' mb-2' : ''}`}>
        <h2 className="min-w-0 flex-1 truncate text-object-title font-semibold text-ink">{title}</h2>
        {Number.isFinite(count) && <span className="text-meta tabular-nums text-muted">{count}</span>}
        {status}
      </div>
      {hasControls && (
        <div className="flex items-center gap-2">
          {onQueryChange && (
            <input
              type="search"
              aria-label={searchLabel || `${title}筛选`}
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-canvas px-3 text-helper text-ink"
            />
          )}
          {secondaryActions.map((action) => (
            <Btn key={action.label} size="xs" onClick={action.onClick}>{action.label}</Btn>
          ))}
          {primaryAction && (
            <Btn variant="primary" size="sm" onClick={primaryAction.onClick}>{primaryAction.label}</Btn>
          )}
        </div>
      )}
    </header>
  )
}
