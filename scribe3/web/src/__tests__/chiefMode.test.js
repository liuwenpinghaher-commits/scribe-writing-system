import { describe, expect, it } from 'vitest'
import { normalizeChiefMode, resolveRightTab } from '../lib/chiefMode'

describe('chiefMode 兼容映射', () => {
  it('旧右栏 tab 落到主编 + 对应 mode', () => {
    expect(resolveRightTab('selection')).toEqual({ tab: 'chief', mode: 'select' })
    expect(resolveRightTab('pilot')).toEqual({ tab: 'chief', mode: 'pilot' })
    expect(resolveRightTab('chief')).toEqual({ tab: 'chief', mode: null })
    expect(resolveRightTab('inbox')).toEqual({ tab: 'inbox', mode: null })
  })

  it('normalize 非法值为 talk', () => {
    expect(normalizeChiefMode('select')).toBe('select')
    expect(normalizeChiefMode('nope')).toBe('talk')
  })
})
