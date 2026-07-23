import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { focusChiefWithSeed, seedChiefCodexWrite, seedChiefNarrativeWrite } from './chiefSeed.js'

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
})
