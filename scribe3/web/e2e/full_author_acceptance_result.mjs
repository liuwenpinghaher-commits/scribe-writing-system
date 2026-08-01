const QWEN_PROVIDER = 'qwen'
const QWEN_MODEL = 'qwen3.8-max-preview'

function hasPositiveUsage(usage) {
  return Boolean(usage && typeof usage === 'object'
    && Object.values(usage).some((value) => typeof value === 'number' && value > 0))
}

function hasHermesGatewayQwenEvidence(record) {
  const calls = Array.isArray(record?.gateway_calls) ? record.gateway_calls : []
  return record?.evidence_type === 'hermes_gateway_log'
    && typeof record.run_id === 'string' && record.run_id.trim()
    && typeof record.profile === 'string' && record.profile.trim()
    && hasPositiveUsage(record.usage)
    && calls.length > 0
    && calls.every((call) => call
      && call.provider === 'alibaba-coding-plan'
      && call.model === QWEN_MODEL
      && hasPositiveUsage(call))
}

export function hasQwenEvidence(record) {
  const isDirectQwenEvidence = Boolean(record
    && record.provider === QWEN_PROVIDER
    && record.model === QWEN_MODEL
    && typeof record.provider_request_id === 'string'
    && record.provider_request_id.trim()
    && hasPositiveUsage(record.usage))
  const isHermesQwenEvidence = Boolean(record
    && record.provider === QWEN_PROVIDER
    && record.model === QWEN_MODEL
    && hasHermesGatewayQwenEvidence(record))
  return isDirectQwenEvidence || isHermesQwenEvidence
}

// 真实写作响应的审计字段存于 Surreal 回读的 assistant.trace 中；验收工件只保留
// 身份、请求 ID 和用量，不能复制正文或完整上下文。只有能通过同一严格判定的 trace
// 才能被提升为模型证据，缺字段时必须返回 null 而非从配置补造。
export function toDirectQwenEvidence(trace) {
  const identity = trace?.provider
  const record = {
    provider: identity?.provider,
    model: trace?.model || identity?.model,
    provider_request_id: trace?.provider_request_id || trace?.response_id,
    usage: trace?.usage,
  }
  return hasQwenEvidence(record) ? record : null
}

// Hermes 的远端完成态先到，本地审计汇总态会短暂保留 pending。验收写入结果必须
// 以远端已完成 + 对应工具明确 written 为准，不能因这段审计滞后误报失败。
export function isCompletedWrittenTrace(trace, tool) {
  return trace?.response?.status === 'completed'
    && Array.isArray(trace?.tool_outputs)
    && trace.tool_outputs.some((output) => output?.tool === tool
      && output?.result_status === 'written'
      && output?.completion?.error !== true)
}

function normalizeStep(requiredIds, raw) {
  const step = raw && typeof raw === 'object' ? raw : {}
  const result = step.result && typeof step.result === 'object' ? step.result : {}
  const evidence = Array.isArray(result.evidence) ? result.evidence : []
  const reasons = []
  if (!requiredIds.has(step.id)) reasons.push('未声明的专项')
  if (!Number.isInteger(step.exitCode) || step.exitCode !== 0) reasons.push('子进程未以 0 退出')
  if (result.ok !== true) reasons.push('专项结果未显式 ok:true')
  if (typeof step.artifact !== 'string' || !step.artifact.trim()) reasons.push('缺少结构化 artifact')
  if (!evidence.some(hasQwenEvidence)) reasons.push('缺少真实 TokenPlan/Qwen 模型证据')
  return {
    id: typeof step.id === 'string' ? step.id : '',
    ok: reasons.length === 0,
    artifact: typeof step.artifact === 'string' ? step.artifact : '',
    reasons,
  }
}

export function buildAcceptanceReport({ required = [], steps = [] } = {}) {
  const requiredIds = new Set(required)
  const source = new Map((Array.isArray(steps) ? steps : []).map((step) => [step?.id, step]))
  const normalized = [...requiredIds].map((id) => normalizeStep(requiredIds, source.get(id) || { id }))
  const failedIds = normalized.filter((step) => !step.ok).map((step) => step.id)
  return {
    ok: failedIds.length === 0,
    required: [...requiredIds],
    steps: normalized,
    failed_ids: failedIds,
  }
}
