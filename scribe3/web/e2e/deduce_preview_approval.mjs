// Gate B：真实 UI 的演绎预览 → 作者修订 → 受限写入审批 → SurrealDB 回读。
// 不以 REST/API 灌入任何世界语义；GET 只用于验收回读与 trace 审计。
import { withPage } from './lib.mjs'
import { approveAllPending, ensureChiefVisible } from './author_decisions.mjs'
import { resolveWorkSlugByExactTitle } from '../src/e2e/workResolution.js'
import { writeFile } from 'node:fs/promises'
import { isReadOnlyRunCompleted } from './run_trace_status.mjs'
import { isCompletedWrittenTrace } from './full_author_acceptance_result.mjs'

const API = process.env.E2E_API || 'http://127.0.0.1:3321'
const BOOK = process.env.E2E_BOOK_TITLE || `GateB预览审批·${Date.now().toString(36)}`
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function json(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} ${response.status}`)
  return response.json()
}

async function waitForValue(read, predicate, label, attempts = 30, delayMs = 1000) {
  let last
  for (let index = 0; index < attempts; index += 1) {
    last = await read()
    if (predicate(last)) return last
    await sleep(delayMs)
  }
  throw new Error(`${label}: ${JSON.stringify(last)}`)
}

async function selectDeduceStage(page) {
  // 现行目录的章节节点是带 aria-label 的 button，不是 ARIA treeitem；用真正的
  // 可访问名称定位，避免测试假定旧树实现而从未进入演绎工作台。
  const chapter = page.getByRole('button', { name: /^1 预览审阅章$/ }).first()
  await chapter.click({ timeout: 20000 })
  const tab = page.getByRole('tab', { name: '演绎' }).first()
  await tab.click({ timeout: 20000 })
  await page.getByTestId('deduce-stage').waitFor({ timeout: 20000 })
}

const result = await withPage(async (page) => {
  // 演绎工作台含常驻 SSE，页面可操作由建书输入与四栏壳的显式等待证明。
  await page.goto(process.env.E2E_BASE || 'http://127.0.0.1:3311', { waitUntil: 'domcontentloaded' })
  const title = page.locator('input[placeholder="书名…"], input[aria-label="书名"]').first()
  await title.fill(BOOK)
  await page.getByRole('button', { name: '建', exact: true }).first().click()
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })

  const works = await json('/works')
  const work = resolveWorkSlugByExactTitle(Array.isArray(works) ? works : works.works || [], BOOK)
  assert(work, '无法解析 Gate B 隔离作品')

  await ensureChiefVisible(page, { bookTitle: BOOK })
  const composer = page.locator('textarea[placeholder^="就当前内容问主编"]').first()
  await composer.fill('请只调用 s3_add_chapter 新建第1章，title=预览审阅章。需我审批；未获批准不得声称已落库。')
  await composer.press('Enter')
  await waitForValue(async () => {
    await approveAllPending(page, { maxRounds: 3, settleMs: 500 })
    const chapters = await json(`/chapters?work=${encodeURIComponent(work)}`)
    return Array.isArray(chapters) ? chapters : chapters.chapters || []
  // TokenPlan/Hermes 的工具发现与首次作者审批可在约 45 秒后才到达；30 秒会把
  // 仍在执行的 s3_add_chapter 错判为“未落库”。与后续阶段审批同样保留三分钟窗口。
  }, (chapters) => chapters.length === 1, '新章未落库', 180, 1000)

  await selectDeduceStage(page)
  const before = await json(`/chapter?seq=1&work=${encodeURIComponent(work)}`)
  assert(!String(before.scene_truth || '').trim(), '预览前章节不应已有场景真相')

  const previewCreated = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
    { timeout: 30000 },
  )
  await page.getByRole('button', { name: '生成', exact: true }).click()
  const previewRun = await (await previewCreated).json()
  const previewRunId = previewRun.run_id || previewRun.id
  assert(previewRunId, 'deduce_preview 未返回 run id')

  await waitForValue(
    async () => page.getByTestId('deduce-submit-preview').isEnabled(),
    Boolean,
    'deduce_preview 未生成可提交预览',
    360,
    1000,
  )
  const previewTrace = await waitForValue(
    () => json(`/ai/runs/${encodeURIComponent(previewRunId)}/trace?work=${encodeURIComponent(work)}`),
    (trace) => isReadOnlyRunCompleted(trace, 's3_get_chapter') || trace.status === 'failed',
    'deduce_preview trace 未结束',
  )
  assert(isReadOnlyRunCompleted(previewTrace, 's3_get_chapter'), `deduce_preview 失败:${JSON.stringify(previewTrace.policy_violations || previewTrace.error)}`)
  assert(previewTrace.stage_policy?.phase === 'deduce_preview', '预览未进入 deduce_preview policy')
  assert(previewTrace.stage_policy?.profile === 'scribe3_deduce_preview', '预览未进入只读 profile')
  assert((previewTrace.tool_calls || []).some((call) => call.name === 's3_get_chapter'), '预览未实际读取章节正典')
  assert((previewTrace.tool_calls || []).every((call) => previewTrace.stage_policy.allowed_tools.includes(call.name)), '预览调用了越权工具')
  assert(!(previewTrace.approvals || []).length, '只读预览不应请求世界写审批')

  const afterPreview = await json(`/chapter?seq=1&work=${encodeURIComponent(work)}`)
  assert(!String(afterPreview.scene_truth || '').trim(), 'deduce_preview 不得写入场景真相')

  // 作者明确审阅并修订本地预览；此动作本身不能落正典。
  const authorRevision = '作者修订：棺材铺的油灯映着沈砚腕内侧灰印，老道只承认灰契会索取代价。'
  await page.getByRole('button', { name: '编辑预览', exact: true }).click()
  await page.getByTestId('deduce-preview-editor').fill(authorRevision)
  await page.getByRole('button', { name: '完成预览编辑', exact: true }).click()

  const deduceCreated = page.waitForResponse(
    (response) => /\/api\/ai\/runs(?:\?|$)/.test(response.url()) && response.request().method() === 'POST',
    { timeout: 30000 },
  )
  await page.getByTestId('deduce-submit-preview').click()
  const deduceRun = await (await deduceCreated).json()
  const deduceRunId = deduceRun.run_id || deduceRun.id
  assert(deduceRunId, 'deduce 未返回 run id')

  await page.getByTestId('deduce-run-approval').waitFor({ timeout: 120000 })
  // 审批卡不能只依赖本地 React state：在真正待审批时刷新，必须从持久 run trace
  // 恢复同一章同一阶段的作者裁决入口，再继续批准。
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  await selectDeduceStage(page)
  await page.getByTestId('deduce-run-approval').waitFor({ timeout: 20000 })
  await page.getByRole('button', { name: '批准演绎写入', exact: true }).click()
  const written = await waitForValue(
    () => json(`/chapter?seq=1&work=${encodeURIComponent(work)}`),
    (chapter) => String(chapter.scene_truth || '').includes(authorRevision),
    '批准后章节未回读到作者修订的场景真相',
    40,
    1000,
  )
  const deduceTrace = await waitForValue(
    () => json(`/ai/runs/${encodeURIComponent(deduceRunId)}/trace?work=${encodeURIComponent(work)}`),
    (trace) => isCompletedWrittenTrace(trace, 's3_patch_chapter_plan') || trace.status === 'failed',
    'deduce trace 未结束',
  )
  assert(isCompletedWrittenTrace(deduceTrace, 's3_patch_chapter_plan'), `deduce 失败:${JSON.stringify(deduceTrace.policy_violations || deduceTrace.error)}`)
  assert(deduceTrace.stage_policy?.phase === 'deduce', '写入未进入 deduce policy')
  assert((deduceTrace.tool_calls || []).some((call) => call.name === 's3_patch_chapter_plan'), 'deduce 未调用唯一允许写工具')
  assert((deduceTrace.tool_calls || []).every((call) => deduceTrace.stage_policy.allowed_tools.includes(call.name)), 'deduce 调用了越权工具')
  assert((deduceTrace.approvals || []).some((approval) => approval.decision === 'approve'), 'deduce 审批结果未落 trace')

  // 刷新后以 UI 重读正典，而不相信本地 React 状态。
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-testid="four-col"]', { timeout: 20000 })
  await selectDeduceStage(page)
  await page.getByTestId('deduce-readonly').getByText(authorRevision, { exact: false }).waitFor({ timeout: 20000 })

  return { work, previewRunId, deduceRunId, chapterTitle: written.title }
})

if (!result.ok || result.errs.length) {
  console.error('DEDUCE_PREVIEW_APPROVAL FAIL', JSON.stringify(result))
  if (process.env.E2E_RESULT_FILE) await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify({ ok: false, ...result }, null, 2))
  // 直接 process.exit(1) 可能截断 PTY 中唯一的失败证据；交给 Node 正常退出。
  process.exitCode = 1
} else if (process.env.E2E_RESULT_FILE) {
  await writeFile(process.env.E2E_RESULT_FILE, JSON.stringify({ ok: true, ...result }, null, 2))
}

console.log('DEDUCE_PREVIEW_APPROVAL OK', JSON.stringify(result))
