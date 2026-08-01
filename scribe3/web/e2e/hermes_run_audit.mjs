const QWEN_PROVIDER = 'alibaba-coding-plan'
const QWEN_MODEL = 'qwen3.8-max-preview'

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function parseHermesRunLog(logText, runId) {
  const marker = `\\[${escapeRegExp(runId)}\\]`
  const pattern = new RegExp(
    `${marker}.*?API call #\\d+: model=([^\\s]+) provider=([^\\s]+) `
    + 'in=(\\d+) out=(\\d+) total=(\\d+)',
  )
  return String(logText || '').split('\n').flatMap((line) => {
    const match = line.match(pattern)
    if (!match) return []
    return [{
      provider: match[2],
      model: match[1],
      input_tokens: Number(match[3]),
      output_tokens: Number(match[4]),
      total_tokens: Number(match[5]),
    }]
  })
}

function isTrustedQwenGatewayCall(call) {
  return call?.provider === QWEN_PROVIDER
    && call.model === QWEN_MODEL
    && Number.isFinite(call.total_tokens)
    && call.total_tokens > 0
}

function hasTrustedQwenGatewayCalls(calls) {
  return Array.isArray(calls) && calls.length > 0 && calls.every(isTrustedQwenGatewayCall)
}

export function toHermesRunEvidence({ runId, profile, runUsage, calls }) {
  const gatewayCalls = Array.isArray(calls) ? calls : []
  if (!hasTrustedQwenGatewayCalls(gatewayCalls)) return null
  return {
    evidence_type: 'hermes_gateway_log',
    provider: 'qwen',
    model: QWEN_MODEL,
    run_id: runId,
    profile,
    usage: runUsage,
    gateway_calls: gatewayCalls,
  }
}

function hasPositiveUsage(usage) {
  return Number.isFinite(usage?.total_tokens) && usage.total_tokens > 0
}

export function buildHermesRunEvidence({ runId, trace, logText }) {
  const remoteCompletedPendingAudit = trace?.status === 'remote_completed_pending_audit'
    && trace.response?.status === 'completed'
  if (!trace || (trace.status !== 'completed' && !remoteCompletedPendingAudit)) return null
  const profile = trace.response?.model
  if (typeof profile !== 'string' || !profile.trim()) return null
  if (!hasPositiveUsage(trace.usage)) return null
  const calls = parseHermesRunLog(logText, runId)
  if (!hasTrustedQwenGatewayCalls(calls)) return null
  return toHermesRunEvidence({ runId, profile, runUsage: trace.usage, calls })
}

/**
 * Hermes 在远端完成后，Surreal 审计汇总与本地 agent.log 的落盘可能相差数秒。
 * 这里仅等待两项真实、可审计的证据同时可读；超时仍返回 null，由总控如实拒绝专项。
 */
export async function waitForHermesRunEvidence({
  runId,
  readTrace,
  readLog,
  attempts = 24,
  delayMs = 1250,
} = {}) {
  const totalAttempts = Math.max(1, Number.isInteger(attempts) ? attempts : 1)
  for (let attempt = 0; attempt < totalAttempts; attempt += 1) {
    try {
      const trace = await readTrace()
      const logText = await readLog(trace)
      const evidence = buildHermesRunEvidence({ runId, trace, logText })
      if (evidence) return evidence
    } catch {
      // 证据尚未可读时继续有界重试；不能将 I/O 错误提升成模型证据。
    }
    if (attempt + 1 < totalAttempts && delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, delayMs))
    }
  }
  return null
}
