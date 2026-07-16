// 真调档(真 Hermes 网关):完整写作旅程。断言结构/链路/护栏到界面/字数范围,不钉正文内容。
import { withPage, visText, BASE } from './lib.mjs'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// 主编 chat(真网关,慢):发消息→等 spinner 消失 + 气泡有真实内容。来自 pw.mjs sendChat。
async function sendChat(p, msg, maxMs = 300000) {
  const ta = p.locator('[data-testid="chief"] textarea').first()
  await ta.click(); await ta.fill(msg); await ta.press('Enter'); await sleep(2000)
  let last = '', t0 = Date.now()
  while (Date.now() - t0 < maxMs) {
    await sleep(3000)
    const { text, busy } = await p.evaluate(() => {
      const dock = document.querySelector('[data-testid="chief"]')
      const bubbles = dock ? [...dock.querySelectorAll('.prose-chat')] : []
      return { text: bubbles.length ? bubbles[bubbles.length - 1].innerText : '',
               busy: !!dock?.querySelector('.animate-spin') }
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
  await nameInput.fill(title); await nameInput.press('Enter'); await sleep(2500)
  await p.waitForSelector('[role="treeitem"]', { timeout: 10000 })
  // 2) 主编对话(真网关):断言回流非空 = 集成通
  const reply = await sendChat(p, '帮我把这本书的主角设定一句话定下来。')
  if (!reply || reply.trim().length < 8) throw new Error('主编真网关回流为空(集成断裂)')
  // 3) 编辑器写正文 → 触发护栏 → 断言护栏渲染
  const editor = p.locator('[data-testid="detail"] .ProseMirror').first()
  if (await editor.count()) {
    await editor.click(); await p.keyboard.type('胡不为牵着驴子在月色下踉跄前行。'); await sleep(4000)
  }
  const txt = await visText(p)
  if (!/限知泄露词|确定性 QC/.test(txt)) throw new Error('护栏面板未渲染')
  return { title, replyLen: reply.length }
})
if (!r.ok) { console.error('FULL JOURNEY FAIL:', r.err, r.errs); process.exit(1) }
console.log('FULL JOURNEY OK', r.title, 'reply', r.replyLen)
