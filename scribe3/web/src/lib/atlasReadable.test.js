import { describe, expect, it } from 'vitest'
import {
  defaultSliceChapter,
  groupAtlasNodes,
  listNodeLabel,
  atlasEmptyKind,
  atlasEmptyCopy,
} from './atlasReadable.js'

describe('defaultSliceChapter', () => {
  it('uses writing chapter when provided', () => {
    expect(defaultSliceChapter(3)).toBe(3)
    expect(defaultSliceChapter('5')).toBe(5)
  })

  it('book-wide only when no chapter prop', () => {
    expect(defaultSliceChapter(null)).toBe(null)
    expect(defaultSliceChapter(undefined)).toBe(null)
    expect(defaultSliceChapter(0)).toBe(null)
  })
})

describe('groupAtlasNodes / listNodeLabel', () => {
  it('groups characters vs propositions and never titles with fact:', () => {
    const g = groupAtlasNodes([
      { id: 'role:甲', type: 'character', label: '甲' },
      { id: 'fact:d2-4', type: 'proposition', label: '' },
      { id: 'fact:x', type: 'proposition', label: '井底有骨' },
      { id: 'faction:门', type: 'faction', label: '门' },
    ])
    expect(g.characters.map((n) => n.listLabel)).toEqual(['甲'])
    expect(g.propositions.map((n) => n.listLabel)).toEqual(['第2章·行动摘要 #4', '井底有骨'])
    expect(g.others.map((n) => n.listLabel)).toEqual(['门'])
    expect(listNodeLabel({ id: 'fact:d2-4', type: 'proposition', label: 'fact:d2-4' })).toBe('第2章·行动摘要 #4')
  })

  it('secret proposition uses placeholder', () => {
    expect(listNodeLabel({ id: 'fact:s', type: 'proposition', label: '机密', secret: true })).toBe('私密命题')
  })
})

describe('atlasEmptyKind / copy', () => {
  it('no nodes + no chars → 还没有角色', () => {
    expect(atlasEmptyKind({ nodes: [], edges: [] }, [])).toBe('no_chars')
    expect(atlasEmptyCopy('no_chars').title).toMatch(/角色/)
  })

  it('no nodes + has chars + no knows → 还没抽到知情边', () => {
    expect(atlasEmptyKind({ nodes: [], edges: [] }, [{ id: 'role:甲' }])).toBe('no_knows')
    expect(atlasEmptyCopy('no_knows').body).toMatch(/知情/)
  })

  it('has nodes is not empty', () => {
    expect(atlasEmptyKind({ nodes: [{ id: 'role:甲' }], edges: [] }, [{ id: 'role:甲' }])).toBe(null)
  })
})
