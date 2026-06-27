import { cn } from '../lib/utils'

const TONES = {
  ok:     'text-ok bg-ok/10 border-ok/20',
  warn:   'text-warn bg-warn/10 border-warn/20',
  danger: 'text-danger bg-danger/10 border-danger/20',
  faint:  'text-faint bg-soft border-line',
}

export function Chip({ tone = 'faint', icon: Icon, children, className, ...p }) {
  return (
    <button type="button"
      className={cn(
        'inline-flex items-center gap-1 h-6 px-2 rounded-lg border text-[11px] whitespace-nowrap cursor-pointer transition-colors active:scale-[.98] focus-visible:ring-2 focus-visible:ring-brand/40 motion-reduce:active:scale-100',
        TONES[tone],
        className
      )}
      {...p}>
      {Icon && <Icon size={12} />}{children}
    </button>
  )
}

export function IconButton({ icon: Icon, label, active, className, ...p }) {
  return (
    <button type="button" aria-label={label} title={label}
      className={cn(
        'w-8 h-8 rounded-lg inline-flex items-center justify-center transition-colors cursor-pointer active:scale-[.95] focus-visible:ring-2 focus-visible:ring-brand/40 motion-reduce:active:scale-100',
        active ? 'bg-soft text-brand ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink',
        className
      )}
      {...p}>
      <Icon size={16} />
    </button>
  )
}
