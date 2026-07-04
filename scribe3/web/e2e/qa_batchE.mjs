// ── e2e · 批E 件1:块四b 塌栏 UX ────────────────────────────────────────────
// 运行:cd scribe3/web && node e2e/qa_batchE.mjs(需前端 :3311 + 后端 :3321 在跑)
// 目标书《纸命》work=book_c256380e。纯前端只读交互,零残留。
//
// 修复:左栏数据面板改用「上次章 seq」记忆。点伏笔行时 sel 从 chapter 变 promise(curSeq→null),
//   修前左栏塌回仅项目树(伏笔/母题/帧/演绎/校验 tab 全消失、当前 tab 复位);修后以最近一次章 seq
//   喂左栏,数据面板不塌 —— 点行浏览详情时台账仍在。
// 断言:点伏笔行后 ①左栏仍显「伏笔 · 埋/收台账」(未塌回项目树)②「校验」rail tab 仍在(数据 tab 未消失)
//   非回归:③中区出 CodexDetail 伏笔详情(块四b 导航保留)④主编聚焦该伏笔(块四b focus 保留)。
import { chromium } from 'playwright'

const FRONT = 'http://127.0.0.1:3311'

const results = []
const consoleErrors = []
const log = (...a) => console.log('[qaE]', ...a)
const rec = (name, pass, evidence) => { results.push({ name, pass, evidence }); log(pass ? 'PASS' : 'FAIL', '|', name, '|', evidence) }

const run = async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)) })
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)))

  const left = () => page.getByTestId('left')
  const detail = () => page.getByTestId('detail')
  const chiefLabel = () => page.getByTestId('chief-ctx').innerText().catch(() => '(no chief header)')
  const chNode = (n) => page.getByRole('button', { name: `${n} 第${n}章` })
  const tab = (n) => page.getByRole('button', { name: n, exact: true })
  const railHas = (n) => tab(n).first().isVisible().catch(() => false)
  const leftHas = (s) => left().getByText(s, { exact: false }).first().isVisible().catch(() => false)

  try {
    await page.goto(FRONT, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: /纸命/ }).first().click()
    await page.getByRole('button', { name: '未分卷' }).waitFor({ timeout: 10000 })

    // 开 ch4 → 切「大纲」讨论阶段(主编=DiscussionDock,读 chief-ctx)→ 切「伏笔」rail tab
    if (!(await chNode(4).isVisible().catch(() => false))) { await page.getByRole('button', { name: '未分卷' }).click() }
    await chNode(4).click()
    await page.waitForTimeout(700)
    await tab('大纲').click()
    await page.waitForTimeout(300)
    await tab('伏笔').click()
    await page.waitForTimeout(400)

    // BEFORE:章上下文下,左栏显伏笔台账 + 数据 tab(校验)在
    const beforeLedger = await leftHas('伏笔 · 埋/收台账')
    const beforeReview = await railHas('校验')
    rec('前置·点行前左栏在伏笔台账且数据tab(校验)在', beforeLedger && beforeReview,
      `ledger=${beforeLedger} 校验tab=${beforeReview}`)

    // 点伏笔行(块四b 注入的真伏笔)
    const pRow = left().getByRole('button', { name: /承影斋经手的那张借命契/ }).first()
    await pRow.waitFor({ timeout: 10000 })
    await pRow.click()
    await page.waitForTimeout(1000)

    // AFTER:核心断言 —— 数据面板不塌回项目树
    const afterLedger = await leftHas('伏笔 · 埋/收台账')
    const afterReview = await railHas('校验')
    rec('①点伏笔行后左栏仍显「伏笔·埋/收台账」(未塌回仅项目树)', afterLedger, `ledgerVisible=${afterLedger}`)
    rec('②点伏笔行后「校验」rail tab 仍在(数据 tab 未消失)', afterReview, `校验tab=${afterReview}`)

    // 非回归:块四b 点行导航 + 主编聚焦仍生效
    const dtxt = await detail().innerText().catch(() => '')
    const detailOk = dtxt.includes('承影斋经手的那张借命契') && (dtxt.includes('埋于') || dtxt.includes('兑现层级') || dtxt.includes('伏笔内容'))
    rec('③非回归·中区出 CodexDetail 伏笔详情(块四b 导航保留)', detailOk, `detailHead="${dtxt.replace(/\s+/g, ' ').slice(0, 80)}"`)
    const lbl = await chiefLabel()
    rec('④非回归·主编聚焦该伏笔(块四b focus 保留)', lbl.includes('伏笔 · ') && lbl.includes('承影'), `chief="${lbl}"`)
  } catch (e) {
    rec('FATAL', false, String(e).slice(0, 200))
  } finally {
    await browser.close()
  }

  console.log('\n==== RESULTS ====')
  for (const r of results) console.log(`${r.pass ? 'PASS' : 'FAIL'} | ${r.name} | ${r.evidence}`)
  console.log('==== CONSOLE ERRORS ====')
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(零错误)')
  if (results.some((r) => r.pass === false) || consoleErrors.length) process.exitCode = 2
}

run().catch((e) => { console.error('FATAL', e); process.exit(1) })
