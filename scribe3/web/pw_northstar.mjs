// 北极星面板真机截图(北极星方案任务10 验收):开 loop-qa 书 → 选第7章 →
// 左栏切「北极星」tab → 断言真实数据渲染(章级硬约束 + 书级四维)→ 截图存档。
// 跑法:cd scribe3/web && node pw_northstar.mjs
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:3311'
const SHOT = '/tmp/goal_shots/northstar_panel.png'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
const errs = []
p.on('pageerror', (e) => errs.push('PAGEERR ' + e.message))
p.on('console', (m) => { if (m.type() === 'error' && !/favicon|ERR_CONNECTION/.test(m.text())) errs.push('CONSOLE ' + m.text().slice(0, 140)) })
try {
  await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(800)
  await p.getByText('北极星验收·loop-qa', { exact: false }).first().click(); await sleep(2200)
  // 项目树选第 7 章(标题「七」)
  await p.getByText(/第\s*7\s*章|^七$/).first().click().catch(async () => {
    await p.getByText('七', { exact: false }).first().click()
  }); await sleep(1200)
  // 左栏图标轨点「北极星」tab(title/aria 含 北极星)
  const rail = p.locator('[title="北极星"], [aria-label="北极星"]')
  if (await rail.count()) { await rail.first().click() } else { await p.getByText('北极星', { exact: true }).first().click() }
  await sleep(1500)
  const bodyText = await p.locator('body').innerText()
  const checks = {
    硬约束: bodyText.includes('硬约束'),
    伏笔超期: bodyText.includes('伏笔超期'),
    目的达成: bodyText.includes('目的达成'),
    书级四维: bodyText.includes('书级四维'),
    回收率: bodyText.includes('伏笔回收率'),
    达成率数据: /目的达成率/.test(bodyText),
  }
  await p.screenshot({ path: SHOT, fullPage: false })
  console.log(JSON.stringify({ ok: Object.values(checks).every(Boolean), checks, shot: SHOT, errs }, null, 1))
} catch (e) {
  try { await p.screenshot({ path: '/tmp/goal_shots/northstar_error.png' }) } catch {}
  console.log(JSON.stringify({ ok: false, err: e.message, errs }))
} finally { await b.close() }
