/**
 * 会话列表纯决策：归档/切换后的「下一个 active」选择；
 * 新建后列表分区（当前 + 其它活跃 + 已归档）。
 * 优先 updated_at 降序；缺省回退 created_at。与创建时间升序列表解耦。
 */

/**
 * @param {Array<{ thread_id: string, status?: string, updated_at?: string, created_at?: string }>} threads
 * @param {string | null | undefined} excludeId 刚归档/离开的线程
 * @returns {object | null}
 */
export function pickLatestActiveThread(threads, excludeId) {
  const list = Array.isArray(threads) ? threads : []
  const candidates = list.filter(
    (t) => t && t.status === 'active' && t.thread_id && t.thread_id !== excludeId,
  )
  if (!candidates.length) return null
  const score = (t) => String(t.updated_at || t.created_at || '')
  return [...candidates].sort((a, b) => {
    const sb = score(b)
    const sa = score(a)
    if (sb !== sa) return sb > sa ? 1 : -1
    // 稳定次键：thread_id 字典序倒序，避免同戳不确定
    return String(b.thread_id).localeCompare(String(a.thread_id))
  })[0]
}

/**
 * 按 recency 排序 active 列表（updated_at 优先）。
 * @param {Array<object>} threads
 * @returns {Array<object>}
 */
export function sortThreadsByRecency(threads) {
  const list = Array.isArray(threads) ? [...threads] : []
  const score = (t) => String(t?.updated_at || t?.created_at || '')
  return list.sort((a, b) => {
    const sb = score(b)
    const sa = score(a)
    if (sb !== sa) return sb > sa ? 1 : -1
    return String(b?.thread_id || '').localeCompare(String(a?.thread_id || ''))
  })
}

/**
 * 新建/列表展示分区：当前会话置顶；其余 active 进「其它」；archived 独立。
 * UI 默认折叠「其它」与「已归档」，保证新建后工作台列表干净。
 *
 * @param {Array<object>} threads
 * @param {string | null | undefined} currentId
 * @returns {{ current: object | null, otherActive: object[], archived: object[] }}
 */
export function partitionThreadList(threads, currentId) {
  const list = Array.isArray(threads) ? threads : []
  const active = list.filter((t) => t && t.status === 'active' && t.thread_id)
  const archived = sortThreadsByRecency(
    list.filter((t) => t && t.status === 'archived' && t.thread_id),
  )
  const curId = currentId || null
  let current = curId
    ? active.find((t) => t.thread_id === curId) || null
    : null
  // 无匹配时不捏造；其它 active 全进 other
  const otherActive = sortThreadsByRecency(
    active.filter((t) => !current || t.thread_id !== current.thread_id),
  )
  // 若 currentId 有但列表尚未含该行（创建后瞬间），合成占位便于 UI 打勾
  if (curId && !current) {
    current = { thread_id: curId, title: '新会话', status: 'active' }
  }
  return { current, otherActive, archived }
}

/**
 * 新建成功后是否应归档「离开的」会话。
 * @param {string | null | undefined} previousId
 * @param {string | null | undefined} newId
 * @returns {boolean}
 */
export function shouldArchivePreviousOnNew(previousId, newId) {
  if (!previousId || !newId) return false
  return String(previousId) !== String(newId)
}
