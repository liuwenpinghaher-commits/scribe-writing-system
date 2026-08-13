/**
 * 管理台 · 运行链路（时间线主界面）。
 * 一次写/存/宣称一条链；点一步看结构化全字段。不回传提示词。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'

const inputCls = 'px-2.5 py-1.5 rounded-md border border-line bg-surface text-f13 outline-none focus:ring-2 focus:ring-brand'
const btnCls = 'px-2.5 py-1.5 rounded-md text-f12 border border-line hover:bg-soft cursor-pointer'
const btnPrimary = 'px-2.5 py-1.5 rounded-md text-f12 bg-brand text-white hover:opacity-90 cursor-pointer'

const KIND_LABEL = { write: '写', save: '存', claim: '宣称' }
const STATUS_LABEL = {
  in_progress: '进行中', ok: '完成', failed: '失败', abandoned: '放弃',
  running: '进行中', empty: '空', dropped: '裁光', skipped: '跳过', present: '有',
}

function fmtWhen(v) {
  if (v == null || v === '') return '—'
  if (typeof v === 'object') v = v.datetime || v.dt || v.value || ''
  if (typeof v === 'number') {
    const ms = v > 1e12 ? v : v * 1000
    const d = new Date(ms)
    return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString()
  }
  const d = new Date(String(v))
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString()
}

function fmtMs(ms) {
  if (ms == null || ms === '') return '—'
  const n = Number(ms)
  if (!Number.isFinite(n)) return '—'
  if (n >= 1000) return `${(n / 1000).toFixed(1)}s`
  return `${Math.round(n)}ms`
}

function Err({ e }) {
  if (!e) return null
  const msg = e?.body?.detail || e?.message || String(e)
  return (
    <div className="text-f12 text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-md px-3 py-2 mb-3">
      {msg}
    </div>
  )
}

function statusChip(status, verdict) {
  const red = verdict === 'red' || status === 'failed' || status === 'empty'
  const run = status === 'in_progress' || status === 'running'
  return (
    <span className={`px-1.5 py-0.5 rounded text-f12 ${
      run ? 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
        : red ? 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'
          : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
    }`}>
      {STATUS_LABEL[status] || status || (red ? '该进未进' : '完成')}
    </span>
  )
}

export function RunLogsPage({ defaultWork = '' }) {
  const [works, setWorks] = useState([])
  const [work, setWork] = useState(defaultWork || '')
  const [kind, setKind] = useState('')
  const [status, setStatus] = useState('')
  const [chapter, setChapter] = useState('')
  const [q, setQ] = useState('')
  const [stepKey, setStepKey] = useState('')
  const [items, setItems] = useState([])
  const [sel, setSel] = useState(null)
  const [pick, setPick] = useState(null)
  const [tab, setTab] = useState('logs')
  const [logs, setLogs] = useState([])
  const [onlyBad, setOnlyBad] = useState(false)
  const [layerOrder, setLayerOrder] = useState(false)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    const apply = (rows) => {
      if (cancelled) return
      setWorks(rows)
      setWork((cur) => {
        if (cur) return cur
        if (defaultWork) return defaultWork
        const g = typeof api.getWork === 'function' ? api.getWork() : ''
        if (g && rows.some((w) => w.slug === g)) return g
        return rows[0]?.slug || ''
      })
    }
    api.adminWorks({ archived: 'active', limit: 200 })
      .then((r) => apply(r.items || []))
      .catch(() => {
        api.works().then((rows) => apply(Array.isArray(rows) ? rows : [])).catch((e) => {
          if (!cancelled) setError(e)
        })
      })
    return () => { cancelled = true }
  }, [defaultWork])

  useEffect(() => { if (defaultWork) setWork(defaultWork) }, [defaultWork])

  const loadList = useCallback(async () => {
    if (!work) { setItems([]); return }
    setBusy(true)
    setError(null)
    try {
      if (stepKey) {
        const r = await api.pipelineSpans({
          step_key: stepKey,
          chapter: chapter !== '' ? Number(chapter) : undefined,
          limit: 50,
        }, work)
        setItems(r.chains || [])
      } else {
        const query = { limit: 20 }
        if (kind) query.kind = kind
        if (status) query.status = status
        if (chapter !== '' && Number.isFinite(Number(chapter))) query.chapter = Number(chapter)
        if (q.trim()) query.q = q.trim()
        const r = await api.pipelineTraces(query, work)
        setItems(r.items || [])
      }
    } catch (e) {
      setError(e)
      setItems([])
    } finally {
      setBusy(false)
    }
  }, [work, kind, status, chapter, q, stepKey])

  useEffect(() => { loadList() }, [loadList])

  const openChain = async (traceId) => {
    if (!work || !traceId) return
    setBusy(true)
    setError(null)
    try {
      const card = await api.pipelineTrace(traceId, work)
      setSel(card)
      setPick(null)
      setTab('logs')
      try {
        const lr = await api.pipelineLogs({ trace_id: traceId, limit: 400 }, work)
        setLogs(lr.items || [])
      } catch {
        setLogs([])
      }
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const highlight = useMemo(() => {
    if (!sel || !pick) return new Set()
    const spans = sel.spans || []
    const byParent = {}
    const byId = {}
    spans.forEach((s) => {
      byId[s.span_id] = s
      if (s.parent_span_id) {
        byParent[s.parent_span_id] = byParent[s.parent_span_id] || []
        byParent[s.parent_span_id].push(s.span_id)
      }
    })
    const out = new Set([pick.span_id])
    let cur = pick
    while (cur && cur.parent_span_id) {
      out.add(cur.parent_span_id)
      cur = byId[cur.parent_span_id]
    }
    const stack = [...(byParent[pick.span_id] || [])]
    while (stack.length) {
      const id = stack.pop()
      if (out.has(id)) continue
      out.add(id)
      ;(byParent[id] || []).forEach((c) => stack.push(c))
    }
    return out
  }, [sel, pick])

  const spans = useMemo(() => {
    let all = Array.isArray(sel?.spans) ? [...sel.spans] : []
    if (onlyBad) {
      all = all.filter((s) => s.verdict === 'red' || s.status === 'failed' || s.status === 'empty' || s.status === 'dropped')
    }
    if (layerOrder) {
      const order = ['guard', 'assemble', 'compile', 'budget', 'llm', 'tool', 'persist', 'save', 'claim']
      all.sort((a, b) => order.indexOf(a.layer) - order.indexOf(b.layer))
    }
    return all
  }, [sel, onlyBad, layerOrder])

  return (
    <div className="space-y-3" data-testid="run-logs-page">
      <div>
        <div className="text-f14 font-semibold">运行链路</div>
        <div className="text-f12 text-faint mt-0.5">
          系统运行分析：每一步叫什么、从哪来、算了什么、产出结构、耗时、和上下游怎么连。不是账号审计，不展示提示词。
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-end">
        <label className="block text-f12">
          <span className="text-faint mb-1 block">书</span>
          <select className={inputCls} data-testid="run-logs-work" value={work}
            onChange={(e) => { setSel(null); setWork(e.target.value) }}>
            <option value="">选择书籍</option>
            {works.map((w) => (
              <option key={w.slug} value={w.slug}>{w.title || w.slug}</option>
            ))}
          </select>
        </label>
        <label className="block text-f12">
          <span className="text-faint mb-1 block">类型</span>
          <select className={inputCls} value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">全部</option>
            <option value="write">写</option>
            <option value="save">存</option>
            <option value="claim">宣称</option>
          </select>
        </label>
        <label className="block text-f12">
          <span className="text-faint mb-1 block">状态</span>
          <select className={inputCls} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">全部</option>
            <option value="in_progress">进行中</option>
            <option value="ok">完成</option>
            <option value="failed">失败</option>
          </select>
        </label>
        <label className="block text-f12">
          <span className="text-faint mb-1 block">章</span>
          <input className={`${inputCls} w-20`} value={chapter}
            onChange={(e) => setChapter(e.target.value.replace(/[^\d]/g, ''))} placeholder="全部" />
        </label>
        <label className="block text-f12">
          <span className="text-faint mb-1 block">步骤键</span>
          <input className={`${inputCls} w-48`} value={stepKey}
            onChange={(e) => setStepKey(e.target.value)} placeholder="assemble.seg.story_ember" />
        </label>
        <label className="block text-f12 grow">
          <span className="text-faint mb-1 block">搜索 trace / request / outcome</span>
          <input className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <button type="button" className={btnCls} onClick={loadList} disabled={busy || !work}>
          {busy ? '加载中…' : '刷新'}
        </button>
      </div>

      <Err e={error} />

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.2fr)] gap-4 items-start">
        <div className="rounded-lg border border-line overflow-hidden bg-surface">
          <div className="px-3 py-2 text-f12 text-faint border-b border-line">时间线列表</div>
          <ul data-testid="run-logs-timeline">
            {items.map((it) => (
              <li
                key={it.trace_id}
                data-testid="run-logs-row"
                className={`px-3 py-2 border-t border-line cursor-pointer hover:bg-soft/50 ${
                  sel?.trace_id === it.trace_id ? 'bg-soft/70' : ''
                } ${it.status === 'in_progress' ? 'border-l-2 border-l-amber-500' : ''}`}
                onClick={() => openChain(it.trace_id)}
              >
                <div className="flex items-center gap-2 text-f12">
                  <span className="text-faint whitespace-nowrap">{fmtWhen(it.started_at)}</span>
                  <span>第 {it.chapter ?? '—'} 章 · {KIND_LABEL[it.kind] || it.kind}</span>
                  {statusChip(it.status)}
                </div>
                <div className="text-f13 mt-0.5">{it.headline || '—'}</div>
                <div className="text-f12 text-faint">{fmtMs(it.duration_ms)} · {it.span_count ?? 0} 步
                  {it.stuck ? ` · ${it.stuck}` : ''}
                </div>
              </li>
            ))}
            {items.length === 0 && (
              <li className="px-3 py-8 text-center text-faint text-f12">
                {work ? '这本书还没有运行链路。去写作台走一轮后再回来。' : '请先选一本书。'}
              </li>
            )}
          </ul>
        </div>

        <div className="rounded-lg border border-line bg-surface p-3 min-h-[240px]" data-testid="run-logs-detail">
          {!sel ? (
            <div className="text-f12 text-faint py-10 text-center">点左侧一条，看这一次每一步怎么连</div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {statusChip(sel.status, sel.contrast_summary?.verdict)}
                <span className="text-f13 font-medium">
                  第 {sel.chapter ?? '—'} 章 · {KIND_LABEL[sel.kind] || sel.kind}
                </span>
                <span className="text-f12 text-faint">{fmtMs(sel.duration_ms)} · {(sel.spans || []).length} 步</span>
              </div>
              <div className="text-f13">{sel.headline || '—'}</div>
              <div className="text-f12 text-faint space-y-0.5">
                <div>请求 {sel.trace_id || '—'}</div>
                {sel.outcome_status && <div>模型 {sel.outcome_status}</div>}
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className={tab === 'logs' ? btnPrimary : btnCls} onClick={() => setTab('logs')}>分析日志</button>
                <button type="button" className={tab === 'timeline' ? btnPrimary : btnCls} onClick={() => setTab('timeline')}>步骤树</button>
                <button type="button" className={tab === 'contrast' ? btnPrimary : btnCls} onClick={() => setTab('contrast')}>更多</button>
                <button type="button" className={btnCls} disabled={!sel.prev_trace_id} onClick={() => sel.prev_trace_id && openChain(sel.prev_trace_id)}>同章上一写</button>
                <button type="button" className={btnCls} disabled={!sel.next_trace_id} onClick={() => sel.next_trace_id && openChain(sel.next_trace_id)}>同章下一写</button>
              </div>

              {tab === 'logs' && (
                <ul className="rounded-md border border-line max-h-[28rem] overflow-auto" data-testid="run-logs-lines">
                  {logs.map((lg) => (
                    <li key={lg.log_id || `${lg.step_key}-${lg.seq}`} className="px-2 py-1.5 border-t border-line text-f12" data-testid="run-log-line">
                      <div className="text-faint">[{lg.step_title || lg.step_key}] {lg.code}</div>
                      <div>{lg.message || '—'}</div>
                    </li>
                  ))}
                  {logs.length === 0 && (
                    <li className="px-2 py-6 text-center text-faint">
                      {sel?.schema_ver ? '旧账·仅摘要（本链没有逐步日志）' : '没有逐步日志。'}
                    </li>
                  )}
                </ul>
              )}
              {tab === 'timeline' && (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <button type="button" className={onlyBad ? btnPrimary : btnCls} onClick={() => setOnlyBad((v) => !v)}>只看异常</button>
                    <button type="button" className={layerOrder ? btnPrimary : btnCls} onClick={() => setLayerOrder((v) => !v)}>按层分析序</button>
                    <span className="text-f12 text-faint">默认全步墙钟序</span>
                  </div>
                  <ul className="rounded-md border border-line max-h-[22rem] overflow-auto" data-testid="run-logs-spans">
                    {spans.map((s) => (
                      <li
                        key={s.span_id}
                        data-testid="run-logs-span"
                        className={`px-2 py-1.5 border-t border-line cursor-pointer text-f12 ${
                          pick?.span_id === s.span_id ? 'bg-brand/10' : highlight.has(s.span_id) ? 'bg-soft/80' : ''
                        }`}
                        onClick={() => setPick(s)}
                      >
                        <div className="flex items-center gap-2">
                          {s.parent_span_id ? <span className="text-faint">└</span> : null}
                          <span className="font-medium">{s.step_title || s.step_key}</span>
                          <span className="text-faint">{fmtMs(s.timing?.duration_ms)}</span>
                          {statusChip(s.status, s.verdict)}
                        </div>
                        <div className="text-faint">{s.step_key}{s.layer ? ` · ${s.layer}` : ''}</div>
                      </li>
                    ))}
                    {spans.length === 0 && (
                      <li className="px-2 py-6 text-center text-faint">没有步骤。</li>
                    )}
                  </ul>
                  {pick && (
                    <div className="rounded-md border border-line p-2 text-f12 space-y-1" data-testid="run-logs-inspector">
                      <div className="font-medium">{pick.step_title} · {pick.step_key}</div>
                      <div>该跑 {pick.expected == null ? '—' : (pick.expected ? '要有' : '不该有')}
                        {pick.expected_reason ? `（${pick.expected_reason}）` : ''}</div>
                      <div>实际 {STATUS_LABEL[pick.actual] || pick.actual || '—'} {pick.actual_reason ? `/ ${pick.actual_reason}` : ''}</div>
                      <div>输入 {(pick.input && pick.input.source) || '—'}
                        {pick.input?.chars_in != null ? ` · ${pick.input.chars_in} 字` : ''}</div>
                      <div>计算 {(pick.compute && pick.compute.fn) || '—'}</div>
                      <div>产出 {(pick.output && pick.output.shape) || 'block'} · {pick.output?.chars ?? 0} 字</div>
                      <div>耗时 {fmtMs(pick.timing?.duration_ms)}</div>
                      <div>关联 父={pick.parent_span_id || '无'} · 层 {pick.layer}{pick.tier ? ` / ${pick.tier}` : ''}</div>
                      {Array.isArray(pick.events) && pick.events.length > 0 && (
                        <div>事件 {pick.events.map((e) => e.tag || e.op).join('、')}</div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {tab === 'contrast' && (
                <div className="rounded-md border border-line overflow-auto max-h-[28rem]">
                  <table className="w-full text-f12">
                    <thead className="bg-soft/80 text-faint text-left">
                      <tr>
                        <th className="px-2 py-1.5">步骤</th>
                        <th className="px-2 py-1.5">该跑</th>
                        <th className="px-2 py-1.5">实际</th>
                        <th className="px-2 py-1.5">字数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(sel.contrast_summary?.rows || []).map((r) => (
                        <tr key={r.name} className="border-t border-line">
                          <td className="px-2 py-1.5">{r.name}</td>
                          <td className="px-2 py-1.5">{r.expected ? '要有' : '不该有'}</td>
                          <td className={`px-2 py-1.5 ${r.verdict === 'red' ? 'text-red-600' : ''}`}>{r.actual}</td>
                          <td className="px-2 py-1.5 tnum">{r.chars ?? 0}</td>
                        </tr>
                      ))}
                      {!(sel.contrast_summary?.rows || []).length && (
                        <tr><td colSpan={4} className="px-2 py-6 text-center text-faint">没有对照摘要。</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default RunLogsPage
