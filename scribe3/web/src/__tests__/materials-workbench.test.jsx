import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MaterialDetail, MaterialList, MaterialNew } from '../Materials'
import { ChapterMaterialRefs } from '../ChapterStudio'

const apiMock = vi.hoisted(() => ({
  materials: vi.fn(),
  material: vi.fn(),
  materialsHealth: vi.fn(),
  materialRecall: vi.fn(),
  materialRefs: vi.fn(),
  objectImpact: vi.fn(),
  deleteObject: vi.fn(),
  archiveObject: vi.fn(),
  materialRefsByChapter: vi.fn(),
  addMaterialReference: vi.fn(),
  addMaterial: vi.fn(),
  editMaterial: vi.fn(),
  delMaterial: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

vi.mock('../MaterialImport', () => ({ MaterialImport: () => <div data-testid="material-import" /> }))
vi.mock('../MaterialNetwork', () => ({ MaterialNetwork: () => <div data-testid="material-network" /> }))
vi.mock('../editor/RichEditor', () => ({
  RichEditor: ({ value, ariaLabel }) => <textarea aria-label={ariaLabel} value={value || ''} readOnly />,
  useUnsavedGuard: vi.fn(),
}))
vi.mock('../ChiefSlotContext', () => ({
  useChiefSlot: () => ({ setStageProposal: vi.fn() }),
}))
vi.mock('../selectionContext', () => ({
  useSelection: () => ({
    focus: { type: 'chapter', id: 7, label: '第7章' },
    setFocus: vi.fn(),
  }),
}))
vi.mock('../lib/sessionClip.js', () => ({
  seedCiteMaterial: vi.fn(),
  seedDiscussMaterial: vi.fn(),
}))
vi.mock('../ui/Toast', () => ({
  useToast: () => vi.fn(),
}))

const rows = [
  {
    id: 1,
    title: '城墙外环与雾港边界',
    body: '旧城外环由三层废弃货线组成。',
    kind: 'research',
    tags: ['城市', '边界'],
    ref_tags: ['世界观'],
    summary: '边界感营造',
    source: '城市规划笔记.md',
    pinned: true,
    recall_count: 7,
    origin: 'manual',
  },
  {
    id: 2,
    title: '码头晨雾中的铜炉反光',
    body: '雾贴着船壳翻卷。',
    kind: 'snippet',
    tags: ['雾'],
    ref_tags: [],
    summary: '',
    source: '',
    pinned: false,
    recall_count: 0,
    origin: 'import',
  },
  {
    id: 3,
    title: '无标签待整理素材',
    body: '还没有整理。',
    kind: 'note',
    tags: [],
    ref_tags: [],
    summary: '',
    source: '',
    pinned: false,
    recall_count: 0,
    origin: 'session_clip',
  },
]

describe('MaterialList 素材库工作台', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.materials.mockImplementation((opts = {}) => {
      let list = rows
      if (opts.view === 'pinned') list = rows.filter((r) => r.pinned)
      if (opts.view === 'referenced') list = rows.filter((r) => r.recall_count > 0)
      if (opts.view === 'untagged') list = rows.filter((r) => !(r.tags?.length || r.ref_tags?.length))
      if (opts.view === 'archived') list = []
      if (opts.kind) list = list.filter((r) => r.kind === opts.kind)
      if (opts.origin) list = list.filter((r) => (r.origin || 'manual') === opts.origin)
      return Promise.resolve({ items: list, next_cursor: null, total: list.length })
    })
    apiMock.materialsHealth.mockResolvedValue({
      total: 3, never_recalled: 2, no_summary: 2, untagged: 1,
    })
    apiMock.materialRecall.mockResolvedValue({ items: [], degraded_sources: [] })
    apiMock.materialRefs.mockResolvedValue([])
    apiMock.material.mockResolvedValue(rows[0])
    apiMock.objectImpact.mockResolvedValue({
      object: { type: 'material', id: 1, label: '城墙外环与雾港边界' },
      references: [
        { kind: 'material_reference', count: 2 },
        { kind: 'graph', count: 1 },
      ],
      recommended_action: 'archive',
      confirm_impact_token: 'material-1-token',
    })
    apiMock.addMaterialReference.mockResolvedValue({ ok: true })
    apiMock.materialRefsByChapter.mockResolvedValue([])
    apiMock.addMaterial.mockResolvedValue({ ok: true, id: 9 })
    apiMock.editMaterial.mockResolvedValue({ ok: true })
    apiMock.delMaterial.mockResolvedValue({ ok: true })
  })

  it('用统一目录壳:sticky header + 搜索 + 动作(新建/导入/网络)', async () => {
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    expect(await screen.findByTestId('material-workbench')).toBeTruthy()
    const header = screen.getByTestId('directory-sticky-header')
    expect(within(header).getByText('素材库')).toBeTruthy()
    expect(within(header).getByLabelText('搜索素材')).toBeTruthy()
    expect(within(header).getByRole('button', { name: '新建' })).toBeTruthy()
    expect(within(header).getByRole('button', { name: '导入' })).toBeTruthy()
    expect(within(header).getByRole('button', { name: '网络' })).toBeTruthy()
    expect(screen.getByTestId('material-smart-views').className).toMatch(/flex/)
    expect(await screen.findByTestId('material-health')).toHaveTextContent(/健康度/)
  })

  it('智能视图请求服务端 view=pinned 并渲染核心记忆', async () => {
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    const smartViews = within(await screen.findByTestId('material-smart-views'))
    fireEvent.click(smartViews.getByRole('button', { name: /核心记忆/ }))

    await waitFor(() => expect(apiMock.materials).toHaveBeenCalledWith(
      expect.objectContaining({ view: 'pinned', limit: 200 }),
    ))
    expect(await screen.findByRole('button', { name: /城墙外环与雾港边界/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /码头晨雾中的铜炉反光/ })).toBeNull()
  })

  it('来源筛选请求服务端 origin=import 并只显示导入素材', async () => {
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    const origins = within(await screen.findByTestId('material-origin-filters'))
    expect(origins.getByRole('button', { name: /全部来源/ })).toBeTruthy()
    expect(origins.getByRole('button', { name: /手建/ })).toBeTruthy()
    expect(origins.getByRole('button', { name: /来自导入/ })).toBeTruthy()
    expect(origins.getByRole('button', { name: /剪藏/ })).toBeTruthy()
    expect(origins.getByRole('button', { name: /历史主编记录/ })).toBeTruthy()

    fireEvent.click(origins.getByRole('button', { name: /来自导入/ }))

    await waitFor(() => expect(apiMock.materials).toHaveBeenCalledWith(
      expect.objectContaining({ origin: 'import', limit: 200 }),
    ))
    expect(await screen.findByRole('button', { name: /码头晨雾中的铜炉反光/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /城墙外环与雾港边界/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /无标签待整理素材/ })).toBeNull()
  })

  it('导入和网络作为素材详情节点传出,不替换二栏目录', async () => {
    const onSelect = vi.fn()
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} onSelect={onSelect} />)

    await screen.findByTestId('material-workbench')
    fireEvent.click(within(screen.getByTestId('directory-header-actions')).getByRole('button', { name: '导入' }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
      id: 'material:import',
      type: 'material_import',
      label: '导入素材',
    }))
    fireEvent.click(within(screen.getByTestId('directory-header-actions')).getByRole('button', { name: '网络' }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
      id: 'material:network',
      type: 'material_network',
      label: '记忆网络',
    }))
  })

  it('素材列表加载失败时显示错误和重试', async () => {
    apiMock.materials
      .mockRejectedValueOnce(new Error('materials down'))
      .mockImplementation(() => Promise.resolve({ items: rows, next_cursor: null, total: 3 }))

    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/素材加载失败/)
    fireEvent.click(screen.getByRole('button', { name: /重试/ }))

    await waitFor(() => expect(apiMock.materials.mock.calls.length).toBeGreaterThanOrEqual(2))
    expect(await screen.findByText('城墙外环与雾港边界')).toBeTruthy()
  })

  it('素材目录按页加载,点击加载更多追加下一页', async () => {
    apiMock.materials
      .mockResolvedValueOnce({ items: rows.slice(0, 2), next_cursor: 2, total: 3 })
      .mockResolvedValueOnce({ items: rows.slice(2), next_cursor: null, total: 3 })

    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    expect(await screen.findByText('城墙外环与雾港边界')).toBeTruthy()
    expect(screen.queryByText('无标签待整理素材')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /加载更多/ }))

    await waitFor(() => expect(apiMock.materials).toHaveBeenCalledWith(
      expect.objectContaining({ cursor: 2 }),
    ))
    expect(await screen.findByText('无标签待整理素材')).toBeTruthy()
  })

  it('素材详情按 id 单条加载,失败时给真实错误与重试', async () => {
    apiMock.material.mockRejectedValue(new Error('materials api down'))

    render(<MaterialDetail node={{ id: 'material:1', type: 'material', ref: 1, label: '城墙外环与雾港边界' }} />)

    expect(await screen.findByText(/materials api down/)).toBeTruthy()
    expect(screen.queryByText(/可能已删除/)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    await waitFor(() => expect(apiMock.material).toHaveBeenCalledTimes(2))
  })

  it('作者直接新建素材并保留分类、来源和置顶字段', async () => {
    const onCreated = vi.fn()
    render(<MaterialNew kind="reference" onCreated={onCreated} />)

    fireEvent.change(screen.getByLabelText('素材标题'), { target: { value: '《印迹》世界观设定全案' } })
    fireEvent.change(screen.getByLabelText('素材来源'), { target: { value: '作者资料' } })
    fireEvent.click(screen.getByLabelText('核心记忆(置顶)'))
    fireEvent.click(screen.getByRole('button', { name: '保存素材' }))

    await waitFor(() => expect(apiMock.addMaterial).toHaveBeenCalledWith(expect.objectContaining({
      title: '《印迹》世界观设定全案',
      kind: 'reference',
      source: '作者资料',
      pinned: true,
      origin: 'manual',
    })))
    expect(onCreated).toHaveBeenCalledWith(9, '《印迹》世界观设定全案')
  })

  it('作者直接保存素材编辑，不生成主编审批请求', async () => {
    const onChanged = vi.fn()
    render(<MaterialDetail node={{ id: 'material:1', type: 'material', ref: 1, label: '城墙外环' }} onChanged={onChanged} />)

    expect(await screen.findByDisplayValue('城墙外环与雾港边界')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('素材标题'), { target: { value: '城墙边界修订' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => expect(apiMock.editMaterial).toHaveBeenCalledWith(1, expect.objectContaining({
      title: '城墙边界修订',
      pinned: true,
    })))
    expect(onChanged).toHaveBeenCalledWith(expect.objectContaining({ title: '城墙边界修订' }))
  })

  it('建议归档时由作者直接 PATCH archived=true', async () => {
    const onDeleted = vi.fn()
    render(<MaterialDetail node={{ id: 'material:1', type: 'material', ref: 1, label: '城墙外环与雾港边界' }} onDeleted={onDeleted} />)

    expect(await screen.findByText(/素材 · 研究/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '删除' }))

    expect(await screen.findByText(/影响范围/)).toBeTruthy()
    const dialog = screen.getByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: '归档' }))

    await waitFor(() => expect(apiMock.editMaterial).toHaveBeenCalledWith(1, { archived: true }))
    expect(onDeleted).toHaveBeenCalled()
  })

  it('无引用素材由作者直接硬删并携带影响令牌', async () => {
    apiMock.objectImpact.mockResolvedValue({
      object: { type: 'material', id: 1, label: '城墙外环与雾港边界' },
      references: [],
      recommended_action: 'hard_delete_allowed',
      confirm_impact_token: 'material-1-token',
    })
    render(<MaterialDetail node={{ id: 'material:1', type: 'material', ref: 1, label: '城墙外环' }} />)

    expect(await screen.findByText(/素材 · 研究/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '删除' }))
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: '删除' }))

    await waitFor(() => expect(apiMock.delMaterial).toHaveBeenCalledWith(1, 'material-1-token'))
  })

  it('插入当前章只发布待采纳草稿，不能在作者填入前伪记 material_reference', async () => {
    render(<MaterialDetail node={{ id: 'material:1', type: 'material', ref: 1, label: '城墙外环' }} />)
    expect(await screen.findByTestId('material-insert-current')).toBeTruthy()
    fireEvent.click(screen.getByTestId('material-insert-current'))
    expect(apiMock.addMaterialReference).not.toHaveBeenCalled()
  })

  it('详情展示 summary/pinned 字段', async () => {
    render(<MaterialDetail node={{ id: 'material:1', type: 'material', ref: 1, label: '城墙外环' }} />)
    expect(await screen.findByTestId('material-summary')).toHaveValue('边界感营造')
    expect(screen.getByTestId('material-pinned-toggle')).toBeChecked()
  })

  it('章级账本展示本章参考素材和 phase', async () => {
    apiMock.materialRefsByChapter.mockResolvedValue([
      { material_id: 1, title: '借命仪式资料', kind: 'research', dimension: 'final', reason: '正文采用' },
    ])
    const onSelect = vi.fn()

    render(<ChapterMaterialRefs seq={4} onSelectMaterial={onSelect} />)

    expect(await screen.findByText('本章参考素材')).toBeTruthy()
    expect(screen.getByText('借命仪式资料')).toBeTruthy()
    expect(screen.getByText('phase:final')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /借命仪式资料/ }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ type: 'material', ref: 1 }))
  })
})
