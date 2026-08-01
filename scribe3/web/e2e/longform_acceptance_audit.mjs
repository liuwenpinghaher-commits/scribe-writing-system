// 长程验收的只读取证器：把 SurrealDB/质量链的当前事实收敛成严格结案输入。
// 它不创建章节、不发起模型调用、不写入任何作品；所有世界写应已由网页→Hermes/MCP→作者批准完成。
import { hasQwenEvidence } from './full_author_acceptance_result.mjs'

function array(value) {
  return Array.isArray(value) ? value : []
}

function c2From(gates) {
  const check = array(gates?.gate_c_det?.checks).find((item) => item?.id === 'C2')
  return {
    verdict: typeof check?.verdict === 'string' ? check.verdict : 'missing',
    events: Number(check?.evidence?.events) || 0,
  }
}

function proseLength(chapter) {
  const prose = chapter?.prose ?? chapter?.body ?? chapter?.content ?? ''
  return typeof prose === 'string' ? prose.replace(/\s/g, '').length : 0
}

function authorVerdictCount(evaluation) {
  return array(evaluation?.dimensions).filter((dimension) => (
    Number.isFinite(Number(dimension?.author?.score))
    && typeof dimension?.author?.decision === 'string' && dimension.author.decision.trim()
    && typeof dimension?.author?.reason === 'string' && dimension.author.reason.trim()
    && Number.isFinite(Number(dimension?.decision_index))
  )).length
}

function evaluationBindsLatestFinalVersion(evaluation, versions) {
  const latestFinalId = array(versions).find((version) => version?.stage === 'final')?.id
  if (latestFinalId == null || String(latestFinalId).trim() === '') return false
  const expected = String(latestFinalId)
  return array(evaluation?.chapter_version_ids).some((versionId) => {
    const actual = String(versionId || '')
    return actual === expected || actual === `chapter_version:${expected}`
  })
}

function trendScore(evaluation) {
  const indices = array(evaluation?.dimensions)
    .map((dimension) => Number(dimension?.decision_index))
    .filter(Number.isFinite)
  return indices.length === 10
    ? indices.reduce((sum, score) => sum + score, 0) / indices.length
    : 0
}

function asWorkStats(payload, work) {
  const rows = Array.isArray(payload) ? payload : array(payload?.works)
  return rows.find((row) => row?.slug === work) || null
}

/**
 * 收集完整长程验收输入。read 只允许对应既有 GET 路由的只读函数，便于以真实 HTTP
 * 或确定性夹具运行；任一读取失败都应由调用方将验收标记为失败。
 */
export async function collectLongformAcceptanceInput({
  work,
  read,
  target = 50000,
  quality_contract = {},
  reliability = {},
} = {}) {
  if (typeof work !== 'string' || !work.trim()) throw new Error('缺少 work')
  if (typeof read !== 'function') throw new Error('缺少只读 read 函数')
  const encodedWork = encodeURIComponent(work)
  // /works 对未加载的作品会故意省略统计，避免书库为每本书建连接；先保留这份
  // 可能不完整的行，逐章 GET 会打开目标 work 后再刷新一次，不能把“未加载”误判为 0。
  const initialStats = asWorkStats(await read('/works'), work) || {}
  const [references, matrices] = await Promise.all([
    read(`/references?work=${encodedWork}`),
    Promise.all(Array.from({ length: 20 }, async (_, index) => {
      const seq = index + 1
      const query = `work=${encodedWork}&seq=${seq}`
      const [chapter, versions, gates, evaluation, traces, materialRefs, referenceUses] = await Promise.all([
        read(`/chapter?${query}`),
        read(`/chapter-versions?${query}`),
        read(`/craft-gates?${query}`),
        read(`/quality/evaluation?${query}`),
        read(`/quality/evaluation-traces?${query}`),
        read(`/materials/refs-by-chapter?chapter=${seq}&work=${encodedWork}`),
        read(`/quality/reference-craft-uses?chapter=${seq}&work=${encodedWork}`),
      ])
      const model_evidence = array(traces).filter(hasQwenEvidence)
      return {
        seq,
        prose_length: proseLength(chapter),
        gates: {
          a: gates?.gate_a?.ok === true,
          b: gates?.gate_b?.ok === true,
          c: gates?.gate_c_det?.ok === true,
          d: gates?.gate_d?.ok === true,
          c2: c2From(gates),
        },
        quality: {
          status: evaluation?.status,
          dimensions: array(evaluation?.dimensions).length,
          author_verdicts: authorVerdictCount(evaluation),
          version_bound_to_final: evaluationBindsLatestFinalVersion(evaluation, versions),
        },
        model_evidence,
        material_refs: array(materialRefs),
        reference_uses: array(referenceUses),
        decision_index: trendScore(evaluation),
      }
    })),
  ])
  const allEvidence = matrices.flatMap((row) => row.model_evidence)
  const stats = asWorkStats(await read('/works'), work) || initialStats
  return {
    work,
    target: Number(target) || 50000,
    word_count: Number(stats.word_count) || 0,
    chapter_count: Number(stats.chapter_count) || 0,
    chapter_matrix: matrices,
    quality_contract,
    reference_consumed: array(references).length > 0
      && matrices.some((row) => row.reference_uses.length > 0),
    material_consumed: matrices.some((row) => row.material_refs.some((ref) => ref?.via === 'manual_insert')),
    quality_trend: matrices.map((row) => ({ seq: row.seq, score: row.decision_index })),
    reliability,
    model_evidence: allEvidence,
  }
}
