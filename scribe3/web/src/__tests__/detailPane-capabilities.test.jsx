import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DetailPane } from '../DetailPane'

const apiMock = vi.hoisted(() => ({
  chapter: vi.fn(),
  entities: vi.fn(),
  promisesLedger: vi.fn(),
  motifs: vi.fn(),
  motifInstances: vi.fn(),
  motifSchedule: vi.fn(),
  motifTimeline: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../ChapterStudio', () => ({ ChapterStudio: () => <div data-testid="chapter-studio" /> }))
vi.mock('../CodexDetail', () => ({
  CodexDetail: ({ node }) => <div data-testid="codex-detail">{node.id}</div>,
  PropositionDetail: ({ node }) => <div data-testid="proposition-detail">{node.id}</div>,
}))
vi.mock('../CodexNew', () => ({ CodexNew: () => <div data-testid="codex-new" /> }))
vi.mock('../Materials', () => ({
  MaterialDetail: ({ node }) => <div data-testid="material-detail">{node.id}</div>,
  MaterialImportPane: () => <div data-testid="material-import-pane">导入素材详情</div>,
  MaterialList: ({ node }) => <div data-testid="material-list">{node.id}</div>,
  MaterialNetworkPane: () => <div data-testid="material-network-pane">素材网络详情</div>,
  MaterialNew: () => <div data-testid="material-new" />,
}))
vi.mock('../views/AtlasView', () => ({ AtlasView: () => <div data-testid="view-atlas" /> }))
vi.mock('../views/InsightView', () => ({ InsightView: () => <div data-testid="view-insight" /> }))
vi.mock('../views/OverviewView', () => ({ OverviewView: () => <div data-testid="view-overview" /> }))
vi.mock('../views/SynopsisView', () => ({ SynopsisView: () => <div data-testid="view-synopsis" /> }))
vi.mock('../views/TimelineView', () => ({ TimelineView: () => <div data-testid="view-timeline" /> }))
vi.mock('../ContainerOutline', () => ({ ContainerOutline: () => <div data-testid="container-outline" /> }))
vi.mock('../NorthStarPanel', () => ({ NorthStarPanel: () => <div data-testid="northstar-panel" /> }))
vi.mock('../DeduceStage', () => ({ DeduceStage: ({ seq, meta }) => <div>演绎工作台:{seq}:{meta?.scene_truth || ''}</div> }))
vi.mock('../quality/ReferenceWorks', () => ({ ReferenceWorks: ({ work }) => <div data-testid="reference-works">参考作品:{work}</div> }))
vi.mock('../quality/QualityReview', () => ({ QualityReview: ({ work, seq }) => <div data-testid="quality-review">质量审阅:{work}:{seq}</div> }))
vi.mock('../quality/QualityContractEditor', () => ({ QualityContractEditor: ({ work }) => <div data-testid="quality-contract">质量合同:{work}</div> }))

describe('DetailPane 能力详情路由', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.chapter.mockResolvedValue({})
    apiMock.entities.mockResolvedValue([])
    apiMock.promisesLedger.mockResolvedValue({
      open: [{ id: 'p1', text: '铜炉会在第七章回收', status: 'open', setup_chapter: 2, payoff_chapter: 7, overdue: false }],
      closed: [],
      red_herring: [],
    })
    apiMock.motifs.mockResolvedValue([{ id: 'm1', name: '铜炉', theme: '借命代价', unfolding: '每次燃起都消耗寿命' }])
    apiMock.motifInstances.mockResolvedValue([{ motif_id: 'm1', evidence: '炉火像一枚倒扣的命' }])
    apiMock.motifSchedule.mockResolvedValue({
      must_echo: [], avoid_overuse: [],
      rows: [{ id: 'm1', name: '铜炉', heat: 'neutral', streak: 0, hit_count: 1 }],
    })
    apiMock.motifTimeline.mockResolvedValue([])
  })

  it.each([
    [{ id: 'deduce:truth', type: 'deduce_view', label: '场景真相', ref: { seq: 23, view: 'truth' } }, /演绎工作台/],
    [{ id: 'promise:payoff', type: 'promise_view', label: '本章要收' }, '伏笔详情'],
    [{ id: 'motif:chapter', type: 'motif_view', label: '本章触及' }, '母题详情'],
    [{ id: 'recall:semantic', type: 'recall_result', label: '语义召回' }, '召回详情'],
    [{ id: 'review:summary', type: 'review_issue', label: '本章总览' }, '校验详情'],
  ])('渲染 %s 对应的能力详情', async (node, text) => {
    render(<DetailPane sel={{ mode: 'node', node }} work="demo" onSelectNode={() => {}} />)

    expect(await screen.findByText(text)).toBeTruthy()
  })

  it('deduce_view 会拉取章 meta 再渲染演绎工作台', async () => {
    apiMock.chapter.mockResolvedValue({ scene_truth: '炉灰变白', deductions: [], involved_characters: [] })
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])

    render(<DetailPane sel={{ mode: 'node', node: { id: 'deduce:truth', type: 'deduce_view', label: '场景真相', ref: { seq: 23, view: 'truth' } } }} work="demo" onSelectNode={() => {}} />)

    expect(await screen.findByText('演绎工作台:23:炉灰变白')).toBeTruthy()
    expect(apiMock.chapter).toHaveBeenCalledWith(23, 'demo')
  })

  it('capability_group 渲染分类总览而不是空详情', async () => {
    render(<DetailPane
      sel={{ mode: 'node', node: {
        id: 'deduce:limited',
        type: 'capability_group',
        capability: 'deduce',
        label: '限知分类',
        ref: { group: 'limited', seq: 23 },
        meta: { seq: 23, count: 4 },
      } }}
      work="demo"
      onSelectNode={() => {}}
    />)

    expect(await screen.findByRole('heading', { name: '限知分类' })).toBeTruthy()
    expect(screen.getByText('分类含义')).toBeTruthy()
    expect(screen.getByText('写作约束')).toBeTruthy()
    // Task 10:配置里无 handler 的假动作按钮已移除,动作只认 live payload
    expect(screen.queryByText('查看全部命中正文')).toBeNull()
    expect(screen.queryByText(/未知节点类型/)).toBeNull()
  })

  it.each([
    [{ id: 'material:import', type: 'material_import', label: '导入素材' }, 'material-import-pane'],
    [{ id: 'material:network', type: 'material_network', label: '记忆网络' }, 'material-network-pane'],
  ])('素材库动作节点 %s 在详情栏渲染', async (node, testId) => {
    render(<DetailPane sel={{ mode: 'node', node }} work="demo" onSelectNode={() => {}} />)

    expect(await screen.findByTestId(testId)).toBeTruthy()
  })

  it('references 节点渲染参考作品工作台', () => {
    render(<DetailPane sel={{ mode: 'node', node: { id: 'references', type: 'references', label: '参考作品' } }} work="demo" onSelectNode={() => {}} />)
    expect(screen.getByTestId('reference-works')).toBeTruthy()
    expect(screen.getByText('参考作品:demo')).toBeTruthy()
  })

  it('quality_review 节点渲染质量审阅并带章号', () => {
    render(<DetailPane sel={{ mode: 'node', node: { id: 'quality:7', type: 'quality_review', label: '质量审阅', ref: { seq: 7 } } }} work="demo" onSelectNode={() => {}} />)
    expect(screen.getByTestId('quality-review')).toBeTruthy()
    expect(screen.getByText('质量审阅:demo:7')).toBeTruthy()
  })

  it('quality_review 没有节点章号时沿用最近选择的章节', () => {
    render(<DetailPane
      sel={{ mode: 'node', node: { id: 'quality_review', type: 'quality_review', label: '质量审阅', ref: null } }}
      work="demo"
      qualitySeq={7}
      onSelectNode={() => {}}
    />)
    expect(screen.getByText('质量审阅:demo:7')).toBeTruthy()
  })

  it('quality_contract 节点渲染全字段质量合同编辑器', async () => {
    render(<DetailPane sel={{ mode: 'node', node: { id: 'quality_contract', type: 'quality_contract', label: '质量合同' } }} work="demo" onSelectNode={() => {}} />)
    expect(await screen.findByTestId('quality-contract')).toBeTruthy()
    expect(screen.getByText('质量合同:demo')).toBeTruthy()
  })

  it('promise_view 渲染真实伏笔台账,不是占位说明', async () => {
    render(<DetailPane sel={{ mode: 'node', node: { id: 'promise:open', type: 'promise_view', label: '仍悬', ref: 'open' } }} work="demo" onSelectNode={() => {}} />)

    expect(await screen.findByText('铜炉会在第七章回收')).toBeTruthy()
    expect(apiMock.promisesLedger).toHaveBeenCalledWith('demo')
    expect(screen.queryByText(/首版先建立/)).toBeNull()
  })

  it('motif_view 渲染真实母题和证据,不是占位说明', async () => {
    render(<DetailPane sel={{ mode: 'node', node: { id: 'motif:chapter', type: 'motif_view', label: '本章触及', ref: 'chapter', meta: { seq: 4 } } }} work="demo" onSelectNode={() => {}} />)

    expect(await screen.findByText('铜炉')).toBeTruthy()
    expect(apiMock.motifs).toHaveBeenCalledWith('demo')
    expect(apiMock.motifInstances).toHaveBeenCalledWith(4, 'demo')
    expect(screen.getByText('炉火像一枚倒扣的命')).toBeTruthy()
    expect(screen.queryByText(/后续再接完整编辑 API/)).toBeNull()
  })

  it('motif_view book 展示全书母题(不因缺 scope 字段而假空)', async () => {
    apiMock.motifs.mockResolvedValue([
      { id: 'm1', name: '铜炉', theme: '借命代价', hit_count: 1 },
      { id: 'm2', name: '纸命', theme: '命如纸', hit_count: 0 },
    ])
    render(<DetailPane sel={{ mode: 'node', node: { id: 'motif:book', type: 'motif_view', label: '全书母题', ref: 'book' } }} work="demo" onSelectNode={() => {}} />)
    expect(await screen.findByText('铜炉')).toBeTruthy()
    expect(screen.getByText('纸命')).toBeTruthy()
  })

  it('motif_view 单条 id 只展示该母题', async () => {
    apiMock.motifs.mockResolvedValue([
      { id: 'm1', name: '铜炉', theme: '借命代价' },
      { id: 'm2', name: '纸命', theme: '命如纸' },
    ])
    render(<DetailPane sel={{ mode: 'node', node: { id: 'motif:m1', type: 'motif_view', label: '铜炉', ref: 'm1' } }} work="demo" onSelectNode={() => {}} />)
    expect(await screen.findByText('铜炉')).toBeTruthy()
    expect(screen.queryByText('纸命')).toBeNull()
  })

  it('motif_view repeat 用 heat=hot 过滤过度重复(优先于裸 hit_count)', async () => {
    apiMock.motifs.mockResolvedValue([
      { id: 'm1', name: '铜炉', hit_count: 2 },
      { id: 'm2', name: '纸命', hit_count: 1 },
    ])
    apiMock.motifSchedule.mockResolvedValue({
      rows: [
        { id: 'm1', name: '铜炉', heat: 'hot', streak: 3, hit_count: 3 },
        { id: 'm2', name: '纸命', heat: 'cold', streak: 0, hit_count: 1 },
      ],
    })
    render(<DetailPane sel={{ mode: 'node', node: { id: 'motif:repeat', type: 'motif_view', label: '过度重复', ref: 'repeat' } }} work="demo" onSelectNode={() => {}} />)
    expect(await screen.findByText('铜炉')).toBeTruthy()
    expect(screen.queryByText('纸命')).toBeNull()
    expect(await screen.findByTestId('motif-heat')).toBeTruthy()
  })

  it('motif_view volume 优先 tier/scope 真绑定', async () => {
    apiMock.motifs.mockResolvedValue([
      { id: 'm1', name: '铜炉', tier: 'volume', scope: '卷1' },
      { id: 'm2', name: '纸命', tier: 'book' },
    ])
    render(<DetailPane sel={{ mode: 'node', node: { id: 'motif:volume', type: 'motif_view', label: '本卷主母题', ref: 'volume' } }} work="demo" onSelectNode={() => {}} />)
    expect(await screen.findByText('铜炉')).toBeTruthy()
    expect(screen.queryByText('纸命')).toBeNull()
  })

  it('motif_view 单条展示时间线历史', async () => {
    apiMock.motifTimeline.mockResolvedValue([
      { chapter: 2, evidence: '炉火初燃' },
      { chapter: 5, evidence: '炉火再起' },
    ])
    render(<DetailPane sel={{ mode: 'node', node: { id: 'motif:m1', type: 'motif_view', label: '铜炉', ref: 'm1' } }} work="demo" onSelectNode={() => {}} />)
    expect(await screen.findByTestId('motif-timeline')).toBeTruthy()
    expect(screen.getByText(/炉火初燃/)).toBeTruthy()
    expect(apiMock.motifTimeline).toHaveBeenCalled()
  })
})
