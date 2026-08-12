// 只读 API 回查（验收断言用）。禁止用本模块 POST 正典/正文。

const API = () => process.env.E2E_API || 'http://127.0.0.1:3321'

export async function apiJson(path, { timeoutMs = 30000 } = {}) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const r = await fetch(`${API()}${path}`, { signal: ctrl.signal })
    if (!r.ok) {
      const text = await r.text().catch(() => '')
      throw new Error(`${path} ${r.status} ${text.slice(0, 200)}`)
    }
    return r.json()
  } finally {
    clearTimeout(t)
  }
}

export async function apiJsonSoft(path, fallback = null) {
  try {
    return await apiJson(path)
  } catch {
    return fallback
  }
}

export function listLen(payload) {
  if (Array.isArray(payload)) return payload.length
  if (!payload || typeof payload !== 'object') return 0
  for (const k of ['items', 'characters', 'entities', 'factions', 'rules', 'world_rules',
    'terms', 'motifs', 'promises', 'chapters', 'works', 'results', 'rows']) {
    if (Array.isArray(payload[k])) return payload[k].length
  }
  return 0
}

export async function workStats(work) {
  const works = await apiJson('/works')
  const list = Array.isArray(works) ? works : (works.works || [])
  return list.find((w) => w.slug === work) || null
}

export async function chapterPayload(work, seq) {
  return apiJson(`/chapter?work=${encodeURIComponent(work)}&seq=${seq}`)
}

export async function chapterProseLen(work, seq) {
  try {
    const d = await chapterPayload(work, seq)
    const prose = d.prose || d.body || d.content || ''
    return String(prose).replace(/\s/g, '').length
  } catch {
    return -1
  }
}

export async function listChapters(work) {
  const chs = await apiJson(`/chapters?work=${encodeURIComponent(work)}`)
  return Array.isArray(chs) ? chs : (chs?.chapters || [])
}

export async function fetchIntent(work) {
  return apiJson(`/intent?work=${encodeURIComponent(work)}`)
}

export async function fetchCraftGates({ work, seq } = {}) {
  const qs = new URLSearchParams({ work })
  if (seq != null) qs.set('seq', String(seq))
  return apiJson(`/craft-gates?${qs}`)
}

export async function fetchQualityDashboard(work) {
  return apiJsonSoft(`/quality?work=${encodeURIComponent(work)}`, null)
}

export async function fetchSettingCompleteness(work) {
  return apiJsonSoft(`/setting-completeness?work=${encodeURIComponent(work)}`, null)
}

export async function fetchEntities(work) {
  return apiJsonSoft(`/entities?work=${encodeURIComponent(work)}`, [])
}

export async function fetchFactions(work) {
  return apiJsonSoft(`/factions?work=${encodeURIComponent(work)}`, [])
}

export async function fetchWorldRules(work) {
  return apiJsonSoft(`/world-rules?work=${encodeURIComponent(work)}`, [])
}

export async function fetchItems(work) {
  return apiJsonSoft(`/items?work=${encodeURIComponent(work)}`, [])
}

export async function fetchTerms(work) {
  return apiJsonSoft(`/terms?work=${encodeURIComponent(work)}`, [])
}

export async function fetchMotifs(work) {
  return apiJsonSoft(`/motifs?work=${encodeURIComponent(work)}`, [])
}

export async function fetchPromises(work) {
  return apiJsonSoft(`/promises?work=${encodeURIComponent(work)}`, [])
}

export async function fetchRecall(work, q) {
  const qs = new URLSearchParams({ work, q: q || '灰契' })
  return apiJsonSoft(`/recall?${qs}`, null)
}

export async function fetchFrame(work, { seq, focalizer } = {}) {
  const qs = new URLSearchParams({ work })
  if (seq != null) qs.set('seq', String(seq))
  if (focalizer) qs.set('focalizer', focalizer)
  return apiJsonSoft(`/frame?${qs}`, null)
}

export async function fetchCanonCandidates(work) {
  return apiJsonSoft(`/canon/candidates?work=${encodeURIComponent(work)}`, null)
}

export async function fetchCanonAnalysis(work, seq) {
  const qs = new URLSearchParams({ work })
  if (seq != null) qs.set('seq', String(seq))
  return apiJsonSoft(`/canon/analysis?${qs}`, null)
}

export async function fetchGraph(work) {
  return apiJsonSoft(`/graph?work=${encodeURIComponent(work)}`, null)
}

/** 定稿门：优先 post-finalize-report 只读信息；无统一 GET 时用 craft-gates + quality 合成 */
export async function evaluateFinalizeGateReadOnly(work) {
  const gates = await fetchCraftGates({ work })
  const quality = await fetchQualityDashboard(work)
  const stats = await workStats(work)
  const blocking = []
  if (!gates?.gate_a?.ok) blocking.push(...(gates?.gate_a?.blocking || ['GATE_A']))
  const wordCount = stats?.word_count || quality?.total_words || 0
  const chapterCount = stats?.chapter_count || (quality?.chapters || []).length || 0
  return {
    ok: blocking.length === 0 && wordCount >= Number(process.env.E2E_WORD_TARGET || 50000),
    allowed: blocking.length === 0,
    code: blocking.length ? 'blocked' : 'ok',
    blocking,
    word_count: wordCount,
    chapter_count: chapterCount,
    gate_a: gates?.gate_a,
    quality_summary: quality ? {
      total_words: quality.total_words,
      open_promises: quality.foreshadow?.open,
      closed_promises: quality.foreshadow?.closed,
    } : null,
  }
}
