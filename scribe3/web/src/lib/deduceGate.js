/**
 * 演绎软门 / 角色 id 归一 / stale 检测（与后端 scribe3.deduce_helpers 对齐）。
 * 纯函数，无 IO。
 */

export const DEDUCTION_HEADINGS = [
  '看到/听到',
  '知道',
  '以为(误读)',
  '做了/说了',
  '没察觉的',
]

export function normalizeRoleId(value) {
  if (value == null) return ''
  const s = String(value).trim()
  if (!s) return ''
  const bare = s.includes(':') ? s.split(':').slice(1).join(':').trim() : s
  if (!bare) return ''
  return `role:${bare}`
}

export function normalizeInvolved(ids) {
  const out = []
  const seen = new Set()
  for (const raw of ids || []) {
    const nid = normalizeRoleId(raw)
    if (!nid || seen.has(nid)) continue
    seen.add(nid)
    out.push(nid)
  }
  return out
}

export function truthRevision(ch) {
  const raw = ch?.scene_truth_revision
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0
}

export function isStaleDeduction(d, currentRev) {
  if (!d || typeof d !== 'object') return false
  const prose = String(d.prose || '').trim()
  if (!prose) return false
  const cur = Number(currentRev) || 0
  if (!('based_on_truth_rev' in d) || d.based_on_truth_rev == null) {
    return cur > 0
  }
  const based = Number(d.based_on_truth_rev)
  if (!Number.isFinite(based)) return true
  return based !== cur
}

export function deductionMap(deds) {
  const out = {}
  for (const raw of deds || []) {
    if (!raw || typeof raw !== 'object') continue
    const cid = normalizeRoleId(raw.character_id || raw.character || raw.role)
    if (!cid) continue
    out[cid] = { ...raw, character_id: cid }
  }
  return out
}

export function hasFiveLayerHeadings(prose) {
  const text = prose || ''
  return DEDUCTION_HEADINGS.every((h) => text.includes(`### ${h}`))
}

/**
 * @returns {{ emptyTruth: boolean, missing: string[], stale: string[], weakLayers: string[], truthRevision: number, needsAttention: boolean }}
 */
export function softGateIssues(ch) {
  const meta = ch || {}
  const rev = truthRevision(meta)
  const truth = String(meta.scene_truth || '').trim()
  const involved = normalizeInvolved(meta.involved_characters || [])
  const dmap = deductionMap(meta.deductions || [])
  const missing = []
  const stale = []
  const weakLayers = []
  for (const id of involved) {
    const d = dmap[id]
    const prose = String(d?.prose || '').trim()
    if (!prose) {
      missing.push(id)
      continue
    }
    if (isStaleDeduction(d, rev)) stale.push(id)
    if (!hasFiveLayerHeadings(prose)) weakLayers.push(id)
  }
  return {
    emptyTruth: !truth,
    missing,
    stale,
    weakLayers,
    truthRevision: rev,
    needsAttention: Boolean((!truth && involved.length) || missing.length || stale.length),
  }
}

/** 简短中文摘要，供 toast / banner。 */
export function softGateSummary(issues) {
  if (!issues?.needsAttention) return ''
  const parts = []
  if (issues.emptyTruth) parts.push('场景真相为空')
  if (issues.missing?.length) parts.push(`${issues.missing.length} 个角色未演绎`)
  if (issues.stale?.length) parts.push(`${issues.stale.length} 个投影相对真相已过期`)
  return parts.join('；') || '演绎未齐'
}
