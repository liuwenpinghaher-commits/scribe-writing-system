import { describe, it, expect, vi, afterEach } from 'vitest'
import { api } from '../api.js'

afterEach(() => {
  api.setWork('main')
  vi.restoreAllMocks()
})

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

  it('materials 支持分页参数并保留 work 隔离', async () => {
    mockFetch(true, 200, { items: [], next_cursor: null, total: 0 })
    api.setWork('book_a')

    await api.materials({ kind: 'research', limit: 200, cursor: 2, view: 'referenced', q: '借命' })

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/materials?kind=research&limit=200&cursor=2&view=referenced&q=%E5%80%9F%E5%91%BD&work=book_a')
  })

  it('materialGraph 支持 focus/limit/hop 图谱参数', async () => {
    mockFetch(true, 200, { nodes: [], edges: [], truncated: false })

    await api.materialGraph({ focus: 'material:1', limit: 50, hop: 2 })

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/materials/graph?focus=material%3A1&limit=50&hop=2&work=main')
  })
})
