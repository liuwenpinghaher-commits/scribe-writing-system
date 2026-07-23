import { cn } from '../lib/utils'

/** 栏2 目录行：统一选中/hover 密度（标题 + 右侧 meta，默认不强制双行副文案） */
export const DIR_ROW =
  'w-full min-h-8 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-md px-2 py-1.5 text-left text-helper transition-colors cursor-pointer'
export const DIR_ROW_IDLE = 'text-ink hover:bg-soft/70'
export const DIR_ROW_ACTIVE = 'bg-brand/10 text-brand font-medium'
export const DIR_SECTION =
  'px-2 pb-1 pt-2 text-meta font-semibold uppercase tracking-wide text-faint'
export const DIR_SHELL = 'h-full min-h-0 flex flex-col bg-canvas'

/**
 * @param {object} props
 * @param {string} props.title
 * @param {React.ReactNode} [props.meta] 右侧 meta（计数/来源/阶段）
 * @param {string} [props.sub] 副行；默认不渲染，仅传入时显示
 * @param {boolean} [props.active]
 * @param {() => void} [props.onClick]
 * @param {string} [props.className]
 * @param {React.ReactNode} [props.leading] 左侧缩进/图标槽
 * @param {object} [props.style]
 * @param {string} [props['aria-label']]
 * @param {string} [props['data-testid']]
 */
export function DirectoryRow({
  title,
  meta,
  sub,
  active = false,
  onClick,
  className,
  leading,
  style,
  'aria-label': ariaLabel,
  'data-testid': testId,
  as: Comp = 'button',
  type = 'button',
  children,
  ...rest
}) {
  return (
    <Comp
      type={Comp === 'button' ? type : undefined}
      aria-label={ariaLabel || (typeof title === 'string' ? title : undefined)}
      data-testid={testId}
      onClick={onClick}
      style={style}
      className={cn(DIR_ROW, active ? DIR_ROW_ACTIVE : DIR_ROW_IDLE, className)}
      {...rest}
    >
      <span className="min-w-0 flex items-center gap-1.5">
        {leading}
        <span className="min-w-0 flex flex-col gap-0.5">
          <span className="min-w-0 truncate text-helper leading-5">{title}</span>
          {sub ? <span className="min-w-0 truncate text-meta leading-4 text-faint">{sub}</span> : null}
        </span>
      </span>
      {meta != null && meta !== '' ? (
        <span className="shrink-0 text-meta text-faint tnum tabular-nums whitespace-nowrap">{meta}</span>
      ) : null}
      {children}
    </Comp>
  )
}

export function DirectorySectionLabel({ children }) {
  return <div className={DIR_SECTION}>{children}</div>
}
