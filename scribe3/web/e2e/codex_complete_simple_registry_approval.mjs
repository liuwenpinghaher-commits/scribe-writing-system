// Gate C·物件/术语/世界规则：真实 UI → Hermes → MCP 审批 → 正典回读。
// 用 E2E_KIND=item|term|world_rule 逐类运行；不走 REST/脚本写入。
import { deepStrictEqual } from 'node:assert'
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { writeFile } from 'node:fs/promises'
import { captureJourneyResult } from './result_artifact.mjs'
import { isCompletedWrittenTrace } from './full_author_acceptance_result.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const kind = process.env.E2E_KIND || 'item'
const configs = {
  item: {
    label: '物件', tool: 's3_add_item', endpoint: '/items', name: '潮纹船票',
    fields: {
      name: '潮纹船票', category: '联络凭证', description: '一张边缘磨损的旧船票，潮纹会在夜里泛蓝。',
      symbolic_state: 'active', current_owner: '林雾', first_chapter: 1,
      special_properties: ['可在涨潮前显出灯号', '可夹入渡口账簿'],
    },
  },
  term: {
    label: '术语', tool: 's3_add_term', endpoint: '/terms', name: '潮汐记忆',
    fields: {
      name: '潮汐记忆', category: '地方传说', definition: '涨潮时会返还被海水记住的声音与片段，但无法返还失去的人。',
      aliases: ['回潮声', '蓝潮旧闻'], first_mention_chapter: 1,
    },
  },
  world_rule: {
    label: '世界规则', tool: 's3_add_world_rule', endpoint: '/world-rules', name: '潮声回显',
    fields: {
      name: '潮声回显', category: 'magic', source: '盐场旧井与近海潮汐的共振',
      cost: '每次借潮声追问失踪者，提问者都会遗忘一段与亲人有关的日常记忆。', scope: 'regional',
      established_chapter: 1, limitations: ['只在大潮前后一小时生效', '同一问题只能追问一次'],
      exceptions: ['携带潮纹船票者可多听见一个模糊名字'], capabilities: ['回放失踪者最后听见的一句声音'],
      note: '规则必须以失去具体记忆作为可见代价，不能成为万能侦查工具。',
    },
  },
}
const config = configs[kind]
if (!config) throw new Error(`E2E_KIND 必须是 ${Object.keys(configs).join('|')}`)
const BOOK = process.env.E2E_BOOK_TITLE || `GateC完整${config.label}·${Date.now().toString(36)}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function assert(condition, message) {
  if (!condition) throw new Error(message)
}
function assertEqual(actual, expected, message) {
  try { deepStrictEqual(actual, expected) } catch { throw new Error(`${message}:${JSON.stringify(actual)}`) }
}
async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}
async function waitFor(read, predicate, label, attempts = 45) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}:${JSON.stringify(value)}`)
}

const result = await captureJourneyResult(() => withPage(async (page) => {
  page.setDefaultNavigationTimeout(15000)
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded' })
  await page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {})
  const title = page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first()
  await title.fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  const works = await json('/works')
  const work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
  assert(work, '无法解析隔离验收作品 work')

  await ensureChiefVisible(page, { bookTitle: BOOK })
  const prompt = [
    `请在当前作品中仅调用一次 ${config.tool}，新建${config.label}「${config.name}」。`,
    `全部参数必须严格使用以下 JSON：${JSON.stringify({ ...config.fields, work })}`,
    '等待我在审批卡点击批准；未获批准不得声称已落库，也不得调用其他工具。',
  ].join('\n')
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await composer.fill(prompt)
  const createdPromise = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
    { timeout: 20000 },
  )
  await composer.press('Enter')
  const created = await createdPromise
  assert(created.ok(), `${config.label} Run 未被服务端受理:${created.status()}`)
  const createdBody = await created.json()
  const runId = createdBody.run_id || createdBody.id
  assert(runId, `${config.label} Run 缺少 run_id`)

  const row = await waitFor(async () => {
    await approveAllPending(page, { maxRounds: 4, settleMs: 500 })
    try { return await json(`${config.endpoint}/${encodeURIComponent(config.name)}?work=${encodeURIComponent(work)}`) }
    catch { return null }
  }, Boolean, `${config.label}未在批准后回读`)
  for (const [key, value] of Object.entries(config.fields)) assertEqual(row[key], value, `${config.label}字段${key}回读不一致`)

  const trace = await waitFor(
    () => json(`/ai/runs/${encodeURIComponent(runId)}/trace?work=${encodeURIComponent(work)}`),
    (value) => isCompletedWrittenTrace(value, config.tool),
    `${config.label} Run 未形成 written 审计输出`,
  )
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  const afterRefresh = await json(`${config.endpoint}/${encodeURIComponent(config.name)}?work=${encodeURIComponent(work)}`)
  assertEqual(afterRefresh.name, config.name, `${config.label}刷新后丢失`)
  return { work, runId, tool: config.tool, status: trace.status }
}))

const artifact = { ok: result.ok && result.errs.length === 0, ...result }
if (process.env.E2E_RESULT_FILE) await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify(artifact, null, 2))
if (!artifact.ok) {
  console.error('CODEX_COMPLETE_SIMPLE_REGISTRY_APPROVAL FAIL', JSON.stringify(result))
  process.exitCode = 1
}
console.log('CODEX_COMPLETE_SIMPLE_REGISTRY_APPROVAL OK', JSON.stringify(result))
