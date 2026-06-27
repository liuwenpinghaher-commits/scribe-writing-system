import { describe, it, expect } from 'vitest'
import { applyProposal } from './applyProposal.js'

describe('applyProposal', () => {
  const prose = '甲说话。乙沉默。甲说话。'   // "甲说话。" 重复出现两次
  it('chapter scope 整章覆盖', () => {
    expect(applyProposal(prose, { scope: 'chapter', prose: '全新章' }, null))
      .toEqual({ next: '全新章', ok: true })
  })
  it('append scope 末尾追加', () => {
    expect(applyProposal(prose, { scope: 'append', prose: '新段' }, null).next)
      .toBe(prose + '\n\n新段')
  })
  it('selection 用偏移精确替换(即使文本重复)', () => {
    // 选中第二个"甲说话。",偏移 [7,12)
    const sel = { from: 7, to: 12, text: '甲说话。' }
    const r = applyProposal(prose, { scope: 'selection', prose: '甲怒吼。' }, sel)
    expect(r).toEqual({ next: '甲说话。乙沉默。甲怒吼。', ok: true })
  })
  it('selection 原文已漂移 → 不静默替换,标记 drifted', () => {
    const sel = { from: 7, to: 12, text: '甲说话。' }
    const changed = '改过的开头。乙沉默。甲说话。'  // from/to 处已不是原选区
    const r = applyProposal(changed, { scope: 'selection', prose: 'X' }, sel)
    expect(r.ok).toBe(false)
    expect(r.drifted).toBe(true)
    expect(r.next).toBe(changed)   // 不动原文
  })
})
