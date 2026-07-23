// 高质量补齐：空章补写 + 扩写至 works.word_count ≥ TARGET（默认 50000）
// 每章前重新 openBook，避免 UI 漂移；零业务表单；Playwright 接受提案
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
const TARGET = Number(process.env.E2E_WORD_TARGET || 50000)
const MAX_NEW_CHS = Number(process.env.E2E_MAX_NEW_CHS || 25)
const ART = process.env.E2E_ART || new URL('../../../artifacts/e2e-20260722-book_b4e72480', import.meta.url).pathname
const logLines = []
const L = (m) => { const s = `[${new Date().toISOString()}] ${m}`; console.log(s); logLines.push(s) }

async function apiJson(path) {
  const r = await fetch(`${API}${path}`)
  if (!r.ok) throw new Error(`${path} ${r.status}`)
  return r.json()
}

async function chapterLen(seq) {
  try {
    const d = await apiJson(`/chapter?work=${encodeURIComponent(WORK)}&seq=${seq}`)
    return (d.prose || d.body || d.content || '').length
  } catch {
    return -1
  }
}

async function workStats() {
  const works = await apiJson('/works')
  const list = Array.isArray(works) ? works : (works.works || [])
  return list.find((w) => w.slug === WORK) || null
}

async function selectChapter(p, seq) {
  const re = new RegExp(`${seq}\\s*第\\s*${seq}\\s*章|第\\s*${seq}\\s*章`)
  // 确保左侧手稿列表可见
  for (const name of ['手稿', '卷章']) {
    const b = p.getByText(name, { exact: true })
    if (await b.count()) await b.first().click().catch(() => {})
    await sleep(400)
  }
  const btn = p.locator('button').filter({ hasText: re })
  if (await btn.count()) {
    await btn.first().click({ force: true })
    await sleep(1500)
    return true
  }
  const byText = p.getByText(re)
  if (await byText.count()) {
    await byText.first().click({ force: true })
    await sleep(1500)
    return true
  }
  return false
}

async function createChapter(p) {
  for (const name of ['手稿', '卷章']) {
    const b = p.getByText(name, { exact: true })
    if (await b.count()) await b.first().click().catch(() => {})
  }
  await sleep(400)
  const candidates = [
    p.getByText('+ 章节', { exact: true }),
    p.locator('button', { hasText: '+章' }),
    p.getByRole('button', { name: /^\+章$/ }),
    p.locator('button[aria-label="新建未分卷章节"]'),
  ]
  for (const b of candidates) {
    if (await b.count() && await b.first().isVisible().catch(() => false)) {
      await b.first().click()
      await sleep(2200)
      return true
    }
  }
  return false
}

async function goProseTab(p) {
  const tab = p.getByRole('tab', { name: '正文' })
  if (await tab.count()) {
    await tab.first().click()
    await sleep(900)
    return true
  }
  // 文案回退
  const t = p.getByText('正文', { exact: true })
  if (await t.count()) {
    await t.first().click().catch(() => {})
    await sleep(900)
    return true
  }
  return false
}

async function ensureWriteComposer(p, { retries = 6 } = {}) {
  for (let i = 0; i < retries; i++) {
    await goProseTab(p)
    const write = p.locator(DECISION_SELECTORS.writeComposer)
    if (await write.count() && await write.first().isVisible().catch(() => false)) return true
    // 写作槽偶发晚于章选挂载：再点一次正文/等网络
    await sleep(900 + i * 400)
    // 有时章 studio 默认在大纲 tab
    const anyTab = p.getByRole('tab')
    if (await anyTab.count()) {
      // 尝试点最后一个「正文」类
      const prose = p.locator('[role="tab"]', { hasText: '正文' })
      if (await prose.count()) await prose.first().click().catch(() => {})
    }
  }
  // 最后兜底：任一「提思路」textarea
  const any = p.locator('textarea[placeholder*="提思路"]')
  return (await any.count()) > 0 && await any.first().isVisible().catch(() => false)
}

async function writeOne(p, seq, brief, { minLen = 2200, attempt = 1 } = {}) {
  L(`writeOne ch${seq} attempt=${attempt}`)
  // 每章前重新打开书，避免 UI 卡死
  await openBook(p, BOOK)
  await sleep(1200)

  let sel = await selectChapter(p, seq)
  if (!sel) {
    const created = await createChapter(p)
    L(`create for ${seq}: ${created}`)
    // 新建后通常落到新章；再试选目标 seq，失败则选列表最后一章
    sel = await selectChapter(p, seq)
    if (!sel) {
      // 点最后一个「第N章」按钮
      const all = p.locator('button').filter({ hasText: /第\s*\d+\s*章/ })
      const n = await all.count()
      if (n) {
        await all.nth(n - 1).click({ force: true })
        await sleep(1500)
        sel = true
      }
    }
  }
  L(`select ch${seq} ok=${sel}`)
  if (!sel) throw new Error(`cannot select ch${seq}`)

  let hasComposer = await ensureWriteComposer(p)
  if (!hasComposer) {
    // 再选一次章后重试
    await selectChapter(p, seq)
    hasComposer = await ensureWriteComposer(p, { retries: 8 })
  }
  L(`composer ready=${hasComposer}`)
  if (!hasComposer) throw new Error(`no write composer for ch${seq}`)

  const prompt = [
    `请直接写第${seq}章完整正文草稿（${brief}）。`,
    `务必用提案卡交付，目标约${minLen}字以上中文正文。`,
    '限知沈砚；动作感官；不解释超自然机制；不洗白加害；承接前章。',
  ].join('')

  await chiefSay(p, prompt, { maxMs: 480000, preferWrite: true })
  await approveAllPending(p)
  try {
    const acc = await acceptDraftProposal(p, { timeoutMs: 300000 })
    await sleep(1800)
    const len = await chapterLen(seq)
    L(`ch${seq} accept=${JSON.stringify(acc)} prose_len=${len}`)
    if (len < 400 && attempt < 2) {
      return writeOne(p, seq, brief + '；上一稿未落库请重写完整成稿', { minLen, attempt: attempt + 1 })
    }
    return { acc, len }
  } catch (e) {
    await p.screenshot({ path: `${ART}/evidence/fail-ch${seq}-a${attempt}.png` }).catch(() => {})
    L(`accept fail ch${seq}: ${e.message}`)
    if (attempt < 2) {
      return writeOne(p, seq, brief + '；请重新用提案卡输出完整正文', { minLen, attempt: attempt + 1 })
    }
    throw e
  }
}

const briefs = {
  10: '灰契人名半露,雪巷对质,感官压抑',
  12: '季棠侧写与沈砚错位信任',
  14: '焦契账本边角露出真名笔画',
  default: '连续推进主线,环境压迫与人物抉择,场景完整',
}

const out = await withPage(async (p) => {
  mkdirSync(`${ART}/evidence`, { recursive: true })
  L(`BASE=${BASE} WORK=${WORK} TARGET=${TARGET}`)
  let stats = await workStats()
  L(`start stats ${JSON.stringify(stats)}`)

  // 优先空/薄章
  const plan = []
  for (let s = 1; s <= Math.max(15, stats?.chapter_count || 15); s++) {
    const n = await chapterLen(s)
    if (n < 400) plan.push({ seq: s, kind: 'fill', brief: briefs[s] || briefs.default, minLen: 2400 })
    else if (n < 2200) plan.push({ seq: s, kind: 'expand', brief: `扩写第${s}章成长稿完整场景`, minLen: 2500 })
  }
  L(`plan ${JSON.stringify(plan.map((x) => x.seq))}`)

  for (const item of plan) {
    stats = await workStats()
    if ((stats?.word_count || 0) >= TARGET) break
    try {
      await writeOne(p, item.seq, item.brief, { minLen: item.minLen })
    } catch (e) {
      L(`plan fail ch${item.seq}: ${e.message}`)
    }
    stats = await workStats()
    L(`after ch${item.seq} word_count=${stats?.word_count}`)
  }

  // 新建章直到达标
  let created = 0
  while ((stats?.word_count || 0) < TARGET && created < MAX_NEW_CHS) {
    created++
    await openBook(p, BOOK)
    await sleep(1000)
    const beforeCount = stats?.chapter_count || 15
    const okCreate = await createChapter(p)
    L(`new chapter create#${created} ok=${okCreate} beforeCount=${beforeCount}`)
    // 探测新 seq
    let targetSeq = beforeCount + 1
    for (let s = 1; s <= beforeCount + 8; s++) {
      const n = await chapterLen(s)
      if (n === 0) { targetSeq = s; break }
    }
    try {
      await writeOne(p, targetSeq, `卷中第${targetSeq}章连续推进长稿`, { minLen: 2400 })
    } catch (e) {
      L(`new write fail #${created} seq=${targetSeq}: ${e.message}`)
    }
    stats = await workStats()
    L(`loop#${created} word_count=${stats?.word_count} chapters=${stats?.chapter_count}`)
  }

  const lengths = {}
  const maxCh = stats?.chapter_count || 15
  for (let s = 1; s <= maxCh; s++) lengths[s] = await chapterLen(s)

  const result = {
    word_count: stats?.word_count || 0,
    chapter_count: stats?.chapter_count || 0,
    lengths,
    target: TARGET,
    hit: (stats?.word_count || 0) >= TARGET,
    form_fill_count: 0,
  }
  L(`RESULT ${JSON.stringify(result)}`)
  return result
})

try {
  mkdirSync(`${ART}/evidence`, { recursive: true })
  writeFileSync(`${ART}/evidence/hq-wordcount-push.log`, logLines.join('\n') + '\n')
  writeFileSync(`${ART}/evidence/hq-wordcount-result.json`, JSON.stringify(out, null, 2))
} catch (e) {
  console.error('write art fail', e.message)
}
if (SCRATCH) {
  try { writeFileSync(`${SCRATCH}/hq-wordcount-push.log`, logLines.join('\n') + '\n') } catch { /* */ }
}
console.log('HQ_WORDCOUNT', JSON.stringify(out))
// 工艺优先:字数达标不够;须 GATE-A 全绿且至少 1 章 B+C(旧空脚手架书应在此失败)
try {
  const { fetchCraftGates, assertCraftGatesOrExit } = await import('./craft_gates.mjs')
  const a = await fetchCraftGates({ work: WORK })
  out.craft_gate_a = a.body?.gate_a?.ok
  if (!a.body?.gate_a?.ok) {
    console.error('HQ_WORDCOUNT CRAFT_GATE_A FAIL — 禁止用字数掩盖空辅信', a.body?.gate_a?.blocking)
    process.exit(10)
  }
  // 抽查有实质正文的章
  const seqs = []
  for (const [s, n] of Object.entries(out.lengths || {})) {
    if (n >= 400) seqs.push(Number(s))
    if (seqs.length >= 3) break
  }
  if (seqs.length) {
    await assertCraftGatesOrExit({ work: WORK, seqs, requireA: false, label: 'HQ_WORDCOUNT' })
  }
  out.craft_gates = 'checked'
} catch (e) {
  if (e && typeof e.message === 'string' && e.message.includes('exit')) throw e
  console.error('HQ_WORDCOUNT craft gate error', e?.message || e)
  process.exit(11)
}
if (!out?.hit) process.exit(1)
