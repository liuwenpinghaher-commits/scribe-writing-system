import { useEffect, useMemo, useState } from 'react'
import { Check, Loader2, Plus, X } from 'lucide-react'
import { api } from '../api'
import { useToast } from '../ui/Toast'
import { DirectoryHeader } from './DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from './DirectoryRow'

const CODEX_CATS = new Set(['character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif', 'proposition'])

const CATEGORY_META = {
  character: { desc: '人物档案 / 关系 / 弧光', tone: 'brand' },
  faction: { desc: '组织目标 / 资源 / 冲突', tone: 'blue' },
  item: { desc: '状态链 / 持有人 / 证据', tone: 'amber' },
  term: { desc: '概念解释 / 使用边界', tone: 'brand' },
  world_rule: { desc: '规则 / 代价 / 例外', tone: 'blue' },
  promise: { desc: '埋设 / 回收 / 线索', tone: 'red' },
  motif: { desc: '主题变体 / 证据章节', tone: 'amber' },
  proposition: { desc: '论断 / 反例 / 结论', tone: 'brand' },
}

const TONE = {
  brand: 'bg-brand shadow-[0_0_0_4px_rgba(47,117,99,.14)]',
  blue: 'bg-blue-600 shadow-[0_0_0_4px_rgba(37,99,235,.12)]',
  amber: 'bg-amber-600 shadow-[0_0_0_4px_rgba(217,119,6,.14)]',
  red: 'bg-danger shadow-[0_0_0_4px_rgba(163,64,64,.12)]',
}

function sameNode(a, b) {
  if (!a || !b) return false
  if (a.id && b.id && a.id === b.id) return true
  return a.type === b.type && a.ref != null && b.ref != null && String(a.ref) === String(b.ref)
}

function findCategory(root, selected) {
  const categories = root?.children || []
  if (!root || selected?.type === 'codex_root') return null
  if (selected?.type === 'codex_new') return categories.find((cat) => String(cat.ref) === String(selected.ref)) || null
  if (selected?.type === 'codex_category') return categories.find((cat) => sameNode(cat, selected)) || selected
  return categories.find((cat) => (cat.children || []).some((child) => sameNode(child, selected))) || null
}

function matchesQuery(node, query) {
  if (!query) return true
  const haystack = [
    node?.label,
    node?.type,
    node?.ref,
    node?.meta?.summary,
    node?.meta?.kind,
    ...(Array.isArray(node?.badges) ? node.badges.map((b) => b?.value) : []),
  ].filter(Boolean).join(' ')
  return haystack.toLowerCase().includes(query.toLowerCase())
}

function CountBadge({ children }) {
  return <span className="shrink-0 min-w-[24px] h-5 inline-flex items-center justify-center rounded-full bg-soft px-1.5 text-meta text-faint tnum">{children}</span>
}

function RowText({ title, sub }) {
  return (
    <span className="min-w-0 flex flex-col gap-0.5">
      <span className="min-w-0 truncate text-f13 leading-5">{title}</span>
      {sub && <span className="min-w-0 truncate text-meta leading-4 text-faint">{sub}</span>}
    </span>
  )
}

function CategoryRow({ category, selected, onSelect }) {
  const count = category.children?.length ?? 0
  return (
    <DirectoryRow
      title={category.label}
      meta={count}
      active={selected}
      aria-label={category.label}
      onClick={() => onSelect?.(category)}
    />
  )
}

function ItemRow({ node, selected, onSelect }) {
  const chapter = node?.meta?.chapter ?? node?.meta?.first_chapter ?? node?.meta?.seq
  return (
    <DirectoryRow
      title={node.label}
      meta={chapter != null ? `第 ${chapter} 章` : undefined}
      active={selected}
      aria-label={node.label}
      onClick={() => onSelect?.(node)}
    />
  )
}

const PENDING_SHOW_CAP = 40

function PendingCharacterRefs({ moduleFilter = null }) {
  /** 全类型设定收件箱：canon_candidate + 旧人物 unverified。
   *  须在设定库根目录与各分类下都可见（旧实现仅 character 分类内，导致「收件箱空」误判）。 */
  const [items, setItems] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [acceptingIds, setAcceptingIds] = useState(() => new Set())
  const [workSlug, setWorkSlug] = useState(() => (typeof api.getWork === 'function' ? api.getWork() : ''))
  const toast = useToast()

  const reload = () => {
    const w = typeof api.getWork === 'function' ? api.getWork() : ''
    setWorkSlug(w || '')
    Promise.all([
      api.listCanonCandidates('pending').catch((e) => {
        setLoadError(e?.body?.detail || e?.message || '候选列表加载失败')
        return { items: [] }
      }),
      api.listUnverified().catch(() => []),
    ]).then(([cand, unv]) => {
      if (Array.isArray(cand?.items) && cand.items.length) setLoadError(null)
      const fromCand = (Array.isArray(cand?.items) ? cand.items : []).map((c) => ({
        id: c.id,
        kind: 'canon',
        module: c.module || 'character',
        name: (c.target || '').split(':').pop() || c.target,
        seq: c.seq,
        role: c.field ? `${c.module}.${c.field}` : (c.module || '设定'),
        evidence: c.evidence,
        risk: c.risk,
      }))
      const fromUnv = (Array.isArray(unv) ? unv : []).map((u) => ({
        id: u.id,
        kind: 'unverified',
        module: 'character',
        name: u.name,
        seq: u.seq,
        role: u.role || '人物引用',
      }))
      const seen = new Set(fromCand.map((x) => x.id))
      const merged = [...fromCand]
      for (const u of fromUnv) {
        if (!seen.has(u.id) && !fromCand.some((c) => c.name === u.name)) merged.push(u)
      }
      setItems(merged)
    }).catch(() => setItems([]))
  }

  useEffect(() => {
    reload()
    // 切书后 api.setWork 会变；轮询 work slug，变则重载
    const t = setInterval(() => {
      const w = typeof api.getWork === 'function' ? api.getWork() : ''
      setWorkSlug((prev) => {
        if (w && w !== prev) reload()
        return w || prev
      })
    }, 1500)
    const onVis = () => { if (document.visibilityState === 'visible') reload() }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      clearInterval(t)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])

  const remove = (id) => setItems((prev) => (prev || []).filter((item) => item.id !== id))
  const accept = async (item) => {
    if (acceptingIds.has(item.id)) return
    setAcceptingIds((prev) => new Set(prev).add(item.id))
    try {
      if (item.kind === 'canon') {
        await api.decideCanonCandidate(item.id, 'approve')
        remove(item.id)
        toast?.(`已批准设定「${item.name}」(${item.module})`)
      } else {
        const result = await api.acceptUnverified(item.id)
        remove(item.id)
        toast?.(result?.replay_queued
          ? `已接受「${item.name}」为角色，正在后台回填第${item.seq ?? '?'}章关联`
          : `已接受「${item.name}」为角色`)
      }
    } catch (e) {
      toast?.(e?.body?.detail || '接受失败', { tone: 'danger' })
    } finally {
      setAcceptingIds((prev) => {
        const next = new Set(prev)
        next.delete(item.id)
        return next
      })
    }
  }
  const ignore = async (item) => {
    try {
      if (item.kind === 'canon') {
        await api.decideCanonCandidate(item.id, 'reject')
      } else {
        await api.ignoreUnverified(item.id)
      }
      remove(item.id)
    } catch (e) {
      toast?.(e?.body?.detail || '忽略失败', { tone: 'danger' })
    }
  }
  const ignoreAll = async () => {
    try {
      const list = visible || []
      for (const it of list) {
        try {
          if (it.kind === 'canon') await api.decideCanonCandidate(it.id, 'reject')
          else await api.ignoreUnverified(it.id)
        } catch { /* continue */ }
      }
      // 全量忽略当前过滤视图对应的全部 pending（含未展示的）
      const all = (items || []).filter((it) => (
        !moduleFilter
        || it.module === moduleFilter
        || (moduleFilter === 'character' && it.kind === 'unverified')
      ))
      for (const it of all) {
        if (list.some((x) => x.id === it.id)) continue
        try {
          if (it.kind === 'canon') await api.decideCanonCandidate(it.id, 'reject')
          else await api.ignoreUnverified(it.id)
        } catch { /* continue */ }
      }
      setItems((prev) => (prev || []).filter((it) => !all.some((x) => x.id === it.id)))
      toast?.(`已处理 ${all.length} 条待确认设定`)
    } catch (e) {
      toast?.(e?.body?.detail || '批量忽略失败', { tone: 'danger' })
    }
  }

  const visible = (items || []).filter((it) => {
    if (!moduleFilter) return true
    if (moduleFilter === 'character' && it.kind === 'unverified') return true
    return it.module === moduleFilter
  })
  const shown = visible.slice(0, PENDING_SHOW_CAP)
  const rest = Math.max(0, visible.length - shown.length)

  if (items === null) {
    return (
      <section className="mb-3 px-2 py-1.5 text-meta text-faint">加载待确认设定…</section>
    )
  }
  if (loadError && visible.length === 0) {
    return (
      <section className="mb-3 rounded-lg bg-danger/[.06] px-2 py-2 text-meta text-danger">
        待确认设定加载失败{workSlug ? `（书 ${workSlug}）` : ''}：{String(loadError)}
        <button type="button" onClick={reload} className="ml-2 underline cursor-pointer">重试</button>
      </section>
    )
  }
  if (visible.length === 0) {
    // 根目录给一句空态，避免「完全没入口」；分类内为空则不占位
    if (!moduleFilter) {
      return (
        <section className="mb-3 px-2 py-1.5 text-meta text-faint">
          待确认设定：无 pending
          {workSlug ? ` · ${workSlug}` : ''}
          <button type="button" onClick={reload} className="ml-2 underline cursor-pointer text-faint hover:text-ink">刷新</button>
        </section>
      )
    }
    return null
  }
  return (
    <section className="mb-3" data-testid="canon-pending-inbox">
      <div className="px-2 pb-1.5 flex items-center gap-2 flex-wrap">
        <div className="text-meta font-semibold uppercase tracking-wide text-faint">待确认设定</div>
        <CountBadge>{visible.length}</CountBadge>
        {workSlug && <span className="text-meta text-faint truncate max-w-[10rem]" title={workSlug}>{workSlug}</span>}
        {moduleFilter && <span className="text-meta text-faint">· {moduleFilter}</span>}
        <button type="button" onClick={reload} className="h-6 rounded-md px-1.5 text-meta text-faint hover:bg-soft hover:text-ink cursor-pointer">刷新</button>
        {visible.length > 3 && (
          <button type="button" onClick={ignoreAll} className="ml-auto h-6 rounded-md px-1.5 text-meta text-faint hover:bg-soft hover:text-ink cursor-pointer">
            全部忽略
          </button>
        )}
      </div>
      <div className="space-y-1 max-h-[40vh] overflow-y-auto">
        {shown.map((item) => (
          <div key={`${item.kind}-${item.id}`} className="rounded-lg bg-warn/[.05] px-2 py-1.5">
            <div className="min-w-0 flex items-center gap-2">
              <RowText
                title={item.name}
                sub={`第${item.seq ?? '—'}章 · ${item.module || 'character'} · ${item.role || '待确认'}${item.risk === 'high' ? ' · 高风险' : ''}`}
              />
              {(() => {
                const accepting = acceptingIds.has(item.id)
                return (
              <button type="button" aria-label={accepting ? '处理中' : '批准写入'} onClick={() => accept(item)} disabled={accepting}
                className="shrink-0 h-7 w-7 grid place-items-center rounded-md text-brand hover:bg-brand/10 disabled:cursor-wait disabled:opacity-60 cursor-pointer">
                {accepting ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              </button>
                )
              })()}
              <button type="button" aria-label="忽略" onClick={() => ignore(item)}
                className="shrink-0 h-7 w-7 grid place-items-center rounded-md text-faint hover:bg-soft hover:text-ink cursor-pointer">
                <X size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
      {rest > 0 && (
        <div className="px-2 pt-1 text-meta text-faint">
          还有 {rest} 条未展开（API 共 {visible.length}；启发式可能偏多，可批量忽略噪声）
        </div>
      )}
    </section>
  )
}

function EmptyState({ category, query, onNew }) {
  return (
    <div className="px-3 py-10 text-center text-f13 text-faint">
      <div className="mb-2 font-medium text-ink">{query ? '没有匹配条目' : '暂无子项'}</div>
      {category && CODEX_CATS.has(category.ref) && (
        <button type="button" onClick={onNew} className="text-brand hover:underline cursor-pointer">
          新建{category.label}
        </button>
      )}
    </div>
  )
}

export function CodexDirectory({ root, selected, onSelectItem }) {
  const [query, setQuery] = useState('')
  const [serverHits, setServerHits] = useState(null) // null=未搜 / []|items=服务端结果
  const [inboxDebt, setInboxDebt] = useState(null)
  useEffect(() => {
    let alive = true
    const pull = () => {
      if (typeof api.canonDebt !== 'function') return
      api.canonDebt().then((d) => { if (alive) setInboxDebt(d) }).catch(() => {})
    }
    pull()
    const t = setInterval(pull, 8000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  const openInbox = () => {
    onSelectItem?.({ type: 'view', id: 'view:canon-inbox', label: '设定收件箱' })
  }
  const [health, setHealth] = useState(null)
  const [smartView, setSmartView] = useState('all') // all|secret|sparse
  const category = findCategory(root, selected)
  const categories = root?.children || []
  const isRoot = !category
  const items = useMemo(() => {
    const children = category?.children || []
    return children.filter((node) => matchesQuery(node, query))
  }, [category, query])
  const canCreate = category?.type === 'codex_category' && CODEX_CATS.has(category.ref)
  const createNode = () => {
    if (!canCreate) return
    onSelectItem?.({ id: `new:${category.ref}`, type: 'codex_new', ref: category.ref, label: category.label })
  }

  useEffect(() => { setQuery(''); setServerHits(null) }, [category?.id])

  useEffect(() => {
    let alive = true
    // 测试 mock 可能未挂 codexHealth:缺省跳过,不炸渲染
    if (typeof api.codexHealth !== 'function') {
      setHealth(null)
      return () => { alive = false }
    }
    api.codexHealth()
      .then((h) => { if (alive) setHealth(h) })
      .catch(() => { if (alive) setHealth(null) })
    return () => { alive = false }
  }, [root?.id])

  // 跨类型服务端搜索(debounce):有 query 时优先用 /codex/search
  useEffect(() => {
    const needle = query.trim()
    if (!needle || needle.length < 1) {
      setServerHits(null)
      return undefined
    }
    if (typeof api.codexSearch !== 'function') {
      setServerHits(null)
      return undefined
    }
    let alive = true
    const t = setTimeout(() => {
      api.codexSearch(needle, 40)
        .then((r) => {
          if (!alive) return
          const items = Array.isArray(r?.items) ? r.items : []
          setServerHits(items.map((it) => ({
            id: it.id || `${it.type}:${it.ref}`,
            type: it.type,
            ref: it.ref,
            label: it.label,
            meta: { subtitle: it.subtitle },
          })))
        })
        .catch(() => { if (alive) setServerHits([]) })
    }, 280)
    return () => { alive = false; clearTimeout(t) }
  }, [query])

  const showServerSearch = serverHits != null && query.trim()

  return (
    <div className={DIR_SHELL} data-testid="codex-directory">
      <div className="px-2 py-1.5 border-b border-line/40 flex items-center gap-2">
        <button
          type="button"
          onClick={openInbox}
          data-testid="open-canon-inbox"
          className="flex-1 h-8 rounded-lg px-2 text-left text-f13 font-medium bg-warn/[.08] text-ink hover:bg-warn/[.14] cursor-pointer"
        >
          设定收件箱
          {inboxDebt?.total != null && (
            <span className="ml-1.5 text-meta text-faint tnum">({inboxDebt.total}{inboxDebt.noise_count ? ` · 噪${inboxDebt.noise_count}` : ''})</span>
          )}
        </button>
      </div>
      <DirectoryHeader
        title={category?.label || root?.label || '设定库'}
        count={isRoot ? categories.length : (category?.children?.length || 0)}
        query={query}
        onQueryChange={setQuery}
        searchLabel="搜设定、别名、标签"
        searchPlaceholder="搜设定、别名、标签"
        status={!isRoot ? (
          <button type="button" aria-label="返回设定库分类" onClick={() => onSelectItem?.(root)}
            className="text-meta text-faint hover:text-brand cursor-pointer">← 分类</button>
        ) : null}
        primaryAction={canCreate ? { label: '新建设定', onClick: createNode } : undefined}
      />
      <div data-testid="codex-directory-title" className="sr-only">{category?.label || root?.label || '设定库'}</div>
      {health && (
        <div data-testid="codex-health" className="px-3 py-1.5 text-meta text-faint border-b border-line/30 bg-surface/80">
          健康度: 角色 {health.characters ?? 0} · 命题 {health.propositions_open ?? 0}
          · 稀疏档案 {health.sparse_dossiers ?? 0} · 无关系角色 {health.isolated_characters ?? 0}
        </div>
      )}
      {isRoot && (
        <div data-testid="codex-smart-views" className="flex flex-wrap gap-1 px-3 py-1.5 border-b border-line/40 bg-surface">
          {[
            { key: 'all', label: '全部分类' },
            { key: 'secret', label: '含私密' },
            { key: 'sparse', label: '稀疏档案' },
          ].map((v) => (
            <button key={v.key} type="button" onClick={() => setSmartView(v.key)}
              className={`h-6 px-2 rounded-md text-meta cursor-pointer ${smartView === v.key ? 'bg-brand/10 text-brand font-medium' : 'text-faint hover:bg-soft'}`}>
              {v.label}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2">
        {showServerSearch ? (
          <>
            <DirectorySectionLabel>搜索结果</DirectorySectionLabel>
            {serverHits.length === 0 ? (
              <div className="px-3 py-8 text-center text-f13 text-faint">没有匹配设定</div>
            ) : (
              <div className="space-y-1" data-testid="codex-search-results">
                {serverHits.map((node) => (
                  <ItemRow key={node.id} node={node} selected={sameNode(node, selected)} onSelect={onSelectItem} />
                ))}
              </div>
            )}
          </>
        ) : isRoot ? (
          <>
            {/* 根目录也展示全类型待确认，避免只进「角色」才看得见 */}
            <PendingCharacterRefs />
            <DirectorySectionLabel>分类</DirectorySectionLabel>
            <div className="space-y-1">
              {categories
                .filter((cat) => matchesQuery(cat, query))
                .filter((cat) => {
                  if (smartView === 'secret') {
                    return (cat.children || []).some((c) => (c.badges || []).some((b) => b?.kind === 'secret'))
                      || cat.ref === 'proposition' || cat.ref === 'character'
                  }
                  if (smartView === 'sparse') return cat.ref === 'character'
                  return true
                })
                .map((cat) => (
                  <CategoryRow key={cat.id} category={cat} selected={sameNode(cat, selected)} onSelect={onSelectItem} />
                ))}
            </div>
          </>
        ) : (
          <>
            {/* 各分类内按 module 过滤展示；character 含旧 unverified */}
            {CODEX_CATS.has(category.ref) && (
              <PendingCharacterRefs moduleFilter={category.ref} />
            )}
            <DirectorySectionLabel>条目</DirectorySectionLabel>
            {items.length === 0 ? (
              <EmptyState category={category} query={query} onNew={createNode} />
            ) : (
              <div className="space-y-1">
                {items
                  .filter((node) => {
                    if (smartView === 'secret') {
                      return (node.badges || []).some((b) => b?.kind === 'secret')
                    }
                    return true
                  })
                  .map((node) => (
                    <ItemRow key={node.id} node={node} selected={sameNode(node, selected)} onSelect={onSelectItem} />
                  ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
