// ── e2e · 批0-F3:右坞「恢复到此版本」同步编辑器(彻查 G/E-4) ─────────────────
// 运行:cd scribe3/web && node e2e/qa_batch0_f3.mjs(需 dev :3311 + 后端 :3321 在跑)
// 数据纪律:临时 work(建 1 章 + 一个命名存档,跑完 DELETE);零残留。
// 复现:章现为「版本B」,存档里有「版本A」→ 右坞回看「存档A」→ 恢复 →
//   ①断言编辑器显示版本A(修前 FAIL:仍显版本B,未同步);
//   ③续编辑后保存,后端存的是恢复版(版本A+改)而非旧版(修前 FAIL:版本B 覆盖恢复)。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const ts = Date.now()
const A = '版本A文本AAA'
const B = '版本B文本BBB'
const EDIT = `F3EDIT-${ts}`

const results = []
const consoleErrors = []
const rec = (name, pass, ev) => { results.push({ name, pass, ev }); console.log('[f3]', pass ? 'PASS' : 'FAIL', '|', name, '|', ev) }

const post = (p, b) => fetch(API + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
const jget = (p) => fetch(API + p).then((r) => r.json())

async function seedWork() {
  const w = await (await post('/works', { title: `F3TEST-${ts}` })).json()
  const slug = w.slug
  await post(`/save-chapter?work=${slug}`, { seq: 1, prose: A, title: '恢复测试章', focalizer: '' })
  await post(`/checkpoint?seq=1&work=${slug}`, { prose: A, label: '存档A', kind: 'checkpoint', qc: {} })
  await post(`/save-chapter?work=${slug}`, { seq: 1, prose: B, title: '恢复测试章', focalizer: '' })
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
  const proseEd = page.locator('.tiptap-prose')
  try {
    await page.goto(FRONT, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: new RegExp(`F3TEST-${ts}`) }).first().click()
    const vol = page.getByRole('button', { name: '未分卷' })
    await vol.waitFor({ timeout: 10000 })
    if (!(await chNode('1 恢复测试章').isVisible().catch(() => false))) await vol.click()
    await chNode('1 恢复测试章').click()
    await page.getByRole('button', { name: '正文', exact: true }).click()
    // 编辑器现应显版本B
    await page.waitForFunction((b) => {
      const el = document.querySelector('.tiptap-prose'); return !!el && el.innerText.includes(b)
    }, B, { timeout: 8000 })
    rec('前置·编辑器现为版本B', (await proseEd.innerText()).includes(B), 'ok')

    // —— 右坞:切到「存档」→ 回看「存档A」→ 恢复到此版本 → 确认 ——
    await page.getByRole('button', { name: '存档' }).click()
    const archRow = page.locator('li').filter({ hasText: '存档A' })
    await archRow.first().waitFor({ timeout: 10000 })
    await archRow.first().getByRole('button', { name: '回看' }).click()
    await page.getByRole('button', { name: '恢复到此版本' }).click()
    await page.getByRole('button', { name: '恢复', exact: true }).click()   // ConfirmDialog 确认

    // —— ① 恢复后编辑器应同步显示版本A ——
    await page.waitForTimeout(2500)
    const afterRestore = await proseEd.innerText()
    rec('① 恢复后编辑器同步显示版本A(不再是版本B)',
      afterRestore.includes(A) && !afterRestore.includes(B), `editor="${afterRestore.slice(0, 40)}"`)
    const backendAfterRestore = await chapterProse(slug, 1)
    rec('② 后端prose=版本A(doRestore已落库)', backendAfterRestore.includes(A), `backend="${backendAfterRestore.slice(0, 30)}"`)

    // —— ③ 续编辑→保存:存的应是恢复版(版本A+改),不是旧版(版本B)——
    await proseEd.click()
    await page.keyboard.press('End')
    await page.keyboard.type(EDIT)
    await page.waitForTimeout(400)
    await page.keyboard.press('Control+s')   // WriteLayout 全局保存
    await page.waitForTimeout(2000)
    const backendAfterEdit = await chapterProse(slug, 1)
    rec('③ 续编辑存的是恢复版(版本A+改·非版本B覆盖)',
      backendAfterEdit.includes(A) && backendAfterEdit.includes(EDIT) && !backendAfterEdit.includes(B),
      `backend="${backendAfterEdit.slice(0, 50)}"`)
  } catch (e) {
    rec('运行异常', false, String(e).slice(0, 200))
  } finally {
    await browser.close()
    await delWork(slug)
  }

  console.log('\n==== F3 RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.ev}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
