/**
 * 卷 PR-4：未分卷章过多时的软提示（后建后整理，非强制先建卷）。
 * 永不 GATE-B / 永不挡存写。
 */

export const VOLUME_SOFT_HINT_DISMISS_KEY = 's3.volume.soft_hint_dismissed'
/** 默认阈值：未分卷章数 ≥ N 才提示（人决未锁死时可配置） */
export const VOLUME_SOFT_HINT_DEFAULT_N = 12

/**
 * @param {{ unassignedCount: number, threshold?: number, dismissed?: boolean }} p
 * @returns {boolean}
 */
export function shouldShowVolumeOrganizeHint({
  unassignedCount,
  threshold = VOLUME_SOFT_HINT_DEFAULT_N,
  dismissed = false,
} = {}) {
  if (dismissed) return false
  const n = Number(unassignedCount) || 0
  const th = Math.max(1, Number(threshold) || VOLUME_SOFT_HINT_DEFAULT_N)
  return n >= th
}

/** 跨弧 soft-suggest：超期伏笔 ≥1 时提示按卷复盘（≠ GATE-B） */
export function shouldShowCrossArcVolumeHint({
  overduePromiseCount = 0,
  dismissed = false,
} = {}) {
  if (dismissed) return false
  return (Number(overduePromiseCount) || 0) >= 1
}

export function loadVolumeSoftHintDismissed(work) {
  try {
    const k = work ? `${VOLUME_SOFT_HINT_DISMISS_KEY}:${work}` : VOLUME_SOFT_HINT_DISMISS_KEY
    return localStorage.getItem(k) === '1'
  } catch {
    return false
  }
}

export function saveVolumeSoftHintDismissed(work, dismissed = true) {
  try {
    const k = work ? `${VOLUME_SOFT_HINT_DISMISS_KEY}:${work}` : VOLUME_SOFT_HINT_DISMISS_KEY
    if (dismissed) localStorage.setItem(k, '1')
    else localStorage.removeItem(k)
  } catch { /* */ }
}
