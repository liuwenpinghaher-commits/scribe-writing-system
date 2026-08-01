// 质量决策真人验收：所有作者写入均经网页输入/点击；fetch 只用于结果回读。
// 使用：E2E_BASE=http://127.0.0.1:3311 E2E_API=http://127.0.0.1:3321 \
//   E2E_BOOK_TITLE='全链路验收·TokenPlan·自定义标题' E2E_WORK=已有作品slug \
//   node e2e/quality_reference_author_journey.mjs
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { chiefSay, acceptDraftProposal, adoptDraftAsFinal, approveAllPending } from './author_decisions.mjs'
import { attachBrowserErrorTrace, partitionVerifiedTerminalSseAborts } from './browser_error_trace.mjs'
import { attachCompletedRunCapture } from './run_identity_capture.mjs'

const BASE = process.env.E2E_BASE || 'http://127.0.0.1:3311'
const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
const BOOK_TITLE = process.env.E2E_BOOK_TITLE || `全链路验收·TokenPlan·${stamp}`
const CHAPTER_SEQ = Number(process.env.E2E_CHAPTER_SEQ || 1)
let work = process.env.E2E_WORK || null
let contractId = process.env.E2E_CONTRACT_ID || null
const SCRATCH = process.env.GOAL_SCRATCH || process.env.SCRATCH || ''
const referenceTitle = `原创技法验收样本·${stamp}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
// 二十章长程验收以每章 2,800 个非空白字符保底，总量留出 5 万字目标的冗余。
// 可仅在显式验收参数下提高，但不得回退为“短稿先评价、再另外扩写”的假闭环。
const E2E_MIN_PROSE_LENGTH = Number(process.env.E2E_MIN_PROSE_LENGTH || 2_800)
// 所有未逐项声明的页面动作也必须有诊断上限，避免界面失配时长程验收只剩无阶段心跳。
const E2E_UI_ACTION_TIMEOUT_MS = 60_000
// 自动 ingest 会在保存正文后异步进行真实模型抽取；C2 必须等到结果形成，不能把
// 合法的慢抽取误判为“无事件”。超过此窗口仍未形成 pass 才是严格失败。
const STRICT_C2_WAIT_MS = 420_000
const report = { book: BOOK_TITLE, work: work, chapter_seq: CHAPTER_SEQ, provider: 'qwen', model: 'qwen3.8-max-preview', steps: [] }
let browser
let writeBoundaryTrace = []
let browserHttp404s = []
const verifiedCompletedRunIds = new Set()
let detachCompletedRunCapture = null
let signalClosing = false
// Playwright 的部分等待在底层连接异常时可能只留下未兑现 Promise；Promise 自身
// 不会保持 Node 事件循环，进程会在未写完结果 artifact 时静默退出。保持一个轻量
// timer，直到 finally 明确收束为止，使超时/异常能走统一的失败落盘路径。
const eventLoopKeepAlive = setInterval(() => {}, 60_000)

function persistReport() {
  report.work = work
  report.updated_at = new Date().toISOString()
  report.write_boundary_trace = writeBoundaryTrace
  report.browser_http_404s = browserHttp404s
  const observedFailures = browserHttp404s.failed_requests || []
  const classifiedFailures = partitionVerifiedTerminalSseAborts(observedFailures, verifiedCompletedRunIds)
  report.browser_observed_failed_requests = observedFailures
  report.browser_controlled_sse_closures = classifiedFailures.controlled_closures
  report.browser_failed_requests = classifiedFailures.unexpected_failures
  const targets = [
    SCRATCH ? `${SCRATCH}/quality-reference-author-${stamp}.json` : null,
    process.env.E2E_RESULT_FILE || null,
  ].filter(Boolean)
  for (const target of new Set(targets)) {
    mkdirSync(dirname(target), { recursive: true })
    writeFileSync(target, JSON.stringify(report, null, 2))
  }
}

function handleTermination(signal) {
  if (signalClosing) return
  signalClosing = true
  report.ok = false
  report.error = `质量真人验收被 ${signal} 终止；最后完成阶段: ${report.last_stage || '尚未完成任何阶段'}`
  report.terminated_by = signal
  persistReport()
  void browser?.close().catch(() => {}).finally(() => process.exit(signal === 'SIGINT' ? 130 : 143))
}

process.once('SIGTERM', () => handleTermination('SIGTERM'))
process.once('SIGINT', () => handleTermination('SIGINT'))

// 真人验收调试证据：仅记录写作/保存边界的路径、状态和 SSE 事件种类；
// 不记录作者提示词、正文、参考文本、响应体或任何凭证。
function attachWriteBoundaryTrace(page) {
  const trace = []
  const apiPath = (url) => {
    const path = new URL(url).pathname
    return path.startsWith('/api/') ? path.slice(4) : path
  }
  const relevant = (url) => {
    try {
      const path = apiPath(url)
      return path === '/chat/write' || path === '/save-chapter' || path === '/quality/snapshot' || path.startsWith('/ai/runs')
    } catch { return false }
  }
  page.on('response', async (response) => {
    if (!relevant(response.url())) return
    const path = apiPath(response.url())
    const item = { method: response.request().method(), path, status: response.status() }
    if (response.status() >= 400) {
      try {
        const body = await response.json()
        const detail = body?.detail
        item.error_code = typeof detail === 'object' && detail ? detail.code || null : null
        item.error_kind = typeof detail === 'string' ? 'text' : typeof detail
        item.blocking_count = Array.isArray(detail?.blocking) ? detail.blocking.length : null
      } catch { item.error_kind = 'unreadable' }
    }
    if (path === '/chat/write' && response.status() < 400) {
      try {
        const body = await response.text()
        item.sse_events = [...body.matchAll(/data:\s*(\{[^\n]*\})/g)]
          .map((match) => {
            try { return Object.keys(JSON.parse(match[1]))[0] || 'empty' } catch { return 'invalid_json' }
          })
      } catch { item.sse_events = ['unreadable'] }
    }
    trace.push(item)
  })
  return trace
}

function step(name, detail = {}) {
  const item = { name, at: new Date().toISOString(), ...detail }
  report.steps.push(item)
  report.last_stage = name
  persistReport()
  console.log(`QUALITY_E2E chapter_seq=${CHAPTER_SEQ} ${name} ${JSON.stringify(detail)}`)
}

function requireThat(condition, message) {
  if (!condition) throw new Error(message)
}

function activeWork() {
  requireThat(typeof work === 'string' && work.length > 0, '隔离作品尚未创建或解析 work')
  return work
}

function activeContractId() {
  if (!contractId) contractId = `quality-contract:${activeWork()}:e2e:${stamp}`
  return contractId
}

async function read(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`只读回查失败 ${response.status}: ${path}`)
  return response.json()
}

// chiefSay 的 Node 侧状态轮询可能先于浏览器响应观察到 completed。用该已存在的
// 只读 trace 再确认一次，才能把对应 EventSource 的 ERR_ABORTED 归为受控关闭；
// 不确定、失败或跨作品 Run 一律不加入豁免集合。
async function chiefSayWithCompletionEvidence(page, message, options) {
  const result = await chiefSay(page, message, options)
  const run = result?.run
  if (!run?.id || (run.work && run.work !== activeWork())) return result
  let status = run.status
  if (status !== 'completed') {
    try {
      const trace = await read(`/ai/runs/${encodeURIComponent(run.id)}/trace?work=${encodeURIComponent(activeWork())}`)
      status = trace?.status
    } catch {
      return result
    }
  }
  if (status === 'completed') verifiedCompletedRunIds.add(run.id)
  return result
}

async function waitForQualityReady(page, jobId) {
  // 后端在 20 条真实系统/参考判断、两路并行、180 秒单维硬截止且每条允许
  // 两次 JSON 修复时，其孤儿作业恢复上限约为 95 分钟。作者可见旅程必须覆盖该窗口，避免把
  // 仍在真实执行的 TokenPlan 评价提前误报成超时。
  const deadline = Date.now() + 5_700_000
  let qualityJobStatus = null
  let retryAttempts = 0
  while (Date.now() < deadline) {
    qualityJobStatus = await read(`/quality/evaluation?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
    requireThat(qualityJobStatus.job_id === jobId,
      `质量作业回读漂移: expected=${jobId}, actual=${qualityJobStatus.job_id || 'none'}`)
    if (qualityJobStatus.status === 'ready') return qualityJobStatus
    if (qualityJobStatus.status === 'retryable_failed' && retryAttempts < 3) {
      // 后台状态先于当前工作台渲染更新时，必须重新经作者可见入口回到质量审阅；
      // 不能用 REST 直接重试，否则会丢失“作者确认重试”这一验收事实。
      const retryCard = page.getByTestId('quality-job-retryable-failed')
      // 当前页面已是质量审阅时，失败卡会直接可见；强制再点左树会因为该入口不在
      // 此布局而超时，反而错过作者的重试决定。仅在卡不在当前页时才真实导航。
      if (!(await retryCard.isVisible().catch(() => false))) {
        const qualityReview = page.getByRole('button', { name: '质量审阅', exact: true })
        // 某些布局会保留质量审阅按钮但暂时隐藏失败卡；此时直接点击现有入口，
        // 不能先点“参考作品”再等待一个不一定挂载的二级入口。
        if (await qualityReview.isVisible().catch(() => false)) {
          await qualityReview.click()
        } else {
          // 其余布局才从作者可见的参考作品入口进入；二级入口和直接表单都合法。
          await page.getByRole('button', { name: '参考作品', exact: true }).click()
          await page.waitForFunction(() => {
            const shown = (node) => node instanceof HTMLElement && node.offsetParent !== null
            return [...document.querySelectorAll('button, input, textarea')].some((node) => (
              (node.textContent?.trim() === '质量审阅'
                || node.getAttribute('aria-label') === '质量审阅'
                || node.getAttribute('aria-label') === '参考作品工作台'
                || node.getAttribute('aria-label') === '参考作品标题') && shown(node)
            ))
          }, null, { timeout: 30000 })
          if (!(await qualityReview.isVisible().catch(() => false))) {
            await page.getByRole('button', { name: '参考作品工作台', exact: true }).click()
            await qualityReview.waitFor({ state: 'visible', timeout: 30000 })
          }
          await qualityReview.click()
        }
      }
      await retryCard.waitFor({ state: 'visible', timeout: 30000 })
      const retry = page.getByRole('button', { name: '重试本次冻结评价', exact: true })
      await retry.waitFor({ state: 'visible', timeout: 30000 })
      await retry.click()
      retryAttempts += 1
      step('作者通过 UI 重试冻结质量评价', { attempt: retryAttempts })
      await sleep(1_000)
      continue
    }
    if (qualityJobStatus.status === 'retryable_failed' || qualityJobStatus.status === 'failed') {
      throw new Error(`质量后台作业失败: ${qualityJobStatus.error_code || qualityJobStatus.status}`)
    }
    await sleep(1_000)
  }
  throw new Error(`质量后台作业超时: ${qualityJobStatus?.status || 'unknown'}`)
}

function assertQwen(record, label) {
  requireThat(record.provider === 'qwen', `${label}: provider 必须为 qwen`)
  requireThat(record.model === 'qwen3.8-max-preview', `${label}: model 必须为 qwen3.8-max-preview`)
  requireThat(typeof record.provider_request_id === 'string' && record.provider_request_id.length > 0,
    `${label}: 缺少真实 provider_request_id`)
  requireThat(record.usage && Object.values(record.usage).some((value) => Number(value) > 0),
    `${label}: 缺少真实 usage`)
}

// 质量合同不能替代写作工艺准备：正文存档仍须经过 Gate A。这里所有世界状态
// 都由作者在网页对话中发起，并逐项点击 Hermes 审批；fetch 仅用于只读核验。
const gateARepairPrompts = {
  A1: '请仅用 s3_set_intent 补齐 reader_feeling=压抑中的清醒、emotional_arc=怀疑到承担、red_lines=不以作者旁白替人物裁定道德。需我审批。',
  A2: '请仅用 s3_add_character 登记两名完整角色：周岑(appearance=手背有旧烫伤,deep_need=确认失踪姐姐是否主动离开)与贺钟(appearance=左耳缺一角,deep_need=守住旧站档案)。需我审批。',
  A3: '请仅用 s3_add_world_rule 登记规则：北桥旧站的封存档案一旦被公开，相关证词必须在当夜失效。需我审批。',
  A4: '请仅用 s3_add_character_relation 建立关系，参数必须精确为 src_oid=role:周岑、dst_oid=role:贺钟、relation=custom、since_chapter=1、note=互相试探、各自隐瞒关键证据。不得把展示名“周岑”或“贺钟”当作 src_oid/dst_oid。需我审批。',
  A5: '请仅用 s3_add_motif 登记母题 name=未署名的信 theme=真相与沉默的代价 echoes=封蜡/潮痕/未拆信封。需我审批。',
  A6: '请仅用 s3_plant_promise 埋伏笔 text=未署名信里的收件人会迫使周岑在公开与沉默之间选择 setup_chapter=1。需我审批。',
  A7: '请仅用 s3_plant_promise 埋伏笔 text=未署名信里的收件人会迫使周岑在公开与沉默之间选择 setup_chapter=1，使其可进入 chapter brief。需我审批。',
}

async function prepareCraftReadiness(page) {
  let gates = await read(`/craft-gates?work=${encodeURIComponent(activeWork())}`)
  for (let round = 0; !gates.gate_a?.ok && round < 2; round++) {
    const blocking = [...new Set(gates.gate_a?.blocking || [])]
    for (const gateId of blocking) {
      const prompt = gateARepairPrompts[gateId]
      requireThat(prompt, `Gate A 缺少 ${gateId} 的 MCP 修复指令`)
      await chiefSayWithCompletionEvidence(page, prompt, { preferWrite: false, maxMs: 300000, bookTitle: BOOK_TITLE })
      await approveAllPending(page)
    }
    gates = await read(`/craft-gates?work=${encodeURIComponent(activeWork())}`)
  }
  requireThat(gates.gate_a?.ok, `Gate A 仍未通过: ${JSON.stringify(gates.gate_a?.blocking || [])}`)
  step('Gate A 作者对话-审批-回读通过', { checks: gates.gate_a.checks?.length || 0 })
}

async function openBook(page) {
  // Vite/HMR 与 SSE 会维持连接，networkidle 永远不成立；DOM 就绪后由下方具体
  // 控件等待确认真实页面可用，不能让验收在模型调用前假失败。
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  if (!work) {
    // 新建隔离书：真实作者界面创建，随后仅以只读接口解析不可变 slug。
    await page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first().fill(BOOK_TITLE)
    await page.getByRole('button', { name: '建', exact: true }).first().click()
    await page.locator('[data-testid="four-col"]').waitFor({ state: 'attached', timeout: 20000 })
    const works = await read('/works')
    const rows = Array.isArray(works) ? works : works.works || []
    const matches = rows.filter((item) => item.title === BOOK_TITLE && typeof item.slug === 'string')
    requireThat(matches.length === 1, `新建隔离书后无法唯一解析 work: ${BOOK_TITLE}`)
    work = matches[0].slug
    report.work = work
    step('新建隔离书', { work })
    return
  }
  // 标题是作者可重复使用的展示字段；真人验收必须按不可变 work slug 进入目标书，
  // 否则同名书会使 UI 写入和只读回查落在不同物理数据库。
  const opener = page.locator(`[data-work-slug="${activeWork()}"]`)
  let openerCount = await opener.count()
  if (openerCount !== 1) {
    // 新的浏览器上下文会按作者上次打开的作品自动恢复。切书必须经过可见的
    // 顶栏「选择作品」入口，不能假定初始页面就是作品库或用 localStorage 偷切。
    const library = page.locator('[data-testid="app-rail"] button[title="切换 / 选择作品"]')
    await library.waitFor({ state: 'visible', timeout: 20000 })
    await library.click()
    await opener.waitFor({ state: 'visible', timeout: 20000 })
    openerCount = await opener.count()
  }
  requireThat(openerCount === 1, `configured work ${activeWork()} is not unique or absent in the library`)
  await opener.click({ timeout: 20000 })
  await page.waitForTimeout(700)
  await page.locator('[data-testid="four-col"]').waitFor({ state: 'attached', timeout: 20000 })
  step('打开隔离书')
}

async function ensureFirstChapter(page) {
  const chapters = await read(`/chapters?work=${encodeURIComponent(activeWork())}`)
  const hasFirst = (Array.isArray(chapters) ? chapters : chapters.chapters || [])
    .some((chapter) => Number(chapter.seq) === CHAPTER_SEQ)
  if (hasFirst) return
  await chiefSayWithCompletionEvidence(page,
    `请只调用 s3_add_chapter，在作品 ${activeWork()} 新建第${CHAPTER_SEQ}章，title=质量验收第${CHAPTER_SEQ}章；等待我批准，未获批准不得声称已落库。`,
    { preferWrite: false, maxMs: 180000, bookTitle: BOOK_TITLE },
  )
  for (let attempt = 0; attempt < 60; attempt++) {
    await approveAllPending(page, { maxRounds: 3, settleMs: 400 })
    const rows = await read(`/chapters?work=${encodeURIComponent(activeWork())}`)
    if ((Array.isArray(rows) ? rows : rows.chapters || []).some((chapter) => Number(chapter.seq) === CHAPTER_SEQ)) {
      step(`作者审批新建第${CHAPTER_SEQ}章`)
      return
    }
    await sleep(1000)
  }
  throw new Error(`新建第${CHAPTER_SEQ}章审批后未落库`)
}

async function openReferenceWorkspace(page) {
  const titleInput = page.getByLabel('参考作品标题')
  if (!(await titleInput.isVisible().catch(() => false))) {
    await page.getByRole('button', { name: '参考作品', exact: true }).click()
    // 参考入口存在两种合法真实落点：直接渲染工作台，或先出现“参考作品工作台”二级入口。
    // 不能用一次 isVisible 就臆断第一种不存在，否则慢渲染时会抢点一个并未挂载的按钮。
    await page.waitForFunction(() => {
      const shown = (node) => node instanceof HTMLElement && node.offsetParent !== null
      const inputReady = [...document.querySelectorAll('input, textarea')]
        .some((node) => node.getAttribute('aria-label') === '参考作品标题' && shown(node))
      const workspaceReady = [...document.querySelectorAll('button')]
        // 二级入口的可访问名称是稳定契约；视觉文案会附带“打开”，不能以
        // textContent 精确相等判断，否则入口已出现仍会错误地等待至超时。
        .some((node) => node.getAttribute('aria-label') === '参考作品工作台' && shown(node))
      return inputReady || workspaceReady
    }, null, { timeout: 30000 })
    if (!(await titleInput.isVisible().catch(() => false))) {
      await page.getByRole('button', { name: '参考作品工作台', exact: true }).click()
    }
  }
  await titleInput.waitFor({ state: 'visible', timeout: 30000 })
}

async function createAndApproveReference(page) {
  await openReferenceWorkspace(page)
  // 只导入原创验收短文；不得把受版权保护的喜欢作品原文写进自动化样本。
  await page.getByLabel('参考作品标题').fill(referenceTitle)
  await page.getByLabel('参考作品正文').fill(
    '雨把旧码头的木板压得发黑。林澈没有解释来意，只把湿伞倒扣在门槛外。\n'
    + '守夜人听见绳结断裂，先看见一只空手，再看见那封没有署名的信。\n'
    + '两人都没有说出潮位表上被划掉的名字。',
  )
  // React 的点击处理器会异步等待真实 POST；仅等待 click 返回会与后端落库竞态，
  // 造成随后只读回查先于导入完成而误报“未能回读”。必须先观察浏览器实际收到的
  // 201 响应，再按返回的本次 reference_work_id 回读，仍保持所有写入走 UI。
  const importResponsePromise = page.waitForResponse((response) => {
    try {
      const pathname = new URL(response.url()).pathname
      return response.request().method() === 'POST'
        && pathname.endsWith('/references/import')
        && response.status() === 201
    } catch { return false }
  }, { timeout: 60_000 })
  await page.getByRole('button', { name: '导入', exact: true }).click()
  const importResponse = await importResponsePromise
  const importedPayload = await importResponse.json().catch(() => null)
  requireThat(importedPayload?.title === referenceTitle, '参考作品 UI 导入响应标题不匹配本次运行')
  requireThat(typeof importedPayload?.reference_work_id === 'string' && importedPayload.reference_work_id.length > 0,
    '参考作品 UI 导入响应缺少本次 reference_work_id')
  // 同一本验收书可以保留前一次运行的参考作品。生成指纹必须绑定本次刚导入的
  // 卡片，不能在全页按按钮名称定位，否则多个历史卡片会触发 Playwright strict mode。
  const importedReferences = await read(`/references?work=${encodeURIComponent(activeWork())}`)
  const importedReference = importedReferences.find((item) => item.reference_work_id === importedPayload.reference_work_id)
  requireThat(importedReference, '参考作品 UI 导入后未能回读本次参考 ID')
  const referenceCard = page.getByTestId(`reference-card-${importedReference.reference_work_id}`)
  await referenceCard.waitFor({ state: 'visible', timeout: 20000 })
  await referenceCard.getByRole('button', { name: '生成指纹', exact: true }).click()
  const corrections = referenceCard.getByLabel('指纹校订')
  await corrections.waitFor({ state: 'visible', timeout: 300000 })
  const fingerprint = JSON.parse(await corrections.inputValue())
  fingerprint.transferable_mechanisms = [
    ...(fingerprint.transferable_mechanisms || []),
    '以可见动作和未说出口的信息维持压力，不解释人物动机。',
  ]
  fingerprint.non_copyable_elements = [
    ...(fingerprint.non_copyable_elements || []),
    '验收短文中的人物、地点、物件、情节和措辞均不可复用。',
  ]
  await corrections.fill(JSON.stringify(fingerprint, null, 2))
  await referenceCard.getByRole('button', { name: '批准指纹', exact: true }).click()
  await page.getByText('已批准', { exact: true }).last().waitFor({ state: 'visible', timeout: 30000 })

  const refs = await read(`/references?work=${encodeURIComponent(activeWork())}`)
  const ref = refs.find((item) => item.title === referenceTitle)
  requireThat(ref, '参考作品 UI 导入后未能只读回查')
  const fingerprints = await read(`/references/${encodeURIComponent(ref.reference_work_id)}/fingerprints?work=${encodeURIComponent(activeWork())}`)
  const approved = fingerprints.find((item) => item.status === 'approved')
  requireThat(approved, '指纹 UI 批准后没有 approved 修订')
  assertQwen(approved, '参考指纹')
  step('参考导入-指纹-作者校订批准', { fingerprint_id: approved.fingerprint_id })
  return approved
}

async function fillEveryContractField(page, approvedFingerprint) {
  await page.getByRole('button', { name: '质量合同', exact: true }).click()
  await page.getByLabel('合同 ID').waitFor({ state: 'visible', timeout: 15000 })
  const fields = {
    '合同 ID': activeContractId(),
    '主类型': '原创悬疑长篇',
    '目标读者': '愿意缓读并复盘伏笔的成年读者',
    '叠加类型': '心理悬疑\n城市志怪',
    '自定义类型说明': '以人物选择承受代价的原创都市悬疑。',
    '阅读情境': '夜间连续阅读，章节结尾保留可回想的不确定性。',
    '核心承诺': '每个场景都让人物在信息不全时作出不可逆的选择。',
    '预期体验': '好奇\n紧张\n余韵',
    '情绪弧光': '压抑\n试探\n反转\n余韵',
    '主题问题': '当真相会伤害他人时，沉默是否也是一种选择？',
    '允许的含混': '不解释全部背景，只让可验证行动留下余波。',
    '禁止说教': '不得用作者旁白裁定人物道德。',
    '不可协商项': '不得复用参考作品的角色、地点、物件、情节、独特比喻或措辞。',
    '允许的取舍': '优先人物逻辑与情绪后果，必要时压缩背景信息。',
    '人物成功标准': '人物的选择必须可在正文行动中定位。',
    '关系成功标准': '关系变化必须有双向代价和可见反应。',
    '结构成功标准': '每章推进悬念并兑现或转换至少一个承诺。',
    '语言成功标准': '声音服务视角，避免空泛解释与套话。',
    '原创性成功标准': '只借鉴经批准的抽象机制，文本表达保持独立。',
    '参考目标（JSON 数组）': JSON.stringify([{
      reference_work_id: approvedFingerprint.reference_work_id,
      dimension: 'language_voice', mode: 'inspired', intensity: 0.4,
      mechanism: '动作承压与信息留白',
      difference_requirement: '不得复用验收参考中的人物、地点、物件、情节或措辞。',
    }]),
    '完成标准': '十维均锚定冻结正文，系统、参考、作者三轴均可回读。\n作者对每一维给出理由、反证或明确裁决。',
  }
  for (const [label, value] of Object.entries(fields)) await page.getByLabel(label, { exact: true }).fill(value)
  for (const milestone of ['scene', 'chapter', 'volume', 'book']) {
    const box = page.locator(`[data-field-path="contract.evaluation_milestones.${milestone}"]`)
    if (!(await box.isChecked())) await box.check()
  }
  await page.getByRole('button', { name: '保存合同草案', exact: true }).click()
  await page.getByRole('button', { name: '批准本修订', exact: true }).click()
  await page.getByText('已批准', { exact: true }).last().waitFor({ state: 'visible', timeout: 30000 })
  // 批准按钮的 UI 状态先于质量合同查询投影稳定可读；单次立即 GET 会在真实
  // Surreal 写入提交竞态下拿到 approved/weights 尚未完整的旧投影，误报作者合同
  // 失败。只读轮询直到同一 contract_id 的批准与三轴权重都稳定，不改变任何写路径。
  let contract = null
  for (let attempt = 0; attempt < 60; attempt++) {
    contract = await read(`/quality/contracts/${encodeURIComponent(activeContractId())}?revision=1&work=${encodeURIComponent(activeWork())}`)
    if (contract.approved === true
      && Number(contract.weights?.author) > Number(contract.weights?.system)
      && Number(contract.weights?.author) > Number(contract.weights?.reference)) break
    await sleep(500)
  }
  requireThat(contract.approved === true && contract.weights.author > contract.weights.system
    && contract.weights.author > contract.weights.reference, '合同批准或作者权重约束未成立')
  step('合同全字段填写并批准', { weights: contract.weights })
}

async function selectChapterStage(page, stage) {
  await page.getByRole('button', { name: '手稿', exact: true }).click()
  // 作者此前折叠目录是有效的个人布局偏好；真实旅程不能假定目录始终占据一列。
  // 只在恢复按钮可见时点击，避免已展开时再次触发无意义的布局切换。
  const restoreDirectory = page.getByTestId('directory-restore-button')
  if (await restoreDirectory.isVisible().catch(() => false)) await restoreDirectory.click()
  await page.getByTestId('manuscript-directory').waitFor({ state: 'visible', timeout: 10000 })
  // 标题是作者实际填写的「夜访棺材铺」等，不是固定“第1章”；序号才是稳定契约。
  const chapter = page.getByRole('button', { name: new RegExp(`^(?:${CHAPTER_SEQ}\\s+|第\\s*${CHAPTER_SEQ}\\s*章)`) }).first()
  await chapter.waitFor({ state: 'visible', timeout: 30000 })
  await chapter.click()
  const tab = page.getByRole('tab', { name: stage, exact: true })
  await tab.waitFor({ state: 'visible', timeout: 30000 })
  await tab.click()
  await page.waitForTimeout(700)
  requireThat(await tab.getAttribute('aria-selected') === 'true', `作者选择${stage}后阶段没有保持`)
}

async function selectChapterFinal(page) {
  // “正文”是 final 成稿检视页；只有“草稿”阶段映射到 WriteChat 的 draft
  // 路径，才能生成可由作者接受的 /chat/write 提案。
  await selectChapterStage(page, '草稿')
}

// 正文不是质量系统的第一步。先通过 MCP 形成可审计的大纲、节拍与限知演绎，
// 再让写作槽据此提案；不得把 Gate B 当作保存时才发现的错误。
const gateBRepairPrompts = {
  B1: `请仅用 s3_patch_chapter_plan 写入第${CHAPTER_SEQ}章 synopsis（至少100字）：周岑夜访北桥旧站，为确认失踪姐姐是否主动离开而带着未拆的无署名信；档案守门人贺钟知道封存档案的代价，却只允许她看见一页被抽走的目录。两人都不肯说破信封上的收件人，周岑在公开档案和保护姐姐之间必须作出不可逆选择。再写入至少3条 beats（推门发现封蜡异常、与贺钟对质且各自隐瞒证据、周岑决定暂不拆信并带走目录缺页）。需我审批。`,
  B2: `请仅用 s3_patch_chapter_plan 为第${CHAPTER_SEQ}章补齐至少3条 beats：推门发现封蜡异常、与贺钟对质且各自隐瞒证据、周岑决定暂不拆信并带走目录缺页。需我审批。`,
  B3: `请仅用 s3_patch_chapter_plan 为第${CHAPTER_SEQ}章写入 scene_truth、involved_characters 和 deductions：scene_truth 至少120字，明确周岑只看见信封封蜡的姐姐缩写并听到贺钟说“信不能拆”，贺钟则知道公开封存档案会使证词失效但没有告诉周岑；involved_characters 必须为 ["role:周岑","role:贺钟"]；deductions 必须恰好覆盖两人，每条 prose 有五个标题 ### 看到/听到、### 知道、### 以为(误读)、### 做了/说了、### 没察觉的，只写该角色可知信息。需我审批。`,
  B4: `请仅用 s3_patch_chapter_plan 修正第${CHAPTER_SEQ}章 involved_characters 为 ["role:周岑","role:贺钟"]，并以 deductions 覆盖两人；每条含 ### 看到/听到、### 知道、### 以为(误读)、### 做了/说了、### 没察觉的五个标题，且只写该角色可知信息。需我审批。`,
  B5: `请仅用 s3_patch_chapter_plan 为第${CHAPTER_SEQ}章补齐周岑与贺钟的 deductions；每条含 ### 看到/听到、### 知道、### 以为(误读)、### 做了/说了、### 没察觉的五个标题，且只写该角色可知信息。需我审批。`,
}

async function prepareChapterScaffold(page) {
  let gates = await read(`/craft-gates?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  for (let round = 0; !gates.gate_b?.ok && round < 2; round++) {
    const blocking = [...new Set(gates.gate_b?.blocking || [])]
    for (const gateId of blocking) requireThat(
      gateBRepairPrompts[gateId], `Gate B 缺少 ${gateId} 的 MCP 修复指令`,
    )
    // B1/B2 是同一份结构计划，B3/B4/B5 是同一份限知演绎；合并后仍保留
    // 对每个缺口的明确覆盖，避免同一章连续发五个重复的真实模型请求。
    const prompts = [
      blocking.some((id) => id === 'B1' || id === 'B2')
        ? { stage: '大纲', text: gateBRepairPrompts.B1 } : null,
      blocking.some((id) => id === 'B3' || id === 'B4' || id === 'B5')
        ? { stage: '演绎', text: gateBRepairPrompts.B3 } : null,
    ].filter(Boolean)
    for (const prompt of prompts) {
      // s3_patch_chapter_plan 只有在实际“大纲/节拍/演绎”章阶段才经 Hermes
      // 写通道执行；正文阶段是提案流，模型会把同一指令当普通文本回答。
      await selectChapterStage(page, prompt.stage)
      await chiefSayWithCompletionEvidence(page, prompt.text, { preferWrite: false, maxMs: 360000, bookTitle: BOOK_TITLE })
      await approveAllPending(page)
    }
    gates = await read(`/craft-gates?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  }
  requireThat(gates.gate_b?.ok, `Gate B 仍未通过: ${JSON.stringify(gates.gate_b?.blocking || [])}`)
  await selectChapterFinal(page)
  step('Gate B 大纲-节拍-限知演绎-回读通过', { checks: gates.gate_b.checks?.length || 0 })
}

async function ensureOriginalProse(page, approvedFingerprint) {
  step('正文生成前置回读')
  const before = await read(`/chapter?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  const uses = await read(`/quality/reference-craft-uses?chapter=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  const currentReferenceWasConsumed = uses.some((item) => (
    item.reference_fingerprint_ids.includes(approvedFingerprint.fingerprint_id)
  ))
  // 已有正文不等于新批准的参考已经参与创作；两者必须同时成立才可跳过真人写作。
  if (String(before.prose || '').replace(/\s/g, '').length >= E2E_MIN_PROSE_LENGTH && currentReferenceWasConsumed) {
    step('正文与本轮参考消费均已回读')
    return before
  }
  step('正文提案请求已发起')
  await chiefSayWithCompletionEvidence(page,
    `请写一段至少 ${E2E_MIN_PROSE_LENGTH} 字的原创悬疑正文草稿。人物是“周岑”，地点是“北桥旧站”，核心是她在信息不全时选择不打开一封无署名信。`
    + '只允许借鉴已批准参考的抽象技法：动作承压、信息留白。严禁复用参考人物、地点、物件、情节、独特比喻或措辞。',
    {
      preferWrite: true,
      maxMs: 420000,
      bookTitle: BOOK_TITLE,
      onProgress: (phase) => step(`正文提案：${phase}`),
    },
  )
  step('正文提案已返回')
  const decision = await acceptDraftProposal(page, { timeoutMs: 240000 })
  // 草稿阶段的“填入草稿框”只落入编辑缓冲；必须再由作者点击“采用为正文”才会
  // 触发 /save-chapter。不能把 UI 局部状态误当作正典持久化。
  if (decision.kind === 'stage') {
    const saveResponse = page.waitForResponse((response) => {
      const path = new URL(response.url()).pathname.replace(/^\/api/, '')
      return response.request().method() === 'POST' && path === '/save-chapter'
    }, { timeout: 120000 })
    await adoptDraftAsFinal(page, { timeoutMs: 120000 })
    requireThat((await saveResponse).status() === 200, '作者采用草稿后正文保存失败')
  }
  const after = await read(`/chapter?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  requireThat(String(after.prose || '').replace(/\s/g, '').length >= E2E_MIN_PROSE_LENGTH,
    '作者在网页接受正文提案后正文未达到本轮长程验收最小长度')
  requireThat(!String(after.prose).includes('林澈') && !String(after.prose).includes('旧码头'),
    '正文疑似复用了验收参考的人物或地点')
  step('Hermes写作提案-作者接受-正文回读', { prose_length: String(after.prose).trim().length })
  return after
}

// 自动 ingest 是保存正文后的异步流程。C2 只有在正文确实抽出事件、且事件图无
// 因果违规时才算通过；“无事件/skip”不是质量验收成功，不能用它掩盖抽取断链。
async function verifyStrictCausalGate() {
  const deadline = Date.now() + STRICT_C2_WAIT_MS
  let last = { events: [], c2: null }
  while (Date.now() < deadline) {
    const events = await read(`/events?chapter=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
    const gates = await read(`/craft-gates?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
    const c2 = (gates.gate_c_det?.checks || []).find((check) => check.id === 'C2')
    last = { events, c2 }
    if (Array.isArray(events) && events.length > 0 && c2?.verdict === 'pass' && c2?.ok === true) {
      report.causal_evidence = { events: events.length, verdict: c2.verdict }
      step('正文自动抽取事件-C2因果回读通过', report.causal_evidence)
      return
    }
    if (c2?.verdict === 'fail') {
      throw new Error(`C2 因果违规: ${c2.detail || 'unknown'}`)
    }
    await sleep(1_000)
  }
  throw new Error(`C2 未形成可审计因果通过: events=${Array.isArray(last.events) ? last.events.length : 0}, verdict=${last.c2?.verdict || 'missing'}`)
}

async function createEvaluationAndAuthorVerdicts(page, approvedFingerprint) {
  await openReferenceWorkspace(page)
  const qualityReview = page.getByRole('button', { name: '质量审阅', exact: true })
  await qualityReview.waitFor({ state: 'visible', timeout: 30000 })
  await qualityReview.click()
  await page.getByLabel('章节号').waitFor({ state: 'visible', timeout: 30000 })
  await page.getByLabel('章节号').fill(String(CHAPTER_SEQ))
  await page.getByLabel('质量合同 ID').fill(activeContractId())
  await page.getByLabel('合同修订').fill('1')
  await page.getByLabel('已批准参考指纹 ID').fill(approvedFingerprint.fingerprint_id)
  // 既有评价卡会在切换工作台时立即渲染；必须等待本轮 POST 成功，不能把旧卡当作新证据。
  const snapshotResponse = page.waitForResponse((response) => {
    const path = new URL(response.url()).pathname.replace(/^\/api/, '')
    return response.request().method() === 'POST' && path === '/quality/snapshot'
  }, { timeout: 1800000 })
  await page.getByRole('button', { name: '创建章节评价', exact: true }).click()
  const evaluationResponse = await snapshotResponse
  requireThat(evaluationResponse.status() === 202,
    `创建章节评价请求失败: HTTP ${evaluationResponse.status()}`)
  const accepted = await evaluationResponse.json()
  requireThat(typeof accepted.job_id === 'string' && accepted.job_id.length > 0,
    '后台质量作业未返回 job_id')
  const created = await waitForQualityReady(page, accepted.job_id)
  await page.getByText(`第 ${CHAPTER_SEQ} 章 · 10 维`, { exact: true }).waitFor({ state: 'visible', timeout: 900000 })

  requireThat(created.dimensions.length === 10, '质量快照未生成十维判断')
  requireThat(created.dimensions.every((item) => item.system && item.reference), '系统/参考双轴不完整')
  await verifyExecutionEvidence(approvedFingerprint)
  for (const dimension of created.dimensions) {
    const title = dimension.dimension
    const score = page.getByRole('spinbutton', { name: `${title} 作者评分` })
    await score.fill(title === created.dimensions[0].dimension ? '5' : '4')
    await page.getByLabel(`${title} 作者裁决`).selectOption(title === created.dimensions[0].dimension ? 'revise' : 'accept')
    await page.getByLabel(`${title} 裁决理由`).fill(`作者对「${title}」的裁决：保留有效证据，同时要求下一稿加强具体行动后果。`)
    const card = score.locator("xpath=ancestor::div[contains(@class, 'rounded-lg')][1]")
    const counter = card.getByRole('checkbox').first()
    if (title === created.dimensions[0].dimension && await counter.count()) await counter.check()
    const verdictResponse = page.waitForResponse((response) => {
      const path = new URL(response.url()).pathname.replace(/^\/api/, '')
      return response.request().method() === 'POST' && path === '/quality/author-judgment'
    }, { timeout: 30000 })
    await card.getByRole('button', { name: '提交裁决', exact: true }).click()
    const savedVerdict = await verdictResponse
    requireThat(savedVerdict.status() === 201,
      `作者裁决提交失败: HTTP ${savedVerdict.status()}`)
    await sleep(350)
  }
  const evaluated = await read(`/quality/evaluation?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  requireThat(evaluated.dimensions.length === 10 && evaluated.dimensions.every((item) => (
    item.author?.reason && item.author?.decision && item.decision_index != null
  )), '十维作者裁决、理由或三轴决策指数未完整回读')
  requireThat(evaluated.weights.author === 0.6 && evaluated.weights.system === 0.25 && evaluated.weights.reference === 0.15,
    '评价没有采用合同三轴权重')
  step('十维系统-参考-作者裁决闭环', { dimensions: evaluated.dimensions.length })
}

async function verifyExecutionEvidence(approvedFingerprint) {
  const traces = await read(`/quality/evaluation-traces?seq=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  requireThat(traces.length === 20, `质量执行证据应有20条，实际${traces.length}条`)
  for (const trace of traces) {
    requireThat(trace.provider === 'qwen', '质量判断必须记录实际 qwen provider')
    requireThat(trace.model === 'qwen3.8-max-preview', '质量判断必须记录实际 TokenPlan 模型')
    requireThat(typeof trace.provider_request_id === 'string' && trace.provider_request_id.length > 0,
      '质量判断不能伪造或遗漏 provider_request_id')
    requireThat(trace.usage && Object.values(trace.usage).some((value) => Number(value) > 0),
      '质量判断不能伪造或遗漏 usage')
  }
  const uses = await read(`/quality/reference-craft-uses?chapter=${CHAPTER_SEQ}&work=${encodeURIComponent(activeWork())}`)
  requireThat(uses.some((item) => item.reference_fingerprint_ids.includes(approvedFingerprint.fingerprint_id)),
    '正文生成后未回读到 reference_craft_use')
  // 总控只需要能复核模型身份与计量，不保存参考文本、正文或提示词。
  report.model_evidence = traces.map((trace) => ({
    provider: trace.provider,
    model: trace.model,
    provider_request_id: trace.provider_request_id,
    usage: trace.usage,
  }))
  report.evidence = { traces: traces.length, reference_craft_uses: uses.length }
  step('TokenPlan与参考消费证据回读', report.evidence)
}

try {
  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.setDefaultTimeout(E2E_UI_ACTION_TIMEOUT_MS)
  writeBoundaryTrace = attachWriteBoundaryTrace(page)
  browserHttp404s = attachBrowserErrorTrace(page)
  detachCompletedRunCapture = attachCompletedRunCapture(page, ({ id, work: runWork }) => {
    if (!runWork || runWork === activeWork()) verifiedCompletedRunIds.add(id)
  })
  const errors = []
  page.on('pageerror', (error) => errors.push(`pageerror:${error.message}`))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`) })
  await openBook(page)
  await ensureFirstChapter(page)
  await prepareCraftReadiness(page)
  const approvedFingerprint = await createAndApproveReference(page)
  await fillEveryContractField(page, approvedFingerprint)
  await selectChapterFinal(page)
  await prepareChapterScaffold(page)
  await ensureOriginalProse(page, approvedFingerprint)
  await verifyStrictCausalGate()
  await createEvaluationAndAuthorVerdicts(page, approvedFingerprint)
  requireThat(errors.length === 0, `浏览器错误: ${errors.join(' | ')}`)
  report.write_boundary_trace = writeBoundaryTrace
  report.browser_http_404s = browserHttp404s
  report.ok = true
  console.log(`QUALITY_REFERENCE_AUTHOR_JOURNEY_OK ${JSON.stringify(report)}`)
} catch (error) {
  report.ok = false
  report.error = error instanceof Error ? error.message : String(error)
  report.write_boundary_trace = writeBoundaryTrace
  report.browser_http_404s = browserHttp404s
  console.error(`QUALITY_REFERENCE_AUTHOR_JOURNEY_FAIL ${JSON.stringify(report)}`)
  process.exitCode = 1
} finally {
  detachCompletedRunCapture?.()
  browserHttp404s.detach?.()
  // artifact 是验收结论本体，必须先落盘；浏览器已断连时 close 不能吞掉根因。
  persistReport()
  try { await browser?.close() } catch { /* artifact 已安全落盘 */ }
  clearInterval(eventLoopKeepAlive)
}
