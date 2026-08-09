import { beforeAll, beforeEach, describe, it, expect, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useEffect, useState } from 'react'
import { FourPaneShell } from '../FourPaneShell'
import { ChiefSlotProvider, useChiefSlot } from '../../ChiefSlotContext'

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
  // ManuscriptDirectory 挂载时回读当前作品的正典章节；空清单代表
  // 项目树快照已覆盖本夹具中的卷章，避免把外部 HTTP 留在组件测试中。
  chapters: vi.fn(() => Promise.resolve([])),
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
  const React = await vi.importActual('react')
  const actual = await vi.importActual('../../studioDocks')
  return {
    ...actual,
    useRightDockController: ({ seq }) => {
      const [activeKey, setActiveKey] = React.useState('chief')
      const caps = [
        { key: 'chief', label: '主编', scope: 'object', render: () => <aside data-testid="chief">主编内容</aside> },
        ...(seq != null ? [{ key: 'versions', label: '存档', scope: 'chapter', render: () => <aside data-testid="versions">存档内容</aside> }] : []),
        { key: 'inbox', label: '收件箱 · 等你决策', scope: 'global', badge: 3, render: () => <aside data-testid="inbox">收件箱内容</aside> },
      ]
      const active = caps.find((cap) => cap.key === activeKey) || caps[0]
      return { caps, active, activeKey: active.key, activate: (key) => setActiveKey(caps.some((cap) => cap.key === key) ? key : 'chief') }
    },
    RightDock: ({ active }) => <div data-testid="right-dock-content">{active.render()}</div>,
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
    apiMock.chapters.mockResolvedValue([])
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

  it('从伏笔详情切到素材库时,栏3 收敛到素材根(不再残留伏笔详情)', () => {
    localStorage.setItem('s3.demo.leftTab', 'promise')
    render(
      <Harness
        initialSel={{
          mode: 'node',
          node: {
            id: 'promise:overdue',
            type: 'promise_view',
            capability: 'promise',
            label: '超期未收',
            ref: { view: 'overdue', seq: 3 },
          },
        }}
      />,
    )
    expect(screen.getByTestId('detail-content').textContent).toBe('node:promise:overdue')

    fireEvent.click(screen.getByRole('button', { name: '素材库' }))

    expect(screen.getByTestId('material-list')).toBeTruthy()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:material_root')
  })

  it('s3-open-capability 打开搜索时栏3 不残留伏笔详情', async () => {
    localStorage.setItem('s3.demo.leftTab', 'promise')
    render(
      <Harness
        initialSel={{
          mode: 'node',
          node: {
            id: 'promise:overdue',
            type: 'promise_view',
            capability: 'promise',
            label: '超期未收',
          },
        }}
      />,
    )
    expect(screen.getByTestId('detail-content').textContent).toBe('node:promise:overdue')

    fireEvent(window, new CustomEvent('s3-open-capability', { detail: { capability: 'search', focus: true } }))

    await waitFor(() => {
      expect(screen.getByTestId('col-directory').textContent).toMatch(/搜索|全局/)
    })
    // 搜索入口无着陆节点 → 清空栏3
    expect(screen.getByTestId('detail-content').textContent).toBe('node:empty')
  })

  it('切入口时保留章选中(写作粘性),不强制清空栏3', () => {
    localStorage.setItem('s3.demo.leftTab', 'manuscript')
    render(
      <Harness
        initialSel={{
          mode: 'node',
          node: { id: 'ch:1', type: 'chapter', ref: 1, label: '第 1 章 入城' },
        }}
      />,
    )
    expect(screen.getByTestId('detail-content').textContent).toBe('node:ch:1')

    fireEvent.click(screen.getByRole('button', { name: '素材库' }))
    expect(screen.getByTestId('material-list')).toBeTruthy()
    expect(screen.getByTestId('detail-content').textContent).toBe('node:ch:1')
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

  it('二栏新建章走主编种子,不调用 createChapter REST', async () => {
    const reload = vi.fn()
    const seeds = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
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

    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(seeds.join('\n')).toMatch(/s3_add_chapter/)
    expect(seeds.join('\n')).toMatch(/volume_id=1/)
    expect(apiMock.createChapter).not.toHaveBeenCalled()
    expect(reload).not.toHaveBeenCalled()
  })

  it('二栏使用可拖拽面板且默认更窄,不再写死 288px', () => {
    render(<Harness />)

    const panel = screen.getByTestId('col-directory-panel')
    // 无章 phase → collaboration；默认栏宽与阅读共用（目录次要，主编=详情）
    expect(panel.getAttribute('data-default-size')).toBe('14')
    expect(panel.getAttribute('data-min-size')).toBe('10')
    expect(panel.getAttribute('data-max-size')).toBe('22')
    expect(screen.getByTestId('four-col').getAttribute('data-layout-mode')).toBe('collaboration')
    // 默认聊天(right) 宽于内容(detail)：52 vs 34
    expect(Number(screen.getByTestId('right-panel').getAttribute('data-default-size')))
      .toBeGreaterThan(Number(screen.getByTestId('detail-panel').getAttribute('data-default-size')))
    expect(Number(screen.getByTestId('right-panel').getAttribute('data-default-size'))).toBe(52)
    expect(Number(screen.getByTestId('detail-panel').getAttribute('data-default-size'))).toBe(34)
    // 详情/主编 max=100：折叠一侧后另一侧可铺满，避免锁在 60% 留下大空白
    expect(screen.getByTestId('detail-panel').getAttribute('data-max-size')).toBe('100')
    expect(screen.getByTestId('right-panel').getAttribute('data-max-size')).toBe('100')
    const handles = screen.getAllByRole('separator')
    expect(handles).toHaveLength(2)
    expect(handles[0].className).toContain('cursor-col-resize')
    // 负 margin 把手会在拖拽时叠层错乱,应已移除
    expect(handles[0].className).not.toContain('-mx-')
    expect(screen.getByTestId('col-directory').className).not.toContain('w-[288px]')
  })

  it('折叠主编后 right 标记 collapsed，详情 max 允许铺满', () => {
    render(<Harness />)
    expect(screen.getByTestId('right-panel').getAttribute('data-collapsed')).toBe('0')
    fireEvent.click(screen.getByRole('button', { name: '主编' }))
    expect(screen.queryByTestId('chief')).toBeNull()
    expect(screen.getByTestId('right-panel').getAttribute('data-collapsed')).toBe('1')
    expect(Number(screen.getByTestId('detail-panel').getAttribute('data-max-size'))).toBe(100)
  })

  it('协作入口并入唯一左轨，右栏不再渲染第二轨', () => {
    render(<Harness />)
    expect(screen.getAllByTestId('unified-entry-rail')).toHaveLength(1)
    expect(within(screen.getByTestId('collaboration-rail')).getByRole('button', { name: '主编' })).toBeTruthy()
    expect(screen.queryByTestId('right-capability-rail')).toBeNull()
    expect(within(screen.getByTestId('right-panel')).queryByTestId('unified-entry-rail')).toBeNull()
    expect(screen.getByTestId('right-dock-content').querySelector('.w-\\[56px\\]')).toBeNull()
  })

  it('展开时再点当前协作入口折叠，折叠时再点同一入口重新展开', () => {
    render(<Harness />)
    const chief = screen.getByRole('button', { name: '主编' })
    fireEvent.click(chief)
    expect(screen.getByTestId('right-panel').getAttribute('data-collapsed')).toBe('1')
    expect(screen.getByRole('button', { name: '主编' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '主编' }))
    expect(screen.getByTestId('right-panel').getAttribute('data-collapsed')).toBe('0')
    expect(screen.getByTestId('chief')).toBeTruthy()
  })

  it('s3-right-tab 在右栏折叠时切换入口并展开', async () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: '主编' }))
    fireEvent(window, new CustomEvent('s3-right-tab', { detail: 'inbox' }))
    await waitFor(() => expect(screen.getByTestId('right-panel').getAttribute('data-collapsed')).toBe('0'))
    expect(screen.getByTestId('inbox')).toBeTruthy()
  })

  it('s3-expand-right 保留当前入口并重新展开', async () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: /收件箱/ }))
    fireEvent.click(screen.getByRole('button', { name: /收件箱/ }))
    expect(screen.getByTestId('right-panel').getAttribute('data-collapsed')).toBe('1')
    fireEvent(window, new CustomEvent('s3-expand-right'))
    await waitFor(() => expect(screen.getByTestId('right-panel').getAttribute('data-collapsed')).toBe('0'))
    expect(screen.getByTestId('inbox')).toBeTruthy()
  })

  it('四栏根与右坞使用 overflow/min-w 裁切,防拖窄后整页散架', () => {
    render(<Harness />)
    expect(screen.getByTestId('four-col').className).toContain('overflow-hidden')
    expect(screen.getByTestId('right-dock').className).toMatch(/min-w-/)
    expect(screen.getByTestId('col-directory-panel').className).toMatch(/min-w-/)
  })

  it('协作模式:折叠栏2后从主编(右)左缘恢复,不误贴 detail', () => {
    render(<Harness />)

    expect(screen.getByTestId('col-directory')).toBeTruthy()
    expect(screen.getByTestId('four-col').getAttribute('data-layout-mode')).toBe('collaboration')

    fireEvent.click(screen.getByRole('button', { name: '手稿' }))

    expect(screen.queryByTestId('col-directory')).toBeNull()
    const restore = screen.getByTestId('directory-restore-button')
    // 协作 order=directory|detail|right → 目录折叠后还原贴详情左缘
    expect(restore.getAttribute('data-restore-host')).toBe('detail')
    expect(restore.getAttribute('data-restore-edge')).toBe('left')
    expect(restore.className).toContain('left-0')
    expect(restore.className).toContain('top-1/2')
    expect(restore.className).not.toContain('top-2 ')

    fireEvent.click(restore)

    expect(screen.getByTestId('col-directory')).toBeTruthy()
  })

  it('协作模式:再点主编轨折叠后从详情右缘恢复(会话在最右)', () => {
    render(<Harness />)

    expect(screen.getByTestId('chief')).toBeTruthy()
    expect(screen.getByTestId('four-col').getAttribute('data-layout-mode')).toBe('collaboration')
    // 无右上角浮层收起钮；唯一入口=再点当前右轨 tab
    expect(screen.queryByTestId('right-collapse-button')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '主编' }))

    expect(screen.queryByTestId('chief')).toBeNull()
    const restore = screen.getByTestId('right-restore-button')
    // 协作: order=directory|detail|right → 还原贴详情右缘
    expect(restore.getAttribute('data-restore-host')).toBe('detail')
    expect(restore.getAttribute('data-restore-edge')).toBe('right')
    expect(restore.className).toContain('right-0')
    expect(restore.className).toContain('top-1/2')

    fireEvent.click(restore)

    expect(screen.getByTestId('chief')).toBeTruthy()
  })

  it('阅读模式:折叠还原仍贴 detail 中间舞台左右缘', async () => {
    function PhaseFinal({ children }) {
      const { setChapterPhase } = useChiefSlot()
      useEffect(() => { setChapterPhase('final') }, [setChapterPhase])
      return children
    }
    function ReadingHarness() {
      const [sel, setSel] = useState({
        mode: 'node',
        node: { id: 'ch:1', type: 'chapter', ref: 1, label: '第1章' },
      })
      return (
        <ChiefSlotProvider>
          <PhaseFinal>
            <FourPaneShell
              tree={tree}
              sel={sel}
              onSelectNode={(node) => {
                if (!node) setSel({ mode: 'node', node: null })
                else setSel({ mode: 'node', node })
              }}
              work="demo"
              leftSeq={1}
              reload={() => {}}
            />
          </PhaseFinal>
        </ChiefSlotProvider>
      )
    }
    render(<ReadingHarness />)
    await waitFor(() => {
      expect(screen.getByTestId('four-col').getAttribute('data-layout-mode')).toBe('reading')
    })

    fireEvent.click(screen.getByRole('button', { name: '手稿' }))
    const dirRestore = screen.getByTestId('directory-restore-button')
    expect(dirRestore.getAttribute('data-restore-host')).toBe('detail')
    expect(dirRestore.getAttribute('data-restore-edge')).toBe('left')
    fireEvent.click(dirRestore)

    fireEvent.click(screen.getByRole('button', { name: '主编' }))
    const rightRestore = screen.getByTestId('right-restore-button')
    expect(rightRestore.getAttribute('data-restore-host')).toBe('detail')
    expect(rightRestore.getAttribute('data-restore-edge')).toBe('right')
  })

  it('storage id 与 data-layout-mode 同源(单 mode 路径)', () => {
    render(<Harness work="book-sync" />)
    const mode = screen.getByTestId('four-col').getAttribute('data-layout-mode')
    expect(mode).toBe('collaboration')
    expect(mockUseDefaultLayout).toHaveBeenCalledWith(expect.objectContaining({
      id: `s3.fourPane.layout.v7:${mode}:book-sync`,
    }))
    expect(screen.getByTestId('detail-panel').getAttribute('data-layout-mode')).toBe(mode)
    expect(screen.getByTestId('right-panel').getAttribute('data-layout-mode')).toBe(mode)
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

  // Task 4 / v5:栏宽按 work + layoutMode 隔离
  it('scopes panel layout by work and mode (v5)', () => {
    render(<Harness work="book-a" />)
    expect(mockUseDefaultLayout).toHaveBeenCalledWith(expect.objectContaining({
      id: 's3.fourPane.layout.v7:collaboration:book-a',
    }))
  })

  it('正文 final 阶段默认 reading:栏序变、默认宽与协作相同', async () => {
    function PhaseFinal({ children }) {
      const { setChapterPhase } = useChiefSlot()
      useEffect(() => { setChapterPhase('final') }, [setChapterPhase])
      return children
    }
    function ReadingHarness() {
      const [sel, setSel] = useState({
        mode: 'node',
        node: { id: 'ch:1', type: 'chapter', ref: 1, label: '第1章' },
      })
      return (
        <ChiefSlotProvider>
          <PhaseFinal>
            <FourPaneShell
              tree={tree}
              sel={sel}
              onSelectNode={(node) => {
                if (!node) setSel({ mode: 'node', node: null })
                else setSel({ mode: 'node', node })
              }}
              work="demo"
              leftSeq={1}
              reload={() => {}}
            />
          </PhaseFinal>
        </ChiefSlotProvider>
      )
    }
    render(<ReadingHarness />)
    await waitFor(() => {
      expect(screen.getByTestId('four-col').getAttribute('data-layout-mode')).toBe('reading')
    })
    const detailW = Number(screen.getByTestId('detail-panel').getAttribute('data-default-size'))
    const rightW = Number(screen.getByTestId('right-panel').getAttribute('data-default-size'))
    // 内容:聊天 4:6（聊天更宽）—— final 阅读态，非旅程 tab
    expect(rightW).toBeGreaterThan(detailW)
    expect(detailW).toBe(34)
    expect(rightW).toBe(52)
    expect(mockUseDefaultLayout).toHaveBeenCalledWith(expect.objectContaining({
      id: 's3.fourPane.layout.v7:reading:demo',
    }))
  })

  it('旅程 tab：会话与旅程换位，会话默认宽=原旅程宽 34%', async () => {
    function JourneyHarness() {
      const [sel, setSel] = useState({ mode: 'view', viewKey: 'journey' })
      return (
        <ChiefSlotProvider>
          <FourPaneShell
            tree={tree}
            sel={sel}
            onSelectNode={(node) => {
              if (node?.type === 'view') setSel({ mode: 'view', viewKey: node.id.split(':')[1] })
              else if (!node) setSel({ mode: 'node', node: null })
              else setSel({ mode: 'node', node })
            }}
            work="demo"
            leftSeq={1}
            reload={() => {}}
          />
        </ChiefSlotProvider>
      )
    }
    render(<JourneyHarness />)
    await waitFor(() => {
      expect(screen.getByTestId('four-col').getAttribute('data-layout-mode')).toBe('reading')
    })
    expect(screen.getByTestId('four-col').getAttribute('data-journey-layout')).toBe('1')
    expect(screen.getByTestId('four-col').getAttribute('data-panel-order')).toBe('directory|detail|right')
    // view 隐藏目录 → 两栏份额归一；会话:旅程 ≈ 52:34，且详情 min 可拖（非 56）
    const detailW = Number(screen.getByTestId('detail-panel').getAttribute('data-default-size'))
    const rightW = Number(screen.getByTestId('right-panel').getAttribute('data-default-size'))
    const detailMin = Number(screen.getByTestId('detail-panel').getAttribute('data-min-size'))
    expect(rightW).toBeGreaterThan(detailW)
    expect(rightW / detailW).toBeCloseTo(52 / 34, 1)
    expect(detailMin).toBe(28)
    expect(detailMin).toBeLessThanOrEqual(detailW)
    expect(mockUseDefaultLayout).toHaveBeenCalledWith(expect.objectContaining({
      id: 's3.fourPane.layout.v7:journey-v4:demo',
    }))
  })
})
