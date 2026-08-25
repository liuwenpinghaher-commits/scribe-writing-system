/**
 * 图谱抽屉 → 主编种子（PR-A）。
 * 主路径 discuss：禁止 s3_ / 审批 / 写库套话，避免 shouldUseHermesRun 强制世界写。
 */
import { focusChiefWithSeed } from './chiefSeed.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'
import { displayNodeLabel, SECRET_PLACEHOLDER } from './atlasNodeDetail.js'

const MAX_SEED = 1200

/**
 * 构建 discuss 种子正文（不调用 focusChief）。
 * @returns {{ text: string, isDiscuss: boolean }}
 */
export function buildAtlasDiscussSeed(node, ctx = {}) {
  if (!node) return { text: '', isDiscuss: true }
  const label = node.secret ? SECRET_PLACEHOLDER : displayNodeLabel(node)
  const type = node.type || 'node'
  const hop = ctx.hop != null ? ctx.hop : 1
  const focusLabel = ctx.focusLabel || ctx.focusId || ''
  const degree = ctx.degree != null ? ctx.degree : null
  const lines = [
    '【图谱操作台】请帮我分析当前选中对象，并给出可用于本章的戏剧建议（只讨论，不要调用写库工具）。',
    `对象：${label}`,
    `类型：${type}`,
    focusLabel ? `图中心：${focusLabel}` : null,
    hop != null ? `当前跳数：${hop}` : null,
    degree != null ? `子图度数：${degree}` : null,
    ctx.arcLine ? `弧光：${ctx.arcLine}` : null,
    ctx.relSummary ? `关系：${ctx.relSummary}` : null,
    '请说明：与中心/POV 的张力、可用的信息差或反讽、下一笔可落地的动作。',
  ].filter(Boolean)
  let text = lines.join('\n')
  if (text.length > MAX_SEED) text = text.slice(0, MAX_SEED - 1) + '…'
  // 复检：discuss 不得触发世界写 Hermes
  const hermes = shouldUseHermesRun(text)
  return { text, isDiscuss: !hermes }
}

function gapLine(rows, prefix) {
  const labels = (rows || []).slice(0, 4).map((r) => {
    if (!r) return ''
    if (r.secret) return SECRET_PLACEHOLDER
    return String(r.label || '').trim() || SECRET_PLACEHOLDER
  }).filter(Boolean)
  if (!labels.length) return null
  return `${prefix}：${labels.join('；')}`
}

/**
 * 「用这个信息差写下一笔」：只讨论，带章号与子图知情差。
 * 禁止 s3_ / 写库套话。
 */
export function buildAtlasNextStrokeSeed(node, ctx = {}) {
  if (!node) return { text: '', isDiscuss: true }
  const label = node.secret ? SECRET_PLACEHOLDER : displayNodeLabel(node)
  const ch = Number(ctx.chapter)
  const chapterBit = Number.isFinite(ch) && ch > 0 ? `截至第${ch}章` : '当前切片'
  const focusLabel = ctx.focusLabel || ctx.focusId || ''
  const lines = [
    `【图谱·信息差】${chapterBit}，请只讨论下一笔可落地的动作（不要调用写库工具）。`,
    `选中：${label}`,
    focusLabel ? `图中心 / POV：${focusLabel}` : null,
    gapLine(ctx.onlyFocus, focusLabel ? `${focusLabel}独知` : '中心独知'),
    gapLine(ctx.onlySelf, `${label}独知`),
    '请给出：这一笔谁开口、藏什么、读者先知道哪一句。',
  ].filter(Boolean)
  let text = lines.join('\n')
  if (text.length > MAX_SEED) text = text.slice(0, MAX_SEED - 1) + '…'
  const hermes = shouldUseHermesRun(text)
  return { text, isDiscuss: !hermes }
}

export function seedAtlasNextStroke(node, ctx = {}) {
  const { text } = buildAtlasNextStrokeSeed(node, ctx)
  if (!text) return ''
  focusChiefWithSeed(text)
  return text
}

/** 主 CTA：问主编（discuss） */
export function seedAtlasDiscuss(node, ctx = {}) {
  const { text } = buildAtlasDiscussSeed(node, ctx)
  if (!text) return ''
  focusChiefWithSeed(text)
  return text
}

/**
 * 次级：写库路径（显式命中 Hermes）— 仅当用户点「让主编写入设定」时用。
 * 不作为主 CTA。
 */
export function buildAtlasWriteSeed(node) {
  if (!node) return ''
  const label = node.secret ? SECRET_PLACEHOLDER : displayNodeLabel(node)
  // 显式工具名 → shouldUseHermesRun true
  return [
    `请根据图谱上下文补全/更正设定「${label}」并提交写入提案供我批准。`,
    '先用只读工具核实现状，再调用对应 s3_ 写工具；未获批准不得声称已落库。',
  ].join('\n')
}

export function seedAtlasWrite(node) {
  const text = buildAtlasWriteSeed(node)
  if (!text) return ''
  focusChiefWithSeed(text)
  return text
}
