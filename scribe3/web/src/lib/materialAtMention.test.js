import { describe, expect, it } from 'vitest'
import {
  buildAtCatalog,
  codexTreeToAtItems,
  detectAtQuery,
  factsToAtItems,
  filterAtCatalog,
  filterMaterialsForAt,
  formatAtMentionToken,
  insertAtMention,
  insertMaterialAtMention,
  manuscriptTreeToAtItems,
  materialsToAtItems,
  timelineToAtItems,
  viewsToAtItems,
} from './sessionClip.js'
import { nextAtActiveIndex } from '../ui/MaterialAtPicker.jsx'

describe('detectAtQuery', () => {
  it('finds @query at caret', () => {
    const t = '请看 @霜'
    expect(detectAtQuery(t, t.length)).toEqual({ atIndex: 3, query: '霜', caret: t.length })
  })
  it('ignores email-like mid-token @', () => {
    expect(detectAtQuery('a@b', 3)).toBeNull()
  })
})

describe('full catalog domains', () => {
  const mats = [
    { id: '1', title: '霜白城墙', kind: 'snippet', body: '城上' },
  ]
  const codex = {
    type: 'codex_root',
    children: [{
      type: 'codex_category',
      children: [
        { type: 'character', id: 'character:崔判', ref: '崔判', label: '崔判' },
      ],
    }],
  }
  const manuscript = {
    type: 'manuscript_root',
    children: [{
      type: 'volume', id: 'vol:1', label: '卷一',
      children: [
        { type: 'chapter', id: 'ch:1', ref: 1, label: '1 开篇' },
        { type: 'chapter', id: 'ch:2', ref: 2, label: '2 借命' },
      ],
    }],
  }
  const views = [
    { id: 'view:atlas', type: 'view', label: '图谱' },
    { id: 'view:timeline', type: 'view', label: '时间线' },
  ]
  const timeline = {
    items: [
      { id: 'eizz', chapter: 1, kind: 'arc', label: '与苏纸鸢建立联系' },
      { id: 'ev:2', chapter: 2, kind: 'event', label: '借命契燃烧' },
    ],
  }
  const facts = [
    { id: 'prop:1', entity: 'role:崔判', attribute: '身份', value: '阴差' },
  ]

  it('manuscriptTreeToAtItems extracts chapters and volumes', () => {
    const items = manuscriptTreeToAtItems(manuscript)
    expect(items.some((i) => i.type === 'chapter' && i.refToken === 'ch:1')).toBe(true)
    expect(items.some((i) => i.type === 'volume')).toBe(true)
  })

  it('views / timeline / facts builders', () => {
    expect(viewsToAtItems(views).map((i) => i.title)).toEqual(['图谱', '时间线'])
    const ev = timelineToAtItems(timeline)
    expect(ev).toHaveLength(2)
    expect(ev[0].domain).toBe('event')
    expect(ev[0].refToken).toMatch(/eizz|ev:/)
    const f = factsToAtItems(facts)
    expect(f[0].domain).toBe('fact')
    expect(f[0].title).toMatch(/崔判|身份|阴差/)
  })

  it('buildAtCatalog merges all domains; filter finds each', () => {
    const cat = buildAtCatalog({
      materials: mats,
      codexRoot: codex,
      manuscriptRoot: manuscript,
      views,
      timeline,
      facts,
      entities: [{ id: 'role:小翠', kind: 'character', name: '小翠' }],
    })
    const domains = new Set(cat.map((i) => i.domain))
    expect(domains.has('chapter')).toBe(true)
    expect(domains.has('view')).toBe(true)
    expect(domains.has('codex')).toBe(true)
    expect(domains.has('event')).toBe(true)
    expect(domains.has('fact')).toBe(true)
    expect(domains.has('material')).toBe(true)

    expect(filterAtCatalog(cat, '开篇').some((i) => i.domain === 'chapter')).toBe(true)
    expect(filterAtCatalog(cat, '图谱').some((i) => i.domain === 'view')).toBe(true)
    expect(filterAtCatalog(cat, '崔判').some((i) => i.domain === 'codex')).toBe(true)
    expect(filterAtCatalog(cat, '借命契').some((i) => i.domain === 'event')).toBe(true)
    expect(filterAtCatalog(cat, '阴差').some((i) => i.domain === 'fact')).toBe(true)
    expect(filterAtCatalog(cat, '霜白').some((i) => i.domain === 'material')).toBe(true)
    expect(filterAtCatalog(cat, '小翠').some((i) => i.title === '小翠')).toBe(true)
  })
})

describe('format / insert tokens by domain', () => {
  it('formatAtMentionToken labels domains', () => {
    expect(formatAtMentionToken({
      domain: 'chapter', type: 'chapter', refToken: 'ch:1', title: '第1章',
    })).toMatch(/@章节/)
    expect(formatAtMentionToken({
      domain: 'view', type: 'view', refToken: 'view:atlas', title: '图谱',
    })).toMatch(/@视图/)
    expect(formatAtMentionToken({
      domain: 'event', type: 'event', refToken: 'ev:x', title: '燃烧',
    })).toMatch(/@事件/)
    expect(formatAtMentionToken({
      domain: 'fact', type: 'fact', refToken: 'prop:1', title: '身份',
    })).toMatch(/@命题/)
    expect(formatAtMentionToken({
      domain: 'codex', type: 'character', refToken: 'character:崔判', title: '崔判',
    })).toMatch(/@设定/)
    expect(formatAtMentionToken({
      domain: 'material', type: 'material', refToken: 'material:9', title: '霜', kind: 'snippet',
    })).toMatch(/@素材/)
  })

  it('insertAtMention for chapter', () => {
    const t = '打开 @第1'
    const out = insertAtMention(t, t.length, {
      domain: 'chapter', type: 'chapter', refToken: 'ch:1', title: '1 开篇',
    })
    expect(out.token).toMatch(/ch:1/)
    expect(out.text).toContain('【@章节')
  })

  it('insertMaterialAtMention still works', () => {
    const t = '结合 @霜'
    const out = insertMaterialAtMention(t, t.length, {
      id: 'mat9', title: '霜白城墙', kind: 'snippet',
    })
    expect(out.token).toMatch(/material:mat9/)
  })

  it('filterMaterialsForAt compat', () => {
    expect(filterMaterialsForAt([{ id: '1', title: '霜' }], '霜')[0].title).toBe('霜')
  })
})

describe('nextAtActiveIndex', () => {
  it('wraps', () => {
    expect(nextAtActiveIndex(0, -1, 3)).toBe(2)
  })
})

describe('materialsToAtItems / codexTree', () => {
  it('skips empty material id', () => {
    expect(materialsToAtItems([{ title: 'x' }])).toEqual([])
  })
  it('codex leaves only', () => {
    const items = codexTreeToAtItems({
      children: [{ type: 'character', id: 'character:甲', label: '甲' }],
    })
    expect(items).toHaveLength(1)
  })
})
