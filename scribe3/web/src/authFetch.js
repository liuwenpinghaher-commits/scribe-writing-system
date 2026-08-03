/**
 * 全局 fetch：同源 API 带 credentials（Cookie 会话），401 时通知登录页。
 * L1 主路径不再把 SCRIBE3_API_TOKEN 写入 localStorage 作为门禁
 * （见 docs/L1-AUTH-ISOLATION.md）。
 *
 * EventSource：浏览器会自动带同站 Cookie；withTokenQuery 仅保留对旧机器 token 的兼容，
 * 无 localStorage token 时原样返回 URL。
 */

const LEGACY_TOKEN_KEY = 's3-api-token'

/** @deprecated L1 主路径不使用；仅兼容旧书签/机器调试 */
export function getApiToken() {
  try { return localStorage.getItem(LEGACY_TOKEN_KEY) || '' } catch { return '' }
}

/** @deprecated */
export function setApiToken(t) {
  try {
    if (t) localStorage.setItem(LEGACY_TOKEN_KEY, t)
    else localStorage.removeItem(LEGACY_TOKEN_KEY)
  } catch { /* */ }
}

export function clearApiToken() {
  setApiToken('')
}

export async function logoutSession() {
  const base = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) || '/api'
  try {
    await fetch(base + '/auth/logout', { method: 'POST', credentials: 'include' })
  } catch { /* */ }
  clearApiToken()
  notifyAuthRequired()
}

function notifyAuthRequired() {
  try { window.dispatchEvent(new CustomEvent('s3-auth-required')) } catch { /* */ }
}

/**
 * 兼容旧 SSE：若仍有 legacy token 则挂 ?token=；Cookie 会话下无需 query。
 */
export function withTokenQuery(url) {
  const t = getApiToken()
  if (!t || !url) return url
  try {
    const u = new URL(url, typeof location !== 'undefined' ? location.origin : 'http://local')
    if (!u.searchParams.has('token')) u.searchParams.set('token', t)
    if (/^https?:\/\//i.test(url)) return u.toString()
    return u.pathname + u.search + u.hash
  } catch {
    const sep = url.includes('?') ? '&' : '?'
    return url + sep + 'token=' + encodeURIComponent(t)
  }
}

const _fetch = globalThis.fetch.bind(globalThis)

globalThis.fetch = function authFetch(input, init) {
  const url = typeof input === 'string' ? input : (input && input.url) || ''
  const base = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) || '/api'
  const isApi = url.startsWith(base) || url.startsWith('/api') || (base.startsWith('http') && url.startsWith(base))
  if (!isApi) return _fetch(input, init)

  const headers = new Headers((init && init.headers) || (typeof input !== 'string' && input.headers) || {})
  // Optional legacy machine token only if explicitly still in storage (not primary UX)
  const t = getApiToken()
  if (t && !headers.has('Authorization')) headers.set('Authorization', 'Bearer ' + t)

  const nextInit = {
    ...(init || {}),
    headers,
    credentials: (init && init.credentials) || 'include',
  }
  return _fetch(input, nextInit).then((res) => {
    if (res.status === 401) {
      clearApiToken()
      notifyAuthRequired()
    }
    return res
  })
}
