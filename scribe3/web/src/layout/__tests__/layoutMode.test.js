import { describe, expect, it } from 'vitest'
import {
  LAYOUT_BOUNDS_BY_MODE,
  LAYOUT_DEFAULTS_BY_MODE,
  LAYOUT_MODE,
  layoutStorageId,
  panelOrderForMode,
  resolveLayoutMode,
  restoreSlotsForOrder,
} from '../layoutMode'
import { sanitizeLayout } from '../sanitizeLayout'

describe('resolveLayoutMode phase-auto', () => {
  it('outline/beats/deduce/draft → collaboration', () => {
    for (const phase of ['outline', 'beats', 'deduce', 'draft']) {
      expect(resolveLayoutMode({ phase, isChapterContext: true })).toBe(LAYOUT_MODE.collaboration)
    }
  })

  it('final → reading', () => {
    expect(resolveLayoutMode({ phase: 'final', isChapterContext: true })).toBe(LAYOUT_MODE.reading)
  })

  it('non-chapter / null phase → collaboration', () => {
    expect(resolveLayoutMode({ phase: null, isChapterContext: false })).toBe(LAYOUT_MODE.collaboration)
    expect(resolveLayoutMode({})).toBe(LAYOUT_MODE.collaboration)
  })

  it('view mode → reading (full canvas detail)', () => {
    expect(resolveLayoutMode({ isView: true, phase: 'outline' })).toBe(LAYOUT_MODE.reading)
  })
})

describe('layout defaults by mode', () => {
  it('collaboration and reading share equal chief/detail defaults', () => {
    const collab = LAYOUT_DEFAULTS_BY_MODE.collaboration
    const reading = LAYOUT_DEFAULTS_BY_MODE.reading
    expect(collab).toEqual(reading)
    expect(collab.right).toBe(collab.detail)
    expect(collab.directory).toBeLessThan(collab.detail)
    expect(collab.directory + collab.detail + collab.right).toBe(100)
  })

  it('sanitizeLayout with shared defaults keeps equal chief/detail shares', () => {
    const collab = sanitizeLayout(null, {
      defaults: LAYOUT_DEFAULTS_BY_MODE.collaboration,
      bounds: LAYOUT_BOUNDS_BY_MODE.collaboration,
    })
    expect(collab.right).toBe(collab.detail)

    const reading = sanitizeLayout(null, {
      defaults: LAYOUT_DEFAULTS_BY_MODE.reading,
      bounds: LAYOUT_BOUNDS_BY_MODE.reading,
    })
    expect(reading).toEqual(collab)
  })
})

describe('panel order + storage id', () => {
  it('collaboration puts chief before detail; reading puts detail before chief', () => {
    expect(panelOrderForMode('collaboration')).toEqual(['directory', 'right', 'detail'])
    expect(panelOrderForMode('reading')).toEqual(['directory', 'detail', 'right'])
  })

  it('layoutStorageId isolates work and mode (v3)', () => {
    expect(layoutStorageId('demo', 'collaboration')).toContain('v3')
    expect(layoutStorageId('demo', 'collaboration')).toContain('collaboration')
    expect(layoutStorageId('demo', 'collaboration')).not.toBe(layoutStorageId('demo', 'reading'))
  })
})

describe('restoreSlotsForOrder (by panel order, not hard-coded on detail)', () => {
  const collab = panelOrderForMode('collaboration') // directory | right | detail
  const reading = panelOrderForMode('reading') // directory | detail | right

  it('reading: both restores host on detail (middle stage)', () => {
    expect(restoreSlotsForOrder(reading, { directoryCollapsed: true, rightCollapsed: false, isView: false }))
      .toEqual({ directory: { hostId: 'detail', edge: 'left' }, right: null })
    expect(restoreSlotsForOrder(reading, { directoryCollapsed: false, rightCollapsed: true, isView: false }))
      .toEqual({ directory: null, right: { hostId: 'detail', edge: 'right' } })
  })

  it('collaboration: directory restore on chief (right panel), not detail', () => {
    expect(restoreSlotsForOrder(collab, { directoryCollapsed: true, rightCollapsed: false, isView: false }))
      .toEqual({ directory: { hostId: 'right', edge: 'left' }, right: null })
  })

  it('collaboration: right restore on previous neighbor (directory right edge)', () => {
    expect(restoreSlotsForOrder(collab, { directoryCollapsed: false, rightCollapsed: true, isView: false }))
      .toEqual({ directory: null, right: { hostId: 'directory', edge: 'right' } })
  })

  it('collaboration: both collapsed → directory left + right opposite edge on detail', () => {
    const slots = restoreSlotsForOrder(collab, {
      directoryCollapsed: true,
      rightCollapsed: true,
      isView: false,
    })
    expect(slots.directory).toEqual({ hostId: 'detail', edge: 'left' })
    expect(slots.right).toEqual({ hostId: 'detail', edge: 'right' })
  })

  it('view: no directory restore', () => {
    expect(restoreSlotsForOrder(reading, { directoryCollapsed: true, rightCollapsed: true, isView: true }))
      .toEqual({ directory: null, right: { hostId: 'detail', edge: 'right' } })
  })
})
