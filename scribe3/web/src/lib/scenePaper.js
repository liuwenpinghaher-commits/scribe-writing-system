/**
 * 与 scribe3.story_constraint_prompt.load_evidence_must_show 同序：
 * bindings.evidence_must_show → pressure.irreversible → stairs
 */
export function loadEvidenceMustShow(chapter) {
  const c = chapter && typeof chapter === 'object' ? chapter : {}
  const contract = c.narrative_contract && typeof c.narrative_contract === 'object'
    ? c.narrative_contract
    : c
  const bindings = contract && typeof contract.bindings === 'object' ? contract.bindings : {}
  const traces = []
  const raw = bindings.evidence_must_show
  if (Array.isArray(raw)) {
    for (const x of raw) {
      const t = String(x || '').trim()
      if (t) traces.push(t)
    }
  } else if (raw && String(raw).trim()) {
    traces.push(String(raw).trim())
  }
  if (traces.length) return traces.slice(0, 3)
  const pd = c.pressure_drive && typeof c.pressure_drive === 'object' ? c.pressure_drive : {}
  const irr = pd.irreversible && typeof pd.irreversible === 'object' ? pd.irreversible : null
  if (irr) {
    const ev = irr.evidence_must_show
    if (Array.isArray(ev)) {
      const out = ev.map((x) => String(x || '').trim()).filter(Boolean)
      if (out.length) return out.slice(0, 3)
    } else if (ev && String(ev).trim()) {
      return [String(ev).trim()]
    }
  }
  const stairs = Array.isArray(pd.progress && pd.progress.stairs)
    ? pd.progress.stairs
    : (Array.isArray(pd.stairs) ? pd.stairs : null)
  if (stairs) {
    const out = []
    for (const s of stairs) {
      if (s && typeof s === 'object') {
        const t = String(s.evidence_must_show || '').trim()
        if (t) out.push(t)
      }
    }
    if (out.length) return out.slice(0, 3)
  }
  return []
}

export function scenePaperView(chapter) {
  const c = chapter && typeof chapter === 'object' ? chapter : {}
  const nc = c.narrative_contract && typeof c.narrative_contract === 'object'
    ? c.narrative_contract
    : {}
  const title = String(c.title || '').trim()
  const seq = c.seq
  const spine = c.chapter_spine && typeof c.chapter_spine === 'object' ? c.chapter_spine : {}
  const setting = String(spine.setting || '').trim()
  const must = String(spine.goal || nc.turn || nc.desire || '').trim()
  const traces = loadEvidenceMustShow(c)
  return {
    day: setting || title || (seq != null ? `第 ${seq} 章` : '第 N 章'),
    mustHappen: must.slice(0, 24),
    mustHappenEmpty: !must,
    trace: traces[0] || '',
    traces,
    desire: String(nc.desire || '').trim(),
    obstacle: String(nc.obstacle || '').trim(),
    turn: String(nc.turn || '').trim(),
    cost: String(nc.cost || '').trim(),
  }
}
