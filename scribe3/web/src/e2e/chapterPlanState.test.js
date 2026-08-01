import { describe, expect, it } from 'vitest'
import { missingDeductionProjections } from './chapterPlanState.js'

describe('missingDeductionProjections', () => {
  it('reports every involved role with no usable deduction', () => {
    expect(missingDeductionProjections({
      involved_characters: ['role:沈砚', 'role:老道'],
      deductions: [{ character_id: 'role:沈砚', prose: '### 看到/听到\\n老道沉默' }],
    })).toEqual(['role:老道'])
  })

  it('accepts canonical and bare role identifiers only when prose exists', () => {
    expect(missingDeductionProjections({
      involved_characters: ['role:沈砚', 'role:老道'],
      deductions: [
        { character_id: '沈砚', prose: '看见铜钱' },
        { character: 'role:老道', prose: '知道灰契，选择不说全' },
      ],
    })).toEqual([])
  })
})
