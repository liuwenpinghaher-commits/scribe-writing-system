import {
  chiefSendHint,
  chiefSendKind,
  seedOrigin,
  seedOriginLabel,
} from '../../lib/chiefReadable.js'

export function ChiefStatusStrip({ label, input, pending, onJumpPending }) {
  const kind = chiefSendKind(input)
  const hint = chiefSendHint(kind)
  const origin = seedOriginLabel(seedOrigin(input))
  return (
    <div
      data-testid="chief-status-strip"
      className="shrink-0 px-3 py-1.5 border-t border-line/60 bg-surface flex items-center gap-2 min-w-0 text-meta"
    >
      <span className="truncate text-ink" data-testid="chief-status-label">{label || '未选中'}</span>
      {origin ? <span className="shrink-0 text-brand" data-testid="chief-seed-origin">{origin}</span> : null}
      {hint ? <span className="shrink-0 text-faint" data-testid="chief-send-hint">{hint}</span> : null}
      {pending ? (
        <button
          type="button"
          data-testid="chief-jump-pending"
          onClick={onJumpPending}
          className="ml-auto shrink-0 text-brand hover:underline cursor-pointer"
        >
          去批
        </button>
      ) : <span className="ml-auto" />}
    </div>
  )
}
