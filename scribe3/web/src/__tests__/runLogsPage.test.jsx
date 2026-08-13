import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RunLogsPage } from '../admin/RunLogsPage'

const apiMock = vi.hoisted(() => ({
  adminWorks: vi.fn(),
  works: vi.fn(),
  getWork: vi.fn(),
  runCards: vi.fn(),
  runCard: vi.fn(),
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
    apiMock.runCards.mockResolvedValue({
      ok: true,
      count: 1,
      items: [{
        run_id: 'abc123',
        kind: 'write',
        chapter: 3,
        verdict: 'red',
        summary: { red: 2, green: 10 },
        created_at: '2026-08-13T10:00:00Z',
      }],
    })
    apiMock.runCard.mockResolvedValue({
      run_id: 'abc123',
      kind: 'write',
      chapter: 3,
      verdict: 'red',
      created_at: '2026-08-13T10:00:00Z',
      prompt_hard_profile: 'novel_96k',
      quality_flags: ['empty_required'],
      rows: [
        {
          name: 'story_causal',
          tier: 'L2',
          expected: true,
          actual: 'empty',
          actual_reason: 'empty_story_causal',
          chars: 0,
          verdict: 'red',
          quality: {},
        },
        {
          name: 'narrative_contract',
          tier: 'L0',
          expected: true,
          actual: 'present',
          chars: 400,
          verdict: 'green',
          quality: {},
        },
      ],
    })
  })

  it('独立页列出卡片，点进明细只看红行', async () => {
    render(<RunLogsPage />)
    expect(await screen.findByTestId('run-logs-page')).toBeTruthy()
    expect(screen.getByText('写路径日志')).toBeTruthy()
    await waitFor(() => expect(apiMock.runCards).toHaveBeenCalled())
    expect(apiMock.runCards.mock.calls[0][1]).toBe('book_qe_live5')
    fireEvent.click(screen.getByTestId('run-logs-row'))
    await waitFor(() => expect(apiMock.runCard).toHaveBeenCalledWith('abc123', 'book_qe_live5'))
    expect(screen.getByText('前因后果')).toBeTruthy()
    expect(screen.queryByText('场面合同')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '全部步骤' }))
    expect(screen.getByText('场面合同')).toBeTruthy()
    expect(screen.queryByText(/该进未进的提示词/)).toBeNull()
  })
})
