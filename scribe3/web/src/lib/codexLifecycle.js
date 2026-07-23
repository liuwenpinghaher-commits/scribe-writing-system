/**
 * 设定库生命周期:删除/归档种子后等待落库,再刷新树并退回分类。
 * 审批在主编栏完成;本模块用「批准事件加速 + 轮询探测」双通道。
 */

export const WORLD_WRITE_EVENT = 's3-world-write-approved'
export const CODEX_TREE_REFRESH_EVENT = 's3-codex-tree-refresh'
const PENDING_KEY = 's3.pending.codex_delete'

/** @param {{ objectType: string, objectId: string, label?: string }} p */
export function registerPendingCodexDelete(p) {
  const payload = {
    objectType: String(p.objectType || '').trim(),
    objectId: String(p.objectId || '').trim(),
    label: p.label || '',
    at: Date.now(),
  }
  if (!payload.objectType || !payload.objectId) return null
  try {
    sessionStorage.setItem(PENDING_KEY, JSON.stringify(payload))
  } catch { /* */ }
  return payload
}

export function readPendingCodexDelete() {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function clearPendingCodexDelete() {
  try { sessionStorage.removeItem(PENDING_KEY) } catch { /* */ }
}

/** 主编批准成功 / 工具 written → 广播 */
export function notifyWorldWriteApproved(detail = {}) {
  try {
    window.dispatchEvent(new CustomEvent(WORLD_WRITE_EVENT, { detail: detail || {} }))
  } catch { /* */ }
}

/** 目录/详情:对象已消失,刷新树 */
export function notifyCodexTreeRefresh(detail = {}) {
  try {
    window.dispatchEvent(new CustomEvent(CODEX_TREE_REFRESH_EVENT, { detail: detail || {} }))
  } catch { /* */ }
}

/**
 * 探测对象是否仍存在。不存在 → true(可退回分类)。
 * @param {{ get: (path: string) => Promise<unknown> }} api
 */
export async function isCodexObjectGone(api, objectType, objectId) {
  const ot = String(objectType || '')
  const oid = String(objectId || '')
  if (!ot || !oid) return false
  const path =
    ot === 'role' ? `/characters/${encodeURIComponent(oid)}`
      : ot === 'fact' ? `/facts/${encodeURIComponent(oid)}`
        : ot === 'faction' ? `/factions/${encodeURIComponent(oid)}`
          : ot === 'item' ? `/items/${encodeURIComponent(oid)}`
            : ot === 'term' ? `/terms/${encodeURIComponent(oid)}`
              : ot === 'world_rule' ? `/world-rules/${encodeURIComponent(oid)}`
                : ot === 'promise' ? `/promises/${encodeURIComponent(oid)}`
                  : ot === 'motif' ? `/motifs/${encodeURIComponent(oid)}`
                    : null
  if (!path || typeof api?.get !== 'function') return false
  try {
    const row = await api.get(path)
    // 软归档:记录仍在但 workbench 应视为已撤下
    if (row && (row.archived === true || row.archived === 'true')) return true
    return false
  } catch (e) {
    const st = e?.status ?? e?.body?.status ?? e?.response?.status
    return st === 404
  }
}

/**
 * 轮询直到对象消失或超时。
 * @returns {Promise<'gone'|'timeout'|'aborted'>}
 */
export function watchCodexObjectGone(api, { objectType, objectId }, {
  intervalMs = 1500,
  timeoutMs = 120000,
  signal,
} = {}) {
  return new Promise((resolve) => {
    let stopped = false
    let timer = null
    const t0 = Date.now()

    const finish = (r) => {
      if (stopped) return
      stopped = true
      if (timer != null) clearTimeout(timer)
      window.removeEventListener(WORLD_WRITE_EVENT, onWrite)
      signal?.removeEventListener?.('abort', onAbort)
      resolve(r)
    }

    const onAbort = () => finish('aborted')
    const onWrite = () => { schedule(0) }

    const schedule = (delay) => {
      if (stopped) return
      if (timer != null) clearTimeout(timer)
      timer = setTimeout(run, delay)
    }

    const run = async () => {
      if (stopped) return
      try {
        if (await isCodexObjectGone(api, objectType, objectId)) {
          finish('gone')
          return
        }
      } catch { /* 网络抖动继续 */ }
      if (Date.now() - t0 >= timeoutMs) {
        finish('timeout')
        return
      }
      schedule(intervalMs)
    }

    signal?.addEventListener?.('abort', onAbort)
    window.addEventListener(WORLD_WRITE_EVENT, onWrite)
    if (signal?.aborted) {
      finish('aborted')
      return
    }
    run()
  })
}
