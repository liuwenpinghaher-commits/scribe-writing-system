/**
 * 校正 react-resizable-panels 的 defaultLayout。
 * 损坏/过旧的 localStorage 布局(缺键、负数、和不等于 100、低于 min)会导致
 * 拖拽时栏宽跳变、中文逐字折行、整页错乱。
 */

export const FOUR_PANE_DEFAULT = { directory: 14, detail: 62, right: 24 }

export const FOUR_PANE_BOUNDS = {
  directory: { min: 10, max: 24 },
  detail: { min: 34, max: 80 },
  right: { min: 18, max: 58 },
}

/**
 * @param {Record<string, number> | null | undefined} layout
 * @param {{ defaults?: Record<string, number>, bounds?: Record<string, {min:number,max:number}>, keys?: string[] }} [opts]
 * @returns {Record<string, number>}
 */
export function sanitizeLayout(layout, opts = {}) {
  const defaults = opts.defaults || FOUR_PANE_DEFAULT
  const bounds = opts.bounds || FOUR_PANE_BOUNDS
  const keys = opts.keys || Object.keys(defaults)

  const raw = layout && typeof layout === 'object' ? layout : {}
  const next = {}
  let valid = true
  for (const k of keys) {
    const v = Number(raw[k])
    if (!Number.isFinite(v) || v < 0) {
      valid = false
      next[k] = defaults[k]
      continue
    }
    const b = bounds[k]
    if (b) {
      if (v > 0 && v < b.min * 0.5) {
        // 接近折叠:保留 0 以便 collapsible 识别;否则抬到 min
        next[k] = v < 1 ? 0 : b.min
      } else if (b && v > 0) {
        next[k] = Math.min(b.max, Math.max(b.min, v))
      } else {
        next[k] = v
      }
    } else {
      next[k] = v
    }
  }

  // 非折叠栏之和应 ≈ 100(允许折叠栏为 0)
  const active = keys.filter((k) => next[k] > 0.5)
  const sum = active.reduce((s, k) => s + next[k], 0)
  if (active.length === 0 || !Number.isFinite(sum) || sum < 90 || sum > 110) {
    return { ...defaults }
  }
  if (Math.abs(sum - 100) > 0.5) {
    const scale = 100 / sum
    for (const k of active) next[k] = Math.round(next[k] * scale * 10) / 10
    // 归一化舍入误差归到 detail
    const sum2 = active.reduce((s, k) => s + next[k], 0)
    if (next.detail != null && next.detail > 0) {
      next.detail = Math.round((next.detail + (100 - sum2)) * 10) / 10
    }
  }

  // 最终再夹一次 min/max(缩放后可能越界),然后二次比例归一化——禁止整表 wipe 用户偏好。
  for (const k of keys) {
    const b = bounds[k]
    if (!b || next[k] <= 0.5) continue
    next[k] = Math.min(b.max, Math.max(b.min, next[k]))
  }
  const active2 = keys.filter((k) => next[k] > 0.5)
  const sum3 = active2.reduce((s, k) => s + next[k], 0)
  if (active2.length && Number.isFinite(sum3) && sum3 > 0 && Math.abs(sum3 - 100) > 0.5) {
    const scale = 100 / sum3
    for (const k of active2) next[k] = Math.round(next[k] * scale * 10) / 10
    const sum4 = active2.reduce((s, k) => s + next[k], 0)
    const anchor = active2.includes('detail') ? 'detail' : active2[0]
    next[anchor] = Math.round((next[anchor] + (100 - sum4)) * 10) / 10
    // 归一化后再夹一次,避免 anchor 越 max
    for (const k of active2) {
      const b = bounds[k]
      if (!b) continue
      next[k] = Math.min(b.max, Math.max(b.min, next[k]))
    }
  }
  if (!valid && Object.keys(raw).length === 0) return { ...defaults }
  return next
}
