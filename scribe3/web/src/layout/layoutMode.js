/**
 * 四栏布局模式：协作（会话主舞台）vs 阅读（详情主舞台）。
 * 默认按章阶段自动：大纲/节拍/演绎/草稿 → collaboration；正文 final → reading。
 * 非章上下文（设定/素材等）默认 collaboration。全画布 view → reading。
 *
 * 栏序：目录 | 详情 | 主编会话（聊天最右）。
 * 默认宽度 v8：directory 18 / detail 42 / right 40（正文与大纲共用 writing 持久化，
 * 避免切 final 时栏宽跳变、目录被压窄后 min-width 顶出遮挡）。
 */

export const LAYOUT_MODE = Object.freeze({
  collaboration: 'collaboration',
  reading: 'reading',
})

/** 对话驱动阶段 → 协作模式 */
const COLLAB_PHASES = new Set(['outline', 'beats', 'design', 'deduce', 'draft'])

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
 * 默认栏宽（%）：协作/阅读共用；正文与大纲同一 writing 键，比例不跳变。
 * 目录略加宽防窄屏被 min 像素顶出；详情略宽于聊天，利于正文阅读。
 * 18 + 42 + 40 = 100。
 */
export const LAYOUT_DEFAULT_SHARES = Object.freeze({ directory: 18, detail: 42, right: 40 })

/**
 * 旅程 tab（目录隐藏时两栏）：detail=旅程、right=会话，保持 42:40 份额比。
 * 三键仍写 directory 占位；Group 用 visibleLayoutShares 归一到 100。
 */
export const JOURNEY_LAYOUT_SHARES = Object.freeze({ directory: 18, detail: 42, right: 40 })

/**
 * 仅保留可见栏 id 的份额并归一到 100（view 隐藏目录时 Group 只有两栏）。
 * @param {Record<string, number>} defaults
 * @param {string[]} visibleIds
 * @returns {Record<string, number>}
 */
export function visibleLayoutShares(defaults, visibleIds) {
  const ids = (visibleIds || []).filter((id) => defaults && defaults[id] != null)
  if (!ids.length) return { ...(defaults || {}) }
  let sum = 0
  for (const id of ids) sum += Number(defaults[id]) || 0
  if (!(sum > 0)) return { ...(defaults || {}) }
  const out = {}
  for (const id of ids) {
    out[id] = Math.round(((Number(defaults[id]) || 0) / sum) * 1000) / 10
  }
  const sum2 = ids.reduce((s, id) => s + out[id], 0)
  const anchor = ids.includes('detail') ? 'detail' : ids[0]
  out[anchor] = Math.round((out[anchor] + (100 - sum2)) * 10) / 10
  return out
}

export const LAYOUT_DEFAULTS_BY_MODE = Object.freeze({
  collaboration: LAYOUT_DEFAULT_SHARES,
  reading: LAYOUT_DEFAULT_SHARES,
})

/**
 * 两模式共用拖拽边界。
 * 目录 min 14：与默认 18 接近，避免拖到 10% 时内层文字顶破邻栏。
 * max 100：折叠一侧后另一侧可吃满；双栏同开时对侧 min 仍限制有效上限。
 */
export const LAYOUT_BOUNDS_SHARED = Object.freeze({
  directory: { min: 14, max: 24 },
  detail: { min: 30, max: 100 },
  right: { min: 30, max: 100 },
})

export const LAYOUT_BOUNDS_BY_MODE = Object.freeze({
  collaboration: LAYOUT_BOUNDS_SHARED,
  reading: LAYOUT_BOUNDS_SHARED,
})

/**
 * Panel 横向顺序（id）。
 * 全模式统一：目录 | 详情 | 主编(right) —— 聊天在最右。
 * @param {'collaboration'|'reading'} mode
 * @returns {Array<'directory'|'detail'|'right'>}
 */
export function panelOrderForMode(mode) {
  void mode
  return ['directory', 'detail', 'right']
}

/** 是否顶栏「旅程」横切视图 */
export function isJourneyViewSel(sel) {
  return sel?.mode === 'view' && String(sel.viewKey || '') === 'journey'
}

/**
 * 旅程 tab：与全局相同 — 目录 | 旅程详情 | 会话（最右）。
 * @returns {Array<'directory'|'detail'|'right'>}
 */
export function panelOrderForJourney() {
  return ['directory', 'detail', 'right']
}

/**
 * 解析最终栏序与默认宽（旅程 tab 特例；其余走 layoutMode）。
 * @param {{ layoutMode: 'collaboration'|'reading', isJourneyView?: boolean }} opts
 */
export function resolvePanelLayout(opts = {}) {
  const mode = opts.layoutMode || LAYOUT_MODE.reading
  if (opts.isJourneyView) {
    // 旅程两栏均可拖：detail/right 下限与全局一致
    const journeyBounds = Object.freeze({
      directory: LAYOUT_BOUNDS_SHARED.directory,
      detail: { min: 30, max: 100 },
      right: { min: 30, max: 100 },
    })
    return {
      panelOrder: panelOrderForJourney(),
      layoutDefaults: JOURNEY_LAYOUT_SHARES,
      layoutBounds: journeyBounds,
      storageMode: 'journey-v5',
      detailMinPercent: 30,
    }
  }
  return {
    panelOrder: panelOrderForMode(mode),
    layoutDefaults: LAYOUT_DEFAULTS_BY_MODE[mode] || LAYOUT_DEFAULT_SHARES,
    layoutBounds: LAYOUT_BOUNDS_BY_MODE[mode] || LAYOUT_BOUNDS_SHARED,
    // 大纲(collaboration)与正文(reading)共用 writing 键：切 final 不换栏宽
    storageMode: opts.isView ? mode : 'writing',
    // 其它 view（图谱等）仍倾向内容更宽
    detailMinPercent: opts.isView ? 40 : undefined,
  }
}

/** layout persistence 前缀 v8：统一默认宽 + writing 共用键，清掉 v7 窄目录/分模式缓存 */
export const FOUR_PANE_LAYOUT_ID_V3 = 's3.fourPane.layout.v8'

export function layoutStorageId(work, mode) {
  return `${FOUR_PANE_LAYOUT_ID_V3}:${mode}:${work || 'main'}`
}

/**
 * 折叠还原钮应贴在「相邻仍可见栏」的正确边缘，而不是写死在 detail 上。
 *
 * @param {Array<'directory'|'detail'|'right'>} panelOrder
 * @param {{ directoryCollapsed?: boolean, rightCollapsed?: boolean, isView?: boolean }} state
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
    const hostId = afterDir.find((id) => id !== 'right' || !rightCollapsed) || afterDir[afterDir.length - 1] || 'detail'
    directory = { hostId, edge: 'left' }
  }

  if (rightCollapsed) {
    const idx = order.indexOf('right')
    // 目录在 view 或已折叠时不可作还原宿主，跳过
    const gone = (id) => id === 'directory' && (directoryCollapsed || isView)
    let prev = idx > 0 ? order[idx - 1] : null
    let next = idx >= 0 && idx < order.length - 1 ? order[idx + 1] : null
    if (gone(prev)) prev = idx > 1 ? order[idx - 2] : null
    if (gone(next)) next = idx >= 0 && idx + 2 < order.length ? order[idx + 2] : null
    if (prev && !gone(prev)) {
      right = { hostId: prev, edge: 'right' }
    } else if (next && !gone(next)) {
      right = { hostId: next, edge: 'left' }
    } else if (prev) {
      right = { hostId: prev, edge: 'right' }
    }
  }

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
