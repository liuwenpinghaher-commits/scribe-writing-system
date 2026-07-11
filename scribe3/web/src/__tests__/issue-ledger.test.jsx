import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IssueDetail } from '../capabilities/issues/IssueDetail'
import { IssueDirectory } from '../capabilities/issues/IssueDirectory'

const apiMock = vi.hoisted(() => ({
  issues: vi.fn(),
  chapter: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

const issue = {
  id: 'issue:qc:4:duplicate_lines:0',
  source: 'qc',
  severity: 'warning',
  title: '整句重复',
  reason: '同一句重复出现',
  chapter: 4,
  range: [12, 28],
  status: 'open',
  suggested_action: '删掉重复句或改写节奏',
  target_node: { id: 'ch:4', type: 'chapter', ref: 4, label: '4 情绪复读' },
}

describe('校验 issue 台账', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.issues.mockResolvedValue({ issues: [issue], degraded_sources: [] })
    // 缺省正文足够长,issue.range [12,28] 有效 → 定位可直达
    apiMock.chapter.mockResolvedValue({ prose: 'x'.repeat(200) })
  })

  it('栏2加载 issue 并点击打开详情节点', async () => {
    const onSelectItem = vi.fn()
    render(<IssueDirectory seq={4} onSelectItem={onSelectItem} />)

    await waitFor(() => expect(apiMock.issues).toHaveBeenCalledWith(4))
    expect(screen.getByText('warning')).toBeTruthy()
    fireEvent.click(within(screen.getByTestId('issue-list')).getByRole('button', { name: /整句重复/ }))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      type: 'review_issue',
      label: '整句重复',
      payload: expect.objectContaining({ chapter: 4 }),
    }))
  })

  it('栏2展示降级来源明细,失败后可重试', async () => {
    apiMock.issues
      .mockRejectedValueOnce(new Error('网络断开'))
      .mockResolvedValueOnce({
        issues: [issue],
        degraded_sources: [{ source: 'causal', chapter: 4, reason: '因果服务超时' }],
      })
    render(<IssueDirectory seq={4} onSelectItem={() => {}} />)

    expect((await screen.findByRole('alert')).textContent).toContain('网络断开')
    fireEvent.click(screen.getByRole('button', { name: /重试/ }))

    expect(await screen.findByText('整句重复')).toBeTruthy()
    expect(screen.getByText(/causal/)).toBeTruthy()
    expect(screen.getByText(/因果服务超时/)).toBeTruthy()
  })

  it('栏3展示 issue 原因、定位、修复和重查控制', async () => {
    const onLocate = vi.fn()
    const onFix = vi.fn()
    const onRecheck = vi.fn()
    render(<IssueDetail node={{ type: 'review_issue', label: '整句重复', payload: issue }} onLocate={onLocate} onFix={onFix} onRecheck={onRecheck} />)

    expect(screen.getByText('整句重复')).toBeTruthy()
    expect(screen.getByText('同一句重复出现')).toBeTruthy()
    expect(screen.getByText(/12-28/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /定位/ }))
    // 定位先按当前正文核对范围(异步),核对通过才导航
    await waitFor(() => expect(onLocate).toHaveBeenCalledWith(expect.objectContaining({ type: 'chapter', ref: 4 })))
    fireEvent.click(screen.getByRole('button', { name: /修复/ }))
    fireEvent.click(screen.getByRole('button', { name: '重新检查' }))

    expect(onFix).toHaveBeenCalledWith(expect.objectContaining({ id: issue.id }))
    expect(onRecheck).toHaveBeenCalled()
  })

  // Task 10 Step 5:正文已变化(范围越界)时不定位到错误范围,给出真实恢复路径。
  it('正文已变化时定位失败,提示重查并可真实重查恢复', async () => {
    apiMock.chapter.mockResolvedValue({ prose: '短文' })   // range [12,28] 超出当前正文
    const onLocate = vi.fn()
    const onRecheck = vi.fn()
    render(<IssueDetail node={{ type: 'review_issue', label: '整句重复', payload: issue }} onLocate={onLocate} onRecheck={onRecheck} />)

    fireEvent.click(screen.getByRole('button', { name: /定位/ }))
    expect((await screen.findByRole('alert')).textContent).toContain('正文已变化,重新检查后再定位')
    expect(onLocate).not.toHaveBeenCalled()

    // 重新检查 = 真实调用 /issues(后端即算即返),拿到新范围后恢复可定位
    apiMock.issues.mockResolvedValue({ issues: [{ ...issue, range: [0, 2] }], degraded_sources: [] })
    fireEvent.click(screen.getByRole('button', { name: '重新检查' }))
    await waitFor(() => expect(apiMock.issues).toHaveBeenCalledWith(4))
    expect(onRecheck).toHaveBeenCalled()
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
    expect(screen.getByText(/0-2/)).toBeTruthy()
  })

  it('重查后命中已不存在时如实说明,不静默', async () => {
    apiMock.issues.mockResolvedValue({ issues: [], degraded_sources: [] })
    render(<IssueDetail node={{ type: 'review_issue', label: '整句重复', payload: issue }} onLocate={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: '重新检查' }))
    expect((await screen.findByRole('alert')).textContent).toContain('已不存在')
  })

  it('无定位目标/无范围/无修复 handler 时不渲染假按钮假范围', () => {
    render(<IssueDetail node={{
      type: 'review_issue',
      label: '本章总览',
      payload: { title: '本章总览', chapter: 4, reason: '查看本章全部校验命中。' },
    }} onLocate={vi.fn()} />)

    expect(screen.queryByRole('button', { name: /定位/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /修复/ })).toBeNull()
    expect(screen.queryByText('0-0')).toBeNull()
  })
})
