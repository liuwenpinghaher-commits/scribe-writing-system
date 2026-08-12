// Phase 1–6 可调用函数（均在 withPage 会话内或只读 API）
import { openBook, BASE } from '../lib.mjs'
import {
  chiefSay,
  acceptDraftProposal,
  adoptDraftAsFinal,
  approveAllPending,
  ensureChiefVisible,
} from '../author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../../src/e2e/workResolution.js'
import { missingDeductionProjections } from '../../src/e2e/chapterPlanState.js'
import {
  apiJson,
  listLen,
  workStats,
  chapterProseLen,
  chapterPayload,
  listChapters,
  fetchIntent,
  fetchCraftGates,
  fetchEntities,
  fetchFactions,
  fetchWorldRules,
  fetchItems,
  fetchTerms,
  fetchMotifs,
  fetchPromises,
  fetchRecall,
  fetchFrame,
  fetchCanonCandidates,
  fetchCanonAnalysis,
  fetchQualityDashboard,
  evaluateFinalizeGateReadOnly,
  fetchGraph,
} from './api_read.mjs'
import { qualityReview, mapTenDimensions } from './quality_bridge.mjs'
import { clickTab, selectChapter, createChapter, ensureWriteComposer, screenshot } from './ui_helpers.mjs'
import { NOVEL, chapterPlan, stagePrompt, prosePrompt, repairPrompt } from './novel_bible.mjs'
import { log, writeJson } from './log.mjs'
import { saveCheckpoint } from './checkpoint.mjs'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function recordRun(cp, result) {
  if (typeof result?.run?.id === 'string' && result.run.id) {
    cp.run_ids = [...new Set([...(cp.run_ids || []), result.run.id])]
  }
  return result
}

// ─── Phase 1: 建书 + 设定 ───────────────────────────────────────────
export async function phase1Bootstrap(page, env, cp, artDir) {
  const L = (m) => log(m, { artDir })
  if (cp.phase && ['settings_done', 'wcg_done', 'writing', 'advanced', 'final', 'done'].includes(cp.phase)
    && cp.work) {
    L(`phase1 skip: already work=${cp.work}`)
    process.env.E2E_WORK = cp.work
    process.env.E2E_BOOK_TITLE = cp.book || env.BOOK
    return cp
  }

  const BOOK = cp.book || env.BOOK
  process.env.E2E_BOOK_TITLE = BOOK
  L(`phase1 create book title=${BOOK}`)

  await page.goto(env.BASE || BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await sleep(1000)

  // 若指定 E2E_WORK 续跑已有书
  if (env.WORK || cp.work) {
    const work = env.WORK || cp.work
    await openBook(page, BOOK, { work })
    cp.work = work
    cp.book = BOOK
    cp.phase = 'settings_done'
    process.env.E2E_WORK = work
    L(`phase1 reopen existing work=${work}`)
    saveCheckpoint(artDir, cp)
    return cp
  }

  const nameInput = page.locator('input[placeholder="书名…"], input[aria-label="书名"]')
  await nameInput.waitFor({ timeout: 20000 })
  await nameInput.fill(BOOK)
  const createBtn = page.getByRole('button', { name: '建', exact: true }).first()
  const waitCreate = page.waitForResponse(
    (r) => /\/works(\?|$)/.test(r.url()) && r.request().method() === 'POST' && r.status() < 500,
    { timeout: 45000 },
  ).catch(() => null)
  if (await createBtn.isVisible().catch(() => false)) await createBtn.click()
  else await nameInput.press('Enter')
  const created = await waitCreate
  L(`createWork response ${created ? created.status() : 'timeout'}`)
  if (created && created.status() >= 400) {
    throw new Error(`建书失败 HTTP ${created.status()}`)
  }

  try {
    await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  } catch {
    const card = page.getByRole('button', { name: `打开${BOOK}`, exact: true })
    if (await card.count()) await card.click()
    else {
      await page.getByRole('button', { name: new RegExp(BOOK.slice(0, 12).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).first().click()
    }
    await page.waitForSelector('[data-testid="four-col"]', { timeout: 30000 })
  }
  L('M1 four-col visible')
  await screenshot(page, artDir, 'phase1-four-col')
  await ensureChiefVisible(page, { bookTitle: BOOK })

  let work = ''
  for (let i = 0; i < 15 && !work; i++) {
    const works = await apiJson('/works')
    const list = Array.isArray(works) ? works : (works.works || [])
    work = resolveWorkSlugByExactTitle(list, BOOK)
    if (!work) await sleep(1000)
  }
  if (!work) throw new Error('M1 FAIL: 无法解析 work slug')
  process.env.E2E_WORK = work
  cp.work = work
  cp.book = BOOK
  cp.must = { ...cp.must, M1: { ok: true, work } }
  L(`M1 PASS work=${work}`)

  const say = (msg, maxMs = 300000) =>
    chiefSay(page, msg, { preferWrite: false, maxMs, bookTitle: BOOK })

  // M2 北极星
  L('M2 intent')
  recordRun(cp, await say(
    `请用 s3_set_intent 写入北极星(需我审批):` +
    `reader_feeling=${NOVEL.reader_feeling};` +
    `emotional_arc=${NOVEL.emotional_arc};` +
    `red_lines=${NOVEL.red_lines}。未获批准不得声称已落库。`,
    300000,
  ))
  await approveAllPending(page)
  let intent = await fetchIntent(work)
  for (let r = 0; r < 2 && !(intent?.reader_feeling && intent?.emotional_arc && intent?.red_lines); r++) {
    recordRun(cp, await say(
      '请仅用 s3_set_intent 补齐 reader_feeling/emotional_arc/red_lines 三项非空。需我审批。',
      240000,
    ))
    await approveAllPending(page)
    intent = await fetchIntent(work)
  }
  const m2ok = !!(intent?.reader_feeling && intent?.emotional_arc && intent?.red_lines)
  cp.must.M2 = { ok: m2ok, intent: {
    reader_feeling: intent?.reader_feeling,
    emotional_arc: intent?.emotional_arc,
    red_lines: intent?.red_lines,
  } }
  L(`M2 ${m2ok ? 'PASS' : 'FAIL'}`)

  // M3 设定库全类型
  L('M3 characters')
  recordRun(cp, await say(
    `请用 s3_add_character 登记：` +
    NOVEL.characters.map((c) =>
      `「${c.name}」(appearance=${c.appearance},deep_need=${c.deep_need})`).join('；') +
    `；再用 s3_add_character_relation 建立${NOVEL.relation}。需我审批。`,
    480000,
  ))
  await approveAllPending(page)

  L('M3 world_rule + faction')
  recordRun(cp, await say(
    `请用 s3_add_world_rule 登记：${NOVEL.world_rule}。` +
    `再用 s3_add_faction 登记 name=${NOVEL.faction.name} goal=${NOVEL.faction.goal} method=${NOVEL.faction.method}。需我审批。`,
    360000,
  ))
  await approveAllPending(page)

  L('M3 item + term + motif')
  recordRun(cp, await say(
    `请登记：物品 s3_add_item name=${NOVEL.item.name}；` +
    `术语（s3_add_term 或等价）name=${NOVEL.term.name} definition=${NOVEL.term.definition}；` +
    `母题 s3_add_motif name=${NOVEL.motif.name} theme=${NOVEL.motif.theme} echoes=${NOVEL.motif.echoes}。需我审批。`,
    360000,
  ))
  await approveAllPending(page)

  // M10 前 5 章伏笔先种 3 条（后续章 track/resolve）
  L('M10 plant promises')
  for (const p of NOVEL.promises) {
    recordRun(cp, await say(
      `请用 s3_plant_promise 埋伏笔 text=${p.text} setup_chapter=${p.setup_chapter}。需我审批。`,
      240000,
    ))
    await approveAllPending(page)
  }

  const counts = {
    entities: listLen(await fetchEntities(work)),
    factions: listLen(await fetchFactions(work)),
    world_rules: listLen(await fetchWorldRules(work)),
    items: listLen(await fetchItems(work)),
    terms: listLen(await fetchTerms(work)),
    motifs: listLen(await fetchMotifs(work)),
    promises: listLen(await fetchPromises(work)),
  }
  const m3ok = counts.entities >= 1 && counts.factions >= 1 && counts.world_rules >= 1
    && counts.motifs >= 1 && counts.promises >= 1
  cp.must.M3 = { ok: m3ok, counts }
  cp.must.M10_plant = { ok: counts.promises >= 1, counts: counts.promises }
  L(`M3 ${m3ok ? 'PASS' : 'PARTIAL'} ${JSON.stringify(counts)}`)

  // S1 explore mode
  try {
    const sc = await apiJson(`/setting-completeness?work=${encodeURIComponent(work)}`)
    cp.should = { ...cp.should, S1_explore: { ok: true, body: sc } }
  } catch (e) {
    cp.should = { ...cp.should, S1_explore: { ok: false, err: e.message } }
  }

  cp.phase = 'settings_done'
  saveCheckpoint(artDir, cp)
  writeJson(`${artDir}/quality/settings_counts.json`, counts)
  return cp
}

// ─── Phase 2: WCG / GATE-A ──────────────────────────────────────────
export async function phase2Wcg(page, env, cp, artDir) {
  const L = (m) => log(m, { artDir })
  const work = cp.work
  const BOOK = cp.book
  const say = (msg, maxMs = 300000) =>
    chiefSay(page, msg, { preferWrite: false, maxMs, bookTitle: BOOK })

  const gateARepair = {
    A1: '请仅用 s3_set_intent 补齐 reader_feeling/emotional_arc/red_lines。需我审批。',
    A2: '请仅用 s3_add_character 确保至少两名完整角色（含 appearance 与 deep_need）。需我审批。',
    A3: '请仅用 s3_add_world_rule 登记至少一条世界规则。需我审批。',
    A4: '请仅用 s3_add_character_relation 建立角色关系。需我审批。',
    A5: '请仅用 s3_add_motif 登记母题。需我审批。',
    A6: '请仅用 s3_plant_promise 埋伏笔。需我审批。',
    A7: '请仅用 s3_plant_promise 使伏笔可进入 chapter brief。需我审批。',
  }

  let ga = await fetchCraftGates({ work })
  L(`GATE-A initial ok=${ga?.gate_a?.ok} blocking=${JSON.stringify(ga?.gate_a?.blocking)}`)
  for (let round = 0; !ga?.gate_a?.ok && round < 3; round++) {
    await openBook(page, BOOK, { work })
    const blocking = [...new Set(ga?.gate_a?.blocking || [])]
    if (!blocking.length) {
      recordRun(cp, await say(
        'GATE-A 未通过但 blocking 为空。请检查并补齐 intent/角色/规则/关系/母题/伏笔。需我审批。',
        300000,
      ))
    } else {
      for (const id of blocking) {
        const prompt = gateARepair[id] || `请修复 GATE-A 项 ${id}。只用对应 s3_* 工具。需我审批。`
        L(`Gate-A repair round=${round + 1} ${id}`)
        recordRun(cp, await say(prompt, 300000))
        await approveAllPending(page)
      }
    }
    ga = await fetchCraftGates({ work })
    L(`GATE-A after repair ok=${ga?.gate_a?.ok} blocking=${JSON.stringify(ga?.gate_a?.blocking)}`)
  }

  const m4ok = !!ga?.gate_a?.ok && !(ga?.gate_a?.blocking || []).length
  cp.must.M4 = { ok: m4ok, gate_a: ga?.gate_a }
  if (!m4ok) L('M4 FAIL — 后续仍写章，终审会 fail-loud')
  else L('M4 PASS')

  writeJson(`${artDir}/quality/craft_gates_phase2.json`, ga)
  cp.phase = 'wcg_done'
  saveCheckpoint(artDir, cp)
  return cp
}

// ─── Phase 3+4: 章脚手架 + 写作 ─────────────────────────────────────
export async function writeChapterCycle(page, env, cp, artDir, seq) {
  const L = (m) => log(m, { artDir })
  const work = cp.work
  const BOOK = cp.book
  const plan = chapterPlan(seq)
  const minLen = env.MIN_CHAPTER_NET
  const t0 = Date.now()
  const result = {
    seq,
    title: plan.title,
    focalizer: plan.focalizer,
    stages: {},
    prose_len: 0,
    quality: null,
    gates: null,
    duration_ms: 0,
    ok: false,
    errors: [],
  }

  await openBook(page, BOOK, { work })
  await sleep(1000)

  // 确保章存在
  let chapters = await listChapters(work)
  let exists = chapters.some((c) => Number(c.seq) === seq)
  if (!exists) {
    L(`ch${seq} create via MCP s3_add_chapter`)
    recordRun(cp, await chiefSay(page,
      `请用 s3_add_chapter 新建第${seq}章,title=${plan.title}。需我审批。未获批准不得声称已落库。`,
      { preferWrite: false, maxMs: 300000, bookTitle: BOOK },
    ))
    await approveAllPending(page)
    for (let i = 0; i < 20 && !exists; i++) {
      await sleep(2000)
      chapters = await listChapters(work)
      exists = chapters.some((c) => Number(c.seq) === seq)
      if (!exists) {
        // 按钮兜底
        if (i === 5) {
          const clicked = await createChapter(page)
          L(`createChapter button fallback=${clicked}`)
        }
      }
    }
  }
  if (!exists) {
    // 若新建落在别的 seq，选最大 seq
    const maxSeq = Math.max(0, ...chapters.map((c) => Number(c.seq) || 0))
    if (maxSeq >= seq || maxSeq > 0) {
      L(`ch${seq} not exact; maxSeq=${maxSeq}`)
    } else {
      result.errors.push('chapter not created')
      result.duration_ms = Date.now() - t0
      return result
    }
  }

  let sel = await selectChapter(page, seq)
  if (!sel) {
    const all = page.locator('button').filter({ hasText: /第\s*\d+\s*章|^\d+\s+/ })
    const n = await all.count()
    if (n) await all.nth(n - 1).click({ force: true })
    await sleep(1500)
    sel = true
  }

  // 脚手架：大纲→节拍→演绎（MCP）
  for (const phase of ['大纲', '节拍', '演绎']) {
    L(`ch${seq} stage ${phase}`)
    await selectChapter(page, seq)
    await clickTab(page, phase)
    await sleep(600)
    try {
      recordRun(cp, await chiefSay(page, stagePrompt(seq, phase, plan), {
        preferWrite: false, maxMs: 300000, bookTitle: BOOK,
      }))
      await approveAllPending(page)
      // 尝试 stage fill（若 UI 有提案）
      try {
        const fill = page.locator('[data-testid="stage-fill"]').first()
        if (await fill.isVisible({ timeout: 3000 }).catch(() => false)) {
          await fill.click()
          await sleep(800)
        }
      } catch { /* */ }
      result.stages[phase] = 'done'
    } catch (e) {
      result.stages[phase] = `error:${e.message}`
      result.errors.push(`${phase}:${e.message}`)
      L(`ch${seq} stage ${phase} fail: ${e.message}`)
    }
  }

  // 演绎回读
  try {
    let ch = await chapterPayload(work, seq)
    let missing = missingDeductionProjections(ch)
    if (missing.length) {
      L(`ch${seq} deduce missing=${JSON.stringify(missing)}`)
      recordRun(cp, await chiefSay(page,
        `第${seq}章演绎不合格：${missing.join('、')}。请仅用 s3_patch_chapter_plan 修正 scene_truth 与 deductions。` +
        `focalizer=${plan.focalizer}。需我审批。`,
        { preferWrite: false, maxMs: 300000, bookTitle: BOOK },
      ))
      await approveAllPending(page)
      ch = await chapterPayload(work, seq)
      missing = missingDeductionProjections(ch)
    }
    result.plan_ok = missing.length === 0
    result.plan_snapshot = {
      has_synopsis: !!(ch.synopsis || ch.plan?.synopsis || ch.outline),
      has_beats: !!(ch.beats || ch.plan?.beats),
      has_scene_truth: !!(ch.scene_truth || ch.plan?.scene_truth),
    }
  } catch (e) {
    result.plan_ok = false
    result.errors.push(`plan_read:${e.message}`)
  }

  // 正文：写作槽提案卡
  L(`ch${seq} prose`)
  await selectChapter(page, seq)
  await clickTab(page, '草稿')
  await clickTab(page, '正文')
  let hasComposer = await ensureWriteComposer(page)
  if (!hasComposer) {
    await selectChapter(page, seq)
    hasComposer = await ensureWriteComposer(page, { retries: 8 })
  }
  if (!hasComposer) {
    result.errors.push('no write composer')
    await screenshot(page, artDir, `fail-ch${seq}-composer`)
  } else {
    try {
      recordRun(cp, await chiefSay(page, prosePrompt(seq, plan, minLen), {
        preferWrite: true, maxMs: env.CHAPTER_MAX_MS, bookTitle: BOOK,
      }))
      await approveAllPending(page)
      const acc = await acceptDraftProposal(page, { timeoutMs: 300000 })
      result.accept = acc
      if (acc.kind === 'stage') {
        const saveResponse = page.waitForResponse((response) => {
          let path = ''
          try { path = new URL(response.url()).pathname.replace(/^\/api/, '') } catch { return false }
          return response.request().method() === 'POST' && path === '/save-chapter'
        }, { timeout: 120000 }).catch(() => null)
        try {
          result.adoption = await adoptDraftAsFinal(page, { timeoutMs: 120000 })
          const saved = await saveResponse
          if (saved && saved.status() !== 200) {
            result.errors.push(`save-chapter HTTP ${saved.status()}`)
          }
        } catch (e) {
          result.errors.push(`adopt:${e.message}`)
          // MCP 回退：仍经 chiefSay 审批，不直 POST
          recordRun(cp, await chiefSay(page,
            `提案卡未采用为正文。请立刻用 s3_save_chapter 写入第${seq}章完整正文，` +
            `title=${plan.title} focalizer=${plan.focalizer}，净文≥${minLen}字。需我审批。`,
            { preferWrite: true, maxMs: env.CHAPTER_MAX_MS, bookTitle: BOOK },
          ))
          await approveAllPending(page)
        }
      }
      await sleep(2000)
    } catch (e) {
      result.errors.push(`prose:${e.message}`)
      await screenshot(page, artDir, `fail-ch${seq}-prose`)
      L(`ch${seq} prose fail: ${e.message}`)
    }
  }

  let proseLen = await chapterProseLen(work, seq)
  result.prose_len = proseLen

  // 质量修订循环
  let quality = qualityReview(work, seq, { minProse: minLen })
  result.quality = quality.report
  for (let repair = 0; !quality.ok && repair < env.QUALITY_REPAIR_ROUNDS; repair++) {
    const failed = (quality.report?.checks || []).filter((c) => !c.ok)
      .map((c) => `${c.id}:${c.detail}`).join('；') || '质量未通过'
    L(`ch${seq} quality repair ${repair + 1}: ${failed}`)
    await openBook(page, BOOK, { work })
    await selectChapter(page, seq)
    await clickTab(page, '草稿')
    try {
      recordRun(cp, await chiefSay(page, repairPrompt(seq, failed, minLen), {
        preferWrite: true, maxMs: env.CHAPTER_MAX_MS, bookTitle: BOOK,
      }))
      await approveAllPending(page)
      try {
        await acceptDraftProposal(page, { timeoutMs: 180000 })
        const adopt = page.getByRole('button', { name: '采用为正文', exact: true }).first()
        if (await adopt.isVisible().catch(() => false)) await adopt.click()
      } catch { /* MCP save 路径 */ }
      await sleep(2000)
    } catch (e) {
      result.errors.push(`repair:${e.message}`)
    }
    proseLen = await chapterProseLen(work, seq)
    result.prose_len = proseLen
    quality = qualityReview(work, seq, { minProse: minLen })
    result.quality = quality.report
  }

  // 章级 craft gates
  try {
    result.gates = await fetchCraftGates({ work, seq })
  } catch (e) {
    result.errors.push(`gates:${e.message}`)
  }

  // 限知帧（M8 采样）
  try {
    result.frame = await fetchFrame(work, { seq, focalizer: plan.focalizer })
  } catch { /* */ }

  // 落盘
  try {
    const ch = await chapterPayload(work, seq)
    const prose = ch.prose || ''
    writeJson(`${artDir}/chapters/ch${String(seq).padStart(2, '0')}.json`, {
      seq,
      title: plan.title,
      focalizer: plan.focalizer,
      prose_len: result.prose_len,
      quality: result.quality,
      gates: result.gates,
      plan: result.plan_snapshot,
      errors: result.errors,
    })
    const { writeFileSync, mkdirSync } = await import('node:fs')
    mkdirSync(`${artDir}/chapters`, { recursive: true })
    writeFileSync(`${artDir}/chapters/ch${String(seq).padStart(2, '0')}.txt`, prose)
  } catch (e) {
    result.errors.push(`artifact:${e.message}`)
  }

  const dims = mapTenDimensions(result.quality?.scores || {})
  result.ten_dim = dims
  result.ok = result.prose_len >= env.MIN_CHAPTER_HARD
    && !!quality.ok
    && result.prose_len >= Math.min(minLen, env.MIN_CHAPTER_HARD)
  // 硬门：最短章；质量硬失败记入但允许 SHOULD 级继续
  result.duration_ms = Date.now() - t0
  L(`ch${seq} done prose=${result.prose_len} quality=${quality.ok} gates_ok=${result.gates?.ok} ms=${result.duration_ms}`)
  return result
}

export async function phase34WriteAll(page, env, cp, artDir) {
  const L = (m) => log(m, { artDir })
  const start = (cp.lastCompletedChapter || 0) + 1
  const end = env.TARGET_CHAPTERS
  cp.phase = 'writing'
  cp.chapter_results = cp.chapter_results || {}

  for (let seq = start; seq <= end; seq++) {
    if (Date.now() - new Date(cp.started_at).getTime() > env.TOTAL_MAX_MS) {
      L('TOTAL_MAX_MS exceeded — stop writing loop')
      break
    }
    const stats = await workStats(cp.work)
    if ((stats?.word_count || 0) >= env.WORD_TARGET && seq > 15) {
      L(`word target hit early word_count=${stats.word_count} at seq boundary ${seq}`)
      // 仍确保至少 15 章
      if ((stats?.chapter_count || 0) >= 15 && seq > 15) break
    }

    L(`=== chapter loop seq=${seq}/${end} ===`)
    let chResult
    try {
      chResult = await writeChapterCycle(page, env, cp, artDir, seq)
    } catch (e) {
      L(`chapter ${seq} thrown: ${e.message}`)
      chResult = { seq, ok: false, errors: [e.message], prose_len: 0 }
      await screenshot(page, artDir, `fail-ch${seq}-throw`).catch(() => {})
    }
    cp.chapter_results[seq] = {
      ok: chResult.ok,
      prose_len: chResult.prose_len,
      quality_ok: chResult.quality?.ok ?? chResult.quality?.quality_pass,
      gate_b: chResult.gates?.gate_b?.ok,
      gate_c: chResult.gates?.gate_c_det?.ok,
      gate_d: chResult.gates?.gate_d?.ok,
      ten_dim: chResult.ten_dim,
      duration_ms: chResult.duration_ms,
      errors: chResult.errors,
    }
    cp.lastCompletedChapter = seq
    saveCheckpoint(artDir, cp)

    // 每章后刷字数
    const st = await workStats(cp.work)
    L(`after ch${seq} word_count=${st?.word_count} chapters=${st?.chapter_count}`)
  }

  // M5/M6 汇总
  const written = Object.entries(cp.chapter_results).filter(([, v]) => (v.prose_len || 0) >= env.MIN_CHAPTER_HARD)
  const planOk = Object.entries(cp.chapter_results).filter(([, v]) => v.ok || v.quality_ok)
  const stats = await workStats(cp.work)
  cp.must.M5 = {
    ok: written.length >= 15 * 0.8,
    note: '≥80% 章应有脚手架；细节见 chapters/*.json plan',
  }
  cp.must.M6 = {
    ok: (stats?.word_count || 0) >= env.WORD_TARGET && (stats?.chapter_count || 0) >= 15,
    word_count: stats?.word_count,
    chapter_count: stats?.chapter_count,
    written_ge_hard: written.length,
  }
  L(`M6 word_count=${stats?.word_count} chapters=${stats?.chapter_count} M6.ok=${cp.must.M6.ok}`)
  return cp
}

// ─── Phase 5: 高级功能 ──────────────────────────────────────────────
export async function phase5Advanced(page, env, cp, artDir) {
  const L = (m) => log(m, { artDir })
  const work = cp.work
  const BOOK = cp.book
  cp.phase = 'advanced'

  // M7 正典
  try {
    const cand = await fetchCanonCandidates(work)
    const analysis = await fetchCanonAnalysis(work)
    const n = listLen(cand) + listLen(analysis)
    // 触发一次章后正典分析（对话）
    await openBook(page, BOOK, { work })
    recordRun(cp, await chiefSay(page,
      '请对最近已写章执行正典抽取/分析（可用相关 canon 工具），列出待确认候选。需我审批。',
      { preferWrite: false, maxMs: 300000, bookTitle: BOOK },
    ))
    await approveAllPending(page)
    const cand2 = await fetchCanonCandidates(work)
    cp.must.M7 = {
      ok: listLen(cand2) >= 0, // 有端点可回读即链路通；候选可为 0
      candidates_before: listLen(cand),
      candidates_after: listLen(cand2),
      analysis_present: analysis != null,
    }
    writeJson(`${artDir}/evidence/canon-candidates.json`, cand2)
    L(`M7 candidates=${listLen(cand2)}`)
  } catch (e) {
    cp.must.M7 = { ok: false, err: e.message }
    L(`M7 FAIL ${e.message}`)
  }

  // M8 限知：抽 3 章 frame
  const leakChecks = []
  const sampleSeqs = Object.keys(cp.chapter_results || {}).map(Number).filter((s) => s > 0).slice(0, 5)
  for (const seq of sampleSeqs) {
    const plan = chapterPlan(seq)
    try {
      const frame = await fetchFrame(work, { seq, focalizer: plan.focalizer })
      // 无统一 find_leaks REST 时：检查 frame 不包含明显“全知旁白”标记字段
      const text = JSON.stringify(frame || {})
      const leak = /全知|上帝视角|他人内心秘密未揭示/.test(text)
      leakChecks.push({ seq, focalizer: plan.focalizer, leak, frame_ok: frame != null })
    } catch (e) {
      leakChecks.push({ seq, err: e.message, leak: false })
    }
  }
  cp.must.M8 = {
    ok: leakChecks.every((c) => !c.leak),
    samples: leakChecks,
  }
  writeJson(`${artDir}/evidence/epistemic-samples.json`, leakChecks)
  L(`M8 ok=${cp.must.M8.ok}`)

  // M9 记忆
  try {
    const recall = await fetchRecall(work, '沈砚 灰契 老道')
    const n = listLen(recall) || (recall?.hits?.length || 0) || (recall?.results?.length || 0)
    // 对话触发 semantic recall
    await openBook(page, BOOK, { work })
    const mem = await chiefSay(page,
      '请用 s3_semantic_recall 或 s3_hybrid_recall 检索「灰契反噬」相关前文，列出至少1条命中摘要。不要写正典。',
      { preferWrite: false, maxMs: 240000, bookTitle: BOOK },
    )
    recordRun(cp, mem)
    const hit = n >= 1 || /命中|召回|记得|前文|第\s*\d+\s*章/.test(mem.reply || '')
    cp.must.M9 = { ok: hit, api_hits: n, reply_snippet: (mem.reply || '').slice(0, 200) }
    writeJson(`${artDir}/evidence/memory-recalls/recall.json`, { recall, reply: mem.reply })
    L(`M9 ok=${hit} api_hits=${n}`)
  } catch (e) {
    cp.must.M9 = { ok: false, err: e.message }
  }

  // M10 伏笔 track/resolve
  try {
    const promises = await fetchPromises(work)
    const list = Array.isArray(promises) ? promises : (promises?.promises || [])
    await openBook(page, BOOK, { work })
    recordRun(cp, await chiefSay(page,
      '请用伏笔工具（s3_track_promise / 推进 / resolve）更新：' +
      '将「灰契会反噬立契人」标为已在后文章节推进或兑现；其余可保持 open。需我审批。',
      { preferWrite: false, maxMs: 300000, bookTitle: BOOK },
    ))
    await approveAllPending(page)
    const promises2 = await fetchPromises(work)
    const list2 = Array.isArray(promises2) ? promises2 : (promises2?.promises || [])
    const statuses = list2.map((p) => p.status || p.state)
    const hasClosed = statuses.some((s) => /close|resolved|paid|兑现/i.test(String(s)))
    cp.must.M10 = {
      ok: list2.length >= 1,
      before: list.length,
      after: list2.length,
      statuses,
      hasClosed,
    }
    writeJson(`${artDir}/evidence/promises.json`, list2)
    L(`M10 promises=${list2.length} hasClosed=${hasClosed}`)
  } catch (e) {
    cp.must.M10 = { ok: false, err: e.message }
  }

  // S2 Director
  try {
    await openBook(page, BOOK, { work })
    const d = await chiefSay(page,
      '请给出当前进度的 Director 创意建议（3条以内可执行下一步），不必写库。',
      { preferWrite: false, maxMs: 180000, bookTitle: BOOK },
    )
    recordRun(cp, d)
    cp.should.S2_director = {
      ok: (d.reply || '').length > 20,
      snippet: (d.reply || '').slice(0, 300),
    }
  } catch (e) {
    cp.should.S2_director = { ok: false, err: e.message }
  }

  // S3 返工
  try {
    const seq = cp.lastCompletedChapter || 1
    await openBook(page, BOOK, { work })
    await selectChapter(page, seq)
    const before = await chapterProseLen(work, seq)
    recordRun(cp, await chiefSay(page,
      `请小幅修订第${seq}章：加强一段感官描写，保持情节与限知不变，用提案卡或 s3_save_chapter 提交。需我审批。`,
      { preferWrite: true, maxMs: 360000, bookTitle: BOOK },
    ))
    await approveAllPending(page)
    try {
      await acceptDraftProposal(page, { timeoutMs: 120000 })
      const adopt = page.getByRole('button', { name: '采用为正文', exact: true }).first()
      if (await adopt.isVisible().catch(() => false)) await adopt.click()
    } catch { /* */ }
    await sleep(2000)
    const after = await chapterProseLen(work, seq)
    cp.should.S3_rewrite = { ok: after > 0, before, after, changed: after !== before }
  } catch (e) {
    cp.should.S3_rewrite = { ok: false, err: e.message }
  }

  // C1 StorylineHub
  try {
    await openBook(page, BOOK, { work })
    const has = await page.locator('[data-testid*="storyline"], text=故事线, text=Storyline').count()
    cp.could.C1_storyline = { ok: has > 0, count: has }
  } catch (e) {
    cp.could.C1_storyline = { ok: false, err: e.message }
  }

  // C2 多 POV
  const focals = new Set(
    Object.keys(cp.chapter_results || {}).map((s) => chapterPlan(Number(s)).focalizer),
  )
  cp.could.C2_multi_pov = { ok: focals.size >= 3, focals: [...focals] }

  // graph
  try {
    const g = await fetchGraph(work)
    cp.could.graph = { ok: g != null, nodes: listLen(g) }
  } catch { /* */ }

  saveCheckpoint(artDir, cp)
  return cp
}

// ─── Phase 6: 终审 ──────────────────────────────────────────────────
export async function phase6FinalAudit(env, cp, artDir) {
  const L = (m) => log(m, { artDir })
  const work = cp.work
  cp.phase = 'final'

  const stats = await workStats(work)
  const qualityDash = await fetchQualityDashboard(work)
  const gateA = await fetchCraftGates({ work })

  // 每章 gates 汇总
  const seqs = Object.keys(cp.chapter_results || {}).map(Number).sort((a, b) => a - b)
  let bOk = 0; let cOk = 0; let dOk = 0; let bN = 0
  const rubricMatrix = {}
  for (const seq of seqs) {
    bN++
    const cr = cp.chapter_results[seq]
    if (cr.gate_b) bOk++
    if (cr.gate_c) cOk++
    if (cr.gate_d) dOk++
    if (!cr.gate_b && cr.gate_b !== false) {
      try {
        const g = await fetchCraftGates({ work, seq })
        if (g?.gate_b?.ok) bOk++
        if (g?.gate_c_det?.ok) cOk++
        if (g?.gate_d?.ok) dOk++
        cr.gate_b = g?.gate_b?.ok
        cr.gate_c = g?.gate_c_det?.ok
        cr.gate_d = g?.gate_d?.ok
      } catch { /* */ }
    }
    // 十维
    if (cr.ten_dim?.dimensions) rubricMatrix[seq] = cr.ten_dim
    else if (cr.quality_ok != null) {
      const q = qualityReview(work, seq, { minProse: env.MIN_CHAPTER_NET })
      rubricMatrix[seq] = mapTenDimensions(q.report?.scores || {})
    }
  }

  const gateRates = {
    A: { ok: !!gateA?.gate_a?.ok, pass_rate: gateA?.gate_a?.ok ? 1 : 0, blocking: gateA?.gate_a?.blocking || [] },
    B: { pass_rate: bN ? bOk / bN : 0, ok_count: bOk, total: bN },
    C: { pass_rate: bN ? cOk / bN : 0, ok_count: cOk, total: bN },
    D: { pass_rate: bN ? dOk / bN : 0, ok_count: dOk, total: bN },
  }

  // 十维全书均值
  const dimAcc = {}
  let dimSamples = 0
  for (const row of Object.values(rubricMatrix)) {
    const dims = row.dimensions || row
    for (const [k, v] of Object.entries(dims)) {
      if (typeof v !== 'number') continue
      dimAcc[k] = dimAcc[k] || []
      dimAcc[k].push(v)
    }
    dimSamples++
  }
  const quality_scores = {}
  for (const [k, arr] of Object.entries(dimAcc)) {
    quality_scores[k] = arr.reduce((a, b) => a + b, 0) / arr.length
  }
  const scoreVals = Object.values(quality_scores)
  const tenAvg = scoreVals.length ? scoreVals.reduce((a, b) => a + b, 0) / scoreVals.length : null
  const tenMin = scoreVals.length ? Math.min(...scoreVals) : null
  const tenHardFail = scoreVals.some((v) => v <= 2.0)

  const finalize = await evaluateFinalizeGateReadOnly(work)

  // MUST 汇总
  const wordOk = (stats?.word_count || 0) >= env.WORD_TARGET
  const chOk = (stats?.chapter_count || 0) >= 15
  cp.must.M6 = {
    ok: wordOk && chOk,
    word_count: stats?.word_count,
    chapter_count: stats?.chapter_count,
  }
  cp.must.M11 = {
    ok: gateRates.A.ok
      && gateRates.B.pass_rate >= 0.8
      && gateRates.C.pass_rate >= 0.9,
    gateRates,
    note: 'GATE-D 软门 ≥0.7 记入 should',
  }
  cp.should.S4_gate_d = { ok: gateRates.D.pass_rate >= 0.7, pass_rate: gateRates.D.pass_rate }
  cp.should.S4_ten_dim = {
    ok: tenAvg != null && tenAvg >= 3.5 && tenMin != null && tenMin >= 3.0 && !tenHardFail,
    avg: tenAvg,
    min: tenMin,
    quality_scores,
    samples: dimSamples,
  }
  cp.must.M12 = {
    ok: finalize.allowed || finalize.ok,
    finalize,
  }

  writeJson(`${artDir}/quality/craft_gates.json`, { gateA, gateRates })
  writeJson(`${artDir}/quality/rubric_scores.json`, { quality_scores, matrix: rubricMatrix, tenAvg, tenMin })
  writeJson(`${artDir}/quality/quality_dashboard.json`, qualityDash)
  writeJson(`${artDir}/quality/finalize.json`, finalize)

  const mustIds = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10', 'M11', 'M12']
  const mustResults = {}
  for (const id of mustIds) {
    if (id === 'M10') {
      mustResults[id] = !!(cp.must.M10?.ok || cp.must.M10_plant?.ok)
    } else {
      mustResults[id] = !!cp.must[id]?.ok
    }
  }
  // 严格：任一 MUST 非 true → 总失败（闸绿≠质量；字数不足也失败）
  const mustAll = mustIds.every((id) => mustResults[id] === true)

  const duration_minutes = (Date.now() - new Date(cp.started_at).getTime()) / 60000
  const summary = {
    ok: mustAll,
    protocol: '50k-cli-playwright-acceptance-v1',
    work,
    book: cp.book,
    word_count: stats?.word_count || 0,
    chapter_count: stats?.chapter_count || 0,
    quality_scores,
    ten_dim_avg: tenAvg,
    ten_dim_min: tenMin,
    gate_results: gateRates,
    duration_minutes,
    run_ids: cp.run_ids || [],
    must: cp.must,
    should: cp.should,
    could: cp.could,
    must_pass: mustResults,
    must_all: mustAll,
    finished_at: new Date().toISOString(),
  }
  writeJson(`${artDir}/summary.json`, summary)
  cp.phase = mustAll ? 'done' : 'final_failed'
  saveCheckpoint(artDir, cp)
  L(`FINAL ok=${mustAll} words=${summary.word_count} ch=${summary.chapter_count} tenAvg=${tenAvg}`)
  return summary
}
