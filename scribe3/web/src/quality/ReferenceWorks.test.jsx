import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReferenceWorks } from './ReferenceWorks'

const apiMock = vi.hoisted(() => ({
  referenceWorks: vi.fn(),
  referenceImport: vi.fn(),
  referenceFingerprints: vi.fn(),
  referenceGenerateFingerprint: vi.fn(),
  referenceApproveFingerprint: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('ReferenceWorks 参考作品工作台', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.referenceWorks.mockResolvedValue([])
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

  it('每部参考作品有稳定卡片锚点，供重复真人验收在同书内精确操作', async () => {
    render(<ReferenceWorks work="demo" initialReferences={[
      { reference_work_id: 'rw-old', title: '历史参考', status: 'imported' },
      { reference_work_id: 'rw-new', title: '本次参考', status: 'imported' },
    ]} />)
    expect((await screen.findByTestId('reference-card-rw-new')).textContent).toContain('本次参考')
    expect(screen.getByTestId('reference-card-rw-old').textContent).toContain('历史参考')
  })

  it('重新打开工作台会回读当前作品已导入的参考作品', async () => {
    apiMock.referenceWorks.mockResolvedValue([
      { reference_work_id: 'rw-persisted', title: '持久化参考', status: 'imported' },
    ])
    render(<ReferenceWorks work="demo" />)
    expect(await screen.findByText('持久化参考')).toBeTruthy()
    expect(apiMock.referenceWorks).toHaveBeenCalledTimes(1)
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
    expect(apiMock.referenceApproveFingerprint).toHaveBeenCalledWith('rw1', 'fp1', {
      work: 'demo', corrections: { full_book_fingerprint: '冷硬叙事' },
    })
  })

  it('作者可校订指纹后再批准，校订内容作为新修订提交', async () => {
    apiMock.referenceFingerprints.mockResolvedValue([
      { fingerprint_id: 'fp1', reference_work_id: 'rw1', status: 'pending_review', revision: 1, fingerprint: { full_book_fingerprint: '冷硬叙事', transferable_mechanisms: ['动作压力'] } },
    ])
    render(<ReferenceWorks work="demo" initialReferences={[{ reference_work_id: 'rw1', title: '参考A', status: 'imported' }]} />)
    const editor = await screen.findByLabelText('指纹校订')
    fireEvent.change(editor, { target: { value: JSON.stringify({
      full_book_fingerprint: '校订后的克制悬念', transferable_mechanisms: ['声音先于反应'],
    }) } })
    fireEvent.click(screen.getByRole('button', { name: /批准/ }))
    expect(apiMock.referenceApproveFingerprint).toHaveBeenCalledWith('rw1', 'fp1', {
      work: 'demo', corrections: {
        full_book_fingerprint: '校订后的克制悬念', transferable_mechanisms: ['声音先于反应'],
      },
    })
  })

  it('已有较新批准版本时不再提供旧待审指纹的批准操作', async () => {
    apiMock.referenceFingerprints.mockResolvedValue([
      { fingerprint_id: 'fp-old', reference_work_id: 'rw1', status: 'pending_review', revision: 1, fingerprint: { full_book_fingerprint: '旧稿' } },
      { fingerprint_id: 'fp-approved', reference_work_id: 'rw1', status: 'approved', revision: 2, fingerprint: { full_book_fingerprint: '定稿' } },
    ])
    render(<ReferenceWorks work="demo" initialReferences={[{ reference_work_id: 'rw1', title: '参考A', status: 'imported' }]} />)
    expect(await screen.findByText('定稿')).toBeTruthy()
    expect(screen.queryByLabelText('批准指纹')).toBeNull()
  })

  it('导入后的参考作品可在真实工作台发起指纹生成', async () => {
    let fingerprints = []
    apiMock.referenceFingerprints.mockImplementation(() => Promise.resolve(fingerprints))
    apiMock.referenceGenerateFingerprint.mockImplementation(() => {
      fingerprints = [{
        fingerprint_id: 'fp1', reference_work_id: 'rw1', status: 'pending_review', revision: 1,
        fingerprint: { full_book_fingerprint: '克制的悬念组织' },
      }]
      return Promise.resolve(fingerprints[0])
    })
    render(<ReferenceWorks work="demo" initialReferences={[{ reference_work_id: 'rw1', title: '参考A', status: 'imported' }]} />)
    fireEvent.click(await screen.findByRole('button', { name: /生成指纹/ }))
    expect(apiMock.referenceGenerateFingerprint).toHaveBeenCalledWith('rw1', { work: 'demo' })
    expect(await screen.findByText('克制的悬念组织')).toBeTruthy()
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
