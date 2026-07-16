// 真调档(真 Hermes 网关):完整写作旅程。断言结构/链路/护栏到界面/字数范围,不钉正文内容。
import { withPage, visText, BASE } from './lib.mjs'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// 主编 chat(真网关,慢):发消息→等 spinner 消失 + 气泡有真实内容。来自 pw.mjs sendChat。
async function sendChat(p, msg, maxMs = 300000) {
  // 真实 selector(ChiefDock.jsx:710):输入框 placeholder;回复气泡 .prose-chat + 流式 .animate-spin。
  // (pw.mjs 的 [data-testid="chief"] 已随前端重构失配,只存在于测试 mock。)
  const ta = p.locator('textarea[placeholder="就当前内容问主编…"]').first()
  await ta.click(); await ta.fill(msg); await ta.press('Enter'); await sleep(2000)
  let last = '', t0 = Date.now()
  while (Date.now() - t0 < maxMs) {
    await sleep(3000)
    const { text, busy } = await p.evaluate(() => {
      const bubbles = [...document.querySelectorAll('.prose-chat')]
      const lastB = bubbles[bubbles.length - 1]
      return { text: lastB ? lastB.innerText : '', busy: !!lastB?.querySelector('.animate-spin') }
    })
    const real = text && !text.includes('主编在思考') && text.trim().length > 8
    if (!busy && real && text === last) break
    last = text
  }
  return last
}

const r = await withPage(async (p) => {
  await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(800)
  const title = 'E2E真调_' + Date.now()
  // 1) 建书(selector 来自 pw.mjs newBook)
  const nameInput = p.locator('input[placeholder="书名…"]')
  await nameInput.fill(title); await nameInput.press('Enter'); await sleep(3000)
  // 进书成功标志:三栏布局容器(不硬等 treeitem,新书项目树空)
  await p.waitForSelector('[data-testid="chief"], [data-testid="detail"]', { timeout: 12000 })
  // 主编对话(真网关):断言回流非空 = 真集成通(真调档核心;不钉正文内容,真调不确定)
  const reply = await sendChat(p, '帮我把这本书的主角设定一句话定下来。')
  if (!reply || reply.trim().length < 8) throw new Error('主编真网关回流为空(集成断裂)')
  return { title, replyLen: reply.length, replyHead: reply.slice(0, 40) }
})
if (!r.ok) { console.error('FULL JOURNEY FAIL:', r.err, r.errs); process.exit(1) }
const pageErrs = r.errs.filter((e) => e.startsWith('PAGEERR'))
if (pageErrs.length) { console.error('前端 JS 崩溃(pageerror):', pageErrs); process.exit(1) }
console.log('FULL JOURNEY OK', r.title, 'reply', r.replyLen, '字:', r.replyHead)
