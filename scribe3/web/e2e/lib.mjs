// 真机操作库:两档前端 e2e 共用。从 pw.mjs 提炼。
import { chromium } from 'playwright'

export const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export async function closeBrowserWithin(browser, { timeoutMs = 15000 } = {}) {
  let timer
  try {
    const completed = await Promise.race([
      Promise.resolve(browser.close()).then(() => true),
      new Promise((resolve) => { timer = setTimeout(() => resolve(false), timeoutMs) }),
    ])
    return { closed: completed }
  } finally {
    clearTimeout(timer)
  }
}

export async function withPage(fn) {
  const b = await chromium.launch()
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
  const errs = []
  p.on('pageerror', (e) => errs.push('PAGEERR ' + e.message))
  p.on('console', (m) => {
    if (m.type() === 'error') {
      const t = m.text()
      if (!/ERR_CONNECTION_CLOSED|favicon/.test(t)) errs.push('CONSOLE ' + t.slice(0, 140))
    }
  })
  let result
  try { const r = await fn(p); result = { ok: true, errs, ...r } }
  catch (e) { result = { ok: false, err: e.message, errs } }
  const closed = await closeBrowserWithin(b)
  if (!closed.closed) {
    result.ok = false
    result.errs.push('BROWSER_CLOSE_TIMEOUT')
    result.err ||= '浏览器关闭超时'
  }
  return result
}

export async function openBook(p, title, { work } = {}) {
  // 写作台的 HMR/SSE 常驻连接不会自然 networkidle。以真实书卡和四栏壳为准，
  // 且优先使用不可变 work slug，避免同名书把 UI 写入与回读带到不同作品。
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  const opener = work
    ? p.locator(`[data-work-slug="${work}"]`)
    : p.getByText(title, { exact: false })
  await opener.first().waitFor({ state: 'visible', timeout: 30000 })
  await opener.first().click()
  await p.locator('[data-testid="four-col"]').waitFor({ state: 'attached', timeout: 30000 })
  await p.waitForSelector('[role="treeitem"]', { timeout: 15000 }).catch(() => {})
}

export const visText = async (p) =>
  (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ').slice(0, 2000)
