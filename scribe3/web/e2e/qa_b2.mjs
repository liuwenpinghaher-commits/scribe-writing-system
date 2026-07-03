// ── e2e · 块二:stageProposal 通道注入式回归(27 用例) ───────────────────────
// 运行:cd scribe3/web && node e2e/qa_b2.mjs(需 dev :3311 + 后端 :3321 在跑)
// ⚠ 会改《纸命》(book_c256380e)第4章数据:先 node e2e/snapshot_ch4.mjs b2 拍快照,
//   跑完必须 node e2e/qa_b2_restore.mjs 恢复并逐字段复核(数据纪律)。
// QA 块二(注入式):stageProposal 通道四阶段落地 + phase/seq/target 错落防护 + chiefIntent 预填。
// 注入 = 页面派发 CustomEvent('s3:stage-proposal'),与 ChiefDock 发布同一通道入口(模拟生成完成)。
// 目标:《纸命》work=book_c256380e 第4章。测试后由 qa_b2_restore.mjs 全量恢复快照。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'
const API = 'http://127.0.0.1:3321'
const WORK = 'book_c256380e'
const SEQ = 4
const ts = Date.now()
const MK_OUT = `块二大纲注入-${ts}`
const MK_OUT2 = `块二大纲追加-${ts}`
const MK_B1 = `块二节拍X-${ts}`
const MK_B2 = `块二节拍Y-${ts}`
const MK_T = `块二真相注入-${ts}`
const MK_R = `块二崔判注入-${ts}`
const MK_D = `块二草稿注入-${ts}`

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qa]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }
const getCh = async (s = SEQ) => (await fetch(`${API}/chapter?seq=${s}&work=${WORK}`)).json()
const getDraft = async () => (await fetch(`${API}/latest-draft?seq=${SEQ}&work=${WORK}`)).json()

const run = async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  const inject = (detail) => page.evaluate((d) => window.dispatchEvent(new CustomEvent('s3:stage-proposal', { detail: d })), detail)
  let injTs = 0

  await page.goto(FRONT, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /纸命/ }).first().click()
  const vol = page.getByRole('button', { name: '未分卷' })
  await vol.waitFor({ timeout: 10000 })
  const chNode = (n) => page.getByRole('button', { name: `${n} 第${n}章` })
  if (!(await chNode(SEQ).isVisible().catch(() => false))) await vol.click()
  await chNode(SEQ).click()
  await page.waitForTimeout(800)
  const tab = (n) => page.getByRole('button', { name: n, exact: true })
  const bar = page.locator('div', { hasText: /^主编生成了/ }).locator('visible=true').first()
  const barVisible = () => page.getByText(/主编生成了/).isVisible().catch(() => false)

  // ============ 1. chiefIntent:中区「让主编生成」→ 右栏预填 + 聚焦 ============
  await tab('大纲').click()
  const out = page.getByRole('textbox', { name: '本章大纲' })
  await out.waitFor({ timeout: 10000 })
  await page.getByRole('button', { name: '让主编生成' }).click()
  await page.waitForTimeout(300)
  const ta = page.getByPlaceholder('就当前内容问主编…(Enter 发送)')
  const taVal = await ta.inputValue().catch(() => '')
  const taFocused = await ta.evaluate((el) => document.activeElement === el).catch(() => false)
  rec('1a 大纲「让主编生成」预填右栏话术', taVal.includes(`第 ${SEQ} 章大纲`), `textarea="${taVal}"`)
  rec('1b 右栏输入框已聚焦', taFocused === true, `focused=${taFocused}`)
  await ta.fill('')   // 清掉,不真发

  // ============ 2. 大纲:注入 → 提示条 → 忽略 → 错落防护 → 填入/追加 → 持久化 ============
  // 2-0「忽略」:注入 → 点忽略 → 提示条消失且编辑器未被改动
  const outBefore = await out.innerText()
  await inject({ phase: 'outline', seq: SEQ, target: null, content: `忽略用例-${ts}`, ts: ++injTs })
  await page.waitForTimeout(300)
  const ignoreShown = await barVisible()
  await page.getByRole('button', { name: '忽略', exact: true }).click()
  await page.waitForTimeout(300)
  const outAfter = await out.innerText()
  rec('2-0 忽略:提示条消失且编辑器未动', ignoreShown && !(await barVisible()) && outAfter === outBefore, `shown=${ignoreShown} after=${await barVisible()} editorSame=${outAfter === outBefore}`)

  await inject({ phase: 'outline', seq: SEQ, target: null, content: MK_OUT, ts: ++injTs })
  await page.waitForTimeout(300)
  rec('2a 注入后大纲提示条出现', await barVisible(), `visible=${await barVisible()}`)
  // 切到第2章:seq 不匹配,提示条不得错落
  await page.getByRole('button', { name: '项目树' }).click()
  await chNode(2).click()
  await page.waitForTimeout(1000)
  await tab('大纲').click()
  await page.waitForTimeout(400)
  rec('2b 切到第2章大纲不错落', !(await barVisible()), `visible=${await barVisible()}`)
  // 回第4章:重新出现
  await chNode(SEQ).click()
  await page.waitForTimeout(1000)
  rec('2c 回第4章提示条恢复', await barVisible(), `visible=${await barVisible()}`)
  // 切到节拍 tab:phase 不匹配
  await tab('节拍').click()
  await page.waitForTimeout(400)
  rec('2d 节拍 tab 不错落(phase 校验)', !(await barVisible()), `visible=${await barVisible()}`)
  await tab('大纲').click()
  await out.waitFor({ timeout: 10000 })
  // 填入
  await page.getByRole('button', { name: '填入', exact: true }).click()
  await page.waitForTimeout(300)
  rec('2e 填入后提示条消失', !(await barVisible()), `visible=${await barVisible()}`)
  let v = await out.innerText()
  rec('2f 填入进编辑器', v.includes(MK_OUT), `editor="${v.slice(0, 60)}"`)
  // 追加:再注入一条,点「追加」
  await inject({ phase: 'outline', seq: SEQ, target: null, content: MK_OUT2, ts: ++injTs })
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: '追加', exact: true }).click()
  await page.waitForTimeout(300)
  v = await out.innerText()
  rec('2g 追加保留原文并加新段', v.includes(MK_OUT) && v.includes(MK_OUT2), `editor="${v.slice(0, 80)}"`)
  // 切走切回不丢 + 后端持久化
  await tab('节拍').click()
  await page.waitForTimeout(1000)
  await tab('大纲').click()
  await out.waitFor({ timeout: 10000 })
  await page.waitForTimeout(600)
  v = await out.innerText()
  rec('2h 切走切回不丢', v.includes(MK_OUT) && v.includes(MK_OUT2), `editor="${v.slice(0, 80)}"`)
  let ch = await getCh()
  rec('2i 大纲已持久化', (ch.synopsis || '').includes(MK_OUT) && (ch.synopsis || '').includes(MK_OUT2), `synopsis…${JSON.stringify((ch.synopsis || '').slice(-60))}`)

  // ============ 3. 节拍:注入列表 → 追加为新条目 → 持久化 ============
  await tab('节拍').click()
  await page.getByPlaceholder('加一个节拍…(Enter 添加)').waitFor({ timeout: 10000 })
  const beatsBefore = ((await getCh()).beats || []).length
  await inject({ phase: 'beats', seq: SEQ, target: null, content: `## 本章节拍\n- ${MK_B1}\n2. ${MK_B2}`, ts: ++injTs })
  await page.waitForTimeout(300)
  const barTxt = await page.getByText(/主编生成了/).innerText().catch(() => '')
  rec('3a 节拍提示条出现且解析 2 条', barTxt.includes('2 条节拍'), `bar="${barTxt}"`)
  await page.getByRole('button', { name: '追加为新条目' }).click()
  await page.waitForTimeout(1200)
  ch = await getCh()
  const bt = (ch.beats || []).map((b) => b.text)
  rec('3b 两条节拍已追加落库(剥列表标记)', bt.includes(MK_B1) && bt.includes(MK_B2), `beats=${(ch.beats || []).length}(原${beatsBefore}) 尾2=${JSON.stringify(bt.slice(-2))}`)
  rec('3c 原有节拍未动', bt.length === beatsBefore + 2, `len=${bt.length}`)

  // ============ 4. 演绎:target 匹配(truth/角色互不错落)→ 填入 → 健壮保存 ============
  await tab('演绎').click()
  await page.getByRole('button', { name: '演绎 · 角色限知' }).click()
  const truthBtn = page.getByRole('button', { name: /^场景真相/ })
  await truthBtn.waitFor({ timeout: 10000 })
  const truthTa = page.getByRole('textbox', { name: '场景真相' })
  const charTa = page.getByRole('textbox', { name: '限知投影' })
  const charBtn = (nm) => page.getByRole('button', { name: new RegExp(nm) })
  await truthBtn.click()
  await truthTa.waitFor({ timeout: 8000 })
  await inject({ phase: 'deduce', seq: SEQ, target: 'truth', content: MK_T, ts: ++injTs })
  await page.waitForTimeout(300)
  rec('4a 真相提示条出现', await barVisible(), `visible=${await barVisible()}`)
  // 切到崔判:target 不匹配,不得错落
  await charBtn('崔判').first().click()
  await charTa.waitFor({ timeout: 8000 })
  await page.waitForTimeout(300)
  rec('4b 切角色不错落(target 校验)', !(await barVisible()), `visible=${await barVisible()}`)
  // 回真相 → 填入 → 切角色触发 flush 落库
  await truthBtn.click()
  await truthTa.waitFor({ timeout: 8000 })
  await page.waitForTimeout(300)
  rec('4c 回真相提示条恢复', await barVisible(), `visible=${await barVisible()}`)
  await page.getByRole('button', { name: '填入', exact: true }).click()
  await page.waitForTimeout(300)
  v = await truthTa.innerText()
  rec('4d 真相填入编辑器', v.includes(MK_T), `editor="${v.slice(0, 50)}"`)
  // 角色投影:注入 role 目标,在崔判上填入
  await inject({ phase: 'deduce', seq: SEQ, target: 'role:崔判', content: MK_R, ts: ++injTs })
  await page.waitForTimeout(200)
  rec('4e 角色 proposal 在真相页不显', !(await barVisible()), `visible=${await barVisible()}`)
  await charBtn('崔判').first().click()   // 切走同时 flush 真相
  await charTa.waitFor({ timeout: 8000 })
  await page.waitForTimeout(400)
  rec('4f 切到崔判提示条出现', await barVisible(), `visible=${await barVisible()}`)
  await page.getByRole('button', { name: '填入', exact: true }).click()
  await page.waitForTimeout(300)
  await truthBtn.click()   // 切走 flush 崔判
  await page.waitForTimeout(1500)
  ch = await getCh()
  const ded = (ch.deductions || []).find((d) => d.character_id === 'role:崔判')
  rec('4g 真相已持久化', (ch.scene_truth || '').includes(MK_T), `scene_truth=${JSON.stringify((ch.scene_truth || '').slice(0, 50))}`)
  rec('4h 崔判投影已持久化', !!ded && (ded.prose || '').includes(MK_R), JSON.stringify(ded || null).slice(0, 100))

  // ============ 5. 草稿:注入 → 填入草稿框 → 切章往返 → 持久化 ============
  await tab('草稿').click()
  const dr = page.getByRole('textbox', { name: '草稿正文' })
  await dr.waitFor({ timeout: 10000 })
  await inject({ phase: 'draft', seq: SEQ, target: null, content: MK_D, ts: ++injTs })
  await page.waitForTimeout(300)
  rec('5a 草稿提示条出现', await barVisible(), `visible=${await barVisible()}`)
  await page.getByRole('button', { name: '填入草稿框' }).click()
  await page.waitForTimeout(300)
  v = await dr.innerText()
  rec('5b 草稿填入编辑器', v.includes(MK_D), `editor="${v.slice(0, 50)}"`)
  await page.getByRole('button', { name: '项目树' }).click()
  await chNode(2).click()
  await page.waitForTimeout(1500)
  await chNode(SEQ).click()
  await page.waitForTimeout(1500)
  v = await dr.innerText()
  rec('5c 草稿切章往返不丢', v.includes(MK_D), `editor="${v.slice(0, 50)}"`)
  const dnow = await getDraft()
  rec('5d 草稿已持久化(切章 flush)', ((dnow && dnow.prose) || '').includes(MK_D), `latest-draft=${JSON.stringify(((dnow && dnow.prose) || '').slice(0, 50))}`)

  await browser.close()

  console.log('\n==== RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.evidence}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
