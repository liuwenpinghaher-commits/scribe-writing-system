/** 主编栏中间态。talk=普通对话；select=选择环作业；pilot=驾驶作业。 */
export const CHIEF_MODES = ['talk', 'select', 'pilot']

/** 旧右栏 tab / 指令 → 主编 mode。未命中则只当普通 tab。 */
export const RIGHT_TAB_TO_MODE = {
  selection: 'select',
  select: 'select',
  pilot: 'pilot',
}

export function normalizeChiefMode(raw) {
  return CHIEF_MODES.includes(raw) ? raw : 'talk'
}

/**
 * s3-right-tab / 存量 s3.rightTab 兼容。
 * selection|pilot → 打开主编 tab，并带上 mode。
 */
export function resolveRightTab(detail) {
  const raw = String(detail || 'chief').trim() || 'chief'
  const mode = RIGHT_TAB_TO_MODE[raw]
  if (mode) return { tab: 'chief', mode }
  return { tab: raw, mode: null }
}
