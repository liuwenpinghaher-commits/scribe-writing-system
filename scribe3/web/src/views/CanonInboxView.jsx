/**
 * 设定收件箱工作台（P0+P1）
 * 类型 Tab · 筛选 · 富列表 · 详情 Diff/证据 · 噪声桶 · 批量拒绝噪声
 */
import { useCallback, useEffect, useState } from 'react'
import { Check, Loader2, RefreshCw, X } from 'lucide-react'
import { api } from '../api'
import { useToast } from '../ui/Toast'

const MODULE_TABS = [
  { key: '', label: '全部' },
  { key: 'character', label: '角色' },
  { key: 'faction', label: '势力' },
  { key: 'item', label: '物件' },
  { key: 'term', label: '术语' },
  { key: 'world_rule', label: '规则' },
  { key: 'relation', label: '关系' },
  { key: 'promise', label: '伏笔' },
  { key: 'motif', label: '母题' },
  { key: 'fact', label: '事实' },
  { key: 'knowledge', label: '知识' },
]

function fmtVal(v) {
  if (v == null || v === '') return '（无）'
  if (typeof v === 'object') {
    try { return JSON.stringify(v, null, 0) } catch { return String(v) }
  }
  return String(v)
}

export function CanonInboxView({ work, onJumpChapter, initialSeq, initialModule }) {
  const toast = useToast()
  const [module, setModule] = useState(initialModule || '')
  const [priority, setPriority] = useState('suggested') // suggested | all | noise
  const [seq, setSeq] = useState(initialSeq != null ? String(initialSeq) : '')
  const [items, setItems] = useState([])
  const [facets, setFacets] = useState({})
  const [debt, setDebt] = useState({})
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [batchBusy, setBatchBusy] = useState(false)
  const [editAfter, setEditAfter] = useState('')

  const noiseMode = priority === 'noise' ? 'only' : priority === 'suggested' ? 'exclude' : 'all'
  const priorityMode = priority === 'suggested' ? 'suggested' : 'all'

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const q = {
        status: 'pending',
        limit: 200,
        noise: noiseMode,
        priority: priority === 'noise' ? 'all' : priorityMode,
      }
      if (module) q.module = module
      if (seq && /^\d+$/.test(seq)) q.seq = Number(seq)
      const res = await api.listCanonCandidatesQuery(q)
      setItems(Array.isArray(res?.items) ? res.items : [])
      setFacets(res?.facets || {})
      setDebt(res?.debt || {})
      setTotal(res?.total ?? (res?.items || []).length)
      if (selectedId && !(res?.items || []).some((i) => i.id === selectedId)) {
        setSelectedId(null)
        setDetail(null)
      }
    } catch (e) {
      toast?.(e?.body?.detail || e?.message || '加载收件箱失败', { tone: 'danger' })
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [module, seq, noiseMode, priorityMode, priority, selectedId, toast])

  useEffect(() => { reload() }, [work, module, seq, priority]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadDetail = useCallback(async (id) => {
    if (!id) { setDetail(null); return }
    setDetailLoading(true)
    try {
      const d = await api.getCanonCandidate(id)
      setDetail(d)
      const after = d?.item?.after ?? d?.diff?.after
      setEditAfter(typeof after === 'object' ? JSON.stringify(after, null, 2) : String(after ?? ''))
    } catch (e) {
      toast?.(e?.body?.detail || '详情加载失败', { tone: 'danger' })
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }, [toast])

  useEffect(() => {
    if (selectedId) loadDetail(selectedId)
  }, [selectedId, loadDetail])

  const byModule = facets.by_module || debt.by_module || {}

  const onApprove = async (id, withEdit = false) => {
    setBusyId(id)
    try {
      let edit
      if (withEdit && editAfter.trim()) {
        let after = editAfter
        try { after = JSON.parse(editAfter) } catch { /* plain string */ }
        edit = { after }
      }
      const res = await api.decideCanonCandidate(id, 'approve', { edit })
      if (!res?.ok) {
        toast?.(res?.result?.rejected ? `批准失败：${JSON.stringify(res.result.rejected).slice(0, 120)}` : '批准未写入', { tone: 'danger' })
      } else {
        toast?.('已批准并写入正典')
        setItems((prev) => prev.filter((i) => i.id !== id))
        setSelectedId(null)
        setDetail(null)
        reload()
      }
    } catch (e) {
      toast?.(e?.body?.detail || e?.message || '批准失败', { tone: 'danger' })
    } finally {
      setBusyId(null)
    }
  }

  const onReject = async (id) => {
    setBusyId(id)
    try {
      await api.decideCanonCandidate(id, 'reject')
      toast?.('已拒绝')
      setItems((prev) => prev.filter((i) => i.id !== id))
      if (selectedId === id) { setSelectedId(null); setDetail(null) }
      reload()
    } catch (e) {
      toast?.(e?.body?.detail || '拒绝失败', { tone: 'danger' })
    } finally {
      setBusyId(null)
    }
  }

  const ignoreNoise = async () => {
    if (!window.confirm(`忽略全部疑似噪声（约 ${debt.noise_count ?? facets.noise_count ?? '?'} 条）？不会写入正典。`)) return
    setBatchBusy(true)
    try {
      const res = await api.batchDecideCanonCandidates({ decision: 'reject', noise_only: true, reason: 'noise_heuristic' })
      toast?.(`已忽略噪声 ${res?.ok_count ?? 0} 条`)
      reload()
    } catch (e) {
      toast?.(e?.body?.detail || '批量忽略失败', { tone: 'danger' })
    } finally {
      setBatchBusy(false)
    }
  }

  const rejectVisible = async () => {
    if (!items.length) return
    if (!window.confirm(`拒绝当前列表 ${items.length} 条？`)) return
    setBatchBusy(true)
    try {
      const res = await api.batchDecideCanonCandidates({
        decision: 'reject',
        ids: items.map((i) => i.id),
        reason: 'batch_reject_list',
      })
      toast?.(`已拒绝 ${res?.ok_count ?? 0} 条`)
      reload()
    } catch (e) {
      toast?.(e?.body?.detail || '批量拒绝失败', { tone: 'danger' })
    } finally {
      setBatchBusy(false)
    }
  }

  const item = detail?.item
  const chEx = detail?.chapter_excerpt

  return (
    <div className="h-full min-h-0 flex flex-col bg-canvas" data-testid="canon-inbox-view">
      {/* 顶栏 */}
      <div className="shrink-0 border-b border-line px-4 py-2 flex flex-wrap items-center gap-2 bg-surface">
        <h2 className="text-f14 font-semibold text-ink">设定收件箱</h2>
        <span className="text-meta text-faint tnum">
          债 {debt.total ?? '—'}
          {debt.noise_count != null && ` · 噪声 ${debt.noise_count}`}
          {debt.suggested_priority_count != null && ` · 建议优先 ${debt.suggested_priority_count}`}
        </span>
        <button type="button" onClick={reload} className="h-7 w-7 grid place-items-center rounded-md hover:bg-soft cursor-pointer" aria-label="刷新">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            disabled={batchBusy || !(debt.noise_count || facets.noise_count)}
            onClick={ignoreNoise}
            className="h-7 px-2 rounded-md text-meta bg-soft hover:bg-line/40 disabled:opacity-40 cursor-pointer"
          >
            {batchBusy ? '处理中…' : `忽略全部噪声 (${debt.noise_count ?? facets.noise_count ?? 0})`}
          </button>
          <button
            type="button"
            disabled={batchBusy || !items.length}
            onClick={rejectVisible}
            className="h-7 px-2 rounded-md text-meta text-faint hover:bg-soft disabled:opacity-40 cursor-pointer"
          >
            拒绝当前列表
          </button>
        </div>
      </div>

      {/* Tab */}
      <div className="shrink-0 flex flex-wrap gap-1 px-3 py-2 border-b border-line/50 bg-surface/80">
        {MODULE_TABS.map((t) => {
          const n = t.key ? (byModule[t.key] || 0) : (facets.total ?? debt.total)
          return (
            <button
              key={t.key || 'all'}
              type="button"
              onClick={() => setModule(t.key)}
              className={`h-7 px-2 rounded-md text-meta cursor-pointer ${module === t.key ? 'bg-brand/10 text-brand font-medium' : 'text-faint hover:bg-soft'}`}
            >
              {t.label}{n != null ? ` ${n}` : ''}
            </button>
          )
        })}
      </div>

      {/* 筛选 */}
      <div className="shrink-0 flex flex-wrap gap-2 px-3 py-2 border-b border-line/40 text-meta">
        <label className="flex items-center gap-1">
          视图
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className="h-7 rounded-md border border-line bg-canvas px-1.5">
            <option value="suggested">建议优先</option>
            <option value="all">全部 pending</option>
            <option value="noise">仅噪声</option>
          </select>
        </label>
        <label className="flex items-center gap-1">
          章
          <input
            value={seq}
            onChange={(e) => setSeq(e.target.value.replace(/[^\d]/g, ''))}
            placeholder="全部"
            className="h-7 w-16 rounded-md border border-line bg-canvas px-1.5 tnum"
          />
        </label>
        <span className="text-faint self-center">列表 {total} 条（本页 {items.length}）</span>
      </div>

      {/* 主体 */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        {/* 列表 */}
        <div className="min-h-0 overflow-y-auto border-r border-line/40">
          {loading && !items.length && (
            <div className="p-6 text-faint text-f13 flex items-center gap-2"><Loader2 size={14} className="animate-spin" />加载中…</div>
          )}
          {!loading && !items.length && (
            <div className="p-8 text-center text-faint text-f13">当前筛选下无待确认设定</div>
          )}
          <ul className="divide-y divide-line/30">
            {items.map((it) => {
              const active = it.id === selectedId
              const title = it.title || `${it.module} · ${it.target}`
              return (
                <li key={it.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(it.id)}
                    className={`w-full text-left px-3 py-2.5 cursor-pointer transition-colors ${active ? 'bg-brand/10' : 'hover:bg-soft'}`}
                  >
                    <div className="text-f13 text-ink font-medium truncate">{title}</div>
                    <div className="text-meta text-faint mt-0.5 truncate">
                      第{it.seq ?? '—'}章
                      {it.labels?.source ? ` · ${it.labels.source}` : it.source ? ` · ${it.source}` : ''}
                      {it.labels?.extractor ? ` · ${it.labels.extractor}` : ''}
                      {it.is_noise ? ' · 噪声' : ''}
                      {it.risk === 'high' ? ' · 高风险' : ''}
                    </div>
                    {(it.before != null || it.after != null) && (
                      <div className="text-meta text-faint mt-0.5 truncate">
                        {fmtVal(it.before).slice(0, 24)} → {fmtVal(it.after).slice(0, 40)}
                      </div>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>

        {/* 详情 */}
        <div className="min-h-0 overflow-y-auto p-4">
          {!selectedId && (
            <div className="h-full grid place-items-center text-faint text-f13">选择左侧一条，查看变更详情与证据</div>
          )}
          {selectedId && detailLoading && (
            <div className="flex items-center gap-2 text-faint"><Loader2 size={14} className="animate-spin" />加载详情…</div>
          )}
          {selectedId && !detailLoading && detail && (
            <div className="space-y-4" data-testid="canon-candidate-detail">
              <div>
                <div className="text-f15 font-semibold text-ink">{detail.title || item?.title}</div>
                <div className="text-meta text-faint mt-1 flex flex-wrap gap-2">
                  <span>{detail.labels?.module}</span>
                  <span>{detail.labels?.op}</span>
                  {detail.labels?.field && <span>· {detail.labels.field}</span>}
                  <span>· {detail.labels?.source}</span>
                  <span>· {detail.labels?.extractor}</span>
                  {detail.is_noise && <span className="text-amber-700">· 疑似噪声</span>}
                  <span>· conf {item?.confidence ?? '—'}</span>
                </div>
              </div>

              <section>
                <h3 className="text-meta font-semibold text-faint uppercase tracking-wide mb-1.5">变更对比</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div className="rounded-lg border border-line/50 bg-soft/40 p-2">
                    <div className="text-meta text-faint mb-1">变更前</div>
                    <pre className="text-f12 text-ink whitespace-pre-wrap break-words">{fmtVal(detail.diff?.before)}</pre>
                  </div>
                  <div className="rounded-lg border border-brand/30 bg-brand/[.06] p-2">
                    <div className="text-meta text-faint mb-1">变更后</div>
                    <pre className="text-f12 text-ink whitespace-pre-wrap break-words">{fmtVal(detail.diff?.after)}</pre>
                  </div>
                </div>
              </section>

              <section>
                <h3 className="text-meta font-semibold text-faint uppercase tracking-wide mb-1.5">证据</h3>
                <p className="text-f13 text-ink whitespace-pre-wrap">{item?.evidence || '（无证据句）'}</p>
                {chEx && (
                  <div className="mt-2 rounded-lg border border-line/40 p-2 bg-surface">
                    <div className="text-meta text-faint mb-1">
                      第 {chEx.seq} 章 {chEx.title || ''}
                      {chEx.located === false && ' · 证据未精确定位'}
                      {chEx.seq != null && onJumpChapter && (
                        <button
                          type="button"
                          className="ml-2 text-brand underline cursor-pointer"
                          onClick={() => onJumpChapter(Number(chEx.seq))}
                        >
                          打开本章
                        </button>
                      )}
                    </div>
                    <p className="text-f12 text-ink/90 leading-relaxed">{chEx.snippet || '（无正文摘录）'}</p>
                  </div>
                )}
              </section>

              {detail.codex_match && (
                <section>
                  <h3 className="text-meta font-semibold text-faint uppercase tracking-wide mb-1.5">与现有设定</h3>
                  <p className="text-f13 text-faint">
                    {detail.codex_match.exists ? '库中已有同名/匹配实体' : '库中未见精确匹配（将新建或需合并）'}
                  </p>
                  {(detail.codex_match.similar || []).length > 0 && (
                    <ul className="mt-1 text-f12 text-ink space-y-0.5">
                      {detail.codex_match.similar.map((s) => (
                        <li key={s.id || s.name}>· {s.name} <span className="text-faint">({s.score})</span></li>
                      ))}
                    </ul>
                  )}
                </section>
              )}

              <section>
                <h3 className="text-meta font-semibold text-faint uppercase tracking-wide mb-1.5">编辑后批准（可选）</h3>
                <textarea
                  value={editAfter}
                  onChange={(e) => setEditAfter(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-line bg-canvas p-2 text-f12 font-mono"
                  placeholder="修改 after 后再点「编辑并批准」；支持 JSON 或纯文本"
                />
              </section>

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  disabled={busyId === item?.id}
                  onClick={() => onApprove(item.id, false)}
                  className="h-9 px-3 rounded-lg bg-brand text-white text-f13 font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer inline-flex items-center gap-1.5"
                >
                  {busyId === item?.id ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  批准写入
                </button>
                <button
                  type="button"
                  disabled={busyId === item?.id}
                  onClick={() => onApprove(item.id, true)}
                  className="h-9 px-3 rounded-lg border border-brand/40 text-brand text-f13 hover:bg-brand/5 disabled:opacity-50 cursor-pointer"
                >
                  编辑并批准
                </button>
                <button
                  type="button"
                  disabled={busyId === item?.id}
                  onClick={() => onReject(item.id)}
                  className="h-9 px-3 rounded-lg border border-line text-faint text-f13 hover:bg-soft disabled:opacity-50 cursor-pointer inline-flex items-center gap-1.5"
                >
                  <X size={14} /> 拒绝
                </button>
              </div>
              {item?.id && (
                <div className="text-meta text-faint">id: {item.id} · target: {item.target} · op: {item.op}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CanonInboxView
