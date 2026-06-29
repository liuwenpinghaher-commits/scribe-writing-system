// 真机操作库(CLI):node pw.mjs <action> '<jsonArgs>'
// 每次重开 headless chromium;书/章/设定状态在后端持久,故重导航即可续。
// 用途:从零真机走通「建书→主编交互写设定→四阶段写正文」全流程。
import { chromium } from 'playwright'
import { WORLD } from './pw_world.mjs'

const BASE = 'http://127.0.0.1:3311'
const SHOTS = '/tmp/goal_shots'
const action = process.argv[2]
const args = process.argv[3] ? JSON.parse(process.argv[3]) : {}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function withPage(fn) {
  const b = await chromium.launch()
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
  const errs = []
  p.on('pageerror', (e) => errs.push('PAGEERR ' + e.message))
  p.on('console', (m) => { if (m.type() === 'error') { const t = m.text(); if (!/ERR_CONNECTION_CLOSED|favicon/.test(t)) errs.push('CONSOLE ' + t.slice(0, 140)) } })
  try { const r = await fn(p); return { ok: true, errs, ...r } }
  catch (e) { let shot = null; try { shot = `${SHOTS}/error.png`; await p.screenshot({ path: shot }) } catch {}; return { ok: false, err: e.message, errs, shot } }
  finally { await b.close() }
}

// 进入书:到首页 → 点书卡(按 title)→ 等三栏
async function openBook(p, title) {
  await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(800)
  await p.getByText(title, { exact: false }).first().click()
  await sleep(2200)
  // 等项目树出现
  await p.waitForSelector('[role="treeitem"]', { timeout: 8000 }).catch(() => {})
}

const visText = async (p) => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ').slice(0, 500)

// 剥离主编回复里的解说/核实前言,只留正文产物
function cleanReply(s) {
  if (!s) return s
  const lines = s.split('\n').map((l) => l.trim()).filter(Boolean)
  const meta = /^(我先|让我|我来|好的|这是|核实|先核实|当前项目|项目状态|以下是|根据|基于已有|说明[:：]|注[:：]|大纲[:：]?$|本章大纲)/
  const kept = lines.filter((l) => !meta.test(l) && !/核实|项目状态|另一部|并非《/.test(l))
  return kept.join('\n').trim() || s.trim()
}

// 打开某章并切到某阶段 tab
async function openChapterTab(p, seq, tab) {
  await p.getByRole('treeitem').filter({ hasText: new RegExp('第\\s*' + seq + '\\s*章') }).first().click()
  await sleep(1800)
  if (tab) { await p.getByText(tab, { exact: true }).first().click(); await sleep(1200) }
}

// 右栏主编 chat:发一条消息,等流式响应真正完成,返回主编回复文本。
// 完成判定:发送按钮 spinner(busy)消失 + 最后一条 assistant 气泡有真实内容(非「主编在思考…」占位)。
// agentic 讨论会联查设定,慢(可达 1-3 分钟)。
async function sendChat(p, msg, { maxMs = 300000 } = {}) {
  const ta = p.locator('[data-testid="chief"] textarea').first()
  await ta.click(); await ta.fill(msg); await ta.press('Enter')
  await sleep(2000)
  const probe = () => p.evaluate(() => {
    const dock = document.querySelector('[data-testid="chief"]')
    if (!dock) return { text: '', busy: false }
    const bubbles = [...dock.querySelectorAll('.prose-chat')]
    const text = bubbles.length ? bubbles[bubbles.length - 1].innerText : ''
    const busy = !!dock.querySelector('.animate-spin')   // 发送按钮/流式 Loader2
    return { text, busy }
  })
  let last = '', stable = 0, t0 = Date.now()
  while (Date.now() - t0 < maxMs) {
    await sleep(3000)
    const { text, busy } = await probe()
    const real = text && !text.includes('主编在思考') && text.trim().length > 8
    if (!busy && real) {
      if (text === last) { stable++; if (stable >= 1) break } else stable = 0
    } else stable = 0
    last = text
  }
  return last
}

const ACTIONS = {
  // 新建空书并进入,返回是否成功进入三栏
  newBook: async (p) => {
    await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(800)
    const input = p.locator('input[placeholder="书名…"]')
    await input.fill(args.title)
    await input.press('Enter')
    await sleep(2500)
    await p.waitForSelector('[role="treeitem"]', { timeout: 10000 }).catch(() => {})
    const rows = await p.locator('[role="treeitem"]').count()
    const t = await visText(p)
    await p.screenshot({ path: `${SHOTS}/newbook.png` })
    return { rows, hasChief: t.includes('主编'), text: t.slice(0, 200) }
  },

  // 批量建设定:走真实表单(进分类→新建→渐进表单填字段→创建),一次会话建完 WORLD。
  seedSettings: async (p) => {
    await openBook(p, args.title)
    const nameOf = (s) => (s.fields.名字 || s.fields.势力名 || s.fields.物品名 || s.fields.术语名 || s.fields.规则名 || s.fields.母题名 || s.fields.伏笔内容 || '?').slice(0, 12)
    const done = []; const fail = []
    const only = args.only // 可选:只建某分类(调试)
    for (const s of WORLD) {
      if (only && s.cat !== only) continue
      try {
        await p.getByRole('treeitem').filter({ hasText: new RegExp('^' + s.cat) }).first().click(); await sleep(650)
        // 新建:空态点「点此新建」,否则点头部可见「新建」
        if (await p.getByText('点此新建').count()) await p.getByText('点此新建').first().click()
        else await p.locator('button:visible', { hasText: '新建' }).first().click()
        await sleep(650)
        for (const [label, val] of Object.entries(s.fields)) {
          const btn = p.getByRole('button', { name: new RegExp('添加' + label) })
          if (await btn.count() === 0) { fail.push(nameOf(s) + ':无字段「' + label + '」'); continue }
          await btn.first().click(); await sleep(380)
          await p.keyboard.type(String(val)); await sleep(140)
        }
        // 提交前先 blur 最后一个字段(点别处),再点创建
        await p.keyboard.press('Tab'); await sleep(200)
        await p.getByRole('button', { name: '创建' }).click(); await sleep(1100)
        const errTxt = await p.locator('[data-testid="detail"] .text-danger').first().innerText().catch(() => '')
        if (errTxt) { fail.push(nameOf(s) + ':' + errTxt.slice(0, 30)) } else done.push(nameOf(s))
      } catch (e) { fail.push(nameOf(s) + ':' + e.message.slice(0, 50)) }
    }
    await sleep(1200)
    const counts = await p.evaluate(() => {
      const t = document.querySelector('[role="tree"]')?.innerText || ''
      const m = {}; for (const c of ['角色', '势力', '物件', '术语', '世界规则', '伏笔', '母题']) { const x = t.match(new RegExp(c + '\\s+(\\d+)')); m[c] = x ? +x[1] : 0 }
      return m
    })
    await p.screenshot({ path: `${SHOTS}/settings_seeded.png` })
    return { created: done.length, fail, counts }
  },

  // 测试主编 chat:开章→切tab→发消息→等响应
  testChat: async (p) => {
    await openBook(p, args.title)
    await openChapterTab(p, args.seq || 1, args.tab || '大纲')
    await p.screenshot({ path: `${SHOTS}/chat_before.png` })
    const reply = await sendChat(p, args.msg)
    await p.screenshot({ path: `${SHOTS}/chat_after.png` })
    return { replyLen: reply.length, reply: reply.slice(0, 600) }
  },

  // 大纲阶段:主编讨论出大纲 → 填进 synopsis 编辑器 → 失焦保存
  doOutline: async (p) => {
    await openBook(p, args.title)
    await openChapterTab(p, args.seq || 1, '大纲')
    const raw = await sendChat(p, args.msg)
    if (!raw || raw.includes('主编在思考')) return { fail: '主编无响应', reply: raw }
    const reply = cleanReply(raw)
    // 填 synopsis 编辑器(中区 textarea)
    const ta = p.locator('[data-testid="detail"] textarea').first()
    await ta.click(); await ta.fill(reply)
    await p.getByText('大纲', { exact: true }).first().click()  // 点 tab 触发 blur→保存
    await sleep(1500)
    await p.screenshot({ path: `${SHOTS}/outline_${args.seq || 1}.png` })
    return { saved: reply.length, reply: reply.slice(0, 200) }
  },

  // 节拍阶段:主编据大纲拆有序节拍 → 逐条加入
  doBeats: async (p) => {
    await openBook(p, args.title)
    await openChapterTab(p, args.seq || 1, '节拍')
    const raw = await sendChat(p, args.msg)
    if (!raw || raw.includes('主编在思考')) return { fail: '主编无响应', reply: raw }
    // 解析节拍:主编可能用换行或空格分隔(中文无词内空格)→ 按空白切;去序号;滤前言。
    const metaRe = /^(我先|让我|我来|好的|这是|以下|根据|基于|据你|帮你|拆成|查看|核实|节拍|大纲|说明)/
    const beats = raw.split(/[\n\s]+/).map((l) => l.replace(/^[\-*0-9.、)）]+/, '').trim())
      .filter((l) => l.length >= 8 && l.length <= 60 && !metaRe.test(l) && !/[:：]$/.test(l)).slice(0, 8)
    // 先清空已有节拍(UI 删除按钮,force 点 hover 隐藏的),避免重跑追加
    for (let g = 0; g < 30; g++) {
      const del = p.locator('[data-testid="detail"] button[title="删除"]')
      if (await del.count() === 0) break
      await del.first().click({ force: true }); await sleep(400)
    }
    const input = p.locator('[data-testid="detail"] input').first()
    for (const b of beats) { await input.click(); await input.fill(b); await input.press('Enter'); await sleep(700) }
    await sleep(1200)
    await p.screenshot({ path: `${SHOTS}/beats_${args.seq || 1}.png` })
    return { added: beats.length, beats, rawLines: raw.split('\n').map((l) => l.trim()).filter(Boolean).slice(0, 12) }
  },

  // 草稿阶段:主编据大纲/节拍生成草稿 → 填进草稿编辑器 → 存草稿
  doDraft: async (p) => {
    await openBook(p, args.title)
    await openChapterTab(p, args.seq || 1, '草稿')
    const raw = await sendChat(p, args.msg)
    if (!raw || raw.includes('主编在思考')) return { fail: '主编无响应', reply: raw }
    const draft = cleanReply(raw)
    const ta = p.locator('[data-testid="detail"] textarea').last()  // 草稿正文 textarea(summary 在前)
    await ta.click(); await ta.fill(draft)
    await p.getByRole('button', { name: /存草稿/ }).click(); await sleep(1500)
    await p.screenshot({ path: `${SHOTS}/draft_${args.seq || 1}.png` })
    return { draftLen: draft.length, draft: draft.slice(0, 150) }
  },

  // 正文阶段:写作 chat → 草稿卡「接受」→ 续写循环到 ≥target 字 → 存为正文
  doFinal: async (p) => {
    await openBook(p, args.title)
    await openChapterTab(p, args.seq || 1, '正文')
    // 重写前清空正文(否则首条提案会 append 旧稿→新旧拼接)。clear=true 时执行。
    if (args.clear) {
      const ed = p.locator('[data-testid="detail"] .ProseMirror').first()
      await ed.click(); await p.keyboard.press('Meta+a'); await p.keyboard.press('Backspace'); await sleep(700)
      await p.getByRole('button', { name: '存为正文' }).first().click(); await sleep(2200)
    }
    const target = args.target || 5200
    const maxRounds = args.maxRounds || 6
    const proseLen = () => p.evaluate(() => {
      const ed = document.querySelector('[data-testid="detail"] .ProseMirror')
      return ed ? ed.innerText.replace(/\s/g, '').length : 0
    })
    // 发写作消息 → 等草稿卡「接受」可点(proposal 流完)→ 接受(applyProposal→persist 落库)
    const sendWrite = async (msg) => {
      const ta = p.locator('[data-testid="chief"] textarea').first()
      await ta.click(); await ta.fill(msg); await ta.press('Enter')
      const accept = p.getByRole('button', { name: '接受', exact: true })
      const t0 = Date.now()
      while (Date.now() - t0 < 280000) {
        await sleep(4000)
        if (await accept.count()) {
          const en = await accept.first().isEnabled().catch(() => false)
          if (en) { await sleep(2500); if (await accept.first().isEnabled().catch(() => false)) break }
        }
      }
      if (await accept.count() === 0) return false
      await accept.first().click(); await sleep(3500)
      return true
    }
    const rounds = []
    const ok1 = await sendWrite(args.firstMsg)
    rounds.push({ r: 1, ok: ok1, len: await proseLen() })
    let r = 1
    while ((await proseLen()) < target && r < maxRounds) {
      const ok = await sendWrite(args.contMsg || '接着上文继续往下写,推进到下一节拍,约+1800字。不要重复已写内容,换感官换喻体,保持柳怀玉限知志怪笔记体。直接写正文。')
      r++; rounds.push({ r, ok, len: await proseLen() })
      if (!ok) break
    }
    await p.getByRole('button', { name: '存为正文' }).first().click(); await sleep(3500)
    await p.screenshot({ path: `${SHOTS}/final_${args.seq || 1}.png` })
    return { finalLen: await proseLen(), rounds }
  },

  // 一次会话走完一章四阶段:大纲→节拍→草稿→正文(≥target,清空重写)。用于第2-4章高效推进。
  writeChapter: async (p) => {
    await openBook(p, args.title)
    const seq = args.seq
    const out = { seq }
    const switchTab = async (tab) => { await p.getByText(tab, { exact: true }).first().click(); await sleep(1300) }
    // —— 大纲 ——
    await openChapterTab(p, seq, '大纲')
    let raw = await sendChat(p, args.outlineMsg)
    const syn = cleanReply(raw)
    if (syn && !syn.includes('主编在思考')) {
      const ta = p.locator('[data-testid="detail"] textarea').first()
      await ta.click(); await ta.fill(syn); await switchTab('大纲'); await sleep(1200)
    }
    out.outline = syn.length
    // —— 节拍 ——
    await switchTab('节拍')
    raw = await sendChat(p, args.beatsMsg)
    const metaRe = /^(我先|让我|我来|好的|这是|以下|根据|基于|据你|帮你|拆成|查看|核实|节拍|大纲|说明)/
    const beats = raw.split(/[\n\s]+/).map((l) => l.replace(/^[\-*0-9.、)）]+/, '').trim())
      .filter((l) => l.length >= 8 && l.length <= 60 && !metaRe.test(l) && !/[:：]$/.test(l)).slice(0, 8)
    for (let g = 0; g < 30; g++) { const del = p.locator('[data-testid="detail"] button[title="删除"]'); if (await del.count() === 0) break; await del.first().click({ force: true }); await sleep(350) }
    const binput = p.locator('[data-testid="detail"] input').first()
    for (const b of beats) { await binput.click(); await binput.fill(b); await binput.press('Enter'); await sleep(650) }
    out.beats = beats.length
    // —— 草稿 ——
    await switchTab('草稿')
    raw = await sendChat(p, args.draftMsg)
    const draft = cleanReply(raw)
    if (draft && !draft.includes('主编在思考')) {
      const tad = p.locator('[data-testid="detail"] textarea').last()
      await tad.click(); await tad.fill(draft); await p.getByRole('button', { name: /存草稿/ }).click(); await sleep(1400)
    }
    out.draft = draft.length
    // —— 正文(清空→写循环→存为正文)——
    await switchTab('正文')
    const ed = p.locator('[data-testid="detail"] .ProseMirror').first()
    await ed.click(); await p.keyboard.press('Meta+a'); await p.keyboard.press('Backspace'); await sleep(700)
    await p.getByRole('button', { name: '存为正文' }).first().click(); await sleep(2200)
    const proseLen = () => p.evaluate(() => { const e = document.querySelector('[data-testid="detail"] .ProseMirror'); return e ? e.innerText.replace(/\s/g, '').length : 0 })
    const sendWrite = async (msg) => {
      const ta = p.locator('[data-testid="chief"] textarea').first()
      await ta.click(); await ta.fill(msg); await ta.press('Enter')
      const accept = p.getByRole('button', { name: '接受', exact: true })
      const t0 = Date.now()
      while (Date.now() - t0 < 280000) {
        await sleep(4000)
        if (await accept.count()) { const en = await accept.first().isEnabled().catch(() => false); if (en) { await sleep(2500); if (await accept.first().isEnabled().catch(() => false)) break } }
      }
      if (await accept.count() === 0) return false
      await accept.first().click(); await sleep(3500); return true
    }
    const target = args.target || 5200, maxRounds = args.maxRounds || 6
    const fr = []
    fr.push(await sendWrite(args.finalFirstMsg)); let r = 1
    while ((await proseLen()) < target && r < maxRounds) { const ok = await sendWrite(args.finalContMsg); r++; fr.push(ok); if (!ok) break }
    await p.getByRole('button', { name: '存为正文' }).first().click(); await sleep(3500)
    out.final = await proseLen(); out.rounds = fr.length
    await p.screenshot({ path: `${SHOTS}/chapter_${seq}.png` })
    return out
  },

  // 截图当前书的某状态(调试用)
  shot: async (p) => {
    await openBook(p, args.title)
    await p.screenshot({ path: `${SHOTS}/${args.name || 'shot'}.png` })
    return { text: await visText(p) }
  },
}

const fn = ACTIONS[action]
if (!fn) { console.log(JSON.stringify({ ok: false, err: 'unknown action ' + action, actions: Object.keys(ACTIONS) })); process.exit(1) }
const res = await withPage(fn)
console.log(JSON.stringify(res))
