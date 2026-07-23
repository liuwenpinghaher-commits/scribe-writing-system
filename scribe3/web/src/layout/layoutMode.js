/**
 * 四栏布局模式：协作（会话主舞台）vs 阅读（详情主舞台）。
 * 默认按章阶段自动：大纲/节拍/演绎/草稿 → collaboration；正文 final → reading。
 * 非章上下文（设定/素材等）默认 collaboration。全画布 view → reading。
 */

export const LAYOUT_MODE = Object.freeze({
  collaboration: 'collaboration',
  reading: 'reading',
})

/** 对话驱动阶段 → 协作模式 */
const COLLAB_PHASES = new Set(['outline', 'beats', 'deduce', 'draft'])

/**
 * @param {{ phase?: string|null, isView?: boolean, isChapterContext?: boolean }} ctx
 * @returns {'collaboration'|'reading'}
 */
export function resolveLayoutMode(ctx = {}) {
  if (ctx.isView) return LAYOUT_MODE.reading
  const phase = ctx.phase == null || ctx.phase === '' ? null : String(ctx.phase)
  if (phase === 'final') return LAYOUT_MODE.reading
  if (phase && COLLAB_PHASES.has(phase)) return LAYOUT_MODE.collaboration
  // 非章 / 无 phase：会话主体默认协作
  if (ctx.isChapterContext === false || phase == null) return LAYOUT_MODE.collaboration
  // 未知 phase 保守协作
  return LAYOUT_MODE.collaboration
}

/**
 * 默认栏宽（%）：协作/阅读共用同一套，避免切 phase 时比例跳变。
 * 差异只在栏序（panelOrder）；directory 次要，主编(right) 与详情对等。
 * 用户拖拽后仍按 mode 分键持久化（可各自记住偏好）。
 */
export const LAYOUT_DEFAULT_SHARES = Object.freeze({ directory: 14, detail: 43, right: 43 })

export const LAYOUT_DEFAULTS_BY_MODE = Object.freeze({
  collaboration: LAYOUT_DEFAULT_SHARES,
  reading: LAYOUT_DEFAULT_SHARES,
})

/**
 * 两模式共用拖拽边界：主编/详情默认对等。
 * max 用 100（而非 60）：折叠一侧后另一侧才能吃满空位；双栏同开时
 * 对侧 min（28）+ 目录 min（10）仍把单栏有效上限卡在 ~62%，不会拖死邻居。
 * 旧 max=60 在折叠后留下大块空白（截屏：时间线右侧空页）。
 */
export const LAYOUT_BOUNDS_SHARED = Object.freeze({
  directory: { min: 10, max: 22 },
  detail: { min: 28, max: 100 },
  right: { min: 28, max: 100 },
})

export const LAYOUT_BOUNDS_BY_MODE = Object.freeze({
  collaboration: LAYOUT_BOUNDS_SHARED,
  reading: LAYOUT_BOUNDS_SHARED,
})

/**
 * Panel 横向顺序（id）。协作：目录 | 主编 | 详情；阅读：目录 | 详情 | 主编。
 * @param {'collaboration'|'reading'} mode
 * @returns {Array<'directory'|'detail'|'right'>}
 */
export function panelOrderForMode(mode) {
  if (mode === LAYOUT_MODE.collaboration) return ['directory', 'right', 'detail']
  return ['directory', 'detail', 'right']
}

/** layout persistence 前缀 v3：按 mode 分键，避免旧 detail-primary 污染协作默认 */
export const FOUR_PANE_LAYOUT_ID_V3 = 's3.fourPane.layout.v3'

export function layoutStorageId(work, mode) {
  return `${FOUR_PANE_LAYOUT_ID_V3}:${mode}:${work || 'main'}`
}

/**
 * 折叠还原钮应贴在「相邻仍可见栏」的正确边缘，而不是写死在 detail 上。
 * 协作 order=directory|right|detail 时：目录还原在主编左缘；主编还原在目录右缘。
 * 阅读 order=directory|detail|right 时：两者仍可落在详情左右缘（中间舞台）。
 *
 * @param {Array<'directory'|'detail'|'right'>} panelOrder
 * @param {{ directoryCollapsed?: boolean, rightCollapsed?: boolean, isView?: boolean }} state
 * @returns {{
 *   directory: { hostId: 'directory'|'detail'|'right', edge: 'left'|'right' } | null,
 *   right: { hostId: 'directory'|'detail'|'right', edge: 'left'|'right' } | null,
 * }}
 */
export function restoreSlotsForOrder(panelOrder, state = {}) {
  const order = Array.isArray(panelOrder) && panelOrder.length
    ? panelOrder
    : panelOrderForMode(LAYOUT_MODE.reading)
  const directoryCollapsed = !!state.directoryCollapsed
  const rightCollapsed = !!state.rightCollapsed
  const isView = !!state.isView

  /** @type {{ hostId: 'directory'|'detail'|'right', edge: 'left'|'right' } | null} */
  let directory = null
  /** @type {{ hostId: 'directory'|'detail'|'right', edge: 'left'|'right' } | null} */
  let right = null

  if (directoryCollapsed && !isView) {
    const afterDir = order.filter((id) => id !== 'directory')
    // 优先贴在下一块仍展开的栏；主编也折起时落到 detail
    const hostId = afterDir.find((id) => id !== 'right' || !rightCollapsed) || afterDir[afterDir.length - 1] || 'detail'
    directory = { hostId, edge: 'left' }
  }

  if (rightCollapsed) {
    const idx = order.indexOf('right')
    const prev = idx > 0 ? order[idx - 1] : null
    const next = idx >= 0 && idx < order.length - 1 ? order[idx + 1] : null
    const prevGone = prev === 'directory' && (directoryCollapsed || isView)
    if (prev && !prevGone) {
      right = { hostId: prev, edge: 'right' }
    } else if (next) {
      right = { hostId: next, edge: 'left' }
    } else if (prev) {
      right = { hostId: prev, edge: 'right' }
    }
  }

  // 同宿主同边时把主编还原拨到对侧，避免叠钮
  if (
    directory
    && right
    && directory.hostId === right.hostId
    && directory.edge === right.edge
  ) {
    right = { hostId: right.hostId, edge: right.edge === 'left' ? 'right' : 'left' }
  }

  return { directory, right }
}
