import { showToast } from '../ui/Toast.jsx'

function failText(e) {
  if (!e) return '未知错误'
  const d = e.body?.detail ?? e.detail
  if (typeof d === 'string' && d.trim()) return d
  if (d && typeof d === 'object') return d.message || d.code || e.message || '失败'
  return e.message || String(e)
}

/**
 * 包装一次异步操作：成功/失败都给作者可见的 toast。
 * @param {Promise} promise
 * @param {{ ok?: string, fail?: string }} labels
 */
export async function withFeedback(promise, { ok = '已保存', fail = '操作失败' } = {}) {
  try {
    const r = await promise
    if (ok) showToast(ok, { tone: 'ok' })
    return r
  } catch (e) {
    showToast(`${fail}: ${failText(e)}`, { tone: 'danger' })
    throw e
  }
}
