import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QualityContractEditor } from './QualityContractEditor'

const apiMock = vi.hoisted(() => ({
  qualityContract: vi.fn(),
  qualityCreateContract: vi.fn(),
  qualityApproveContract: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('QualityContractEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.qualityContract.mockResolvedValue({ found: false })
    apiMock.qualityCreateContract.mockResolvedValue({ approved: false })
    apiMock.qualityApproveContract.mockResolvedValue({ approved: true })
  })

  it('暴露完整合同字段并以 append-only 草案保存', async () => {
    render(<QualityContractEditor work="demo" />)
    await screen.findByLabelText('主类型')
    expect(apiMock.qualityContract).toHaveBeenCalledWith('quality-contract:demo', 1, 'demo', true)
    fireEvent.change(screen.getByLabelText('核心承诺'), {
      target: { value: '让人物每次选择都付出可见代价。' },
    })
    fireEvent.change(screen.getByLabelText('作者权重'), { target: { value: '0.6' } })
    fireEvent.click(screen.getByRole('button', { name: '保存合同草案' }))

    await waitFor(() => expect(apiMock.qualityCreateContract).toHaveBeenCalled())
    const saved = apiMock.qualityCreateContract.mock.calls[0][0]
    expect(saved).toMatchObject({
      work: 'demo',
      core_promise: '让人物每次选择都付出可见代价。',
      weights: { author: 0.6, system: 0.25, reference: 0.15 },
    })
    expect(saved.dimension_weights).toHaveLength(10)
    expect(saved.success_criteria).toHaveLength(5)
    expect(saved.evaluation_milestones).toContain('chapter')
    expect(saved.completion_criteria.length).toBeGreaterThan(0)
    expect(document.querySelectorAll('[data-field-path]').length).toBeGreaterThanOrEqual(30)
  })

  it('草案保存后可由作者明确批准', async () => {
    render(<QualityContractEditor work="demo" />)
    await screen.findByLabelText('主类型')
    fireEvent.click(screen.getByRole('button', { name: '保存合同草案' }))
    await waitFor(() => expect(apiMock.qualityCreateContract).toHaveBeenCalled())
    fireEvent.click(screen.getByRole('button', { name: '批准本修订' }))
    await waitFor(() => expect(apiMock.qualityApproveContract).toHaveBeenCalled())
  })
})
