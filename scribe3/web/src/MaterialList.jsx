import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { api } from './api'
import { AsyncState } from './ui/AsyncState.jsx'
import { MATERIAL_KINDS, KIND_LABEL } from './materialKinds'
import { DirectoryHeader } from './layout/DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from './layout/DirectoryRow'

export const matLeafNode = (m) => ({ id: `material:${m.id}`, type: 'material', ref: m.id, label: m.title || '—', meta: { kind: m.kind } })

const materialRefCount = (m) => Number(m?.recall_count || m?.ref_count || 0)

const normalizeMaterialRows = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  return []
}

const MATERIAL_PAGE_SIZE = 200

const normalizeMaterialPage = (payload) => {
  const items = normalizeMaterialRows(payload)
  if (Array.isArray(payload)) return { items, nextCursor: null, total: items.length }
  const rawTotal = Number(payload?.total)
  return {
    items,
    nextCursor: payload?.next_cursor ?? null,
    total: Number.isFinite(rawTotal) ? rawTotal : items.length,
  }
}

export function MaterialList({ node, onSelect }) {
  const isCat = node?.type === 'material_category'
  const kind = isCat ? node.ref : null
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState(null)
  const [q, setQ] = useState('')
  const [activeView, setActiveView] = useState('all')
  const [activeKind, setActiveKind] = useState(kind || 'all')
  const [activeOrigin, setActiveOrigin] = useState('all') // all|manual|import|session_clip
  const [reloadTick, setReloadTick] = useState(0)
  const [pageInfo, setPageInfo] = useState({ nextCursor: null, total: null })
  const [loadingMore, setLoadingMore] = useState(false)
  const [health, setHealth] = useState(null)
  const [healthErr, setHealthErr] = useState('')
  const [recallDegraded, setRecallDegraded] = useState([])

  useEffect(() => {
    setActiveKind(kind || 'all')
    setActiveView('all')
    setActiveOrigin('all')
  }, [kind])

  useEffect(() => {
    let alive = true
    // 测试 mock 可能未挂 materialsHealth:跳过不炸
    if (typeof api.materialsHealth !== 'function') {
      setHealth(null)
      setHealthErr('')
      return () => { alive = false }
    }
    api.materialsHealth()
      .then((h) => { if (alive) { setHealth(h); setHealthErr('') } })
      .catch((e) => {
        if (alive) {
          setHealth(null)
          setHealthErr(e?.body?.detail || e?.message || '健康度加载失败')
        }
      })
    return () => { alive = false }
  }, [reloadTick])

  // 服务端 view/kind/origin 分页;搜索走三通道召回(with_meta 透出 degraded)
  useEffect(() => {
    let alive = true
    const needle = q.trim()
    setErr(null)
    setLoadingMore(false)
    setPageInfo({ nextCursor: null, total: null })
    setRecallDegraded([])
    const selectedKind = isCat ? kind : (activeKind === 'all' ? null : activeKind)
    const originFilter = activeOrigin === 'all' ? undefined : activeOrigin
    if (!needle) {
      api.materials({
        kind: selectedKind || undefined,
        view: activeView || 'all',
        origin: originFilter,
        limit: MATERIAL_PAGE_SIZE,
      })
        .then((r) => {
          if (!alive) return
          const page = normalizeMaterialPage(r)
          setRows(page.items)
          setPageInfo({ nextCursor: page.nextCursor, total: page.total })
          setErr(null)
        })
        .catch((e) => { if (alive) { setRows(null); setErr(e?.body?.detail || e?.message || '素材加载失败') } })
      return () => { alive = false }
    }
    const t = setTimeout(() => {
      api.materialRecall(needle, undefined, true)
        .then((r) => {
          if (!alive) return
          let items = normalizeMaterialRows(r).map((x) => ({ ...x, id: x.material_id || x.id }))
          // 搜索结果客户端再叠 origin/kind(服务端 recall 未带 origin 参)
          if (selectedKind) items = items.filter((m) => m.kind === selectedKind)
          if (originFilter) items = items.filter((m) => (m.origin || 'manual') === originFilter)
          setRows(items)
          setPageInfo({ nextCursor: null, total: items.length })
          setRecallDegraded(Array.isArray(r?.degraded_sources) ? r.degraded_sources : [])
          setErr(null)
        })
        .catch((e) => { if (alive) { setRows(null); setErr(e?.body?.detail || e?.message || '素材加载失败') } })
    }, 350)
    return () => { alive = false; clearTimeout(t) }
  }, [node?.id, kind, q, reloadTick, activeView, activeKind, activeOrigin, isCat])

  const sourceRows = rows || []
  const selectedKind = isCat ? kind : (activeKind === 'all' ? null : activeKind)
  const originFilter = activeOrigin === 'all' ? undefined : activeOrigin
  // 服务端已按 view/origin 过滤;搜索路径上客户端再滤
  const filtered = sourceRows

  const countForKind = (k) => sourceRows.filter((m) => m.kind === k).length
  const title = isCat ? `素材 · ${KIND_LABEL[kind] || kind}` : '素材库'
  const newKind = selectedKind || kind || 'note'

  const newNode = () => onSelect?.({ id: `matnew:${newKind}`, type: 'material_new', ref: newKind, label: KIND_LABEL[newKind] || node?.label })
  const importNode = () => onSelect?.({ id: 'material:import', type: 'material_import', ref: newKind, label: '导入素材' })
  const networkNode = () => onSelect?.({ id: 'material:network', type: 'material_network', ref: null, label: '记忆网络' })
  const retryLoad = () => {
    setErr(null)
    setRows(null)
    setPageInfo({ nextCursor: null, total: null })
    setReloadTick((t) => t + 1)
  }
  const hasMore = pageInfo.nextCursor !== null && pageInfo.nextCursor !== undefined && pageInfo.nextCursor !== ''
  const loadMore = async () => {
    if (!hasMore || loadingMore) return
    setLoadingMore(true)
    try {
      const page = normalizeMaterialPage(await api.materials({
        kind: selectedKind || undefined,
        view: activeView || 'all',
        origin: originFilter,
        limit: MATERIAL_PAGE_SIZE,
        cursor: pageInfo.nextCursor,
      }))
      setRows((prev) => [...(prev || []), ...page.items])
      setPageInfo({ nextCursor: page.nextCursor, total: page.total })
      setErr(null)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '素材加载失败')
    } finally {
      setLoadingMore(false)
    }
  }

  if (err) return (
    <div className="p-3">
      <AsyncState state="error" title="素材加载失败" message={err} onRetry={retryLoad} />
    </div>
  )
  if (!rows) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载素材…</div>

  const smartViews = [
    { key: 'all', label: '全部' },
    { key: 'pinned', label: '核心记忆' },
    { key: 'referenced', label: '已引用' },
    { key: 'untagged', label: '无标签' },
    { key: 'recent', label: '最近' },
    { key: 'archived', label: '已归档' },
  ]
  const originFilters = [
    { key: 'all', label: '全部来源' },
    { key: 'manual', label: '手建' },
    { key: 'import', label: '来自导入' },
    { key: 'session_clip', label: '剪藏' },
  ]

  return (
    <div data-testid="material-workbench" className={DIR_SHELL}>
      <div data-testid="material-workbench-header">
        <DirectoryHeader
          title={title}
          count={pageInfo.total != null ? pageInfo.total : filtered.length}
          query={q}
          onQueryChange={setQ}
          searchLabel="搜索素材"
          searchPlaceholder="标题 / 正文 / 标签"
          primaryAction={{ label: '新建', onClick: newNode }}
          secondaryActions={[
            { label: '导入', onClick: importNode },
            { label: '网络', onClick: networkNode },
          ]}
        />
        <div data-testid="material-smart-views" className="flex flex-wrap gap-1 px-3 pb-2 border-b border-line/40 bg-surface">
          {smartViews.map((v) => (
            <button key={v.key} type="button" onClick={() => setActiveView(v.key)}
              className={`h-6 px-2 rounded-md text-meta whitespace-nowrap transition-colors cursor-pointer ${activeView === v.key ? 'bg-brand/10 text-brand font-medium' : 'text-faint hover:bg-soft'}`}>
              {v.label}
            </button>
          ))}
        </div>
        <div data-testid="material-origin-filters" className="flex flex-wrap gap-1 px-3 pb-2 border-b border-line/40 bg-surface">
          {originFilters.map((o) => (
            <button key={o.key} type="button" onClick={() => setActiveOrigin(o.key)}
              aria-pressed={activeOrigin === o.key}
              className={`h-6 px-2 rounded-md text-meta whitespace-nowrap transition-colors cursor-pointer ${activeOrigin === o.key ? 'bg-brand/10 text-brand font-medium' : 'text-faint hover:bg-soft'}`}>
              {o.label}
            </button>
          ))}
        </div>
        {healthErr && (
          <div role="alert" data-testid="material-health-error" className="px-3 py-1.5 text-meta text-danger border-b border-line/30">
            健康度加载失败: {healthErr}
          </div>
        )}
        {health && !healthErr && (
          <div data-testid="material-health" className="px-3 py-1.5 text-meta text-faint border-b border-line/30 bg-surface/80">
            健康度: 共 {health.total ?? 0} · 未召回 {health.never_recalled ?? 0} · 无摘要 {health.no_summary ?? 0} · 无标签 {health.untagged ?? 0}
          </div>
        )}
        {recallDegraded.length > 0 && (
          <div role="status" data-testid="material-recall-degraded" className="px-3 py-1.5 text-meta text-danger border-b border-line/30">
            召回降级: {recallDegraded.map((s) => `${s.source}: ${s.reason}`).join('；')}
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2">
        <div className="mb-2">
          <DirectorySectionLabel>分类</DirectorySectionLabel>
          <div data-testid="material-kind-list" className="space-y-0.5">
            {!isCat && (
              <DirectoryRow
                title="全部分类"
                meta={String(pageInfo.total ?? sourceRows.length)}
                active={activeKind === 'all'}
                onClick={() => setActiveKind('all')}
                aria-label="全部分类"
              />
            )}
            {MATERIAL_KINDS.map((k) => (
              <DirectoryRow
                key={k.key}
                title={k.label}
                meta={String(countForKind(k.key))}
                active={(selectedKind || activeKind) === k.key}
                onClick={() => setActiveKind(k.key)}
                aria-label={k.label}
              />
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="text-f13 text-faint/60 py-8 text-center">
            {q.trim() ? '没有匹配的素材。' : <>还没有素材。<button type="button" onClick={newNode} className="text-brand hover:underline cursor-pointer ml-1">新建一条</button></>}
          </div>
        ) : (
          <div className="space-y-0.5" data-testid="material-item-list">
            <DirectorySectionLabel>素材</DirectorySectionLabel>
            {filtered.map((m) => (
              <DirectoryRow
                key={m.id}
                title={m.title || '—'}
                leading={m.pinned ? <span className="text-brand shrink-0" aria-hidden>·</span> : null}
                meta={`${KIND_LABEL[m.kind] || m.kind}${m.origin ? ` · ${m.origin}` : ''}${materialRefCount(m) > 0 ? ` · ${materialRefCount(m)}次` : ''}`}
                onClick={() => onSelect?.(matLeafNode(m))}
                aria-label={m.title || '—'}
              />
            ))}
            {hasMore && (
              <button type="button" onClick={loadMore} disabled={loadingMore}
                className="mt-2 w-full h-8 rounded-md bg-soft text-f12 text-faint hover:bg-brand/10 hover:text-brand disabled:opacity-50 cursor-pointer">
                {loadingMore ? '加载中…' : `加载更多 (${sourceRows.length}/${pageInfo.total ?? '?'})`}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
