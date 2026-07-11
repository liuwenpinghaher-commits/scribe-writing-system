import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Library } from '../Library'
import { CodexNew } from '../CodexNew'
import { CodexDetail } from '../CodexDetail'

const apiMock = vi.hoisted(() => ({
  createWork: vi.fn(),
  deleteWork: vi.fn(),
  entities: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('Library 作品卡可访问性与状态', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('does not nest delete interaction inside the open-work button', () => {
    render(<Library works={[{ slug: 'book-a', title: '书 A' }]} reload={() => Promise.resolve()} onSelect={() => {}} />)
    const open = screen.getByRole('button', { name: /打开书 A/ })
    const remove = screen.getByRole('button', { name: /删除书 A/ })
    expect(open.contains(remove)).toBe(false)
  })

  it('作品库加载失败显示真实错误并可重试', async () => {
    const reload = vi.fn()
      .mockRejectedValueOnce(new Error('works down'))
      .mockResolvedValueOnce(undefined)
    render(<Library works={[]} reload={reload} onSelect={() => {}} />)

    expect(await screen.findByText(/works down/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(2))
  })

  it('空库显示「新建第一部作品」引导', async () => {
    render(<Library works={[]} reload={() => Promise.resolve()} onSelect={() => {}} />)
    expect(await screen.findByRole('button', { name: /新建第一部作品/ })).toBeTruthy()
    expect(screen.getByRole('textbox', { name: /书名/ })).toBeTruthy()
  })
})

describe('Codex 表单字段语义', () => {
  beforeEach(() => { vi.clearAllMocks() })

  // 规格示例断言 name '名称';真实角色字段 label 为「名字」(views/CodexView chars fieldset),按实际调整。
  it('associates codex field labels with inputs', () => {
    render(<CodexNew catType="character" label="角色" />)
    expect(screen.getByRole('textbox', { name: /名字/ })).toBeTruthy()
  })

  it('associates codex select labels in the new form', () => {
    render(<CodexNew catType="character" label="角色" />)
    expect(screen.getByRole('combobox', { name: /重要度/ })).toBeTruthy()
  })

  it('必填校验错误以 alert 语义呈现', async () => {
    render(<CodexNew catType="character" label="角色" />)
    fireEvent.click(screen.getByRole('button', { name: '创建' }))
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toMatch(/请填写名称/)
  })
})

describe('CodexDetail 载入错误如实呈现', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('请求失败给真实错误与重试,不谎称「可能已删除」', async () => {
    apiMock.entities.mockRejectedValue(new Error('backend down'))
    render(<CodexDetail node={{ id: 'character:小翠', type: 'character', ref: '小翠', label: '小翠' }} />)

    expect(await screen.findByText(/backend down/)).toBeTruthy()
    expect(screen.queryByText(/可能已删除/)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    await waitFor(() => expect(apiMock.entities).toHaveBeenCalledTimes(2))
  })
})
