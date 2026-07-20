import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReferenceWorks } from './ReferenceWorks'

const apiMock = vi.hoisted(() => ({
  referenceImport: vi.fn(),
  referenceFingerprints: vi.fn(),
  referenceGenerateFingerprint: vi.fn(),
  referenceApproveFingerprint: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('ReferenceWorks 参考作品工作台', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.referenceFingerprints.mockResolvedValue([])
    apiMock.referenceImport.mockResolvedValue({ reference_work_id: 'rw1', title: '参考A', status: 'imported' })
    apiMock.referenceGenerateFingerprint.mockResolvedValue({ fingerprint_id: 'fp1', status: 'pending_review' })
    apiMock.referenceApproveFingerprint.mockResolvedValue({ fingerprint_id: 'fp1', status: 'approved', revision: 2 })
  })

  it('粘贴文本导入参考作品', async () => {
    render(<ReferenceWorks work="demo" />)
    const titleInput = screen.getByLabelText(/标题/)
    const textInput = screen.getByLabelText(/正文|文本/)
    fireEvent.change(titleInput, { target: { value: '参考A' } })
    fireEvent.change(textInput, { target: { value: '一段参考文本' } })
    fireEvent.click(screen.getByRole('button', { name: /导入/ }))
    expect(await screen.findByText('参考A')).toBeTruthy()
    expect(apiMock.referenceImport).toHaveBeenCalled()
  })

  it('导入后显示在列表中', async () => {
    render(<ReferenceWorks work="demo" initialReferences={[{ reference_work_id: 'rw1', title: '已有参考', status: 'imported' }]} />)
    expect(await screen.findByText('已有参考')).toBeTruthy()
  })

  it('批准指纹后状态更新为已批准', async () => {
    let fpStatus = 'pending_review'
    apiMock.referenceFingerprints.mockImplementation(() => Promise.resolve([
      { fingerprint_id: 'fp1', reference_work_id: 'rw1', status: fpStatus, revision: 1, fingerprint: { full_book_fingerprint: '冷硬叙事' } },
    ]))
    apiMock.referenceApproveFingerprint.mockImplementation(() => {
      fpStatus = 'approved'
      return Promise.resolve({ fingerprint_id: 'fp1', status: 'approved', revision: 2 })
    })
    render(<ReferenceWorks work="demo" initialReferences={[{ reference_work_id: 'rw1', title: '参考A', status: 'imported' }]} />)
    expect(await screen.findByText('冷硬叙事')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /批准/ }))
    expect(await screen.findByText('已批准')).toBeTruthy()
    expect(apiMock.referenceApproveFingerprint).toHaveBeenCalled()
  })

  it('空列表显示引导文案', async () => {
    render(<ReferenceWorks work="demo" initialReferences={[]} />)
    expect(await screen.findByText(/还没有参考作品/)).toBeTruthy()
  })

  it('导入失败显示错误提示', async () => {
    apiMock.referenceImport.mockRejectedValue(new Error('导入失败'))
    render(<ReferenceWorks work="demo" />)
    fireEvent.change(screen.getByLabelText(/标题/), { target: { value: 'X' } })
    fireEvent.change(screen.getByLabelText(/正文|文本/), { target: { value: 'Y' } })
    fireEvent.click(screen.getByRole('button', { name: /导入/ }))
    expect(await screen.findByRole('alert')).toBeTruthy()
  })
})
