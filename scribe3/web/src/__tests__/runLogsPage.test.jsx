import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RunLogsPage } from '../admin/RunLogsPage'

const apiMock = vi.hoisted(() => ({
  adminWorks: vi.fn(),
  works: vi.fn(),
  getWork: vi.fn(),
  runCards: vi.fn(),
  runCard: vi.fn(),
  pipelineTraces: vi.fn(),
  pipelineTrace: vi.fn(),
  pipelineSpans: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('管理台写路径日志页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.getWork.mockReturnValue('book_qe_live5')
    apiMock.adminWorks.mockResolvedValue({
      items: [{ slug: 'book_qe_live5', title: '乱世铜炉' }],
      total: 1,
    })
    apiMock.pipelineTraces.mockResolvedValue({
      ok: true,
      count: 1,
      items: [{
        trace_id: 'abc123',
        kind: 'write',
        chapter: 3,
        status: 'ok',
        headline: '上章余烬（empty_story_ember）',
        started_at: '2026-08-13T10:00:00Z',
        duration_ms: 12800,
        span_count: 12,
        red_count: 1,
      }],
    })
    apiMock.pipelineTrace.mockResolvedValue({
      trace_id: 'abc123',
      kind: 'write',
      chapter: 3,
      status: 'ok',
      headline: '上章余烬（empty_story_ember）',
      spans: [
        {
          span_id: 's1',
          step_key: 'assemble.seg.story_ember',
          step_title: '上章余烬',
          layer: 'assemble',
          status: 'empty',
          expected: true,
          actual: 'empty',
          verdict: 'red',
          input: { source: 'end_hook' },
          compute: { fn: 'collect_story_fuel_segments' },
          output: { chars: 0 },
          timing: { duration_ms: 2 },
        },
        {
          span_id: 's2',
          step_key: 'assemble.seg.narrative_contract',
          step_title: '场面合同',
          layer: 'assemble',
          status: 'ok',
          expected: true,
          actual: 'present',
          verdict: 'green',
          input: { source: 'contract' },
          compute: { fn: 'format_story_contract_head' },
          output: { chars: 400 },
          timing: { duration_ms: 1 },
        },
      ],
    })
  })

  it('独立页默认时间线，点进明细看全步字段', async () => {
    render(<RunLogsPage />)
    expect(await screen.findByTestId('run-logs-page')).toBeTruthy()
    expect(screen.getByText('运行链路')).toBeTruthy()
    await waitFor(() => expect(apiMock.pipelineTraces).toHaveBeenCalled())
    expect(apiMock.pipelineTraces.mock.calls[0][1]).toBe('book_qe_live5')
    fireEvent.click(screen.getByTestId('run-logs-row'))
    await waitFor(() => expect(apiMock.pipelineTrace).toHaveBeenCalledWith('abc123', 'book_qe_live5'))
    expect(screen.getByTestId('run-logs-spans')).toBeTruthy()
    expect(screen.getByText('上章余烬')).toBeTruthy()
    expect(screen.getByText('场面合同')).toBeTruthy()
    fireEvent.click(screen.getAllByText('上章余烬')[0])
    expect(screen.getByTestId('run-logs-inspector')).toBeTruthy()
    expect(screen.getByText(/collect_story_fuel_segments/)).toBeTruthy()
  })
})
