/**
 * 伏笔/母题 · 列表栏分组过滤（与 PromiseDetailPane / MotifDetailPane 同源规则）。
 * 纯函数：配置分组 id/ref → 条目列表。业务数据必须来自 API live payload。
 */

export function filterPromiseRows(ledger, ref, seq) {
  if (!ledger || typeof ledger !== 'object') return []
  const open = Array.isArray(ledger.open) ? ledger.open : []
  const closed = Array.isArray(ledger.closed) ? ledger.closed : []
  const herring = Array.isArray(ledger.red_herring) ? ledger.red_herring : []
  const abandoned = Array.isArray(ledger.abandoned) ? ledger.abandoned : []
  if (ref === 'payoff' && seq != null) {
    return [...open, ...closed].filter((p) => Number(p.payoff_chapter) === Number(seq))
  }
  if (ref === 'setup' && seq != null) {
    return [...open, ...closed].filter((p) => Number(p.setup_chapter) === Number(seq))
  }
  if (ref === 'overdue') {
    return open.filter((p) => p.overdue || p.window?.state === 'overdue')
  }
  if (ref === 'open') return open
  if (ref === 'done') return closed
  if (ref === 'abandoned') return abandoned
  return [...open, ...closed, ...herring, ...abandoned]
}

export function promiseItemNode(p, seq, groupId) {
  const pid = String(p.id || p.promise_id || '').replace(/^promise:/, '')
  const text = (p.text || p.title || pid || '未命名伏笔').trim()
  return {
    id: `promise:${pid}`,
    type: 'promise',
    capability: 'promise',
    ref: pid,
    label: text.slice(0, 48) + (text.length > 48 ? '…' : ''),
    meta: {
      seq,
      group: groupId,
      setup_chapter: p.setup_chapter,
      payoff_chapter: p.payoff_chapter,
      status: p.status,
      overdue: !!(p.overdue || p.window?.state === 'overdue'),
    },
  }
}

const MOTIF_VIEW_KEYS = new Set(['chapter', 'thin', 'volume', 'book', 'repeat'])

export function normMotifId(id) {
  return String(id ?? '').replace(/^motif:/, '')
}

/**
 * @param {{ motifs: array, instances?: array, schedule?: object|null }} state
 * @param {string} ref - chapter|thin|volume|book|repeat
 * @param {number|null} seq
 */
export function filterMotifRows(state, ref, seq) {
  if (!state || typeof state !== 'object') return []
  const motifsIn = Array.isArray(state.motifs) ? state.motifs : []
  const instances = Array.isArray(state.instances) ? state.instances : []
  const heatById = new Map()
  for (const r of (state.schedule?.rows || [])) {
    heatById.set(normMotifId(r.id), r)
  }
  const motifs = motifsIn.map((m) => {
    const h = heatById.get(normMotifId(m.id))
    return h ? { ...m, heat: h.heat, streak: h.streak, gap: h.gap, last_touch: h.last_touch } : m
  })
  const evById = new Map()
  for (const i of instances) {
    evById.set(normMotifId(i.motif_id), i.evidence)
  }
  const withEv = (list) => list.map((m) => ({
    ...m,
    evidence: evById.get(normMotifId(m.id)),
  }))
  if (ref === 'chapter') {
    return withEv(motifs.filter((m) => evById.has(normMotifId(m.id))))
  }
  if (ref === 'thin') {
    return withEv(motifs.filter((m) => !m.theme && !m.unfolding))
  }
  if (ref === 'book') return withEv(motifs)
  if (ref === 'volume') {
    const scoped = motifs.filter((m) => (
      m.tier === 'volume' || (m.scope != null && String(m.scope).trim() !== '')
      || m.level === 'volume' || m.volume != null
    ))
    if (scoped.length) return withEv(scoped)
    const touched = motifs.filter((m) => Number(m.hit_count || 0) > 0 || evById.has(normMotifId(m.id)))
    return withEv(touched.length ? touched : motifs)
  }
  if (ref === 'repeat') {
    return withEv(motifs.filter((m) => (
      m.heat === 'hot' || m.repeat || m.overused || m.risk === 'repeat'
      || Number(m.hit_count || 0) > 3
    )))
  }
  if (ref != null && ref !== '' && !MOTIF_VIEW_KEYS.has(ref)) {
    const want = normMotifId(ref)
    return withEv(motifs.filter((m) => (
      normMotifId(m.id) === want || m.name === ref || m.name === want
    )))
  }
  return withEv(motifs)
}

export function motifItemNode(m, seq, groupId) {
  const mid = normMotifId(m.id || m.name)
  const name = (m.name || mid || '未命名母题').trim()
  return {
    id: `motif:${mid}`,
    type: 'motif',
    capability: 'motif',
    ref: mid,
    label: name.slice(0, 48) + (name.length > 48 ? '…' : ''),
    meta: {
      seq,
      group: groupId,
      heat: m.heat,
      hit_count: m.hit_count,
      theme: m.theme,
    },
  }
}

export { MOTIF_VIEW_KEYS }
