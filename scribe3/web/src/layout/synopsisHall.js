import { entryPatch } from '../context/contextSnapshot'

export const SYNOPSIS_HALL_EVENT = 's3-open-synopsis-hall'

const HUB_VIEWS = new Set(['admin', 'system', 'settings'])

/** 系统中心/设置/管理台时四栏壳未挂载，必须先退出 hub。 */
export function shouldExitHubForSynopsis(sel) {
  if (sel?.mode !== 'view') return false
  return HUB_VIEWS.has(sel.viewKey)
}

/**
 * 总纲专用落地。禁止 planEntryChange / 只改 sel。
 * 三步同一调用内做完：手稿 tab + 空 sel + entryPatch。
 */
export function landSynopsisHall({
  setTab,
  onSelectNode,
  navigate,
  directoryCollapsed,
  expandDirectory,
}) {
  setTab?.('manuscript')
  onSelectNode?.(null)
  navigate?.(entryPatch('manuscript'))
  if (directoryCollapsed) expandDirectory?.()
}

export function dispatchSynopsisHall() {
  try {
    window.dispatchEvent(new CustomEvent(SYNOPSIS_HALL_EVENT))
  } catch { /* */ }
}
