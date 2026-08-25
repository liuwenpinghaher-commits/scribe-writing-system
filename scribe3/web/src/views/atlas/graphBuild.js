import { MultiDirectedGraph } from 'graphology'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import { REL_LABEL, relColor } from '../../lib/relColors'

export function cssVar(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

export function resolveColor(c, theme) {
  if (typeof c === 'string' && c.startsWith('var(')) {
    const m = c.match(/var\((--[a-z-]+)\)/)
    return m ? (theme[m[1]] || theme['--color-faint'] || '#65706a') : (theme['--color-faint'] || '#65706a')
  }
  return c
}

export function readTheme() {
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
  if (n.type === 'faction') return theme['--color-secret'] || '#9c5f86'
  if (n.type === 'item') return theme['--color-line'] || '#8a8070'
  return n.secret ? theme['--color-secret'] : theme['--color-irony']
}

/** 禁止依赖 picked（KD-9：pick 不重跑 forceAtlas2） */
export function buildGraph(data, focus, theme) {
  const g = new MultiDirectedGraph()
  const nodes = data?.nodes || []
  const edges = data?.edges || []
  const N = Math.max(nodes.length, 1)
  nodes.forEach((n, i) => {
    if (g.hasNode(n.id)) return
    const isChar = n.type === 'character'
    const isEntity = n.type === 'faction' || n.type === 'item'
    const isFocus = focus && n.id === focus
    const ang = (i / N) * Math.PI * 2
    g.addNode(n.id, {
      x: Math.cos(ang) * 10,
      y: Math.sin(ang) * 10,
      size: isFocus ? 16 : isChar ? 11 : isEntity ? 9 : 7,
      color: nodeColor(n, theme),
      label: n.label || n.id,
      _type: n.type,
      _secret: !!n.secret,
      _rawlabel: n.label || n.id,
      _focus: !!isFocus,
    })
  })
  if (focus && g.hasNode(focus)) {
    g.setNodeAttribute(focus, 'x', 0)
    g.setNodeAttribute(focus, 'y', 0)
  }
  edges.forEach((e, i) => {
    if (!g.hasNode(e.src) || !g.hasNode(e.dst)) return
    const isKnows = e.rel === 'knows'
    try {
      const w = Number(e.weight)
      const size = Number.isFinite(w) && w > 0
        ? Math.max(0.8, Math.min(6, w * 1.6))
        : (isKnows ? 1 : 2.2)
      g.addEdgeWithKey('e' + i, e.src, e.dst, {
        size,
        color: resolveColor(relColor(e.rel), theme),
        _rel: e.rel,
        _weight: Number.isFinite(w) ? w : 1,
        _directed: e.directed !== false,
        label: isKnows ? '' : `${REL_LABEL[e.rel] || e.rel}${Number.isFinite(w) && w !== 1 ? ` ·${w}` : ''}`,
        type: e.directed === false ? 'line' : 'arrow',
      })
    } catch { /* 重复边忽略 */ }
  })
  if (g.order > 1) {
    const settings = forceAtlas2.inferSettings(g)
    forceAtlas2.assign(g, {
      iterations: Math.min(100, 30 + g.order),
      settings: { ...settings, scalingRatio: 12, gravity: 1.2, slowDown: 2 },
    })
  }
  return g
}
