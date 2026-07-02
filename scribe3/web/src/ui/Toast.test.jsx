import { describe, it, expect, vi, beforeEach } from 'vitest'

// sonner 是底层:mock 掉,验证 showToast 把四词表 ok|danger|warn|info 正确映射到
// sonner 的 success/error/warning/info(其它/缺省 → 默认 toast)。
const calls = { default: [], success: [], error: [], warning: [], info: [] }
vi.mock('sonner', () => {
  const toast = (msg, o) => calls.default.push([msg, o])
  toast.success = (msg, o) => calls.success.push([msg, o])
  toast.error = (msg, o) => calls.error.push([msg, o])
  toast.warning = (msg, o) => calls.warning.push([msg, o])
  toast.info = (msg, o) => calls.info.push([msg, o])
  return { toast, Toaster: () => null }
})

import { showToast } from './Toast.jsx'

beforeEach(() => { calls.default = []; calls.success = []; calls.error = []; calls.warning = []; calls.info = [] })

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
  it('tone warn → sonner.warning', () => {
    showToast('careful', { tone: 'warn' })
    expect(calls.warning).toHaveLength(1)
    expect(calls.warning[0][0]).toBe('careful')
  })
  it('tone info → sonner.info', () => {
    showToast('note', { tone: 'info' })
    expect(calls.info).toHaveLength(1)
    expect(calls.info[0][0]).toBe('note')
  })
  it('duration 透传', () => {
    showToast('x', { duration: 1000 })
    expect(calls.default[0][1]).toEqual({ duration: 1000 })
  })
})
