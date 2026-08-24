import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SynopsisView, OverviewView } from './SynopsisView'

const apiMock = vi.hoisted(() => ({
  quality: vi.fn(),
  get: vi.fn(),
  promisesLedger: vi.fn(),
  workflowSnapshot: vi.fn(),
  outline: vi.fn(),
  intent: vi.fn(),
  northStarBook: vi.fn(),
  northStarChapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

const qualityOk = {
  total_words: 1200,
  chapters: [{ seq: 1, title: '开篇', word_count: 1200, qc_issues: 2, causal: 1 }],
  foreshadow: { open: 1, closed: 0, overdue: 0 },
}

const completenessOk = {
  completeness_score: 80,
  total_chars: 3,
  total_rules: 1,
  total_factions: 0,
  total_places: 2,
  total_facts: 4,
  missing_dimensions: [],
}

const ledgerOk = {
  open: [{ id: 'p1' }],
  closed: [],
  red_herring: [],
  audit: { balanced: false, overdue_count: 0, never_paid: 0 },
}

const snapOk = {
  journey: {
    stations: [
      { id: 'intent', label: '立项', status: 'done' },
      { id: 'world', label: '世界底座', status: 'current' },
      { id: 'structure', label: '结构', status: 'todo' },
      { id: 'serialize', label: '连载推进', status: 'todo' },
      { id: 'ledger', label: '账本健康', status: 'todo' },
    ],
  },
  bible_motif_gap: {
    ok: false,
    count: 1,
    min_required: 3,
    deficit: 2,
    names: ['灯与债'],
  },
}

const outlineOk = {
  volumes: [{ id: 'vol-1', title: '第一卷', intro: '华山那一夜' }],
  chapters: [
    { seq: 1, title: '华山成核', volume: 'vol-1', synopsis: '按碎片' },
    { seq: 2, title: '四十二度', volume: 'vol-1', synopsis: '' },
  ],
}

function mockLightOk() {
  apiMock.quality.mockResolvedValue(qualityOk)
  apiMock.get.mockResolvedValue(completenessOk)
  apiMock.promisesLedger.mockResolvedValue(ledgerOk)
  apiMock.workflowSnapshot.mockResolvedValue(snapOk)
  apiMock.outline.mockResolvedValue(outlineOk)
  apiMock.intent.mockResolvedValue({
    reader_feeling: '压抑中见微光',
    emotional_arc: '由怯到决',
    red_lines: '不写超自然',
  })
  apiMock.northStarBook.mockResolvedValue({
    tension: { findings: [] },
    promise_recovery: { rate: 0.5, open: 1, payoff: 1, overdue: 0 },
    contradiction_density: { per_10k: 0 },
    fulfillment: { rate: 1, carried_backlog: 0, waived: 0 },
    causal_debt_total: 0,
  })
}

describe('SynopsisView 总纲', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLightOk()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('标题是总纲，并内嵌作品意图', async () => {
    render(<SynopsisView />)
    expect(await screen.findByTestId('synopsis-view')).toBeTruthy()
    expect(screen.getByRole('heading', { name: '总纲' })).toBeTruthy()
    expect(await screen.findByTestId('northstar-bar')).toBeTruthy()
    expect(screen.getByText('作品意图')).toBeTruthy()
    expect(await screen.findByText(/压抑中见微光/)).toBeTruthy()
  })

  it('OverviewView 别名渲同一页', async () => {
    render(<OverviewView />)
    expect(await screen.findByTestId('synopsis-view')).toBeTruthy()
    expect(screen.getByRole('heading', { name: '总纲' })).toBeTruthy()
  })

  it('单块失败不挡住整页', async () => {
    apiMock.quality.mockRejectedValue(new Error('quality down'))
    apiMock.outline.mockRejectedValue(new Error('outline down'))
    render(<SynopsisView />)
    expect(await screen.findByTestId('northstar-bar')).toBeTruthy()
    expect(await screen.findByText('暂时读不到规模，不影响其他块')).toBeTruthy()
    expect(screen.getByText('暂时读不到卷纲，不影响其他块')).toBeTruthy()
    expect(screen.getByText('世界底座')).toBeTruthy()
    expect(screen.getByText('灯与债')).toBeTruthy()
  })

  it('首屏不请求书级评分卡；展开才请求', async () => {
    render(<SynopsisView />)
    await screen.findByTestId('synopsis-scorecard-toggle')
    expect(apiMock.northStarBook).not.toHaveBeenCalled()
    expect(screen.queryByTestId('scorecard-panel')).toBeNull()

    fireEvent.click(screen.getByTestId('synopsis-scorecard-toggle'))
    expect(await screen.findByTestId('synopsis-scorecard-body')).toBeTruthy()
    await waitFor(() => expect(apiMock.northStarBook).toHaveBeenCalledTimes(1))
    expect(apiMock.northStarChapter).not.toHaveBeenCalled()
  })

  it('点五站跳到旅程', async () => {
    const onOpenView = vi.fn()
    render(<SynopsisView onOpenView={onOpenView} />)
    fireEvent.click(await screen.findByRole('button', { name: '世界底座' }))
    expect(onOpenView).toHaveBeenCalledWith('journey')
  })

  it('点章摘要跳章', async () => {
    const onJumpChapter = vi.fn()
    render(<SynopsisView onJumpChapter={onJumpChapter} />)
    fireEvent.click(await screen.findByRole('button', { name: /华山成核/ }))
    expect(onJumpChapter).toHaveBeenCalledWith(1)
  })

  it('s3-live 300ms 后刷新轻量块，不拉评分卡', async () => {
    render(<SynopsisView />)
    await screen.findByText('世界底座')
    const calls = apiMock.quality.mock.calls.length
    vi.useFakeTimers()
    act(() => {
      window.dispatchEvent(new CustomEvent('s3-live', { detail: { table: 'chapter' } }))
    })
    expect(apiMock.quality.mock.calls.length).toBe(calls)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300)
    })
    expect(apiMock.quality.mock.calls.length).toBeGreaterThan(calls)
    expect(apiMock.northStarBook).not.toHaveBeenCalled()
    vi.useRealTimers()
  })
})
