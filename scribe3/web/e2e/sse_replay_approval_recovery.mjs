// 真实 SSE 断连恢复：浏览器收到待批卡后强制刷新，再由重新挂载的界面恢复并批准。
// 正典写入只能经页面主编 → Hermes/MCP → 作者点击批准；fetch 仅用于只读核验。
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible, resolveComposer, submitComposerWithDeadline } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { writeJsonArtifact } from './result_artifact.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const BOOK = process.env.E2E_BOOK_TITLE || `SSE重放恢复验收·${Date.now().toString(36)}`
const CASE = (process.env.E2E_CASE || Date.now().toString(36)).replace(/[^A-Za-z0-9_-]/g, '')
const NAME = `重放角色${CASE}`
const OID = `role:${NAME}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const assert = (value, message) => { if (!value) throw new Error(message) }
// 语义锚：审批请求的作者可见卡（approval-request-card）必须在刷新后重新出现。
const APPROVAL_REQUEST_CARD = 'approval-request-card'

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}

async function waitFor(read, predicate, label, attempts = 180) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (await predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}: ${JSON.stringify(value).slice(0, 600)}`)
}

const result = await withPage(async (page) => {
  const failedResponses = []
  const phases = []
  page.on('response', (response) => {
    if (response.status() >= 400) failedResponses.push({ status: response.status(), url: response.url() })
  })
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first().fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.getByTestId('four-col').waitFor({ state: 'attached', timeout: 20000 })
  const works = await json('/works')
  const work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
  assert(work, '无法解析隔离作品 work')
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = await resolveComposer(page, true, { bookTitle: BOOK })
  const createdPromise = page.waitForResponse((response) => (
    response.request().method() === 'POST' && /\/api\/ai\/runs(?:\?|$)/.test(response.url())
  ), { timeout: 30000 })
  await submitComposerWithDeadline(composer,
    `请只调用一次 s3_add_character，在作品 ${work} 新建角色，oid=${OID},name=${NAME},appearance=潮湿斗篷,personality_detail=谨慎, surface_goal=寻找失船者,deep_need=承认恐惧,fear=再次失去同伴,importance=配角,first_appearance=1。等待我批准，勿调用其他工具。`,
    { timeoutMs: 30000 },
  )
  const created = await createdPromise
  assert(created.ok(), `Run 创建失败: ${created.status()}`)
  const body = await created.json()
  const runId = body.run_id || body.id
  assert(runId, 'Run 响应缺少 id')
  const approve = page.getByTestId('run-approve').first()
  await approve.waitFor({ state: 'visible', timeout: 300000 })
  phases.push('approval_visible_before_disconnect')

  // 这里明确断开旧 EventSource。页面重载后必须从持久 Run 事件恢复待批卡，
  // 而非借用旧 React 内存中的 approval 对象。
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.getByTestId('four-col').waitFor({ state: 'attached', timeout: 30000 })
  await ensureChiefVisible(page, { bookTitle: BOOK })
  await page.getByTestId('run-approve').first().waitFor({ state: 'visible', timeout: 30000 })
  phases.push('approval_visible_after_sse_replay')

  const approvals = await approveAllPending(page, { maxRounds: 4, settleMs: 600 })
  assert(approvals.approved + approvals.staleApproved > 0, '刷新后页面未实际批准待批写入')
  const trace = await waitFor(
    () => json(`/ai/runs/${encodeURIComponent(runId)}/trace?work=${encodeURIComponent(work)}`),
    // 该 Hermes 版本对已批准且成功的 MCP 调用会如实标为 approved_unverified；
    // 不可把它误判成未完成。Run completed 加上下面的正典角色回读才构成验收完成。
    (value) => value?.status === 'completed',
    '刷新恢复后 Run 未完成写入',
  )
  const character = await waitFor(
    () => json(`/characters/${encodeURIComponent(NAME)}?work=${encodeURIComponent(work)}`),
    (value) => value?.name === NAME,
    '刷新恢复后正典未落库',
  )
  return { work, run_id: runId, phases, approvals, trace_status: trace?.status || null, character: character?.name || null, failedResponses }
})

const artifact = { ok: result.ok === true && result.errs.length === 0 && result.failedResponses?.length === 0, ...result }
if (process.env.E2E_RESULT_FILE) await writeJsonArtifact(process.env.E2E_RESULT_FILE, artifact)
if (!artifact.ok) {
  console.error('SSE_REPLAY_APPROVAL_RECOVERY FAIL', JSON.stringify(artifact))
  process.exitCode = 1
}
console.log('SSE_REPLAY_APPROVAL_RECOVERY', JSON.stringify(artifact))
