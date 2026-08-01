// Gate C·角色完整档案：真实 UI → Hermes → MCP 审批 → SurrealDB 回读。
// 不使用 REST 写入或预置数据库；所有正典变化必须来自作者在 UI 中批准的工具调用。
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { writeFile } from 'node:fs/promises'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || `GateC完整角色档案·${Date.now().toString(36)}`
const CHARACTER = '林雾'
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const checkpoint = (label) => console.log(`GATE_C_PROFILE checkpoint=${label}`)

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}

// Hermes 首轮 tool_search + tool_describe 后才会请求写入审批；实测该阶段可超过 40 秒。
// 这里的等待覆盖“真实审批卡出现→作者点击→Surreal 回读”的完整链，不是放宽业务断言。
async function waitFor(read, predicate, label, attempts = 180) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (predicate(value)) return value
    await sleep(1000)
  }
  throw new Error(`${label}: ${JSON.stringify(value)}`)
}

async function approvePendingWithRecovery(page, idlePolls) {
  const decisions = await approveAllPending(page, { maxRounds: 5, settleMs: 800 })
  // 刚提交的 Run 仍在建立 SSE/首轮工具调用时不能每 3 秒强制刷新：这会取消仍健康的
  // 浏览器流并制造 ERR_NETWORK_IO_SUSPENDED 假失败。超过 15 秒仍没卡时才验收恢复路径。
  if (decisions.approved + decisions.staleApproved !== 0 || idlePolls < 15 || idlePolls % 15 !== 0) return
  // collector 可能先持久化审批而当前 EventSource 没拿到卡；刷新后仍由 UI 点击，
  // 不得借 approval REST 绕过作者决策。
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  await ensureChiefVisible(page, { bookTitle: BOOK })
}

let observedWork = null
const observedRunIds = []

const result = await withPage(async (page) => {
  // 主编、HMR 与上下文 SSE 会保持连接；以具体首屏控件确认可操作，不能等待永远
  // 不会出现的 networkidle。
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded' })
  const title = page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first()
  await title.fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })

  const works = await json('/works')
  const work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
  assert(work, '无法解析 Gate C 隔离作品')
  observedWork = work
  await ensureChiefVisible(page, { bookTitle: BOOK })

  const prompt = [
    `请在作品 ${work} 中新建角色「${CHARACTER}」，这是一次完整档案写入，必须调用一次 s3_add_character 并带上以下全部字段，然后等待我审批。`,
    'oid="role:林雾"，name="林雾"，aliases=["阿雾"]，appearance="雨衣袖口磨白，左手总攥着潮湿的船票"，personality_detail="谨慎、擅长观察，却会在他人受困时冒险"，personality_tags=["谨慎","倔强"]，backstory="她曾在盐场失踪三日，只记得潮声替她叫过名字"，backstory_secret=true，surface_goal="找到失踪的姐姐"，deep_need="承认自己也需要他人的帮助"，fear="再次被遗弃在涨潮的堤岸"，internal_conflict="独自追查姐姐与向同伴求援之间的拉扯"，abilities=["辨认潮声","修补旧船灯"]，weaknesses=["惧怕深水","不肯求助"]，importance="主角"，first_appearance=1。',
    '新书无需重复建角色。未获批准不得声称已落库；不要改写或省略任何字段。',
  ].join('\n')
  // 此处验收的是“主编发起 MCP 写入并由作者批准”，不是自然语言回复是否停止流式输出。
  // chiefSay 会为对话质量测试等待回复稳定，最长 8 分钟；把它用于本测试会令已经落库的
  // 审批路径假性卡住。仍经真实右栏输入发送，随后由下方轮询真实审批卡与正典回读。
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await composer.fill(prompt)
  // 先锁定真实浏览器的 POST，再等待服务端创建 Run；否则在网关创建阶段阻塞时，
  // 40 秒后的“角色未回读”只会掩盖真正的故障边界。
  const runRequestSeen = page.waitForRequest(
    (request) => /\/api\/ai\/runs(?:\?|$)/.test(request.url())
      && request.method() === 'POST',
    { timeout: 20000 },
  )
  const runCreated = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url())
      && response.request().method() === 'POST',
    { timeout: 90000 },
  )
  await composer.press('Enter')
  await runRequestSeen
  const createResponse = await runCreated
  assert(createResponse.ok(), `角色档案 Run 未被服务端受理:${createResponse.status()} ${await createResponse.text()}`)
  const profileRun = await createResponse.json()
  const profileRunId = profileRun.run_id || profileRun.id
  assert(profileRunId, '角色档案 Run 缺少 run_id')
  observedRunIds.push(profileRunId)
  checkpoint('chief-submitted')

  let characterPolls = 0
  const character = await waitFor(async () => {
    characterPolls += 1
    await approvePendingWithRecovery(page, characterPolls)
    const rows = await json(`/entities?work=${encodeURIComponent(work)}`)
    return rows.find((row) => row.name === CHARACTER)
  }, Boolean, '批准后完整角色档案未回读')
  checkpoint('public-readback')

  // 公共设定列表必须掩码私密前史；这既是 UI 刷新验收的一部分，也是防止
  // "全字段回读" 测试反过来要求服务端泄露私密的边界。原值只从作者显式解锁的
  // 单条详情读接口验收，且该请求只读、不会绕过 MCP 写入边界。
  const expected = {
    aliases: ['阿雾'], appearance: '雨衣袖口磨白，左手总攥着潮湿的船票',
    personality_detail: '谨慎、擅长观察，却会在他人受困时冒险', personality_tags: ['谨慎', '倔强'],
    backstory_secret: true,
    surface_goal: '找到失踪的姐姐', deep_need: '承认自己也需要他人的帮助',
    fear: '再次被遗弃在涨潮的堤岸', internal_conflict: '独自追查姐姐与向同伴求援之间的拉扯',
    abilities: ['辨认潮声', '修补旧船灯'], weaknesses: ['惧怕深水', '不肯求助'],
    importance: 'protagonist', first_appearance: 1,
  }
  for (const [key, value] of Object.entries(expected)) {
    assert(JSON.stringify(character[key]) === JSON.stringify(value),
      `角色字段 ${key} 回读不一致: ${JSON.stringify(character[key])}`)
  }
  assert(character.backstory === '🔒 私密', `私密前史在公共列表中泄露: ${JSON.stringify(character.backstory)}`)

  const unlocked = await json(`/characters/${encodeURIComponent(CHARACTER)}?work=${encodeURIComponent(work)}&reveal_secret=true`)
  assert(unlocked.backstory === '她曾在盐场失踪三日，只记得潮声替她叫过名字',
    `作者解锁后角色前史回读不一致: ${JSON.stringify(unlocked.backstory)}`)
  checkpoint('unlocked-readback')

  await page.reload({ waitUntil: 'domcontentloaded' })
  checkpoint('reloaded')
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  const afterRefresh = (await json(`/entities?work=${encodeURIComponent(work)}`))
    .find((row) => row.name === CHARACTER)
  assert(afterRefresh?.backstory === '🔒 私密', '刷新后私密角色前史未保持掩码')
  assert(afterRefresh?.abilities?.includes('修补旧船灯'), '刷新后角色能力未保留')
  checkpoint('refresh-readback')

  // Gate C 不能停在“字段已经存在”。再经真实 UI 建章、进入草稿阶段主编对话生成一轮，
  // 以 assistant 留痕中的 Context Manifest 绑定证明生产写作链实际完成了上下文编译。
  const chapterTitle = '设定消费章'
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const chapterComposer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await chapterComposer.fill(
    `请仅调用 s3_add_chapter，在作品 ${work} 新建第1章，title=${chapterTitle}；等待我批准，未获批准不得声称已落库。`,
  )
  const chapterRunCreated = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url())
      && response.request().method() === 'POST',
    { timeout: 20000 },
  )
  await chapterComposer.press('Enter')
  const chapterRunResponse = await chapterRunCreated
  assert(chapterRunResponse.ok(), `新建章节 Run 未被服务端受理:${chapterRunResponse.status()}`)
  const chapterRun = await chapterRunResponse.json()
  const chapterRunId = chapterRun.run_id || chapterRun.id
  assert(chapterRunId, '新建章节 Run 缺少 run_id')
  observedRunIds.push(chapterRunId)
  let chapterPolls = 0
  const chapters = await waitFor(async () => {
    chapterPolls += 1
    await approvePendingWithRecovery(page, chapterPolls)
    return json(`/chapters?work=${encodeURIComponent(work)}`)
  }, (rows) => (Array.isArray(rows) ? rows : rows.chapters || [])
    .some((row) => row.title === chapterTitle), '设定消费章未落库', 90)
  assert((Array.isArray(chapters) ? chapters : chapters.chapters || []).length === 1,
    '隔离作品应只创建一章')
  checkpoint('chapter-written')

  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  await page.getByRole('button', { name: new RegExp(`^1 ${chapterTitle}$`) }).click({ timeout: 20000 })
  await page.getByRole('tab', { name: '草稿', exact: true }).click({ timeout: 20000 })
  // 现行产品在 draft 阶段保留 DiscussionDock；WriteChat portal 只在 final 阶段出现。
  // draft 的真实入口仍是右侧主编输入，且它会物理路由至 /chat/write(phase=draft)。
  const writeComposer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await writeComposer.waitFor({ state: 'visible', timeout: 30000 })
  await writeComposer.fill(
    '请以林雾为焦点写一个约 250 字的冷开场草稿：她必须在码头做一个不可回头的选择。' +
    '请主动服从本书已有角色档案和限知约束，不要解释你的依据，也不要调用 MCP 工具。',
  )
  const writePosted = page.waitForResponse(
    (response) => /\/chat\/write(?:\?|$)/.test(response.url())
      && response.request().method() === 'POST',
    // TokenPlan/Qwen 的真实长文生成会稳定超过 20 秒；这里验收的是
    // 完整 Context Manifest + 写作结果，不能以浏览器的短网络等待误杀真调。
    { timeout: 180000 },
  )
  await page.getByTestId('chief-chat-shell').getByRole('button', { name: '发送', exact: true }).click()
  const writeResponse = await writePosted
  assert(writeResponse.status() === 200,
    `章内写作请求未被服务端受理:${writeResponse.status()} ${await writeResponse.text()}`)
  const assistantMessage = await waitFor(async () => {
    const rows = await json(`/chat/messages?chapter=1&work=${encodeURIComponent(work)}`)
    const assistant = [...rows].reverse().find((row) => row.role === 'assistant' && row.trace?.context)
    if (assistant) return assistant
    const uiText = await page.getByTestId('chief-chat-shell').innerText().catch(() => '')
    if (/出错:|上下文.*(?:失败|过期|缺失)|HTTP\s*(?:4|5)\d\d/.test(uiText)) {
      throw new Error(`写作槽未持久化的错误:${uiText.replace(/\s+/g, ' ').slice(0, 800)}`)
    }
    return null
  }, Boolean, '写作轮未产出带 Context Manifest 的 assistant 留痕', 90)
  const context = assistantMessage.trace.context
  assert(context.manifest_id && context.actual_input_hash, '写作轮缺少 Manifest 不可变绑定')
  assert(Array.isArray(context.blocks) && context.blocks.some((block) => block.name === 'canonical'),
    '写作轮 Context Manifest 缺少 canonical 块')
  assert(!JSON.stringify(context).includes('她曾在盐场失踪三日'),
    'Context Manifest 不得保存私密前史明文')
  checkpoint('context-manifest')
  return { work, book: BOOK, character: CHARACTER, manifestId: context.manifest_id, runIds: [profileRunId, chapterRunId] }
})

const artifact = {
  ok: result.ok && result.errs.length === 0,
  ...result,
  work: result.work || observedWork,
  runIds: result.runIds || observedRunIds,
}
if (process.env.E2E_RESULT_FILE) await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify(artifact, null, 2))
if (!artifact.ok) {
  console.error('CODEX_COMPLETE_PROFILE_APPROVAL FAIL', JSON.stringify(result))
  process.exitCode = 1
}

console.log('CODEX_COMPLETE_PROFILE_APPROVAL OK', JSON.stringify(result))
