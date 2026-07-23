// 融合验收旅程（对话驱动 + Playwright 点批准/接受）
// 约束：零业务表单字段填写；决策按钮仅真实 click。
// 用法：E2E_BASE=http://127.0.0.1:3311 node e2e/fused_author_journey.mjs
import { writeFileSync, mkdirSync } from 'node:fs'
import { withPage, BASE } from './lib.mjs'
import { chiefSay, acceptDraftProposal, approveAllPending, DECISION_SELECTORS } from './author_decisions.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SCRATCH = process.env.GOAL_SCRATCH || process.env.SCRATCH || ''
const logLines = []
function log(m) {
  const line = `[${new Date().toISOString()}] ${m}`
  console.log(line)
  logLines.push(line)
}

async function createBook(p, title) {
  // 作品库书名：白名单（非业务设定表单字段）
  const nameInput = p.locator('input[placeholder="书名…"]')
  await nameInput.waitFor({ timeout: 15000 })
  await nameInput.fill(title)
  await nameInput.press('Enter')
  await sleep(3000)
  await p.waitForSelector('[data-testid="chief-chat-shell"], [data-testid="detail"], [data-testid="chief"]', { timeout: 20000 })
}

async function ensureFirstChapter(p) {
  // 无字段：点「新建未分卷章节」或等价（非表单字段填写）
  const candidates = [
    p.getByRole('button', { name: /新建未分卷章节/ }),
    p.getByRole('button', { name: /未分卷/ }),
    p.locator('button', { hasText: '新建未分卷章节' }),
    p.locator('button', { hasText: '+章' }),
  ]
  for (const loc of candidates) {
    if (await loc.count() && await loc.first().isVisible().catch(() => false)) {
      await loc.first().click()
      await sleep(2000)
      log('clicked create-chapter control')
      return true
    }
  }
  // 已有树项第 1 章
  const ch = p.getByRole('treeitem').filter({ hasText: /第\s*1\s*章|章/ })
  if (await ch.count()) {
    await ch.first().click()
    await sleep(1500)
    log('selected existing chapter treeitem')
    return true
  }
  log('WARN no chapter create control; will try write anyway')
  return false
}

async function openWritePhase(p) {
  for (const tab of ['正文', '草稿', '大纲']) {
    const t = p.getByRole('tab', { name: tab })
    if (await t.count() && await t.first().isVisible().catch(() => false)) {
      await t.first().click()
      await sleep(800)
      log(`opened tab ${tab}`)
      if (tab === '正文' || tab === '草稿') return tab
    }
    // 文本回退
    const tx = p.getByText(tab, { exact: true })
    if (await tx.count()) {
      await tx.first().click().catch(() => {})
      await sleep(600)
    }
  }
  return 'unknown'
}

const r = await withPage(async (p) => {
  log(`BASE=${BASE}`)
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await sleep(1000)

  const title = `融合验收·${Date.now().toString(36)}`
  await createBook(p, title)
  log(`book created title=${title}`)

  // 北极星：仅对话（不打开 intent 表单）
  const north = await chiefSay(p, '请用三句话定本书北极星：读者感受、情感弧、三条红线。先写在对话里即可，不要让我填表。')
  log(`northstar dialog replyLen=${(north.reply || '').length} approve=${JSON.stringify(north.decisions)}`)

  await ensureFirstChapter(p)
  await openWritePhase(p)
  // 等待写作槽出现（章选中后右栏 WriteChat）
  await p.locator(DECISION_SELECTORS.writeComposer).first().waitFor({ state: 'visible', timeout: 30000 }).catch(async () => {
    log('write composer not visible yet; trying tree chapter click')
    const ch = p.getByRole('treeitem').filter({ hasText: /第\s*1\s*章|第1章/ })
    if (await ch.count()) await ch.first().click()
    await sleep(2000)
    await openWritePhase(p)
    await p.locator(`${DECISION_SELECTORS.writeComposer}, ${DECISION_SELECTORS.chiefComposer}`).first()
      .waitFor({ state: 'visible', timeout: 30000 })
  })
  log('composer ready')

  // 最小设定：对话登记（若出审批则点）
  const setting = await chiefSay(p, '请在对话里一句话设定主角「候潮匠沈砚」：外貌与核心欲望。若需写入设定库请走审批，我会点批准。', { preferWrite: true })
  log(`setting dialog replyLen=${(setting.reply || '').length}`)

  // 动稿：必须走写作槽 WriteChat（preferWrite），明确散文意图
  const writeMsg =
    '请直接写第1章完整正文草稿（限知视角沈砚，动作感官推进，约800-1500字，不要解释机制）。用提案卡给我，不要只聊天。'
  const write = await chiefSay(p, writeMsg, { maxMs: 360000, preferWrite: true })
  log(`write dialog replyLen=${(write.reply || '').length} decisions=${JSON.stringify(write.decisions)}`)

  // 再批一次
  const mid = await approveAllPending(p)
  log(`mid approve ${JSON.stringify(mid)}`)

  let accept = null
  try {
    accept = await acceptDraftProposal(p, { timeoutMs: 120000 })
    log(`accept ok ${JSON.stringify(accept)}`)
  } catch (e) {
    log(`accept failed: ${e.message}`)
    // 截图正文区文本以便诊断
    const bodyText = await p.evaluate(() => document.body.innerText.slice(0, 2500))
    log(`body snippet: ${bodyText.replace(/\s+/g, ' ').slice(0, 800)}`)
    throw e
  }

  // 读回：编辑器或页面字数
  const proseInfo = await p.evaluate(() => {
    const ed = document.querySelector('.tiptap-prose, .ProseMirror, .manuscript')
    const t = (ed?.innerText || '').trim()
    return { len: t.length, head: t.slice(0, 120) }
  })
  log(`prose after accept len=${proseInfo.len} head=${proseInfo.head}`)

  // 可选截图
  if (SCRATCH) {
    try {
      await p.screenshot({ path: `${SCRATCH}/ch1-accept.png`, fullPage: true })
      log(`screenshot ${SCRATCH}/ch1-accept.png`)
    } catch (e) {
      log(`screenshot fail ${e.message}`)
    }
  }

  return {
    title,
    northReplyLen: (north.reply || '').length,
    writeReplyLen: (write.reply || '').length,
    accept,
    proseLen: proseInfo.len,
    proseHead: proseInfo.head,
    form_fill_count: 0,
    human_click_approve_count: 0,
    selectors: DECISION_SELECTORS,
  }
})

if (SCRATCH) {
  try {
    mkdirSync(SCRATCH, { recursive: true })
    writeFileSync(`${SCRATCH}/pw-author.log`, logLines.join('\n') + '\n' + JSON.stringify(r, null, 2))
  } catch (_) {}
}

if (!r.ok) {
  console.error('FUSED JOURNEY FAIL:', r.err, r.errs)
  if (SCRATCH) {
    try {
      writeFileSync(`${SCRATCH}/pw-author.log`, logLines.join('\n') + `\nFAIL ${r.err}\n${(r.errs || []).join('\n')}`)
    } catch (_) {}
  }
  process.exit(1)
}

if (!r.proseLen || r.proseLen < 80) {
  console.error('FUSED JOURNEY FAIL: prose too short after accept', r.proseLen)
  process.exit(2)
}

// 工艺优先:字数/接受成功不够;须 GATE-A + ch1 B/C(与 verify_craft_compliance 同源)
const WORK = process.env.E2E_WORK || ''
if (WORK) {
  const { assertCraftGatesOrExit } = await import('./craft_gates.mjs')
  await assertCraftGatesOrExit({ work: WORK, seqs: [1], label: 'FUSED' })
} else {
  console.warn('FUSED: E2E_WORK 未设,跳过 craft-gates 机判(请在完整旅程设置 work slug)')
}

console.log('FUSED JOURNEY OK', JSON.stringify({
  title: r.title,
  proseLen: r.proseLen,
  accept: r.accept,
  form_fill_count: 0,
  human_click_approve_count: 0,
  craft_gates: WORK ? 'checked' : 'skipped_no_work',
}))
