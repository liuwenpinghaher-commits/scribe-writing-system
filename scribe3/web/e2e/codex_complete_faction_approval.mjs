// Gate C·势力完整档案：真实 UI → Hermes → MCP 审批 → SurrealDB 回读。
// 验证 faction 的全部活跃字段与嵌套字段；不使用 REST/脚本写入正典。
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { deepStrictEqual } from 'node:assert'
import { writeFile } from 'node:fs/promises'
import { isCompletedWrittenTrace } from './full_author_acceptance_result.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || `GateC完整势力档案·${Date.now().toString(36)}`
const FACTION = '潮汐会'
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function assertEqual(actual, expectedValue, message) {
  try {
    deepStrictEqual(actual, expectedValue)
  } catch {
    throw new Error(`${message}:${JSON.stringify(actual)}`)
  }
}

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}

async function waitFor(read, predicate, label, attempts = 80) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}: ${JSON.stringify(value)}`)
}

const expected = {
  name: FACTION,
  status: 'active',
  ideology: '以失踪者的名字约束活人与权力，拒绝用任何弱者交换城镇安全。',
  leader: '林雾',
  known_members: ['林雾', '许棹', '沈灯'],
  public_face: '码头互助会，负责潮汛时救援失船者并登记失踪人口。',
  first_mention_chapter: 1,
  artifact_operation: '以刻有潮纹的旧船票传递求救信号和集会地点。',
  external_manipulation: '有人借救援名单筛选可被献给潮神的替身。',
  acceleration_methods: '每次大潮前散布失踪谣言，逼迫居民交出家人名单。',
  origin: '三年前盐场失踪者的遗属秘密结成此会。',
  internal_factions: [
    { name: '岸灯组', claim: '公开救援优先', representative: '许棹', power_share: '55%' },
    { name: '沉钟组', claim: '先追查失踪案', representative: '林雾', power_share: '45%' },
  ],
  structure: { type: '双头', core_size: 2, decision_mechanism: '双组共识后表决', succession: '两组各推一人并获全会确认' },
  key_figures: [
    { name: '林雾', generation: 1, fragment_decay_rate: '缓慢', status: 'active', known_abilities: '辨认潮声' },
    { name: '许棹', generation: 1, fragment_decay_rate: '无', status: 'active', known_abilities: '夜航救援' },
  ],
  artifacts: [
    { artifact_name: '潮纹船票', artifact_type: '联络凭证', current_power_level: '低', decay_rate: '无', last_transfer_chapter: 1 },
    { artifact_name: '缺角航图', artifact_type: '水域档案', current_power_level: '中', decay_rate: '缓慢', last_transfer_chapter: 1 },
  ],
  scale: '约三十名固定成员与百余名互助居民',
  recruitment: '由两名成员担保，并先参与一次夜间救援。',
  symbols: '一盏罩着蓝纸的岸灯',
  motto: '潮退以后，名字还在。',
  goals: [
    { phase: '近期', target: '找回盐场失踪者名单', status: 'ongoing' },
    { phase: '中期', target: '阻断替身献祭', status: 'planned' },
  ],
  world_rule_affinity: [
    { rule_name: '潮汐记忆', affinity_type: '利用', note: '借潮声追踪失踪者' },
    { rule_name: '献祭代价', affinity_type: '对抗', note: '拒绝以替身换平安' },
  ],
  aliases: ['蓝灯会', '岸灯人'],
  timeline: [{ chapter: 1, event: '成立救援互助会' }, { chapter: 2, event: '发现名单被篡改' }],
  headquarters: '废弃盐仓东侧的旧引航塔',
  communication: '潮纹船票、灯号与渡口账簿夹页。',
  rituals: '每次大潮前点一盏岸灯，逐个念出失踪者名字。',
  secret_agenda: '查出借潮神之名献祭者，并把证据交给所有遗属。',
}

const result = await withPage(async (page) => {
  page.setDefaultNavigationTimeout(15000)
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded' })
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {})
  const title = page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first()
  await title.fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })

  const works = await json('/works')
  const work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
  assert(work, '无法解析隔离验收作品 work')
  await ensureChiefVisible(page, { bookTitle: BOOK })

  const fields = JSON.stringify({
    ...expected,
    artifact_operation_secret: true,
    external_manipulation_secret: true,
    acceleration_methods_secret: true,
    origin_secret: true,
    secret_agenda_secret: true,
    work,
  })
  const prompt = [
    `请在当前作品中仅调用一次 s3_add_faction，新建势力「${FACTION}」。`,
    `全部参数必须严格使用以下 JSON：${fields}`,
    '等待我在审批卡点击批准；未获批准不得声称已落库，也不得调用其他工具。',
  ].join('\n')
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await composer.fill(prompt)
  const runCreated = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
    { timeout: 20000 },
  )
  await composer.press('Enter')
  const created = await runCreated
  assert(created.ok(), `势力 Run 未被服务端受理:${created.status()}`)
  const run = await created.json()
  const runId = run.run_id || run.id
  assert(runId, '势力 Run 缺少 run_id')

  const row = await waitFor(async () => {
    await approveAllPending(page, { maxRounds: 4, settleMs: 500 })
    try { return await json(`/factions/${encodeURIComponent(FACTION)}?work=${encodeURIComponent(work)}&reveal_secret=true`) }
    catch { return null }
  }, Boolean, '完整势力档案未在作者批准后回读')

  for (const [key, value] of Object.entries(expected)) {
    assertEqual(row[key], value, `势力字段 ${key} 回读不一致`)
  }
  for (const key of ['artifact_operation_secret', 'external_manipulation_secret', 'acceleration_methods_secret', 'origin_secret', 'secret_agenda_secret']) {
    assert(row[key] === true, `势力私密标记 ${key} 未回读为 true`)
  }

  const publicRow = await json(`/factions/${encodeURIComponent(FACTION)}?work=${encodeURIComponent(work)}`)
  for (const key of ['artifact_operation', 'external_manipulation', 'acceleration_methods', 'origin', 'secret_agenda']) {
    assert(publicRow[key] === '🔒 私密', `公共视图泄露 ${key}:${JSON.stringify(publicRow[key])}`)
  }

  const trace = await waitFor(
    () => json(`/ai/runs/${encodeURIComponent(runId)}/trace?work=${encodeURIComponent(work)}`),
    (value) => isCompletedWrittenTrace(value, 's3_add_faction'),
    '势力 Run 未形成已审计的 written 工具输出',
  )

  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  const refreshed = await json(`/factions/${encodeURIComponent(FACTION)}?work=${encodeURIComponent(work)}&reveal_secret=true`)
  assert(refreshed.motto === expected.motto && refreshed.structure?.core_size === 2,
    '刷新后势力完整档案未保持')
  return { work, runId, status: trace.status }
})

const artifact = { ok: result.ok && result.errs.length === 0, ...result }
if (process.env.E2E_RESULT_FILE) await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify(artifact, null, 2))
if (!artifact.ok) {
  console.error('CODEX_COMPLETE_FACTION_APPROVAL FAIL', JSON.stringify(result))
  process.exitCode = 1
}
console.log('CODEX_COMPLETE_FACTION_APPROVAL OK', JSON.stringify(result))
