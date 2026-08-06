import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QualityReview } from './QualityReview'

const apiMock = vi.hoisted(() => ({
  qualityEvaluation: vi.fn(),
  qualityAuthorJudgment: vi.fn(),
  qualityCreateSnapshot: vi.fn(),
  qualityRetryJob: vi.fn(),
  approvedReferenceFingerprints: vi.fn(),
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
      system: { score: 3, effect: '稳', mechanism: '机制' + i, evidence: [{ chapter_version_id: 'chapter_version:abc', quote: '原文证据', start_utf16: 0, end_utf16: 4, content_hash: 'a'.repeat(64) }], confidence: 0.8 },
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
    apiMock.qualityCreateSnapshot.mockResolvedValue(evaluation())
    apiMock.approvedReferenceFingerprints.mockResolvedValue([
      {
        fingerprint_id: 'fp-a', reference_work_id: 'rw-a', title: '标尺A', revision: 2,
        full_book_fingerprint: '冷硬', transferable_mechanisms_preview: ['节奏'],
      },
      {
        fingerprint_id: 'fp-b', reference_work_id: 'rw-b', title: '标尺B', revision: 1,
        full_book_fingerprint: '克制', transferable_mechanisms_preview: ['视角'],
      },
    ])
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

  it('作者必须带理由与明确裁决提交，且重新读取服务器三轴', async () => {
    apiMock.qualityEvaluation.mockResolvedValue(evaluation({ withAuthor: true }))
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    fireEvent.change(screen.getByRole('spinbutton', { name: '连贯性与因果 作者评分' }), { target: { value: '5' } })
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'revise' } })
    fireEvent.change(screen.getAllByRole('textbox', { name: /裁决理由/ })[0], {
      target: { value: '因果尚缺关键代价，需继续修订。' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: '提交裁决' })[0])
    expect(apiMock.qualityAuthorJudgment).toHaveBeenCalledWith(expect.objectContaining({
      work: 'demo', seq: 7, dimension: '连贯性与因果', score: 5,
      decision: 'revise', reason: '因果尚缺关键代价，需继续修订。',
      evidence: [expect.objectContaining({ quote: '原文证据' })],
    }))
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

  it('运行中不渲染作者裁决表单', async () => {
    apiMock.qualityEvaluation.mockResolvedValue({
      chapter: 7, job_id: 'job-7', status: 'running', dimensions: [],
    })
    render(<QualityReview work="demo" seq={7} />)
    await act(async () => { await Promise.resolve() })
    expect(screen.getByText(/正在执行质量判断/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: '提交裁决' })).toBeNull()
  })

  it('用户字段带稳定 data-field-path', async () => {
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    const fields = document.querySelectorAll('[data-field-path]')
    expect(fields.length).toBeGreaterThan(0)
  })

  it('无有效章节时不读取评价且不能发起快照', async () => {
    render(<QualityReview work="demo" />)
    expect((await screen.findAllByText(/先选择章节/)).length).toBeGreaterThan(0)
    expect(apiMock.qualityEvaluation).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '创建章节评价' }).disabled).toBe(true)
  })

  it('从明确章节、合同和已批准指纹创建质量快照', async () => {
    apiMock.qualityEvaluation.mockResolvedValue({ chapter: 7, dimensions: [], status: 'empty' })
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText(/暂无质量评价/)
    fireEvent.change(screen.getByRole('textbox', { name: '质量合同 ID' }), {
      target: { value: 'contract-demo' },
    })
    // 主路径：从标尺库勾选，而非手填 ID
    fireEvent.click(await screen.findByRole('checkbox', { name: /选择标尺 标尺A/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /选择标尺 标尺B/ }))
    fireEvent.click(screen.getByRole('button', { name: '创建章节评价' }))
    await waitFor(() => expect(apiMock.qualityCreateSnapshot).toHaveBeenCalledWith({
      work: 'demo', seq: 7, contract_id: 'contract-demo', contract_revision: 1,
      reference_fingerprint_ids: ['fp-a', 'fp-b'],
    }))
    await screen.findByText('连贯性与因果')
  })

  it('创建新评价后忽略先前读取返回的旧冻结评价', async () => {
    let resolveInitialLoad
    apiMock.qualityEvaluation.mockImplementationOnce(() => new Promise((resolve) => {
      resolveInitialLoad = resolve
    }))
    apiMock.qualityCreateSnapshot.mockResolvedValue({
      chapter: 7, job_id: 'job-new', status: 'queued', dimensions: [],
    })
    render(<QualityReview work="demo" seq={7} />)
    fireEvent.change(screen.getByRole('textbox', { name: '质量合同 ID' }), {
      target: { value: 'contract-demo' },
    })
    fireEvent.click(screen.getByRole('button', { name: '创建章节评价' }))
    await waitFor(() => expect(apiMock.qualityCreateSnapshot).toHaveBeenCalled())
    resolveInitialLoad({
      ...evaluation(),
      job_id: 'job-old',
      dimensions: evaluation().dimensions.map((dimension) => ({
        ...dimension,
        system: { ...dimension.system, evidence: [{ ...dimension.system.evidence[0], quote: '旧冻结证据' }] },
      })),
    })
    expect(await screen.findByTestId('quality-job-running')).toBeTruthy()
    expect(screen.queryByText('旧冻结证据')).toBeNull()
  })

  it('创建评价失败时展示后端已脱敏的具体原因，便于作者修正输入后重试', async () => {
    apiMock.qualityCreateSnapshot.mockRejectedValue(Object.assign(
      new Error('HTTP 409'), { status: 409, body: { detail: '质量合同未获作者批准' } },
    ))
    render(<QualityReview work="demo" seq={7} />)
    await screen.findByText('连贯性与因果')
    fireEvent.change(screen.getByRole('textbox', { name: '质量合同 ID' }), {
      target: { value: 'contract-demo' },
    })
    fireEvent.click(screen.getByRole('button', { name: '创建章节评价' }))
    expect((await screen.findByRole('alert')).textContent).toContain('质量合同未获作者批准')
  })
})
