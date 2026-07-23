import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { MultiDirectedGraph } from 'graphology'
import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import { List, Loader2, Network, Pin, X } from 'lucide-react'
import { api } from './api'

// 记忆网络(素材库=主编联想记忆 · 可视化):照 AtlasView 的 sigma(WebGL)+ graphology 范式。
// 节点=素材(label=标题,size 随 recall_count,pinned 高亮为 brand 色);点击节点 → onSelect(material)。
// 边=后端 /materials/graph 返回的 relates 联想边;若边查询降级,保留节点并显示 degraded 提示。

// —— 主题色:WebGL 不认 CSS var(),运行时从 :root 取真色,随明暗主题自适应(同 AtlasView) ——
function cssVar(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
function readTheme() {
  return {
    brand: cssVar('--color-brand', '#3f6b58'),
    irony: cssVar('--color-irony', '#4f76a3'),
    faint: cssVar('--color-faint', '#84817a'),
    ink: cssVar('--color-ink', '#37352f'),
  }
}

// 召回越多越大;pinned 再加一档。封顶防超大节点糊屏。
function nodeSize(m) {
  const rc = Number(m?.recall_count) || 0
  const base = 6 + Math.sqrt(rc) * 2.2
  return Math.min(26, m?.pinned ? base + 4 : base)
}

// —— graphology 构建:向日葵/黄金角排布,无边也能均匀铺开(不必跑 forceAtlas2) ——
function buildGraph(materials, edges, theme) {
  const g = new MultiDirectedGraph()
  const golden = Math.PI * (3 - Math.sqrt(5))
  materials.forEach((m, i) => {
    if (!m?.id || g.hasNode(m.id)) return
    const r = Math.sqrt(i + 0.5)
    const ang = i * golden
    g.addNode(m.id, {
      x: Math.cos(ang) * r * 3,
      y: Math.sin(ang) * r * 3,
      size: nodeSize(m),
      color: m?.pinned ? theme.brand : theme.irony,
      label: m?.title || '(无题)',
      _pinned: !!m?.pinned,
      _recall: Number(m?.recall_count) || 0,
    })
  })
  // relates 联想边(后端 /materials/graph):只连两端都在的节点,防悬空;weight → 线宽
  ;(edges || []).forEach((e, i) => {
    if (e?.src && e?.dst && g.hasNode(e.src) && g.hasNode(e.dst) && !g.hasEdge(e.src, e.dst)) {
      g.addEdgeWithKey(`e${i}`, e.src, e.dst, {
        size: Math.max(0.5, Math.min(3, Number(e.weight) || 1)),
        color: theme.faint, type: 'line',
      })
    }
  })
  return g
}

// 内层:构建 graph 挂进 sigma + 注册点击事件(照 AtlasView.GraphContent)
function GraphContent({ materials, edges, theme, onPick }) {
  const loadGraph = useLoadGraph()
  const registerEvents = useRegisterEvents()
  const sigma = useSigma()

  // node id → material,点击时回查完整素材对象
  const byId = useMemo(() => {
    const m = new Map()
    for (const it of materials) if (it?.id) m.set(it.id, it)
    return m
  }, [materials])

  useEffect(() => {
    loadGraph(buildGraph(materials, edges, theme))
    requestAnimationFrame(() => {
      try { sigma.getCamera().animatedReset({ duration: 0 }) } catch { /* */ }
    })
  }, [materials, edges, theme, loadGraph, sigma])

  useEffect(() => {
    registerEvents({
      clickNode: ({ node }) => { const m = byId.get(node); if (m) onPick(m) },
      clickStage: () => onPick(null), // 点空白 → 清选中
    })
  }, [registerEvents, byId, onPick])

  // 真机 e2e 只读 seam(与 AtlasView __s3Atlas 同构):暴露节点视口坐标,让测试能真实点中 WebGL 节点。
  useEffect(() => {
    window.__s3MatNet = {
      nodes: () => sigma.getGraph().nodes(),
      nodeViewport: (id) => {
        const g = sigma.getGraph()
        if (!g.hasNode(id)) return null
        return sigma.graphToViewport({ x: g.getNodeAttribute(id, 'x'), y: g.getNodeAttribute(id, 'y') })
      },
    }
    return () => { delete window.__s3MatNet }
  }, [sigma])

  return null
}

// 选中素材的小卡(点击节点后弹出;主操作 = 打开素材,回调 onSelect)
function PickedCard({ m, onOpen, onClose }) {
  return (
    <div className="absolute top-3 right-3 z-20 w-60 rounded-md border border-line bg-surface/95 backdrop-blur shadow-lg p-3.5 flex flex-col gap-2.5">
      <div className="flex items-start gap-2">
        <span className="text-f14 font-medium text-ink leading-snug flex-1 break-words">{m.title || '(无题)'}</span>
        <button onClick={onClose} className="text-faint hover:text-ink shrink-0 mt-0.5 cursor-pointer"><X size={14} /></button>
      </div>
      <div className="flex items-center gap-2 text-f12 text-faint flex-wrap">
        {m.pinned && <span className="inline-flex items-center gap-1 text-brand"><Pin size={12} />置顶</span>}
        <span className="tnum">召回 {Number(m.recall_count) || 0} 次</span>
      </div>
      <button onClick={onOpen}
        className="mt-0.5 inline-flex items-center justify-center gap-1.5 h-8 rounded-lg bg-brand text-brandfg text-f13 font-medium hover:opacity-90 cursor-pointer">
        打开素材
      </button>
    </div>
  )
}

export function MaterialNetwork({ onSelect }) {
  const [rows, setRows] = useState(null)      // 节点(素材)
  const [edges, setEdges] = useState([])      // relates 联想边
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [theme, setTheme] = useState(readTheme)
  const [picked, setPicked] = useState(null)
  const [retryTick, setRetryTick] = useState(0)
  const [degradedSources, setDegradedSources] = useState([])
  const [truncated, setTruncated] = useState(false)
  const [focusId, setFocusId] = useState(null)
  // 图/列表双呈现:WebGL 图不可用或边关系 degraded 时,平铺列表是同一份节点数据的替代路径(不另调 API)
  const [view, setView] = useState('graph')

  // 明暗切换 → 刷新色板(同 AtlasView)
  useEffect(() => {
    const obs = new MutationObserver(() => setTheme(readTheme()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] })
    return () => obs.disconnect()
  }, [])

  // 载入素材(节点),retry 触发重拉;focus 时做 ego-neighborhood
  useEffect(() => {
    let alive = true
    setLoading(true); setErr(null); setDegradedSources([]); setTruncated(false)
    const opts = focusId ? { focus: focusId, hop: 1, limit: 200 } : { limit: 200 }
    api.materialGraph(opts)
      .then((g) => {
        if (!alive) return
        setRows(Array.isArray(g?.nodes) ? g.nodes : [])
        setEdges(Array.isArray(g?.edges) ? g.edges : [])
        setTruncated(!!g?.truncated)
        setDegradedSources(g?.edges_degraded
          ? (Array.isArray(g?.degraded_sources) && g.degraded_sources.length
            ? g.degraded_sources
            : [{ source: 'edges', reason: '边关系加载失败' }])
          : [])
        setLoading(false)
      })
      .catch((e) => { if (alive) { setErr(e?.message || '加载失败'); setLoading(false) } })
    return () => { alive = false }
  }, [retryTick, focusId])

  const pick = useCallback((m) => {
    setPicked(m)
    if (m?.id) setFocusId(m.id) // 以节点为 focus 收紧邻域
    if (m) onSelect?.(m) // 点击节点 → 回调
  }, [onSelect])

  const materials = useMemo(() => (rows || []).filter((m) => m?.id), [rows])
  const pinnedCount = useMemo(() => materials.filter((m) => m?.pinned).length, [materials])
  const edgeDegraded = degradedSources.length > 0

  const sigmaSettings = useMemo(() => ({
    renderLabels: true,
    labelColor: { color: theme.ink },
    labelFont: 'inherit',
    labelSize: 12,
    labelDensity: 0.6,
    labelGridCellSize: 80,
    enableEdgeEvents: false,
    allowInvalidContainer: true,
  }), [theme])

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-3 px-4">
        <Network size={15} className="text-brand" />
        <span className="text-f13 font-medium text-ink">记忆网络</span>
        {rows && <span className="text-meta text-faint tnum">{materials.length} 素材 · {pinnedCount} 置顶</span>}
        <div className="ml-auto flex items-center gap-3 text-meta text-faint">
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-brand)' }} />置顶</span>
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-irony)' }} />素材</span>
          {/* 图的替代路径:同一份节点数据的平铺列表(WebGL 异常/degraded 时仍可浏览与选中) */}
          {materials.length > 0 && (
            <button onClick={() => setView(view === 'graph' ? 'list' : 'graph')} aria-pressed={view === 'list'}
              className="inline-flex items-center gap-1 h-7 px-2 rounded-lg border border-line text-meta text-ink hover:border-brand cursor-pointer transition-colors">
              {view === 'graph' ? <><List size={12} />列表视图</> : <><Network size={12} />图视图</>}
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 relative">
        {err ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-faint">
            <span className="text-f13 text-ink">记忆网络加载失败</span>
            <span className="text-f12">{err}</span>
            <button onClick={() => setRetryTick((t) => t + 1)}
              className="mt-1 h-7 px-3 rounded-lg border border-line text-f12 hover:border-brand cursor-pointer">重试</button>
          </div>
        ) : loading ? (
          <div className="absolute inset-0 flex items-center justify-center gap-2 text-faint text-f13">
            <Loader2 size={16} className="animate-spin" /> 加载素材…
          </div>
        ) : materials.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 text-faint">
            <span className="text-f13 text-ink">还没有素材</span>
            <span className="text-f12">导入或新建素材后,会在这里连成主编的联想记忆网。</span>
          </div>
        ) : view === 'list' ? (
          /* 平铺列表:图的替代路径(数据即已拉取的 graph 节点,不另调 API);点击项 = 点击节点同语义 */
          <div role="region" aria-label="记忆网络素材列表" className="absolute inset-0 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-3 space-y-1">
              {materials.map((m) => (
                <button key={m.id} onClick={() => onSelect?.(m)}
                  className="w-full text-left rounded-lg px-3 py-2 hover:bg-soft transition-colors cursor-pointer border border-transparent hover:border-line">
                  <div className="flex items-center gap-2">
                    {m.pinned && <span className="shrink-0 inline-flex items-center gap-1 text-meta text-brand"><Pin size={11} />置顶</span>}
                    <span className="text-helper text-ink truncate">{m.title || '(无题)'}</span>
                    <span className="ml-auto shrink-0 text-meta text-faint tnum">召回 {Number(m.recall_count) || 0} 次</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            <SigmaContainer
              graph={MultiDirectedGraph}
              settings={sigmaSettings}
              style={{ width: '100%', height: '100%', background: 'transparent' }}
            >
              <GraphContent materials={materials} edges={edges} theme={theme} onPick={pick} />
            </SigmaContainer>

            {(edgeDegraded || truncated || focusId) && (
              <div role="status" data-testid="material-network-status"
                className="absolute top-3 left-3 z-20 max-w-[320px] rounded-lg border border-line bg-surface/95 px-3 py-2 text-f12 shadow-sm">
                {edgeDegraded && (
                  <>
                    <div className="font-medium text-ink">边关系降级</div>
                    <div className="mt-0.5 text-faint leading-snug">
                      {degradedSources.map((s) => `${s.source || 'edges'}: ${s.reason || '加载失败'}`).join('；')}
                    </div>
                  </>
                )}
                {truncated && (
                  <div className="font-medium text-ink mt-0.5" data-testid="material-network-truncated">
                    图已截断(未显示全部节点)
                  </div>
                )}
                {focusId && (
                  <div className="text-faint mt-0.5">
                    聚焦邻域: {focusId}
                    <button type="button" onClick={() => setFocusId(null)}
                      className="ml-2 underline cursor-pointer text-brand">查看全图</button>
                  </div>
                )}
                {edgeDegraded && (
                  <button onClick={() => setView('list')}
                    className="mt-1.5 inline-flex items-center gap-1 h-7 px-2 rounded-md border border-line text-meta text-ink hover:border-brand cursor-pointer transition-colors">
                    <List size={12} />改用列表浏览
                  </button>
                )}
              </div>
            )}

            <div className="absolute bottom-3 left-3 z-10 text-meta text-faint/70 max-w-[240px] leading-snug pointer-events-none">
              节点=素材(大小随召回次数),边=联想(语义近邻)。
            </div>
            <div className="absolute bottom-3 right-3 z-10 text-meta text-faint/80 pointer-events-none">点击节点查看 / 选中素材</div>

            {picked && <PickedCard m={picked} onOpen={() => onSelect?.(picked)} onClose={() => setPicked(null)} />}
          </>
        )}
      </div>
    </div>
  )
}
