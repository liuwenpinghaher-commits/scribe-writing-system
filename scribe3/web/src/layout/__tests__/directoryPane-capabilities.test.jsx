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
    canonDebt: vi.fn(() => Promise.resolve({ total: 3, noise_count: 1 })),
    listCanonCandidates: vi.fn(() => Promise.resolve({ items: [] })),
    promisesLedger: vi.fn(() => Promise.resolve({
      open: [
        { id: 'p-pay', text: '本章要收的伏笔', setup_chapter: 1, payoff_chapter: 23, overdue: false },
        { id: 'p-open', text: '仍悬伏笔', setup_chapter: 2, payoff_chapter: 30, overdue: true },
      ],
      closed: [],
      red_herring: [],
      abandoned: [],
    })),
    motifs: vi.fn(() => Promise.resolve([
      { id: 'm1', name: '铜腥', theme: '味', unfolding: '升' },
    ])),
    motifInstances: vi.fn(() => Promise.resolve([{ motif_id: 'm1', evidence: '铜腥起' }])),
    motifSchedule: vi.fn(() => Promise.resolve({ rows: [] })),
    getWork: vi.fn(() => 'book_test'),
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
    ['review', '校验', '本章总览', 'review_issue'],
  ])('%s 渲染二级目录并传出详情节点', (capability, label, rowLabel, type) => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry(capability, label)} seq={23} onSelectItem={onSelectItem} />)

    expect(screen.getByTestId('directory-sticky-header').textContent).toContain(label)
    fireEvent.click(screen.getByRole('button', { name: new RegExp(rowLabel) }))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({ type }))
  })

  it('伏笔目录列出真实条目，点击产出 promise 叶节点（详情栏 CodexDetail）', async () => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry('promise', '伏笔')} seq={23} onSelectItem={onSelectItem} />)
    expect(screen.getByTestId('directory-sticky-header').textContent).toContain('伏笔')
    const item = await screen.findByRole('button', { name: /本章要收的伏笔/ })
    fireEvent.click(item)
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      type: 'promise',
      ref: 'p-pay',
      capability: 'promise',
    }))
  })

  it('母题目录列出本章触及条目，点击产出 motif 叶节点', async () => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry('motif', '母题')} seq={23} onSelectItem={onSelectItem} />)
    const item = await screen.findByRole('button', { name: /铜腥/ })
    fireEvent.click(item)
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      type: 'motif',
      ref: 'm1',
      capability: 'motif',
    }))
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

  it('设定库根目录展示收件箱目录入口（不堆 pending 列表），分类/搜索/新建仍可用', async () => {
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
    const { rerender } = render(<DirectoryPane entry={codexEntry} sel={{ mode: 'node', node: null }} onSelectItem={onSelectItem} />)

    expect(screen.getByTestId('codex-directory')).toBeTruthy()
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('设定库')
    // 目录入口，非长列表
    expect(await screen.findByTestId('codex-inbox-dir-row')).toBeTruthy()
    expect(screen.getByRole('button', { name: '设定收件箱' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '设定收件箱' }))
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({ type: 'view', id: 'view:canon-inbox' }))

    fireEvent.click(screen.getByRole('button', { name: '角色' }))
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({ type: 'codex_category', ref: 'character' }))

    rerender(<DirectoryPane entry={codexEntry} sel={{ mode: 'node', node: characterCat }} onSelectItem={onSelectItem} />)
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('角色')
    expect(screen.getByPlaceholderText('搜设定、别名、标签')).toBeTruthy()
    // 分类内仍有收件箱入口，不再展示「待确认人物引用」长列表
    expect(screen.getByRole('button', { name: '设定收件箱' })).toBeTruthy()
    expect(screen.queryByText('待确认人物引用')).toBeNull()
    expect(screen.queryByText('神秘人')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '新建设定' }))
    expect(onSelectItem).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'codex_new', ref: 'character' }))
    fireEvent.click(screen.getByRole('button', { name: '小翠' }))
    expect(onSelectItem).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'character', ref: '小翠' }))

    rerender(<DirectoryPane entry={codexEntry} sel={{ mode: 'node', node: characterCat.children[0] }} onSelectItem={onSelectItem} />)
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('角色')
    expect(screen.getByRole('button', { name: '崔判' })).toBeTruthy()
    fireEvent.change(screen.getByPlaceholderText('搜设定、别名、标签'), { target: { value: '崔' } })
    expect(screen.queryByRole('button', { name: '小翠' })).toBeNull()
    expect(screen.getByRole('button', { name: '崔判' })).toBeTruthy()

    rerender(<DirectoryPane entry={codexEntry} sel={{ mode: 'node', node: { id: 'new:character', type: 'codex_new', ref: 'character', label: '角色' } }} onSelectItem={onSelectItem} />)
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('角色')
  })

  it('设定收件箱目录入口可打开工作台视图', async () => {
    const onSelectItem = vi.fn()
    const characterCat = {
      id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色', children: [],
    }
    const codexEntry = {
      id: 'entry:codex', type: 'entry_capability', capability: 'codex', label: '设定库',
      source: { id: 'codex_root', type: 'codex_root', label: '设定库', children: [characterCat] },
    }
    render(<DirectoryPane entry={codexEntry} sel={{ mode: 'node', node: null }} onSelectItem={onSelectItem} />)
    fireEvent.click(await screen.findByRole('button', { name: '设定收件箱' }))
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      type: 'view', id: 'view:canon-inbox',
    }))
  })

  it.skip('接受待确认人物回放期间禁用该条操作（已迁至设定收件箱工作台）', async () => {
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

  it.skip('接受后明确告知章节关联正在后台回填（已迁至设定收件箱工作台）', async () => {
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
  it('不把配置里的 demo 计数当 live 数据渲染', async () => {
    render(<CapabilityDirectory capability="promise" seq={3} onSelectItem={() => {}} />)
    await screen.findByTestId('capability-dir-promise')
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
