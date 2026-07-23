import { Btn } from '../ui.jsx'

// 受控语义目录头:标题 + 可选数量/状态/搜索/动作。
// 只在传入真实 handler 时渲染对应控件(无 onQueryChange 不出搜索框)。
// 窄栏(≈240–264px)下：搜索独占一行，动作另起一行且 nowrap，避免中文竖排成「导/入」。
export function DirectoryHeader({
  title,
  count,
  query = '',
  onQueryChange,
  searchLabel,
  searchPlaceholder,
  searchInputRef,
  primaryAction,
  secondaryActions = [],
  status,
}) {
  const hasSearch = Boolean(onQueryChange)
  const hasActions = secondaryActions.length > 0 || Boolean(primaryAction)
  const hasControls = hasSearch || hasActions
  return (
    <header
      data-testid="directory-sticky-header"
      className="shrink-0 border-b border-line/60 bg-surface px-3 py-2.5"
    >
      <div className={`flex min-h-7 items-center gap-2${hasControls ? ' mb-2' : ''}`}>
        <h2 className="min-w-0 flex-1 truncate text-object-title font-semibold tracking-tight text-ink">{title}</h2>
        {Number.isFinite(count) && <span className="text-meta tabular-nums text-muted shrink-0">{count}</span>}
        {status}
      </div>
      {hasSearch && (
        <div className={hasActions ? 'mb-2' : ''}>
          <input
            ref={searchInputRef}
            type="search"
            aria-label={searchLabel || `${title}筛选`}
            placeholder={searchPlaceholder || searchLabel || undefined}
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            className="h-8 w-full min-w-0 rounded-md border border-transparent bg-soft/80 px-2.5 text-helper text-ink outline-none transition-colors focus:border-brand/40 focus:bg-surface focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-brand)_12%,transparent)]"
          />
        </div>
      )}
      {hasActions && (
        <div className="flex flex-wrap items-center gap-1.5" data-testid="directory-header-actions">
          {secondaryActions.map((action) => (
            // 默认 type=button：嵌在 <form> 内时不会误提交（语义召回等次要动作）
            <Btn
              key={action.label}
              type={action.type || 'button'}
              size="xs"
              onClick={action.onClick}
              disabled={action.disabled}
              className="shrink-0 whitespace-nowrap"
            >
              {action.label}
            </Btn>
          ))}
          {primaryAction && (
            // 默认 type=button；需要表单提交语义时由调用方传 type:'submit'
            <Btn
              type={primaryAction.type || 'button'}
              variant="primary"
              size="sm"
              onClick={primaryAction.onClick}
              disabled={primaryAction.disabled}
              className="shrink-0 whitespace-nowrap"
            >
              {primaryAction.label}
            </Btn>
          )}
        </div>
      )}
    </header>
  )
}
