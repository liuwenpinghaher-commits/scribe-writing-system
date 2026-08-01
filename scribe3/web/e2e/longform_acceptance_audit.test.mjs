import assert from 'node:assert/strict'
import test from 'node:test'
import { collectLongformAcceptanceInput } from './longform_acceptance_audit.mjs'

const trace = {
  provider: 'qwen', model: 'qwen3.8-max-preview',
  provider_request_id: 'chatcmpl-real', usage: { prompt_tokens: 3, completion_tokens: 7 },
}

function evaluation() {
  return {
    status: 'ready',
    chapter_version_ids: ['chapter_version:final-1'],
    weights: { author: 0.6, system: 0.25, reference: 0.15 },
    dimensions: Array.from({ length: 10 }, (_, index) => ({
      dimension: `维度${index + 1}`,
      decision_index: 4.2,
      system: { score: 4 }, reference: { score: 4 },
      author: { score: 5, decision: 'accept', reason: '作者已审阅并作出裁决' },
    })),
  }
}

function gates(seq) {
  return {
    gate_a: { ok: true }, gate_b: { ok: true }, gate_d: { ok: true },
    gate_c_det: { ok: true, checks: [{ id: 'C2', verdict: 'pass', evidence: { events: 3 } }] },
    seq,
  }
}

function fakeRead(path) {
  if (path === '/works') return [{ slug: 'book_longform', word_count: 50000, chapter_count: 20 }]
  if (path === '/references?work=book_longform') return [{ reference_work_id: 'ref-1' }]
  if (path.startsWith('/chapter?')) return { prose: '甲'.repeat(2500) }
  if (path.startsWith('/chapter-versions?')) return [{ id: 'final-1', stage: 'final' }]
  if (path.startsWith('/craft-gates?')) return gates(Number(new URLSearchParams(path.split('?')[1]).get('seq')))
  if (path.startsWith('/quality/evaluation-traces?')) return Array.from({ length: 20 }, () => trace)
  if (path.startsWith('/quality/evaluation?')) return evaluation()
  if (path.startsWith('/materials/refs-by-chapter?')) return [{ material_id: 'material-1', via: 'manual_insert' }]
  if (path.startsWith('/quality/reference-craft-uses?')) return [{ reference_fingerprint_ids: ['fp-1'], mechanism_ids: ['m-1'] }]
  throw new Error(`未建模的只读路径: ${path}`)
}

test('只读审计逐章收集 Gate A/B/C/D、C2 事件、质量裁决和真实 TokenPlan trace', async () => {
  const result = await collectLongformAcceptanceInput({
    work: 'book_longform', read: async (path) => fakeRead(path),
    reliability: { refresh_restart: true, stop_partial_recovery: true, sse_replay: true, concurrent_conflict: true },
    quality_contract: { approved: true, all_fields_filled: true, author_weight_dominant: true },
  })

  assert.equal(result.word_count, 50000)
  assert.equal(result.chapter_matrix.length, 20)
  assert.deepEqual(result.chapter_matrix[0].gates.c2, { verdict: 'pass', events: 3 })
  assert.equal(result.chapter_matrix.every((row) => row.quality.author_verdicts === 10), true)
  assert.equal(result.chapter_matrix.every((row) => row.model_evidence.length === 20), true)
  assert.equal(result.chapter_matrix.every((row) => row.quality.version_bound_to_final === true), true)
  assert.equal(result.reference_consumed, true)
  assert.equal(result.material_consumed, true)
})

test('书库首次未加载统计时，长程审计在逐章只读打开作品后必须刷新统计', async () => {
  let workReads = 0
  const result = await collectLongformAcceptanceInput({
    work: 'book_lazy_stats',
    read: async (path) => {
      if (path === '/works') {
        workReads += 1
        return workReads === 1
          ? [{ slug: 'book_lazy_stats', title: '待加载统计书' }]
          : [{ slug: 'book_lazy_stats', word_count: 56766, chapter_count: 20 }]
      }
      return fakeRead(path.replaceAll('book_lazy_stats', 'book_longform'))
    },
    reliability: { refresh_restart: true, stop_partial_recovery: true, sse_replay: true, concurrent_conflict: true },
    quality_contract: { approved: true, all_fields_filled: true, author_weight_dominant: true },
  })

  assert.equal(workReads, 2)
  assert.equal(result.word_count, 56766)
  assert.equal(result.chapter_count, 20)
})
