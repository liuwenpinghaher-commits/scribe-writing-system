import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../../api'
import { DirectoryHeader } from '../../layout/DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from '../../layout/DirectoryRow'

const SOURCE_ORDER = ['正文', '设定', '素材', '伏笔', '母题']

// ── Task 10 Step 4:顶栏搜索 / ⌘K 与左栏搜索工作区统一入口 ──
// AppRail(topbar-search)与 App 层 ⌘K 都派发 s3-open-capability
// { capability:'search', focus:true }。左轨 useLeftDockCapabilities 收到同一事件
// 才切 tab 挂载本目录,组件内 listener 会错过这枚"开门事件"——所以在模块层先把
// focus 请求登记下来,挂载时消费;已挂载时走组件 listener 直接聚焦。
// 只聚焦既有的唯一搜索框,不新建第二份结果 store。
//
// 注意 残留边界:pendingFocus 是"一次性"闩——focus:true 只由显式用户手势(顶栏搜索键 /
// ⌘K)派发,且同一事件会让左轨立刻切到 search tab 并挂载本目录、当拍 consume 清位,
// 所以正常路径不会留残。切书(BinderLayout key=slug 重挂 SearchDirectory)本身不派发
// 该事件,故不会让 B 书首开自动抢焦。仅在"派发了 focus 却始终没挂载"的异常时序才可能
// 留一枚闩;测试用 __resetSearchFocusLatch() 在 beforeEach 清零,避免用例间串味。
let pendingFocus = false
function consumePendingFocus() {
  const v = pendingFocus
  pendingFocus = false
  return v
}
function isSearchFocusRequest(e) {
  return e?.detail?.capability === 'search' && e?.detail?.focus === true
}
// test-only:清零模块级一次性闩,防跨用例残留(生产不调用)
export function __resetSearchFocusLatch() {
  pendingFocus = false
}
if (typeof window !== 'undefined') {
  window.addEventListener('s3-open-capability', (e) => {
    if (isSearchFocusRequest(e)) pendingFocus = true
  })
}

function toNode(result) {
  return {
    id: result.id,
    type: 'recall_result',
    label: result.label,
    source: result.source,
    excerpt: result.excerpt,
    target_node: result.target_node,
    payload: result,
  }
}

export function SearchDirectory({ onSelectItem }) {
  const [q, setQ] = useState('')
  const [state, setState] = useState({ loading: false, err: '', results: [] })
  const inputRef = useRef(null)

  // focus 请求两条路都接:挂载时消费模块层登记(先派发后挂载的真实时序),
  // 已挂载时监听同一事件直接聚焦。模块层 listener 先注册、先执行,组件里
  // 统一 consume,避免下次挂载重复消费同一枚请求。
  useEffect(() => {
    if (consumePendingFocus()) inputRef.current?.focus()
    const onOpen = (e) => {
      if (!isSearchFocusRequest(e)) return
      consumePendingFocus()
      inputRef.current?.focus()
    }
    window.addEventListener('s3-open-capability', onOpen)
    return () => window.removeEventListener('s3-open-capability', onOpen)
  }, [])

  const groups = useMemo(() => {
    const map = new Map()
    for (const r of state.results) {
      const key = r.source || r.type || '其他'
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(r)
    }
    return [...map.entries()].sort((a, b) => {
      const ai = SOURCE_ORDER.indexOf(a[0])
      const bi = SOURCE_ORDER.indexOf(b[0])
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi)
    })
  }, [state.results])

  const run = async (e) => {
    e?.preventDefault?.()
    const needle = q.trim()
    if (!needle) return
    setState({ loading: true, err: '', results: [] })
    try {
      const r = await api.search(needle)
      setState({ loading: false, err: '', results: Array.isArray(r?.results) ? r.results : [] })
    } catch (err) {
      setState({ loading: false, err: err?.body?.detail || err?.message || '搜索失败', results: [] })
    }
  }

  return (
    <div className={DIR_SHELL}>
      <form
        onSubmit={run}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && e.target?.tagName === 'INPUT') run(e)
        }}
      >
        <DirectoryHeader
          title="搜索"
          query={q}
          onQueryChange={setQ}
          searchLabel="全局搜索"
          searchPlaceholder="全局搜索"
          searchInputRef={inputRef}
          primaryAction={{ label: state.loading ? '…' : '搜索', onClick: () => run() }}
        />
      </form>
      <div data-testid="search-results" className="flex-1 min-h-0 overflow-auto px-2 py-2">
        {state.err && <div role="alert" className="rounded-md border border-danger/30 bg-danger/5 px-2 py-1.5 text-f12 text-danger">{state.err}</div>}
        {state.loading && <div className="py-6 text-center text-f12 text-faint">搜索中…</div>}
        {!state.loading && !state.err && state.results.length === 0 && <div className="py-6 text-center text-f12 text-faint">输入关键词后搜索。</div>}
        {groups.map(([source, items]) => (
          <div key={source} className="mb-2">
            <DirectorySectionLabel>{source}</DirectorySectionLabel>
            <div className="space-y-0.5">
              {items.map((r) => (
                <DirectoryRow
                  key={r.id}
                  title={r.label}
                  // 分组标题已是 source，行 meta 用章号/类型，避免与 DirectorySectionLabel 文案重复
                  meta={r.chapter != null ? `第 ${r.chapter} 章` : (r.type || undefined)}
                  sub={r.excerpt || undefined}
                  onClick={() => onSelectItem?.(toNode(r))}
                  aria-label={r.label}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
