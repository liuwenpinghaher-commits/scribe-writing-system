// Gate D·跨会话记忆：真实 UI → TokenPlan/Qwen → Surreal memory trace → 成稿消费。
// 不用 REST 写世界状态；章节创建必须由主编 MCP 提案且由浏览器点击批准。
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { toDirectQwenEvidence } from './full_author_acceptance_result.mjs'
import { consumesEbbLeveragePreference } from './memory_preference_quality.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || `跨会话记忆验收·${Date.now().toString(36)}`
const REUSE = process.env.E2E_REUSE === '1'
const CHAPTER = '潮票记忆章'
const PREFERENCE = '潮票Alpha场景必须先写退潮借力，再让人物承担风险；不可直说惊险。'
// REUSE 模式会多次对同一本隔离书复跑；必须让本轮请求唯一，避免从历史 chat_message
// 错配到已被清理的旧 ContextSession 而把检索审计误判为运行时缺失。
const CASE = process.env.E2E_CASE || `memory-${Date.now().toString(36)}`
// 工件必须能证明它由当前磁盘上的验收脚本生成，不能让旧进程/旧 checkout 的结果
// 冒充本次回归证据。读取 source 本身不触及业务数据，也不影响真实作者路径。
const HARNESS_SOURCE_SHA256 = createHash('sha256')
  .update(await readFile(new URL('./cross_session_memory_recall.mjs', import.meta.url)))
  .digest('hex')
// 这是记忆消费门禁，不是长篇性能压测：短篇合同能把“是否消费了跨会话偏好”与
// 长文生成的推理时延分离；五万字闭环另有专门的长篇/续写验收。
const BLIND_REQUEST = `请用120字以内写潮票Alpha的码头救援冷开场，遵循此前已经记下的作者偏好，不要解释依据。验收标记：${CASE}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}: ${await response.text()}`)
  return response.json()
}

async function waitFor(read, predicate, label, attempts = 100) {
  let value
  for (let index = 0; index < attempts; index += 1) {
    value = await read()
    if (predicate(value)) return value
    await sleep(1000)
  }
  // predicate 一直为 false 时 value 可能仍是 undefined；失败报告必须保留原始
  // “哪个回读没有出现”，不能在格式化阶段二次抛 TypeError 抹掉诊断。
  throw new Error(`${label}: ${String(JSON.stringify(value)).slice(0, 1000)}`)
}

async function approveChapterThroughUi(page, work) {
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await composer.fill(
    `请仅调用 s3_add_chapter，在作品 ${work} 新建第1章，title=${CHAPTER}；等待我批准，未获批准不得声称已落库。`,
  )
  await composer.press('Enter')
  await waitFor(async () => {
    await approveAllPending(page, { maxRounds: 5, settleMs: 800 })
    const rows = await json(`/chapters?work=${encodeURIComponent(work)}`)
    const chapters = Array.isArray(rows) ? rows : rows.chapters || []
    return chapters.find((row) => row.seq === 1 && row.title === CHAPTER)
  }, Boolean, 'MCP 审批后章节未落库')
}

async function waitForWritingContext(page) {
  // snapshot_v1 开启时，WriteChat 会在服务端 session/revision/hash 可用前明确阻止发送。
  // 不能只等 textarea 可见：那正是此前把未绑定请求送到后端 400 的竞态窗口。
  await waitFor(async () => {
    const pending = page.getByRole('status').filter({ hasText: /上下文(?:准备中|尚未就绪)/ })
    return (await pending.count()) === 0
  }, Boolean, '写作上下文会话未就绪', 60)
}

async function selectDraft(page) {
  // 硬导航确保 ContextSnapshotProvider 真正卸载重建；reload 在长 SSE 连接下可能
  // 保留旧页面生命周期，无法作为跨会话证据。随后按 UI 的作品恢复路径重新进书。
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await ensureChiefVisible(page, { bookTitle: BOOK })
  const chapterButton = page.getByRole('button', { name: new RegExp(`^1 ${CHAPTER}$`) }).first()
  await chapterButton.waitFor({ state: 'visible', timeout: 30000 })
  await chapterButton.click({ timeout: 30000 })
  const draftTab = page.getByRole('tab', { name: '草稿', exact: true }).first()
  await draftTab.waitFor({ state: 'visible', timeout: 30000 })
  await draftTab.click({ timeout: 30000 })
  await page.locator('textarea[placeholder^="就当前内容问主编"]').first().waitFor({ state: 'visible', timeout: 30000 })
  await waitForWritingContext(page)
}

async function sendDraft(page, work, message, { expectProposal = false } = {}) {
  const sent = page.waitForRequest((request) =>
    /\/chat\/write(?:\?|$)/.test(request.url()) && request.method() === 'POST',
  { timeout: 180000 })
  const accepted = page.waitForResponse((response) =>
    /\/chat\/write(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
  { timeout: 180000 })
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await composer.fill(message)
  const send = page.getByTestId('chief-chat-shell').getByRole('button', { name: '发送', exact: true })
  await waitFor(async () => !(await send.isDisabled()), Boolean, '写作上下文尚未完成绑定，发送按钮未启用', 60)
  await send.click()
  const [request, response] = await Promise.all([sent, accepted])
  assert(response.status() === 200, `写作请求未受理: ${response.status()} ${await response.text()}`)
  const body = JSON.parse(request.postData() || '{}')
  assert(body.context_session_id && Number.isInteger(body.context_revision), '真实写作请求缺 Context 会话绑定')
  // 写作台会在作者输入前附加当前焦点，SurrealDB 持久化的必须是实际发出的
  // body.msg，而非输入框内的裸文本；否则验收会把已写入的 assistant 误判为缺失。
  const persistedUserText = typeof body.msg === 'string' ? body.msg : message
  const assistant = await waitFor(async () => {
    const rows = await json(`/chat/messages?chapter=1&work=${encodeURIComponent(work)}`)
    const users = rows.filter((row) => row.role === 'user' && row.text === persistedUserText)
    if (!users.length) return null
    const turn = users[users.length - 1].turn
    return [...rows].reverse().find((row) => row.role === 'assistant' && row.turn === turn) || null
  }, Boolean, '写作轮没有持久化 assistant 输出', 300)
  // chat_message 出于避免“提案正文与版本库双写”的约束，只保留提案标记；
  // 草稿阶段的真实作者路径是“填入草稿框后审阅/编辑”，而非正文阶段的 DraftCard。
  // 因而质量验收必须模拟这一步，读取作者可见但尚未采用为正文的草稿。
  let proposal = null
  if (expectProposal) {
    const fill = page.getByRole('button', { name: '填入草稿框', exact: true })
    await waitFor(() => fill.count(), Boolean, '草稿提案未提供“填入草稿框”动作', 120)
    await fill.click()
    const draftEditor = page.locator('[aria-label="草稿正文"]').first()
    proposal = await waitFor(async () => {
      const text = (await draftEditor.count()) ? await draftEditor.innerText() : ''
      return text.trim() || null
    }, Boolean, '填入后作者可见的草稿正文为空', 30)
  }
  return { body, assistant, proposal }
}

const result = await withPage(async (page) => {
  let work = process.env.E2E_WORK || ''
  let first = null
  if (!REUSE) {
    // 写作台会维持 SSE/HMR 连接；networkidle 在这种正常运行态下并不代表页面是否可用。
    // 以 DOM 已解析加上书名输入和四栏 UI 的显式可见性作为真实就绪证据。
    await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded' })
    const title = page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first()
    await title.waitFor({ state: 'visible', timeout: 30000 })
    await title.fill(BOOK)
    await page.getByRole('button', { name: '建', exact: true }).first().click()
    // 新建作品后 FourPane 会先完成挂载，再由布局/选择状态让主编槽可见。
    // 此处只证明“已进入该书的写作壳”；真正可交互性仍由
    // approveChapterThroughUi()/selectDraft() 中具体的可见控件门禁保证。
    // 不能把短暂的折叠态误判为建书失败。
    await page.locator('[data-testid="four-col"]').waitFor({ state: 'attached', timeout: 20000 })

    const works = await json('/works')
    work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
    assert(work, '无法解析隔离作品 slug')
    await approveChapterThroughUi(page, work)
    await selectDraft(page)

    // 第一会话用作者自然语言形成可迁移偏好；不使用 REST/memory 写旁路。
    first = await sendDraft(page, work, `作为作者，请记住这条后续写作偏好：${PREFERENCE}。只回复“已记住”，不要展开解释。`)
    await waitFor(async () => {
      const trace = await json(`/context/sessions/${encodeURIComponent(first.body.context_session_id)}/trace/${first.body.context_revision}?work=${encodeURIComponent(work)}`)
      return trace.available === false || trace
    }, Boolean, '首轮 trace 不可读取')
  }
  assert(work, 'E2E_REUSE=1 时必须提供 E2E_WORK')

  // 刷新会卸载并重新建立 ContextSnapshotProvider；第二次请求必须是另一个 context session。
  await selectDraft(page)
  const second = await sendDraft(page, work, BLIND_REQUEST, { expectProposal: true })
  const priorSession = first?.body.context_session_id || process.env.E2E_PRIOR_SESSION || ''
  assert(priorSession, '缺少第一会话 id，无法证明跨会话')
  assert(second.body.context_session_id !== priorSession,
    '刷新后未建立新的上下文会话，不能声称跨会话验收')
  const trace = await waitFor(
    () => json(`/context/sessions/${encodeURIComponent(second.body.context_session_id)}/trace/${second.body.context_revision}?work=${encodeURIComponent(work)}`),
    (value) => Array.isArray(value?.selected),
    '第二会话 memory trace 未落库',
  )
  assert(trace.query === second.body.msg, `实际检索 query 不是本轮实际请求: ${trace.query}`)
  assert(trace.selected.some((item) => item.source_kind === 'procedural' && String(item.text || '').includes('潮票Alpha')),
    `跨会话偏好未被选入检索证据: ${JSON.stringify(trace.selected).slice(0, 1000)}`)

  const prose = String(second.proposal || second.assistant.text || '')
  // 判“先退潮、再借势”这一叙事因果，而非要求模型机械复读作者的原句。
  assert(consumesEbbLeveragePreference(prose),
    `TokenPlan/Qwen 成稿未消费“先退潮、再借力”的偏好: ${prose.slice(0, 700)}`)
  assert(!/作者(?:偏好|要求)|依据上述/.test(prose),
    `成稿把上下文来源解释给读者，未自然消费偏好: ${prose.slice(0, 700)}`)
  const model_evidence = [first?.assistant?.trace, second.assistant?.trace]
    .map(toDirectQwenEvidence)
    .filter(Boolean)
  assert(model_evidence.length >= 1,
    '跨会话成稿缺少已持久化的真实 TokenPlan 请求 ID 与用量证据')
  return {
    work,
    provider: second.assistant.trace?.provider || null,
    model: second.assistant.trace?.model || null,
    model_evidence,
    firstSession: priorSession,
    secondSession: second.body.context_session_id,
    traceId: trace.trace_id,
    prose: prose.slice(0, 240),
  }
})

if (!result.ok || result.errs.length) {
  console.error('CROSS_SESSION_MEMORY_RECALL FAIL', JSON.stringify(result))
  if (process.env.E2E_RESULT_FILE) {
    await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify({
      ok: false,
      harness_source_sha256: HARNESS_SOURCE_SHA256,
      ...result,
    }, null, 2))
  }
  // 保留 stdout/stderr 的异步写入；直接 process.exit(1) 会截断 CI/PTY 中最关键的失败证据。
  process.exitCode = 1
} else if (process.env.E2E_RESULT_FILE) {
  await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify({
    ok: true,
    harness_source_sha256: HARNESS_SOURCE_SHA256,
    ...result,
  }, null, 2))
}

console.log('CROSS_SESSION_MEMORY_RECALL OK', JSON.stringify(result))
