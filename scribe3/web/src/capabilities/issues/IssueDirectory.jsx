import { useMemo } from 'react'
import { useIssueLedger } from '../../hooks/useIssueLedger'

function toNode(issue) {
  return {
    id: issue.id,
    type: 'review_issue',
    label: issue.title || issue.id,
    payload: issue,
    target_node: issue.target_node,
  }
}

export function IssueDirectory({ seq, onSelectItem }) {
  const { loading, err, issues, degraded, reload } = useIssueLedger(seq)

  const groups = useMemo(() => {
    const map = new Map()
    for (const issue of issues) {
      const key = issue.severity || 'warning'
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(issue)
    }
    return [...map.entries()]
  }, [issues])

  return (
    <div className="h-full min-h-0 flex flex-col bg-surface">
        <div data-testid="directory-sticky-header" className="shrink-0 border-b border-line px-3 py-3">
          <div className="mb-1 text-f16 font-semibold text-ink">校验</div>
        <div className="text-f12 text-faint">{seq != null ? `第 ${seq} 章` : '全书'} · {issues.length} 项</div>
        <button
          type="button"
          onClick={() => onSelectItem?.({ id: 'review:summary', type: 'review_issue', label: '本章总览', payload: { title: '本章总览', chapter: seq, reason: '查看本章全部校验命中。' } })}
          className="mt-2 text-f12 text-faint hover:text-ink"
        >
          本章总览
        </button>
      </div>
      <div data-testid="issue-list" className="flex-1 min-h-0 overflow-auto px-3 py-2">
        {err && (
          <div role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-2 py-1.5 text-f12 text-danger">
            <div>{err}</div>
            <button type="button" onClick={reload} className="mt-1 text-meta underline">重试</button>
          </div>
        )}
        {loading && <div className="py-6 text-center text-f12 text-faint">加载校验台账…</div>}
        {degraded.length > 0 && (
          <div className="mb-2 rounded-md bg-danger/5 px-2 py-1.5 text-meta text-danger">
            <div>部分来源降级,清单可能不全。</div>
            <ul className="mt-1 space-y-0.5">
              {degraded.map((d, i) => (
                <li key={`${d.source}:${d.chapter ?? ''}:${i}`}>
                  {d.source}{d.chapter != null ? ` · 第 ${d.chapter} 章` : ''}{d.reason ? `: ${d.reason}` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
        {!loading && !err && issues.length === 0 && <div className="py-6 text-center text-f12 text-faint">暂无校验命中。</div>}
        {groups.map(([severity, items]) => (
          <div key={severity} className="mb-3">
            <div className="mb-1 text-meta font-semibold text-faint">{severity}</div>
            <div className="space-y-1">
              {items.map((issue) => (
                <button key={issue.id} type="button" onClick={() => onSelectItem?.(toNode(issue))}
                  className="w-full rounded-md px-2 py-2 text-left hover:bg-soft">
                  <div className="truncate text-f13 text-ink">{issue.title || issue.id}</div>
                  <div className="mt-0.5 text-meta text-faint">第 {issue.chapter} 章 · {issue.source}</div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
