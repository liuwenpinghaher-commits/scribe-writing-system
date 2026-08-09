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
    '【图谱操作台】请帮我分析当前选中对象，并给出可写入本章的戏剧建议（只讨论，不要调用写库工具）。',
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

/** 主 CTA：问主编（discuss） */
export function seedAtlasDiscuss(node, ctx = {}) {
  const { text, isDiscuss } = buildAtlasDiscussSeed(node, ctx)
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
