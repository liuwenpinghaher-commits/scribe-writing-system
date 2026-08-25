import { describe, expect, it } from 'vitest'
import {
  rankWeakChapters,
  weakChapterEmptyKind,
  weakChapterEmptyCopy,
  promiseEmptyKind,
  promiseEmptyCopy,
  breathDefaultSeq,
} from './insightReadable.js'

describe('rankWeakChapters', () => {
  it('pins current writing chapter when it is also weak', () => {
    const rows = rankWeakChapters([
      { seq: 1, title: '开篇', qc_issues: 1, causal: 0 },
      { seq: 3, title: '灯罩', qc_issues: 2, causal: 1 },
      { seq: 5, title: '尾', qc_issues: 9, causal: 0 },
    ], { currentChapter: 3, limit: 8 })
    expect(rows.map((r) => r.seq)).toEqual([3, 5, 1])
  })

  it('does not invent weak rows for a clean current chapter', () => {
    const rows = rankWeakChapters([
      { seq: 3, title: '灯罩', qc_issues: 0, causal: 0 },
      { seq: 5, title: '尾', qc_issues: 2, causal: 0 },
    ], { currentChapter: 3 })
    expect(rows.map((r) => r.seq)).toEqual([5])
  })
})

describe('weakChapterEmptyKind', () => {
  it('empty book is 还没有章, not 质检干净', () => {
    expect(weakChapterEmptyKind({ chapters: [] })).toBe('no_chapters')
    expect(weakChapterEmptyCopy('no_chapters').title).not.toMatch(/干净/)
  })

  it('chapters with no issues is 这几章质检干净', () => {
    expect(weakChapterEmptyKind({
      chapters: [{ seq: 1, qc_issues: 0, causal: 0 }],
    })).toBe('no_weak')
    expect(weakChapterEmptyCopy('no_weak').title).toMatch(/干净/)
  })
})

describe('promiseEmptyKind', () => {
  it('no open promises is 还没有未收的账', () => {
    expect(promiseEmptyKind({ led: { open: [] } })).toBe('no_open')
    expect(promiseEmptyCopy('no_open').title).toMatch(/未收/)
  })
})

describe('breathDefaultSeq', () => {
  it('follows writing chapter, not book tail', () => {
    expect(breathDefaultSeq(3, 12)).toBe(3)
    expect(breathDefaultSeq(null, 12)).toBe(12)
    expect(breathDefaultSeq(undefined, 0)).toBe(1)
  })
})
