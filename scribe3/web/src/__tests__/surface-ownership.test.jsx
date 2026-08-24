import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InsightView } from '../views/InsightView'
import { JourneyView } from '../views/JourneyView'

const apiMock = vi.hoisted(() => ({
  quality: vi.fn(),
  intent: vi.fn(),
  progress: vi.fn(),
  promisesLedger: vi.fn(),
  workflowSnapshot: vi.fn(),
  storylineHub: vi.fn(),
  storylineGantt: vi.fn(),
  storylineEmotion: vi.fn(),
  storylineLines: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('recharts', () => ({
  AreaChart: ({ children }) => <div>{children}</div>,
  Area: () => <div />,
  BarChart: ({ children }) => <div>{children}</div>,
  Bar: () => <div />,
  LineChart: ({ children }) => <div>{children}</div>,
  Line: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  Tooltip: () => <div />,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  CartesianGrid: () => <div />,
  ReferenceLine: () => <div />,
}))

const qualityPayload = {
  total_words: 1200,
  chapters: [{ seq: 1, title: '开篇', word_count: 1200, qc_issues: 0, causal: 0 }],
  foreshadow: { open: 0, closed: 0, overdue: 0 },
}

const progressPayload = {
  total_words: 1200,
  total_word_goal: 100000,
  daily_word_goal: 2000,
  today_words: 300,
  daily: [],
  current_streak: 0,
  longest_streak: 0,
  heatmap: [],
  weekday_histogram: [],
}

describe('作者面去重叠', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.intent.mockResolvedValue({})
    apiMock.progress.mockResolvedValue(progressPayload)
    apiMock.promisesLedger.mockResolvedValue({ open: [], closed: [], red_herring: [] })
    apiMock.quality.mockResolvedValue(qualityPayload)
    apiMock.workflowSnapshot.mockResolvedValue({
      journey: { stations: [] },
      chapter_lane: { seq: 1, title: '开篇' },
      next_step: { title: '写第 1 章' },
      blockers: [],
    })
    apiMock.storylineHub.mockResolvedValue({
      gantt: { rows: [] },
      emotion: { points: [] },
      storylines: [],
    })
  })

  it('仪表盘不再嵌跨章弧，副标题不含规划看板', async () => {
    render(<InsightView />)
    expect(await screen.findByRole('heading', { name: '仪表盘' })).toBeTruthy()
    expect(screen.getByText(/质量 · 伏笔 · 码字/)).toBeTruthy()
    expect(screen.queryByTestId('storyline-hub')).toBeNull()
    expect(screen.queryByTestId('insight-planning-section')).toBeNull()
    expect(screen.queryByText('规划看板 · 跨章弧')).toBeNull()
    expect(screen.queryByText('全局规划')).toBeNull()
  })

  it('旅程底部挂跨章弧参考，不叫全局规划', async () => {
    render(<JourneyView work="demo" />)
    expect(await screen.findByTestId('journey-view')).toBeTruthy()
    expect(screen.getByTestId('journey-arcs')).toBeTruthy()
    expect(screen.getByText('跨章弧（参考）')).toBeTruthy()
    expect(screen.queryByTestId('storyline-hub')).toBeNull()
    fireEvent.click(screen.getByTestId('journey-arcs-toggle'))
    await waitFor(() => expect(screen.getByTestId('storyline-hub')).toBeTruthy())
    expect(screen.queryByText('全局规划')).toBeNull()
    expect(screen.queryByText('规划看板 · 跨章弧')).toBeNull()
  })
})
