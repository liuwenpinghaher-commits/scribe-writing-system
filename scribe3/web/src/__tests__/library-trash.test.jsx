import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Library } from '../Library'

// WL-Task 3:前端作品库废弃箱(恢复/永久删除需输入书名)+ 重名就地提示。
const apiMock = vi.hoisted(() => ({
  createWork: vi.fn(),
  deleteWork: vi.fn(),
  archivedWorks: vi.fn(),
  restoreWork: vi.fn(),
  purgeWork: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

const activeWork = { slug: 'book-a', title: '纸命' }
const archivedRow = { slug: 'book-b', title: '旧稿', archived_at: '2026-07-01T10:00:00Z' }

describe('Library 删除确认文案 = 移入废弃箱语义', () => {
  beforeEach(() => { vi.clearAllMocks(); apiMock.archivedWorks.mockResolvedValue({ works: [] }) })

  it('点删除弹出的确认框文案含「废弃箱」,确认后仍调用 deleteWork', async () => {
    apiMock.deleteWork.mockResolvedValue({ ok: true, archived: true })
    const reload = vi.fn().mockResolvedValue(undefined)
    render(<Library works={[activeWork]} reload={reload} onSelect={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /删除纸命/ }))
    const confirmBtn = await screen.findByRole('button', { name: '移入废弃箱' })
    expect(screen.getAllByText(/废弃箱/).length).toBeGreaterThan(0)

    fireEvent.click(confirmBtn)
    await waitFor(() => expect(apiMock.deleteWork).toHaveBeenCalledWith('book-a'))
  })
})

describe('Library 废弃箱区', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('渲染已废弃作品:书名 + 废弃时间', async () => {
    apiMock.archivedWorks.mockResolvedValue({ works: [archivedRow] })
    render(<Library works={[activeWork]} reload={() => Promise.resolve()} onSelect={() => {}} />)

    expect(await screen.findByText('旧稿')).toBeTruthy()
    expect(await screen.findByText(/废弃箱/)).toBeTruthy()
    // 废弃时间已格式化渲染(不是裸 ISO 字符串"T"分隔)
    expect(screen.queryByText('2026-07-01T10:00:00Z')).toBeNull()
  })

  it('恢复成功:调用 restoreWork 并重拉两个列表', async () => {
    apiMock.archivedWorks.mockResolvedValue({ works: [archivedRow] })
    apiMock.restoreWork.mockResolvedValue({ ok: true })
    const reload = vi.fn().mockResolvedValue(undefined)
    render(<Library works={[activeWork]} reload={reload} onSelect={() => {}} />)

    fireEvent.click(await screen.findByRole('button', { name: /恢复旧稿/ }))
    await waitFor(() => expect(apiMock.restoreWork).toHaveBeenCalledWith('book-b'))
    await waitFor(() => expect(reload).toHaveBeenCalled())
    await waitFor(() => expect(apiMock.archivedWorks).toHaveBeenCalledTimes(2))
  })

  it('恢复 409 同名冲突:该行红字显示 detail,不整体报错', async () => {
    apiMock.archivedWorks.mockResolvedValue({ works: [archivedRow] })
    apiMock.restoreWork.mockRejectedValue(
      Object.assign(new Error('HTTP 409'), { status: 409, body: { detail: '已有同名作品「旧稿」,请先改名' } }),
    )
    render(<Library works={[activeWork]} reload={() => Promise.resolve()} onSelect={() => {}} />)

    fireEvent.click(await screen.findByRole('button', { name: /恢复旧稿/ }))
    expect(await screen.findByText(/已有同名作品「旧稿」,请先改名/)).toBeTruthy()
  })

  it('永久删除:确认按钮默认禁用,输入完整书名后才启用,确认后调 purgeWork 并重拉', async () => {
    apiMock.archivedWorks.mockResolvedValue({ works: [archivedRow] })
    apiMock.purgeWork.mockResolvedValue({ ok: true, purged: true })
    const reload = vi.fn().mockResolvedValue(undefined)
    render(<Library works={[activeWork]} reload={reload} onSelect={() => {}} />)

    fireEvent.click(await screen.findByRole('button', { name: /永久删除旧稿/ }))
    expect(await screen.findByText(/彻底销毁/)).toBeTruthy()

    const confirmBtn = screen.getByRole('button', { name: '永久删除' })
    expect(confirmBtn.disabled).toBe(true)

    const input = screen.getByRole('textbox', { name: /确认书名/ })
    fireEvent.change(input, { target: { value: '旧' } })
    expect(confirmBtn.disabled).toBe(true)

    fireEvent.change(input, { target: { value: '旧稿' } })
    expect(confirmBtn.disabled).toBe(false)

    fireEvent.click(confirmBtn)
    await waitFor(() => expect(apiMock.purgeWork).toHaveBeenCalledWith('book-b', '旧稿'))
    await waitFor(() => expect(reload).toHaveBeenCalled())
    await waitFor(() => expect(apiMock.archivedWorks).toHaveBeenCalledTimes(2))
  })

  it('works 全空(所有作品都被废弃)时,空态引导页仍显示废弃箱,不把用户锁死', async () => {
    apiMock.archivedWorks.mockResolvedValue({ works: [archivedRow] })
    render(<Library works={[]} reload={() => Promise.resolve()} onSelect={() => {}} />)

    expect(await screen.findByRole('button', { name: /新建第一部作品/ })).toBeTruthy()
    expect(await screen.findByText('旧稿')).toBeTruthy()
    expect(await screen.findByRole('button', { name: /恢复旧稿/ })).toBeTruthy()
  })
})

describe('Library 建书重名 409 就地提示', () => {
  beforeEach(() => { vi.clearAllMocks(); apiMock.archivedWorks.mockResolvedValue({ works: [] }) })

  it('409 就地红字显示 detail,输入不清空', async () => {
    apiMock.createWork.mockRejectedValue(
      Object.assign(new Error('HTTP 409'), { status: 409, body: { detail: '已有同名作品:纸命' } }),
    )
    render(<Library works={[activeWork]} reload={() => Promise.resolve()} onSelect={() => {}} />)

    const input = screen.getByRole('textbox', { name: '书名' })
    fireEvent.change(input, { target: { value: '纸命' } })
    fireEvent.click(screen.getByRole('button', { name: '建' }))

    expect(await screen.findByText(/已有同名作品/)).toBeTruthy()
    expect(input.value).toBe('纸命')
  })
})
