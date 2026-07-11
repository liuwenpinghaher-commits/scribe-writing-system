// ── e2e · 批E 件1:块四b 塌栏 UX ──【已退役 2026-07-11 · 旧三栏时代只读 e2e】────────
// ⚠ 退役说明:本脚本建立在【旧三栏 LeftDock】DOM 假设上——单个 data-testid="left" 列
//   同时承载 rail 页签(大纲/节拍/伏笔/母题/校验,role=button)与其下的数据面板。PC UI 四栏
//   系统整修后该假设整体失效:① data-testid="left" 已不存在(拆成 栏1 入口轨 left-entry-rail /
//   栏2 目录 col-directory);② 大纲/节拍 阶段页签上移 ObjectFrame 顶栏并改 role="tab";
//   ③ 伏笔/校验 成入口轨 caps(aria-label);④ 它所测的"点伏笔行→左栏数据面板塌回项目树"这一
//   bug 在四栏架构下已无法复现。逐一硬修选择器会连环崩(未分卷 strict-mode → tab('大纲') 角色
//   不匹配 → getByTestId('left') 空定位 FATAL),故不硬修。
//   四栏只读验收已由 ../pw_layout.mjs v2 取代且更严:三视口(1280/1440/1600)×双主题 + 全程
//   POST/PATCH/DELETE 只读拦截 + 0 console error + detail≥600/右栏不重叠 + 目录常驻 + DOM 单套
//   + 视图往返 + 键盘可自动化项。本脚本待按四栏重写,不阻塞 PC UI 验收(以 pw_layout 为准)。
import { chromium } from 'playwright'

console.log('[qaE] RETIRED — 旧三栏时代只读 e2e;四栏只读验收已由 pw_layout.mjs v2 取代(更严、覆盖三视口×双主题只读拦截)。此脚本待四栏重写,本次跳过并退出 0。')
process.exit(0)

// ↓↓↓ 历史断言(旧三栏 DOM,勿在四栏下运行;留档供未来四栏重写参考)↓↓↓

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
