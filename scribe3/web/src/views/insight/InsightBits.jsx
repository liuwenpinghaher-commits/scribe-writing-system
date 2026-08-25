export function Metric({ icon: Icon, label, value, sub, tone = 'brand' }) {
  const c = { brand: 'text-brand', fore: 'text-fore', danger: 'text-danger', ok: 'text-ok' }[tone]
  return (
    <div className="py-2 pr-2">
      <div className="flex items-center gap-1.5 text-faint text-meta uppercase tracking-wider mb-1"><Icon size={13} />{label}</div>
      <div className={`text-2xl font-semibold tnum ${c}`}>{value}</div>
      {sub && <div className="text-meta text-faint mt-0.5">{sub}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-4 py-3 text-f13 text-danger">
      <div>{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 inline-flex rounded-md border border-danger/30 px-2.5 py-1 text-f12 hover:bg-danger/10 transition-colors cursor-pointer">
          重试
        </button>
      )}
    </div>
  )
}
