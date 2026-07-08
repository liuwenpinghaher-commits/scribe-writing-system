import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IssueDetail } from '../capabilities/issues/IssueDetail'
import { IssueDirectory } from '../capabilities/issues/IssueDirectory'

const apiMock = vi.hoisted(() => ({
  issues: vi.fn(),
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

  it('栏3展示 issue 原因、定位、修复和重查控制', () => {
    const onLocate = vi.fn()
    const onFix = vi.fn()
    const onRecheck = vi.fn()
    render(<IssueDetail node={{ type: 'review_issue', label: '整句重复', payload: issue }} onLocate={onLocate} onFix={onFix} onRecheck={onRecheck} />)

    expect(screen.getByText('整句重复')).toBeTruthy()
    expect(screen.getByText('同一句重复出现')).toBeTruthy()
    expect(screen.getByText(/12-28/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /定位/ }))
    fireEvent.click(screen.getByRole('button', { name: /修复/ }))
    fireEvent.click(screen.getByRole('button', { name: /重查/ }))

    expect(onLocate).toHaveBeenCalledWith(expect.objectContaining({ type: 'chapter', ref: 4 }))
    expect(onFix).toHaveBeenCalledWith(expect.objectContaining({ id: issue.id }))
    expect(onRecheck).toHaveBeenCalled()
  })
})
