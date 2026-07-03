// ── e2e · 批0-F5:OutlineTab/BeatsTab 卸载兜底 flush 钉死 work,防切书写错书(F1 同类)──
// 运行:cd scribe3/web && node e2e/qa_batch0_f5_crossbook.mjs(需 dev :3311 + 后端 :3321)
// 数据纪律:两本临时 work(A/B),跑完 DELETE;零残留,不碰真书 book_c256380e。
//
// 复现路径(必须走「主编 proposal 一键填入置 dirty 但不聚焦编辑器 → ⌘K 切书」——
//   RichEditor 的 onBlur={flush} 兜住了「手输后失焦」,唯有这条无 blur 的路能触发):
//   ① A 章大纲阶段,经 window CustomEvent('s3:stage-proposal') 注入主编生成(与 ChiefDock
//      发布口径同一 seam)→ 点「填入」→ OutlineTab dirtyRef.dirty=true,编辑器未获焦;
//   ② ⌘K 切到 B(App.open 同步先 api.setWork(B) 再重挂 → 旧 ChapterStudio(A) 卸载,
//      OutlineTab(A) 卸载 flush 此刻全局 WORK 已是 B);
//   ③ 断言 B 同章 synopsis 未被污染(curl B 无 A 标记,原大纲仍在);
//   ④ 断言 A 同章 synopsis 收到自己的编辑(curl A 有标记);⑤ 切回 A 编辑器可见标记。
//   修前 ③④⑤ FAIL(A 的大纲被写进 B),修后全 PASS。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const ts = Date.now()
const MARK = `XBSYN-${ts}`

const results = []
const consoleErrors = []
const rec = (name, pass, ev) => { results.push({ name, pass, ev }); console.log('[f5xb]', pass ? 'PASS' : 'FAIL', '|', name, '|', ev) }

const post = (p, b) => fetch(API + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) })
const jget = (p) => fetch(API + p).then((r) => r.json())
const patchSyn = (slug, syn) => fetch(API + `/chapters/1?work=${slug}`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ synopsis: syn }),
})

async function seedWork(title, prose, chTitle, syn) {
  const w = await (await post('/works', { title })).json()
  await post(`/save-chapter?work=${w.slug}`, { seq: 1, prose, title: chTitle, focalizer: '' })
  await patchSyn(w.slug, syn)
  return w.slug
}
const chapterSyn = async (slug) => (await jget(`/chapter?seq=1&work=${slug}`)).synopsis || ''
const delWork = (slug) => fetch(API + '/works/' + slug, { method: 'DELETE' }).catch(() => {})

const run = async () => {
  const slugA = await seedWork(`XBOOKA-${ts}`, 'A章原文AAA', 'A甲', 'A原大纲AAA')
  const slugB = await seedWork(`XBOOKB-${ts}`, 'B章原文BBB', 'B甲', 'B原大纲BBB')
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))
  const chNode = (label) => page.getByRole('button', { name: label })
  const outlineEditor = page.getByRole('textbox', { name: '本章大纲' })

  const switchBook = async (titleSubstr) => {
    await page.keyboard.press('Control+k')
    const input = page.getByPlaceholder('跳视图 / 切书 / 作品库…')
    await input.waitFor({ timeout: 6000 })
    await input.fill(titleSubstr)
    await page.waitForTimeout(300)
    await page.keyboard.press('Enter')
  }
  const openOutline = async (chLabel) => {
    const vol = page.getByRole('button', { name: '未分卷' })
    await vol.waitFor({ timeout: 10000 })
    if (!(await chNode(chLabel).isVisible().catch(() => false))) await vol.click()
    await chNode(chLabel).click()
    await page.getByRole('button', { name: '大纲', exact: true }).click()
    await outlineEditor.waitFor({ timeout: 8000 })
  }
  // 经与 ChiefDock 同一 seam 注入「主编生成完成」(不聚焦编辑器),再点「填入」→ 置 dirty
  const injectAndFill = async (seq, content) => {
    await page.evaluate(({ seq, content }) => {
      window.dispatchEvent(new CustomEvent('s3:stage-proposal', {
        detail: { phase: 'outline', seq, target: null, content, ts: Date.now() },
      }))
    }, { seq, content })
    const fill = page.getByRole('button', { name: '填入', exact: true })
    await fill.waitFor({ timeout: 6000 })
    await fill.click()
  }

  try {
    await page.goto(FRONT, { waitUntil: 'networkidle' })
    // —— 打开 A 书,第1章大纲阶段;经 proposal 填入置 dirty(编辑器未聚焦,无 blur)——
    await page.getByRole('button', { name: new RegExp(`XBOOKA-${ts}`) }).first().click()
    await openOutline('1 A甲')
    await page.waitForFunction(() => {
      const el = document.querySelector('[aria-label="本章大纲"] .tiptap-prose, [aria-label="本章大纲"]')
      return !!el && el.innerText.includes('A原大纲AAA')
    }, null, { timeout: 8000 }).catch(() => {})
    await injectAndFill(1, MARK)
    await page.waitForTimeout(600)
    const fillGone = !(await page.getByRole('button', { name: '填入', exact: true }).isVisible().catch(() => false))
    rec('前置·A书ch1大纲经proposal填入(dirty,未聚焦编辑器)', fillGone && (await outlineEditor.innerText()).includes(MARK), `editor="${(await outlineEditor.innerText()).slice(0, 30)}"`)

    // —— ⌘K 切到 B 书(触发 OutlineTab(A) 卸载 flush,此刻全局 WORK 已是 B)——
    await switchBook(`XBOOKB-${ts}`)
    await chNode('1 B甲').waitFor({ timeout: 10000 })   // B 树就位 = A 已卸载(flush 已发)
    await page.waitForTimeout(2000)                     // 等 flush 网络落定

    // —— ① B 同章未被污染;② A 同章收到自己的编辑 ——
    const bSyn = await chapterSyn(slugB)
    rec('① 切书后B书同章大纲未被污染(无A标记)', !bSyn.includes(MARK) && bSyn.includes('B原大纲BBB'), `B.syn="${bSyn.slice(0, 40)}"`)
    const aSyn = await chapterSyn(slugA)
    rec('② A书同章大纲收到自己的编辑(标记落A)', aSyn.includes(MARK), `A.syn="${aSyn.slice(0, 40)}"`)

    // —— ③ 切回 A,大纲编辑器可见标记 ——
    await switchBook(`XBOOKA-${ts}`)
    await openOutline('1 A甲')
    await page.waitForTimeout(1500)
    rec('③ 切回A大纲编辑器可见标记(A的编辑未丢)', (await outlineEditor.innerText()).includes(MARK), `A.editor="${(await outlineEditor.innerText()).slice(0, 40)}"`)
  } catch (e) {
    rec('运行异常', false, String(e).slice(0, 200))
  } finally {
    await browser.close()
    await delWork(slugA)
    await delWork(slugB)
  }

  console.log('\n==== F5-crossbook RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.ev}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
