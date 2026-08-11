/**
 * 事件图面板（O18 · 一跳/多跳列表 · 非全屏编辑器）
 */
import { useState } from 'react'
import { Btn } from '../ui.jsx'

export function EventGraphPanel({ work, seq }) {
  const [k, setK] = useState(1)
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    setBusy(true)
    setErr('')
    try {
      const res = await fetch('/api/event-graph', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ k, seed_id: null }),
      })
      if (!res.ok) throw new Error(res.status === 401 ? '请先登录' : `HTTP ${res.status}`)
      setData(await res.json())
    } catch (e) {
      setErr(e?.message || '失败')
    } finally {
      setBusy(false)
    }
  }

  const nodes = data?.multi_hop?.nodes || data?.graph?.nodes || []
  const edges = data?.multi_hop?.edges || []
  const pair = data?.sample_pair

  return (
    <div className="p-3 space-y-2" data-testid="event-graph-panel">
      <div className="flex gap-2 items-center">
        <span className="font-medium text-sm">事件图</span>
        <label className="text-xs">
          k
          <select className="ml-1 border rounded" value={k} onChange={(e) => setK(Number(e.target.value))}>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </select>
        </label>
        <Btn onClick={load} disabled={busy}>{busy ? '…' : '加载'}</Btn>
      </div>
      {err && <div className="text-amber-700 text-xs">{err}</div>}
      {pair?.linked && (
        <div className="text-xs opacity-70">
          样例边：{pair.a} → {pair.b} ({(pair.relations || []).join(',')})
        </div>
      )}
      <div className="text-xs">
        节点 {nodes.length} · 边 {edges.length}
        <ul className="mt-1 max-h-40 overflow-auto">
          {edges.slice(0, 40).map((e, i) => (
            <li key={i}>{e.src} -[{e.rel}]→ {e.dst}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default EventGraphPanel
