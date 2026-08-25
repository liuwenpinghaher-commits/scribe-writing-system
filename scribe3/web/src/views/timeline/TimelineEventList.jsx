import { List } from 'lucide-react'
import { groupTimelineItems } from '../../lib/timelineReadable.js'

export function TimelineEventList({ items, selectedId, onPick }) {
  const groups = groupTimelineItems(items)
  const total = groups.reduce((n, g) => n + g.rows.length, 0)
  if (!total) return null
  return (
    <div
      role="region"
      aria-label="时间线事件列表"
      data-testid="timeline-event-list"
      className="w-56 shrink-0 border-r border-line bg-surface min-h-0 overflow-y-auto overscroll-contain hidden md:block"
    >
      <div className="sticky top-0 z-[1] bg-surface/95 backdrop-blur px-3 py-2 border-b border-line flex items-center gap-1.5 text-meta font-medium text-faint">
        <List size={12} />何时 · {total}
      </div>
      {groups.map((g) => (
        <div key={g.chapter || '0'}>
          <div className="px-3 pt-2 pb-1 text-meta text-faint tnum">
            {g.chapter ? `第${g.chapter}章` : '未标章'}
          </div>
          <ul className="pb-1">
            {g.rows.map((row) => {
              const id = `${row.cat}:${row.raw.id}`
              const on = selectedId === id || selectedId === row.raw.id
              return (
                <li key={id}>
                  <button
                    type="button"
                    data-testid="timeline-list-pick"
                    onClick={() => onPick?.(row.raw, row.cat)}
                    className={`w-full text-left px-3 py-1.5 text-f12 text-ink hover:bg-soft/60 flex items-center gap-1.5 transition-colors cursor-pointer ${on ? 'bg-soft' : ''}`}
                  >
                    <span className="truncate">{row.label}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </div>
  )
}
