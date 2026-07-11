import { Btn } from '../ui.jsx'

export function AsyncState({ state, title, message, onRetry, children }) {
  if (state === 'ready') return children
  const role = state === 'error' ? 'alert' : 'status'

  return (
    <div role={role} className="rounded-lg border border-line bg-surface p-4 text-helper">
      <div className="font-medium text-ink">{title}</div>
      {message && <div className="mt-1 text-muted">{message}</div>}
      {state === 'error' && onRetry && <Btn className="mt-3" onClick={onRetry}>重试</Btn>}
    </div>
  )
}
