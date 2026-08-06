/**
 * 会话列表纯决策：归档/切换后的「下一个 active」选择。
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
