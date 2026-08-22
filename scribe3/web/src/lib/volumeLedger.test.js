import { describe, expect, it } from 'vitest'
import {
  remainingLaterFromOutline,
  volumeRemainingWork,
  introLooksLikeOneChapterNight,
  volumePendingHuman,
  pendingOutlineLine,
} from './volumeLedger.js'

describe('volumeLedger', () => {
  const outline = {
    chapters: [
      { seq: 1, title: '华山成核', volume: 'cage', synopsis: '按碎片', has_prose: true },
      { seq: 2, title: '四十二度', volume: 'cage', synopsis: '体温标价', has_prose: false },
      { seq: 3, title: '金縢裂纹', volume: 'cage', synopsis: '金縢被点名', has_prose: false },
      { seq: 4, title: '灭活边缘', volume: 'cage', synopsis: '灭活三分钟', has_prose: false },
    ],
  }

  it('remaining later excludes tonight', () => {
    const later = remainingLaterFromOutline(outline, 1)
    expect(later.map((c) => c.title)).toEqual(['四十二度', '金縢裂纹', '灭活边缘'])
  })

  it('volume remaining excludes chapters with prose', () => {
    const later = volumeRemainingWork(outline, 'cage')
    expect(later.map((c) => c.seq)).toEqual([2, 3, 4])
  })

  it('intro that names only one chapter looks like one night', () => {
    expect(introLooksLikeOneChapterNight('华山成核那一夜', outline.chapters)).toBe(true)
    expect(introLooksLikeOneChapterNight('华山成核 / 四十二度 / 金縢裂纹 / 灭活边缘', outline.chapters)).toBe(false)
  })

  it('pending human lists stale and review in this volume', () => {
    const o = {
      chapters: [
        { seq: 1, title: '华山成核', volume: 'cage', outline_status: 'stale' },
        { seq: 2, title: '四十二度', volume: 'cage', outline_status: 'review' },
        { seq: 3, title: '金縢裂纹', volume: 'cage', outline_status: 'frozen' },
        { seq: 9, title: '别卷', volume: 'other', outline_status: 'stale' },
      ],
    }
    expect(volumePendingHuman(o, 'cage').map((c) => c.seq)).toEqual([1, 2])
    expect(pendingOutlineLine(o.chapters[0])).toMatch(/还没冻回去/)
    expect(pendingOutlineLine(o.chapters[0])).toMatch(/冻回去/)
    expect(pendingOutlineLine(o.chapters[1])).toMatch(/看一眼对不对/)
    expect(pendingOutlineLine(o.chapters[1])).toMatch(/冻回去/)
  })

  it('review copy distinguishes high confidence vs too many edits', () => {
    expect(pendingOutlineLine({
      seq: 2, title: '四十二度', outline_status: 'review', confidence: 'high', outline_rev: 1,
    })).toMatch(/高把握改的/)
    expect(pendingOutlineLine({
      seq: 2, title: '四十二度', outline_status: 'review', outline_rev: 3,
    })).toMatch(/纲已改过 3 次/)
    expect(pendingOutlineLine({
      seq: 2, title: '四十二度', outline_status: 'review', confidence: 'high', outline_rev: 3,
    })).toMatch(/纲已改过 3 次/)
    expect(pendingOutlineLine({
      seq: 2, title: '四十二度', outline_status: 'review', confidence: 'high', outline_rev: 3,
    })).not.toMatch(/高把握改的/)
  })
})
