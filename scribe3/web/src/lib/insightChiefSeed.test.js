import { describe, expect, it } from 'vitest'
import { buildInsightNextStrokeSeed } from './insightChiefSeed.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'

describe('buildInsightNextStrokeSeed', () => {
  it('carries weak chapter and stays discuss', () => {
    const { text, isDiscuss } = buildInsightNextStrokeSeed(
      { seq: 3, title: '第3章 · 灯罩里的母亲', qc_issues: 2, causal: 1 },
      { kind: 'weak_chapter', chapter: 3 },
    )
    expect(text).toContain('第3章')
    expect(text).toContain('灯罩里的母亲')
    expect(text).toContain('QC 2')
    expect(text).not.toMatch(/s3_/)
    expect(shouldUseHermesRun(text)).toBe(false)
    expect(isDiscuss).toBe(true)
  })

  it('carries open promise without write-tool talk', () => {
    const { text, isDiscuss } = buildInsightNextStrokeSeed(
      { id: 'p1', text: '井底有骨', overdue: true, setup_chapter: 2 },
      { kind: 'promise', chapter: 2 },
    )
    expect(text).toContain('井底有骨')
    expect(text).toContain('超期')
    expect(text).not.toMatch(/s3_/)
    expect(isDiscuss).toBe(true)
  })
})
