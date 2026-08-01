// Gate C·因果/关系/限知图谱：真实 UI → Hermes → MCP 审批 → SurrealDB/图谱/时间线回读。
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'
import { writeFile } from 'node:fs/promises'
import { APPROVAL_RUN_SETTLE_ATTEMPTS, isApprovedWriteFinalized } from './approval_run_wait.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE
const WORK = process.env.E2E_WORK
if (!BOOK || !WORK) throw new Error('图谱验收必须显式传入隔离作品 E2E_BOOK_TITLE 与 E2E_WORK')
const CASE = (process.env.E2E_CASE || Date.now().toString(36)).replace(/[^A-Za-z0-9_-]/g, '')
const CHARACTER_NAME = `许棹${CASE}`
const CHARACTER_OID = `role:${CHARACTER_NAME}`
const FACT_OID = `fact:潮纹船票归属_${CASE}`
const EVENT_OID = `ev:船票交付_${CASE}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const checkpoint = (label) => console.log(`GRAPH_SEMANTICS checkpoint=${label}`)

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}
async function waitFor(read, predicate, label, attempts = 60) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}:${JSON.stringify(value)}`)
}

const result = await withPage(async (page) => {
  // 验收要求浏览器控制台零意外错误。为 4xx/5xx 保留请求 URL，不能只留下
  // "Failed to load resource" 这种无法定位跨组件边界的表象。
  const failedResponses = []
  page.on('response', (response) => {
    if (response.status() >= 400) {
      failedResponses.push({ status: response.status(), url: response.url() })
    }
  })
  page.setDefaultNavigationTimeout(15000)
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded' })
  await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {})
  await page.getByText(BOOK, { exact: false }).first().click()
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  await ensureChiefVisible(page, { bookTitle: BOOK })

  async function runAndApprove(label, tool, input, read, predicate) {
    await ensureChiefVisible(page, { bookTitle: BOOK })
    const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
    await composer.fill(input)
    const createdPromise = page.waitForResponse(
      (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
      { timeout: 20000 },
    )
    await composer.press('Enter')
    const created = await createdPromise
    assert(created.ok(), `${label} Run 未受理:${created.status()}`)
    const body = await created.json()
    const runId = body.run_id || body.id
    assert(runId, `${label} 缺少 run_id`)
    let idleApprovalPolls = 0
    await waitFor(async () => {
      const decisions = await approveAllPending(page, { maxRounds: 4, settleMs: 500 })
      // 服务端 collector 可先于浏览器 EventSource 持久化 approval.requested。
      // 若当前页面没收到卡片，主动刷新并从持久 trace 恢复，仍由作者 UI 点击批准；
      // 禁止在脚本里直调 approval REST 伪造作者决议。
      if (decisions.approved + decisions.staleApproved === 0) {
        idleApprovalPolls += 1
        if (idleApprovalPolls % 3 === 0) {
          await page.reload({ waitUntil: 'domcontentloaded' })
          await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
          await ensureChiefVisible(page, { bookTitle: BOOK })
        }
      } else {
        idleApprovalPolls = 0
      }
      return json(`/ai/runs/${encodeURIComponent(runId)}/trace?work=${encodeURIComponent(WORK)}`)
        .catch(() => null)
    }, (trace) => isApprovedWriteFinalized(trace, tool), `${label}缺少 written 审计输出`, APPROVAL_RUN_SETTLE_ATTEMPTS)
    await waitFor(read, predicate, `${label}正典回读失败`)
    checkpoint(label)
    return runId
  }

  const characterRun = await runAndApprove(
    'character', 's3_add_character',
    `请在当前作品中仅调用一次 s3_add_character，新建角色「${CHARACTER_NAME}」，参数 oid="${CHARACTER_OID}",name="${CHARACTER_NAME}",appearance="总带盐霜的黑斗篷",personality_detail="沉稳而固执",surface_goal="救回失船者",deep_need="承认不能独自承担",fear="重演旧船难",importance="配角",first_appearance=1,work="${WORK}"。等待我批准，勿调用其他工具。`,
    () => json(`/characters/${encodeURIComponent(CHARACTER_NAME)}?work=${encodeURIComponent(WORK)}`),
    (row) => row?.name === CHARACTER_NAME,
  )
  const factRun = await runAndApprove(
    'fact', 's3_add_fact',
    `请在当前作品中仅调用一次 s3_add_fact，参数 oid="${FACT_OID}",entity="role:林雾",attribute="持有",value="潮纹船票",valid_from=1,secret=false,work="${WORK}"。等待我批准，勿调用其他工具。`,
    () => json(`/facts/${encodeURIComponent(FACT_OID.slice('fact:'.length))}?work=${encodeURIComponent(WORK)}`),
    (row) => row?.value === '潮纹船票' && row?.entity === 'role:林雾',
  )
  const eventRun = await runAndApprove(
    'event', 's3_add_event',
    `请在当前作品中仅调用一次 s3_add_event，参数 oid="${EVENT_OID}",etype="交出船票",valid_from=1,motivated_by_goal="让${CHARACTER_NAME}相信林雾愿意共同追查",participants=[{"role":"SUBJ","entity":"role:林雾"},{"role":"WITNESS","entity":"${CHARACTER_OID}"}],effects=[{"id":"${FACT_OID}"}],causal_root_reason="码头冷开场的独立场景根",narrative_position=1,work="${WORK}"。等待我批准，勿调用其他工具。`,
    () => json(`/events?chapter=1&work=${encodeURIComponent(WORK)}`),
    (rows) => rows.some((row) => row.id === EVENT_OID && row.goal?.includes(CHARACTER_NAME)),
  )
  const relationRun = await runAndApprove(
    'relation', 's3_add_character_relation',
    `请在当前作品中仅调用一次 s3_add_character_relation，参数 src_oid="role:林雾",dst_oid="${CHARACTER_OID}",relation="盟友",since_chapter=1,note="船票交付后形成互助同盟",work="${WORK}"。等待我批准，勿调用其他工具。`,
    () => json(`/character-relations?chapter=1&work=${encodeURIComponent(WORK)}`),
    // 关系 API 是读模型，按契约返回裸角色名；MCP 写参数仍必须使用 role: 前缀。
    (rows) => rows.some((row) => row.src === '林雾' && row.dst === CHARACTER_NAME && row.relation === '盟友'),
  )
  const knowledgeRun = await runAndApprove(
    'knowledge', 's3_record_knowledge',
    `请在当前作品中仅调用一次 s3_record_knowledge，参数 knower="${CHARACTER_OID}",proposition="${FACT_OID}",since_chapter=1,acquired_via="told",work="${WORK}"。等待我批准，勿调用其他工具。`,
    () => json(`/graph?focus=${encodeURIComponent(CHARACTER_OID)}&hop=1&work=${encodeURIComponent(WORK)}`),
    // 当前 /graph 的公开边类型字段是 rel；保留 type/kind 兼容旧读模型。
    (graph) => (graph?.edges || []).some((edge) => String(edge.rel || edge.type || edge.kind || '').includes('knows')),
  )

  const timeline = await json(`/timeline?ch_from=1&ch_to=1&work=${encodeURIComponent(WORK)}`)
  assert((timeline.items || []).some((item) => item.kind === 'event' && item.id === EVENT_OID),
    '时间线未出现经批准事件')
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '图谱', exact: true }).click()
  await page.waitForTimeout(500)
  await page.getByRole('button', { name: '时间线', exact: true }).click()
  await page.waitForTimeout(500)
  return { work: WORK, case: CASE, runIds: [characterRun, factRun, eventRun, relationRun, knowledgeRun], failedResponses }
})

const artifact = { ok: result.ok && result.errs.length === 0, ...result }
if (process.env.E2E_RESULT_FILE) await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify(artifact, null, 2))
if (!artifact.ok) {
  console.error('GRAPH_SEMANTICS_APPROVAL FAIL', JSON.stringify(result))
  process.exitCode = 1
}
console.log('GRAPH_SEMANTICS_APPROVAL OK', JSON.stringify(result))
