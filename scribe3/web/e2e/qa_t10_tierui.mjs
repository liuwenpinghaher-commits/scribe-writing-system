// 聚焦验证:伏笔详情 tier 选择器「兑现层级」渲染(纯前端,后端无关,只读不写)。
import { chromium } from 'playwright'
const FRONT = 'http://127.0.0.1:3311'
const run = async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.setDefaultTimeout(12000)
  const errs = []
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)) })
  page.on('pageerror', (e) => errs.push('pageerror: ' + String(e).slice(0, 200)))
  await page.goto(FRONT, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()
  await page.getByRole('button', { name: '未分卷' }).waitFor({ timeout: 10000 })
  const tb = (nm) => page.getByRole('button', { name: nm, exact: true }).first()
  // 展开 codex 根「素材」→「伏笔」→ 选一条(auto-scroll 由 playwright 处理)
  if (!(await tb('伏笔').isVisible().catch(() => false))) await tb('素材').click().catch(() => {})
  await tb('伏笔').click()
  await page.waitForTimeout(400)
  await page.getByRole('button', { name: /续命者一栏为何空着/ }).first().click()
  await page.waitForTimeout(1000)
  const label = await page.getByText('兑现层级').isVisible().catch(() => false)
  // 该字段的 select 应含 章级/卷级/书级 三选项
  const sel = page.locator('select').filter({ has: page.locator('option', { hasText: '章级（近场' }) }).first()
  const hasSel = await sel.count().then((c) => c > 0).catch(() => false)
  const optTxt = hasSel ? await sel.locator('option').allInnerTexts().catch(() => []) : []
  console.log('RESULT 兑现层级label =', label, '| select存在 =', hasSel, '| 选项 =', JSON.stringify(optTxt))
  console.log('CONSOLE ERRORS:', errs.length ? errs.join('\n') : '(零错误)')
  await browser.close()
  if (!label || !hasSel || errs.length) process.exitCode = 2
}
run().catch((e) => { console.error('FATAL', e); process.exit(1) })
