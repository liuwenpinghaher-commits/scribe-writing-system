import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { DirectoryHeader } from './DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from './DirectoryRow'

const CODEX_CATS = new Set(['character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif', 'proposition'])

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

/** 设定库目录里的收件箱入口行（详情与审批只在工作台，不在侧栏堆列表） */
function InboxDirRow({ debt, selected, onOpen }) {
  const total = debt?.total
  const noise = debt?.noise_count
  const meta = total == null
    ? '待批设定'
    : `${total} 待批${noise ? ` · 噪 ${noise}` : ''}`
  return (
    <DirectoryRow
      title="设定收件箱"
      meta={meta}
      active={selected}
      aria-label="设定收件箱"
      onClick={onOpen}
      data-testid="codex-inbox-dir-row"
      className={selected ? undefined : 'bg-warn/[.06] hover:bg-warn/[.12]'}
    />
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

export function CodexDirectory({ root, selected, sel, onSelectItem }) {
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

  // 中栏已是收件箱视图时，目录行高亮
  const inboxActive = sel?.mode === 'view' && sel?.viewKey === 'canon-inbox'

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
            {/* 目录入口：审批工作台在中栏，此处只一行入口，不堆 pending 列表 */}
            <DirectorySectionLabel>待办</DirectorySectionLabel>
            <div className="space-y-1 mb-2">
              <InboxDirRow debt={inboxDebt} selected={inboxActive} onOpen={openInbox} />
            </div>
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
            {/* 分类内仅保留短入口，避免与收件箱工作台重复堆列表 */}
            <div className="mb-2">
              <InboxDirRow debt={inboxDebt} selected={inboxActive} onOpen={openInbox} />
            </div>
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
