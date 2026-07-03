// ── e2e · 批0-F1:切章丢稿根因(彻查 G/B-3) ─────────────────────────────────
// 运行:cd scribe3/web && node e2e/qa_batch0_f1.mjs(需 dev :3311 + 后端 :3321 在跑)
// 数据纪律:全程用「临时 work」(建 2 章测试书,跑完 DELETE);零残留,不碰真实书。
// 复现:打开第1章正文 → 编辑器输入标记(不手存)→ 经项目树点第2章(外部切章)→
//   ①断言后端 ch1 已持久化标记(切章不丢稿,PRIMARY);②断言 ch2 正确加载(防串章);
//   ③切回 ch1 编辑器仍显标记。修前 ①③ FAIL(丢稿),修后 PASS。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const ts = Date.now()
const MARK = `F1LOSS-${ts}`

const results = []
const consoleErrors = []
const rec = (name, pass, ev) => { results.push({ name, pass, ev }); console.log('[f1]', pass ? 'PASS' : 'FAIL', '|', name, '|', ev) }

const post = (p, b) => fetch(API + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
const jget = (p) => fetch(API + p).then((r) => r.json())

async function seedWork() {
  const w = await (await post('/works', { title: `F1TEST-${ts}` })).json()
  const slug = w.slug
  await post(`/save-chapter?work=${slug}`, { seq: 1, prose: '甲章原文AAA', title: '甲章', focalizer: '' })
  await post(`/save-chapter?work=${slug}`, { seq: 2, prose: '乙章原文BBB', title: '乙章', focalizer: '' })
  return slug
}
const chapterProse = async (slug, seq) => (await jget(`/chapter?seq=${seq}&work=${slug}`)).prose || ''
const delWork = (slug) => fetch(API + '/works/' + slug, { method: 'DELETE' }).catch(() => {})

const waitForProse = (page, sub, to = 8000) => page.waitForFunction(
  (s) => { const el = document.querySelector('.tiptap-prose'); return !!el && el.innerText.includes(s) },
  sub, { timeout: to })

const run = async () => {
  const slug = await seedWork()
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))
  const chNode = (label) => page.getByRole('button', { name: label })   // 子串匹配:章按钮名含字数角标
  const editor = page.locator('.tiptap-prose')
  try {
    await page.goto(FRONT, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: new RegExp(`F1TEST-${ts}`) }).first().click()
    // 展开手稿/未分卷(默认展开;兜底点一次)
    const vol = page.getByRole('button', { name: '未分卷' })
    await vol.waitFor({ timeout: 10000 })
    if (!(await chNode('1 甲章').isVisible().catch(() => false))) await vol.click()

    // —— 打开第 1 章,切到正文,确认原文加载 ——
    await chNode('1 甲章').click()
    await page.getByRole('button', { name: '正文', exact: true }).click()
    await waitForProse(page, '甲章原文AAA', 8000)

    // —— 编辑器输入标记,不手存 ——
    await editor.click()
    await page.keyboard.press('End')
    await page.keyboard.type(MARK)
    await page.waitForTimeout(1300)   // onChange 置 dirty + ProseEditor localStorage 防抖(1s)
    const beforeSwitch = await editor.innerText()
    rec('前置·ch1编辑器已含标记(未手存)', beforeSwitch.includes(MARK), `editorLen=${beforeSwitch.length}`)

    // —— 外部切章:项目树点第 2 章(触发 WriteLayout 重挂)——
    await chNode('2 乙章').click()
    await waitForProse(page, '乙章原文BBB', 8000)
    const ch2text = await editor.innerText()
    rec('② 切章正确加载新章(ch2显乙章·无ch1标记,防串章)',
      ch2text.includes('乙章原文BBB') && !ch2text.includes(MARK), `ch2="${ch2text.slice(0, 40)}"`)

    // 等切换 flush 落库(修后 fire-and-forget 保存需一点时间)
    await page.waitForTimeout(2000)

    // —— ① PRIMARY:后端 ch1 是否已持久化标记 ——
    const backend1 = await chapterProse(slug, 1)
    rec('① 切章不丢稿·后端ch1已持久化标记(PRIMARY)', backend1.includes(MARK), `backendCh1="${backend1.slice(0, 60)}"`)

    // —— ③ 切回 ch1,编辑器应显示标记 ——
    await chNode('1 甲章').click()
    await page.waitForTimeout(1500)
    const back1 = await editor.innerText()
    rec('③ 切回ch1编辑器显示标记(不丢稿)', back1.includes(MARK), `back1="${back1.slice(0, 60)}"`)
  } catch (e) {
    rec('运行异常', false, String(e).slice(0, 200))
  } finally {
    await browser.close()
    await delWork(slug)
  }

  console.log('\n==== F1 RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.ev}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
