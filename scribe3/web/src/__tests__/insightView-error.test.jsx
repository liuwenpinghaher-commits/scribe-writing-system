import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InsightView } from '../views/InsightView'

const apiMock = vi.hoisted(() => ({
  quality: vi.fn(),
  intent: vi.fn(),
  progress: vi.fn(),
  promisesLedger: vi.fn(),
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

describe('InsightView 错误态', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.intent.mockResolvedValue({})
    apiMock.progress.mockResolvedValue(progressPayload)
    apiMock.promisesLedger.mockResolvedValue(null)
  })

  it('质量接口失败时显示错误和重试', async () => {
    apiMock.quality
      .mockRejectedValueOnce(new Error('quality down'))
      .mockResolvedValueOnce(qualityPayload)

    render(<InsightView />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/质量仪表盘加载失败/)
    fireEvent.click(screen.getByRole('button', { name: /重试/ }))

    await waitFor(() => expect(apiMock.quality).toHaveBeenCalledTimes(2))
    expect(await screen.findByRole('heading', { name: '仪表盘' })).toBeTruthy()
  })

  it('进度接口失败时显示错误和重试', async () => {
    apiMock.quality.mockResolvedValue(qualityPayload)
    apiMock.progress
      .mockRejectedValueOnce(new Error('progress down'))
      .mockResolvedValueOnce(progressPayload)

    render(<InsightView />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/进度数据加载失败/)
    fireEvent.click(screen.getByRole('button', { name: /重试/ }))

    await waitFor(() => expect(apiMock.progress).toHaveBeenCalledTimes(2))
    expect(await screen.findByText(/今日码字/)).toBeTruthy()
  })
})
