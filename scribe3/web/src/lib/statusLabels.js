/**
 * 用户可见状态/枚举 → 中文。
 * value 仍用后端英文协议；仅展示层翻译。未知码回退原文，避免丢信息。
 */

export const PROMISE_STATUS_CN = {
  open: '未收',
  closed: '已收',
  abandoned: '已弃',
}

export const PROMISE_TIER_CN = {
  chapter: '章级',
  arc: '卷级',
  volume: '卷级',
  book: '书级',
}

export const PROMISE_KIND_CN = {
  promise: '正伏笔',
  red_herring: '障眼法',
}

/** 母题 heat（motif_craft：hot/cold/neutral） */
export const MOTIF_HEAT_CN = {
  hot: '过热',
  cold: '该回声',
  neutral: '平稳',
}

/** 母题生命周期 phase */
export const MOTIF_PHASE_CN = {
  seed: '种下',
  echo: '回声',
  turn: '转折',
  payoff: '兑现',
  rest: '休眠',
}

export const MOTIF_TIER_CN = {
  book: '书级',
  volume: '卷级',
  arc: '弧级',
  chapter: '章级',
}

export const ITEM_STATE_CN = {
  active: '在场',
  lost: '遗失',
  destroyed: '毁坏',
  unknown: '未知',
}

export const SCOPE_CN = {
  global: '全局',
  regional: '地域',
  faction_specific: '势力限定',
}

export const IMPORTANCE_CN = {
  protagonist: '主角',
  major: '主要',
  minor: '次要',
  background: '背景',
}

export const RULE_CAT_CN = {
  magic: '魔法',
  technology: '科技',
  social: '社会',
  physical: '物理',
  economic: '经济',
  political: '政治',
}

/** 体验/问诊信条目状态 */
export const LETTER_STATUS_CN = {
  open: '待处理',
  pending: '待处理',
  acknowledged: '已读',
  waived: '已豁免',
  closed: '已关闭',
  done: '已处理',
}

const ALL_CN = {
  ...PROMISE_STATUS_CN,
  ...PROMISE_TIER_CN,
  ...PROMISE_KIND_CN,
  ...MOTIF_HEAT_CN,
  ...MOTIF_PHASE_CN,
  ...MOTIF_TIER_CN,
  ...ITEM_STATE_CN,
  ...SCOPE_CN,
  ...IMPORTANCE_CN,
  ...RULE_CAT_CN,
  ...LETTER_STATUS_CN,
}

/**
 * @param {unknown} code
 * @param {Record<string, string>|null} [map] 优先用专表，否则全局表
 * @param {string} [fallback] 未知时的展示；默认原文字符串
 */
export function uiStatusLabel(code, map = null, fallback) {
  if (code == null || code === '') return fallback ?? '—'
  const key = String(code)
  if (map && Object.prototype.hasOwnProperty.call(map, key)) return map[key]
  if (Object.prototype.hasOwnProperty.call(ALL_CN, key)) return ALL_CN[key]
  return fallback !== undefined ? fallback : key
}

/** select options：英文 value + 中文 label */
export function labeledOptions(values, map) {
  return (values || []).map((v) => {
    if (v && typeof v === 'object' && 'value' in v) {
      return { value: v.value, label: v.label || uiStatusLabel(v.value, map) }
    }
    return { value: v, label: uiStatusLabel(v, map) }
  })
}

/** option 列表项取值（兼容 string | {value,label}） */
export function optionValue(o) {
  return o && typeof o === 'object' && 'value' in o ? o.value : o
}

export function optionLabel(o, map = null) {
  if (o && typeof o === 'object' && 'label' in o) return o.label
  return uiStatusLabel(optionValue(o), map)
}
