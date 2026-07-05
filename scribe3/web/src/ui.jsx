import { cn } from './lib/utils'

export function Btn({ variant = 'ghost', size = 'md', icon = false, className, ...p }) {
  const base = 'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors duration-150 cursor-pointer select-none active:scale-[.98] motion-reduce:active:scale-100 disabled:opacity-40 disabled:pointer-events-none disabled:cursor-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40'
  // icon-only:方形、无横向 padding、居中图标(调用处务必传 aria-label / title)
  const sizes = icon
    ? { xs: 'h-6 w-6 rounded-md', sm: 'h-7 w-7', md: 'h-8 w-8' }
    : { xs: 'h-6 px-2 text-f11', sm: 'h-7 px-2.5 text-f12', md: 'h-8 px-3.5 text-f13' }
  const variants = {
    primary: 'bg-brand text-brandfg hover:brightness-110 shadow-sm',
    soft: 'bg-soft text-ink border border-line hover:border-faint/50',
    ghost: 'text-faint hover:bg-soft hover:text-ink',
    danger: 'bg-danger text-white hover:brightness-110',
  }
  return <button className={cn(base, sizes[size], variants[variant], className)} {...p} />
}

// 统一文本输入原语。h-9 rounded-lg border-line bg-canvas + focus:border-brand(:focus 光环由 index.css 全局提供)。
export function Input({ size = 'md', className, ...p }) {
  const sizes = { xs: 'h-6 px-1.5 text-f11', sm: 'h-7 px-2 text-f12', md: 'h-9 px-3 text-f13' }
  return <input className={cn('w-full rounded-lg border border-line bg-canvas text-ink outline-none transition-colors focus:border-brand placeholder:text-faint/60 disabled:opacity-40 disabled:cursor-default', sizes[size], className)} {...p} />
}

// 统一多行输入原语。min-h + resize-y,可选 auto-resize(随内容增高,受 maxRows 约束由样式承担)。
export function Textarea({ className, autoResize = false, ...p }) {
  const onInput = autoResize
    ? (e) => { const el = e.target; el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; p.onInput?.(e) }
    : p.onInput
  return <textarea {...p} onInput={onInput} className={cn('w-full rounded-lg border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors focus:border-brand placeholder:text-faint/60 disabled:opacity-40 disabled:cursor-default', autoResize ? 'resize-none overflow-hidden' : 'resize-y', className)} />
}

export function Card({ className, clickable, ...p }) {
  return <div className={cn('rounded-xl border border-line bg-surface',
    clickable && 'cursor-pointer transition-all duration-150 ease-out hover:border-brand/50 hover:-translate-y-0.5 hover:[box-shadow:var(--shadow-card)]', className)} {...p} />
}

export function Skeleton({ className }) {
  return <div className={cn('skel h-4', className)} />
}

export function SectionTitle({ icon: Icon, children, right }) {
  return (
    <div className="flex items-center gap-2 mb-2.5 mt-1">
      {Icon && <Icon size={13} className="text-faint shrink-0" />}
      <span className="text-f11 font-semibold uppercase tracking-[.08em] text-faint">{children}</span>
      {right != null && <span className="ml-auto text-f11 text-faint tnum">{right}</span>}
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
  return <span className={cn('inline-flex items-center rounded px-1.5 py-px text-f10 font-medium tracking-wide', bg)}>{children}</span>
}
