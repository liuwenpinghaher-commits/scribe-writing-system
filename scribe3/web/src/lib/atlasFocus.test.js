import { describe, expect, it } from 'vitest'
import { atlasFocusId, canOpenInAtlas } from './atlasFocus.js'

describe('atlasFocusId', () => {
  it('maps character/role to role:…', () => {
    expect(atlasFocusId({ kind: 'character', row: { id: 'role:小翠', name: '小翠' } })).toBe('role:小翠')
    expect(atlasFocusId({ detailType: 'chars', row: { name: '小翠' }, ref: '小翠' })).toBe('role:小翠')
    expect(atlasFocusId({ kind: 'role', row: { id: '小翠' } })).toBe('role:小翠')
  })

  it('maps proposition/fact to fact:…', () => {
    expect(atlasFocusId({ kind: 'proposition', row: { id: 'fact:p1' }, ref: 'p1' })).toBe('fact:p1')
    expect(atlasFocusId({ kind: 'fact', row: {}, ref: '井底有骨' })).toBe('fact:井底有骨')
  })

  it('maps faction/item to faction:/item:', () => {
    expect(atlasFocusId({ detailType: 'factions', row: { name: '秘会' }, ref: '秘会' })).toBe('faction:秘会')
    expect(atlasFocusId({ detailType: 'items', row: { name: '铜炉' } })).toBe('item:铜炉')
    expect(canOpenInAtlas({ detailType: 'factions', row: { name: 'x' } })).toBe(true)
  })

  it('returns null for types still outside store.graph', () => {
    expect(atlasFocusId({ detailType: 'terms', row: { name: '气' } })).toBeNull()
    expect(atlasFocusId({ detailType: 'promises', row: { id: 'p1' } })).toBeNull()
    expect(canOpenInAtlas({ kind: 'character', ref: '甲' })).toBe(true)
  })
})
