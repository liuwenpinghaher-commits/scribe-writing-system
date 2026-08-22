import { describe, expect, it } from 'vitest'
import { buildAddVolumeSeed, buildPatchVolumeSeed } from './volumeSeed.js'
import { volumeMetaPeekVisible, volumeReviewVisible } from './iaDensity.js'

describe('buildPatchVolumeSeed', () => {
  it('must name s3_patch_volume and volume_id', () => {
    const s = buildPatchVolumeSeed({
      volumeId: 'vol-2',
      title: '第二卷',
      intro: '卷纲草稿',
      color: '#111',
      sort_order: 2,
    })
    expect(s).toMatch(/s3_patch_volume/)
    expect(s).toMatch(/volume_id=vol-2/)
    expect(s).toMatch(/卷纲草稿/)
    expect(s).toMatch(/未获批准/)
    expect(s).toMatch(/禁止只写其中一章的夜/)
  })

  it('把本卷已有章写进种子', () => {
    const s = buildPatchVolumeSeed({
      volumeId: 'cage',
      title: '囚笼',
      intro: '四笔账',
      chapters: [
        { seq: 1, title: '华山成核', synopsis: '按碎片' },
        { seq: 2, title: '四十二度', synopsis: '体温标价' },
      ],
    })
    expect(s).toMatch(/华山成核/)
    expect(s).toMatch(/四十二度/)
  })

  it('throws without volumeId', () => {
    expect(() => buildPatchVolumeSeed({})).toThrow(/volumeId/)
  })
})

describe('buildAddVolumeSeed', () => {
  it('names s3_add_volume', () => {
    const s = buildAddVolumeSeed({ title: '第一卷', intro: '纲', chapterSeqs: [1, 2] })
    expect(s).toMatch(/s3_add_volume/)
    expect(s).toMatch(/第一卷/)
    expect(s).toMatch(/\[1, 2\]/)
    expect(s).toMatch(/禁止只写其中一章的夜/)
  })
})

describe('volumeMetaPeekVisible', () => {
  it('essential false; standard/full true', () => {
    expect(volumeMetaPeekVisible('essential')).toBe(false)
    expect(volumeMetaPeekVisible('standard')).toBe(true)
    expect(volumeMetaPeekVisible('full')).toBe(true)
  })
})

describe('volumeReviewVisible', () => {
  it('only full', () => {
    expect(volumeReviewVisible('essential')).toBe(false)
    expect(volumeReviewVisible('standard')).toBe(false)
    expect(volumeReviewVisible('full')).toBe(true)
  })
})
