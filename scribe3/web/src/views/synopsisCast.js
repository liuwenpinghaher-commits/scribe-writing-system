const IMPORTANCE_ALIASES = {
  protagonist: 'protagonist',
  主角: 'protagonist',
  major: 'major',
  主要: 'major',
  主要角色: 'major',
  重要配角: 'major',
  main: 'major',
  lead: 'major',
  primary: 'major',
  核心: 'major',
  minor: 'minor',
  配角: 'minor',
  background: 'background',
  龙套: 'background',
  extra: 'extra',
}

const MAIN_CAST = new Set(['protagonist', 'major', 'main', 'lead', 'primary'])

export function normalizeImportance(imp) {
  const s = String(imp || '').trim()
  if (!s) return ''
  if (IMPORTANCE_ALIASES[s]) return IMPORTANCE_ALIASES[s]
  const low = s.toLowerCase()
  if (IMPORTANCE_ALIASES[low]) return IMPORTANCE_ALIASES[low]
  return low
}

export function isMainCastImportance(imp) {
  const n = normalizeImportance(imp)
  return !!n && (MAIN_CAST.has(n) || n === 'protagonist' || n === 'major')
}

export function characterWant(entity) {
  return String(entity?.surface_goal || entity?.deep_need || '').trim()
}

export function portraitCast(entities) {
  const chars = (Array.isArray(entities) ? entities : []).filter((e) => e?.kind === 'character')
  const mains = []
  const rest = []
  for (const c of chars) {
    if (isMainCastImportance(c.importance)) mains.push(c)
    else rest.push(c)
  }
  const ordered = [...mains, ...rest]
  const shown = ordered.slice(0, 12)
  return { shown, hidden: Math.max(0, ordered.length - shown.length), total: ordered.length }
}

export function ruleLine(rule) {
  const name = String(rule?.name || '').trim()
  const cost = String(rule?.cost || '').trim()
  if (cost) return { name, detail: cost }
  const lims = Array.isArray(rule?.limitations) ? rule.limitations : []
  const first = String(lims[0] || '').trim()
  return { name, detail: first }
}

export function motifLine(motif) {
  const name = String(motif?.name || '').trim()
  const one = String(motif?.theme || motif?.unfolding || '').trim()
  return { id: motif?.id, name, one }
}

export function openLedgerSummary(led) {
  const open = Array.isArray(led?.open) ? led.open : []
  const overdue = Number(led?.audit?.overdue_count)
  const overdueN = Number.isFinite(overdue)
    ? overdue
    : open.filter((p) => p?.window?.state === 'overdue' || p?.overdue).length
  const items = open.slice(0, 5).map((p) => {
    const text = String(p?.text || p?.summary || '').trim()
    return text.length > 40 ? `${text.slice(0, 40)}…` : text
  }).filter(Boolean)
  return { n: open.length, overdueN, items }
}
