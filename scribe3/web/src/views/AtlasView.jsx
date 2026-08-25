import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { Loader2 } from 'lucide-react'
import { api } from '../api'
import { useSelection } from '../selectionContext'
import { atlasNavType } from '../lib/atlasNodeDetail.js'
import { atlasEmptyKind, defaultSliceChapter } from '../lib/atlasReadable.js'
import { NodeDetail } from './atlas/NodeDetail.jsx'
import { AtlasToolbar } from './atlas/AtlasToolbar.jsx'
import { AtlasNodeList } from './atlas/AtlasNodeList.jsx'
import { AtlasCanvas } from './atlas/AtlasCanvas.jsx'
import { AtlasEmptyState } from './atlas/AtlasEmptyState.jsx'
import { readTheme } from './atlas/graphBuild.js'

// 知情图：到第 N 章，这个人知道什么。默认列表+抽屉；画布可折。

export function AtlasView({ onNavigateToObject, chapter = null }) {
  const [raw, setRaw] = useState(null)
  const [chars, setChars] = useState([])
  const [focus, setFocus] = useState('')
  const [hop, setHop] = useState(1)
  const [sliceChapter, setSliceChapter] = useState(() => defaultSliceChapter(chapter))
  const [maxChapter, setMaxChapter] = useState(0)
  const [picked, setPicked] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [theme, setTheme] = useState(readTheme)
  const [retryTick, setRetryTick] = useState(0)
  const [showCanvas, setShowCanvas] = useState(false)
  const reqId = useRef(0)
  const retainPickRef = useRef(null)
  const prevGraphDeps = useRef({ focus: '', hop: 1, sliceChapter: defaultSliceChapter(chapter), retryTick: 0 })
  const { setFocus: setBusFocus } = useSelection()

  useEffect(() => {
    setSliceChapter(defaultSliceChapter(chapter))
  }, [chapter])

  const pickNode = useCallback((n) => {
    setPicked(n)
    if (!n) { setBusFocus(null); return }
    const t = atlasNavType(n)
    if (t === 'character') {
      setBusFocus({ type: 'character', id: n.id, label: n.label, origin: 'atlas' })
    } else if (t === 'faction' || t === 'item') {
      setBusFocus({ type: t, id: n.id, label: n.label, origin: 'atlas' })
    } else {
      setBusFocus({ type: 'frame_fact', id: n.id, label: n.secret ? '私密命题' : n.label, payload: { secret: !!n.secret }, origin: 'atlas' })
    }
  }, [setBusFocus])

  const changeHop = useCallback((h, keepPick = true) => {
    if (keepPick && picked) {
      retainPickRef.current = {
        id: picked.id,
        label: picked.label,
        type: picked.type,
        secret: !!picked.secret,
      }
    } else if (!keepPick) {
      retainPickRef.current = null
    }
    setHop(h)
  }, [picked])

  const navToNode = useCallback((n) => {
    const t = atlasNavType(n)
    const panel = (t === 'character' || t === 'faction' || t === 'item') ? 'truth' : undefined
    onNavigateToObject?.({
      id: n.id,
      type: t,
      label: n.secret ? '私密真相' : (n.label || n.id),
      secret: !!n.secret,
      panel,
      meta: panel ? { panel } : undefined,
    })
  }, [onNavigateToObject])

  useEffect(() => {
    const obs = new MutationObserver(() => setTheme(readTheme()))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] })
    return () => obs.disconnect()
  }, [])

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
      setSliceChapter((prev) => {
        if (prev == null || !(max > 0) || prev <= max) return prev
        const d = defaultSliceChapter(chapter)
        return d != null && d <= max ? d : max
      })
    }).catch(() => { if (alive) setMaxChapter(0) })
    api.graph({ limit: 600 }).then((g) => {
      if (!alive) return
      const cs = (g.nodes || []).filter((n) => n.type === 'character')
        .map((n) => ({ id: n.id, label: n.label || n.id }))
      setChars(cs)
      let pendingFocus = ''
      try {
        pendingFocus = sessionStorage.getItem('s3.atlas.focus') || ''
        if (pendingFocus) sessionStorage.removeItem('s3.atlas.focus')
      } catch { /* */ }
      if (pendingFocus) {
        setFocus(pendingFocus)
        return
      }
      if (cs.length) {
        const charIds = new Set(cs.map((c) => c.id))
        const deg = {}
        for (const e of (g.edges || [])) {
          if (charIds.has(e.src)) deg[e.src] = (deg[e.src] || 0) + 1
          if (charIds.has(e.dst)) deg[e.dst] = (deg[e.dst] || 0) + 1
        }
        const central = cs.reduce((best, c) => (deg[c.id] || 0) > (deg[best.id] || 0) ? c : best, cs[0])
        setFocus(central.id)
      } else {
        setRaw(g); setLoading(false)
      }
    }).catch((e) => { if (alive) { setErr(e.message || '加载失败'); setLoading(false) } })
    return () => { alive = false }
  }, [retryTick, chapter])

  useEffect(() => {
    if (!focus) return
    let alive = true
    const myReq = ++reqId.current
    const prev = prevGraphDeps.current
    const hopOnly = prev.focus === focus
      && prev.sliceChapter === sliceChapter
      && prev.retryTick === retryTick
      && prev.hop !== hop
    prevGraphDeps.current = { focus, hop, sliceChapter, retryTick }

    if (!hopOnly) {
      retainPickRef.current = null
      setPicked(null)
      setBusFocus(null)
    } else if (picked && !retainPickRef.current) {
      retainPickRef.current = {
        id: picked.id, label: picked.label, type: picked.type, secret: !!picked.secret,
      }
    }

    setLoading(true); setErr(null)
    const opts = { focus, hop, limit: 300 }
    if (sliceChapter != null) opts.chapter = sliceChapter
    api.graph(opts).then((g) => {
      if (!alive || myReq !== reqId.current) return
      setRaw(g); setLoading(false)
      const retain = retainPickRef.current
      if (hopOnly && retain?.id) {
        const n = (g.nodes || []).find((x) => x.id === retain.id)
        if (n) {
          pickNode({
            id: n.id,
            label: n.label || retain.label,
            type: n.type || retain.type,
            secret: !!n.secret,
          })
        }
        return
      }
      const center = (g.nodes || []).find((x) => x.id === focus)
      if (center) {
        pickNode({
          id: center.id,
          label: center.label || center.id,
          type: center.type,
          secret: !!center.secret,
        })
      }
    }).catch((e) => {
      if (!alive || myReq !== reqId.current) return
      setErr(e.message || '加载失败'); setLoading(false)
    })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus, hop, sliceChapter, retryTick, setBusFocus])

  const stat = useMemo(() => {
    const ns = raw?.nodes || []
    return {
      c: ns.filter((n) => n.type === 'character').length,
      p: ns.filter((n) => n.type === 'proposition').length,
      e: (raw?.edges || []).length,
    }
  }, [raw])

  const onExpandTo = useCallback((id) => {
    retainPickRef.current = null
    setHop(1)
    setFocus(id)
  }, [])

  const present = useMemo(
    () => [...new Set((raw?.edges || []).map((e) => e.rel).filter((r) => r && r !== 'knows'))],
    [raw])

  const focusLabel = chars.find((c) => c.id === focus)?.label
    || (raw?.nodes || []).find((n) => n.id === focus)?.label
    || focus

  const emptyKind = err ? 'error' : atlasEmptyKind(raw, chars)
  const showEmpty = !!err || (!raw && loading) || emptyKind

  return (
    <div className="h-full flex flex-col bg-canvas" data-testid="atlas-view">
      <AtlasToolbar
        focus={focus}
        focusLabel={focusLabel}
        chars={chars}
        hop={hop}
        sliceChapter={sliceChapter}
        maxChapter={maxChapter}
        stat={stat}
        showCanvas={showCanvas}
        onFocus={(id) => { setHop(1); setFocus(id) }}
        onHop={(h) => changeHop(h, true)}
        onSlice={setSliceChapter}
        onToggleCanvas={() => setShowCanvas((v) => !v)}
      />

      <div className="flex-1 min-h-0 flex">
        <AtlasNodeList
          nodes={raw?.nodes || []}
          pickedId={picked?.id}
          onPick={pickNode}
          onOpen={navToNode}
        />
        <div className="flex-1 min-h-0 relative flex">
          {showEmpty ? (
            err ? (
              <AtlasEmptyState kind="error" onRetry={() => setRetryTick((t) => t + 1)} />
            ) : !raw && loading ? (
              <div className="absolute inset-0 flex items-center justify-center gap-2 text-faint text-f13">
                <Loader2 size={16} className="animate-spin" /> 加载子图…
              </div>
            ) : (
              <AtlasEmptyState kind={emptyKind} />
            )
          ) : (
            <>
              {showCanvas ? (
                <AtlasCanvas
                  raw={raw}
                  focus={focus}
                  theme={theme}
                  loading={loading}
                  present={present}
                  onPickNode={pickNode}
                />
              ) : (
                <div className="flex-1 min-h-0 bg-canvas" data-testid="atlas-reading-pane" />
              )}
              <NodeDetail
                node={picked}
                focus={focus}
                hop={hop}
                edges={raw?.edges || []}
                nodes={raw?.nodes || []}
                focusLabel={focusLabel}
                sliceChapter={sliceChapter}
                maxChapter={maxChapter}
                layout={showCanvas ? 'overlay' : 'pane'}
                onExpand={onExpandTo}
                onHopBoost={(h) => changeHop(h, true)}
                onOpenNode={navToNode}
                onClose={() => pickNode(null)}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
