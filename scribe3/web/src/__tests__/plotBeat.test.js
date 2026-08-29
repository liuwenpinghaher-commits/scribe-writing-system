import { describe, it, expect } from 'vitest'
import { plotBeat, ACTION_TOKEN } from '../plotBeat'

describe('plotBeat', () => {
  it('付温度买几息 → 买 / 半成', () => {
    const b = plotBeat({
      focalizer: 'role:柳岸青',
      synopsis: '柳岸青付零点五度，交易接口只差一步没合上。',
    })
    expect(b.focalizer).toBe('柳岸青')
    expect(b.action).toBe('买')
    expect(b.outcome).toBe('半成')
  })

  it('挡住 / 失败 / 被锁 → 败', () => {
    expect(plotBeat({ synopsis: '付零点七度挡住吞名' }).outcome).toBe('败')
    expect(plotBeat({ synopsis: '付零点五度买断白牌七息，白牌挡秤失败' }).outcome).toBe('败')
    expect(plotBeat({ synopsis: '付腕内零点五度买验锁三息，交差被锁' }).outcome).toBe('败')
  })

  it('six sampled chapters are the same shape: 柳岸青+买+非成', () => {
    const samples = [
      '付零点五度，交易接口只差一步没合上',
      '付零点七度挡住吞名',
      '付零点五度买断白牌七息，白牌挡秤失败',
      '付腕内零点五度买验锁三息，交差被锁',
      '付掌心零点四度自补半枚缺口',
      '付锚体零点三度让合法炉只熔冷票',
    ]
    const beats = samples.map((synopsis) => plotBeat({ synopsis }))
    expect(new Set(beats.map((b) => b.action))).toEqual(new Set(['买']))
    expect(beats.every((b) => b.outcome !== '成')).toBe(true)
  })

  it('explicit focalizer wins; empty infers 柳岸青 from 付', () => {
    expect(plotBeat({ focalizer: 'role:兰因', synopsis: '兰因付掌心零点二度' }).focalizer).toBe('兰因')
    expect(plotBeat({ synopsis: '柳岸青付掌心零点三度换三息按压' }).focalizer).toBe('柳岸青')
  })

  it('non-buy actions classify: 揭发 / 结盟 / 背叛', () => {
    expect(plotBeat({ synopsis: '沈烛揭发炉主身份，金縢当场摊牌' }).action).toBe('揭发')
    expect(plotBeat({ synopsis: '兰因与牧场主结盟，联手挡下观测权' }).action).toBe('结盟')
    expect(plotBeat({ synopsis: '赫斯背叛守火人，把名册卖给档案局' }).action).toBe('背叛')
  })

  it('relation changes when the synopsis names a shift', () => {
    expect(plotBeat({ synopsis: '兰因与柳岸青反目，摊牌不跟' }).relation).toBe('反目')
    expect(plotBeat({ synopsis: '付零点三度买三息' }).relation).toBe('未变')
  })

  it('win is 成 when the chapter lands', () => {
    expect(plotBeat({ synopsis: '双权试官判双权按回成立' }).outcome).toBe('成')
  })

  it('ACTION_TOKEN is stable so a wall of 买 is one color', () => {
    expect(ACTION_TOKEN.买).toBeTruthy()
    expect(ACTION_TOKEN.买).not.toBe(ACTION_TOKEN.揭发)
  })

  it('stored plot_action wins over synopsis inference', () => {
    const b = plotBeat({
      focalizer: 'role:兰因',
      plot_action: '揭发',
      synopsis: '兰因付零点五度买三息，只差一步没合上。',
    })
    expect(b.action).toBe('揭发')
    expect(b.focalizer).toBe('兰因')
  })
})
