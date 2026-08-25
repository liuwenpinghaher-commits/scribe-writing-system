/**
 * 仪表盘 → 主编种子。只讨论，禁止 s3_ / 写库套话。
 */
import { focusChiefWithSeed } from './chiefSeed.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'

const MAX_SEED = 1200

export function buildInsightNextStrokeSeed(item, ctx = {}) {
  if (!item) return { text: '', isDiscuss: true }
  const kind = ctx.kind || item.kind || 'weak_chapter'
  const ch = Number(ctx.chapter ?? item.chapter ?? item.seq ?? item.setup_chapter)
  const chapterBit = Number.isFinite(ch) && ch > 0 ? `第${ch}章` : '当前章'
  const label = String(item.title || item.text || item.label || '这条体检').trim()
  const lines = [
    `【仪表盘】针对${chapterBit}的体检「${label}」只讨论下一笔可落地的动作（不要调用写库工具）。`,
    `类型：${kind}`,
    kind === 'weak_chapter'
      ? `QC ${item.qc_issues ?? 0} · 因果 ${item.causal ?? 0}`
      : null,
    kind === 'promise' && item.overdue ? '状态：超期未收' : null,
    '请给出：这一笔落在哪一章附近、先修病还是先还账、读者先看见哪一句。',
  ].filter(Boolean)
  let text = lines.join('\n')
  if (text.length > MAX_SEED) text = `${text.slice(0, MAX_SEED - 1)}…`
  return { text, isDiscuss: !shouldUseHermesRun(text) }
}

export function seedInsightNextStroke(item, ctx = {}) {
  const { text } = buildInsightNextStrokeSeed(item, ctx)
  if (!text) return ''
  focusChiefWithSeed(text)
  return text
}
