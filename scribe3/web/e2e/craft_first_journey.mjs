// 工艺优先主旅程(契约 v3)
// 顺序:建书 → 对话补齐辅信(intent/角色/伏笔/母题) → 章脚手架(大纲→节拍→演绎) → 正文 → craft-gates
// PASS = GATE-A ∧ 每章 B+C(+D 软);字数不是主门控。
//
// 前置:后端 :3321(SCRIBE3_CRAFT_GATE=1 推荐) + 前端 :3311 + Hermes
// 跑法:
//   cd scribe3/web && E2E_BOOK_TITLE='工艺优先·smoke' node e2e/craft_first_journey.mjs
//
import { writeFileSync, mkdirSync } from 'node:fs'
import { withPage, openBook } from './lib.mjs'
import {
  chiefSay, acceptDraftProposal, acceptStageFill, approveAllPending,
} from './author_decisions.mjs'
import { assertCraftGatesOrExit, fetchCraftGates } from './craft_gates.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SCRATCH = process.env.GOAL_SCRATCH || process.env.SCRATCH || ''
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || `工艺优先·${Date.now().toString(36)}`
const logLines = []
const L = (m) => { const s = `[${new Date().toISOString()}] ${m}`; console.log(s); logLines.push(s) }

async function apiJson(path) {
  const r = await fetch(`${API}${path}`)
  if (!r.ok) throw new Error(`${path} ${r.status}`)
  return r.json()
}

async function clickTab(p, name) {
  const tab = p.getByRole('tab', { name })
  if (await tab.count()) {
    await tab.first().click()
    await sleep(800)
    return true
  }
  return false
}

async function selectChapter(p, seq) {
  const re = new RegExp(`第\\s*${seq}\\s*章`)
  const item = p.getByRole('treeitem').filter({ hasText: re })
  if (await item.count()) {
    await item.first().click()
    await sleep(1200)
    return true
  }
  return false
}

async function createChapter(p) {
  for (const b of [
    p.getByRole('button', { name: /新建未分卷章节/ }),
    p.locator('button[aria-label="新建未分卷章节"]'),
    p.locator('button', { hasText: '+章' }),
  ]) {
    if (await b.count() && await b.first().isVisible().catch(() => false)) {
      await b.first().click()
      await sleep(1800)
      return true
    }
  }
  return false
}

const out = await withPage(async (p) => {
  // 建书
  await p.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'networkidle' })
  await sleep(800)
  const create = p.getByRole('button', { name: /新建|新书|创建作品/ }).first()
  if (await create.count()) {
    await create.click()
    await sleep(500)
    const inp = p.locator('input').first()
    if (await inp.isVisible().catch(() => false)) {
      await inp.fill(BOOK)
      await inp.press('Enter')
      await sleep(2000)
    }
  }
  await openBook(p, BOOK)
  L(`opened ${BOOK}`)

  // 解析 work slug
  let work = process.env.E2E_WORK || ''
  if (!work) {
    const works = await apiJson('/works')
    const list = Array.isArray(works) ? works : (works.works || [])
    const hit = list.find((w) => (w.title || '').includes(BOOK.slice(0, 8)) || w.title === BOOK)
    work = hit?.slug || list[list.length - 1]?.slug || ''
  }
  L(`work=${work}`)
  if (!work) throw new Error('无法解析 work slug')
  process.env.E2E_WORK = work

  // Phase A: 辅信(对话+审批)
  L('phase-A intent')
  await chiefSay(p, '请把本书北极星写入:读者感受「压抑中见一线热」,情感弧「隐瞒到对质」,红线「不美化私刑」。走审批落库。', { preferWrite: true, maxMs: 240000 })
  await approveAllPending(p)

  L('phase-A characters')
  await chiefSay(p, '登记主角「沈砚」(外貌右手茧,欲望查清灰契)与「老道」(灰袍,守炉),并建立二人竞争者关系。审批写入设定库。', { preferWrite: true, maxMs: 240000 })
  await approveAllPending(p)

  L('phase-A motif+promise')
  await chiefSay(p, '登记母题「灰契」(回声词:灰印/契血),并埋伏笔「灰契会反噬立契人」setup 第1章。审批写入。', { preferWrite: true, maxMs: 240000 })
  await approveAllPending(p)

  let ga = await fetchCraftGates({ work })
  L(`GATE-A after dialog ok=${ga.body?.gate_a?.ok} blocking=${JSON.stringify(ga.body?.gate_a?.blocking)}`)
  // 若对话未落库,允许 API 补种仅用于机判通路验证(记 form 风险)
  if (!ga.body?.gate_a?.ok && process.env.E2E_ALLOW_API_SEED === '1') {
    L('API seed aux (E2E_ALLOW_API_SEED=1)')
    await fetch(`${API}/intent?work=${encodeURIComponent(work)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reader_feeling: '压抑中见一线热', emotional_arc: '隐瞒到对质', red_lines: '不美化私刑',
      }),
    })
  }
  ga = await fetchCraftGates({ work })
  if (!ga.body?.gate_a?.ok) {
    L('GATE-A still red — continue chapter stages; final assert will fail loudly')
  }

  // 建章
  await createChapter(p)
  await selectChapter(p, 1)

  // Phase B: 大纲→节拍→演绎
  for (const [phase, prompt] of [
    ['大纲', '请写第1章大纲 3-5 句:沈砚夜访棺材铺逼问灰契,老道只给半句。直接给可填入正文。'],
    ['节拍', '把第1章拆成至少3条节拍:推门/对质/缄口。可填入。'],
    ['演绎', '写第1章场景真相(含灰契真名机制)与沈砚、老道的限知投影。可填入。'],
  ]) {
    L(`stage ${phase}`)
    await clickTab(p, phase)
    await chiefSay(p, prompt, { maxMs: 300000, preferWrite: false })
    try {
      await acceptStageFill(p)
      L(`stage ${phase} filled`)
    } catch (e) {
      L(`stage ${phase} fill miss: ${e.message}`)
    }
    await approveAllPending(p)
  }

  // Phase C: 正文
  L('prose')
  await clickTab(p, '正文')
  // 质量硬要求：章级篇幅 + 对白 + 伏笔可追踪 + 限知；闸绿不算过
  const MIN_PROSE = Number(process.env.E2E_MIN_PROSE || 1500)
  await chiefSay(p,
    `按大纲、节拍、演绎与设定写第1章正文（净文至少${MIN_PROSE}字）。` +
    '限知沈砚视角：禁止出现「炉心真名」。' +
    '必须：①写出老道那「半句」的具体对白；②埋下「灰契反噬立契人」可回收钩子；' +
    '③点出二人竞争/信息权张力；④灰印与契血意象服务「契约代价」主题；⑤压抑里有一点不肯退的热。' +
    '不要提纲体，要可连载场景。',
    { maxMs: 420000, preferWrite: true },
  )
  let accept = null
  try {
    accept = await acceptDraftProposal(p)
    L(`accept ${JSON.stringify(accept)}`)
  } catch (e) {
    L(`accept fail ${e.message}`)
  }
  await approveAllPending(p)

  const ch = await apiJson(`/chapter?seq=1&work=${encodeURIComponent(work)}`)
  const prose = String(ch.prose || '')
  const proseLen = prose.replace(/\s/g, '').length
  L(`proseLen_net=${proseLen}`)

  return { work, book: BOOK, proseLen, prose, accept, gate_a: ga.body?.gate_a }
})

if (SCRATCH) {
  try {
    mkdirSync(SCRATCH, { recursive: true })
    writeFileSync(`${SCRATCH}/craft-first.log`, logLines.join('\n') + '\n' + JSON.stringify(out, null, 2))
  } catch { /* */ }
}

if (!out.ok) {
  console.error('CRAFT_FIRST FAIL', out.err, out.errs)
  process.exit(1)
}

const MIN_PROSE = Number(process.env.E2E_MIN_PROSE || 1500)
const work = out.work || process.env.E2E_WORK

// 1) 工艺卫生闸（必要但不充分）
await assertCraftGatesOrExit({
  work,
  seqs: out.proseLen >= 80 ? [1] : [],
  requireA: true,
  label: 'CRAFT_FIRST_GATES',
})

// 2) 篇幅硬门：短稿直接失败（禁止闸绿冒充完成）
if (!out.proseLen || out.proseLen < MIN_PROSE) {
  console.error('CRAFT_FIRST QUALITY FAIL: prose too short for chapter', {
    proseLen: out.proseLen, min: MIN_PROSE,
    note: '闸绿 ≠ 质量通过',
  })
  process.exit(2)
}

// 3) 内容质量轨（Python 同源）
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
const root = join(dirname(fileURLToPath(import.meta.url)), '../../..')
const py = join(root, 'scribe3/.venv/bin/python')
const q = spawnSync(py, ['-c', `
from scribe3.store import SurrealStore
from scribe3.verify_content_quality import review_chapter_quality
import json, sys
st = SurrealStore(ns="scribe3", db=sys.argv[1])
r = review_chapter_quality(st, int(sys.argv[2]))
print(json.dumps(r.to_dict(), ensure_ascii=False))
st.close()
sys.exit(0 if r.ok else 3)
`, work, '1'], { encoding: 'utf-8', cwd: root })
console.log('QUALITY_REPORT', q.stdout || q.stderr)
if (q.status !== 0) {
  console.error('CRAFT_FIRST QUALITY FAIL: content review not ok (闸绿不能代替质量)', {
    status: q.status, note: 'see verify_content_quality',
  })
  process.exit(q.status || 3)
}

console.log('CRAFT_FIRST OK', JSON.stringify({
  work: out.work,
  book: out.book,
  proseLen: out.proseLen,
  craft_gates: 'checked',
  content_quality: 'checked',
  note: 'gates+quality 双轨均过才算完成',
}))
