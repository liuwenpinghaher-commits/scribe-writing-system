import { beforeEach, describe, it, expect, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { DetailPane } from '../../DetailPane'

// 生产详情接入测试:CodexDetail / MaterialDetail 保持真身(验证真实详情路径确实被 ObjectFrame 包裹),
// 仅把「不在测范围内、且转译 import 会拉进 sigma/tiptap 等重库」的兄弟组件 stub 掉,
// 并 mock api 让详情组件的网络读取有确定返回(空集 → 详情落到「未找到」态,但对象头部已由 presentationForNode 渲染)。
// 关键断言:标题(<h1>)来自 DetailPane 经 presentationForNode 生成的 ObjectFrame 头部,不依赖子详情组件内部渲染。
const apiMock = vi.hoisted(() => ({
  entities: vi.fn(),
  materials: vi.fn(),
  material: vi.fn(),
  materialRefs: vi.fn(),
  get: vi.fn(),
  getChar: vi.fn(),
  getFact: vi.fn(),
  getFaction: vi.fn(),
  promises: vi.fn(),
  motifs: vi.fn(),
  objectImpact: vi.fn(),
  charAnchors: vi.fn(),
  charStates: vi.fn(),
  voiceFlags: vi.fn(),
  characterRelations: vi.fn(),
}))
vi.mock('../../api', () => ({ api: apiMock }))

// —— 保持真身:DetailPane / ObjectFrame / objectRegistry / ErrorBoundary / CodexDetail / Materials(MaterialDetail)——
// —— stub 掉不在测范围内的重兄弟(与 materials-workbench.test.jsx 同款处理:MaterialImport/MaterialNetwork/RichEditor) ——
vi.mock('../../editor/RichEditor', () => ({
  RichEditor: ({ ariaLabel }) => <textarea aria-label={ariaLabel} readOnly />,
  useUnsavedGuard: vi.fn(),
}))
vi.mock('../../MaterialImport', () => ({ MaterialImport: () => <div data-testid="material-import" /> }))
vi.mock('../../MaterialNetwork', () => ({ MaterialNetwork: () => <div data-testid="material-network" /> }))
vi.mock('../../ChapterStudio', () => ({ ChapterStudio: () => <div data-testid="chapter-studio" /> }))
vi.mock('../../CodexNew', () => ({ CodexNew: () => <div data-testid="codex-new" /> }))
vi.mock('../../ContainerOutline', () => ({ ContainerOutline: () => <div data-testid="container-outline" /> }))
vi.mock('../../NorthStarPanel', () => ({ NorthStarPanel: () => <div data-testid="northstar-panel" /> }))
vi.mock('../../views/AtlasView', () => ({ AtlasView: () => <div data-testid="view-atlas" /> }))
vi.mock('../../views/InsightView', () => ({ InsightView: () => <div data-testid="view-insight" /> }))
vi.mock('../../views/OverviewView', () => ({ OverviewView: () => <div data-testid="view-overview" /> }))
vi.mock('../../views/TimelineView', () => ({ TimelineView: () => <div data-testid="view-timeline" /> }))
vi.mock('../CapabilityDetailPanes', () => ({
  CapabilityGroupDetailPane: () => <div />, DeduceDetailPane: () => <div />, MotifDetailPane: () => <div />,
  PromiseDetailPane: () => <div />, RecallResultDetail: () => <div />, ReviewIssueDetail: () => <div />,
}))
vi.mock('../VolumeDetailPane', () => ({ VolumeDetailPane: () => <div data-testid="volume-detail" /> }))

describe('ObjectFrame 生产详情接入', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.entities.mockResolvedValue([])
    apiMock.materials.mockResolvedValue([])
    apiMock.material.mockResolvedValue({ id: 'a', title: '铃铛资料', kind: 'research', body: '' })
    apiMock.materialRefs.mockResolvedValue([])
    apiMock.get.mockResolvedValue([])
    apiMock.getChar.mockResolvedValue({ id: 'role:a', name: '柳三更', kind: 'character' })
    apiMock.promises.mockResolvedValue([])
    apiMock.motifs.mockResolvedValue([])
    apiMock.objectImpact.mockResolvedValue({ recommended_action: 'archive', references: [] })
    apiMock.charAnchors.mockResolvedValue({ anchors: {}, arc_plan: [] })
    apiMock.charStates.mockResolvedValue([])
    apiMock.voiceFlags.mockResolvedValue([])
    apiMock.characterRelations.mockResolvedValue([])
  })

  // ⚠ ref 用去前缀本地 id('a'),node.id 才带类型前缀(见 targetNavigation.js:codexNode/targetNodeToSelection,
  //   CodexDetail.jsx:53 pickRow / Materials.jsx:136 MaterialDetail 均按此约定匹配)。
  it.each([
    [{ mode: 'node', node: { id: 'character:a', type: 'character', ref: 'a', label: '柳三更' } }, '柳三更', '设定库 / 角色'],
    [{ mode: 'node', node: { id: 'material:a', type: 'material', ref: 'a', label: '铃铛资料' } }, '铃铛资料', '素材库'],
  ])('frames production detail %j', (sel, title, breadcrumb) => {
    render(<DetailPane sel={sel} work="book-a" />)
    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument()
    expect(screen.getByText(breadcrumb)).toBeInTheDocument()
  })

  it('未被包裹的类型(容器/命题)不套对象外框,原详情原样渲染', () => {
    // codex_category 是容器:不进 presentationForNode 的三类,DetailPane 走原兜底(选择目录条目)。
    render(<DetailPane sel={{ mode: 'node', node: { id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色' } }} work="book-a" />)
    expect(screen.queryByRole('heading', { name: '角色' })).toBeNull()
    expect(screen.getByText(/选择目录条目/)).toBeInTheDocument()
  })
})
