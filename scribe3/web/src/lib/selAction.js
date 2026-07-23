/**
 * 选区「聊这段 / 改这段」统一话术与主编入口。
 * 正文 ProseEditor / 草稿 RichEditor 已有气泡；其它面（素材/大纲/节拍/演绎只读…）
 * 共用本模块，避免各写一套 prompt。
 */
import { focusChiefWithSeed } from './chiefSeed.js'

const MAX_QUOTE = 800

export function truncateQuote(text, max = MAX_QUOTE) {
  const t = String(text || '').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

export function selDiscussPrompt(scopeLabel, text) {
  const q = truncateQuote(text)
  const scope = scopeLabel ? `「${scopeLabel}」` : ''
  return `就${scope}这段和你聊聊(先不改):「${q}」\n`
}

export function selEditPrompt(scopeLabel, text) {
  const q = truncateQuote(text)
  const scope = scopeLabel ? `「${scopeLabel}」` : '选中内容'
  return `把${scope}这段改一下,直接给出改后的完整段落:「${q}」`
}

/**
 * 打开主编并预填选区话术（不绑 chapter phase，适用于素材/设定/只读面）。
 * @returns {boolean} 是否发出
 */
export function openChiefForSelection({ intent = 'discuss', text, scopeLabel = '选中内容' } = {}) {
  const raw = String(text || '').trim()
  if (!raw) return false
  const body = intent === 'edit'
    ? selEditPrompt(scopeLabel, raw)
    : selDiscussPrompt(scopeLabel, raw)
  focusChiefWithSeed(body)
  return true
}

/** RichEditor / 气泡回调的薄封装 */
export function handleSelAction(payload, { scopeLabel, onEdit, onDiscuss } = {}) {
  const text = typeof payload === 'string' ? payload : payload?.text
  const intent = (typeof payload === 'object' && payload?.intent) || 'edit'
  if (intent === 'discuss' && onDiscuss) return onDiscuss(text)
  if (intent === 'edit' && onEdit) return onEdit(text)
  return openChiefForSelection({ intent, text, scopeLabel })
}

/**
 * 空字段：没有可划选正文时，仍可指定「这一项」送进主编。
 * @param {{ entityLabel?: string, fieldLabel: string, fieldKey?: string, hint?: string }} p
 */
export function openChiefForEmptyField({ entityLabel, fieldLabel, fieldKey, hint } = {}) {
  const field = String(fieldLabel || fieldKey || '该字段').trim()
  if (!field) return false
  const entity = String(entityLabel || '当前条目').trim()
  const lines = [
    `请聊聊并补写「${entity}」的「${field}」字段(当前为空,需我审批后写入)。`,
    '先只读核实库内是否已有相关事实,再给出建议内容;若要落库请用对应 s3_ 写工具提交审批,未获批准不得声称已落库。',
  ]
  if (fieldKey) lines.push(`(字段键: ${fieldKey})`)
  if (hint) lines.push(String(hint))
  focusChiefWithSeed(lines.join('\n'))
  return true
}
