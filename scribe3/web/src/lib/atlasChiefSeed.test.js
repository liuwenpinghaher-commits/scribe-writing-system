import { describe, it, expect, vi, beforeEach } from 'vitest'
import { buildAtlasDiscussSeed, buildAtlasNextStrokeSeed, buildAtlasWriteSeed } from './atlasChiefSeed.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'

describe('atlasChiefSeed', () => {
  it('discuss seed does not force Hermes world-write', () => {
    const { text, isDiscuss } = buildAtlasDiscussSeed(
      { id: 'role:甲', type: 'character', label: '甲' },
      { hop: 1, focusLabel: '乙', degree: 3, arcLine: 'overdue · 中点' },
    )
    expect(text).toContain('【图谱操作台】')
    expect(text).toContain('甲')
    expect(text).not.toMatch(/s3_/)
    expect(shouldUseHermesRun(text)).toBe(false)
    expect(isDiscuss).toBe(true)
  })

  it('write seed forces Hermes path', () => {
    const text = buildAtlasWriteSeed({ id: 'role:甲', type: 'character', label: '甲' })
    expect(shouldUseHermesRun(text)).toBe(true)
    expect(text).toMatch(/s3_/)
  })

  it('secret uses placeholder not plaintext', () => {
    const { text } = buildAtlasDiscussSeed(
      { id: 'fact:x', type: 'proposition', label: '机密正文XYZ', secret: true },
      {},
    )
    expect(text).not.toContain('机密正文XYZ')
    expect(text).toContain('私密')
  })

  it('next-stroke seed carries chapter and knowledge gap, stays discuss', () => {
    const { text, isDiscuss } = buildAtlasNextStrokeSeed(
      { id: 'role:乙', type: 'character', label: '乙' },
      {
        chapter: 3,
        focusLabel: '甲',
        onlyFocus: [{ id: 'fact:a', label: '甲独知井底' }],
        onlySelf: [{ id: 'fact:b', label: '乙独知契约' }],
      },
    )
    expect(text).toContain('截至第3章')
    expect(text).toContain('甲独知井底')
    expect(text).toContain('乙独知契约')
    expect(text).toMatch(/下一笔/)
    expect(text).not.toMatch(/s3_/)
    expect(shouldUseHermesRun(text)).toBe(false)
    expect(isDiscuss).toBe(true)
  })

  it('next-stroke never leaks secret plaintext', () => {
    const { text } = buildAtlasNextStrokeSeed(
      { id: 'role:乙', type: 'character', label: '乙' },
      {
        chapter: 2,
        focusLabel: '甲',
        onlyFocus: [{ id: 'fact:s', label: '不该出现的明文', secret: true }],
      },
    )
    expect(text).not.toContain('不该出现的明文')
    expect(text).toContain('私密')
  })
})
