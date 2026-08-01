// 真实并发审批验收：两个独立浏览器页面同时点击同一 Hermes 待批卡。
// 写入仅走页面 → Hermes/MCP → 作者批准；fetch 只用于验收后的 GET 回查。
import { chromium } from 'playwright'
import { closeBrowserWithin } from './lib.mjs'
import { ensureChiefVisible, ensureInBook, resolveComposer, submitComposerWithDeadline } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { writeJsonArtifact } from './result_artifact.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const BOOK = process.env.E2E_BOOK_TITLE || `并发审批验收·${Date.now().toString(36)}`
const CASE = (process.env.E2E_CASE || Date.now().toString(36)).replace(/[^A-Za-z0-9_-]/g, '')
const NAME = `并发角色${CASE}`
const OID = `role:${NAME}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const assert = (value, message) => { if (!value) throw new Error(message) }

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
  throw new Error(`${label}: ${JSON.stringify(value).slice(0, 700)}`)
}

function workRows(payload) {
  return Array.isArray(payload) ? payload : (payload?.works || [])
}

function characterRows(payload) {
  return Array.isArray(payload) ? payload : (payload?.characters || [])
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const peer = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errs = []
const approvalResponses = []
const approvalResultReads = []
for (const current of [page, peer]) {
  current.on('pageerror', (error) => errs.push(`PAGEERR ${error.message}`))
  current.on('console', (message) => {
    if (message.type() === 'error' && !/ERR_CONNECTION_CLOSED|favicon/.test(message.text())) {
      errs.push(`CONSOLE ${message.text().slice(0, 160)}`)
    }
  })
  current.on('response', (response) => {
    if (response.request().method() === 'POST' && /\/api\/ai\/runs\/[^/]+\/approval(?:\?|$)/.test(response.url())) {
      const status = response.status()
      approvalResponses.push(status)
      approvalResultReads.push(response.json()
        .then((body) => ({ status, body }))
        .catch(() => ({ status, body: null })))
    }
  })
}

let artifact
try {
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first().fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.getByTestId('four-col').waitFor({ state: 'attached', timeout: 20000 })
  const work = resolveWorkSlugByExactTitle(workRows(await json('/works')), BOOK)
  assert(work, '无法解析隔离作品 work')

  await peer.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await ensureInBook(peer, BOOK)
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = await resolveComposer(page, false, { bookTitle: BOOK })
  const createdPromise = page.waitForResponse((response) => (
    response.request().method() === 'POST' && /\/api\/ai\/runs(?:\?|$)/.test(response.url())
  ), { timeout: 30000 })
  await submitComposerWithDeadline(composer,
    `请只调用一次 s3_add_character，在作品 ${work} 新建角色，oid=${OID},name=${NAME},appearance=带雨水的黑斗篷,personality_detail=谨慎克制,surface_goal=找回失船者,deep_need=承认恐惧,fear=再失去同伴,importance=配角,first_appearance=1。等待我批准，勿调用其他工具。`,
    { timeoutMs: 30000 },
  )
  const created = await createdPromise
  assert(created.ok(), `Run 创建失败: ${created.status()}`)
  const createdBody = await created.json()
  const runId = createdBody.run_id || createdBody.id
  assert(runId, 'Run 响应缺少 id')

  const approve = page.getByTestId('run-approve').first()
  await approve.waitFor({ state: 'visible', timeout: 300000 })
  // peer 在 Run 创建前已挂载，首次 pending-approvals 拉取为空；刷新触发持久审计链的重放。
  await peer.reload({ waitUntil: 'domcontentloaded' })
  await ensureChiefVisible(peer, { bookTitle: BOOK })
  const approvePeer = peer.getByTestId('run-approve').first()
  await approvePeer.waitFor({ state: 'visible', timeout: 30000 })

  // 两个独立页面在同一事件循环 tick 发送作者点击，验证网关/前端不会双写或双报成功。
  await Promise.all([
    approve.click(),
    approvePeer.click(),
  ])
  await waitFor(
    () => json(`/ai/runs/${encodeURIComponent(runId)}/trace?work=${encodeURIComponent(work)}`),
    (trace) => trace?.status === 'completed',
    '并发审批后 Run 未完成',
  )
  const canonical = await waitFor(
    () => json(`/entities?work=${encodeURIComponent(work)}`),
    (rows) => characterRows(rows).some((row) => row?.name === NAME),
    '并发审批后角色正典未落库',
  )
  const canonicalCount = characterRows(canonical).filter((row) => row?.name === NAME).length
  assert(canonicalCount === 1, `并发审批产生重复正典:${canonicalCount}`)
  const character = await json(`/characters/${encodeURIComponent(NAME)}?work=${encodeURIComponent(work)}`)
  assert(character?.name === NAME, '角色单体正典回读失败')
  await waitFor(
    async () => approvalResponses.length,
    (count) => count >= 2,
    '未捕获两个页面的审批响应',
    30,
  )
  const approvalResults = await Promise.all(approvalResultReads)
  const replayed = approvalResults.filter((result) => result.body?.already_resolved === true)
  const firstDecision = approvalResults.filter((result) => result.body?.already_resolved !== true)
  assert(replayed.length === 1, `并发重放语义错误:${JSON.stringify(approvalResults)}`)
  assert(firstDecision.length === 1 && firstDecision[0].status >= 200 && firstDecision[0].status < 300,
    `并发审批没有唯一首次写入:${JSON.stringify(approvalResults)}`)
  const peerError = await peer.locator('[data-testid="run-approve"]').count().catch(() => 0)
  artifact = {
    ok: errs.length === 0,
    errs,
    work,
    run_id: runId,
    approval_responses: approvalResults,
    canonical_count: canonicalCount,
    character: character?.name || null,
    pending_approval_controls_after_race: peerError,
  }
} catch (error) {
  artifact = { ok: false, errs, error: error.message, approval_responses: approvalResponses }
} finally {
  const closed = await closeBrowserWithin(browser)
  if (!closed.closed) {
    artifact ||= { ok: false, errs, approval_responses }
    artifact.ok = false
    artifact.errs.push('BROWSER_CLOSE_TIMEOUT')
  }
}

if (process.env.E2E_RESULT_FILE) await writeJsonArtifact(process.env.E2E_RESULT_FILE, artifact)
if (!artifact.ok) {
  console.error('CONCURRENT_APPROVAL_CONFLICT FAIL', JSON.stringify(artifact))
  process.exitCode = 1
}
console.log('CONCURRENT_APPROVAL_CONFLICT', JSON.stringify(artifact))
