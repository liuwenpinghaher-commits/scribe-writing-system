/**
 * 设定详情 → Atlas ego focus id。
 * 与 store.graph 节点 id 对齐:role: / fact: / faction: / item:。
 */

function localFromPrefixed(id, prefix) {
  const s = String(id || '')
  if (s.startsWith(`${prefix}:`)) return s.slice(prefix.length + 1)
  return s.includes(':') ? s.split(':').slice(1).join(':') : s
}

/**
 * @param {{ kind?: string, detailType?: string, row?: object, ref?: string }} opts
 * @returns {string|null} focus id 或 null
 */
export function atlasFocusId({ kind, detailType, row, ref } = {}) {
  const k = kind || detailType || ''
  if (k === 'character' || k === 'chars' || k === 'role') {
    const id = row?.id
    if (typeof id === 'string' && id.startsWith('role:')) return id
    const local = localFromPrefixed(id, 'role') || ref || row?.name
    return local ? `role:${local}` : null
  }
  if (k === 'proposition' || k === 'fact' || k === 'facts') {
    const id = row?.id
    if (typeof id === 'string' && id.startsWith('fact:')) return id
    const local = ref || localFromPrefixed(id, 'fact')
    return local ? `fact:${local}` : null
  }
  if (k === 'faction' || k === 'factions') {
    const name = row?.name || ref
    return name ? `faction:${name}` : null
  }
  if (k === 'item' || k === 'items') {
    const name = row?.name || ref
    return name ? `item:${name}` : null
  }
  return null
}

/** 是否展示「在图谱中打开」 */
export function canOpenInAtlas(opts) {
  return Boolean(atlasFocusId(opts))
}
