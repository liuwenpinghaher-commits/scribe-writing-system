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
  await nameInput.fill(title); await nameInput.press('Enter'); await sleep(3000)
  // 进书成功标志:三栏布局容器出现(主编 dock / 详情栏)。不硬等 treeitem——新书项目树可能空。
  await p.waitForSelector('[data-testid="chief"], [data-testid="detail"]', { timeout: 12000 })
  const txt = await visText(p)
  const treeitems = await p.locator('[role="treeitem"]').count()
  return { title, hasChief: txt.includes('主编'), treeitems }
})

if (!r.ok) { console.error('FRONTEND SMOKE FAIL:', r.err, r.errs); process.exit(1) }
// 只对 PAGEERR(JS 崩溃)失败;CONSOLE network 错误(如新 session trace 404)不算前端渲染崩
const pageErrs = r.errs.filter((e) => e.startsWith('PAGEERR'))
if (pageErrs.length) { console.error('前端 JS 崩溃(pageerror):', pageErrs); process.exit(1) }
console.log('FRONTEND SMOKE OK', r.title, 'chief', r.hasChief, 'treeitems', r.treeitems, 'console噪声', r.errs.length)
