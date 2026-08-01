import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import {
  buildStreamStopResult,
  captureStreamStopResult,
  persistStreamStopResult,
  settleObservedRequest,
  visibleGeneratedText,
} from './stream_stop_partial_recovery_result.mjs'

test('结果工件的父目录不存在时仍会创建并写入结构化结果', async () => {
  const root = await mkdtemp(join(tmpdir(), 'scribe3-stream-result-'))
  const target = join(root, 'missing', 'nested', 'stream-recovery.json')
  try {
    await persistStreamStopResult(target, { ok: true, work: 'book_test' })
    assert.deepEqual(JSON.parse(await readFile(target, 'utf8')), {
      ok: true,
      work: 'book_test',
    })
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('正文阶段将右侧流式气泡或中区草稿卡中任一可见文本视为作者已收到的首字', () => {
  assert.equal(visibleGeneratedText({ chatText: '右侧首字', proposalText: '' }), '右侧首字')
  assert.equal(visibleGeneratedText({ chatText: '主编在思考…', proposalText: '中区草稿首字' }), '中区草稿首字')
  assert.equal(visibleGeneratedText({ chatText: '右侧较短', proposalText: '中区草稿更长的可见文本' }), '中区草稿更长的可见文本')
})

test('业务异常时仍保留原始错误并生成可序列化失败报告', () => {
  const report = buildStreamStopResult({
    ok: false,
    err: '停止后未恢复为作者可见的部分稿提案',
    errs: ['CONSOLE unexpected stream close'],
  })

  assert.deepEqual(report, {
    ok: false,
    err: '停止后未恢复为作者可见的部分稿提案',
    errs: ['CONSOLE unexpected stream close'],
    failedResponses: [],
    writeResponses: [],
    passed: false,
  })
})

test('仅在所有浏览器与写接口证据均正常时通过', () => {
  assert.equal(buildStreamStopResult({
    ok: true,
    errs: [],
    failedResponses: [],
    writeResponses: [200],
  }).passed, true)

  assert.equal(buildStreamStopResult({
    ok: true,
    errs: [],
    failedResponses: [],
    writeResponses: [],
  }).passed, false)
})

test('顶层异常也归档为结构化失败证据', async () => {
  const report = await captureStreamStopResult(async () => {
    throw new Error('page.waitForRequest: Timeout 30000ms exceeded')
  })

  assert.equal(report.ok, false)
  assert.equal(report.passed, false)
  assert.match(report.err, /page\.waitForRequest/)
  assert.deepEqual(report.errs, [])
})

test('页面执行普通失败时，落盘报告仍保留已收集的诊断证据', async () => {
  const root = await mkdtemp(join(tmpdir(), 'scribe3-stream-failure-evidence-'))
  const target = join(root, 'stream-recovery.json')
  const evidence = {
    work: 'stream_stop_failure_book',
    chatRequests: ['/chat/write'],
    writeResponses: [502],
    failedResponses: [{ path: '/chat/write', status: 502 }],
    reload: { beforeOpenFour: 1, afterOpenFour: null },
  }
  try {
    // 模拟 withPage 已捕获页面异常后的普通返回，而非顶层 throw。
    const report = await captureStreamStopResult(async () => ({
      ok: false,
      err: '停止后未恢复为作者可见的部分稿提案',
      errs: ['PAGEERR stream closed'],
    }), evidence)
    await persistStreamStopResult(target, report)

    assert.deepEqual(JSON.parse(await readFile(target, 'utf8')), {
      ok: false,
      err: '停止后未恢复为作者可见的部分稿提案',
      errs: ['PAGEERR stream closed'],
      ...evidence,
      passed: false,
    })
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('请求观察器超时会保留失败信息而不是形成未处理拒绝', async () => {
  const observed = await settleObservedRequest(Promise.reject(
    new Error('page.waitForRequest: Timeout 30000ms exceeded'),
  ))

  assert.equal(observed.request, null)
  assert.match(observed.error, /Timeout 30000ms/)
})

test('停止操作使用组件声明的无障碍名称“停止生成”', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')
  assert.match(script, /name: '停止生成', exact: true/)
})

test('停止恢复门采用已验证的章节级生成负载，而不是把五万字总目标塞进单次请求', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')
  assert.match(script, /约700字/)
  assert.doesNotMatch(script, /约一万字/)
})

test('TokenPlan 强思考期间停止恢复旅程等待真实首字，而非把 90 秒无正文误判为流式故障', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')

  assert.match(script, /'停止前未收到可见 SSE 文本',[\s\S]{0,280}360,/)
})

test('流式停止旅程不把长期 SSE 连接误判为页面尚未可用', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')

  assert.doesNotMatch(script, /page\.goto\(BASE, \{ waitUntil: 'networkidle'/)
  assert.match(script, /page\.goto\(BASE, \{ waitUntil: 'domcontentloaded'/)
})

test('停止恢复旅程刷新后兼容仍在书内和退回作品库两种真实页面状态', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')
  assert.match(script, /waitFor\(\{ state: 'attached', timeout: 5000 \}\)\.catch\(\(\) => \{\}\)/)
  assert.match(script, /const stillInBook = await page\.getByTestId\('four-col'\)\.count\(\)/)
  assert.match(script, /if \(!stillInBook\)/)
  assert.match(script, /await opener\.waitFor\(\{ state: 'visible', timeout: 30000 \}\)/)
  assert.match(script, /getByTestId\('four-col'\)\.waitFor\(\{ state: 'attached', timeout: 45000 \}\)/)
})

test('停止恢复旅程必须先通过真实 UI+MCP 的 Gate A，不能用裸章绕过正文保存门', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')
  assert.match(script, /async function prepareCraftReadiness/)
  assert.match(script, /s3_set_intent/)
  assert.match(script, /s3_add_character_relation/)
  assert.match(script, /src_oid=role:周岑/)
  assert.match(script, /dst_oid=role:贺钟/)
  assert.match(script, /s3_plant_promise/)
  assert.ok(
    script.indexOf('await prepareCraftReadiness(page, work)') < script.indexOf('const requestSeen'),
    '必须在正文 /chat/write 前完成 Gate A',
  )
})

test('建章模型未调用工具时只作有限、带 Run 身份的重试，不以 API 代写补洞', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')
  assert.match(script, /const observedRuns = \[\]/)
  assert.match(script, /for \(let attempt = 0; attempt < 2; attempt \+= 1\)/)
  assert.match(script, /已审计 Run: \$\{observedRuns\.join\(','\)/)
  assert.doesNotMatch(script, /api\.addChapter|fetch\([^\n]*\/chapters[^\n]*POST/)
})

test('停止恢复专项把所有主编 Run 身份写入结果，供总控回查真实 TokenPlan 证据', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')

  assert.match(script, /const runIds = new Set\(\)/)
  assert.match(script, /run_ids: \[\.\.\.runIds\]/)
  assert.match(script, /recordRun\(await chiefSay/)
})

test('刷新恢复失败时仍归档隔离作品与恢复阶段状态，供真人故障定位', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')

  assert.match(script, /const evidence = \{[\s\S]*work: null[\s\S]*reload: null/)
  assert.match(script, /evidence\.work = work/)
  assert.match(script, /evidence\.reload = \{[\s\S]*beforeOpenFour/)
  assert.match(script, /afterOpenFour/)
})

test('停止恢复旅程必须先完成 Gate B 的大纲、节拍和限知演绎，不能在采用部分稿时才触发保存门', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')
  assert.match(script, /async function prepareChapterScaffold/)
  assert.match(script, /s3_patch_chapter_plan/)
  assert.match(script, /B3Scene/)
  assert.match(script, /B3Deductions/)
  assert.match(script, /async function selectChapterStage/)
  assert.ok(
    script.indexOf('await prepareChapterScaffold(page, work)') < script.lastIndexOf('await ensureChiefVisible(page'),
    '必须在进入正文写作前完成 Gate B',
  )
})

test('长程真实验收在每个 Gate B MCP 请求前后写入不含正文的阶段进度工件', async () => {
  const script = await readFile(new URL('./stream_stop_partial_recovery.mjs', import.meta.url), 'utf8')

  assert.match(script, /function checkpoint\(stage, detail = \{\}\)/)
  assert.match(script, /checkpoint\('gate-b-before-run'/)
  assert.match(script, /checkpoint\('gate-b-after-run'/)
  assert.match(script, /in_progress: true/)
})
