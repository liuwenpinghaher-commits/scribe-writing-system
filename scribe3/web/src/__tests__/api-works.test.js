import { describe, it, expect, vi, afterEach } from 'vitest'
import { api } from '../api.js'

afterEach(() => { vi.restoreAllMocks() })

const mockFetch = (ok, status, body) => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok,
    status,
    json: async () => body,
  })
}

describe('api works 写操作 — res.ok 检查', () => {
  it('createWork HTTP 500 应 reject', async () => {
    mockFetch(false, 500, { detail: '内部错误' })
    await expect(api.createWork('测试书')).rejects.toThrow('HTTP 500')
  })

  it('renameWork HTTP 500 应 reject', async () => {
    mockFetch(false, 500, { detail: '重命名失败' })
    await expect(api.renameWork('test-slug', '新书名')).rejects.toThrow('HTTP 500')
  })

  it('deleteWork HTTP 500 应 reject', async () => {
    mockFetch(false, 500, { detail: '删除失败' })
    await expect(api.deleteWork('test-slug')).rejects.toThrow('HTTP 500')
  })

  it('createWork 成功时返回 json', async () => {
    mockFetch(true, 201, { slug: 'new-book', title: '新书' })
    const result = await api.createWork('新书')
    expect(result).toEqual({ slug: 'new-book', title: '新书' })
  })
})
