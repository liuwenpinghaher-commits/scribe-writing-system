import { useMemo, useState } from 'react'
import { api } from '../../api'

const SOURCE_ORDER = ['正文', '设定', '素材', '伏笔', '母题']

function toNode(result) {
  return {
    id: result.id,
    type: 'recall_result',
    label: result.label,
    source: result.source,
    excerpt: result.excerpt,
    target_node: result.target_node,
    payload: result,
  }
}

export function SearchDirectory({ onSelectItem }) {
  const [q, setQ] = useState('')
  const [state, setState] = useState({ loading: false, err: '', results: [] })

  const groups = useMemo(() => {
    const map = new Map()
    for (const r of state.results) {
      const key = r.source || r.type || '其他'
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(r)
    }
    return [...map.entries()].sort((a, b) => {
      const ai = SOURCE_ORDER.indexOf(a[0])
      const bi = SOURCE_ORDER.indexOf(b[0])
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi)
    })
  }, [state.results])

  const run = async (e) => {
    e?.preventDefault?.()
    const needle = q.trim()
    if (!needle) return
    setState({ loading: true, err: '', results: [] })
    try {
      const r = await api.search(needle)
      setState({ loading: false, err: '', results: Array.isArray(r?.results) ? r.results : [] })
    } catch (err) {
      setState({ loading: false, err: err?.body?.detail || err?.message || '搜索失败', results: [] })
    }
  }

  return (
    <div className="h-full min-h-0 flex flex-col bg-surface">
      <div data-testid="directory-sticky-header" className="shrink-0 border-b border-line px-3 py-3">
        <div className="mb-2 text-f16 font-semibold text-ink">搜索</div>
        <form onSubmit={run} className="flex gap-1.5">
          <input
            aria-label="全局搜索"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜正文 / 设定 / 素材"
            className="min-w-0 flex-1 rounded-md border border-line bg-canvas px-2 py-1.5 text-f12 text-ink"
          />
          <button type="submit" disabled={state.loading} className="rounded-md bg-brand px-2.5 py-1.5 text-f12 text-brandfg disabled:opacity-50">
            搜索
          </button>
        </form>
        <button
          type="button"
          onClick={() => onSelectItem?.({ id: 'recall:semantic', type: 'recall_result', label: '语义召回', source: '搜索' })}
          className="mt-2 text-f12 text-faint hover:text-ink"
        >
          语义召回
        </button>
      </div>
      <div data-testid="search-results" className="flex-1 min-h-0 overflow-auto px-3 py-2">
        {state.err && <div role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-2 py-1.5 text-f12 text-danger">{state.err}</div>}
        {state.loading && <div className="py-6 text-center text-f12 text-faint">搜索中…</div>}
        {!state.loading && !state.err && state.results.length === 0 && <div className="py-6 text-center text-f12 text-faint">输入关键词后搜索。</div>}
        {groups.map(([source, items]) => (
          <div key={source} className="mb-3">
            <div className="mb-1 text-f11 font-semibold text-faint">{source}</div>
            <div className="space-y-1">
              {items.map((r) => (
                <button key={r.id} type="button" onClick={() => onSelectItem?.(toNode(r))}
                  className="w-full rounded-md px-2 py-2 text-left hover:bg-soft">
                  <div className="truncate text-f13 text-ink">{r.label}</div>
                  {r.excerpt && <div className="mt-0.5 line-clamp-2 text-f11 text-faint">{r.excerpt}</div>}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
