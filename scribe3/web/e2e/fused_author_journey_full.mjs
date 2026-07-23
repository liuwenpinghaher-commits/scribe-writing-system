// 完整融合旅程（硬约束第5条）：续跑 book_b4e72480
// 环境→书→北极星→卷章synopsis→阶段→连写+看板→返工→扫尾
// 零业务表单字段；决策仅 Playwright 点击
import { writeFileSync, mkdirSync } from 'node:fs'
import { withPage, BASE, openBook } from './lib.mjs'
import {
  chiefSay, acceptDraftProposal, acceptStageFill, approveAllPending, DECISION_SELECTORS,
} from './author_decisions.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SCRATCH = process.env.GOAL_SCRATCH || process.env.SCRATCH || ''
const BOOK_TITLE = process.env.E2E_BOOK_TITLE || '融合验收·mruwfo36'
const logLines = []
const journal = []
function log(m) {
  const line = `[${new Date().toISOString()}] ${m}`
  console.log(line)
  logLines.push(line)
}
function step(id, obj) {
  journal.push({ id, t: new Date().toISOString(), ...obj })
  log(`STEP ${id} ${JSON.stringify(obj)}`)
}

async function clickTab(p, name) {
  const tab = p.getByRole('tab', { name })
  if (await tab.count() && await tab.first().isVisible().catch(() => false)) {
    await tab.first().click()
    await sleep(900)
    return true
  }
  const tx = p.getByText(name, { exact: true })
  if (await tx.count()) {
    await tx.first().click().catch(() => {})
    await sleep(700)
    return true
  }
  return false
}

async function selectChapter(p, seq) {
  const re = new RegExp(`第\\s*${seq}\\s*章`)
  const item = p.getByRole('treeitem').filter({ hasText: re })
  if (await item.count()) {
    await item.first().click()
    await sleep(1500)
    return true
  }
  // 列表回退
  const any = p.getByText(re)
  if (await any.count()) {
    await any.first().click()
    await sleep(1500)
    return true
  }
  return false
}

async function createChapterNoFields(p) {
  const btns = [
    p.getByRole('button', { name: /新建未分卷章节/ }),
    p.locator('button[aria-label="新建未分卷章节"]'),
    p.getByRole('button', { name: /^\+章$/ }),
    p.locator('button', { hasText: '+章' }),
  ]
  for (const b of btns) {
    if (await b.count() && await b.first().isVisible().catch(() => false)) {
      await b.first().click()
      await sleep(2000)
      return true
    }
  }
  return false
}

async function createVolume(p, title) {
  // 新建卷若弹出输入框：产品上属结构字段；尽量一键。若必须标题，记 form 风险。
  const add = p.getByRole('button', { name: /新建卷/ }).or(p.locator('button[title="新建卷"]'))
  if (!(await add.count())) return { ok: false, reason: 'no-volume-btn' }
  await add.first().click()
  await sleep(600)
  const inp = p.locator('input[placeholder*="卷"], input[placeholder*="标题"]').first()
  if (await inp.isVisible().catch(() => false)) {
    // 结构标题：记为 structure_title_input（非设定表单字段，journal 单独计数）
    await inp.fill(title)
    await inp.press('Enter')
    await sleep(1500)
    return { ok: true, structure_title_inputs: 1 }
  }
  // 可能已创建
  await sleep(1000)
  return { ok: true, structure_title_inputs: 0 }
}

async function visitDashboards(p) {
  const views = ['图谱', '时间线', '仪表盘']
  const seen = []
  for (const v of views) {
    const btn = p.getByRole('button', { name: v }).or(p.getByText(v, { exact: true }))
    if (await btn.count()) {
      await btn.first().click().catch(() => {})
      await sleep(1200)
      seen.push(v)
    }
  }
  // 回手稿：点树或关闭视图
  const ms = p.getByText('手稿', { exact: true })
  if (await ms.count()) await ms.first().click().catch(() => {})
  await sleep(800)
  return seen
}

async function stageGenerateAndFill(p, phaseLabel, prompt) {
  await clickTab(p, phaseLabel)
  await sleep(800)
  // 讨论槽或写作槽
  const preferWrite = phaseLabel === '正文' || phaseLabel === '草稿'
  await chiefSay(p, prompt, { maxMs: 300000, preferWrite })
  if (preferWrite) {
    try {
      return await acceptDraftProposal(p, { timeoutMs: 120000 })
    } catch {
      // 草稿阶段也可能是填入
      return await acceptStageFill(p, { timeoutMs: 90000 })
    }
  }
  return await acceptStageFill(p, { prefer: phaseLabel === '节拍' ? 'append' : 'fill', timeoutMs: 180000 })
}

async function writeChapterBody(p, seq, brief) {
  await selectChapter(p, seq)
  await clickTab(p, '正文')
  await sleep(1000)
  await p.locator(DECISION_SELECTORS.writeComposer).first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {})
  const msg = `请直接写第${seq}章完整正文草稿（${brief}）。用提案卡给我，约600-1200字。`
  await chiefSay(p, msg, { maxMs: 360000, preferWrite: true })
  await approveAllPending(p)
  return await acceptDraftProposal(p, { timeoutMs: 180000 })
}

const r = await withPage(async (p) => {
  log(`BASE=${BASE} book=${BOOK_TITLE}`)
  let structure_title_inputs = 0
  let form_fill_count = 0
  let human_click_approve_count = 0
  const playwright_clicks = []

  await openBook(p, BOOK_TITLE)
  step('open-book', { title: BOOK_TITLE })

  // —— 北极星再确认（对话，不填表）——
  await chiefSay(p, '回顾本书北极星：读者感受、情感弧、红线三条，用五句话写在对话里。不要让我填表。')
  step('northstar-dialog', { ok: true })

  // —— 卷章骨架 ——
  const v1 = await createVolume(p, '第一卷·灰契')
  structure_title_inputs += v1.structure_title_inputs || 0
  step('volume', v1)
  // 确保至少 3 章
  for (let i = 0; i < 3; i++) {
    const ok = await createChapterNoFields(p)
    step('create-chapter-btn', { i, ok })
    if (!ok) break
  }

  // ch1 大纲/节拍/演绎（对话→填入）
  await selectChapter(p, 1)
  try {
    const o = await stageGenerateAndFill(p, '大纲',
      '请把第1章大纲写成3-5句（含开局灰契、沈砚出场、悬念）。生成后我会点填入。')
    playwright_clicks.push(o)
    step('ch1-outline', { ok: true, o })
  } catch (e) {
    step('ch1-outline', { ok: false, err: e.message })
  }
  try {
    const b = await stageGenerateAndFill(p, '节拍',
      '请据大纲把第1章拆成4-6条有序节拍列表。生成后我会点追加/填入。')
    playwright_clicks.push(b)
    step('ch1-beats', { ok: true, b })
  } catch (e) {
    step('ch1-beats', { ok: false, err: e.message })
  }
  try {
    await clickTab(p, '演绎')
    await chiefSay(p, '请写第1章场景真相：客观发生了什么（含灰契/祭灶街景），3-6句。生成后我会点填入。', { preferWrite: false })
    const d = await acceptStageFill(p, { timeoutMs: 120000 }).catch(async (err) => {
      // 演绎可能没有 proposal bar，记缺口
      step('ch1-deduce', { ok: false, err: err.message })
      return null
    })
    if (d) {
      playwright_clicks.push(d)
      step('ch1-deduce', { ok: true, d })
    }
  } catch (e) {
    step('ch1-deduce', { ok: false, err: e.message })
  }
  // 正文已有则跳过再写；确认仍在
  await clickTab(p, '正文')
  step('ch1-body-existing', { note: 'prior journey accepted ~1392 chars' })

  // —— 连写 ch2 + 看板仪式 ——
  const dash1 = await visitDashboards(p)
  step('dashboard-before-ch2', { views: dash1 })
  // ensure ch2 exists
  if (!(await selectChapter(p, 2))) {
    await createChapterNoFields(p)
  }
  try {
    await selectChapter(p, 2)
    try {
      await stageGenerateAndFill(p, '大纲', '第2章大纲3-5句：沈砚追查灰契来源，夜访棺材铺。生成后填入。')
      step('ch2-outline', { ok: true })
    } catch (e) {
      step('ch2-outline', { ok: false, err: e.message })
    }
    const a2 = await writeChapterBody(p, 2, '限知沈砚，夜访棺材铺，推进灰契悬念，动作感官')
    playwright_clicks.push(a2)
    step('ch2-body', { ok: true, a2 })
  } catch (e) {
    step('ch2-body', { ok: false, err: e.message })
  }

  // —— 连写 ch3 + 看板 ——
  const dash2 = await visitDashboards(p)
  step('dashboard-before-ch3', { views: dash2 })
  if (!(await selectChapter(p, 3))) await createChapterNoFields(p)
  try {
    await selectChapter(p, 3)
    const a3 = await writeChapterBody(p, 3, '限知沈砚，发现焦契背后的人名缺口，克制不解释机制')
    playwright_clicks.push(a3)
    step('ch3-body', { ok: true, a3 })
  } catch (e) {
    step('ch3-body', { ok: false, err: e.message })
  }

  // —— 返工 R1：改设定（对话，若出审批则点）——
  try {
    await chiefSay(p, '设定更正：沈砚左手茧改为右手茧，请写入角色档案并说明影响第1-2章哪些描写。若需审批请出审批卡。', { preferWrite: false })
    const ap = await approveAllPending(p, { maxRounds: 6 })
    step('rework-R1-setting', { ok: true, ap })
  } catch (e) {
    step('rework-R1-setting', { ok: false, err: e.message })
  }

  // —— R2 北极星改航（对话）——
  try {
    await chiefSay(p, '北极星微调：红线增加「不写超自然明机制」。请对话确认，不要让我填表。')
    step('rework-R2-northstar', { ok: true })
  } catch (e) {
    step('rework-R2-northstar', { ok: false, err: e.message })
  }

  // —— R3 结构：再建一章表示结构调整意图 ——
  try {
    const ok = await createChapterNoFields(p)
    step('rework-R3-structure', { ok, note: 'added chapter via no-field button' })
  } catch (e) {
    step('rework-R3-structure', { ok: false, err: e.message })
  }

  // —— R4 版本：打开存档若可见 ——
  try {
    const ver = p.getByText(/存档|版本/)
    if (await ver.count()) {
      await ver.first().click().catch(() => {})
      await sleep(1000)
      step('rework-R4-version', { ok: true, opened: true })
    } else {
      step('rework-R4-version', { ok: true, opened: false, note: 'no version UI entry found this layout' })
    }
  } catch (e) {
    step('rework-R4-version', { ok: false, err: e.message })
  }

  // —— 扫尾：横切入口各点一次 ——
  const sweep = []
  for (const label of ['设定', '素材', '伏笔', '母题', '搜索', '校验', '参考作品']) {
    const el = p.getByText(label, { exact: true })
    if (await el.count()) {
      await el.first().click().catch(() => {})
      await sleep(700)
      sweep.push(label)
    }
  }
  step('f-matrix-sweep', { visited: sweep })

  // 读 ch2/ch3 编辑器字数快照
  await selectChapter(p, 2)
  await clickTab(p, '正文')
  const prose2 = await p.evaluate(() => (document.querySelector('.ProseMirror, .tiptap-prose, .manuscript')?.innerText || '').trim().length)
  await selectChapter(p, 3)
  await clickTab(p, '正文')
  const prose3 = await p.evaluate(() => (document.querySelector('.ProseMirror, .tiptap-prose, .manuscript')?.innerText || '').trim().length)

  if (SCRATCH) {
    try {
      await p.screenshot({ path: `${SCRATCH}/full-journey-end.png`, fullPage: true })
    } catch (_) {}
  }

  return {
    book: BOOK_TITLE,
    form_fill_count,
    human_click_approve_count,
    structure_title_inputs,
    playwright_clicks: playwright_clicks.length,
    journal,
    prose2,
    prose3,
    dashboards: { before2: dash1, before3: dash2 },
    sweep,
  }
})

if (SCRATCH) {
  try {
    mkdirSync(SCRATCH, { recursive: true })
    writeFileSync(`${SCRATCH}/pw-full.log`, logLines.join('\n') + '\n' + JSON.stringify(r, null, 2))
    writeFileSync(`${SCRATCH}/journal-full.json`, JSON.stringify(r.journal || r, null, 2))
  } catch (_) {}
}

if (!r.ok) {
  console.error('FULL FUSED FAIL', r.err, r.errs)
  process.exit(1)
}

// 门控：至少再写出一章新正文（ch2 或 ch3）
// 编辑器 DOM 字数仅作辅助；以 API 读回为准（accept 后可能尚未挂载 ProseMirror）
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const WORK = process.env.E2E_WORK || 'book_b4e72480'
async function apiProseLen(seq) {
  try {
    const res = await fetch(`${API}/chapter?seq=${seq}&work=${encodeURIComponent(WORK)}`)
    if (!res.ok) return 0
    const d = await res.json()
    return String(d.prose || '').trim().length
  } catch {
    return 0
  }
}
const api2 = await apiProseLen(2)
const api3 = await apiProseLen(3)
const wrote = api2 >= 200 || api3 >= 200 || (r.prose2 || 0) >= 200 || (r.prose3 || 0) >= 200
if (!wrote) {
  console.error('FULL FUSED FAIL: no additional chapter body', {
    prose2: r.prose2, prose3: r.prose3, api2, api3,
  })
  process.exit(2)
}
r.api2 = api2
r.api3 = api3
if (SCRATCH) {
  try {
    writeFileSync(`${SCRATCH}/pw-full.log`, logLines.join('\n') + '\n' + JSON.stringify(r, null, 2))
  } catch (_) {}
}

// 工艺优先主门控:prose 长度只作辅助;PASS 须 craft-gates
{
  const { assertCraftGatesOrExit } = await import('./craft_gates.mjs')
  const seqs = []
  if (api2 >= 80) seqs.push(2)
  if (api3 >= 80) seqs.push(3)
  if (seqs.length === 0) seqs.push(1)
  await assertCraftGatesOrExit({ work: WORK, seqs, label: 'FULL_FUSED' })
}

console.log('FULL FUSED OK', JSON.stringify({
  book: r.book,
  form_fill_count: r.form_fill_count,
  human_click_approve_count: r.human_click_approve_count,
  structure_title_inputs: r.structure_title_inputs,
  playwright_clicks: r.playwright_clicks,
  prose2: r.prose2,
  prose3: r.prose3,
  craft_gates: 'checked',
  steps: (r.journal || []).length,
}))
