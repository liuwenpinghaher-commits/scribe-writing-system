import { describe, it, expect, beforeEach } from 'vitest'
import { loadButtons, addButton, removeButton } from './rewriteButtons.js'

describe('rewriteButtons', () => {
  beforeEach(() => localStorage.clear())
  it('默认空', () => {
    expect(loadButtons('main')).toEqual([])
  })
  it('add 后能读回,按 work 隔离', () => {
    addButton('main', '压缩、去形容词')
    addButton('other', '加潜台词')
    expect(loadButtons('main')).toEqual(['压缩、去形容词'])
    expect(loadButtons('other')).toEqual(['加潜台词'])
  })
  it('去重 + remove', () => {
    addButton('main', '压缩'); addButton('main', '压缩')
    expect(loadButtons('main')).toEqual(['压缩'])
    removeButton('main', '压缩')
    expect(loadButtons('main')).toEqual([])
  })
})
