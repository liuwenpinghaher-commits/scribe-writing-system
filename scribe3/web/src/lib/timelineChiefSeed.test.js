import { describe, expect, it } from 'vitest'
import { buildTimelineNextStrokeSeed } from './timelineChiefSeed.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'

describe('buildTimelineNextStrokeSeed', () => {
  it('carries chapter and event, stays discuss', () => {
    const { text, isDiscuss } = buildTimelineNextStrokeSeed(
      {
        id: 'ev-1',
        label: '井底夜审',
        chapter: 4,
        refs: { causal_in: [{ id: 'ev-0', chapter: 3 }] },
      },
      { cat: 'event', chapter: 4 },
    )
    expect(text).toContain('第4章')
    expect(text).toContain('井底夜审')
    expect(text).toContain('ev-0')
    expect(text).not.toMatch(/s3_/)
    expect(shouldUseHermesRun(text)).toBe(false)
    expect(isDiscuss).toBe(true)
  })
})
