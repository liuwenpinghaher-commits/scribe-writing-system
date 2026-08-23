/**
 * S-8 / 剩余债：LIVE 事件是否应触发某面板刷新。
 * - 仅有 table：兼容旧 SSE，对该表相关面板刷新
 * - 有 id：尽量只刷新匹配记录（章号 / record id）
 * - detail.tb 与 detail.table 等价（兼容旧推送）
 */

function liveTable(detail) {
  if (!detail) return null
  return detail.table || detail.tb || null
}

/** @param {object|null|undefined} detail s3-live detail / SSE JSON */
export function liveTouchesTable(detail, tables) {
  if (!detail) return true
  const t = liveTable(detail)
  if (t === '_reconnect') return true
  if (!t || t === '_init') return t !== '_init' ? true : false
  const set = Array.isArray(tables) ? tables : [tables]
  return set.includes(t)
}

/**
 * 章级面板：table=chapter 时，若带 id 且能解析出章号且不等于当前 seq → 不刷新。
 */
export function liveTouchesChapter(detail, seq) {
  if (!detail) return true
  const t = liveTable(detail)
  if (t && t !== 'chapter' && t !== '_init') return false
  if (t === '_init') return false
  if (seq == null || detail.id == null || detail.id === '') return true
  const n = parseChapterSeqFromLiveId(detail.id)
  if (n == null) return true
  return Number(n) === Number(seq)
}

export function parseChapterSeqFromLiveId(id) {
  const s = String(id || '')
  // chapter:12 / chapter:〔12〕 / record style
  let m = s.match(/chapter[:：](\d+)/i)
  if (m) return parseInt(m[1], 10)
  m = s.match(/^(\d+)$/)
  if (m) return parseInt(m[1], 10)
  return null
}
