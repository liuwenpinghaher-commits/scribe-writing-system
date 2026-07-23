import { cn } from './lib/utils'

export function Btn({ variant = 'ghost', size = 'md', icon = false, className, ...p }) {
  // 全局圆角收紧：md(6px) 替代原 xl(12px)；whitespace-nowrap 防窄栏中文竖排
  const base = 'inline-flex items-center justify-center gap-1.5 rounded-md font-medium whitespace-nowrap transition-all duration-150 cursor-pointer select-none active:scale-[.98] motion-reduce:active:scale-100 disabled:opacity-40 disabled:pointer-events-none disabled:cursor-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40'
  // icon-only:方形、无横向 padding、居中图标(调用处务必传 aria-label / title)
  const sizes = icon
    ? { xs: 'h-8 w-8 rounded-md', sm: 'h-8 w-8 rounded-md', md: 'h-9 w-9 rounded-md' }
    : { xs: 'h-[28px] px-2 text-meta', sm: 'h-8 px-2.5 text-helper', md: 'h-9 px-3 text-body font-medium' }
  const variants = {
    primary: 'bg-brand text-brandfg hover:brightness-110 shadow-sm',
    soft: 'bg-soft text-ink hover:bg-soft/80',
    ghost: 'text-faint hover:bg-soft hover:text-ink',
    danger: 'bg-danger text-white hover:brightness-110',
  }
  return <button className={cn(base, sizes[size], variants[variant], className)} {...p} />
}

// 统一文本输入原语。
// variant=ghost(默认,Notion):无常驻重框,hover/focus 才显边；bordered:表单/新建等必须常显场景。
export function Input({ size = 'md', variant = 'ghost', className, ...p }) {
  const sizes = { xs: 'h-6 px-1.5 text-meta', sm: 'h-7 px-2 text-f12', md: 'h-9 px-3 text-f13' }
  const variants = {
    ghost: 'border border-transparent bg-transparent hover:bg-soft/60 focus:border-brand/40 focus:bg-surface',
    bordered: 'border border-line/80 bg-soft/40 focus:border-brand/50 focus:bg-surface',
  }
  return <input className={cn('w-full rounded-md text-ink outline-none transition-colors placeholder:text-faint/60 disabled:opacity-40 disabled:cursor-default', sizes[size], variants[variant] || variants.ghost, className)} {...p} />
}

// 统一多行输入原语。min-h + resize-y,可选 auto-resize。variant 语义同 Input。
export function Textarea({ className, autoResize = false, variant = 'ghost', ...p }) {
  const onInput = autoResize
    ? (e) => { const el = e.target; el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; p.onInput?.(e) }
    : p.onInput
  const variants = {
    ghost: 'border border-transparent bg-transparent hover:bg-soft/60 focus:border-brand/40 focus:bg-surface',
    bordered: 'border border-line/80 bg-soft/40 focus:border-brand/50 focus:bg-surface',
  }
  return <textarea {...p} onInput={onInput} className={cn('w-full rounded-md px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors placeholder:text-faint/60 disabled:opacity-40 disabled:cursor-default', variants[variant] || variants.ghost, autoResize ? 'resize-none overflow-hidden' : 'resize-y', className)} />
}

// Card:Upstream 默认白面;elevated 用软阴影抬升(少硬边)。clickable 轻上浮。
export function Card({ className, clickable, elevated = false, ...p }) {
  return <div className={cn('rounded-[var(--radius-pane)] bg-surface',
    elevated ? '[box-shadow:var(--shadow-panel)]' : '',
    clickable && 'cursor-pointer transition-all duration-150 ease-out hover:-translate-y-0.5 hover:[box-shadow:var(--shadow-card)]', className)} {...p} />
}

export function Skeleton({ className }) {
  return <div className={cn('skel h-4', className)} />
}

export function SectionTitle({ icon: Icon, children, right }) {
  return (
    <div className="flex items-center gap-2 mb-2.5 mt-1">
      {Icon && <Icon size={13} className="text-faint shrink-0" />}
      <span className="text-meta font-semibold uppercase tracking-[.08em] text-faint">{children}</span>
      {/* right 区不强制 text-faint:可放计数或「让主编…」CTA */}
      {right != null && <span className="ml-auto text-meta tnum shrink-0">{right}</span>}
    </div>
  )
}

export function Empty({ children }) {
  return <div className="text-f13 text-faint/70 py-1.5 italic">{children}</div>
}

const TONES = {
  faint: 'text-faint', ink: 'text-ink', danger: 'text-danger', ok: 'text-ok',
  irony: 'text-irony', fore: 'text-fore', secret: 'text-secret', brand: 'text-brand',
}

export function Row({ tone = 'ink', icon: Icon, className, children, ...p }) {
  return (
    <div className={cn('flex items-start gap-2 text-f13 leading-snug py-1.5 border-b border-line/50 last:border-0', TONES[tone], className)} {...p}>
      {Icon && <Icon size={13} className="mt-[3px] shrink-0 opacity-80" />}
      <span className="min-w-0">{children}</span>
    </div>
  )
}

export function Tag({ tone = 'faint', children }) {
  const bg = {
    secret: 'bg-secret/12 text-secret', fore: 'bg-fore/12 text-fore', ok: 'bg-ok/12 text-ok',
    danger: 'bg-danger/12 text-danger', faint: 'bg-soft text-faint', brand: 'bg-brand/12 text-brand',
  }[tone]
  return <span className={cn('inline-flex items-center rounded px-1.5 py-px text-meta font-medium tracking-wide', bg)}>{children}</span>
}
