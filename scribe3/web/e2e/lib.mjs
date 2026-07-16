// 真机操作库:两档前端 e2e 共用。从 pw.mjs 提炼。
import { chromium } from 'playwright'

export const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

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
  try { const r = await fn(p); return { ok: true, errs, ...r } }
  catch (e) { return { ok: false, err: e.message, errs } }
  finally { await b.close() }
}

export async function openBook(p, title) {
  await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(800)
  await p.getByText(title, { exact: false }).first().click()
  await sleep(2000)
  await p.waitForSelector('[role="treeitem"]', { timeout: 8000 }).catch(() => {})
}

export const visText = async (p) =>
  (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ').slice(0, 2000)
