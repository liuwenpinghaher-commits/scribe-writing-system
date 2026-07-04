import { describe, it, expect } from 'vitest'
import { causalStatus } from './causalStatus.js'

// 批D P1-5 假绿根治:/causal 从裸 list 改成 {no_event_data, violations},
// 前端必须读三态且「无事件数据」绝不落到真绿。
describe('causalStatus · /causal 三态', () => {
  it('有事件 + 有违规 → violations,count=违规数', () => {
    const s = causalStatus({ no_event_data: false, violations: [{ event: 'e1', reason: 'x' }, { event: 'e2', reason: 'y' }] })
    expect(s).toEqual({ state: 'violations', count: 2 })
  })
  it('有事件 + 无违规 → complete(真绿,count=0)', () => {
    expect(causalStatus({ no_event_data: false, violations: [] })).toEqual({ state: 'complete', count: 0 })
  })
  it('无事件数据(event 表空)→ no-data 中性,绝不假绿', () => {
    const s = causalStatus({ no_event_data: true, violations: [] })
    expect(s).toEqual({ state: 'no-data', count: 0 })
    expect(s.state).not.toBe('complete')  // 铁律:无数据 ≠ 因果完整✅
  })
  it('初值/拉取失败 null|undefined → no-data,首帧不闪假绿', () => {
    expect(causalStatus(null)).toEqual({ state: 'no-data', count: 0 })
    expect(causalStatus(undefined)).toEqual({ state: 'no-data', count: 0 })
  })
  it('violations 缺失/非数组 → 当作空,不崩', () => {
    expect(causalStatus({ no_event_data: false })).toEqual({ state: 'complete', count: 0 })
    expect(causalStatus({ no_event_data: true })).toEqual({ state: 'no-data', count: 0 })
    expect(causalStatus({ no_event_data: false, violations: null })).toEqual({ state: 'complete', count: 0 })
  })
  it('违规优先于 no_event_data:后端异常同时置位也不吞真实违规', () => {
    expect(causalStatus({ no_event_data: true, violations: [{ event: 'e1', reason: 'x' }] }))
      .toEqual({ state: 'violations', count: 1 })
  })
  it('旧裸数组契约兜底:非空→violations,空→complete', () => {
    expect(causalStatus([{ event: 'e1' }])).toEqual({ state: 'violations', count: 1 })
    expect(causalStatus([])).toEqual({ state: 'complete', count: 0 })
  })
  it('count 与徽章同源:no-data / complete 均 0(不把无数据误算成问题)', () => {
    expect(causalStatus({ no_event_data: true, violations: [] }).count).toBe(0)
    expect(causalStatus({ no_event_data: false, violations: [] }).count).toBe(0)
    expect(causalStatus({ no_event_data: false, violations: [{ event: 'e' }] }).count).toBe(1)
  })
})
