import { describe, expect, it, vi } from 'vitest'
import App from '../App'

const moduleLoads = vi.hoisted(() => ({ binder: 0, library: 0 }))

vi.mock('../BinderLayout', () => {
  moduleLoads.binder += 1
  return { BinderLayout: () => null }
})
vi.mock('../Library', () => {
  moduleLoads.library += 1
  return { Library: () => null }
})

describe('App 页面分包', () => {
  it('导入顶层编排时不提前求值作品库和写作工作区', () => {
    expect(App).toBeTypeOf('function')
    expect(moduleLoads.library).toBe(0)
    expect(moduleLoads.binder).toBe(0)
  })
})
