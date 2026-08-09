import { describe, expect, it } from 'vitest'
import {
  filterPromiseRows,
  filterMotifRows,
  promiseItemNode,
  motifItemNode,
} from '../capabilityItems'

describe('filterPromiseRows', () => {
  const ledger = {
    open: [
      { id: 'p1', text: '铜炉要响', setup_chapter: 1, payoff_chapter: 5, overdue: true },
      { id: 'p2', text: '仍悬一条', setup_chapter: 2, payoff_chapter: 9, overdue: false },
    ],
    closed: [
      { id: 'p3', text: '已收', setup_chapter: 1, payoff_chapter: 3, status: 'closed' },
    ],
    red_herring: [],
    abandoned: [],
  }

  it('payoff/setup 按章过滤', () => {
    expect(filterPromiseRows(ledger, 'payoff', 5).map((p) => p.id)).toEqual(['p1'])
    expect(filterPromiseRows(ledger, 'setup', 1).map((p) => p.id)).toEqual(['p1', 'p3'])
  })

  it('overdue / open / done', () => {
    expect(filterPromiseRows(ledger, 'overdue', null).map((p) => p.id)).toEqual(['p1'])
    expect(filterPromiseRows(ledger, 'open', null)).toHaveLength(2)
    expect(filterPromiseRows(ledger, 'done', null).map((p) => p.id)).toEqual(['p3'])
  })

  it('promiseItemNode 产出 codex 叶节点', () => {
    const n = promiseItemNode(ledger.open[0], 5, 'risk')
    expect(n).toMatchObject({
      id: 'promise:p1',
      type: 'promise',
      capability: 'promise',
      ref: 'p1',
    })
    expect(n.meta.overdue).toBe(true)
  })
})

describe('statusLabels · 列表 meta 中文', () => {
  it('heat/status 可映射中文', async () => {
    const { uiStatusLabel, MOTIF_HEAT_CN, PROMISE_STATUS_CN } = await import('../../lib/statusLabels')
    expect(uiStatusLabel('hot', MOTIF_HEAT_CN)).toBe('过热')
    expect(uiStatusLabel('cold', MOTIF_HEAT_CN)).toBe('该回声')
    expect(uiStatusLabel('neutral', MOTIF_HEAT_CN)).toBe('平稳')
    expect(uiStatusLabel('open', PROMISE_STATUS_CN)).toBe('未收')
    expect(uiStatusLabel('closed', PROMISE_STATUS_CN)).toBe('已收')
    expect(uiStatusLabel('abandoned', PROMISE_STATUS_CN)).toBe('已弃')
  })
})

describe('filterMotifRows', () => {
  const state = {
    motifs: [
      { id: 'm1', name: '铜腥', theme: '味', unfolding: '升', hit_count: 5, heat: 'hot' },
      { id: 'm2', name: '空标签' },
    ],
    instances: [{ motif_id: 'm1', evidence: '第3章铜腥' }],
    schedule: { rows: [{ id: 'm1', heat: 'hot', streak: 2 }] },
  }

  it('chapter 仅本章触及', () => {
    expect(filterMotifRows(state, 'chapter', 3).map((m) => m.id)).toEqual(['m1'])
  })

  it('thin / repeat', () => {
    expect(filterMotifRows(state, 'thin', 1).map((m) => m.id)).toEqual(['m2'])
    expect(filterMotifRows(state, 'repeat', 1).map((m) => m.id)).toEqual(['m1'])
  })

  it('motifItemNode 产出 leaf', () => {
    const n = motifItemNode(state.motifs[0], 3, 'evidence')
    expect(n).toMatchObject({ type: 'motif', ref: 'm1', capability: 'motif' })
  })
})
