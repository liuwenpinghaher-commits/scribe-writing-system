/**
 * 故事线中枢（GAP-16/17/19）
 * - recharts 情绪曲线（-5…+5）与技法对标
 * - 可编辑 storyline 实体 + 关联章节
 * 不宣称文学分。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, BarChart, Bar,
} from 'recharts'
import { api } from '../api'
import { Btn } from '../ui.jsx'

async function fetchJson(path) {
  const base = (typeof api.base === 'string' ? api.base : '/api')
  const r = await fetch(`${base}${path}`, { credentials: 'include' })
  if (!r.ok) throw new Error(r.status === 401 ? '请先登录' : `${path} ${r.status}`)
  return r.json()
}

async function postJson(path, body) {
  const base = (typeof api.base === 'string' ? api.base : '/api')
  const r = await fetch(`${base}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  if (!r.ok) throw new Error(`${path} ${r.status}`)
  return r.json()
}

export function StorylineHub({ work }) {
  const [gantt, setGantt] = useState(null)
  const [curve, setCurve] = useState(null)
  const [lines, setLines] = useState([])
  const [align, setAlign] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [linkSeq, setLinkSeq] = useState('')
  const [activeId, setActiveId] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setErr('')
    Promise.all([
      fetchJson('/storyline/gantt').catch(() => null),
      fetchJson('/storyline/emotion-curve').catch(() => null),
      fetchJson('/storyline/lines').catch(() => ({ storylines: [] })),
      fetchJson('/storyline/craft-align').catch(() => null),
    ])
      .then(([g, e, l, a]) => {
        if (g) setGantt(g)
        if (e) setCurve(e)
        setLines(l?.storylines || [])
        setAlign(a?.align || e?.craft_align || null)
      })
      .catch((ex) => setErr(ex?.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [work])

  useEffect(() => { load() }, [load])

  const rows = gantt?.rows || []
  const chartData = useMemo(() => {
    const pts = curve?.points || []
    return pts.map((p) => ({
      seq: p.seq,
      emotion: typeof p.emotion === 'number' ? p.emotion : ((p.tension || 0.5) - 0.5) * 10,
      label: p.label,
    }))
  }, [curve])

  const idealOverlay = useMemo(() => {
    const ideal = align?.ideal_resampled || []
    if (!ideal.length || !chartData.length) return []
    return chartData.map((d, i) => ({
      seq: d.seq,
      emotion: d.emotion,
      ideal: ideal[Math.min(i, ideal.length - 1)] ?? 0,
    }))
  }, [align, chartData])

  const dimBars = useMemo(() => {
    const dims = align?.core_dimensions || []
    return dims.map((d) => ({
      key: d.key,
      label: d.label || d.key,
      score: Number(d.score) || 0,
    }))
  }, [align])

  const onCreate = async () => {
    try {
      await postJson('/storyline/lines', { title: title || '新故事线', work })
      setTitle('')
      load()
    } catch (ex) {
      setErr(ex?.message || '创建失败')
    }
  }

  const onLink = async () => {
    if (!activeId || !linkSeq) return
    try {
      await postJson(`/storyline/lines/${activeId}/link`, { seq: Number(linkSeq), work })
      setLinkSeq('')
      load()
    } catch (ex) {
      setErr(ex?.message || '关联失败')
    }
  }

  return (
    <div className="p-4 space-y-4" data-testid="storyline-hub">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">故事线（advisory · recharts）</h2>
        <Btn onClick={load} disabled={loading}>{loading ? '…' : '刷新'}</Btn>
      </div>
      <p className="text-sm opacity-70">
        情绪标尺 -5…+5；技法 DTW 对标对接 CORE_DIMENSIONS。非文学评分。
      </p>
      {err && <div className="text-amber-700 text-sm" data-testid="storyline-err">{err}</div>}

      <section data-testid="storyline-entities">
        <h3 className="font-medium mb-2">故事线实体（可编辑）</h3>
        <div className="flex gap-2 mb-2">
          <input
            className="border px-2 py-1 text-sm flex-1"
            placeholder="新故事线标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            data-testid="storyline-title-input"
          />
          <Btn onClick={onCreate} data-testid="storyline-create">创建</Btn>
        </div>
        <ul className="text-sm space-y-1">
          {lines.map((sl) => (
            <li
              key={sl.id}
              className={`border-b border-black/5 py-1 cursor-pointer ${activeId === sl.id ? 'bg-indigo-50' : ''}`}
              onClick={() => setActiveId(sl.id)}
              data-testid={`storyline-item-${sl.id}`}
            >
              <span className="font-medium">{sl.title}</span>
              <span className="opacity-50 ml-2">{sl.arc_kind}</span>
              <span className="opacity-60 ml-2">章:{(sl.chapter_seqs || []).join(',') || '—'}</span>
              {sl.persisted && <span className="ml-2 text-xs text-green-700">DB</span>}
            </li>
          ))}
          {!lines.length && !loading && <li className="opacity-50">暂无故事线实体</li>}
        </ul>
        <div className="flex gap-2 mt-2">
          <input
            className="border px-2 py-1 text-sm w-24"
            placeholder="章号"
            value={linkSeq}
            onChange={(e) => setLinkSeq(e.target.value)}
            data-testid="storyline-link-seq"
          />
          <Btn onClick={onLink} disabled={!activeId} data-testid="storyline-link">关联到选中线</Btn>
        </div>
      </section>

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

      <section data-testid="emotion-chart">
        <h3 className="font-medium mb-2">情绪曲线（-5…+5 · recharts）</h3>
        <div className="h-56 w-full" data-testid="emotion-recharts">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={idealOverlay.length ? idealOverlay : chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="seq" />
              <YAxis domain={[-5, 5]} />
              <ReferenceLine y={0} stroke="#999" />
              <Tooltip />
              <Line type="monotone" dataKey="emotion" stroke="#6366f1" name="情绪" dot />
              {idealOverlay.length > 0 && (
                <Line type="monotone" dataKey="ideal" stroke="#f59e0b" name="理想" strokeDasharray="4 4" dot={false} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
        {curve?.disclaimer && (
          <p className="text-xs opacity-60 mt-1">{curve.disclaimer}</p>
        )}
      </section>

      <section data-testid="craft-align">
        <h3 className="font-medium mb-2">技法标尺对标（DTW + CORE_DIMENSIONS）</h3>
        {align ? (
          <div className="text-sm space-y-2">
            <div>DTW 距离：{align.dtw_distance} · 相似度：{align.similarity}</div>
            <div className="opacity-60 text-xs">ideal={align.ideal_name || 'qichengzhuanhe_v0'} · {align.dimension_ssot || ''}</div>
            {dimBars.length > 0 && (
              <div className="h-40 w-full" data-testid="dimension-bars">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dimBars}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="key" hide />
                    <YAxis domain={[0, 1]} />
                    <Tooltip />
                    <Bar dataKey="score" fill="#818cf8" name="轴分" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm opacity-50">暂无对标数据</div>
        )}
      </section>
    </div>
  )
}

export default StorylineHub
