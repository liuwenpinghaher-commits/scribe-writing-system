import { atlasEmptyCopy } from '../../lib/atlasReadable.js'

export function AtlasEmptyState({ kind, onRetry }) {
  const copy = atlasEmptyCopy(kind)
  return (
    <div
      data-testid="atlas-empty"
      className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 text-faint px-6 text-center"
    >
      <span className="text-f13 text-ink">{copy.title}</span>
      {copy.body ? <span className="text-f12 max-w-sm leading-relaxed">{copy.body}</span> : null}
      {kind === 'error' && onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 h-7 px-3 rounded-lg border border-line text-f12 hover:border-brand cursor-pointer"
        >重试</button>
      ) : null}
    </div>
  )
}
