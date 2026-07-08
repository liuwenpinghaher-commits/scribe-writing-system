import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CodexDetail, PropositionDetail } from '../CodexDetail'

const apiMock = vi.hoisted(() => ({
  entities: vi.fn(),
  facts: vi.fn(),
  objectImpact: vi.fn(),
  deleteObject: vi.fn(),
  archiveObject: vi.fn(),
  charAnchors: vi.fn(),
  charStates: vi.fn(),
  voiceFlags: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../views/CodexView', () => ({
  stripSecretMask: (row) => row,
  DetailView: ({ row, onDelete }) => (
    <div>
      <div>{row.name || row.attribute}</div>
      <button onClick={onDelete}>触发删除</button>
    </div>
  ),
}))

describe('Codex lifecycle delete', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.facts.mockResolvedValue([{ id: 'fact:秘密', entity: 'role:甲', attribute: '秘密', value: '井底有骨', is_secret: false }])
    apiMock.charAnchors.mockResolvedValue({ anchors: {}, arc_plan: [] })
    apiMock.charStates.mockResolvedValue([])
    apiMock.voiceFlags.mockResolvedValue([])
    apiMock.deleteObject.mockResolvedValue({ deleted: true })
    apiMock.archiveObject.mockResolvedValue({ ok: true })
  })

  it('角色删除前展示影响范围,建议归档时默认归档', async () => {
    const onDeleted = vi.fn()
    apiMock.objectImpact.mockResolvedValue({
      object: { type: 'role', id: '小翠', label: '小翠' },
      references: [{ kind: 'knowledge_edge', count: 1 }],
      recommended_action: 'archive',
      confirm_impact_token: 'role-token',
    })

    render(<CodexDetail node={{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }} onDeleted={onDeleted} />)

    expect(await screen.findByText('小翠')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '触发删除' }))

    expect(await screen.findByText(/影响范围/)).toBeTruthy()
    expect(screen.getByText(/knowledge_edge: 1/)).toBeTruthy()

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '归档' }))

    await waitFor(() => expect(apiMock.archiveObject).toHaveBeenCalledWith('role', '小翠'))
    expect(apiMock.deleteObject).not.toHaveBeenCalled()
    expect(onDeleted).toHaveBeenCalled()
  })

  it('命题删除前展示影响范围,建议归档时默认归档', async () => {
    const onDeleted = vi.fn()
    apiMock.objectImpact.mockResolvedValue({
      object: { type: 'fact', id: '秘密', label: '秘密' },
      references: [{ kind: 'knowledge_edge', count: 2 }],
      recommended_action: 'archive',
      confirm_impact_token: 'fact-token',
    })

    render(<PropositionDetail node={{ id: 'proposition:秘密', type: 'proposition', ref: '秘密', label: '秘密' }} onDeleted={onDeleted} />)

    expect(await screen.findByText('命题详情')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /删除命题/ }))

    expect(await screen.findByText(/影响范围/)).toBeTruthy()
    expect(screen.getByText(/knowledge_edge: 2/)).toBeTruthy()

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '归档' }))

    await waitFor(() => expect(apiMock.archiveObject).toHaveBeenCalledWith('fact', '秘密'))
    expect(apiMock.deleteObject).not.toHaveBeenCalled()
    expect(onDeleted).toHaveBeenCalled()
  })
})
