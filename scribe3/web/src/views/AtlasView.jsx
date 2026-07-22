import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { MultiDirectedGraph } from 'graphology'
import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import { Eye, X, Crosshair, ChevronRight, Loader2, Lock, List } from 'lucide-react'
import { api } from '../api'
import { REL_LABEL, relColor } from '../lib/relColors'
import { useSelection } from '../selectionContext'

// 关系图谱 = scribe3 真知识图:角色 —knows→ 命题(谁知道什么)+ 角色关系边。
// 重写要点(波A):sigma(WebGL/canvas)+ graphology + forceAtlas2,默认只画 focus 角色的
// ego 子图(后端 /graph?focus=&hop=&limit= 子图),点击节点可展开/换中心。根治 React Flow+ELK
// 主线程全量渲染数千节点冻死。

// —— 主题色解析:WebGL 不认 CSS var(),运行时从 :root 取真色,随明暗主题自适应 ——
function cssVar(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
function resolveColor(c, theme) {
  // relColor 可能返回 'var(--color-line)';统一成真色
  if (typeof c === 'string' && c.startsWith('var(')) {
    const m = c.match(/var\((--[a-z-]+)\)/)
    return m ? (theme[m[1]] || theme['--color-faint'] || '#65706a') : (theme['--color-faint'] || '#65706a')
  }
  return c
}
function readTheme() {
  return {
    '--color-brand': cssVar('--color-brand', '#2f6b5d'),
    '--color-irony': cssVar('--color-irony', '#4f76a3'),
    '--color-secret': cssVar('--color-secret', '#9c5f86'),
    '--color-line': cssVar('--color-line', '#d8d4cb'),
    '--color-faint': cssVar('--color-faint', '#65706a'),
    '--color-ink': cssVar('--color-ink', '#1d2420'),
  }
}

function nodeColor(n, theme) {
  if (n.type === 'character') return theme['--color-brand']
  return n.secret ? theme['--color-secret'] : theme['--color-irony']
}

// —— graphology 构建 + forceAtlas2 布局,挂进 sigma(在数据加载后跑有限迭代) ——
function buildGraph(data, focus, theme) {
  const g = new MultiDirectedGraph()
  const nodes = data?.nodes || []
  const edges = data?.edges || []
  // 初始圆环排布(给 forceAtlas2 一个非退化起点)
  const N = Math.max(nodes.length, 1)
  nodes.forEach((n, i) => {
    if (g.hasNode(n.id)) return
    const isChar = n.type === 'character'
    const isFocus = focus && n.id === focus
    const ang = (i / N) * Math.PI * 2
    g.addNode(n.id, {
      x: Math.cos(ang) * 10 + (isFocus ? 0 : 0),
      y: Math.sin(ang) * 10,
      size: isFocus ? 16 : isChar ? 11 : 7,
      color: nodeColor(n, theme),
      // 角色显名;命题节点 label 后端已对 secret 屏蔽(store.graph 出带锁前缀的私密串),
      // 此处不再前端重复加锁前缀,避免双锁——secret 语义由后端 label + 节点配色承载
      label: n.label || n.id,
      _type: n.type,
      _secret: !!n.secret,
      _rawlabel: n.label || n.id,
      _focus: !!isFocus,
    })
  })
  // focus 居中(布局更稳)
  if (focus && g.hasNode(focus)) {
    g.setNodeAttribute(focus, 'x', 0)
    g.setNodeAttribute(focus, 'y', 0)
  }
  edges.forEach((e, i) => {
    if (!g.hasNode(e.src) || !g.hasNode(e.dst)) return
    const isKnows = e.rel === 'knows'
    try {
      g.addEdgeWithKey('e' + i, e.src, e.dst, {
        size: isKnows ? 1 : 2.2,
        color: resolveColor(relColor(e.rel), theme),
        _rel: e.rel,
        label: isKnows ? '' : (REL_LABEL[e.rel] || e.rel),
        type: 'arrow',
      })
    } catch { /* 重复边忽略 */ }
  })
  // forceAtlas2 有限迭代(子图 ≤300 很快;上限防长卡)
  if (g.order > 1) {
    const settings = forceAtlas2.inferSettings(g)
    forceAtlas2.assign(g, {
      iterations: Math.min(100, 30 + g.order),
      settings: { ...settings, scalingRatio: 12, gravity: 1.2, slowDown: 2 },
    })
  }
  return g
}

// 内层:加载 graph 到 sigma + 注册点击事件
function GraphContent({ data, focus, theme, onPickNode, onHoverNode }) {
  const loadGraph = useLoadGraph()
  const registerEvents = useRegisterEvents()
  const sigma = useSigma()

  useEffect(() => {
    const g = buildGraph(data, focus, theme)
    loadGraph(g)
    // 自适应视野
    requestAnimationFrame(() => {
      try { sigma.getCamera().animatedReset({ duration: 0 }) } catch { /* */ }
    })
  }, [data, focus, theme, loadGraph, sigma])

  useEffect(() => {
    registerEvents({
      clickNode: ({ node }) => {
        const g = sigma.getGraph()
        if (!g.hasNode(node)) return
        onPickNode({
          id: node,
          label: g.getNodeAttribute(node, '_rawlabel'),
          type: g.getNodeAttribute(node, '_type'),
          secret: g.getNodeAttribute(node, '_secret'),
        })
      },
      // 块三:点画布空白 → 清选中(详情面板关闭 + 总线 focus 清空 → 主编回退视图级话术)
      clickStage: () => onPickNode(null),
      enterNode: ({ node }) => onHoverNode?.(node),
      leaveNode: () => onHoverNode?.(null),
    })
  }, [registerEvents, sigma, onPickNode, onHoverNode])

  // 真机 e2e 只读 seam:暴露节点的屏幕坐标,让测试能对 WebGL 画布做「真实点击」命中节点(不改任何状态)。
  useEffect(() => {
    window.__s3Atlas = {
      nodes: () => sigma.getGraph().nodes(),
      nodeViewport: (id) => {
        const g = sigma.getGraph()
        if (!g.hasNode(id)) return null
        return sigma.graphToViewport({ x: g.getNodeAttribute(id, 'x'), y: g.getNodeAttribute(id, 'y') })
      },
    }
    return () => { delete window.__s3Atlas }
  }, [sigma])

  return null
}

// 节点详情面板(点击后弹出)
function NodeDetail({ node, focus, edges, onExpand, onOpenNode, onClose }) {
  if (!node) return null
  // 该节点与 focus 之间的关系(若直连)
  const relToFocus = focus && focus !== node.id
    ? edges.find((e) =>
        (e.src === node.id && e.dst === focus) || (e.src === focus && e.dst === node.id))
    : null
  return (
    <div className="absolute top-3 right-3 z-20 w-64 rounded-xl border border-line/70 bg-surface/95 backdrop-blur p-3.5 flex flex-col gap-2.5 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-2">
        <span className="text-f14 font-medium text-ink leading-snug flex-1 break-words">
          {node.secret ? <span className="inline-flex items-center gap-1"><Lock size={13} />私密命题</span> : node.label}
        </span>
        <button onClick={onClose} className="text-faint hover:text-ink shrink-0 mt-0.5"><X size={14} /></button>
      </div>
      <div className="flex items-center gap-1.5 text-f12 text-faint">
        <i className="w-2.5 h-2.5 rounded-full inline-block"
          style={{ background: node.type === 'character' ? 'var(--color-brand)' : node.secret ? 'var(--color-secret)' : 'var(--color-irony)' }} />
        {node.type === 'character' ? '角色' : node.secret ? '私密命题' : '命题'}
      </div>
      {relToFocus && (
        <div className="text-f12 text-ink">
          与中心关系:<span className="font-medium">{REL_LABEL[relToFocus.rel] || (relToFocus.rel === 'knows' ? '知道' : relToFocus.rel)}</span>
        </div>
      )}
      {node.secret && (
        <div className="text-meta text-faint leading-relaxed">该命题为私密内容,图谱中不展示明文。</div>
      )}
      <button
        onClick={() => onOpenNode?.({
          id: node.id,
          type: node.type === 'character' ? 'character' : 'proposition',
          label: node.secret ? '私密命题' : node.label,
          secret: !!node.secret,
        })}
        className="mt-0.5 inline-flex items-center justify-center gap-1.5 h-8 rounded-lg text-f13 text-ink hover:bg-soft cursor-pointer"
      >
        打开设定
      </button>
      {node.type === 'character' && (
        <button
          onClick={() => onExpand(node.id)}
          className="mt-0.5 inline-flex items-center justify-center gap-1.5 h-8 rounded-lg bg-brand text-brandfg text-f13 font-medium hover:opacity-90"
        >
          <Crosshair size={13} /> 以此为中心展开
        </button>
      )}
    </div>
  )
}

export function AtlasView({ onNavigateToObject }) {
  const [raw, setRaw] = useState(null)        // 当前子图数据
  const [chars, setChars] = useState([])      // 全部角色(下拉用)— 仅 id/label
  const [focus, setFocus] = useState('')      // 当前中心角色 id
  const [hop, setHop] = useState(1)
  // 章切片:null=全书(不传 chapter);number=截至该章的时间门(后端 graph 已支持)
  const [sliceChapter, setSliceChapter] = useState(null)
  const [maxChapter, setMaxChapter] = useState(0)
  const [picked, setPicked] = useState(null)  // 点击的节点
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [theme, setTheme] = useState(readTheme)
  const [retryTick, setRetryTick] = useState(0) // 重试触发器
  const reqId = useRef(0)
  // 块三:选中节点 → 通用选中总线(主编聚焦);清选中 → focus 清空(回退视图级话术)。
  const { setFocus: setBusFocus } = useSelection()
  const pickNode = useCallback((n) => {
    setPicked(n)
    if (!n) { setBusFocus(null); return }
    setBusFocus(n.type === 'character'
      ? { type: 'character', id: n.id, label: n.label, origin: 'atlas' }
      : { type: 'frame_fact', id: n.id, label: n.secret ? '私密命题' : n.label, payload: { secret: !!n.secret }, origin: 'atlas' })
  }, [setBusFocus])

  // 键盘等价路径:图谱对象列表项 → 与图形节点「打开设定」相同的 onNavigateToObject。
  const navToNode = useCallback((n) => {
    onNavigateToObject?.({
      id: n.id,
      type: n.type === 'character' ? 'character' : 'proposition',
      label: n.secret ? '私密命题' : (n.label || n.id),
      secret: !!n.secret,
    })
  }, [onNavigateToObject])

  // 主题(明暗切换时刷新色板)
  useEffect(() => {
    const obs = new MutationObserver(() => setTheme(readTheme()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] })
    return () => obs.disconnect()
  }, [])

  // 首屏:取一份角色清单(用于下拉 + 选首个角色作默认 focus)。
  // 用一个小子图请求拿到角色列表:不带 focus 取 top-limit,从中筛角色。
  // 角色清单始终全书(便于选中后按切片看邻域);章上限并行取 /chapters。
  useEffect(() => {
    let alive = true
    setLoading(true); setErr(null)
    const chPromise = typeof api.chapters === 'function'
      ? api.chapters()
      : Promise.resolve([])
    chPromise.then((chs) => {
      if (!alive) return
      const rows = Array.isArray(chs) ? chs : []
      const max = rows.reduce((m, c) => Math.max(m, Number(c?.seq) || 0), 0)
      setMaxChapter(max)
      // 若先前切片超出新上限(换书/重试),钳回全书
      setSliceChapter((prev) => (prev != null && max > 0 && prev > max ? null : prev))
    }).catch(() => { if (alive) setMaxChapter(0) })
    api.graph({ limit: 600 }).then((g) => {
      if (!alive) return
      const cs = (g.nodes || []).filter((n) => n.type === 'character')
        .map((n) => ({ id: n.id, label: n.label || n.id }))
      setChars(cs)
      if (cs.length) {
        // 默认聚焦「最中心」角色(边数最多,通常是主角)→ 一进来就看到主关系网,而非随机首个稀疏角色。
        const charIds = new Set(cs.map((c) => c.id))
        const deg = {}
        for (const e of (g.edges || [])) {
          if (charIds.has(e.src)) deg[e.src] = (deg[e.src] || 0) + 1
          if (charIds.has(e.dst)) deg[e.dst] = (deg[e.dst] || 0) + 1
        }
        const central = cs.reduce((best, c) => (deg[c.id] || 0) > (deg[best.id] || 0) ? c : best, cs[0])
        setFocus(central.id) // 触发 ego 子图加载
      } else {
        // 无角色:直接把 top-limit 子图作为展示
        setRaw(g); setLoading(false)
      }
    }).catch((e) => { if (alive) { setErr(e.message || '加载失败'); setLoading(false) } })
    return () => { alive = false }
  }, [retryTick])

  // focus / hop / 章切片 / 重试 → 拉 ego 子图(默认不全量)
  useEffect(() => {
    if (!focus) return
    let alive = true
    const myReq = ++reqId.current
    setLoading(true); setErr(null); setPicked(null)
    const opts = { focus, hop, limit: 300 }
    if (sliceChapter != null) opts.chapter = sliceChapter
    api.graph(opts).then((g) => {
      if (!alive || myReq !== reqId.current) return
      setRaw(g); setLoading(false)
    }).catch((e) => {
      if (!alive || myReq !== reqId.current) return
      setErr(e.message || '加载失败'); setLoading(false)
    })
    return () => { alive = false }
  }, [focus, hop, sliceChapter, retryTick])

  const stat = useMemo(() => {
    const ns = raw?.nodes || []
    return {
      c: ns.filter((n) => n.type === 'character').length,
      p: ns.filter((n) => n.type === 'proposition').length,
      e: (raw?.edges || []).length,
    }
  }, [raw])

  const onExpandTo = useCallback((id) => {
    setHop(1)
    setFocus(id) // 以该节点为新中心拉子图
  }, [])

  const sigmaSettings = useMemo(() => ({
    renderLabels: true,
    labelColor: { color: theme['--color-ink'] },
    labelFont: 'inherit',
    labelSize: 12,
    labelDensity: 0.7,
    labelGridCellSize: 70,
    defaultEdgeType: 'arrow',
    enableEdgeEvents: false,
    allowInvalidContainer: true,
  }), [theme])

  const present = useMemo(
    () => [...new Set((raw?.edges || []).map((e) => e.rel).filter((r) => r && r !== 'knows'))],
    [raw])

  const focusLabel = chars.find((c) => c.id === focus)?.label

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line/60 bg-surface/95 backdrop-blur-sm flex items-center gap-2.5 px-4 overflow-x-auto">
        <Eye size={15} className="text-brand shrink-0" />
        <span className="text-f13 font-semibold tracking-tight text-ink shrink-0">知识图谱</span>
        {focusLabel && (
          <span className="text-f12 text-faint tnum inline-flex items-center gap-1 shrink-0">
            <Crosshair size={12} className="text-brand" />{focusLabel} · {stat.c}角 · {stat.p}题 · {stat.e}边
          </span>
        )}
        <select
          value={focus}
          onChange={(e) => { setHop(1); setFocus(e.target.value) }}
          className="h-7 rounded-xl border-0 bg-soft/80 px-2.5 text-f13 outline-none focus:ring-2 focus:ring-brand/20 cursor-pointer"
        >
          {chars.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
        {/* hop 展开:1→2→3 跳邻域 — 胶囊切换 */}
        <div className="inline-flex items-center gap-0.5 rounded-xl bg-soft/80 p-0.5 text-f12 shrink-0">
          <span className="px-1.5 text-meta text-faint">跳数</span>
          {[1, 2, 3].map((h) => (
            <button
              key={h}
              onClick={() => setHop(h)}
              className={`min-w-7 h-6 px-1.5 rounded-lg text-meta transition-colors cursor-pointer ${hop === h ? 'bg-surface text-brand font-medium shadow-sm' : 'text-faint hover:text-ink'}`}
            >{h}</button>
          ))}
        </div>
        {/* 章切片:时间门截至第 N 章(复用后端 /graph?chapter=);默认全书 */}
        {maxChapter > 0 && (
          <div className="inline-flex items-center gap-1.5 text-f12 text-faint shrink-0">
            <label htmlFor="atlas-chapter-slice" className="shrink-0">章切片</label>
            <select
              id="atlas-chapter-slice"
              aria-label="章切片"
              value={sliceChapter == null ? '' : String(sliceChapter)}
              onChange={(e) => {
                const v = e.target.value
                setSliceChapter(v === '' ? null : Number(v))
              }}
              className="h-7 rounded-xl border-0 bg-soft/80 px-2.5 text-f13 tnum outline-none focus:ring-2 focus:ring-brand/20 cursor-pointer"
            >
              <option value="">全书</option>
              {Array.from({ length: maxChapter }, (_, i) => i + 1).map((ch) => (
                <option key={ch} value={String(ch)}>截至第{ch}章</option>
              ))}
            </select>
          </div>
        )}
        <div className="ml-auto flex items-center gap-3 text-meta text-faint shrink-0">
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-brand)' }} />角色</span>
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-irony)' }} />命题</span>
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-secret)' }} /><Lock size={11} />私密</span>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex">
        {/* 键盘/读屏等价路径:与画布同一份 raw.nodes 的命名对象列表(WebGL 图无法聚焦时的可达替代) */}
        {raw?.nodes?.length > 0 && (
          <div role="region" aria-label="图谱对象列表"
            className="w-56 shrink-0 border-r border-line/50 bg-surface overflow-y-auto hidden md:block">
            <div className="sticky top-0 bg-surface/95 backdrop-blur px-3 py-2 border-b border-line/50 flex items-center gap-1.5 text-meta font-medium text-faint">
              <List size={12} />对象列表 · {raw.nodes.length}
            </div>
            <ul className="py-1 px-1">
              {raw.nodes.map((n) => (
                <li key={n.id}>
                  <button onClick={() => navToNode(n)}
                    className="w-full text-left px-2.5 py-1.5 rounded-lg text-f12 text-ink hover:bg-soft inline-flex items-center gap-1.5 transition-colors">
                    <i className="w-2 h-2 rounded-full shrink-0"
                      style={{ background: n.type === 'character' ? 'var(--color-brand)' : n.secret ? 'var(--color-secret)' : 'var(--color-irony)' }} />
                    {n.secret && <Lock size={11} className="shrink-0 text-faint" />}
                    <span className="truncate">{n.secret ? '私密命题' : (n.label || n.id)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      <div className="flex-1 min-h-0 relative">
        {err ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-faint">
            <span className="text-f13 text-ink">图谱加载失败</span>
            <span className="text-f12">{err}</span>
            <button
              onClick={() => setRetryTick((t) => t + 1)}
              className="mt-1 h-7 px-3 rounded-lg border border-line text-f12 hover:border-brand"
            >重试</button>
          </div>
        ) : !raw && loading ? (
          <div className="absolute inset-0 flex items-center justify-center gap-2 text-faint text-f13">
            <Loader2 size={16} className="animate-spin" /> 加载子图…
          </div>
        ) : (raw && raw.nodes.length === 0) ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 text-faint">
            <span className="text-f13 text-ink">该角色暂无邻域</span>
            <span className="text-f12">尚未录入「知道」边或角色关系。</span>
          </div>
        ) : (
          <>
            <SigmaContainer
              key={focus /* 换 focus 重建画布,避免残留状态 */}
              graph={MultiDirectedGraph}
              settings={sigmaSettings}
              style={{ width: '100%', height: '100%', background: 'transparent' }}
            >
              {raw && (
                <GraphContent
                  data={raw}
                  focus={focus}
                  theme={theme}
                  onPickNode={pickNode}
                />
              )}
            </SigmaContainer>

            {/* 加载叠层(子图切换时) */}
            {loading && (
              <div className="absolute top-3 left-3 z-10 inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface/90 backdrop-blur px-2.5 py-1 text-f12 text-faint shadow-sm">
                <Loader2 size={13} className="animate-spin" /> 更新中…
              </div>
            )}

            {/* 角色关系图例 */}
            {present.length > 0 && (
              <div className="absolute bottom-3 left-3 z-10 rounded-lg border border-line bg-surface/90 backdrop-blur px-3 py-2 flex flex-col gap-1 shadow-sm">
                <span className="text-meta font-medium text-faint mb-0.5">角色关系</span>
                {present.map((rel) => (
                  <span key={rel} className="inline-flex items-center gap-1.5 text-meta text-ink">
                    <i className="w-3 h-[2px] rounded-full inline-block" style={{ background: relColor(rel) }} />
                    {REL_LABEL[rel] || rel}
                  </span>
                ))}
              </div>
            )}

            {/* 提示 */}
            <div className="absolute bottom-3 right-3 z-10 text-meta text-faint/80 inline-flex items-center gap-1">
              点击节点查看详情 <ChevronRight size={11} /> 角色可「以此为中心展开」
            </div>

            <NodeDetail
              node={picked}
              focus={focus}
              edges={raw?.edges || []}
              onExpand={onExpandTo}
              onOpenNode={onNavigateToObject}
              onClose={() => pickNode(null)}
            />
          </>
        )}
        </div>
      </div>
    </div>
  )
}
