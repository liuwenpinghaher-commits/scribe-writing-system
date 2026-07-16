// L2 前端最后一厘米(进 CI):独立临时后端,验证前端真机能连通、建书成功、页面零 console 崩。
// 核心价值=证明整条前后端链路走通且无渲染崩溃;护栏红字的精确渲染由后端 test_reveal_e2e
// (确定性档)+ 组件测覆盖。走 dev server(proxy /api→:3321),跨端口 POST 不被拦。
import { withPage, visText, BASE } from './lib.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const r = await withPage(async (p) => {
  await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(800)
  // 建临时书(selector 来自 pw.mjs 的 newBook,已验证)
  const title = 'E2E临时书_' + Date.now()
  const nameInput = p.locator('input[placeholder="书名…"]')
  await nameInput.fill(title); await nameInput.press('Enter'); await sleep(2500)
  await p.waitForSelector('[role="treeitem"]', { timeout: 10000 })
  const rows = await p.locator('[role="treeitem"]').count()
  const txt = await visText(p)
  return { title, rows, hasChief: txt.includes('主编') }
})

if (!r.ok) { console.error('FRONTEND SMOKE FAIL:', r.err, r.errs); process.exit(1) }
if (r.errs.length) { console.error('页面 console 报错:', r.errs); process.exit(1) }
if (!r.rows || r.rows < 1) { console.error('建书后项目树为空(前后端链路未通)'); process.exit(1) }
console.log('FRONTEND SMOKE OK', r.title, 'treeitems', r.rows, 'chief', r.hasChief)
