import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  isCodexObjectGone,
  notifyWorldWriteApproved,
  registerPendingCodexDelete,
  readPendingCodexDelete,
  clearPendingCodexDelete,
  watchCodexObjectGone,
  WORLD_WRITE_EVENT,
} from './codexLifecycle.js'

describe('codexLifecycle', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
    clearPendingCodexDelete()
  })

  it('register/read/clear pending delete', () => {
    registerPendingCodexDelete({ objectType: 'role', objectId: '小翠', label: '小翠' })
    expect(readPendingCodexDelete()).toMatchObject({ objectType: 'role', objectId: '小翠' })
    clearPendingCodexDelete()
    expect(readPendingCodexDelete()).toBeNull()
  })

  it('isCodexObjectGone: 404 → true; archived → true; 正常 → false', async () => {
    const api404 = { get: vi.fn().mockRejectedValue(Object.assign(new Error('HTTP 404'), { status: 404 })) }
    await expect(isCodexObjectGone(api404, 'role', '甲')).resolves.toBe(true)

    const apiArch = { get: vi.fn().mockResolvedValue({ name: '甲', archived: true }) }
    await expect(isCodexObjectGone(apiArch, 'role', '甲')).resolves.toBe(true)

    const apiOk = { get: vi.fn().mockResolvedValue({ name: '甲', archived: false }) }
    await expect(isCodexObjectGone(apiOk, 'role', '甲')).resolves.toBe(false)
  })

  it('watchCodexObjectGone 在批准事件后加速探测', async () => {
    vi.useRealTimers()
    let n = 0
    const api = {
      get: vi.fn().mockImplementation(async () => {
        n += 1
        if (n < 2) return { name: '甲', archived: false }
        return { name: '甲', archived: true }
      }),
    }
    const p = watchCodexObjectGone(api, { objectType: 'role', objectId: '甲' }, { intervalMs: 30, timeoutMs: 3000 })
    await new Promise((r) => setTimeout(r, 5))
    notifyWorldWriteApproved({ decision: 'approve' })
    await expect(p).resolves.toBe('gone')
    expect(api.get.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('notifyWorldWriteApproved 派发自定义事件', () => {
    const spy = vi.fn()
    window.addEventListener(WORLD_WRITE_EVENT, spy)
    notifyWorldWriteApproved({ decision: 'approve' })
    expect(spy).toHaveBeenCalled()
    window.removeEventListener(WORLD_WRITE_EVENT, spy)
  })
})
