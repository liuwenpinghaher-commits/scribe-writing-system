import '@testing-library/jest-dom/vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AtlasView } from '../views/AtlasView'
import { InsightView } from '../views/InsightView'
import { TimelineView } from '../views/TimelineView'

const apiMock = vi.hoisted(() => ({
  graph: vi.fn(),
  chapters: vi.fn(),
  timeline: vi.fn(),
  quality: vi.fn(),
  intent: vi.fn(),
  progress: vi.fn(),
  promisesLedger: vi.fn(),
}))

const sigmaMock = vi.hoisted(() => ({
  currentGraph: null,
  events: null,
}))

const timelineMock = vi.hoisted(() => ({
  instances: [],
}))

vi.mock('../api', () => ({ api: apiMock }))

vi.mock('recharts', () => ({
  AreaChart: ({ children }) => <div>{children}</div>,
  Area: () => <div />,
  BarChart: ({ children }) => <div>{children}</div>,
  Bar: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  Tooltip: () => <div />,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  CartesianGrid: () => <div />,
  ReferenceLine: () => <div />,
}))

vi.mock('@react-sigma/core', () => ({
  SigmaContainer: ({ children }) => <div data-testid="sigma-container">{children}</div>,
  useLoadGraph: () => (graph) => { sigmaMock.currentGraph = graph },
  useRegisterEvents: () => (events) => { sigmaMock.events = events },
  useSigma: () => ({
    getGraph: () => sigmaMock.currentGraph,
    getCamera: () => ({ animatedReset: vi.fn() }),
    graphToViewport: () => ({ x: 0, y: 0 }),
  }),
}))

vi.mock('vis-data/esnext', () => {
  class DataSet {
    constructor(items = []) {
      this.items = new Map()
      this.add(items)
    }

    add(items = []) {
      const rows = Array.isArray(items) ? items : [items]
      rows.forEach((it) => {
        if (it?.id != null) this.items.set(it.id, it)
      })
    }

    clear() {
      this.items.clear()
    }

    get(id) {
      if (id == null) return [...this.items.values()]
      return this.items.get(id)
    }
    update(rows = []) {
      const list = Array.isArray(rows) ? rows : [rows]
      list.forEach((it) => {
        if (it?.id == null) return
        const prev = this.items.get(it.id) || {}
        this.items.set(it.id, { ...prev, ...it })
      })
    }
  }
  return { DataSet }
})

vi.mock('vis-timeline/esnext', () => ({
  Timeline: function Timeline(_container, items) {
    const handlers = {}
    const instance = {
      on: (eventName, handler) => { handlers[eventName] = handler },
      setWindow: vi.fn(),
      getWindow: vi.fn(() => ({ start: new Date('2000-01-01'), end: new Date('2000-01-10') })),
      redraw: vi.fn(),
      destroy: vi.fn(),
      fit: vi.fn(),
      setSelection: vi.fn(),
      __handlers: handlers,
      __items: items,
    }
    timelineMock.instances.push(instance)
    return instance
  },
}))

const qualityPayload = {
  total_words: 1800,
  chapters: [
    { seq: 4, title: '井底夜审', word_count: 1800, qc_issues: 2, causal: 1 },
  ],
  foreshadow: { open: 0, closed: 0, overdue: 0 },
}

const progressPayload = {
  total_words: 1800,
  total_word_goal: 100000,
  daily_word_goal: 2000,
  today_words: 300,
  daily: [],
  current_streak: 0,
  longest_streak: 0,
  heatmap: [],
  weekday_histogram: [],
}

const graphPayload = {
  nodes: [
    { id: 'role:小翠', type: 'character', label: '小翠' },
    { id: 'fact:井底有骨', type: 'proposition', label: '井底有骨' },
  ],
  edges: [
    { src: 'role:小翠', dst: 'fact:井底有骨', rel: 'knows' },
  ],
}

const timelinePayload = {
  max_chapter: 5,
  items: [
    {
      id: 'ev-night',
      kind: 'event',
      chapter: 4,
      story_chapter: 4,
      label: '井底夜审',
      event_type: '对话',
      refs: { subj: ['role:小翠'] },
      lane_keys: ['role:小翠'],
    },
    {
      id: 'role:小翠->role:崔判@sc',
      kind: 'relation_start',
      chapter: 2,
      label: '同盟',
      refs: { src: 'role:小翠', dst: 'role:崔判', relation: 'ally' },
      lane_keys: ['role:小翠', 'role:崔判'],
    },
  ],
}

describe('横切视图真实组件对象回流', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sigmaMock.currentGraph = null
    sigmaMock.events = null
    timelineMock.instances = []
    apiMock.intent.mockResolvedValue({})
    apiMock.progress.mockResolvedValue(progressPayload)
    apiMock.promisesLedger.mockResolvedValue({ open: [], closed: [], red_herring: [] })
    apiMock.chapters.mockResolvedValue([{ seq: 5 }])
  })

  it('仪表盘弱章按钮发出可进入校验台账的 weak_chapter target', async () => {
    const onNavigateToObject = vi.fn()
    apiMock.quality.mockResolvedValue(qualityPayload)

    render(<InsightView onNavigateToObject={onNavigateToObject} />)

    fireEvent.click(await screen.findByRole('button', { name: /第4章 · 井底夜审/ }))

    expect(onNavigateToObject).toHaveBeenCalledWith(expect.objectContaining({
      type: 'weak_chapter',
      id: 'quality:4',
      chapter: 4,
      title: '第4章 · 井底夜审 · 弱章诊断',
      target_node: { id: 'ch:4', type: 'chapter', ref: 4, label: '第4章 · 井底夜审' },
    }))
    expect(screen.getByTestId('insight-next-stroke')).toBeTruthy()
    expect(screen.getByTestId('insight-charts')).toBeTruthy()
  })

  it('传入 chapter 时弱章钉当前章且呼吸默认该章', async () => {
    apiMock.quality.mockResolvedValue({
      total_words: 3000,
      chapters: [
        { seq: 3, title: '灯罩', word_count: 1200, qc_issues: 1, causal: 0 },
        { seq: 5, title: '尾', word_count: 1800, qc_issues: 9, causal: 0 },
      ],
      foreshadow: { open: 0, closed: 0, overdue: 0 },
    })
    render(<InsightView chapter={3} onNavigateToObject={vi.fn()} />)
    expect(await screen.findByText('当前章')).toBeTruthy()
    expect(screen.getByTestId('insight-discourse-seq')).toHaveValue(3)
    const buttons = screen.getAllByRole('button', { name: /第3章 · 灯罩|第5章 · 尾/ })
    expect(buttons[0].textContent).toMatch(/灯罩/)
  })

  it('图谱节点详情的打开设定发出设定库对象 target', async () => {
    const onNavigateToObject = vi.fn()
    apiMock.graph.mockResolvedValue(graphPayload)

    render(<AtlasView onNavigateToObject={onNavigateToObject} />)

    fireEvent.click(await screen.findByRole('button', { name: '打开设定 小翠' }))

    expect(onNavigateToObject).toHaveBeenCalledWith(expect.objectContaining({
      id: 'role:小翠',
      type: 'character',
      label: '小翠',
    }))
  })

  it('时间线事件详情发出手稿章 target', async () => {
    const onNavigateToObject = vi.fn()
    apiMock.timeline.mockResolvedValue(timelinePayload)

    render(<TimelineView onNavigateToObject={onNavigateToObject} />)

    await waitFor(() => expect(timelineMock.instances[0]?.__handlers.select).toBeTruthy())
    act(() => {
      timelineMock.instances[0].__handlers.select({ items: ['ev:ev-night:__event__'] })
    })
    fireEvent.click(await screen.findByRole('button', { name: /跳到第4章/ }))

    expect(onNavigateToObject).toHaveBeenCalledWith(expect.objectContaining({
      type: 'event',
      id: 'ev-night',
      label: '井底夜审',
      chapter: 4,
    }))
  })

  it('时间线关系详情发出设定库关系 target', async () => {
    const onNavigateToObject = vi.fn()
    apiMock.timeline.mockResolvedValue(timelinePayload)

    render(<TimelineView onNavigateToObject={onNavigateToObject} />)

    await waitFor(() => expect(timelineMock.instances[0]?.__handlers.select).toBeTruthy())
    act(() => {
      timelineMock.instances[0].__handlers.select({ items: ['rel:role:小翠->role:崔判@sc:__relation__'] })
    })
    fireEvent.click(await screen.findByRole('button', { name: /跳到第2章/ }))

    expect(onNavigateToObject).toHaveBeenCalledWith(expect.objectContaining({
      type: 'relation',
      id: 'role:小翠->role:崔判@sc',
      label: '同盟',
      chapter: 2,
    }))
  })

  it('列表点选留在时间线并开抽屉，轴仍在', async () => {
    const onNavigateToObject = vi.fn()
    apiMock.timeline.mockResolvedValue(timelinePayload)

    render(<TimelineView onNavigateToObject={onNavigateToObject} />)

    fireEvent.click(await screen.findByRole('button', { name: '井底夜审' }))

    expect(onNavigateToObject).not.toHaveBeenCalled()
    expect(screen.getByTestId('timeline-view')).toBeTruthy()
    expect(screen.getByTestId('timeline-canvas')).toBeTruthy()
    expect(screen.getByTestId('timeline-detail')).toBeTruthy()
    expect(screen.getByTestId('timeline-next-stroke')).toBeTruthy()
  })

  it('传入 chapter 时首屏围着该章，不是书末 50 章', async () => {
    apiMock.timeline.mockResolvedValue({ max_chapter: 80, items: [] })
    render(<TimelineView chapter={3} onNavigateToObject={vi.fn()} />)
    await waitFor(() => expect(apiMock.timeline).toHaveBeenCalled())
    expect(apiMock.timeline).toHaveBeenCalledWith(1, 8, 'story', 800)
    expect(apiMock.timeline.mock.calls.some((args) => args[0] === 1 && args[1] === 1)).toBe(false)
  })

  it('全书无条目时说还没有事件', async () => {
    apiMock.timeline.mockResolvedValue({ max_chapter: 0, items: [] })
    render(<TimelineView onNavigateToObject={vi.fn()} />)
    expect(await screen.findByText('还没有事件')).toBeTruthy()
    expect(screen.getByTestId('timeline-canvas')).toBeTruthy()
  })

  it('有条目但画不出时说这窗里是空的', async () => {
    apiMock.timeline.mockResolvedValue({
      max_chapter: 5,
      items: [{ id: 'pay-1', kind: 'promise_payoff', chapter: 5, label: '已收' }],
    })
    render(<TimelineView onNavigateToObject={vi.fn()} />)
    expect(await screen.findByText('这窗里是空的')).toBeTruthy()
  })
})
