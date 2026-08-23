/**
 * 时间线工艺辅助：跳章窗口、因果弧、选中联动。纯函数，不碰 vis 实例。
 */

export function jumpWindowForChapter(n) {
  const N = Math.max(1, Math.floor(Number(n) || 0))
  if (!N) return null
  return { n: N, from: Math.max(1, N - 5), to: N + 5 }
}

function causalId(c) {
  if (c == null) return ''
  if (typeof c === 'string') return c
  return String(c.id || '')
}

export function causalArcsFromItems(visItems) {
  const arcs = []
  for (const it of visItems || []) {
    if (it._cat !== 'event') continue
    const dest = Number(it._raw?.story_chapter ?? it._raw?.chapter)
    for (const c of it._raw?.refs?.causal_in || []) {
      const src = Number(typeof c === 'object' ? c.chapter : NaN)
      if (Number.isFinite(src) && Number.isFinite(dest) && src !== dest) {
        arcs.push({ from: src, to: dest, fromId: causalId(c), toId: String(it._raw?.id || '') })
      }
    }
  }
  return arcs
}

/** 选中事件时：前驱因果 + 同角色弧光。 */
export function relatedVisIds(selected, visItems) {
  if (!selected || !Array.isArray(visItems)) return []
  const raw = selected.raw || {}
  const cat = selected.cat
  const causalIds = new Set((raw.refs?.causal_in || []).map(causalId).filter(Boolean))
  const chars = new Set(
    [...(raw.refs?.subj || []), ...(raw.refs?.obj || []), ...(raw.lane_keys || []), raw.refs?.character]
      .filter(Boolean)
      .map(String),
  )
  const out = []
  for (const it of visItems) {
    if (!it?.id || it.id === selected.id) continue
    const r = it._raw || {}
    if (cat === 'event') {
      if (causalIds.has(String(r.id))) out.push(it.id)
      if (it._cat === 'arc') {
        const who = String(r.refs?.character || (r.lane_keys || [])[0] || '')
        if (who && chars.has(who)) out.push(it.id)
      }
    } else if (cat === 'arc' && it._cat === 'event') {
      const evChars = [...(r.refs?.subj || []), ...(r.lane_keys || [])].map(String)
      if (evChars.some((c) => chars.has(c))) out.push(it.id)
    }
  }
  return out
}

export function withHighlightClass(className, on) {
  const cls = String(className || '')
  const stripped = cls.replace(/\b(vis-highlighted|tl-related)\b/g, '').replace(/\s+/g, ' ').trim()
  if (!on) return stripped
  return `${stripped} vis-highlighted tl-related`.trim()
}
