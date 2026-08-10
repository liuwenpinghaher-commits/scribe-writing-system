/** 章工作台渐进披露密度（仅 localStorage，禁止 Hermes USER.md / author_prefs）。
 * key: s3.ia.density · 值: essential | standard | full
 * 未设置时默认 essential（人决 KD-IA-13）。
 */
export const IA_DENSITY_KEY = 's3.ia.density'
export const IA_DENSITY_VALUES = ['essential', 'standard', 'full']

export function loadIaDensity() {
  try {
    const v = localStorage.getItem(IA_DENSITY_KEY)
    if (v === 'essential' || v === 'standard' || v === 'full') return v
  } catch { /* */ }
  return 'essential'
}

export function saveIaDensity(next) {
  const v = IA_DENSITY_VALUES.includes(next) ? next : 'essential'
  try { localStorage.setItem(IA_DENSITY_KEY, v) } catch { /* */ }
  return v
}

/** essential：隐藏评分卡/经验复盘；standard/full：全部辅助面 */
export function auxVisibleForDensity(density, auxKey) {
  if (auxKey === 'brief' || auxKey === 'frame') return true
  if (auxKey === 'northstar' || auxKey === 'pressure') {
    return density === 'standard' || density === 'full'
  }
  return true
}

/**
 * 章节信息里的「本卷卷纲摘要」peek（KD-VOL-8）。
 * essential → false；standard/full → true。Binder 卷节点不受此限制。
 */
export function volumeMetaPeekVisible(density) {
  const d = density || loadIaDensity()
  return d === 'standard' || d === 'full'
}

/** full 密度可挂 GET /volume/review 只读摘要（可选） */
export function volumeReviewVisible(density) {
  const d = density || loadIaDensity()
  return d === 'full'
}
