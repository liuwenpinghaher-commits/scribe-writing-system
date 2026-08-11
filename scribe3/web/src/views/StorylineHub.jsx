/**
 * 故事线中枢（O30/O31/O33 薄 UI · 只读 API）
 * 不宣称文学分；数据失败 soft 提示。
 */
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { Btn } from '../ui.jsx'

export function StorylineHub({ work }) {
  const [gantt, setGantt] = useState(null)
  const [curve, setCurve] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    setErr('')
    Promise.all([
      (typeof api.storylineGantt === 'function' ? api.storylineGantt() : api.get?.('/storyline/gantt')).catch(() => null),
      (typeof api.storylineEmotion === 'function' ? api.storylineEmotion() : api.get?.('/storyline/emotion-curve')).catch(() => null),
    ])
      .then(async () => {
        // 兼容 api.js 形态：优先命名方法，否则 fetch
        const base = (typeof api.base === 'string' ? api.base : '/api')
        const h = await fetch(`${base}/storyline/gantt`, { credentials: 'include' })
        const e = await fetch(`${base}/storyline/emotion-curve`, { credentials: 'include' })
        if (!h.ok) throw new Error(h.status === 401 ? '请先登录' : `gantt ${h.status}`)
        if (!e.ok) throw new Error(`emotion ${e.status}`)
        setGantt(await h.json())
        setCurve(await e.json())
      })
      .catch((ex) => setErr(ex?.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [work])

  useEffect(() => { load() }, [load])

  const rows = gantt?.rows || []
  const points = curve?.points || []

  return (
    <div className="p-4 space-y-4" data-testid="storyline-hub">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">故事线（advisory）</h2>
        <Btn onClick={load} disabled={loading}>{loading ? '…' : '刷新'}</Btn>
      </div>
      <p className="text-sm opacity-70">
        Gantt / 张力曲线为启发式，非文学评分，禁止当作质量达标证据。
      </p>
      {err && <div className="text-amber-700 text-sm">{err}</div>}
      <section>
        <h3 className="font-medium mb-2">章条 Gantt</h3>
        <div className="space-y-1">
          {rows.map((r) => (
            <div key={r.seq} className="flex gap-2 text-sm border-b border-black/5 py-1">
              <span className="w-12">#{r.seq}</span>
              <span className="flex-1 truncate">{r.title}</span>
              <span className="opacity-60">{r.phase}</span>
              <span className="opacity-50">stakes:{r.stakes_hint}</span>
            </div>
          ))}
          {!rows.length && !loading && <div className="text-sm opacity-50">暂无章节</div>}
        </div>
      </section>
      <section>
        <h3 className="font-medium mb-2">张力曲线</h3>
        <div className="flex items-end gap-1 h-24">
          {points.map((p) => (
            <div
              key={p.seq}
              title={`#${p.seq} ${p.label} ${p.tension}`}
              className="flex-1 bg-indigo-400/70 min-w-[4px]"
              style={{ height: `${Math.max(8, (p.tension || 0) * 100)}%` }}
            />
          ))}
        </div>
        {curve?.disclaimer && (
          <p className="text-xs opacity-60 mt-1">{curve.disclaimer}</p>
        )}
      </section>
    </div>
  )
}

export default StorylineHub
