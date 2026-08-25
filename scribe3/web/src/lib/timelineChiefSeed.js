/**
 * 时间线抽屉 → 主编种子。只讨论，禁止 s3_ / 写库套话。
 */
import { focusChiefWithSeed } from './chiefSeed.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'

const MAX_SEED = 1200

function causalBits(raw) {
  const rows = raw?.refs?.causal_in || []
  const bits = rows.slice(0, 4).map((c) => {
    if (c == null) return ''
    if (typeof c === 'string') return c
    const id = c.id || c.label || ''
    const ch = c.chapter != null ? `第${c.chapter}章` : ''
    return [ch, id].filter(Boolean).join(' ')
  }).filter(Boolean)
  return bits.length ? bits.join('；') : null
}

export function buildTimelineNextStrokeSeed(raw, ctx = {}) {
  if (!raw) return { text: '', isDiscuss: true }
  const ch = Number(ctx.chapter ?? raw.story_chapter ?? raw.chapter)
  const chapterBit = Number.isFinite(ch) && ch > 0 ? `第${ch}章` : '当前章'
  const label = String(raw.label || raw.event_type || raw.id || '这件事').trim()
  const cat = ctx.cat || 'event'
  const lines = [
    `【时间线】围绕${chapterBit}的「${label}」只讨论下一笔可落地的动作（不要调用写库工具）。`,
    `类型：${cat}`,
    causalBits(raw) ? `前驱：${causalBits(raw)}` : null,
    '请给出：这一笔落在哪一章附近、谁先动、读者先看见哪一句。',
  ].filter(Boolean)
  let text = lines.join('\n')
  if (text.length > MAX_SEED) text = `${text.slice(0, MAX_SEED - 1)}…`
  return { text, isDiscuss: !shouldUseHermesRun(text) }
}

export function seedTimelineNextStroke(raw, ctx = {}) {
  const { text } = buildTimelineNextStrokeSeed(raw, ctx)
  if (!text) return ''
  focusChiefWithSeed(text)
  return text
}
