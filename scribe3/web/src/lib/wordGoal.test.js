import { describe, expect, it } from 'vitest'
import { safeWordGoal, wordGoalPct } from './wordGoal.js'

describe('safeWordGoal / wordGoalPct (DSH-01)', () => {
  it('goal=0 不产出 Infinity', () => {
    expect(safeWordGoal(0)).toBe(100000)
    expect(wordGoalPct(5000, 0)).toBe(5)
    expect(Number.isFinite(wordGoalPct(5000, 0))).toBe(true)
  })

  it('null / undefined / 负数走回落', () => {
    expect(safeWordGoal(null)).toBe(100000)
    expect(safeWordGoal(undefined)).toBe(100000)
    expect(safeWordGoal(-10)).toBe(100000)
    expect(wordGoalPct(200, '')).toBe(0)
  })

  it('正常目标按比例封顶 100', () => {
    expect(wordGoalPct(50, 100)).toBe(50)
    expect(wordGoalPct(200, 100)).toBe(100)
  })
})
