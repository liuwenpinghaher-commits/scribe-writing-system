import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DirectoryPane } from '../DirectoryPane'

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
  useToast: () => vi.fn(),
}))

function entry(capability, label) {
  return { id: `entry:${capability}`, type: 'entry_capability', capability, label }
}

describe('DirectoryPane 能力二级目录', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it.each([
    ['deduce', '演绎', '场景真相', 'deduce_view'],
    ['promise', '伏笔', '本章要收', 'promise_view'],
    ['motif', '母题', '本章触及', 'motif_view'],
    ['search', '搜索', '语义召回', 'recall_result'],
    ['review', '校验', '本章总览', 'review_issue'],
  ])('%s 渲染二级目录并传出详情节点', (capability, label, rowLabel, type) => {
    const onSelectItem = vi.fn()
    render(<DirectoryPane entry={entry(capability, label)} seq={23} onSelectItem={onSelectItem} />)

    expect(screen.getByTestId('directory-sticky-header').textContent).toContain(label)
    fireEvent.click(screen.getByRole('button', { name: new RegExp(rowLabel) }))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({ type }))
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
})
