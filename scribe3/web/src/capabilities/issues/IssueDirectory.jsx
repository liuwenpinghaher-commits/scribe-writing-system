import { useMemo } from 'react'
import { useIssueLedger } from '../../hooks/useIssueLedger'
import { DirectoryHeader } from '../../layout/DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from '../../layout/DirectoryRow'

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
    <div className={DIR_SHELL}>
      <DirectoryHeader
        title="校验"
        count={issues.length}
        status={
          <span className="text-meta text-faint">{seq != null ? `第 ${seq} 章` : '全书'}</span>
        }
        secondaryActions={[
          {
            label: '本章总览',
            onClick: () => onSelectItem?.({
              id: 'review:summary',
              type: 'review_issue',
              label: '本章总览',
              payload: { title: '本章总览', chapter: seq, reason: '查看本章全部校验命中。' },
            }),
          },
        ]}
      />
      <div data-testid="issue-list" className="flex-1 min-h-0 overflow-auto px-2 py-2">
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
          <div key={severity} className="mb-2">
            <DirectorySectionLabel>{severity}</DirectorySectionLabel>
            <div className="space-y-0.5">
              {items.map((issue) => (
                <DirectoryRow
                  key={issue.id}
                  title={issue.title || issue.id}
                  meta={`第 ${issue.chapter} 章 · ${issue.source}`}
                  onClick={() => onSelectItem?.(toNode(issue))}
                  aria-label={issue.title || issue.id}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
