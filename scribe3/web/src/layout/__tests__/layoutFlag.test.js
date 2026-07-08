import { describe, expect, it } from 'vitest'
import { isFourPaneLayoutEnabled } from '../layoutFlag'

describe('isFourPaneLayoutEnabled', () => {
  it('默认启用四栏布局,避免真实浏览器缺少 flag 时回到旧三栏', () => {
    const storage = { getItem: () => null }

    expect(isFourPaneLayoutEnabled(storage)).toBe(true)
  })

  it('只有显式关闭时才回到旧三栏', () => {
    expect(isFourPaneLayoutEnabled({ getItem: () => '0' })).toBe(false)
    expect(isFourPaneLayoutEnabled({ getItem: () => '1' })).toBe(true)
  })

  it('localStorage 不可用时仍默认启用四栏布局', () => {
    const brokenStorage = { getItem: () => { throw new Error('blocked') } }

    expect(isFourPaneLayoutEnabled(brokenStorage)).toBe(true)
  })
})
