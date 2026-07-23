import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CodexDetail, PropositionDetail } from '../CodexDetail'

const apiMock = vi.hoisted(() => ({
  getChar: vi.fn(),
  getFact: vi.fn(),
  getFaction: vi.fn(),
  getItem: vi.fn(),
  getTerm: vi.fn(),
  getWorldRule: vi.fn(),
  getPromise: vi.fn(),
  getMotif: vi.fn(),
  objectImpact: vi.fn(),
  charAnchors: vi.fn(),
  charStates: vi.fn(),
  voiceFlags: vi.fn(),
  entities: vi.fn(),
  archiveObject: vi.fn(),
  deleteObject: vi.fn(),
  get: vi.fn().mockResolvedValue([]),
  characterRelations: vi.fn().mockResolvedValue([]),
  entityRelations: vi.fn().mockResolvedValue([]),
}))
// note: api.get 亦用于删批后 isCodexObjectGone 轮询

const seedMocks = vi.hoisted(() => ({
  seedChiefDeleteCodex: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../lib/chiefSeed.js', async () => {
  const actual = await vi.importActual('../lib/chiefSeed.js')
  return { ...actual, seedChiefDeleteCodex: seedMocks.seedChiefDeleteCodex }
})
vi.mock('../views/CodexView', async () => ({
  DetailView: ({ row, onDelete }) => (
    <div data-testid="detail-view">
      <div>{row?.name || row?.attribute}</div>
      <button type="button" onClick={onDelete}>触发删除</button>
    </div>
  ),
  seedChiefCodexWrite: vi.fn(),
  SECRET_MASK: '🔒 私密',
  stripSecretMask: (o) => o,
}))
vi.mock('../ui/Toast', () => ({
  showToast: vi.fn(),
  useToast: () => vi.fn(),
}))

describe('CodexDetail 单条加载 + 主编删除', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.getChar.mockResolvedValue({
      id: 'role:小翠', kind: 'character', name: '小翠', appearance: '青衫',
    })
    apiMock.get.mockResolvedValue({ name: 'still-there', archived: false })
    apiMock.charAnchors.mockResolvedValue({ anchors: {}, arc_plan: [] })
    apiMock.charStates.mockResolvedValue([])
    apiMock.voiceFlags.mockResolvedValue([])
    apiMock.objectImpact.mockResolvedValue({
      recommended_action: 'archive',
      references: [{ kind: 'proposition', count: 1 }],
      confirm_impact_token: 'tok',
    })
  })

  it('按 id 单条加载角色,不调用 entities 全表', async () => {
    render(<CodexDetail node={{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }} />)
    expect(await screen.findByText('小翠')).toBeTruthy()
    expect(apiMock.getChar).toHaveBeenCalledWith('小翠')
    expect(apiMock.entities).not.toHaveBeenCalled()
  })

  it('删除走 s3_delete_codex 种子,不 REST archiveObject', async () => {
    const onDeleted = vi.fn()
    render(<CodexDetail
      node={{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }}
      onDeleted={onDeleted}
    />)
    expect(await screen.findByText('小翠')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '触发删除' }))
    expect(await screen.findByRole('dialog')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /交给主编归档|归档/ }))
    await waitFor(() => expect(seedMocks.seedChiefDeleteCodex).toHaveBeenCalledWith(
      'role',
      '小翠',
      expect.objectContaining({ archive: true }),
    ))
    expect(apiMock.archiveObject).not.toHaveBeenCalled()
    expect(apiMock.deleteObject).not.toHaveBeenCalled()
    // 种子后不立刻 onDeleted
    expect(onDeleted).not.toHaveBeenCalled()
    // 批准后归档探测 → onDeleted
    apiMock.get = apiMock.get || vi.fn()
    apiMock.get.mockResolvedValue({ name: '小翠', archived: true })
    await waitFor(() => expect(onDeleted).toHaveBeenCalled(), { timeout: 5000 })
  })

  it('在图谱中打开:写 session 焦点并导航 type=view atlas', async () => {
    sessionStorage.clear()
    const onNavigateToObject = vi.fn()
    render(
      <CodexDetail
        node={{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }}
        onNavigateToObject={onNavigateToObject}
      />,
    )
    const btn = await screen.findByTestId('codex-open-graph')
    fireEvent.click(btn)
    expect(sessionStorage.getItem('s3.atlas.focus')).toBe('role:小翠')
    expect(onNavigateToObject).toHaveBeenCalledWith(expect.objectContaining({
      type: 'view',
      id: 'view:atlas',
      viewKey: 'atlas',
      focus: 'role:小翠',
    }))
  })

  it('势力详情可在图谱中打开(faction: focus)', async () => {
    sessionStorage.clear()
    apiMock.getFaction.mockResolvedValue({ name: '秘会', ideology: '隐' })
    const onNavigateToObject = vi.fn()
    render(
      <CodexDetail
        node={{ id: 'faction:秘会', type: 'faction', ref: '秘会', label: '秘会' }}
        onNavigateToObject={onNavigateToObject}
      />,
    )
    expect(await screen.findByTestId('codex-detail')).toBeTruthy()
    fireEvent.click(await screen.findByTestId('codex-open-graph'))
    expect(sessionStorage.getItem('s3.atlas.focus')).toBe('faction:秘会')
    expect(onNavigateToObject).toHaveBeenCalledWith(expect.objectContaining({
      type: 'view', viewKey: 'atlas', focus: 'faction:秘会',
    }))
  })
})

describe('PropositionDetail 单条 getFact', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.getFact.mockResolvedValue({
      id: 'fact:p1', entity: 'role:甲', attribute: '状态', value: '清醒', is_secret: false,
    })
    apiMock.objectImpact.mockResolvedValue({ recommended_action: 'hard_delete_allowed', references: [] })
  })

  it('加载命题用 getFact 而非 facts 全表', async () => {
    render(<PropositionDetail node={{ id: 'proposition:p1', type: 'proposition', ref: 'p1', label: '甲·状态' }} />)
    expect(await screen.findByTestId('proposition-detail')).toBeTruthy()
    expect(apiMock.getFact).toHaveBeenCalledWith('p1')
  })

  it('在图谱中打开:写 fact: 焦点并导航 atlas', async () => {
    sessionStorage.clear()
    const onNavigateToObject = vi.fn()
    render(
      <PropositionDetail
        node={{ id: 'proposition:p1', type: 'proposition', ref: 'p1', label: '甲·状态' }}
        onNavigateToObject={onNavigateToObject}
      />,
    )
    const btn = await screen.findByTestId('codex-open-graph')
    fireEvent.click(btn)
    expect(sessionStorage.getItem('s3.atlas.focus')).toBe('fact:p1')
    expect(onNavigateToObject).toHaveBeenCalledWith(expect.objectContaining({
      type: 'view',
      viewKey: 'atlas',
      focus: 'fact:p1',
    }))
  })
})
