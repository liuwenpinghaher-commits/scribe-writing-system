// 高质量补齐：空章补写 + 扩写至 works.word_count ≥ TARGET（默认 50000）
// 每章前重新 openBook，避免 UI 漂移；零业务表单；Playwright 接受提案
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { withPage, BASE, openBook } from './lib.mjs'
import {
  chiefSay, acceptDraftProposal, adoptDraftAsFinal, approveAllPending, DECISION_SELECTORS,
} from './author_decisions.mjs'
import { collectLongformAcceptanceInput } from './longform_acceptance_audit.mjs'
import { buildLongformAcceptanceReport } from './longform_acceptance_result.mjs'
import { buildLongformDraftPrompt } from './longform_prompt.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SCRATCH = process.env.GOAL_SCRATCH || process.env.SCRATCH || ''
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const WORK = process.env.E2E_WORK || 'book_b4e72480'
const BOOK = process.env.E2E_BOOK_TITLE || '融合验收·mruwfo36'
const TARGET = Number(process.env.E2E_WORD_TARGET || 50000)
const MAX_NEW_CHS = Number(process.env.E2E_MAX_NEW_CHS || 25)
const ART = process.env.E2E_ART || new URL('../../../artifacts/e2e-20260722-book_b4e72480', import.meta.url).pathname
const RESULT_FILE = process.env.E2E_RESULT_FILE || ''
const logLines = []
const runIds = new Set()
let latestProgress = { stage: 'init' }

function persistResult(payload) {
  if (!RESULT_FILE) return
  try {
    mkdirSync(dirname(RESULT_FILE), { recursive: true })
    writeFileSync(RESULT_FILE, JSON.stringify({
      work: WORK,
      target: TARGET,
      run_ids: [...runIds],
      updated_at: new Date().toISOString(),
      ...payload,
    }, null, 2))
  } catch { /* 诊断工件不能中断真实作者路径 */ }
}

function checkpoint(stage, detail = {}) {
  latestProgress = { stage, ...detail }
  persistResult({ ok: false, in_progress: true, progress: latestProgress })
}

function recordRun(result) {
  if (typeof result?.run?.id === 'string' && result.run.id) runIds.add(result.run.id)
  return result
}

const L = (m) => {
  const s = `[${new Date().toISOString()}] ${m}`
  console.log(s)
  logLines.push(s)
  checkpoint('running', { message: m })
}

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
  // 手稿目录的稳定可访问名称是「序号 + 标题」（例如 `1 质量验收起章`），
  // 而不是旧脚本假设的「第1章」。保留后者作兼容回退。
  const re = new RegExp(`^${seq}\\s+|第\\s*${seq}\\s*章`)
  // 已激活的入口重复点击会重置选择并瞬间卸载目录；只在未激活时切换。
  const manuscript = p.getByRole('button', { name: '手稿', exact: true }).first()
  if (await manuscript.count() && await manuscript.getAttribute('aria-pressed') !== 'true') {
    await manuscript.click()
  }
  await p.getByTestId('manuscript-directory').waitFor({ state: 'visible', timeout: 20000 })
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
  const manuscript = p.getByRole('button', { name: '手稿', exact: true }).first()
  if (await manuscript.count() && await manuscript.getAttribute('aria-pressed') !== 'true') {
    await manuscript.click()
  }
  await p.getByTestId('manuscript-directory').waitFor({ state: 'visible', timeout: 20000 })
  const candidates = [
    p.getByText('+ 章节', { exact: true }),
    p.locator('button', { hasText: '+章' }),
    p.getByRole('button', { name: /^\+章$/ }),
    p.locator('button[aria-label="新建未分卷章节"]'),
  ]
  for (const b of candidates) {
    if (await b.count() && await b.first().isVisible().catch(() => false)) {
      await b.first().click()
      // 「+ 章节」是主编种子：点击只创建待审 Run，必须由作者在同一 UI 中批准，
      // 之后才允许把它作为已存在的章节继续写作。
      await approveAllPending(p)
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
  await openBook(p, BOOK, { work: WORK })
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

  const prompt = buildLongformDraftPrompt({ seq, brief, minLen })

  recordRun(await chiefSay(p, prompt, { maxMs: 480000, preferWrite: true }))
  await approveAllPending(p)
  try {
    const acc = await acceptDraftProposal(p, { timeoutMs: 300000 })
    let adoption = null
    if (acc.kind === 'stage') {
      const saveResponse = p.waitForResponse((response) => {
        const path = new URL(response.url()).pathname.replace(/^\/api/, '')
        return response.request().method() === 'POST' && path === '/save-chapter'
      }, { timeout: 120000 })
      adoption = await adoptDraftAsFinal(p, { timeoutMs: 120000 })
      const saved = await saveResponse
      if (saved.status() !== 200) {
        throw new Error(`草稿采用为正文保存失败: HTTP ${saved.status()}`)
      }
    }
    await sleep(1800)
    const len = await chapterLen(seq)
    L(`ch${seq} accept=${JSON.stringify(acc)} adoption=${JSON.stringify(adoption)} prose_len=${len}`)
    if (len < 400 && attempt < 2) {
      return writeOne(p, seq, brief + '；上一稿未落库请重写完整成稿', { minLen, attempt: attempt + 1 })
    }
    return { acc, adoption, len }
  } catch (e) {
    await p.screenshot({ path: `${ART}/evidence/fail-ch${seq}-a${attempt}.png` }).catch(() => {})
    L(`accept fail ch${seq}: ${e.message}`)
    if (attempt < 2) {
      return writeOne(p, seq, brief + '；请重新用提案卡输出完整正文', { minLen, attempt: attempt + 1 })
    }
    throw e
  }
}

const briefForCurrentBook = (seq) => `以当前书第${seq}章已批准的章计划为准，推进尚未解决的冲突并完成一个有后果的场景`

const out = await withPage(async (p) => {
  mkdirSync(`${ART}/evidence`, { recursive: true })
  L(`BASE=${BASE} WORK=${WORK} TARGET=${TARGET}`)
  let stats = await workStats()
  L(`start stats ${JSON.stringify(stats)}`)

  // 优先空/薄章
  const plan = []
  for (let s = 1; s <= Math.max(15, stats?.chapter_count || 15); s++) {
    const n = await chapterLen(s)
    if (n < 400) plan.push({ seq: s, kind: 'fill', brief: briefForCurrentBook(s), minLen: 2400 })
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
    await openBook(p, BOOK, { work: WORK })
    await sleep(1000)
    const beforeCount = stats?.chapter_count || 15
    const okCreate = await createChapter(p)
    L(`new chapter create#${created} ok=${okCreate} beforeCount=${beforeCount}`)
    stats = await workStats()
    if (!okCreate || (stats?.chapter_count || 0) <= beforeCount) {
      throw new Error(`新章经作者审批后未回读到新增章节: before=${beforeCount} after=${stats?.chapter_count || 0}`)
    }
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
    persistResult({ ok: false, in_progress: false, error: 'Gate A 未通过', result: out })
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
  persistResult({ ok: false, in_progress: false, error: `craft gate error: ${e?.message || e}`, result: out })
  process.exit(11)
}
if (!out?.hit) {
  persistResult({ ok: false, in_progress: false, error: '未达到字数目标', result: out })
  process.exit(1)
}

// 字数达标以后只读回查完整的二十章矩阵。当前控制器尚未在同一本书内实际执行
// 合同全字段/四项可靠性旅程，因此显式传入 false，严禁把“未运行”伪造成通过。
// 后续真实控制器必须以可复查的 UI artifact 覆盖这些字段后才能改为 true。
let longform_report
try {
  const longform_input = await collectLongformAcceptanceInput({
    work: WORK,
    read: apiJson,
    target: TARGET,
    quality_contract: {
      approved: false,
      all_fields_filled: false,
      author_weight_dominant: false,
    },
    reliability: {
      refresh_restart: false,
      stop_partial_recovery: false,
      sse_replay: false,
      concurrent_conflict: false,
    },
  })
  longform_report = buildLongformAcceptanceReport(longform_input)
  out.longform_report = longform_report
  writeFileSync(`${ART}/evidence/longform-acceptance-report.json`, JSON.stringify(longform_report, null, 2))
} catch (error) {
  persistResult({
    ok: false,
    in_progress: false,
    error: `长程只读审计失败: ${error instanceof Error ? error.message : String(error)}`,
    result: out,
  })
  process.exit(12)
}
if (!longform_report.ok) {
  persistResult({
    ok: false,
    in_progress: false,
    error: '字数已达标但完整真人验收未闭合',
    result: out,
    longform_report,
  })
  process.exit(12)
}
persistResult({ ok: true, in_progress: false, result: out, longform_report, progress: latestProgress })
