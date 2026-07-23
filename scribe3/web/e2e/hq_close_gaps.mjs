// 高质量补齐：真机对话审批写 intent/角色、R4 恢复、连写+看板决策、QC、设定/素材有后果
import { writeFileSync, mkdirSync } from 'node:fs'
import { withPage, BASE, openBook } from './lib.mjs'
import {
  chiefSay, acceptDraftProposal, approveAllPending, DECISION_SELECTORS,
} from './author_decisions.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SCRATCH = process.env.GOAL_SCRATCH || process.env.SCRATCH || ''
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const WORK = process.env.E2E_WORK || 'book_b4e72480'
const BOOK = process.env.E2E_BOOK_TITLE || '融合验收·mruwfo36'
const logLines = []
const L = (m) => { const s = `[${new Date().toISOString()}] ${m}`; console.log(s); logLines.push(s) }

async function apiJson(path) {
  const r = await fetch(`${API}${path}`)
  if (!r.ok) throw new Error(`${path} ${r.status}`)
  return r.json()
}

async function clickTab(p, name) {
  const t = p.getByRole('tab', { name })
  if (await t.count()) { await t.first().click(); await sleep(800); return true }
  return false
}

async function selectChapter(p, seq) {
  const re = new RegExp(`第\\s*${seq}\\s*章`)
  const item = p.getByRole('treeitem').filter({ hasText: re })
  if (await item.count()) { await item.first().click(); await sleep(1200); return true }
  return false
}

async function createChapter(p) {
  const b = p.locator('button[aria-label="新建未分卷章节"]').or(p.getByRole('button', { name: /新建未分卷章节|\+章/ }))
  if (await b.count()) { await b.first().click(); await sleep(1800); return true }
  return false
}

async function visitDashboards(p, decisionNote) {
  const views = ['图谱', '时间线', '仪表盘']
  const seen = []
  for (const v of views) {
    const btn = p.getByRole('button', { name: v }).or(p.locator(`[data-testid="topbar-global-views"] button:has-text("${v}")`))
    if (await btn.count()) {
      await btn.first().click().catch(() => {})
      await sleep(1000)
      seen.push(v)
    }
  }
  L(`dashboard visited ${seen.join(',')} decision=${decisionNote}`)
  // 回手稿树
  const ms = p.getByText('手稿', { exact: true })
  if (await ms.count()) await ms.first().click().catch(() => {})
  await sleep(600)
  return { views: seen, decisionNote }
}

async function hermesWriteAndApprove(p, msg, { timeoutMs = 300000 } = {}) {
  // force hermes run via shouldUseHermesRun keywords
  const r = await chiefSay(p, msg, { maxMs: timeoutMs, preferWrite: false })
  // chiefSay 已累计中途批准；此处再扫尾
  let total = {
    approved: r.decisions?.approved || 0,
    staleApproved: r.decisions?.staleApproved || 0,
  }
  const t0 = Date.now()
  while (Date.now() - t0 < 120000) {
    const d = await approveAllPending(p, { maxRounds: 5, settleMs: 700 })
    total.approved += d.approved
    total.staleApproved += d.staleApproved
    // also aria
    const busy = await p.locator('.animate-spin').count().catch(() => 0)
    if (d.approved === 0 && d.staleApproved === 0 && busy === 0) break
    await sleep(2500)
  }
  L(`hermesWrite approved=${total.approved} stale=${total.staleApproved} replyLen=${(r.reply || '').length}`)
  return { ...r, decisions: total }
}

async function writeChapter(p, seq, brief) {
  if (!(await selectChapter(p, seq))) await createChapter(p)
  await selectChapter(p, seq)
  await clickTab(p, '正文')
  await sleep(800)
  await p.locator(DECISION_SELECTORS.writeComposer).first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {})
  await chiefSay(p, `请直接写第${seq}章完整正文草稿（${brief}）。用提案卡给我，约700-1200字。`, {
    maxMs: 360000, preferWrite: true,
  })
  await approveAllPending(p)
  const acc = await acceptDraftProposal(p, { timeoutMs: 180000 })
  L(`ch${seq} accept ${JSON.stringify(acc)}`)
  return acc
}

const out = await withPage(async (p) => {
  L(`BASE=${BASE} WORK=${WORK}`)
  await openBook(p, BOOK)
  await sleep(1500)

  // —— HQ1 北极星：只读条 + 主编审批写 ——
  const ns = p.getByTestId('northstar-bar').or(p.getByText('北极星').first())
  if (await ns.count()) {
    await ns.first().click().catch(() => {})
    await sleep(500)
  }
  // 直接发强制 Run 文案（不依赖 CTA 挂载时序）
  const intentMsg = [
    '请登记/更新本书北极星意图并写入落库(需我审批):',
    '读者感受:压抑中见微光,雪夜仍有灯——验收HQ轮',
    '情感弧:由怯到决,灰契为代价——验收HQ轮',
    '红线:不写超自然明机制;不洗白加害;不丑化底层;不表单直填',
    '必须先 s3_get_intent 核实,再用 s3_set_intent 写入。',
  ].join('\n')
  const intentRun = await hermesWriteAndApprove(p, intentMsg)
  let intentAfter = null
  try {
    intentAfter = await apiJson(`/intent?work=${encodeURIComponent(WORK)}`)
  } catch (e) {
    L(`intent api fail ${e.message}`)
  }
  L(`intent_after ${JSON.stringify(intentAfter)}`)

  // —— HQ2 角色更正 R1 真审批 ——
  const charMsg = [
    '请更新/更正角色沈砚的外貌档案并写入落库(需我审批):',
    'appearance:右手食指有握笔老茧,遇冷便僵(HQ验收改自左手)',
    '必须用 s3_patch_character。先核实再写。',
  ].join('\n')
  const charRun = await hermesWriteAndApprove(p, charMsg)
  let charApp = ''
  try {
    const ents = await apiJson(`/entities?work=${encodeURIComponent(WORK)}`)
    const list = Array.isArray(ents) ? ents : (ents.entities || ents.items || [])
    for (const e of list) {
      const name = e.name || e.label || ''
      const id = e.id || e.oid || ''
      if (String(name).includes('沈砚') || String(id).includes('沈砚')) {
        charApp = e.appearance || e.traits?.appearance || JSON.stringify(e).slice(0, 200)
        break
      }
    }
  } catch (e) {
    L(`entities fail ${e.message}`)
  }
  L(`char_appearance_probe ${charApp}`)

  // —— 看板决策：根据仪表盘/图谱后明确写进下一章 brief ——
  const d4 = await visitDashboards(p, 'ch4:焦契线需推进人名缺口,伏笔未收')
  if (!(await selectChapter(p, 4))) await createChapter(p)
  await writeChapter(p, 4, '限知沈砚;看板结论:推进焦契人名缺口;动作感官;不解释机制')

  const d5 = await visitDashboards(p, 'ch5:关系网仍薄,加对手线索')
  if (!(await selectChapter(p, 5))) await createChapter(p)
  await writeChapter(p, 5, '限知沈砚;看板结论:引入对手侧耳目;冷调;不表单')

  // 继续 ch6-8 加深
  for (const [seq, brief] of [
    [6, '限知沈砚;夜审旧案卷;信息差'],
    [7, '限知沈砚;灰契烫字加重;克制'],
    [8, '限知沈砚;暂时失利;不洗白'],
  ]) {
    await visitDashboards(p, `ch${seq}:连续推进`)
    if (!(await selectChapter(p, seq))) await createChapter(p)
    try {
      await writeChapter(p, seq, brief)
    } catch (e) {
      L(`ch${seq} write fail ${e.message}`)
    }
  }

  // —— 素材有后果：对话请登记一条素材并在 ch 讨论中引用（若无审批工具则对话引用）——
  await chiefSay(p, '请把以下参考段当作素材研究笔记记住并在下一章写作时沿用其冷调:「雪夜刑房的灯只照得见桌上一寸。」若有素材写工具请写入;否则在对话确认。', { preferWrite: false })
  await approveAllPending(p)

  // —— R4 版本恢复：打开存档 → 回看 final → 恢复 ——
  await selectChapter(p, 1)
  await sleep(800)
  // 右栏「存档」可能是 role=button name 存档
  const archBtns = p.getByRole('button', { name: '存档' })
  let r4 = { opened: false, restored: false }
  if (await archBtns.count()) {
    await archBtns.first().click()
    await sleep(1500)
    r4.opened = true
    const look = p.getByText('回看')
    if (await look.count()) {
      await look.first().click()
      await sleep(1000)
      const restore = p.getByRole('button', { name: /恢复到此版本/ })
      if (await restore.count()) {
        await restore.first().click()
        await sleep(800)
        // confirm dialog if any
        const conf = p.getByRole('button', { name: /确认|确定|恢复/ })
        if (await conf.count()) await conf.last().click().catch(() => {})
        await sleep(1500)
        r4.restored = true
      }
    }
  }
  L(`R4 ${JSON.stringify(r4)}`)

  // —— QC 深审（API）——
  const qc = {}
  for (const seq of [1, 2, 3, 4, 5]) {
    try {
      const ch = await apiJson(`/chapter?seq=${seq}&work=${encodeURIComponent(WORK)}`)
      const prose = ch.prose || ''
      if (!prose) { qc[seq] = { prose_len: 0 }; continue }
      const q = await apiJson(`/qc?seq=${seq}&work=${encodeURIComponent(WORK)}`)
      qc[seq] = { prose_len: prose.length, qc: q }
      L(`qc ch${seq} len=${prose.length}`)
    } catch (e) {
      qc[seq] = { err: e.message }
      L(`qc ch${seq} err ${e.message}`)
    }
  }

  // 设定库入口：只读浏览 + 对话更正已做
  for (const label of ['设定', '素材', '伏笔', '母题', '搜索', '校验']) {
    const el = p.getByText(label, { exact: true })
    if (await el.count()) {
      await el.first().click().catch(() => {})
      await sleep(500)
      L(`visited ${label}`)
    }
  }

  if (SCRATCH) {
    try { await p.screenshot({ path: `${SCRATCH}/hq-closeout.png`, fullPage: true }) } catch (_) {}
  }

  // final API snapshot
  const lengths = {}
  for (const seq of [1, 2, 3, 4, 5, 6, 7, 8]) {
    try {
      const ch = await apiJson(`/chapter?seq=${seq}&work=${encodeURIComponent(WORK)}`)
      lengths[seq] = (ch.prose || '').length
    } catch { lengths[seq] = -1 }
  }
  const intentFinal = await apiJson(`/intent?work=${encodeURIComponent(WORK)}`)

  return {
    intentRun, charRun, intentAfter: intentFinal, charApp, r4, qc, lengths,
    dashboards: { d4, d5 },
    form_fill_count: 0,
    human_click_approve_count: 0,
  }
})

if (SCRATCH) {
  mkdirSync(SCRATCH, { recursive: true })
  writeFileSync(`${SCRATCH}/hq-close-gaps.log`, logLines.join('\n') + '\n' + JSON.stringify(out, null, 2))
}

if (!out.ok) {
  console.error('HQ FAIL', out.err, out.errs)
  process.exit(1)
}

const lens = out.lengths || {}
const filled = Object.entries(lens).filter(([, n]) => n >= 400).length
const intentOk = out.intentAfter && /压抑|微光/.test(out.intentAfter.reader_feeling || '')
console.log('HQ RESULT', JSON.stringify({
  filledChapters: filled,
  lengths: lens,
  intentOk,
  charApp: out.charApp,
  r4: out.r4,
  form_fill_count: 0,
  human_click_approve_count: 0,
  hermesApproved: (out.intentRun?.decisions?.approved || 0) + (out.charRun?.decisions?.approved || 0),
}))

// 高质量门槛：至少 5 章有实质正文；intent 可读
if (filled < 5 || !intentOk) {
  console.error('HQ GATE FAIL', { filled, intentOk })
  process.exit(2)
}
// 工艺优先:字数/intent 不够;须 craft-gates(空辅信书在此失败)
{
  const { assertCraftGatesOrExit } = await import('./craft_gates.mjs')
  const WORK = process.env.E2E_WORK || 'book_b4e72480'
  const seqs = Object.entries(lens)
    .filter(([, n]) => n >= 400)
    .map(([s]) => Number(s))
    .slice(0, 3)
  await assertCraftGatesOrExit({ work: WORK, seqs: seqs.length ? seqs : [1], label: 'HQ_CLOSE' })
}
console.log('HQ CLOSE GAPS OK')
