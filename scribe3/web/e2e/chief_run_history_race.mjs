// P0 回归：线程历史空快照与 Hermes Run 事件乱序时，作者仍能在真实 UI 批准并写入章节。
// 运行：cd scribe3/web && E2E_API=http://127.0.0.1:3321 node e2e/chief_run_history_race.mjs
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || `Run审批竞态·${Date.now().toString(36)}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}

const result = await withPage(async (page) => {
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'networkidle' })
  const nameInput = page.locator('input[placeholder="书名…"], input[aria-label="书名"]')
  await nameInput.fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })

  const works = await json('/works')
  const work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
  if (!work) throw new Error('无法解析隔离验收书 work')

  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  const createRun = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
    { timeout: 30000 },
  )
  await composer.fill('请只调用 s3_add_chapter 新建第1章，title=夜访棺材铺。需我审批。未获批准不得声称已落库。')
  await composer.press('Enter')
  const run = await (await createRun).json()
  const runId = run.run_id || run.id
  if (!runId) throw new Error(`Run 创建未返回 id:${JSON.stringify(run)}`)

  let approved = 0
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const decisions = await approveAllPending(page, { maxRounds: 3, settleMs: 600 })
    approved += decisions.approved + decisions.staleApproved
    const chapters = await json(`/chapters?work=${encodeURIComponent(work)}`)
    const count = Array.isArray(chapters) ? chapters.length : (chapters.chapters || []).length
    if (approved > 0 && count > 0) {
      await page.screenshot({ path: '/tmp/gateb-chief-run-history-race.png', fullPage: true })
      return { work, runId, approvals: approved, chapterCount: count }
    }
    await sleep(2000)
  }
  await page.screenshot({ path: '/tmp/gateb-chief-run-history-race.png', fullPage: true })
  const status = await json(`/ai/runs/${encodeURIComponent(runId)}?work=${encodeURIComponent(work)}`).catch((error) => ({ error: error.message }))
  throw new Error(`Run 未完成审批写章:run=${runId},approved=${approved},status=${JSON.stringify(status)}`)
})

if (!result.ok || result.errs.some((entry) => entry.startsWith('PAGEERR'))) {
  console.error('CHIEF_RUN_HISTORY_RACE FAIL', JSON.stringify(result))
  process.exit(1)
}

console.log('CHIEF_RUN_HISTORY_RACE OK', JSON.stringify(result))
