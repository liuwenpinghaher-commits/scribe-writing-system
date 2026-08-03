/**
 * 全局 fetch 拦截：为同源 /api 请求附加 Bearer token，并在 401 时清 token + 通知登录页。
 * 在 main.jsx 最早 import，保证 api.js 的 fetch 全部经过此处。
 * EventSource 不能设 header → 用 withTokenQuery 把 token 挂到 ?token=（后端桥接中间件会注入 Authorization）。
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

/**
 * 给 EventSource / 裸 URL 追加 token query（浏览器 EventSource 无法设 Authorization）。
 * 已有 token= 时不重复；无 token 时原样返回（本地放行）。
 */
export function withTokenQuery(url) {
  const t = getApiToken()
  if (!t || !url) return url
  try {
    // 相对路径也可用：以当前 origin 为 base 解析
    const u = new URL(url, typeof location !== 'undefined' ? location.origin : 'http://local')
    if (!u.searchParams.has('token')) u.searchParams.set('token', t)
    // 若入参是相对路径，返回 pathname+search+hash；绝对 URL 原样绝对
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
