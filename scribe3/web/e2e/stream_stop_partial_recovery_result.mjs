import { writeJsonArtifact } from './result_artifact.mjs'

function stringList(value) {
  return Array.isArray(value) ? value.map(String) : []
}

export async function persistStreamStopResult(path, result) {
  if (!path) return
  await writeJsonArtifact(path, result)
}

/**
 * 正文阶段的流式正文可能显示在右侧对话气泡，也可能已进入中区草稿卡。
 * 两者都是作者在真实 UI 中可见的生成结果；选择较长者供验收检查首字到达。
 */
export function visibleGeneratedText({ chatText = '', proposalText = '' } = {}) {
  const chat = String(chatText || '').trim()
  const proposal = String(proposalText || '').trim()
  if (proposal && (!chat || chat === '主编在思考…' || proposal.length >= chat.length)) return proposal
  return chat
}

export function buildStreamStopResult(raw) {
  const result = raw && typeof raw === 'object' ? raw : {}
  const errs = stringList(result.errs)
  const failedResponses = Array.isArray(result.failedResponses) ? result.failedResponses : []
  const writeResponses = Array.isArray(result.writeResponses) ? result.writeResponses : []
  return {
    ...result,
    ok: result.ok === true,
    errs,
    failedResponses,
    writeResponses,
    passed: result.ok === true
      && errs.length === 0
      && failedResponses.length === 0
      && writeResponses.length > 0
      && writeResponses.every((status) => status === 200),
  }
}

function withEvidence(raw, evidence) {
  const result = raw && typeof raw === 'object' ? raw : {}
  const diagnostics = evidence && typeof evidence === 'object' ? evidence : {}
  return { ...result, ...diagnostics }
}

export async function captureStreamStopResult(execute, evidence) {
  try {
    return buildStreamStopResult(withEvidence(await execute(), evidence))
  } catch (error) {
    return buildStreamStopResult(withEvidence({
      ok: false,
      err: error instanceof Error ? error.message : String(error),
      errs: [],
    }, evidence))
  }
}

export async function settleObservedRequest(requestPromise) {
  try {
    return { request: await requestPromise, error: null }
  } catch (error) {
    return {
      request: null,
      error: error instanceof Error ? error.message : String(error),
    }
  }
}
