import assert from 'node:assert/strict'
import test from 'node:test'
import { buildLongformAcceptanceReport } from './longform_acceptance_result.mjs'

const modelEvidence = {
  provider: 'qwen',
  model: 'qwen3.8-max-preview',
  provider_request_id: 'chatcmpl-real-longform',
  usage: { prompt_tokens: 120, completion_tokens: 880, total_tokens: 1000 },
}

function chapterMatrix() {
  return Array.from({ length: 20 }, (_, index) => ({
    seq: index + 1,
    prose_length: 2500,
    gates: { a: true, b: true, c: true, d: true, c2: { verdict: 'pass', events: 1 } },
    quality: { status: 'ready', dimensions: 10, author_verdicts: 10, version_bound_to_final: true },
    model_evidence: Array.from({ length: 20 }, () => modelEvidence),
  }))
}

function validInput() {
  return {
    work: 'book_longform_real',
    target: 50000,
    word_count: 50000,
    chapter_count: 20,
    chapter_matrix: chapterMatrix(),
    quality_contract: { approved: true, all_fields_filled: true, author_weight_dominant: true },
    reference_consumed: true,
    material_consumed: true,
    quality_trend: Array.from({ length: 20 }, (_, index) => ({ seq: index + 1, score: 4 })),
    reliability: {
      refresh_restart: true,
      stop_partial_recovery: true,
      sse_replay: true,
      concurrent_conflict: true,
    },
    model_evidence: [modelEvidence],
  }
}

test('长程结案只认可二十章、五万字、逐章 Gate/质量与真实 TokenPlan 证据齐全的作品', () => {
  const report = buildLongformAcceptanceReport(validInput())

  assert.equal(report.ok, true)
  assert.deepEqual(report.reasons, [])
  assert.equal(report.chapter_matrix.length, 20)
})

test('长程结案拒绝把五万字替代逐章质量、素材、可靠性或真实模型证据', () => {
  for (const [label, patch] of [
    ['少于二十章', { chapter_count: 19 }],
    ['章节 Gate C 未过', { chapter_matrix: chapterMatrix().map((row, index) => index === 4 ? { ...row, gates: { ...row.gates, c: false } } : row) }],
    ['章节质量未就绪', { chapter_matrix: chapterMatrix().map((row, index) => index === 7 ? { ...row, quality: { status: 'running', dimensions: 0 } } : row) }],
    ['素材未消费', { material_consumed: false }],
    ['取消恢复未验证', { reliability: { ...validInput().reliability, stop_partial_recovery: false } }],
    ['没有真实模型证据', { model_evidence: [] }],
  ]) {
    const report = buildLongformAcceptanceReport({ ...validInput(), ...patch })
    assert.equal(report.ok, false, label)
    assert.ok(report.reasons.length > 0, label)
  }
})

test('长程结案拒绝缺少 Gate D、持久化事件 C2、十维作者裁决或逐章 TokenPlan 证据的章节', () => {
  const incomplete = chapterMatrix()
  const cases = [
    ['Gate D', 1, incomplete.map((row, index) => index === 0 ? { ...row, gates: { ...row.gates, d: false } } : row)],
    ['C2 事件', 2, incomplete.map((row, index) => index === 1 ? { ...row, gates: { ...row.gates, c2: { verdict: 'skip', events: 0 } } } : row)],
    ['作者裁决', 3, incomplete.map((row, index) => index === 2 ? { ...row, quality: { ...row.quality, author_verdicts: 9 } } : row)],
    ['逐章模型证据', 4, incomplete.map((row, index) => index === 3 ? { ...row, model_evidence: [] } : row)],
    ['冻结版本绑定', 5, incomplete.map((row, index) => index === 4 ? { ...row, quality: { ...row.quality, version_bound_to_final: false } } : row)],
  ]
  for (const [label, seq, chapter_matrix] of cases) {
    const report = buildLongformAcceptanceReport({ ...validInput(), chapter_matrix })
    assert.equal(report.ok, false, label)
    assert.match(report.reasons.join(' '), new RegExp(`第${seq}章`), label)
  }
})
