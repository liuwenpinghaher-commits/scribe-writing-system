import { describe, expect, it, vi } from 'vitest'
import { loadAtCatalogSources } from './useMaterialAt.js'

const apiMock = vi.hoisted(() => ({
  materials: vi.fn(),
  projectTree: vi.fn(),
  timeline: vi.fn(),
  entities: vi.fn(),
  facts: vi.fn(),
}))

vi.mock('../api.js', () => ({ api: apiMock }))

describe('loadAtCatalogSources', () => {
  it('素材请求失败时抛错，不装成空目录', async () => {
    apiMock.materials.mockRejectedValue(new Error('materials down'))
    apiMock.projectTree.mockResolvedValue(null)
    apiMock.timeline.mockResolvedValue(null)
    apiMock.entities.mockResolvedValue([])
    await expect(loadAtCatalogSources('霜白')).rejects.toThrow(/materials down/)
  })

  it('有查询时把 q 交给服务端，不靠前端 300 条再滤', async () => {
    apiMock.materials.mockResolvedValue({ items: [], next_cursor: null, total: 0 })
    apiMock.projectTree.mockResolvedValue(null)
    apiMock.timeline.mockResolvedValue(null)
    apiMock.entities.mockResolvedValue([])
    await loadAtCatalogSources('霜白城墙')
    expect(apiMock.materials).toHaveBeenCalledWith(expect.objectContaining({
      q: '霜白城墙',
    }))
  })
})
