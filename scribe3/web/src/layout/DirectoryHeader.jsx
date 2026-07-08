export function DirectoryHeader({
  title,
  badge,
  current,
  subtitle,
  inputPlaceholder = '跳章 / 过滤',
  primaryAction = '同步',
  secondaryAction = '范围',
  chips = [],
  onPrimary,
  onSecondary,
}) {
  return (
    <div
      data-testid="directory-sticky-header"
      className="shrink-0 border-b border-line bg-surface/95 px-3 py-2"
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="min-w-0 flex-1 text-f13 font-semibold text-ink">{title}</div>
        {badge && <span className="shrink-0 rounded-full bg-brand/10 px-2 py-0.5 text-f10 text-brand">{badge}</span>}
      </div>
      <div className="rounded-md border border-line bg-canvas px-2.5 py-2 mb-2">
        <div className="flex items-center justify-between gap-2 text-f12 font-medium text-ink">
          <span className="truncate">当前:{current || '未选择'}</span>
          <span className="shrink-0 text-f10 text-faint">固定</span>
        </div>
        {subtitle && <div className="mt-0.5 truncate text-f10 text-faint">{subtitle}</div>}
      </div>
      <div className="grid grid-cols-[1fr_auto_auto] gap-1.5 mb-2">
        <input
          aria-label={`${title}筛选`}
          className="min-w-0 h-7 rounded-md border border-line bg-canvas px-2 text-f11 text-ink"
          placeholder={inputPlaceholder}
        />
        <button
          type="button"
          onClick={onSecondary}
          className="h-7 rounded-md border border-line bg-canvas px-2 text-f11 text-faint hover:text-ink"
        >
          {secondaryAction}
        </button>
        <button
          type="button"
          onClick={onPrimary}
          className="h-7 rounded-md bg-brand px-2 text-f11 text-brandfg"
        >
          {primaryAction}
        </button>
      </div>
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {chips.map((chip, index) => (
            <span
              key={chip}
              className={`rounded-full px-2 py-0.5 text-f10 ${index === 0 ? 'bg-brand/10 text-brand' : 'bg-soft text-faint'}`}
            >
              {chip}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
