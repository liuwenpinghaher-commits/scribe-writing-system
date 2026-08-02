import { describe, expect, it, vi } from 'vitest'
import { DetailPane } from '../DetailPane'

const moduleLoads = vi.hoisted(() => ({
  atlas: 0,
  capability: 0,
  chapterStudio: 0,
  codex: 0,
  qualityContract: 0,
}))

vi.mock('../views/AtlasView', () => {
  moduleLoads.atlas += 1
  return { AtlasView: () => null }
})
vi.mock('../ChapterStudio', () => {
  moduleLoads.chapterStudio += 1
  return { ChapterStudio: () => null }
})
vi.mock('../CodexDetail', () => {
  moduleLoads.codex += 1
  return { CodexDetail: () => null, PropositionDetail: () => null }
})
vi.mock('../layout/CapabilityDetailPanes', () => {
  moduleLoads.capability += 1
  return {
    CapabilityGroupDetailPane: () => null,
    DeduceDetailPane: () => null,
    MotifDetailPane: () => null,
    PromiseDetailPane: () => null,
    RecallResultDetail: () => null,
    ReviewIssueDetail: () => null,
  }
})
vi.mock('../quality/QualityContractEditor', () => {
  moduleLoads.qualityContract += 1
  return { QualityContractEditor: () => null }
})
vi.mock('../Materials', () => {
  return {
    MaterialDetail: () => null,
    MaterialImportPane: () => null,
    MaterialNetworkPane: () => null,
    MaterialNew: () => null,
  }
})

describe('DetailPane 路由分包', () => {
  it('导入详情路由时不提前求值图谱视图模块', () => {
    expect(DetailPane).toBeTypeOf('function')
    expect(moduleLoads.atlas).toBe(0)
    expect(moduleLoads.chapterStudio).toBe(0)
    expect(moduleLoads.codex).toBe(0)
    expect(moduleLoads.capability).toBe(0)
    expect(moduleLoads.qualityContract).toBe(0)
  })
})
