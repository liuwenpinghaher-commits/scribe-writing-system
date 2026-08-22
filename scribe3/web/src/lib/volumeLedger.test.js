import { describe, expect, it } from 'vitest'
import {
  remainingLaterFromOutline,
  volumeRemainingWork,
  introLooksLikeOneChapterNight,
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
})
