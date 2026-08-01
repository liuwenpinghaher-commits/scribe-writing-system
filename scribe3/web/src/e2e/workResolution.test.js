import { describe, expect, it } from 'vitest'
import { resolveWorkSlugByExactTitle } from './workResolution.js'

describe('resolveWorkSlugByExactTitle', () => {
  it('同前缀作品并存时只解析本次新建作品的 work', () => {
    const works = [
      { slug: 'book_old', title: '上下文质量验收·20260727-01' },
      { slug: 'book_new', title: '上下文质量验收·20260727-02' },
    ]

    expect(resolveWorkSlugByExactTitle(works, '上下文质量验收·20260727-02')).toBe('book_new')
  })

  it('找不到精确书名时拒绝猜测相同前缀作品', () => {
    const works = [{ slug: 'book_old', title: '上下文质量验收·20260727-01' }]

    expect(resolveWorkSlugByExactTitle(works, '上下文质量验收·20260727-02')).toBe('')
  })
})
