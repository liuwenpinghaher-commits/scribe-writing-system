// 会话摘录 e2e：闸关时 POST /author/session-clips 可落库；POST /materials 仍 403。
// 默认打 Vite 同源代理 /api → :3321；也可用 E2E_API=http://127.0.0.1:3321 直连。
const API = (process.env.E2E_API || 'http://127.0.0.1:3311/api').replace(/\/$/, '')
const WORK = process.env.E2E_WORK || 'main'

async function j(method, path, body) {
  const r = await fetch(API + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await r.text()
  let data
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  return { status: r.status, data }
}

const fail = (msg) => { console.error('SESSION CLIP E2E FAIL:', msg); process.exit(1) }

const health = await j('GET', '/health')
if (health.status !== 200) fail(`health ${health.status}`)

const blocked = await j('POST', `/materials?work=${encodeURIComponent(WORK)}`, {
  title: '应被闸', body: 'x', kind: 'snippet',
})
if (blocked.status !== 403) {
  // emergency 可能开着：仍要求 clip 端点 200；materials 403 只在闸关时强断言
  console.warn('WARN: POST /materials not 403 (emergency rest write may be on):', blocked.status)
} else if (!String(blocked.data?.detail || '').includes('REST world write disabled')) {
  fail(`unexpected 403 detail: ${JSON.stringify(blocked.data)}`)
}

const bodyText = `E2E摘录_${Date.now()}_霜白城墙`
const clip = await j('POST', `/author/session-clips?work=${encodeURIComponent(WORK)}`, {
  body: bodyText,
  kind: 'snippet',
  origin_label: 'e2e',
  scope_label: '会话',
})
if (clip.status !== 200) fail(`session-clips ${clip.status} ${JSON.stringify(clip.data)}`)
if (!clip.data?.id) fail(`no id: ${JSON.stringify(clip.data)}`)
if (clip.data.kind !== 'snippet') fail(`kind ${clip.data.kind}`)
if (!String(clip.data.source || '').includes('会话摘录')) fail(`source ${clip.data.source}`)

const list = await j('GET', `/materials?work=${encodeURIComponent(WORK)}&kind=snippet`)
if (list.status !== 200) fail(`list materials ${list.status}`)
const rows = Array.isArray(list.data) ? list.data : (list.data?.items || [])
const hit = rows.find((m) => String(m.id) === String(clip.data.id) || String(m.body || '').includes(bodyText))
if (!hit) fail(`saved clip not listed; id=${clip.data.id} rows=${rows.length}`)

// 空 body 422
const empty = await j('POST', `/author/session-clips?work=${encodeURIComponent(WORK)}`, { body: '  ' })
if (empty.status !== 422) fail(`empty body expected 422 got ${empty.status}`)

console.log('SESSION CLIP E2E OK', {
  id: clip.data.id,
  title: clip.data.title,
  materialsBlocked: blocked.status === 403,
  listed: true,
})
