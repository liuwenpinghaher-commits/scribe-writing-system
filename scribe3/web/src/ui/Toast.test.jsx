import { describe, it, expect, vi, beforeEach } from 'vitest'

// sonner 是底层:mock 掉,验证 showToast 把 tone 正确映射到 sonner 的 success/error/默认。
const calls = { default: [], success: [], error: [] }
vi.mock('sonner', () => {
  const toast = (msg, o) => calls.default.push([msg, o])
  toast.success = (msg, o) => calls.success.push([msg, o])
  toast.error = (msg, o) => calls.error.push([msg, o])
  return { toast, Toaster: () => null }
})

import { showToast } from './Toast.jsx'

beforeEach(() => { calls.default = []; calls.success = []; calls.error = [] })

describe('showToast', () => {
  it('默认 tone → sonner 默认 toast', () => {
    showToast('hi')
    expect(calls.default).toHaveLength(1)
    expect(calls.default[0][0]).toBe('hi')
  })
  it('tone danger → sonner.error', () => {
    showToast('boom', { tone: 'danger' })
    expect(calls.error).toHaveLength(1)
    expect(calls.error[0][0]).toBe('boom')
  })
  it('tone ok → sonner.success', () => {
    showToast('done', { tone: 'ok' })
    expect(calls.success).toHaveLength(1)
  })
  it('duration 透传', () => {
    showToast('x', { duration: 1000 })
    expect(calls.default[0][1]).toEqual({ duration: 1000 })
  })
})
