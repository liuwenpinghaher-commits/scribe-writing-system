import { describe, expect, it } from 'vitest'
import { FOUR_PANE_DEFAULT, sanitizeLayout } from '../sanitizeLayout'

describe('sanitizeLayout', () => {
  it('returns defaults for null/empty', () => {
    expect(sanitizeLayout(null)).toEqual(FOUR_PANE_DEFAULT)
    expect(sanitizeLayout({})).toEqual(FOUR_PANE_DEFAULT)
  })

  it('clamps and renormalizes valid-ish layouts', () => {
    const out = sanitizeLayout({ directory: 5, detail: 90, right: 5 })
    // 低于 min → 抬到 min（目录 14 / 主编·详情 30）
    expect(out.directory).toBeGreaterThanOrEqual(14)
    expect(out.right).toBeGreaterThanOrEqual(30)
    expect(out.detail).toBeGreaterThanOrEqual(30)
    const sum = out.directory + out.detail + out.right
    expect(sum).toBeGreaterThan(95)
    expect(sum).toBeLessThan(105)
  })

  it('resets when sum is absurd', () => {
    expect(sanitizeLayout({ directory: 1, detail: 1, right: 1 })).toEqual(FOUR_PANE_DEFAULT)
  })

  it('preserves collapsed zero for collapsible sides when near-zero', () => {
    const out = sanitizeLayout({ directory: 0, detail: 57, right: 43 })
    expect(out.directory).toBe(0)
    expect(out.right).toBe(43)
  })

  it('right collapsed: detail may exceed old dual max and fill ~100 (no wipe to defaults)', () => {
    const out = sanitizeLayout({ directory: 18, detail: 43, right: 0 })
    expect(out.right).toBe(0)
    expect(out.detail).toBeGreaterThan(60)
    expect(out.directory + out.detail).toBeGreaterThan(95)
    expect(out.directory + out.detail).toBeLessThan(105)
  })

  it('right collapsed with detail already large: keep near-full layout', () => {
    const out = sanitizeLayout({ directory: 18, detail: 82, right: 0 })
    expect(out.right).toBe(0)
    expect(out.detail).toBeGreaterThanOrEqual(75)
    expect(Math.abs(out.directory + out.detail - 100)).toBeLessThan(3)
  })

  it('ignores NaN keys', () => {
    const out = sanitizeLayout({ directory: 'x', detail: 43, right: 43 })
    expect(out.directory).toBe(FOUR_PANE_DEFAULT.directory)
  })

  it('clamp edge does not wipe to full defaults when sum can renormalize', () => {
    // after min clamp each side would overshoot 100; must scale, not return bare defaults
    const out = sanitizeLayout({ directory: 40, detail: 40, right: 40 })
    const sum = out.directory + out.detail + out.right
    expect(Math.abs(sum - 100)).toBeLessThan(3)
    // not a silent full wipe unless absurd
    expect(out).not.toEqual(FOUR_PANE_DEFAULT)
  })
})
