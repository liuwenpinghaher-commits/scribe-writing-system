// Gate C·单项图谱能力真实验收。E2E_GRAPH_KIND=fact|event|character_relation|knowledge。
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || 'GateC完整角色档案·ms2ogxwl'
const WORK = process.env.E2E_WORK || 'book_01888fac'
const kind = process.env.E2E_GRAPH_KIND || 'fact'
const CASE = (process.env.E2E_CASE || Date.now().toString(36)).replace(/[^A-Za-z0-9_-]/g, '')
const FACT_OID = `fact:潮纹船票归属_${CASE}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const assert = (condition, message) => { if (!condition) throw new Error(message) }

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}
async function waitFor(read, predicate, label, attempts = 45) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read().catch(() => null)
    if (predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}:${JSON.stringify(value)}`)
}

const configs = {
  fact: {
    tool: 's3_add_fact',
    input: `请在当前作品中仅调用一次 s3_add_fact，参数 oid="${FACT_OID}",entity="role:林雾",attribute="持有",value="潮纹船票",valid_from=1,secret=false,work="${WORK}"。等待我批准，勿调用其他工具。`,
    read: () => json(`/facts/${encodeURIComponent(FACT_OID.slice('fact:'.length))}?work=${encodeURIComponent(WORK)}`),
    valid: (row) => row?.entity === 'role:林雾' && row?.attribute === '持有' && row?.value === '潮纹船票',
  },
  event: {
    tool: 's3_add_event',
    input: `请在当前作品中仅调用一次 s3_add_event，参数 oid="ev:船票交付",etype="交出船票",valid_from=1,motivated_by_goal="让许棹相信林雾愿意共同追查",participants=[{"role":"SUBJ","entity":"role:林雾"},{"role":"WITNESS","entity":"role:许棹"}],effects=[{"id":"fact:潮纹船票归属"}],causal_root_reason="码头冷开场的独立场景根",narrative_position=1,work="${WORK}"。等待我批准，勿调用其他工具。`,
    read: () => json(`/events?chapter=1&work=${encodeURIComponent(WORK)}`),
    valid: (rows) => Array.isArray(rows) && rows.some((row) => row.id === 'ev:船票交付' && row.goal?.includes('许棹')),
  },
  character_relation: {
    tool: 's3_add_character_relation',
    input: `请在当前作品中仅调用一次 s3_add_character_relation，参数 src_oid="role:林雾",dst_oid="role:许棹",relation="盟友",since_chapter=1,note="船票交付后形成互助同盟",work="${WORK}"。等待我批准，勿调用其他工具。`,
    read: () => json(`/character-relations?chapter=1&work=${encodeURIComponent(WORK)}`),
    // 关系读模型返回裸角色名；写参数仍必须使用 role: 前缀。
    valid: (rows) => Array.isArray(rows) && rows.some((row) => row.src === '林雾' && row.dst === '许棹' && row.relation === '盟友'),
  },
  knowledge: {
    tool: 's3_record_knowledge',
    input: `请在当前作品中仅调用一次 s3_record_knowledge，参数 knower="role:许棹",proposition="fact:潮纹船票归属",since_chapter=1,acquired_via="told",work="${WORK}"。等待我批准，勿调用其他工具。`,
    read: () => json(`/graph?focus=${encodeURIComponent('role:许棹')}&hop=1&work=${encodeURIComponent(WORK)}`),
    valid: (graph) => (graph?.edges || []).some((edge) => String(edge.rel || edge.type || edge.kind || '').includes('knows')),
  },
}
const config = configs[kind]
if (!config) throw new Error(`E2E_GRAPH_KIND 必须是 ${Object.keys(configs).join('|')}`)

const result = await withPage(async (page) => {
  page.setDefaultNavigationTimeout(15000)
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded' })
  await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {})
  await page.getByText(BOOK, { exact: false }).first().click()
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await composer.fill(config.input)
  const createdPromise = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
    { timeout: 20000 },
  )
  await composer.press('Enter')
  const created = await createdPromise
  assert(created.ok(), `${kind} Run 未受理:${created.status()}`)
  const payload = await created.json()
  const runId = payload.run_id || payload.id
  assert(runId, `${kind} Run 缺少 run_id`)
  let idleApprovalPolls = 0
  await waitFor(async () => {
    const decisions = await approveAllPending(page, { maxRounds: 4, settleMs: 500 })
    // 服务端 collector 可能先于当前浏览器 EventSource 落库 approval.requested；刷新后
    // 仍必须通过作者 UI 的恢复卡点击批准，禁止用 REST 伪造决策。
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
    return config.read()
  }, config.valid, `${kind}正典回读失败`)
  const trace = await waitFor(
    () => json(`/ai/runs/${encodeURIComponent(runId)}/trace?work=${encodeURIComponent(WORK)}`),
    (value) => value?.status === 'completed' && value?.tool_outputs?.some((output) => output.tool === config.tool && output.result_status === 'written'),
    `${kind}缺少written审计输出`,
  )
  await page.reload({ waitUntil: 'domcontentloaded' })
  return { work: WORK, case: CASE, runId, tool: config.tool, status: trace.status }
})

if (!result.ok || result.errs.length) {
  console.error('GRAPH_TOOL_APPROVAL FAIL', JSON.stringify(result))
  process.exit(1)
}
console.log('GRAPH_TOOL_APPROVAL OK', JSON.stringify(result))
