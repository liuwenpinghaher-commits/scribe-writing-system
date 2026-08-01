// 可靠性 Gate：真实 UI 流式生成 → 作者停止 → 部分稿提案 → 作者采用 → 刷新/Surreal 回读。
// 不用 REST 写正文；REST 仅用于确认作者的 UI 决定已持久化。
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { withPage } from './lib.mjs'
import { approveAllPending, chiefSay, ensureChiefVisible, resolveComposer, submitComposerWithDeadline } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import {
  captureStreamStopResult,
  settleObservedRequest,
  visibleGeneratedText,
  persistStreamStopResult,
} from './stream_stop_partial_recovery_result.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const BOOK = process.env.E2E_BOOK_TITLE || `流式停止恢复验收·${Date.now().toString(36)}`
const TITLE = '止流后仍可采用'
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const assert = (value, message) => { if (!value) throw new Error(message) }
const runIds = new Set()
const recordRun = (outcome) => {
  if (outcome?.run?.id) runIds.add(outcome.run.id)
  return outcome
}

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}

async function waitFor(read, predicate, label, attempts = 90) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (await predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}: ${String(value).slice(0, 600)}`)
}

async function addChapterThroughApproval(page, work) {
  const observedRuns = []
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const observed = recordRun(await chiefSay(page,
      `请只调用 s3_add_chapter，在作品 ${work} 新建第1章，title=${TITLE}；等待我批准，未获批准不得声称已落库。`,
      { bookTitle: BOOK, maxMs: 120000 },
    ))
    if (observed.run?.id) observedRuns.push(observed.run.id)
    try {
      const created = await waitFor(async () => {
        await approveAllPending(page, { maxRounds: 4, settleMs: 500 })
        const chapters = await json(`/chapters?work=${encodeURIComponent(work)}`)
        return (Array.isArray(chapters) ? chapters : chapters.chapters || [])
          .find((chapter) => chapter.seq === 1)
      }, Boolean, '审批建章未落库', 30)
      return created
    } catch (error) {
      if (attempt === 1) {
        throw new Error(`审批建章未落库；已审计 Run: ${observedRuns.join(',') || '无 Run id'}`)
      }
    }
  }
}

// 正文保存受 Gate A 工艺门保护。停止恢复旅程同样必须让作者经由网页主编
// 发起 MCP 写入、逐项批准，再只读回查；不能以 REST 造一个“可存稿”的裸书。
const gateARepairPrompts = {
  A1: '请仅用 s3_set_intent 补齐 reader_feeling=压抑中的清醒、emotional_arc=怀疑到承担、red_lines=不以作者旁白替人物裁定道德。需我审批。',
  A2: '请仅用 s3_add_character 登记两名完整角色：周岑(appearance=手背有旧烫伤,deep_need=确认失踪姐姐是否主动离开)与贺钟(appearance=左耳缺一角,deep_need=守住旧站档案)。需我审批。',
  A3: '请仅用 s3_add_world_rule 登记规则：北桥旧站的封存档案一旦被公开，相关证词必须在当夜失效。需我审批。',
  A4: '请仅调用一次 s3_add_character_relation，并精确传 src_oid=role:周岑、dst_oid=role:贺钟、relation=custom、since_chapter=1、note=互相试探且各自隐瞒关键证据。不得省略上述字段；work 参数将在本消息末尾给出。需我审批。',
  A5: '请仅用 s3_add_motif 登记母题 name=未署名的信 theme=真相与沉默的代价 echoes=封蜡/潮痕/未拆信封。需我审批。',
  A6: '请仅用 s3_plant_promise 埋伏笔 text=未署名信里的收件人会迫使周岑在公开与沉默之间选择 setup_chapter=1。需我审批。',
  A7: '请仅用 s3_plant_promise 埋伏笔 text=未署名信里的收件人会迫使周岑在公开与沉默之间选择 setup_chapter=1，使其可进入 chapter brief。需我审批。',
}

async function prepareCraftReadiness(page, work) {
  let gates = await json(`/craft-gates?work=${encodeURIComponent(work)}`)
  for (let round = 0; !gates.gate_a?.ok && round < 2; round += 1) {
    const blocking = [...new Set(gates.gate_a?.blocking || [])]
    for (const gateId of blocking) {
      const prompt = gateARepairPrompts[gateId]
      assert(prompt, `Gate A 缺少 ${gateId} 的 MCP 修复指令`)
      recordRun(await chiefSay(page,
        `${prompt} 目标作品 work=${work}，不得改动其他作品。`,
        { preferWrite: false, maxMs: 300000, bookTitle: BOOK },
      ))
      await approveAllPending(page)
    }
    gates = await json(`/craft-gates?work=${encodeURIComponent(work)}`)
  }
  assert(gates.gate_a?.ok, `Gate A 仍未通过: ${JSON.stringify(gates.gate_a?.blocking || [])}`)
}

async function selectChapterStage(page, stage) {
  await page.getByRole('button', { name: '手稿', exact: true }).click()
  const restoreDirectory = page.getByTestId('directory-restore-button')
  if (await restoreDirectory.isVisible().catch(() => false)) await restoreDirectory.click()
  await page.getByTestId('manuscript-directory').waitFor({ state: 'visible', timeout: 15000 })
  const chapter = page.getByRole('button', { name: new RegExp(`^1 ${TITLE}$`) }).first()
  await chapter.waitFor({ state: 'visible', timeout: 30000 })
  await chapter.click()
  const tab = page.getByRole('tab', { name: stage, exact: true })
  await tab.click()
  await page.waitForTimeout(700)
  assert(await tab.getAttribute('aria-selected') === 'true', `作者选择${stage}后阶段没有保持`)
}

// Gate B 是正文保存前的章节工艺门：结构、节拍、限知演绎都必须先经作者批准。
// 复用质量真人旅程中已经跑通的最小结构，只读 /craft-gates 用于确认，绝不直接写库。
const gateBRepairPrompts = {
  B1: '请仅用 s3_patch_chapter_plan 写入第1章 synopsis（至少100字）：周岑夜访北桥旧站，为确认失踪姐姐是否主动离开而带着未拆的无署名信；档案守门人贺钟知道封存档案的代价，却只允许她看见一页被抽走的目录。两人都不肯说破信封上的收件人，周岑在公开档案和保护姐姐之间必须作出不可逆选择。再写入至少3条 beats（推门发现封蜡异常、与贺钟对质且各自隐瞒证据、周岑决定暂不拆信并带走目录缺页）。需我审批。',
  // TokenPlan 对一次同时生成场景真相、角色范围和两份五层演绎会发生超长思考。
  // 拆成两次作者批准的同一 MCP 写入，仍由 Gate B 的只读回查决定是否通过。
  B3Scene: '请仅用一次 s3_patch_chapter_plan 为第1章写入 scene_truth 和 involved_characters：scene_truth 至少120字，明确周岑只看见信封封蜡的姐姐缩写并听到贺钟说“信不能拆”，贺钟则知道公开封存档案会使证词失效但没有告诉周岑；involved_characters 必须为 ["role:周岑","role:贺钟"]。不要写 deductions。需我审批。',
  B3Deductions: '请仅用一次 s3_patch_chapter_plan 为第1章写入 deductions，必须恰好覆盖 role:周岑 与 role:贺钟。每条 prose 都必须有五个标题：### 看到/听到、### 知道、### 以为(误读)、### 做了/说了、### 没察觉的；只能写该角色可知信息。不要改 scene_truth、involved_characters 或其他字段。需我审批。',
}

async function prepareChapterScaffold(page, work) {
  let gates = await json(`/craft-gates?seq=1&work=${encodeURIComponent(work)}`)
  for (let round = 0; !gates.gate_b?.ok && round < 2; round += 1) {
    const blocking = new Set(gates.gate_b?.blocking || [])
    const prompts = [
      (blocking.has('B1') || blocking.has('B2')) ? { stage: '大纲', text: gateBRepairPrompts.B1 } : null,
      (blocking.has('B3') || blocking.has('B4')) ? { stage: '演绎', text: gateBRepairPrompts.B3Scene } : null,
      blocking.has('B5') ? { stage: '演绎', text: gateBRepairPrompts.B3Deductions } : null,
    ].filter(Boolean)
    assert(prompts.length > 0, `Gate B 缺少 MCP 修复指令: ${JSON.stringify([...blocking])}`)
    for (const prompt of prompts) {
      await selectChapterStage(page, prompt.stage)
      checkpoint('gate-b-before-run', { stage: prompt.stage, blocking: [...blocking] })
      const observed = recordRun(await chiefSay(page,
        `${prompt.text} 目标作品 work=${work}，不得改动其他作品。`,
        { preferWrite: false, maxMs: 360000, bookTitle: BOOK },
      ))
      checkpoint('gate-b-after-run', { stage: prompt.stage, run_id: observed.run?.id || null })
      await approveAllPending(page)
    }
    gates = await json(`/craft-gates?seq=1&work=${encodeURIComponent(work)}`)
  }
  assert(gates.gate_b?.ok, `Gate B 仍未通过: ${JSON.stringify(gates.gate_b?.blocking || [])}`)
  await selectChapterStage(page, '正文')
}

const evidence = {
  chatRequests: [],
  writeResponses: [],
  failedResponses: [],
  work: null,
  reload: null,
}
const progress = { stage: 'init', at: new Date().toISOString() }

// 长程真实链路的运行态只记录阶段、Run ID 和 Gate 缺口，绝不记录提示词、正文或响应。
function checkpoint(stage, detail = {}) {
  progress.stage = stage
  progress.at = new Date().toISOString()
  Object.assign(progress, detail)
  const target = process.env.E2E_RESULT_FILE
  if (!target) return
  try {
    mkdirSync(dirname(target), { recursive: true })
    writeFileSync(target, JSON.stringify({
      ok: false, passed: false, in_progress: true,
      progress, run_ids: [...runIds], ...evidence,
    }, null, 2))
  } catch { /* 诊断落盘不能破坏真实作者路径 */ }
}
// 外部验收器可能在长推理期间发送 SIGTERM；必须留下已观察到的真实边界，
// 不能只剩一个没有 artifact 的退出码。
function persistTermination(signal) {
  const target = process.env.E2E_RESULT_FILE
  if (!target) return
  try {
    mkdirSync(dirname(target), { recursive: true })
    writeFileSync(target, JSON.stringify({
      ok: false, passed: false, err: `流式恢复验收被 ${signal} 终止`,
      terminated_by: signal, run_ids: [...runIds], ...evidence,
    }, null, 2))
  } catch { /* 保持原始终止语义 */ }
}
process.once('SIGTERM', () => { persistTermination('SIGTERM'); process.exit(143) })
process.once('SIGINT', () => { persistTermination('SIGINT'); process.exit(130) })
const result = await captureStreamStopResult(async () => {
  const raw = await withPage(async (page) => {
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname.replace(/^\/api/, '')
    if (request.method() === 'POST' && path.startsWith('/chat/')) evidence.chatRequests.push(path)
  })
  page.on('response', (response) => {
    const path = new URL(response.url()).pathname.replace(/^\/api/, '')
    if (response.status() >= 400) evidence.failedResponses.push({ path, status: response.status() })
    if (path === '/chat/write') evidence.writeResponses.push(response.status())
  })
  // 流式写作页常驻 SSE/HMR，不能把 networkidle 当作首屏可操作的前置条件。
  // 后续对建书控件及四栏壳的显式等待才构成真实 UI 就绪证据。
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first().fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.getByTestId('four-col').waitFor({ state: 'attached', timeout: 20000 })
  const works = await json('/works')
  const work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
  assert(work, '无法解析隔离作品 work')
  evidence.work = work
  await addChapterThroughApproval(page, work)
  await prepareCraftReadiness(page, work)
  await prepareChapterScaffold(page, work)
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = await resolveComposer(page, true, { bookTitle: BOOK })
  const requestSeen = settleObservedRequest(page.waitForRequest((request) => (
    request.method() === 'POST' && /\/chat\/write(?:\?|$)/.test(request.url())
  ), { timeout: 30000 }))
  await submitComposerWithDeadline(
    composer,
    '请写一篇约700字的原创港口悬疑正文，从人物在退潮的黑水边发现一张无署名船票开始。先持续输出正文，不要解释写作计划。',
    { timeoutMs: 30000 },
  )
  const observedWrite = await requestSeen
  assert(observedWrite.request, `正文发送未触发 /chat/write：${observedWrite.error || evidence.chatRequests.join(',') || '未观察到聊天请求'}`)
  await page.getByRole('button', { name: '停止生成', exact: true }).waitFor({ state: 'visible', timeout: 30000 })
  await waitFor(
    async () => visibleGeneratedText({
      chatText: await page.locator('.prose-chat').last().innerText().catch(() => ''),
      proposalText: await page.getByTestId('draft-proposal-text').innerText().catch(() => ''),
    }),
    (text) => String(text).trim().length >= 80,
    '停止前未收到可见 SSE 文本',
    // TokenPlan/Qwen 会先完成不可见的强思考；验收必须等到作者实际看见首字后
    // 才测试“停止后保留部分稿”，90 秒不能区分正常思考与真实流故障。
    360,
  )
  await page.getByRole('button', { name: '停止生成', exact: true }).click()
  const partial = await waitFor(
    () => page.getByTestId('draft-proposal-text').innerText().catch(() => ''),
    (text) => String(text).trim().length >= 80,
    '停止后未恢复为作者可见的部分稿提案',
    30,
  )
  await page.getByTestId('draft-accept').click()
  const stored = await waitFor(
    () => json(`/chapter?seq=1&work=${encodeURIComponent(work)}`),
    (chapterRow) => String(chapterRow.prose || '').trim().length >= 80,
    '作者采用部分稿后正文未持久化',
    30,
  )
  const storedText = String(stored.prose || '').trim()
  assert(storedText.slice(0, 32) === String(partial).trim().slice(0, 32), '持久化正文不是作者所见的部分稿')

  await page.reload({ waitUntil: 'domcontentloaded' })
  // App 会先以作品库的初始态挂载，再异步从 localStorage 恢复当前书；不能在
  // domcontentloaded 的瞬间把这段正常恢复窗口误判成“已退回作品库”。
  await page.getByTestId('four-col').waitFor({ state: 'attached', timeout: 5000 }).catch(() => {})
  const stillInBook = await page.getByTestId('four-col').count()
  evidence.reload = { beforeOpenFour: stillInBook, cardVisible: false, opened: false, afterOpenFour: null }
  try {
    if (!stillInBook) {
      const opener = page.locator(`[data-work-slug="${work}"]`)
      if (await opener.isVisible().catch(() => false)) {
        evidence.reload.cardVisible = true
        await opener.click()
        evidence.reload.opened = true
      } else {
        // 初次 isVisible 可能早于 Library 的 /works 回读；优先等待不可变 slug，
        // 仅当现行 UI 没有该属性时才退回标题，避免同名书被打开。
        try {
          await opener.waitFor({ state: 'visible', timeout: 30000 })
          evidence.reload.cardVisible = true
          await opener.click()
          evidence.reload.opened = true
        } catch {
          const byTitle = page.getByRole('button', { name: new RegExp(BOOK.slice(0, 12)) }).first()
          await byTitle.waitFor({ state: 'visible', timeout: 30000 })
          await byTitle.click()
          evidence.reload.opened = true
        }
      }
      // 打开作品后还会异步拉项目树与 ContextSnapshot；慢的真实 TokenPlan 验收环境下
      // 20 秒不足以区分“仍在恢复”与“恢复失败”。
      await page.getByTestId('four-col').waitFor({ state: 'attached', timeout: 45000 })
    }
  } finally {
    evidence.reload.afterOpenFour = await page.getByTestId('four-col').count().catch(() => 0)
  }
  return {
    work,
    run_ids: [...runIds],
    partial_length: String(partial).trim().length,
    stored_length: storedText.length,
  }
  })
  return raw
}, evidence)

await persistStreamStopResult(process.env.E2E_RESULT_FILE, result)
if (!result.passed) {
  console.error('STREAM_STOP_PARTIAL_RECOVERY FAIL', JSON.stringify(result))
  process.exitCode = 1
} else {
  console.log('STREAM_STOP_PARTIAL_RECOVERY OK', JSON.stringify(result))
}
