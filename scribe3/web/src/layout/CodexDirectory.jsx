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

function PendingCharacterRefs() {
  const [items, setItems] = useState(null)
  const [acceptingIds, setAcceptingIds] = useState(() => new Set())
  const toast = useToast()

  useEffect(() => {
    let alive = true
    api.listUnverified()
      .then((rows) => { if (alive) setItems(Array.isArray(rows) ? rows : []) })
      .catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [])

  const remove = (id) => setItems((prev) => (prev || []).filter((item) => item.id !== id))
  const accept = async (item) => {
    if (acceptingIds.has(item.id)) return
    setAcceptingIds((prev) => new Set(prev).add(item.id))
    try {
      const result = await api.acceptUnverified(item.id)
      remove(item.id)
      toast?.(result?.replay_queued
        ? `已接受「${item.name}」为角色，正在后台回填第${item.seq ?? '?'}章关联`
        : `已接受「${item.name}」为角色`)
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
      await api.ignoreUnverified(item.id)
      remove(item.id)
    } catch (e) {
      toast?.(e?.body?.detail || '忽略失败', { tone: 'danger' })
    }
  }
  const ignoreAll = async () => {
    try {
      const r = await api.ignoreAllUnverified()
      setItems([])
      toast?.(`已忽略 ${r?.ignored ?? 0} 条待确认引用`)
    } catch (e) {
      toast?.(e?.body?.detail || '批量忽略失败', { tone: 'danger' })
    }
  }

  if (!items || items.length === 0) return null
  return (
    <section className="mb-3">
      <div className="px-2 pb-1.5 flex items-center gap-2">
        <div className="text-meta font-semibold uppercase tracking-wide text-faint">待确认人物引用</div>
        <CountBadge>{items.length}</CountBadge>
        {items.length > 3 && (
          <button type="button" onClick={ignoreAll} className="ml-auto h-6 rounded-md px-1.5 text-meta text-faint hover:bg-soft hover:text-ink cursor-pointer">
            全部忽略
          </button>
        )}
      </div>
      <div className="space-y-1">
        {items.map((item) => (
          <div key={item.id} className="rounded-lg bg-warn/[.05] px-2 py-1.5">
            <div className="min-w-0 flex items-center gap-2">
              <RowText title={item.name} sub={`第${item.seq ?? '?'}章 / ${item.role || '待确认'}`} />
              {(() => {
                const accepting = acceptingIds.has(item.id)
                return (
              <button type="button" aria-label={accepting ? '接受中' : '接受为角色'} onClick={() => accept(item)} disabled={accepting}
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
            {category.ref === 'character' && <PendingCharacterRefs />}
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
