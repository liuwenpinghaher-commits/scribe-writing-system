/**
 * 设定收件箱工作台 P0–P2
 * 分类 Tab · 筛选 · 分组 · 详情 Diff/合并/改 module · 键盘 · 审计
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

const MODULE_OPTIONS = MODULE_TABS.filter((t) => t.key)

function fmtVal(v) {
  if (v == null || v === '') return '（无）'
  if (typeof v === 'object') {
    try { return JSON.stringify(v, null, 0) } catch { return String(v) }
  }
  return String(v)
}

function groupKeyOf(it) {
  const mod = (it.module || '').toLowerCase()
  const bare = (it.target || '').split(':').pop()
  return `${mod}|${bare}`
}

export function CanonInboxView({ work, onJumpChapter, initialSeq, initialModule }) {
  const toast = useToast()
  const listRef = useRef(null)
  const [module, setModule] = useState(initialModule || '')
  const [status, setStatus] = useState('pending') // pending|approved|rejected
  const [priority, setPriority] = useState('suggested') // suggested|all|noise
  const [seq, setSeq] = useState(() => {
    if (initialSeq != null) return String(initialSeq)
    try {
      const s = sessionStorage.getItem('canon-inbox-seq')
      if (s) {
        sessionStorage.removeItem('canon-inbox-seq')
        return s
      }
    } catch { /* */ }
    return ''
  })
  const [groupMode, setGroupMode] = useState(true)
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
  const [editModule, setEditModule] = useState('')
  const [editTarget, setEditTarget] = useState('')
  const [editField, setEditField] = useState('')
  const [mergeInto, setMergeInto] = useState('')
  const [collapsed, setCollapsed] = useState(() => new Set())

  const isAudit = status !== 'pending'
  const noiseMode = isAudit ? 'all' : (priority === 'noise' ? 'only' : priority === 'suggested' ? 'exclude' : 'all')
  const priorityMode = priority === 'suggested' && !isAudit ? 'suggested' : 'all'

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const q = {
        status,
        limit: 200,
        noise: isAudit ? undefined : noiseMode,
        priority: isAudit ? undefined : (priority === 'noise' ? 'all' : priorityMode),
      }
      if (module) q.module = module
      if (seq && /^\d+$/.test(seq)) q.seq = Number(seq)
      const res = await api.listCanonCandidatesQuery(q)
      const list = Array.isArray(res?.items) ? res.items : []
      setItems(list)
      setFacets(res?.facets || {})
      setDebt(res?.debt || {})
      setTotal(res?.total ?? list.length)
      if (selectedId && !list.some((i) => i.id === selectedId)) {
        setSelectedId(null)
        setDetail(null)
      }
    } catch (e) {
      toast?.(e?.body?.detail || e?.message || '加载收件箱失败', { tone: 'danger' })
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [module, seq, noiseMode, priorityMode, priority, status, isAudit, selectedId, toast])

  useEffect(() => { reload() }, [work, module, seq, priority, status]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadDetail = useCallback(async (id) => {
    if (!id) { setDetail(null); return }
    setDetailLoading(true)
    try {
      const d = await api.getCanonCandidate(id)
      setDetail(d)
      const it = d?.item || {}
      const after = it.after ?? d?.diff?.after
      setEditAfter(typeof after === 'object' ? JSON.stringify(after, null, 2) : String(after ?? ''))
      setEditModule(it.module || '')
      setEditTarget(it.target || '')
      setEditField(it.field || '')
      const sim = d?.codex_match?.similar?.[0]
      setMergeInto(sim?.id || sim?.name || '')
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

  const flatIds = useMemo(() => items.map((i) => i.id), [items])

  const groups = useMemo(() => {
    if (!groupMode) return null
    const map = new Map()
    for (const it of items) {
      const k = groupKeyOf(it)
      if (!map.has(k)) map.set(k, [])
      map.get(k).push(it)
    }
    return [...map.entries()].sort((a, b) => b[1].length - a[1].length)
  }, [items, groupMode])

  const selectByIndex = (delta) => {
    if (!flatIds.length) return
    const idx = Math.max(0, flatIds.indexOf(selectedId))
    let next = idx + delta
    if (selectedId == null) next = delta > 0 ? 0 : flatIds.length - 1
    if (next < 0) next = 0
    if (next >= flatIds.length) next = flatIds.length - 1
    setSelectedId(flatIds[next])
  }

  const onApprove = async (id, opts = {}) => {
    if (isAudit) return
    setBusyId(id)
    try {
      const extra = {}
      if (opts.withEdit) {
        let after = editAfter
        try { after = JSON.parse(editAfter) } catch { /* text */ }
        extra.edit = {
          after,
          module: editModule || undefined,
          target: editTarget || undefined,
          field: editField || null,
        }
      }
      if (opts.merge) {
        if (!mergeInto.trim()) {
          toast?.('请选择或填写合并目标', { tone: 'danger' })
          return
        }
        extra.merge_into = mergeInto.trim()
        if (editField) {
          let after = editAfter
          try { after = JSON.parse(editAfter) } catch { /* */ }
          extra.edit = { ...(extra.edit || {}), after, field: editField || undefined }
        }
      }
      const res = await api.decideCanonCandidate(id, 'approve', extra)
      if (!res?.ok) {
        toast?.(
          res?.result?.rejected
            ? `批准失败：${JSON.stringify(res.result.rejected).slice(0, 140)}`
            : '批准未写入',
          { tone: 'danger' },
        )
      } else {
        toast?.(opts.merge ? '已合并并写入' : '已批准并写入正典')
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
    if (isAudit) return
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
    const nHint = debt.noise_count ?? facets.noise_count ?? '?'
    if (!window.confirm(`清除全书待确认中的疑似噪声（约 ${nHint} 条，可多轮）？`)) return
    setBatchBusy(true)
    try {
      // 优先多轮 purge；旧后端回退单批 noise_only
      let res
      if (typeof api.purgeCanonNoise === 'function') {
        res = await api.purgeCanonNoise({})
        toast?.(`已清除噪声 ${res?.rejected ?? 0} 条` +
          (res?.remaining_noise != null ? ` · 剩余噪 ${res.remaining_noise}` : '') +
          (res?.debt?.total != null ? ` · 待批 ${res.debt.total}` : ''))
      } else {
        res = await api.batchDecideCanonCandidates({
          decision: 'reject', noise_only: true, reason: 'noise_heuristic',
        })
        toast?.(`已忽略噪声 ${res?.ok_count ?? 0} 条`)
      }
      reload()
    } catch (e) {
      toast?.(e?.body?.detail || '批量忽略失败', { tone: 'danger' })
    } finally {
      setBatchBusy(false)
    }
  }

  const dedupePending = async () => {
    if (!window.confirm('合并重复待确认（同对象只留最新一条，已在设定库的一并拒）？')) return
    setBatchBusy(true)
    try {
      const res = await api.dedupeCanonCandidates()
      toast?.(
        `去重完成 · 保留 ${res?.kept ?? 0}` +
        ` · 重复拒 ${res?.rejected_dupes ?? 0}` +
        ` · 库中已有拒 ${res?.rejected_already_in_codex ?? 0}` +
        (res?.debt?.total != null ? ` · 待批 ${res.debt.total}` : ''),
      )
      reload()
    } catch (e) {
      toast?.(e?.body?.detail || '去重失败', { tone: 'danger' })
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

  const decideGroup = async (gk, decision) => {
    if (isAudit) return
    const label = decision === 'approve' ? '批准' : '拒绝'
    if (!window.confirm(`${label}本组全部条目（${gk}）？`)) return
    setBatchBusy(true)
    try {
      const res = await api.batchDecideCanonCandidates({ decision, group_key: gk, reason: `group_${decision}` })
      toast?.(`组操作完成 ${res?.ok_count ?? 0}/${res?.processed ?? 0}`)
      reload()
    } catch (e) {
      toast?.(e?.body?.detail || '组操作失败', { tone: 'danger' })
    } finally {
      setBatchBusy(false)
    }
  }

  // 键盘
  useEffect(() => {
    const onKey = (e) => {
      const tag = (e.target && e.target.tagName) || ''
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target?.isContentEditable) return
      if (e.key === 'j' || e.key === 'J') { e.preventDefault(); selectByIndex(1) }
      else if (e.key === 'k' || e.key === 'K') { e.preventDefault(); selectByIndex(-1) }
      else if ((e.key === 'a' || e.key === 'A') && selectedId && !isAudit) { e.preventDefault(); onApprove(selectedId) }
      else if ((e.key === 'r' || e.key === 'R') && selectedId && !isAudit) { e.preventDefault(); onReject(selectedId) }
      else if ((e.key === 'o' || e.key === 'O') && detail?.chapter_excerpt?.seq != null && onJumpChapter) {
        e.preventDefault()
        onJumpChapter(Number(detail.chapter_excerpt.seq))
      }
      else if ((e.key === 'm' || e.key === 'M') && selectedId && !isAudit) {
        e.preventDefault()
        onApprove(selectedId, { merge: true })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const byModule = facets.by_module || debt.by_module || {}
  const item = detail?.item
  const chEx = detail?.chapter_excerpt
  const mergeOpts = detail?.merge_options || []

  const renderRow = (it) => {
    const active = it.id === selectedId
    const title = it.title || `${it.module} · ${it.target}`
    return (
      <button
        key={it.id}
        type="button"
        onClick={() => setSelectedId(it.id)}
        className={`w-full text-left px-3 py-2.5 cursor-pointer transition-colors ${active ? 'bg-brand/10' : 'hover:bg-soft'}`}
      >
        <div className="text-f13 text-ink font-medium truncate">{title}</div>
        <div className="text-meta text-faint mt-0.5 truncate">
          第{it.seq ?? '—'}章
          {it.labels?.source ? ` · ${it.labels.source}` : it.source ? ` · ${it.source}` : ''}
          {it.labels?.extractor ? ` · ${it.labels.extractor}` : it.extractor ? ` · ${it.extractor}` : ''}
          {it.is_noise ? ' · 噪声' : ''}
          {it.risk === 'high' ? ' · 高风险' : ''}
          {it.status && it.status !== 'pending' ? ` · ${it.status}` : ''}
        </div>
        {(it.before != null || it.after != null) && status === 'pending' && (
          <div className="text-meta text-faint mt-0.5 truncate">
            {fmtVal(it.before).slice(0, 20)} → {fmtVal(it.after).slice(0, 36)}
          </div>
        )}
      </button>
    )
  }

  return (
    <div className="h-full min-h-0 flex flex-col bg-canvas" data-testid="canon-inbox-view" ref={listRef}>
      <div className="shrink-0 border-b border-line px-4 py-2 flex flex-wrap items-center gap-2 bg-surface">
        <h2 className="text-f14 font-semibold text-ink">设定收件箱</h2>
        <span className="text-meta text-faint tnum">
          债 {debt.total ?? '—'}
          {debt.noise_count != null && ` · 噪 ${debt.noise_count}`}
          {debt.suggested_priority_count != null && ` · 优先 ${debt.suggested_priority_count}`}
        </span>
        <button type="button" onClick={reload} className="h-7 w-7 grid place-items-center rounded-md hover:bg-soft cursor-pointer" aria-label="刷新">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
        <span className="text-meta text-faint hidden sm:inline">快捷键 j/k 移动 · a 批 · r 拒 · m 合并 · o 开章</span>
        <div className="ml-auto flex flex-wrap gap-2">
          {!isAudit && (
            <>
              <button type="button" disabled={batchBusy || !(debt.noise_count || facets.noise_count)} onClick={ignoreNoise}
                className="h-7 px-2 rounded-md text-meta bg-soft hover:bg-line/40 disabled:opacity-40 cursor-pointer"
                data-testid="canon-purge-noise">
                清除全书噪声 ({debt.noise_count ?? facets.noise_count ?? 0})
              </button>
              <button type="button" disabled={batchBusy || !(debt.total || items.length)} onClick={dedupePending}
                className="h-7 px-2 rounded-md text-meta bg-soft hover:bg-line/40 disabled:opacity-40 cursor-pointer"
                data-testid="canon-dedupe-pending">
                合并重复
              </button>
              <button type="button" disabled={batchBusy || !items.length} onClick={rejectVisible}
                className="h-7 px-2 rounded-md text-meta text-faint hover:bg-soft disabled:opacity-40 cursor-pointer">
                拒绝当前列表
              </button>
            </>
          )}
        </div>
      </div>

      {/* 状态：待批 / 审计 */}
      <div className="shrink-0 flex flex-wrap gap-1 px-3 py-1.5 border-b border-line/40 bg-surface/90">
        {[
          { k: 'pending', l: '待确认' },
          { k: 'approved', l: '已批准' },
          { k: 'rejected', l: '已拒绝' },
        ].map((s) => (
          <button key={s.k} type="button" onClick={() => { setStatus(s.k); setSelectedId(null) }}
            className={`h-7 px-2.5 rounded-md text-meta cursor-pointer ${status === s.k ? 'bg-ink text-canvas' : 'text-faint hover:bg-soft'}`}>
            {s.l}
          </button>
        ))}
        <label className="ml-2 flex items-center gap-1 text-meta text-faint">
          <input type="checkbox" checked={groupMode} onChange={(e) => setGroupMode(e.target.checked)} />
          按对象分组
        </label>
      </div>

      <div className="shrink-0 flex flex-wrap gap-1 px-3 py-2 border-b border-line/50 bg-surface/80">
        {MODULE_TABS.map((t) => {
          const n = t.key ? (byModule[t.key] || 0) : (facets.total ?? debt.total)
          return (
            <button key={t.key || 'all'} type="button" onClick={() => setModule(t.key)}
              className={`h-7 px-2 rounded-md text-meta cursor-pointer ${module === t.key ? 'bg-brand/10 text-brand font-medium' : 'text-faint hover:bg-soft'}`}>
              {t.label}{!isAudit && n != null ? ` ${n}` : ''}
            </button>
          )
        })}
      </div>

      {!isAudit && (
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
            <input value={seq} onChange={(e) => setSeq(e.target.value.replace(/[^\d]/g, ''))}
              placeholder="全部" className="h-7 w-16 rounded-md border border-line bg-canvas px-1.5 tnum" />
          </label>
          <span className="text-faint self-center">列表 {total} 条（本页 {items.length}）</span>
        </div>
      )}

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <div className="min-h-0 overflow-y-auto border-r border-line/40">
          {loading && !items.length && (
            <div className="p-6 text-faint text-f13 flex items-center gap-2"><Loader2 size={14} className="animate-spin" />加载中…</div>
          )}
          {!loading && !items.length && (
            <div className="p-8 text-center text-faint text-f13">当前筛选下无条目</div>
          )}
          {!groupMode && (
            <ul className="divide-y divide-line/30">{items.map((it) => <li key={it.id}>{renderRow(it)}</li>)}</ul>
          )}
          {groupMode && groups && groups.map(([gk, list]) => {
            const open = !collapsed.has(gk)
            const [mod, bare] = gk.split('|')
            return (
              <div key={gk} className="border-b border-line/30">
                <div className="sticky top-0 z-[1] flex items-center gap-2 px-2 py-1.5 bg-soft/90 backdrop-blur-sm">
                  <button type="button" className="text-f13 font-medium text-ink truncate cursor-pointer flex-1 text-left"
                    onClick={() => setCollapsed((prev) => {
                      const n = new Set(prev)
                      if (n.has(gk)) n.delete(gk); else n.add(gk)
                      return n
                    })}>
                    {open ? '▾' : '▸'} {mod}「{bare}」 · {list.length}
                  </button>
                  {!isAudit && (
                    <>
                      <button type="button" disabled={batchBusy} onClick={() => decideGroup(gk, 'reject')}
                        className="h-6 px-1.5 rounded text-meta text-faint hover:bg-canvas cursor-pointer disabled:opacity-40">拒组</button>
                      <button type="button" disabled={batchBusy} onClick={() => decideGroup(gk, 'approve')}
                        className="h-6 px-1.5 rounded text-meta text-brand hover:bg-brand/10 cursor-pointer disabled:opacity-40">批组</button>
                    </>
                  )}
                </div>
                {open && <div className="divide-y divide-line/20">{list.map((it) => renderRow(it))}</div>}
              </div>
            )
          })}
        </div>

        <div className="min-h-0 overflow-y-auto p-4">
          {!selectedId && (
            <div className="h-full grid place-items-center text-faint text-f13 px-6 text-center">
              选择左侧一条查看详情<br />
              <span className="text-meta mt-2 block">j/k 上下 · a 批准 · r 拒绝 · m 合并到已有 · o 打开正文</span>
            </div>
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
                  <span>· {item?.status || status}</span>
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
                        <button type="button" className="ml-2 text-brand underline cursor-pointer"
                          onClick={() => onJumpChapter(Number(chEx.seq))}>打开本章 (o)</button>
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
                    {detail.codex_match.exists ? '库中已有匹配' : '库中未见精确匹配'}
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

              {!isAudit && (
                <>
                  <section className="space-y-2">
                    <h3 className="text-meta font-semibold text-faint uppercase tracking-wide">编辑后再批</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <label className="text-meta text-faint block">
                        类型 module
                        <select value={editModule} onChange={(e) => setEditModule(e.target.value)}
                          className="mt-0.5 w-full h-8 rounded-md border border-line bg-canvas px-1.5 text-f12 text-ink">
                          {MODULE_OPTIONS.map((m) => (
                            <option key={m.key} value={m.key}>{m.label} ({m.key})</option>
                          ))}
                        </select>
                      </label>
                      <label className="text-meta text-faint block">
                        目标 target
                        <input value={editTarget} onChange={(e) => setEditTarget(e.target.value)}
                          className="mt-0.5 w-full h-8 rounded-md border border-line bg-canvas px-1.5 text-f12 text-ink" />
                      </label>
                      <label className="text-meta text-faint block sm:col-span-2">
                        字段 field（可空）
                        <input value={editField} onChange={(e) => setEditField(e.target.value)}
                          className="mt-0.5 w-full h-8 rounded-md border border-line bg-canvas px-1.5 text-f12 text-ink" />
                      </label>
                    </div>
                    <label className="text-meta text-faint block">
                      after（JSON 或文本）
                      <textarea value={editAfter} onChange={(e) => setEditAfter(e.target.value)} rows={3}
                        className="mt-0.5 w-full rounded-lg border border-line bg-canvas p-2 text-f12 font-mono text-ink" />
                    </label>
                  </section>

                  <section className="space-y-2">
                    <h3 className="text-meta font-semibold text-faint uppercase tracking-wide">合并到已有 (m)</h3>
                    <select value={mergeInto} onChange={(e) => setMergeInto(e.target.value)}
                      className="w-full h-8 rounded-md border border-line bg-canvas px-1.5 text-f12">
                      <option value="">— 选择 Codex 已有条目 —</option>
                      {mergeOpts.map((o) => (
                        <option key={o.target} value={o.target}>{o.label}</option>
                      ))}
                    </select>
                    <input value={mergeInto} onChange={(e) => setMergeInto(e.target.value)}
                      placeholder="或手写 target，如 role:沈拾灯"
                      className="w-full h-8 rounded-md border border-line bg-canvas px-1.5 text-f12" />
                  </section>

                  <div className="flex flex-wrap gap-2 pt-1">
                    <button type="button" disabled={busyId === item?.id} onClick={() => onApprove(item.id, false)}
                      className="h-9 px-3 rounded-lg bg-brand text-white text-f13 font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer inline-flex items-center gap-1.5">
                      {busyId === item?.id ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                      批准写入 (a)
                    </button>
                    <button type="button" disabled={busyId === item?.id} onClick={() => onApprove(item.id, { withEdit: true })}
                      className="h-9 px-3 rounded-lg border border-brand/40 text-brand text-f13 hover:bg-brand/5 disabled:opacity-50 cursor-pointer">
                      编辑并批准
                    </button>
                    <button type="button" disabled={busyId === item?.id} onClick={() => onApprove(item.id, { merge: true })}
                      className="h-9 px-3 rounded-lg border border-line text-ink text-f13 hover:bg-soft disabled:opacity-50 cursor-pointer">
                      合并并批准 (m)
                    </button>
                    <button type="button" disabled={busyId === item?.id} onClick={() => onReject(item.id)}
                      className="h-9 px-3 rounded-lg border border-line text-faint text-f13 hover:bg-soft disabled:opacity-50 cursor-pointer inline-flex items-center gap-1.5">
                      <X size={14} /> 拒绝 (r)
                    </button>
                  </div>
                </>
              )}

              {isAudit && (
                <div className="text-f13 text-faint rounded-lg border border-line/40 p-3 bg-soft/30">
                  审计只读视图。状态：<span className="text-ink">{item?.status}</span>
                  {item?.decided_at && <> · 决定于 {String(item.decided_at)}</>}
                </div>
              )}

              {item?.id && (
                <div className="text-meta text-faint">id: {item.id} · group: {groupKeyOf(item)}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CanonInboxView
