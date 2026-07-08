import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MaterialDetail, MaterialList } from '../Materials'
import { ChapterMaterialRefs } from '../ChapterStudio'

const apiMock = vi.hoisted(() => ({
  materials: vi.fn(),
  materialRecall: vi.fn(),
  materialRefs: vi.fn(),
  objectImpact: vi.fn(),
  deleteObject: vi.fn(),
  archiveObject: vi.fn(),
  materialRefsByChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

vi.mock('../MaterialImport', () => ({ MaterialImport: () => <div data-testid="material-import" /> }))
vi.mock('../MaterialNetwork', () => ({ MaterialNetwork: () => <div data-testid="material-network" /> }))
vi.mock('../editor/RichEditor', () => ({
  RichEditor: ({ value, ariaLabel }) => <textarea aria-label={ariaLabel} value={value || ''} readOnly />,
  useUnsavedGuard: vi.fn(),
}))

const rows = [
  {
    id: 1,
    title: '城墙外环与雾港边界',
    body: '旧城外环由三层废弃货线组成。',
    kind: 'research',
    tags: ['城市', '边界'],
    source: '城市规划笔记.md',
    pinned: true,
    recall_count: 7,
  },
  {
    id: 2,
    title: '码头晨雾中的铜炉反光',
    body: '雾贴着船壳翻卷。',
    kind: 'snippet',
    tags: ['雾'],
    source: '',
    pinned: false,
    recall_count: 0,
  },
  {
    id: 3,
    title: '无标签待整理素材',
    body: '还没有整理。',
    kind: 'note',
    tags: [],
    source: '',
    pinned: false,
    recall_count: 0,
  },
]

describe('MaterialList 素材库工作台', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.materials.mockResolvedValue(rows)
    apiMock.materialRecall.mockResolvedValue([])
    apiMock.materialRefs.mockResolvedValue([])
    apiMock.objectImpact.mockResolvedValue({
      object: { type: 'material', id: 1, label: '城墙外环与雾港边界' },
      references: [
        { kind: 'material_reference', count: 2 },
        { kind: 'graph', count: 1 },
      ],
      recommended_action: 'archive',
      confirm_impact_token: 'material-1-token',
    })
    apiMock.deleteObject.mockResolvedValue({ deleted: true })
    apiMock.archiveObject.mockResolvedValue({ ok: true })
    apiMock.materialRefsByChapter.mockResolvedValue([])
  })

  it('用窄目录工作台布局保留搜索第一行和动作第二行', async () => {
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    expect(await screen.findByTestId('material-workbench')).toBeTruthy()
    const header = screen.getByTestId('material-workbench-header')
    const searchRow = screen.getByTestId('material-search-row')
    const actionRow = screen.getByTestId('material-action-row')

    expect(within(header).getByText('素材库')).toBeTruthy()
    expect(within(searchRow).getByLabelText('搜索素材')).toBeTruthy()
    expect(Boolean(searchRow.compareDocumentPosition(actionRow) & Node.DOCUMENT_POSITION_FOLLOWING)).toBe(true)
    expect(within(actionRow).getByRole('button', { name: '新建' })).toBeTruthy()
    expect(within(actionRow).getByRole('button', { name: '导入' })).toBeTruthy()
    expect(within(actionRow).getByRole('button', { name: '网络' })).toBeTruthy()
  })

  it('提供智能视图、分类筛选和素材点击详情联动', async () => {
    const onSelect = vi.fn()
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} onSelect={onSelect} />)

    expect(await screen.findByText('智能视图')).toBeTruthy()
    const smartViews = within(screen.getByTestId('material-smart-views'))
    const kinds = within(screen.getByTestId('material-kind-list'))
    expect(smartViews.getByRole('button', { name: /核心记忆/ })).toBeTruthy()
    expect(smartViews.getByRole('button', { name: /已引用/ })).toBeTruthy()
    expect(smartViews.getByRole('button', { name: /无标签/ })).toBeTruthy()
    expect(kinds.getByRole('button', { name: /研究/ })).toBeTruthy()
    expect(kinds.getByRole('button', { name: /片段/ })).toBeTruthy()

    fireEvent.click(smartViews.getByRole('button', { name: /核心记忆/ }))
    expect(screen.getByRole('button', { name: /城墙外环与雾港边界/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /码头晨雾中的铜炉反光/ })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /城墙外环与雾港边界/ }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
      id: 'material:1',
      type: 'material',
      ref: 1,
      label: '城墙外环与雾港边界',
    }))
  })

  it('导入和网络作为素材详情节点传出,不替换二栏目录', async () => {
    const onSelect = vi.fn()
    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} onSelect={onSelect} />)

    await screen.findByTestId('material-workbench')
    fireEvent.click(screen.getByRole('button', { name: '导入' }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
      id: 'material:import',
      type: 'material_import',
      label: '导入素材',
    }))
    expect(screen.getByTestId('material-workbench')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '网络' }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
      id: 'material:network',
      type: 'material_network',
      label: '记忆网络',
    }))
  })

  it('素材列表加载失败时显示错误和重试', async () => {
    apiMock.materials
      .mockRejectedValueOnce(new Error('materials down'))
      .mockResolvedValueOnce(rows)

    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/素材加载失败/)
    fireEvent.click(screen.getByRole('button', { name: /重试/ }))

    await waitFor(() => expect(apiMock.materials).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('城墙外环与雾港边界')).toBeTruthy()
  })

  it('兼容后端分页返回形态,只渲染 items 中的素材', async () => {
    apiMock.materials.mockResolvedValue({
      items: rows.slice(0, 2),
      next_cursor: 2,
      total: 3,
    })

    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    expect(await screen.findByText('城墙外环与雾港边界')).toBeTruthy()
    expect(screen.getByText('码头晨雾中的铜炉反光')).toBeTruthy()
    expect(screen.queryByText('无标签待整理素材')).toBeNull()
  })

  it('素材目录按页加载,点击加载更多追加下一页', async () => {
    apiMock.materials
      .mockResolvedValueOnce({ items: rows.slice(0, 2), next_cursor: 2, total: 3 })
      .mockResolvedValueOnce({ items: rows.slice(2), next_cursor: null, total: 3 })

    render(<MaterialList node={{ id: 'material_root', type: 'material_root', label: '素材库' }} />)

    expect(await screen.findByText('城墙外环与雾港边界')).toBeTruthy()
    expect(screen.queryByText('无标签待整理素材')).toBeNull()
    expect(apiMock.materials).toHaveBeenCalledWith({ limit: 200 })

    fireEvent.click(screen.getByRole('button', { name: /加载更多/ }))

    await waitFor(() => expect(apiMock.materials).toHaveBeenCalledWith({ limit: 200, cursor: 2 }))
    expect(await screen.findByText('无标签待整理素材')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /加载更多/ })).toBeNull()
  })

  it('删除素材前展示生命周期影响范围,建议归档时默认归档', async () => {
    const onDeleted = vi.fn()
    render(<MaterialDetail node={{ id: 'material:1', type: 'material', ref: 1, label: '城墙外环与雾港边界' }} onDeleted={onDeleted} />)

    expect(await screen.findByText('素材 · 研究')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '删除' }))

    expect(await screen.findByText(/影响范围/)).toBeTruthy()
    expect(screen.getByText(/material_reference: 2/)).toBeTruthy()
    expect(screen.getByText(/graph: 1/)).toBeTruthy()

    const dialog = screen.getByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: '归档' }))

    await waitFor(() => expect(apiMock.archiveObject).toHaveBeenCalledWith('material', 1))
    expect(apiMock.deleteObject).not.toHaveBeenCalled()
    expect(onDeleted).toHaveBeenCalled()
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
