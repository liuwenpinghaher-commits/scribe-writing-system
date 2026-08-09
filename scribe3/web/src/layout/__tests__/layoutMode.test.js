import { describe, expect, it } from 'vitest'
import {
  JOURNEY_LAYOUT_SHARES,
  LAYOUT_BOUNDS_BY_MODE,
  LAYOUT_DEFAULTS_BY_MODE,
  LAYOUT_MODE,
  isJourneyViewSel,
  layoutStorageId,
  panelOrderForJourney,
  panelOrderForMode,
  resolveLayoutMode,
  resolvePanelLayout,
  restoreSlotsForOrder,
  visibleLayoutShares,
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
  it('collaboration and reading share chat-wider defaults (content:chat ≈ 4:6)', () => {
    const collab = LAYOUT_DEFAULTS_BY_MODE.collaboration
    const reading = LAYOUT_DEFAULTS_BY_MODE.reading
    expect(collab).toEqual(reading)
    expect(collab.right).toBeGreaterThan(collab.detail)
    expect(collab.right / collab.detail).toBeCloseTo(6 / 4, 1)
    expect(collab.directory).toBeLessThan(collab.detail)
    expect(collab.directory + collab.detail + collab.right).toBe(100)
  })

  it('sanitizeLayout with shared defaults keeps chat-wider shares', () => {
    const collab = sanitizeLayout(null, {
      defaults: LAYOUT_DEFAULTS_BY_MODE.collaboration,
      bounds: LAYOUT_BOUNDS_BY_MODE.collaboration,
    })
    expect(collab.right).toBeGreaterThan(collab.detail)
    expect(collab.right).toBe(52)
    expect(collab.detail).toBe(34)

    const reading = sanitizeLayout(null, {
      defaults: LAYOUT_DEFAULTS_BY_MODE.reading,
      bounds: LAYOUT_BOUNDS_BY_MODE.reading,
    })
    expect(reading).toEqual(collab)
  })
})

describe('panel order + storage id', () => {
  it('all modes put chief (right) rightmost: directory | detail | right', () => {
    expect(panelOrderForMode('collaboration')).toEqual(['directory', 'detail', 'right'])
    expect(panelOrderForMode('reading')).toEqual(['directory', 'detail', 'right'])
  })

  it('layoutStorageId isolates work and mode (v7)', () => {
    expect(layoutStorageId('demo', 'collaboration')).toContain('v7')
    expect(layoutStorageId('demo', 'collaboration')).toContain('collaboration')
    expect(layoutStorageId('demo', 'collaboration')).not.toBe(layoutStorageId('demo', 'reading'))
  })
})

describe('journey tab shares + rightmost session', () => {
  it('isJourneyViewSel only for viewKey=journey', () => {
    expect(isJourneyViewSel({ mode: 'view', viewKey: 'journey' })).toBe(true)
    expect(isJourneyViewSel({ mode: 'view', viewKey: 'atlas' })).toBe(false)
    expect(isJourneyViewSel({ mode: 'node', node: {} })).toBe(false)
    expect(isJourneyViewSel(null)).toBe(false)
  })

  it('journey order: directory | detail | session (session rightmost)', () => {
    expect(panelOrderForJourney()).toEqual(['directory', 'detail', 'right'])
  })

  it('journey defaults: session 52%, journey/detail 34%', () => {
    expect(JOURNEY_LAYOUT_SHARES.right).toBe(52)
    expect(JOURNEY_LAYOUT_SHARES.detail).toBe(34)
    expect(JOURNEY_LAYOUT_SHARES.directory + JOURNEY_LAYOUT_SHARES.detail + JOURNEY_LAYOUT_SHARES.right).toBe(100)
  })

  it('visibleLayoutShares drops directory and keeps session:journey ratio', () => {
    const two = visibleLayoutShares(JOURNEY_LAYOUT_SHARES, ['right', 'detail'])
    expect(Object.keys(two).sort()).toEqual(['detail', 'right'])
    expect(two.right + two.detail).toBeCloseTo(100, 0)
    expect(two.right / two.detail).toBeCloseTo(52 / 34, 1)
  })

  it('resolvePanelLayout journey only overrides when isJourneyView', () => {
    const journey = resolvePanelLayout({ layoutMode: 'reading', isJourneyView: true })
    expect(journey.panelOrder).toEqual(['directory', 'detail', 'right'])
    expect(journey.layoutDefaults.right).toBe(52)
    expect(journey.layoutDefaults.detail).toBe(34)
    expect(journey.detailMinPercent).toBe(28)
    expect(journey.storageMode).toBe('journey-v4')

    const atlas = resolvePanelLayout({ layoutMode: 'reading', isJourneyView: false, isView: true })
    expect(atlas.panelOrder).toEqual(['directory', 'detail', 'right'])
    expect(atlas.layoutDefaults.right).toBe(52)
    expect(atlas.layoutDefaults.detail).toBe(34)
    expect(atlas.detailMinPercent).toBe(40)
    expect(atlas.storageMode).toBe('reading')
  })
})

describe('restoreSlotsForOrder (directory | detail | right)', () => {
  const order = panelOrderForMode('collaboration')

  it('directory collapsed: restore on detail left', () => {
    expect(restoreSlotsForOrder(order, { directoryCollapsed: true, rightCollapsed: false, isView: false }))
      .toEqual({ directory: { hostId: 'detail', edge: 'left' }, right: null })
  })

  it('right collapsed: restore on detail right edge', () => {
    expect(restoreSlotsForOrder(order, { directoryCollapsed: false, rightCollapsed: true, isView: false }))
      .toEqual({ directory: null, right: { hostId: 'detail', edge: 'right' } })
  })

  it('both collapsed: directory left + right opposite on detail', () => {
    const slots = restoreSlotsForOrder(order, {
      directoryCollapsed: true,
      rightCollapsed: true,
      isView: false,
    })
    expect(slots.directory).toEqual({ hostId: 'detail', edge: 'left' })
    expect(slots.right).toEqual({ hostId: 'detail', edge: 'right' })
  })

  it('view: no directory restore; right collapsed hosts on detail right', () => {
    expect(restoreSlotsForOrder(order, { directoryCollapsed: true, rightCollapsed: true, isView: true }))
      .toEqual({ directory: null, right: { hostId: 'detail', edge: 'right' } })
  })
})
