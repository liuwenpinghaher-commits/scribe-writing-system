/**
 * 全局 fetch 拦截：为同源 /api 请求附加 Bearer token，并在 401 时清 token + 通知登录页。
 * 在 main.jsx 最早 import，保证 api.js 的 fetch 全部经过此处。
 * EventSource 仍走 query token（见后续 withTokenQuery 或后端 cookie）。
 */
const TOKEN_KEY = 's3-api-token'

export function getApiToken() {
  try { return localStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
}

export function setApiToken(t) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* */ }
}

export function clearApiToken() {
  setApiToken('')
}

function notifyAuthRequired() {
  try { window.dispatchEvent(new CustomEvent('s3-auth-required')) } catch { /* */ }
}

const _fetch = globalThis.fetch.bind(globalThis)

globalThis.fetch = function authFetch(input, init) {
  const url = typeof input === 'string' ? input : (input && input.url) || ''
  // 只拦截本应用 API（同源 /api 或 VITE_API_BASE）
  const base = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) || '/api'
  const isApi = url.startsWith(base) || url.startsWith('/api') || (base.startsWith('http') && url.startsWith(base))
  if (!isApi) return _fetch(input, init)

  const headers = new Headers((init && init.headers) || (typeof input !== 'string' && input.headers) || {})
  const t = getApiToken()
  if (t && !headers.has('Authorization')) headers.set('Authorization', 'Bearer ' + t)

  const nextInit = { ...(init || {}), headers }
  return _fetch(input, nextInit).then((res) => {
    if (res.status === 401) {
      clearApiToken()
      notifyAuthRequired()
    }
    return res
  })
}
