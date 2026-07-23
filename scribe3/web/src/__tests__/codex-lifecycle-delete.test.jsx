import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CodexDetail, PropositionDetail } from '../CodexDetail'

const apiMock = vi.hoisted(() => ({
  getChar: vi.fn(),
  getFact: vi.fn(),
  get: vi.fn(),
  entities: vi.fn(),
  facts: vi.fn(),
  objectImpact: vi.fn(),
  deleteObject: vi.fn(),
  archiveObject: vi.fn(),
  editChar: vi.fn(),
  editPromise: vi.fn(),
  charAnchors: vi.fn(),
  charStates: vi.fn(),
  voiceFlags: vi.fn(),
}))

const seedMocks = vi.hoisted(() => ({
  seedChiefDeleteCodex: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../lib/chiefSeed.js', async () => {
  const actual = await vi.importActual('../lib/chiefSeed.js')
  return { ...actual, seedChiefDeleteCodex: seedMocks.seedChiefDeleteCodex }
})
vi.mock('../views/CodexView', async () => {
  const actual = await vi.importActual('../views/CodexView')
  return {
    ...actual,
    DetailView: ({ row, onDelete }) => (
      <div>
        <div>{row.name || row.attribute}</div>
        <button type="button" onClick={onDelete}>触发删除</button>
      </div>
    ),
  }
})
vi.mock('../ui/Toast', () => ({
  showToast: vi.fn(),
  useToast: () => vi.fn(),
}))

describe('Codex lifecycle delete', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.getChar.mockResolvedValue({ id: 'role:小翠', kind: 'character', name: '小翠' })
    apiMock.getFact.mockResolvedValue({ id: 'fact:秘密', entity: 'role:甲', attribute: '秘密', value: '井底有骨', is_secret: false })
    // 删批轮询默认仍存在(未归档);各测再改为 archived/404
    apiMock.get.mockResolvedValue({ name: 'still-there', archived: false })
    apiMock.charAnchors.mockResolvedValue({ anchors: {}, arc_plan: [] })
    apiMock.charStates.mockResolvedValue([])
    apiMock.voiceFlags.mockResolvedValue([])
    apiMock.deleteObject.mockResolvedValue({ deleted: true })
    apiMock.archiveObject.mockResolvedValue({ ok: true })
  })

  it('角色删除前展示影响范围,建议归档时默认交给主编归档', async () => {
    const onDeleted = vi.fn()
    apiMock.objectImpact.mockResolvedValue({
      object: { type: 'role', id: '小翠', label: '小翠' },
      references: [{ kind: 'knowledge_edge', count: 1 }],
      recommended_action: 'archive',
      confirm_impact_token: 'role-token',
    })

    render(<CodexDetail node={{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }} onDeleted={onDeleted} />)

    expect(await screen.findByText('小翠')).toBeTruthy()
    expect(apiMock.getChar).toHaveBeenCalledWith('小翠')
    fireEvent.click(screen.getByRole('button', { name: '触发删除' }))

    expect(await screen.findByText(/影响范围/)).toBeTruthy()
    expect(screen.getByText(/knowledge_edge: 1/)).toBeTruthy()

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /交给主编归档|归档/ }))

    await waitFor(() => expect(seedMocks.seedChiefDeleteCodex).toHaveBeenCalledWith(
      'role',
      '小翠',
      expect.objectContaining({ archive: true }),
    ))
    expect(apiMock.archiveObject).not.toHaveBeenCalled()
    expect(apiMock.deleteObject).not.toHaveBeenCalled()
    // 种子当下不退回;对象仍显示
    expect(onDeleted).not.toHaveBeenCalled()
    expect(screen.getByText('小翠')).toBeTruthy()

    // 模拟批准后归档:GET 回 archived → 退回分类
    apiMock.get.mockResolvedValue({ name: '小翠', archived: true })
    await waitFor(() => expect(onDeleted).toHaveBeenCalled(), { timeout: 5000 })
  })

  it('命题删除前展示影响范围,建议归档时交给主编', async () => {
    const onDeleted = vi.fn()
    apiMock.objectImpact.mockResolvedValue({
      object: { type: 'fact', id: '秘密', label: '秘密' },
      references: [{ kind: 'knowledge_edge', count: 2 }],
      recommended_action: 'archive',
      confirm_impact_token: 'fact-token',
    })

    render(<PropositionDetail node={{ id: 'proposition:秘密', type: 'proposition', ref: '秘密', label: '秘密' }} onDeleted={onDeleted} />)

    expect(await screen.findByText('命题详情')).toBeTruthy()
    expect(apiMock.getFact).toHaveBeenCalledWith('秘密')
    fireEvent.click(screen.getByRole('button', { name: /删除命题/ }))

    expect(await screen.findByText(/影响范围/)).toBeTruthy()
    expect(screen.getByText(/knowledge_edge: 2/)).toBeTruthy()

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /归档|交给主编/ }))

    await waitFor(() => expect(seedMocks.seedChiefDeleteCodex).toHaveBeenCalledWith(
      'fact',
      '秘密',
      expect.objectContaining({ archive: true }),
    ))
    expect(apiMock.archiveObject).not.toHaveBeenCalled()
    expect(onDeleted).not.toHaveBeenCalled()
    expect(screen.getByText('命题详情')).toBeTruthy()

    apiMock.get.mockResolvedValue({ id: 'fact:秘密', archived: true })
    await waitFor(() => expect(onDeleted).toHaveBeenCalled(), { timeout: 5000 })
  })
})

describe('CodexDetail 禁止字段 REST 双写', () => {
  const charNode = { id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }

  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.getChar.mockResolvedValue({ id: 'role:小翠', kind: 'character', name: '小翠' })
    apiMock.charAnchors.mockResolvedValue({ anchors: {}, arc_plan: [] })
    apiMock.charStates.mockResolvedValue([])
    apiMock.voiceFlags.mockResolvedValue([])
  })

  it('加载已有角色后不渲染保存状态机,也不调用 editChar', async () => {
    render(<CodexDetail node={charNode} />)
    expect(await screen.findByText('小翠')).toBeTruthy()
    expect(screen.queryByText('已保存')).toBeNull()
    expect(screen.queryByText('保存中…')).toBeNull()
    expect(screen.queryByRole('button', { name: '重试保存' })).toBeNull()
    expect(apiMock.editChar).not.toHaveBeenCalled()
  })
})
