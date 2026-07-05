// ── e2e · 块一-B:前置四阶段 RichEditor 健壮保存 ─────────────────────────────
// 运行:cd scribe3/web && node e2e/qa_b1b.mjs(需 dev :3311 + 后端 :3321 在跑)
// ⚠ 会改《纸命》(book_c256380e)第4章数据:先 node e2e/snapshot_ch4.mjs b1b 拍快照,
//   跑完必须 node e2e/qa_b1b_restore.mjs 恢复并逐字段复核(数据纪律)。
// QA 块一-B:前置四阶段 RichEditor 拉齐正文 —— 健壮保存(切章/切阶段/切选中项不丢)+ markdown 序列化 + 演绎回归(A/B)
// 目标:《纸命》work=book_c256380e 第4章。测试后由 qa_b1b_restore.mjs 全量恢复快照。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const WORK = 'book_c256380e'
const SEQ = 4
const ts = Date.now()
const MK_OUT = `大纲标记-${ts}`
const HEAD_TXT = `阶段标题-${ts}`
const BOLD_TXT = `加粗词-${ts}`
const MK_BEAT_NEW = `节拍新增-${ts}`
const MK_BEAT_EDIT = `节拍改-${ts}`
const MK_A = `演绎A-${ts}`
const MK_B1 = `演绎B1-${ts}`
const MK_B2 = `演绎B2-${ts}`
const MK_DRAFT = `草稿标记-${ts}`

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qa]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass === null ? 'SKIP' : pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }
const getCh = async () => (await fetch(`${API}/chapter?seq=${SEQ}&work=${WORK}`)).json()
const getDraft = async () => (await fetch(`${API}/latest-draft?seq=${SEQ}&work=${WORK}`)).json()

const run = async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  await page.goto(FRONT, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()
  const vol = page.getByRole('button', { name: '未分卷' })
  await vol.waitFor({ timeout: 10000 })
  const chNode = (n) => page.getByRole('button', { name: `${n} 第${n}章` })
  if (!(await chNode(SEQ).isVisible().catch(() => false))) await vol.click()
  await chNode(SEQ).click()
  await page.waitForTimeout(800)

  const tab = (n) => page.getByRole('button', { name: n, exact: true })

  // ============ 1. 大纲:富文本 + 切阶段不丢 + markdown 落库 ============
  await tab('大纲').click()
  const out = page.getByRole('textbox', { name: '本章大纲' })
  await out.waitFor({ timeout: 10000 })
  await out.click()
  // 纯键盘路径:全选后直接打字替换,保证 ProseMirror 选区状态与输入同步(fill 后紧跟 Enter 会不分段)
  await page.keyboard.press('ControlOrMeta+a')
  await page.keyboard.type(MK_OUT)
  await page.keyboard.press('Enter')
  await page.keyboard.type(HEAD_TXT)
  await page.keyboard.press('Enter')
  await page.keyboard.type(BOLD_TXT)
  // 选中标题行 → 气泡「小标题」
  await page.getByText(HEAD_TXT).click({ clickCount: 3 })
  await page.getByRole('button', { name: '小标题' }).click()
  // 选中加粗行 → 气泡「加粗」
  await page.getByText(BOLD_TXT).click({ clickCount: 3 })
  await page.getByRole('button', { name: '加粗' }).click()
  await page.waitForTimeout(200)
  // 不手动保存,直接切到节拍再切回
  await tab('节拍').click()
  await page.waitForTimeout(1000)
  await tab('大纲').click()
  await out.waitFor({ timeout: 10000 })
  await page.waitForTimeout(600)
  const outTxt = await out.innerText()
  rec('1a 大纲切阶段往返内容仍在', outTxt.includes(MK_OUT) && outTxt.includes(HEAD_TXT) && outTxt.includes(BOLD_TXT), `innerText含三标记=${[MK_OUT, HEAD_TXT, BOLD_TXT].map((m) => outTxt.includes(m)).join(',')}`)
  // H3 是否渲染为标题元素
  const h3ok = await page.locator('.tiptap-rich h3', { hasText: HEAD_TXT }).count()
  rec('1b 大纲 H3 富文本渲染', h3ok === 1, `h3 count=${h3ok}`)
  let ch = await getCh()
  const syn = ch.synopsis || ''
  rec('1c 大纲落库为 markdown', syn.includes(MK_OUT) && syn.includes(`### ${HEAD_TXT}`) && syn.includes(`**${BOLD_TXT}**`), `synopsis=${JSON.stringify(syn.slice(0, 120))}`)

  // ============ 2. 节拍:条目增/编辑不丢/移/删 ============
  await tab('节拍').click()
  const addInput = page.getByPlaceholder('加一个节拍…(Enter 添加)')
  await addInput.waitFor({ timeout: 10000 })
  const beatsBefore = ((await getCh()).beats || []).length
  await addInput.fill(MK_BEAT_NEW)
  await addInput.press('Enter')
  await page.waitForTimeout(1000)
  ch = await getCh()
  rec('2a 新增节拍已落库', (ch.beats || []).some((b) => b.text === MK_BEAT_NEW), `beats=${(ch.beats || []).length}(原${beatsBefore})`)
  // 编辑第一条(富文本填充),不手动保存直接切阶段
  const b1 = page.getByRole('textbox', { name: '节拍 1' })
  await b1.click()
  await b1.fill(MK_BEAT_EDIT)
  await tab('大纲').click()
  await page.waitForTimeout(1000)
  await tab('节拍').click()
  await b1.waitFor({ timeout: 10000 })
  await page.waitForTimeout(600)
  const b1Txt = await b1.innerText()
  ch = await getCh()
  rec('2b 节拍文本编辑切阶段不丢', b1Txt.trim() === MK_BEAT_EDIT, `editor="${b1Txt.trim().slice(0, 40)}"`)
  rec('2c 节拍文本编辑已落库', ((ch.beats || [])[0] || {}).text === MK_BEAT_EDIT, `beats[0]=${JSON.stringify(((ch.beats || [])[0] || {}).text || '').slice(0, 60)}`)
  // 下移第一条
  const rows = page.locator('div.group').filter({ has: page.getByRole('textbox', { name: /^节拍 / }) })
  await rows.nth(0).getByRole('button', { name: '下移' }).click()
  await page.waitForTimeout(1000)
  ch = await getCh()
  rec('2d 下移生效', ((ch.beats || [])[1] || {}).text === MK_BEAT_EDIT, `beats[1]=${JSON.stringify(((ch.beats || [])[1] || {}).text || '').slice(0, 60)}`)
  // 上移还原
  await rows.nth(1).getByRole('button', { name: '上移' }).click()
  await page.waitForTimeout(1000)
  ch = await getCh()
  rec('2e 上移还原', ((ch.beats || [])[0] || {}).text === MK_BEAT_EDIT, `beats[0]=${JSON.stringify(((ch.beats || [])[0] || {}).text || '').slice(0, 60)}`)
  // 删除新增的最后一条
  const n = await rows.count()
  await rows.nth(n - 1).getByRole('button', { name: '删除' }).click()
  await page.waitForTimeout(1000)
  ch = await getCh()
  rec('2f 删除生效', !(ch.beats || []).some((b) => b.text === MK_BEAT_NEW), `beats=${(ch.beats || []).length}`)

  // ============ 3. 演绎回归(块一-A 两用例,富文本版) ============
  await tab('演绎').click()
  await page.getByRole('button', { name: '演绎 · 角色限知' }).click()
  const truthBtn = page.getByRole('button', { name: /^场景真相/ })
  await truthBtn.waitFor({ timeout: 10000 })
  const truthTa = page.getByRole('textbox', { name: '场景真相' })
  const charTa = page.getByRole('textbox', { name: '限知投影' })
  const charBtn = (nm) => page.getByRole('button', { name: new RegExp(nm) })

  // A:切换不丢
  await truthBtn.click()
  await truthTa.waitFor({ timeout: 8000 })
  await truthTa.click()
  await truthTa.fill(MK_A)
  await charBtn('崔判').first().click()   // 不手动保存,直接切角色
  await charTa.waitFor({ timeout: 8000 })
  await truthBtn.click()
  await truthTa.waitFor({ timeout: 8000 })
  await page.waitForTimeout(600)
  let v = await truthTa.innerText()
  rec('3-A1 切角色再切回:真相仍在', v.includes(MK_A), `editor="${v.slice(0, 50)}"`)
  // 切章往返
  await page.getByRole('button', { name: '项目树' }).click()
  await chNode(2).click()
  await page.waitForTimeout(1200)
  await chNode(SEQ).click()
  await page.waitForTimeout(1200)
  await page.getByRole('button', { name: '演绎 · 角色限知' }).click()
  await truthBtn.click()
  await truthTa.waitFor({ timeout: 8000 })
  await page.waitForTimeout(800)
  v = await truthTa.innerText()
  rec('3-A2 切章往返:真相仍在', v.includes(MK_A), `editor="${v.slice(0, 50)}"`)
  ch = await getCh()
  rec('3-A3 后端已持久化', (ch.scene_truth || '').includes(MK_A), `scene_truth=${JSON.stringify((ch.scene_truth || '').slice(0, 50))}`)

  // B:多角色不覆盖
  await charBtn('崔判').first().click()
  await charTa.waitFor({ timeout: 8000 })
  await charTa.click()
  await charTa.fill(MK_B1)
  await charBtn('柳怀玉').first().click()
  await charTa.waitFor({ timeout: 8000 })
  await page.waitForTimeout(600)
  await charTa.click()
  await charTa.fill(MK_B2)
  await truthBtn.click()
  await page.waitForTimeout(1500)
  ch = await getCh()
  const deds = ch.deductions || []
  const d1 = deds.find((d) => d.character_id === 'role:崔判')
  const d2 = deds.find((d) => d.character_id === 'role:柳怀玉')
  rec('3-B1 崔判投影在', !!d1 && (d1.prose || '').includes(MK_B1), JSON.stringify(d1 || null).slice(0, 100))
  rec('3-B2 柳怀玉投影在(未覆盖崔判)', !!d2 && (d2.prose || '').includes(MK_B2), JSON.stringify(d2 || null).slice(0, 100))
  rec('3-B3 场景真相未被清掉', (ch.scene_truth || '').includes(MK_A), `scene_truth=${JSON.stringify((ch.scene_truth || '').slice(0, 50))}`)

  // ============ 4. 草稿:填标记 → 不手动保存直接切章往返 ============
  await tab('草稿').click()
  const dr = page.getByRole('textbox', { name: '草稿正文' })
  await dr.waitFor({ timeout: 10000 })
  await dr.click()
  await dr.fill(MK_DRAFT)
  // 不点「存草稿」,直接切到第2章再回
  await page.getByRole('button', { name: '项目树' }).click()
  await chNode(2).click()
  await page.waitForTimeout(1500)
  await chNode(SEQ).click()
  await page.waitForTimeout(1500)
  const drTxt = await dr.innerText()
  rec('4a 草稿切章往返内容仍在', drTxt.includes(MK_DRAFT), `editor="${drTxt.slice(0, 50)}"`)
  const dnow = await getDraft()
  rec('4b 草稿后端已持久化(切章flush)', ((dnow && dnow.prose) || '').includes(MK_DRAFT), `latest-draft=${JSON.stringify(((dnow && dnow.prose) || '').slice(0, 50))}`)

  // ============ 5. 正文不回归(只验渲染与可编辑,绝不输入) ============
  await tab('正文').click()
  const prose = page.locator('.tiptap-prose')
  await prose.waitFor({ timeout: 15000 })
  const editable = await prose.getAttribute('contenteditable')
  const plen = ((await prose.innerText()) || '').replace(/\s/g, '').length
  rec('5 正文编辑器渲染且可编辑', editable === 'true' && plen > 100, `contenteditable=${editable} 字数≈${plen}`)

  await browser.close()

  console.log('\n==== RESULTS ====')
  for (const r of results) console.log(`${r.pass === null ? 'SKIP' : r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.evidence}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false)) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
