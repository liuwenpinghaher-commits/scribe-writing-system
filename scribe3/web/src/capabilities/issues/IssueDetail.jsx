export function IssueDetail({ node, onLocate, onFix, onRecheck }) {
  const issue = node?.payload || node || {}
  const range = Array.isArray(issue.range) ? issue.range : [0, 0]
  const fix = () => {
    if (onFix) {
      onFix(issue)
      return
    }
    if (issue.target_node) onLocate?.(issue.target_node)
  }
  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="text-f20 font-semibold text-ink">校验详情</h2>
        </div>
        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-1 text-f14 font-semibold text-ink">{issue.title || node?.label || '校验命中'}</div>
          <div className="mb-3 flex flex-wrap gap-2 text-f11 text-faint">
            {issue.source && <span>{issue.source}</span>}
            {issue.severity && <span>{issue.severity}</span>}
            {issue.chapter != null && <span>第 {issue.chapter} 章</span>}
            <span>{range[0]}-{range[1]}</span>
          </div>
          {issue.reason && <p className="text-f13 leading-7 text-ink">{issue.reason}</p>}
          {issue.suggested_action && (
            <div className="mt-3 rounded-md bg-soft px-3 py-2">
              <div className="mb-1 text-f11 font-semibold text-faint">修复建议</div>
              <p className="text-f12 leading-6 text-fore">{issue.suggested_action}</p>
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={() => issue.target_node && onLocate?.(issue.target_node)}
              className="rounded-md border border-brand/40 px-3 py-1.5 text-f12 text-brand hover:bg-brand/10">
              定位
            </button>
            <button type="button" onClick={fix}
              className="rounded-md border border-line px-3 py-1.5 text-f12 text-ink hover:bg-soft">
              修复
            </button>
            <button type="button" onClick={() => onRecheck?.(issue)}
              className="rounded-md border border-line px-3 py-1.5 text-f12 text-faint hover:text-ink">
              重查
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
