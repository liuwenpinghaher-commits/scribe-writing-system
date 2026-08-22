/** 统一错误形状：detail 可能是字符串或 {code, message}。 */
export function httpErrorMessage(e, fallback = '') {
  const d = e?.body?.detail
  if (d && typeof d === 'object') {
    return String(d.message || d.code || fallback || e?.message || '')
  }
  if (typeof d === 'string' && d.trim()) return d
  return String(e?.message || fallback || '')
}

export function guideMissingLine(ev) {
  const blob = [
    ev?.payload?.name,
    ev?.payload?.tag,
    ev?.actual_reason,
    ev?.summary,
  ].map((x) => String(x || '')).join(' ')
  if (blob.includes('codex_recall_empty')) return '本章没对上设定条目'
  return ''
}
