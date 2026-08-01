import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildHermesRunEvidence,
  parseHermesRunLog,
  toHermesRunEvidence,
  waitForHermesRunEvidence,
} from './hermes_run_audit.mjs'

const qwenLine = (runId, number, input, output, total) => (
  `2026-07-29 12:00:0${number},000 INFO [${runId}] agent.conversation_loop: `
  + `API call #${number}: model=qwen3.8-max-preview provider=alibaba-coding-plan `
  + `in=${input} out=${output} total=${total} latency=1.2s cache=0/0 (0%)`
)

test('按 Hermes Run ID 提取每次真实下游调用，忽略其他运行与消息正文', () => {
  const runId = 'run_qwen'
  const log = [
    '2026-07-29 INFO [run_other] agent.turn_context: msg=不应进入验收产物',
    qwenLine(runId, 1, 11, 7, 18),
    qwenLine(runId, 2, 19, 5, 24),
  ].join('\n')

  assert.deepEqual(parseHermesRunLog(log, runId), [
    { provider: 'alibaba-coding-plan', model: 'qwen3.8-max-preview', input_tokens: 11, output_tokens: 7, total_tokens: 18 },
    { provider: 'alibaba-coding-plan', model: 'qwen3.8-max-preview', input_tokens: 19, output_tokens: 5, total_tokens: 24 },
  ])
})

test('混合或备用网关调用不得被伪装成 Qwen 证据', () => {
  const logText = [
    qwenLine('run_mixed', 1, 11, 7, 18),
    '2026-07-29 INFO [run_mixed] agent.conversation_loop: API call #2: model=kimi-k2-thinking provider=custom in=8 out=3 total=11 latency=1.2s cache=0/0 (0%)',
  ].join('\n')
  const calls = parseHermesRunLog(logText, 'run_mixed')

  const evidence = toHermesRunEvidence({
    runId: 'run_mixed',
    profile: 'scribe3_write',
    runUsage: { input_tokens: 19, output_tokens: 10, total_tokens: 29 },
    calls,
  })

  assert.equal(evidence, null)
  assert.equal(buildHermesRunEvidence({
    runId: 'run_mixed',
    trace: {
      status: 'completed',
      response: { model: 'scribe3_write' },
      usage: { input_tokens: 19, output_tokens: 10, total_tokens: 29 },
    },
    logText,
  }), null)
})

test('仅把已完成且带 profile、usage 与同 Run 网关日志的运行提升为验收证据', () => {
  const evidence = buildHermesRunEvidence({
    runId: 'run_completed',
    trace: {
      status: 'completed',
      response: { model: 'scribe3_write' },
      usage: { input_tokens: 11, output_tokens: 7, total_tokens: 18 },
    },
    logText: qwenLine('run_completed', 1, 11, 7, 18),
  })

  assert.deepEqual(evidence, {
    evidence_type: 'hermes_gateway_log',
    provider: 'qwen',
    model: 'qwen3.8-max-preview',
    run_id: 'run_completed',
    profile: 'scribe3_write',
    usage: { input_tokens: 11, output_tokens: 7, total_tokens: 18 },
    gateway_calls: [
      { provider: 'alibaba-coding-plan', model: 'qwen3.8-max-preview', input_tokens: 11, output_tokens: 7, total_tokens: 18 },
    ],
  })
  assert.equal(buildHermesRunEvidence({ runId: 'run_completed', trace: { status: 'running' }, logText: '' }), null)
})

test('远端已完成但本地审计待汇总的 Run，在响应终态、正用量与同 Run 日志齐备时仍可成为模型证据', () => {
  const evidence = buildHermesRunEvidence({
    runId: 'run_remote_pending',
    trace: {
      status: 'remote_completed_pending_audit',
      response: { status: 'completed', model: 'scribe3_write' },
      usage: { input_tokens: 11, output_tokens: 7, total_tokens: 18 },
    },
    logText: qwenLine('run_remote_pending', 1, 11, 7, 18),
  })

  assert.equal(evidence?.run_id, 'run_remote_pending')
  assert.equal(evidence?.profile, 'scribe3_write')
  assert.deepEqual(evidence?.usage, { input_tokens: 11, output_tokens: 7, total_tokens: 18 })
  assert.equal(evidence?.gateway_calls?.length, 1)
})

test('远端待审计态缺少响应完成态、正用量或同 Run 日志时不得成为模型证据', () => {
  const trace = {
    status: 'remote_completed_pending_audit',
    response: { status: 'completed', model: 'scribe3_write' },
    usage: { input_tokens: 11, output_tokens: 7, total_tokens: 18 },
  }

  assert.equal(buildHermesRunEvidence({
    runId: 'run_remote_not_completed',
    trace: { ...trace, response: { status: 'in_progress', model: 'scribe3_write' } },
    logText: qwenLine('run_remote_not_completed', 1, 11, 7, 18),
  }), null)
  assert.equal(buildHermesRunEvidence({
    runId: 'run_remote_zero_usage',
    trace: { ...trace, usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 } },
    logText: qwenLine('run_remote_zero_usage', 1, 0, 0, 0),
  }), null)
  assert.equal(buildHermesRunEvidence({
    runId: 'run_remote_other_log',
    trace,
    logText: qwenLine('run_other', 1, 11, 7, 18),
  }), null)
  assert.equal(buildHermesRunEvidence({
    runId: 'run_running',
    trace: { ...trace, status: 'running' },
    logText: qwenLine('run_running', 1, 11, 7, 18),
  }), null)
  assert.equal(buildHermesRunEvidence({
    runId: 'run_failed',
    trace: { ...trace, status: 'failed' },
    logText: qwenLine('run_failed', 1, 11, 7, 18),
  }), null)
})

test('任一 Qwen 网关调用没有正用量时不得成为模型证据', () => {
  assert.equal(buildHermesRunEvidence({
    runId: 'run_zero_call_usage',
    trace: {
      status: 'completed',
      response: { model: 'scribe3_write' },
      usage: { input_tokens: 11, output_tokens: 7, total_tokens: 18 },
    },
    logText: [
      qwenLine('run_zero_call_usage', 1, 11, 7, 18),
      qwenLine('run_zero_call_usage', 2, 0, 0, 0),
    ].join('\n'),
  }), null)
})

test('总控等待 Run 审计和网关日志短暂滞后后再判定缺少模型证据', async () => {
  let traceReads = 0
  let logReads = 0
  const evidence = await waitForHermesRunEvidence({
    runId: 'run_lagging',
    readTrace: async () => {
      traceReads += 1
      return traceReads === 1
        ? { status: 'running', response: { model: 'scribe3_write' } }
        : {
          status: 'completed',
          response: { model: 'scribe3_write' },
          usage: { input_tokens: 11, output_tokens: 7, total_tokens: 18 },
        }
    },
    readLog: async () => {
      logReads += 1
      return logReads === 1 ? '' : qwenLine('run_lagging', 1, 11, 7, 18)
    },
    attempts: 3,
    delayMs: 0,
  })

  assert.equal(evidence?.run_id, 'run_lagging')
  assert.equal(evidence?.gateway_calls?.length, 1)
  assert.equal(traceReads, 2)
  assert.equal(logReads, 2)
})
