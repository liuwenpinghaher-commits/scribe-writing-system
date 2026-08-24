import { describe, expect, it } from 'vitest'
import { isMainCastImportance, openLedgerSummary, portraitCast, ruleLine } from './synopsisCast.js'

describe('portraitCast', () => {
  it('滤地点；主要角色排在前面', () => {
    const { shown, total } = portraitCast([
      { id: 'place:华山', kind: 'place', name: '华山' },
      { id: 'role:龙套', kind: 'character', name: '路人', importance: '龙套' },
      { id: 'role:沈', kind: 'character', name: '沈拾灯', importance: '主要角色' },
    ])
    expect(total).toBe(2)
    expect(shown[0].name).toBe('沈拾灯')
    expect(shown.map((c) => c.name)).not.toContain('华山')
  })

  it('主要角色别名算主档', () => {
    expect(isMainCastImportance('主要角色')).toBe(true)
    expect(isMainCastImportance('重要配角')).toBe(true)
    expect(isMainCastImportance('龙套')).toBe(false)
  })
})

describe('ruleLine / ledger', () => {
  it('规则展示丢掉 note', () => {
    expect(ruleLine({ name: '金縢', cost: '三年', note: '秘密', limitations: ['不可逆'] })).toEqual({
      name: '金縢',
      detail: '三年',
    })
  })

  it('未收账用人话计数', () => {
    const s = openLedgerSummary({
      open: [{ text: 'a' }, { text: 'b' }],
      audit: { overdue_count: 1 },
    })
    expect(s.n).toBe(2)
    expect(s.overdueN).toBe(1)
  })
})
