/**
 * 一级入口 ↔ 栏3 选中节点的兼容性与切换计划。
 *
 * 两级选中：entry 驱动栏2、sel 驱动栏3。切换入口时若仍展示「别的能力」详情
 * （如素材库入口 + 伏笔详情），会严重误导。约定：
 *  - 写作粘性节点（章/景/卷）跨入口保留，方便工艺/素材侧栏对照写作；
 *  - 其余节点必须归属当前入口，否则落到该入口的默认着陆点。
 */

import { entryPatch, nodePatch } from '../context/contextSnapshot'

const STICKY_TYPES = new Set(['chapter', 'scene', 'volume'])

const ENTRY_TYPES = {
  manuscript: new Set([
    'chapter', 'scene', 'volume', 'manuscript_root', 'book_outline', 'book_northstar',
  ]),
  codex: new Set([
    'character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif', 'proposition',
    'codex_root', 'codex_category', 'codex_new',
  ]),
  materials: new Set([
    'material', 'material_root', 'material_category', 'material_new', 'material_import', 'material_network',
  ]),
  deduce: new Set(['deduce_view', 'capability_group']),
  promise: new Set(['promise_view', 'capability_group', 'promise']),
  motif: new Set(['motif_view', 'capability_group', 'motif']),
  search: new Set(['recall_result']),
  review: new Set(['review_issue']),
  references: new Set(['references', 'quality_review', 'quality_contract']),
}

/** 当前节点是否可与 entry 共存（不强制清空栏3） */
export function nodeCompatibleWithEntry(node, entryKey) {
  if (!node || !entryKey) return true
  if (STICKY_TYPES.has(node.type)) return true
  if (node.capability) return node.capability === entryKey
  const allowed = ENTRY_TYPES[entryKey]
  if (!allowed) return true
  return allowed.has(node.type)
}

/** 切到不兼容入口时的默认着陆节点；null = 清空栏3 */
export function defaultLandingNode(entryKey, tree) {
  if (entryKey === 'materials') {
    const src = tree?.materials
    return {
      id: src?.id || 'material_root',
      type: 'material_root',
      ref: null,
      label: src?.label || '素材库',
    }
  }
  if (entryKey === 'codex') {
    const src = tree?.codex
    return {
      id: src?.id || 'codex_root',
      type: 'codex_root',
      ref: null,
      label: src?.label || '设定库',
    }
  }
  if (entryKey === 'manuscript') {
    const src = tree?.manuscript
    return {
      id: src?.id || 'manuscript_root',
      type: 'manuscript_root',
      ref: null,
      label: src?.label || '手稿',
    }
  }
  if (entryKey === 'references') {
    return { id: 'references', type: 'references', ref: null, label: '参考作品' }
  }
  // 工艺/检查：清空，让用户从栏2 点条目再出详情
  return null
}

/**
 * 入口切换时的选中收敛结果。
 * @returns {{ action: 'keep' } | { action: 'land', node: object } | { action: 'clear' }}
 */
export function resolveEntrySelection(entryKey, node, tree) {
  if (nodeCompatibleWithEntry(node, entryKey)) return { action: 'keep' }
  const landing = defaultLandingNode(entryKey, tree)
  if (landing) return { action: 'land', node: landing }
  return { action: 'clear' }
}

/**
 * 统一「切入口」计划：rail 点击 / s3-open-capability 共用，保证只发一次 navigate。
 * @returns {{ patch: object, select: object|null|undefined }}
 *   select === undefined → 不改本地 sel；null → 清空；object → 着陆节点
 */
export function planEntryChange(entryKey, node, tree, label = '') {
  const decision = resolveEntrySelection(entryKey, node, tree)
  if (decision.action === 'land') {
    return { patch: nodePatch(decision.node, entryKey), select: decision.node }
  }
  if (decision.action === 'clear') {
    return { patch: entryPatch(entryKey, label), select: null }
  }
  // keep：粘性章时把 entry 写进 path，但 focus 仍指向章，避免 entry-only 投影把章冲掉
  if (node && STICKY_TYPES.has(node.type)) {
    return { patch: { ...nodePatch(node, entryKey), reason: 'entry' }, select: undefined }
  }
  return { patch: entryPatch(entryKey, label), select: undefined }
}

/** 手稿门厅：空选或停在手稿根。禁止用 !entryKey 冒充手稿。 */
export function isSynopsisHall(entryKey, sel) {
  if (entryKey !== 'manuscript') return false
  if (sel?.mode === 'view') return false
  const t = sel?.node?.type
  return !sel?.node || t === 'manuscript_root'
}

/** 空态文案：按当前入口域 */
export function emptyDetailCopy(entryKey) {
  switch (entryKey) {
    case 'materials':
      return { title: '素材库', hint: '在左侧选择素材，或新建 / 导入一条。' }
    case 'codex':
      return { title: '设定库', hint: '在左侧选择设定条目查看详情。' }
    case 'manuscript':
      return { title: '手稿', hint: '在左侧选择章节开始写作。' }
    case 'promise':
      return { title: '伏笔', hint: '在左侧选择分组或条目查看伏笔台账。' }
    case 'motif':
      return { title: '母题', hint: '在左侧选择分组或条目查看母题。' }
    case 'deduce':
      return { title: '演绎', hint: '在左侧选择限知 / 场景真相等入口。' }
    case 'search':
      return { title: '搜索', hint: '在左侧输入关键词搜索，再点结果查看详情。' }
    case 'review':
      return { title: '校验', hint: '确定性命中台账；日常请看正文护栏与全量体检。' }
    case 'references':
      return { title: '参考作品', hint: '在左侧打开参考作品工作台。' }
    default:
      return { title: '详情', hint: '从左侧目录选择条目查看详情。' }
  }
}
