import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AtlasView } from '../views/AtlasView'
import { InsightView } from '../views/InsightView'
import { TimelineView } from '../views/TimelineView'

// 全局(Canvas/WebGL)视图旁必须有键盘/读屏可达的命名列表或文本摘要(role=region)。
// 数据源全部 mock,断言各视图渲染出与画布同源数据的等价区域。

const apiMock = vi.hoisted(() => ({
  graph: vi.fn(),
  chapters: vi.fn(),
  timeline: vi.fn(),
  quality: vi.fn(),
  intent: vi.fn(),
  progress: vi.fn(),
  promisesLedger: vi.fn(),
}))

const sigmaMock = vi.hoisted(() => ({ currentGraph: null, events: null }))
const timelineMock = vi.hoisted(() => ({ instances: [] }))

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
    constructor(items = []) { this.items = new Map(); this.add(items) }
    add(items = []) {
      const rows = Array.isArray(items) ? items : [items]
      rows.forEach((it) => { if (it?.id != null) this.items.set(it.id, it) })
    }
    clear() { this.items.clear() }
    get(id) { return id == null ? [...this.items.values()] : this.items.get(id) }
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
      setWindow: vi.fn(), getWindow: vi.fn(() => ({ start: new Date('2000-01-01'), end: new Date('2000-01-10') })),
      redraw: vi.fn(), destroy: vi.fn(),
      fit: vi.fn(), setSelection: vi.fn(),
      __handlers: handlers, __items: items,
    }
    timelineMock.instances.push(instance)
    return instance
  },
}))

const graphPayload = {
  nodes: [
    { id: 'role:小翠', type: 'character', label: '小翠' },
    { id: 'fact:井底有骨', type: 'proposition', label: '井底有骨' },
  ],
  edges: [{ src: 'role:小翠', dst: 'fact:井底有骨', rel: 'knows' }],
}

const timelinePayload = {
  max_chapter: 5,
  items: [
    { id: 'ev-night', kind: 'event', chapter: 4, story_chapter: 4, label: '井底夜审', event_type: '对话', refs: { subj: ['role:小翠'] }, lane_keys: ['role:小翠'] },
    { id: 'role:小翠->role:崔判@sc', kind: 'relation_start', chapter: 2, label: '同盟', refs: { src: 'role:小翠', dst: 'role:崔判', relation: 'ally' }, lane_keys: ['role:小翠', 'role:崔判'] },
  ],
}

const qualityPayload = {
  total_words: 1800,
  chapters: [{ seq: 4, title: '井底夜审', word_count: 1800, qc_issues: 2, causal: 1 }],
  foreshadow: { open: 0, closed: 0, overdue: 0 },
}

const progressPayload = {
  total_words: 1800, total_word_goal: 100000, daily_word_goal: 2000, today_words: 300,
  daily: [], current_streak: 0, longest_streak: 0, heatmap: [], weekday_histogram: [],
}

describe('全局视图键盘等价路径', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sigmaMock.currentGraph = null
    sigmaMock.events = null
    timelineMock.instances = []
    apiMock.graph.mockResolvedValue(graphPayload)
    apiMock.chapters.mockResolvedValue([{ seq: 5 }])
    apiMock.timeline.mockResolvedValue(timelinePayload)
    apiMock.quality.mockResolvedValue(qualityPayload)
    apiMock.intent.mockResolvedValue({})
    apiMock.progress.mockResolvedValue(progressPayload)
    apiMock.promisesLedger.mockResolvedValue({ open: [], closed: [], red_herring: [], audit: {} })
  })

  it.each([
    ['图谱对象列表', () => <AtlasView onNavigateToObject={vi.fn()} />],
    ['时间线事件列表', () => <TimelineView onNavigateToObject={vi.fn()} />],
    ['洞察数据摘要', () => <InsightView onNavigateToObject={vi.fn()} />],
  ])('画布旁暴露 %s 区域', async (name, view) => {
    render(view())
    expect(await screen.findByRole('region', { name })).toBeInTheDocument()
  })
})
