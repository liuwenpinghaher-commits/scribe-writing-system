import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DirectoryPane } from '../DirectoryPane'
import { CapabilityDirectory } from '../CapabilityDirectories'
import { CapabilityGroupDetailPane } from '../CapabilityDetailPanes'

const { toastSpy } = vi.hoisted(() => ({ toastSpy: vi.fn() }))

// CapabilityDetailPanes 顶层 import DeduceStage(拖 TipTap 编辑器链);
// 本文件只测 group 详情面板,掐断这条重依赖。
vi.mock('../../DeduceStage', () => ({ DeduceStage: () => null }))
vi.mock('../../ContainerOutline', () => ({
  ContainerOutline: ({ node, onSelect }) => (
    <div data-testid="container-outline">
      <div data-testid="container-outline-label">{node?.label}</div>
      {(node?.children || []).map((child) => (
        <button key={child.id} type="button" onClick={() => onSelect?.(child)}>
          {child.label}
        </button>
      ))}
    </div>
  ),
}))
vi.mock('../../Materials', () => ({
  MaterialList: () => <div data-testid="material-list" />,
}))
vi.mock('../../api', () => ({
  api: {
    issues: vi.fn(() => Promise.resolve({ issues: [], degraded_sources: [] })),
    listUnverified: vi.fn(() => Promise.resolve([
      { id: 'uv:1', name: '神秘人', seq: 1, role: 'did_who' },
    ])),
    acceptUnverified: vi.fn(() => Promise.resolve({ ok: true })),
    ignoreUnverified: vi.fn(() => Promise.resolve({ ok: true })),
    ignoreAllUnverified: vi.fn(() => Promise.resolve({ ignored: 1 })),
  },
}))
vi.mock('../../ui/Toast', () => ({
  useToast: () => toastSpy,
}))

function entry(capability, label) {
  return { id: `entry:${capability}`, type: 'entry_capability', capability, label }
}

describe('DirectoryPane 能力二级目录', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    toastSpy.mockClear()
  })

  it.each([
    ['deduce', '演绎', '场景真相', 'deduce_view'],
    ['promise', '伏笔', '本章要收', 'promise_view'],
    ['motif', '母题', '本章触及', 'motif_view'],
    ['review', '校验', '本章总览', 'review_issue'],
  ])('%s 渲染二级目录并传出详情节点', (capability, label, rowLabel, type) => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry(capability, label)} seq={23} onSelectItem={onSelectItem} />)

    expect(screen.getByTestId('directory-sticky-header').textContent).toContain(label)
    fireEvent.click(screen.getByRole('button', { name: new RegExp(rowLabel) }))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({ type }))
  })

  it('搜索目录只提供真实搜索框,不挂无 payload 的语义召回占位', () => {
    render(<DirectoryPane entry={entry('search', '搜索')} seq={23} onSelectItem={vi.fn()} />)
    expect(screen.getByTestId('directory-sticky-header').textContent).toContain('搜索')
    expect(screen.getByRole('searchbox', { name: /全局/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: '语义召回' })).toBeNull()
  })

  it('演绎二栏按上下文树先选分类总览,再选具体项', () => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry('deduce', '演绎')} seq={23} onSelectItem={onSelectItem} />)

    fireEvent.click(screen.getByRole('button', { name: '限知分类' }))
    expect(onSelectItem).toHaveBeenLastCalledWith(expect.objectContaining({
      id: 'deduce:limited',
      type: 'capability_group',
      capability: 'deduce',
      label: '限知分类',
      ref: expect.objectContaining({ group: 'limited', seq: 23 }),
    }))

    fireEvent.click(screen.getByRole('button', { name: /角色限知/ }))
    expect(onSelectItem).toHaveBeenLastCalledWith(expect.objectContaining({
      id: 'deduce:roles',
      type: 'deduce_view',
      ref: expect.objectContaining({ view: 'roles', group: 'limited', seq: 23 }),
    }))
  })

  it('设定库按 demo 风格保留分类、搜索、新建、待确认引用和原有设定叶子', async () => {
    const onSelectItem = vi.fn()
    const characterCat = {
      id: 'cat:character',
      type: 'codex_category',
      ref: 'character',
      label: '角色',
      children: [
        { id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' },
        { id: 'character:崔判', type: 'character', ref: '崔判', label: '崔判' },
      ],
    }
    const codexEntry = {
      id: 'entry:codex',
      type: 'entry_capability',
      capability: 'codex',
      label: '设定库',
      source: {
        id: 'codex_root',
        type: 'codex_root',
        label: '设定库',
        children: [characterCat],
      },
    }
    const { rerender } = render(<DirectoryPane entry={codexEntry} sel={{ node: null }} onSelectItem={onSelectItem} />)

    expect(screen.getByTestId('codex-directory')).toBeTruthy()
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('设定库')
    fireEvent.click(screen.getByRole('button', { name: '角色' }))
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({ type: 'codex_category', ref: 'character' }))

    rerender(<DirectoryPane entry={codexEntry} sel={{ node: characterCat }} onSelectItem={onSelectItem} />)
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('角色')
    expect(screen.getByPlaceholderText('搜设定、别名、标签')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '新建设定' }))
    expect(onSelectItem).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'codex_new', ref: 'character' }))
    expect(await screen.findByText('待确认人物引用')).toBeTruthy()
    expect(screen.getByText('神秘人')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '小翠' }))
    expect(onSelectItem).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'character', ref: '小翠' }))

    rerender(<DirectoryPane entry={codexEntry} sel={{ node: characterCat.children[0] }} onSelectItem={onSelectItem} />)
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('角色')
    expect(screen.getByRole('button', { name: '崔判' })).toBeTruthy()
    fireEvent.change(screen.getByPlaceholderText('搜设定、别名、标签'), { target: { value: '崔' } })
    expect(screen.queryByRole('button', { name: '小翠' })).toBeNull()
    expect(screen.getByRole('button', { name: '崔判' })).toBeTruthy()

    rerender(<DirectoryPane entry={codexEntry} sel={{ node: { id: 'new:character', type: 'codex_new', ref: 'character', label: '角色' } }} onSelectItem={onSelectItem} />)
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('角色')

    fireEvent.click(screen.getByRole('button', { name: '接受为角色' }))
    await waitFor(async () => {
      const { api } = await import('../../api')
      expect(api.acceptUnverified).toHaveBeenCalledWith('uv:1')
    })
  })

  it('接受待确认人物回放期间禁用该条操作，防止重复提交', async () => {
    const { api } = await import('../../api')
    let finishAccept
    api.acceptUnverified.mockImplementationOnce(() => new Promise((resolve) => { finishAccept = resolve }))
    const characterCat = {
      id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色', children: [],
    }
    const codexEntry = {
      id: 'entry:codex', type: 'entry_capability', capability: 'codex', label: '设定库',
      source: { id: 'codex_root', type: 'codex_root', label: '设定库', children: [characterCat] },
    }
    render(<DirectoryPane entry={codexEntry} sel={{ node: characterCat }} onSelectItem={() => {}} />)

    const accept = await screen.findByRole('button', { name: '接受为角色' })
    fireEvent.click(accept)
    fireEvent.click(accept)

    expect(api.acceptUnverified).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: '接受中' }).disabled).toBe(true)

    finishAccept({ ok: true })
    await waitFor(() => expect(screen.queryByText('神秘人')).toBeNull())
  })

  it('接受后明确告知章节关联正在后台回填', async () => {
    const { api } = await import('../../api')
    api.acceptUnverified.mockResolvedValueOnce({ ok: true, replay_queued: true })
    const characterCat = {
      id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色', children: [],
    }
    const codexEntry = {
      id: 'entry:codex', type: 'entry_capability', capability: 'codex', label: '设定库',
      source: { id: 'codex_root', type: 'codex_root', label: '设定库', children: [characterCat] },
    }
    render(<DirectoryPane entry={codexEntry} sel={{ node: characterCat }} onSelectItem={() => {}} />)

    fireEvent.click(await screen.findByRole('button', { name: '接受为角色' }))

    await waitFor(() => expect(toastSpy).toHaveBeenCalledWith('已接受「神秘人」为角色，正在后台回填第1章关联'))
  })
})

// Task 10:工艺目录/分类详情只展示真实状态 —— 配置里的 demo 计数与无 handler 的
// 动作按钮不得进入 UI;数量与动作一律等 live payload,值不存在就不渲染。
describe('CapabilityDirectory / CapabilityGroupDetailPane 无假数据', () => {
  it('不把配置里的 demo 计数当 live 数据渲染', () => {
    render(<CapabilityDirectory capability="promise" seq={3} onSelectItem={() => {}} />)
    // 旧配置写死的超期 4 / 仍悬 7 / 已回收 19,一个都不许出现
    expect(screen.queryByText('4')).toBeNull()
    expect(screen.queryByText('7')).toBeNull()
    expect(screen.queryByText('19')).toBeNull()
  })

  it('不渲染没有 handler 的动作按钮', () => {
    // 未知 group(落兜底文案)不得长出写死的三颗动作按钮
    const first = render(<CapabilityGroupDetailPane node={{ capability: 'promise', ref: { group: 'open' }, label: '待回收' }} />)
    expect(screen.queryByRole('button', { name: '查看全部命中正文' })).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
    first.unmount()

    // 真实 group 的配置 actions 同样是无 handler 的假动作,不得渲染
    render(<CapabilityGroupDetailPane node={{ capability: 'promise', ref: { group: 'risk' }, label: '风险状态' }} />)
    expect(screen.queryByRole('button', { name: '查看风险伏笔' })).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('payload 提供带 handler 的动作/关联/数量时才渲染', () => {
    const onAct = vi.fn()
    render(<CapabilityGroupDetailPane node={{
      capability: 'promise',
      ref: { group: 'risk', seq: 3 },
      label: '风险状态',
      payload: { count: 5, related: [['超期未收', 'overdue']], actions: [{ label: '查看风险伏笔', onClick: onAct }] },
    }} />)
    expect(screen.getByText(/5项/)).toBeTruthy()
    expect(screen.getByText('超期未收')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '查看风险伏笔' }))
    expect(onAct).toHaveBeenCalledTimes(1)
  })
})
