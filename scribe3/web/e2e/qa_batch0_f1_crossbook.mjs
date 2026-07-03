// ── e2e · 批0-F1 追修 Critical:卸载兜底 flush 钉死 work,防切书写错书 ──────────
// 运行:cd scribe3/web && node e2e/qa_batch0_f1_crossbook.mjs(需 dev :3311 + 后端 :3321)
// 数据纪律:两本临时 work(A/B),跑完 DELETE;零残留,不碰真书。
// 复现路径(必须走 ⌘K 切书):A 章编辑器输标记不手存 → ⌘K 切到 B(App.open 同步先
//   api.setWork(B) 再重挂 → 旧 WriteLayout(A) 卸载 flush 此刻全局 WORK 已是 B)→
//   ①断言 B 同章未被污染(curl B 无 A 标记);②断言 A 同章收到自己的编辑(curl A 有标记);
//   ③切回 A 编辑器可见标记。修前 ①②③ FAIL(A 的正文被写进 B),修后全 PASS。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const ts = Date.now()
const MARK = `XBLOSS-${ts}`

const results = []
const consoleErrors = []
const rec = (name, pass, ev) => { results.push({ name, pass, ev }); console.log('[f1xb]', pass ? 'PASS' : 'FAIL', '|', name, '|', ev) }

const post = (p, b) => fetch(API + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
const jget = (p) => fetch(API + p).then((r) => r.json())

async function seedWork(title, prose, chTitle) {
  const w = await (await post('/works', { title })).json()
  await post(`/save-chapter?work=${w.slug}`, { seq: 1, prose, title: chTitle, focalizer: '' })
  return w.slug
}
const chapterProse = async (slug) => (await jget(`/chapter?seq=1&work=${slug}`)).prose || ''
const delWork = (slug) => fetch(API + '/works/' + slug, { method: 'DELETE' }).catch(() => {})

const run = async () => {
  const slugA = await seedWork(`XBOOKA-${ts}`, 'A章原文AAA', 'A甲')
  const slugB = await seedWork(`XBOOKB-${ts}`, 'B章原文BBB', 'B甲')
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))
  const chNode = (label) => page.getByRole('button', { name: label })
  const editor = page.locator('.tiptap-prose')

  const switchBook = async (titleSubstr) => {
    await page.keyboard.press('Control+k')
    const input = page.getByPlaceholder('跳视图 / 切书 / 作品库…')
    await input.waitFor({ timeout: 6000 })
    await input.fill(titleSubstr)
    await page.waitForTimeout(300)
    await page.keyboard.press('Enter')
  }
  const openCh1 = async (chLabel) => {
    const vol = page.getByRole('button', { name: '未分卷' })
    await vol.waitFor({ timeout: 10000 })
    if (!(await chNode(chLabel).isVisible().catch(() => false))) await vol.click()
    await chNode(chLabel).click()
    await page.getByRole('button', { name: '正文', exact: true }).click()
  }

  try {
    await page.goto(FRONT, { waitUntil: 'networkidle' })
    // —— 打开 A 书,第1章正文,输标记不手存 ——
    await page.getByRole('button', { name: new RegExp(`XBOOKA-${ts}`) }).first().click()
    await openCh1('1 A甲')
    await page.waitForFunction(() => { const el = document.querySelector('.tiptap-prose'); return !!el && el.innerText.includes('A章原文AAA') }, null, { timeout: 8000 })
    await editor.click()
    await page.keyboard.press('End')
    await page.keyboard.type(MARK)
    await page.waitForTimeout(1000)
    rec('前置·A书ch1编辑器含标记(未手存)', (await editor.innerText()).includes(MARK), 'ok')

    // —— ⌘K 切到 B 书(触发 A 的卸载 flush,此刻全局 WORK 已是 B)——
    await switchBook(`XBOOKB-${ts}`)
    await chNode('1 B甲').waitFor({ timeout: 10000 })   // B 树就位 = A 已卸载(flush 已发)
    await page.waitForTimeout(2000)                     // 等 flush 网络落定

    // —— ① B 同章未被污染;② A 同章收到自己的编辑 ——
    const bProse = await chapterProse(slugB)
    rec('① 切书后B书同章未被污染(无A标记)', !bProse.includes(MARK) && bProse.includes('B章原文BBB'), `B.ch1="${bProse.slice(0, 40)}"`)
    const aProse = await chapterProse(slugA)
    rec('② A书同章收到自己的编辑(标记落A)', aProse.includes(MARK), `A.ch1="${aProse.slice(0, 40)}"`)

    // —— ③ 切回 A,编辑器可见标记 ——
    await switchBook(`XBOOKA-${ts}`)
    await openCh1('1 A甲')
    await page.waitForTimeout(1500)
    rec('③ 切回A编辑器可见标记(A的编辑未丢)', (await editor.innerText()).includes(MARK), `A.editor="${(await editor.innerText()).slice(0, 40)}"`)
  } catch (e) {
    rec('运行异常', false, String(e).slice(0, 200))
  } finally {
    await browser.close()
    await delWork(slugA)
    await delWork(slugB)
  }

  console.log('\n==== F1-crossbook RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.ev}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
