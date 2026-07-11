import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ContainerOutline } from '../ContainerOutline'

const apiMock = vi.hoisted(() => ({
  outline: vi.fn(),
  addVolume: vi.fn(),
  saveChapter: vi.fn(),
  reorderChapters: vi.fn(),
  patchChapter: vi.fn(),
  patchVolume: vi.fn(),
  deleteVolume: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../NorthStarBar', () => ({ NorthStarBar: () => <div data-testid="northstar" /> }))
vi.mock('../Corkboard', () => ({ Corkboard: () => <div data-testid="corkboard" /> }))
vi.mock('../Outliner', () => ({ Outliner: () => <div data-testid="outliner" /> }))

const emptyOutline = { volumes: [], chapters: [] }

describe('ContainerOutline 错误态', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.outline.mockResolvedValue(emptyOutline)
    apiMock.addVolume.mockResolvedValue({ ok: true })
  })

  it('大纲加载失败时显示错误和重试', async () => {
    apiMock.outline
      .mockRejectedValueOnce(new Error('outline down'))
      .mockResolvedValueOnce(emptyOutline)

    render(<ContainerOutline node={{ type: 'manuscript_root', label: '手稿' }} />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/大纲加载失败/)
    fireEvent.click(screen.getByRole('button', { name: /重试/ }))

    await waitFor(() => expect(apiMock.outline).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('手稿')).toBeTruthy()
  })

  it('新建卷失败时显示可重试错误', async () => {
    apiMock.addVolume
      .mockRejectedValueOnce(new Error('add volume down'))
      .mockResolvedValueOnce({ ok: true })

    render(<ContainerOutline node={{ type: 'manuscript_root', label: '手稿' }} />)

    expect(await screen.findByText('手稿')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /新建卷/ }))
    fireEvent.change(screen.getByPlaceholderText('卷标题'), { target: { value: '第一卷' } })
    fireEvent.keyDown(screen.getByPlaceholderText('卷标题'), { key: 'Enter' })

    expect(await screen.findByRole('alert')).toHaveTextContent(/新建卷失败/)
    fireEvent.click(screen.getByRole('button', { name: /重试/ }))

    await waitFor(() => expect(apiMock.addVolume).toHaveBeenCalledTimes(2))
  })
})
