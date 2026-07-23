// 工艺优先主旅程(契约 v3)
// 顺序:建书 → 对话补齐辅信(intent/角色/伏笔/母题) → 章脚手架(大纲→节拍→演绎) → 正文 → craft-gates
// PASS = GATE-A ∧ 每章 B+C(+D 软);字数不是主门控。
//
// 前置:后端 :3321(SCRIBE3_CRAFT_GATE=1 推荐) + 前端 :3311 + Hermes
// 跑法:
//   cd scribe3/web && E2E_BOOK_TITLE='工艺优先·smoke' node e2e/craft_first_journey.mjs
//
import { writeFileSync, mkdirSync } from 'node:fs'
import { withPage } from './lib.mjs'
import {
  chiefSay, acceptDraftProposal, acceptStageFill, approveAllPending,
} from './author_decisions.mjs'
import { assertCraftGatesOrExit, fetchCraftGates } from './craft_gates.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SCRATCH = process.env.GOAL_SCRATCH || process.env.SCRATCH || ''
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || `工艺优先·${Date.now().toString(36)}`
// ensureChiefVisible / chiefSay 退库恢复依赖此环境变量
process.env.E2E_BOOK_TITLE = BOOK
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
  // 手稿目录空态 / 目录 hover 等入口;点击仅 seed,调用方必须 approveAllPending
  for (const b of [
    p.getByRole('button', { name: /新建未分卷章节/ }),
    p.getByRole('button', { name: /新建第一章/ }),
    p.getByRole('button', { name: /^新建章$/ }),
    p.locator('button[aria-label="新建未分卷章节"]'),
    p.locator('button', { hasText: '新建第一章' }),
    p.locator('button', { hasText: '新建章' }),
    p.locator('button', { hasText: '+章' }),
  ]) {
    if (await b.count() && await b.first().isVisible().catch(() => false)) {
      await b.first().click()
      await sleep(1200)
      return true
    }
  }
  return false
}

const out = await withPage(async (p) => {
  // 建书:填书名 → 点「建」→ 等 POST /works → 等四栏(create 成功会 onSelect 进书)
  await p.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'networkidle' })
  await sleep(1000)
  const nameInput = p.locator('input[placeholder="书名…"], input[aria-label="书名"]')
  await nameInput.waitFor({ timeout: 15000 })
  await nameInput.fill(BOOK)
  const createBtn = p.getByRole('button', { name: '建', exact: true }).first()
  const waitCreate = p.waitForResponse(
    (r) => /\/works(\?|$)/.test(r.url()) && r.request().method() === 'POST' && r.status() < 500,
    { timeout: 30000 },
  ).catch(() => null)
  if (await createBtn.isVisible().catch(() => false)) await createBtn.click()
  else await nameInput.press('Enter')
  const created = await waitCreate
  L(`createWork response ${created ? created.status() : 'timeout'}`)
  // 进四栏;若 create 后仍停在库页则点书卡
  try {
    await p.waitForSelector('[data-testid="four-col"]', { timeout: 15000 })
  } catch {
    L('four-col not yet, try open book card')
    const card = p.getByRole('button', { name: new RegExp(BOOK.slice(0, 10).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).first()
    if (await card.count()) await card.click()
    else {
      await p.locator('button').filter({ hasText: BOOK.slice(0, 8) }).first().click({ timeout: 8000 }).catch(() => {})
    }
    await p.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  }
  L('four-col present')
  const { ensureChiefVisible, chiefSay: _probe } = await import('./author_decisions.mjs')
  // 新书进台后右坞可能折叠/晚挂载；先 probe 再 ensure（ensure 不得再点已激活主编轨）
  await sleep(800)
  let ready = false
  for (let i = 0; i < 8; i++) {
    const diag = await p.evaluate(() => ({
      right: document.querySelector('[data-testid="right-panel"]')?.getAttribute('data-collapsed'),
      shell: !!document.querySelector('[data-testid="chief-chat-shell"]'),
      write: !!document.querySelector('[data-testid="chief-write-chat"]'),
      restore: document.querySelectorAll('[data-testid="right-restore-button"]').length,
      tas: [...document.querySelectorAll('textarea')].map((t) => ({
        ph: t.placeholder?.slice(0, 24), w: t.offsetWidth, h: t.offsetHeight,
      })),
    }))
    L(`open-probe i=${i} ${JSON.stringify(diag)}`)
    if ((diag.tas || []).some((t) => t.w > 20 && t.h > 10) && diag.right !== '1') {
      ready = true
      break
    }
    await ensureChiefVisible(p)
    await sleep(700)
  }
  if (!ready) {
    await ensureChiefVisible(p)
    await sleep(1000)
  }
  const ta = p.locator('textarea').filter({ hasNot: p.locator('[disabled]') }).first()
  await ta.waitFor({ state: 'attached', timeout: 15000 })
  // 不强制 visible——被折叠时 offset 可能短暂为 0，chiefSay 内会再 ensure
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

  // Phase A: 辅信(对话+审批)——工具名写死,避免模型只聊天不落库
  // preferWrite=false：未选章时写作槽不在，走主编对话；bookTitle 防退库后无法续跑
  const say = (msg, maxMs = 300000) => chiefSay(p, msg, { preferWrite: false, maxMs, bookTitle: BOOK })
  L('phase-A intent')
  await say('请用 s3_set_intent 写入北极星(需我审批):reader_feeling=压抑中见一线热;emotional_arc=隐瞒到对质;red_lines=不美化私刑。未获批准不得声称已落库。', 240000)
  await approveAllPending(p)

  L('phase-A characters')
  // 双角色+关系：Hermes 多轮工具，给足时间（r15/r16 卡在 300s 边界）
  await say('请用 s3_add_character 登记「沈砚」(appearance=右手有茧,deep_need=查清灰契)与「老道」(appearance=灰袍,deep_need=守炉),再用 s3_add_character_relation 建竞争关系。需我审批。未获批准不得声称已落库。', 480000)
  await approveAllPending(p)

  L('phase-A world rule')
  await say('请用 s3_add_world_rule 登记规则:灰契立契后必有代价,不可无故解除。需我审批。', 240000)
  await approveAllPending(p)

  L('phase-A motif')
  await say('请用 s3_add_motif 登记母题 name=灰契 theme=契约代价 echoes=灰印/契血。需我审批。未获批准不得声称已落库。', 240000)
  await approveAllPending(p)

  L('phase-A promise')
  await say('请用 s3_plant_promise 埋伏笔:text=灰契会反噬立契人 setup_chapter=1。需我审批。', 240000)
  await approveAllPending(p)

  let ga = await fetchCraftGates({ work })
  L(`GATE-A after dialog ok=${ga.body?.gate_a?.ok} blocking=${JSON.stringify(ga.body?.gate_a?.blocking)}`)
  // 默认禁止 API 灌库;仅显式 E2E_ALLOW_API_SEED=1 可补(不得当质量 PASS 证据)
  if (!ga.body?.gate_a?.ok && process.env.E2E_ALLOW_API_SEED === '1') {
    L('API seed aux (E2E_ALLOW_API_SEED=1) — 非主路径')
    await fetch(`${API}/intent?work=${encodeURIComponent(work)}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reader_feeling: '压抑中见一线热', emotional_arc: '隐瞒到对质', red_lines: '不美化私刑',
      }),
    })
  }
  ga = await fetchCraftGates({ work })
  if (!ga.body?.gate_a?.ok) {
    L('GATE-A still red — continue; final assert will fail loudly')
  }

  // 建章:chief seed 只填输入框不自动发送——必须 chiefSay 真正 Enter
  L('create chapter via MCP s3_add_chapter')
  await say('请用 s3_add_chapter 新建第1章,title=夜访棺材铺。需我审批。未获批准不得声称已落库。', 300000)
  await approveAllPending(p)
  // 轮询落库(最多 ~40s)
  let chapterN = 0
  for (let i = 0; i < 20; i++) {
    await approveAllPending(p)
    try {
      const chs = await apiJson(`/chapters?work=${encodeURIComponent(work)}`)
      chapterN = Array.isArray(chs) ? chs.length : (chs?.chapters || []).length
    } catch { /* */ }
    L(`chapters poll i=${i} n=${chapterN}`)
    if (chapterN > 0) break
    await sleep(2000)
  }
  if (chapterN < 1) {
    // 按钮种子路径兜底:点「新建章」后手动发送 composer 当前内容
    const clicked = await createChapter(p)
    L(`createChapter button fallback clicked=${clicked}`)
    if (clicked) {
      try {
        const ta = p.locator('textarea[placeholder="就当前内容问主编…"]').first()
        if (await ta.isVisible().catch(() => false)) {
          await ta.press('Enter')
          await sleep(2000)
          await approveAllPending(p)
          await sleep(3000)
        }
      } catch (e) {
        L(`seed Enter fail ${e.message}`)
      }
    }
    try {
      const chs = await apiJson(`/chapters?work=${encodeURIComponent(work)}`)
      chapterN = Array.isArray(chs) ? chs.length : (chs?.chapters || []).length
    } catch { /* */ }
    L(`chapters after fallback n=${chapterN}`)
  }
  if (chapterN < 1) throw new Error('s3_add_chapter 未落库:无法进入章阶段')
  await selectChapter(p, 1)
  await sleep(1500)

  // Phase B: 大纲→节拍→演绎 —— 优先 s3_patch_chapter_plan 落库,stage-fill 作辅
  for (const [phase, planHint] of [
    ['大纲', 'synopsis 至少80字:沈砚夜访棺材铺逼问灰契,老道只给半句,灰印意象起'],
    ['节拍', 'beats 至少3条:推门/对质/缄口'],
    ['演绎', 'scene_truth≥80字含灰契机制;involved_characters 含沈砚、老道;每人 deductions prose 非空'],
  ]) {
    L(`stage ${phase}`)
    await selectChapter(p, 1)
    await clickTab(p, phase)
    await sleep(800)
    // 主路径:MCP 章 plan(与禁表单直填一致)。不做第二轮 stage-fill 闲聊——易把 UI 弄丢输入框
    await say(`第1章当前在「${phase}」阶段。请用 s3_patch_chapter_plan 写入(${planHint})。需我审批。未获批准不得声称已落库。`, 300000)
    await approveAllPending(p)
    await sleep(1000)
  }

  // Phase C: 优先 WriteChat 提案卡「接受」；无卡则 MCP s3_save_chapter（manuscript 直写，作者路径）
  L('prose via draft tab')
  await selectChapter(p, 1)
  await clickTab(p, '草稿')
  await sleep(800)
  // 质量硬要求：章级篇幅 + 对白 + 伏笔可追踪 + 限知；闸绿不算过
  const MIN_PROSE = Number(process.env.E2E_MIN_PROSE || 1500)
  // 先试提案卡（WriteLayout DraftCard）
  await chiefSay(p,
    `请按大纲、节拍、演绎给第1章写一版草稿提案卡（净文至少${MIN_PROSE}字，限知沈砚视角）。` +
    '必须：①老道半句具体对白；②埋「灰契反噬立契人」钩子；③竞争张力；④灰印/契血意象；⑤压抑中有热。' +
    '用提案卡输出，不要只聊天。',
    { maxMs: 420000, preferWrite: true, bookTitle: BOOK },
  )
  let accept = null
  try {
    accept = await acceptDraftProposal(p, { timeoutMs: 120000 })
    L(`accept ${JSON.stringify(accept)}`)
  } catch (e) {
    L(`accept fail ${e.message}`)
  }
  await approveAllPending(p)
  // 若仍停在草稿,点「采用为正文」
  try {
    const adopt = p.getByRole('button', { name: /采用为正文/ })
    if (await adopt.count() && await adopt.first().isVisible().catch(() => false)) {
      await adopt.first().click()
      await sleep(1500)
      L('clicked 采用为正文')
    }
  } catch (e) {
    L(`adopt skip ${e.message}`)
  }

  let ch = await apiJson(`/chapter?seq=1&work=${encodeURIComponent(work)}`)
  let prose = String(ch.prose || '')
  if (prose.replace(/\s/g, '').length < MIN_PROSE) {
    // 提案卡未落库：显式 s3_save_chapter（不经 elicitation，属 manuscript 作者草稿路径）
    L('prose fallback via s3_save_chapter')
    await selectChapter(p, 1)
    await clickTab(p, '草稿')
    await sleep(600)
    await chiefSay(p,
      `提案卡未采用。请立刻用工具 s3_save_chapter 写入第1章正文（seq=1），` +
      `prose 净文至少${MIN_PROSE}汉字。限知沈砚视角。必须含：①老道半句对白「灰契不在纸上，在你身上」；` +
      `②腕内侧灰印发烫；③灰契反噬立契人的暗示钩子；④竞争张力；⑤压抑中见热。` +
      `title=夜访棺材铺 focalizer=沈砚。写完即调用工具，不要只聊天。`,
      { maxMs: 480000, preferWrite: true, bookTitle: BOOK },
    )
    await approveAllPending(p)
    for (let i = 0; i < 15; i++) {
      await sleep(2000)
      try {
        ch = await apiJson(`/chapter?seq=1&work=${encodeURIComponent(work)}`)
        prose = String(ch.prose || '')
      } catch { /* */ }
      const n = prose.replace(/\s/g, '').length
      L(`prose poll i=${i} n=${n}`)
      if (n >= MIN_PROSE) break
    }
  }
  if (prose.replace(/\s/g, '').length < 80) {
    try {
      const dr = await apiJson(`/latest-draft?seq=1&work=${encodeURIComponent(work)}`)
      prose = String(dr?.prose || prose)
      L(`fallback draft prose len=${prose.replace(/\s/g, '').length}`)
    } catch { /* */ }
  }
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
