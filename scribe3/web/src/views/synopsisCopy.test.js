import { describe, expect, it } from 'vitest'
import { chapterOneLine, progressLineFromOutline } from './synopsisCopy.js'

describe('chapterOneLine', () => {
  it('优先 settled_note，再 hook_preview，再截断 synopsis', () => {
    expect(chapterOneLine({ settled_note: '办成了核', hook_preview: '钩', synopsis: '长纲' })).toBe('办成了核')
    expect(chapterOneLine({ hook_preview: '钩子一句', synopsis: '长纲' })).toBe('钩子一句')
    expect(chapterOneLine({ synopsis: 'x'.repeat(90) })).toBe(`${'x'.repeat(80)}…`)
    expect(chapterOneLine({})).toBe('还没写这一句')
  })
})

describe('progressLineFromOutline', () => {
  it('无章', () => {
    expect(progressLineFromOutline({ chapters: [] })).toBe('还没有章。')
  })

  it('无正文说立到，不写约 0 字', () => {
    const line = progressLineFromOutline({
      chapters: [
        { seq: 1, title: '华山成核', has_prose: false, settled_note: '成核' },
        { seq: 3, title: '双锚', has_prose: false, synopsis: '设计过' },
      ],
    })
    expect(line).toBe('立到第 3 章《双锚》，还没有正文。全书 2 章。')
    expect(line).not.toMatch(/约 0 字/)
    expect(line).not.toMatch(/写到/)
  })

  it('有正文说写到并带字数', () => {
    const line = progressLineFromOutline({
      chapters: [
        { seq: 1, title: '开篇', has_prose: true, word_count: 1200 },
        { seq: 2, title: '未写', has_prose: false, word_count: 0 },
      ],
    })
    expect(line).toBe('稿子写到第 1 章《开篇》。全书 2 章，约 1200 字。')
  })
})
