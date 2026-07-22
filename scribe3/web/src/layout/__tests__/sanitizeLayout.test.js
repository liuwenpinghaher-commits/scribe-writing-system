import { describe, expect, it } from 'vitest'
import { FOUR_PANE_DEFAULT, sanitizeLayout } from '../sanitizeLayout'

describe('sanitizeLayout', () => {
  it('returns defaults for null/empty', () => {
    expect(sanitizeLayout(null)).toEqual(FOUR_PANE_DEFAULT)
    expect(sanitizeLayout({})).toEqual(FOUR_PANE_DEFAULT)
  })

  it('clamps and renormalizes valid-ish layouts', () => {
    const out = sanitizeLayout({ directory: 5, detail: 90, right: 5 })
    // 5 is below min → lifted to min (10 / 18)
    expect(out.directory).toBeGreaterThanOrEqual(10)
    expect(out.right).toBeGreaterThanOrEqual(18)
    expect(out.detail).toBeGreaterThanOrEqual(34)
    const sum = out.directory + out.detail + out.right
    expect(sum).toBeGreaterThan(95)
    expect(sum).toBeLessThan(105)
  })

  it('resets when sum is absurd', () => {
    expect(sanitizeLayout({ directory: 1, detail: 1, right: 1 })).toEqual(FOUR_PANE_DEFAULT)
  })

  it('preserves collapsed zero for collapsible sides when near-zero', () => {
    const out = sanitizeLayout({ directory: 0, detail: 76, right: 24 })
    expect(out.directory).toBe(0)
    expect(out.right).toBe(24)
  })

  it('ignores NaN keys', () => {
    const out = sanitizeLayout({ directory: 'x', detail: 62, right: 24 })
    expect(out.directory).toBe(FOUR_PANE_DEFAULT.directory)
  })
})
