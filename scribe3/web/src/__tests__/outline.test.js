import { describe, it, expect } from 'vitest'
import { computeReorder } from '../Corkboard'
import { povToken, cardColorVar, wcLabel, LABEL_META } from '../outlineColors'

describe('computeReorder', () => {
  it('moves active before over', () => {
    expect(computeReorder([1, 2, 3, 4], 4, 2)).toEqual([1, 4, 2, 3])
  })
  it('no-op when same', () => {
    expect(computeReorder([1, 2, 3], 2, 2)).toEqual([1, 2, 3])
  })
  it('no-op when not found', () => {
    expect(computeReorder([1, 2, 3], 9, 2)).toEqual([1, 2, 3])
  })
})

describe('outlineColors', () => {
  it('povToken is stable per focalizer', () => {
    expect(povToken('焦三')).toBe(povToken('焦三'))
    expect(povToken('')).toBe('faint')
  })
  it('cardColorVar by status maps label → token', () => {
    expect(cardColorVar({ label: 'done' }, 'status')).toBe(`var(--color-${LABEL_META.done.token})`)
    expect(cardColorVar({ label: undefined }, 'status')).toBe('var(--color-line)')
  })
  it('cardColorVar by pov uses focalizer hash', () => {
    expect(cardColorVar({ focalizer: '焦三' }, 'pov')).toBe(`var(--color-${povToken('焦三')})`)
  })
  it('cardColorVar by plot uses action token', () => {
    expect(cardColorVar({ synopsis: '付零点五度买三息' }, 'plot')).toMatch(/var\(--color-/)
  })
  it('wcLabel compacts thousands', () => {
    expect(wcLabel(3120)).toBe('3.1k')
    expect(wcLabel(800)).toBe('800')
    expect(wcLabel(0)).toBe('0')
  })
})
