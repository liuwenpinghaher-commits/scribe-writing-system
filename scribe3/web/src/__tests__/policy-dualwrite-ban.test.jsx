import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BriefPanel } from '../BriefPanel.jsx'
import { seedChiefCodexWrite } from '../lib/chiefSeed.js'
import { ChapterCard } from '../ChapterCard.jsx'
import { InsightView } from '../views/InsightView.jsx'

const apiMock = vi.hoisted(() => ({
  chapterBrief: vi.fn(),
  promises: vi.fn(),
  advancePromise: vi.fn(),
  markHerring: vi.fn(),
  editPromise: vi.fn(),
  editChar: vi.fn(),
  putIntent: vi.fn(),
  patchChapter: vi.fn(),
  patchVolume: vi.fn(),
  quality: vi.fn(),
  intent: vi.fn(),
  progress: vi.fn(),
  promisesLedger: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../ui/Toast', () => ({ showToast: vi.fn() }))
vi.mock('../selectionContext', () => ({
  useSelection: () => ({ setFocus: vi.fn(), suppressNextMirror: vi.fn() }),
}))
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
// ChapterCard dnd-kit sortable no-op
vi.mock('@dnd-kit/sortable', () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: () => {},
    transform: null,
    transition: null,
    isDragging: false,
  }),
}))
vi.mock('@dnd-kit/utilities', () => ({ CSS: { Transform: { toString: () => '' } } }))

describe('policy dual-write ban surfaces', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('BriefPanel overdue decisions seed chief and never call promise mutate APIs', async () => {
    apiMock.chapterBrief.mockResolvedValue({ sections: { promises: {}, arcs: [], loops: {}, heartbeat: [], injection: {} } })
    apiMock.promises.mockResolvedValue([
      { id: 'promise:1', text: '炉认主', overdue: true, status: 'open', tier: 'chapter' },
    ])
    const seeds = []
    const tabs = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))

    render(<BriefPanel seq={3} />)
    expect(await screen.findByTestId('brief-promise-decision')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '让主编兑现' }))
    expect(seeds.length).toBeGreaterThan(0)
    expect(tabs).toContain('chief')
    expect(apiMock.advancePromise).not.toHaveBeenCalled()
    expect(apiMock.markHerring).not.toHaveBeenCalled()
    expect(apiMock.editPromise).not.toHaveBeenCalled()
  })

  it('InsightView open-promise controls seed chief and never call advance/markHerring/editPromise', async () => {
    apiMock.quality.mockResolvedValue({
      total_words: 100,
      chapters: [],
      foreshadow: { open: 1, closed: 0, overdue: 0 },
    })
    apiMock.intent.mockResolvedValue({})
    apiMock.progress.mockResolvedValue({
      total_words: 100, total_word_goal: 100000, daily_word_goal: 2000, today_words: 10,
      daily: [], current_streak: 0, longest_streak: 0, heatmap: [], weekday_histogram: [],
    })
    apiMock.promisesLedger.mockResolvedValue({
      threshold: 5,
      max_chapter: 10,
      open: [{ id: 'promise:open1', text: '炉认主未收', status: 'open', setup_chapter: 2, overdue: true }],
      closed: [],
      red_herring: [],
      audit: { balanced: true, overdue_count: 1 },
    })

    const seeds = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))

    render(<InsightView />)
    expect(await screen.findByTestId('insight-promise-card')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '让主编回收' }))
    await waitFor(() => expect(seeds.length).toBeGreaterThan(0))
    expect(seeds[0]).toMatch(/回收|兑现|伏笔/)

    fireEvent.click(screen.getByRole('button', { name: '让主编标障眼法' }))
    await waitFor(() => expect(seeds.length).toBeGreaterThanOrEqual(2))

    expect(apiMock.advancePromise).not.toHaveBeenCalled()
    expect(apiMock.markHerring).not.toHaveBeenCalled()
    expect(apiMock.editPromise).not.toHaveBeenCalled()
  })

  it('ChapterCard synopsis CTA seeds chief without form edit', async () => {
    const seeds = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    render(
      <ChapterCard
        chapter={{ seq: 2, title: '借命契', synopsis: '立约', word_count: 100, label: 'draft' }}
        colorMode="status"
      />,
    )
    fireEvent.click(screen.getByTestId('chapter-card-synopsis-seed'))
    expect(seeds[0]).toMatch(/第 2 章|synopsis|立约/)
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('seedChiefCodexWrite is the shipped focus contract used by codex CTAs', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    seedChiefCodexWrite('promises', { id: 'p1', text: 'x' }, '回收')
    expect(tabs).toEqual(['chief'])
  })
})
