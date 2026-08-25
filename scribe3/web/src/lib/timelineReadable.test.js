import { describe, expect, it } from 'vitest'
import {
  groupTimelineItems,
  bootWindowForChapter,
  timelineEmptyKind,
  timelineEmptyCopy,
} from './timelineReadable.js'

describe('groupTimelineItems', () => {
  it('groups by chapter so list can answer what happened in N', () => {
    const groups = groupTimelineItems([
      { raw: { id: 'a', kind: 'event', chapter: 3, label: '夜审' }, cat: 'event' },
      { raw: { id: 'b', kind: 'relation_start', chapter: 2, label: '同盟' }, cat: 'relation' },
      { raw: { id: 'c', kind: 'event', chapter: 3, label: '开灯' }, cat: 'event' },
    ])
    expect(groups.map((g) => g.chapter)).toEqual([2, 3])
    expect(groups[1].rows.map((r) => r.label)).toEqual(['夜审', '开灯'])
  })
})

describe('bootWindowForChapter', () => {
  it('centers on writing chapter, not book tail', () => {
    expect(bootWindowForChapter(3)).toEqual({ n: 3, from: 1, to: 8 })
    expect(bootWindowForChapter(null)).toBe(null)
    expect(bootWindowForChapter(undefined)).toBe(null)
    expect(bootWindowForChapter(0)).toBe(null)
  })
})

describe('timelineEmptyKind', () => {
  it('no items at all → 还没有事件', () => {
    expect(timelineEmptyKind({ data: { items: [] }, hasContent: false })).toBe('no_events')
    expect(timelineEmptyCopy('no_events').title).toMatch(/事件/)
  })

  it('has items but none in view → 这窗里是空的', () => {
    expect(timelineEmptyKind({
      data: { items: [{ id: 1 }] },
      hasContent: false,
    })).toBe('empty_window')
    expect(timelineEmptyCopy('empty_window').title).toMatch(/窗/)
  })
})
