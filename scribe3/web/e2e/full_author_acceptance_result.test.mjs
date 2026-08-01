import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildAcceptanceReport,
  hasQwenEvidence,
  isCompletedWrittenTrace,
  toDirectQwenEvidence,
} from './full_author_acceptance_result.mjs'

const evidence = {
  provider: 'qwen',
  model: 'qwen3.8-max-preview',
  provider_request_id: 'req-real-1',
  usage: { input_tokens: 12, output_tokens: 34 },
}

const hermesEvidence = {
  evidence_type: 'hermes_gateway_log',
  provider: 'qwen',
  model: 'qwen3.8-max-preview',
  run_id: 'run_hermes-real',
  profile: 'scribe3_write',
  usage: { input_tokens: 120, output_tokens: 34, total_tokens: 154 },
  gateway_calls: [
    { provider: 'alibaba-coding-plan', model: 'qwen3.8-max-preview', input_tokens: 120, output_tokens: 34, total_tokens: 154 },
  ],
}

test('只认可带有真实 TokenPlan/Qwen 审计字段的模型证据', () => {
  assert.equal(hasQwenEvidence(evidence), true)
  assert.equal(hasQwenEvidence({ ...evidence, provider_request_id: '' }), false)
  assert.equal(hasQwenEvidence({ ...evidence, usage: { input_tokens: 0, output_tokens: 0 } }), false)
  assert.equal(hasQwenEvidence({ ...evidence, model: 'other-model' }), false)
  assert.equal(hasQwenEvidence(hermesEvidence), true)
  assert.equal(hasQwenEvidence({
    ...hermesEvidence,
    gateway_calls: [{ ...hermesEvidence.gateway_calls[0], provider: 'custom', model: 'kimi-k2-thinking' }],
  }), false)
})

test('将已持久化的直连写作 trace 收敛为可验收的 TokenPlan 证据，拒绝不完整 trace', () => {
  const trace = {
    provider: {
      provider: 'qwen',
      model: 'qwen3.8-max-preview',
      official: true,
      transport: 'httpx',
    },
    model: 'qwen3.8-max-preview',
    response_id: 'chatcmpl-real-1',
    usage: { prompt_tokens: 12, completion_tokens: 34, total_tokens: 46 },
  }

  assert.deepEqual(toDirectQwenEvidence(trace), {
    provider: 'qwen',
    model: 'qwen3.8-max-preview',
    provider_request_id: 'chatcmpl-real-1',
    usage: trace.usage,
  })
  assert.equal(toDirectQwenEvidence({ ...trace, response_id: '' }), null)
  assert.equal(toDirectQwenEvidence({ ...trace, provider: { ...trace.provider, provider: 'proxy' } }), null)
})

test('已批准的写入 Run 以 Hermes 完成态和 written 工具输出为准，不误读本地审计滞后态', () => {
  const trace = {
    status: 'remote_completed_pending_audit',
    response: { status: 'completed' },
    tool_outputs: [{ tool: 's3_add_item', result_status: 'written', completion: { error: false } }],
  }

  assert.equal(isCompletedWrittenTrace(trace, 's3_add_item'), true)
  assert.equal(isCompletedWrittenTrace({ ...trace, response: { status: 'running' } }, 's3_add_item'), false)
  assert.equal(isCompletedWrittenTrace({ ...trace, tool_outputs: [] }, 's3_add_item'), false)
})

test('总控拒绝没有 artifact、失败结果或缺少模型证据的专项', () => {
  const report = buildAcceptanceReport({
    required: ['quality', 'materials'],
    steps: [
      { id: 'quality', exitCode: 0, artifact: '/tmp/quality.json', result: { ok: true, evidence: [evidence] } },
      { id: 'materials', exitCode: 0, artifact: '', result: { ok: true, evidence: [evidence] } },
    ],
  })

  assert.equal(report.ok, false)
  assert.deepEqual(report.failed_ids, ['materials'])
  assert.match(report.steps[1].reasons.join(' '), /artifact/)
})

test('总控只在所有已声明专项都有成功、artifact 与真实模型证据时通过', () => {
  const report = buildAcceptanceReport({
    required: ['quality', 'materials'],
    steps: [
      { id: 'quality', exitCode: 0, artifact: '/tmp/quality.json', result: { ok: true, evidence: [evidence] } },
      { id: 'materials', exitCode: 0, artifact: '/tmp/materials.json', result: { ok: true, evidence: [evidence] } },
    ],
  })

  assert.equal(report.ok, true)
  assert.deepEqual(report.failed_ids, [])
  assert.equal(report.steps.every((step) => step.ok), true)
})
