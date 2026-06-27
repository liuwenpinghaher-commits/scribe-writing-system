import { describe, it, expect } from 'vitest'
import { toastReducer } from './Toast.jsx'

describe('toastReducer', () => {
  it('add 入队带 id', () => {
    const s = toastReducer([], { type: 'add', toast: { msg: 'x' } })
    expect(s).toHaveLength(1); expect(s[0].id).toBeTruthy(); expect(s[0].msg).toBe('x')
  })
  it('remove 按 id 出队', () => {
    const s1 = toastReducer([], { type: 'add', toast: { msg: 'a', id: 1 } })
    const s2 = toastReducer(s1, { type: 'remove', id: 1 })
    expect(s2).toHaveLength(0)
  })
})
