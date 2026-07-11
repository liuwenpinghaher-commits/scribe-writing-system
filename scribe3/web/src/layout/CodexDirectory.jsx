import { useEffect, useMemo, useState } from 'react'
import { Check, MoreHorizontal, Plus, Search, X } from 'lucide-react'
import { api } from '../api'
import { useToast } from '../ui/Toast'

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

function Dot({ tone }) {
  return <span className={`shrink-0 w-2 h-2 rounded-full ${TONE[tone] || TONE.brand}`} />
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
  const meta = CATEGORY_META[category.ref] || { desc: '设定分类', tone: 'brand' }
  const count = category.children?.length ?? 0
  return (
    <button
      type="button"
      aria-label={category.label}
      onClick={() => onSelect?.(category)}
      className={`w-full min-h-10 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors cursor-pointer ${selected ? 'bg-soft text-brand' : 'text-ink hover:bg-soft/70'}`}
    >
      <span className="min-w-0 flex items-center gap-2">
        <Dot tone={meta.tone} />
        <RowText title={category.label} sub={meta.desc} />
      </span>
      <CountBadge>{count}</CountBadge>
    </button>
  )
}

function ItemRow({ node, selected, tone, onSelect }) {
  const chapter = node?.meta?.chapter ?? node?.meta?.first_chapter ?? node?.meta?.seq
  const sub = node?.meta?.summary || node?.meta?.kind || node?.meta?.status || ''
  return (
    <button
      type="button"
      aria-label={node.label}
      onClick={() => onSelect?.(node)}
      className={`w-full min-h-10 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors cursor-pointer ${selected ? 'bg-soft text-brand' : 'text-ink hover:bg-soft/70'}`}
    >
      <span className="min-w-0 flex items-center gap-2">
        <Dot tone={tone} />
        <RowText title={node.label} sub={sub} />
      </span>
      {chapter != null ? <CountBadge>第 {chapter} 章</CountBadge> : <span />}
    </button>
  )
}

function PendingCharacterRefs() {
  const [items, setItems] = useState(null)
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
    try {
      await api.acceptUnverified(item.id)
      remove(item.id)
      toast?.(`已接受「${item.name}」为角色`)
    } catch (e) {
      toast?.(e?.body?.detail || '接受失败', { tone: 'danger' })
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
              <button type="button" aria-label="接受为角色" onClick={() => accept(item)}
                className="shrink-0 h-7 w-7 grid place-items-center rounded-md text-brand hover:bg-brand/10 cursor-pointer">
                <Check size={14} />
              </button>
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

function SectionLabel({ children }) {
  return <div className="px-2 pb-1.5 pt-2 text-meta font-semibold uppercase tracking-wide text-faint">{children}</div>
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
  const category = findCategory(root, selected)
  const categories = root?.children || []
  const activeMeta = CATEGORY_META[category?.ref] || { desc: '设定分类', tone: 'brand' }
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

  useEffect(() => { setQuery('') }, [category?.id])

  return (
    <div className="h-full min-h-0 flex flex-col bg-surface/75" data-testid="codex-directory">
      <div className="shrink-0 border-b border-line/70 bg-surface/90 px-3.5 py-3">
        <div className="mb-2 flex items-center gap-1.5 text-f12 text-faint">
          <button type="button" aria-label="返回设定库分类" onClick={() => onSelectItem?.(root)}
            className="rounded-md px-1 -ml-1 text-faint hover:bg-soft hover:text-brand cursor-pointer">
            设定库
          </button>
          {category && <span>/ {category.label}</span>}
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <h2 className="min-w-0 flex-1 truncate text-f17 font-semibold text-ink" data-testid="codex-directory-title">
            {category?.label || root?.label || '设定库'}
          </h2>
          <span className="shrink-0 text-f12 text-faint">{isRoot ? `${categories.length} 类` : `${category.children?.length || 0} 项`}</span>
        </div>
        <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto_auto] gap-1.5">
          <label className="relative min-w-0">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-faint pointer-events-none" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜设定、别名、标签"
              className="w-full h-8 rounded-lg border border-line bg-canvas pl-8 pr-2 text-f13 text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
            />
          </label>
          <button type="button" aria-label="新建设定" title="新建设定" disabled={!canCreate} onClick={createNode}
            className="h-8 w-8 grid place-items-center rounded-lg bg-soft text-faint hover:text-brand disabled:opacity-35 disabled:cursor-not-allowed cursor-pointer">
            <Plus size={15} />
          </button>
          <button type="button" aria-label="更多操作" title="更多操作"
            className="h-8 w-8 grid place-items-center rounded-lg bg-soft text-faint hover:text-ink cursor-pointer">
            <MoreHorizontal size={15} />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2">
        {isRoot ? (
          <>
            <SectionLabel>分类</SectionLabel>
            <div className="space-y-1">
              {categories.filter((cat) => matchesQuery(cat, query)).map((cat) => (
                <CategoryRow key={cat.id} category={cat} selected={sameNode(cat, selected)} onSelect={onSelectItem} />
              ))}
            </div>
          </>
        ) : (
          <>
            {category.ref === 'character' && <PendingCharacterRefs />}
            <SectionLabel>条目</SectionLabel>
            {items.length === 0 ? (
              <EmptyState category={category} query={query} onNew={createNode} />
            ) : (
              <div className="space-y-1">
                {items.map((node) => (
                  <ItemRow key={node.id} node={node} selected={sameNode(node, selected)} tone={activeMeta.tone} onSelect={onSelectItem} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
