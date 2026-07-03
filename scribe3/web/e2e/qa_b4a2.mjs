// ── e2e · 块四a-2:命名正位 + 大纲层级/单一真相源/视角露出/北极星常驻/显示修复 ──
// 运行:cd scribe3/web && node e2e/snapshot_ch4.mjs b4a2 && node e2e/qa_b4a2.mjs && node e2e/qa_b4a2_restore.mjs
// 会写数据(第4章 synopsis 标记 + 超长文本验证),跑前必拍快照、跑完必恢复(数据纪律同 qa_b1b/qa_b2)。
// 目标:《纸命》work=book_c256380e。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const WORK = 'book_c256380e'
const SEQ = 4
const ts = Date.now()
const MARK = `块四a2标记-${ts}`

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qa4a2]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }

const run = async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  await page.goto(FRONT, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()
  const vol = page.getByRole('button', { name: '未分卷' })
  await vol.waitFor({ timeout: 10000 })
  const left = page.getByTestId('left')
  const chNode = (n) => left.getByRole('button', { name: `${n} 第${n}章` })
  const manuscriptRoot = left.getByRole('button', { name: /^手稿/ }).first()

  // ============ ① 点手稿根 → 全书大纲(ContainerOutline)+ 北极星页头 ============
  await manuscriptRoot.click()
  await page.waitForTimeout(700)
  const newChBtn = page.getByRole('button', { name: /新建章/ })
  const hasOutlineView = await newChBtn.isVisible().catch(() => false)
  const nsCount1 = await page.getByText('北极星', { exact: true }).count()
  rec('① 点手稿根→全书大纲视图', hasOutlineView, `新建章按钮可见=${hasOutlineView}`)
  rec('①b 全书大纲页头北极星条(且不重复)', nsCount1 === 1, `北极星条数=${nsCount1}`)

  // 切「大纲表」模式(章行含 梗概/视角 列)
  await page.getByRole('button', { name: '大纲表' }).click()
  await page.waitForTimeout(400)
  const synHeader = await page.getByText('(即章级大纲 · 处处同步)').first().isVisible().catch(() => false)
  rec('② 梗概列标注「即章级大纲 · 处处同步」', synHeader, `header可见=${synHeader}`)

  // ============ ③ 视角露出:双POV真值,剥 role: 前缀 ============
  const pov = await page.evaluate(() => {
    const txt = [...document.querySelectorAll('table')].map((t) => t.innerText).join('\n')
    return { a: (txt.match(/柳怀玉/g) || []).length, b: (txt.match(/苏纸鸢/g) || []).length, raw: (txt.match(/role:/g) || []).length }
  })
  rec('③ 章行视角露出(柳怀玉/苏纸鸢,无 role: 前缀)', pov.a >= 1 && pov.b >= 1 && pov.raw === 0, JSON.stringify(pov))

  // ============ ④ 命名正位:左栏 rail「母题」,无「素材 · 母题」 ============
  // motif cap 需选中章后出现:先经大纲表点开第4章(顺带验证⑤导航)
  await page.getByRole('button', { name: '第4章', exact: true }).click()
  await page.waitForTimeout(900)
  const outlineHeading = await page.getByText('本章大纲 · 一句话到一段话写清这章要发生什么').isVisible().catch(() => false)
  rec('⑤ 全书大纲点章行→直落该章「大纲」阶段', outlineHeading, `大纲阶段标题可见=${outlineHeading}`)
  const nsOutline = await page.getByText('北极星', { exact: true }).count()
  rec('⑥a 大纲阶段页头北极星条(且不重复)', nsOutline === 1, `北极星条数=${nsOutline}`)

  const motifRail = await left.getByRole('button', { name: '母题', exact: true }).isVisible().catch(() => false)
  const oldLabel = await page.getByRole('button', { name: '素材 · 母题' }).count()
  rec('④ 左栏 tab 正名「母题」,无「素材 · 母题」残留', motifRail && oldLabel === 0, `母题rail=${motifRail} 旧label=${oldLabel}`)
  await left.getByRole('button', { name: '母题', exact: true }).click()
  await page.waitForTimeout(400)
  const motifTitle = await page.getByText('母题 · 设定库').isVisible().catch(() => false)
  rec('④b 母题面板标题归属设定库', motifTitle, `标题可见=${motifTitle}`)
  await page.getByRole('button', { name: '项目树' }).click()

  // ============ ⑤b 单一真相源:章级大纲改 synopsis → 全书大纲同步 ============
  const editor = page.getByRole('textbox', { name: '本章大纲' })
  await editor.click()
  await page.keyboard.press('End')
  await page.keyboard.type(MARK)
  const patchWait = page.waitForResponse((r) => r.url().includes(`/chapters/${SEQ}`) && r.request().method() === 'PATCH', { timeout: 10000 })
  await page.getByText('本章大纲 · 一句话到一段话写清这章要发生什么').click()   // 失焦 → flush
  const patchRes = await patchWait
  rec('⑤c 章级大纲失焦落库(PATCH /chapters/4)', patchRes.ok(), `status=${patchRes.status()}`)

  // ============ ⑥b 节拍阶段北极星 ============
  await page.getByRole('button', { name: '节拍', exact: true }).click()
  await page.waitForTimeout(500)
  const nsBeats = await page.getByText('北极星', { exact: true }).count()
  rec('⑥b 节拍阶段页头北极星条(且不重复)', nsBeats === 1, `北极星条数=${nsBeats}`)

  // ============ ⑥c 正文阶段北极星不回退(WriteLayout 自带,单实例) ============
  await page.getByRole('button', { name: '正文', exact: true }).click()
  await page.waitForTimeout(1200)
  const nsFinal = await page.getByText('北极星', { exact: true }).count()
  rec('⑥c 正文侧北极星不回退(且不重复)', nsFinal === 1, `北极星条数=${nsFinal}`)

  // ============ ⑤d 回全书大纲:同步可见标记 ============
  await manuscriptRoot.click()
  await page.waitForTimeout(800)
  const markVisible = await page.getByText(new RegExp(MARK.slice(0, 12))).first().isVisible().catch(() => false)
  rec('⑤d 全书大纲同步显示章级大纲改动(同一 synopsis)', markVisible, `标记「${MARK}」可见=${markVisible}`)

  // ============ ⑦ 显示修复:超长 synopsis 不撑破布局 + 截断省略 ============
  const LONG = ('这是一段用于验证全书大纲显示修复的超长梗概文本,包含长句与不含空格的英文串' + 'Wwwwwwwwww'.repeat(12) + '。').repeat(8)
  let r = await fetch(`${API}/chapters/${SEQ}?work=${WORK}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ synopsis: LONG }),
  })
  log('inject long synopsis:', r.status, `len=${LONG.length}`)
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()
  await page.getByRole('button', { name: '未分卷' }).waitFor({ timeout: 10000 })
  await page.getByTestId('left').getByRole('button', { name: /^手稿/ }).first().click()
  await page.waitForTimeout(800)
  // 大纲表模式(localStorage 已记住);断言表格容器无横向溢出 + 单元格两行截断
  const layout = await page.evaluate(() => {
    const table = [...document.querySelectorAll('table')].at(-1)
    if (!table) return { noTable: true }
    const scroller = table.closest('.overflow-y-auto') || table.parentElement
    const cell = [...table.querySelectorAll('td .line-clamp-2')].find((el) => el.textContent.length > 200)
    const cs = cell ? getComputedStyle(cell) : null
    return {
      tableW: table.scrollWidth, hostW: scroller.clientWidth,
      overflowX: scroller.scrollWidth > scroller.clientWidth + 1,
      clamped: cs ? cs.webkitLineClamp === '2' && cs.overflow === 'hidden' : false,
      cellH: cell ? cell.getBoundingClientRect().height : -1,
    }
  })
  rec('⑦a 超长梗概不撑破布局(无横向溢出)', !layout.noTable && !layout.overflowX, JSON.stringify(layout))
  rec('⑦b 超长梗概两行截断+省略(line-clamp-2)', layout.clamped && layout.cellH > 0 && layout.cellH < 60, `clamped=${layout.clamped} cellH=${Math.round(layout.cellH)}px`)
  // 卡片墙模式同查(line-clamp-3)
  await page.getByRole('button', { name: '卡片墙' }).click()
  await page.waitForTimeout(400)
  const cardLayout = await page.evaluate(() => {
    const el = [...document.querySelectorAll('.line-clamp-3')].find((n) => n.textContent.length > 200)
    if (!el) return { none: true }
    const cs = getComputedStyle(el)
    return { clamped: cs.webkitLineClamp === '3', h: el.getBoundingClientRect().height, docOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth }
  })
  rec('⑦c 卡片墙超长梗概三行截断且页面无横向滚动', !cardLayout.none && cardLayout.clamped && !cardLayout.docOverflow, JSON.stringify(cardLayout))

  await browser.close()

  console.log('\n==== RESULTS ====')
  for (const x of results) console.log(`${x.pass ? 'PASS' : 'FAIL'} | ${x.name} | ${x.evidence}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  console.log('\n⚠ 记得跑 node e2e/qa_b4a2_restore.mjs 恢复第4章快照')
  if (results.some((x) => x.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
