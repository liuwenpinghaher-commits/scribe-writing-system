import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QualityReview } from './QualityReview'

const apiMock = vi.hoisted(() => ({
  qualityEvaluation: vi.fn(),
  qualityAuthorJudgment: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

const DIMENSIONS = [
  '连贯性与因果', '人物真实性', '场景必要性', '结构与节奏', '悬念与兑现',
  '情绪效力', '阅读体验', '语言与声音', '主题与潜台词', '原创性',
]

function evaluation({ withAuthor = false, conflicted = false } = {}) {
  return {
    chapter_version_id: 'chapter_version:abc',
    chapter: 7,
    dimensions: DIMENSIONS.map((label, i) => ({
      dimension: label,
      state: 'evaluable',
      system: { score: 3, effect: '稳', mechanism: '机制' + i, evidence: [{ quote: '原文证据', start_utf16: 0, end_utf16: 4 }], confidence: 0.8 },
      reference: { score: 4, mode: 'close' },
      author: withAuthor ? { score: 4 } : null,
      decision_index: withAuthor ? 3.6 : null,
      conflicted: conflicted && i === 0,
    })),
    status: 'ready',
  }
}

describe('QualityReview 十维三轴审阅', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.qualityEvaluation.mockResolvedValue(evaluation())
    apiMock.qualityAuthorJudgment.mockResolvedValue({ ok: true })
  })

  it('渲染全部十个维度标签', async () => {
    render(<QualityReview work="demo" seq={7} />)
    for (const label of DIMENSIONS) {
      expect(await screen.findByText(label)).toBeTruthy()
    }
  })

  it('显示系统判断分数与证据', async () => {
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    expect(screen.getAllByText('原文证据').length).toBeGreaterThan(0)
  })

  it('作者未评分时不显示决策指数', async () => {
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    expect(screen.queryByText(/决策指数/)).toBeNull()
  })

  it('三轴齐全时显示同维度决策指数', async () => {
    apiMock.qualityEvaluation.mockResolvedValue(evaluation({ withAuthor: true }))
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    expect(screen.getAllByText(/决策指数/).length).toBeGreaterThan(0)
  })

  it('绝不显示小说总分', async () => {
    apiMock.qualityEvaluation.mockResolvedValue(evaluation({ withAuthor: true }))
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    expect(screen.queryByText(/总分/)).toBeNull()
    expect(screen.queryByText(/total/i)).toBeNull()
  })

  it('作者评分提交后重新读取服务器三轴', async () => {
    apiMock.qualityEvaluation.mockResolvedValue(evaluation({ withAuthor: true }))
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    const inputs = screen.getAllByRole('spinbutton')
    fireEvent.change(inputs[0], { target: { value: '5' } })
    fireEvent.blur(inputs[0])
    expect(apiMock.qualityAuthorJudgment).toHaveBeenCalled()
    await waitFor(() => expect(apiMock.qualityEvaluation.mock.calls.length).toBeGreaterThan(1))
  })

  it('证据点击回指章与 UTF-16 范围', async () => {
    const onLocate = vi.fn()
    render(<QualityReview work="demo" seq={7} onLocateEvidence={onLocate} />)
    await screen.findByText('连贯性与因果')
    fireEvent.click(screen.getAllByText('原文证据')[0])
    expect(onLocate).toHaveBeenCalledWith(expect.objectContaining({
      chapter: 7,
      start_utf16: 0,
      end_utf16: 4,
    }))
  })

  it('conflicted 维度有明确分歧标记', async () => {
    apiMock.qualityEvaluation.mockResolvedValue(evaluation({ withAuthor: true, conflicted: true }))
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    expect(screen.getAllByText(/分歧/).length).toBeGreaterThan(0)
  })

  it('加载失败显示错误态与重试', async () => {
    apiMock.qualityEvaluation.mockRejectedValue(new Error('boom'))
    render(<QualityReview work="demo" seq={7} />)
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByRole('button', { name: '重试' })).toBeTruthy()
  })

  it('用户字段带稳定 data-field-path', async () => {
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    const fields = document.querySelectorAll('[data-field-path]')
    expect(fields.length).toBeGreaterThan(0)
  })
})
