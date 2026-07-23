export function SearchDetail({ node, onOpenTarget }) {
  const payload = node?.payload || node || {}
  const target = node?.target_node || payload.target_node
  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="type-section text-ink">召回详情</h2>
        </div>
        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-1 text-f14 font-semibold text-ink">{payload.label || node?.label || '搜索结果'}</div>
          <div className="mb-3 text-meta text-faint">{payload.source || '搜索'}{payload.chapter ? ` · 第 ${payload.chapter} 章` : ''}</div>
          {payload.excerpt
            ? <p className="text-f13 leading-7 text-ink">{payload.excerpt}</p>
            : <p className="text-f13 leading-7 text-faint">暂无摘录。请在左侧先搜索，再点选具体结果。</p>}
          {/* Task 10:按钮必须同时有真实目标和真实 handler 才渲染,不留点了没反应的假按钮 */}
          {target && onOpenTarget && (
            <button type="button" onClick={() => onOpenTarget(target)}
              className="mt-4 rounded-md border border-brand/40 px-3 py-1.5 text-f12 text-brand hover:bg-brand/10">
              打开目标
            </button>
          )}
        </section>
      </div>
    </div>
  )
}
