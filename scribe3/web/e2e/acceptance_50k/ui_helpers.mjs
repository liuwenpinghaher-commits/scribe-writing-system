// 章选择 / 新建 / Tab 切换 — 复用 hq_wordcount_push + craft_first 已验证模式
import {
  approveAllPending,
  DECISION_SELECTORS,
} from '../author_decisions.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export async function clickTab(page, name) {
  const tab = page.getByRole('tab', { name, exact: true })
  if (await tab.count()) {
    await tab.first().click().catch(() => {})
    await sleep(800)
    return true
  }
  const loose = page.getByRole('tab', { name: new RegExp(name) })
  if (await loose.count()) {
    await loose.first().click().catch(() => {})
    await sleep(800)
    return true
  }
  return false
}

export async function selectChapter(page, seq) {
  const re = new RegExp(`^${seq}\\s+|第\\s*${seq}\\s*章`)
  const manuscript = page.getByRole('button', { name: '手稿', exact: true }).first()
  if (await manuscript.count() && await manuscript.getAttribute('aria-pressed') !== 'true') {
    await manuscript.click().catch(() => {})
  }
  await page.getByTestId('manuscript-directory').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {})
  // treeitem 优先
  const item = page.getByRole('treeitem').filter({ hasText: re })
  if (await item.count()) {
    await item.first().click()
    await sleep(1200)
    return true
  }
  const btn = page.locator('button').filter({ hasText: re })
  if (await btn.count()) {
    await btn.first().click({ force: true })
    await sleep(1500)
    return true
  }
  const byText = page.getByText(re)
  if (await byText.count()) {
    await byText.first().click({ force: true })
    await sleep(1500)
    return true
  }
  return false
}

export async function createChapter(page) {
  const manuscript = page.getByRole('button', { name: '手稿', exact: true }).first()
  if (await manuscript.count() && await manuscript.getAttribute('aria-pressed') !== 'true') {
    await manuscript.click().catch(() => {})
  }
  await page.getByTestId('manuscript-directory').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {})
  const candidates = [
    page.getByRole('button', { name: /新建未分卷章节/ }),
    page.getByRole('button', { name: /新建第一章/ }),
    page.getByRole('button', { name: /^新建章$/ }),
    page.getByText('+ 章节', { exact: true }),
    page.locator('button', { hasText: '+章' }),
    page.getByRole('button', { name: /^\+章$/ }),
    page.locator('button[aria-label="新建未分卷章节"]'),
    page.locator('button', { hasText: '新建章' }),
  ]
  for (const b of candidates) {
    if (await b.count() && await b.first().isVisible().catch(() => false)) {
      await b.first().click()
      // 「+ 章节」可能只 seed 主编 Run，必须批准
      await approveAllPending(page)
      await sleep(2200)
      return true
    }
  }
  return false
}

export async function ensureWriteComposer(page, { retries = 6 } = {}) {
  for (let i = 0; i < retries; i++) {
    await clickTab(page, '正文')
    await clickTab(page, '草稿')
    const write = page.locator(DECISION_SELECTORS.writeComposer)
    if (await write.count() && await write.first().isVisible().catch(() => false)) return true
    const any = page.locator('textarea[placeholder*="提思路"]')
    if (await any.count() && await any.first().isVisible().catch(() => false)) return true
    await sleep(900 + i * 400)
  }
  return false
}

export async function screenshot(page, artDir, name) {
  try {
    const { mkdirSync } = await import('node:fs')
    mkdirSync(`${artDir}/evidence`, { recursive: true })
    await page.screenshot({ path: `${artDir}/evidence/${name}.png`, fullPage: false })
  } catch { /* */ }
}
