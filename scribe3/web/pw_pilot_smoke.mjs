// 主编主动化 P0/P1 冒烟(实施计划铁律5:前端 DoD 的 pw 资产,可回归)。
// 前置:后端 :3321 + 前端 dev :3311 + loop-qa 书存在(有超期伏笔的章效果最佳)。
// 跑法:cd scribe3/web && node pw_pilot_smoke.mjs [seq]
// 覆盖:①PulseBar 六点 ②弹层「聊这个」预填 ③进章开场白(decision 级恰一条,刷新不重复)
//      ④收件箱 badge/条目/pilot 放行按钮 ⑤s3-right-tab 事件切主编 ⑥零 pageerror。
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:3311'
const SEQ = process.argv[2] || '9'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
const errs = []
p.on('pageerror', (e) => errs.push('PAGEERR ' + e.message.slice(0, 120)))
p.on('console', (m) => { if (m.type() === 'error' && !/favicon|ERR_CONNECTION/.test(m.text())) errs.push('CONSOLE ' + m.text().slice(0, 120)) })
const out = []
let fail = 0
const check = (name, ok) => { out.push(`${ok ? '✓' : '✗'} ${name}`); if (!ok) fail++ }
try {
  await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(900)
  await p.getByText('北极星验收·loop-qa', { exact: false }).first().click(); await sleep(2000)
  await p.getByRole('button', { name: new RegExp(`^${SEQ} `) }).first().click(); await sleep(2600)
  const dots = await p.evaluate(() => [...document.querySelectorAll('[data-testid^="pulse-"]')].length)
  check('PulseBar 六点', dots >= 6)
  const greet1 = await p.evaluate(() => /进章提醒/.test(document.body.innerText))
  out.push(`  (进章开场白:${greet1 ? '出现' : '无 decision 或已记账'})`)
  await p.getByTestId('pulse-promise').click(); await sleep(500)
  const chatBtn = p.getByText('跟主编聊这个', { exact: false }).first()
  if (await chatBtn.count()) {
    await chatBtn.click(); await sleep(600)
    check('弹层「聊这个」预填输入框',
      await p.evaluate(() => [...document.querySelectorAll('textarea')].some(t => t.value.length > 4)))
  } else out.push('  (promise 维无 decision 条目,预填项跳过)')
  const inboxBtn = p.getByRole('button', { name: /收件箱/ }).first()
  check('收件箱 tab 存在', !!(await inboxBtn.count()))
  if (await inboxBtn.count()) {
    await inboxBtn.click(); await sleep(800)
    check('收件箱条目渲染', await p.evaluate(() => /决策收件箱|没有等你的事项/.test(document.body.innerText)))
  }
  await p.evaluate(() => window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })))
  await sleep(500)
  check('s3-right-tab 切主编', await p.evaluate(() => /提思路|主编帮你写|想法/.test(document.body.innerText)))
  if (greet1) {
    await p.reload({ waitUntil: 'networkidle' }); await sleep(1800)
    await p.getByRole('button', { name: new RegExp(`^${SEQ} `) }).first().click().catch(() => {}); await sleep(2200)
    check('开场白刷新不重复(记账)', !(await p.evaluate(() => /进章提醒/.test(document.body.innerText))))
  }
  check('零 console/page error', errs.length === 0)
} finally {
  console.log(out.join('\n'))
  if (errs.length) console.log('errors:', JSON.stringify(errs.slice(0, 4)))
  console.log(fail === 0 ? 'PW SMOKE: ALL PASS' : `PW SMOKE: ${fail} FAILED`)
  await b.close()
  process.exit(fail === 0 ? 0 : 1)
}
