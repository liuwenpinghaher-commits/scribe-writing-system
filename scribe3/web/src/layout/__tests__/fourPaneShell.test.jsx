import { beforeAll, beforeEach, describe, it, expect, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { FourPaneShell } from '../FourPaneShell'

const materialListMount = vi.hoisted(() => ({ count: 0 }))
// 只替换 useDefaultLayout(断言布局 id 按作品隔离),其余 Group/Panel/Separator/usePanelRef 走真身,
// 整包 mock 会炸掉四栏渲染。返回 defaultLayout=undefined 让 Group 回退默认布局,不至崩。
const mockUseDefaultLayout = vi.hoisted(() => vi.fn(() => ({ defaultLayout: undefined, onLayoutChanged: () => {} })))
vi.mock('react-resizable-panels', async () => {
  const actual = await vi.importActual('react-resizable-panels')
  return { ...actual, useDefaultLayout: mockUseDefaultLayout }
})
const apiMock = vi.hoisted(() => ({
  promisesLedger: vi.fn(() => Promise.resolve({ open: [], closed: [], red_herring: [] })),
  motifs: vi.fn(() => Promise.resolve([])),
  qc: vi.fn(() => Promise.resolve({})),
  search: vi.fn(() => Promise.resolve({ results: [] })),
  issues: vi.fn(() => Promise.resolve({ issues: [{ id: 'issue:1', title: '整句重复', chapter: 4, source: 'qc', severity: 'warning', range: [0, 4], status: 'open' }], degraded_sources: [] })),
  chapter: vi.fn(() => Promise.resolve({ title: '第七章', scene_truth: '', deductions: [], involved_characters: [] })),
  entities: vi.fn(() => Promise.resolve([])),
  listUnverified: vi.fn(() => Promise.resolve([])),
  acceptUnverified: vi.fn(() => Promise.resolve({ ok: true })),
  ignoreUnverified: vi.fn(() => Promise.resolve({ ok: true })),
  ignoreAllUnverified: vi.fn(() => Promise.resolve({ ignored: 0 })),
  createChapter: vi.fn(() => Promise.resolve({ status: 'created', seq: 8, title: '第8章', volume: null })),
}))

vi.mock('../../DetailPane', () => ({
  DetailPane: ({ sel, onTreeChanged }) => (
    <div>
      <div data-testid="detail-content">{sel?.mode === 'view' ? `view:${sel.viewKey}` : `node:${sel?.node?.id || 'empty'}`}</div>
      <button onClick={() => onTreeChanged?.()}>触发树刷新</button>
    </div>
  ),
}))

vi.mock('../../api', () => ({
  api: apiMock,
}))

vi.mock('../../ProjectTree', () => ({
  ProjectTree: ({ tree, onSelect }) => (
    <div data-testid="project-tree">
      <div>{tree?.manuscript?.label}</div>
      <div>{tree?.codex?.label}</div>
      <div>{tree?.materials?.label}</div>
      <button onClick={() => onSelect?.(tree?.codex?.children?.[0])}>打开条目</button>
    </div>
  ),
}))

vi.mock('../../DeduceTree', () => ({
  DeduceTree: () => <div data-testid="deduce-tree">场景真相 涉及角色 添加涉及角色</div>,
}))

vi.mock('../../DeduceStage', () => ({
  DeduceStage: ({ seq }) => <div data-testid="deduce-stage">演绎详情:{seq}</div>,
}))

vi.mock('../../studioDocks', async () => {
  const actual = await vi.importActual('../../studioDocks')
  return {
    ...actual,
    RightDock: ({ sel, lastSeq }) => (
    <aside data-testid="chief">{`${sel?.mode || 'none'}:${lastSeq ?? ''}`}</aside>
    ),
  }
})

vi.mock('../../ContainerOutline', () => ({
  ContainerOutline: ({ node, onOpenChapter, onSelect }) => (
    <div data-testid="container-outline" data-node={node.id}>
      <button onClick={() => onSelect?.(node.children?.[0])}>打开条目</button>
      <button onClick={() => onOpenChapter?.({ seq: 7, title: '第七章' })}>打开章节</button>
    </div>
  ),
}))

vi.mock('../../Materials', async () => {
  const React = await vi.importActual('react')
  return {
    MaterialList: ({ node, onSelect }) => {
      const [instance] = React.useState(() => ++materialListMount.count)
      return (
        <div data-testid="material-list" data-node={node.id} data-instance={String(instance)}>
          <label>
            搜索素材
            <input aria-label="搜索素材" />
          </label>
          <button>网络</button>
          <button>导入</button>
          <button>新建</button>
          <button onClick={() => onSelect?.({ id: 'material:1', type: 'material', ref: 1, label: '素材一' })}>素材一</button>
        </div>
      )
    },
  }
})

const tree = {
  manuscript: {
    id: 'manuscript_root',
    type: 'manuscript_root',
    label: '手稿',
    children: [
      { id: 'vol:1', type: 'volume', ref: '1', label: '第一卷', children: [{ id: 'ch:1', type: 'chapter', ref: 1, label: '第 1 章 入城' }] },
    ],
  },
  codex: {
    id: 'codex_root',
    type: 'codex_root',
    label: '设定库',
    children: [
      { id: 'cat:character', type: 'codex_category', ref: 'character', label: '角色', children: [{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }] },
    ],
  },
  materials: { id: 'material_root', type: 'material_root', label: '素材库' },
}

function Harness({ initialSel = { mode: 'node', node: null }, work = 'demo', leftSeq = 3 }) {
  const [sel, setSel] = useState(initialSel)
  const onSelectNode = (node) => {
    if (!node) { setSel({ mode: 'node', node: null }); return }
    if (node.type === 'view') setSel({ mode: 'view', viewKey: node.id.split(':')[1] })
    else setSel({ mode: 'node', node })
  }
  return <FourPaneShell tree={tree} sel={sel} onSelectNode={onSelectNode} work={work} leftSeq={leftSeq} reload={() => {}} />
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('FourPaneShell 四栏钻取', () => {
  beforeAll(() => {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    globalThis.ResizeObserver = ResizeObserverMock
  })

  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    apiMock.promisesLedger.mockResolvedValue({ open: [], closed: [], red_herring: [] })
    apiMock.motifs.mockResolvedValue([])
    apiMock.qc.mockResolvedValue({})
    apiMock.search.mockResolvedValue({ results: [] })
    apiMock.issues.mockResolvedValue({ issues: [{ id: 'issue:1', title: '整句重复', chapter: 4, source: 'qc', severity: 'warning', range: [0, 4], status: 'open' }], degraded_sources: [] })
    apiMock.chapter.mockResolvedValue({ title: '第七章', scene_truth: '', deductions: [], involved_characters: [] })
    apiMock.entities.mockResolvedValue([])
    apiMock.createChapter.mockResolvedValue({ status: 'created', seq: 8, title: '第8章', volume: null })
  })

  it('入口只切换栏2目录,目录条目才切换栏3详情,且栏2常驻', () => {
    render(<Harness />)

    expect(screen.getByTestId('left-entry-rail').querySelector('.w-\\[56px\\]')).toBeTruthy()
    expect(screen.queryByTestId('entry-rail')).toBeNull()
    expect(screen.queryByRole('button', { name: '项目树' })).toBeNull()
    expect(screen.getByRole('button', { name: '手稿' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '设定库' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '素材库' })).toBeTruthy()
    expect(screen.getByTestId('col-directory')).toBeTruthy()
    expect(screen.queryByTestId('project-tree')).toBeNull()
    expect(screen.queryByText('书级')).toBeNull()
    expect(screen.getByText('卷章')).toBeTruthy()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:empty')

    fireEvent.click(screen.getByRole('button', { name: '设定库' }))
    expect(screen.queryByTestId('project-tree')).toBeNull()
    expect(screen.getByTestId('codex-directory-title').textContent).toBe('设定库')

    fireEvent.click(within(screen.getByTestId('col-directory')).getByRole('button', { name: '角色' }))
    expect(screen.getByTestId('col-directory')).toBeTruthy()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:cat:character')
  })

  it('素材库入口保留原素材工作台能力,不是只剩分类树', () => {
    render(<Harness />)

    fireEvent.click(screen.getByRole('button', { name: '素材库' }))

    expect(screen.getByTestId('material-list').getAttribute('data-node')).toBe('material_root')
    expect(screen.queryByTestId('project-tree')).toBeNull()
    expect(screen.getByLabelText('搜索素材')).toBeTruthy()
    expect(within(screen.getByTestId('material-list')).getByRole('button', { name: '新建' })).toBeTruthy()
    expect(within(screen.getByTestId('material-list')).getByRole('button', { name: '导入' })).toBeTruthy()
    expect(within(screen.getByTestId('material-list')).getByRole('button', { name: '网络' })).toBeTruthy()

    fireEvent.click(within(screen.getByTestId('material-list')).getByRole('button', { name: '素材一' }))
    expect(screen.getByTestId('detail-content').textContent).toBe('node:material:1')
  })

  it('三栏详情触发树刷新后会重挂载素材目录,重新读取活跃列表', async () => {
    localStorage.setItem('s3.demo.leftTab', 'materials')
    materialListMount.count = 0
    render(<Harness />)

    const firstInstance = screen.getByTestId('material-list').getAttribute('data-instance')
    fireEvent.click(screen.getByRole('button', { name: '触发树刷新' }))

    await waitFor(() => {
      expect(screen.getByTestId('material-list').getAttribute('data-instance')).not.toBe(firstInstance)
    })
  })

  it('二栏新建章会调用后端并在三栏选中新章', async () => {
    const reload = vi.fn()
    function CreateHarness() {
      const [sel, setSel] = useState({ mode: 'node', node: null })
      const onSelectNode = (node) => {
        if (!node) { setSel({ mode: 'node', node: null }); return }
        if (node.type === 'view') setSel({ mode: 'view', viewKey: node.id.split(':')[1] })
        else setSel({ mode: 'node', node })
      }
      return <FourPaneShell tree={tree} sel={sel} onSelectNode={onSelectNode} work="demo" leftSeq={1} reload={reload} />
    }
    render(<CreateHarness />)

    expect(screen.queryByRole('button', { name: '新建章' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '在第一卷中新建章' }))

    await waitFor(() => expect(apiMock.createChapter).toHaveBeenCalledWith({ volume: '1' }))
    expect(reload).toHaveBeenCalled()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:ch:8')
  })

  it('二栏使用可拖拽面板且默认更窄,不再写死 288px', () => {
    render(<Harness />)

    const panel = screen.getByTestId('col-directory-panel')
    expect(panel.getAttribute('data-default-size')).toBe('14')
    expect(panel.getAttribute('data-min-size')).toBe('10')
    expect(panel.getAttribute('data-max-size')).toBe('24')
    const handles = screen.getAllByRole('separator')
    expect(handles).toHaveLength(2)
    expect(handles[0].className).toContain('cursor-col-resize')
    expect(screen.getByTestId('col-directory').className).not.toContain('w-[288px]')
  })

  it('点击当前栏1入口可以折叠栏2,并从详情栏恢复', () => {
    render(<Harness />)

    expect(screen.getByTestId('col-directory')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '手稿' }))

    expect(screen.queryByTestId('col-directory')).toBeNull()
    const restore = screen.getByTestId('directory-restore-button')
    // 2026-07-12 重叠修复:还原钮=贴栏3 左缘垂直居中的细把手,不再 top-2 left-2 压住头部面包屑
    expect(restore.className).toContain('left-0')
    expect(restore.className).toContain('top-1/2')
    expect(restore.className).not.toContain('top-2 ')

    fireEvent.click(restore)

    expect(screen.getByTestId('col-directory')).toBeTruthy()
  })

  it('右侧主编栏可以折叠并从详情栏恢复', () => {
    render(<Harness />)

    expect(screen.getByTestId('chief')).toBeTruthy()

    fireEvent.click(screen.getByTestId('right-collapse-button'))

    expect(screen.queryByTestId('chief')).toBeNull()
    const restore = screen.getByTestId('right-restore-button')
    // 同款重叠修复:贴栏3 右缘垂直居中,不再 top-2 right-2 压住头部「更多」按钮
    expect(restore.className).toContain('right-0')
    expect(restore.className).toContain('top-1/2')

    fireEvent.click(restore)

    expect(screen.getByTestId('chief')).toBeTruthy()
  })

  it('左栏能力切换进入栏2,右侧主编栏保持常驻', () => {
    render(<Harness />)

    fireEvent.click(screen.getByRole('button', { name: '演绎 · 角色限知' }))

    expect(screen.queryByTestId('deduce-tree')).toBeNull()
    expect(screen.getByTestId('directory-sticky-header').textContent).toContain('演绎')
    expect(screen.getByRole('button', { name: /场景真相/ })).toBeTruthy()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:empty')

    fireEvent.click(screen.getByRole('button', { name: /场景真相/ }))

    expect(screen.getByTestId('detail-content').textContent).toBe('node:deduce:truth')
    expect(screen.getByTestId('chief')).toBeTruthy()
  })

  it('未选章时仍保留所有全书能力入口', () => {
    render(<Harness leftSeq={null} />)

    for (const label of ['手稿', '设定库', '素材库', '演绎 · 角色限知', '伏笔', '母题', '搜索', '校验']) {
      expect(screen.getByRole('button', { name: label })).toBeTruthy()
    }
  })

  it('左栏 active tab 按 work 隔离读取', async () => {
    localStorage.setItem('s3.book_a.leftTab', 'materials')
    localStorage.setItem('s3.book_b.leftTab', 'codex')
    const { rerender } = render(<Harness work="book_a" />)

    expect(screen.getByTestId('material-list').getAttribute('data-node')).toBe('material_root')

    rerender(<Harness work="book_b" />)

    await waitFor(() => expect(screen.getByTestId('codex-directory-title').textContent).toBe('设定库'))
    expect(screen.queryByTestId('project-tree')).toBeNull()
  })

  it('同一章号切换 work 时左栏数据源会重新读取,避免伏笔母题校验串书', async () => {
    localStorage.setItem('s3.book_a.leftTab', 'promise')
    localStorage.setItem('s3.book_b.leftTab', 'promise')
    const { rerender } = render(<Harness work="book_a" leftSeq={4} />)

    await waitFor(() => expect(apiMock.promisesLedger).toHaveBeenCalledTimes(1))
    expect(apiMock.motifs).toHaveBeenCalledTimes(1)
    expect(apiMock.qc).toHaveBeenCalledTimes(1)
    expect(apiMock.chapter).toHaveBeenCalledTimes(1)
    expect(apiMock.promisesLedger).toHaveBeenNthCalledWith(1, 'book_a')
    expect(apiMock.motifs).toHaveBeenNthCalledWith(1, 'book_a')
    expect(apiMock.qc).toHaveBeenNthCalledWith(1, 4, 'book_a')
    expect(apiMock.chapter).toHaveBeenNthCalledWith(1, 4, 'book_a')

    rerender(<Harness work="book_b" leftSeq={4} />)

    await waitFor(() => expect(apiMock.promisesLedger).toHaveBeenCalledTimes(2))
    expect(apiMock.motifs).toHaveBeenCalledTimes(2)
    expect(apiMock.qc).toHaveBeenCalledTimes(2)
    expect(apiMock.chapter).toHaveBeenCalledTimes(2)
    expect(apiMock.promisesLedger).toHaveBeenNthCalledWith(2, 'book_b')
    expect(apiMock.motifs).toHaveBeenNthCalledWith(2, 'book_b')
    expect(apiMock.qc).toHaveBeenNthCalledWith(2, 4, 'book_b')
    expect(apiMock.chapter).toHaveBeenNthCalledWith(2, 4, 'book_b')
  })

  it('切换 work 后忽略旧书晚到的伏笔台账响应', async () => {
    localStorage.setItem('s3.book_a.leftTab', 'promise')
    localStorage.setItem('s3.book_b.leftTab', 'promise')
    const bookA = deferred()
    const bookB = deferred()
    apiMock.promisesLedger
      .mockReturnValueOnce(bookA.promise)
      .mockReturnValueOnce(bookB.promise)

    const { rerender } = render(<Harness work="book_a" leftSeq={4} />)
    await waitFor(() => expect(apiMock.promisesLedger).toHaveBeenCalledTimes(1))

    rerender(<Harness work="book_b" leftSeq={4} />)
    await waitFor(() => expect(apiMock.promisesLedger).toHaveBeenCalledTimes(2))

    await act(async () => {
      bookB.resolve({
        open: [
          { id: 'b1', text: 'B书伏笔1', setup_chapter: 1, payoff_chapter: null, status: 'open' },
          { id: 'b2', text: 'B书伏笔2', setup_chapter: 2, payoff_chapter: null, status: 'open' },
        ],
        closed: [],
        red_herring: [],
      })
      await bookB.promise
    })
    await waitFor(() => expect(screen.getByRole('button', { name: '伏笔' }).textContent).toContain('2'))

    await act(async () => {
      bookA.resolve({ open: [{ id: 'a', text: 'A书旧伏笔', setup_chapter: 1, payoff_chapter: null, status: 'open' }], closed: [], red_herring: [] })
      await bookA.promise
    })

    await waitFor(() => expect(screen.getByRole('button', { name: '伏笔' }).textContent).toContain('2'))
    expect(screen.getByRole('button', { name: '伏笔' }).textContent).not.toContain('1')
  })

  it('横切视图不再作为栏1入口', () => {
    render(<Harness />)

    const rail = within(screen.getByTestId('left-entry-rail'))
    expect(rail.queryByRole('button', { name: '图谱' })).toBeNull()
    expect(rail.queryByRole('button', { name: '时间线' })).toBeNull()
    expect(rail.queryByRole('button', { name: '仪表盘' })).toBeNull()
    expect(rail.queryByRole('button', { name: '简报' })).toBeNull()
    expect(rail.queryByRole('button', { name: '北极星' })).toBeNull()
    expect(rail.queryByRole('button', { name: '帧/意图' })).toBeNull()
  })

  it('四栏真实路径使用全局搜索目录和校验 issue 台账', async () => {
    render(<Harness leftSeq={4} />)

    fireEvent.click(screen.getByRole('button', { name: '搜索' }))
    expect(screen.getByLabelText('全局搜索')).toBeTruthy()
    expect(screen.queryByPlaceholderText('按意思搜,如「炼丹复活」')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '校验' }))
    expect(await screen.findByTestId('issue-list')).toBeTruthy()
    expect(screen.getByText('整句重复')).toBeTruthy()
  })

  it('外层顶栏切入视图时隐藏栏2,栏3全画布渲染 view', () => {
    render(<Harness initialSel={{ mode: 'view', viewKey: 'atlas' }} />)

    expect(screen.queryByTestId('col-directory')).toBeNull()
    expect(screen.getByTestId('detail-content').textContent).toBe('view:atlas')
  })

  it('view 态点击左栏非当前入口会退出横切视图并恢复栏2目录', () => {
    localStorage.setItem('s3.demo.leftTab', 'materials')
    render(<Harness initialSel={{ mode: 'view', viewKey: 'atlas' }} />)

    expect(screen.queryByTestId('col-directory')).toBeNull()
    expect(screen.getByTestId('detail-content').textContent).toBe('view:atlas')

    fireEvent.click(screen.getByRole('button', { name: '手稿' }))

    expect(screen.getByTestId('col-directory')).toBeTruthy()
    expect(screen.queryByText('书级')).toBeNull()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:empty')
  })

  it('view 态点击当前高亮左栏入口也会回到该入口目录', () => {
    localStorage.setItem('s3.demo.leftTab', 'materials')
    render(<Harness initialSel={{ mode: 'view', viewKey: 'atlas' }} />)

    expect(screen.queryByTestId('col-directory')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '素材库' }))

    expect(screen.getByTestId('col-directory')).toBeTruthy()
    expect(screen.getByTestId('material-list').getAttribute('data-node')).toBe('material_root')
    expect(screen.getByTestId('detail-content').textContent).toBe('node:empty')
  })

  // Task 3:栏1 八入口按「内容/工艺/检查」三组呈现,分组不得删除任何能力,
  // 且三个组必须能被辅助技术识别(role=group + aria-label),八入口可访问名逐一保留。
  it('八个 PC 入口按三组呈现且不丢能力', () => {
    render(<Harness />)

    expect(screen.getByRole('group', { name: '内容' })).toBeTruthy()
    expect(screen.getByRole('group', { name: '工艺' })).toBeTruthy()
    expect(screen.getByRole('group', { name: '检查' })).toBeTruthy()

    for (const name of ['手稿', '设定库', '素材库', '演绎 · 角色限知', '伏笔', '母题', '搜索', '校验']) {
      expect(screen.getByRole('button', { name })).toBeTruthy()
    }
  })

  // Task 4:面板栏宽布局按作品隔离,换书不串栏宽。id 保留现常量前缀,换名会作废用户既有偏好。
  it('scopes panel layout by work', () => {
    render(<Harness work="book-a" />)
    expect(mockUseDefaultLayout).toHaveBeenCalledWith(expect.objectContaining({ id: 's3.fourPane.layout.v2:book-a' }))
  })
})
