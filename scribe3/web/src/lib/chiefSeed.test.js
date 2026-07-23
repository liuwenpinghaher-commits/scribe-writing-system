import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  focusChiefWithSeed,
  seedChiefCodexWrite,
  seedChiefCodexCreate,
  seedChiefNarrativeWrite,
  seedChiefReorderChapters,
  seedChiefDeleteVolume,
  seedChiefAddMaterial,
  seedChiefPatchMaterial,
  seedChiefDeleteMaterial,
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

  it('seedChiefCodexWrite includes type intent and focuses chief', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    const t = seedChiefCodexWrite('chars', { name: '季棠' }, '补外貌')
    expect(t).toMatch(/季棠/)
    expect(t).toMatch(/补外貌/)
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

  it('production structure/codex/material seeds route to Hermes Run', () => {
    const samples = [
      seedChiefCodexCreate('character', { name: '甲' }),
      seedChiefReorderChapters('vol1', [3, 1, 2]),
      seedChiefDeleteVolume('vol1', '卷一'),
      seedChiefAddMaterial({ title: '密室', body: '寒', kind: 'snippet', source: '札记' }),
      seedChiefNarrativeWrite('volume', '新建分卷「潮」', '请用 s3_add_volume 创建卷'),
    ]
    for (const s of samples) {
      expect(shouldUseHermesRun(s)).toBe(true)
    }
  })

  it('seedChiefAddMaterial keeps source for MCP s3_add_material', () => {
    const t = seedChiefAddMaterial({
      title: '密室白描', body: '寒气', kind: 'snippet', source: '《乱世》札记',
    })
    expect(t).toMatch(/source/)
    expect(t).toMatch(/乱世/)
    expect(t).toMatch(/s3_add_material/)
  })

  it('seedChiefPatchMaterial / DeleteMaterial route to Hermes Run', () => {
    const patch = seedChiefPatchMaterial('m1', {
      title: '改', body: '文', kind: 'note', source: '出处',
    })
    const del = seedChiefDeleteMaterial('m1', { title: '改', archive: true })
    expect(patch).toMatch(/s3_patch_material/)
    expect(del).toMatch(/s3_delete_material/)
    expect(shouldUseHermesRun(patch)).toBe(true)
    expect(shouldUseHermesRun(del)).toBe(true)
  })
})
