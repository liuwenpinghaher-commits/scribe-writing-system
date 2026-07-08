import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MaterialImport } from '../MaterialImport'
import { MaterialNetwork } from '../MaterialNetwork'

const apiMock = vi.hoisted(() => ({
  materialImport: vi.fn(),
  materialImportPreview: vi.fn(),
  materialImportCommit: vi.fn(),
  materialImportProgressUrl: vi.fn(),
  materialGraph: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('@react-sigma/core', () => ({
  SigmaContainer: ({ children }) => <div data-testid="sigma">{children}</div>,
  useLoadGraph: () => vi.fn(),
  useRegisterEvents: () => vi.fn(),
  useSigma: () => ({ getCamera: () => ({ animatedReset: vi.fn() }), getGraph: () => ({ nodes: () => [], hasNode: () => false }) }),
}))

let lastEventSource = null
class FakeEventSource {
  constructor(url) {
    this.url = url
    lastEventSource = this
  }
  close = vi.fn()
}

describe('素材导入可信反馈', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    lastEventSource = null
    global.EventSource = FakeEventSource
    apiMock.materialImport.mockResolvedValue({ job_id: 'job-1' })
    apiMock.materialImportProgressUrl.mockReturnValue('/api/materials/import/job-1/progress')
    apiMock.materialImportPreview.mockResolvedValue({
      items: [
        { title: '好素材', kind: 'note', body: '可导入', source: '粘贴文本' },
        { title: '坏素材', kind: 'note', body: '分类坏', source: '粘贴文本' },
      ],
    })
    apiMock.materialImportCommit.mockResolvedValue({
      created: 1,
      ids: ['m1'],
      failed: [{ index: 1, title: '坏素材', reason: '非法分类 kind=bad' }],
      warnings: [],
    })
  })

  it('提交部分失败时留在页面显示失败项和原因', async () => {
    render(<MaterialImport />)

    fireEvent.click(screen.getByRole('button', { name: '粘贴文本' }))
    fireEvent.change(screen.getByLabelText('粘贴要导入的文本'), { target: { value: '一段素材' } })
    fireEvent.click(screen.getByRole('button', { name: /开始导入/ }))

    await waitFor(() => expect(apiMock.materialImport).toHaveBeenCalled())
    act(() => {
      lastEventSource.onmessage({ data: JSON.stringify({ stage: 'done', done: 1, total: 1 }) })
    })

    expect(await screen.findByText(/解析出 2 条素材/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /确认导入/ }))

    expect(await screen.findByText(/部分导入成功/)).toBeTruthy()
    expect(screen.getByText(/成功 1 条/)).toBeTruthy()
    expect(screen.getByText(/失败 1 条/)).toBeTruthy()
    expect(screen.getByText(/坏素材/)).toBeTruthy()
    expect(screen.getByText(/非法分类 kind=bad/)).toBeTruthy()
  })
})

describe('素材网络降级反馈', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.materialGraph.mockResolvedValue({
      nodes: [{ id: 'm1', title: '孤立素材', kind: 'note', recall_count: 0, pinned: false }],
      edges: [],
      edges_degraded: true,
      degraded_sources: [{ source: 'relates', reason: 'relates 查询失败' }],
      truncated: false,
    })
  })

  it('边关系降级时仍显示节点并提示 degraded 来源', async () => {
    render(<MaterialNetwork />)

    expect(await screen.findByText(/1 素材/)).toBeTruthy()
    expect(screen.getByText(/边关系降级/)).toBeTruthy()
    expect(screen.getByText(/relates 查询失败/)).toBeTruthy()
  })
})
