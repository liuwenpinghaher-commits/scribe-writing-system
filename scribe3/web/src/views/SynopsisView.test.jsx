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

const outlineOk = {
  volumes: [{ id: 'vol-1', title: '第一卷', intro: '华山那一夜' }],
  chapters: [
    { seq: 1, title: '华山成核', volume: 'vol-1', settled_note: '成核落下', synopsis: '按碎片' },
    { seq: 2, title: '四十二度', volume: 'vol-1', synopsis: '' },
  ],
}

function mockLightOk() {
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

  it('标题是总纲，副标题是读书，并内嵌作品意图', async () => {
    render(<SynopsisView />)
    expect(await screen.findByTestId('synopsis-view')).toBeTruthy()
    expect(screen.getByRole('heading', { name: '总纲' })).toBeTruthy()
    expect(screen.getByText(/当一本书来读/)).toBeTruthy()
    expect(await screen.findByTestId('northstar-bar')).toBeTruthy()
    expect(screen.getByText('作品意图')).toBeTruthy()
    expect(await screen.findByText(/压抑中见微光/)).toBeTruthy()
  })

  it('OverviewView 别名渲同一页', async () => {
    render(<OverviewView />)
    expect(await screen.findByTestId('synopsis-view')).toBeTruthy()
    expect(screen.getByRole('heading', { name: '总纲' })).toBeTruthy()
  })

  it('没有五站、规模四格、完整度、契诃夫和工程跳转', async () => {
    render(<SynopsisView />)
    await screen.findByTestId('synopsis-progress-line')
    expect(screen.queryByTestId('synopsis-stations')).toBeNull()
    expect(screen.queryByTestId('synopsis-scale')).toBeNull()
    expect(screen.queryByTestId('synopsis-codex')).toBeNull()
    expect(screen.queryByTestId('synopsis-weak')).toBeNull()
    expect(screen.queryByText('世界底座')).toBeNull()
    expect(screen.queryByText('Benchmark 库')).toBeNull()
    expect(screen.queryByText(/契诃夫/)).toBeNull()
    expect(screen.queryByText(/完整度/)).toBeNull()
  })

  it('第一屏不打 snapshot / quality / completeness', async () => {
    render(<SynopsisView />)
    await screen.findByTestId('synopsis-progress-line')
    expect(apiMock.workflowSnapshot).not.toHaveBeenCalled()
    expect(apiMock.quality).not.toHaveBeenCalled()
    expect(apiMock.get).not.toHaveBeenCalled()
    expect(apiMock.promisesLedger).not.toHaveBeenCalled()
  })

  it('无正文进度行用立到；弱链去旅程；整行不是按钮', async () => {
    const onOpenView = vi.fn()
    render(<SynopsisView onOpenView={onOpenView} />)
    const line = await screen.findByTestId('synopsis-progress-line')
    expect(line.textContent).toMatch(/立到第 1 章《华山成核》/)
    expect(line.textContent).toMatch(/还没有正文/)
    expect(line.tagName).not.toBe('BUTTON')
    fireEvent.click(screen.getByTestId('synopsis-open-journey'))
    expect(onOpenView).toHaveBeenCalledWith('journey')
  })

  it('章一句优先 settled_note', async () => {
    render(<SynopsisView />)
    expect(await screen.findByText('成核落下')).toBeTruthy()
    expect(screen.getByText('还没写这一句')).toBeTruthy()
  })

  it('空书最小文案', async () => {
    apiMock.outline.mockResolvedValue({ volumes: [], chapters: [] })
    render(<SynopsisView />)
    expect(await screen.findByText('还没有章。')).toBeTruthy()
  })

  it('单块失败不挡住整页', async () => {
    apiMock.outline.mockRejectedValue(new Error('outline down'))
    render(<SynopsisView />)
    expect(await screen.findByTestId('northstar-bar')).toBeTruthy()
    expect(await screen.findByText('暂时读不到卷纲，不影响其他块')).toBeTruthy()
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

  it('点章摘要跳章', async () => {
    const onJumpChapter = vi.fn()
    render(<SynopsisView onJumpChapter={onJumpChapter} />)
    fireEvent.click(await screen.findByRole('button', { name: /华山成核/ }))
    expect(onJumpChapter).toHaveBeenCalledWith(1)
  })

  it('s3-live 300ms 后刷新 outline，不拉评分卡和 snapshot', async () => {
    render(<SynopsisView />)
    await screen.findByTestId('synopsis-progress-line')
    const calls = apiMock.outline.mock.calls.length
    vi.useFakeTimers()
    act(() => {
      window.dispatchEvent(new CustomEvent('s3-live', { detail: { table: 'chapter' } }))
    })
    expect(apiMock.outline.mock.calls.length).toBe(calls)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300)
    })
    expect(apiMock.outline.mock.calls.length).toBeGreaterThan(calls)
    expect(apiMock.northStarBook).not.toHaveBeenCalled()
    expect(apiMock.quality).not.toHaveBeenCalled()
    expect(apiMock.workflowSnapshot).not.toHaveBeenCalled()
    vi.useRealTimers()
  })
})
