/** 卷契约只读面。作者看不见的机制等于不存在。 */

function items(raw) {
  const out = []
  for (const item of raw || []) {
    if (typeof item === 'string') {
      const t = item.trim()
      if (t) out.push({ oid: t, why: '', key: '', what: t })
      continue
    }
    if (!item || typeof item !== 'object') continue
    const oid = String(item.oid || item.id || item.name || '').trim()
    const why = String(item.why || '').trim()
    const key = String(item.key || '').trim()
    const what = String(item.what || item.text || '').trim()
    if (oid || key || what) out.push({ oid, why, key, what })
  }
  return out
}

export function parseVolumeCharter(raw) {
  if (raw == null || raw === '') return null
  let c = raw
  if (typeof raw === 'string') {
    try {
      c = JSON.parse(raw)
    } catch {
      return null
    }
  }
  if (!c || typeof c !== 'object') return null
  const duty = String(c.duty || '').trim()
  const introduces = items(c.introduces)
  const thickens = items(c.thickens)
  const pays = items(c.pays).map((x) => x.what || x.oid)
  const ke = c.knowledge_end || {}
  const mustKnow = items(ke.must_know)
  const mustNotKnow = items(ke.must_not_know)
  const rng = Array.isArray(c.chapter_range) && c.chapter_range.length === 2
    ? c.chapter_range
    : null
  if (!duty && !introduces.length && !thickens.length && !pays.length
      && !mustKnow.length && !mustNotKnow.length) {
    return null
  }
  return { duty, introduces, thickens, pays, mustKnow, mustNotKnow, chapter_range: rng }
}
