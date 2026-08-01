import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('质量真人旅程不把开发服务器的长连接当作页面可用条件', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  assert.equal(source.includes("page.goto(BASE, { waitUntil: 'networkidle'"), false)
  assert.equal(source.includes("page.goto(BASE, { waitUntil: 'domcontentloaded'"), true)
})

test('质量真人旅程可写出总控读取的结构化结果 artifact', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')

  assert.match(source, /E2E_RESULT_FILE/)
  assert.match(source, /writeFileSync\(target, JSON\.stringify\(report, null, 2\)\)/)
})

test('质量真人旅程将浏览器请求失败与 HTTP 404 分别写入 artifact，供根因判定', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')

  assert.match(source, /browser_failed_requests/)
  assert.match(source, /browserHttp404s\.failed_requests/)
})

test('质量旅程将主编轮询已证实完成的 Run 传给 SSE 分类器，避免误报主动关闭', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')

  assert.match(source, /async function chiefSayWithCompletionEvidence/)
  assert.match(source, /\/ai\/runs\/\$\{encodeURIComponent\(run\.id\)\}\/trace/)
  assert.match(source, /verifiedCompletedRunIds\.add\(run\.id\)/)
})

test('质量旅程在关闭浏览器前解绑网络探针，避免把 teardown 误写为请求失败', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const finallyBlock = source.slice(source.lastIndexOf('} finally {'))

  assert.match(finallyBlock, /browserHttp404s\.detach\?\.\(\)/)
  assert.ok(finallyBlock.indexOf('browserHttp404s.detach?.()') < finallyBlock.indexOf('await browser?.close()'))
})

test('质量旅程在浏览器 teardown 前写出最终 artifact，关闭异常也不能抹掉根因', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const finallyBlock = source.slice(source.lastIndexOf('} finally {'))

  assert.ok(finallyBlock.indexOf('persistReport()') < finallyBlock.indexOf('await browser?.close()'))
})

test('质量真人旅程在每个阶段即时落盘，并在可捕获终止时保留最后阶段', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')

  assert.match(source, /function persistReport\(/)
  assert.match(source, /report\.last_stage = name/)
  assert.match(source, /persistReport\(\)/)
  assert.match(source, /process\.once\('SIGTERM'/)
})

test('质量真人旅程在 Playwright 等待期间保持 Node 事件循环，不能静默提前退出', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')

  assert.match(source, /const eventLoopKeepAlive = setInterval\(/)
  assert.match(source, /clearInterval\(eventLoopKeepAlive\)/)
})

test('质量真人旅程为未显式声明时限的 UI 动作设定全局上限，避免无阶段心跳地卡住', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const startup = source.slice(source.indexOf('try {'), source.indexOf('await openBook(page)'))

  assert.match(source, /const E2E_UI_ACTION_TIMEOUT_MS = 60_000/)
  assert.match(startup, /page\.setDefaultTimeout\(E2E_UI_ACTION_TIMEOUT_MS\)/)
})

test('质量旅程切换章节阶段前等待目录章节和目标标签可见，避免合同视图切回手稿的竞态', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const stage = source.slice(source.indexOf('async function selectChapterStage'), source.indexOf('async function selectChapterFinal'))

  assert.match(stage, /chapter\.waitFor\(\{ state: 'visible', timeout: 30000 \}\)/)
  assert.match(stage, /tab\.waitFor\(\{ state: 'visible', timeout: 30000 \}\)/)
})

test('Gate A4 用规范角色 OID 提交关系，不能把展示名当作关系端点', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf("A4:")
  const end = source.indexOf("A5:", start)
  const prompt = source.slice(start, end)

  assert.match(prompt, /src_oid=role:周岑/)
  assert.match(prompt, /dst_oid=role:贺钟/)
  assert.match(prompt, /relation=custom/)
  assert.match(prompt, /since_chapter=1/)
})

test('质量真人旅程要求 C2 已有事件且因果完整，不能把 skip 当作通过', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')

  assert.match(source, /async function verifyStrictCausalGate\(/)
  assert.match(source, /\/events\?chapter=\$\{CHAPTER_SEQ\}&work=/)
  assert.match(source, /c2\?\.verdict === 'pass'/)
  assert.match(source, /await verifyStrictCausalGate\(\)/)
})

test('质量真人旅程为异步知识抽取保留足够的严格 C2 回读窗口', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  assert.match(source, /const STRICT_C2_WAIT_MS = 420_000/)
  assert.match(source, /Date\.now\(\) \+ STRICT_C2_WAIT_MS/)
})

test('质量真人旅程的等待上限覆盖后端二十条真实调用的最坏恢复窗口', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function waitForQualityReady')
  const end = source.indexOf('function assertQwen', start)
  const wait = source.slice(start, end)

  // 单维硬截止 180 秒、两路并行、20 条系统/参考判断、两次 JSON 修复
  // 和安全余量的理论恢复上限至少约 95 分钟；作者可见验收不能抢先报超时。
  // 作者可见验收不得在该上限之前自行报超时。
  assert.match(wait, /Date\.now\(\) \+ 5_700_000/)
})

test('质量真人旅程必须在草稿阶段请求正文提案，不能把 final 正文页误当写作槽', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function selectChapterFinal')
  const end = source.indexOf('// 正文不是质量系统的第一步', start)
  const selection = source.slice(start, end)

  assert.match(selection, /selectChapterStage\(page, '草稿'\)/)
  assert.doesNotMatch(selection, /selectChapterStage\(page, '正文'\)/)
})

test('正文生成前必须记录前置回读和提案请求边界，卡住时不能只停在 Gate B', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function ensureOriginalProse')
  const end = source.indexOf('async function verifyStrictCausalGate', start)
  const prose = source.slice(start, end)

  assert.match(prose, /正文生成前置回读/)
  assert.match(prose, /正文提案请求已发起/)
  assert.match(prose, /正文提案已返回/)
})

test('五万字长程验收的逐章正文必须直接达到足量，不能先以短稿评价再另行扩写', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function ensureOriginalProse')
  const end = source.indexOf('async function verifyStrictCausalGate', start)
  const prose = source.slice(start, end)

  assert.match(source, /const E2E_MIN_PROSE_LENGTH = Number\(process\.env\.E2E_MIN_PROSE_LENGTH \|\| 2_800\)/)
  assert.match(prose, /length >= E2E_MIN_PROSE_LENGTH/)
  assert.match(prose, /至少 \$\{E2E_MIN_PROSE_LENGTH\} 字/)
  assert.match(prose, /正文未达到本轮长程验收最小长度/)
})

test('质量作业可重试失败时，旅程必须回到质量审阅并等待失败状态卡再点击重试', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function waitForQualityReady')
  const end = source.indexOf('function assertQwen', start)
  const wait = source.slice(start, end)

  assert.match(wait, /quality-job-retryable-failed/)
  assert.match(wait, /name: '质量审阅'/)
  assert.match(wait, /重试本次冻结评价/)
})

test('已在质量审阅页时，重试流程优先使用可见失败卡而不重复强制导航', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf("if (qualityJobStatus.status === 'retryable_failed'")
  const end = source.indexOf("if (qualityJobStatus.status === 'retryable_failed' ||", start)
  const retry = source.slice(start, end)
  assert.match(retry, /retryCard\.isVisible\(\)/)
  assert.match(retry, /if \(!\(await retryCard\.isVisible\(\)\.catch\(\(\) => false\)\)\)/)
})

test('参考导入工作台等待“已直接打开”或“工作台入口”任一合法落点，不能抢点不存在的入口', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function openReferenceWorkspace')
  const end = source.indexOf('async function createAndApproveReference', start)
  const workspace = source.slice(start, end)
  assert.match(workspace, /page\.waitForFunction\(/)
  assert.match(workspace, /参考作品工作台/)
  // 真实入口的可访问名称来自 aria-label，视觉文案还带有“打开”后缀。
  // 不能只按 textContent 精确相等判断，否则二级入口已出现也会一直等待到超时。
  assert.match(workspace, /node\.getAttribute\('aria-label'\) === '参考作品工作台'/)
  assert.match(workspace, /titleInput\.isVisible\(\)/)
})

test('质量重试从其它工作台返回时，直接进入质量审阅，不绕经无关的参考导入工作台', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf("if (!(await retryCard.isVisible")
  const end = source.indexOf("await retryCard.waitFor", start)
  const retry = source.slice(start, end)

  assert.match(retry, /getByRole\('button', \{ name: '参考作品', exact: true \}\)\.click\(\)/)
  assert.match(retry, /const qualityReview = page\.getByRole\('button', \{ name: '质量审阅', exact: true \}\)/)
  assert.match(retry, /waitFor\(\{ state: 'visible', timeout: 30000 \}\)/)
  assert.doesNotMatch(retry, /openReferenceWorkspace\(page\)/)
})

test('质量重试遇到参考作品二级入口时可进入质量审阅', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function waitForQualityReady')
  const end = source.indexOf('function assertQwen', start)
  const retry = source.slice(start, end)

  assert.match(retry, /参考作品工作台/)
  assert.match(retry, /质量审阅/)
})

test('质量重试在当前页面已有质量审阅入口时不依赖参考工作台导航', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf("if (!(await retryCard.isVisible")
  const end = source.indexOf("await retryCard.waitFor", start)
  const retry = source.slice(start, end)

  assert.match(retry, /if \(await qualityReview\.isVisible\(\)\.catch\(\(\) => false\)\)/)
})

test('指定既有作品时先经作者可见的作品库切书，不依赖新页面的上次打开作品', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('// 标题是作者可重复使用的展示字段')
  const end = source.indexOf("step('打开隔离书')", start)
  const openExisting = source.slice(start, end)

  assert.match(openExisting, /\[data-testid="app-rail"\].*title="切换 \/ 选择作品"/)
  assert.match(openExisting, /await library\.click\(\)/)
  assert.match(openExisting, /await opener\.waitFor\(/)
})

test('质量真人旅程可由环境变量指定任意连续章节，不能把第1章硬编码为长程唯一闭环', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')

  assert.match(source, /const CHAPTER_SEQ = Number\(process\.env\.E2E_CHAPTER_SEQ \|\| 1\)/)
  assert.match(source, /chapter=\$\{CHAPTER_SEQ\}/)
  assert.match(source, /第\$\{CHAPTER_SEQ\}章/)
  assert.match(source, /QUALITY_E2E.*chapter_seq/)
})

test('参考指纹批准只操作本次导入卡片，历史待审指纹不得造成严格定位冲突', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function createAndApproveReference')
  const end = source.indexOf('async function fillEveryContractField', start)
  const reference = source.slice(start, end)

  assert.match(reference, /referenceCard\.getByRole\('button', \{ name: '批准指纹', exact: true \}\)\.click\(\)/)
  assert.doesNotMatch(reference, /await page\.getByRole\('button', \{ name: '批准指纹', exact: true \}\)\.click\(\)/)
})

test('参考作品导入先等待真实 201 响应再回读，避免 UI 点击与落库竞态', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function createAndApproveReference')
  const end = source.indexOf('async function fillEveryContractField', start)
  const reference = source.slice(start, end)

  assert.match(reference, /page\.waitForResponse\(/)
  assert.match(reference, /pathname\.endsWith\('\/references\/import'\)/)
  assert.match(reference, /response\.status\(\) === 201/)
  assert.match(reference, /const importedPayload = await importResponse\.json\(\)/)
  assert.match(reference, /item\.reference_work_id === importedPayload\.reference_work_id/)
})

test('合同批准后等待只读投影稳定，避免批准按钮与权重回读竞态', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function fillEveryContractField')
  const end = source.indexOf('async function selectChapterStage', start)
  const contract = source.slice(start, end)
  assert.match(contract, /for \(let attempt = 0; attempt < 60; attempt\+\+\)/)
  assert.match(contract, /Number\(contract\.weights\?\.author\)/)
  assert.match(contract, /await sleep\(500\)/)
})

test('质量评价导航先确认参考工作台已打开，再查找质量审阅表单', () => {
  const source = readFileSync(new URL('./quality_reference_author_journey.mjs', import.meta.url), 'utf8')
  const start = source.indexOf('async function createEvaluationAndAuthorVerdicts')
  const end = source.indexOf('async function verifyExecutionEvidence', start)
  const evaluation = source.slice(start, end)

  assert.match(evaluation, /await openReferenceWorkspace\(page\)/)
  assert.match(evaluation, /const qualityReview = page\.getByRole\('button', \{ name: '质量审阅', exact: true \}\)/)
  assert.match(evaluation, /await qualityReview\.waitFor\(\{ state: 'visible', timeout: 30000 \}\)/)
  assert.ok(evaluation.indexOf('await openReferenceWorkspace(page)') < evaluation.indexOf("name: '质量审阅'"))
})
