import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CodexDetail, PropositionDetail } from '../CodexDetail'

const apiMock = vi.hoisted(() => ({
  entities: vi.fn(),
  facts: vi.fn(),
  objectImpact: vi.fn(),
  deleteObject: vi.fn(),
  archiveObject: vi.fn(),
  editChar: vi.fn(),
  charAnchors: vi.fn(),
  charStates: vi.fn(),
  voiceFlags: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../views/CodexView', () => ({
  stripSecretMask: (row) => row,
  // onUpdate 触发字段保存(整行上抛,同真实 DetailView 的 {...row,[k]:v} 语义)
  DetailView: ({ row, onUpdate, onDelete }) => (
    <div>
      <div>{row.name || row.attribute}</div>
      <button onClick={() => onUpdate({ ...row, name: '改后名' })}>触发保存</button>
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
    apiMock.editChar.mockResolvedValue({ ok: true })
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

// #7:保存状态机(saving/saved/error + 重试重发 lastPayload)+ Issue 1(不被 spinner 吞)守护
describe('CodexDetail 字段保存状态机', () => {
  const charNode = { id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }

  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.entities.mockResolvedValue([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
    apiMock.charAnchors.mockResolvedValue({ anchors: {}, arc_plan: [] })
    apiMock.charStates.mockResolvedValue([])
    apiMock.voiceFlags.mockResolvedValue([])
  })

  it('保存成功显示「已保存」,且表单主体不被 loading spinner 吞(Issue 1)', async () => {
    apiMock.editChar.mockResolvedValue({ ok: true })
    // 首拉解析出表单;保存后的那次 reload 让 entities 悬挂——
    // 若保存后 reload 非静默(回归),loading 会一直 true → spinner 常驻、「已保存」永不出现,本测试即 FAIL。
    apiMock.entities
      .mockResolvedValueOnce([{ id: 'role:小翠', kind: 'character', name: '小翠' }])
      .mockReturnValue(new Promise(() => {}))
    render(<CodexDetail node={charNode} onChanged={vi.fn()} />)

    expect(await screen.findByText('小翠')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '触发保存' }))

    expect(await screen.findByText('已保存')).toBeTruthy()
    // 表单主体仍在、未被居中「加载中…」spinner 替换(保存后 reload 走静默路径)
    expect(screen.getByRole('button', { name: '触发保存' })).toBeTruthy()
    expect(screen.queryByText('加载中…')).toBeNull()
  })

  it('保存失败以 alert 呈现真实错误并给「重试保存」', async () => {
    apiMock.editChar.mockRejectedValue(new Error('save boom'))
    render(<CodexDetail node={charNode} onChanged={vi.fn()} />)

    expect(await screen.findByText('小翠')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '触发保存' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toMatch(/save boom/)
    expect(screen.getByRole('button', { name: '重试保存' })).toBeTruthy()
  })

  it('点「重试保存」用 lastPayloadRef 重发同一 payload', async () => {
    apiMock.editChar
      .mockRejectedValueOnce(new Error('save boom'))
      .mockResolvedValueOnce({ ok: true })
    render(<CodexDetail node={charNode} onChanged={vi.fn()} />)

    expect(await screen.findByText('小翠')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '触发保存' }))
    fireEvent.click(await screen.findByRole('button', { name: '重试保存' }))

    await waitFor(() => expect(apiMock.editChar).toHaveBeenCalledTimes(2))
    // 第二个实参是 payload(整行);重发须与首次完全一致
    expect(apiMock.editChar.mock.calls[1][1]).toEqual(apiMock.editChar.mock.calls[0][1])
    expect(await screen.findByText('已保存')).toBeTruthy()
  })
})
