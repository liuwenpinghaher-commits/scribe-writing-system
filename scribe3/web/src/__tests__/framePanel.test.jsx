import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { FramePanel } from '../FramePanel'
import { SelectionProvider, useSelection } from '../selectionContext'

const apiMock = vi.hoisted(() => ({
  frame: vi.fn(),
  irony: vi.fn(),
  intent: vi.fn(),
  materialRefsByChapter: vi.fn(),
  facts: vi.fn(),
  characterRelations: vi.fn(),
  motifInstances: vi.fn(),
  promisesLedger: vi.fn(),
  issues: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

function FocusProbe() {
  const { focus } = useSelection()
  return <output data-testid="focus-label">{focus?.label || ''}</output>
}

function renderFrame(props = {}) {
  const onSelectNode = props.onSelectNode || vi.fn()
  return {
    onSelectNode,
    ...render(
      <SelectionProvider>
        <FramePanel
          work="demo"
          focalizer="role:小翠"
          chapter={3}
          focalizerOptions={[
            { id: 'role:小翠', name: '小翠' },
            { id: 'role:柳怀玉', name: '柳怀玉' },
          ]}
          onSelectNode={onSelectNode}
          {...props}
        />
        <FocusProbe />
      </SelectionProvider>,
    ),
  }
}

describe('FramePanel 关联 tab（单列精简）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.frame.mockResolvedValue([
      { id: 'f1', entity: '柳怀玉', attribute: '知道', value: '借命契存在', chapter: 1 },
      { id: 'f2', entity: '柳怀玉', attribute: '秘密', value: null, chapter: 2 },
    ])
    apiMock.irony.mockResolvedValue([
      { id: 'i1', entity: '读者', attribute: '真相', value: '续命者为空', chapter: 1 },
    ])
    apiMock.intent.mockResolvedValue({})
    apiMock.materialRefsByChapter.mockResolvedValue([
      { material_id: 'm1', title: '铜炉制度', kind: 'worldbuilding', phase: 'outline' },
    ])
    apiMock.facts.mockResolvedValue([
      { id: 'p1', entity: 'role:柳怀玉', attribute: '身份', value: '纸扎匠', chapter: 3 },
    ])
    apiMock.characterRelations.mockResolvedValue([])
    apiMock.motifInstances.mockResolvedValue([{ id: 'motif:命纸:3', motif_id: '命纸', title: '命与纸', chapter: 3 }])
    apiMock.promisesLedger.mockResolvedValue({ open: [], closed: [], red_herring: [] })
    apiMock.issues.mockResolvedValue({ issues: [] })
  })

  it('默认单列 master–detail：无 min-w 三列宽板、无向右延展、有双域分区', async () => {
    renderFrame()
    await waitFor(() => expect(screen.getByTestId('frame-assoc-board')).toBeTruthy())
    const board = screen.getByTestId('frame-assoc-board')
    expect(board.innerHTML).not.toMatch(/min-w-\[720px\]/)
    expect(screen.queryByRole('button', { name: '向右延展' })).toBeNull()
    expect(screen.queryByRole('button', { name: '向下压缩' })).toBeNull()
    expect(screen.getByTestId('frame-domain-assoc')).toBeTruthy()
    expect(screen.getByTestId('frame-domain-frame')).toBeTruthy()
    // 默认打开本章设定（关联域），不是可写事实
    expect(screen.getByRole('button', { name: /本章设定/ }).getAttribute('aria-expanded')).toBe('true')
    // 无 elevated 装饰墙
    expect(board.innerHTML).not.toContain('panel-elevated')
    // summary 无重复「风险」格
    const chips = screen.getByTestId('frame-summary-chips').textContent
    expect(chips).toMatch(/设定/)
    expect(chips).toMatch(/禁写/)
    expect(chips).not.toMatch(/风险/)
  })

  it('限知条目点选展示精简详情,不含分类含义/写作约束/当前范围套话', async () => {
    renderFrame()
    await waitFor(() => expect(screen.getByRole('button', { name: /禁止泄露/ })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /禁止泄露/ }))
    fireEvent.click(await screen.findByText(/柳怀玉 · 秘密/))
    const detail = await screen.findByTestId('frame-detail')
    expect(detail.textContent).toMatch(/私密|未知/)
    expect(detail.textContent).not.toMatch(/分类含义/)
    expect(detail.textContent).not.toMatch(/写作约束/)
    expect(detail.textContent).not.toMatch(/当前范围/)
    expect(screen.getByTestId('focus-label').textContent).toContain('柳怀玉·秘密')
  })

  it('章级设定/素材点击调用 onSelectNode', async () => {
    const onSelectNode = vi.fn()
    renderFrame({ onSelectNode })
    await waitFor(() => expect(screen.getByRole('button', { name: /本章素材/ })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /本章素材/ }))
    fireEvent.click(await screen.findByText(/铜炉制度/))
    expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({
      id: 'material:m1',
      type: 'material',
      ref: 'm1',
      label: '铜炉制度',
    }))
    fireEvent.click(screen.getByRole('button', { name: /本章设定/ }))
    fireEvent.click(await screen.findByText(/柳怀玉 · 身份/))
    expect(onSelectNode).toHaveBeenCalledWith(expect.objectContaining({
      type: 'character',
      ref: '柳怀玉',
    }))
  })

  it('切换视角时重拉限知帧', async () => {
    apiMock.frame.mockImplementation((focalizer) => Promise.resolve(
      focalizer === 'role:柳怀玉'
        ? [{ id: 'f3', entity: '柳怀玉', attribute: '确信', value: '自己安全', chapter: 3 }]
        : [{ id: 'f1', entity: '小翠', attribute: '知道', value: '借命契存在', chapter: 1 }],
    ))
    apiMock.irony.mockResolvedValue([])
    renderFrame()
    await waitFor(() => expect(apiMock.frame).toHaveBeenCalledWith('role:小翠', 3))
    fireEvent.change(screen.getByLabelText('限知视角'), { target: { value: 'role:柳怀玉' } })
    await waitFor(() => expect(apiMock.frame).toHaveBeenLastCalledWith('role:柳怀玉', 3))
    fireEvent.click(screen.getByRole('button', { name: /可写事实/ }))
    expect(await screen.findByText(/自己安全/)).toBeTruthy()
  })

  it('无误判盲区一级入口', async () => {
    renderFrame()
    await waitFor(() => expect(screen.getByTestId('frame-domain-assoc')).toBeTruthy())
    expect(screen.queryByRole('button', { name: /误判盲区/ })).toBeNull()
  })
})
