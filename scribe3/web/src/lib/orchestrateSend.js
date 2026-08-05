/**
 * 统一编排发送前置：调用 shipped /orchestration/resolve，决定通道与跟焦。
 * 正则 shouldUseHermesRun 仅作离线弱回退，不再是唯一真理。
 */
import { api } from '../api'
import { shouldUseHermesRun, hermesRunInstructions } from './hermesRunIntent'
import { applyUiEvents } from './uiDirective'

/**
 * @param {string} message
 * @param {{ chapter?: number|null, phase?: string, action?: string, journey_next_domain?: string, focus_hint?: object, onSel?: Function, applyFocus?: boolean }} opts
 * @returns {Promise<{
 *   useWorldWriteRun: boolean,
 *   package: object|null,
 *   uiEvents: array,
 *   channel: string,
 *   instructions: string,
 *   evaluationHint: object|null,
 *   resolveOk: boolean,
 * }>}
 */
export async function orchestrateBeforeSend(message, opts = {}) {
  const {
    chapter = null,
    phase = '',
    action = 'auto',
    journey_next_domain = null,
    focus_hint = null,
    onSel = null,
    applyFocus = true,
  } = opts

  let resolveOk = false
  let pkg = null
  let uiEvents = []
  let useWorldWriteRun = false
  let channel = 'discuss'

  try {
    const body = {
      message: message || '',
      chapter: chapter != null ? Number(chapter) : null,
      phase: phase || null,
      action,
      journey_next_domain: journey_next_domain || null,
      focus_hint: focus_hint || null,
      activate: true,
    }
    const res = await api.orchResolve(body)
    resolveOk = true
    pkg = res.package || null
    uiEvents = Array.isArray(res.ui_events) ? res.ui_events : []
    useWorldWriteRun = !!res.use_world_write_run
    channel = res.channel || pkg?.channel || 'discuss'
  } catch {
    // 离线/后端旧版：弱回退正则（非唯一真理路径的兼容）
    useWorldWriteRun = shouldUseHermesRun(message)
    channel = useWorldWriteRun ? 'world_write' : 'discuss'
  }

  if (applyFocus && uiEvents.length) {
    applyUiEvents(uiEvents, { onSel })
  }

  const instructions = useWorldWriteRun
    ? hermesRunInstructions({
      chapter,
      phase: useWorldWriteRun ? '' : phase,
      focalizer: '',
    })
    : ''

  return {
    useWorldWriteRun,
    package: pkg,
    uiEvents,
    channel,
    instructions,
    evaluationHint: pkg?.required_outcome === 'write_proposal'
      ? { required_outcome: 'write_proposal', write_tools: pkg.write_tools || [] }
      : null,
    resolveOk,
  }
}

/**
 * 回合结束：写必出包若无写工具 → incomplete + 补救文案。
 */
export async function evaluateOrchTurn({ toolsCalled = [], approvedWrites = [] } = {}) {
  try {
    return await api.orchEvaluateTurn({
      tools_called: toolsCalled,
      approved_writes: approvedWrites,
    })
  } catch {
    return null
  }
}
