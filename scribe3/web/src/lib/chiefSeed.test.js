import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  focusChiefWithSeed,
  seedChiefCodexWrite,
  seedChiefCodexCreate,
  seedChiefNarrativeWrite,
  seedChiefReorderChapters,
  seedChiefDeleteVolume,
} from './chiefSeed.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'

describe('chiefSeed helpers', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })
  afterEach(() => {
    sessionStorage.clear()
  })

  it('focusChiefWithSeed writes storage, seed event, and right-tab focus', () => {
    const seeds = []
    const tabs = []
    const onSeed = (e) => seeds.push(e.detail)
    const onTab = (e) => tabs.push(e.detail)
    window.addEventListener('s3-chief-seed', onSeed)
    window.addEventListener('s3-right-tab', onTab)

    const text = focusChiefWithSeed('hello chief')
    expect(text).toBe('hello chief')
    expect(sessionStorage.getItem('s3.chief.seed')).toBe('hello chief')
    expect(seeds).toEqual(['hello chief'])
    expect(tabs).toEqual(['chief'])

    window.removeEventListener('s3-chief-seed', onSeed)
    window.removeEventListener('s3-right-tab', onTab)
  })

  it('完整设定更正使用注册表驱动的待批工具并聚焦主编', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    const t = seedChiefCodexWrite('chars', { name: '季棠', aliases: ['小棠'], abilities: ['读唇'] }, '补外貌')
    expect(t).toMatch(/季棠/)
    expect(t).toMatch(/补外貌/)
    expect(t).toMatch(/s3_patch_codex/)
    expect(t).toMatch(/aliases/)
    expect(t).toMatch(/abilities/)
    expect(sessionStorage.getItem('s3.chief.seed')).toBe(t)
    expect(tabs).toContain('chief')
  })

  it('seedChiefNarrativeWrite focuses chief', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    seedChiefNarrativeWrite('outline', '第 1 章大纲', '请更新')
    expect(tabs).toContain('chief')
    expect(sessionStorage.getItem('s3.chief.seed')).toMatch(/第 1 章大纲/)
  })

  it('production structure/codex seeds route to Hermes Run', () => {
    const samples = [
      seedChiefCodexCreate('character', { name: '甲' }),
      seedChiefReorderChapters('vol1', [3, 1, 2]),
      seedChiefDeleteVolume('vol1', '卷一'),
      seedChiefNarrativeWrite('volume', '新建分卷「潮」', '请用 s3_add_volume 创建卷'),
    ]
    for (const s of samples) {
      expect(shouldUseHermesRun(s)).toBe(true)
    }
  })
})
