// ── e2e · 批0-F2:草稿「采用为正文」搬运 prose(彻查 B-4) ─────────────────────
// 运行:cd scribe3/web && node e2e/qa_batch0_f2.mjs(需 dev :3311 + 后端 :3321 在跑)
// 数据纪律:临时 work(建 1 章测试书,跑完 DELETE);零残留。
// 复现:草稿阶段写入标记 → 点「采用为正文」→ 切正文 tab →
//   ①断言正文编辑器含标记 ②断言后端 chapter.prose 已是草稿内容。
// 修前 FAIL:onAdopt 丢弃 text 只切 tab,chapter.prose 仍是旧正文(采用名不副实)。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const ts = Date.now()
const MARK = `F2ADOPT-${ts}`

const results = []
const consoleErrors = []
const rec = (name, pass, ev) => { results.push({ name, pass, ev }); console.log('[f2]', pass ? 'PASS' : 'FAIL', '|', name, '|', ev) }

const post = (p, b) => fetch(API + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
const jget = (p) => fetch(API + p).then((r) => r.json())

async function seedWork() {
  const w = await (await post('/works', { title: `F2TEST-${ts}` })).json()
  const slug = w.slug
  await post(`/save-chapter?work=${slug}`, { seq: 1, prose: '原正文OLD', title: '采用测试章', focalizer: '' })
  return slug
}
const chapterProse = async (slug, seq) => (await jget(`/chapter?seq=${seq}&work=${slug}`)).prose || ''
const delWork = (slug) => fetch(API + '/works/' + slug, { method: 'DELETE' }).catch(() => {})

const run = async () => {
  const slug = await seedWork()
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))
  const chNode = (label) => page.getByRole('button', { name: label })
  const tab = (n) => page.getByRole('button', { name: n, exact: true })
  const richEd = page.locator('.tiptap-rich')
  const proseEd = page.locator('.tiptap-prose')
  try {
    await page.goto(FRONT, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: new RegExp(`F2TEST-${ts}`) }).first().click()
    const vol = page.getByRole('button', { name: '未分卷' })
    await vol.waitFor({ timeout: 10000 })
    if (!(await chNode('1 采用测试章').isVisible().catch(() => false))) await vol.click()
    await chNode('1 采用测试章').click()

    // —— 进草稿阶段,写入标记 ——
    await tab('草稿').click()
    await richEd.waitFor({ timeout: 10000 })
    await richEd.click()
    await page.keyboard.type(MARK)
    await page.waitForTimeout(500)
    const draftText = await richEd.innerText()
    rec('前置·草稿编辑器已含标记', draftText.includes(MARK), `draft="${draftText.slice(0, 40)}"`)

    // —— 采用为正文 ——
    await page.getByRole('button', { name: '采用为正文' }).click()
    // 切到正文(WriteLayout);等编辑器就位 + prose 加载
    await proseEd.waitFor({ timeout: 10000 })
    await page.waitForFunction((m) => {
      const el = document.querySelector('.tiptap-prose')
      return !!el && el.innerText.includes(m)
    }, MARK, { timeout: 8000 }).catch(() => {})
    const proseText = await proseEd.innerText()
    rec('① 采用后正文编辑器含草稿标记(搬运prose)', proseText.includes(MARK), `prose="${proseText.slice(0, 40)}"`)

    // —— 后端 chapter.prose 已是草稿内容 ——
    await page.waitForTimeout(1500)
    const backend = await chapterProse(slug, 1)
    rec('② 后端chapter.prose已搬为草稿内容(非旧正文)', backend.includes(MARK), `backend="${backend.slice(0, 40)}"`)
  } catch (e) {
    rec('运行异常', false, String(e).slice(0, 200))
  } finally {
    await browser.close()
    await delWork(slug)
  }

  console.log('\n==== F2 RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.ev}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
