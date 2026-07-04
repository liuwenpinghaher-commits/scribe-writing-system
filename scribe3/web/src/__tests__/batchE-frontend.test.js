import { describe, it, expect } from 'vitest'
import { isChapterNum } from '../lib/utils.js'
import { hasNarrativeData } from '../lib/timelineAxis.js'
import { REL_VOCAB } from '../views/CodexView.jsx'

// ═══ 批D Minor① · 章号 ≥1 守卫(防 since_chapter/valid_from 输入 0 触发后端 500)═══
describe('批D Minor① · isChapterNum(章号 ≥1 守卫)', () => {
  it('空串 / null / undefined 非法', () => {
    expect(isChapterNum('')).toBe(false)
    expect(isChapterNum(null)).toBe(false)
    expect(isChapterNum(undefined)).toBe(false)
  })
  it('0 与负数非法(旧 === "" 守卫漏拦 → 后端 ASSERT >=1 报 500)', () => {
    expect(isChapterNum(0)).toBe(false)
    expect(isChapterNum('0')).toBe(false)
    expect(isChapterNum(-1)).toBe(false)
    expect(isChapterNum('-3')).toBe(false)
  })
  it('非数字非法', () => {
    expect(isChapterNum('abc')).toBe(false)
    expect(isChapterNum(NaN)).toBe(false)
  })
  it('≥1 的整数(数字或数字串)合法', () => {
    expect(isChapterNum(1)).toBe(true)
    expect(isChapterNum('1')).toBe(true)
    expect(isChapterNum(42)).toBe(true)
    expect(isChapterNum('100')).toBe(true)
  })
})

// ═══ #74 · 时间线叙事轴诚实判定 ═══
describe('#74 · hasNarrativeData(叙事顺序轴是否可用)', () => {
  it('无 items / 空 / 非数组 → false', () => {
    expect(hasNarrativeData(null)).toBe(false)
    expect(hasNarrativeData([])).toBe(false)
    expect(hasNarrativeData(undefined)).toBe(false)
  })
  it('事件都无 narrative_position(纯 UI 作者常态)→ false(两轴等价,空操作)', () => {
    expect(hasNarrativeData([
      { kind: 'event', story_chapter: 3, narrative_position: null },
      { kind: 'event', story_chapter: 5, narrative_position: null },
    ])).toBe(false)
  })
  it('narrative_position 等于 story_chapter(线性,非闪回)→ false', () => {
    expect(hasNarrativeData([
      { kind: 'event', story_chapter: 4, narrative_position: 4 },
    ])).toBe(false)
  })
  it('存在叙事位 ≠ 故事章的事件(倒叙/闪回)→ true', () => {
    expect(hasNarrativeData([
      { kind: 'event', story_chapter: 2, narrative_position: null },
      { kind: 'event', story_chapter: 8, narrative_position: 3 },   // 故事第8章,却在第3章叙事位讲述
    ])).toBe(true)
  })
  it('仅非事件条目带 narrative_position 也不算(伏笔/关系只有故事章)', () => {
    expect(hasNarrativeData([
      { kind: 'promise_setup', story_chapter: 1, narrative_position: 9 },
    ])).toBe(false)
  })
  it('story_chapter 缺失时回退 chapter 比较', () => {
    expect(hasNarrativeData([{ kind: 'event', chapter: 7, narrative_position: 2 }])).toBe(true)
    expect(hasNarrativeData([{ kind: 'event', chapter: 7, narrative_position: 7 }])).toBe(false)
  })
})

// ═══ 批D Minor② · REL_VOCAB 去 custom 死字面量 ═══
// 后端 migration 029 relation ASSERT 只收固定 22 词 + 字面量 'custom';自由文本任何真实自定义词都 500。
// 故去掉 'custom' 选项(而非加自由文本框):每个下拉项都映射到后端确收的真实关系词。
describe('批D Minor② · REL_VOCAB 无 custom 死字面量', () => {
  it('词表任一分组都不含 custom 选项', () => {
    const flat = REL_VOCAB.flatMap(([, items]) => items)
    expect(flat).not.toContain('custom')
  })
  it('词表非空且全为受控中文关系词', () => {
    const flat = REL_VOCAB.flatMap(([, items]) => items)
    expect(flat.length).toBeGreaterThan(0)
    expect(flat.every((w) => typeof w === 'string' && w.length > 0)).toBe(true)
  })
})
