import { hasQwenEvidence } from './full_author_acceptance_result.mjs'

const REQUIRED_RELIABILITY_SCENARIOS = [
  'refresh_restart',
  'stop_partial_recovery',
  'sse_replay',
  'concurrent_conflict',
]

function validChapter(row) {
  return Number.isInteger(row?.seq)
    && Number(row?.prose_length) > 0
    && row?.gates?.a === true
    && row?.gates?.b === true
    && row?.gates?.c === true
    && row?.gates?.d === true
    && row?.gates?.c2?.verdict === 'pass'
    && Number(row?.gates?.c2?.events) > 0
    && row?.quality?.status === 'ready'
    && Number(row?.quality?.dimensions) === 10
    && Number(row?.quality?.author_verdicts) === 10
    && row?.quality?.version_bound_to_final === true
    && Array.isArray(row?.model_evidence)
    && row.model_evidence.length === 20
    && row.model_evidence.every(hasQwenEvidence)
}

/**
 * 长程验收的纯结案判定。只读已产出的真人路径证据，绝不写入作品。
 */
export function buildLongformAcceptanceReport(input = {}) {
  const reasons = []
  const target = Number(input.target) || 50000
  const matrix = Array.isArray(input.chapter_matrix) ? input.chapter_matrix : []
  const expectedSequences = Array.from({ length: 20 }, (_, index) => index + 1)

  if (typeof input.work !== 'string' || !input.work.trim()) reasons.push('缺少隔离作品 work')
  if (Number(input.word_count) < target) reasons.push(`SurrealDB 回读字数不足 ${target}`)
  if (Number(input.chapter_count) < 20) reasons.push('章节数不足二十章')
  if (matrix.length < 20) reasons.push('缺少二十章章节矩阵')
  for (const seq of expectedSequences) {
    const row = matrix.find((item) => Number(item?.seq) === seq)
    if (!validChapter(row)) reasons.push(`第${seq}章 Gate A/B/C 或十维质量未完成`)
  }

  const contract = input.quality_contract || {}
  if (contract.approved !== true || contract.all_fields_filled !== true || contract.author_weight_dominant !== true) {
    reasons.push('质量合同全字段、批准态或作者权重未验证')
  }
  if (input.reference_consumed !== true) reasons.push('参考作品抽象技法消费未验证')
  if (input.material_consumed !== true) reasons.push('素材作者消费未验证')

  const trend = Array.isArray(input.quality_trend) ? input.quality_trend : []
  if (trend.length < 20 || expectedSequences.some((seq) => !trend.some((item) => Number(item?.seq) === seq && Number(item?.score) > 0))) {
    reasons.push('二十章质量趋势不完整')
  }
  const reliability = input.reliability || {}
  for (const scenario of REQUIRED_RELIABILITY_SCENARIOS) {
    if (reliability[scenario] !== true) reasons.push(`可靠性场景未通过: ${scenario}`)
  }
  const evidence = Array.isArray(input.model_evidence) ? input.model_evidence : []
  if (!evidence.some(hasQwenEvidence)) reasons.push('缺少真实 TokenPlan/Qwen 模型证据')

  return {
    ok: reasons.length === 0,
    work: typeof input.work === 'string' ? input.work : '',
    target,
    word_count: Number(input.word_count) || 0,
    chapter_count: Number(input.chapter_count) || 0,
    chapter_matrix: matrix,
    reasons,
  }
}
